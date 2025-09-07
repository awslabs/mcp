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

"""Unit tests for the bcm_pricing_calculator_tools module.

These tests verify the functionality of the BCM Pricing Calculator tools, including:
- Getting preferences and validating configuration
- Listing workload estimates with various filters
- Getting specific workload estimate details
- Listing workload estimate usage with filters
- Formatting response objects
- Error handling for invalid parameters and API exceptions
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools import (
    PREFERENCES_NOT_CONFIGURED_ERROR,
    bcm_pricing_calculator_server,
    describe_workload_estimate,
    describe_workload_estimate_usage,
    describe_workload_estimates,
    format_usage_item_response,
    format_workload_estimate_response,
    get_preferences,
)
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_bcm_client():
    """Create a mock BCM Pricing Calculator boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.get_preferences.return_value = {
        'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
        'memberAccountRateTypeSelections': ['AFTER_DISCOUNTS'],
        'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS'],
    }

    mock_client.list_workload_estimates.return_value = {
        'items': [
            {
                'id': '7ef37735-f7b9-444c-99b2-4faad224ead6',
                'name': 'Test-Workload-Estimate',
                'status': 'VALID',
                'rateType': 'AFTER_DISCOUNTS',
                'createdAt': datetime(2023, 1, 1, 12, 0, 0),
                'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
                'rateTimestamp': datetime(2023, 1, 1, 0, 0, 0),
                'totalCost': 1500.50,
                'costCurrency': 'USD',
            }
        ],
        'nextToken': 'next-token-123',
    }

    mock_client.get_workload_estimate.return_value = {
        'id': '70f54b81-73b2-471f-bbb8-c92c6eda87f6',
        'name': 'Detailed Workload Estimate',
        'status': 'UPDATING',
        'rateType': 'BEFORE_DISCOUNTS',
        'createdAt': datetime(2023, 2, 1, 10, 30, 0),
        'expiresAt': datetime(2023, 11, 30, 23, 59, 59),
        'rateTimestamp': datetime(2023, 2, 1, 0, 0, 0),
        'totalCost': 2750.75,
        'costCurrency': 'USD',
        'failureMessage': None,
    }

    mock_client.list_workload_estimate_usage.return_value = {
        'items': [
            {
                'id': 'd4422ec0-2265-4079-be5b-baad6ade5672',
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'group': 'compute',
                'status': 'VALID',
                'currency': 'USD',
                'quantity': {'amount': 744.0, 'unit': 'Hrs'},
                'cost': 50.25,
                'historicalUsage': {
                    'serviceCode': 'AmazonEC2',
                    'usageType': 'BoxUsage:t3.medium',
                    'operation': 'RunInstances',
                    'location': 'US East (N. Virginia)',
                    'usageAccountId': '123456789012',
                    'billInterval': {'start': datetime(2023, 1, 1), 'end': datetime(2023, 1, 31)},
                },
            }
        ],
        'nextToken': 'usage-next-token-456',
    }

    return mock_client


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


class TestGetPreferences:
    """Test the get_preferences function."""

    @pytest.mark.asyncio
    async def test_get_preferences_success_all_account_types(self, mock_context, mock_bcm_client):
        """Test get_preferences with all account types configured."""
        result = await get_preferences(mock_context, mock_bcm_client)

        assert result is True
        mock_bcm_client.get_preferences.assert_called_once()
        mock_context.info.assert_called()

        # Check that info was called with the expected message about account types
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any(
            'management account, member account, standalone account' in call for call in info_calls
        )

    @pytest.mark.asyncio
    async def test_get_preferences_success_partial_account_types(
        self, mock_context, mock_bcm_client
    ):
        """Test get_preferences with only some account types configured."""
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }

        result = await get_preferences(mock_context, mock_bcm_client)

        assert result is True
        mock_bcm_client.get_preferences.assert_called_once()
        mock_context.info.assert_called()

        # Check that info was called with only management account
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any(
            'management account' in call and 'member account' not in call for call in info_calls
        )

    @pytest.mark.asyncio
    async def test_get_preferences_no_rate_selections(self, mock_context, mock_bcm_client):
        """Test get_preferences with no rate type selections."""
        mock_bcm_client.get_preferences.return_value = {}

        result = await get_preferences(mock_context, mock_bcm_client)

        assert result is False
        mock_bcm_client.get_preferences.assert_called_once()
        mock_context.error.assert_called_once()

        error_call = mock_context.error.call_args[0][0]
        assert 'no rate type selections found' in error_call

    @pytest.mark.asyncio
    async def test_get_preferences_empty_response(self, mock_context, mock_bcm_client):
        """Test get_preferences with empty response."""
        mock_bcm_client.get_preferences.return_value = None

        result = await get_preferences(mock_context, mock_bcm_client)

        assert result is False
        mock_bcm_client.get_preferences.assert_called_once()
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_preferences_client_error(self, mock_context, mock_bcm_client):
        """Test get_preferences with client error."""
        mock_bcm_client.get_preferences.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'GetPreferences'
        )

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
        ) as mock_handle_error:
            mock_handle_error.return_value = {'data': {'error': 'Access denied'}}

            result = await get_preferences(mock_context, mock_bcm_client)

            assert result is False
            mock_handle_error.assert_called_once()
            mock_context.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_preferences_generic_exception(self, mock_context, mock_bcm_client):
        """Test get_preferences with generic exception."""
        mock_bcm_client.get_preferences.side_effect = Exception('Network error')

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
        ) as mock_handle_error:
            mock_handle_error.return_value = {'data': {'error': 'Network error'}}

            result = await get_preferences(mock_context, mock_bcm_client)

            assert result is False
            mock_handle_error.assert_called_once()
            mock_context.error.assert_called()


class TestListWorkloadEstimates:
    """Test the list_workload_estimates function."""

    @pytest.mark.asyncio
    async def test_list_workload_estimates_success(self, mock_context, mock_bcm_client):
        """Test successful list_workload_estimates call."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context, status_filter='VALID', name_filter='Test', max_results=10
            )

        assert result['status'] == 'success'
        assert 'data' in result
        assert 'workload_estimates' in result['data']
        assert len(result['data']['workload_estimates']) == 1
        assert (
            result['data']['workload_estimates'][0]['id'] == '7ef37735-f7b9-444c-99b2-4faad224ead6'
        )
        assert result['data']['workload_estimates'][0]['name'] == 'Test-Workload-Estimate'
        assert result['data']['total_count'] == 1
        assert result['data']['next_token'] == 'next-token-123'
        assert result['data']['has_more_results'] is True

        mock_bcm_client.list_workload_estimates.assert_called_once()
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]
        assert call_kwargs['maxResults'] == 10
        assert len(call_kwargs['filters']) == 2  # status and name filters

    @pytest.mark.asyncio
    async def test_list_workload_estimates_with_date_filters(self, mock_context, mock_bcm_client):
        """Test list_workload_estimates with date filters."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                created_after='2023-01-01T00:00:00',
                created_before='2023-12-31T23:59:59',
                expires_after='2023-06-01T00:00:00',
                expires_before='2023-12-31T23:59:59',
            )

        assert result['status'] == 'success'
        mock_bcm_client.list_workload_estimates.assert_called_once()
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]
        assert 'createdAtFilter' in call_kwargs
        assert 'expiresAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['createdAtFilter']
        assert 'beforeTimestamp' in call_kwargs['createdAtFilter']

    @pytest.mark.asyncio
    async def test_list_workload_estimates_preferences_not_configured(
        self, mock_context, mock_bcm_client
    ):
        """Test list_workload_estimates when preferences are not configured."""
        # Mock get_preferences to return False (preferences not configured)
        mock_bcm_client.get_preferences.return_value = {}  # Empty response means no preferences

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(mock_context)

        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'
        mock_bcm_client.list_workload_estimates.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_workload_estimates_client_error(self, mock_context, mock_bcm_client):
        """Test list_workload_estimates with client error."""
        mock_bcm_client.list_workload_estimates.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}},
            'ListWorkloadEstimates',
        )

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            with patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
            ) as mock_handle_error:
                mock_handle_error.return_value = {
                    'status': 'error',
                    'data': {'error': 'Invalid parameter'},
                }

                result = await describe_workload_estimates(mock_context)

        assert result['status'] == 'error'
        mock_handle_error.assert_called_once()


class TestGetWorkloadEstimate:
    """Test the get_workload_estimate function."""

    @pytest.mark.asyncio
    async def test_get_workload_estimate_success(self, mock_context, mock_bcm_client):
        """Test successful get_workload_estimate call."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimate(mock_context, 'estimate-456')

        assert result['status'] == 'success'
        assert 'data' in result
        assert 'workload_estimate' in result['data']
        assert result['data']['workload_estimate']['id'] == '70f54b81-73b2-471f-bbb8-c92c6eda87f6'
        assert result['data']['workload_estimate']['name'] == 'Detailed Workload Estimate'
        assert result['data']['workload_estimate']['status'] == 'UPDATING'
        assert result['data']['identifier'] == 'estimate-456'

        mock_bcm_client.get_workload_estimate.assert_called_once()
        call_kwargs = mock_bcm_client.get_workload_estimate.call_args[1]
        assert call_kwargs['identifier'] == 'estimate-456'

    @pytest.mark.asyncio
    async def test_get_workload_estimate_preferences_not_configured(
        self, mock_context, mock_bcm_client
    ):
        """Test get_workload_estimate when preferences are not configured."""
        # Mock get_preferences to return False (preferences not configured)
        mock_bcm_client.get_preferences.return_value = {}  # Empty response means no preferences

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimate(mock_context, 'estimate-456')

        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'
        mock_bcm_client.get_workload_estimate.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_workload_estimate_not_found(self, mock_context, mock_bcm_client):
        """Test get_workload_estimate with not found error."""
        mock_bcm_client.get_workload_estimate.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Workload estimate not found',
                }
            },
            'GetWorkloadEstimate',
        )

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            with patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
            ) as mock_handle_error:
                mock_handle_error.return_value = {
                    'status': 'error',
                    'data': {'error': 'Workload estimate not found'},
                }

                result = await describe_workload_estimate(mock_context, 'nonexistent-estimate')

        assert result['status'] == 'error'
        mock_handle_error.assert_called_once()


class TestListWorkloadEstimateUsage:
    """Test the list_workload_estimate_usage function."""

    @pytest.mark.asyncio
    async def test_list_workload_estimate_usage_success(self, mock_context, mock_bcm_client):
        """Test successful list_workload_estimate_usage call."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimate_usage(
                mock_context,
                '7ef37735-f7b9-444c-99b2-4faad224ead6',
                service_code_filter='AmazonEC2',
                usage_type_filter='BoxUsage',
                max_results=25,
            )

        assert result['status'] == 'success'
        assert 'data' in result
        assert 'usage_items' in result['data']
        assert len(result['data']['usage_items']) == 1
        assert result['data']['usage_items'][0]['id'] == 'd4422ec0-2265-4079-be5b-baad6ade5672'
        assert result['data']['usage_items'][0]['service_code'] == 'AmazonEC2'
        assert result['data']['total_count'] == 1
        assert result['data']['next_token'] == 'usage-next-token-456'
        assert result['data']['workload_estimate_id'] == '7ef37735-f7b9-444c-99b2-4faad224ead6'

        mock_bcm_client.list_workload_estimate_usage.assert_called_once()
        call_kwargs = mock_bcm_client.list_workload_estimate_usage.call_args[1]
        assert call_kwargs['workloadEstimateId'] == '7ef37735-f7b9-444c-99b2-4faad224ead6'
        assert call_kwargs['maxResults'] == 25
        assert len(call_kwargs['filters']) == 2  # service_code and usage_type filters

    @pytest.mark.asyncio
    async def test_list_workload_estimate_usage_all_filters(self, mock_context, mock_bcm_client):
        """Test list_workload_estimate_usage with all filter types."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimate_usage(
                mock_context,
                'estimate-123',
                usage_account_id_filter='123456789012',
                service_code_filter='AmazonEC2',
                usage_type_filter='BoxUsage',
                operation_filter='RunInstances',
                location_filter='US East (N. Virginia)',
                usage_group_filter='compute',
            )

        assert result['status'] == 'success'
        mock_bcm_client.list_workload_estimate_usage.assert_called_once()
        call_kwargs = mock_bcm_client.list_workload_estimate_usage.call_args[1]
        assert len(call_kwargs['filters']) == 6  # All filter types

    @pytest.mark.asyncio
    async def test_list_workload_estimate_usage_preferences_not_configured(
        self, mock_context, mock_bcm_client
    ):
        """Test list_workload_estimate_usage when preferences are not configured."""
        # Mock get_preferences to return False (preferences not configured)
        mock_bcm_client.get_preferences.return_value = {}  # Empty response means no preferences

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimate_usage(mock_context, 'estimate-123')

        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'
        mock_bcm_client.list_workload_estimate_usage.assert_not_called()


class TestFormatUsageItemResponse:
    """Test the format_usage_item_response function."""

    def test_format_usage_item_response_complete(self):
        """Test formatting a complete usage item response."""
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'usageType': 'BoxUsage:t3.medium',
            'operation': 'RunInstances',
            'location': 'US East (N. Virginia)',
            'usageAccountId': '123456789012',
            'group': 'compute',
            'status': 'VALID',
            'currency': 'USD',
            'quantity': {'amount': 744.0, 'unit': 'Hrs'},
            'cost': 50.25,
            'historicalUsage': {
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'billInterval': {'start': datetime(2023, 1, 1), 'end': datetime(2023, 1, 31)},
            },
        }

        result = format_usage_item_response(usage_item)

        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'
        assert result['usage_type'] == 'BoxUsage:t3.medium'
        assert result['operation'] == 'RunInstances'
        assert result['location'] == 'US East (N. Virginia)'
        assert result['usage_account_id'] == '123456789012'
        assert result['group'] == 'compute'
        assert result['status'] == 'VALID'
        assert result['currency'] == 'USD'
        assert result['status_indicator'] == 'Valid'

        # Check quantity formatting
        assert result['quantity']['amount'] == 744.0
        assert result['quantity']['unit'] == 'Hrs'
        assert result['quantity']['formatted'] == '744.00 Hrs'

        # Check cost formatting
        assert result['cost']['amount'] == 50.25
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] == 'USD 50.25'

        # Check historical usage
        assert 'historical_usage' in result
        assert result['historical_usage']['service_code'] == 'AmazonEC2'
        assert 'bill_interval' in result['historical_usage']
        assert result['historical_usage']['bill_interval']['start'] == '2023-01-01T00:00:00'
        assert result['historical_usage']['bill_interval']['end'] == '2023-01-31T00:00:00'

    def test_format_usage_item_response_minimal(self):
        """Test formatting a minimal usage item response."""
        usage_item = {'id': 'usage-456', 'serviceCode': 'AmazonS3', 'status': 'INVALID'}

        result = format_usage_item_response(usage_item)

        assert result['id'] == 'usage-456'
        assert result['service_code'] == 'AmazonS3'
        assert result['status'] == 'INVALID'
        assert result['currency'] == 'USD'  # Default value
        assert result['status_indicator'] == 'Invalid'
        assert 'quantity' not in result
        assert 'cost' not in result
        assert 'historical_usage' not in result

    def test_format_usage_item_response_unknown_status(self):
        """Test formatting usage item with unknown status."""
        usage_item = {'id': 'usage-789', 'serviceCode': 'AmazonRDS', 'status': 'UNKNOWN_STATUS'}

        result = format_usage_item_response(usage_item)

        assert result['status_indicator'] == '❓ UNKNOWN_STATUS'


class TestFormatWorkloadEstimateResponse:
    """Test the format_workload_estimate_response function."""

    def test_format_workload_estimate_response_complete(self):
        """Test formatting a complete workload estimate response."""
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'rateType': 'AFTER_DISCOUNTS',
            'createdAt': datetime(2023, 1, 1, 12, 0, 0),
            'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
            'rateTimestamp': datetime(2023, 1, 1, 0, 0, 0),
            'totalCost': 1500.50,
            'costCurrency': 'USD',
            'failureMessage': 'Some failure message',
        }

        result = format_workload_estimate_response(estimate)

        assert result['id'] == 'estimate-123'
        assert result['name'] == 'Test Estimate'
        assert result['status'] == 'VALID'
        assert result['rate_type'] == 'AFTER_DISCOUNTS'
        assert result['status_indicator'] == 'Valid'
        assert result['failure_message'] == 'Some failure message'

        # Check timestamp formatting
        assert result['created_at']['timestamp'] == '2023-01-01T12:00:00'
        assert result['created_at']['formatted'] == '2023-01-01 12:00:00 UTC'
        assert result['expires_at']['timestamp'] == '2023-12-31T23:59:59'
        assert result['expires_at']['formatted'] == '2023-12-31 23:59:59 UTC'
        assert result['rate_timestamp']['timestamp'] == '2023-01-01T00:00:00'
        assert result['rate_timestamp']['formatted'] == '2023-01-01 00:00:00 UTC'

        # Check cost formatting
        assert result['cost']['amount'] == 1500.50
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] == 'USD 1,500.50'

    def test_format_workload_estimate_response_minimal(self):
        """Test formatting a minimal workload estimate response."""
        estimate = {'id': 'estimate-456', 'name': 'Minimal Estimate', 'status': 'UPDATING'}

        result = format_workload_estimate_response(estimate)

        assert result['id'] == 'estimate-456'
        assert result['name'] == 'Minimal Estimate'
        assert result['status'] == 'UPDATING'
        assert result['status_indicator'] == 'Updating'
        assert 'created_at' not in result
        assert 'expires_at' not in result
        assert 'rate_timestamp' not in result
        assert 'cost' not in result
        assert 'failure_message' not in result

    def test_format_workload_estimate_response_string_timestamps(self):
        """Test formatting workload estimate with string timestamps."""
        estimate = {
            'id': 'estimate-789',
            'name': 'String Timestamp Estimate',
            'status': 'ACTION_NEEDED',
            'createdAt': '2023-01-01T12:00:00',
            'totalCost': None,  # Test null cost
        }

        result = format_workload_estimate_response(estimate)

        assert result['created_at']['timestamp'] == '2023-01-01T12:00:00'
        assert result['created_at']['formatted'] == '2023-01-01T12:00:00'
        assert result['status_indicator'] == 'Action Needed'
        assert result['cost']['formatted'] is None

    def test_format_workload_estimate_response_unknown_status(self):
        """Test formatting workload estimate with unknown status."""
        estimate = {
            'id': 'estimate-999',
            'name': 'Unknown Status Estimate',
            'status': 'UNKNOWN_STATUS',
        }

        result = format_workload_estimate_response(estimate)

        assert result['status_indicator'] == '❓ UNKNOWN_STATUS'


class TestConstants:
    """Test module constants."""

    def test_preferences_not_configured_error_constant(self):
        """Test that the error constant is properly defined."""
        assert (
            PREFERENCES_NOT_CONFIGURED_ERROR
            == 'BCM Pricing Calculator preferences are not configured. Please configure preferences before using this service.'
        )
        assert isinstance(PREFERENCES_NOT_CONFIGURED_ERROR, str)
        assert len(PREFERENCES_NOT_CONFIGURED_ERROR) > 0


class TestServerInitialization:
    """Test server initialization."""

    def test_bcm_pricing_calculator_server_initialization(self):
        """Test that the server is properly initialized."""
        assert bcm_pricing_calculator_server.name == 'bcm-pricing-calculator-tools'
        assert isinstance(bcm_pricing_calculator_server.instructions, str)
        assert len(bcm_pricing_calculator_server.instructions) > 0
        assert 'BCM Pricing Calculator' in bcm_pricing_calculator_server.instructions


class TestIntegrationTests:
    """Integration tests for the BCM Pricing Calculator tools."""

    @pytest.mark.asyncio
    async def test_list_workload_estimates_integration(self, mock_context):
        """Test list_workload_estimates integration with mocked AWS client."""
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_client.list_workload_estimates.return_value = {
            'items': [
                {
                    'id': 'integration-test-estimate',
                    'name': 'Integration Test Estimate',
                    'status': 'VALID',
                    'rateType': 'BEFORE_DISCOUNTS',
                    'createdAt': datetime(2023, 1, 1),
                    'totalCost': 100.0,
                    'costCurrency': 'USD',
                }
            ]
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_client,
        ):
            result = await describe_workload_estimates(mock_context, max_results=1)

        assert result['status'] == 'success'
        assert len(result['data']['workload_estimates']) == 1
        assert result['data']['workload_estimates'][0]['id'] == 'integration-test-estimate'

    @pytest.mark.asyncio
    async def test_get_workload_estimate_integration(self, mock_context):
        """Test get_workload_estimate integration with mocked AWS client."""
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS']
        }
        mock_client.get_workload_estimate.return_value = {
            'id': 'integration-test-detail',
            'name': 'Integration Test Detail',
            'status': 'VALID',
            'rateType': 'AFTER_DISCOUNTS',
            'totalCost': 250.0,
            'costCurrency': 'USD',
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_client,
        ):
            result = await describe_workload_estimate(mock_context, 'integration-test-detail')

        assert result['status'] == 'success'
        assert result['data']['workload_estimate']['id'] == 'integration-test-detail'
        assert result['data']['workload_estimate']['name'] == 'Integration Test Detail'

    @pytest.mark.asyncio
    async def test_list_workload_estimate_usage_integration(self, mock_context):
        """Test list_workload_estimate_usage integration with mocked AWS client."""
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'memberAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS']
        }
        mock_client.list_workload_estimate_usage.return_value = {
            'items': [
                {
                    'id': 'integration-usage-item',
                    'serviceCode': 'AmazonS3',
                    'usageType': 'StandardStorage',
                    'status': 'VALID',
                    'cost': 25.50,
                    'currency': 'USD',
                }
            ]
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_client,
        ):
            result = await describe_workload_estimate_usage(mock_context, 'test-estimate-id')

        assert result['status'] == 'success'
        assert len(result['data']['usage_items']) == 1
        assert result['data']['usage_items'][0]['id'] == 'integration-usage-item'
        assert result['data']['usage_items'][0]['service_code'] == 'AmazonS3'


class TestDateTimeHandling:
    """Test datetime parsing and timezone handling in list_workload_estimates."""

    @pytest.mark.asyncio
    async def test_list_workload_estimates_datetime_parsing_with_z_suffix(
        self, mock_context, mock_bcm_client
    ):
        """Test datetime parsing with Z suffix (UTC timezone)."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                created_after='2023-01-01T00:00:00Z',
                created_before='2023-12-31T23:59:59Z',
            )

        assert result['status'] == 'success'
        mock_bcm_client.list_workload_estimates.assert_called_once()
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify that datetime parsing worked correctly
        assert 'createdAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['createdAtFilter']
        assert 'beforeTimestamp' in call_kwargs['createdAtFilter']

    @pytest.mark.asyncio
    async def test_list_workload_estimates_datetime_parsing_without_z_suffix(
        self, mock_context, mock_bcm_client
    ):
        """Test datetime parsing without Z suffix."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                expires_after='2023-06-01T12:00:00',
                expires_before='2023-12-31T12:00:00',
            )

        assert result['status'] == 'success'
        mock_bcm_client.list_workload_estimates.assert_called_once()
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify that datetime parsing worked correctly
        assert 'expiresAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['expiresAtFilter']
        assert 'beforeTimestamp' in call_kwargs['expiresAtFilter']

    @pytest.mark.asyncio
    async def test_list_workload_estimates_only_created_after_filter(
        self, mock_context, mock_bcm_client
    ):
        """Test with only created_after filter."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context, created_after='2023-01-01T00:00:00Z'
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify only afterTimestamp is set
        assert 'createdAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['createdAtFilter']
        assert 'beforeTimestamp' not in call_kwargs['createdAtFilter']

    @pytest.mark.asyncio
    async def test_list_workload_estimates_only_expires_before_filter(
        self, mock_context, mock_bcm_client
    ):
        """Test with only expires_before filter."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context, expires_before='2023-12-31T23:59:59Z'
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify only beforeTimestamp is set
        assert 'expiresAtFilter' in call_kwargs
        assert 'beforeTimestamp' in call_kwargs['expiresAtFilter']
        assert 'afterTimestamp' not in call_kwargs['expiresAtFilter']

    @pytest.mark.asyncio
    async def test_list_workload_estimates_name_match_options(self, mock_context, mock_bcm_client):
        """Test different name match options."""
        # Test EQUALS match option
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context, name_filter='Exact Name', name_match_option='EQUALS'
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]
        name_filter = next((f for f in call_kwargs['filters'] if f['name'] == 'NAME'), None)
        assert name_filter is not None
        assert name_filter['matchOption'] == 'EQUALS'
        assert name_filter['values'] == ['Exact Name']

        # Test STARTS_WITH match option
        mock_bcm_client.reset_mock()
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context, name_filter='Prefix', name_match_option='STARTS_WITH'
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]
        name_filter = next((f for f in call_kwargs['filters'] if f['name'] == 'NAME'), None)
        assert name_filter is not None
        assert name_filter['matchOption'] == 'STARTS_WITH'

    @pytest.mark.asyncio
    async def test_list_workload_estimates_max_results_conversion(
        self, mock_context, mock_bcm_client
    ):
        """Test that max_results is properly converted to int."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                max_results=50,  # This should be converted to int
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]
        assert call_kwargs['maxResults'] == 50
        assert isinstance(call_kwargs['maxResults'], int)

    @pytest.mark.asyncio
    async def test_list_workload_estimates_next_token_handling(
        self, mock_context, mock_bcm_client
    ):
        """Test next_token parameter handling."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(mock_context, next_token='test-token-123')

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]
        assert call_kwargs['nextToken'] == 'test-token-123'

    @pytest.mark.asyncio
    async def test_list_workload_estimates_no_filters(self, mock_context, mock_bcm_client):
        """Test list_workload_estimates with no filters applied."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(mock_context)

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Should only have maxResults, no filters
        assert 'filters' not in call_kwargs
        assert 'createdAtFilter' not in call_kwargs
        assert 'expiresAtFilter' not in call_kwargs
        assert call_kwargs['maxResults'] == 25  # default value

    @pytest.mark.asyncio
    async def test_list_workload_estimates_comprehensive_parameter_building(
        self, mock_context, mock_bcm_client
    ):
        """Test comprehensive parameter building with all possible combinations."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                created_after='2023-01-01T00:00:00Z',
                created_before='2023-06-30T23:59:59Z',
                expires_after='2023-07-01T00:00:00Z',
                expires_before='2023-12-31T23:59:59Z',
                status_filter='VALID',
                name_filter='Production',
                name_match_option='STARTS_WITH',
                next_token='pagination-token-456',
                max_results=75,
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify all parameters are correctly built
        assert call_kwargs['maxResults'] == 75
        assert call_kwargs['nextToken'] == 'pagination-token-456'

        # Verify date filters
        assert 'createdAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['createdAtFilter']
        assert 'beforeTimestamp' in call_kwargs['createdAtFilter']
        assert 'expiresAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['expiresAtFilter']
        assert 'beforeTimestamp' in call_kwargs['expiresAtFilter']

        # Verify filters
        assert 'filters' in call_kwargs
        assert len(call_kwargs['filters']) == 2

        status_filter = next((f for f in call_kwargs['filters'] if f['name'] == 'STATUS'), None)
        assert status_filter is not None
        assert status_filter['values'] == ['VALID']
        assert status_filter['matchOption'] == 'EQUALS'

        name_filter = next((f for f in call_kwargs['filters'] if f['name'] == 'NAME'), None)
        assert name_filter is not None
        assert name_filter['values'] == ['Production']
        assert name_filter['matchOption'] == 'STARTS_WITH'


class TestDescribeWorkloadEstimates:
    """Test the describe_workload_estimates helper function directly."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimates_success(self, mock_create_client, mock_context):
        """Test successful describe_workload_estimates call."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.list_workload_estimates.return_value = {
            'items': [
                {
                    'id': 'test-estimate-123',
                    'name': 'Test Estimate',
                    'status': 'VALID',
                    'rateType': 'BEFORE_DISCOUNTS',
                    'createdAt': datetime(2023, 1, 1, 12, 0, 0),
                    'totalCost': 100.0,
                    'costCurrency': 'USD',
                }
            ],
            'nextToken': 'test-token',
        }
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimates(
            mock_context, status_filter='VALID', name_filter='Test', max_results=10
        )

        assert result['status'] == 'success'
        assert len(result['data']['workload_estimates']) == 1
        assert result['data']['workload_estimates'][0]['id'] == 'test-estimate-123'
        assert result['data']['next_token'] == 'test-token'
        assert result['data']['has_more_results'] is True

        # Verify API call parameters
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]
        assert call_kwargs['maxResults'] == 10
        assert len(call_kwargs['filters']) == 2

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimates_datetime_parsing(
        self, mock_create_client, mock_context
    ):
        """Test datetime parsing with Z suffix replacement."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.list_workload_estimates.return_value = {'items': []}
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimates(
            mock_context,
            created_after='2023-01-01T00:00:00Z',
            expires_before='2023-12-31T23:59:59Z',
        )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify datetime filters were created
        assert 'createdAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['createdAtFilter']
        assert 'expiresAtFilter' in call_kwargs
        assert 'beforeTimestamp' in call_kwargs['expiresAtFilter']

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimates_preferences_not_configured(
        self, mock_create_client, mock_context
    ):
        """Test when preferences are not configured."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {}  # No preferences
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimates(mock_context)

        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'
        mock_bcm_client.list_workload_estimates.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_describe_workload_estimates_client_error(
        self, mock_handle_error, mock_create_client, mock_context
    ):
        """Test client error handling."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.list_workload_estimates.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}},
            'ListWorkloadEstimates',
        )
        mock_create_client.return_value = mock_bcm_client
        mock_handle_error.return_value = {
            'status': 'error',
            'data': {'error': 'Invalid parameter'},
        }

        result = await describe_workload_estimates(mock_context)

        assert result['status'] == 'error'
        mock_handle_error.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimates_all_filters(self, mock_create_client, mock_context):
        """Test with all possible filters and parameters."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.list_workload_estimates.return_value = {'items': []}
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimates(
            mock_context,
            created_after='2023-01-01T00:00:00Z',
            created_before='2023-06-30T23:59:59Z',
            expires_after='2023-07-01T00:00:00Z',
            expires_before='2023-12-31T23:59:59Z',
            status_filter='VALID',
            name_filter='Production',
            name_match_option='STARTS_WITH',
            next_token='pagination-token',
            max_results=25,
        )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify all parameters
        assert call_kwargs['maxResults'] == 25
        assert call_kwargs['nextToken'] == 'pagination-token'
        assert 'createdAtFilter' in call_kwargs
        assert 'expiresAtFilter' in call_kwargs
        assert len(call_kwargs['filters']) == 2


class TestDescribeWorkloadEstimate:
    """Test the describe_workload_estimate helper function directly."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimate_success(self, mock_create_client, mock_context):
        """Test successful describe_workload_estimate call."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS']
        }
        mock_bcm_client.get_workload_estimate.return_value = {
            'id': 'estimate-456',
            'name': 'Detailed Estimate',
            'status': 'UPDATING',
            'rateType': 'AFTER_DISCOUNTS',
            'totalCost': 250.0,
            'costCurrency': 'USD',
        }
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimate(mock_context, 'estimate-456')

        assert result['status'] == 'success'
        assert result['data']['workload_estimate']['id'] == 'estimate-456'
        assert result['data']['workload_estimate']['name'] == 'Detailed Estimate'
        assert result['data']['identifier'] == 'estimate-456'

        # Verify API call parameters
        call_kwargs = mock_bcm_client.get_workload_estimate.call_args[1]
        assert call_kwargs['identifier'] == 'estimate-456'

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimate_preferences_not_configured(
        self, mock_create_client, mock_context
    ):
        """Test when preferences are not configured."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {}  # No preferences
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimate(mock_context, 'estimate-456')

        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'
        mock_bcm_client.get_workload_estimate.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_describe_workload_estimate_not_found(
        self, mock_handle_error, mock_create_client, mock_context
    ):
        """Test workload estimate not found error."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.get_workload_estimate.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Workload estimate not found',
                }
            },
            'GetWorkloadEstimate',
        )
        mock_create_client.return_value = mock_bcm_client
        mock_handle_error.return_value = {
            'status': 'error',
            'data': {'error': 'Workload estimate not found'},
        }

        result = await describe_workload_estimate(mock_context, 'nonexistent-estimate')

        assert result['status'] == 'error'
        mock_handle_error.assert_called_once()


class TestDescribeWorkloadEstimateUsage:
    """Test the describe_workload_estimate_usage helper function directly."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimate_usage_success(
        self, mock_create_client, mock_context
    ):
        """Test successful describe_workload_estimate_usage call."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'memberAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS']
        }
        mock_bcm_client.list_workload_estimate_usage.return_value = {
            'items': [
                {
                    'id': 'usage-item-123',
                    'serviceCode': 'AmazonEC2',
                    'usageType': 'BoxUsage:t3.medium',
                    'operation': 'RunInstances',
                    'status': 'VALID',
                    'cost': 50.25,
                    'currency': 'USD',
                }
            ],
            'nextToken': 'usage-token',
        }
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimate_usage(
            mock_context,
            'estimate-123',
            service_code_filter='AmazonEC2',
            usage_type_filter='BoxUsage',
            max_results=25,
        )

        assert result['status'] == 'success'
        assert len(result['data']['usage_items']) == 1
        assert result['data']['usage_items'][0]['id'] == 'usage-item-123'
        assert result['data']['usage_items'][0]['service_code'] == 'AmazonEC2'
        assert result['data']['workload_estimate_id'] == 'estimate-123'
        assert result['data']['next_token'] == 'usage-token'

        # Verify API call parameters
        call_kwargs = mock_bcm_client.list_workload_estimate_usage.call_args[1]
        assert call_kwargs['workloadEstimateId'] == 'estimate-123'
        assert call_kwargs['maxResults'] == 25
        assert len(call_kwargs['filters']) == 2

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimate_usage_all_filters(
        self, mock_create_client, mock_context
    ):
        """Test with all possible filter types."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.list_workload_estimate_usage.return_value = {'items': []}
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimate_usage(
            mock_context,
            'estimate-123',
            usage_account_id_filter='123456789012',
            service_code_filter='AmazonEC2',
            usage_type_filter='BoxUsage',
            operation_filter='RunInstances',
            location_filter='US East (N. Virginia)',
            usage_group_filter='compute',
            next_token='test-token',
            max_results=50,
        )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimate_usage.call_args[1]

        # Verify all parameters
        assert call_kwargs['workloadEstimateId'] == 'estimate-123'
        assert call_kwargs['maxResults'] == 50
        assert call_kwargs['nextToken'] == 'test-token'
        assert len(call_kwargs['filters']) == 6  # All filter types

        # Verify specific filter configurations
        filters = call_kwargs['filters']
        usage_account_filter = next((f for f in filters if f['name'] == 'USAGE_ACCOUNT_ID'), None)
        assert usage_account_filter is not None
        assert usage_account_filter['matchOption'] == 'EQUALS'
        assert usage_account_filter['values'] == ['123456789012']

        service_code_filter = next((f for f in filters if f['name'] == 'SERVICE_CODE'), None)
        assert service_code_filter is not None
        assert service_code_filter['matchOption'] == 'EQUALS'

        usage_type_filter = next((f for f in filters if f['name'] == 'USAGE_TYPE'), None)
        assert usage_type_filter is not None
        assert usage_type_filter['matchOption'] == 'CONTAINS'

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimate_usage_preferences_not_configured(
        self, mock_create_client, mock_context
    ):
        """Test when preferences are not configured."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {}  # No preferences
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimate_usage(mock_context, 'estimate-123')

        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'
        mock_bcm_client.list_workload_estimate_usage.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_describe_workload_estimate_usage_client_error(
        self, mock_handle_error, mock_create_client, mock_context
    ):
        """Test client error handling."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.list_workload_estimate_usage.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid workload estimate ID'}},
            'ListWorkloadEstimateUsage',
        )
        mock_create_client.return_value = mock_bcm_client
        mock_handle_error.return_value = {
            'status': 'error',
            'data': {'error': 'Invalid workload estimate ID'},
        }

        result = await describe_workload_estimate_usage(mock_context, 'invalid-estimate')

        assert result['status'] == 'error'
        mock_handle_error.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_describe_workload_estimate_usage_no_filters(
        self, mock_create_client, mock_context
    ):
        """Test with no filters applied."""
        mock_bcm_client = MagicMock()
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }
        mock_bcm_client.list_workload_estimate_usage.return_value = {'items': []}
        mock_create_client.return_value = mock_bcm_client

        result = await describe_workload_estimate_usage(mock_context, 'estimate-123')

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimate_usage.call_args[1]

        # Should only have required parameters, no filters
        assert 'filters' not in call_kwargs
        assert call_kwargs['workloadEstimateId'] == 'estimate-123'
        assert call_kwargs['maxResults'] == 25  # default value


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_format_usage_item_response_zero_quantity(self):
        """Test formatting usage item with zero quantity."""
        usage_item = {
            'id': 'zero-usage',
            'serviceCode': 'AmazonEC2',
            'quantity': {'amount': 0.0, 'unit': 'Hrs'},
            'cost': 0.0,
            'currency': 'USD',
        }

        result = format_usage_item_response(usage_item)

        assert result['quantity']['formatted'] == '0.00 Hrs'
        assert result['cost']['formatted'] == 'USD 0.00'

    def test_format_usage_item_response_none_quantity_amount(self):
        """Test formatting usage item with None quantity amount."""
        usage_item = {
            'id': 'none-usage',
            'serviceCode': 'AmazonS3',
            'quantity': {'amount': None, 'unit': 'GB'},
        }

        result = format_usage_item_response(usage_item)

        assert result['quantity']['formatted'] is None

    def test_format_workload_estimate_response_zero_cost(self):
        """Test formatting workload estimate with zero cost."""
        estimate = {
            'id': 'zero-cost-estimate',
            'name': 'Zero Cost Estimate',
            'status': 'VALID',
            'totalCost': 0.0,
            'costCurrency': 'USD',
        }

        result = format_workload_estimate_response(estimate)

        assert result['cost']['formatted'] == 'USD 0.00'

    def test_format_usage_item_response_missing_bill_interval(self):
        """Test formatting usage item with historical usage but no bill interval."""
        usage_item = {
            'id': 'no-interval-usage',
            'serviceCode': 'AmazonRDS',
            'historicalUsage': {
                'serviceCode': 'AmazonRDS',
                'usageType': 'InstanceUsage:db.t3.micro',
                # billInterval intentionally missing
            },
        }

        result = format_usage_item_response(usage_item)

        assert 'historical_usage' in result
        assert 'bill_interval' not in result['historical_usage']

    @pytest.mark.asyncio
    async def test_get_preferences_partial_response_fields(self, mock_context, mock_bcm_client):
        """Test get_preferences with response containing only some expected fields."""
        mock_bcm_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
            'unexpectedField': 'unexpected_value',
        }

        result = await get_preferences(mock_context, mock_bcm_client)

        assert result is True
        mock_context.info.assert_called()
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any('management account' in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_list_workload_estimates_empty_response_items(
        self, mock_context, mock_bcm_client
    ):
        """Test list_workload_estimates with empty items in response."""
        mock_bcm_client.list_workload_estimates.return_value = {
            'items': [],  # Empty list
            'nextToken': None,
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(mock_context)

        assert result['status'] == 'success'
        assert result['data']['workload_estimates'] == []
        assert result['data']['total_count'] == 0


class TestUncoveredLines:
    """Test specific uncovered lines to increase code coverage."""

    @pytest.mark.asyncio
    async def test_describe_workload_estimates_created_before_only(
        self, mock_context, mock_bcm_client
    ):
        """Test lines 138-140: created_before filter logic specifically."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                created_before='2023-12-31T23:59:59Z',
                # created_after intentionally omitted to test lines 138-140
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify only beforeTimestamp is set (lines 138-140)
        assert 'createdAtFilter' in call_kwargs
        assert 'beforeTimestamp' in call_kwargs['createdAtFilter']
        assert 'afterTimestamp' not in call_kwargs['createdAtFilter']

    @pytest.mark.asyncio
    async def test_describe_workload_estimates_expires_before_only(
        self, mock_context, mock_bcm_client
    ):
        """Test lines 149-151: expires_before filter logic specifically."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                expires_before='2023-12-31T23:59:59Z',
                # expires_after intentionally omitted to test lines 149-151
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify only beforeTimestamp is set (lines 149-151)
        assert 'expiresAtFilter' in call_kwargs
        assert 'beforeTimestamp' in call_kwargs['expiresAtFilter']
        assert 'afterTimestamp' not in call_kwargs['expiresAtFilter']

    @pytest.mark.asyncio
    async def test_describe_workload_estimates_created_after_only(
        self, mock_context, mock_bcm_client
    ):
        """Test created_after filter logic."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                created_after='2023-01-01T00:00:00Z',
                # created_before intentionally omitted
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify only afterTimestamp is set
        assert 'createdAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['createdAtFilter']
        assert 'beforeTimestamp' not in call_kwargs['createdAtFilter']

    @pytest.mark.asyncio
    async def test_describe_workload_estimates_expires_after_only(
        self, mock_context, mock_bcm_client
    ):
        """Test expires_after filter logic."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(
                mock_context,
                expires_after='2023-06-01T00:00:00Z',
                # expires_before intentionally omitted
            )

        assert result['status'] == 'success'
        call_kwargs = mock_bcm_client.list_workload_estimates.call_args[1]

        # Verify only afterTimestamp is set
        assert 'expiresAtFilter' in call_kwargs
        assert 'afterTimestamp' in call_kwargs['expiresAtFilter']
        assert 'beforeTimestamp' not in call_kwargs['expiresAtFilter']

    def test_format_workload_estimate_response_status_indicators(self):
        """Test lines 716-725: status indicator logic in format_workload_estimate_response."""
        # Test all known status indicators
        test_cases = [
            ('VALID', 'Valid'),
            ('UPDATING', 'Updating'),
            ('INVALID', 'Invalid'),
            ('ACTION_NEEDED', 'Action Needed'),
            ('UNKNOWN_STATUS', '❓ UNKNOWN_STATUS'),  # Test unknown status fallback
        ]

        for status, expected_indicator in test_cases:
            estimate = {
                'id': f'test-estimate-{status.lower()}',
                'name': f'Test Estimate {status}',
                'status': status,
            }

            result = format_workload_estimate_response(estimate)

            # Test lines 716-723: status indicator mapping
            assert result['status_indicator'] == expected_indicator
            assert result['status'] == status

    def test_format_workload_estimate_response_no_status(self):
        """Test format_workload_estimate_response when status is None or missing."""
        estimate = {
            'id': 'no-status-estimate',
            'name': 'No Status Estimate',
            # status intentionally omitted
        }

        result = format_workload_estimate_response(estimate)

        # When status is None/missing, status_indicator should not be added
        assert 'status_indicator' not in result
        assert result.get('status') is None

    @pytest.mark.asyncio
    async def test_list_workload_estimates_missing_items_key(self, mock_context, mock_bcm_client):
        """Test list_workload_estimates when response doesn't have 'items' key."""
        mock_bcm_client.list_workload_estimates.return_value = {
            # 'items' key is missing
            'nextToken': None
        }

        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
            return_value=mock_bcm_client,
        ):
            result = await describe_workload_estimates(mock_context)

        assert result['status'] == 'success'
        assert result['data']['workload_estimates'] == []
        assert result['data']['total_count'] == 0
