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

"""Amazon Cognito identity-provider provisioning + token minting for the harness.

The AgentCore deployment authenticates callers with a JWT authorizer that verifies tokens
cryptographically against an OIDC provider. To make the suite deploy-and-run with zero
manual identity setup, provisioning stands up a Cognito user pool as that provider and mints
the caller tokens the tests present; teardown deletes the pool.

What provisioning creates:

- A **user pool** whose issuer/discovery URL the AgentCore JWT authorizer trusts.
- An **app client** (no secret) with the admin/user password auth flows enabled, whose
  client id the authorizer's ``allowedClients`` list pins.
- One **user per tenant** (Tenant_A / Tenant_B) with a permanent password.

Provisioning then mints each user's access token via ``AdminInitiateAuth`` and reads each
user's ``sub`` (the stable JWT ``sub`` claim, a UUID) via ``AdminGetUser``. The tenant's
registry ``identity`` is exactly that ``sub``, and the minted access token carries it, so the
server's ``jwt`` mechanism resolves the correct Tenant_Role. AgentCore validates the access
token's ``client_id`` against ``allowedClients``.

Design for testability
-----------------------
:func:`discovery_url`, :func:`issuer_url`, and :func:`app_client_auth_flows` are pure and
asserted offline. All AWS work flows through the injected ``cognito_client`` passed to
:func:`provision_identity_provider` and :func:`mint_access_token`; no boto3 client is
constructed at import time. Minted tokens are **Credential_Material**: they are returned in
memory to the orchestrator and are never written to the inventory or any artifact on disk.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from integration.deploy.common import ResourceNotFound
from integration.harness.inventory import ResourceInventory, ResourceRecord
from typing import Any


# ``resource_type`` recorded in the inventory for the created user pool. The app client and
# users are deleted implicitly when the pool is deleted, so only the pool is inventoried.
RESOURCE_TYPE_COGNITO_USER_POOL = 'cognito-user-pool'

# Default names for the harness identity provider.
DEFAULT_USER_POOL_NAME = 'aho-mcp-itest-pool'
DEFAULT_APP_CLIENT_NAME = 'aho-mcp-itest-client'

# The explicit auth flows the app client enables so the harness can mint tokens
# non-interactively via AdminInitiateAuth.
_AUTH_FLOWS = ('ALLOW_ADMIN_USER_PASSWORD_AUTH', 'ALLOW_REFRESH_TOKEN_AUTH')
_ADMIN_AUTH_FLOW = 'ADMIN_USER_PASSWORD_AUTH'


def issuer_url(*, region: str, user_pool_id: str) -> str:
    """Return the OIDC issuer URL for a Cognito user pool."""
    return f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'


def discovery_url(*, region: str, user_pool_id: str) -> str:
    """Return the OIDC discovery URL the AgentCore JWT authorizer reads."""
    return (
        f'{issuer_url(region=region, user_pool_id=user_pool_id)}/.well-known/openid-configuration'
    )


def app_client_auth_flows() -> list[str]:
    """Return the explicit auth flows the harness app client enables (pure)."""
    return list(_AUTH_FLOWS)


@dataclass(frozen=True)
class CognitoUser:
    """A provisioned Cognito user and its minted access token.

    Attributes:
        username: The user's login name (a tenant label, e.g. ``Tenant_A``).
        sub: The user's stable ``sub`` claim (a UUID); the registry Authenticated_Identity.
        access_token: The minted OAuth access token (Credential_Material; never persisted).
    """

    username: str
    sub: str
    access_token: str


@dataclass(frozen=True)
class IdentityProvider:
    """The provisioned Cognito identity provider and its callers.

    Attributes:
        user_pool_id: The Cognito user pool id (the inventory resource id).
        app_client_id: The app client id the authorizer's ``allowedClients`` pins.
        discovery_url: The OIDC discovery URL the JWT authorizer trusts.
        users: The provisioned users (one per tenant), in tenant order.
    """

    user_pool_id: str
    app_client_id: str
    discovery_url: str
    users: tuple[CognitoUser, ...]


def mint_access_token(
    *,
    cognito_client: Any,
    user_pool_id: str,
    app_client_id: str,
    username: str,
    password: str,
) -> str:
    """Mint a user's access token via ``AdminInitiateAuth`` (ADMIN_USER_PASSWORD_AUTH).

    Args:
        cognito_client: An injected boto3 ``cognito-idp`` client.
        user_pool_id: The user pool id.
        app_client_id: The app client id.
        username: The user to authenticate.
        password: The user's permanent password.

    Returns:
        The user's OAuth access token (Credential_Material).

    Raises:
        RuntimeError: If Cognito returns a challenge instead of tokens (e.g. the password is
            not permanent), so the failure is explicit rather than a missing token.
    """
    response = cognito_client.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=app_client_id,
        AuthFlow=_ADMIN_AUTH_FLOW,
        AuthParameters={'USERNAME': username, 'PASSWORD': password},
    )
    result = response.get('AuthenticationResult')
    if not result or 'AccessToken' not in result:
        challenge = response.get('ChallengeName', 'unknown')
        raise RuntimeError(
            f'Cognito did not return tokens for {username!r}; got challenge {challenge!r}.'
        )
    return result['AccessToken']


def _read_sub(cognito_client: Any, user_pool_id: str, username: str) -> str:
    """Return a user's ``sub`` attribute via ``AdminGetUser``."""
    response = cognito_client.admin_get_user(UserPoolId=user_pool_id, Username=username)
    for attribute in response.get('UserAttributes', []):
        if attribute.get('Name') == 'sub':
            return attribute['Value']
    raise RuntimeError(f'Cognito user {username!r} has no sub attribute.')


def provision_identity_provider(
    *,
    cognito_client: Any,
    inventory: ResourceInventory,
    region: str,
    usernames: Sequence[str],
    password: str,
    user_pool_name: str = DEFAULT_USER_POOL_NAME,
    app_client_name: str = DEFAULT_APP_CLIENT_NAME,
) -> IdentityProvider:
    """Create the Cognito pool/client/users, mint tokens, and return the provider.

    The user pool is recorded in the inventory immediately after creation so teardown can
    delete it even if a later step fails (Req 8.3). For each username a user is created with a
    permanent password, its ``sub`` is read, and its access token is minted.

    Args:
        cognito_client: An injected boto3 ``cognito-idp`` client.
        inventory: The inventory to record the created user pool into.
        region: The deployment region (used for the discovery URL and inventory record).
        usernames: The tenant usernames to create (one per tenant, e.g. Tenant_A/Tenant_B).
        password: The permanent password to set for every created user.
        user_pool_name: The user pool name.
        app_client_name: The app client name.

    Returns:
        The provisioned :class:`IdentityProvider`, including minted access tokens.
    """
    pool = cognito_client.create_user_pool(PoolName=user_pool_name)
    user_pool_id = pool['UserPool']['Id']
    # Record the pool right after creation so teardown finds it even if later steps fail.
    inventory.add(
        ResourceRecord(
            resource_id=user_pool_id,
            resource_type=RESOURCE_TYPE_COGNITO_USER_POOL,
            region=region,
            deployment=inventory.deployment,
        )
    )

    client = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=app_client_name,
        GenerateSecret=False,
        ExplicitAuthFlows=app_client_auth_flows(),
    )
    app_client_id = client['UserPoolClient']['ClientId']

    users: list[CognitoUser] = []
    for username in usernames:
        cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            MessageAction='SUPPRESS',
        )
        cognito_client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=password,
            Permanent=True,
        )
        sub = _read_sub(cognito_client, user_pool_id, username)
        access_token = mint_access_token(
            cognito_client=cognito_client,
            user_pool_id=user_pool_id,
            app_client_id=app_client_id,
            username=username,
            password=password,
        )
        users.append(CognitoUser(username=username, sub=sub, access_token=access_token))

    return IdentityProvider(
        user_pool_id=user_pool_id,
        app_client_id=app_client_id,
        discovery_url=discovery_url(region=region, user_pool_id=user_pool_id),
        users=tuple(users),
    )


def delete_user_pool(*, cognito_client: Any, user_pool_id: str) -> None:
    """Delete a Cognito user pool, mapping absence to ``ResourceNotFound`` (idempotent).

    Args:
        cognito_client: An injected boto3 ``cognito-idp`` client.
        user_pool_id: The user pool to delete.

    Raises:
        ResourceNotFound: If the pool does not exist.
    """
    try:
        cognito_client.delete_user_pool(UserPoolId=user_pool_id)
    except cognito_client.exceptions.ResourceNotFoundException as exc:
        raise ResourceNotFound(f'Cognito user pool {user_pool_id!r} already absent.') from exc
