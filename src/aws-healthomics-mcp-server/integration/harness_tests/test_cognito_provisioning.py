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

"""Offline unit tests for Cognito identity-provider provisioning + token minting.

Pure and offline: the URL/auth-flow helpers are asserted directly, and provisioning is driven
with a fake ``cognito-idp`` client so no boto3 client is constructed and no request leaves the
process. The fake models pool/client/user creation, ``sub`` assignment, and
``AdminInitiateAuth`` token minting, and never returns Credential_Material beyond synthetic
token strings the test itself supplies.

Validates: Requirements Provisioning and teardown lifecycle, Cross-tenant isolation
verification, Credential material safety.
"""

import pytest
from integration.deploy import cognito as cognito_mod
from integration.deploy.common import ResourceNotFound
from integration.harness.inventory import ResourceInventory


class _ResourceNotFoundException(Exception):
    """Stand-in for ``cognito-idp`` ``ResourceNotFoundException``."""


class _FakeExceptions:
    ResourceNotFoundException = _ResourceNotFoundException


class _FakeCognitoClient:
    """A minimal in-memory ``cognito-idp`` fake for offline provisioning tests."""

    def __init__(self) -> None:
        self.exceptions = _FakeExceptions()
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
        self.pools[UserPoolId]['clients'][client_id] = {
            'flows': list(ExplicitAuthFlows),
            'secret': GenerateSecret,
        }
        return {'UserPoolClient': {'ClientId': client_id}}

    def admin_create_user(self, *, UserPoolId, Username, MessageAction):
        self._next_sub += 1
        sub = f'00000000-0000-0000-0000-00000000000{self._next_sub}'
        self.pools[UserPoolId]['users'][Username] = {'sub': sub, 'password': None}

    def admin_set_user_password(self, *, UserPoolId, Username, Password, Permanent):
        self.pools[UserPoolId]['users'][Username]['password'] = Password
        self.pools[UserPoolId]['users'][Username]['permanent'] = Permanent

    def admin_get_user(self, *, UserPoolId, Username):
        sub = self.pools[UserPoolId]['users'][Username]['sub']
        return {'UserAttributes': [{'Name': 'sub', 'Value': sub}]}

    def admin_initiate_auth(self, *, UserPoolId, ClientId, AuthFlow, AuthParameters):
        return {
            'AuthenticationResult': {
                'AccessToken': f'token-for-{AuthParameters["USERNAME"]}',
                'TokenType': 'Bearer',
            }
        }

    def delete_user_pool(self, *, UserPoolId):
        if UserPoolId not in self.pools:
            raise self.exceptions.ResourceNotFoundException(UserPoolId)
        del self.pools[UserPoolId]


class TestPureHelpers:
    """Discovery/issuer URLs and auth flows are deterministic.

    Validates: Requirements AgentCore deployment demonstration.
    """

    def test_issuer_and_discovery_urls(self) -> None:
        """The issuer and discovery URLs follow the Cognito OIDC convention."""
        assert cognito_mod.issuer_url(region='us-east-1', user_pool_id='us-east-1_abc') == (
            'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc'
        )
        assert cognito_mod.discovery_url(region='us-east-1', user_pool_id='us-east-1_abc') == (
            'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc/'
            '.well-known/openid-configuration'
        )

    def test_auth_flows_enable_admin_password(self) -> None:
        """The app client enables the admin password flow so tokens can be minted."""
        flows = cognito_mod.app_client_auth_flows()
        assert 'ALLOW_ADMIN_USER_PASSWORD_AUTH' in flows


class TestProvisionIdentityProvider:
    """Provisioning creates the pool/client/users, records the pool, and mints tokens.

    Validates: Requirements Provisioning and teardown lifecycle, Cross-tenant isolation
    verification.
    """

    def test_provision_returns_users_with_subs_and_tokens(self) -> None:
        """Each provisioned user has a distinct sub and a minted access token."""
        client = _FakeCognitoClient()
        inventory = ResourceInventory(deployment='agentcore', region='us-east-1')

        idp = cognito_mod.provision_identity_provider(
            cognito_client=client,
            inventory=inventory,
            region='us-east-1',
            usernames=['Tenant_A', 'Tenant_B'],
            password='Aho1!secret-value',  # pragma: allowlist secret
        )

        assert idp.discovery_url.endswith('/.well-known/openid-configuration')
        assert [user.username for user in idp.users] == ['Tenant_A', 'Tenant_B']
        subs = {user.sub for user in idp.users}
        assert len(subs) == 2
        assert idp.users[0].access_token == 'token-for-Tenant_A'  # pragma: allowlist secret
        assert idp.users[1].access_token == 'token-for-Tenant_B'  # pragma: allowlist secret

        pool_records = [
            record
            for record in inventory.records
            if record.resource_type == cognito_mod.RESOURCE_TYPE_COGNITO_USER_POOL
        ]
        assert len(pool_records) == 1
        assert pool_records[0].resource_id == idp.user_pool_id

    def test_inventory_never_contains_tokens(self) -> None:
        """The minted tokens (Credential_Material) never appear in any inventory attribute."""
        client = _FakeCognitoClient()
        inventory = ResourceInventory(deployment='agentcore', region='us-east-1')

        idp = cognito_mod.provision_identity_provider(
            cognito_client=client,
            inventory=inventory,
            region='us-east-1',
            usernames=['Tenant_A', 'Tenant_B'],
            password='Aho1!secret-value',  # pragma: allowlist secret
        )

        serialized = inventory.to_json()
        for user in idp.users:
            assert user.access_token not in serialized

    def test_delete_user_pool_is_idempotent(self) -> None:
        """Deleting the pool removes it; a second delete reports already-absent."""
        client = _FakeCognitoClient()
        inventory = ResourceInventory(deployment='agentcore', region='us-east-1')
        idp = cognito_mod.provision_identity_provider(
            cognito_client=client,
            inventory=inventory,
            region='us-east-1',
            usernames=['Tenant_A', 'Tenant_B'],
            password='Aho1!secret-value',  # pragma: allowlist secret
        )

        cognito_mod.delete_user_pool(cognito_client=client, user_pool_id=idp.user_pool_id)
        assert idp.user_pool_id not in client.pools

        with pytest.raises(ResourceNotFound):
            cognito_mod.delete_user_pool(cognito_client=client, user_pool_id=idp.user_pool_id)

    def test_mint_raises_on_challenge(self) -> None:
        """A challenge response (no tokens) raises rather than returning an empty token."""

        class _ChallengeClient(_FakeCognitoClient):
            def admin_initiate_auth(self, **_kwargs):
                return {'ChallengeName': 'NEW_PASSWORD_REQUIRED'}

        client = _ChallengeClient()
        with pytest.raises(RuntimeError):
            cognito_mod.mint_access_token(
                cognito_client=client,
                user_pool_id='p',
                app_client_id='c',
                username='Tenant_A',
                password='pw',  # pragma: allowlist secret
            )
