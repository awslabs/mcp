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

"""Tests for the ROSA auth handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_auth_handler import RosaAuthHandler


class TestRosaWhoami:
    """Tests for rosa_whoami."""

    @pytest.mark.asyncio
    async def test_given_valid_token_when_whoami_then_decodes_jwt(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_whoami decodes JWT token correctly."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_whoami(mock_context)

        mock_ocm_client._ensure_token.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert 'username' in data
        assert 'email' in data
        assert 'org_id' in data
        assert 'username' in data


class TestRosaListIdps:
    """Tests for rosa_list_idps."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_list_idps_then_returns_idp_list(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_idps returns IDP list."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_idps(mock_context, cluster_id='test-id')

        mock_ocm_client.list_identity_providers.assert_called_once_with('test-id')
        data = json.loads(result[0].text)
        assert 'items' in data
        assert len(data['items']) == 1
        assert data['items'][0]['type'] == 'HTPasswdIdentityProvider'


class TestRosaCreateIdp:
    """Tests for rosa_create_idp."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_idp_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_idp requires allow_write."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_idp(
                mock_context,
                cluster_id='test-id',
                name='my-idp',
                idp_type='htpasswd',
            )

    @pytest.mark.asyncio
    async def test_given_htpasswd_type_when_create_then_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_idp with HTPasswd type."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=True)
        config = {'username': 'admin', 'password': 'secret123'}
        await handler.rosa_create_idp(
            mock_context,
            cluster_id='test-id',
            name='my-htpasswd',
            idp_type='htpasswd',
            config=config,
        )

        mock_ocm_client.create_identity_provider.assert_called_once()
        call_args = mock_ocm_client.create_identity_provider.call_args
        assert call_args[0][0] == 'test-id'
        body = call_args[0][1]
        assert body['type'] == 'HTPasswdIdentityProvider'
        assert body['name'] == 'my-htpasswd'
        assert body['mapping_method'] == 'claim'
        assert body['htpasswd'] == config

    @pytest.mark.asyncio
    async def test_given_github_type_when_create_then_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_idp with GitHub type."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=True)
        config = {
            'client_id': 'gh-client-id',
            'client_secret': 'gh-secret',
            'organizations': ['my-org'],
        }
        await handler.rosa_create_idp(
            mock_context,
            cluster_id='test-id',
            name='github-idp',
            idp_type='github',
            config=config,
        )

        body = mock_ocm_client.create_identity_provider.call_args[0][1]
        assert body['type'] == 'GithubIdentityProvider'
        assert body['github'] == config

    @pytest.mark.asyncio
    async def test_given_openid_type_when_create_then_builds_correct_body(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_idp with OpenID type."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=True)
        config = {
            'client_id': 'oidc-client',
            'client_secret': 'oidc-secret',
            'issuer': 'https://accounts.google.com',
        }
        await handler.rosa_create_idp(
            mock_context,
            cluster_id='test-id',
            name='openid-idp',
            idp_type='openid',
            config=config,
        )

        body = mock_ocm_client.create_identity_provider.call_args[0][1]
        assert body['type'] == 'OpenIDIdentityProvider'
        assert body['openid'] == config

    @pytest.mark.asyncio
    async def test_given_invalid_type_when_create_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_idp rejects invalid IDP type."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=True)

        with pytest.raises(ValueError, match='Invalid idp_type'):
            await handler.rosa_create_idp(
                mock_context,
                cluster_id='test-id',
                name='bad-idp',
                idp_type='invalid',
            )


class TestRosaDeleteIdp:
    """Tests for rosa_delete_idp."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_delete_idp_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_idp requires allow_write."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_delete_idp(
                mock_context, cluster_id='test-id', idp_id='idp-1'
            )

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_delete_then_calls_ocm_correctly(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_delete_idp calls OCM correctly."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_delete_idp(
            mock_context, cluster_id='test-id', idp_id='idp-1'
        )

        mock_ocm_client.delete_identity_provider.assert_called_once_with('test-id', 'idp-1')
        data = json.loads(result[0].text)
        assert data['status'] == 'deleted'
        assert data['idp_id'] == 'idp-1'
        assert data['http_status'] == 204


class TestRosaCreateAdmin:
    """Tests for rosa_create_admin."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_create_admin_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_admin requires allow_write."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_create_admin(mock_context, cluster_id='test-id')

    @pytest.mark.asyncio
    async def test_given_write_enabled_when_create_admin_then_generates_password(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_create_admin generates password and creates HTPasswd IDP."""
        handler = RosaAuthHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_create_admin(mock_context, cluster_id='test-id')

        mock_ocm_client.create_identity_provider.assert_called_once()
        call_args = mock_ocm_client.create_identity_provider.call_args
        assert call_args[0][0] == 'test-id'
        body = call_args[0][1]
        assert body['type'] == 'HTPasswdIdentityProvider'
        assert body['name'] == 'cluster-admin'
        assert body['htpasswd']['username'] == 'cluster-admin'
        assert len(body['htpasswd']['password']) == 23

        data = json.loads(result[0].text)
        assert data['username'] == 'cluster-admin'
        assert len(data['password']) == 23
        assert 'username' in data
        assert 'note' in data
