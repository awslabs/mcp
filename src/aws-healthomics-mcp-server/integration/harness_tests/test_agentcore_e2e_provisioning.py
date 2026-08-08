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

"""Offline unit tests for the zero-setup AgentCore provisioning orchestration.

Pure and offline: :func:`provision_agentcore` is driven with fully injected fakes (FSM
creator, DynamoDB / IAM / Cognito clients, and an explicit account id so STS is never called),
so the whole create flow -- roles, execution role, identity provider, registry, image, runtime
-- is exercised without constructing any boto3 client or making any request.

The tests assert the end-to-end wiring the live path depends on: every resource type is
inventoried for teardown, the runtime is configured with the execution role and the Cognito
JWT authorizer, and the returned run config carries the endpoint, per-tenant tokens, and the
exact expected assumed-role ARNs the isolation test compares against. Tokens never appear in
the persisted inventory.

Validates: Requirements AgentCore deployment demonstration, Provisioning and teardown
lifecycle, Cross-tenant isolation verification, Credential material safety.
"""

from integration.deploy import agentcore
from integration.deploy import cognito as cognito_mod
from integration.deploy import iam as iam_mod
from integration.deploy.common import CreatedResource, ProvisionStatus
from integration.deploy.registry import RESOURCE_TYPE_DYNAMODB_TABLE
from integration.harness.inventory import ResourceInventory


class _FakeWaiter:
    def wait(self, **_kwargs):
        return None


class _NoSuchEntity(Exception):
    """Stand-in for ``iam.exceptions.NoSuchEntityException``."""


class _IamExceptions:
    NoSuchEntityException = _NoSuchEntity


class _FakeIamClient:
    """A minimal in-memory IAM client fake (create/put/list/delete role)."""

    def __init__(self, *, account_id: str = '111122223333', partition: str = 'aws') -> None:
        self._account_id = account_id
        self._partition = partition
        self.roles: dict[str, dict] = {}
        self.exceptions = _IamExceptions()

    def create_role(self, *, RoleName, AssumeRolePolicyDocument, Description=''):
        arn = f'arn:{self._partition}:iam::{self._account_id}:role/{RoleName}'
        self.roles[RoleName] = {'arn': arn, 'policies': {}}
        return {'Role': {'Arn': arn, 'RoleName': RoleName}}

    def put_role_policy(self, *, RoleName, PolicyName, PolicyDocument):
        self.roles[RoleName]['policies'][PolicyName] = PolicyDocument

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


class _ResourceNotFoundException(Exception):
    """Stand-in for ``cognito-idp`` ``ResourceNotFoundException``."""


class _CognitoExceptions:
    ResourceNotFoundException = _ResourceNotFoundException


class _FakeCognitoClient:
    """A minimal in-memory ``cognito-idp`` fake (pool/client/user + token minting)."""

    def __init__(self) -> None:
        self.exceptions = _CognitoExceptions()
        self.pools: dict[str, dict] = {}
        self._next_pool = 0
        self._next_sub = 0

    def create_user_pool(self, *, PoolName):
        self._next_pool += 1
        pool_id = f'us-east-1_pool{self._next_pool}'
        self.pools[pool_id] = {'name': PoolName, 'clients': {}, 'users': {}}
        return {'UserPool': {'Id': pool_id}}

    def create_user_pool_client(
        self, *, UserPoolId, ClientName, GenerateSecret, ExplicitAuthFlows
    ):
        client_id = f'client-{ClientName}'
        self.pools[UserPoolId]['clients'][client_id] = {'flows': list(ExplicitAuthFlows)}
        return {'UserPoolClient': {'ClientId': client_id}}

    def admin_create_user(self, *, UserPoolId, Username, MessageAction):
        self._next_sub += 1
        sub = f'00000000-0000-0000-0000-00000000000{self._next_sub}'
        self.pools[UserPoolId]['users'][Username] = {'sub': sub}

    def admin_set_user_password(self, *, UserPoolId, Username, Password, Permanent):
        self.pools[UserPoolId]['users'][Username]['password'] = Password

    def admin_get_user(self, *, UserPoolId, Username):
        sub = self.pools[UserPoolId]['users'][Username]['sub']
        return {'UserAttributes': [{'Name': 'sub', 'Value': sub}]}

    def admin_initiate_auth(self, *, UserPoolId, ClientId, AuthFlow, AuthParameters):
        return {'AuthenticationResult': {'AccessToken': f'token-for-{AuthParameters["USERNAME"]}'}}

    def delete_user_pool(self, *, UserPoolId):
        if UserPoolId not in self.pools:
            raise self.exceptions.ResourceNotFoundException(UserPoolId)
        del self.pools[UserPoolId]


class _FakeStsClient:
    """A minimal STS fake whose assume_role echoes the role name and session into the ARN."""

    def __init__(self, account: str = '111122223333') -> None:
        self._account = account

    def assume_role(self, *, RoleArn, RoleSessionName, ExternalId, DurationSeconds):
        role_name = RoleArn.split('/')[-1]
        return {
            'Credentials': {
                'AccessKeyId': f'AKIA-{role_name}',
                'SecretAccessKey': f'secret-{role_name}',
                'SessionToken': f'token-{role_name}',
            },
            'AssumedRoleUser': {
                'Arn': f'arn:aws:sts::{self._account}:assumed-role/{role_name}/{RoleSessionName}',
            },
        }


class _FakeDynamoClient:
    """A minimal DynamoDB client fake capturing created tables and written items."""

    def __init__(self) -> None:
        self.tables: dict[str, list] = {}

    def create_table(self, *, TableName, **_kwargs):
        self.tables[TableName] = []

    def get_waiter(self, _name):
        return _FakeWaiter()

    def put_item(self, *, TableName, Item):
        self.tables[TableName].append(Item)


class _RecordingCreator:
    """An FSM creator fake that records the runtime config and returns a canned endpoint."""

    def __init__(self) -> None:
        self.runtime_config = None
        self.endpoint = None

    def __call__(self, resource_type, /, **params):
        # The live creator injects ``region`` itself, so the stages must not also pass it in
        # ``params`` (doing so caused a duplicate-keyword TypeError on the first live run).
        assert 'region' not in params, f'stage passed region in params for {resource_type!r}'
        if resource_type == agentcore.RESOURCE_TYPE_ECR_IMAGE:
            return CreatedResource(
                resource_id='111122223333.dkr.ecr.us-east-1.amazonaws.com/aho-mcp-itest:latest',
                resource_type=resource_type,
            )
        if resource_type == agentcore.RESOURCE_TYPE_AGENTCORE_RUNTIME:
            self.runtime_config = params['config']
            runtime_arn = 'arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/aho-mcp-itest'
            self.endpoint = agentcore.agentcore_endpoint_url(
                region='us-east-1', runtime_arn=runtime_arn
            )
            return CreatedResource(
                resource_id=runtime_arn,
                resource_type=resource_type,
                attributes={'endpoint': self.endpoint},
                endpoint=self.endpoint,
            )
        raise AssertionError(f'unexpected resource_type {resource_type!r}')


def _provision(tmp_path):
    """Run ``provision_agentcore`` with fully injected fakes and return the seams for assertion."""
    creator = _RecordingCreator()
    dynamodb = _FakeDynamoClient()
    iam = _FakeIamClient()
    cognito = _FakeCognitoClient()
    outcome = agentcore.provision_agentcore(
        region='us-east-1',
        inventory_path=tmp_path / 'agentcore-inventory.json',
        account_id='111122223333',
        creator=creator,
        dynamodb_client=dynamodb,
        iam_client=iam,
        cognito_client=cognito,
        external_ids=['ext-a', 'ext-b'],
        user_password='Aho1!fixed-value',  # pragma: allowlist secret
        clock=lambda: 0.0,
    )
    return outcome, creator, dynamodb, iam, cognito


class TestProvisionAgentCoreEndToEnd:
    """A fully-faked provision completes and wires every resource correctly.

    Validates: Requirements AgentCore deployment demonstration, Provisioning and teardown
    lifecycle.
    """

    def test_provision_completes_and_inventories_every_resource(self, tmp_path) -> None:
        """Every resource type the deployment creates is recorded for teardown."""
        outcome, _creator, _dynamo, _iam, _cognito = _provision(tmp_path)

        assert outcome.result.status is ProvisionStatus.COMPLETE
        assert outcome.run_config is not None

        loaded = ResourceInventory.load(outcome.result.inventory_path)
        types = [record.resource_type for record in loaded.records]
        assert types.count(iam_mod.RESOURCE_TYPE_IAM_ROLE) == 3
        assert types.count(cognito_mod.RESOURCE_TYPE_COGNITO_USER_POOL) == 1
        assert types.count(RESOURCE_TYPE_DYNAMODB_TABLE) == 1
        assert types.count(agentcore.RESOURCE_TYPE_ECR_IMAGE) == 1
        assert types.count(agentcore.RESOURCE_TYPE_AGENTCORE_RUNTIME) == 1

    def test_runtime_wired_with_execution_role_and_jwt_authorizer(self, tmp_path) -> None:
        """The runtime config carries the execution role and the Cognito JWT authorizer."""
        _outcome, creator, _dynamo, _iam, cognito = _provision(tmp_path)

        config = creator.runtime_config
        assert config['execution_role_arn'].endswith(':role/aho-mcp-itest-exec')

        authorizer = config['inbound_authorizer']
        assert authorizer['type'] == 'jwt'
        pool_id = next(iter(cognito.pools))
        assert authorizer['discovery_url'] == cognito_mod.discovery_url(
            region='us-east-1', user_pool_id=pool_id
        )
        assert authorizer['allowed_clients']

    def test_registry_written_with_sub_keyed_records(self, tmp_path) -> None:
        """Each registry item's identity (partition key) is a Cognito user's sub."""
        _outcome, _creator, dynamo, _iam, cognito = _provision(tmp_path)

        items = dynamo.tables[agentcore.DEFAULT_TABLE_NAME]
        assert len(items) == 2
        written_identities = {item['identity']['S'] for item in items}
        expected_subs = {
            user['sub'] for pool in cognito.pools.values() for user in pool['users'].values()
        }
        assert written_identities == expected_subs


class TestRunConfig:
    """The run config carries the endpoint, tokens, and exact expected ARNs.

    Validates: Requirements Cross-tenant isolation verification, Credential material safety.
    """

    def test_run_config_env_and_expected_arns(self, tmp_path) -> None:
        """The env mapping exposes the endpoint, tokens, and distinct expected ARNs."""
        outcome, creator, _dynamo, iam, cognito = _provision(tmp_path)
        run_config = outcome.run_config
        env = run_config.to_env()

        assert env['AHO_ITEST_AGENTCORE_ENDPOINT'] == creator.endpoint
        assert env['AHO_ITEST_ENDPOINT'] == creator.endpoint
        assert env['AHO_ITEST_BEARER_TOKEN'] == env['AHO_ITEST_TENANT_A_TOKEN']

        pool = next(iter(cognito.pools.values()))
        users = list(pool['users'].values())
        role_a = iam.roles['aho-mcp-itest-tenant-a']['arn']
        expected_a = iam_mod.expected_assumed_role_arn(role_arn=role_a, caller_sub=users[0]['sub'])
        assert env['AHO_ITEST_TENANT_A_EXPECTED_ARN'] == expected_a
        assert env['AHO_ITEST_TENANT_A_EXPECTED_ARN'] != env['AHO_ITEST_TENANT_B_EXPECTED_ARN']

    def test_tokens_absent_from_persisted_inventory(self, tmp_path) -> None:
        """Neither tenant's token appears in the persisted inventory JSON."""
        outcome, _creator, _dynamo, _iam, _cognito = _provision(tmp_path)
        serialized = outcome.result.inventory_path.read_text(encoding='utf-8')
        assert outcome.run_config.tenant_a_token not in serialized
        assert outcome.run_config.tenant_b_token not in serialized


def _provision_explicit(tmp_path):
    """Run ``provision_agentcore`` in explicit inbound mode with injected fakes."""
    creator = _RecordingCreator()
    outcome = agentcore.provision_agentcore(
        region='us-east-1',
        inventory_path=tmp_path / 'agentcore-inventory.json',
        account_id='111122223333',
        creator=creator,
        dynamodb_client=_FakeDynamoClient(),
        iam_client=_FakeIamClient(),
        cognito_client=_FakeCognitoClient(),
        sts_client=_FakeStsClient(),
        external_ids=['ext-a', 'ext-b'],
        user_password='Aho1!fixed-value',  # pragma: allowlist secret
        clock=lambda: 0.0,
        inbound=agentcore.INBOUND_AUTH_EXPLICIT,
    )
    return outcome, creator


class TestExplicitInboundMode:
    """The explicit inbound mode forwards X-Aws-* creds and avoids sts:TagSession.

    Validates: Requirements Cross-tenant isolation verification, AgentCore deployment
    demonstration.
    """

    def test_runtime_configured_for_explicit_and_allowlists_aws_headers(self, tmp_path) -> None:
        """The server env selects the explicit mechanism and the X-Aws-* headers are forwarded."""
        from awslabs.aws_healthomics_mcp_server import consts
        from integration.harness.headers import EXPLICIT_CREDENTIAL_HEADERS

        _outcome, creator = _provision_explicit(tmp_path)
        config = creator.runtime_config

        assert config['environment'][consts.MCP_INBOUND_AUTH_ENV] == 'explicit'
        for header in EXPLICIT_CREDENTIAL_HEADERS:
            assert header in config['request_header_allowlist']

    def test_run_config_carries_assumed_creds_and_arns(self, tmp_path) -> None:
        """The run config exposes each tenant's assumed creds and the assumed-role ARN."""
        outcome, _creator = _provision_explicit(tmp_path)
        run_config = outcome.run_config

        assert run_config.tenant_a_creds is not None
        assert run_config.tenant_a_creds.access_key_id == 'AKIA-aho-mcp-itest-tenant-a'
        # The expected ARN is exactly the assumed-role ARN STS returns for those creds.
        assert run_config.tenant_a_expected_arn == (
            'arn:aws:sts::111122223333:assumed-role/aho-mcp-itest-tenant-a/aho-itest'
        )
        assert run_config.tenant_a_expected_arn != run_config.tenant_b_expected_arn

        env = run_config.to_env()
        # Transport-test creds (Tenant_A) and per-tenant isolation creds are all exported.
        assert env['AHO_ITEST_AWS_ACCESS_KEY_ID'] == 'AKIA-aho-mcp-itest-tenant-a'
        assert env['AHO_ITEST_TENANT_B_AWS_SESSION_TOKEN'] == 'token-aho-mcp-itest-tenant-b'

    def test_assumed_creds_absent_from_inventory(self, tmp_path) -> None:
        """The forwarded short-lived credentials never appear in the persisted inventory."""
        outcome, _creator = _provision_explicit(tmp_path)
        serialized = outcome.result.inventory_path.read_text(encoding='utf-8')
        assert outcome.run_config.tenant_a_creds.secret_access_key not in serialized
        assert outcome.run_config.tenant_b_creds.session_token not in serialized


class TestTeardownDeletesEverything:
    """Teardown hands every provisioned resource to the deleter dispatch.

    Validates: Requirements Provisioning and teardown lifecycle.
    """

    def test_teardown_deletes_all_recorded_resources(self, tmp_path) -> None:
        """Every recorded resource is passed to the deleter and teardown succeeds."""
        outcome, _creator, _dynamo, _iam, _cognito = _provision(tmp_path)
        loaded = ResourceInventory.load(outcome.result.inventory_path)

        deleted: list[str] = []

        def fake_deleter(record, /):
            deleted.append(record.resource_type)

        result = agentcore.teardown_agentcore(inventory=loaded, deleter=fake_deleter)

        assert result.succeeded is True
        assert len(deleted) == len(loaded.records)
