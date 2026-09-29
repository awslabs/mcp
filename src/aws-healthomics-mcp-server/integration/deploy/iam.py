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

"""IAM role provisioning for the integration harness (tenant + execution roles).

To make the harness deploy-and-run with zero manual IAM setup, provisioning creates the
IAM roles the multi-tenant demonstration needs, and teardown deletes them:

- Two **Tenant_Roles** (Tenant_A / Tenant_B) that the deployed server assumes per request
  via ``sts:AssumeRole`` with a per-tenant ``ExternalId``. Their trust policy trusts the
  deployment account root guarded by the tenant's ``ExternalId`` (the confused-deputy
  guard), which avoids any create-ordering dependency on the execution role. Their
  permission policy grants read-only Amazon HealthOmics access -- enough for a realistic
  tenant, though the current tests (``WhoAmI`` -> ``sts:GetCallerIdentity`` and
  ``GetAHOSupportedRegions`` -> local metadata) need no tenant permissions at all.
- One **execution role** the AgentCore Runtime container runs as. It trusts the
  ``bedrock-agentcore`` service principal and is permitted to assume the two Tenant_Roles
  (with session tags), read the DynamoDB role registry, pull the container image from ECR,
  write logs, and call ``sts:GetCallerIdentity``.

Design for testability
-----------------------
Every policy document and derived identifier is produced by a **pure function**
(:func:`tenant_trust_policy`, :func:`tenant_permission_policy`,
:func:`execution_role_trust_policy`, :func:`execution_role_permission_policy`,
:func:`tenant_role_name`, :func:`expected_assumed_role_arn`, :func:`parse_arn_account`,
:func:`parse_arn_partition`) so they are asserted offline with no AWS access. All real AWS
work flows through the injected boto3 IAM client passed to :func:`provision_tenant_roles` /
:func:`provision_execution_role` and through the live creator/deleter dispatch in
``deploy/agentcore.py``; no boto3 client is constructed at import time.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from integration.deploy.common import ResourceNotFound
from integration.harness.inventory import ResourceInventory, ResourceRecord
from integration.harness.tenants import TenantRecord
from typing import Any, Optional


# ``resource_type`` values recorded in the inventory for the roles this module creates.
RESOURCE_TYPE_IAM_ROLE = 'iam-role'

# The single inline policy name attached to each created role. Teardown deletes this inline
# policy before deleting the role.
INLINE_POLICY_NAME = 'aho-mcp-itest-inline'

# Default naming for the harness IAM roles.
DEFAULT_ROLE_NAME_PREFIX = 'aho-mcp-itest'
DEFAULT_EXECUTION_ROLE_SUFFIX = 'exec'

# The AgentCore service principal that assumes the execution role.
_AGENTCORE_SERVICE_PRINCIPAL = 'bedrock-agentcore.amazonaws.com'

# Mirrors the server's RoleSessionName sanitization in
# ``awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange`` so the expected assumed-role
# ARN the isolation test compares against matches exactly what STS reports for a request.
_SESSION_NAME_ALLOWED = re.compile(r'[^\w+=,.@-]')
_SESSION_NAME_MAX_LEN = 64
_DEFAULT_SESSION_NAME = 'jwt-caller'


def sanitize_session_name(value: str) -> str:
    """Return ``value`` sanitized into a valid STS ``RoleSessionName``.

    This mirrors ``jwt_exchange._sanitize_session_name`` exactly: characters outside the
    allowed set become ``-``, the result is trimmed to 64 characters, and a constant default
    is used when nothing usable remains. It is kept here (rather than imported from the
    server's private helper) so the harness owns the value it must reproduce, while the
    matching offline test guards against drift.

    Args:
        value: The raw caller identifier (the JWT ``sub`` claim).

    Returns:
        The sanitized session name the server passes to ``sts:AssumeRole``.
    """
    cleaned = _SESSION_NAME_ALLOWED.sub('-', value).strip('-')
    cleaned = cleaned[:_SESSION_NAME_MAX_LEN]
    return cleaned or _DEFAULT_SESSION_NAME


def parse_arn_account(arn: str) -> str:
    """Return the account id from an ARN.

    Args:
        arn: An ARN of the shape ``arn:<partition>:<service>:<region>:<account>:<resource>``.

    Returns:
        The account-id segment.

    Raises:
        ValueError: If ``arn`` does not have at least the five leading ARN segments.
    """
    parts = arn.split(':')
    if len(parts) < 6:
        raise ValueError(f'Not a valid ARN: {arn!r}')
    return parts[4]


def parse_arn_partition(arn: str) -> str:
    """Return the partition (e.g. ``aws``, ``aws-cn``, ``aws-us-gov``) from an ARN.

    Args:
        arn: An ARN of the shape ``arn:<partition>:<service>:<region>:<account>:<resource>``.

    Returns:
        The partition segment.

    Raises:
        ValueError: If ``arn`` does not have at least the five leading ARN segments.
    """
    parts = arn.split(':')
    if len(parts) < 6:
        raise ValueError(f'Not a valid ARN: {arn!r}')
    return parts[1]


def tenant_role_name(label: str, *, prefix: str = DEFAULT_ROLE_NAME_PREFIX) -> str:
    """Return the deterministic IAM role name for a tenant label (e.g. ``Tenant_A``)."""
    return f'{prefix}-{label.lower().replace("_", "-")}'


def execution_role_name(*, prefix: str = DEFAULT_ROLE_NAME_PREFIX) -> str:
    """Return the deterministic IAM role name for the AgentCore execution role."""
    return f'{prefix}-{DEFAULT_EXECUTION_ROLE_SUFFIX}'


def expected_assumed_role_arn(*, role_arn: str, caller_sub: str) -> str:
    """Return the assumed-role ARN ``WhoAmI`` reports when the server assumes ``role_arn``.

    The server assumes the tenant role with ``RoleSessionName = sanitize(sub)``, so STS
    reports ``arn:<partition>:sts::<account>:assumed-role/<RoleName>/<sanitized-sub>``. This
    is the exact string the cross-tenant isolation test compares against, computed as a pure
    function of the role ARN and the caller's ``sub`` claim.

    Args:
        role_arn: The tenant role's IAM ARN (``arn:<part>:iam::<account>:role/<name>``).
        caller_sub: The caller's JWT ``sub`` claim (the Cognito user's ``sub``).

    Returns:
        The assumed-role ARN STS reports for a request made under this tenant.
    """
    partition = parse_arn_partition(role_arn)
    account = parse_arn_account(role_arn)
    role_name = role_arn.split(':role/', 1)[-1]
    session = sanitize_session_name(caller_sub)
    return f'arn:{partition}:sts::{account}:assumed-role/{role_name}/{session}'


def tenant_trust_policy(*, account_id: str, external_id: str, partition: str = 'aws') -> dict:
    """Return the trust policy for a Tenant_Role.

    Trusts the deployment account root, guarded by an ``sts:ExternalId`` condition equal to
    the tenant's ``external_id``. Trusting the account root (rather than a specific execution
    role ARN) removes any create-ordering dependency between the tenant roles and the
    execution role; the ``ExternalId`` condition is the confused-deputy guard, and the
    execution role is separately scoped to assume only these role ARNs.

    Args:
        account_id: The deployment account id.
        external_id: The tenant's ``sts:ExternalId`` guard value.
        partition: The AWS partition (default ``aws``).

    Returns:
        The trust policy document.
    """
    # The server attaches ABAC session tags on the AssumeRole call, so the trust policy must
    # allow sts:TagSession in addition to sts:AssumeRole; without it STS denies the tagged
    # assume with an AccessDenied ClientError.
    return {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'AWS': f'arn:{partition}:iam::{account_id}:root'},
                'Action': ['sts:AssumeRole', 'sts:TagSession'],
                'Condition': {'StringEquals': {'sts:ExternalId': external_id}},
            }
        ],
    }


def tenant_permission_policy() -> dict:
    """Return the read-only Amazon HealthOmics permission policy for a Tenant_Role.

    The current integration tests need no tenant permissions (``WhoAmI`` uses
    ``sts:GetCallerIdentity`` and ``GetAHOSupportedRegions`` is a local metadata lookup), so
    this grants a realistic read-only surface for future tool tests rather than being
    strictly required.

    Returns:
        The permission policy document.
    """
    return {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'HealthOmicsReadOnly',
                'Effect': 'Allow',
                'Action': ['omics:List*', 'omics:Get*'],
                'Resource': '*',
            }
        ],
    }


def execution_role_trust_policy() -> dict:
    """Return the trust policy for the AgentCore execution role.

    Trusts the ``bedrock-agentcore`` service principal so AgentCore Runtime can assume the
    role the server container runs as.

    Returns:
        The trust policy document.
    """
    return {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': _AGENTCORE_SERVICE_PRINCIPAL},
                'Action': 'sts:AssumeRole',
            }
        ],
    }


def execution_role_permission_policy(
    *,
    tenant_role_arns: Sequence[str],
    registry_table_arn: str,
) -> dict:
    """Return the permission policy for the AgentCore execution role.

    Grants exactly what the deployed server needs to run the multi-tenant demonstration:
    assume the tenant roles (with session tags for ABAC), read the DynamoDB role registry,
    pull the container image from ECR, write CloudWatch logs, and call
    ``sts:GetCallerIdentity`` (used by the ``WhoAmI`` isolation tool).

    Args:
        tenant_role_arns: The Tenant_Role ARNs the server is permitted to assume.
        registry_table_arn: The DynamoDB role-registry table ARN the server reads.

    Returns:
        The permission policy document.
    """
    return {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'AssumeTenantRoles',
                'Effect': 'Allow',
                'Action': ['sts:AssumeRole', 'sts:TagSession'],
                'Resource': list(tenant_role_arns),
            },
            {
                'Sid': 'ReadRoleRegistry',
                'Effect': 'Allow',
                'Action': ['dynamodb:GetItem'],
                'Resource': registry_table_arn,
            },
            {
                'Sid': 'CallerIdentity',
                'Effect': 'Allow',
                'Action': ['sts:GetCallerIdentity'],
                'Resource': '*',
            },
            {
                'Sid': 'PullImage',
                'Effect': 'Allow',
                'Action': [
                    'ecr:GetAuthorizationToken',
                    'ecr:BatchCheckLayerAvailability',
                    'ecr:GetDownloadUrlForLayer',
                    'ecr:BatchGetImage',
                ],
                'Resource': '*',
            },
            {
                'Sid': 'WriteLogs',
                'Effect': 'Allow',
                'Action': [
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                ],
                'Resource': '*',
            },
        ],
    }


# Default RoleSessionName used when the harness assumes a Tenant_Role for the explicit-mechanism
# workaround. It appears in the assumed-role ARN the isolation test compares against.
DEFAULT_ASSUME_SESSION_NAME = 'aho-itest'


@dataclass(frozen=True)
class AssumedTenantCredentials:
    """Short-lived credentials the harness obtains by assuming a Tenant_Role (untagged).

    Used by the explicit-mechanism workaround: the harness assumes each Tenant_Role *without*
    session tags (which succeeds even where ``sts:TagSession`` is denied) and forwards these
    credentials to the server via the explicit-credential headers. These values are
    Credential_Material and must never be persisted to the inventory or any artifact.

    Attributes:
        access_key_id: The temporary access key id.
        secret_access_key: The temporary secret access key.
        session_token: The temporary session token.
        assumed_role_arn: The ``arn:...:sts::...:assumed-role/<role>/<session>`` STS reports,
            which is exactly what ``WhoAmI`` returns for a request made with these credentials.
    """

    access_key_id: str
    secret_access_key: str
    session_token: str
    assumed_role_arn: str


def assume_tenant_role(
    *,
    sts_client: Any,
    role_arn: str,
    external_id: str,
    session_name: str = DEFAULT_ASSUME_SESSION_NAME,
    duration_seconds: int = 3600,
) -> AssumedTenantCredentials:
    """Assume ``role_arn`` (untagged) and return its short-lived credentials + assumed ARN.

    The call passes the tenant's ``ExternalId`` but **no** session tags, so it succeeds in
    accounts that deny ``sts:TagSession``. The returned ``assumed_role_arn`` is the exact
    identity ``WhoAmI`` will report for a request that uses these credentials.

    Args:
        sts_client: An STS client using the harness's own (operator) credentials.
        role_arn: The Tenant_Role ARN to assume.
        external_id: The tenant's ``sts:ExternalId``.
        session_name: The ``RoleSessionName`` to use (appears in the assumed-role ARN).
        duration_seconds: The session duration.

    Returns:
        The assumed tenant credentials and the assumed-role ARN.
    """
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        ExternalId=external_id,
        DurationSeconds=duration_seconds,
    )
    creds = response['Credentials']
    return AssumedTenantCredentials(
        access_key_id=creds['AccessKeyId'],
        secret_access_key=creds['SecretAccessKey'],
        session_token=creds['SessionToken'],
        assumed_role_arn=response['AssumedRoleUser']['Arn'],
    )


@dataclass(frozen=True)
class CreatedRole:
    """The identity of an IAM role created during provisioning.

    Attributes:
        role_name: The IAM role name (the resource id recorded for teardown).
        role_arn: The IAM role ARN, consumed by later stages and the run config.
    """

    role_name: str
    role_arn: str


def _record_role(inventory: ResourceInventory, role_name: str, region: str) -> None:
    """Record an IAM role in the inventory before creating it (Req 8.3).

    IAM is a global service, but the record carries the deployment's region for a uniform
    inventory; the live deleter ignores region for IAM calls.
    """
    inventory.add(
        ResourceRecord(
            resource_id=role_name,
            resource_type=RESOURCE_TYPE_IAM_ROLE,
            region=region,
            deployment=inventory.deployment,
        )
    )


def provision_tenant_roles(
    *,
    iam_client: Any,
    inventory: ResourceInventory,
    region: str,
    specs: Sequence['TenantRoleSpec'],
) -> list[CreatedRole]:
    """Create the Tenant_Roles and return their names/ARNs.

    Each role is recorded in the inventory before creation so a mid-flight failure still
    leaves a teardown trail (Req 8.3). The role is created with the account-root +
    ``ExternalId`` trust policy and the read-only HealthOmics inline policy, and the
    provisioner waits for it to exist before returning.

    Args:
        iam_client: An injected boto3 IAM client (``create_role``, ``put_role_policy``,
            ``get_waiter('role_exists')``).
        inventory: The inventory to record created roles into.
        region: The deployment region (recorded on the inventory record).
        specs: The tenant role specifications (label, account, external id, partition).

    Returns:
        The created roles in the same order as ``specs``.
    """
    created: list[CreatedRole] = []
    for spec in specs:
        _record_role(inventory, spec.role_name, region)
        response = iam_client.create_role(
            RoleName=spec.role_name,
            AssumeRolePolicyDocument=json.dumps(
                tenant_trust_policy(
                    account_id=spec.account_id,
                    external_id=spec.external_id,
                    partition=spec.partition,
                )
            ),
            Description='AWS HealthOmics MCP integration-test tenant role.',
        )
        iam_client.put_role_policy(
            RoleName=spec.role_name,
            PolicyName=INLINE_POLICY_NAME,
            PolicyDocument=json.dumps(tenant_permission_policy()),
        )
        iam_client.get_waiter('role_exists').wait(RoleName=spec.role_name)
        created.append(CreatedRole(role_name=spec.role_name, role_arn=response['Role']['Arn']))
    return created


def provision_execution_role(
    *,
    iam_client: Any,
    inventory: ResourceInventory,
    region: str,
    role_name: str,
    tenant_role_arns: Sequence[str],
    registry_table_arn: str,
) -> CreatedRole:
    """Create the AgentCore execution role and return its name/ARN.

    Recorded in the inventory before creation (Req 8.3). Created with the ``bedrock-agentcore``
    service-principal trust policy and the scoped permission policy, then waited on.

    Args:
        iam_client: An injected boto3 IAM client.
        inventory: The inventory to record the created role into.
        region: The deployment region (recorded on the inventory record).
        role_name: The execution role name.
        tenant_role_arns: The Tenant_Role ARNs the execution role may assume.
        registry_table_arn: The DynamoDB role-registry table ARN the server reads.

    Returns:
        The created execution role.
    """
    _record_role(inventory, role_name, region)
    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(execution_role_trust_policy()),
        Description='AWS HealthOmics MCP integration-test AgentCore execution role.',
    )
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=INLINE_POLICY_NAME,
        PolicyDocument=json.dumps(
            execution_role_permission_policy(
                tenant_role_arns=tenant_role_arns,
                registry_table_arn=registry_table_arn,
            )
        ),
    )
    iam_client.get_waiter('role_exists').wait(RoleName=role_name)
    return CreatedRole(role_name=role_name, role_arn=response['Role']['Arn'])


@dataclass(frozen=True)
class TenantRoleSpec:
    """The inputs needed to create one Tenant_Role.

    Attributes:
        label: The tenant label (e.g. ``Tenant_A``) used to derive the role name.
        role_name: The concrete IAM role name to create.
        account_id: The deployment account id (for the trust-policy principal).
        external_id: The tenant's ``sts:ExternalId`` guard value.
        partition: The AWS partition (default ``aws``).
    """

    label: str
    role_name: str
    account_id: str
    external_id: str
    partition: str = 'aws'


def delete_iam_role(*, iam_client: Any, role_name: str) -> None:
    """Delete an IAM role and its inline policy, mapping absence to ``ResourceNotFound``.

    Deletes every inline policy attached to the role, then the role itself. A missing role
    (or a missing inline policy) is treated as already-absent so teardown is idempotent
    (Req 8.7).

    Args:
        iam_client: An injected boto3 IAM client.
        role_name: The role to delete.

    Raises:
        ResourceNotFound: If the role does not exist.
    """
    try:
        policy_names = iam_client.list_role_policies(RoleName=role_name).get('PolicyNames', [])
    except iam_client.exceptions.NoSuchEntityException as exc:
        raise ResourceNotFound(f'IAM role {role_name!r} already absent.') from exc

    for policy_name in policy_names:
        try:
            iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        except iam_client.exceptions.NoSuchEntityException:
            # Inline policy already gone; continue toward deleting the role.
            continue

    try:
        iam_client.delete_role(RoleName=role_name)
    except iam_client.exceptions.NoSuchEntityException as exc:
        raise ResourceNotFound(f'IAM role {role_name!r} already absent.') from exc


def build_tenant_role_records(
    created_roles: Sequence[CreatedRole],
    subs: Sequence[str],
    external_ids: Sequence[str],
    account_ids: Sequence[Optional[str]],
) -> list[TenantRecord]:
    """Zip created roles, caller subs, and external ids into registry ``TenantRecord``s.

    The registry keys on the JWT ``sub`` (the Authenticated_Identity), so each record's
    ``identity`` is the corresponding Cognito user's ``sub``.

    Args:
        created_roles: The created Tenant_Roles, in tenant order.
        subs: The Cognito user ``sub`` claims, in the same order.
        external_ids: The per-tenant ``ExternalId`` values, in the same order.
        account_ids: Optional owning account ids, in the same order.

    Returns:
        The tenant records to write into the DynamoDB registry.
    """
    records: list[TenantRecord] = []
    for role, sub, external_id, account_id in zip(created_roles, subs, external_ids, account_ids):
        records.append(
            TenantRecord(
                identity=sub,
                role_arn=role.role_arn,
                external_id=external_id,
                account_id=account_id,
            )
        )
    return records
