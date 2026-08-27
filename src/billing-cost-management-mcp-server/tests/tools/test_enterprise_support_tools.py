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

"""Unit tests for the enterprise_support_tools module."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.enterprise_support_tools import (
    _enterprise_support,
    enterprise_support,
    enterprise_support_server,
)
from contextlib import ExitStack, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch


GET_CHARGE_SUMMARY_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.enterprise_support_tools._get_charge_summary'
)
GET_CONTRACT_DETAILS_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.enterprise_support_tools'
    '._get_contract_details'
)
LIST_LINKED_CHARGES_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.enterprise_support_tools'
    '._list_linked_account_charges'
)
SUCCESS = {'status': 'success', 'data': {}}

# Operation name to the handler it must reach, so the routing tests can be driven
# from one place rather than repeating a patch per operation in every test.
HANDLER_PATHS = {
    'get_charge_summary': GET_CHARGE_SUMMARY_PATH,
    'get_contract_details': GET_CONTRACT_DETAILS_PATH,
    'list_linked_account_charges': LIST_LINKED_CHARGES_PATH,
}


@pytest.fixture
def mock_context():
    """Create a mock MCP context with async logging methods."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


async def _registered_tool():
    """Return the registered enterprise_support tool, asserting it exists.

    Returns:
        The registered FastMCP tool.
    """
    tool = await enterprise_support_server.get_tool('enterprise_support')
    assert tool is not None
    return tool


def _await_kwargs(mock):
    """Return the keyword arguments of a mock's most recent await.

    Args:
        mock: The awaited mock to read.

    Returns:
        The keyword arguments passed to the most recent await.
    """
    assert mock.await_args is not None
    return mock.await_args.kwargs


@contextmanager
def _patched_handlers():
    """Patch every operation handler, yielding the mocks keyed by operation name.

    Entering the patches through a stack keeps each test to a single with
    statement, and keying the mocks by operation lets a test name the handler it
    expects without tracking positional bindings.

    Yields:
        Dict mapping each operation name to its patched handler mock.
    """
    mocks = {operation: AsyncMock(return_value=SUCCESS) for operation in HANDLER_PATHS}
    with ExitStack() as stack:
        for operation, path in HANDLER_PATHS.items():
            stack.enter_context(patch(path, new=mocks[operation]))
        yield mocks


class TestToolRegistration:
    """The tool is registered on the server under its expected name."""

    @pytest.mark.asyncio
    async def test_tool_is_registered(self):
        """The enterprise_support tool exists on the server."""
        tool = await _registered_tool()

        assert tool is not None

    @pytest.mark.asyncio
    async def test_description_documents_the_discount_fields(self):
        """The description keeps the guard against conflating the two discounts.

        The two discount fields are independent and were conflated during
        validation against real data, so losing this guidance is a regression
        in the tool's semantics rather than a cosmetic edit.
        """
        tool = await _registered_tool()

        assert 'supportDiscount' in (tool.description or '')
        assert 'planDiscountPercent' in (tool.description or '')


class TestOperationRouting:
    """Each operation reaches its own handler and no others."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize('operation', list(HANDLER_PATHS))
    async def test_operation_routes_to_its_own_handler(self, mock_context, operation):
        """The named operation calls only its own handler."""
        with _patched_handlers() as mocks:
            result = await _enterprise_support(mock_context, operation, billing_month='2026-06')

        assert result == SUCCESS
        mocks[operation].assert_awaited_once()
        for other, mock in mocks.items():
            if other != operation:
                mock.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'operation',
        [
            'list_charges',
            'GetEnterpriseSupportChargeSummary',
            'charge_summary',
            '',
            'delete_charge_summary',
        ],
    )
    async def test_unknown_operation_is_rejected(self, mock_context, operation):
        """An unrecognized operation returns an error without calling a handler."""
        with _patched_handlers() as mocks:
            result = await _enterprise_support(mock_context, operation)

        assert result['status'] == 'error'
        for mock in mocks.values():
            mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_operation_lists_supported_operations(self, mock_context):
        """The error names every supported operation."""
        with _patched_handlers():
            result = await _enterprise_support(mock_context, 'delete_charge_summary')

        message = result['data']['message']
        for operation in HANDLER_PATHS:
            assert operation in message


class TestParameterForwarding:
    """Parameters reach the handler that accepts them, unchanged."""

    @pytest.mark.asyncio
    async def test_billing_month_is_forwarded(self, mock_context):
        """billing_month is passed through to the handler as given."""
        with _patched_handlers() as mocks:
            await _enterprise_support(mock_context, 'get_charge_summary', billing_month='2025-03')

        assert _await_kwargs(mocks['get_charge_summary'])['billing_month'] == '2025-03'

    @pytest.mark.asyncio
    async def test_list_only_parameters_are_forwarded(self, mock_context):
        """The filter and paging arguments reach the list handler unchanged."""
        with _patched_handlers() as mocks:
            await _enterprise_support(
                mock_context,
                'list_linked_account_charges',
                billing_month='2026-06',
                account_id='111122223333',
                max_results=50,
                next_token='token',
                max_pages=2,
            )

        kwargs = _await_kwargs(mocks['list_linked_account_charges'])
        assert kwargs['account_id'] == '111122223333'
        assert kwargs['max_results'] == 50
        assert kwargs['next_token'] == 'token'
        assert kwargs['max_pages'] == 2


class TestWrapperDelegation:
    """The decorated tool delegates to the testable router."""

    @pytest.mark.asyncio
    async def test_wrapper_forwards_every_parameter(self, mock_context):
        """The FastMCP wrapper passes all parameters through to the router."""
        with _patched_handlers() as mocks:
            await enterprise_support(
                mock_context,
                'list_linked_account_charges',
                billing_month='2026-06',
                account_id='111122223333',
                max_results=25,
                next_token='token',
                max_pages=3,
            )

        kwargs = _await_kwargs(mocks['list_linked_account_charges'])
        assert kwargs['billing_month'] == '2026-06'
        assert kwargs['account_id'] == '111122223333'
        assert kwargs['max_results'] == 25
        assert kwargs['next_token'] == 'token'
        assert kwargs['max_pages'] == 3
