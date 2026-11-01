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

"""Unit tests for the billing_conductor_tools module.

These tests verify the MCP tool wrappers for AWS Billing Conductor operations including
billing groups, account associations, cost reports, pricing rules/plans,
and custom line items.
"""

import asyncio
import fastmcp
import importlib
import pytest
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    billing_conductor_server,
)
from unittest.mock import AsyncMock, MagicMock, patch


# --- Constants ---

ACCOUNT_ID_PRIMARY = '123456789012'
ARN_PREFIX = f'arn:aws:billingconductor::{ACCOUNT_ID_PRIMARY}'
BILLING_GROUP_ARN_1 = f'{ARN_PREFIX}:billinggroup/abcdef1234'
PRICING_PLAN_ARN_1 = f'{ARN_PREFIX}:pricingplan/abcdef1234'
PRICING_RULE_ARN_1 = f'{ARN_PREFIX}:pricingrule/abcdef1234'
CUSTOM_LINE_ITEM_ARN_1 = f'{ARN_PREFIX}:customlineitem/abcdef1234'
BILLING_PERIOD = '2025-01'

STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'

ACCOUNT_ID_LINKED_1 = '111111111111'

PATCH_LIST_BILLING_GROUPS_OP = (
    'awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools._list_billing_groups'
)
PATCH_LIST_ACCOUNT_ASSOCIATIONS_OP = (
    'awslabs.billing_cost_management_mcp_server.tools.'
    'billing_conductor_tools._list_account_associations'
)


@pytest.fixture(scope='module', autouse=True)
def _restore_real_tool_module():
    """Reload the module with the real FastMCP.tool after this file's tests.

    _reload_bc_with_identity_decorator() leaves the module's server with no registered tools;
    restoring it keeps later test files from seeing that state.
    """
    yield
    from awslabs.billing_cost_management_mcp_server.tools import billing_conductor_tools as module

    importlib.reload(module)


def _reload_bc_with_identity_decorator():
    """Reload billing_conductor_tools with FastMCP.tool patched to return the original function.

    This exposes callable tool functions we can invoke directly to cover the routing lines.
    """
    from awslabs.billing_cost_management_mcp_server.tools import (
        billing_conductor_tools as bc_mod,
    )

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(bc_mod)
        return bc_mod


# --- Fixtures ---


@pytest.fixture
def mock_ctx():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.info = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


# --- Server Initialization Tests ---


def test_billing_conductor_server_initialization():
    """Test that the billing_conductor_server is properly initialized."""
    assert billing_conductor_server.name == 'billing-conductor-tools'

    instructions = billing_conductor_server.instructions
    assert instructions is not None
    assert 'Billing Conductor' in instructions if instructions else False


def test_list_billing_groups_tool_registered():
    """Test that the list_billing_groups tool is registered with proper name."""
    tool = asyncio.run(billing_conductor_server.get_tool('list-billing-groups'))
    assert tool is not None
    assert tool.name == 'list-billing-groups'


def test_list_account_associations_tool_registered():
    """Test that the list_account_associations tool is registered with proper name."""
    tool = asyncio.run(billing_conductor_server.get_tool('list-account-associations'))
    assert tool is not None
    assert tool.name == 'list-account-associations'


def _description(tool_name):
    tool = asyncio.run(billing_conductor_server.get_tool(tool_name))
    assert tool is not None
    return ' '.join((tool.description or '').split())


def test_list_billing_groups_describes_filter_limits():
    """Names takes one case-sensitive prefix, Statuses at most 2, PricingPlan a full ARN."""
    description = _description('list-billing-groups')
    assert 'Names: exactly one name search, a case-sensitive prefix match' in description
    assert 'Statuses: at most 2 of ACTIVE, PRIMARY_ACCOUNT_MISSING, PENDING' in description
    assert 'PricingPlan: a full pricing plan ARN' in description
    assert 'supports STARTS_WITH search' not in description
    assert 'validation_error' not in description


def test_list_account_associations_describes_filter_rules():
    """AccountId and AccountIds exclude each other, and Association takes a full ARN."""
    description = _description('list-account-associations')
    assert 'Use AccountId or AccountIds, not both' in description
    assert 'A full billing group ARN' in description
    assert 'MONITORED and UNMONITORED are upper case' in description
    assert 'bare billing group ID' not in description
    assert 'validation_error' not in description


def test_get_billing_group_cost_report_describes_period_defaults():
    """No range means the current month to date; the end is exclusive; months sum without BILLING_PERIOD."""
    description = _description('get-billing-group-cost-report')
    assert 'Without it, the report covers only the current month, month-to-date' in description
    assert 'The end month is excluded' in description
    assert 'Include BILLING_PERIOD in GroupBy to get one row per month' in description
    assert 'the months of a range are summed' in description
    assert 'BILLING_PERIOD: "2025-01"' in description
    assert 'Nov 2023' not in description


def test_list_billing_group_cost_reports_tool_registered():
    """Test that the list_billing_group_cost_reports tool is registered."""
    tool = asyncio.run(billing_conductor_server.get_tool('list-billing-group-cost-reports'))
    assert tool is not None
    assert tool.name == 'list-billing-group-cost-reports'


def test_get_billing_group_cost_report_tool_registered():
    """Test that the get_billing_group_cost_report tool is registered."""
    tool = asyncio.run(billing_conductor_server.get_tool('get-billing-group-cost-report'))
    assert tool is not None
    assert tool.name == 'get-billing-group-cost-report'


def test_get_billing_group_cost_report_describes_page_sizes():
    """The description gives the 200-300 page size and what it means for a small max_items."""
    tool = asyncio.run(billing_conductor_server.get_tool('get-billing-group-cost-report'))
    assert tool is not None
    description = ' '.join((tool.description or '').split())
    assert 'Results come in pages of up to 300' in description
    assert 'a `max_items` below 200 can return up to 200' in description


@pytest.mark.parametrize(
    'tool_name', ['list-billing-group-cost-reports', 'get-billing-group-cost-report']
)
def test_cost_report_descriptions_state_margin_sign_and_unit(tool_name):
    """Margin is proforma minus AWS cost, and margin percentage is a fraction, not a percent."""
    tool = asyncio.run(billing_conductor_server.get_tool(tool_name))
    assert tool is not None
    description = ' '.join((tool.description or '').split())
    assert (
        'Margin (proforma cost minus AWS cost; negative means the proforma cost is below'
        in description
    )
    assert 'as a fraction, not a percent: -0.25 means -25%' in description
    assert '"0.0" when the AWS cost is 0' in description
    assert 'percentage of billing group margin' not in description


@pytest.mark.parametrize(
    'tool_name', ['list-billing-group-cost-reports', 'get-billing-group-cost-report']
)
def test_cost_report_descriptions_say_how_to_read_amount_strings(tool_name):
    """Amounts are strings that can use exponent form; decimal_values gives them plain."""
    tool = asyncio.run(billing_conductor_server.get_tool(tool_name))
    assert tool is not None
    description = ' '.join((tool.description or '').split())
    assert 'exponent form ("5.0E-7")' in description
    assert '`decimal_values`' in description
    assert 'MONETARY AMOUNTS ARE STRINGS' in description
    assert 'parse them as decimals, never floats' in description


def test_list_pricing_rules_tool_registered():
    """Test that the list_pricing_rules tool is registered."""
    tool = asyncio.run(billing_conductor_server.get_tool('list-pricing-rules'))
    assert tool is not None
    assert tool.name == 'list-pricing-rules'


def test_list_pricing_plans_tool_registered():
    """Test that the list_pricing_plans tool is registered."""
    tool = asyncio.run(billing_conductor_server.get_tool('list-pricing-plans'))
    assert tool is not None
    assert tool.name == 'list-pricing-plans'


def test_get_billing_transfer_preference_tool_registered():
    """Test that the get_billing_transfer_preference tool is registered."""
    tool = asyncio.run(billing_conductor_server.get_tool('get-billing-transfer-preference'))
    assert tool is not None
    assert tool.name == 'get-billing-transfer-preference'
    assert 'responsibility_transfer_arn' in tool.parameters.get('required', [])


def test_list_custom_line_items_tool_registered():
    """Test that the list_custom_line_items tool is registered."""
    tool = asyncio.run(billing_conductor_server.get_tool('list-custom-line-items'))
    assert tool is not None
    assert tool.name == 'list-custom-line-items'


# --- List Billing Groups Tool Tests ---


@pytest.mark.asyncio
class TestListBillingGroupsTool:
    """Tests for the list_billing_groups MCP tool wrapper."""

    async def test_list_billing_groups_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_billing_groups  # type: ignore

        with patch.object(bc_mod, '_list_billing_groups', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_groups': [{'arn': BILLING_GROUP_ARN_1, 'name': 'TestGroup'}],
                    'total_count': 1,
                    'billing_period': 'current',
                },
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['total_count'] == 1
            mock_op.assert_awaited_once_with(mock_ctx, None, None, None, None)

    async def test_list_billing_groups_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_billing_groups  # type: ignore

        with patch.object(bc_mod, '_list_billing_groups', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_groups': [],
                    'total_count': 0,
                    'billing_period': BILLING_PERIOD,
                },
            }

            filters_str = '{"Statuses": ["ACTIVE"]}'
            result = await real_fn(  # type: ignore
                mock_ctx,
                billing_period=BILLING_PERIOD,
                filters=filters_str,
                max_items=5,
                next_token='tok123',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_PERIOD, filters_str, 5, 'tok123')

    async def test_list_billing_groups_handles_operation_error(self, mock_ctx):
        """Test that errors from the operation are returned properly."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_billing_groups  # type: ignore

        with patch.object(bc_mod, '_list_billing_groups', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_ERROR,
                'error_type': 'AccessDeniedException',
                'message': 'You do not have sufficient access',
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR

    async def test_list_billing_groups_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_billing_groups  # type: ignore

        with (
            patch.object(bc_mod, '_list_billing_groups', new_callable=AsyncMock) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('Unexpected error')
            mock_handle.return_value = {
                'status': STATUS_ERROR,
                'message': 'Unexpected error',
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Billing Group Cost Reports Tool Tests ---


@pytest.mark.asyncio
class TestListBillingGroupCostReportsTool:
    """Tests for the list_billing_group_cost_reports MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_billing_group_cost_reports  # type: ignore

        with patch.object(
            bc_mod, '_list_billing_group_cost_reports', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_group_cost_reports': [],
                    'total_count': 0,
                    'billing_period': 'current',
                },
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, None, None, None, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_billing_group_cost_reports  # type: ignore

        with patch.object(
            bc_mod, '_list_billing_group_cost_reports', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            filters_str = '{"BillingGroupArns": ["arn:test"]}'
            await real_fn(  # type: ignore
                mock_ctx,
                billing_period=BILLING_PERIOD,
                filters=filters_str,
                max_items=2,
                next_token='tok',
            )

            mock_op.assert_awaited_once_with(mock_ctx, BILLING_PERIOD, filters_str, 2, 'tok')

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_billing_group_cost_reports  # type: ignore

        with (
            patch.object(
                bc_mod, '_list_billing_group_cost_reports', new_callable=AsyncMock
            ) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- Get Billing Group Cost Report Tool Tests ---


@pytest.mark.asyncio
class TestGetBillingGroupCostReportTool:
    """Tests for the get_billing_group_cost_report MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.get_billing_group_cost_report  # type: ignore

        with patch.object(
            bc_mod, '_get_billing_group_cost_report', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_group_cost_report_results': [],
                    'total_count': 0,
                    'arn': BILLING_GROUP_ARN_1,
                },
            }

            result = await real_fn(mock_ctx, arn=BILLING_GROUP_ARN_1)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_GROUP_ARN_1, None, None, None, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.get_billing_group_cost_report  # type: ignore

        with patch.object(
            bc_mod, '_get_billing_group_cost_report', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            range_str = '{"InclusiveStartBillingPeriod": "2025-01"}'
            group_by_str = '["PRODUCT_NAME"]'
            await real_fn(  # type: ignore
                mock_ctx,
                arn=BILLING_GROUP_ARN_1,
                billing_period_range=range_str,
                group_by=group_by_str,
                max_items=3,
                next_token='tok',
            )

            mock_op.assert_awaited_once_with(
                mock_ctx, BILLING_GROUP_ARN_1, range_str, group_by_str, 3, 'tok'
            )

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.get_billing_group_cost_report  # type: ignore

        with (
            patch.object(
                bc_mod, '_get_billing_group_cost_report', new_callable=AsyncMock
            ) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx, arn=BILLING_GROUP_ARN_1)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Pricing Rules Tool Tests ---


@pytest.mark.asyncio
class TestListPricingRulesTool:
    """Tests for the list_pricing_rules MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_rules  # type: ignore

        with patch.object(bc_mod, '_list_pricing_rules', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'pricing_rules': [], 'total_count': 0, 'billing_period': 'current'},
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, None, None, None, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_rules  # type: ignore

        with patch.object(bc_mod, '_list_pricing_rules', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            await real_fn(  # type: ignore
                mock_ctx, billing_period=BILLING_PERIOD, filters='{}', max_items=2, next_token='t'
            )

            mock_op.assert_awaited_once_with(mock_ctx, BILLING_PERIOD, '{}', 2, 't')

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_rules  # type: ignore

        with (
            patch.object(bc_mod, '_list_pricing_rules', new_callable=AsyncMock) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Pricing Plans Tool Tests ---


@pytest.mark.asyncio
class TestListPricingPlansTool:
    """Tests for the list_pricing_plans MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_plans  # type: ignore

        with patch.object(bc_mod, '_list_pricing_plans', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'pricing_plans': [], 'total_count': 0, 'billing_period': 'current'},
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, None, None, None, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_plans  # type: ignore

        with patch.object(bc_mod, '_list_pricing_plans', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            await real_fn(  # type: ignore
                mock_ctx, billing_period=BILLING_PERIOD, filters='{}', max_items=3, next_token='x'
            )

            mock_op.assert_awaited_once_with(mock_ctx, BILLING_PERIOD, '{}', 3, 'x')

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_plans  # type: ignore

        with (
            patch.object(bc_mod, '_list_pricing_plans', new_callable=AsyncMock) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Pricing Rules for Plan Tool Tests ---


@pytest.mark.asyncio
class TestListPricingRulesForPlanTool:
    """Tests for the list_pricing_rules_associated_to_pricing_plan MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_rules_associated_to_pricing_plan  # type: ignore

        with patch.object(bc_mod, '_list_rules_for_plan', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'pricing_rule_arns': [PRICING_RULE_ARN_1], 'total_count': 1},
            }

            result = await real_fn(mock_ctx, pricing_plan_arn=PRICING_PLAN_ARN_1)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, PRICING_PLAN_ARN_1, None, None, None)

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_rules_associated_to_pricing_plan  # type: ignore

        with (
            patch.object(bc_mod, '_list_rules_for_plan', new_callable=AsyncMock) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx, pricing_plan_arn=PRICING_PLAN_ARN_1)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Pricing Plans for Rule Tool Tests ---


@pytest.mark.asyncio
class TestListPricingPlansForRuleTool:
    """Tests for the list_pricing_plans_associated_with_pricing_rule MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_plans_associated_with_pricing_rule  # type: ignore

        with patch.object(bc_mod, '_list_plans_for_rule', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'pricing_plan_arns': [PRICING_PLAN_ARN_1], 'total_count': 1},
            }

            result = await real_fn(mock_ctx, pricing_rule_arn=PRICING_RULE_ARN_1)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, PRICING_RULE_ARN_1, None, None, None)

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_plans_associated_with_pricing_rule  # type: ignore

        with (
            patch.object(bc_mod, '_list_plans_for_rule', new_callable=AsyncMock) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx, pricing_rule_arn=PRICING_RULE_ARN_1)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Custom Line Items Tool Tests ---


@pytest.mark.asyncio
class TestListCustomLineItemsTool:
    """Tests for the list_custom_line_items MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_custom_line_items  # type: ignore

        with patch.object(bc_mod, '_list_custom_line_items', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'custom_line_items': [], 'total_count': 0, 'billing_period': 'current'},
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, None, None, None, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_custom_line_items  # type: ignore

        with patch.object(bc_mod, '_list_custom_line_items', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            await real_fn(  # type: ignore
                mock_ctx, billing_period=BILLING_PERIOD, filters='{}', max_items=5, next_token='n'
            )

            mock_op.assert_awaited_once_with(mock_ctx, BILLING_PERIOD, '{}', 5, 'n')

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_custom_line_items  # type: ignore

        with (
            patch.object(bc_mod, '_list_custom_line_items', new_callable=AsyncMock) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Custom Line Item Versions Tool Tests ---


@pytest.mark.asyncio
class TestListCustomLineItemVersionsTool:
    """Tests for the list_custom_line_item_versions MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_custom_line_item_versions  # type: ignore

        with patch.object(
            bc_mod, '_list_custom_line_item_versions', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'custom_line_item_versions': [], 'total_count': 0},
            }

            result = await real_fn(mock_ctx, arn=CUSTOM_LINE_ITEM_ARN_1)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, CUSTOM_LINE_ITEM_ARN_1, None, None, None)

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_custom_line_item_versions  # type: ignore

        with (
            patch.object(
                bc_mod, '_list_custom_line_item_versions', new_callable=AsyncMock
            ) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx, arn=CUSTOM_LINE_ITEM_ARN_1)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Resources Associated to Custom Line Item Tool Tests ---


@pytest.mark.asyncio
class TestListResourcesAssociatedToCustomLineItemTool:
    """Tests for the list_resources_associated_to_custom_line_item MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_resources_associated_to_custom_line_item  # type: ignore

        with patch.object(
            bc_mod, '_list_resources_associated_to_cli', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'associated_resources': [], 'total_count': 0},
            }

            result = await real_fn(mock_ctx, arn=CUSTOM_LINE_ITEM_ARN_1)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx, CUSTOM_LINE_ITEM_ARN_1, None, None, None, None
            )

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_resources_associated_to_custom_line_item  # type: ignore

        with (
            patch.object(
                bc_mod, '_list_resources_associated_to_cli', new_callable=AsyncMock
            ) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(mock_ctx, arn=CUSTOM_LINE_ITEM_ARN_1)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- List Account Associations Tool Tests ---


@pytest.mark.asyncio
class TestListAccountAssociationsTool:
    """Tests for the list_account_associations MCP tool wrapper."""

    async def test_list_account_associations_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_account_associations  # type: ignore

        with patch.object(bc_mod, '_list_account_associations', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'linked_accounts': [
                        {'account_id': ACCOUNT_ID_LINKED_1, 'account_name': 'Dev'}
                    ],
                    'total_count': 1,
                    'billing_period': 'current',
                },
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['total_count'] == 1
            mock_op.assert_awaited_once_with(mock_ctx, None, None, None, None)

    async def test_list_account_associations_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_account_associations  # type: ignore

        with patch.object(bc_mod, '_list_account_associations', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'linked_accounts': [],
                    'total_count': 0,
                    'billing_period': BILLING_PERIOD,
                },
            }

            filters_str = '{"Association": "MONITORED"}'
            result = await real_fn(  # type: ignore
                mock_ctx,
                billing_period=BILLING_PERIOD,
                filters=filters_str,
                max_items=3,
                next_token='tok456',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_PERIOD, filters_str, 3, 'tok456')

    async def test_list_account_associations_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_account_associations  # type: ignore

        with (
            patch.object(bc_mod, '_list_account_associations', new_callable=AsyncMock) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('Unexpected error')
            mock_handle.return_value = {
                'status': STATUS_ERROR,
                'message': 'Unexpected error',
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


# --- Get Billing Transfer Preference Tool Tests ---


@pytest.mark.asyncio
class TestGetBillingTransferPreferenceTool:
    """Tests for the get_billing_transfer_preference MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.get_billing_transfer_preference  # type: ignore
        transfer_arn = (
            'arn:aws:organizations::123456789012:transfer/o-abc123/billing/inbound/rt-12345678'
        )

        with patch.object(
            bc_mod, '_get_billing_transfer_preference', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'responsibility_transfer_arn': transfer_arn},
            }

            result = await real_fn(mock_ctx, responsibility_transfer_arn=transfer_arn)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, transfer_arn)

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.get_billing_transfer_preference  # type: ignore

        with (
            patch.object(
                bc_mod, '_get_billing_transfer_preference', new_callable=AsyncMock
            ) as mock_op,
            patch.object(bc_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await real_fn(  # type: ignore
                mock_ctx, responsibility_transfer_arn='arn:example'
            )

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_tool_schemas_follow_the_max_items_contract():
    """Every paginated conductor tool takes max_items + next_token; the get-preference tool neither."""
    from awslabs.billing_cost_management_mcp_server.tools import billing_conductor_tools as bct

    # Other tests reload this module under a patched FastMCP; reload the real one here.
    real = importlib.reload(bct)
    tools = {t.name: t for t in await real.billing_conductor_server.list_tools()}
    assert len(tools) == 12
    for name, tool in tools.items():
        params = set(tool.parameters['properties'])
        assert not {'max_pages', 'max_results', 'page_size'} & params, name
        if name == 'get-billing-transfer-preference':
            assert not {'max_items', 'next_token'} & params
        else:
            assert {'max_items', 'next_token'} <= params, name
            assert 'max_items' in tool.description, name


@pytest.mark.asyncio
async def test_descriptions_state_future_billing_period_behavior():
    """Each tool that takes a billing period says what a month after the current one does."""
    from awslabs.billing_cost_management_mcp_server.tools import billing_conductor_tools as bct

    # Other tests reload this module under a patched FastMCP; reload the real one here.
    real = importlib.reload(bct)
    tools = {t.name: t for t in await real.billing_conductor_server.list_tools()}
    rejected = {'list-billing-group-cost-reports', 'get-billing-group-cost-report'}
    projected = {
        name
        for name, tool in tools.items()
        if 'billing_period' in tool.parameters['properties'] and name not in rejected
    }
    assert len(projected) == 8, 'a new tool takes billing_period: add it to the checks below'
    for name in projected:
        description = ' '.join((tools[name].description or '').split())
        assert 'after the current month (UTC) is a projection, not a record' in description, name
        assert '`billing_period_is_future: true`' in description, name
    for name in rejected:
        description = ' '.join((tools[name].description or '').split())
        assert 'after the current month (UTC) fails with validation_error' in description, name


@pytest.mark.asyncio
async def test_descriptions_state_past_month_with_nothing_in_effect():
    """Tools that answer a month with nothing in effect predictably say so; the rest stay silent."""
    from awslabs.billing_cost_management_mcp_server.tools import billing_conductor_tools as bct

    # Other tests reload this module under a patched FastMCP; reload the real one here.
    real = importlib.reload(bct)
    tools = {t.name: t for t in await real.billing_conductor_server.list_tools()}
    expected = {
        'list-billing-group-cost-reports': (
            'A past month with no billing group in effect returns an empty list, not an error.'
        ),
        'get-billing-group-cost-report': (
            'A range with no data for the billing group (for example, months before it took '
            'effect) returns no results, not an error.'
        ),
        'list-resources-associated-to-custom-line-item': (
            'was not in effect (before it started or after it ended) fails with '
            'ResourceNotFoundException ("Custom line item does not exist."), not an empty list. '
            'A mistyped ARN can return the same error: confirm the ARN with list-custom-line-items'
            ' for a recent month.'
        ),
        'list-pricing-rules-for-plan': (
            'fails with ResourceNotFoundException ("Pricing plan does not exist."), not an empty '
            'list. A mistyped ARN can return the same error: confirm the ARN with list-pricing-plans'
            ' for a recent month.'
        ),
        'list-pricing-plans-for-rule': (
            'fails with ResourceNotFoundException ("Pricing rule does not exist."), not an empty '
            'list. A mistyped ARN can return the same error: confirm the ARN with list-pricing-rules'
            ' for a recent month.'
        ),
    }
    for name, text in expected.items():
        description = ' '.join((tools[name].description or '').split())
        assert text in description, name
    # These lists can be non-empty for a month with nothing in effect (very old months return
    # historical records), or list the payer's linked accounts, so they make no such claim.
    for name in set(tools) - set(expected):
        description = ' '.join((tools[name].description or '').split())
        assert 'returns an empty list' not in description, name
        assert 'returns no results, not an error' not in description, name
