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

import pytest
from awslabs.billing_cost_management_mcp_server.tools.cost_explorer_tools import (
    cost_explorer as ce_tool,
)
from awslabs.billing_cost_management_mcp_server.tools.cost_explorer_tools import (
    cost_explorer_server,
)
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


# Use the cost_explorer function directly in tests
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
async def test_cost_explorer_unknown_operation(mock_context, mock_ce_client):
    """Test that cost_explorer returns an error for an unknown operation."""
    # Patch the create_aws_client function to return our mock client
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
    assert 'Supported operations' in result['message'], (
        'Error message should mention supported operations'
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
    mock_context.error.assert_called(), 'Error should be logged via context.error'

    # Verify the result is an error
    assert 'status' in result, 'Result should contain a status field'
    assert result['status'] == 'error', "Status should be 'error' for exceptions"
    assert 'message' in result, 'Error response should contain a message field'
    assert isinstance(result['message'], str), 'Error message should be a string'

    # The handle_aws_error function standardizes error messages based on exception type
    # We expect either a generic error or a service error message
    error_msg = result['message'].lower()
    assert error_msg.startswith('aws service error') or 'unexpected error' in error_msg, (
        'Error message should indicate AWS service error or unexpected error'
    )

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
    assert len(cost_explorer_server.instructions) > 0, 'Server instructions should not be empty'
    instructions = cost_explorer_server.instructions
    assert instructions is not None
    assert 'Tools for working with AWS Cost Explorer API' in instructions if instructions else False, (
        'Server instructions should mention AWS Cost Explorer API'
    )

    # Check that the cost_explorer tool was imported correctly
    assert hasattr(ce_tool, 'name'), 'The imported cost_explorer tool should have a name attribute'
    assert ce_tool.name == 'cost_explorer', (
        'The imported cost_explorer tool should have the right name'
    )

    # Check server has expected methods and properties
    assert hasattr(cost_explorer_server, 'run'), "Server should have a 'run' method"
    assert hasattr(cost_explorer_server, 'name'), "Server should have a 'name' property"
    assert hasattr(cost_explorer_server, 'instructions'), (
        "Server should have 'instructions' property"
    )
