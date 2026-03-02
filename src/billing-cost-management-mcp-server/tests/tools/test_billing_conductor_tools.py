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

import fastmcp
import importlib
import pytest
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    billing_conductor_server,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    get_billing_group_cost_report as get_billing_group_cost_report_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    list_account_associations as list_account_associations_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    list_billing_group_cost_reports as list_billing_group_cost_reports_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    list_billing_groups as list_billing_groups_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    list_custom_line_items as list_custom_line_items_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    list_pricing_plans as list_pricing_plans_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_tools import (
    list_pricing_rules as list_pricing_rules_tool,
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
    assert hasattr(list_billing_groups_tool, 'name')
    assert list_billing_groups_tool.name == 'list-billing-groups'


def test_list_account_associations_tool_registered():
    """Test that the list_account_associations tool is registered with proper name."""
    assert hasattr(list_account_associations_tool, 'name')
    assert list_account_associations_tool.name == 'list-account-associations'


def test_list_billing_group_cost_reports_tool_registered():
    """Test that the list_billing_group_cost_reports tool is registered."""
    assert hasattr(list_billing_group_cost_reports_tool, 'name')
    assert list_billing_group_cost_reports_tool.name == 'list-billing-group-cost-reports'


def test_get_billing_group_cost_report_tool_registered():
    """Test that the get_billing_group_cost_report tool is registered."""
    assert hasattr(get_billing_group_cost_report_tool, 'name')
    assert get_billing_group_cost_report_tool.name == 'get-billing-group-cost-report'


def test_list_pricing_rules_tool_registered():
    """Test that the list_pricing_rules tool is registered."""
    assert hasattr(list_pricing_rules_tool, 'name')
    assert list_pricing_rules_tool.name == 'list-pricing-rules'


def test_list_pricing_plans_tool_registered():
    """Test that the list_pricing_plans tool is registered."""
    assert hasattr(list_pricing_plans_tool, 'name')
    assert list_pricing_plans_tool.name == 'list-pricing-plans'


def test_list_custom_line_items_tool_registered():
    """Test that the list_custom_line_items tool is registered."""
    assert hasattr(list_custom_line_items_tool, 'name')
    assert list_custom_line_items_tool.name == 'list-custom-line-items'


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
            mock_op.assert_awaited_once_with(mock_ctx, None, None, 10, None)

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
                max_pages=5,
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
            mock_op.assert_awaited_once_with(mock_ctx, None, None, 10, None)

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
                max_pages=2,
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
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_GROUP_ARN_1, None, None, 10, None)

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
                max_pages=3,
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
            mock_op.assert_awaited_once_with(mock_ctx, None, None, 10, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_rules  # type: ignore

        with patch.object(bc_mod, '_list_pricing_rules', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            await real_fn(  # type: ignore
                mock_ctx, billing_period=BILLING_PERIOD, filters='{}', max_pages=2, next_token='t'
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
            mock_op.assert_awaited_once_with(mock_ctx, None, None, 10, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_pricing_plans  # type: ignore

        with patch.object(bc_mod, '_list_pricing_plans', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            await real_fn(  # type: ignore
                mock_ctx, billing_period=BILLING_PERIOD, filters='{}', max_pages=3, next_token='x'
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
            mock_op.assert_awaited_once_with(mock_ctx, PRICING_PLAN_ARN_1, None, None, 10, None)

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
            mock_op.assert_awaited_once_with(mock_ctx, PRICING_RULE_ARN_1, None, None, 10, None)

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
            mock_op.assert_awaited_once_with(mock_ctx, None, None, 10, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through."""
        bc_mod = _reload_bc_with_identity_decorator()
        real_fn = bc_mod.list_custom_line_items  # type: ignore

        with patch.object(bc_mod, '_list_custom_line_items', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}

            await real_fn(  # type: ignore
                mock_ctx, billing_period=BILLING_PERIOD, filters='{}', max_pages=5, next_token='n'
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
            mock_op.assert_awaited_once_with(mock_ctx, CUSTOM_LINE_ITEM_ARN_1, None, 10, None)

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
                mock_ctx, CUSTOM_LINE_ITEM_ARN_1, None, None, 10, None
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
            mock_op.assert_awaited_once_with(mock_ctx, None, None, 10, None)

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
                max_pages=3,
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
