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


class TestArgumentValidationErrors:
    """Arguments that fail a tool's schema get the standard validation_error response."""

    @pytest.fixture
    def served(self):
        """A server with the middleware and one tool taking lists, an object and an int."""
        from fastmcp import FastMCP
        from typing import Any, Dict, List, Optional, Union

        mcp = FastMCP('argument-errors')
        mcp.add_middleware(ErrorSignalingMiddleware())

        @mcp.tool
        def probe(
            metrics: Optional[List[str]] = None,
            filter: Optional[Dict[str, Any]] = None,
            max_items: Optional[int] = None,
            ids: Optional[Union[List[str], str]] = None,
            operation: Optional[str] = None,
        ) -> dict:
            return {'status': 'success'}

        return mcp

    async def _call(self, served, args):
        from fastmcp import Client

        async with Client(served) as client:
            return await client.call_tool('probe', args, raise_on_error=False)

    @staticmethod
    def _body(result):
        """The structured content of a client result, which must be present."""
        assert result.structured_content is not None
        return result.structured_content

    @pytest.mark.asyncio
    async def test_a_wrong_type_is_a_structured_validation_error(self, served):
        """A wrong type gets error_type, retry_strategy and the parameter that failed."""
        result = await self._call(served, {'filter': '{"a": 1}'})

        assert result.is_error
        body = self._body(result)
        assert body['status'] == 'error'
        assert body['error_type'] == 'validation_error'
        assert body['retry_strategy'] == 'modify_request'
        assert body['operation'] == 'probe'
        assert body['data']['invalid_parameters'] == [
            {'parameter': 'filter', 'message': 'Input should be a valid dictionary'}
        ]
        assert body['message'] == 'Invalid arguments: filter: Input should be a valid dictionary'
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert json.loads(content.text) == body

    @pytest.mark.asyncio
    async def test_every_failing_parameter_is_listed(self, served):
        """Several bad arguments are all named, with the list index for a list item."""
        result = await self._call(
            served, {'metrics': ['Hour', 5], 'filter': '["x"]', 'max_items': 'many'}
        )

        body = self._body(result)
        params = [p['parameter'] for p in body['data']['invalid_parameters']]
        assert params == ['metrics.1', 'filter', 'max_items']
        assert 'filter: Input should be a valid dictionary' in body['message']

    @pytest.mark.asyncio
    async def test_a_long_bad_list_is_capped_and_counted(self, served):
        """Past _MAX_ARGUMENT_PROBLEMS the problems are counted, not all listed."""
        from awslabs.billing_cost_management_mcp_server.server import _MAX_ARGUMENT_PROBLEMS

        result = await self._call(served, {'metrics': list(range(_MAX_ARGUMENT_PROBLEMS + 15))})

        body = self._body(result)
        data = body['data']
        assert len(data['invalid_parameters']) == _MAX_ARGUMENT_PROBLEMS
        assert data['omitted_count'] == 15
        assert body['message'].endswith('; and 15 more')

    @pytest.mark.asyncio
    async def test_a_very_long_bad_list_is_handled_in_linear_time(self, served):
        """20,000 bad items (one pydantic error each) are counted quickly, not compared pairwise."""
        import time

        started = time.monotonic()
        result = await self._call(served, {'metrics': list(range(20_000))})

        assert self._body(result)['data']['omitted_count'] == 20_000 - 10
        assert time.monotonic() - started < 5

    @pytest.mark.asyncio
    async def test_a_union_reports_the_list_item_not_every_branch(self, served):
        """A bad list item in a list-or-string union is reported once, at the item."""
        result = await self._call(served, {'ids': [True]})

        assert self._body(result)['data']['invalid_parameters'] == [
            {'parameter': 'ids.0', 'message': 'Input should be a valid string'}
        ]

    @pytest.mark.asyncio
    async def test_an_unknown_argument_keeps_its_name(self, served):
        """The argument name is never dropped, even one that looks like a union branch tag."""
        result = await self._call(served, {'list': 1})

        assert self._body(result)['data']['invalid_parameters'] == [
            {'parameter': 'list', 'message': 'Unexpected keyword argument'}
        ]

    @pytest.mark.asyncio
    async def test_operation_is_the_requested_operation(self, served):
        """The response names the operation argument when the call has one, else the tool."""
        result = await self._call(served, {'operation': 'getCostAndUsage', 'max_items': 'x'})

        assert self._body(result)['operation'] == 'getCostAndUsage'

    @pytest.mark.asyncio
    async def test_an_echoed_operation_is_truncated(self, served):
        """A very long operation value is cut before it is echoed back."""
        result = await self._call(served, {'operation': 'o' * 5000, 'max_items': 'x'})

        assert self._body(result)['operation'] == 'o' * 100 + '...'

    @pytest.mark.asyncio
    async def test_valid_arguments_are_untouched(self, served):
        """A call that passes validation returns the tool's own result."""
        result = await self._call(served, {'metrics': ['Hour'], 'filter': {'a': 1}})

        assert not result.is_error
        assert result.structured_content == {'status': 'success'}

    @pytest.mark.asyncio
    async def test_a_validation_error_without_a_pydantic_cause_keeps_its_text(
        self, middleware, mock_context
    ):
        """An ArgumentValidationError raised without a pydantic cause still gets the contract."""
        from fastmcp.exceptions import ValidationError as ArgumentValidationError

        mock_context.message.name = 'probe'
        call_next = AsyncMock(side_effect=ArgumentValidationError('bad arguments'))

        result = await middleware.on_call_tool(mock_context, call_next)

        body = result.to_mcp_result().structured_content
        assert body['error_type'] == 'validation_error'
        assert body['data']['invalid_parameters'] == [
            {'parameter': None, 'message': 'bad arguments'}
        ]
        assert body['message'] == 'Invalid arguments: bad arguments'

        call_next = AsyncMock(side_effect=ArgumentValidationError('x' * 5000))
        result = await middleware.on_call_tool(mock_context, call_next)
        problem = result.to_mcp_result().structured_content['data']['invalid_parameters'][0]
        assert problem['message'] == 'x' * 100 + '...'


def test_parameter_path_keeps_the_argument_and_list_indexes():
    """Union branch tags (of any type) are dropped; the argument and list indexes are kept."""
    from awslabs.billing_cost_management_mcp_server.server import _parameter_path

    assert _parameter_path(('account_ids', 'list[function-before[f(), str]]', 0)) == (
        'account_ids.0'
    )
    assert _parameter_path(('account_ids', 'str')) == 'account_ids'
    assert _parameter_path(('names', 0, 'searchValue')) == 'names.0'
    assert _parameter_path(('when', 'datetime')) == 'when'
    assert _parameter_path(('x' * 500,)) == 'x' * 100 + '...'
    assert _parameter_path(('list',)) == 'list'
    assert _parameter_path(('a[0]', 'str')) == 'a[0]'
