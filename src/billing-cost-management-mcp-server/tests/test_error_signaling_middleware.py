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

import json
import pytest
from awslabs.billing_cost_management_mcp_server.server import (
    ErrorSignalingMiddleware,
    _ErrorToolResult,
)
from fastmcp.tools import ToolResult
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
        """When a tool returns status='error', is_error should be True."""
        error_result = ToolResult(
            structured_content={'status': 'error', 'message': 'Access denied'},
        )
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        assert isinstance(result, _ErrorToolResult)
        mcp_result = result.to_mcp_result()
        assert isinstance(mcp_result, CallToolResult)
        assert mcp_result.is_error is True
        assert mcp_result.structured_content == {
            'status': 'error',
            'message': 'Access denied',
            'retry_strategy': 'do_not_retry',
        }

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
    async def test_error_response_preserves_fields(self, middleware, mock_context):
        """Error response should keep every original field alongside the retry guidance."""
        original = {
            'status': 'error',
            'error_type': 'validation_error',
            'message': 'Invalid date format',
            'service': 'Cost Explorer',
            'operation': 'getCostAndUsage',
        }
        error_result = ToolResult(structured_content=original)
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        mcp_result = result.to_mcp_result()
        assert mcp_result.is_error is True
        assert mcp_result.structured_content.items() >= original.items()
        assert mcp_result.structured_content['retry_strategy'] == 'modify_request'
        assert 'hint' in mcp_result.structured_content

    @pytest.mark.asyncio
    async def test_error_content_text_matches_structured_content(self, middleware, mock_context):
        """The text block the model reads should carry the same fields as structured_content."""
        error_result = ToolResult(
            structured_content={
                'status': 'error',
                'error_type': 'ThrottlingException',
                'message': 'Rate exceeded',
            },
        )
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        mcp_result = result.to_mcp_result()
        assert len(mcp_result.content) == 1
        assert json.loads(mcp_result.content[0].text) == mcp_result.structured_content
        assert mcp_result.structured_content['retry_strategy'] == 'retry_same_request'

    @pytest.mark.asyncio
    async def test_error_custom_content_preserved(self, middleware, mock_context):
        """Content that is not the serialized structured_content should be left as-is."""
        custom = [TextContent(type='text', text='Custom error summary')]
        error_result = ToolResult(
            content=custom,
            structured_content={'status': 'error', 'error_type': 'access_denied'},
        )
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        mcp_result = result.to_mcp_result()
        assert mcp_result.content == custom
        assert mcp_result.structured_content['retry_strategy'] == 'do_not_retry'

    @pytest.mark.asyncio
    async def test_error_tool_override_kept(self, middleware, mock_context):
        """A retry_strategy and hint set by the tool should not be replaced."""
        original = {
            'status': 'error',
            'error_type': 'validation_error',
            'retry_strategy': 'do_not_retry',
            'hint': 'Ask the user to pick a supported region.',
        }
        error_result = ToolResult(structured_content=original)
        call_next = AsyncMock(return_value=error_result)

        result = await middleware.on_call_tool(mock_context, call_next)

        mcp_result = result.to_mcp_result()
        assert mcp_result.is_error is True
        assert mcp_result.structured_content == original
        assert mcp_result.content == error_result.content

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
        assert mcp_result.is_error is True
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


class TestErrorSignalingEndToEnd:
    """Runs a real tool through FastMCP so the content check sees what tools actually return."""

    @pytest.mark.asyncio
    async def test_dict_error_from_tool_carries_retry_guidance(self):
        """A tool's dict error reaches the client with is_error and matching text content."""
        from fastmcp import Client, FastMCP

        server = FastMCP(name='test')
        server.add_middleware(ErrorSignalingMiddleware())

        @server.tool
        def failing_tool() -> dict:
            return {'status': 'error', 'error_type': 'ThrottlingException', 'message': 'slow'}

        async with Client(server) as client:
            result = await client.call_tool('failing_tool', raise_on_error=False)

        assert result.is_error is True
        assert result.structured_content is not None
        assert result.structured_content['retry_strategy'] == 'retry_same_request'
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert json.loads(content.text) == result.structured_content
