"""Tests for BCM Pricing Calculator Tools.

This module contains comprehensive tests for all methods in the BCM Pricing Calculator Tools,
ensuring complete code coverage and proper error handling.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools import (
    PREFERENCES_NOT_CONFIGURED_ERROR,
    bcm_pricing_calc_core,
    bcm_pricing_calculator_server,
    format_usage_item_response,
    format_workload_estimate_response,
    get_preferences,
    get_workload_estimate,
    list_workload_estimate_usage,
    list_workload_estimates,
)
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_bcm_pricing_calculator_client():
    """Create a mock BCM Pricing Calculator boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.get_preferences.return_value = {
        'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
        'memberAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
        'standaloneAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
    }

    mock_client.list_workload_estimates.return_value = {
        'items': [
            {
                'id': 'estimate-123',
                'name': 'Test Workload Estimate',
                'status': 'VALID',
                'rateType': 'BEFORE_DISCOUNTS',
                'createdAt': datetime(2023, 1, 1, 12, 0, 0),
                'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
                'rateTimestamp': datetime(2023, 1, 1, 0, 0, 0),
                'totalCost': 1500.50,
                'costCurrency': 'USD',
            },
            {
                'id': 'estimate-456',
                'name': 'Another Estimate',
                'status': 'UPDATING',
                'rateType': 'AFTER_DISCOUNTS',
                'createdAt': datetime(2023, 2, 1, 10, 0, 0),
                'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
                'rateTimestamp': datetime(2023, 2, 1, 0, 0, 0),
                'totalCost': 2000.75,
                'costCurrency': 'USD',
            },
        ],
        'nextToken': None,
    }

    mock_client.get_workload_estimate.return_value = {
        'id': 'estimate-123',
        'name': 'Test Workload Estimate',
        'status': 'VALID',
        'rateType': 'BEFORE_DISCOUNTS',
        'createdAt': datetime(2023, 1, 1, 12, 0, 0),
        'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
        'rateTimestamp': datetime(2023, 1, 1, 0, 0, 0),
        'totalCost': 1500.50,
        'costCurrency': 'USD',
    }

    mock_client.list_workload_estimate_usage.return_value = {
        'items': [
            {
                'id': 'usage-123',
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'group': 'EC2-Instance',
                'status': 'VALID',
                'currency': 'USD',
                'quantity': {
                    'amount': 744.0,
                    'unit': 'Hrs',
                },
                'cost': 50.25,
                'historicalUsage': {
                    'serviceCode': 'AmazonEC2',
                    'usageType': 'BoxUsage:t3.medium',
                    'operation': 'RunInstances',
                    'location': 'US East (N. Virginia)',
                    'usageAccountId': '123456789012',
                    'billInterval': {
                        'start': datetime(2023, 1, 1),
                        'end': datetime(2023, 1, 31),
                    },
                },
            },
        ],
        'nextToken': None,
    }

    return mock_client


@pytest.mark.asyncio
class TestGetPreferences:
    """Tests for get_preferences function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_success_management_account(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with account_types when management account preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        mock_create_client.assert_called_once_with(
            'bcm-pricing-calculator', region_name='us-east-1'
        )
        mock_bcm_pricing_calculator_client.get_preferences.assert_called_once()
        assert 'account_types' in result
        assert 'management account' in result['account_types']
        mock_context.info.assert_called()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_success_member_account(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with account_types when member account preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {
            'memberAccountRateTypeSelections': ['AFTER_DISCOUNTS']
        }

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'member account' in result['account_types']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_success_standalone_account(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with account_types when standalone account preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS']
        }

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'standalone account' in result['account_types']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_not_configured(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with error when no preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {}

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'error' in result
        assert 'BCM Pricing Calculator preferences are not configured' in result['error']
        mock_context.error.assert_called()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_get_preferences_exception(
        self, mock_handle_error, mock_create_client, mock_context
    ):
        """Test get_preferences handles exceptions properly."""
        # Setup
        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'GetPreferences'
        )
        mock_create_client.side_effect = error
        mock_handle_error.return_value = {'data': {'error': 'Access denied'}}

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'get_preferences', 'BCM Pricing Calculator'
        )
        assert 'error' in result
        assert (
            'Failed to check BCM Pricing Calculator preferences: Access denied' in result['error']
        )
        mock_context.error.assert_called()


@pytest.mark.asyncio
class TestListWorkloadEstimates:
    """Tests for list_workload_estimates function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_success(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates returns formatted estimates."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': 'management account'}

        # Execute
        result = await list_workload_estimates(mock_context, max_results=50)

        # Assert
        mock_create_client.assert_called_once_with('bcm-pricing-calculator')
        mock_get_preferences.assert_called_once()
        mock_bcm_pricing_calculator_client.list_workload_estimates.assert_called_once()

        assert result['status'] == 'success'
        assert 'workload_estimates' in result['data']
        assert len(result['data']['workload_estimates']) == 2
        assert result['data']['total_count'] == 2
        assert result['data']['has_more_results'] is False

        # Check first estimate details
        first_estimate = result['data']['workload_estimates'][0]
        assert first_estimate['id'] == 'estimate-123'
        assert first_estimate['name'] == 'Test Workload Estimate'
        assert first_estimate['status'] == 'VALID'
        assert first_estimate['status_indicator'] == 'Valid'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_with_filters(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates with various filters."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': 'management account'}

        # Execute
        result = await list_workload_estimates(
            mock_context,
            created_after='2023-01-01T00:00:00Z',
            created_before='2023-12-31T23:59:59Z',
            expires_after='2023-06-01T00:00:00Z',
            expires_before='2024-01-01T00:00:00Z',
            status_filter='VALID',
            name_filter='Test',
            name_match_option='CONTAINS',
            max_results=25,
        )

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert call_kwargs['maxResults'] == 25
        assert 'createdAtFilter' in call_kwargs
        assert 'expiresAtFilter' in call_kwargs
        assert 'filters' in call_kwargs
        assert len(call_kwargs['filters']) == 2  # status and name filters

        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_list_workload_estimates_preferences_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimates when preferences are not configured."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured'
        }

        # Execute
        result = await list_workload_estimates(mock_context)

        # Assert
        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_list_workload_estimates_exception(
        self, mock_handle_error, mock_create_client, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimates handles exceptions properly."""
        # Setup
        error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}},
            'ListWorkloadEstimates',
        )
        mock_get_preferences.return_value = {'account_types': 'management account'}
        mock_create_client.return_value.list_workload_estimates.side_effect = error
        mock_handle_error.return_value = {'status': 'error', 'message': 'Invalid parameter'}

        # Execute
        result = await list_workload_estimates(mock_context)

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'list_workload_estimates', 'BCM Pricing Calculator'
        )
        assert result['status'] == 'error'


@pytest.mark.asyncio
class TestGetWorkloadEstimate:
    """Tests for get_workload_estimate function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_workload_estimate_success(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test get_workload_estimate returns formatted estimate."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': 'management account'}

        # Execute
        result = await get_workload_estimate(mock_context, identifier='estimate-123')

        # Assert
        mock_create_client.assert_called_once_with('bcm-pricing-calculator')
        mock_get_preferences.assert_called_once()
        mock_bcm_pricing_calculator_client.get_workload_estimate.assert_called_once_with(
            identifier='estimate-123'
        )

        assert result['status'] == 'success'
        assert 'workload_estimate' in result['data']
        assert result['data']['identifier'] == 'estimate-123'

        estimate = result['data']['workload_estimate']
        assert estimate['id'] == 'estimate-123'
        assert estimate['name'] == 'Test Workload Estimate'
        assert estimate['status'] == 'VALID'

    async def test_get_workload_estimate_missing_identifier(self, mock_context):
        """Test get_workload_estimate returns error when identifier is missing."""
        # Execute
        result = await get_workload_estimate(mock_context, identifier=None)

        # Assert
        assert result['status'] == 'error'
        assert 'Identifier is required' in result['data']['error']
        assert result['data']['error_code'] == 'MISSING_PARAMETER'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_get_workload_estimate_preferences_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test get_workload_estimate when preferences are not configured."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured'
        }

        # Execute
        result = await get_workload_estimate(mock_context, identifier='estimate-123')

        # Assert
        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'


@pytest.mark.asyncio
class TestListWorkloadEstimateUsage:
    """Tests for list_workload_estimate_usage function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimate_usage_success(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimate_usage returns formatted usage items."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute
        result = await list_workload_estimate_usage(
            mock_context,
            workload_estimate_id='estimate-123',
            service_code_filter='AmazonEC2',
            max_results=50,
        )

        # Assert
        mock_create_client.assert_called_once_with('bcm-pricing-calculator')
        mock_get_preferences.assert_called_once()
        mock_bcm_pricing_calculator_client.list_workload_estimate_usage.assert_called_once()

        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimate_usage.call_args[1]
        assert call_kwargs['workloadEstimateId'] == 'estimate-123'
        assert call_kwargs['maxResults'] == 50
        assert 'filters' in call_kwargs
        assert len(call_kwargs['filters']) == 1  # service_code_filter

        assert result['status'] == 'success'
        assert 'usage_items' in result['data']
        assert len(result['data']['usage_items']) == 1
        assert result['data']['workload_estimate_id'] == 'estimate-123'

        # Check usage item details
        usage_item = result['data']['usage_items'][0]
        assert usage_item['id'] == 'usage-123'
        assert usage_item['service_code'] == 'AmazonEC2'
        assert usage_item['usage_type'] == 'BoxUsage:t3.medium'

    async def test_list_workload_estimate_usage_missing_id(self, mock_context):
        """Test list_workload_estimate_usage returns error when workload_estimate_id is missing."""
        # Execute
        result = await list_workload_estimate_usage(mock_context, workload_estimate_id=None)

        # Assert
        assert result['status'] == 'error'
        assert 'workload_estimate_id is required' in result['data']['error']
        assert result['data']['error_code'] == 'MISSING_PARAMETER'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimate_usage_with_all_filters(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimate_usage with all possible filters."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute
        result = await list_workload_estimate_usage(
            mock_context,
            workload_estimate_id='estimate-123',
            usage_account_id_filter='123456789012',
            service_code_filter='AmazonEC2',
            usage_type_filter='BoxUsage',
            operation_filter='RunInstances',
            location_filter='US East (N. Virginia)',
            usage_group_filter='EC2-Instance',
            max_results=100,
        )

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimate_usage.call_args[1]
        assert len(call_kwargs['filters']) == 6  # All filters applied
        assert result['status'] == 'success'


class TestFormatWorkloadEstimateResponse:
    """Tests for format_workload_estimate_response function."""

    def test_format_workload_estimate_response_basic(self):
        """Test format_workload_estimate_response with basic fields."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'rateType': 'BEFORE_DISCOUNTS',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['id'] == 'estimate-123'
        assert result['name'] == 'Test Estimate'
        assert result['status'] == 'VALID'
        assert result['rate_type'] == 'BEFORE_DISCOUNTS'
        assert result['status_indicator'] == 'Valid'

    def test_format_workload_estimate_response_with_timestamps(self):
        """Test format_workload_estimate_response with timestamp fields."""
        # Setup
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        expires_at = datetime(2023, 12, 31, 23, 59, 59)
        rate_timestamp = datetime(2023, 1, 1, 0, 0, 0)

        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'UPDATING',
            'createdAt': created_at,
            'expiresAt': expires_at,
            'rateTimestamp': rate_timestamp,
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'created_at' in result
        assert result['created_at']['timestamp'] == created_at.isoformat()
        assert result['created_at']['formatted'] == '2023-01-01 12:00:00 UTC'

        assert 'expires_at' in result
        assert result['expires_at']['timestamp'] == expires_at.isoformat()

        assert 'rate_timestamp' in result
        assert result['rate_timestamp']['timestamp'] == rate_timestamp.isoformat()

        assert result['status_indicator'] == 'Updating'

    def test_format_workload_estimate_response_with_cost(self):
        """Test format_workload_estimate_response with cost information."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'totalCost': 1500.50,
            'costCurrency': 'USD',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'cost' in result
        assert result['cost']['amount'] == 1500.50
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] == 'USD 1,500.50'

    def test_format_workload_estimate_response_with_failure_message(self):
        """Test format_workload_estimate_response with failure message."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'INVALID',
            'failureMessage': 'Invalid configuration detected',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['failure_message'] == 'Invalid configuration detected'
        assert result['status_indicator'] == 'Invalid'

    def test_format_workload_estimate_response_action_needed_status(self):
        """Test format_workload_estimate_response with ACTION_NEEDED status."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'ACTION_NEEDED',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['status_indicator'] == 'Action Needed'

    def test_format_workload_estimate_response_unknown_status(self):
        """Test format_workload_estimate_response with unknown status."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'UNKNOWN_STATUS',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['status_indicator'] == '❓ UNKNOWN_STATUS'


class TestFormatUsageItemResponse:
    """Tests for format_usage_item_response function."""

    def test_format_usage_item_response_basic(self):
        """Test format_usage_item_response with basic fields."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'usageType': 'BoxUsage:t3.medium',
            'operation': 'RunInstances',
            'location': 'US East (N. Virginia)',
            'usageAccountId': '123456789012',
            'group': 'EC2-Instance',
            'status': 'VALID',
            'currency': 'USD',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'
        assert result['usage_type'] == 'BoxUsage:t3.medium'
        assert result['operation'] == 'RunInstances'
        assert result['location'] == 'US East (N. Virginia)'
        assert result['usage_account_id'] == '123456789012'
        assert result['group'] == 'EC2-Instance'
        assert result['status'] == 'VALID'
        assert result['currency'] == 'USD'
        assert result['status_indicator'] == 'Valid'

    def test_format_usage_item_response_with_quantity(self):
        """Test format_usage_item_response with quantity information."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'quantity': {
                'amount': 744.0,
                'unit': 'Hrs',
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'quantity' in result
        assert result['quantity']['amount'] == 744.0
        assert result['quantity']['unit'] == 'Hrs'
        assert result['quantity']['formatted'] == '744.00 Hrs'

    def test_format_usage_item_response_with_cost(self):
        """Test format_usage_item_response with cost information."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'cost': 50.25,
            'currency': 'USD',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'cost' in result
        assert result['cost']['amount'] == 50.25
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] == 'USD 50.25'

    def test_format_usage_item_response_with_historical_usage(self):
        """Test format_usage_item_response with historical usage information."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'billInterval': {
                    'start': datetime(2023, 1, 1),
                    'end': datetime(2023, 1, 31),
                },
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'historical_usage' in result
        historical = result['historical_usage']
        assert historical['service_code'] == 'AmazonEC2'
        assert historical['usage_type'] == 'BoxUsage:t3.medium'
        assert historical['operation'] == 'RunInstances'
        assert historical['location'] == 'US East (N. Virginia)'
        assert historical['usage_account_id'] == '123456789012'
        assert 'bill_interval' in historical
        assert historical['bill_interval']['start'] == '2023-01-01T00:00:00'
        assert historical['bill_interval']['end'] == '2023-01-31T00:00:00'

    def test_format_usage_item_response_quantity_none_amount(self):
        """Test format_usage_item_response with None quantity amount."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'quantity': {
                'amount': None,
                'unit': 'Hrs',
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'quantity' in result
        assert result['quantity']['amount'] is None
        assert result['quantity']['unit'] == 'Hrs'
        assert result['quantity']['formatted'] is None

    def test_format_usage_item_response_stale_status(self):
        """Test format_usage_item_response with STALE status."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'STALE',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['status_indicator'] == 'Stale'

    def test_format_usage_item_response_invalid_status(self):
        """Test format_usage_item_response with INVALID status."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'INVALID',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['status_indicator'] == 'Invalid'

    def test_format_usage_item_response_unknown_status(self):
        """Test format_usage_item_response with unknown status."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'UNKNOWN_STATUS',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['status_indicator'] == '❓ UNKNOWN_STATUS'


def test_bcm_pricing_calculator_server_initialization():
    """Test that the bcm_pricing_calculator_server is properly initialized."""
    # Verify the server name
    assert bcm_pricing_calculator_server.name == 'bcm-pricing-calc-tools'

    # Verify the server instructions
    instructions = bcm_pricing_calculator_server.instructions
    assert instructions is not None
    assert 'BCM Pricing Calculator tools' in instructions


class TestAdditionalFormattingCases:
    """Tests for additional formatting edge cases to achieve complete coverage."""

    def test_format_usage_item_response_no_quantity(self):
        """Test format_usage_item_response with no quantity field."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'VALID',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'quantity' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'
        assert result['status'] == 'VALID'

    def test_format_usage_item_response_no_cost(self):
        """Test format_usage_item_response with no cost field."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'VALID',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'cost' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'

    def test_format_usage_item_response_no_status(self):
        """Test format_usage_item_response with no status field."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'status_indicator' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'

    def test_format_usage_item_response_default_currency(self):
        """Test format_usage_item_response uses default USD currency."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            # No currency field provided
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['currency'] == 'USD'

    def test_format_usage_item_response_historical_usage_no_bill_interval_start_end(self):
        """Test format_usage_item_response with historical usage but no start/end in bill interval."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'billInterval': {
                    'start': None,
                    'end': None,
                },
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'historical_usage' in result
        historical = result['historical_usage']
        assert 'bill_interval' in historical
        assert historical['bill_interval']['start'] is None
        assert historical['bill_interval']['end'] is None

    def test_format_workload_estimate_response_no_status(self):
        """Test format_workload_estimate_response with no status field."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'rateType': 'BEFORE_DISCOUNTS',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'status_indicator' not in result
        assert result['id'] == 'estimate-123'
        assert result['name'] == 'Test Estimate'

    def test_format_workload_estimate_response_no_failure_message(self):
        """Test format_workload_estimate_response with no failure message."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'failure_message' not in result
        assert result['id'] == 'estimate-123'
        assert result['status'] == 'VALID'


@pytest.mark.asyncio
class TestMissingCoverageBranches:
    """Tests specifically targeting lines 100-148 that are missing coverage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_management_account_only(self, mock_create_client, mock_context):
        """Test get_preferences with only management account preferences (covers lines ~100-110)."""
        # Setup - only management account preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': [
                'BEFORE_DISCOUNTS',
                'AFTER_DISCOUNTS_AND_COMMITMENTS',
            ]
            # No member or standalone account selections
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'management account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the specific log message for management account
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any('management account' in call for call in info_calls)

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_member_account_only(self, mock_create_client, mock_context):
        """Test get_preferences with only member account preferences (covers lines ~100-110)."""
        # Setup - only member account preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'memberAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
            # No management or standalone account selections
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'member account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the specific log message for member account
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any('member account' in call for call in info_calls)

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_standalone_account_only(self, mock_create_client, mock_context):
        """Test get_preferences with only standalone account preferences (covers lines ~100-110)."""
        # Setup - only standalone account preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS']
            # No management or member account selections
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'standalone account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the specific log message for standalone account
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any('standalone account' in call for call in info_calls)

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_multiple_account_types(self, mock_create_client, mock_context):
        """Test get_preferences with multiple account type preferences (covers lines ~100-110)."""
        # Setup - multiple account type preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
            'memberAccountRateTypeSelections': ['AFTER_DISCOUNTS'],
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS'],
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'management account' in result['account_types']
        assert 'member account' in result['account_types']
        assert 'standalone account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the log message contains all account types
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        combined_message = ' '.join(info_calls)
        assert 'management account' in combined_message
        assert 'member account' in combined_message
        assert 'standalone account' in combined_message

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_created_after_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for created_after only (covers lines ~120-130)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only created_after
        result = await list_workload_estimates(mock_context, created_after='2023-01-01T00:00:00Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'createdAtFilter' in call_kwargs
        created_filter = call_kwargs['createdAtFilter']
        assert 'afterTimestamp' in created_filter
        assert 'beforeTimestamp' not in created_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_created_before_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for created_before only (covers lines ~120-130)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only created_before
        result = await list_workload_estimates(mock_context, created_before='2023-12-31T23:59:59Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'createdAtFilter' in call_kwargs
        created_filter = call_kwargs['createdAtFilter']
        assert 'beforeTimestamp' in created_filter
        assert 'afterTimestamp' not in created_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_expires_after_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for expires_after only (covers lines ~130-140)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only expires_after
        result = await list_workload_estimates(mock_context, expires_after='2023-06-01T00:00:00Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'expiresAtFilter' in call_kwargs
        expires_filter = call_kwargs['expiresAtFilter']
        assert 'afterTimestamp' in expires_filter
        assert 'beforeTimestamp' not in expires_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_expires_before_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for expires_before only (covers lines ~130-140)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only expires_before
        result = await list_workload_estimates(mock_context, expires_before='2024-01-01T00:00:00Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'expiresAtFilter' in call_kwargs
        expires_filter = call_kwargs['expiresAtFilter']
        assert 'beforeTimestamp' in expires_filter
        assert 'afterTimestamp' not in expires_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_filter_building_status_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates filter building for status only (covers lines ~140-148)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only status filter
        result = await list_workload_estimates(mock_context, status_filter='VALID')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'filters' in call_kwargs
        filters = call_kwargs['filters']
        assert len(filters) == 1
        assert filters[0]['name'] == 'STATUS'
        assert filters[0]['values'] == ['VALID']
        assert filters[0]['matchOption'] == 'EQUALS'
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_filter_building_name_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates filter building for name only (covers lines ~140-148)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only name filter
        result = await list_workload_estimates(
            mock_context, name_filter='Test', name_match_option='STARTS_WITH'
        )

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'filters' in call_kwargs
        filters = call_kwargs['filters']
        assert len(filters) == 1
        assert filters[0]['name'] == 'NAME'
        assert filters[0]['values'] == ['Test']
        assert filters[0]['matchOption'] == 'STARTS_WITH'
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_no_filters_applied(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates with no filters (covers the filters conditional logic)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with no filters
        result = await list_workload_estimates(mock_context)

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        # Should not have filters key when no filters are applied
        assert 'filters' not in call_kwargs or not call_kwargs.get('filters')
        assert result['status'] == 'success'


@pytest.mark.asyncio
class TestAdditionalConditionalBranches:
    """Tests for additional conditional branches to achieve complete coverage."""


@pytest.mark.asyncio
class TestListWorkloadEstimateUsagePreferencesNotConfigured:
    """Test for line 476 - preferences not configured in list_workload_estimate_usage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_list_workload_estimate_usage_preferences_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimate_usage when preferences are not configured (line 476)."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured - no rate type selections found'
        }

        # Execute
        result = await list_workload_estimate_usage(
            mock_context, workload_estimate_id='estimate-123'
        )

        # Assert
        assert result['status'] == 'error'
        assert (
            result['data']['error']
            == 'BCM Pricing Calculator preferences are not configured - no rate type selections found'
        )
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.paginate_aws_response'
    )
    async def test_list_workload_estimates_with_pagination(
        self,
        mock_paginate_aws_response,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates with pagination token."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Mock the paginate_aws_response function to prevent infinite loop
        mock_paginate_aws_response.return_value = (
            [],  # results
            {  # pagination_metadata
                'total_count': 0,
                'next_token': 'next-page-token',
                'has_more_results': True,
                'pages_fetched': 1,
            },
        )

        # Execute
        result = await list_workload_estimates(
            mock_context, next_token='current-token', max_pages=2
        )

        # Assert
        mock_paginate_aws_response.assert_called_once()
        assert result['status'] == 'success'
        assert result['data']['pagination']['next_token'] == 'next-page-token'
        assert result['data']['pagination']['has_more_results'] is True

    @pytest.mark.asyncio
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.paginate_aws_response'
    )
    async def test_list_workload_estimate_usage_with_pagination(
        self,
        mock_paginate_aws_response,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimate_usage with pagination token."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Mock the paginate_aws_response function to prevent infinite loop
        mock_paginate_aws_response.return_value = (
            [],  # results
            {  # pagination_metadata
                'total_count': 0,
                'next_token': 'usage-next-token',
                'has_more_results': True,
                'pages_fetched': 1,
            },
        )

        # Execute
        result = await list_workload_estimate_usage(
            mock_context,
            workload_estimate_id='estimate-123',
            next_token='usage-current-token',
            max_pages=2,
        )

        # Assert
        mock_paginate_aws_response.assert_called_once()
        assert result['status'] == 'success'
        assert result['data']['pagination']['next_token'] == 'usage-next-token'
        assert result['data']['pagination']['has_more_results'] is True

    def test_format_workload_estimate_response_with_string_timestamps(self):
        """Test format_workload_estimate_response with string timestamps."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'createdAt': '2023-01-01T12:00:00Z',
            'expiresAt': '2023-12-31T23:59:59Z',
            'rateTimestamp': '2023-01-01T00:00:00Z',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['created_at']['timestamp'] == '2023-01-01T12:00:00Z'
        assert result['created_at']['formatted'] == '2023-01-01T12:00:00Z'
        assert result['expires_at']['timestamp'] == '2023-12-31T23:59:59Z'
        assert result['rate_timestamp']['timestamp'] == '2023-01-01T00:00:00Z'

    def test_format_workload_estimate_response_none_cost(self):
        """Test format_workload_estimate_response with None total cost."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'totalCost': None,
            'costCurrency': 'USD',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'cost' in result
        assert result['cost']['amount'] is None
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] is None

    def test_format_usage_item_response_no_historical_bill_interval(self):
        """Test format_usage_item_response with historical usage but no bill interval."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                # No billInterval
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'historical_usage' in result
        historical = result['historical_usage']
        assert 'bill_interval' not in historical

    def test_format_usage_item_response_empty_historical_usage(self):
        """Test format_usage_item_response with empty historical usage."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {},
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        # Empty historicalUsage dict should not add historical_usage to result
        assert 'historical_usage' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_get_workload_estimate_exception(
        self, mock_handle_error, mock_create_client, mock_get_preferences, mock_context
    ):
        """Test get_workload_estimate handles exceptions properly."""
        # Setup
        error = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Estimate not found'}},
            'GetWorkloadEstimate',
        )
        mock_get_preferences.return_value = {'account_types': ['management account']}
        mock_create_client.return_value.get_workload_estimate.side_effect = error
        mock_handle_error.return_value = {'status': 'error', 'message': 'Estimate not found'}

        # Execute
        result = await get_workload_estimate(mock_context, identifier='nonexistent-estimate')

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'get_workload_estimate', 'BCM Pricing Calculator'
        )
        assert result['status'] == 'error'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_list_workload_estimate_usage_exception(
        self, mock_handle_error, mock_create_client, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimate_usage handles exceptions properly."""
        # Setup
        error = BotoCoreError()
        mock_get_preferences.return_value = {'account_types': ['management account']}
        mock_create_client.return_value.list_workload_estimate_usage.side_effect = error
        mock_handle_error.return_value = {'status': 'error', 'message': 'Connection error'}

        # Execute
        result = await list_workload_estimate_usage(
            mock_context, workload_estimate_id='estimate-123'
        )

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'list_workload_estimate_usage', 'BCM Pricing Calculator'
        )
        assert result['status'] == 'error'


@pytest.mark.parametrize(
    'status,expected_indicator',
    [
        ('VALID', 'Valid'),
        ('UPDATING', 'Updating'),
        ('INVALID', 'Invalid'),
        ('ACTION_NEEDED', 'Action Needed'),
        ('UNKNOWN', '❓ UNKNOWN'),
    ],
)
def test_format_workload_estimate_response_status_indicators(status, expected_indicator):
    """Test format_workload_estimate_response status indicators."""
    # Setup
    estimate = {
        'id': 'estimate-123',
        'name': 'Test Estimate',
        'status': status,
    }

    # Execute
    result = format_workload_estimate_response(estimate)

    # Assert
    assert result['status_indicator'] == expected_indicator


@pytest.mark.parametrize(
    'status,expected_indicator',
    [
        ('VALID', 'Valid'),
        ('INVALID', 'Invalid'),
        ('STALE', 'Stale'),
        ('UNKNOWN', '❓ UNKNOWN'),
    ],
)
def test_format_usage_item_response_status_indicators(status, expected_indicator):
    """Test format_usage_item_response status indicators."""
    # Setup
    usage_item = {
        'id': 'usage-123',
        'serviceCode': 'AmazonEC2',
        'status': status,
    }

    # Execute
    result = format_usage_item_response(usage_item)

    # Assert
    assert result['status_indicator'] == expected_indicator


@pytest.mark.asyncio
class TestBcmPricingCalcCoreFunction:
    """Tests for the core bcm_pricing_calc_core function (lines 101-149)."""

    async def test_bcm_pricing_calc_core_invalid_operation(self, mock_context):
        """Test bcm_pricing_calc_core with invalid operation (covers lines 106-113)."""
        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='invalid_operation')

        # Assert
        assert result['status'] == 'error'
        assert 'Invalid operation' in result['message']
        assert 'invalid_parameter' in result['data']
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: invalid_operation'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_workload_estimate'
    )
    async def test_bcm_pricing_calc_core_get_workload_estimate_operation(
        self, mock_get_workload_estimate, mock_context
    ):
        """Test bcm_pricing_calc_core with get_workload_estimate operation (covers lines 115-117)."""
        # Setup
        mock_get_workload_estimate.return_value = {
            'status': 'success',
            'data': {'workload_estimate': {}},
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context, operation='get_workload_estimate', identifier='estimate-123'
        )

        # Assert
        mock_get_workload_estimate.assert_called_once_with(mock_context, 'estimate-123')
        assert result['status'] == 'success'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: get_workload_estimate'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.list_workload_estimates'
    )
    async def test_bcm_pricing_calc_core_list_workload_estimates_operation(
        self, mock_list_workload_estimates, mock_context
    ):
        """Test bcm_pricing_calc_core with list_workload_estimates operation (covers lines 118-121)."""
        # Setup
        mock_list_workload_estimates.return_value = {
            'status': 'success',
            'data': {'workload_estimates': []},
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context,
            operation='list_workload_estimates',
            created_after='2023-01-01T00:00:00Z',
            created_before='2023-12-31T23:59:59Z',
            expires_after='2023-06-01T00:00:00Z',
            expires_before='2024-01-01T00:00:00Z',
            status_filter='VALID',
            name_filter='Test',
            name_match_option='CONTAINS',
            next_token='token123',
            max_results=50,
        )

        # Assert
        mock_list_workload_estimates.assert_called_once_with(
            mock_context,
            '2023-01-01T00:00:00Z',
            '2023-12-31T23:59:59Z',
            '2023-06-01T00:00:00Z',
            '2024-01-01T00:00:00Z',
            'VALID',
            'Test',
            'CONTAINS',
            'token123',
            50,
            None,
        )
        assert result['status'] == 'success'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: list_workload_estimates'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.list_workload_estimate_usage'
    )
    async def test_bcm_pricing_calc_core_list_workload_estimate_usage_operation(
        self, mock_list_usage, mock_context
    ):
        """Test bcm_pricing_calc_core with list_workload_estimate_usage operation (covers lines 122-125)."""
        # Setup
        mock_list_usage.return_value = {'status': 'success', 'data': {'usage_items': []}}

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context,
            operation='list_workload_estimate_usage',
            identifier='estimate-123',
            usage_account_id_filter='123456789012',
            service_code_filter='AmazonEC2',
            usage_type_filter='BoxUsage',
            operation_filter='RunInstances',
            location_filter='US East (N. Virginia)',
            usage_group_filter='EC2-Instance',
            next_token='usage-token',
            max_results=100,
        )

        # Assert
        mock_list_usage.assert_called_once_with(
            mock_context,
            'estimate-123',
            '123456789012',
            'AmazonEC2',
            'BoxUsage',
            'RunInstances',
            'US East (N. Virginia)',
            'EC2-Instance',
            'usage-token',
            100,
            None,
        )
        assert result['status'] == 'success'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: list_workload_estimate_usage'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_bcm_pricing_calc_core_get_preferences_operation_success(
        self, mock_get_preferences, mock_context
    ):
        """Test bcm_pricing_calc_core with get_preferences operation - success case (covers lines 126-133)."""
        # Setup
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='get_preferences')

        # Assert
        mock_get_preferences.assert_called_once_with(mock_context)
        assert result['status'] == 'success'
        assert result['data']['message'] == 'Preferences are properly configured'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: get_preferences'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_bcm_pricing_calc_core_get_preferences_operation_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test bcm_pricing_calc_core with get_preferences operation - not configured case (covers lines 127-131)."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured. Please configure preferences before using this service.'
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='get_preferences')

        # Assert
        mock_get_preferences.assert_called_once_with(mock_context)
        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['message'] == PREFERENCES_NOT_CONFIGURED_ERROR
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: get_preferences'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_workload_estimate'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_bcm_pricing_calc_core_exception_handling(
        self, mock_handle_error, mock_get_workload_estimate, mock_context
    ):
        """Test bcm_pricing_calc_core exception handling (covers lines 137-149)."""
        # Setup
        test_error = Exception('Test error')
        mock_get_workload_estimate.side_effect = test_error
        mock_handle_error.return_value = {
            'data': {'error': 'Test error message'},
            'status': 'error',
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context, operation='get_workload_estimate', identifier='estimate-123'
        )

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context,
            test_error,
            'get_workload_estimate',
            'AWS Billing and Cost Management Pricing Calculator',
        )
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in error_call_args
        )
        assert 'Test error message' in error_call_args

        assert result['status'] == 'error'
        assert result['data']['error'] == 'Test error message'
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in result['message']
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.list_workload_estimates'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_bcm_pricing_calc_core_exception_handling_no_error_in_response(
        self, mock_handle_error, mock_list_estimates, mock_context
    ):
        """Test bcm_pricing_calc_core exception handling when error response has no error field (covers lines 137-149)."""
        # Setup
        test_error = Exception('Direct error message')
        mock_list_estimates.side_effect = test_error
        mock_handle_error.return_value = {
            'data': {},  # No error field in data
            'status': 'error',
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='list_workload_estimates')

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context,
            test_error,
            'list_workload_estimates',
            'AWS Billing and Cost Management Pricing Calculator',
        )
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in error_call_args
        )
        assert 'Direct error message' in error_call_args

        assert result['status'] == 'error'
        assert result['data']['error'] == 'Direct error message'
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in result['message']
        )
