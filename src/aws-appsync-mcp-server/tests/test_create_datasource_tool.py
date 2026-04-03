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

"""Unit tests for create_datasource tool."""

import pytest
from awslabs.aws_appsync_mcp_server.tools.create_datasource import register_create_datasource_tool
from unittest.mock import patch


class TestCreateDatasourceTool:
    """Test create_datasource tool registration and execution."""

    @patch('awslabs.aws_appsync_mcp_server.tools.create_datasource.create_datasource_operation')
    @pytest.mark.asyncio
    async def test_tool_execution(self, mock_operation):
        """Test tool execution calls operation with correct parameters."""
        mock_operation.return_value = {'dataSource': {'name': 'test'}}

        # Mock MCP server
        from typing import Any, Callable

        class MockMCP:
            def __init__(self):
                self.tool_func: Callable[..., Any] | None = None

            def tool(self, **kwargs):
                def decorator(func):
                    self.tool_func = func
                    return func

                return decorator

        mock_mcp = MockMCP()
        register_create_datasource_tool(mock_mcp)

        # Execute the tool function
        tool_func = mock_mcp.tool_func
        assert tool_func is not None, 'Tool function was not registered'
        result = await tool_func(
            'api123',
            'test-ds',
            'HTTP',
            description='test',
            service_role_arn='arn:aws:iam::123456789012:role/test',
            http_config={'endpoint': 'https://api.example.com'},
        )

        assert result == {'dataSource': {'name': 'test'}}
        mock_operation.assert_called_once_with(
            'api123',
            'test-ds',
            'HTTP',
            'test',
            'arn:aws:iam::123456789012:role/test',
            None,
            None,
            None,
            None,
            {'endpoint': 'https://api.example.com'},
            None,
            None,
            None,
        )
