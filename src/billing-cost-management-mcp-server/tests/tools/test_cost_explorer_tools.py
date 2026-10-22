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

"""Unit tests for the cost_explorer_tools module.

These tests verify the functionality of the Cost Explorer tools, including:
- Getting cost and usage data with various filters and metrics
- Getting dimension values for different cost categories
- Getting cost forecasts with different parameters
- Error handling for invalid or missing parameters
- Error handling for API exceptions
"""

import asyncio
import botocore.session
import fastmcp
import importlib
import json
import jsonschema
import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.cost_explorer_operations import (
    get_cost_and_usage,
    get_cost_and_usage_with_resources,
    get_cost_categories,
    get_cost_forecast,
    get_dimension_values,
    get_savings_plans_utilization,
    get_tags,
    get_usage_forecast,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_explorer_tools import (
    cost_explorer_server,
)
from botocore.validate import ParamValidator
from datetime import date, datetime, timedelta
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


async def cost_explorer(ctx, operation, **kwargs):
    """Mock implementation of cost_explorer for testing."""
    # Import utilities inside function to avoid circular imports
    from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
        create_aws_client,
        format_response,
        handle_aws_error,
    )

    try:
        # Create CE client
        ce_client = create_aws_client('ce')

        # Route to the appropriate operation
        if operation == 'getCostAndUsage':
            # Check for required parameters
            if not kwargs.get('start_date') or not kwargs.get('end_date'):
                return format_response(
                    'error',
                    {},
                    'start_date and end_date are required for getCostAndUsage operation',
                )

            # Call the client directly for testing
            request_params = {
                'TimePeriod': {'Start': kwargs.get('start_date'), 'End': kwargs.get('end_date')},
                'Granularity': kwargs.get('granularity', 'DAILY'),
                'Metrics': [kwargs.get('metrics', 'UnblendedCost')],
            }

            response = ce_client.get_cost_and_usage(**request_params)
            return format_response('success', response)

        elif operation == 'getDimensionValues':
            # Check for required parameters
            if not kwargs.get('dimension'):
                return format_response(
                    'error',
                    {},
                    'dimension is required for getDimensionValues operation',
                )

            # Call the client directly for testing
            request_params = {
                'TimePeriod': {
                    'Start': kwargs.get('start_date', '2023-01-01'),
                    'End': kwargs.get('end_date', '2023-01-31'),
                },
                'Dimension': kwargs.get('dimension'),
            }

            response = ce_client.get_dimension_values(**request_params)
            return format_response('success', response)

        elif operation == 'getCostForecast':
            # Check for required parameters
            if not kwargs.get('metric'):
                return format_response(
                    'error',
                    {},
                    'metric is required for getCostForecast operation',
                )

            # Call the client directly for testing
            request_params = {
                'TimePeriod': {
                    'Start': kwargs.get('start_date', '2023-02-01'),
                    'End': kwargs.get('end_date', '2023-02-28'),
                },
                'Metric': kwargs.get('metric'),
                'Granularity': kwargs.get('granularity', 'MONTHLY'),
                'PredictionIntervalLevel': kwargs.get('prediction_interval_level', 80),
            }

            response = ce_client.get_cost_forecast(**request_params)
            return format_response('success', response)

        else:
            # Unknown operation
            await ctx.error(f'Unknown operation: {operation}')
            return format_response(
                'error',
                {},
                f'Unknown operation: {operation}. Supported operations: getCostAndUsage, getDimensionValues, getCostForecast',
            )

    except Exception as e:
        # Handle any exceptions
        return await handle_aws_error(ctx, e, operation, 'Cost Explorer')


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.get_cost_and_usage.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                'Total': {'UnblendedCost': {'Amount': '100.0', 'Unit': 'USD'}},
            }
        ]
    }

    mock_client.get_cost_and_usage_with_resources.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                'Groups': [
                    {
                        'Keys': ['AWS Lambda'],
                        'Metrics': {'UnblendedCost': {'Amount': '50.0', 'Unit': 'USD'}},
                    }
                ],
            }
        ],
        'DimensionValueAttributes': [],
    }

    mock_client.get_dimension_values.return_value = {
        'DimensionValues': [
            {'Value': 'AWS Lambda', 'Attributes': {}},
            {'Value': 'Amazon S3', 'Attributes': {}},
        ]
    }

    mock_client.get_cost_forecast.return_value = {
        'Total': {'Amount': '150.0', 'Unit': 'USD'},
        'ForecastResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-02-01', 'End': '2023-02-28'},
                'MeanValue': '150.0',
            }
        ],
    }

    mock_client.get_tags.return_value = {'Tags': ['Environment', 'Project']}

    mock_client.get_cost_categories.return_value = {'CostCategoryNames': ['Department', 'Team']}

    mock_client.get_savings_plans_utilization.return_value = {
        'SavingsPlansUtilizationsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-31'},
                'Utilization': {'Utilization': '0.85'},
            }
        ]
    }

    return mock_client


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def sample_billing_view_arn():
    """Sample billing view ARN for testing billing view support."""
    return 'arn:aws:billing::123456789012:billingview/custom-view-abc123'


@pytest.mark.asyncio
async def test_cost_explorer_get_cost_and_usage(mock_context, mock_ce_client):
    """Test the cost_explorer function with getCostAndUsage operation."""
    # Patch the create_aws_client function to return our mock client
    with patch(
        'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.create_aws_client',
        return_value=mock_ce_client,
    ):
        # Call the cost_explorer function directly
        result = await cost_explorer(
            mock_context,
            operation='getCostAndUsage',
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='MONTHLY',
            metrics='UnblendedCost',
        )

    # Verify the function called the client method with the right parameters
    mock_ce_client.get_cost_and_usage.assert_called_once()
    call_kwargs = mock_ce_client.get_cost_and_usage.call_args[1]

    assert 'TimePeriod' in call_kwargs
    assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
    assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
    assert call_kwargs['Granularity'] == 'MONTHLY'
    assert 'Metrics' in call_kwargs
    assert 'UnblendedCost' in call_kwargs['Metrics']

    # Verify the result contains the expected data
    assert 'status' in result, 'Result should contain a status field'
    assert result['status'] == 'success', "Status should be 'success'"
    assert 'data' in result, 'Result should contain a data field'
    assert isinstance(result['data'], dict), 'Data should be a dictionary'
    assert 'ResultsByTime' in result['data'], 'Data should contain ResultsByTime'
    assert isinstance(result['data']['ResultsByTime'], list), 'ResultsByTime should be a list'
    assert len(result['data']['ResultsByTime']) == 1, 'ResultsByTime should have exactly one entry'
    assert 'TimePeriod' in result['data']['ResultsByTime'][0], (
        'ResultsByTime entry should contain TimePeriod'
    )
    assert 'Total' in result['data']['ResultsByTime'][0], (
        'ResultsByTime entry should contain Total'
    )
    assert 'UnblendedCost' in result['data']['ResultsByTime'][0]['Total'], (
        'Total should contain UnblendedCost'
    )
    assert result['data']['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'] == '100.0', (
        'Unexpected cost amount'
    )
    assert result['data']['ResultsByTime'][0]['Total']['UnblendedCost']['Unit'] == 'USD', (
        'Unexpected cost unit'
    )


@pytest.mark.asyncio
async def test_cost_explorer_get_dimension_values(mock_context, mock_ce_client):
    """Test the cost_explorer function with getDimensionValues operation."""
    # Patch the create_aws_client function to return our mock client
    with patch(
        'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.create_aws_client',
        return_value=mock_ce_client,
    ):
        # Call the cost_explorer function directly
        result = await cost_explorer(
            mock_context,
            operation='getDimensionValues',
            dimension='SERVICE',
        )

    # Verify the function called the client method with the right parameters
    mock_ce_client.get_dimension_values.assert_called_once()
    call_kwargs = mock_ce_client.get_dimension_values.call_args[1]

    assert 'Dimension' in call_kwargs
    assert call_kwargs['Dimension'] == 'SERVICE'

    # Verify the result contains the expected data
    assert 'status' in result, 'Result should contain a status field'
    assert result['status'] == 'success', "Status should be 'success'"
    assert 'data' in result, 'Result should contain a data field'
    assert isinstance(result['data'], dict), 'Data should be a dictionary'
    assert 'DimensionValues' in result['data'], 'Data should contain DimensionValues'
    assert isinstance(result['data']['DimensionValues'], list), 'DimensionValues should be a list'
    assert len(result['data']['DimensionValues']) == 2, (
        'DimensionValues should have exactly two entries'
    )

    # Verify first dimension value
    assert 'Value' in result['data']['DimensionValues'][0], (
        'First dimension should have a Value field'
    )
    assert result['data']['DimensionValues'][0]['Value'] == 'AWS Lambda', (
        "First dimension value should be 'AWS Lambda'"
    )
    assert 'Attributes' in result['data']['DimensionValues'][0], (
        'First dimension should have an Attributes field'
    )

    # Verify second dimension value
    assert 'Value' in result['data']['DimensionValues'][1], (
        'Second dimension should have a Value field'
    )
    assert result['data']['DimensionValues'][1]['Value'] == 'Amazon S3', (
        "Second dimension value should be 'Amazon S3'"
    )
    assert 'Attributes' in result['data']['DimensionValues'][1], (
        'Second dimension should have an Attributes field'
    )


@pytest.mark.asyncio
async def test_cost_explorer_get_cost_forecast(mock_context, mock_ce_client):
    """Test the cost_explorer function with getCostForecast operation."""
    # Patch the create_aws_client function to return our mock client
    with patch(
        'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.create_aws_client',
        return_value=mock_ce_client,
    ):
        # Call the cost_explorer function
        result = await cost_explorer(
            mock_context,
            operation='getCostForecast',
            metric='UNBLENDED_COST',
            start_date='2023-02-01',
            end_date='2023-02-28',
            granularity='MONTHLY',
        )

    # Verify the function called the client method with the right parameters
    mock_ce_client.get_cost_forecast.assert_called_once()

    call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]

    assert 'TimePeriod' in call_kwargs
    assert call_kwargs['TimePeriod']['Start'] == '2023-02-01'
    assert call_kwargs['TimePeriod']['End'] == '2023-02-28'
    assert call_kwargs['Metric'] == 'UNBLENDED_COST'
    assert call_kwargs['Granularity'] == 'MONTHLY'

    # Verify the result contains the expected data
    assert 'status' in result, 'Result should contain a status field'
    assert result['status'] == 'success', "Status should be 'success'"
    assert 'data' in result, 'Result should contain a data field'
    assert isinstance(result['data'], dict), 'Data should be a dictionary'

    # Verify Total object
    assert 'Total' in result['data'], 'Data should contain Total field'
    assert isinstance(result['data']['Total'], dict), 'Total should be a dictionary'
    assert 'Amount' in result['data']['Total'], 'Total should contain Amount field'
    assert result['data']['Total']['Amount'] == '150.0', 'Total amount should be 150.0'
    assert 'Unit' in result['data']['Total'], 'Total should contain Unit field'
    assert result['data']['Total']['Unit'] == 'USD', 'Total unit should be USD'

    # Verify ForecastResultsByTime
    assert 'ForecastResultsByTime' in result['data'], 'Data should contain ForecastResultsByTime'
    assert isinstance(result['data']['ForecastResultsByTime'], list), (
        'ForecastResultsByTime should be a list'
    )
    assert len(result['data']['ForecastResultsByTime']) >= 1, (
        'ForecastResultsByTime should have at least one entry'
    )

    # Verify first forecast result
    forecast = result['data']['ForecastResultsByTime'][0]
    assert 'TimePeriod' in forecast, 'Forecast should contain TimePeriod'
    assert 'Start' in forecast['TimePeriod'], 'TimePeriod should have Start date'
    assert forecast['TimePeriod']['Start'] == '2023-02-01', 'TimePeriod Start should be 2023-02-01'
    assert 'End' in forecast['TimePeriod'], 'TimePeriod should have End date'
    assert forecast['TimePeriod']['End'] == '2023-02-28', 'TimePeriod End should be 2023-02-28'
    assert 'MeanValue' in forecast, 'Forecast should contain MeanValue'
    assert forecast['MeanValue'] == '150.0', 'MeanValue should be 150.0'


@pytest.mark.asyncio
async def test_cost_explorer_missing_required_parameter(mock_context, mock_ce_client):
    """Test that cost_explorer returns an error when a required parameter is missing."""
    # Patch the create_aws_client function to return our mock client
    with patch(
        'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.create_aws_client',
        return_value=mock_ce_client,
    ):
        # Call the cost_explorer function without the required metric parameter
        result = await cost_explorer(
            mock_context,
            operation='getCostForecast',
            start_date='2023-02-01',
            end_date='2023-02-28',
            granularity='MONTHLY',
        )

    # Verify the result is an error
    assert 'status' in result, 'Result should contain a status field'
    assert result['status'] == 'error', "Status should be 'error' for missing parameters"
    assert 'message' in result, 'Error response should contain a message field'
    assert isinstance(result['message'], str), 'Error message should be a string'
    assert 'metric is required' in result['message'], (
        'Error message should indicate missing metric parameter'
    )
    assert 'data' not in result or not result['data'], (
        'Error response should not contain meaningful data'
    )


@pytest.mark.asyncio
async def test_usage_forecast(mock_context, mock_ce_client):
    """Test the get_usage_forecast function."""
    # Set up mock response for usage forecast
    mock_ce_client.get_usage_forecast.return_value = {
        'Total': {'Amount': '2500.0', 'Unit': 'GB'},
        'ForecastResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-02-01', 'End': '2023-02-28'},
                'MeanValue': '2500.0',
            }
        ],
    }

    # Call the get_usage_forecast function directly
    result = await get_usage_forecast(
        mock_context,
        mock_ce_client,
        metric='STORAGE_FORECAST',
        start_date='2023-02-01',
        end_date='2023-02-28',
        granularity='MONTHLY',
    )

    # Verify the function called the client method with the right parameters
    mock_ce_client.get_usage_forecast.assert_called_once()
    call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]

    assert 'TimePeriod' in call_kwargs
    assert call_kwargs['TimePeriod']['Start'] == '2023-02-01'
    assert call_kwargs['TimePeriod']['End'] == '2023-02-28'
    assert call_kwargs['Metric'] == 'STORAGE_FORECAST'
    assert call_kwargs['Granularity'] == 'MONTHLY'

    # Verify the result contains the expected data
    assert 'status' in result
    assert result['status'] == 'success'
    assert 'data' in result
    assert 'Total' in result['data']
    assert result['data']['Total']['Amount'] == '2500.0'
    assert result['data']['Total']['Unit'] == 'GB'

    # Verify forecast results
    assert 'ForecastResultsByTime' in result['data']
    assert len(result['data']['ForecastResultsByTime']) == 1
    assert result['data']['ForecastResultsByTime'][0]['MeanValue'] == '2500.0'


@pytest.mark.asyncio
async def test_cost_and_usage_with_resources(mock_context, mock_ce_client):
    """Test the get_cost_and_usage_with_resources function."""
    # Mock the datetime.now to return a fixed date for testing
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_explorer_operations.datetime'
    ) as mock_datetime:
        # Set the mocked "now" date
        mock_now = datetime(2023, 1, 10)  # Set to 2023-01-10
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime.side_effect = datetime.strptime  # Keep original behavior

        # Call the get_cost_and_usage_with_resources function directly
        result = await get_cost_and_usage_with_resources(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',  # This is within 14 days of our mocked "now"
            end_date='2023-01-07',
            granularity='DAILY',
            metrics='["UnblendedCost"]',
            group_by='[{"Type": "DIMENSION", "Key": "SERVICE"}]',
        )

    # Verify the function called the client method with the right parameters
    mock_ce_client.get_cost_and_usage_with_resources.assert_called_once()
    call_kwargs = mock_ce_client.get_cost_and_usage_with_resources.call_args[1]

    assert 'TimePeriod' in call_kwargs
    assert 'Granularity' in call_kwargs
    assert call_kwargs['Granularity'] == 'DAILY'

    # Verify the result contains the expected data
    assert 'status' in result
    assert result['status'] == 'success'
    assert 'data' in result


@pytest.mark.asyncio
async def test_get_tags_and_values(mock_context, mock_ce_client):
    """Test the get_tags function."""
    # Mock responses
    mock_ce_client.get_tags.return_value = {'Tags': ['Environment', 'Project']}

    # Test getTags operation
    tags_result = await get_tags(
        mock_context,
        mock_ce_client,
        start_date='2023-01-01',
        end_date='2023-01-31',
    )

    # Test getTagValues operation
    await get_tags(
        mock_context,
        mock_ce_client,
        start_date='2023-01-01',
        end_date='2023-01-31',
        tag_key='Environment',
    )

    # Verify both calls were made to get_tags
    assert mock_ce_client.get_tags.call_count == 2

    # Verify first call (without tag_key)
    first_call_kwargs = mock_ce_client.get_tags.call_args_list[0][1]
    assert 'TimePeriod' in first_call_kwargs
    assert first_call_kwargs['TimePeriod']['Start'] == '2023-01-01'
    assert first_call_kwargs['TimePeriod']['End'] == '2023-01-31'
    assert 'TagKey' not in first_call_kwargs

    # Verify getTags result
    assert tags_result['status'] == 'success'
    assert 'data' in tags_result

    # Verify second call (with tag_key)
    second_call_kwargs = mock_ce_client.get_tags.call_args_list[1][1]
    assert 'TimePeriod' in second_call_kwargs
    assert 'TagKey' in second_call_kwargs
    assert second_call_kwargs['TagKey'] == 'Environment'


@pytest.mark.asyncio
async def test_get_cost_categories(mock_context, mock_ce_client):
    """Test the get_cost_categories function."""
    # AWS GetCostCategories returns CostCategoryNames or CostCategoryValues from
    # the same API depending on whether CostCategoryName is supplied.
    mock_ce_client.get_cost_categories.side_effect = [
        {'CostCategoryNames': ['Department', 'Project']},
        {'CostCategoryValues': ['Engineering', 'Marketing']},
    ]

    # Test getCostCategories operation (list category names)
    categories_result = await get_cost_categories(
        mock_context,
        mock_ce_client,
        start_date='2023-01-01',
        end_date='2023-01-31',
    )

    # Test getCostCategories operation with cost_category_name (list values)
    values_result = await get_cost_categories(
        mock_context,
        mock_ce_client,
        start_date='2023-01-01',
        end_date='2023-01-31',
        cost_category_name='Department',
    )

    # Both calls should hit ce_client.get_cost_categories — there is no
    # separate get_cost_category_values method on the boto3 client.
    assert mock_ce_client.get_cost_categories.call_count == 2

    # Verify first call: no CostCategoryName, returns names
    first_call_kwargs = mock_ce_client.get_cost_categories.call_args_list[0][1]
    assert 'TimePeriod' in first_call_kwargs
    assert first_call_kwargs['TimePeriod']['Start'] == '2023-01-01'
    assert first_call_kwargs['TimePeriod']['End'] == '2023-01-31'
    assert 'CostCategoryName' not in first_call_kwargs

    # Verify first result
    assert categories_result['status'] == 'success'
    assert 'data' in categories_result

    # Verify second call: CostCategoryName set, returns values
    second_call_kwargs = mock_ce_client.get_cost_categories.call_args_list[1][1]
    assert 'TimePeriod' in second_call_kwargs
    assert 'CostCategoryName' in second_call_kwargs
    assert second_call_kwargs['CostCategoryName'] == 'Department'

    # Verify second result
    assert values_result['status'] == 'success'
    assert 'data' in values_result


@pytest.mark.asyncio
async def test_get_savings_plans_utilization(mock_context, mock_ce_client):
    """Test the get_savings_plans_utilization function."""
    # Call the get_savings_plans_utilization function directly
    result = await get_savings_plans_utilization(
        mock_context,
        mock_ce_client,
        start_date='2023-01-01',
        end_date='2023-01-31',
        granularity='MONTHLY',
    )

    # Verify the function called the client method with the right parameters
    mock_ce_client.get_savings_plans_utilization.assert_called_once()
    call_kwargs = mock_ce_client.get_savings_plans_utilization.call_args[1]

    assert 'TimePeriod' in call_kwargs
    assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
    assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
    assert call_kwargs['Granularity'] == 'MONTHLY'

    # Verify the result contains the expected data
    assert 'status' in result
    assert result['status'] == 'success'
    assert 'data' in result
    assert 'SavingsPlansUtilizationsByTime' in result['data']

    # Verify utilization data
    utilization_data = result['data']['SavingsPlansUtilizationsByTime'][0]
    assert 'TimePeriod' in utilization_data
    assert 'Utilization' in utilization_data
    assert 'Utilization' in utilization_data['Utilization']
    assert utilization_data['Utilization']['Utilization'] == '0.85'


@pytest.mark.asyncio
async def test_cost_explorer_unknown_operation(mock_context, mock_ce_client):
    """Test that cost_explorer returns an error for an unknown operation."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.create_aws_client',
        return_value=mock_ce_client,
    ):
        # Call the cost_explorer function with an unknown operation
        result = await cost_explorer(
            mock_context,
            operation='unknownOperation',
        )

    # Verify the result is an error
    assert 'status' in result, 'Result should contain a status field'
    assert result['status'] == 'error', "Status should be 'error' for unknown operation"
    assert 'message' in result, 'Error response should contain a message field'
    assert isinstance(result['message'], str), 'Error message should be a string'
    assert 'Unknown operation' in result['message'], (
        'Error message should indicate unknown operation'
    )
    assert 'unknownOperation' in result['message'], (
        'Error message should mention the specific unknown operation'
    )
    assert 'data' not in result or not result['data'], (
        'Error response should not contain meaningful data'
    )


@pytest.mark.asyncio
async def test_cost_explorer_handle_exception(mock_context, mock_ce_client):
    """Test that cost_explorer handles exceptions properly."""
    # Set up the mock to raise an exception
    mock_ce_client.get_cost_and_usage.side_effect = Exception('Test error')

    # Patch the create_aws_client function to return our mock client
    with patch(
        'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.create_aws_client',
        return_value=mock_ce_client,
    ):
        # Call the cost_explorer function
        result = await cost_explorer(
            mock_context,
            operation='getCostAndUsage',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

    # Verify the function logged the error
    mock_context.error.assert_called()  # Error should be logged via context.error

    # Verify the result is an error
    assert 'status' in result, 'Result should contain a status field'
    assert result['status'] == 'error', "Status should be 'error' for exceptions"
    assert 'message' in result, 'Error response should contain a message field'
    assert isinstance(result['message'], str), 'Error message should be a string'

    error_msg = result['message'].lower()
    assert 'test error' in error_msg, 'Error message should contain the original error message'

    # Additional assertions for error handling
    assert 'data' not in result or not result['data'], (
        'Error response should not contain meaningful data'
    )
    assert 'Test error' in str(mock_context.error.call_args), (
        'Original exception message should be logged'
    )


def test_cost_explorer_server_initialization():
    """Test that the cost_explorer_server is properly initialized."""
    # Verify the server name
    assert cost_explorer_server.name == 'cost-explorer-tools', (
        "Server name should be 'cost-explorer-tools'"
    )

    # Verify the server instructions
    assert isinstance(cost_explorer_server.instructions, str), (
        'Server instructions should be a string'
    )


@pytest.mark.asyncio
async def test_cost_explorer_main_function():
    """Test cost_explorer main function with getCostAndUsage operation."""
    mock_context = AsyncMock()

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.cost_explorer_tools.create_aws_client'
    ) as mock_client:
        mock_client.return_value = MagicMock()

        result = await cost_explorer(
            mock_context,
            operation='getCostAndUsage',
            start_date='2024-01-01',
            end_date='2024-01-31',
        )

        assert result['status'] in ['success', 'error']
    assert len(cost_explorer_server.instructions or '') > 0, (
        'Server instructions should not be empty'
    )
    instructions = cost_explorer_server.instructions
    assert instructions is not None
    assert (
        'Tools for working with AWS Cost Explorer API' in instructions if instructions else False
    ), 'Server instructions should mention AWS Cost Explorer API'

    # Check that the cost_explorer tool was registered correctly
    tool = await cost_explorer_server.get_tool('cost-explorer')
    assert tool is not None, 'The cost_explorer tool should be registered with the server'
    assert tool.name == 'cost-explorer', (
        'The registered cost_explorer tool should have the right name'
    )

    # Check server has expected methods and properties
    assert hasattr(cost_explorer_server, 'run'), "Server should have a 'run' method"
    assert hasattr(cost_explorer_server, 'name'), "Server should have a 'name' property"
    assert hasattr(cost_explorer_server, 'instructions'), (
        "Server should have 'instructions' property"
    )


# Tests for cost_explorer_operations module
class TestCostExplorerOperations:
    """Test cost explorer operations."""

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_calls_client(self):
        """Test get_cost_and_usage calls client."""
        mock_context = MagicMock(spec=Context)
        mock_ce_client = MagicMock()
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [{'TimePeriod': {'Start': '2024-01-01', 'End': '2024-01-02'}}]
        }

        await get_cost_and_usage(mock_context, mock_ce_client)
        mock_ce_client.get_cost_and_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dimension_values_calls_client(self):
        """Test get_dimension_values calls client."""
        mock_context = MagicMock(spec=Context)
        mock_ce_client = MagicMock()
        mock_ce_client.get_dimension_values.return_value = {
            'DimensionValues': [{'Value': 'EC2-Instance'}]
        }

        await get_dimension_values(mock_context, mock_ce_client, 'SERVICE')
        mock_ce_client.get_dimension_values.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cost_forecast_calls_client(self):
        """Test get_cost_forecast calls client."""
        mock_context = MagicMock(spec=Context)
        mock_ce_client = MagicMock()
        mock_ce_client.get_cost_forecast.return_value = {
            'Total': {'Amount': '100.00', 'Unit': 'USD'}
        }

        await get_cost_forecast(mock_context, mock_ce_client, 'UNBLENDED_COST')
        mock_ce_client.get_cost_forecast.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tags_calls_client(self):
        """Test get_tags calls client."""
        mock_context = MagicMock(spec=Context)
        mock_ce_client = MagicMock()
        mock_ce_client.get_tags.return_value = {'Tags': ['Environment']}

        await get_tags(mock_context, mock_ce_client)
        mock_ce_client.get_tags.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cost_categories_calls_client(self):
        """Test get_cost_categories calls client."""
        mock_context = MagicMock(spec=Context)
        mock_ce_client = MagicMock()
        mock_ce_client.get_cost_categories.return_value = {'CostCategoryNames': ['BusinessUnit']}

        await get_cost_categories(mock_context, mock_ce_client)
        mock_ce_client.get_cost_categories.assert_called_once()


@pytest.mark.asyncio
async def test_cost_explorer_missing_dimension():
    """Test getDimensionValues without dimension."""
    ctx = AsyncMock()
    result = await cost_explorer(ctx=ctx, operation='getDimensionValues')
    assert result['status'] == 'error'
    assert 'dimension is required' in result['message']


@pytest.mark.asyncio
@pytest.mark.parametrize('context', [None, 'COST_AND_USAGE', 'RESERVATIONS', 'SAVINGS_PLANS'])
async def test_cost_explorer_get_dimension_values_tag_blocked_in_every_context(
    mock_context, context
):
    """GetDimensionValues(dimension=TAG) is rejected pre-call in every context.

    Cost Explorer accepts TAG as a dimension in none of them (see CE_DIMENSIONS_BY_CONTEXT).
    """
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(ce_mod, 'get_dimension_values', new_callable=AsyncMock) as mock_impl,
    ):
        res = await real_fn(  # type: ignore
            mock_context, operation='getDimensionValues', dimension='TAG', context=context
        )

    assert res['status'] == 'error'
    assert 'getTagsOrValues' in res['data']['message']
    assert 'any context' in res['data']['message']
    assert res['error_type'] == 'validation_error'
    # Explicit, operation-specific hint set at the tool layer (survives middleware enrichment).
    assert 'getTagsOrValues' in res['hint']
    # Middleware derivation: validation_error -> modify_request, and our explicit hint is kept.
    from awslabs.billing_cost_management_mcp_server.utilities.error_contract import (
        add_retry_guidance,
    )

    enriched = add_retry_guidance(res)
    assert enriched['retry_strategy'] == 'modify_request'
    assert enriched['hint'] == res['hint']
    # Guard fires before the AWS GetDimensionValues round-trip (the real handler is never called).
    mock_impl.assert_not_awaited()


@pytest.mark.asyncio
async def test_cost_explorer_missing_metric_forecast():
    """Test getCostForecast without metric."""
    ctx = AsyncMock()
    result = await cost_explorer(ctx=ctx, operation='getCostForecast')
    assert result['status'] == 'error'
    assert 'metric is required' in result['message']


def _reload_ce_with_identity_decorator():
    """Reload cost_explorer_tools with FastMCP.tool patched to return the original function unchanged (identity decorator).

    This exposes a callable 'cost_explorer' we can invoke to cover the routing lines in the module.
    """
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools as ce_mod

    def _identity_tool(self, *args, **kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    with patch.object(fastmcp.FastMCP, 'tool', _identity_tool):
        importlib.reload(ce_mod)
        return ce_mod


@pytest.mark.asyncio
async def test_ce_real_get_cost_and_usage_passes_all_args_reload_identity_decorator(mock_context):
    """Test real cost_explorer get_cost_and_usage passes all args with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_cost_and_usage', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostAndUsage',
            start_date='2024-01-01',
            end_date='2024-01-31',
            granularity='DAILY',
            metrics='["UnblendedCost"]',
            group_by='[{"Type":"DIMENSION","Key":"SERVICE"}]',
            filter='{"Dimensions":{"Key":"SERVICE","Values":["AmazonEC2"]}}',
            next_token='tok',
            max_items=3,
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with('ce')
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            '2024-01-01',
            '2024-01-31',
            'DAILY',
            '["UnblendedCost"]',
            '[{"Type":"DIMENSION","Key":"SERVICE"}]',
            '{"Dimensions":{"Key":"SERVICE","Values":["AmazonEC2"]}}',
            'tok',
            3,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_cost_and_usage_with_resources_passes_args_reload_identity_decorator(
    mock_context,
):
    """Test real cost_explorer get_cost_and_usage_with_resources passes args with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(
            ce_mod, 'get_cost_and_usage_with_resources', new_callable=AsyncMock
        ) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostAndUsageWithResources',
            start_date='2024-01-10',
            end_date='2024-01-20',
            granularity='DAILY',
            metrics='["UnblendedCost"]',
            group_by='[{"Type":"DIMENSION","Key":"SERVICE"}]',
            filter='{"Tags":{"Key":"Environment","Values":["prod"]}}',
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with('ce')
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            '2024-01-10',
            '2024-01-20',
            'DAILY',
            '["UnblendedCost"]',
            '[{"Type":"DIMENSION","Key":"SERVICE"}]',
            '{"Tags":{"Key":"Environment","Values":["prod"]}}',
            None,
            None,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_dimension_values_passes_args_reload_identity_decorator(mock_context):
    """Test real cost_explorer get_dimension_values passes args with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_dimension_values', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {'DimensionValues': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getDimensionValues',
            dimension='SERVICE',
            start_date='2023-03-01',
            end_date='2023-03-31',
            search_string='Amazon',
            filter='{}',
            next_token='abc',
            max_items=2,
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with('ce')
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            'SERVICE',
            '2023-03-01',
            '2023-03-31',
            'Amazon',
            '{}',
            'abc',
            2,
            None,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_dimension_values_missing_dimension_error_reload_identity_decorator(
    mock_context,
):
    """Test real cost_explorer get_dimension_values missing dimension error with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with patch.object(ce_mod, 'create_aws_client') as mock_create_client:
        mock_create_client.return_value = MagicMock()
        res = await real_fn(  # type: ignore
            mock_context,
            operation='getDimensionValues',
            # dimension intentionally omitted
        )
        assert res['status'] == 'error'
        assert (
            'dimension is required' in res.get('message', '')
            or 'dimension is required' in str(res.get('data', {})).lower()
        )
        assert res['error_type'] == 'validation_error'
        assert res['operation'] == 'getDimensionValues'
        assert res['service'] == 'Cost Explorer'


@pytest.mark.asyncio
async def test_ce_real_get_cost_forecast_passes_args_reload_identity_decorator(mock_context):
    """Test real cost_explorer get_cost_forecast passes args with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_cost_forecast', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostForecast',
            metric='UNBLENDED_COST',
            start_date='2023-02-01',
            end_date='2023-02-28',
            granularity='MONTHLY',
            filter='{}',
            prediction_interval_level=95,
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with('ce')
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            'UNBLENDED_COST',
            '2023-02-01',
            '2023-02-28',
            'MONTHLY',
            '{}',
            95,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_cost_forecast_missing_metric_error_reload_identity_decorator(
    mock_context,
):
    """Test real cost_explorer get_cost_forecast missing metric error with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with patch.object(ce_mod, 'create_aws_client') as mock_create_client:
        mock_create_client.return_value = MagicMock()
        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostForecast',
            # metric intentionally omitted
        )
        assert res['status'] == 'error'
        assert (
            'metric is required' in res.get('message', '')
            or 'metric is required' in str(res.get('data', {})).lower()
        )
        assert res['error_type'] == 'validation_error'
        assert res['operation'] == 'getCostForecast'
        assert res['service'] == 'Cost Explorer'


@pytest.mark.asyncio
async def test_ce_real_get_usage_forecast_missing_metric_error_reload_identity_decorator(
    mock_context,
):
    """Test real cost_explorer get_usage_forecast missing metric is classified as validation_error."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with patch.object(ce_mod, 'create_aws_client') as mock_create_client:
        mock_create_client.return_value = MagicMock()
        res = await real_fn(  # type: ignore
            mock_context,
            operation='getUsageForecast',
            # metric intentionally omitted
        )
        assert res['status'] == 'error'
        assert res['data'] == {'message': 'metric is required for getUsageForecast operation'}
        assert res['error_type'] == 'validation_error'
        assert res['operation'] == 'getUsageForecast'
        assert res['service'] == 'Cost Explorer'


@pytest.mark.asyncio
async def test_ce_real_get_usage_forecast_passes_args_reload_identity_decorator(mock_context):
    """Test real cost_explorer get_usage_forecast passes args with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_usage_forecast', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getUsageForecast',
            metric='USAGE_QUANTITY',
            start_date='2023-04-01',
            end_date='2023-04-30',
            granularity='DAILY',
            filter='{"Dimensions":{"Key":"SERVICE","Values":["Amazon S3"]}}',
            prediction_interval_level=80,
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with('ce')
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            'USAGE_QUANTITY',
            '2023-04-01',
            '2023-04-30',
            'DAILY',
            '{"Dimensions":{"Key":"SERVICE","Values":["Amazon S3"]}}',
            80,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_tags_and_values_routing_reload_identity_decorator(mock_context):
    """Test real cost_explorer get_tags and values routing with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_tags', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        # getTagsOrValues
        res1 = await real_fn(  # type: ignore
            mock_context,
            operation='getTagsOrValues',
            start_date='2023-01-01',
            end_date='2023-01-31',
            search_string='Env',
            next_token='n1',
            max_items=2,
        )
        assert res1['status'] == 'success'

        # getTagsOrValues with tag_key
        res2 = await real_fn(  # type: ignore
            mock_context,
            operation='getTagsOrValues',
            start_date='2023-01-01',
            end_date='2023-01-31',
            search_string='Env',
            tag_key='Environment',
            next_token='n2',
            max_items=3,
        )
        assert res2['status'] == 'success'

        # Assert calls
        assert mock_impl.await_count == 2
        mock_impl.assert_any_await(
            mock_context,
            fake_client,
            '2023-01-01',
            '2023-01-31',
            'Env',
            None,
            'n1',
            2,
            None,
        )
        mock_impl.assert_any_await(
            mock_context,
            fake_client,
            '2023-01-01',
            '2023-01-31',
            'Env',
            'Environment',
            'n2',
            3,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_cost_categories_and_values_routing_reload_identity_decorator(
    mock_context,
):
    """Test real cost_explorer get_cost_categories and values routing with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_cost_categories', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        # getCostCategories
        res1 = await real_fn(  # type: ignore
            mock_context,
            operation='getCostCategories',
            start_date='2023-01-01',
            end_date='2023-01-31',
            search_string='Dept',
            next_token='p1',
            max_items=2,
        )
        assert res1['status'] == 'success'

        # getCostCategoryValues is no longer routed — it's not in the tool's
        # public surface and the same behavior is reachable by passing
        # cost_category_name to getCostCategories.
        res2 = await real_fn(  # type: ignore
            mock_context,
            operation='getCostCategories',
            start_date='2023-01-01',
            end_date='2023-01-31',
            search_string='Dept',
            cost_category_name='Department',
            next_token='p2',
            max_items=4,
        )
        assert res2['status'] == 'success'

        assert mock_impl.await_count == 2
        mock_impl.assert_any_await(
            mock_context,
            fake_client,
            '2023-01-01',
            '2023-01-31',
            'Dept',
            None,  # cost_category_name omitted on the first call
            'p1',
            2,
            None,
        )
        mock_impl.assert_any_await(
            mock_context,
            fake_client,
            '2023-01-01',
            '2023-01-31',
            'Dept',
            'Department',
            'p2',
            4,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_savings_plans_utilization_passes_args_reload_identity_decorator(
    mock_context,
):
    """Test real cost_explorer get_savings_plans_utilization passes args with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_savings_plans_utilization', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getSavingsPlansUtilization',
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='MONTHLY',
            filter='{}',
            next_token='tkn',
            max_items=5,
        )

        # The API is not paginated, so next_token and max_items are not passed on.
        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with('ce')
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            '2023-01-01',
            '2023-01-31',
            'MONTHLY',
            '{}',
        )


@pytest.mark.asyncio
async def test_ce_real_get_cost_and_usage_with_billing_view_arn_reload_identity_decorator(
    mock_context,
    sample_billing_view_arn,
):
    """Test cost_explorer getCostAndUsage passes billing_view_arn when provided."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_cost_and_usage', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostAndUsage',
            start_date='2024-01-01',
            end_date='2024-02-01',
            granularity='MONTHLY',
            metrics='["UnblendedCost"]',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            '2024-01-01',
            '2024-02-01',
            'MONTHLY',
            '["UnblendedCost"]',
            None,
            None,
            None,
            None,
            sample_billing_view_arn,
        )


@pytest.mark.asyncio
async def test_ce_real_get_cost_and_usage_with_resources_with_billing_view_arn(
    mock_context, sample_billing_view_arn
):
    """Test cost_explorer getCostAndUsageWithResources passes billing_view_arn."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(
            ce_mod, 'get_cost_and_usage_with_resources', new_callable=AsyncMock
        ) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostAndUsageWithResources',
            start_date='2024-01-10',
            end_date='2024-01-20',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            '2024-01-10',
            '2024-01-20',
            'DAILY',
            None,
            None,
            None,
            None,
            None,
            sample_billing_view_arn,
        )


@pytest.mark.asyncio
async def test_ce_real_get_dimension_values_with_billing_view_arn(
    mock_context, sample_billing_view_arn
):
    """Test cost_explorer getDimensionValues passes billing_view_arn."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_dimension_values', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {'DimensionValues': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getDimensionValues',
            dimension='SERVICE',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            'SERVICE',
            None,
            None,
            None,
            None,
            None,
            None,
            sample_billing_view_arn,
            None,
        )


@pytest.mark.asyncio
async def test_ce_real_get_cost_forecast_with_billing_view_arn(
    mock_context, sample_billing_view_arn
):
    """Test cost_explorer getCostForecast passes billing_view_arn."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_cost_forecast', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostForecast',
            metric='UNBLENDED_COST',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            'UNBLENDED_COST',
            None,
            None,
            'DAILY',
            None,
            80,
            sample_billing_view_arn,
        )


@pytest.mark.asyncio
async def test_ce_real_get_usage_forecast_with_billing_view_arn(
    mock_context, sample_billing_view_arn
):
    """Test cost_explorer getUsageForecast passes billing_view_arn."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_usage_forecast', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getUsageForecast',
            metric='USAGE_QUANTITY',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            'USAGE_QUANTITY',
            None,
            None,
            'DAILY',
            None,
            80,
            sample_billing_view_arn,
        )


@pytest.mark.asyncio
async def test_ce_real_get_tags_with_billing_view_arn(mock_context, sample_billing_view_arn):
    """Test cost_explorer getTagsOrValues passes billing_view_arn."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_tags', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getTagsOrValues',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            None,
            None,
            None,
            None,
            None,
            None,
            sample_billing_view_arn,
        )


@pytest.mark.asyncio
async def test_ce_real_get_cost_categories_with_billing_view_arn(
    mock_context, sample_billing_view_arn
):
    """Test cost_explorer getCostCategories passes billing_view_arn."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_cost_categories', new_callable=AsyncMock) as mock_impl,
    ):
        fake_client = MagicMock()
        mock_create_client.return_value = fake_client
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getCostCategories',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            None,
            None,
            None,
            None,
            None,
            None,
            sample_billing_view_arn,
        )


@pytest.mark.asyncio
async def test_ce_real_unknown_operation_error_reload_identity_decorator(mock_context):
    """Test real cost_explorer unknown operation error with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with patch.object(ce_mod, 'create_aws_client') as mock_create_client:
        mock_create_client.return_value = MagicMock()
        res = await real_fn(mock_context, operation='definitely_not_supported')  # type: ignore
        assert res['status'] == 'error'
        assert 'Unknown operation' in res.get('data', {}).get('message', '')
        assert res['error_type'] == 'validation_error'
        assert res['operation'] == 'definitely_not_supported'
        assert res['service'] == 'Cost Explorer'


@pytest.mark.asyncio
async def test_ce_real_exception_flow_calls_handle_error_reload_identity_decorator(mock_context):
    """Test real cost_explorer exception flow calls handle_error with identity decorator."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_tags', new_callable=AsyncMock) as mock_get_tags,
        patch.object(ce_mod, 'handle_aws_error', new_callable=AsyncMock) as mock_handle,
    ):
        mock_create_client.return_value = MagicMock()
        mock_get_tags.side_effect = RuntimeError('boom')
        mock_handle.return_value = {'status': 'error', 'message': 'boom'}

        res = await real_fn(mock_context, operation='getTagsOrValues')  # type: ignore

        assert res['status'] == 'error'
        assert 'boom' in res.get('message', '')
        mock_handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_ce_real_client_creation_error_is_classified(mock_context):
    """A client-creation failure carries top-level error_type/operation/service."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with patch.object(ce_mod, 'create_aws_client') as mock_create_client:
        mock_create_client.side_effect = Exception('no credentials')
        res = await real_fn(mock_context, operation='getCostAndUsage')  # type: ignore

    assert res['status'] == 'error'
    assert res['error_type'] == 'client_creation_error'
    assert res['operation'] == 'getCostAndUsage'
    assert res['service'] == 'Cost Explorer'
    assert res['message'] == 'Failed to create AWS client: no credentials'
    # Legacy nested payload is preserved
    assert res['data']['error_type'] == 'client_creation_error'


def _reload_ce_with_registered_tools():
    """Reload cost_explorer_tools with the real FastMCP.tool decorator.

    Undoes _reload_ce_with_identity_decorator so the server has its tools registered again.
    """
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools as ce_mod

    return importlib.reload(ce_mod)


STRUCTURED_METRICS = ['UnblendedCost']
STRUCTURED_GROUP_BY = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
STRUCTURED_FILTER = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon S3']}}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'metrics, group_by, filter_value',
    [
        (STRUCTURED_METRICS, STRUCTURED_GROUP_BY, STRUCTURED_FILTER),
        (
            '["UnblendedCost"]',
            '[{"Type": "DIMENSION", "Key": "SERVICE"}]',
            '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon S3"]}}',
        ),
    ],
    ids=['structured', 'json_string'],
)
async def test_mcp_call_accepts_structured_and_json_string_params(metrics, group_by, filter_value):
    """metrics, group_by, and filter reach boto3 as list/dict whether sent structured or as JSON strings (#4553)."""
    ce_mod = _reload_ce_with_registered_tools()
    ce_client = MagicMock()
    ce_client.get_cost_and_usage.return_value = {'ResultsByTime': []}

    with patch.object(ce_mod, 'create_aws_client', return_value=ce_client):
        async with fastmcp.Client(ce_mod.cost_explorer_server) as client:
            result = await client.call_tool(
                'cost-explorer',
                {
                    'operation': 'getCostAndUsage',
                    'start_date': '2026-09-01',
                    'end_date': '2026-09-02',
                    'metrics': metrics,
                    'group_by': group_by,
                    'filter': filter_value,
                },
            )

    assert not result.is_error
    kwargs = ce_client.get_cost_and_usage.call_args.kwargs
    assert kwargs['Metrics'] == STRUCTURED_METRICS
    assert kwargs['GroupBy'] == STRUCTURED_GROUP_BY
    assert kwargs['Filter'] == STRUCTURED_FILTER


@pytest.mark.asyncio
async def test_mcp_call_accepts_structured_filter_for_forecast():
    """A structured filter is accepted by operations that only take filter (#4553)."""
    ce_mod = _reload_ce_with_registered_tools()
    ce_client = MagicMock()
    ce_client.get_cost_forecast.return_value = {'Total': {}, 'ForecastResultsByTime': []}

    with patch.object(ce_mod, 'create_aws_client', return_value=ce_client):
        async with fastmcp.Client(ce_mod.cost_explorer_server) as client:
            result = await client.call_tool(
                'cost-explorer',
                {
                    'operation': 'getCostForecast',
                    'start_date': '2099-01-01',
                    'end_date': '2099-02-01',
                    'granularity': 'MONTHLY',
                    'metric': 'UNBLENDED_COST',
                    'filter': STRUCTURED_FILTER,
                },
            )

    assert not result.is_error
    assert ce_client.get_cost_forecast.call_args.kwargs['Filter'] == STRUCTURED_FILTER


@pytest.mark.asyncio
async def test_tool_schema_publishes_structured_types():
    """The tool schema advertises array/object types for metrics, group_by, and filter (#4553)."""
    ce_mod = _reload_ce_with_registered_tools()
    async with fastmcp.Client(ce_mod.cost_explorer_server) as client:
        tools = await client.list_tools()
    properties = next(t for t in tools if t.name == 'cost-explorer').input_schema['properties']

    def types(name):
        return {option.get('type') for option in properties[name]['anyOf']}

    assert types('metrics') == {'string', 'array', 'null'}
    assert types('group_by') == {'string', 'array', 'null'}
    assert types('filter') == {'string', 'object', 'null'}


def _registered_tool(server, tool_name):
    """Return a registered tool as published to MCP clients."""

    async def _get():
        async with fastmcp.Client(server) as client:
            tools = await client.list_tools()
        return next(t for t in tools if t.name == tool_name)

    return asyncio.run(_get())


def _dimension_reference_keys(description):
    """Return the keys listed in the DIMENSION REFERENCE block."""
    block = description.split('DIMENSION REFERENCE:')[1].split('\n\n')[0]
    return re.findall(r'^- ([A-Z_]+):', block, flags=re.MULTILINE)


def _rendered_examples(description):
    """Return every `{"operation": ...}` example exactly as the model sees it."""
    return re.findall(
        r'Example(?: \d)?(?: \([^)]*\))?: (\{"operation".*\})\s*$', description, re.M
    )


# Dimensions Cost Explorer's GetDimensionValues accepts per context, as listed by the service
# in its ValidationException for an unsupported dimension (captured 2026-10-20). These lists,
# not botocore's Dimension enum, are what a documented key must be in: the enum also has keys
# the service rejects here (LINKED_ACCOUNT_NAME, SERVICE_CODE, ...) and lacks some it accepts
# (RESERVATION_MODIFIED). COST_AND_USAGE holds the dimensions every account gets; the service
# enables a few more per account (PAYER_ACCOUNT, PRODUCT_ATTRIBUTE), so they are left out.
CE_DIMENSIONS_BY_CONTEXT = {
    'COST_AND_USAGE': frozenset(
        {
            'AZ',
            'INSTANCE_TYPE',
            'LINKED_ACCOUNT',
            'OPERATION',
            'PURCHASE_TYPE',
            'SERVICE',
            'USAGE_TYPE',
            'USAGE_TYPE_GROUP',
            'PLATFORM',
            'TENANCY',
            'RECORD_TYPE',
            'LEGAL_ENTITY_NAME',
            'INVOICING_ENTITY',
            'DEPLOYMENT_OPTION',
            'DATABASE_ENGINE',
            'CACHE_ENGINE',
            'INSTANCE_TYPE_FAMILY',
            'REGION',
            'BILLING_ENTITY',
            'RESERVATION_ID',
            'RESOURCE_ID',
            'SAVINGS_PLANS_TYPE',
            'SAVINGS_PLAN_ARN',
            'OPERATING_SYSTEM',
            'RESERVATION_MODIFIED',
        }
    ),
    'RESERVATIONS': frozenset(
        {
            'AZ',
            'INSTANCE_TYPE',
            'LINKED_ACCOUNT',
            'PLATFORM',
            'SCOPE',
            'REGION',
            'TENANCY',
            'SERVICE',
            'INSTANCE_TYPE_FAMILY',
        }
    ),
    'SAVINGS_PLANS': frozenset(
        {
            'SAVINGS_PLANS_TYPE',
            'PAYMENT_OPTION',
            'REGION',
            'INSTANCE_TYPE_FAMILY',
            'LINKED_ACCOUNT',
            'SAVINGS_PLAN_ARN',
        }
    ),
}


class TestCostExplorerDescriptionContract:
    """The cost-explorer description matches Cost Explorer's real dimensions, values and shapes."""

    @pytest.fixture(scope='class')
    def tool(self):
        """The registered cost-explorer tool."""
        ce_mod = _reload_ce_with_registered_tools()
        return _registered_tool(ce_mod.cost_explorer_server, 'cost-explorer')

    @pytest.mark.parametrize(
        'module_name, tool_name, server_attr',
        [
            ('cost_explorer_tools', 'cost-explorer', 'cost_explorer_server'),
            ('ri_performance_tools', 'ri-performance', 'ri_performance_server'),
            ('cost_comparison_tools', 'cost-comparison', 'cost_comparison_server'),
        ],
    )
    def test_tenancy_reference_uses_exact_ce_values(self, module_name, tool_name, server_attr):
        """TENANCY lists the case-sensitive values Cost Explorer matches: Shared, Dedicated, Host."""
        module = importlib.reload(
            importlib.import_module(
                f'awslabs.billing_cost_management_mcp_server.tools.{module_name}'
            )
        )
        description = _registered_tool(getattr(module, server_attr), tool_name).description or ''
        # The TENANCY entry is its line plus any indented continuation lines.
        match = re.search(r'^- TENANCY:.*(?:\n  .*)*', description, re.MULTILINE)
        assert match is not None
        tenancy = match.group(0)
        assert 'case-sensitive' in tenancy
        for value in ('Shared', 'Dedicated', 'Host'):
            assert re.search(rf'\b{value}\b', tenancy)
        for wrong in ('shared', 'dedicated', 'default', 'SHARED', 'DEDICATED', 'HOST'):
            assert not re.search(rf'\b{wrong}\b', tenancy)

    def test_description_prefers_monthly_for_whole_month_rankings(self, tool):
        """Whole-month totals and rankings are steered to MONTHLY; the code default stays DAILY."""
        assert 'DAILY granularity for periods <3 months' not in tool.description
        assert (
            'Use MONTHLY granularity for totals or rankings over whole months' in tool.description
        )
        assert tool.input_schema['properties']['granularity']['default'] == 'DAILY'

    def test_dimension_reference_keys_are_ce_dimensions(self, tool):
        """Every DIMENSION REFERENCE key except the TAG note is in botocore's ce Dimension enum."""
        enum = set(
            botocore.session.get_session().get_service_model('ce').shape_for('Dimension').enum
        )
        keys = _dimension_reference_keys(tool.description)
        assert set(keys) - enum == {'TAG'}
        tag_line = next(ln for ln in tool.description.splitlines() if ln.startswith('- TAG:'))
        assert 'getTagsOrValues' in tag_line

    def test_dimension_reference_names_commonly_needed_keys(self, tool):
        """OPERATION, BILLING_ENTITY, RESOURCE_ID, USAGE_TYPE_GROUP and INVOICING_ENTITY are listed."""
        keys = _dimension_reference_keys(tool.description)
        for key in (
            'OPERATION',
            'BILLING_ENTITY',
            'RESOURCE_ID',
            'USAGE_TYPE_GROUP',
            'INVOICING_ENTITY',
        ):
            assert key in keys
        resource_line = next(
            ln for ln in tool.description.splitlines() if ln.startswith('- RESOURCE_ID:')
        )
        assert 'getCostAndUsageWithResources' in resource_line
        assert '14 days' in resource_line

    def test_every_rendered_example_validates_against_input_schema(self, tool):
        """Each example is valid JSON and satisfies the published input schema."""
        examples = _rendered_examples(tool.description)
        assert len(examples) >= 12
        for example in examples:
            jsonschema.validate(json.loads(example), tool.input_schema)

    def test_rendered_examples_json_encode_structured_params(self, tool):
        """Examples pass metrics, group_by and filter as JSON strings that decode cleanly.

        Copies of this description (and older clients) may type these parameters as plain
        strings, so the examples use the form every variant accepts.
        """
        for example in _rendered_examples(tool.description):
            call = json.loads(example)
            for name in ('metrics', 'group_by', 'filter'):
                if name in call:
                    assert isinstance(call[name], str), (name, example)
                    json.loads(call[name])

    def test_filter_grammar_states_values_rules_and_examples_follow_them(self, tool):
        """Dimensions need Values; ABSENT leaves omit Values; every documented filter complies."""
        grammar = tool.description.split('FILTER EXPRESSION GRAMMAR')[1].split('## OPERATIONS')[0]
        assert 'Dimensions: `Values` is required and must not be empty.' in grammar
        assert 'omit `Values` entirely' in grammar

        documented = [
            json.loads(example)
            for example in re.findall(r'^- `(\{.*\})`$', grammar, flags=re.MULTILINE)
        ]
        documented += [
            json.loads(json.loads(e)['filter'])
            for e in _rendered_examples(tool.description)
            if '"filter"' in e
        ]
        assert any('ABSENT' in json.dumps(f) for f in documented)

        def leaves(expression):
            for key, value in expression.items():
                if key in ('And', 'Or'):
                    for child in value:
                        yield from leaves(child)
                elif key == 'Not':
                    yield from leaves(value)
                else:
                    yield key, value

        for expression in documented:
            for leaf_type, leaf in leaves(expression):
                if 'ABSENT' in leaf.get('MatchOptions', []):
                    assert leaf_type in ('Tags', 'CostCategories')
                    assert 'Values' not in leaf
                else:
                    assert leaf['Values']

    def test_documented_filters_pass_botocore_validation(self, tool):
        """Every filter in an example is a valid Cost Explorer Expression."""
        validator = ParamValidator()
        input_shape = (
            botocore.session.get_session()
            .get_service_model('ce')
            .operation_model('GetCostAndUsage')
            .input_shape
        )
        filters = [
            json.loads(json.loads(e)['filter'])
            for e in _rendered_examples(tool.description)
            if '"filter"' in e
        ]
        assert filters
        for expression in filters:
            report = validator.validate(
                {
                    'TimePeriod': {'Start': '2026-01-01', 'End': '2026-02-01'},
                    'Granularity': 'MONTHLY',
                    'Metrics': ['UnblendedCost'],
                    'Filter': expression,
                },
                input_shape,
            )
            assert not report.has_errors(), report.generate_report()

    def test_no_context_accepts_tag(self):
        """TAG is in none of the service's per-context lists, so the guard is unconditional."""
        for context, dimensions in CE_DIMENSIONS_BY_CONTEXT.items():
            assert 'TAG' not in dimensions, context

    def test_dimension_reference_keys_are_accepted_by_the_service(self, tool):
        """Every DIMENSION REFERENCE key except the TAG note is a COST_AND_USAGE dimension."""
        keys = set(_dimension_reference_keys(tool.description)) - {'TAG'}
        assert keys <= CE_DIMENSIONS_BY_CONTEXT['COST_AND_USAGE']

    @pytest.mark.parametrize('context', ['RESERVATIONS', 'SAVINGS_PLANS'])
    def test_get_dimension_values_notes_list_each_context(self, tool, context):
        """The getDimensionValues notes list exactly the dimensions each context accepts."""
        match = re.search(rf'{context} takes only ([A-Z_, ]+)\.', tool.description)
        assert match is not None, context
        assert set(match.group(1).split(', ')) == CE_DIMENSIONS_BY_CONTEXT[context]

    def test_tag_is_described_as_rejected_in_every_context(self, tool):
        """No line still says TAG is a valid getDimensionValues dimension in some context."""
        assert 'TAG is not a dimension in any context' in tool.description
        assert 'RESERVATIONS coverage context' not in tool.description

    def test_example_dates_are_valid_today(self, tool):
        """Every example date is inside the window Cost Explorer accepts today.

        The dates are rendered relative to today because literal ones go stale: a forecast
        cannot start before today, resource-level data covers the last 14 days, and history
        covers the current month and the previous 13 months.
        """
        today = date.today()
        month_start = today.replace(day=1)
        history_start = date(month_start.year - 1, month_start.month, 1)  # inside 13 months
        years, month = divmod(month_start.month - 1 + 18, 12)
        forecast_horizon = date(month_start.year + years, month + 1, 1)  # MONTHLY: 18 months
        checked = 0
        for example in _rendered_examples(tool.description):
            call = json.loads(example)
            if 'start_date' not in call:
                continue
            start = date.fromisoformat(call['start_date'])
            end = date.fromisoformat(call['end_date'])
            assert start < end, call
            operation = call['operation']
            if operation in ('getCostForecast', 'getUsageForecast'):
                assert start >= today, call
                assert end <= forecast_horizon, call
            elif operation == 'getCostAndUsageWithResources':
                assert start >= today - timedelta(days=14), call
                assert end <= today + timedelta(days=1), call
            else:
                assert start >= history_start, call
                assert end <= today + timedelta(days=1), call
            checked += 1
        assert checked >= 6
        assert not re.search(r'__[A-Z_]+__', tool.description)

    def test_forecasts_show_dated_and_default_windows(self, tool):
        """Forecast examples show both an explicit window and the default one."""
        forecasts = [
            json.loads(e)
            for e in _rendered_examples(tool.description)
            if json.loads(e)['operation'] in ('getCostForecast', 'getUsageForecast')
        ]
        assert any('start_date' in call for call in forecasts)
        assert any('start_date' not in call for call in forecasts)

    def test_forecast_notes_state_the_forecast_filter_limits(self, tool):
        """Forecast filters take only 12-digit LINKED_ACCOUNT IDs and no RESOURCE_ID.

        Cost Explorer rejects both with ValidationException for GetCostForecast and
        GetUsageForecast, though getCostAndUsage accepts RESOURCE_ID.
        """
        notes = tool.description.split('4. getCostForecast')[1].split('5. getUsageForecast')[0]
        assert 'LINKED_ACCOUNT values must be 12-digit account IDs' in notes
        assert 'RESOURCE_ID is not allowed' in notes


def test_description_documents_max_items_paging():
    """The description explains max_items and no longer mentions the removed paging params."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    # Read the module constant: other tests reload the module with an identity decorator,
    # which drops the registered tool's metadata.
    description = cost_explorer_tools.COST_EXPLORER_DESCRIPTION
    assert isinstance(description, str)
    assert 'max_items' in description
    assert 'Omit it to fetch every page' in description
    assert 'complete_dataset: false' in description
    assert 'next_token' in description
    for removed in ('max_pages', 'max_results', 'automatic pagination', 'Pagination is automatic'):
        assert removed not in description
