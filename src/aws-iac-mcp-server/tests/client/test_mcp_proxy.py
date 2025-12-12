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
from awslabs.aws_iac_mcp_server.client.mcp_proxy import create_proxied_tool
from unittest.mock import AsyncMock, MagicMock


class TestCreateProxiedTool:
    """Test cases for create_proxied_tool function."""

    @pytest.mark.asyncio
    async def test_create_proxied_tool_calls_get_tool(self):
        """Test that create_proxied_tool calls get_tool on proxy server."""
        mock_proxy_server = MagicMock()
        mock_proxy_server.get_tool = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match='Tool .* not found'):
            await create_proxied_tool(
                proxy_server=mock_proxy_server,
                remote_tool_name='remote_tool',
            )

        mock_proxy_server.get_tool.assert_called_once_with('remote_tool')

    @pytest.mark.asyncio
    async def test_create_proxied_tool_not_found(self):
        """Test error when remote tool is not found."""
        mock_proxy_server = MagicMock()
        mock_proxy_server.get_tool = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match='Tool .* not found on remote server'):
            await create_proxied_tool(
                proxy_server=mock_proxy_server,
                remote_tool_name='nonexistent_tool',
            )
