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

"""Unit tests for the credits_tools module."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.credits_tools import (
    _credits,
    credits,
    credits_server,
)
from unittest.mock import AsyncMock, MagicMock, patch


GET_CREDITS_PATH = 'awslabs.billing_cost_management_mcp_server.tools.credits_tools._get_credits'
GET_CREDIT_ALLOCATION_HISTORY_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.credits_tools._get_credit_allocation_history'
)
SUCCESS = {'status': 'success', 'data': {}}


@pytest.fixture
def mock_context():
    """Create a mock MCP context with async logging methods."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


def _await_kwargs(mock):
    """Return the keyword arguments of a mock's most recent await."""
    assert mock.await_args is not None
    return mock.await_args.kwargs


async def _registered_tool():
    """Return the registered credits tool, asserting it exists."""
    tool = await credits_server.get_tool('credits')
    assert tool is not None
    return tool


def _handlers():
    """Patch both operation handlers, yielding the two mocks."""
    return patch(GET_CREDITS_PATH, new=AsyncMock(return_value=SUCCESS)), patch(
        GET_CREDIT_ALLOCATION_HISTORY_PATH, new=AsyncMock(return_value=SUCCESS)
    )


class TestOperationRouting:
    """Each operation reaches its own handler."""

    @pytest.mark.asyncio
    async def test_get_credits_routes_to_handler(self, mock_context):
        """The get_credits operation calls the credits handler only."""
        credits_patch, history_patch = _handlers()
        with credits_patch as credits_mock, history_patch as history_mock:
            result = await _credits(mock_context, 'get_credits', start_date='2026-01-01')

        assert result == SUCCESS
        credits_mock.assert_awaited_once()
        history_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_credit_allocation_history_routes_to_handler(self, mock_context):
        """The allocation-history operation calls the ledger handler only."""
        credits_patch, history_patch = _handlers()
        with credits_patch as credits_mock, history_patch as history_mock:
            result = await _credits(
                mock_context, 'get_credit_allocation_history', billing_period='2026-06'
            )

        assert result == SUCCESS
        history_mock.assert_awaited_once()
        credits_mock.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'operation', ['get_invoices', 'GetCredits', 'delete_credits', '', 'get_credit']
    )
    async def test_unknown_operation_is_rejected(self, mock_context, operation):
        """An unrecognized operation returns an error without calling a handler."""
        credits_patch, history_patch = _handlers()
        with credits_patch as credits_mock, history_patch as history_mock:
            result = await _credits(mock_context, operation)

        assert result['status'] == 'error'
        credits_mock.assert_not_awaited()
        history_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_operation_lists_supported_operations(self, mock_context):
        """The error names both supported operations."""
        credits_patch, history_patch = _handlers()
        with credits_patch, history_patch:
            result = await _credits(mock_context, 'get_invoices')

        message = result['data']['message']
        assert 'get_credits' in message
        assert 'get_credit_allocation_history' in message


class TestParameterForwarding:
    """Only the parameters an operation accepts are forwarded to it."""

    @pytest.mark.asyncio
    async def test_credits_receives_its_own_parameters(self, mock_context):
        """get_credits receives payer_account_flag and the date window."""
        credits_patch, history_patch = _handlers()
        with credits_patch as credits_mock, history_patch:
            await _credits(
                mock_context,
                'get_credits',
                start_date='2026-01-01',
                end_date='2026-06-30',
                account_id='123456789012',
                payer_account_flag=True,
            )

        kwargs = _await_kwargs(credits_mock)
        assert kwargs['start_date'] == '2026-01-01'
        assert kwargs['end_date'] == '2026-06-30'
        assert kwargs['account_id'] == '123456789012'
        assert kwargs['payer_account_flag'] is True

    @pytest.mark.asyncio
    async def test_credits_does_not_receive_ledger_parameters(self, mock_context):
        """Ledger-only parameters are never forwarded to get_credits."""
        credits_patch, history_patch = _handlers()
        with credits_patch as credits_mock, history_patch:
            await _credits(
                mock_context,
                'get_credits',
                start_date='2026-01-01',
                credit_id='4242',
                billing_period='2026-06',
                max_results=50,
                next_token='token',
                max_pages=2,
            )

        kwargs = _await_kwargs(credits_mock)
        for name in ('credit_id', 'billing_period', 'max_results', 'next_token', 'max_pages'):
            assert name not in kwargs

    @pytest.mark.asyncio
    async def test_get_credit_allocation_history_receives_its_own_parameters(self, mock_context):
        """Allocation history receives billing_period, credit_id and paging controls."""
        credits_patch, history_patch = _handlers()
        with credits_patch, history_patch as history_mock:
            await _credits(
                mock_context,
                'get_credit_allocation_history',
                billing_period='2026-06',
                credit_id='4242',
                max_results=50,
                next_token='token',
                max_pages=3,
            )

        kwargs = _await_kwargs(history_mock)
        assert kwargs['billing_period'] == '2026-06'
        assert kwargs['credit_id'] == '4242'
        assert kwargs['max_results'] == 50
        assert kwargs['next_token'] == 'token'
        assert kwargs['max_pages'] == 3

    @pytest.mark.asyncio
    async def test_get_credit_allocation_history_does_not_receive_payer_account_flag(
        self, mock_context
    ):
        """payer_account_flag is never forwarded to allocation history."""
        credits_patch, history_patch = _handlers()
        with credits_patch, history_patch as history_mock:
            await _credits(
                mock_context,
                'get_credit_allocation_history',
                billing_period='2026-06',
                payer_account_flag=True,
            )

        assert 'payer_account_flag' not in _await_kwargs(history_mock)


class TestWrapperDelegation:
    """The decorated tool delegates to the testable router."""

    @pytest.mark.asyncio
    async def test_wrapper_forwards_every_parameter(self, mock_context):
        """The FastMCP wrapper passes all parameters through to the router."""
        credits_patch, history_patch = _handlers()
        with credits_patch, history_patch as history_mock:
            await credits(
                mock_context,
                'get_credit_allocation_history',
                billing_period='2026-06',
                account_id='123456789012',
                credit_id='4242',
                max_results=10,
                next_token='token',
                max_pages=1,
            )

        kwargs = _await_kwargs(history_mock)
        assert kwargs['billing_period'] == '2026-06'
        assert kwargs['account_id'] == '123456789012'
        assert kwargs['credit_id'] == '4242'


class TestToolRegistration:
    """The tool is registered on the sub-server with a usable description."""

    @pytest.mark.asyncio
    async def test_tool_is_registered(self):
        """A tool named credits is registered on the sub-server."""
        tool = await _registered_tool()

        assert tool.name == 'credits'

    @pytest.mark.asyncio
    async def test_description_documents_both_operations(self):
        """The description names both operations and their required parameters."""
        tool = await _registered_tool()

        assert 'get_credits' in (tool.description or '')
        assert 'get_credit_allocation_history' in (tool.description or '')
        assert 'billing_period' in (tool.description or '')

    @pytest.mark.asyncio
    async def test_description_carries_response_guardrails(self):
        """The description warns about completeness, clamping and precision."""
        tool = await _registered_tool()

        assert 'partial_results' in (tool.description or '')
        assert 'narrowed_from_request' in (tool.description or '')
        assert 'one year before today' in (tool.description or '')
        assert 'never floats' in (tool.description or '')
