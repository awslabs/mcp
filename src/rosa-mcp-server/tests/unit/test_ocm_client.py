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

"""Tests for the OCM client."""

import pytest
import time
from awslabs.rosa_mcp_server.ocm_client import (
    API_PATH,
    OCM_API_URL,
    OCM_CLIENT_ID_DEFAULT,
    OCM_SSO_TOKEN_URL,
    OCMClient,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestOCMClientInitialization:
    """Tests for OCMClient initialization and token loading."""

    def test_given_offline_token_in_env_when_init_then_uses_env_token(self):
        """Test token loading from environment variable."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'env-token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()
                assert client._offline_token == 'env-token'

    def test_given_offline_token_arg_when_init_then_uses_arg_token(self):
        """Test token loading from constructor argument takes priority."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'env-token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient(offline_token='arg-token')
                assert client._offline_token == 'arg-token'

    def test_given_token_in_config_file_when_no_env_then_uses_config_token(self):
        """Test token loading from config file when env var is not set."""
        config = {'refresh_token': 'config-token', 'client_id': 'config-client'}
        with patch.dict('os.environ', {'OCM_TOKEN': '', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value=config):
                client = OCMClient()
                assert client._offline_token == 'config-token'
                assert client._client_id == 'config-client'

    def test_given_no_token_anywhere_when_init_then_raises_value_error(self):
        """Test ValueError when no token is available."""
        with patch.dict('os.environ', {'OCM_TOKEN': '', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                with pytest.raises(ValueError, match='OCM offline token required'):
                    OCMClient()

    def test_given_no_client_id_when_init_then_uses_default(self):
        """Test client_id fallback to default 'cloud-services'."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()
                assert client._client_id == OCM_CLIENT_ID_DEFAULT

    def test_given_client_id_in_env_when_init_then_uses_env_client_id(self):
        """Test client_id from OCM_CLIENT_ID env var."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'token', 'OCM_CLIENT_ID': 'my-client'}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()
                assert client._client_id == 'my-client'

    def test_given_custom_api_url_when_init_then_uses_custom_url(self):
        """Test custom API URL is used."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient(api_url='https://custom.api.com/')
                assert client._api_url == 'https://custom.api.com'


class TestOCMClientTokenManagement:
    """Tests for token exchange and caching."""

    @pytest.mark.asyncio
    async def test_given_no_token_when_ensure_token_then_makes_post_request(self):
        """Test _ensure_token makes correct POST request to SSO."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'offline-token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'new-access-token',
            'expires_in': 900,
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        client._http = mock_http_client

        token = await client._ensure_token()

        assert token == 'new-access-token'
        mock_http_client.post.assert_called_once_with(
            OCM_SSO_TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'client_id': OCM_CLIENT_ID_DEFAULT,
                'refresh_token': 'offline-token',
            },
        )

    @pytest.mark.asyncio
    async def test_given_valid_cached_token_when_ensure_token_then_returns_cached(self):
        """Test _ensure_token uses cached token when not expired."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'offline-token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()

        client._access_token = 'cached-token'
        client._token_expiry = time.time() + 600  # Expires in 10 minutes

        mock_http_client = AsyncMock()
        client._http = mock_http_client

        token = await client._ensure_token()

        assert token == 'cached-token'
        mock_http_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_given_expired_token_when_ensure_token_then_refreshes(self):
        """Test _ensure_token refreshes when token is expired."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'offline-token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()

        client._access_token = 'old-token'
        client._token_expiry = time.time() - 10  # Already expired

        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'refreshed-token',
            'expires_in': 900,
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        client._http = mock_http_client

        token = await client._ensure_token()

        assert token == 'refreshed-token'
        mock_http_client.post.assert_called_once()


class TestOCMClientHTTPMethods:
    """Tests for HTTP method helpers."""

    @pytest.fixture
    def client_with_token(self):
        """Create a client with a pre-set valid token."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'offline-token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()
        client._access_token = 'test-token'
        client._token_expiry = time.time() + 600
        return client

    @pytest.mark.asyncio
    async def test_get_formats_url_correctly(self, client_with_token):
        """Test _get method formats URLs correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'items': []}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        client_with_token._http = mock_http

        await client_with_token._get('/clusters', params={'page': 1})

        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert f'{OCM_API_URL}{API_PATH}/clusters' == call_args[0][0]
        assert call_args[1]['params'] == {'page': 1}

    @pytest.mark.asyncio
    async def test_post_formats_url_and_sends_body(self, client_with_token):
        """Test _post method formats URLs and sends JSON body."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'new'}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        client_with_token._http = mock_http

        body = {'name': 'test'}
        await client_with_token._post('/clusters', body)

        call_args = mock_http.post.call_args
        assert f'{OCM_API_URL}{API_PATH}/clusters' == call_args[0][0]
        assert call_args[1]['json'] == body

    @pytest.mark.asyncio
    async def test_patch_formats_url_and_sends_body(self, client_with_token):
        """Test _patch method formats URLs and sends JSON body."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'id': 'updated'}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.patch = AsyncMock(return_value=mock_response)
        client_with_token._http = mock_http

        body = {'replicas': 5}
        await client_with_token._patch('/clusters/c1', body)

        call_args = mock_http.patch.call_args
        assert f'{OCM_API_URL}{API_PATH}/clusters/c1' == call_args[0][0]
        assert call_args[1]['json'] == body

    @pytest.mark.asyncio
    async def test_delete_formats_url_correctly(self, client_with_token):
        """Test _delete method formats URLs correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.delete = AsyncMock(return_value=mock_response)
        client_with_token._http = mock_http

        result = await client_with_token._delete('/clusters/c1', params={'deprovision': 'true'})

        call_args = mock_http.delete.call_args
        assert f'{OCM_API_URL}{API_PATH}/clusters/c1' == call_args[0][0]
        assert call_args[1]['params'] == {'deprovision': 'true'}
        assert result == 204


class TestOCMClientClusterMethods:
    """Tests for cluster-specific OCM client methods."""

    @pytest.fixture
    def client_with_mocks(self):
        """Create client with mocked HTTP methods."""
        with patch.dict('os.environ', {'OCM_TOKEN': 'offline-token', 'OCM_CLIENT_ID': ''}):
            with patch.object(OCMClient, '_load_ocm_config', return_value={}):
                client = OCMClient()
        client._get = AsyncMock()
        client._post = AsyncMock()
        client._patch = AsyncMock()
        client._delete = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_list_clusters_with_search(self, client_with_mocks):
        """Test list_clusters with search parameter."""
        client_with_mocks._get.return_value = {'items': [], 'total': 0}
        await client_with_mocks.list_clusters(search="name like 'prod%'")
        client_with_mocks._get.assert_called_once_with(
            '/clusters',
            params={'page': 1, 'size': 100, 'search': "name like 'prod%'"},
        )

    @pytest.mark.asyncio
    async def test_list_clusters_without_search(self, client_with_mocks):
        """Test list_clusters without search parameter."""
        client_with_mocks._get.return_value = {'items': [], 'total': 0}
        await client_with_mocks.list_clusters()
        client_with_mocks._get.assert_called_once_with(
            '/clusters',
            params={'page': 1, 'size': 100},
        )

    @pytest.mark.asyncio
    async def test_get_cluster(self, client_with_mocks):
        """Test get_cluster calls correct path."""
        client_with_mocks._get.return_value = {'id': 'c1'}
        result = await client_with_mocks.get_cluster('c1')
        client_with_mocks._get.assert_called_once_with('/clusters/c1')
        assert result == {'id': 'c1'}

    @pytest.mark.asyncio
    async def test_create_cluster(self, client_with_mocks):
        """Test create_cluster posts body to correct path."""
        body = {'name': 'new-cluster'}
        client_with_mocks._post.return_value = {'id': 'new-id'}
        result = await client_with_mocks.create_cluster(body)
        client_with_mocks._post.assert_called_once_with('/clusters', body)
        assert result == {'id': 'new-id'}

    @pytest.mark.asyncio
    async def test_delete_cluster(self, client_with_mocks):
        """Test delete_cluster calls correct path with deprovision param."""
        client_with_mocks._delete.return_value = 204
        result = await client_with_mocks.delete_cluster('c1', deprovision=True)
        client_with_mocks._delete.assert_called_once_with(
            '/clusters/c1',
            params={'deprovision': 'true'},
        )
        assert result == 204
