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

import pytest
from awslabs.aws_iac_mcp_server.client.mcp_proxy import (
    create_local_proxied_tool,
    get_remote_proxy_server_tool,
)
from fastmcp import FastMCP
from fastmcp.tools import Tool
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetRemoteProxyServerTool:
    """Test cases for get_remote_proxy_server_tool function."""

    @pytest.mark.asyncio
    async def test_get_remote_tool_success(self):
        """Test successfully retrieving a remote tool."""
        mock_client = MagicMock(spec=FastMCP)
        mock_tool = MagicMock(spec=Tool)
        mock_tool.name = 'remote_tool'

        mock_proxy = MagicMock()
        mock_proxy.get_tool = AsyncMock(return_value=mock_tool)

        with patch.object(FastMCP, 'as_proxy', return_value=mock_proxy):
            result = await get_remote_proxy_server_tool(
                remote_proxy_client=mock_client,
                remote_tool_name='remote_tool',
            )

            assert result == mock_tool
            mock_proxy.get_tool.assert_called_once_with('remote_tool')

    @pytest.mark.asyncio
    async def test_get_remote_tool_not_found(self):
        """Test error when remote tool is not found."""
        mock_client = MagicMock(spec=FastMCP)

        mock_proxy = MagicMock()
        mock_proxy.get_tool = AsyncMock(return_value=None)

        with patch.object(FastMCP, 'as_proxy', return_value=mock_proxy):
            with pytest.raises(ValueError, match='Tool remote_tool not found on remote server'):
                await get_remote_proxy_server_tool(
                    remote_proxy_client=mock_client,
                    remote_tool_name='remote_tool',
                )


class TestCreateLocalProxiedTool:
    """Test cases for create_local_proxied_tool function."""

    @pytest.mark.asyncio
    async def test_create_proxied_tool_basic(self):
        """Test creating a proxied tool with basic parameters."""
        mock_remote_tool = MagicMock(spec=Tool)
        mock_proxied_tool = MagicMock(spec=Tool)

        with patch.object(Tool, 'from_tool', return_value=mock_proxied_tool) as mock_from_tool:
            result = await create_local_proxied_tool(
                remote_tool=mock_remote_tool,
                local_tool_name='local_tool',
            )

            assert result == mock_proxied_tool
            mock_from_tool.assert_called_once_with(
                mock_remote_tool,
                name='local_tool',
            )

    @pytest.mark.asyncio
    async def test_create_proxied_tool_with_description(self):
        """Test creating a proxied tool with custom description."""
        mock_remote_tool = MagicMock(spec=Tool)
        mock_proxied_tool = MagicMock(spec=Tool)

        with patch.object(Tool, 'from_tool', return_value=mock_proxied_tool) as mock_from_tool:
            result = await create_local_proxied_tool(
                remote_tool=mock_remote_tool,
                local_tool_name='local_tool',
                local_tool_description='Custom description',
            )

            assert result == mock_proxied_tool
            mock_from_tool.assert_called_once_with(
                mock_remote_tool,
                name='local_tool',
                description='Custom description',
            )

    @pytest.mark.asyncio
    async def test_create_proxied_tool_with_transformer(self):
        """Test creating a proxied tool with response transformer."""
        mock_remote_tool = MagicMock(spec=Tool)
        mock_proxied_tool = MagicMock(spec=Tool)

        def transformer(response):
            return f'Transformed: {response}'

        with patch.object(Tool, 'from_tool', return_value=mock_proxied_tool) as mock_from_tool:
            result = await create_local_proxied_tool(
                remote_tool=mock_remote_tool,
                local_tool_name='local_tool',
                response_transformer=transformer,
            )

            assert result == mock_proxied_tool
            mock_from_tool.assert_called_once_with(
                mock_remote_tool,
                name='local_tool',
                transform_fn=transformer,
            )

    @pytest.mark.asyncio
    async def test_create_proxied_tool_with_all_parameters(self):
        """Test creating a proxied tool with all optional parameters."""
        mock_remote_tool = MagicMock(spec=Tool)
        mock_proxied_tool = MagicMock(spec=Tool)

        def transformer(response):
            return f'Transformed: {response}'

        with patch.object(Tool, 'from_tool', return_value=mock_proxied_tool) as mock_from_tool:
            result = await create_local_proxied_tool(
                remote_tool=mock_remote_tool,
                local_tool_name='local_tool',
                local_tool_description='Custom description',
                response_transformer=transformer,
            )

            assert result == mock_proxied_tool
            mock_from_tool.assert_called_once_with(
                mock_remote_tool,
                name='local_tool',
                description='Custom description',
                transform_fn=transformer,
            )
