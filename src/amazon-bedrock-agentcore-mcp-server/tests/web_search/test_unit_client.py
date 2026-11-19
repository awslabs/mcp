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

"""Unit tests for the web search client and tool registration."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search import client as client_mod
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def clear_cache():
    """Reset the cached client around each test."""
    client_mod.get_web_search_client.cache_clear()
    yield
    client_mod.get_web_search_client.cache_clear()


class TestGetWebSearchClient:
    """Tests for get_web_search_client."""

    def test_creates_one_cached_client(self, monkeypatch):
        """The client is built once, for AWS_REGION, with the web-search user agent."""
        monkeypatch.setenv('AWS_REGION', 'eu-west-1')
        with patch.object(client_mod, 'boto3') as mock_boto3:
            first = client_mod.get_web_search_client()
            again = client_mod.get_web_search_client()

        assert first is again
        mock_boto3.Session.assert_called_once_with(region_name='eu-west-1')
        call = mock_boto3.Session.return_value.client.call_args
        assert call.args[0] == 'bedrock-agentcore'
        assert 'web-search' in call.kwargs['config'].user_agent_extra

    def test_default_region_fallback(self, monkeypatch):
        """With no AWS_REGION the client is built for us-east-1."""
        monkeypatch.delenv('AWS_REGION', raising=False)
        with patch.object(client_mod, 'boto3') as mock_boto3:
            client_mod.get_web_search_client()

        mock_boto3.Session.assert_called_once_with(region_name='us-east-1')


class TestRegisterWebSearchTools:
    """Tests for register_web_search_tools."""

    def test_registers_one_read_only_tool(self):
        """Registration adds one read-only, open-world tool named web_search."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search import (
            register_web_search_tools,
        )

        mock_mcp = MagicMock()
        mock_mcp.tool.return_value = lambda fn: fn

        register_web_search_tools(mock_mcp)

        mock_mcp.tool.assert_called_once()
        kwargs = mock_mcp.tool.call_args.kwargs
        assert kwargs['name'] == 'web_search'
        assert kwargs['annotations'].read_only_hint is True
        assert kwargs['annotations'].open_world_hint is True
