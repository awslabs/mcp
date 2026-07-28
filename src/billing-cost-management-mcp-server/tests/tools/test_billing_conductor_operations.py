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

"""Unit tests for the billing_conductor_operations module."""

import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.billing_conductor_operations import (
    _format_billing_group_cost_report_results,
    _format_billing_group_cost_reports,
    _format_billing_groups,
    _format_custom_line_items,
    _format_linked_accounts,
    _format_pricing_plans,
    _format_pricing_rules,
    get_billing_group_cost_report,
    list_account_associations,
    list_billing_group_cost_reports,
    list_billing_groups,
    list_custom_line_item_versions,
    list_custom_line_items,
    list_pricing_plans,
    list_pricing_plans_associated_with_pricing_rule,
    list_pricing_rules,
    list_pricing_rules_associated_to_pricing_plan,
    list_resources_associated_to_custom_line_item,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


# --- Constants ---

ACCOUNT_ID_PRIMARY = '123456789012'
ACCOUNT_ID_PRIMARY_2 = '987654321098'
ACCOUNT_ID_LINKED_1 = '111111111111'
ACCOUNT_ID_LINKED_2 = '222222222222'
ACCOUNT_ID_LINKED_3 = '333333333333'
ACCOUNT_ID_LINKED_4 = '444444444444'
ARN_PREFIX = f'arn:aws:billingconductor::{ACCOUNT_ID_PRIMARY}'

BILLING_GROUP_ARN_1 = f'{ARN_PREFIX}:billinggroup/abcdef1234'
BILLING_GROUP_ARN_2 = f'{ARN_PREFIX}:billinggroup/ghijkl5678'

PRICING_PLAN_ARN_1 = f'{ARN_PREFIX}:pricingplan/abcdef1234'
PRICING_PLAN_ARN_2 = f'{ARN_PREFIX}:pricingplan/ghijkl5678'
PRICING_RULE_ARN_1 = f'{ARN_PREFIX}:pricingrule/abcdef1234'
PRICING_RULE_ARN_2 = f'{ARN_PREFIX}:pricingrule/ghijkl5678'
CUSTOM_LINE_ITEM_ARN_1 = f'{ARN_PREFIX}:customlineitem/abcdef1234'
CUSTOM_LINE_ITEM_ARN_2 = f'{ARN_PREFIX}:customlineitem/ghijkl5678'

RESPONSIBILITY_TRANSFER_ARN = (
    f'arn:aws:organizations::{ACCOUNT_ID_PRIMARY}:transfer/o-abc123/billing/inbound/rt-12345678'
)

BILLING_PERIOD = '2025-01'

NEXT_TOKEN_PAGE2 = 'page2token'
NEXT_TOKEN_MORE = 'more_results_token'
NEXT_TOKEN_CONTINUE = 'continue_from_here'

STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'

ERROR_ACCESS_DENIED = 'AccessDeniedException'

PATCH_BC_CLIENT = (
    'awslabs.billing_cost_management_mcp_server.tools.'
    'billing_conductor_operations._create_billing_conductor_client'
)


def _make_client_error_response(
    code='AccessDeniedException',
    message='You do not have sufficient access',
    http_status=403,
):
    """Build a standard ClientError response dict for tests."""
    return {
        'Error': {'Code': code, 'Message': message},
        'ResponseMetadata': {'RequestId': 'test-request-id', 'HTTPStatusCode': http_status},
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
def sample_billing_groups():
    """Sample billing group data from AWS API."""
    return [
        {
            'Arn': BILLING_GROUP_ARN_1,
            'Name': 'TestBillingGroup1',
            'Description': 'A test billing group',
            'BillingGroupType': 'STANDARD',
            'Status': 'ACTIVE',
            'StatusReason': '',
            'PrimaryAccountId': ACCOUNT_ID_PRIMARY,
            'Size': 5,
            'ComputationPreference': {
                'PricingPlanArn': PRICING_PLAN_ARN_1,
            },
            'AccountGrouping': {
                'AutoAssociate': True,
            },
            'CreationTime': 1700000000,
            'LastModifiedTime': 1700100000,
        },
        {
            'Arn': BILLING_GROUP_ARN_2,
            'Name': 'TestBillingGroup2',
            'Description': 'Another test billing group',
            'BillingGroupType': 'TRANSFER_BILLING',
            'Status': 'PENDING',
            'StatusReason': 'Waiting for approval',
            'PrimaryAccountId': ACCOUNT_ID_PRIMARY_2,
            'Size': 2,
            'AccountGrouping': {
                'AutoAssociate': False,
                'ResponsibilityTransferArn': RESPONSIBILITY_TRANSFER_ARN,
            },
            'CreationTime': 1700200000,
            'LastModifiedTime': 1700300000,
        },
    ]


# --- Billing Group Format Tests ---


class TestFormatBillingGroups:
    """Tests for the _format_billing_groups function."""

    def test_format_empty_list(self):
        """Test formatting an empty list of billing groups."""
        result = _format_billing_groups([])
        assert result == []

    def test_format_basic_fields(self, sample_billing_groups):
        """Test that basic fields are formatted correctly."""
        result = _format_billing_groups(sample_billing_groups)

        assert len(result) == 2
        assert result[0]['arn'] == BILLING_GROUP_ARN_1
        assert result[0]['name'] == 'TestBillingGroup1'
        assert result[0]['description'] == 'A test billing group'
        assert result[0]['billing_group_type'] == 'STANDARD'
        assert result[0]['status'] == 'ACTIVE'
        assert result[0]['primary_account_id'] == ACCOUNT_ID_PRIMARY
        assert result[0]['size'] == 5

    def test_format_computation_preference(self, sample_billing_groups):
        """Test that computation preference is formatted correctly."""
        result = _format_billing_groups(sample_billing_groups)

        assert 'computation_preference' in result[0]
        assert result[0]['computation_preference']['pricing_plan_arn'] == PRICING_PLAN_ARN_1

    def test_format_account_grouping(self, sample_billing_groups):
        """Test that account grouping is formatted correctly."""
        result = _format_billing_groups(sample_billing_groups)

        # First group: auto_associate only
        assert 'account_grouping' in result[0]
        assert result[0]['account_grouping']['auto_associate'] is True

        # Second group: auto_associate + responsibility_transfer_arn
        assert 'account_grouping' in result[1]
        assert result[1]['account_grouping']['auto_associate'] is False
        assert 'responsibility_transfer_arn' in result[1]['account_grouping']

    def test_format_timestamps(self, sample_billing_groups):
        """Test that timestamps are formatted correctly."""
        result = _format_billing_groups(sample_billing_groups)

        assert 'creation_time' in result[0]
        assert 'last_modified_time' in result[0]

    def test_format_missing_optional_fields(self):
        """Test formatting billing groups with missing optional fields."""
        minimal_bg = [
            {
                'Arn': BILLING_GROUP_ARN_1,
                'Name': 'MinimalGroup',
                'Status': 'ACTIVE',
            }
        ]
        result = _format_billing_groups(minimal_bg)

        assert len(result) == 1
        assert result[0]['arn'] == BILLING_GROUP_ARN_1
        assert result[0]['name'] == 'MinimalGroup'
        assert 'computation_preference' not in result[0]
        assert 'account_grouping' not in result[0]
        assert 'creation_time' not in result[0]


# --- List Billing Groups Operation Tests ---


@pytest.mark.asyncio
class TestListBillingGroups:
    """Tests for the list_billing_groups operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_success(
        self, mock_create_client, mock_ctx, sample_billing_groups
    ):
        """Test successful listing of billing groups."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.return_value = {
            'BillingGroups': sample_billing_groups,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_groups(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert len(result['data']['billing_groups']) == 2
        assert 'next_token' not in result['data']

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_with_billing_period(
        self, mock_create_client, mock_ctx, sample_billing_groups
    ):
        """Test listing billing groups with a specific billing period."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.return_value = {
            'BillingGroups': sample_billing_groups,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_groups(mock_ctx, BILLING_PERIOD, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['billing_period'] == BILLING_PERIOD

        call_kwargs = mock_client.list_billing_groups.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_with_filters(
        self, mock_create_client, mock_ctx, sample_billing_groups
    ):
        """Test listing billing groups with filters."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.return_value = {
            'BillingGroups': [sample_billing_groups[0]],
        }
        mock_create_client.return_value = mock_client

        filters_json = json.dumps({'Statuses': ['ACTIVE'], 'BillingGroupTypes': ['STANDARD']})
        result = await list_billing_groups(mock_ctx, None, filters_json, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1

        call_kwargs = mock_client.list_billing_groups.call_args[1]
        assert call_kwargs['Filters'] == {
            'Statuses': ['ACTIVE'],
            'BillingGroupTypes': ['STANDARD'],
        }

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_pagination(
        self, mock_create_client, mock_ctx, sample_billing_groups
    ):
        """Test listing billing groups with pagination across multiple pages."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.side_effect = [
            {
                'BillingGroups': [sample_billing_groups[0]],
                'NextToken': NEXT_TOKEN_PAGE2,
            },
            {
                'BillingGroups': [sample_billing_groups[1]],
            },
        ]
        mock_create_client.return_value = mock_client

        result = await list_billing_groups(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert mock_client.list_billing_groups.call_count == 2
        assert 'next_token' not in result['data']

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_max_pages_stops_pagination(
        self, mock_create_client, mock_ctx, sample_billing_groups
    ):
        """Test that max_pages limits the number of API calls and returns next_token."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.return_value = {
            'BillingGroups': [sample_billing_groups[0]],
            'NextToken': NEXT_TOKEN_MORE,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_groups(mock_ctx, None, None, 1, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert mock_client.list_billing_groups.call_count == 1
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_with_next_token(
        self, mock_create_client, mock_ctx, sample_billing_groups
    ):
        """Test continuing pagination with a next_token from a previous response."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.return_value = {
            'BillingGroups': [sample_billing_groups[1]],
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_groups(mock_ctx, None, None, 10, NEXT_TOKEN_CONTINUE)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert 'next_token' not in result['data']

        call_kwargs = mock_client.list_billing_groups.call_args[1]
        assert call_kwargs['NextToken'] == NEXT_TOKEN_CONTINUE

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_empty_result(self, mock_create_client, mock_ctx):
        """Test listing billing groups when none exist."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.return_value = {
            'BillingGroups': [],
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_groups(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 0
        assert result['data']['billing_groups'] == []
        assert 'next_token' not in result['data']

    async def test_list_billing_groups_invalid_filters(self, mock_ctx):
        """Test listing billing groups with invalid filter JSON."""
        result = await list_billing_groups(mock_ctx, None, 'not-valid-json', 10, None)

        assert result['status'] == STATUS_ERROR

    @patch(PATCH_BC_CLIENT)
    async def test_list_billing_groups_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_billing_groups.side_effect = ClientError(
            _make_client_error_response(),
            'ListBillingGroups',
        )
        mock_create_client.return_value = mock_client

        result = await list_billing_groups(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED


# --- Custom Line Item Fixtures ---


@pytest.fixture
def sample_custom_line_items():
    """Sample custom line item data from AWS API."""
    return [
        {
            'Arn': CUSTOM_LINE_ITEM_ARN_1,
            'Name': 'SupportFee',
            'Description': 'Monthly support fee',
            'AccountId': ACCOUNT_ID_PRIMARY,
            'BillingGroupArn': BILLING_GROUP_ARN_1,
            'CurrencyCode': 'USD',
            'AssociationSize': 3,
            'ChargeDetails': {
                'Type': 'FEE',
                'Flat': {'ChargeValue': 100.0},
            },
            'CreationTime': 1700000000,
            'LastModifiedTime': 1700100000,
        },
        {
            'Arn': CUSTOM_LINE_ITEM_ARN_2,
            'Name': 'SharedDiscount',
            'Description': 'Shared RI discount',
            'AccountId': ACCOUNT_ID_PRIMARY,
            'BillingGroupArn': BILLING_GROUP_ARN_2,
            'CurrencyCode': 'USD',
            'ChargeDetails': {
                'Type': 'CREDIT',
                'Percentage': {'PercentageValue': 15.0},
            },
            'PresentationDetails': {'Service': 'Amazon EC2'},
            'CreationTime': 1700200000,
            'LastModifiedTime': 1700300000,
        },
    ]


# --- Custom Line Item Format Tests ---


class TestFormatCustomLineItems:
    """Tests for the _format_custom_line_items function."""

    def test_format_empty_list(self):
        """Test formatting an empty list of custom line items."""
        result = _format_custom_line_items([])
        assert result == []

    def test_format_basic_fields(self, sample_custom_line_items):
        """Test that basic fields are formatted correctly."""
        result = _format_custom_line_items(sample_custom_line_items)

        assert len(result) == 2
        assert result[0]['arn'] == CUSTOM_LINE_ITEM_ARN_1
        assert result[0]['name'] == 'SupportFee'
        assert result[0]['description'] == 'Monthly support fee'
        assert result[0]['currency_code'] == 'USD'

    def test_format_charge_details_flat(self, sample_custom_line_items):
        """Test that flat charge details are formatted correctly."""
        result = _format_custom_line_items(sample_custom_line_items)

        assert 'charge_details' in result[0]
        assert result[0]['charge_details']['type'] == 'FEE'
        assert result[0]['charge_details']['flat']['charge_value'] == 100.0

    def test_format_charge_details_percentage(self, sample_custom_line_items):
        """Test that percentage charge details are formatted correctly."""
        result = _format_custom_line_items(sample_custom_line_items)

        assert 'charge_details' in result[1]
        assert result[1]['charge_details']['type'] == 'CREDIT'
        assert result[1]['charge_details']['percentage']['percentage_value'] == 15.0

    def test_format_presentation_details(self, sample_custom_line_items):
        """Test that presentation details are formatted correctly."""
        result = _format_custom_line_items(sample_custom_line_items)

        assert 'presentation_details' not in result[0]
        assert 'presentation_details' in result[1]
        assert result[1]['presentation_details']['service'] == 'Amazon EC2'

    def test_format_timestamps(self, sample_custom_line_items):
        """Test that timestamps are formatted correctly."""
        result = _format_custom_line_items(sample_custom_line_items)

        assert 'creation_time' in result[0]
        assert 'last_modified_time' in result[0]

    def test_format_without_timestamps(self):
        """Test formatting custom line items without timestamps."""
        items = [{'Arn': 'arn:test'}]
        result = _format_custom_line_items(items)
        assert 'creation_time' not in result[0]
        assert 'last_modified_time' not in result[0]

    def test_format_charge_details_with_line_item_filters(self):
        """Test formatting charge details that include line item filters."""
        items = [
            {
                'Arn': 'arn:test',
                'ChargeDetails': {
                    'Type': 'FEE',
                    'Percentage': {'PercentageValue': 10.0},
                    'LineItemFilters': [
                        {
                            'Attribute': 'LINE_ITEM_TYPE',
                            'MatchOption': 'NOT_EQUAL',
                            'Values': ['SAVINGS_PLAN_NEGATION'],
                        },
                        {
                            'Attribute': 'USAGE_TYPE',
                            'MatchOption': 'EQUAL',
                            'AttributeValues': ['BoxUsage'],
                        },
                    ],
                },
            }
        ]
        result = _format_custom_line_items(items)
        charge = result[0]['charge_details']
        assert 'line_item_filters' in charge
        filters = charge['line_item_filters']
        assert len(filters) == 2
        assert filters[0]['attribute'] == 'LINE_ITEM_TYPE'
        assert filters[0]['values'] == ['SAVINGS_PLAN_NEGATION']
        assert filters[1]['attribute_values'] == ['BoxUsage']


# --- List Custom Line Items Operation Tests ---


@pytest.mark.asyncio
class TestListCustomLineItems:
    """Tests for the list_custom_line_items operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_list_custom_line_items_success(
        self, mock_create_client, mock_ctx, sample_custom_line_items
    ):
        """Test successful listing of custom line items."""
        mock_client = MagicMock()
        mock_client.list_custom_line_items.return_value = {
            'CustomLineItems': sample_custom_line_items,
        }
        mock_create_client.return_value = mock_client

        result = await list_custom_line_items(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert len(result['data']['custom_line_items']) == 2

    @patch(PATCH_BC_CLIENT)
    async def test_list_custom_line_items_with_billing_period(
        self, mock_create_client, mock_ctx, sample_custom_line_items
    ):
        """Test listing custom line items with a billing period."""
        mock_client = MagicMock()
        mock_client.list_custom_line_items.return_value = {
            'CustomLineItems': sample_custom_line_items,
        }
        mock_create_client.return_value = mock_client

        result = await list_custom_line_items(mock_ctx, BILLING_PERIOD, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_custom_line_items.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_list_custom_line_items_with_filters(
        self, mock_create_client, mock_ctx, sample_custom_line_items
    ):
        """Test listing custom line items with filters."""
        mock_client = MagicMock()
        mock_client.list_custom_line_items.return_value = {
            'CustomLineItems': [sample_custom_line_items[0]],
        }
        mock_create_client.return_value = mock_client

        filters_json = json.dumps({'Names': ['SupportFee']})
        result = await list_custom_line_items(mock_ctx, None, filters_json, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1

    @patch(PATCH_BC_CLIENT)
    async def test_list_custom_line_items_empty(self, mock_create_client, mock_ctx):
        """Test listing custom line items when none exist."""
        mock_client = MagicMock()
        mock_client.list_custom_line_items.return_value = {'CustomLineItems': []}
        mock_create_client.return_value = mock_client

        result = await list_custom_line_items(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 0

    @patch(PATCH_BC_CLIENT)
    async def test_list_custom_line_items_max_pages_next_token(self, mock_create_client, mock_ctx):
        """Test that next_token is returned when max_pages reached."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_custom_line_items.return_value = {
            'CustomLineItems': [{'Arn': 'a1'}],
            'NextToken': NEXT_TOKEN_MORE,
        }
        result = await list_custom_line_items(mock_ctx, max_pages=1)
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_list_custom_line_items_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_custom_line_items.side_effect = ClientError(
            _make_client_error_response(), 'ListCustomLineItems'
        )
        mock_create_client.return_value = mock_client

        result = await list_custom_line_items(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED


# --- List Custom Line Item Versions Operation Tests ---


@pytest.mark.asyncio
class TestListCustomLineItemVersions:
    """Tests for the list_custom_line_item_versions operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_success(self, mock_create_client, mock_ctx):
        """Test successful listing of custom line item versions."""
        mock_client = MagicMock()
        mock_client.list_custom_line_item_versions.return_value = {
            'CustomLineItemVersions': [
                {
                    'Arn': CUSTOM_LINE_ITEM_ARN_1,
                    'Name': 'SupportFee',
                    'StartBillingPeriod': '2025-01',
                    'EndBillingPeriod': '2025-06',
                }
            ],
        }
        mock_create_client.return_value = mock_client

        result = await list_custom_line_item_versions(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1, None, 10, None
        )

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert result['data']['arn'] == CUSTOM_LINE_ITEM_ARN_1

    @patch(PATCH_BC_CLIENT)
    async def test_max_pages_next_token(self, mock_create_client, mock_ctx):
        """Test next_token returned when max_pages reached."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_custom_line_item_versions.return_value = {
            'CustomLineItemVersions': [
                {
                    'Arn': 'a1',
                    'ChargeDetails': {'Type': 'FEE', 'Flat': {'ChargeValue': 50.0}},
                    'StartTime': 1700000000,
                    'CreationTime': 1700000000,
                    'LastModifiedTime': 1700100000,
                }
            ],
            'NextToken': NEXT_TOKEN_MORE,
        }
        result = await list_custom_line_item_versions(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1, None, 1, None
        )
        assert result['data']['next_token'] == NEXT_TOKEN_MORE
        assert result['data']['custom_line_item_versions'][0]['charge_details']['type'] == 'FEE'

    @patch(PATCH_BC_CLIENT)
    async def test_with_filters(self, mock_create_client, mock_ctx):
        """Test with BillingPeriodRange filter."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_custom_line_item_versions.return_value = {'CustomLineItemVersions': []}
        filters_str = '{"BillingPeriodRange": {"StartBillingPeriod": "2025-01"}}'
        result = await list_custom_line_item_versions(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1, filters_str, 10, None
        )
        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_custom_line_item_versions.call_args[1]
        assert 'Filters' in call_kwargs

    @patch(PATCH_BC_CLIENT)
    async def test_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_custom_line_item_versions.side_effect = ClientError(
            _make_client_error_response(), 'ListCustomLineItemVersions'
        )
        mock_create_client.return_value = mock_client

        result = await list_custom_line_item_versions(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1, None, 10, None
        )

        assert result['status'] == STATUS_ERROR


# --- List Resources Associated to Custom Line Item Operation Tests ---


@pytest.mark.asyncio
class TestListResourcesAssociatedToCustomLineItem:
    """Tests for the list_resources_associated_to_custom_line_item operation."""

    @patch(PATCH_BC_CLIENT)
    async def test_success(self, mock_create_client, mock_ctx):
        """Test successful listing of associated resources."""
        mock_client = MagicMock()
        mock_client.list_resources_associated_to_custom_line_item.return_value = {
            'AssociatedResources': [
                {
                    'Arn': BILLING_GROUP_ARN_1,
                    'Relationship': 'PARENT',
                    'EndBillingPeriod': '2025-12',
                }
            ],
        }
        mock_create_client.return_value = mock_client

        result = await list_resources_associated_to_custom_line_item(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1
        )

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert result['data']['arn'] == CUSTOM_LINE_ITEM_ARN_1

    @patch(PATCH_BC_CLIENT)
    async def test_with_billing_period(self, mock_create_client, mock_ctx):
        """Test with billing period parameter."""
        mock_client = MagicMock()
        mock_client.list_resources_associated_to_custom_line_item.return_value = {
            'AssociatedResources': [],
        }
        mock_create_client.return_value = mock_client

        result = await list_resources_associated_to_custom_line_item(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1, billing_period=BILLING_PERIOD
        )

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_resources_associated_to_custom_line_item.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_max_pages_next_token(self, mock_create_client, mock_ctx):
        """Test next_token returned when max_pages reached."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_resources_associated_to_custom_line_item.return_value = {
            'AssociatedResources': [{'Arn': 'a1'}],
            'NextToken': NEXT_TOKEN_MORE,
        }
        result = await list_resources_associated_to_custom_line_item(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1, max_pages=1
        )
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_with_filters(self, mock_create_client, mock_ctx):
        """Test with Relationship filter."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_resources_associated_to_custom_line_item.return_value = {
            'AssociatedResources': []
        }
        filters_str = '{"Relationship": "CHILD"}'
        await list_resources_associated_to_custom_line_item(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1, filters=filters_str
        )
        call_kwargs = mock_client.list_resources_associated_to_custom_line_item.call_args[1]
        assert call_kwargs['Filters'] == {'Relationship': 'CHILD'}

    @patch(PATCH_BC_CLIENT)
    async def test_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_resources_associated_to_custom_line_item.side_effect = ClientError(
            _make_client_error_response(),
            'ListResourcesAssociatedToCustomLineItem',
        )
        mock_create_client.return_value = mock_client

        result = await list_resources_associated_to_custom_line_item(
            mock_ctx, CUSTOM_LINE_ITEM_ARN_1
        )

        assert result['status'] == STATUS_ERROR


# --- Pricing Rules/Plans Fixtures ---


@pytest.fixture
def sample_pricing_rules():
    """Sample pricing rule data from AWS API."""
    return [
        {
            'Arn': PRICING_RULE_ARN_1,
            'Name': 'TestRule1',
            'Description': 'A 10% markup',
            'Type': 'MARKUP',
            'Scope': 'GLOBAL',
            'ModifierPercentage': 10.0,
            'AssociatedPricingPlanCount': 1,
            'Service': 'AmazonEC2',
            'CreationTime': 1700000000,
            'LastModifiedTime': 1700100000,
        },
        {
            'Arn': PRICING_RULE_ARN_2,
            'Name': 'TestRule2',
            'Description': 'A 5% discount',
            'Type': 'DISCOUNT',
            'Scope': 'SERVICE',
            'ModifierPercentage': 5.0,
            'AssociatedPricingPlanCount': 2,
            'Tiering': {
                'FreeTier': {'Activated': True},
            },
            'CreationTime': 1700200000,
            'LastModifiedTime': 1700300000,
        },
    ]


@pytest.fixture
def sample_pricing_plans():
    """Sample pricing plan data from AWS API."""
    return [
        {
            'Arn': PRICING_PLAN_ARN_1,
            'Name': 'TestPlan1',
            'Description': 'A test pricing plan',
            'Size': 2,
            'CreationTime': 1700000000,
            'LastModifiedTime': 1700100000,
        },
        {
            'Arn': PRICING_PLAN_ARN_2,
            'Name': 'TestPlan2',
            'Description': 'Another pricing plan',
            'Size': 3,
            'CreationTime': 1700200000,
            'LastModifiedTime': 1700300000,
        },
    ]


# --- Pricing Format Tests ---


class TestFormatPricingRules:
    """Tests for the _format_pricing_rules function."""

    def test_format_empty_list(self):
        """Test formatting an empty list of pricing rules."""
        result = _format_pricing_rules([])
        assert result == []

    def test_format_basic_fields(self, sample_pricing_rules):
        """Test that basic fields are formatted correctly."""
        result = _format_pricing_rules(sample_pricing_rules)

        assert len(result) == 2
        assert result[0]['arn'] == PRICING_RULE_ARN_1
        assert result[0]['name'] == 'TestRule1'
        assert result[0]['type'] == 'MARKUP'
        assert result[0]['scope'] == 'GLOBAL'
        assert result[0]['modifier_percentage'] == 10.0

    def test_format_tiering(self, sample_pricing_rules):
        """Test that tiering is formatted correctly."""
        result = _format_pricing_rules(sample_pricing_rules)

        assert 'tiering' not in result[0]  # First has no Tiering
        assert 'tiering' in result[1]
        assert result[1]['tiering']['free_tier']['activated'] is True

    def test_format_timestamps(self, sample_pricing_rules):
        """Test that timestamps are formatted correctly."""
        result = _format_pricing_rules(sample_pricing_rules)

        assert 'creation_time' in result[0]
        assert 'last_modified_time' in result[0]

    def test_format_minimal_rule(self):
        """Test formatting pricing rules with minimal fields."""
        minimal = [{'Arn': PRICING_RULE_ARN_1, 'Name': 'Min', 'Type': 'MARKUP'}]
        result = _format_pricing_rules(minimal)

        assert len(result) == 1
        assert 'tiering' not in result[0]
        assert 'creation_time' not in result[0]


class TestFormatPricingPlans:
    """Tests for the _format_pricing_plans function."""

    def test_format_empty_list(self):
        """Test formatting an empty list of pricing plans."""
        result = _format_pricing_plans([])
        assert result == []

    def test_format_basic_fields(self, sample_pricing_plans):
        """Test that basic fields are formatted correctly."""
        result = _format_pricing_plans(sample_pricing_plans)

        assert len(result) == 2
        assert result[0]['arn'] == PRICING_PLAN_ARN_1
        assert result[0]['name'] == 'TestPlan1'
        assert result[0]['description'] == 'A test pricing plan'
        assert result[0]['size'] == 2

    def test_format_timestamps(self, sample_pricing_plans):
        """Test that timestamps are formatted correctly."""
        result = _format_pricing_plans(sample_pricing_plans)

        assert 'creation_time' in result[0]
        assert 'last_modified_time' in result[0]


# --- List Pricing Rules Operation Tests ---


@pytest.mark.asyncio
class TestListPricingRules:
    """Tests for the list_pricing_rules operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_rules_success(
        self, mock_create_client, mock_ctx, sample_pricing_rules
    ):
        """Test successful listing of pricing rules."""
        mock_client = MagicMock()
        mock_client.list_pricing_rules.return_value = {
            'PricingRules': sample_pricing_rules,
        }
        mock_create_client.return_value = mock_client

        result = await list_pricing_rules(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert len(result['data']['pricing_rules']) == 2

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_rules_with_billing_period(
        self, mock_create_client, mock_ctx, sample_pricing_rules
    ):
        """Test listing pricing rules with a billing period."""
        mock_client = MagicMock()
        mock_client.list_pricing_rules.return_value = {
            'PricingRules': sample_pricing_rules,
        }
        mock_create_client.return_value = mock_client

        result = await list_pricing_rules(mock_ctx, BILLING_PERIOD, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_pricing_rules.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_rules_empty(self, mock_create_client, mock_ctx):
        """Test listing pricing rules when none exist."""
        mock_client = MagicMock()
        mock_client.list_pricing_rules.return_value = {'PricingRules': []}
        mock_create_client.return_value = mock_client

        result = await list_pricing_rules(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 0

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_rules_max_pages_next_token(self, mock_create_client, mock_ctx):
        """Test next_token returned when max_pages reached."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_pricing_rules.return_value = {
            'PricingRules': [{'Arn': 'a1'}],
            'NextToken': NEXT_TOKEN_MORE,
        }
        result = await list_pricing_rules(mock_ctx, max_pages=1)
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_rules_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_pricing_rules.side_effect = ClientError(
            _make_client_error_response(), 'ListPricingRules'
        )
        mock_create_client.return_value = mock_client

        result = await list_pricing_rules(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED


# --- List Pricing Plans Operation Tests ---


@pytest.mark.asyncio
class TestListPricingPlans:
    """Tests for the list_pricing_plans operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_plans_success(
        self, mock_create_client, mock_ctx, sample_pricing_plans
    ):
        """Test successful listing of pricing plans."""
        mock_client = MagicMock()
        mock_client.list_pricing_plans.return_value = {
            'PricingPlans': sample_pricing_plans,
        }
        mock_create_client.return_value = mock_client

        result = await list_pricing_plans(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert len(result['data']['pricing_plans']) == 2

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_plans_with_billing_period(
        self, mock_create_client, mock_ctx, sample_pricing_plans
    ):
        """Test listing pricing plans with a billing period."""
        mock_client = MagicMock()
        mock_client.list_pricing_plans.return_value = {
            'PricingPlans': sample_pricing_plans,
        }
        mock_create_client.return_value = mock_client

        result = await list_pricing_plans(mock_ctx, BILLING_PERIOD, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_pricing_plans.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_plans_max_pages_next_token(self, mock_create_client, mock_ctx):
        """Test next_token returned when max_pages reached."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_pricing_plans.return_value = {
            'PricingPlans': [{'Arn': 'a1'}],
            'NextToken': NEXT_TOKEN_MORE,
        }
        result = await list_pricing_plans(mock_ctx, max_pages=1)
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_list_pricing_plans_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_pricing_plans.side_effect = ClientError(
            _make_client_error_response(), 'ListPricingPlans'
        )
        mock_create_client.return_value = mock_client

        result = await list_pricing_plans(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED


# --- List Pricing Rules Associated To Pricing Plan Operation Tests ---


@pytest.mark.asyncio
class TestListPricingRulesAssociatedToPricingPlan:
    """Tests for the list_pricing_rules_associated_to_pricing_plan operation."""

    @patch(PATCH_BC_CLIENT)
    async def test_success(self, mock_create_client, mock_ctx):
        """Test successful listing of pricing rules for a plan."""
        mock_client = MagicMock()
        mock_client.list_pricing_rules_associated_to_pricing_plan.return_value = {
            'PricingRuleArns': [PRICING_RULE_ARN_1, PRICING_RULE_ARN_2],
            'BillingPeriod': BILLING_PERIOD,
            'PricingPlanArn': PRICING_PLAN_ARN_1,
        }
        mock_create_client.return_value = mock_client

        result = await list_pricing_rules_associated_to_pricing_plan(mock_ctx, PRICING_PLAN_ARN_1)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert PRICING_RULE_ARN_1 in result['data']['pricing_rule_arns']

    @patch(PATCH_BC_CLIENT)
    async def test_with_billing_period(self, mock_create_client, mock_ctx):
        """Test with billing period parameter."""
        mock_client = MagicMock()
        mock_client.list_pricing_rules_associated_to_pricing_plan.return_value = {
            'PricingRuleArns': [PRICING_RULE_ARN_1],
            'BillingPeriod': BILLING_PERIOD,
            'PricingPlanArn': PRICING_PLAN_ARN_1,
        }
        mock_create_client.return_value = mock_client

        result = await list_pricing_rules_associated_to_pricing_plan(
            mock_ctx, PRICING_PLAN_ARN_1, billing_period=BILLING_PERIOD
        )

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.list_pricing_rules_associated_to_pricing_plan.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_max_pages_next_token(self, mock_create_client, mock_ctx):
        """Test next_token returned when max_pages reached."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_pricing_rules_associated_to_pricing_plan.return_value = {
            'PricingRuleArns': ['a1'],
            'NextToken': NEXT_TOKEN_MORE,
        }
        result = await list_pricing_rules_associated_to_pricing_plan(
            mock_ctx, PRICING_PLAN_ARN_1, max_pages=1
        )
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_pricing_rules_associated_to_pricing_plan.side_effect = ClientError(
            _make_client_error_response(), 'ListPricingRulesAssociatedToPricingPlan'
        )
        mock_create_client.return_value = mock_client

        result = await list_pricing_rules_associated_to_pricing_plan(mock_ctx, PRICING_PLAN_ARN_1)

        assert result['status'] == STATUS_ERROR


# --- List Pricing Plans Associated With Pricing Rule Operation Tests ---


@pytest.mark.asyncio
class TestListPricingPlansAssociatedWithPricingRule:
    """Tests for the list_pricing_plans_associated_with_pricing_rule operation."""

    @patch(PATCH_BC_CLIENT)
    async def test_success(self, mock_create_client, mock_ctx):
        """Test successful listing of pricing plans for a rule."""
        mock_client = MagicMock()
        mock_client.list_pricing_plans_associated_with_pricing_rule.return_value = {
            'PricingPlanArns': [PRICING_PLAN_ARN_1, PRICING_PLAN_ARN_2],
            'BillingPeriod': BILLING_PERIOD,
            'PricingRuleArn': PRICING_RULE_ARN_1,
        }
        mock_create_client.return_value = mock_client

        result = await list_pricing_plans_associated_with_pricing_rule(
            mock_ctx, PRICING_RULE_ARN_1
        )

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert PRICING_PLAN_ARN_1 in result['data']['pricing_plan_arns']

    @patch(PATCH_BC_CLIENT)
    async def test_max_pages_next_token(self, mock_create_client, mock_ctx):
        """Test next_token returned when max_pages reached."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_client.list_pricing_plans_associated_with_pricing_rule.return_value = {
            'PricingPlanArns': ['a1'],
            'NextToken': NEXT_TOKEN_MORE,
        }
        result = await list_pricing_plans_associated_with_pricing_rule(
            mock_ctx, PRICING_RULE_ARN_1, max_pages=1
        )
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_pricing_plans_associated_with_pricing_rule.side_effect = ClientError(
            _make_client_error_response(), 'ListPricingPlansAssociatedWithPricingRule'
        )
        mock_create_client.return_value = mock_client

        result = await list_pricing_plans_associated_with_pricing_rule(
            mock_ctx, PRICING_RULE_ARN_1
        )

        assert result['status'] == STATUS_ERROR


# --- Billing Group Cost Report Fixtures ---


@pytest.fixture
def sample_cost_reports():
    """Sample billing group cost report data from AWS API."""
    return [
        {
            'Arn': BILLING_GROUP_ARN_1,
            'AWSCost': '1000.00',
            'ProformaCost': '900.00',
            'Margin': '100.00',
            'MarginPercentage': '10.0',
            'Currency': 'USD',
        },
        {
            'Arn': BILLING_GROUP_ARN_2,
            'AWSCost': '500.00',
            'ProformaCost': '475.00',
            'Margin': '25.00',
            'MarginPercentage': '5.0',
            'Currency': 'USD',
        },
    ]


@pytest.fixture
def sample_cost_report_results():
    """Sample billing group cost report result data from AWS API."""
    return [
        {
            'Arn': BILLING_GROUP_ARN_1,
            'AWSCost': '200.00',
            'ProformaCost': '180.00',
            'Margin': '20.00',
            'MarginPercentage': '10.0',
            'Currency': 'USD',
            'Attributes': [
                {'Key': 'PRODUCT_NAME', 'Value': 'Amazon S3'},
            ],
        },
        {
            'Arn': BILLING_GROUP_ARN_1,
            'AWSCost': '800.00',
            'ProformaCost': '720.00',
            'Margin': '80.00',
            'MarginPercentage': '10.0',
            'Currency': 'USD',
            'Attributes': [
                {'Key': 'PRODUCT_NAME', 'Value': 'Amazon EC2'},
            ],
        },
    ]


# --- Billing Group Cost Report Format Tests ---


class TestFormatBillingGroupCostReports:
    """Tests for the _format_billing_group_cost_reports function."""

    def test_format_empty_list(self):
        """Test formatting an empty list of cost reports."""
        result = _format_billing_group_cost_reports([])
        assert result == []

    def test_format_basic_fields(self, sample_cost_reports):
        """Test that basic fields are formatted correctly."""
        result = _format_billing_group_cost_reports(sample_cost_reports)

        assert len(result) == 2
        assert result[0]['arn'] == BILLING_GROUP_ARN_1
        assert result[0]['aws_cost'] == '1000.00'
        assert result[0]['proforma_cost'] == '900.00'
        assert result[0]['margin'] == '100.00'
        assert result[0]['margin_percentage'] == '10.0'
        assert result[0]['currency'] == 'USD'


class TestFormatBillingGroupCostReportResults:
    """Tests for the _format_billing_group_cost_report_results function."""

    def test_format_empty_list(self):
        """Test formatting an empty list of cost report results."""
        result = _format_billing_group_cost_report_results([])
        assert result == []

    def test_format_with_attributes(self, sample_cost_report_results):
        """Test that attributes are formatted correctly."""
        result = _format_billing_group_cost_report_results(sample_cost_report_results)

        assert len(result) == 2
        assert result[0]['arn'] == BILLING_GROUP_ARN_1
        assert result[0]['aws_cost'] == '200.00'
        assert 'attributes' in result[0]
        assert result[0]['attributes'][0]['key'] == 'PRODUCT_NAME'
        assert result[0]['attributes'][0]['value'] == 'Amazon S3'

    def test_format_without_attributes(self):
        """Test formatting results without attributes."""
        minimal_result = [
            {
                'Arn': BILLING_GROUP_ARN_1,
                'AWSCost': '100.00',
                'ProformaCost': '90.00',
                'Margin': '10.00',
                'MarginPercentage': '10.0',
                'Currency': 'USD',
            }
        ]
        result = _format_billing_group_cost_report_results(minimal_result)

        assert len(result) == 1
        assert 'attributes' not in result[0]


# --- List Billing Group Cost Reports Operation Tests ---


@pytest.mark.asyncio
class TestListBillingGroupCostReports:
    """Tests for the list_billing_group_cost_reports operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_list_cost_reports_success(
        self, mock_create_client, mock_ctx, sample_cost_reports
    ):
        """Test successful listing of billing group cost reports."""
        mock_client = MagicMock()
        mock_client.list_billing_group_cost_reports.return_value = {
            'BillingGroupCostReports': sample_cost_reports,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_group_cost_reports(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert len(result['data']['billing_group_cost_reports']) == 2

    @patch(PATCH_BC_CLIENT)
    async def test_list_cost_reports_with_billing_period(
        self, mock_create_client, mock_ctx, sample_cost_reports
    ):
        """Test listing cost reports with a specific billing period."""
        mock_client = MagicMock()
        mock_client.list_billing_group_cost_reports.return_value = {
            'BillingGroupCostReports': sample_cost_reports,
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_group_cost_reports(mock_ctx, BILLING_PERIOD, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['billing_period'] == BILLING_PERIOD

        call_kwargs = mock_client.list_billing_group_cost_reports.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_list_cost_reports_with_filters(
        self, mock_create_client, mock_ctx, sample_cost_reports
    ):
        """Test listing cost reports with filters."""
        mock_client = MagicMock()
        mock_client.list_billing_group_cost_reports.return_value = {
            'BillingGroupCostReports': [sample_cost_reports[0]],
        }
        mock_create_client.return_value = mock_client

        filters_json = json.dumps({'BillingGroupArns': [BILLING_GROUP_ARN_1]})
        result = await list_billing_group_cost_reports(mock_ctx, None, filters_json, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1

    @patch(PATCH_BC_CLIENT)
    async def test_list_cost_reports_pagination(
        self, mock_create_client, mock_ctx, sample_cost_reports
    ):
        """Test listing cost reports with pagination."""
        mock_client = MagicMock()
        mock_client.list_billing_group_cost_reports.side_effect = [
            {
                'BillingGroupCostReports': [sample_cost_reports[0]],
                'NextToken': NEXT_TOKEN_PAGE2,
            },
            {
                'BillingGroupCostReports': [sample_cost_reports[1]],
            },
        ]
        mock_create_client.return_value = mock_client

        result = await list_billing_group_cost_reports(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert mock_client.list_billing_group_cost_reports.call_count == 2

    @patch(PATCH_BC_CLIENT)
    async def test_list_cost_reports_empty_result(self, mock_create_client, mock_ctx):
        """Test listing cost reports when none exist."""
        mock_client = MagicMock()
        mock_client.list_billing_group_cost_reports.return_value = {
            'BillingGroupCostReports': [],
        }
        mock_create_client.return_value = mock_client

        result = await list_billing_group_cost_reports(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 0

    @patch(PATCH_BC_CLIENT)
    async def test_list_cost_reports_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_billing_group_cost_reports.side_effect = ClientError(
            _make_client_error_response(),
            'ListBillingGroupCostReports',
        )
        mock_create_client.return_value = mock_client

        result = await list_billing_group_cost_reports(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED


# --- Get Billing Group Cost Report Operation Tests ---


@pytest.mark.asyncio
class TestGetBillingGroupCostReport:
    """Tests for the get_billing_group_cost_report operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_get_cost_report_success(
        self, mock_create_client, mock_ctx, sample_cost_report_results
    ):
        """Test successful retrieval of a billing group cost report."""
        mock_client = MagicMock()
        mock_client.get_billing_group_cost_report.return_value = {
            'BillingGroupCostReportResults': sample_cost_report_results,
        }
        mock_create_client.return_value = mock_client

        result = await get_billing_group_cost_report(mock_ctx, BILLING_GROUP_ARN_1)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert result['data']['arn'] == BILLING_GROUP_ARN_1

    @patch(PATCH_BC_CLIENT)
    async def test_get_cost_report_with_group_by(
        self, mock_create_client, mock_ctx, sample_cost_report_results
    ):
        """Test getting cost report with group_by parameter."""
        mock_client = MagicMock()
        mock_client.get_billing_group_cost_report.return_value = {
            'BillingGroupCostReportResults': sample_cost_report_results,
        }
        mock_create_client.return_value = mock_client

        group_by_json = '["PRODUCT_NAME"]'
        result = await get_billing_group_cost_report(
            mock_ctx, BILLING_GROUP_ARN_1, group_by=group_by_json
        )

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.get_billing_group_cost_report.call_args[1]
        assert call_kwargs['GroupBy'] == ['PRODUCT_NAME']

    @patch(PATCH_BC_CLIENT)
    async def test_get_cost_report_with_billing_period_range(
        self, mock_create_client, mock_ctx, sample_cost_report_results
    ):
        """Test getting cost report with billing period range."""
        mock_client = MagicMock()
        mock_client.get_billing_group_cost_report.return_value = {
            'BillingGroupCostReportResults': sample_cost_report_results,
        }
        mock_create_client.return_value = mock_client

        range_json = json.dumps(
            {
                'InclusiveStartBillingPeriod': '2025-01',
                'ExclusiveEndBillingPeriod': '2025-07',
            }
        )
        result = await get_billing_group_cost_report(
            mock_ctx, BILLING_GROUP_ARN_1, billing_period_range=range_json
        )

        assert result['status'] == STATUS_SUCCESS
        call_kwargs = mock_client.get_billing_group_cost_report.call_args[1]
        assert 'BillingPeriodRange' in call_kwargs

    @patch(PATCH_BC_CLIENT)
    async def test_get_cost_report_pagination(
        self, mock_create_client, mock_ctx, sample_cost_report_results
    ):
        """Test getting cost report with pagination."""
        mock_client = MagicMock()
        mock_client.get_billing_group_cost_report.side_effect = [
            {
                'BillingGroupCostReportResults': [sample_cost_report_results[0]],
                'NextToken': NEXT_TOKEN_PAGE2,
            },
            {
                'BillingGroupCostReportResults': [sample_cost_report_results[1]],
            },
        ]
        mock_create_client.return_value = mock_client

        result = await get_billing_group_cost_report(mock_ctx, BILLING_GROUP_ARN_1)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert mock_client.get_billing_group_cost_report.call_count == 2

    @patch(PATCH_BC_CLIENT)
    async def test_get_cost_report_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.get_billing_group_cost_report.side_effect = ClientError(
            _make_client_error_response(),
            'GetBillingGroupCostReport',
        )
        mock_create_client.return_value = mock_client

        result = await get_billing_group_cost_report(mock_ctx, BILLING_GROUP_ARN_1)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED


# --- Account Association Fixtures ---


@pytest.fixture
def sample_linked_accounts():
    """Sample linked account data from AWS API."""
    return [
        {
            'AccountId': ACCOUNT_ID_LINKED_1,
            'AccountName': 'Development Account',
            'AccountEmail': 'dev@example.com',
            'BillingGroupArn': BILLING_GROUP_ARN_1,
        },
        {
            'AccountId': ACCOUNT_ID_LINKED_2,
            'AccountName': 'Production Account',
            'AccountEmail': 'prod@example.com',
            'BillingGroupArn': BILLING_GROUP_ARN_2,
        },
        {
            'AccountId': ACCOUNT_ID_LINKED_3,
            'AccountName': 'Sandbox Account',
            'AccountEmail': 'sandbox@example.com',
        },
    ]


# --- Account Association Format Tests ---


class TestFormatLinkedAccounts:
    """Tests for the _format_linked_accounts function."""

    def test_format_empty_list(self):
        """Test formatting an empty list of linked accounts."""
        result = _format_linked_accounts([])
        assert result == []

    def test_format_basic_fields(self, sample_linked_accounts):
        """Test that basic fields are formatted correctly."""
        result = _format_linked_accounts(sample_linked_accounts)

        assert len(result) == 3
        assert result[0]['account_id'] == ACCOUNT_ID_LINKED_1
        assert result[0]['account_name'] == 'Development Account'
        assert result[0]['account_email'] == 'dev@example.com'

    def test_format_billing_group_arn_present(self, sample_linked_accounts):
        """Test that billing group ARN is included when present."""
        result = _format_linked_accounts(sample_linked_accounts)

        assert result[0]['billing_group_arn'] == BILLING_GROUP_ARN_1
        assert result[1]['billing_group_arn'] == BILLING_GROUP_ARN_2

    def test_format_billing_group_arn_absent(self, sample_linked_accounts):
        """Test that billing group ARN is omitted when not present."""
        result = _format_linked_accounts(sample_linked_accounts)

        # Third account has no BillingGroupArn
        assert 'billing_group_arn' not in result[2]
        assert result[2]['account_id'] == ACCOUNT_ID_LINKED_3
        assert result[2]['account_name'] == 'Sandbox Account'

    def test_format_minimal_account(self):
        """Test formatting accounts with minimal fields."""
        minimal_accounts = [
            {
                'AccountId': ACCOUNT_ID_LINKED_4,
            }
        ]
        result = _format_linked_accounts(minimal_accounts)

        assert len(result) == 1
        assert result[0]['account_id'] == ACCOUNT_ID_LINKED_4
        assert result[0]['account_name'] is None
        assert result[0]['account_email'] is None
        assert 'billing_group_arn' not in result[0]


# --- List Account Associations Operation Tests ---


@pytest.mark.asyncio
class TestListAccountAssociations:
    """Tests for the list_account_associations operation function."""

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_success(
        self, mock_create_client, mock_ctx, sample_linked_accounts
    ):
        """Test successful listing of account associations."""
        mock_client = MagicMock()
        mock_client.list_account_associations.return_value = {
            'LinkedAccounts': sample_linked_accounts,
        }
        mock_create_client.return_value = mock_client

        result = await list_account_associations(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 3
        assert len(result['data']['linked_accounts']) == 3
        assert 'next_token' not in result['data']

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_with_billing_period(
        self, mock_create_client, mock_ctx, sample_linked_accounts
    ):
        """Test listing account associations with a specific billing period."""
        mock_client = MagicMock()
        mock_client.list_account_associations.return_value = {
            'LinkedAccounts': sample_linked_accounts,
        }
        mock_create_client.return_value = mock_client

        result = await list_account_associations(mock_ctx, BILLING_PERIOD, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['billing_period'] == BILLING_PERIOD

        call_kwargs = mock_client.list_account_associations.call_args[1]
        assert call_kwargs['BillingPeriod'] == BILLING_PERIOD

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_with_association_filter(
        self, mock_create_client, mock_ctx, sample_linked_accounts
    ):
        """Test listing account associations with an Association filter."""
        mock_client = MagicMock()
        mock_client.list_account_associations.return_value = {
            'LinkedAccounts': sample_linked_accounts[:2],
        }
        mock_create_client.return_value = mock_client

        filters_json = json.dumps({'Association': 'MONITORED'})
        result = await list_account_associations(mock_ctx, None, filters_json, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2

        call_kwargs = mock_client.list_account_associations.call_args[1]
        assert call_kwargs['Filters'] == {'Association': 'MONITORED'}

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_with_account_ids_filter(
        self, mock_create_client, mock_ctx, sample_linked_accounts
    ):
        """Test listing account associations with AccountIds filter."""
        mock_client = MagicMock()
        mock_client.list_account_associations.return_value = {
            'LinkedAccounts': [sample_linked_accounts[0]],
        }
        mock_create_client.return_value = mock_client

        filters_json = json.dumps({'AccountIds': [ACCOUNT_ID_LINKED_1]})
        result = await list_account_associations(mock_ctx, None, filters_json, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1

        call_kwargs = mock_client.list_account_associations.call_args[1]
        assert call_kwargs['Filters'] == {'AccountIds': [ACCOUNT_ID_LINKED_1]}

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_pagination(
        self, mock_create_client, mock_ctx, sample_linked_accounts
    ):
        """Test listing account associations with pagination across multiple pages."""
        mock_client = MagicMock()
        mock_client.list_account_associations.side_effect = [
            {
                'LinkedAccounts': [sample_linked_accounts[0]],
                'NextToken': NEXT_TOKEN_PAGE2,
            },
            {
                'LinkedAccounts': [sample_linked_accounts[1]],
            },
        ]
        mock_create_client.return_value = mock_client

        result = await list_account_associations(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 2
        assert mock_client.list_account_associations.call_count == 2
        assert 'next_token' not in result['data']

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_max_pages_stops_pagination(
        self, mock_create_client, mock_ctx, sample_linked_accounts
    ):
        """Test that max_pages limits the number of API calls and returns next_token."""
        mock_client = MagicMock()
        mock_client.list_account_associations.return_value = {
            'LinkedAccounts': [sample_linked_accounts[0]],
            'NextToken': NEXT_TOKEN_MORE,
        }
        mock_create_client.return_value = mock_client

        result = await list_account_associations(mock_ctx, None, None, 1, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert mock_client.list_account_associations.call_count == 1
        assert result['data']['next_token'] == NEXT_TOKEN_MORE

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_with_next_token(
        self, mock_create_client, mock_ctx, sample_linked_accounts
    ):
        """Test continuing pagination with a next_token from a previous response."""
        mock_client = MagicMock()
        mock_client.list_account_associations.return_value = {
            'LinkedAccounts': [sample_linked_accounts[1]],
        }
        mock_create_client.return_value = mock_client

        result = await list_account_associations(mock_ctx, None, None, 10, NEXT_TOKEN_CONTINUE)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 1
        assert 'next_token' not in result['data']

        call_kwargs = mock_client.list_account_associations.call_args[1]
        assert call_kwargs['NextToken'] == NEXT_TOKEN_CONTINUE

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_empty_result(self, mock_create_client, mock_ctx):
        """Test listing account associations when none exist."""
        mock_client = MagicMock()
        mock_client.list_account_associations.return_value = {
            'LinkedAccounts': [],
        }
        mock_create_client.return_value = mock_client

        result = await list_account_associations(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['total_count'] == 0
        assert result['data']['linked_accounts'] == []
        assert 'next_token' not in result['data']

    async def test_list_account_associations_invalid_filters(self, mock_ctx):
        """Test listing account associations with invalid filter JSON."""
        result = await list_account_associations(mock_ctx, None, 'not-valid-json', 10, None)

        assert result['status'] == STATUS_ERROR

    @patch(PATCH_BC_CLIENT)
    async def test_list_account_associations_aws_error(self, mock_create_client, mock_ctx):
        """Test handling of AWS service errors."""
        mock_client = MagicMock()
        mock_client.list_account_associations.side_effect = ClientError(
            _make_client_error_response(),
            'ListAccountAssociations',
        )
        mock_create_client.return_value = mock_client

        result = await list_account_associations(mock_ctx, None, None, 10, None)

        assert result['status'] == STATUS_ERROR
        assert result['error_type'] == ERROR_ACCESS_DENIED
