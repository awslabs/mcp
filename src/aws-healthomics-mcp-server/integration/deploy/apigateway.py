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

"""ApiGateway_Deployment provisioning/teardown for the integration harness.

This module plugs a deployment-specific stage list and a real, boto3-backed
:class:`~integration.deploy.common.ResourceCreator` into the deployment-agnostic
provisioning FSM in :mod:`integration.deploy.common`. It stands up the
ApiGateway_Deployment described in the design:

- The server runs bound to the loopback address ``127.0.0.1`` with multi-tenant
  mode and the ``jwt`` inbound mechanism enabled, so it is not reachable on any
  non-loopback interface (Req 3.2, 3.6). A caller that tries to reach the server
  directly has the connection refused (Req 3.5).
- Amazon API Gateway is placed in front of the server as the *only*
  network-reachable entry point via a **private integration** (a VPC link to the
  loopback-bound server's private target). API Gateway authenticates callers with
  an authorizer and forwards only authenticated requests (Req 3.1, 3.3, 3.4).
- The DynamoDB role registry is provisioned first (see
  :func:`integration.deploy.registry.provision_role_registry`) and its
  ``dynamodb://<table>`` URI is injected into the server environment (Req 5.3).
- The API Gateway invoke endpoint is emitted as the deployment's endpoint
  reference, at which point the FSM reports the deployment complete (Req 3.7);
  a stage error or the 900s budget being exceeded reports it failed with the
  failed stage and a human-readable cause (Req 3.8, 3.9).

Testability / AWS isolation
---------------------------
The server environment and the API Gateway configuration are computed by the
**pure** functions :func:`apigateway_server_env` and :func:`apigateway_config`,
which are deterministic, take no I/O, and are unit-testable offline (task 10.4).
Every AWS call flows through injected seams -- the ``ResourceCreator`` /
``ResourceDeleter`` of the FSM and the injected DynamoDB client of the registry
module -- so no boto3 client is constructed at import time or during unit tests.
:func:`provision_apigateway` and :func:`teardown_apigateway` build the real,
boto3-backed seams lazily only when the caller does not inject one, so the live
clients are never created at import.
"""

from __future__ import annotations

import os
import time
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import build_user_agent_extra
from collections.abc import Mapping, Sequence
from integration.deploy.common import (
    Clock,
    CreatedResource,
    ProvisionResult,
    ProvisionStage,
    ResourceDeleter,
    ResourceNotFound,
    StageContext,
    TeardownResult,
    provision,
    teardown,
    teardown_from_path,
)
from integration.deploy.registry import (
    RESOURCE_TYPE_DYNAMODB_TABLE,
    create_dynamodb_client,
    provision_role_registry,
    registry_uri,
)
from integration.harness.inventory import ResourceInventory, ResourceRecord
from integration.harness.tenants import TenantRecord
from pathlib import Path
from typing import Any, Optional


# The deployment identifier recorded on the inventory and every resource record.
DEPLOYMENT = 'apigateway'

# Server-facing configuration values injected into the loopback-bound server. These
# mirror the design's "Deployment configuration (server-facing env)" table for the
# API Gateway column and reuse the server's own constant for the loopback host so the
# harness and server share one source of truth (consts.DEFAULT_HTTP_HOST == '127.0.0.1').
SERVER_TRANSPORT = 'streamable-http'
LOOPBACK_HOST = consts.DEFAULT_HTTP_HOST
MULTI_TENANT_VALUE = 'true'
INBOUND_AUTH_VALUE = 'jwt'

# Resource-type tags recorded in the inventory for the resources this deployment creates.
RESOURCE_TYPE_SERVER = 'apigateway-server'
RESOURCE_TYPE_VPC_LINK = 'apigateway-vpclink'
RESOURCE_TYPE_REST_API = 'apigateway-restapi'

# API Gateway configuration defaults (all inspectable via apigateway_config).
DEFAULT_STAGE_NAME = 'itest'
DEFAULT_AUTHORIZER_NAME = 'aho-mcp-itest-authorizer'
# A TOKEN Lambda authorizer verifies a single bearer token from the Authorization
# header -- the shape the harness's JWT test callers present.
DEFAULT_AUTHORIZER_TYPE = 'TOKEN'
DEFAULT_AUTHORIZER_IDENTITY_SOURCE = 'method.request.header.Authorization'
# The method requires the custom authorizer so unauthenticated requests are rejected
# at the gateway and never forwarded to the server (Req 3.4).
METHOD_AUTHORIZATION = 'CUSTOM'
# A private integration: API Gateway reaches the loopback-bound server through a VPC
# link rather than a public address, keeping API Gateway the sole reachable ingress.
INTEGRATION_TYPE = 'HTTP_PROXY'
INTEGRATION_CONNECTION_TYPE = 'VPC_LINK'
INTEGRATION_HTTP_METHOD = 'ANY'
ENDPOINT_TYPE = 'REGIONAL'

# Environment variables carrying the live-only compute/network inputs the operator
# provisions per the documented, repeatable definition (Req 8.1). The loopback-bound
# server host and the network-load-balancer target that the API Gateway VPC link
# fronts, and the authorizer Lambda's invoke ARN, cannot be fabricated by the harness;
# they are supplied to the live creator here. These are read only by the live
# (boto3-backed) creator, never by the pure functions or unit tests.
SERVER_TARGET_ENV = 'AHO_ITEST_APIGW_SERVER_TARGET'
VPC_LINK_TARGET_ARNS_ENV = 'AHO_ITEST_APIGW_VPC_LINK_TARGET_ARNS'
AUTHORIZER_URI_ENV = 'AHO_ITEST_APIGW_AUTHORIZER_URI'


def apigateway_server_env(*, registry_uri: str) -> dict[str, str]:
    """Return the server-facing environment injected into the loopback-bound server.

    This is a pure function of the registry URI: for the ApiGateway_Deployment the
    server runs the ``streamable-http`` transport bound to the loopback address with
    multi-tenant mode and the ``jwt`` inbound mechanism enabled, reading its per-tenant
    role mappings from the DynamoDB registry named by ``registry_uri``. The returned
    keys use the server's own environment-variable names (see
    :mod:`awslabs.aws_healthomics_mcp_server.consts`) so the harness never invents new
    server configuration:

    - ``MCP_TRANSPORT`` = ``streamable-http``
    - ``MCP_HOST`` = ``127.0.0.1`` (the loopback host; Req 3.2)
    - ``MCP_MULTI_TENANT`` = ``true`` (Req 3.6)
    - ``MCP_INBOUND_AUTH`` = ``jwt`` (Req 3.6)
    - ``MCP_JWT_ROLE_REGISTRY`` = the ``dynamodb://<table>`` registry URI (Req 5.3)

    Args:
        registry_uri: The ``dynamodb://<table>`` value selecting the role registry.

    Returns:
        The server environment mapping (all values are strings).
    """
    return {
        consts.MCP_TRANSPORT_ENV: SERVER_TRANSPORT,
        consts.MCP_HOST_ENV: LOOPBACK_HOST,
        consts.MCP_MULTI_TENANT_ENV: MULTI_TENANT_VALUE,
        consts.MCP_INBOUND_AUTH_ENV: INBOUND_AUTH_VALUE,
        consts.MCP_JWT_ROLE_REGISTRY_ENV: registry_uri,
    }


def apigateway_config(
    *,
    api_name: str,
    server_host: str = LOOPBACK_HOST,
    server_port: int = consts.DEFAULT_HTTP_PORT,
    server_path: str = consts.DEFAULT_HTTP_PATH,
    authorizer_name: str = DEFAULT_AUTHORIZER_NAME,
    authorizer_type: str = DEFAULT_AUTHORIZER_TYPE,
    authorizer_identity_source: str = DEFAULT_AUTHORIZER_IDENTITY_SOURCE,
    stage_name: str = DEFAULT_STAGE_NAME,
) -> dict[str, Any]:
    """Return the inspectable API Gateway configuration for the deployment.

    This is a pure function describing the API Gateway topology the deployment builds:
    a regional REST API whose sole reachable ingress requires an authorizer and whose
    integration is *private* (a VPC link to the loopback-bound server). The returned
    structure is deterministic and free of I/O so it can be asserted offline:

    - ``authorizer`` -- the caller-authenticating authorizer that the method requires,
      so an unauthenticated request is rejected at the gateway (Req 3.3, 3.4).
    - ``integration`` -- a private (``VPC_LINK``) ``HTTP_PROXY`` integration to the
      loopback-bound server target, so API Gateway remains the only network-reachable
      entry point and the server is never bound to a non-loopback interface (Req 3.1,
      3.2, 3.5).
    - ``method`` -- requires ``CUSTOM`` authorization (the authorizer above).
    - ``sole_ingress`` -- records the invariant that API Gateway is the only ingress.

    Args:
        api_name: The REST API name.
        server_host: The loopback host the server binds; defaults to ``127.0.0.1``.
        server_port: The port the server listens on behind the private integration.
        server_path: The request path the server serves (default ``/mcp``).
        authorizer_name: The API Gateway authorizer name.
        authorizer_type: The API Gateway authorizer type (default ``TOKEN``).
        authorizer_identity_source: The request field the authorizer reads the token
            from (default the ``Authorization`` header).
        stage_name: The deployment stage name.

    Returns:
        A nested, JSON-serializable dict describing the API Gateway configuration.
    """
    return {
        'api_name': api_name,
        'endpoint_type': ENDPOINT_TYPE,
        'stage_name': stage_name,
        'server': {
            'host': server_host,
            'port': server_port,
            'path': server_path,
        },
        'authorizer': {
            'name': authorizer_name,
            'type': authorizer_type,
            'identity_source': authorizer_identity_source,
        },
        'method': {
            'http_method': INTEGRATION_HTTP_METHOD,
            'authorization': METHOD_AUTHORIZATION,
        },
        'integration': {
            'type': INTEGRATION_TYPE,
            'connection_type': INTEGRATION_CONNECTION_TYPE,
            'http_method': INTEGRATION_HTTP_METHOD,
            'target_path': server_path,
        },
        'sole_ingress': True,
    }


def _api_name(table_name: str) -> str:
    """Derive a deterministic REST API name from the registry table name."""
    return f'{table_name}-apigw'


def _registry_stage(
    *,
    dynamodb_client: Any,
    table_name: str,
    region: str,
    tenant_records: Sequence[TenantRecord],
) -> ProvisionStage:
    """Build the stage that creates the DynamoDB role registry and writes tenants.

    The registry table is created and the Tenant_A / Tenant_B records are written
    through :func:`provision_role_registry`, which records the table into the FSM's
    inventory at creation so a mid-flight failure still leaves a teardown trail
    (Req 8.3). This stage emits no endpoint.
    """

    def run(ctx: StageContext) -> Optional[str]:
        provision_role_registry(
            dynamodb_client=dynamodb_client,
            table_name=table_name,
            region=region,
            records=tenant_records,
            inventory=ctx.inventory,
        )
        return None

    return ProvisionStage(name='create-role-registry', run=run)


def _server_stage(*, server_env: Mapping[str, str]) -> ProvisionStage:
    """Build the stage that stands up the loopback-bound server and its VPC link.

    The server is created bound to ``127.0.0.1`` with the injected environment
    (Req 3.2, 3.6), and the private-integration plumbing (a VPC link fronting the
    server's private target) is created so API Gateway can reach the loopback-bound
    server without exposing it publicly (Req 3.1). Both resources are recorded in the
    inventory at creation. This stage emits no endpoint.
    """

    def run(ctx: StageContext) -> Optional[str]:
        ctx.create(RESOURCE_TYPE_SERVER, server_env=dict(server_env))
        ctx.create(RESOURCE_TYPE_VPC_LINK)
        return None

    return ProvisionStage(name='start-loopback-server', run=run)


def _apigateway_stage(
    *,
    config: Mapping[str, Any],
    server_env: Mapping[str, str],
) -> ProvisionStage:
    """Build the stage that creates the API Gateway ingress and emits the endpoint.

    The REST API, its authorizer, and the private (``VPC_LINK``) integration are
    created from ``config`` as the sole network-reachable ingress (Req 3.1, 3.3, 3.4).
    The stage returns the API Gateway invoke endpoint, which the FSM reports as the
    deployment's endpoint reference (Req 3.7).
    """

    def run(ctx: StageContext) -> Optional[str]:
        created = ctx.create(
            RESOURCE_TYPE_REST_API,
            config=dict(config),
            server_env=dict(server_env),
        )
        return created.endpoint

    return ProvisionStage(name='create-api-gateway', run=run)


def provision_apigateway(
    *,
    region: str,
    table_name: str,
    tenant_records: Sequence[TenantRecord],
    inventory_path: str | Path,
    creator: Optional[Any] = None,
    dynamodb_client: Optional[Any] = None,
    clock: Clock = time.monotonic,
) -> ProvisionResult:
    """Provision the ApiGateway_Deployment and return the provisioning outcome.

    Computes the registry URI (``dynamodb://<table>``) and the pure server
    environment / API Gateway configuration up front, then runs the provisioning FSM
    over three stages: create the DynamoDB role registry and tenant records, stand up
    the loopback-bound server and its private-integration VPC link, and create the API
    Gateway ingress (authorizer + private integration) which emits the endpoint
    reference. The FSM reports :class:`~integration.deploy.common.ProvisionStatus.COMPLETE`
    when the endpoint is emitted (Req 3.7) or ``FAILED`` with the failed stage and a
    human-readable cause on error or on exceeding the 900s budget (Req 3.8, 3.9).

    The ``creator`` and ``dynamodb_client`` seams are injected: unit tests pass fakes so
    no AWS call leaves the process, while live callers leave them ``None`` and this
    function builds the real, boto3-backed clients lazily (never at import).

    Args:
        region: The target AWS region; provisioned resources are recorded here (Req 8.4).
        table_name: Name of the DynamoDB role-registry table to create.
        tenant_records: The tenant records to write (Tenant_A / Tenant_B, >= 2).
        inventory_path: Where the resource inventory is persisted for teardown.
        creator: Optional injected resource-creation seam; built lazily when ``None``.
        dynamodb_client: Optional injected DynamoDB client; built lazily when ``None``.
        clock: Monotonic clock seam; defaults to :func:`time.monotonic`.

    Returns:
        The :class:`~integration.deploy.common.ProvisionResult` for the run.
    """
    uri = registry_uri(table_name)
    server_env = apigateway_server_env(registry_uri=uri)
    config = apigateway_config(api_name=_api_name(table_name))

    if dynamodb_client is None:
        dynamodb_client = create_dynamodb_client(region)
    if creator is None:
        creator = _LiveApiGatewayCreator(region=region)

    stages = [
        _registry_stage(
            dynamodb_client=dynamodb_client,
            table_name=table_name,
            region=region,
            tenant_records=tenant_records,
        ),
        _server_stage(server_env=server_env),
        _apigateway_stage(config=config, server_env=server_env),
    ]

    return provision(
        deployment=DEPLOYMENT,
        region=region,
        stages=stages,
        creator=creator,
        inventory_path=inventory_path,
        clock=clock,
    )


def teardown_apigateway(
    *,
    inventory_path: Optional[str | Path] = None,
    inventory: Optional[ResourceInventory] = None,
    deleter: Optional[ResourceDeleter] = None,
) -> TeardownResult:
    """Tear down the ApiGateway_Deployment recorded in an inventory.

    Deletes every recorded resource through the ``deleter`` seam. The deleter is
    injected: unit tests pass a fake driving per-resource outcomes, while live callers
    leave it ``None`` and this function builds the real, boto3-backed deleter lazily
    (never at import). Teardown is idempotent -- an already-absent resource is treated
    as deleted -- and reports the exact set of resources whose deletion failed
    (Req 8.2, 8.5, 8.6, 8.7).

    Exactly one of ``inventory`` or ``inventory_path`` must be supplied.

    Args:
        inventory_path: Path to a persisted inventory to load and tear down.
        inventory: An already-loaded inventory to tear down.
        deleter: Optional injected resource-deletion seam; built lazily when ``None``.

    Returns:
        The :class:`~integration.deploy.common.TeardownResult` for the run.

    Raises:
        ValueError: If neither or both of ``inventory`` and ``inventory_path`` are given.
    """
    if (inventory is None) == (inventory_path is None):
        raise ValueError('Provide exactly one of inventory or inventory_path.')

    if deleter is None:
        deleter = _LiveApiGatewayDeleter()

    if inventory is not None:
        return teardown(inventory=inventory, deleter=deleter)
    return teardown_from_path(inventory_path, deleter)  # type: ignore[arg-type]


def _harness_session(region: str) -> Any:
    """Build a boto3 session using the harness/server's default credential chain."""
    import boto3
    import botocore.session

    botocore_session = botocore.session.Session()
    botocore_session.user_agent_extra = build_user_agent_extra()
    return boto3.Session(botocore_session=botocore_session, region_name=region)


def create_apigateway_client(region: str) -> Any:
    """Build an API Gateway (REST) client for live provisioning/teardown.

    Only for live callers; never invoked at import and never in unit tests, which inject
    their own creator/deleter seam instead.

    Args:
        region: The AWS region for the client.

    Returns:
        A configured boto3 ``apigateway`` client.
    """
    return _harness_session(region).client('apigateway')


def _require_env(name: str) -> str:
    """Return a required live-input environment variable or fail closed.

    Args:
        name: The environment variable name.

    Returns:
        The non-empty value.

    Raises:
        ValueError: If the variable is unset or blank. The FSM surfaces this as a
            FAILED stage with a human-readable cause; the value is a resource identifier,
            never Credential_Material.
    """
    value = os.environ.get(name, '').strip()
    if not value:
        raise ValueError(
            f'Required live provisioning input {name} is unset; provision the '
            'loopback-bound server and its private-integration target per the '
            'documented deployment definition and export it.'
        )
    return value


class _LiveApiGatewayCreator:
    """Real, boto3-backed :class:`ResourceCreator` for the ApiGateway_Deployment.

    Builds its boto3 clients lazily on first use so importing this module -- and unit
    tests that inject a fake creator -- never construct a real client. The loopback
    server host/port and the VPC-link network-load-balancer target ARNs and authorizer
    invoke ARN are live-only inputs read from the environment (see the ``*_ENV``
    constants), because the harness cannot fabricate the operator-provisioned compute
    and network resources the private integration fronts.
    """

    def __init__(self, *, region: str, apigateway_client: Optional[Any] = None) -> None:
        """Initialize the creator for a region with an optional pre-built client."""
        self._region = region
        self._apigateway_client = apigateway_client
        # Set while creating the VPC link so the REST-API stage can wire the private
        # integration to it.
        self._vpc_link_id: Optional[str] = None

    @property
    def _apigateway(self) -> Any:
        """Return the API Gateway client, building it lazily on first use."""
        if self._apigateway_client is None:
            self._apigateway_client = create_apigateway_client(self._region)
        return self._apigateway_client

    def __call__(self, resource_type: str, /, **params: Any) -> CreatedResource:
        """Create the resource for ``resource_type`` through the live AWS clients."""
        if resource_type == RESOURCE_TYPE_SERVER:
            return self._create_server(**params)
        if resource_type == RESOURCE_TYPE_VPC_LINK:
            return self._create_vpc_link()
        if resource_type == RESOURCE_TYPE_REST_API:
            return self._create_rest_api(**params)
        raise ValueError(f'Unknown ApiGateway_Deployment resource type: {resource_type!r}')

    def _create_server(self, *, server_env: Mapping[str, str]) -> CreatedResource:
        """Record the loopback-bound server target the private integration fronts.

        The server compute is provisioned per the operator's documented, repeatable
        definition and its private target is supplied via the environment. The server
        binds ``127.0.0.1`` (Req 3.2); its private target is what the VPC link fronts.
        The injected environment is not recorded verbatim to keep inventory attributes
        minimal and secret-free.
        """
        target = _require_env(SERVER_TARGET_ENV)
        return CreatedResource(
            resource_id=target,
            resource_type=RESOURCE_TYPE_SERVER,
            attributes={'host': LOOPBACK_HOST, 'target': target},
        )

    def _create_vpc_link(self) -> CreatedResource:
        """Create the VPC link that makes the API Gateway integration private.

        The link fronts the operator-provisioned network load balancer(s) whose ARNs
        are supplied via the environment, so API Gateway reaches the loopback-bound
        server privately and remains the sole network-reachable ingress (Req 3.1).
        """
        target_arns = [
            arn.strip() for arn in _require_env(VPC_LINK_TARGET_ARNS_ENV).split(',') if arn.strip()
        ]
        response = self._apigateway.create_vpc_link(
            name=f'{DEPLOYMENT}-itest-vpclink',
            targetArns=target_arns,
        )
        vpc_link_id = response['id']
        self._vpc_link_id = vpc_link_id
        # Wait for the link to become AVAILABLE before it is used by the integration.
        self._apigateway.get_waiter('vpc_link_available').wait(vpcLinkId=vpc_link_id)
        return CreatedResource(
            resource_id=vpc_link_id,
            resource_type=RESOURCE_TYPE_VPC_LINK,
        )

    def _create_rest_api(
        self,
        *,
        config: Mapping[str, Any],
        server_env: Mapping[str, str],
    ) -> CreatedResource:
        """Create the REST API, its authorizer, and the private integration; deploy it.

        Builds the regional REST API as the sole reachable ingress: a proxy resource
        whose ``ANY`` method requires the custom authorizer (Req 3.3, 3.4) and forwards
        authenticated requests to the loopback-bound server through the private VPC-link
        integration (Req 3.1). Deploying to the configured stage yields the invoke
        endpoint returned as the deployment's endpoint reference (Req 3.7).
        """
        if self._vpc_link_id is None:
            raise ValueError('VPC link was not created before the API Gateway stage.')

        authorizer_uri = _require_env(AUTHORIZER_URI_ENV)
        server = config['server']
        authorizer = config['authorizer']
        stage_name = config['stage_name']
        target_uri = f'http://{server["host"]}:{server["port"]}{server["path"]}'

        api = self._apigateway.create_rest_api(
            name=config['api_name'],
            endpointConfiguration={'types': [config['endpoint_type']]},
        )
        api_id = api['id']

        resources = self._apigateway.get_resources(restApiId=api_id)
        root_id = next(item['id'] for item in resources['items'] if item['path'] == '/')
        proxy = self._apigateway.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='{proxy+}',
        )
        proxy_id = proxy['id']

        authorizer_response = self._apigateway.create_authorizer(
            restApiId=api_id,
            name=authorizer['name'],
            type=authorizer['type'],
            authorizerUri=authorizer_uri,
            identitySource=authorizer['identity_source'],
        )
        authorizer_id = authorizer_response['id']

        self._apigateway.put_method(
            restApiId=api_id,
            resourceId=proxy_id,
            httpMethod=INTEGRATION_HTTP_METHOD,
            authorizationType=METHOD_AUTHORIZATION,
            authorizerId=authorizer_id,
        )
        self._apigateway.put_integration(
            restApiId=api_id,
            resourceId=proxy_id,
            httpMethod=INTEGRATION_HTTP_METHOD,
            type=INTEGRATION_TYPE,
            integrationHttpMethod=INTEGRATION_HTTP_METHOD,
            connectionType=INTEGRATION_CONNECTION_TYPE,
            connectionId=self._vpc_link_id,
            uri=target_uri,
        )
        self._apigateway.create_deployment(restApiId=api_id, stageName=stage_name)

        endpoint = (
            f'https://{api_id}.execute-api.{self._region}.amazonaws.com/'
            f'{stage_name}{server["path"]}'
        )
        return CreatedResource(
            resource_id=api_id,
            resource_type=RESOURCE_TYPE_REST_API,
            attributes={'endpoint': endpoint},
            endpoint=endpoint,
        )


class _LiveApiGatewayDeleter:
    """Real, boto3-backed :class:`ResourceDeleter` for the ApiGateway_Deployment.

    Dispatches on each record's ``resource_type`` and deletes the resource through
    boto3 clients built lazily and cached per region, so importing this module -- and
    unit tests that inject a fake deleter -- never construct a real client. An
    already-absent resource is signalled by raising
    :class:`~integration.deploy.common.ResourceNotFound`, which teardown treats as an
    idempotent success (Req 8.7).
    """

    def __init__(self) -> None:
        """Initialize the deleter with empty per-region client caches."""
        self._apigateway_clients: dict[str, Any] = {}
        self._dynamodb_clients: dict[str, Any] = {}

    def _apigateway(self, region: str) -> Any:
        """Return a region-scoped API Gateway client, building it lazily."""
        client = self._apigateway_clients.get(region)
        if client is None:
            client = create_apigateway_client(region)
            self._apigateway_clients[region] = client
        return client

    def _dynamodb(self, region: str) -> Any:
        """Return a region-scoped DynamoDB client, building it lazily."""
        client = self._dynamodb_clients.get(region)
        if client is None:
            client = create_dynamodb_client(region)
            self._dynamodb_clients[region] = client
        return client

    def __call__(self, record: ResourceRecord, /) -> None:
        """Delete the resource identified by ``record`` or signal it already absent."""
        if record.resource_type == RESOURCE_TYPE_DYNAMODB_TABLE:
            self._delete_dynamodb_table(record)
            return
        if record.resource_type == RESOURCE_TYPE_REST_API:
            self._delete_rest_api(record)
            return
        if record.resource_type == RESOURCE_TYPE_VPC_LINK:
            self._delete_vpc_link(record)
            return
        if record.resource_type == RESOURCE_TYPE_SERVER:
            # The loopback-bound server compute is operator-managed per the documented
            # deployment definition; there is no harness-created cloud resource to delete.
            return
        raise ValueError(f'Unknown ApiGateway_Deployment resource type: {record.resource_type!r}')

    def _delete_dynamodb_table(self, record: ResourceRecord) -> None:
        """Delete the role-registry table, treating an absent table as already gone."""
        client = self._dynamodb(record.region)
        try:
            client.delete_table(TableName=record.resource_id)
        except client.exceptions.ResourceNotFoundException as exc:
            raise ResourceNotFound(record.resource_id) from exc

    def _delete_rest_api(self, record: ResourceRecord) -> None:
        """Delete the REST API, treating an absent API as already gone."""
        client = self._apigateway(record.region)
        try:
            client.delete_rest_api(restApiId=record.resource_id)
        except client.exceptions.NotFoundException as exc:
            raise ResourceNotFound(record.resource_id) from exc

    def _delete_vpc_link(self, record: ResourceRecord) -> None:
        """Delete the VPC link, treating an absent link as already gone."""
        client = self._apigateway(record.region)
        try:
            client.delete_vpc_link(vpcLinkId=record.resource_id)
        except client.exceptions.NotFoundException as exc:
            raise ResourceNotFound(record.resource_id) from exc
