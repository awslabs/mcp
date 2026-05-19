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

"""Tests for ErrorSignalingMiddleware."""

import pytest
from awslabs.billing_cost_management_mcp_server.server import (
    ErrorSignalingMiddleware,
    _ErrorToolResult,
)
from fastmcp.tools.tool import ToolResult
from mcp.types import CallToolResult, TextContent
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def middleware():
    """Create an ErrorSignalingMiddleware instance."""
    return ErrorSignalingMiddleware()


@pytest.fixture
def mock_context():
    """Create a mock middleware context."""
    return MagicMock()


class TestErrorSignalingMiddleware:
    """Tests for ErrorSignalingMiddleware.on_call_tool."""

    @pytest.mark.asyncio
    async def test_error_response_sets_is_error_true(self, middleware, mock_context):
        """When a tool returns status='error', isError should be True."""
        error_result = ToolResult(
            structured_content={'status': 'error', 'message': 'Access denied'},
        )
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        assert isinstance(result, _ErrorToolResult)
        mcp_result = result.to_mcp_result()
        assert isinstance(mcp_result, CallToolResult)
        assert mcp_result.isError is True
        assert mcp_result.structuredContent == {'status': 'error', 'message': 'Access denied'}

    @pytest.mark.asyncio
    async def test_success_response_unchanged(self, middleware, mock_context):
        """When a tool returns status='success', result should pass through unchanged."""
        success_result = ToolResult(
            structured_content={'status': 'success', 'data': {'cost': 100}},
        )
        call_next = AsyncMock(return_value=success_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        assert result is success_result

    @pytest.mark.asyncio
    async def test_error_response_preserves_content(self, middleware, mock_context):
        """Error response should preserve the original content blocks."""
        error_result = ToolResult(
            structured_content={
                'status': 'error',
                'error_type': 'ValidationError',
                'message': 'Invalid date format',
                'service': 'Cost Explorer',
                'operation': 'getCostAndUsage',
            },
        )
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        mcp_result = result.to_mcp_result()
        assert mcp_result.isError is True
        assert mcp_result.content == error_result.content
        assert mcp_result.structuredContent['error_type'] == 'ValidationError'

    @pytest.mark.asyncio
    async def test_error_response_preserves_meta(self, middleware, mock_context):
        """Error response should preserve meta if present."""
        error_result = ToolResult(
            structured_content={'status': 'error', 'message': 'fail'},
            meta={'requestId': '123'},
        )
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        mcp_result = result.to_mcp_result()
        assert mcp_result.isError is True
        assert mcp_result.meta == {'requestId': '123'}

    @pytest.mark.asyncio
    async def test_no_structured_content_passes_through(self, middleware, mock_context):
        """When structured_content is None, result should pass through."""
        result_no_structured = ToolResult(content='plain text response')
        call_next = AsyncMock(return_value=result_no_structured)

        result = await middleware.on_call_tool(mock_context, call_next)

        assert result is result_no_structured

    @pytest.mark.asyncio
    async def test_non_dict_structured_content_passes_through(self, middleware, mock_context):
        """When structured_content is not a dict, result should pass through."""
        # ToolResult requires structured_content to be a dict, so test with None
        text_result = ToolResult(content=[TextContent(type='text', text='hello')])
        call_next = AsyncMock(return_value=text_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        assert result is text_result

    @pytest.mark.asyncio
    async def test_non_tool_result_passes_through(self, middleware, mock_context):
        """When call_next returns something other than ToolResult, pass through."""
        other_result = 'not a ToolResult'
        call_next = AsyncMock(return_value=other_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        assert result is other_result
