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

"""Tests for create_schema tool registration."""

import pytest
from awslabs.aws_appsync_mcp_server.tools.create_schema import register_create_schema_tool
from unittest.mock import Mock, patch


class TestCreateSchemaTool:
    """Test cases for create_schema tool registration."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_appsync_mcp_server.tools.create_schema.create_schema_operation')
    async def test_tool_execution(self, mock_operation):
        """Test that the registered tool calls the operation correctly."""
        # Setup mock MCP server
        from typing import Any, Callable

        mock_mcp = Mock()
        captured_func: Callable[..., Any] | None = None

        def capture_tool_func(name, description, annotations):
            def decorator(func):
                nonlocal captured_func
                captured_func = func
                return func

            return decorator

        mock_mcp.tool = capture_tool_func

        # Register the tool
        register_create_schema_tool(mock_mcp)

        # Setup operation mock
        mock_operation.return_value = {'status': 'SUCCESS', 'details': 'Schema created'}

        # Execute the tool
        assert captured_func is not None, 'Tool function was not registered'
        from typing import cast

        tool_func = cast(Callable[..., Any], captured_func)
        result = await tool_func('test-api-id', 'type Query { hello: String }')

        # Verify operation was called correctly
        mock_operation.assert_called_once_with('test-api-id', 'type Query { hello: String }')
        assert result == {'status': 'SUCCESS', 'details': 'Schema created'}
