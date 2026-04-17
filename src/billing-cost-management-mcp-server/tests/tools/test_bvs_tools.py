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

"""Unit tests for the bvs_tools module.

These tests verify the MCP tool wrappers for AWS Billing operations
including retrieving billing view metadata, listing billing views, listing source views,
and retrieving resource-based policies.
"""

import fastmcp
import importlib
import pytest
from awslabs.billing_cost_management_mcp_server.tools.bvs_tools import (
    bvs_server,
)
from awslabs.billing_cost_management_mcp_server.tools.bvs_tools import (
    get_billing_view as get_billing_view_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.bvs_tools import (
    get_resource_policy as get_resource_policy_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.bvs_tools import (
    list_billing_views as list_billing_views_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.bvs_tools import (
    list_source_views_for_billing_view as list_source_views_for_billing_view_tool,
)
from unittest.mock import AsyncMock, MagicMock, patch


# --- Constants ---

ACCOUNT_ID_PRIMARY = '123456789012'
BVS_ARN_PREFIX = f'arn:aws:billing::{ACCOUNT_ID_PRIMARY}'
BILLING_VIEW_ARN_PRIMARY = f'{BVS_ARN_PREFIX}:billingview/primary'
BILLING_VIEW_ARN_CUSTOM = f'{BVS_ARN_PREFIX}:billingview/custom-view-abc123'
BILLING_VIEW_ARN_BILLING_GROUP = f'{BVS_ARN_PREFIX}:billingview/billing-group-view-xyz789'

STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'


def _reload_bvs_with_identity_decorator():
    """Reload bvs_tools with FastMCP.tool patched to return the original function.

    This exposes callable tool functions we can invoke directly to cover the routing lines.
    """
    from awslabs.billing_cost_management_mcp_server.tools import bvs_tools as bvs_mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(bvs_mod)
        return bvs_mod


@pytest.fixture
def mock_ctx():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.info = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


def test_bvs_server_initialization():
    """Test that the bvs_server is properly initialized."""
    assert bvs_server.name == 'bvs-tools'

    instructions = bvs_server.instructions
    assert instructions is not None
    assert 'Billing' in instructions if instructions else False


def test_get_billing_view_tool_registered():
    """Test that the get_billing_view tool is registered with proper name."""
    assert hasattr(get_billing_view_tool, 'name')
    assert get_billing_view_tool.name == 'get-billing-view'


def test_list_billing_views_tool_registered():
    """Test that the list_billing_views tool is registered with proper name."""
    assert hasattr(list_billing_views_tool, 'name')
    assert list_billing_views_tool.name == 'list-billing-views'


def test_list_source_views_for_billing_view_tool_registered():
    """Test that the list_source_views_for_billing_view tool is registered with proper name."""
    assert hasattr(list_source_views_for_billing_view_tool, 'name')
    assert list_source_views_for_billing_view_tool.name == 'list-source-views-for-billing-view'


def test_get_resource_policy_tool_registered():
    """Test that the get_resource_policy tool is registered with proper name."""
    assert hasattr(get_resource_policy_tool, 'name')
    assert get_resource_policy_tool.name == 'get-resource-policy'


@pytest.mark.asyncio
class TestGetBillingViewTool:
    """Tests for the get_billing_view MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.get_billing_view  # type: ignore

        with patch.object(bvs_mod, '_get_billing_view', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_view': {
                        'arn': BILLING_VIEW_ARN_PRIMARY,
                        'name': 'Primary Billing View',
                        'billing_view_type': 'PRIMARY',
                    },
                },
            }

            result = await real_fn(mock_ctx, arn=BILLING_VIEW_ARN_PRIMARY)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['billing_view']['arn'] == BILLING_VIEW_ARN_PRIMARY
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_VIEW_ARN_PRIMARY)

    async def test_passes_arn_param(self, mock_ctx):
        """Test that the ARN parameter is passed through to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.get_billing_view  # type: ignore

        with patch.object(bvs_mod, '_get_billing_view', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_view': {
                        'arn': BILLING_VIEW_ARN_CUSTOM,
                        'billing_view_type': 'CUSTOM',
                    },
                },
            }

            result = await real_fn(mock_ctx, arn=BILLING_VIEW_ARN_CUSTOM)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

    async def test_handles_operation_error(self, mock_ctx):
        """Test that errors from the operation are returned properly."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.get_billing_view  # type: ignore

        with patch.object(bvs_mod, '_get_billing_view', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_ERROR,
                'error_type': 'ResourceNotFoundException',
                'message': 'The specified ARN does not exist',
            }

            result = await real_fn(mock_ctx, arn=BILLING_VIEW_ARN_CUSTOM)  # type: ignore

            assert result['status'] == STATUS_ERROR

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.get_billing_view  # type: ignore

        with (
            patch.object(bvs_mod, '_get_billing_view', new_callable=AsyncMock) as mock_op,
            patch.object(bvs_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('Unexpected error')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'Unexpected error'}

            result = await real_fn(mock_ctx, arn=BILLING_VIEW_ARN_PRIMARY)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


@pytest.mark.asyncio
class TestListBillingViewsTool:
    """Tests for the list_billing_views MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_views': [
                        {
                            'arn': BILLING_VIEW_ARN_PRIMARY,
                            'name': 'Primary Billing View',
                            'billing_view_type': 'PRIMARY',
                        },
                    ],
                    'total_count': 1,
                },
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['total_count'] == 1
            mock_op.assert_awaited_once_with(
                mock_ctx, None, None, None, None, None, None, None, None, 10, None
            )

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'billing_views': [], 'total_count': 0},
            }

            arns_str = '["arn:aws:billing::123456789012:billingview/primary"]'
            types_str = '["PRIMARY", "CUSTOM"]'
            names_str = '[{"searchOption": "STARTS_WITH", "searchValue": "My"}]'

            result = await real_fn(  # type: ignore
                mock_ctx,
                active_after_inclusive='2024-01-01',
                active_before_inclusive='2024-01-31',
                arns=arns_str,
                billing_view_types=types_str,
                max_results=50,
                names=names_str,
                owner_account_id=ACCOUNT_ID_PRIMARY,
                source_account_id=ACCOUNT_ID_PRIMARY,
                max_pages=5,
                next_token='tok123',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx,
                '2024-01-01',
                '2024-01-31',
                arns_str,
                types_str,
                50,
                names_str,
                ACCOUNT_ID_PRIMARY,
                ACCOUNT_ID_PRIMARY,
                5,
                'tok123',
            )

    async def test_handles_operation_error(self, mock_ctx):
        """Test that errors from the operation are returned properly."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_ERROR,
                'error_type': 'AccessDeniedException',
                'message': 'You do not have sufficient access',
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with (
            patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op,
            patch.object(bvs_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('Unexpected error')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'Unexpected error'}

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()

    async def test_with_billing_view_types_only(self, mock_ctx):
        """Test calling with only billing_view_types parameter."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'billing_views': [
                        {
                            'arn': BILLING_VIEW_ARN_PRIMARY,
                            'billing_view_type': 'PRIMARY',
                        },
                    ],
                    'total_count': 1,
                },
            }

            types_str = '["PRIMARY"]'
            result = await real_fn(  # type: ignore
                mock_ctx, billing_view_types=types_str
            )

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['total_count'] == 1
            mock_op.assert_awaited_once_with(
                mock_ctx, None, None, None, types_str, None, None, None, None, 10, None
            )

    async def test_with_time_range_params(self, mock_ctx):
        """Test calling with active_after_inclusive and active_before_inclusive parameters."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'billing_views': [], 'total_count': 0},
            }

            result = await real_fn(  # type: ignore
                mock_ctx,
                active_after_inclusive='2024-01-01T00:00:00',
                active_before_inclusive='2024-01-31T23:59:59',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx,
                '2024-01-01T00:00:00',
                '2024-01-31T23:59:59',
                None,
                None,
                None,
                None,
                None,
                None,
                10,
                None,
            )


@pytest.mark.asyncio
class TestListSourceViewsForBillingViewTool:
    """Tests for the list_source_views_for_billing_view MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_source_views_for_billing_view  # type: ignore

        with patch.object(
            bvs_mod, '_list_source_views_for_billing_view', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'source_views': [BILLING_VIEW_ARN_PRIMARY],
                    'total_count': 1,
                },
            }

            result = await real_fn(mock_ctx, arn=BILLING_VIEW_ARN_CUSTOM)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['total_count'] == 1
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_VIEW_ARN_CUSTOM, None, 10, None)

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_source_views_for_billing_view  # type: ignore

        with patch.object(
            bvs_mod, '_list_source_views_for_billing_view', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'source_views': [BILLING_VIEW_ARN_PRIMARY],
                    'total_count': 1,
                },
            }

            result = await real_fn(  # type: ignore
                mock_ctx,
                arn=BILLING_VIEW_ARN_CUSTOM,
                max_results=5,
                max_pages=3,
                next_token='tok456',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_VIEW_ARN_CUSTOM, 5, 3, 'tok456')

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_source_views_for_billing_view  # type: ignore

        with (
            patch.object(
                bvs_mod, '_list_source_views_for_billing_view', new_callable=AsyncMock
            ) as mock_op,
            patch.object(bvs_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('Unexpected error')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'Unexpected error'}

            result = await real_fn(mock_ctx, arn=BILLING_VIEW_ARN_CUSTOM)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


@pytest.mark.asyncio
class TestGetResourcePolicyTool:
    """Tests for the get_resource_policy MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.get_resource_policy  # type: ignore

        with patch.object(bvs_mod, '_get_resource_policy', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'resource_arn': BILLING_VIEW_ARN_CUSTOM,
                    'policy': '{"Version": "2012-10-17", "Statement": []}',
                },
            }

            result = await real_fn(mock_ctx, resource_arn=BILLING_VIEW_ARN_CUSTOM)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['resource_arn'] == BILLING_VIEW_ARN_CUSTOM
            mock_op.assert_awaited_once_with(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

    async def test_handles_operation_error(self, mock_ctx):
        """Test that errors from the operation are returned properly."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.get_resource_policy  # type: ignore

        with patch.object(bvs_mod, '_get_resource_policy', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_ERROR,
                'error_type': 'ResourceNotFoundException',
                'message': 'The specified ARN does not exist',
            }

            result = await real_fn(mock_ctx, resource_arn=BILLING_VIEW_ARN_CUSTOM)  # type: ignore

            assert result['status'] == STATUS_ERROR

    async def test_handles_unexpected_exception(self, mock_ctx):
        """Test that unexpected exceptions are caught by the tool wrapper."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.get_resource_policy  # type: ignore

        with (
            patch.object(bvs_mod, '_get_resource_policy', new_callable=AsyncMock) as mock_op,
            patch.object(bvs_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('Unexpected error')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'Unexpected error'}

            result = await real_fn(mock_ctx, resource_arn=BILLING_VIEW_ARN_CUSTOM)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()
