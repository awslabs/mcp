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

import asyncio
import fastmcp
import importlib
import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.bvs_tools import (
    bvs_server,
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
    tool = asyncio.run(bvs_server.get_tool('get-billing-view'))
    assert tool is not None
    assert tool.name == 'get-billing-view'


def test_list_billing_views_tool_registered():
    """Test that the list_billing_views tool is registered with proper name."""
    tool = asyncio.run(bvs_server.get_tool('list-billing-views'))
    assert tool is not None
    assert tool.name == 'list-billing-views'


def test_list_source_views_for_billing_view_tool_registered():
    """Test that the list_source_views_for_billing_view tool is registered with proper name."""
    tool = asyncio.run(bvs_server.get_tool('list-source-views-for-billing-view'))
    assert tool is not None
    assert tool.name == 'list-source-views-for-billing-view'


def test_get_resource_policy_tool_registered():
    """Test that the get_resource_policy tool is registered with proper name."""
    tool = asyncio.run(bvs_server.get_tool('get-resource-policy'))
    assert tool is not None
    assert tool.name == 'get-resource-policy'


def test_list_billing_view_segments_tool_registered():
    """Test that the list_billing_view_segments tool is registered with proper name."""
    tool = asyncio.run(bvs_server.get_tool('list-billing-view-segments'))
    assert tool is not None
    assert tool.name == 'list-billing-view-segments'


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
                mock_ctx,
                active_after_inclusive=None,
                active_before_inclusive=None,
                arns=None,
                billing_view_types=None,
                names=None,
                owner_account_id=None,
                source_account_id=None,
                max_items=None,
                next_token=None,
            )

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'billing_views': []},
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
                names=names_str,
                owner_account_id=ACCOUNT_ID_PRIMARY,
                source_account_id=ACCOUNT_ID_PRIMARY,
                max_items=50,
                next_token='tok123',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx,
                active_after_inclusive='2024-01-01',
                active_before_inclusive='2024-01-31',
                arns=arns_str,
                billing_view_types=types_str,
                names=names_str,
                owner_account_id=ACCOUNT_ID_PRIMARY,
                source_account_id=ACCOUNT_ID_PRIMARY,
                max_items=50,
                next_token='tok123',
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
                mock_ctx,
                active_after_inclusive=None,
                active_before_inclusive=None,
                arns=None,
                billing_view_types=types_str,
                names=None,
                owner_account_id=None,
                source_account_id=None,
                max_items=None,
                next_token=None,
            )

    async def test_with_time_range_params(self, mock_ctx):
        """Test calling with active_after_inclusive and active_before_inclusive parameters."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_views  # type: ignore

        with patch.object(bvs_mod, '_list_billing_views', new_callable=AsyncMock) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'billing_views': []},
            }

            result = await real_fn(  # type: ignore
                mock_ctx,
                active_after_inclusive='2024-01-01T00:00:00',
                active_before_inclusive='2024-01-31T23:59:59',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx,
                active_after_inclusive='2024-01-01T00:00:00',
                active_before_inclusive='2024-01-31T23:59:59',
                arns=None,
                billing_view_types=None,
                names=None,
                owner_account_id=None,
                source_account_id=None,
                max_items=None,
                next_token=None,
            )


@pytest.mark.asyncio
async def test_list_billing_views_description_explains_source_account_id_and_name_case():
    """source_account_id is described as a sourceAccountId match, not a membership search."""
    from awslabs.billing_cost_management_mcp_server.tools import bvs_tools

    real = importlib.reload(bvs_tools)
    tools = {t.name: t for t in await real.bvs_server.list_tools()}
    description = ' '.join(tools['list-billing-views'].description.split())
    assert 'Filter by source account ID (12-digit AWS account ID)' not in description
    assert 'Not an account membership search' in description
    assert "billing group's primary account is this ID" in description
    assert 'PRIMARY and CUSTOM views are never returned with it' in description
    assert 'No filter of this tool lists the views that include a given account' in description
    assert 'list-account-associations' in description
    assert 'list-billing-groups' in description
    assert 'without one it matches billing groups from all periods' in description
    assert 'The prefix match is case-sensitive' in description


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
            mock_op.assert_awaited_once_with(
                mock_ctx, BILLING_VIEW_ARN_CUSTOM, max_items=None, next_token=None
            )

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
                max_items=5,
                next_token='tok456',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx, BILLING_VIEW_ARN_CUSTOM, max_items=5, next_token='tok456'
            )

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


@pytest.mark.asyncio
class TestListBillingViewSegmentsTool:
    """Tests for the list_billing_view_segments MCP tool wrapper."""

    async def test_delegates_to_operation(self, mock_ctx):
        """Test that the tool delegates to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_view_segments  # type: ignore

        with patch.object(
            bvs_mod, '_list_billing_view_segments', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {
                    'segments': [
                        {
                            'domain': 'BILLABLE',
                            'management_account_id': ACCOUNT_ID_PRIMARY,
                            'time_range': {
                                'begin_date_inclusive': '2024-09-01T00:00:00',
                                'end_date_exclusive': '2024-10-01T00:00:00',
                            },
                        },
                    ],
                    'pagination': {
                        'items_returned': 1,
                        'has_more': False,
                    },
                },
            }

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_SUCCESS
            assert result['data']['pagination']['items_returned'] == 1
            mock_op.assert_awaited_once_with(
                mock_ctx,
                arn=None,
                begin_date_inclusive=None,
                end_date_exclusive=None,
                max_items=None,
                next_token=None,
            )

    async def test_passes_all_params(self, mock_ctx):
        """Test that all parameters are passed through to the operation function."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_view_segments  # type: ignore

        with patch.object(
            bvs_mod, '_list_billing_view_segments', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'segments': [], 'pagination': {'items_returned': 0, 'has_more': False}},
            }

            result = await real_fn(  # type: ignore
                mock_ctx,
                arn=BILLING_VIEW_ARN_PRIMARY,
                begin_date_inclusive='2024-09-01',
                end_date_exclusive='2024-10-01',
                max_items=50,
                next_token='tok123',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx,
                arn=BILLING_VIEW_ARN_PRIMARY,
                begin_date_inclusive='2024-09-01',
                end_date_exclusive='2024-10-01',
                max_items=50,
                next_token='tok123',
            )

    async def test_handles_operation_error(self, mock_ctx):
        """Test that errors from the operation are returned properly."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_view_segments  # type: ignore

        with patch.object(
            bvs_mod, '_list_billing_view_segments', new_callable=AsyncMock
        ) as mock_op:
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
        real_fn = bvs_mod.list_billing_view_segments  # type: ignore

        with (
            patch.object(
                bvs_mod, '_list_billing_view_segments', new_callable=AsyncMock
            ) as mock_op,
            patch.object(bvs_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_op.side_effect = RuntimeError('Unexpected error')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'Unexpected error'}

            result = await real_fn(mock_ctx)  # type: ignore

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()

    async def test_with_time_range_params(self, mock_ctx):
        """Test calling with begin_date_inclusive and end_date_exclusive parameters."""
        bvs_mod = _reload_bvs_with_identity_decorator()
        real_fn = bvs_mod.list_billing_view_segments  # type: ignore

        with patch.object(
            bvs_mod, '_list_billing_view_segments', new_callable=AsyncMock
        ) as mock_op:
            mock_op.return_value = {
                'status': STATUS_SUCCESS,
                'data': {'segments': [], 'pagination': {'items_returned': 0, 'has_more': False}},
            }

            result = await real_fn(  # type: ignore
                mock_ctx,
                begin_date_inclusive='2024-09-01T00:00:00',
                end_date_exclusive='2024-10-01T00:00:00',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once_with(
                mock_ctx,
                arn=None,
                begin_date_inclusive='2024-09-01T00:00:00',
                end_date_exclusive='2024-10-01T00:00:00',
                max_items=None,
                next_token=None,
            )


@pytest.mark.asyncio
async def test_tool_schemas_follow_the_max_items_contract():
    """List tools take max_items + next_token; get tools take neither."""
    from awslabs.billing_cost_management_mcp_server.tools import bvs_tools

    # Other tests reload this module under a patched FastMCP; reload the real one here.
    real = importlib.reload(bvs_tools)
    tools = {t.name: t for t in await real.bvs_server.list_tools()}
    for name, tool in tools.items():
        params = set(tool.parameters['properties'])
        assert not {'max_pages', 'max_results'} & params, name
        if name.startswith('get-'):
            assert not {'max_items', 'next_token'} & params, name
        else:
            assert {'max_items', 'next_token'} <= params, name
            assert 'max_pages' not in tool.description, name


@pytest.mark.asyncio
async def test_get_billing_view_description_counts_types_and_explains_filter():
    """The type list is not miscounted, and data_filter_expression is explained."""
    from awslabs.billing_cost_management_mcp_server.tools import bvs_tools

    real = importlib.reload(bvs_tools)
    tools = {t.name: t for t in await real.bvs_server.list_tools()}
    description = tools['get-billing-view'].description

    assert 'four types' not in description
    for view_type in (
        'PRIMARY',
        'BILLING_GROUP',
        'CUSTOM',
        'BILLING_TRANSFER',
        'BILLING_TRANSFER_SHOWBACK',
    ):
        assert f'- {view_type}:' in description
    assert 'data_filter_expression' in description
    assert 'LINKED_ACCOUNT' in description
    assert 'unfiltered' in description
    assert 'exact matches' not in description
    assert 'uncategorized' not in description


@pytest.mark.asyncio
async def test_list_billing_views_description_explains_the_time_range_rules():
    """The one-month rule and the date-only end gotcha are stated where callers read them."""
    from awslabs.billing_cost_management_mcp_server.tools import bvs_tools

    real = importlib.reload(bvs_tools)
    tools = {t.name: t for t in await real.bvs_server.list_tools()}
    tool = tools['list-billing-views']

    assert 'same UTC calendar month' in tool.description
    assert 'A date-only active_before_inclusive means 00:00:00' in tool.description
    # No example may teach a date-only end, which drops most of the last day.
    assert not re.search(r'"active_before_inclusive": "\d{4}-\d{2}-\d{2}"', tool.description)
