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

"""Unit tests for AWS client utility (BrowserClient wrapper)."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser import browser_client
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.browser_client import (
    DEFAULT_BROWSER_CLIENT_TTL_SECONDS,
    MCP_INTEGRATION_SOURCE,
    _browser_client_created_at,
    _browser_clients,
    get_browser_client,
)
from unittest.mock import MagicMock, patch


PATCH_BROWSER_CLIENT = (
    'awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.browser_client.BrowserClient'
)
PATCH_MONOTONIC = (
    'awslabs.amazon_bedrock_agentcore_mcp_server.tools.browser.browser_client.time.monotonic'
)


class TestGetBrowserClient:
    """Tests for get_browser_client utility."""

    def setup_method(self):
        """Clear client cache before each test."""
        _browser_clients.clear()
        _browser_client_created_at.clear()

    @patch.dict('os.environ', {}, clear=True)
    @patch(PATCH_BROWSER_CLIENT)
    def test_creates_client_with_defaults(self, mock_browser_client_cls):
        """Creates client with default region (us-east-1) when no env var set."""
        mock_instance = MagicMock()
        mock_browser_client_cls.return_value = mock_instance

        client = get_browser_client()

        mock_browser_client_cls.assert_called_once_with(
            region='us-east-1', integration_source=MCP_INTEGRATION_SOURCE
        )
        assert client is mock_instance

    @patch.dict('os.environ', {'AWS_REGION': 'eu-west-1'}, clear=True)
    @patch(PATCH_BROWSER_CLIENT)
    def test_creates_client_with_env_region(self, mock_browser_client_cls):
        """Creates client using AWS_REGION environment variable."""
        mock_instance = MagicMock()
        mock_browser_client_cls.return_value = mock_instance

        client = get_browser_client()

        mock_browser_client_cls.assert_called_once_with(
            region='eu-west-1', integration_source=MCP_INTEGRATION_SOURCE
        )
        assert client is mock_instance

    @patch(PATCH_BROWSER_CLIENT)
    def test_creates_client_with_explicit_region(self, mock_browser_client_cls):
        """Creates client with explicitly specified region."""
        mock_instance = MagicMock()
        mock_browser_client_cls.return_value = mock_instance

        client = get_browser_client(region_name='ap-southeast-1')

        mock_browser_client_cls.assert_called_once_with(
            region='ap-southeast-1', integration_source=MCP_INTEGRATION_SOURCE
        )
        assert client is mock_instance

    @patch(PATCH_BROWSER_CLIENT)
    def test_caches_client(self, mock_browser_client_cls):
        """Returns cached client on subsequent calls with same region (within TTL)."""
        mock_instance = MagicMock()
        mock_browser_client_cls.return_value = mock_instance

        client1 = get_browser_client(region_name='us-east-1')
        client2 = get_browser_client(region_name='us-east-1')

        assert client1 is client2
        assert mock_browser_client_cls.call_count == 1

    @patch(PATCH_BROWSER_CLIENT)
    def test_different_regions_different_clients(self, mock_browser_client_cls):
        """Different regions produce different cached clients."""
        mock_browser_client_cls.side_effect = [MagicMock(), MagicMock()]

        client1 = get_browser_client(region_name='us-east-1')
        client2 = get_browser_client(region_name='us-west-2')

        assert client1 is not client2
        assert mock_browser_client_cls.call_count == 2

    @patch(PATCH_BROWSER_CLIENT)
    def test_integration_source_tagging(self, mock_browser_client_cls):
        """Client is created with MCP integration source for telemetry."""
        mock_browser_client_cls.return_value = MagicMock()

        get_browser_client(region_name='us-east-1')

        call_kwargs = mock_browser_client_cls.call_args.kwargs
        assert call_kwargs['integration_source'] == MCP_INTEGRATION_SOURCE

    @patch(PATCH_MONOTONIC)
    @patch(PATCH_BROWSER_CLIENT)
    def test_recreates_client_after_ttl_expiry(self, mock_browser_client_cls, mock_monotonic):
        """A cache entry older than the TTL is recreated (picks up refreshed creds).

        This is the credential-caching regression guard: without TTL expiry the
        first client would be returned forever, serving credentials captured at
        construction time even after `ada credentials update` / role rotation.
        """
        first, second = MagicMock(), MagicMock()
        mock_browser_client_cls.side_effect = [first, second]

        # t=0 create; t just past TTL -> must recreate.
        mock_monotonic.side_effect = [0.0, DEFAULT_BROWSER_CLIENT_TTL_SECONDS + 1.0]

        client1 = get_browser_client(region_name='us-east-1')
        client2 = get_browser_client(region_name='us-east-1')

        assert client1 is first
        assert client2 is second
        assert client1 is not client2
        assert mock_browser_client_cls.call_count == 2

    @patch(PATCH_MONOTONIC)
    @patch(PATCH_BROWSER_CLIENT)
    def test_reuses_client_within_ttl(self, mock_browser_client_cls, mock_monotonic):
        """A cache entry younger than the TTL is reused (no rebuild)."""
        mock_browser_client_cls.side_effect = [MagicMock(), MagicMock()]
        # Second call is still inside the TTL window.
        mock_monotonic.side_effect = [0.0, DEFAULT_BROWSER_CLIENT_TTL_SECONDS - 1.0]

        client1 = get_browser_client(region_name='us-east-1')
        client2 = get_browser_client(region_name='us-east-1')

        assert client1 is client2
        assert mock_browser_client_cls.call_count == 1

    @patch.dict('os.environ', {'AGENTCORE_BROWSER_CLIENT_TTL_SECONDS': '0'}, clear=True)
    @patch(PATCH_BROWSER_CLIENT)
    def test_ttl_zero_disables_caching(self, mock_browser_client_cls):
        """TTL of 0 disables caching: every call builds a fresh client."""
        mock_browser_client_cls.side_effect = [MagicMock(), MagicMock()]

        client1 = get_browser_client(region_name='us-east-1')
        client2 = get_browser_client(region_name='us-east-1')

        assert client1 is not client2
        assert mock_browser_client_cls.call_count == 2
        # Nothing should be retained in the cache when disabled.
        assert 'us-east-1' not in _browser_clients

    @patch.dict('os.environ', {'AGENTCORE_BROWSER_CLIENT_TTL_SECONDS': 'not-a-number'}, clear=True)
    @patch(PATCH_BROWSER_CLIENT)
    def test_invalid_ttl_env_falls_back_to_default(self, mock_browser_client_cls):
        """An unparseable TTL env var falls back to the default and still caches."""
        mock_browser_client_cls.return_value = MagicMock()

        assert browser_client._get_ttl_seconds() == DEFAULT_BROWSER_CLIENT_TTL_SECONDS

        client1 = get_browser_client(region_name='us-east-1')
        client2 = get_browser_client(region_name='us-east-1')

        assert client1 is client2
        assert mock_browser_client_cls.call_count == 1

    @patch.dict('os.environ', {'AGENTCORE_BROWSER_CLIENT_TTL_SECONDS': '900'}, clear=True)
    def test_ttl_env_override_parsed(self):
        """A valid TTL env var overrides the default."""
        assert browser_client._get_ttl_seconds() == 900.0
