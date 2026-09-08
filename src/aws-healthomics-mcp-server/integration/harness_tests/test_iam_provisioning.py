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

"""Offline unit tests for IAM tenant/execution role provisioning.

Pure and offline: the policy builders and identifier derivations are asserted directly, and
the create/delete paths are driven with a fake IAM client so no boto3 client is constructed
and no request leaves the process. The fake mirrors just the surface the code uses
(``create_role``, ``put_role_policy``, ``get_waiter``, ``list_role_policies``,
``delete_role_policy``, ``delete_role`` and a ``NoSuchEntityException``).

Validates: Requirements Provisioning and teardown lifecycle, Cross-tenant isolation
verification.
"""

import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import _sanitize_session_name
from integration.deploy import iam as iam_mod
from integration.deploy.common import ResourceNotFound
from integration.harness.inventory import ResourceInventory


class _NoSuchEntity(Exception):
    """Stand-in for ``iam.exceptions.NoSuchEntityException``."""


class _FakeExceptions:
    NoSuchEntityException = _NoSuchEntity


class _FakeWaiter:
    def wait(self, **_kwargs):
        return None


class _FakeIamClient:
    """A minimal in-memory IAM client fake for offline provisioning/teardown tests."""

    def __init__(self, *, account_id: str = '111122223333', partition: str = 'aws') -> None:
        self._account_id = account_id
        self._partition = partition
        self.roles: dict[str, dict] = {}
        self.exceptions = _FakeExceptions()

    def create_role(self, *, RoleName, AssumeRolePolicyDocument, Description=''):
        arn = f'arn:{self._partition}:iam::{self._account_id}:role/{RoleName}'
        self.roles[RoleName] = {
            'arn': arn,
            'trust': json.loads(AssumeRolePolicyDocument),
            'policies': {},
        }
        return {'Role': {'Arn': arn, 'RoleName': RoleName}}

    def put_role_policy(self, *, RoleName, PolicyName, PolicyDocument):
        self.roles[RoleName]['policies'][PolicyName] = json.loads(PolicyDocument)

    def get_waiter(self, _name):
        return _FakeWaiter()

    def list_role_policies(self, *, RoleName):
        if RoleName not in self.roles:
            raise self.exceptions.NoSuchEntityException(RoleName)
        return {'PolicyNames': list(self.roles[RoleName]['policies'])}

    def delete_role_policy(self, *, RoleName, PolicyName):
        self.roles[RoleName]['policies'].pop(PolicyName, None)

    def delete_role(self, *, RoleName):
        if RoleName not in self.roles:
            raise self.exceptions.NoSuchEntityException(RoleName)
        del self.roles[RoleName]


class TestPurePolicyBuilders:
    """The trust/permission policy documents have the required shape.

    Validates: Requirements Cross-tenant isolation verification.
    """

    def test_tenant_trust_policy_pins_account_root_and_external_id(self) -> None:
        """The tenant trust policy trusts the account root guarded by the ExternalId."""
        policy = iam_mod.tenant_trust_policy(
            account_id='111122223333', external_id='ext-a', partition='aws'
        )
        statement = policy['Statement'][0]
        # Both AssumeRole and TagSession are required because the server passes ABAC session
        # tags on the assume-role call.
        assert 'sts:AssumeRole' in statement['Action']
        assert 'sts:TagSession' in statement['Action']
        assert statement['Principal'] == {'AWS': 'arn:aws:iam::111122223333:root'}
        assert statement['Condition'] == {'StringEquals': {'sts:ExternalId': 'ext-a'}}

    def test_tenant_permission_policy_is_read_only_omics(self) -> None:
        """The tenant permission policy grants only read-only HealthOmics actions."""
        policy = iam_mod.tenant_permission_policy()
        actions = policy['Statement'][0]['Action']
        assert actions == ['omics:List*', 'omics:Get*']

    def test_execution_role_trust_is_agentcore_service(self) -> None:
        """The execution role trusts the bedrock-agentcore service principal."""
        policy = iam_mod.execution_role_trust_policy()
        assert policy['Statement'][0]['Principal'] == {
            'Service': 'bedrock-agentcore.amazonaws.com'
        }

    def test_execution_role_permissions_scope_assume_and_registry(self) -> None:
        """The execution role is scoped to assume the tenant roles and read the registry."""
        policy = iam_mod.execution_role_permission_policy(
            tenant_role_arns=['arn:aws:iam::111122223333:role/a'],
            registry_table_arn='arn:aws:dynamodb:us-east-1:111122223333:table/tbl',
        )
        sids = {statement['Sid']: statement for statement in policy['Statement']}
        assert sids['AssumeTenantRoles']['Resource'] == ['arn:aws:iam::111122223333:role/a']
        assert 'sts:AssumeRole' in sids['AssumeTenantRoles']['Action']
        assert 'sts:TagSession' in sids['AssumeTenantRoles']['Action']
        assert sids['ReadRoleRegistry']['Resource'] == (
            'arn:aws:dynamodb:us-east-1:111122223333:table/tbl'
        )


class TestIdentifierDerivation:
    """Role names, ARN parsing, and the expected assumed-role ARN are derived correctly.

    Validates: Requirements Cross-tenant isolation verification.
    """

    def test_tenant_role_name_is_deterministic(self) -> None:
        """Tenant labels map to stable, lowercased role names."""
        assert iam_mod.tenant_role_name('Tenant_A') == 'aho-mcp-itest-tenant-a'
        assert iam_mod.tenant_role_name('Tenant_B') == 'aho-mcp-itest-tenant-b'

    def test_arn_parsing(self) -> None:
        """Account id and partition are parsed from an ARN's fixed segments."""
        arn = 'arn:aws-us-gov:iam::111122223333:role/x'
        assert iam_mod.parse_arn_account(arn) == '111122223333'
        assert iam_mod.parse_arn_partition(arn) == 'aws-us-gov'

    @pytest.mark.parametrize(
        'sub',
        [
            '11111111-2222-3333-4444-555555555555',
            'user@example.com',
            'has spaces and *bad* chars',
            '',
        ],
    )
    def test_expected_arn_session_matches_server_sanitizer(self, sub: str) -> None:
        """The expected ARN's session segment equals the server's own sanitizer output.

        Guards against drift between the harness's :func:`sanitize_session_name` and the
        server's private ``_sanitize_session_name`` used to build the ``RoleSessionName``.
        """
        role_arn = 'arn:aws:iam::111122223333:role/aho-mcp-itest-tenant-a'
        arn = iam_mod.expected_assumed_role_arn(role_arn=role_arn, caller_sub=sub)
        expected_session = _sanitize_session_name(sub)
        assert arn == (
            f'arn:aws:sts::111122223333:assumed-role/aho-mcp-itest-tenant-a/{expected_session}'
        )


class TestProvisionAndDeleteRoles:
    """Provisioning records + creates roles; deletion is idempotent.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_provision_tenant_roles_records_and_creates(self) -> None:
        """Both tenant roles are created with inline policies and recorded in the inventory."""
        client = _FakeIamClient()
        inventory = ResourceInventory(deployment='agentcore', region='us-east-1')
        specs = [
            iam_mod.TenantRoleSpec(
                label='Tenant_A',
                role_name=iam_mod.tenant_role_name('Tenant_A'),
                account_id='111122223333',
                external_id='ext-a',
            ),
            iam_mod.TenantRoleSpec(
                label='Tenant_B',
                role_name=iam_mod.tenant_role_name('Tenant_B'),
                account_id='111122223333',
                external_id='ext-b',
            ),
        ]

        created = iam_mod.provision_tenant_roles(
            iam_client=client, inventory=inventory, region='us-east-1', specs=specs
        )

        assert [role.role_name for role in created] == [
            'aho-mcp-itest-tenant-a',
            'aho-mcp-itest-tenant-b',
        ]
        assert set(client.roles) == {'aho-mcp-itest-tenant-a', 'aho-mcp-itest-tenant-b'}
        recorded = {
            record.resource_id
            for record in inventory.records
            if record.resource_type == iam_mod.RESOURCE_TYPE_IAM_ROLE
        }
        assert recorded == {'aho-mcp-itest-tenant-a', 'aho-mcp-itest-tenant-b'}

    def test_provision_execution_role_scopes_registry_and_tenants(self) -> None:
        """The execution role carries the assume/registry/pull/logs statements."""
        client = _FakeIamClient()
        inventory = ResourceInventory(deployment='agentcore', region='us-east-1')

        exec_role = iam_mod.provision_execution_role(
            iam_client=client,
            inventory=inventory,
            region='us-east-1',
            role_name=iam_mod.execution_role_name(),
            tenant_role_arns=['arn:aws:iam::111122223333:role/aho-mcp-itest-tenant-a'],
            registry_table_arn='arn:aws:dynamodb:us-east-1:111122223333:table/tbl',
        )

        assert exec_role.role_name == 'aho-mcp-itest-exec'
        policy = client.roles['aho-mcp-itest-exec']['policies'][iam_mod.INLINE_POLICY_NAME]
        sids = {statement['Sid'] for statement in policy['Statement']}
        assert {'AssumeTenantRoles', 'ReadRoleRegistry', 'PullImage', 'WriteLogs'} <= sids

    def test_assume_tenant_role_untagged_returns_creds_and_arn(self) -> None:
        """assume_tenant_role passes ExternalId, no Tags, and returns creds + assumed ARN."""

        class _FakeSts:
            def __init__(self) -> None:
                self.call = None

            def assume_role(self, **kwargs):
                self.call = kwargs
                return {
                    'Credentials': {
                        'AccessKeyId': 'AKIA',
                        'SecretAccessKey': 'secret',  # pragma: allowlist secret
                        'SessionToken': 'token',  # pragma: allowlist secret
                    },
                    'AssumedRoleUser': {
                        'Arn': 'arn:aws:sts::111122223333:assumed-role/r-a/aho-itest'
                    },
                }

        sts = _FakeSts()
        creds = iam_mod.assume_tenant_role(
            sts_client=sts,
            role_arn='arn:aws:iam::111122223333:role/r-a',
            external_id='ext-a',
        )

        # No session tags are passed (that is the whole point of the workaround).
        assert 'Tags' not in sts.call
        assert sts.call['ExternalId'] == 'ext-a'
        assert creds.access_key_id == 'AKIA'
        assert creds.assumed_role_arn.endswith(':assumed-role/r-a/aho-itest')

    def test_delete_iam_role_is_idempotent(self) -> None:
        """Deleting a role removes it; a second delete reports already-absent."""
        client = _FakeIamClient()
        inventory = ResourceInventory(deployment='agentcore', region='us-east-1')
        iam_mod.provision_tenant_roles(
            iam_client=client,
            inventory=inventory,
            region='us-east-1',
            specs=[
                iam_mod.TenantRoleSpec(
                    label='Tenant_A',
                    role_name='r-a',
                    account_id='111122223333',
                    external_id='ext-a',
                )
            ],
        )

        iam_mod.delete_iam_role(iam_client=client, role_name='r-a')
        assert 'r-a' not in client.roles

        with pytest.raises(ResourceNotFound):
            iam_mod.delete_iam_role(iam_client=client, role_name='r-a')
