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

"""Unit tests for the bvs_operations module."""

import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.bvs_operations import (
    _format_billing_view_common,
    _format_cost_category_values,
    _format_dimension_values,
    _format_expression,
    _format_get_billing_view_element,
    _format_health_status,
    _format_list_billing_view_element,
    _format_tag_values,
    _format_time_range,
    get_billing_view,
    get_resource_policy,
    list_billing_views,
    list_source_views_for_billing_view,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# --- Constants ---

ACCOUNT_ID_PRIMARY = '123456789012'
ACCOUNT_ID_PRIMARY_2 = '987654321098'

BVS_ARN_PREFIX = f'arn:aws:billing::{ACCOUNT_ID_PRIMARY}'
BILLING_VIEW_ARN_PRIMARY = f'{BVS_ARN_PREFIX}:billingview/primary'
BILLING_VIEW_ARN_CUSTOM = f'{BVS_ARN_PREFIX}:billingview/custom-view-abc123'
BILLING_VIEW_ARN_BILLING_GROUP = f'{BVS_ARN_PREFIX}:billingview/billing-group-view-xyz789'

NEXT_TOKEN_PAGE2 = 'page2token'
NEXT_TOKEN_MORE = 'more_results_token'
NEXT_TOKEN_CONTINUE = 'continue_from_here'

STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'

ERROR_ACCESS_DENIED = 'AccessDeniedException'
ERROR_ACCESS_DENIED_MSG = 'You do not have sufficient access'
ERROR_RESOURCE_NOT_FOUND = 'ResourceNotFoundException'
ERROR_RESOURCE_NOT_FOUND_MSG = 'The request references a resource that does not exist'
ERROR_VALIDATION = 'ValidationException'
TEST_REQUEST_ID = 'test-request-id'
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_BAD_REQUEST = 400

PATCH_BVS_CLIENT = (
    'awslabs.billing_cost_management_mcp_server.tools.bvs_operations._create_bvs_client'
)


def make_client_error_response(
    code: str = ERROR_ACCESS_DENIED,
    message: str = ERROR_ACCESS_DENIED_MSG,
    request_id: str = TEST_REQUEST_ID,
    http_status: int = HTTP_STATUS_FORBIDDEN,
) -> dict:
    """Build a standard ClientError response dict for tests."""
    return {
        'Error': {'Code': code, 'Message': message},
        'ResponseMetadata': {'RequestId': request_id, 'HTTPStatusCode': http_status},
    }


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


@pytest.fixture
def sample_billing_view_primary():
    """Sample primary billing view data from AWS API."""
    return {
        'arn': BILLING_VIEW_ARN_PRIMARY,
        'name': 'Primary Billing View',
        'description': 'Default billing view for the account',
        'billingViewType': 'PRIMARY',
        'ownerAccountId': ACCOUNT_ID_PRIMARY,
        'derivedViewCount': 2,
        'sourceViewCount': 0,
        'createdAt': 1700000000,
        'updatedAt': 1700100000,
    }


@pytest.fixture
def sample_billing_view_custom():
    """Sample custom billing view data from AWS API with all optional fields."""
    return {
        'arn': BILLING_VIEW_ARN_CUSTOM,
        'name': 'Custom Billing View',
        'description': 'A custom billing view for business unit',
        'billingViewType': 'CUSTOM',
        'ownerAccountId': ACCOUNT_ID_PRIMARY,
        'sourceAccountId': ACCOUNT_ID_PRIMARY_2,
        'derivedViewCount': 0,
        'sourceViewCount': 3,
        'dataFilterExpression': {
            'dimensions': {
                'key': 'LINKED_ACCOUNT',
                'values': ['111111111111', '222222222222'],
            },
            'tags': {
                'key': 'Environment',
                'values': ['Production', 'Staging'],
            },
            'costCategories': {
                'key': 'Team',
                'values': ['Engineering', 'Marketing'],
            },
            'timeRange': {
                'beginDateInclusive': 1700000000,
                'endDateInclusive': 1700500000,
            },
        },
        'healthStatus': {
            'statusCode': 'HEALTHY',
            'statusReasons': [],
        },
        'createdAt': 1700000000,
        'updatedAt': 1700200000,
        'viewDefinitionLastUpdatedAt': 1700150000,
    }


@pytest.fixture
def sample_billing_view_list_elements():
    """Sample billing view list elements from the ListBillingViews API."""
    return [
        {
            'arn': BILLING_VIEW_ARN_PRIMARY,
            'name': 'Primary Billing View',
            'description': 'Default billing view for the account',
            'billingViewType': 'PRIMARY',
            'ownerAccountId': ACCOUNT_ID_PRIMARY,
        },
        {
            'arn': BILLING_VIEW_ARN_CUSTOM,
            'name': 'Custom Billing View',
            'description': 'A custom billing view for business unit',
            'billingViewType': 'CUSTOM',
            'ownerAccountId': ACCOUNT_ID_PRIMARY,
            'sourceAccountId': ACCOUNT_ID_PRIMARY_2,
            'healthStatus': {
                'statusCode': 'HEALTHY',
                'statusReasons': [],
            },
        },
        {
            'arn': BILLING_VIEW_ARN_BILLING_GROUP,
            'name': 'Billing Group View',
            'description': 'Billing group billing view',
            'billingViewType': 'BILLING_GROUP',
            'ownerAccountId': ACCOUNT_ID_PRIMARY,
        },
    ]


class TestFormatDimensionValues:
    """Tests for the _format_dimension_values function."""

    def test_format_basic_dimensions(self):
        """Test formatting dimension values with key and values."""
        result = _format_dimension_values(
            {
                'key': 'LINKED_ACCOUNT',
                'values': ['111111111111', '222222222222'],
            }
        )
        assert result['key'] == 'LINKED_ACCOUNT'
        assert result['values'] == ['111111111111', '222222222222']

    def test_format_missing_values(self):
        """Test formatting dimension values with missing values list."""
        result = _format_dimension_values({'key': 'LINKED_ACCOUNT'})
        assert result['key'] == 'LINKED_ACCOUNT'
        assert result['values'] == []

    def test_format_missing_key(self):
        """Test formatting dimension values with missing key."""
        result = _format_dimension_values({'values': ['111111111111']})
        assert result['key'] is None
        assert result['values'] == ['111111111111']


class TestFormatTagValues:
    """Tests for the _format_tag_values function."""

    def test_format_basic_tags(self):
        """Test formatting tag values with key and values."""
        result = _format_tag_values(
            {
                'key': 'Environment',
                'values': ['Production', 'Staging'],
            }
        )
        assert result['key'] == 'Environment'
        assert result['values'] == ['Production', 'Staging']

    def test_format_missing_values(self):
        """Test formatting tag values with missing values list."""
        result = _format_tag_values({'key': 'Environment'})
        assert result['key'] == 'Environment'
        assert result['values'] == []


class TestFormatCostCategoryValues:
    """Tests for the _format_cost_category_values function."""

    def test_format_basic_cost_categories(self):
        """Test formatting cost category values with key and values."""
        result = _format_cost_category_values(
            {
                'key': 'Team',
                'values': ['Engineering', 'Marketing'],
            }
        )
        assert result['key'] == 'Team'
        assert result['values'] == ['Engineering', 'Marketing']

    def test_format_missing_values(self):
        """Test formatting cost category values with missing values list."""
        result = _format_cost_category_values({'key': 'Team'})
        assert result['key'] == 'Team'
        assert result['values'] == []


class TestFormatTimeRange:
    """Tests for the _format_time_range function."""

    def test_format_full_time_range(self):
        """Test formatting time range with both dates."""
        result = _format_time_range(
            {
                'beginDateInclusive': 1700000000,
                'endDateInclusive': 1700500000,
            }
        )
        assert 'begin_date_inclusive' in result
        assert 'end_date_inclusive' in result

    def test_format_begin_date_only(self):
        """Test formatting time range with begin date only."""
        result = _format_time_range({'beginDateInclusive': 1700000000})
        assert 'begin_date_inclusive' in result
        assert 'end_date_inclusive' not in result

    def test_format_empty_time_range(self):
        """Test formatting an empty time range."""
        result = _format_time_range({})
        assert result == {}


class TestFormatHealthStatus:
    """Tests for the _format_health_status function."""

    def test_format_healthy_status(self):
        """Test formatting a healthy status."""
        result = _format_health_status(
            {
                'statusCode': 'HEALTHY',
                'statusReasons': [],
            }
        )
        assert result['status_code'] == 'HEALTHY'
        assert result['status_reasons'] == []

    def test_format_unhealthy_status_with_reasons(self):
        """Test formatting an unhealthy status with reasons."""
        result = _format_health_status(
            {
                'statusCode': 'UNHEALTHY',
                'statusReasons': ['SOURCE_VIEW_UNHEALTHY', 'SOURCE_VIEW_ACCESS_DENIED'],
            }
        )
        assert result['status_code'] == 'UNHEALTHY'
        assert result['status_reasons'] == ['SOURCE_VIEW_UNHEALTHY', 'SOURCE_VIEW_ACCESS_DENIED']

    def test_format_status_without_reasons(self):
        """Test formatting a status without reasons field."""
        result = _format_health_status({'statusCode': 'CREATING'})
        assert result['status_code'] == 'CREATING'
        assert 'status_reasons' not in result

    def test_format_status_missing_code(self):
        """Test formatting a status with missing status code."""
        result = _format_health_status({})
        assert result['status_code'] is None
        assert 'status_reasons' not in result


class TestFormatExpression:
    """Tests for the _format_expression function."""

    def test_format_empty_expression(self):
        """Test formatting an empty expression."""
        result = _format_expression({})
        assert result == {}

    def test_format_expression_with_dimensions(self):
        """Test formatting expression with dimensions only."""
        result = _format_expression(
            {
                'dimensions': {'key': 'LINKED_ACCOUNT', 'values': ['111111111111']},
            }
        )
        assert 'dimensions' in result
        assert result['dimensions']['key'] == 'LINKED_ACCOUNT'

    def test_format_expression_with_all_fields(self, sample_billing_view_custom):
        """Test formatting expression with all fields present."""
        expression = sample_billing_view_custom['dataFilterExpression']
        result = _format_expression(expression)

        assert 'dimensions' in result
        assert 'tags' in result
        assert 'cost_categories' in result
        assert 'time_range' in result


class TestFormatBillingViewCommon:
    """Tests for the _format_billing_view_common function."""

    def test_format_empty_billing_view(self):
        """Test formatting an empty billing view."""
        result = _format_billing_view_common({})
        assert result['arn'] is None
        assert result['name'] is None
        assert result['billing_view_type'] is None
        assert 'health_status' not in result

    def test_format_basic_fields(self):
        """Test formatting common fields with basic data."""
        result = _format_billing_view_common(
            {
                'arn': BILLING_VIEW_ARN_PRIMARY,
                'name': 'Primary Billing View',
                'billingViewType': 'PRIMARY',
                'ownerAccountId': ACCOUNT_ID_PRIMARY,
            }
        )
        assert result['arn'] == BILLING_VIEW_ARN_PRIMARY
        assert result['billing_view_type'] == 'PRIMARY'
        assert result['owner_account_id'] == ACCOUNT_ID_PRIMARY

    def test_format_with_health_status(self):
        """Test formatting common fields with health status."""
        result = _format_billing_view_common(
            {
                'arn': BILLING_VIEW_ARN_CUSTOM,
                'healthStatus': {'statusCode': 'HEALTHY', 'statusReasons': []},
            }
        )
        assert 'health_status' in result
        assert result['health_status']['status_code'] == 'HEALTHY'


class TestFormatGetBillingViewElement:
    """Tests for the _format_get_billing_view_element function."""

    def test_format_empty_billing_view(self):
        """Test formatting an empty billing view element."""
        result = _format_get_billing_view_element({})
        assert result['arn'] is None
        assert result['derived_view_count'] is None
        assert result['source_view_count'] is None

    def test_format_primary_billing_view(self, sample_billing_view_primary):
        """Test formatting a primary billing view with basic fields."""
        result = _format_get_billing_view_element(sample_billing_view_primary)

        assert result['arn'] == BILLING_VIEW_ARN_PRIMARY
        assert result['name'] == 'Primary Billing View'
        assert result['billing_view_type'] == 'PRIMARY'
        assert result['derived_view_count'] == 2
        assert result['source_view_count'] == 0
        assert 'created_at' in result
        assert 'updated_at' in result

    def test_format_custom_billing_view(self, sample_billing_view_custom):
        """Test formatting a custom billing view with all optional fields."""
        result = _format_get_billing_view_element(sample_billing_view_custom)

        assert result['arn'] == BILLING_VIEW_ARN_CUSTOM
        assert result['billing_view_type'] == 'CUSTOM'
        assert 'data_filter_expression' in result
        assert 'health_status' in result
        assert 'view_definition_last_updated_at' in result

    def test_format_datetime_timestamps(self):
        """Test that datetime objects are handled correctly as timestamps."""
        dt_utc = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
        billing_view = {
            'arn': BILLING_VIEW_ARN_CUSTOM,
            'billingViewType': 'CUSTOM',
            'createdAt': dt_utc,
            'updatedAt': dt_utc,
            'viewDefinitionLastUpdatedAt': dt_utc,
        }
        result = _format_get_billing_view_element(billing_view)

        assert result['created_at'] == '2023-11-14T22:13:20'
        assert result['updated_at'] == '2023-11-14T22:13:20'
        assert result['view_definition_last_updated_at'] == '2023-11-14T22:13:20'


class TestFormatListBillingViewElement:
    """Tests for the _format_list_billing_view_element function."""

    def test_format_empty_billing_view(self):
        """Test formatting an empty billing view list element."""
        result = _format_list_billing_view_element({})
        assert result['arn'] is None
        assert 'derived_view_count' not in result
        assert 'created_at' not in result

    def test_format_primary_list_element(self):
        """Test formatting a primary billing view list element."""
        result = _format_list_billing_view_element(
            {
                'arn': BILLING_VIEW_ARN_PRIMARY,
                'name': 'Primary Billing View',
                'billingViewType': 'PRIMARY',
                'ownerAccountId': ACCOUNT_ID_PRIMARY,
            }
        )
        assert result['arn'] == BILLING_VIEW_ARN_PRIMARY
        assert result['billing_view_type'] == 'PRIMARY'


@pytest.mark.asyncio
class TestGetBillingView:
    """Tests for the get_billing_view operation function."""

    @patch(PATCH_BVS_CLIENT)
    async def test_get_billing_view_success(
        self, mock_create_client, mock_ctx, sample_billing_view_primary
    ):
        """Test successful retrieval of a billing view."""
        mock_client = MagicMock()
        mock_client.get_billing_view.return_value = {
            'billingView': sample_billing_view_primary,
        }
        mock_create_client.return_value = mock_client

        result = await get_billing_view(mock_ctx, BILLING_VIEW_ARN_PRIMARY)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['billing_view']['arn'] == BILLING_VIEW_ARN_PRIMARY
        assert result['data']['billing_view']['billing_view_type'] == 'PRIMARY'

    @patch(PATCH_BVS_CLIENT)
    async def test_get_billing_view_custom_with_all_fields(
        self, mock_create_client, mock_ctx, sample_billing_view_custom
    ):
        """Test successful retrieval of a custom billing view with all fields."""
        mock_client = MagicMock()
        mock_client.get_billing_view.return_value = {
            'billingView': sample_billing_view_custom,
        }
        mock_create_client.return_value = mock_client

        result = await get_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_SUCCESS
        billing_view = result['data']['billing_view']
        assert billing_view['billing_view_type'] == 'CUSTOM'
        assert 'data_filter_expression' in billing_view
        assert 'health_status' in billing_view

    @patch(PATCH_BVS_CLIENT)
    async def test_get_billing_view_passes_arn(
        self, mock_create_client, mock_ctx, sample_billing_view_primary
    ):
        """Test that the ARN is passed correctly to the API call."""
        mock_client = MagicMock()
        mock_client.get_billing_view.return_value = {
            'billingView': sample_billing_view_primary,
        }
        mock_create_client.return_value = mock_client

        await get_billing_view(mock_ctx, BILLING_VIEW_ARN_PRIMARY)

        call_kwargs = mock_client.get_billing_view.call_args[1]
        assert call_kwargs['arn'] == BILLING_VIEW_ARN_PRIMARY

    @patch(PATCH_BVS_CLIENT)
    async def test_get_billing_view_empty_response(self, mock_create_client, mock_ctx):
        """Test retrieval when the billing view response is empty."""
        mock_client = MagicMock()
        mock_client.get_billing_view.return_value = {'billingView': {}}
        mock_create_client.return_value = mock_client

        result = await get_billing_view(mock_ctx, BILLING_VIEW_ARN_PRIMARY)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['billing_view']['arn'] is None

    @patch(PATCH_BVS_CLIENT)
    async def test_get_billing_view_access_denied(self, mock_create_client, mock_ctx):
        """Test handling of AccessDeniedException."""
        mock_client = MagicMock()
        mock_client.get_billing_view.side_effect = ClientError(
            make_client_error_response(),
            'GetBillingView',
        )
        mock_create_client.return_value = mock_client

        result = await get_billing_view(mock_ctx, BILLING_VIEW_ARN_PRIMARY)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED

    @patch(PATCH_BVS_CLIENT)
    async def test_get_billing_view_resource_not_found(self, mock_create_client, mock_ctx):
        """Test handling of ResourceNotFoundException."""
        mock_client = MagicMock()
        mock_client.get_billing_view.side_effect = ClientError(
            make_client_error_response(
                code=ERROR_RESOURCE_NOT_FOUND,
                message=ERROR_RESOURCE_NOT_FOUND_MSG,
                http_status=HTTP_STATUS_NOT_FOUND,
            ),
            'GetBillingView',
        )
        mock_create_client.return_value = mock_client

        result = await get_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_RESOURCE_NOT_FOUND


@pytest.mark.asyncio
class TestListBillingViews:
    """Tests for the list_billing_views operation function."""

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_success(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test successful listing of billing views."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': sample_billing_view_list_elements,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 3
        assert 'next_token' not in result['data']

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_with_billing_view_types(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test listing billing views with billing view types filter."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': [sample_billing_view_list_elements[0]],
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx, billing_view_types=json.dumps(['PRIMARY']))

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        call_kwargs = mock_client.list_billing_views.call_args[1]
        assert call_kwargs['billingViewTypes'] == ['PRIMARY']

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_with_active_time_range(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test listing billing views with active time range."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': sample_billing_view_list_elements,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(
            mock_ctx,
            active_after_inclusive='2024-01-01',
            active_before_inclusive='2024-01-31',
        )

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_billing_views.call_args[1]
        assert 'activeTimeRange' in call_kwargs
        assert call_kwargs['activeTimeRange']['activeAfterInclusive'] == 1704067200
        assert call_kwargs['activeTimeRange']['activeBeforeInclusive'] == 1706659200

    async def test_list_billing_views_active_time_range_only_after(self, mock_ctx):
        """Test that providing only active_after_inclusive raises an error."""
        result = await list_billing_views(mock_ctx, active_after_inclusive='2024-01-01')
        assert result['status'] == STATUS_ERROR

    async def test_list_billing_views_active_time_range_only_before(self, mock_ctx):
        """Test that providing only active_before_inclusive raises an error."""
        result = await list_billing_views(mock_ctx, active_before_inclusive='2024-01-31')
        assert result['status'] == STATUS_ERROR

    async def test_list_billing_views_invalid_date_format(self, mock_ctx):
        """Test listing billing views with invalid date format."""
        result = await list_billing_views(
            mock_ctx,
            active_after_inclusive='not-a-date',
            active_before_inclusive='2024-01-31',
        )
        assert result['status'] == STATUS_ERROR

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_with_owner_account_id(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test listing billing views with owner account ID filter."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': sample_billing_view_list_elements,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx, owner_account_id=ACCOUNT_ID_PRIMARY)

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_billing_views.call_args[1]
        assert call_kwargs['ownerAccountId'] == ACCOUNT_ID_PRIMARY

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_pagination(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test listing billing views with pagination across multiple pages."""
        mock_client = MagicMock()
        mock_client.list_billing_views.side_effect = [
            {
                'billingViews': [sample_billing_view_list_elements[0]],
                'nextToken': NEXT_TOKEN_PAGE2,
            },
            {
                'billingViews': [sample_billing_view_list_elements[1]],
            },
        ]
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert mock_client.list_billing_views.call_count == 2
        assert 'next_token' not in result['data']

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_max_pages_stops_pagination(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test that max_pages limits the number of API calls and returns next_token."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': [sample_billing_view_list_elements[0]],
            'nextToken': NEXT_TOKEN_MORE,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx, max_pages=1)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_empty_result(self, mock_create_client, mock_ctx):
        """Test listing billing views when none exist."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {'billingViews': []}
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 0
        assert result['data']['billing_views'] == []

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_with_names_filter(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test listing billing views with names filter."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': [sample_billing_view_list_elements[1]],
        }
        mock_create_client.return_value = mock_client

        names_json = json.dumps([{'searchOption': 'STARTS_WITH', 'searchValue': 'Custom'}])
        result = await list_billing_views(mock_ctx, names=names_json)

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_billing_views.call_args[1]
        assert call_kwargs['names'] == [{'searchOption': 'STARTS_WITH', 'searchValue': 'Custom'}]

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_with_source_account_id(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test listing billing views with source account ID filter."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': [sample_billing_view_list_elements[1]],
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx, source_account_id=ACCOUNT_ID_PRIMARY_2)

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_billing_views.call_args[1]
        assert call_kwargs['sourceAccountId'] == ACCOUNT_ID_PRIMARY_2

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_with_max_results(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test listing billing views with max_results parameter."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': [sample_billing_view_list_elements[0]],
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx, max_results=50)

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_billing_views.call_args[1]
        assert call_kwargs['maxResults'] == 50

    async def test_list_billing_views_invalid_arns(self, mock_ctx):
        """Test listing billing views with invalid ARNs JSON."""
        result = await list_billing_views(mock_ctx, arns='not-valid-json')
        assert result['status'] == STATUS_ERROR

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_access_denied(self, mock_create_client, mock_ctx):
        """Test handling of AccessDeniedException."""
        mock_client = MagicMock()
        mock_client.list_billing_views.side_effect = ClientError(
            make_client_error_response(),
            'ListBillingViews',
        )
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED

    @patch(PATCH_BVS_CLIENT)
    async def test_list_billing_views_response_format(
        self, mock_create_client, mock_ctx, sample_billing_view_list_elements
    ):
        """Test that list response items contain only list-level fields."""
        mock_client = MagicMock()
        mock_client.list_billing_views.return_value = {
            'billingViews': sample_billing_view_list_elements,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_views(mock_ctx)

        assert result['status'] == STATUS_SUCCESS
        for bv in result['data']['billing_views']:
            assert 'arn' in bv
            assert 'billing_view_type' in bv
            assert 'derived_view_count' not in bv
            assert 'created_at' not in bv


@pytest.mark.asyncio
class TestListSourceViewsForBillingView:
    """Tests for the list_source_views_for_billing_view operation function."""

    @patch(PATCH_BVS_CLIENT)
    async def test_list_source_views_success(self, mock_create_client, mock_ctx):
        """Test successful listing of source views."""
        mock_client = MagicMock()
        mock_client.list_source_views_for_billing_view.return_value = {
            'sourceViews': [BILLING_VIEW_ARN_PRIMARY, BILLING_VIEW_ARN_BILLING_GROUP],
        }
        mock_create_client.return_value = mock_client

        result = await list_source_views_for_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert 'next_token' not in result['data']

    @patch(PATCH_BVS_CLIENT)
    async def test_list_source_views_passes_arn(self, mock_create_client, mock_ctx):
        """Test that the ARN is passed correctly to the API call."""
        mock_client = MagicMock()
        mock_client.list_source_views_for_billing_view.return_value = {
            'sourceViews': [BILLING_VIEW_ARN_PRIMARY],
        }
        mock_create_client.return_value = mock_client

        await list_source_views_for_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        call_kwargs = mock_client.list_source_views_for_billing_view.call_args[1]
        assert call_kwargs['arn'] == BILLING_VIEW_ARN_CUSTOM

    @patch(PATCH_BVS_CLIENT)
    async def test_list_source_views_with_max_results(self, mock_create_client, mock_ctx):
        """Test listing source views with max_results parameter."""
        mock_client = MagicMock()
        mock_client.list_source_views_for_billing_view.return_value = {
            'sourceViews': [BILLING_VIEW_ARN_PRIMARY],
        }
        mock_create_client.return_value = mock_client

        await list_source_views_for_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM, max_results=5)

        call_kwargs = mock_client.list_source_views_for_billing_view.call_args[1]
        assert call_kwargs['maxResults'] == 5

    @patch(PATCH_BVS_CLIENT)
    async def test_list_source_views_pagination(self, mock_create_client, mock_ctx):
        """Test listing source views with pagination across multiple pages."""
        mock_client = MagicMock()
        mock_client.list_source_views_for_billing_view.side_effect = [
            {
                'sourceViews': [BILLING_VIEW_ARN_PRIMARY],
                'nextToken': NEXT_TOKEN_PAGE2,
            },
            {
                'sourceViews': [BILLING_VIEW_ARN_BILLING_GROUP],
            },
        ]
        mock_create_client.return_value = mock_client

        result = await list_source_views_for_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert mock_client.list_source_views_for_billing_view.call_count == 2

    @patch(PATCH_BVS_CLIENT)
    async def test_list_source_views_max_pages_stops_pagination(
        self, mock_create_client, mock_ctx
    ):
        """Test that max_pages limits the number of API calls."""
        mock_client = MagicMock()
        mock_client.list_source_views_for_billing_view.return_value = {
            'sourceViews': [BILLING_VIEW_ARN_PRIMARY],
            'nextToken': NEXT_TOKEN_MORE,
        }
        mock_create_client.return_value = mock_client

        result = await list_source_views_for_billing_view(
            mock_ctx, BILLING_VIEW_ARN_CUSTOM, max_pages=1
        )

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BVS_CLIENT)
    async def test_list_source_views_empty_result(self, mock_create_client, mock_ctx):
        """Test listing source views when none are returned."""
        mock_client = MagicMock()
        mock_client.list_source_views_for_billing_view.return_value = {
            'sourceViews': [],
        }
        mock_create_client.return_value = mock_client

        result = await list_source_views_for_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 0

    @patch(PATCH_BVS_CLIENT)
    async def test_list_source_views_access_denied(self, mock_create_client, mock_ctx):
        """Test handling of AccessDeniedException."""
        mock_client = MagicMock()
        mock_client.list_source_views_for_billing_view.side_effect = ClientError(
            make_client_error_response(),
            'ListSourceViewsForBillingView',
        )
        mock_create_client.return_value = mock_client

        result = await list_source_views_for_billing_view(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED


@pytest.mark.asyncio
class TestGetResourcePolicy:
    """Tests for the get_resource_policy operation function."""

    @patch(PATCH_BVS_CLIENT)
    async def test_get_resource_policy_success(self, mock_create_client, mock_ctx):
        """Test successful retrieval of a resource policy."""
        sample_policy = json.dumps(
            {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Effect': 'Allow',
                        'Principal': {'AWS': 'arn:aws:iam::111111111111:root'},
                        'Action': 'billing:GetBillingView',
                        'Resource': BILLING_VIEW_ARN_CUSTOM,
                    }
                ],
            }
        )
        mock_client = MagicMock()
        mock_client.get_resource_policy.return_value = {
            'resourceArn': BILLING_VIEW_ARN_CUSTOM,
            'policy': sample_policy,
        }
        mock_create_client.return_value = mock_client

        result = await get_resource_policy(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['resource_arn'] == BILLING_VIEW_ARN_CUSTOM
        assert result['data']['policy'] == sample_policy

    @patch(PATCH_BVS_CLIENT)
    async def test_get_resource_policy_passes_resource_arn(self, mock_create_client, mock_ctx):
        """Test that the resource ARN is passed correctly to the API call."""
        mock_client = MagicMock()
        mock_client.get_resource_policy.return_value = {
            'resourceArn': BILLING_VIEW_ARN_CUSTOM,
            'policy': '{}',
        }
        mock_create_client.return_value = mock_client

        await get_resource_policy(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        call_kwargs = mock_client.get_resource_policy.call_args[1]
        assert call_kwargs['resourceArn'] == BILLING_VIEW_ARN_CUSTOM

    @patch(PATCH_BVS_CLIENT)
    async def test_get_resource_policy_none_policy(self, mock_create_client, mock_ctx):
        """Test retrieval when the policy field is missing from the response."""
        mock_client = MagicMock()
        mock_client.get_resource_policy.return_value = {
            'resourceArn': BILLING_VIEW_ARN_CUSTOM,
        }
        mock_create_client.return_value = mock_client

        result = await get_resource_policy(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['policy'] is None

    @patch(PATCH_BVS_CLIENT)
    async def test_get_resource_policy_access_denied(self, mock_create_client, mock_ctx):
        """Test handling of AccessDeniedException."""
        mock_client = MagicMock()
        mock_client.get_resource_policy.side_effect = ClientError(
            make_client_error_response(),
            'GetResourcePolicy',
        )
        mock_create_client.return_value = mock_client

        result = await get_resource_policy(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED

    @patch(PATCH_BVS_CLIENT)
    async def test_get_resource_policy_resource_not_found(self, mock_create_client, mock_ctx):
        """Test handling of ResourceNotFoundException."""
        mock_client = MagicMock()
        mock_client.get_resource_policy.side_effect = ClientError(
            make_client_error_response(
                code=ERROR_RESOURCE_NOT_FOUND,
                message=ERROR_RESOURCE_NOT_FOUND_MSG,
                http_status=HTTP_STATUS_NOT_FOUND,
            ),
            'GetResourcePolicy',
        )
        mock_create_client.return_value = mock_client

        result = await get_resource_policy(mock_ctx, BILLING_VIEW_ARN_CUSTOM)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_RESOURCE_NOT_FOUND
