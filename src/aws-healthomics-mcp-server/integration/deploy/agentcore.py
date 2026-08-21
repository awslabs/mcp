# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AgentCore_Deployment provisioning and teardown for the integration harness.

This module stands up the AgentCore_Deployment: the AWS HealthOmics MCP Server packaged as a
container image (``image/Dockerfile``) and hosted on Amazon Bedrock AgentCore Runtime with
``server_protocol: MCP``, serving ``streamable-http`` on the AgentCore container port, with
AgentCore Runtime as the *sole* network-reachable ingress and a JWT inbound authorizer
terminating authentication at the boundary.

Zero-setup provisioning
-----------------------
To make the suite deploy-and-run with no manual IAM or identity setup, provisioning creates
*everything* it needs and teardown deletes it:

1. Two **Tenant_Roles** (Tenant_A / Tenant_B) with an account-root + ``ExternalId`` trust and
   a read-only HealthOmics policy (``deploy/iam.py``).
2. An **execution role** the AgentCore container runs as, scoped to assume the Tenant_Roles,
   read the role registry, pull the image, and write logs (``deploy/iam.py``).
3. A **Cognito** user pool + app client + one user per tenant, and the minted per-tenant
   access tokens (``deploy/cognito.py``). The user pool is the OIDC provider the AgentCore
   JWT authorizer trusts; each user's ``sub`` is the tenant's registry identity.
4. The **DynamoDB role registry** mapping each ``sub`` to its Tenant_Role (``deploy/registry.py``).
5. The **ECR image** and the **AgentCore Runtime**, wired with the execution role and a
   ``customJWTAuthorizer`` pinned to the Cognito discovery URL + app-client id.

On success :func:`provision_agentcore` returns both the provisioning outcome and an
:class:`AgentCoreRunConfig` carrying the endpoint, the per-tenant bearer tokens, and the exact
expected assumed-role ARNs -- everything the integration tests need as ``AHO_ITEST_*`` inputs.
Tokens are Credential_Material: they are returned in memory and never written to the inventory
or any on-disk artifact.

Design for testability
-----------------------
The pure functions (:func:`agentcore_server_env`, :func:`agentcore_inbound_authorizer`,
:func:`agentcore_runtime_config`, :func:`agentcore_endpoint_url`, :func:`partition_for_region`)
are asserted offline. All AWS work flows through injectable seams: the FSM ``ResourceCreator``,
the DynamoDB / IAM / Cognito / STS clients. When any is ``None`` a real, boto3-backed
implementation is built lazily -- never at import time -- so importing this module and running
the offline unit tests never touch AWS.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from awslabs.aws_healthomics_mcp_server import consts
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from integration.deploy import cognito as cognito_mod
from integration.deploy import iam as iam_mod
from integration.deploy.common import (
    Clock,
    CreatedResource,
    ProvisionResult,
    ProvisionStage,
    ProvisionStatus,
    ResourceCreator,
    ResourceDeleter,
    ResourceNotFound,
    StageContext,
    TeardownResult,
    provision,
    teardown,
)
from integration.deploy.registry import (
    RESOURCE_TYPE_DYNAMODB_TABLE,
    create_dynamodb_client,
    provision_role_registry,
    registry_uri,
)
from integration.harness.headers import EXPLICIT_CREDENTIAL_HEADERS, TENANT_TOKEN_HEADER
from integration.harness.inventory import ResourceInventory
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import quote


# Deployment identifier recorded on the inventory and every resource record (Req 8.1).
DEPLOYMENT = 'agentcore'

# The container port AgentCore Runtime routes inbound MCP traffic to. AgentCore serves MCP by
# connecting to the container at the fixed address ``0.0.0.0:8000/mcp`` (there is no port
# parameter on CreateAgentRuntime), so the injected ``MCP_PORT`` must be 8000 to match.
DEFAULT_CONTAINER_PORT = 8000

# The MCP server protocol AgentCore Runtime is configured with (Req 2.3).
SERVER_PROTOCOL_MCP = 'MCP'

# The transport the container serves and the inbound mechanism the server enforces. These
# feed the injected server environment; the variable *names* come from ``consts``.
TRANSPORT_STREAMABLE_HTTP = 'streamable-http'
BIND_HOST_ALL_INTERFACES = '0.0.0.0'  # noqa: S104 - AgentCore reaches the container over its NIC
MULTI_TENANT_ENABLED = 'true'
INBOUND_AUTH_JWT = 'jwt'

# Inbound identity mechanisms the deployment can run the server with. ``jwt`` is the default
# (JWT sub -> DynamoDB registry -> tagged AssumeRole). ``explicit`` is the Option A workaround
# for accounts that deny ``sts:TagSession``: the server reads forwarded short-lived credentials
# directly (no AssumeRole, no tagging), which the harness obtains by assuming each Tenant_Role
# untagged. AgentCore still authenticates the caller at its JWT authorizer either way.
INBOUND_AUTH_EXPLICIT = 'explicit'
INBOUND_CHOICES = (INBOUND_AUTH_JWT, INBOUND_AUTH_EXPLICIT)

# The inbound authorizer type AgentCore verifies before requests reach the server (Req 2.3).
AUTHORIZER_TYPE_JWT = 'jwt'

# AgentCore Runtime network mode. A hosted runtime reachable via the AgentCore data plane uses
# ``PUBLIC``; the container port is never otherwise exposed (Req 2.4).
NETWORK_MODE_PUBLIC = 'PUBLIC'

# Inbound request headers AgentCore forwards to the container. AgentCore consumes the reserved
# ``Authorization`` header at its JWT authorizer and does not forward it even when allow-listed,
# so the harness forwards the bearer token in the non-reserved ``TENANT_TOKEN_HEADER`` instead;
# the container entrypoint maps it back onto ``Authorization`` for the server. Header names must
# match [A-Za-z][A-Za-z0-9_-]{0,255}.
REQUEST_HEADER_ALLOWLIST = (TENANT_TOKEN_HEADER,)

# The container CLI used to build/push the harness image. Configurable via this env var so
# environments with a docker-compatible CLI (e.g. ``finch``, ``podman``) can be used; defaults
# to ``docker``.
CONTAINER_CLI_ENV = 'AHO_ITEST_CONTAINER_CLI'
DEFAULT_CONTAINER_CLI = 'docker'

# AgentCore Runtime requires linux/arm64 container images, so the harness image is always built
# for that platform regardless of the build host's architecture.
IMAGE_PLATFORM = 'linux/arm64'

# ``resource_type`` values recorded in the inventory for the resources this deployment creates.
RESOURCE_TYPE_ECR_IMAGE = 'ecr-image'
RESOURCE_TYPE_AGENTCORE_RUNTIME = 'agentcore-runtime'

# Default resource names for the harness AgentCore deployment.
DEFAULT_REPOSITORY_NAME = 'aho-mcp-itest'
# AgentCore runtime names must match [a-zA-Z][a-zA-Z0-9_]{0,47} (letters, digits, underscores;
# no hyphens), so this uses underscores unlike the ECR repository/table names.
DEFAULT_RUNTIME_NAME = 'aho_mcp_itest'
DEFAULT_TABLE_NAME = 'aho-mcp-itest-registry'

# The two tenant labels the harness auto-provisions to demonstrate isolation.
DEFAULT_TENANT_LABELS = ('Tenant_A', 'Tenant_B')

# The build context for the harness image. The Dockerfile lives beside this module under
# ``image/`` and must be built from the project root (see the Dockerfile header).
_IMAGE_DIR = Path(__file__).resolve().parent / 'image'
DOCKERFILE_PATH = _IMAGE_DIR / 'Dockerfile'


def partition_for_region(region: str) -> str:
    """Return the AWS partition for ``region`` (``aws``, ``aws-cn``, or ``aws-us-gov``)."""
    if region.startswith('cn-'):
        return 'aws-cn'
    if region.startswith('us-gov-'):
        return 'aws-us-gov'
    return 'aws'


def agentcore_endpoint_url(
    *,
    region: str,
    runtime_arn: str,
    qualifier: str = 'DEFAULT',
) -> str:
    """Return the AgentCore Runtime MCP invocation endpoint for a runtime ARN.

    AgentCore exposes a hosted runtime at its data-plane invocations URL; callers reach the
    MCP server there, presenting ``Authorization: Bearer <token>`` which the runtime's JWT
    authorizer verifies. The runtime ARN is percent-encoded into the path. This is a pure
    function so it is asserted offline.

    Args:
        region: The AWS region the runtime is hosted in.
        runtime_arn: The AgentCore Runtime ARN.
        qualifier: The runtime endpoint qualifier (default ``DEFAULT``).

    Returns:
        The HTTPS invocation endpoint URL.
    """
    encoded = quote(runtime_arn, safe='')
    return (
        f'https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded}'
        f'/invocations?qualifier={qualifier}'
    )


def agentcore_server_env(
    *,
    registry_uri: str,
    container_port: int = DEFAULT_CONTAINER_PORT,
) -> dict[str, str]:
    """Return the server-facing environment injected into the AgentCore container.

    This is a pure function of the registry URI and container port. The keys are the server's
    own configuration variable names from :mod:`awslabs.aws_healthomics_mcp_server.consts`, and
    the values put the deployed server into the AgentCore posture: the ``streamable-http``
    transport bound to the AgentCore container port, multi-tenant mode enabled, the ``jwt``
    inbound mechanism enabled, and the DynamoDB role registry selected.

    Args:
        registry_uri: The ``dynamodb://<table>`` value selecting the role registry (Req 5.3).
        container_port: The container port AgentCore routes inbound MCP traffic to; defaults to
            :data:`DEFAULT_CONTAINER_PORT` (8000).

    Returns:
        A mapping of server environment variable names to their string values.
    """
    return {
        consts.MCP_TRANSPORT_ENV: TRANSPORT_STREAMABLE_HTTP,
        consts.MCP_HOST_ENV: BIND_HOST_ALL_INTERFACES,
        consts.MCP_PORT_ENV: str(container_port),
        consts.MCP_MULTI_TENANT_ENV: MULTI_TENANT_ENABLED,
        consts.MCP_INBOUND_AUTH_ENV: INBOUND_AUTH_JWT,
        consts.MCP_JWT_ROLE_REGISTRY_ENV: registry_uri,
    }


def agentcore_inbound_authorizer(
    *,
    discovery_url: Optional[str] = None,
    allowed_clients: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    """Return the inbound-authorizer descriptor for the AgentCore Runtime configuration.

    The descriptor documents the JWT authorizer AgentCore uses to cryptographically verify the
    caller's token before any request reaches the server, and that it is the sole ingress
    (Req 2.3, 2.4). When a ``discovery_url`` (and optionally ``allowed_clients``) is supplied,
    the concrete OIDC binding is included so the live runtime create can configure the real
    ``customJWTAuthorizer``; with no arguments it returns only the sole-ingress posture
    descriptor. It is pure and asserted offline.

    Args:
        discovery_url: The OIDC discovery URL the authorizer trusts (the Cognito user pool's
            ``.well-known/openid-configuration``). When ``None``, no OIDC binding is included.
        allowed_clients: The app-client ids the authorizer accepts (matched against the token's
            ``client_id``). Included only when non-empty.

    Returns:
        The inbound-authorizer descriptor.
    """
    descriptor: dict[str, Any] = {
        'type': AUTHORIZER_TYPE_JWT,
        'terminates_authentication': True,
        'sole_ingress': True,
    }
    if discovery_url is not None:
        descriptor['discovery_url'] = discovery_url
    if allowed_clients:
        descriptor['allowed_clients'] = list(allowed_clients)
    return descriptor


def agentcore_runtime_config(
    *,
    image_uri: str,
    server_env: Mapping[str, str],
    container_port: int = DEFAULT_CONTAINER_PORT,
    authorizer: Optional[Mapping[str, Any]] = None,
    execution_role_arn: Optional[str] = None,
    request_header_allowlist: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    """Return the AgentCore Runtime configuration data for the harness deployment.

    Pure function so the runtime posture is inspectable and testable without AWS access. The
    configuration pins ``server_protocol: 'MCP'`` (Req 2.3), carries the injected server
    environment (Req 2.2), records the container port the runtime routes to (Req 2.1), attaches
    the inbound-authorizer descriptor (Req 2.3, 2.4), and records the execution role the
    container runs as.

    Args:
        image_uri: The container image reference AgentCore Runtime hosts (the pushed ECR image).
        server_env: The server-facing environment to inject into the container.
        container_port: The container port AgentCore routes inbound MCP traffic to.
        authorizer: Optional inbound-authorizer descriptor; defaults to
            :func:`agentcore_inbound_authorizer`.
        execution_role_arn: Optional ARN of the execution role the container runs as.
        request_header_allowlist: Inbound header names AgentCore forwards to the container;
            defaults to :data:`REQUEST_HEADER_ALLOWLIST` (the jwt tenant-token header).

    Returns:
        The AgentCore Runtime configuration as a plain, JSON-serializable ``dict``.
    """
    return {
        'server_protocol': SERVER_PROTOCOL_MCP,
        'container': {
            'image_uri': image_uri,
            'port': container_port,
        },
        'environment': dict(server_env),
        'inbound_authorizer': dict(
            authorizer if authorizer is not None else agentcore_inbound_authorizer()
        ),
        'execution_role_arn': execution_role_arn,
        'request_header_allowlist': list(
            request_header_allowlist
            if request_header_allowlist is not None
            else REQUEST_HEADER_ALLOWLIST
        ),
        # AgentCore Runtime is the only network-reachable ingress; the container port is never
        # otherwise exposed (Req 2.4).
        'network_ingress': 'agentcore-runtime-only',
    }


def build_create_agent_runtime_kwargs(
    *,
    runtime_name: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the ``bedrock-agentcore-control:CreateAgentRuntime`` kwargs for ``config``.

    This is a pure function so the exact request shape can be validated offline against the
    botocore service model (see the boto-model smoke test) and asserted without any AWS access.
    It maps the inspectable :func:`agentcore_runtime_config` structure onto the real API
    parameters:

    - ``agentRuntimeName`` -- the runtime name.
    - ``agentRuntimeArtifact.containerConfiguration.containerUri`` -- the pushed image.
    - ``networkConfiguration.networkMode`` -- ``PUBLIC`` (AgentCore is the sole ingress).
    - ``protocolConfiguration.serverProtocol`` -- ``MCP`` (the server protocol lives here, not
      as a top-level ``serverProtocol`` parameter).
    - ``environmentVariables`` -- the injected server environment.
    - ``roleArn`` -- the execution role the container runs as (included when set).
    - ``authorizerConfiguration.customJWTAuthorizer`` -- the Cognito discovery URL and
      allowed client ids (included when a discovery URL is present).

    Args:
        runtime_name: The AgentCore Runtime name.
        config: The runtime configuration from :func:`agentcore_runtime_config`.

    Returns:
        The keyword arguments to pass to ``create_agent_runtime``.
    """
    container = dict(config.get('container', {}))
    authorizer = dict(config.get('inbound_authorizer', {}))
    kwargs: dict[str, Any] = {
        'agentRuntimeName': runtime_name,
        'agentRuntimeArtifact': {
            'containerConfiguration': {'containerUri': container.get('image_uri')},
        },
        'networkConfiguration': {'networkMode': NETWORK_MODE_PUBLIC},
        'protocolConfiguration': {
            'serverProtocol': config.get('server_protocol', SERVER_PROTOCOL_MCP),
        },
        'environmentVariables': dict(config.get('environment', {})),
        # Forward the caller's credential-bearing headers to the container (AgentCore otherwise
        # strips them). For jwt this is the tenant-token header; for explicit it is the
        # X-Aws-* credential headers.
        'requestHeaderConfiguration': {
            'requestHeaderAllowlist': list(
                config.get('request_header_allowlist', REQUEST_HEADER_ALLOWLIST)
            ),
        },
    }
    execution_role_arn = config.get('execution_role_arn')
    if execution_role_arn:
        kwargs['roleArn'] = execution_role_arn
    discovery_url = authorizer.get('discovery_url')
    if discovery_url:
        custom_jwt: dict[str, Any] = {'discoveryUrl': discovery_url}
        allowed_clients = authorizer.get('allowed_clients')
        if allowed_clients:
            custom_jwt['allowedClients'] = list(allowed_clients)
        kwargs['authorizerConfiguration'] = {'customJWTAuthorizer': custom_jwt}
    return kwargs


@dataclass(frozen=True)
class AgentCoreRunConfig:
    """Everything the integration tests need to run against a provisioned AgentCore deployment.

    Tokens are Credential_Material: this object is returned in memory to the orchestrator and
    is never persisted to the inventory or any on-disk artifact.

    Attributes:
        endpoint: The AgentCore MCP invocation endpoint.
        bearer_token: A valid bearer token for the transport test (Tenant_A's access token).
        tenant_a_token: Tenant_A's access token.
        tenant_b_token: Tenant_B's access token.
        tenant_a_expected_arn: The exact assumed-role ARN ``WhoAmI`` returns for Tenant_A.
        tenant_b_expected_arn: The exact assumed-role ARN ``WhoAmI`` returns for Tenant_B.
        inventory_path: The persisted inventory path (for teardown).
    """

    endpoint: str
    bearer_token: str
    tenant_a_token: str
    tenant_b_token: str
    tenant_a_expected_arn: str
    tenant_b_expected_arn: str
    inventory_path: Path
    # Populated only in the ``explicit`` inbound mode: the short-lived credentials the harness
    # obtained by assuming each Tenant_Role (untagged), forwarded to the server via the
    # X-Aws-* headers. ``None`` in ``jwt`` mode.
    tenant_a_creds: Optional['iam_mod.AssumedTenantCredentials'] = None
    tenant_b_creds: Optional['iam_mod.AssumedTenantCredentials'] = None

    def to_env(self) -> dict[str, str]:
        """Return the ``AHO_ITEST_*`` environment mapping the integration tests read.

        Sets the AgentCore endpoint, the per-tenant bearer tokens (the Cognito tokens the
        AgentCore JWT authorizer validates), and the expected assumed-role ARNs. In the
        ``explicit`` inbound mode it additionally exports the per-tenant short-lived AWS
        credentials the tests forward to the server via the explicit-credential headers.
        """
        env = {
            'AHO_ITEST_AGENTCORE_ENDPOINT': self.endpoint,
            'AHO_ITEST_ENDPOINT': self.endpoint,
            'AHO_ITEST_BEARER_TOKEN': self.bearer_token,
            'AHO_ITEST_TENANT_A_TOKEN': self.tenant_a_token,
            'AHO_ITEST_TENANT_B_TOKEN': self.tenant_b_token,
            'AHO_ITEST_TENANT_A_EXPECTED_ARN': self.tenant_a_expected_arn,
            'AHO_ITEST_TENANT_B_EXPECTED_ARN': self.tenant_b_expected_arn,
        }
        if self.tenant_a_creds is not None:
            # Transport test uses the single AHO_ITEST_AWS_* set (Tenant_A); the isolation test
            # uses the per-tenant AHO_ITEST_TENANT_{A,B}_AWS_* sets.
            env['AHO_ITEST_AWS_ACCESS_KEY_ID'] = self.tenant_a_creds.access_key_id
            env['AHO_ITEST_AWS_SECRET_ACCESS_KEY'] = self.tenant_a_creds.secret_access_key
            env['AHO_ITEST_AWS_SESSION_TOKEN'] = self.tenant_a_creds.session_token
            env['AHO_ITEST_TENANT_A_AWS_ACCESS_KEY_ID'] = self.tenant_a_creds.access_key_id
            env['AHO_ITEST_TENANT_A_AWS_SECRET_ACCESS_KEY'] = self.tenant_a_creds.secret_access_key
            env['AHO_ITEST_TENANT_A_AWS_SESSION_TOKEN'] = self.tenant_a_creds.session_token
        if self.tenant_b_creds is not None:
            env['AHO_ITEST_TENANT_B_AWS_ACCESS_KEY_ID'] = self.tenant_b_creds.access_key_id
            env['AHO_ITEST_TENANT_B_AWS_SECRET_ACCESS_KEY'] = self.tenant_b_creds.secret_access_key
            env['AHO_ITEST_TENANT_B_AWS_SESSION_TOKEN'] = self.tenant_b_creds.session_token
        return env


@dataclass(frozen=True)
class AgentCoreProvisionOutcome:
    """The result of :func:`provision_agentcore`.

    Attributes:
        result: The provisioning FSM outcome (COMPLETE/FAILED, endpoint, inventory path).
        run_config: The run config with tokens/endpoint/expected ARNs on COMPLETE; ``None``
            when provisioning failed before the runtime stage emitted the endpoint.
    """

    result: ProvisionResult
    run_config: Optional[AgentCoreRunConfig]


def _generate_password() -> str:
    """Return a strong, permanent Cognito password meeting the default complexity policy."""
    # 'Aho1!' guarantees upper, lower, digit, and symbol; the random suffix adds entropy.
    return 'Aho1!' + secrets.token_urlsafe(24)


def _dynamodb_table_arn(*, partition: str, region: str, account_id: str, table_name: str) -> str:
    """Return the DynamoDB table ARN the execution role is scoped to read."""
    return f'arn:{partition}:dynamodb:{region}:{account_id}:table/{table_name}'


def _resolve_account_and_partition(
    *,
    region: str,
    account_id: Optional[str],
    partition: Optional[str],
    sts_client: Optional[Any],
) -> tuple[str, str]:
    """Resolve the deployment account id and partition, calling STS lazily only if needed.

    When ``account_id`` is supplied (as unit tests do) no AWS call is made. Otherwise a real
    STS client is built lazily and ``get_caller_identity`` provides the account id. The
    partition is derived from the region unless explicitly provided.
    """
    resolved_partition = partition or partition_for_region(region)
    if account_id is not None:
        return account_id, resolved_partition
    if sts_client is None:
        import boto3

        sts_client = boto3.client('sts', region_name=region)
    resolved_account = sts_client.get_caller_identity()['Account']
    return resolved_account, resolved_partition


def provision_agentcore(
    *,
    region: str,
    inventory_path: Union[str, Path],
    table_name: str = DEFAULT_TABLE_NAME,
    account_id: Optional[str] = None,
    partition: Optional[str] = None,
    creator: Optional[ResourceCreator] = None,
    dynamodb_client: Optional[Any] = None,
    iam_client: Optional[Any] = None,
    cognito_client: Optional[Any] = None,
    sts_client: Optional[Any] = None,
    clock: Clock = time.monotonic,
    container_port: int = DEFAULT_CONTAINER_PORT,
    repository_name: str = DEFAULT_REPOSITORY_NAME,
    runtime_name: str = DEFAULT_RUNTIME_NAME,
    tenant_labels: Sequence[str] = DEFAULT_TENANT_LABELS,
    external_ids: Optional[Sequence[str]] = None,
    user_password: Optional[str] = None,
    inbound: str = INBOUND_AUTH_JWT,
) -> AgentCoreProvisionOutcome:
    """Provision the AgentCore_Deployment end-to-end and return its outcome + run config.

    Creates the Tenant_Roles, execution role, Cognito identity provider (and mints tokens), the
    DynamoDB role registry, the ECR image, and the AgentCore Runtime (wired with the execution
    role and a ``customJWTAuthorizer``), driven by the provisioning FSM. Every created resource
    is recorded into a single inventory at ``inventory_path`` as it goes, so teardown always has
    a trail (Req 8.3). Reports COMPLETE when the runtime stage emits the endpoint, or FAILED
    with the failed stage on error / budget overrun (Req 2.5-2.7).

    All AWS seams are injectable so the orchestration is offline-testable; when a seam is
    ``None`` a real, boto3-backed implementation is built lazily (never at import time).

    Args:
        region: Target AWS region; provisioned resources are recorded here (Req 8.4).
        inventory_path: Where the resource inventory is persisted; also returned on the result.
        table_name: Name of the DynamoDB role-registry table to create.
        account_id: Deployment account id. When ``None`` it is resolved via STS lazily.
        partition: AWS partition. When ``None`` it is derived from ``region``.
        creator: Optional injected FSM resource-creation seam (ECR image + AgentCore runtime).
        dynamodb_client: Optional injected DynamoDB client for the registry table.
        iam_client: Optional injected IAM client for the roles.
        cognito_client: Optional injected ``cognito-idp`` client for the identity provider.
        sts_client: Optional injected STS client used only to resolve the account id.
        clock: Monotonic clock seam (seconds); defaults to :func:`time.monotonic`.
        container_port: The AgentCore container port; defaults to :data:`DEFAULT_CONTAINER_PORT`.
        repository_name: ECR repository name for the harness image.
        runtime_name: AgentCore Runtime name.
        tenant_labels: The tenant labels to provision (default Tenant_A / Tenant_B).
        external_ids: Optional per-tenant ``ExternalId`` values; generated when ``None``.
        user_password: Optional permanent Cognito password; generated when ``None``.
        inbound: The inbound identity mechanism the server enforces -- ``'jwt'`` (default, the
            JWT-to-STS registry exchange) or ``'explicit'`` (forwarded short-lived per-tenant
            credentials, avoiding ``sts:TagSession``).

    Returns:
        An :class:`AgentCoreProvisionOutcome` with the FSM result and (on COMPLETE) run config.
    """
    if len(tenant_labels) < 2:
        raise ValueError('At least two tenant labels are required to demonstrate isolation.')
    if inbound not in INBOUND_CHOICES:
        raise ValueError(f'inbound must be one of {INBOUND_CHOICES}; got {inbound!r}.')

    resolved_account, resolved_partition = _resolve_account_and_partition(
        region=region,
        account_id=account_id,
        partition=partition,
        sts_client=sts_client,
    )
    resolved_external_ids = list(external_ids or [uuid.uuid4().hex for _ in tenant_labels])
    if len(resolved_external_ids) != len(tenant_labels):
        raise ValueError('external_ids must have one entry per tenant label.')
    password = user_password or _generate_password()

    uri = registry_uri(table_name)
    # Inject the region so the server's boto3 clients (notably the DynamoDB role-registry
    # resolver, which builds its client with no explicit region) resolve a region inside the
    # AgentCore container, which has no ~/.aws/config to fall back on. Without this the
    # registry lookup fails with a no-region error and every request is rejected 401.
    server_env = {
        **agentcore_server_env(registry_uri=uri, container_port=container_port),
        'AWS_REGION': region,
        'AWS_DEFAULT_REGION': region,
        # Select the inbound mechanism the server enforces (jwt by default, or explicit for the
        # sts:TagSession workaround).
        consts.MCP_INBOUND_AUTH_ENV: inbound,
    }
    # AgentCore forwards different credential-bearing headers depending on the mechanism.
    header_allowlist = (
        REQUEST_HEADER_ALLOWLIST if inbound == INBOUND_AUTH_JWT else EXPLICIT_CREDENTIAL_HEADERS
    )
    table_arn = _dynamodb_table_arn(
        partition=resolved_partition,
        region=region,
        account_id=resolved_account,
        table_name=table_name,
    )

    if dynamodb_client is None:
        dynamodb_client = create_dynamodb_client(region)
    if iam_client is None:
        iam_client = _create_iam_client(region)
    if cognito_client is None:
        cognito_client = _create_cognito_client(region)
    if creator is None:
        creator = create_agentcore_creator(region=region)

    # Mutable state threaded between stages, and a holder for the final run config.
    state: dict[str, Any] = {}
    run_holder: dict[str, AgentCoreRunConfig] = {}

    def _tenant_roles_stage(ctx: StageContext) -> Optional[str]:
        specs = [
            iam_mod.TenantRoleSpec(
                label=label,
                role_name=iam_mod.tenant_role_name(label),
                account_id=resolved_account,
                external_id=external_id,
                partition=resolved_partition,
            )
            for label, external_id in zip(tenant_labels, resolved_external_ids)
        ]
        state['tenant_roles'] = iam_mod.provision_tenant_roles(
            iam_client=iam_client,
            inventory=ctx.inventory,
            region=region,
            specs=specs,
        )
        return None

    def _execution_role_stage(ctx: StageContext) -> Optional[str]:
        exec_role = iam_mod.provision_execution_role(
            iam_client=iam_client,
            inventory=ctx.inventory,
            region=region,
            role_name=iam_mod.execution_role_name(),
            tenant_role_arns=[role.role_arn for role in state['tenant_roles']],
            registry_table_arn=table_arn,
        )
        state['execution_role_arn'] = exec_role.role_arn
        return None

    def _identity_provider_stage(ctx: StageContext) -> Optional[str]:
        state['idp'] = cognito_mod.provision_identity_provider(
            cognito_client=cognito_client,
            inventory=ctx.inventory,
            region=region,
            usernames=list(tenant_labels),
            password=password,
        )
        return None

    def _registry_stage(ctx: StageContext) -> Optional[str]:
        idp = state['idp']
        records = iam_mod.build_tenant_role_records(
            created_roles=state['tenant_roles'],
            subs=[user.sub for user in idp.users],
            external_ids=resolved_external_ids,
            account_ids=[resolved_account for _ in tenant_labels],
        )
        provision_role_registry(
            dynamodb_client=dynamodb_client,
            table_name=table_name,
            region=region,
            records=records,
            inventory=ctx.inventory,
        )
        return None

    def _image_stage(ctx: StageContext) -> Optional[str]:
        created = ctx.create(
            RESOURCE_TYPE_ECR_IMAGE,
            repository=repository_name,
            dockerfile=str(DOCKERFILE_PATH),
            build_context=str(_IMAGE_DIR.parent.parent.parent),
        )
        state['image_uri'] = created.resource_id
        return None

    def _runtime_stage(ctx: StageContext) -> Optional[str]:
        idp = state['idp']
        authorizer = agentcore_inbound_authorizer(
            discovery_url=idp.discovery_url,
            allowed_clients=[idp.app_client_id],
        )
        runtime_config = agentcore_runtime_config(
            image_uri=state['image_uri'],
            server_env=server_env,
            container_port=container_port,
            authorizer=authorizer,
            execution_role_arn=state['execution_role_arn'],
            request_header_allowlist=header_allowlist,
        )
        created = ctx.create(
            RESOURCE_TYPE_AGENTCORE_RUNTIME,
            runtime_name=runtime_name,
            config=runtime_config,
        )
        endpoint = created.endpoint
        if endpoint is None:
            raise ValueError('AgentCore runtime creation did not emit an endpoint reference.')

        roles = state['tenant_roles']
        if inbound == INBOUND_AUTH_EXPLICIT:
            # Assume each Tenant_Role untagged (allowed even where sts:TagSession is denied) and
            # forward the resulting credentials to the server via the explicit-credential
            # headers. The assumed-role ARN is exactly what WhoAmI reports for those creds.
            assume_client = sts_client if sts_client is not None else _create_sts_client(region)
            creds_a = iam_mod.assume_tenant_role(
                sts_client=assume_client,
                role_arn=roles[0].role_arn,
                external_id=resolved_external_ids[0],
            )
            creds_b = iam_mod.assume_tenant_role(
                sts_client=assume_client,
                role_arn=roles[1].role_arn,
                external_id=resolved_external_ids[1],
            )
            run_holder['config'] = AgentCoreRunConfig(
                endpoint=endpoint,
                bearer_token=idp.users[0].access_token,
                tenant_a_token=idp.users[0].access_token,
                tenant_b_token=idp.users[1].access_token,
                tenant_a_expected_arn=creds_a.assumed_role_arn,
                tenant_b_expected_arn=creds_b.assumed_role_arn,
                inventory_path=Path(inventory_path),
                tenant_a_creds=creds_a,
                tenant_b_creds=creds_b,
            )
        else:
            run_holder['config'] = AgentCoreRunConfig(
                endpoint=endpoint,
                bearer_token=idp.users[0].access_token,
                tenant_a_token=idp.users[0].access_token,
                tenant_b_token=idp.users[1].access_token,
                tenant_a_expected_arn=iam_mod.expected_assumed_role_arn(
                    role_arn=roles[0].role_arn, caller_sub=idp.users[0].sub
                ),
                tenant_b_expected_arn=iam_mod.expected_assumed_role_arn(
                    role_arn=roles[1].role_arn, caller_sub=idp.users[1].sub
                ),
                inventory_path=Path(inventory_path),
            )
        return endpoint

    stages = [
        ProvisionStage(name='create-tenant-roles', run=_tenant_roles_stage),
        ProvisionStage(name='create-execution-role', run=_execution_role_stage),
        ProvisionStage(name='create-identity-provider', run=_identity_provider_stage),
        ProvisionStage(name='create-role-registry', run=_registry_stage),
        ProvisionStage(name='build-push-image', run=_image_stage),
        ProvisionStage(name='create-agentcore-runtime', run=_runtime_stage),
    ]

    result = provision(
        deployment=DEPLOYMENT,
        region=region,
        stages=stages,
        creator=creator,
        inventory_path=inventory_path,
        clock=clock,
    )

    run_config = run_holder.get('config') if result.status is ProvisionStatus.COMPLETE else None
    return AgentCoreProvisionOutcome(result=result, run_config=run_config)


def teardown_agentcore(
    *,
    inventory_path: Optional[Union[str, Path]] = None,
    inventory: Optional[ResourceInventory] = None,
    deleter: Optional[ResourceDeleter] = None,
) -> TeardownResult:
    """Tear down a provisioned AgentCore_Deployment and report the outcome.

    Deletes every resource recorded in the deployment's inventory (Tenant_Roles, execution
    role, Cognito user pool, DynamoDB registry, ECR image, and AgentCore Runtime) through an
    injectable ``deleter`` seam, treating already-absent resources as deleted so re-runs are
    idempotent (Req 8.2, 8.5, 8.7). Exactly one of ``inventory`` or ``inventory_path`` must be
    supplied. When ``deleter`` is ``None`` a real, boto3-backed deleter is built lazily using
    the inventory's region.

    Args:
        inventory_path: Path to a persisted inventory to tear down (used when ``inventory`` is
            ``None``).
        inventory: An already-loaded inventory to tear down. Takes precedence over the path.
        deleter: Optional injected resource-deletion seam.

    Returns:
        A :class:`~integration.deploy.common.TeardownResult`.

    Raises:
        ValueError: If neither ``inventory`` nor ``inventory_path`` is provided.
    """
    if inventory is None and inventory_path is None:
        raise ValueError('teardown_agentcore requires either inventory or inventory_path.')
    if inventory is None:
        inventory = ResourceInventory.load(inventory_path)  # type: ignore[arg-type]
    if deleter is None:
        deleter = create_agentcore_deleter(region=inventory.region)
    return teardown(inventory=inventory, deleter=deleter)


# ---------------------------------------------------------------------------
# Live-AWS seams (boto3-backed). Built lazily by the orchestration functions above; never
# constructed at import time and never exercised by the offline unit tests, which inject fakes.
# ---------------------------------------------------------------------------


def _create_iam_client(region: str) -> Any:
    """Build a boto3 IAM client for live provisioning/teardown (lazy import)."""
    import boto3

    return boto3.client('iam', region_name=region)


def _create_sts_client(region: str) -> Any:
    """Build a boto3 STS client (operator credentials) for assuming Tenant_Roles (lazy import)."""
    import boto3

    return boto3.client('sts', region_name=region)


def _create_cognito_client(region: str) -> Any:
    """Build a boto3 ``cognito-idp`` client for live provisioning/teardown (lazy import)."""
    import boto3

    return boto3.client('cognito-idp', region_name=region)


def create_agentcore_creator(*, region: str) -> ResourceCreator:
    """Build a real, boto3-backed :class:`ResourceCreator` for live provisioning.

    Handles the FSM-created resources (the ECR image and the AgentCore Runtime); the IAM,
    Cognito, and DynamoDB resources are created directly by their modules' provision functions
    through their injected clients. boto3 is imported inside the callables so importing this
    module stays offline.

    Args:
        region: Target AWS region for the created resources.

    Returns:
        A resource-creation callable matching the ``ResourceCreator`` protocol.
    """

    def _create(resource_type: str, /, **params: Any) -> CreatedResource:
        if resource_type == RESOURCE_TYPE_ECR_IMAGE:
            return _build_and_push_image(region=region, **params)
        if resource_type == RESOURCE_TYPE_AGENTCORE_RUNTIME:
            return _create_agentcore_runtime(region=region, **params)
        raise ValueError(f'Unsupported AgentCore resource type: {resource_type!r}')

    return _create


def create_agentcore_deleter(*, region: str) -> ResourceDeleter:
    """Build a real, boto3-backed :class:`ResourceDeleter` for live teardown.

    Deletes every resource type the deployment records -- Tenant_Roles / execution role,
    Cognito user pool, DynamoDB registry table, ECR image/repository, and AgentCore Runtime --
    using lazily constructed, region-cached clients. It raises
    :class:`~integration.deploy.common.ResourceNotFound` when a resource is already absent so
    teardown stays idempotent (Req 8.7).

    Args:
        region: AWS region the resources live in.

    Returns:
        A resource-deletion callable matching the ``ResourceDeleter`` protocol.
    """
    from integration.harness.inventory import ResourceRecord  # local import: offline-safe

    clients: dict[str, Any] = {}

    def _client(service: str) -> Any:
        client = clients.get(service)
        if client is None:
            if service == 'iam':
                client = _create_iam_client(region)
            elif service == 'cognito-idp':
                client = _create_cognito_client(region)
            elif service == 'dynamodb':
                client = create_dynamodb_client(region)
            else:  # pragma: no cover - only the services below are requested
                import boto3

                client = boto3.client(service, region_name=region)
            clients[service] = client
        return client

    def _delete(record: ResourceRecord, /) -> None:
        if record.resource_type == iam_mod.RESOURCE_TYPE_IAM_ROLE:
            iam_mod.delete_iam_role(iam_client=_client('iam'), role_name=record.resource_id)
        elif record.resource_type == cognito_mod.RESOURCE_TYPE_COGNITO_USER_POOL:
            cognito_mod.delete_user_pool(
                cognito_client=_client('cognito-idp'), user_pool_id=record.resource_id
            )
        elif record.resource_type == RESOURCE_TYPE_DYNAMODB_TABLE:
            _delete_dynamodb_table(region=region, table_name=record.resource_id)
        elif record.resource_type == RESOURCE_TYPE_ECR_IMAGE:
            _delete_ecr_image(region=region, image_uri=record.resource_id)
        elif record.resource_type == RESOURCE_TYPE_AGENTCORE_RUNTIME:
            _delete_agentcore_runtime(region=region, runtime_id=record.resource_id)
        else:
            raise ValueError(f'Unsupported AgentCore resource type: {record.resource_type!r}')

    return _delete


def _build_and_push_image(
    *,
    region: str,
    repository: str,
    dockerfile: str,
    build_context: str,
    **_ignored: Any,
) -> CreatedResource:
    """Build the harness image and push it to ECR, returning the pushed image URI.

    Live path only. boto3 and subprocess are imported lazily so this module imports offline.
    """
    import base64
    import boto3
    import subprocess

    container_cli = os.environ.get(CONTAINER_CLI_ENV, DEFAULT_CONTAINER_CLI)

    # The harness image builds FROM public.ecr.aws base images, so authenticate to public ECR
    # first (its registry lives only in us-east-1). Without this the base-image pull can fail
    # with HTTP 403 when the container CLI otherwise sends private-registry credentials.
    public_ecr = boto3.client('ecr-public', region_name='us-east-1')
    public_auth = public_ecr.get_authorization_token()['authorizationData']
    public_token = base64.b64decode(public_auth['authorizationToken']).decode('utf-8')
    _public_user, public_password = public_token.split(':', 1)
    subprocess.run(
        [container_cli, 'login', '--username', 'AWS', '--password-stdin', 'public.ecr.aws'],
        input=public_password.encode('utf-8'),
        check=True,
    )

    ecr = boto3.client('ecr', region_name=region)
    try:
        ecr.create_repository(repositoryName=repository)
    except ecr.exceptions.RepositoryAlreadyExistsException:
        pass

    registry = ecr.describe_repositories(repositoryNames=[repository])['repositories'][0]
    repository_uri = registry['repositoryUri']
    image_uri = f'{repository_uri}:latest'

    auth = ecr.get_authorization_token()['authorizationData'][0]
    token = base64.b64decode(auth['authorizationToken']).decode('utf-8')
    _username, password = token.split(':', 1)
    endpoint = auth['proxyEndpoint']

    subprocess.run(
        [container_cli, 'login', '--username', 'AWS', '--password-stdin', endpoint],
        input=password.encode('utf-8'),
        check=True,
    )
    subprocess.run(
        [
            container_cli,
            'build',
            '--platform',
            IMAGE_PLATFORM,
            '-f',
            dockerfile,
            '-t',
            image_uri,
            build_context,
        ],
        check=True,
    )
    subprocess.run([container_cli, 'push', image_uri], check=True)

    return CreatedResource(
        resource_id=image_uri,
        resource_type=RESOURCE_TYPE_ECR_IMAGE,
        attributes={'repository': repository},
    )


def _create_agentcore_runtime(
    *,
    region: str,
    runtime_name: str,
    config: Mapping[str, Any],
    **_ignored: Any,
) -> CreatedResource:
    """Create the AgentCore Runtime from ``config`` and return its identity + endpoint.

    Wires the execution role and the ``customJWTAuthorizer`` (Cognito discovery URL +
    app-client id) so AgentCore terminates authentication at the boundary and the container
    runs as the scoped execution role. Live path only; boto3 is imported lazily.
    """
    import boto3

    client = boto3.client('bedrock-agentcore-control', region_name=region)
    kwargs = build_create_agent_runtime_kwargs(runtime_name=runtime_name, config=config)

    response = client.create_agent_runtime(**kwargs)

    runtime_arn = response['agentRuntimeArn']
    # Delete requires the runtime *id*, not the ARN, so the id is what we record for teardown;
    # the ARN is used only to build the invocation endpoint and is kept as an attribute.
    runtime_id = response['agentRuntimeId']
    # A freshly created runtime starts in CREATING and is not invokable until READY, so wait
    # before emitting the endpoint (otherwise the first client connection times out).
    _wait_for_runtime_ready(client, runtime_id)
    endpoint = agentcore_endpoint_url(region=region, runtime_arn=runtime_arn)
    return CreatedResource(
        resource_id=runtime_id,
        resource_type=RESOURCE_TYPE_AGENTCORE_RUNTIME,
        attributes={'endpoint': endpoint, 'runtime_arn': runtime_arn},
        endpoint=endpoint,
    )


def _wait_for_runtime_ready(
    client: Any,
    runtime_id: str,
    *,
    timeout_s: float = 300.0,
    interval_s: float = 5.0,
) -> None:
    """Poll ``GetAgentRuntime`` until the runtime is READY, or raise on failure/timeout.

    A freshly created AgentCore Runtime is ``CREATING`` and cannot be invoked until it reaches
    ``READY``; this bounded poll gates the emitted endpoint on readiness so the transport test
    does not connect before the runtime can serve. Live path only.

    Args:
        client: The ``bedrock-agentcore-control`` client.
        runtime_id: The runtime id to poll.
        timeout_s: Maximum seconds to wait for READY.
        interval_s: Seconds between polls.

    Raises:
        RuntimeError: If the runtime enters a ``*_FAILED`` state (with its failure reason).
        TimeoutError: If the runtime is not READY within ``timeout_s``.
    """
    import time as _time

    deadline = _time.monotonic() + timeout_s
    while True:
        described = client.get_agent_runtime(agentRuntimeId=runtime_id)
        status = described.get('status')
        if status == 'READY':
            return
        if status in ('CREATE_FAILED', 'UPDATE_FAILED'):
            reason = described.get('failureReason', '<no reason reported>')
            raise RuntimeError(f'AgentCore runtime {runtime_id!r} entered {status}: {reason}')
        if _time.monotonic() > deadline:
            raise TimeoutError(
                f'AgentCore runtime {runtime_id!r} did not become READY within '
                f'{timeout_s:g}s (last status={status!r})'
            )
        _time.sleep(interval_s)


def _delete_dynamodb_table(*, region: str, table_name: str) -> None:
    """Delete the DynamoDB registry table, mapping not-found to ``ResourceNotFound``."""
    import boto3

    client = boto3.client('dynamodb', region_name=region)
    try:
        client.delete_table(TableName=table_name)
    except client.exceptions.ResourceNotFoundException as exc:
        raise ResourceNotFound(f'DynamoDB table {table_name!r} already absent.') from exc


def _delete_ecr_image(*, region: str, image_uri: str) -> None:
    """Delete the ECR repository backing the pushed image, mapping not-found to ResourceNotFound."""
    import boto3

    # image_uri is '<account>.dkr.ecr.<region>.amazonaws.com/<repository>:<tag>'.
    repository = image_uri.split('/', 1)[-1].split(':', 1)[0]
    client = boto3.client('ecr', region_name=region)
    try:
        client.delete_repository(repositoryName=repository, force=True)
    except client.exceptions.RepositoryNotFoundException as exc:
        raise ResourceNotFound(f'ECR repository {repository!r} already absent.') from exc


def _delete_agentcore_runtime(*, region: str, runtime_id: str) -> None:
    """Delete the AgentCore Runtime, mapping not-found to ``ResourceNotFound``."""
    import boto3
    from botocore.exceptions import ClientError  # noqa: I001

    client = boto3.client('bedrock-agentcore-control', region_name=region)
    try:
        client.delete_agent_runtime(agentRuntimeId=runtime_id)
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') == 'ResourceNotFoundException':
            raise ResourceNotFound(f'AgentCore runtime {runtime_id!r} already absent.') from exc
        raise
