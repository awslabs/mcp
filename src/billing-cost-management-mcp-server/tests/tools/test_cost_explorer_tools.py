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
import mcp.types
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


REGION_FILTER = '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}'


@pytest.fixture(scope='module', autouse=True)
def _restore_real_tool_module():
    """Reload the module with the real FastMCP.tool after this file's tests.

    _reload_ce_with_identity_decorator() leaves the module's server with no registered tools;
    restoring it keeps later test files from seeing that state.
    """
    yield
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools as module

    importlib.reload(module)


@pytest.fixture
def real_cost_explorer():
    """Yield cost_explorer_tools with the undecorated cost_explorer tool, restored afterwards."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools as mod

    with patch.object(fastmcp.FastMCP, 'tool', lambda self, *a, **k: lambda fn: fn):
        importlib.reload(mod)
    try:
        yield mod
    finally:
        importlib.reload(mod)


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

    # The API returns DAILY bounds as UTC-midnight timestamps here, unlike get_cost_and_usage.
    mock_client.get_cost_and_usage_with_resources.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01T00:00:00Z', 'End': '2023-01-02T00:00:00Z'},
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
async def test_cost_explorer_get_cost_and_usage(mock_context, mock_ce_client, real_cost_explorer):
    """The getCostAndUsage operation sends the parsed request and returns the API rows with pagination."""
    with patch.object(real_cost_explorer, 'create_aws_client', return_value=mock_ce_client):
        result = await real_cost_explorer.cost_explorer(  # type: ignore[reportCallIssue]
            mock_context,
            operation='getCostAndUsage',
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='MONTHLY',
            metrics='["UnblendedCost"]',
        )

    mock_ce_client.get_cost_and_usage.assert_called_once_with(
        TimePeriod={'Start': '2023-01-01', 'End': '2023-01-31'},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
    )
    assert result['status'] == 'success'
    rows = result['data']['ResultsByTime']
    assert len(rows) == 1
    assert rows[0]['Total']['UnblendedCost'] == {'Amount': '100.0', 'Unit': 'USD'}
    assert result['data']['pagination']['complete_dataset'] is True


@pytest.mark.asyncio
async def test_cost_explorer_get_dimension_values(
    mock_context, mock_ce_client, real_cost_explorer
):
    """The getDimensionValues operation sends the dimension and window and returns the values."""
    with patch.object(real_cost_explorer, 'create_aws_client', return_value=mock_ce_client):
        result = await real_cost_explorer.cost_explorer(  # type: ignore[reportCallIssue]
            mock_context,
            operation='getDimensionValues',
            dimension='SERVICE',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

    mock_ce_client.get_dimension_values.assert_called_once_with(
        TimePeriod={'Start': '2023-01-01', 'End': '2023-01-31'}, Dimension='SERVICE'
    )
    assert result['status'] == 'success'
    assert [v['Value'] for v in result['data']['DimensionValues']] == ['AWS Lambda', 'Amazon S3']


@pytest.mark.asyncio
async def test_cost_explorer_get_dimension_values_forwards_dimension_key(
    mock_context, mock_ce_client, real_cost_explorer
):
    """The tool passes dimension_key through, so a product attribute's values can be listed."""
    with patch.object(real_cost_explorer, 'create_aws_client', return_value=mock_ce_client):
        result = await real_cost_explorer.cost_explorer(  # type: ignore[reportCallIssue]
            mock_context,
            operation='getDimensionValues',
            dimension='PRODUCT_ATTRIBUTE',
            dimension_key='model',
            start_date='2026-10-01',
            end_date='2026-11-01',
        )

    mock_ce_client.get_dimension_values.assert_called_once_with(
        TimePeriod={'Start': '2026-10-01', 'End': '2026-11-01'},
        Dimension='PRODUCT_ATTRIBUTE',
        DimensionKey='model',
    )
    assert result['status'] == 'success'


@pytest.mark.asyncio
async def test_cost_explorer_get_cost_forecast(mock_context, mock_ce_client, real_cost_explorer):
    """The getCostForecast operation sends metric, window, granularity and the default 80% interval."""
    with patch.object(real_cost_explorer, 'create_aws_client', return_value=mock_ce_client):
        result = await real_cost_explorer.cost_explorer(  # type: ignore[reportCallIssue]
            mock_context,
            operation='getCostForecast',
            metric='UNBLENDED_COST',
            start_date='2023-02-01',
            end_date='2023-02-28',
            granularity='MONTHLY',
        )

    mock_ce_client.get_cost_forecast.assert_called_once_with(
        TimePeriod={'Start': '2023-02-01', 'End': '2023-02-28'},
        Metric='UNBLENDED_COST',
        Granularity='MONTHLY',
        PredictionIntervalLevel=80,
    )
    assert result['status'] == 'success'
    assert result['data']['Total'] == {'Amount': '150.0', 'Unit': 'USD'}
    assert result['data']['ForecastResultsByTime'][0]['MeanValue'] == '150.0'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'operation, args, expected',
    [
        ('getCostForecast', {'start_date': '2023-02-01'}, 'metric is required'),
        ('getDimensionValues', {}, 'dimension is required'),
    ],
)
async def test_cost_explorer_missing_required_parameter(
    mock_context, mock_ce_client, real_cost_explorer, operation, args, expected
):
    """A missing required argument is a validation error, and no API call is made."""
    with patch.object(real_cost_explorer, 'create_aws_client', return_value=mock_ce_client):
        result = await real_cost_explorer.cost_explorer(  # type: ignore[reportCallIssue]
            mock_context, operation=operation, **args
        )

    assert result['status'] == 'error'
    assert expected in result['message']
    assert result['error_type'] == 'validation_error'
    mock_ce_client.get_cost_forecast.assert_not_called()
    mock_ce_client.get_dimension_values.assert_not_called()


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
async def test_cost_explorer_unknown_operation(mock_context, mock_ce_client, real_cost_explorer):
    """An unknown operation is a validation error naming the operation."""
    with patch.object(real_cost_explorer, 'create_aws_client', return_value=mock_ce_client):
        result = await real_cost_explorer.cost_explorer(  # type: ignore[reportCallIssue]
            mock_context, operation='unknownOperation'
        )

    assert result['status'] == 'error'
    assert result['message'] == 'Unknown operation: unknownOperation'
    assert result['error_type'] == 'validation_error'


@pytest.mark.asyncio
async def test_cost_explorer_handle_exception(mock_context, mock_ce_client, real_cost_explorer):
    """An API exception comes back as an error response with the exception's text."""
    mock_ce_client.get_cost_and_usage.side_effect = Exception('Test error')

    with patch.object(real_cost_explorer, 'create_aws_client', return_value=mock_ce_client):
        result = await real_cost_explorer.cost_explorer(  # type: ignore[reportCallIssue]
            mock_context,
            operation='getCostAndUsage',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

    assert result['status'] == 'error'
    assert result['operation'] == 'getCostAndUsage'
    assert result['service'] == 'Cost Explorer'
    assert 'Test error' in result['message']
    mock_context.error.assert_called()


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
async def test_cost_explorer_tool_is_registered():
    """The cost-explorer tool is registered on the server under its public name."""
    tool = await cost_explorer_server.get_tool('cost-explorer')
    assert tool is not None, 'The cost_explorer tool should be registered with the server'
    assert tool.name == 'cost-explorer'


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
            filter='{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
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
            '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
            'abc',
            2,
            None,
            None,
            dimension_key=None,
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
            filter='{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
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
            '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
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
            filter=REGION_FILTER,
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
            REGION_FILTER,
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
            filter=REGION_FILTER,
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
            None,
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
            REGION_FILTER,
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
            filter='{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
        )

        assert res['status'] == 'success'
        mock_create_client.assert_called_once_with('ce')
        mock_impl.assert_awaited_once_with(
            mock_context,
            fake_client,
            '2023-01-01',
            '2023-01-31',
            'MONTHLY',
            '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
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
            dimension_key=None,
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


def _dimension_reference_entry(description, key):
    """Return one DIMENSION REFERENCE entry, its wrapped lines joined."""
    block = description.split('DIMENSION REFERENCE:')[1].split('\n\n')[0]
    match = re.search(rf'^- {key}:.*(?:\n  .*)*', block, re.MULTILINE)
    assert match is not None, key
    return ' '.join(match.group(0).split())


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


# DIMENSION REFERENCE keys the service enables per account, so they are in none of the lists
# here. Live (2026-11-02, two accounts with it enabled), PAYER_ACCOUNT worked as a filter key,
# a group_by key and a getDimensionValues dimension; the forecast filter's allowed list names it.
CE_PER_ACCOUNT_KEYS = frozenset({'PAYER_ACCOUNT'})


# Keys Cost Explorer accepts, as listed by the service in its ValidationException for an
# unsupported key (captured 2026-10-30). As above, keys the service enables per account
# (PAYER_ACCOUNT, PRODUCT_ATTRIBUTE, SUBSCRIPTION_ID) are left out.
_CE_SHARED_KEYS = frozenset(
    {
        'AZ',
        'BILLING_ENTITY',
        'CACHE_ENGINE',
        'DATABASE_ENGINE',
        'DEPLOYMENT_OPTION',
        'INSTANCE_TYPE',
        'INSTANCE_TYPE_FAMILY',
        'INVOICING_ENTITY',
        'LEGAL_ENTITY_NAME',
        'LINKED_ACCOUNT',
        'OPERATING_SYSTEM',
        'OPERATION',
        'PLATFORM',
        'PURCHASE_TYPE',
        'RECORD_TYPE',
        'REGION',
        'RESERVATION_ID',
        'SAVINGS_PLAN_ARN',
        'SAVINGS_PLANS_TYPE',
        'SERVICE',
        'TENANCY',
        'USAGE_TYPE',
    }
)
# GetCostAndUsage GroupBy ("Group Definition dimension is invalid. Valid values are ...").
CE_GROUP_BY_DIMENSIONS = _CE_SHARED_KEYS
# GetCostAndUsage Filter ("Dimension SCOPE is not allowed. Allowed dimension(s): ...").
CE_FILTER_DIMENSIONS = _CE_SHARED_KEYS | {'USAGE_TYPE_GROUP'}
# GetCostForecast Filter ("Invalid Filter: Dimension SCOPE is not allowed. Allowed ...").
CE_FORECAST_FILTER_DIMENSIONS = _CE_SHARED_KEYS | {'USAGE_TYPE_GROUP'}


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

    def test_record_type_reference_uses_exact_ce_values(self, tool):
        """RECORD_TYPE lists the values Cost Explorer matches, not CUR codes or prose."""
        match = re.search(r'^- RECORD_TYPE:.*(?:\n  .*)*', tool.description, re.MULTILINE)
        assert match is not None
        # Re-join wrapped lines so multi-word values split across a line break still match.
        record_type = ' '.join(match.group(0).split())
        assert 'case-sensitive' in record_type
        for value in (
            'Usage',
            'DiscountedUsage',
            'SavingsPlanCoveredUsage',
            'SavingsPlanNegation',
            'SavingsPlanRecurringFee',
            'SavingsPlanUpfrontFee',
            'Recurring',
            'Upfront',
            'Support',
            'Other',
            'Tax',
            'Credit',
            'Refund',
            'Bundled Discount',
            'Enterprise Discount Program Discount',
            'Private Rate Card Discount',
            'RI Volume Discount',
            'Solution Provider Program Discount',
            'Distributor Discount',
            'Marketplace Discount',
        ):
            assert re.search(rf'\b{value}\b', record_type), value
        # The old prose guesses are gone, and the CUR codes are named only as non-values.
        assert 'e.g., RI fees, usage costs' not in record_type
        assert 'reports RIFee as Recurring, so a RIFee filter matches nothing' in record_type
        assert 'most CUR Fee rows as Upfront, Other or Support' in record_type
        assert 'use Upfront for RI upfront fees, Other for other subscription fees' in record_type
        assert 'RIFee and Fee match nothing' not in record_type
        # The list is not exhaustive: any unmapped CUR line-item type passes through unchanged.
        assert 'Exact' not in record_type
        assert 'Any other CUR line-item type' in record_type
        assert 'passes through unchanged' in record_type
        assert 'getDimensionValues with RECORD_TYPE' in record_type

    @pytest.mark.parametrize(
        'module_name, tool_name, server_attr, key, values, wrong',
        [
            (
                'cost_explorer_tools',
                'cost-explorer',
                'cost_explorer_server',
                'DATABASE_ENGINE',
                ('Aurora MySQL', 'Aurora PostgreSQL', 'MySQL', 'PostgreSQL'),
                ('Aurora',),
            ),
            (
                'cost_explorer_tools',
                'cost-explorer',
                'cost_explorer_server',
                'DEPLOYMENT_OPTION',
                ('Single-AZ', 'Multi-AZ'),
                ('SingleAZ', 'MultiAZ'),
            ),
            (
                'cost_explorer_tools',
                'cost-explorer',
                'cost_explorer_server',
                'INSTANCE_TYPE_FAMILY',
                ('m5', 't3', 'c6g', 'r5', 'R5'),
                ('Compute Optimized', 'Memory Optimized'),
            ),
            (
                'cost_explorer_tools',
                'cost-explorer',
                'cost_explorer_server',
                'OPERATING_SYSTEM',
                ('Linux/UNIX', 'Windows (Amazon VPC)'),
                ('Windows', 'Linux'),
            ),
            (
                'cost_explorer_tools',
                'cost-explorer',
                'cost_explorer_server',
                'PLATFORM',
                ('Linux/UNIX', 'Windows (Amazon VPC)'),
                ('Windows', 'Linux'),
            ),
            (
                'cost_explorer_tools',
                'cost-explorer',
                'cost_explorer_server',
                'PURCHASE_TYPE',
                ('On Demand Instances', 'Standard Reserved Instances', 'Savings Plans'),
                ('On-Demand',),
            ),
            (
                'cost_comparison_tools',
                'cost-comparison',
                'cost_comparison_server',
                'PLATFORM',
                ('Linux/UNIX', 'Windows (Amazon VPC)'),
                ('Windows', 'Linux'),
            ),
        ],
    )
    def test_dimension_examples_use_exact_ce_values(
        self, module_name, tool_name, server_attr, key, values, wrong
    ):
        """Dimension examples are values Cost Explorer returns, not console or pricing labels."""
        module = importlib.reload(
            importlib.import_module(
                f'awslabs.billing_cost_management_mcp_server.tools.{module_name}'
            )
        )
        description = _registered_tool(getattr(module, server_attr), tool_name).description or ''
        match = re.search(rf'^- {key}:.*(?:\n  .*)*', description, re.MULTILINE)
        assert match is not None
        entry = ' '.join(match.group(0).split())
        for value in values:
            assert re.search(rf'(?<![\w-]){re.escape(value)}(?![\w-])', entry), value
        for value in wrong:
            # A wrong value only counts as a whole list item, so 'Aurora MySQL' is not 'Aurora'.
            assert not re.search(rf'[ (]{re.escape(value)}(?=[,);.]|$)', entry), value

    @pytest.mark.parametrize(
        'module_name, tool_name, server_attr',
        [
            ('cost_explorer_tools', 'cost-explorer', 'cost_explorer_server'),
            ('cost_comparison_tools', 'cost-comparison', 'cost_comparison_server'),
        ],
    )
    def test_empty_value_placeholder_is_filtered_as_empty_string(
        self, module_name, tool_name, server_attr
    ):
        """Grouped results label an empty value NoRegion etc.; a filter must use "" instead.

        Cost Explorer reports a cost with no value for a grouped dimension under a
        placeholder key (NoRegion, NoTenancy, ...), but its filters match the stored empty
        value, so a filter on the placeholder silently returns $0.
        """
        module = importlib.reload(
            importlib.import_module(
                f'awslabs.billing_cost_management_mcp_server.tools.{module_name}'
            )
        )
        description = _registered_tool(getattr(module, server_attr), tool_name).description or ''
        flat = ' '.join(description.split())
        assert 'NoRegion' in flat
        assert 'NoTenancy' in flat
        assert 'a filter on it matches nothing' in flat
        examples = [json.loads(m) for m in re.findall(r'`(\{"Dimensions": [^`]*\})`', description)]
        assert {'Dimensions': {'Key': 'REGION', 'Values': ['']}} in examples

    def test_filter_grammar_allows_one_empty_string_value(self, tool):
        """The grammar's "Values must not be empty" rule does not forbid the [""] filter."""
        grammar = tool.description.split('Values per leaf type:')[1].split('\n- Tags')[0]
        assert '`[""]` (one empty string) is not' in grammar

    def test_description_prefers_monthly_for_whole_month_rankings(self, tool):
        """Whole-month totals and rankings are steered to MONTHLY; the code default stays DAILY."""
        assert 'DAILY granularity for periods <3 months' not in tool.description
        assert (
            'Use MONTHLY granularity for totals or rankings over whole months' in tool.description
        )
        assert (
            'If granularity is omitted, every operation that takes it uses DAILY'
            in tool.description
        )
        assert tool.input_schema['properties']['granularity']['default'] == 'DAILY'

    def test_description_says_an_empty_filter_is_rejected(self, tool):
        """The filter grammar says to use double quotes and to omit filter for no filter."""
        assert 'with double quotes; omit it for no filter, as an empty one is rejected' in (
            tool.description
        )

    def test_forecast_notes_say_monthly_periods_are_whole_months(self, tool):
        """MONTHLY forecasts widen to whole months, so a partial month is steered to DAILY."""
        cost = tool.description.split('4. getCostForecast')[1].split('5. getUsageForecast')[0]
        usage = tool.description.split('5. getUsageForecast')[1].split('\n\n')[0]
        assert 'each period is a whole calendar month' in cost
        assert 'include its actual costs to date' in cost
        assert '`period_note`' in cost
        assert 'For part of a month, such as the rest of this month, use DAILY' in cost
        assert 'MONTHLY periods are whole calendar months' in usage

    def test_description_flags_partial_monthly_sp_utilization(self, tool):
        """The getSavingsPlansUtilization notes flag partial MONTHLY entries and period_note."""
        notes = tool.description.split('8. getSavingsPlansUtilization')[1].split('Returns:')[0]
        assert "each entry's TimePeriod is its whole calendar month" in notes
        assert "the current month's entry ends at the first day without data" in notes
        assert 'cover only the requested days' in notes
        assert '`period_note`' in notes

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
        """Each DIMENSION REFERENCE key is a COST_AND_USAGE dimension or names its own context.

        TAG is the note that TAG is no dimension; SCOPE is listed to say it is a RESERVATIONS
        dimension only, so an agent does not filter getCostAndUsage or a forecast on it.
        PRODUCT_ATTRIBUTE is enabled per account, so it is left out of CE_DIMENSIONS_BY_CONTEXT.
        """
        keys = (
            set(_dimension_reference_keys(tool.description))
            - {'TAG', 'PRODUCT_ATTRIBUTE'}
            - CE_PER_ACCOUNT_KEYS
        )
        context_only = {}
        for key in keys:
            entry = re.search(rf'^- {key}:.*(?:\n  .*)*', tool.description, re.MULTILINE)
            assert entry is not None, key
            match = re.search(
                r'Only a getDimensionValues dimension in the ([A-Z_]+)\s+context',
                entry.group(0),
            )
            if match:
                context_only[key] = match.group(1)
        assert context_only == {'SCOPE': 'RESERVATIONS'}
        assert 'SCOPE' not in CE_DIMENSIONS_BY_CONTEXT['COST_AND_USAGE']
        assert 'SCOPE' in CE_DIMENSIONS_BY_CONTEXT['RESERVATIONS']
        assert keys - set(context_only) <= CE_DIMENSIONS_BY_CONTEXT['COST_AND_USAGE']

    def test_dimension_reference_preamble_holds_for_every_unqualified_key(self, tool):
        """Keys with no "where accepted" note are filter, group_by and forecast filter keys.

        The preamble says so; the five keys accepted in fewer places say where instead.
        """
        keys = set(_dimension_reference_keys(tool.description)) - CE_PER_ACCOUNT_KEYS
        qualified = {'PRODUCT_ATTRIBUTE', 'RESOURCE_ID', 'SCOPE', 'TAG', 'USAGE_TYPE_GROUP'}
        for key in keys - qualified:
            assert key in CE_GROUP_BY_DIMENSIONS, key
            assert key in CE_FILTER_DIMENSIONS, key
            assert key in CE_FORECAST_FILTER_DIMENSIONS, key
            assert key in CE_DIMENSIONS_BY_CONTEXT['COST_AND_USAGE'], key
        assert 'USAGE_TYPE_GROUP' in CE_FILTER_DIMENSIONS - CE_GROUP_BY_DIMENSIONS
        assert 'USAGE_TYPE_GROUP' in CE_FORECAST_FILTER_DIMENSIONS
        for key in ('RESOURCE_ID', 'SCOPE'):
            assert key not in CE_FILTER_DIMENSIONS | CE_GROUP_BY_DIMENSIONS, key
            assert key not in CE_FORECAST_FILTER_DIMENSIONS, key

    def test_per_account_keys_say_they_may_be_unavailable(self, tool):
        """A per-account key is documented with its fallback, so a rejection is expected."""
        assert CE_PER_ACCOUNT_KEYS <= set(_dimension_reference_keys(tool.description))
        for key in CE_PER_ACCOUNT_KEYS:
            assert key not in CE_DIMENSIONS_BY_CONTEXT['COST_AND_USAGE'], key
            entry = re.search(rf'^- {key}:.*(?:\n  .*)*', tool.description, re.MULTILINE)
            assert entry is not None, key
            text = ' '.join(entry.group(0).split())
            assert 'Not available in every account' in text, key
            assert 'use LINKED_ACCOUNT' in text, key

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

    def test_filter_grammar_states_operand_minimum_and_limits_by_operation(self, tool):
        """And/Or need 2 operands; depth and operator limits differ by operation."""
        grammar = tool.description.split('FILTER EXPRESSION GRAMMAR')[1].split('## OPERATIONS')[0]
        flat = ' '.join(grammar.split())
        assert '`And` and `Or` (each takes an array of at least 2 expressions)' in flat
        limits = flat.split('Limits by operation')[1]
        assert (
            'getCostAndUsage, getCostAndUsageWithResources: `And`, `Or` and `Not` nest up to 4 '
            'levels deep; a 5th is rejected.' in limits
        )
        assert (
            'getDimensionValues (default COST_AND_USAGE context), getTagsOrValues and '
            'getCostCategories: `And` of leaves only (an `And` inside it is rejected); `Or` and '
            '`Not` are rejected.' in limits
        )
        assert 'getSavingsPlansUtilization: `And` and `Not` only; `Or` is rejected.' in limits

    def test_linked_account_rule_applies_to_every_operation(self, tool):
        """LINKED_ACCOUNT takes IDs everywhere, and names map to IDs via getDimensionValues."""
        flat = _dimension_reference_entry(tool.description, 'LINKED_ACCOUNT')
        assert 'AWS member accounts, as 12-digit account IDs in every operation' in flat
        assert (
            'With the default match, any other value, such as an account name, is rejected with '
            'ValidationException' in flat
        )
        assert 'a forecast with CONTAINS, STARTS_WITH or ENDS_WITH is not checked' in flat
        assert 'LINKED_ACCOUNT_NAME is not a filter key' in flat
        assert 'call getDimensionValues with dimension LINKED_ACCOUNT' in flat
        assert 'its attributes carry the account name (`description`)' in flat
        assert 'LINKED_ACCOUNT_NAME' not in _dimension_reference_keys(tool.description)

    def test_dimension_reference_lists_commitment_and_cache_keys_and_marks_scope(self, tool):
        """Missing keys are listed, and each key accepted in only some places says where."""
        keys = _dimension_reference_keys(tool.description)
        for key in (
            'CACHE_ENGINE',
            'RESERVATION_ID',
            'SAVINGS_PLAN_ARN',
            'SAVINGS_PLANS_TYPE',
            'SCOPE',
        ):
            assert key in keys, key
        assert keys.count('SCOPE') == 1

        def entry(key):
            return _dimension_reference_entry(tool.description, key)

        assert 'Filter only: not a group_by key' in entry('USAGE_TYPE_GROUP')
        assert 'not a filter or group_by key in the other operations' in entry('SCOPE')
        assert 'the forecast API reference lists it as a filter key' in entry('SCOPE')
        assert 'getDimensionValues dimension and filter key; not usable in getCostAndUsage' in (
            entry('RESOURCE_ID')
        )
        gdv_notes = tool.description.split('3. getDimensionValues')[1].split('4. getCostForecast')[
            0
        ]
        assert 'DIMENSION REFERENCE keys below except SCOPE and TAG' in gdv_notes
        reference = ' '.join(tool.description.split('DIMENSION REFERENCE:')[1].split())
        assert reference.startswith(
            'Unless an entry says otherwise, a key works as a filter key and a group_by key in '
            'getCostAndUsage and getCostAndUsageWithResources, as a filter key in the '
            'forecasts, and as a getDimensionValues dimension.'
        )

    def test_resource_level_notes_cover_every_opted_in_service(self, tool):
        """Resource-level data is not EC2-only and needs no SERVICE filter."""
        block = tool.description.split('2. getCostAndUsageWithResources')[1].split(
            '3. getDimensionValues'
        )[0]
        flat = ' '.join(block.split())
        assert 'works for every service the account has opted in to resource-level data' in flat
        assert 'a SERVICE filter is not required' in flat
        assert 'though the API reference says SERVICE = Amazon Elastic Compute Cloud' in flat
        assert 'RESOURCE_ID must be included in either filter OR group_by' in flat
        examples = [json.loads(e) for e in _rendered_examples(block)]
        assert examples
        services = {
            value
            for call in examples
            for value in json.loads(call['filter']).get('Dimensions', {}).get('Values', [])
        }
        assert services, 'the example has no top-level Dimensions filter to read'
        assert 'Amazon Elastic Compute Cloud - Compute' not in services


def test_description_documents_max_items_paging():
    """The description explains max_items and no longer mentions the removed paging params."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    # Read the module constant: other tests reload the module with an identity decorator,
    # which drops the registered tool's metadata.
    description = cost_explorer_tools.COST_EXPLORER_DESCRIPTION
    assert isinstance(description, str)
    assert 'max_items' in description
    assert 'Omit it to fetch every page' not in description
    assert 'fetches every page for up to 300 seconds' in description
    assert 'complete_dataset: false' in description
    assert 'next_token' in description
    for removed in ('max_pages', 'max_results', 'automatic pagination', 'Pagination is automatic'):
        assert removed not in description


@pytest.mark.asyncio
async def test_description_states_savings_plans_data_lag():
    """The getSavingsPlansUtilization notes state the 2-3 day lag and the unmatched-filter case."""
    tool = await cost_explorer_server.get_tool('cost-explorer')
    assert tool is not None and tool.description
    assert 'Data lags ~1 day' not in tool.description
    assert 'set end_date to yesterday' not in tool.description
    assert 'end_date must be before the current date' not in tool.description
    assert 'report none/zero' not in tool.description
    assert 'Data for the most recent 2-3 days (counting today) is not processed yet' in (
        tool.description
    )
    assert 'an unknown SAVINGS_PLANS_TYPE matches nothing' in tool.description
    assert 'report that no data is available for that window (not zero)' in tool.description


@pytest.mark.asyncio
async def test_ce_get_savings_plans_utilization_rejects_billing_view_arn(
    mock_context, sample_billing_view_arn
):
    """GetSavingsPlansUtilization has no BillingViewArn, so the tool refuses the ARN.

    Dropping it would return utilization for the primary view labelled as the caller's view.
    """
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_savings_plans_utilization', new_callable=AsyncMock) as mock_impl,
    ):
        mock_create_client.return_value = MagicMock()

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getSavingsPlansUtilization',
            start_date='2024-01-01',
            end_date='2024-02-01',
            granularity='MONTHLY',
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'error'
        assert res['error_type'] == 'validation_error'
        assert 'billing_view_arn' in res['message']
        assert 'getSavingsPlansUtilization' in res['message']
        assert 'not scoped to the requested view' in res['message']
        assert 'Do **NOT** retry' in res['hint']
        mock_impl.assert_not_awaited()


@pytest.mark.asyncio
async def test_ce_get_savings_plans_utilization_empty_billing_view_arn_is_absent(mock_context):
    """An empty billing_view_arn means no view, as for the operations that send it."""
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_savings_plans_utilization', new_callable=AsyncMock) as mock_impl,
    ):
        mock_create_client.return_value = MagicMock()
        mock_impl.return_value = {'status': 'success', 'data': {}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getSavingsPlansUtilization',
            start_date='2024-01-01',
            end_date='2024-02-01',
            billing_view_arn='',
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once()


@pytest.mark.asyncio
async def test_description_names_billing_view_operations():
    """The description names which operations take billing_view_arn and which refuse it."""
    tool = await cost_explorer_server.get_tool('cost-explorer')
    assert tool is not None and tool.description
    description = ' '.join(tool.description.split())
    assert 'Most Cost Explorer operations support an optional billing_view_arn' not in description
    assert (
        'billing_view_arn is accepted by getCostAndUsage, getCostAndUsageWithResources, '
        'getDimensionValues (COST_AND_USAGE context only), getCostForecast, getUsageForecast, '
        'getTagsOrValues and getCostCategories'
    ) in description
    assert (
        'getSavingsPlansUtilization (the AWS API has no billing view parameter) and '
        'getDimensionValues with context RESERVATIONS or SAVINGS_PLANS (AWS does not apply the '
        'view there) do not accept billing_view_arn'
    ) in description


@pytest.mark.asyncio
@pytest.mark.parametrize('context', ['RESERVATIONS', 'SAVINGS_PLANS'])
async def test_ce_get_dimension_values_rejects_billing_view_arn_outside_cost_and_usage(
    mock_context, sample_billing_view_arn, context
):
    """AWS does not apply a billing view to RESERVATIONS or SAVINGS_PLANS dimension values.

    Sending the ARN would return unscoped values labelled as the caller's view.
    """
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_dimension_values', new_callable=AsyncMock) as mock_impl,
    ):
        mock_create_client.return_value = MagicMock()

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getDimensionValues',
            dimension='LINKED_ACCOUNT',
            context=context,
            billing_view_arn=sample_billing_view_arn,
        )

        assert res['status'] == 'error'
        assert res['error_type'] == 'validation_error'
        assert 'billing_view_arn' in res['message']
        assert f'context={context}' in res['message']
        assert 'Do **NOT** retry with the same billing_view_arn' in res['hint']
        assert context not in res['hint']  # the hint is fixed text; the context is in message
        mock_impl.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'context, billing_view_arn',
    [
        ('COST_AND_USAGE', 'arn:aws:billing::123456789012:billingview/custom-abc'),
        ('SAVINGS_PLANS', None),
        ('RESERVATIONS', ''),
        ('savings_plans', 'arn:aws:billing::123456789012:billingview/custom-abc'),
    ],
)
async def test_ce_get_dimension_values_billing_view_arn_allowed_cases(
    mock_context, context, billing_view_arn
):
    """COST_AND_USAGE still sends the ARN; the other contexts run when no ARN is set.

    A lowercase context goes to AWS unchanged, which rejects the context itself.
    """
    ce_mod = _reload_ce_with_identity_decorator()
    real_fn = ce_mod.cost_explorer  # type: ignore

    with (
        patch.object(ce_mod, 'create_aws_client') as mock_create_client,
        patch.object(ce_mod, 'get_dimension_values', new_callable=AsyncMock) as mock_impl,
    ):
        mock_create_client.return_value = MagicMock()
        mock_impl.return_value = {'status': 'success', 'data': {'DimensionValues': []}}

        res = await real_fn(  # type: ignore
            mock_context,
            operation='getDimensionValues',
            dimension='LINKED_ACCOUNT',
            context=context,
            billing_view_arn=billing_view_arn,
        )

        assert res['status'] == 'success'
        mock_impl.assert_awaited_once()
        await_args = mock_impl.await_args
        assert await_args is not None
        assert await_args.args[-2:] == (billing_view_arn, context)


@pytest.mark.asyncio
async def test_description_says_a_forecast_filter_can_match_nothing():
    """The forecast notes say an unmatched filter returns the same 'too little history' error."""
    tool = await cost_explorer_server.get_tool('cost-explorer')
    assert tool is not None and tool.description
    description = tool.description
    assert 'A filter that matches no past costs returns the same' in description
    assert 'CASE_INSENSITIVE are accepted but not applied' in description
    assert 'match exactly, including case' in description
    assert (
        'STARTS_WITH' in description.split('4. getCostForecast')[1].split('5. getUsageForecast')[0]
    )
    assert 'Filter values match as for getCostForecast' in description


# Operations whose AWS API has no GroupBy, with the arguments each needs to reach its handler.
NO_GROUP_BY_OPERATIONS = {
    'getCostForecast': ('get_cost_forecast', {'metric': 'UNBLENDED_COST'}),
    'getUsageForecast': (
        'get_usage_forecast',
        {
            'metric': 'USAGE_QUANTITY',
            'filter': '{"Dimensions": {"Key": "USAGE_TYPE", "Values": ["BoxUsage:t3.micro"]}}',
        },
    ),
    'getSavingsPlansUtilization': ('get_savings_plans_utilization', {}),
    'getDimensionValues': ('get_dimension_values', {'dimension': 'SERVICE'}),
    'getTagsOrValues': ('get_tags', {}),
    'getCostCategories': ('get_cost_categories', {}),
}
REGION_GROUP_BY = '[{"Type": "DIMENSION", "Key": "REGION"}]'


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', sorted(NO_GROUP_BY_OPERATIONS))
@pytest.mark.parametrize(
    'group_by',
    [REGION_GROUP_BY, [{'Type': 'DIMENSION', 'Key': 'REGION'}], 'SERVICE', ' '],
    ids=['json', 'list', 'not-json', 'blank'],
)
async def test_group_by_is_rejected_where_the_api_has_no_group_by(
    mock_context, real_cost_explorer, operation, group_by
):
    """group_by on an operation without GroupBy is a validation_error, not a silent total.

    Forwarding the call would drop group_by and return one ungrouped total that reads as if
    it were split by the requested dimension.
    """
    handler, args = NO_GROUP_BY_OPERATIONS[operation]
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, group_by=group_by, **args
        )

    mock_impl.assert_not_awaited()
    assert res['status'] == 'error'
    assert res['error_type'] == 'validation_error'
    assert res['operation'] == operation
    assert res['service'] == 'Cost Explorer'
    message = res['data']['message']
    assert f'group_by is not supported for {operation}' in message
    assert 'getCostAndUsage and getCostAndUsageWithResources' in message
    assert 'one forecast or utilization call per value' in message
    assert 'Do **NOT** retry' in res['hint']


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', sorted(NO_GROUP_BY_OPERATIONS))
@pytest.mark.parametrize('group_by', ['[]', ' [] ', 'null'], ids=repr)
async def test_empty_group_by_json_is_no_grouping(
    mock_context, real_cost_explorer, operation, group_by
):
    """group_by '[]' is no grouping, as getCostAndUsage reads it, so the call goes through."""
    handler, args = NO_GROUP_BY_OPERATIONS[operation]
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, group_by=group_by, **args
        )

    assert res['status'] == 'success'
    mock_impl.assert_awaited_once()


@pytest.mark.asyncio
async def test_description_lists_filter_for_tags_and_cost_categories():
    """The tags and cost category operations list filter as optional."""
    tool = await cost_explorer_server.get_tool('cost-explorer')
    assert tool is not None and tool.description
    description = ' '.join(tool.description.split())
    assert 'Optional: start_date, end_date, tag_key, search_string, filter,' in description
    assert (
        'Optional: start_date, end_date, cost_category_name, search_string, filter,' in description
    )


@pytest.mark.asyncio
@pytest.mark.parametrize('group_by', [None, '', []], ids=['none', 'empty_string', 'empty_list'])
async def test_forecast_without_group_by_still_reaches_the_api(
    mock_context, real_cost_explorer, group_by
):
    """An unset or empty group_by does not trip the check: the forecast is sent as before."""
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, 'get_cost_forecast', new_callable=AsyncMock) as impl,
    ):
        impl.return_value = {'status': 'success', 'data': {}}
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation='getCostForecast', metric='UNBLENDED_COST', group_by=group_by
        )

    assert res == {'status': 'success', 'data': {}}
    impl.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'operation, handler',
    [
        ('getCostAndUsage', 'get_cost_and_usage'),
        ('getCostAndUsageWithResources', 'get_cost_and_usage_with_resources'),
    ],
)
async def test_group_by_still_reaches_the_operations_that_take_it(
    mock_context, real_cost_explorer, operation, handler
):
    """The two operations that take group_by, getCostAndUsage and its resource variant, get it."""
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock) as impl,
    ):
        impl.return_value = {'status': 'success', 'data': {}}
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, group_by=REGION_GROUP_BY
        )

    assert res['status'] == 'success'
    assert impl.await_args is not None
    assert REGION_GROUP_BY in impl.await_args.args


def test_examples_pass_group_by_only_where_it_is_used():
    """No example passes group_by to an operation that rejects it (getUsageForecast Example 3)."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    description = cost_explorer_tools.COST_EXPLORER_DESCRIPTION
    examples = [json.loads(e) for e in _rendered_examples(description)]
    assert any('group_by' in call for call in examples)
    for call in examples:
        if 'group_by' in call:
            assert 'group_by' in cost_explorer_tools.OPERATION_ARGUMENTS[call['operation']], call
    flat = ' '.join(description.split())
    assert (
        'group_by works only with getCostAndUsage and getCostAndUsageWithResources; the other '
        'operations reject it' in flat
    )


def test_every_documented_operation_is_classified_for_group_by():
    """Only getCostAndUsage and getCostAndUsageWithResources accept group_by.

    A new operation added to the table with group_by would silently drop it again.
    """
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    operations_block = cost_explorer_tools.COST_EXPLORER_DESCRIPTION.split('## OPERATIONS')[1]
    documented = set(re.findall(r'^\d+[.)] (\w+)', operations_block, flags=re.MULTILINE))
    assert len(documented) == 8
    assert documented == set(cost_explorer_tools.OPERATION_ARGUMENTS)
    takes_group_by = {
        op for op, args in cost_explorer_tools.OPERATION_ARGUMENTS.items() if 'group_by' in args
    }
    assert takes_group_by == {'getCostAndUsage', 'getCostAndUsageWithResources'}


def test_description_documents_tags_leaf_format():
    """The Tags-leaf rules are stated: a wrong key is silent ($0, or every cost with ABSENT).

    Cost Explorer adds `user:` to user-defined tag keys itself, so a `user:` key matches
    nothing, and a TAG group_by label (`key$value`) is not a value.
    """
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    description = cost_explorer_tools.COST_EXPLORER_DESCRIPTION
    tags = ' '.join(
        description.split(
            'Tags leaves in getCostAndUsage, getCostAndUsageWithResources, getDimensionValues,\n'
            'getTagsOrValues and getCostCategories filters:'
        )[1]
        .split('Correct filter examples:')[0]
        .split()
    )
    assert 'no `user:` prefix' in tags
    assert '`Environment`, not `user:Environment`' in tags
    assert '(`aws:createdBy`)' in tags
    assert 'Keys and values are case-sensitive' in tags
    assert '`<key>$<value>`' in tags and 'The label is not a filter value' in tags
    assert '`"Values": [""]` matches the same costs as `ABSENT`' in tags
    assert (
        'With `Values` it matches nothing ($0, or an empty list); with `ABSENT` it matches '
        'every cost'
    ) in tags
    assert 'The forecasts accept either form' in tags
    assert '`{"Tags": {"Key": "", "Values": []}}`' in tags
    assert 'getCostAndUsage only: `{"Tags": {"Key": "", "Values": []}}`' in tags
    assert 'no activated cost allocation tag (user-defined or AWS-generated)' in tags
    assert (
        'getCostAndUsageWithResources, getDimensionValues, getTagsOrValues and '
        'getCostCategories reject an empty key'
    ) in tags
    assert 'An empty key with any value, or with Values omitted, is rejected' in tags
    assert 'Copy the key from getTagsOrValues' in tags


def test_description_documents_product_attributes():
    """ProductAttributes is a documented leaf, with its silent-mismatch and scope gotchas.

    A wrong key or value returns $0 (ABSENT: every Bedrock cost), Not and a PRODUCT_ATTRIBUTE
    group_by cover only supported services, and getDimensionValues needs a SERVICE filter.
    """
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    description = cost_explorer_tools.COST_EXPLORER_DESCRIPTION
    flat = ' '.join(description.split())
    assert '- Leaf keys: `Dimensions`, `Tags`, `CostCategories`, `ProductAttributes`' in flat
    assert '- ProductAttributes: EQUALS, ABSENT, CASE_SENSITIVE' in flat
    section = ' '.join(
        description.split('ProductAttributes leaves')[1]
        .split('Correct filter examples:')[0]
        .split()
    )
    assert 'the forecasts reject them' in section
    assert '`provider`, `model`, `inferenceType` and `feature`' in section
    assert 'only from 2026-09-01, in every account' in section
    assert 'DataUnavailableException' in section
    assert 'Keys and values are case-sensitive' in section
    assert 'With `Values` it matches nothing ($0)' in section
    assert '`"Values": [""]`' in section and 'every Bedrock cost' in section
    assert 'even under `Not`' in section
    assert 'do not add up to the account total' in section
    assert '`<key>$<value>`' in section and 'Filter on the value, not the label' in section
    assert 'If the filter has a SERVICE leaf anywhere' in section
    assert 'Under `Or`, every branch must be scoped that way' in section
    assert 'A SERVICE leaf under `Not` never counts' in section
    assert 'pair it with one in an `And`' in section
    assert 'omit SERVICE to include all of them' in section
    assert 'which differ by account' in section and '(Amazon Bedrock Edition)' in section
    assert 'a period that starts earlier returns DataUnavailableException' in section
    assert 'search_string does match case-insensitively and partially' in section
    assert 'PRODUCT_ATTRIBUTE: Product attributes of supported services' in flat
    assert 'dimension_key with any other dimension is rejected' in flat
    assert 'a wrong name returns only `""`, not an error' in flat
    examples = [json.loads(e) for e in _rendered_examples(description)]
    assert any(call.get('dimension_key') == 'model' for call in examples)


def test_description_states_match_options_and_value_limits():
    """A case option alone and more than 6,000 values are both rejected by Cost Explorer."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    description = ' '.join(cost_explorer_tools.COST_EXPLORER_DESCRIPTION.split())
    assert 'include EQUALS (or ABSENT): `["CASE_SENSITIVE"]` alone is rejected' in description
    assert 'at most 6,000 values in total, counted across all leaves' in description
    assert '`["ABSENT", "CASE_SENSITIVE"]` is rejected' in description


@pytest.mark.parametrize(
    'flt',
    [
        {'Tags': {'Key': 'user:Environment', 'MatchOptions': ['ABSENT']}},
        '{"Tags": {"Key": "user:Environment", "Values": ["Dev"]}}',
        {
            'And': [
                {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}},
                {'Not': {'Tags': {'Key': 'user:Environment', 'Values': ['Dev']}}},
            ]
        },
        {'Or': [{'Tags': {'Key': 'user:Environment', 'Values': ['Dev']}}]},
    ],
)
def test_tag_filter_hint_flags_user_prefixed_key(flt):
    """A user:-prefixed Tags key anywhere in the expression gets a hint naming the bare key."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    hint = cost_explorer_tools._tag_filter_hint(flt)
    assert hint is not None
    assert "Tags key 'user:Environment' has a user: prefix" in hint
    assert "Use 'Environment', unless getTagsOrValues lists the key with the prefix" in hint
    assert 'Values match nothing, and ABSENT matches every cost' in hint


def test_tag_filter_hint_flags_group_by_label_value():
    """A Values entry copied from a TAG group_by label gets a hint naming the bare value."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    hint = cost_explorer_tools._tag_filter_hint(
        {'Tags': {'Key': 'Environment', 'Values': ['Environment$Dev', 'QA']}}
    )
    assert hint is not None
    assert "Tags value 'Environment$Dev' is a TAG group_by label" in hint
    assert "Filter on 'Dev' instead" in hint
    assert 'user:' not in hint


@pytest.mark.parametrize(
    'flt',
    [
        None,
        '',
        'not json',
        '[1, 2]',
        {'Tags': {'Key': 'Environment', 'Values': ['Dev']}},
        {'Tags': {'Key': 'aws:createdBy', 'Values': ['IAMUser:x']}},
        {'Tags': {'Key': 'Environment', 'MatchOptions': ['ABSENT']}},
        {'Tags': {'Key': 'Environment', 'Values': ['']}},
        {'Tags': {'Values': ['Dev']}},
        {'Dimensions': {'Key': 'SERVICE', 'Values': ['user:x']}},
        {'CostCategories': {'Key': 'user:Team', 'Values': ['Team$A']}},
        {'Not': None, 'And': None},
        {'Tags': {'Key': 'user:', 'Values': ['Dev']}},
        {'Tags': {'Key': '', 'Values': ['$x']}},
        {'Tags': {'Key': '$Dev', 'Values': ['x']}},
    ],
)
def test_tag_filter_hint_ignores_filters_that_can_match(flt):
    """Correct Tags filters, non-Tags leaves and unparsable input get no hint."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    assert cost_explorer_tools._tag_filter_hint(flt) is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'operation, impl, extra',
    [
        ('getCostAndUsage', 'get_cost_and_usage', {}),
        ('getDimensionValues', 'get_dimension_values', {'dimension': 'SERVICE'}),
        ('getCostAndUsageWithResources', 'get_cost_and_usage_with_resources', {}),
        ('getTagsOrValues', 'get_tags', {}),
        ('getTagsOrValues', 'get_tags', {'tag_key': 'Environment'}),
        ('getCostCategories', 'get_cost_categories', {}),
        ('getCostCategories', 'get_cost_categories', {'cost_category_name': 'Team'}),
    ],
)
async def test_routed_response_carries_tag_filter_hint(mock_context, operation, impl, extra):
    """Every operation whose Tags matching was checked carries the hint on success.

    A user:-prefixed key returned $0 live in getCostAndUsageWithResources, where the
    unprefixed key returned the tagged resources' cost, and an empty list in getTagsOrValues
    and getCostCategories, where the unprefixed key returned matches.
    """
    ce_mod = _reload_ce_with_identity_decorator()
    flt = '{"Tags": {"Key": "user:Environment", "MatchOptions": ["ABSENT"]}}'
    with (
        patch.object(ce_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(ce_mod, impl, new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await ce_mod.cost_explorer(  # type: ignore
            mock_context, operation=operation, filter=flt, **extra
        )
    assert res['status'] == 'success'
    assert "Use 'Environment'" in res['hint']


@pytest.mark.asyncio
async def test_routed_response_hint_only_on_success_and_correct_filter(mock_context):
    """Errors keep the hint the error mapping adds, and a correct Tags filter adds none."""
    ce_mod = _reload_ce_with_identity_decorator()
    bad = {'Tags': {'Key': 'user:Environment', 'Values': ['Dev']}}
    with (
        patch.object(ce_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(ce_mod, 'get_cost_and_usage', new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'error', 'error_type': 'ThrottlingException'}
        res = await ce_mod.cost_explorer(  # type: ignore
            mock_context, operation='getCostAndUsage', filter=bad
        )
        assert 'hint' not in res

        mock_impl.return_value = {'status': 'success', 'data': {}, 'hint': 'own hint'}
        res = await ce_mod.cost_explorer(  # type: ignore
            mock_context, operation='getCostAndUsage', filter=bad
        )
        assert res['hint'] == 'own hint'

        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await ce_mod.cost_explorer(  # type: ignore
            mock_context,
            operation='getCostAndUsage',
            filter={'Tags': {'Key': 'Environment', 'Values': ['Dev']}},
        )
        assert 'hint' not in res


@pytest.mark.parametrize(
    'flt',
    [
        {'And': 5},
        {'Or': True},
        {'Tags': {'Key': 'Environment', 'Values': 5}},
        {'Tags': {'Key': 5, 'Values': ['Dev']}},
        '{"Not": ' * 3000 + '{}' + '}' * 3000,
    ],
)
def test_tag_filter_hint_tolerates_malformed_filters(flt):
    """Malformed or very deep filters get no hint and raise nothing; the API rejects them."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    assert cost_explorer_tools._tag_filter_hint(flt) is None


@pytest.mark.asyncio
async def test_malformed_filter_still_routes_to_the_operation(mock_context):
    """The hint check never stops a malformed filter from reaching the API's own validation."""
    ce_mod = _reload_ce_with_identity_decorator()
    with (
        patch.object(ce_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(ce_mod, 'get_tags', new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await ce_mod.cost_explorer(  # type: ignore
            mock_context, operation='getTagsOrValues', filter={'And': 5}
        )
    assert res == {'status': 'success', 'data': {}}


@pytest.mark.parametrize(
    'leaf, expected',
    [
        (
            {'Key': 'user:Environment', 'Values': ['Environment$Dev']},
            ["Use 'Environment'", "Tags value 'Environment$Dev'", "Filter on 'Dev' instead"],
        ),
        (
            {'Key': 'Environment$Dev', 'Values': ['x']},
            [
                "Tags key 'Environment$Dev' looks like a TAG group_by label",
                "Use Key 'Environment' with Values ['Dev']",
            ],
        ),
        (
            {'Key': 'Environment', 'Values': ['Environment$']},
            ['Use ABSENT for the Environment$ group'],
        ),
        (
            {'Key': 'User:Environment', 'Values': ['Dev']},
            ["Tags key 'User:Environment' has a user: prefix", "Use 'Environment'"],
        ),
        (
            {'Key': 'Environment$Dev', 'MatchOptions': ['ABSENT']},
            ["Use Key 'Environment'."],
        ),
        (
            {'Key': 'user:Environment$Dev', 'Values': ['x']},
            ["Use 'Environment$Dev'", "Use Key 'Environment' with Values ['Dev']"],
        ),
        (
            {'Key': 'user:Environment', 'Values': ['user:Environment$Dev']},
            ["Tags value 'user:Environment$Dev'", "Filter on 'Dev' instead"],
        ),
    ],
)
def test_tag_filter_hint_combined_and_label_cases(leaf, expected):
    """A prefixed key with a label value, a label as key, and the <key>$ label each get a fix."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    hint = cost_explorer_tools._tag_filter_hint({'And': [{'Tags': leaf}]})
    assert hint is not None
    for phrase in expected:
        assert phrase in hint
    assert "Filter on '' instead" not in hint


def test_tag_filter_hint_is_deduplicated():
    """The same bad key in two Or branches is reported once."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    leaf = {'Tags': {'Key': 'user:Environment', 'Values': ['Dev']}}
    hint = cost_explorer_tools._tag_filter_hint({'Or': [leaf, {'Not': leaf}]})
    assert hint is not None and hint.count("Tags key 'user:Environment'") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'operation, impl, extra',
    [
        ('getCostForecast', 'get_cost_forecast', {'metric': 'UNBLENDED_COST'}),
        ('getUsageForecast', 'get_usage_forecast', {'metric': 'USAGE_QUANTITY'}),
    ],
)
async def test_unchecked_operations_carry_no_tag_filter_hint(mock_context, operation, impl, extra):
    """The forecasts get no hint: they accept a user:-prefixed key.

    A forecast filtered on a user:-prefixed key returned the same forecast as the
    unprefixed key, so the "matches nothing" hint would be wrong there.
    """
    ce_mod = _reload_ce_with_identity_decorator()
    with (
        patch.object(ce_mod, 'create_aws_client', return_value=MagicMock()),
        patch.object(ce_mod, impl, new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await ce_mod.cost_explorer(  # type: ignore
            mock_context,
            operation=operation,
            filter={'Tags': {'Key': 'user:Environment', 'Values': ['Dev']}},
            **extra,
        )
    assert 'hint' not in res


# The arguments each operation needs to reach its handler, so a test can add one more.
OPERATION_HANDLERS = {
    'getCostAndUsage': ('get_cost_and_usage', {}),
    'getCostAndUsageWithResources': (
        'get_cost_and_usage_with_resources',
        {
            'filter': '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon Relational Database Service"]}}'
        },
    ),
    **NO_GROUP_BY_OPERATIONS,
}

# Arguments that operations drop, each with a value a caller would plausibly pass.
UNUSED_ARGUMENT_CASES = [
    (operation, argument, value)
    for argument, value, operations in [
        (
            'search_string',
            'no-such-service',
            [
                'getCostAndUsage',
                'getCostAndUsageWithResources',
                'getCostForecast',
                'getUsageForecast',
                'getSavingsPlansUtilization',
            ],
        ),
        ('tag_key', 'Environment', ['getCostCategories', 'getCostAndUsage', 'getDimensionValues']),
        ('cost_category_name', 'Teams', ['getTagsOrValues', 'getCostAndUsage']),
        ('dimension', 'SERVICE', [op for op in OPERATION_HANDLERS if op != 'getDimensionValues']),
        ('dimension_key', 'model', ['getCostAndUsage', 'getTagsOrValues', 'getCostForecast']),
        (
            'context',
            'SAVINGS_PLANS',
            [op for op in OPERATION_HANDLERS if op != 'getDimensionValues'],
        ),
        ('max_items', 1, ['getCostForecast', 'getUsageForecast', 'getSavingsPlansUtilization']),
        (
            'next_token',
            'tkn',
            ['getCostForecast', 'getUsageForecast', 'getSavingsPlansUtilization'],
        ),
        (
            'metric',
            'AMORTIZED_COST',
            [
                'getCostAndUsage',
                'getCostAndUsageWithResources',
                'getTagsOrValues',
                'getDimensionValues',
            ],
        ),
        (
            'metrics',
            '["AmortizedCost"]',
            ['getCostForecast', 'getUsageForecast', 'getTagsOrValues'],
        ),
        ('metrics', ['AmortizedCost'], ['getSavingsPlansUtilization']),
        (
            'billing_view_arn',
            'arn:aws:billing::123456789012:billingview/custom-abc',
            ['getSavingsPlansUtilization'],
        ),
    ]
    for operation in operations
]


@pytest.mark.asyncio
@pytest.mark.parametrize('operation, argument, value', UNUSED_ARGUMENT_CASES)
async def test_an_argument_the_operation_does_not_use_is_rejected(
    mock_context, real_cost_explorer, operation, argument, value
):
    """An argument the operation never sends is a validation_error, not a silent drop.

    Dropping it returns a result that reads as narrowed (search_string, tag_key) or as
    selected (metric, context) when it is not. No AWS client is created.
    """
    handler, args = OPERATION_HANDLERS[operation]
    with (
        patch.object(real_cost_explorer, 'create_aws_client') as mock_client,
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock) as mock_impl,
    ):
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, **{**args, argument: value}
        )

    mock_impl.assert_not_awaited()
    mock_client.assert_not_called()
    assert res['status'] == 'error'
    assert res['error_type'] == 'validation_error'
    assert res['operation'] == operation
    assert res['message'].startswith(f'{argument} is not supported for {operation}: ')
    assert res['hint'] == real_cost_explorer.UNUSED_ARGUMENT_HINT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'operation, argument, value, pointer',
    [
        ('getCostCategories', 'tag_key', 'Environment', 'operation=getTagsOrValues with tag_key'),
        (
            'getTagsOrValues',
            'cost_category_name',
            'Teams',
            'operation=getCostCategories with cost_category_name',
        ),
        ('getCostAndUsage', 'search_string', 'EC2', 'put exact values in filter'),
        ('getCostAndUsage', 'metric', 'AMORTIZED_COST', 'take metrics instead'),
        ('getCostForecast', 'metrics', '["AmortizedCost"]', 'take metric instead'),
        ('getCostAndUsage', 'dimension', 'SERVICE', 'use getCostAndUsage with group_by'),
        ('getCostForecast', 'max_items', 1, 'whole result comes back in one response'),
        ('getTagsOrValues', 'group_by', REGION_GROUP_BY, 'getDimensionValues to list'),
        ('getCostAndUsage', 'dimension_key', 'model', 'ProductAttributes leaf in filter'),
        ('getCostAndUsage', 'dimension', 'PRODUCT_ATTRIBUTE', 'ProductAttributes leaf'),
        (
            'getUsageForecast',
            'metrics',
            '["UsageQuantity"]',
            'USAGE_QUANTITY for getUsageForecast',
        ),
    ],
)
async def test_unused_argument_message_points_to_what_the_caller_meant(
    mock_context, real_cost_explorer, operation, argument, value, pointer
):
    """The message names the operation or argument that does what the caller asked for."""
    handler, args = OPERATION_HANDLERS[operation]
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock),
    ):
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, **{**args, argument: value}
        )

    assert res['error_type'] == 'validation_error'
    assert pointer in res['message']


@pytest.mark.asyncio
async def test_every_unused_argument_is_named_in_one_error(mock_context, real_cost_explorer):
    """Several unused arguments are reported together, so one retry fixes them all."""
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, 'get_cost_categories', new_callable=AsyncMock) as impl,
    ):
        res = await real_cost_explorer.cost_explorer(
            mock_context,
            operation='getCostCategories',
            tag_key='Environment',
            dimension='SERVICE',
            group_by=REGION_GROUP_BY,
        )

    impl.assert_not_awaited()
    for argument in ('tag_key', 'dimension', 'group_by'):
        assert f'{argument} is not supported for getCostCategories' in res['message']
    assert res['hint'].count('Do **NOT** retry') == 1


# A value that counts as set for every argument the tool takes but ctx and operation.
SET_VALUES = {
    'start_date': '2026-01-01',
    'end_date': '2026-02-01',
    'granularity': 'MONTHLY',
    'metrics': '["AmortizedCost"]',
    'group_by': REGION_GROUP_BY,
    'filter': '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}',
    'dimension': 'SERVICE',
    'dimension_key': 'model',
    'search_string': 'EC2',
    'max_items': 1,
    'next_token': 'tkn',
    'metric': 'AMORTIZED_COST',
    'prediction_interval_level': 95,
    'tag_key': 'Environment',
    'cost_category_name': 'Teams',
    'billing_view_arn': 'arn:aws:billing::123456789012:billingview/custom-abc',
    'context': 'SAVINGS_PLANS',
}


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', sorted(OPERATION_HANDLERS))
async def test_every_argument_the_operation_does_not_list_is_checked(
    mock_context, real_cost_explorer, operation
):
    """With every argument set, the error names exactly the unlisted ones, in signature order.

    This covers every tool parameter, so a parameter the check does not see fails here.
    """
    import inspect

    parameters = [
        name
        for name in inspect.signature(real_cost_explorer.cost_explorer).parameters
        if name not in ('ctx', 'operation')
    ]
    assert sorted(parameters) == sorted(SET_VALUES)
    accepted = real_cost_explorer.OPERATION_ARGUMENTS[operation]
    expected = [
        name
        for name in parameters
        if name not in accepted and name not in real_cost_explorer.UNCHECKED_ARGUMENTS
    ]
    handler, _ = OPERATION_HANDLERS[operation]
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock) as mock_impl,
    ):
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, **SET_VALUES
        )

    mock_impl.assert_not_awaited()
    named = re.findall(r'(\w+) is not supported for ' + operation, res['message'])
    assert named == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', sorted(OPERATION_HANDLERS))
@pytest.mark.parametrize(
    'unset',
    [
        {},
        {
            'search_string': '',
            'tag_key': '',
            'cost_category_name': '',
            'next_token': '',
            'billing_view_arn': '',
            'dimension_key': '',
        },
        {
            'dimension': None,
            'context': None,
            'max_items': None,
            'metric': None,
            'dimension_key': None,
        },
        {'group_by': '[]', 'metrics': '[]'},
        {'group_by': 'null', 'metrics': []},
        {'group_by': '{}', 'metrics': 'null'},
        {'granularity': 'MONTHLY', 'prediction_interval_level': 95},
    ],
    ids=[
        'omitted',
        'empty-strings',
        'none',
        'empty-json',
        'null-json',
        'empty-object',
        'unchecked',
    ],
)
async def test_unset_and_unchecked_arguments_are_not_rejected(
    mock_context, real_cost_explorer, operation, unset
):
    """None, '' and empty JSON are not set; granularity and prediction_interval_level are not checked."""
    handler, args = OPERATION_HANDLERS[operation]
    unset = {k: v for k, v in unset.items() if k not in args}
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, **{**args, **unset}
        )

    assert res['status'] == 'success', res
    mock_impl.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'operation, argument, value',
    [
        ('getDimensionValues', 'search_string', 'EC2'),
        ('getDimensionValues', 'context', 'SAVINGS_PLANS'),
        ('getDimensionValues', 'max_items', 7),
        ('getTagsOrValues', 'tag_key', 'Environment'),
        ('getTagsOrValues', 'search_string', 'Env'),
        ('getCostCategories', 'cost_category_name', 'Teams'),
        ('getCostCategories', 'next_token', 'tkn'),
        ('getCostAndUsage', 'max_items', 7),
        ('getCostAndUsage', 'metrics', '["AmortizedCost"]'),
        ('getCostForecast', 'prediction_interval_level', 95),
        ('getSavingsPlansUtilization', 'granularity', 'MONTHLY'),
    ],
)
async def test_an_argument_the_operation_uses_still_reaches_it(
    mock_context, real_cost_explorer, operation, argument, value
):
    """The check rejects only what an operation drops; what it sends reaches its parameter."""
    import inspect
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_operations

    handler, args = OPERATION_HANDLERS[operation]
    position = list(
        inspect.signature(getattr(cost_explorer_operations, handler)).parameters
    ).index(argument)
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, handler, new_callable=AsyncMock) as mock_impl,
    ):
        mock_impl.return_value = {'status': 'success', 'data': {}}
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation=operation, **{**args, argument: value}
        )

    assert res['status'] == 'success', res
    assert mock_impl.await_args is not None
    assert mock_impl.await_args.args[position] == value


@pytest.mark.asyncio
async def test_a_non_json_type_counts_as_set(mock_context, real_cost_explorer):
    """A metrics value json cannot read (an int from a direct call) is set, not a TypeError."""
    with (
        patch.object(real_cost_explorer, 'create_aws_client', return_value=MagicMock()),
        patch.object(real_cost_explorer, 'get_tags', new_callable=AsyncMock) as mock_impl,
    ):
        res = await real_cost_explorer.cost_explorer(
            mock_context, operation='getTagsOrValues', metrics=5
        )

    mock_impl.assert_not_awaited()
    assert res['message'].startswith('metrics is not supported for getTagsOrValues: ')


@pytest.mark.asyncio
async def test_served_tool_rejects_an_unused_argument():
    """Through the registered FastMCP tool (not the reloaded function), the check still runs."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools as module

    with (
        patch.object(module, 'create_aws_client') as mock_client,
        patch.object(module, 'get_cost_categories', new_callable=AsyncMock) as mock_impl,
    ):
        async with fastmcp.Client(module.cost_explorer_server) as client:
            result = await client.call_tool(
                'cost-explorer',
                {'operation': 'getCostCategories', 'tag_key': 'Environment'},
                raise_on_error=False,
            )

    content = result.content[0]
    assert isinstance(content, mcp.types.TextContent)
    res = json.loads(content.text)
    mock_client.assert_not_called()
    mock_impl.assert_not_awaited()
    assert res['error_type'] == 'validation_error'
    assert res['message'].startswith('tag_key is not supported for getCostCategories: ')


def _documented_arguments() -> dict:
    """Return each operation's Required and Optional arguments as the description lists them."""
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    block = cost_explorer_tools.COST_EXPLORER_DESCRIPTION.split('## OPERATIONS')[1]
    block = block.split('DIMENSION REFERENCE:')[0]
    documented = {}
    for section in re.split(r'^\d+[.)] ', block, flags=re.MULTILINE)[1:]:
        operation = section.split()[0]
        names = set()
        for label in ('Required', 'Optional'):
            match = re.search(rf'^\s+{label}: (.*)$', section, flags=re.MULTILINE)
            if match:
                names |= {name.split('=')[0].strip() for name in match.group(1).split(',')}
        documented[operation] = names - {'operation'}
    return documented


def test_documented_arguments_match_what_each_operation_accepts():
    """Each operation's Required and Optional lists are exactly the arguments it accepts.

    A list that names an argument the table rejects (or misses one it accepts) sends callers
    into a validation_error, or hides an argument they could use.
    """
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    documented = _documented_arguments()
    assert len(documented) == 8
    assert documented == {
        op: set(args) for op, args in cost_explorer_tools.OPERATION_ARGUMENTS.items()
    }


def test_every_tool_argument_is_used_by_some_operation():
    """A new cost-explorer argument must be added to the table of the operations that send it.

    Otherwise every operation rejects it.
    """
    import inspect
    from awslabs.billing_cost_management_mcp_server.tools import cost_explorer_tools

    parameters = set(inspect.signature(cost_explorer_tools.cost_explorer).parameters)
    accepted = set().union(*cost_explorer_tools.OPERATION_ARGUMENTS.values())
    assert accepted == parameters - {'ctx', 'operation'}
    rejected_somewhere = {
        name
        for name in accepted
        if any(name not in args for args in cost_explorer_tools.OPERATION_ARGUMENTS.values())
    }
    assert set(cost_explorer_tools.UNUSED_ARGUMENT_REASONS) == (
        rejected_somewhere - cost_explorer_tools.UNCHECKED_ARGUMENTS
    )
    assert cost_explorer_tools.UNCHECKED_ARGUMENTS <= rejected_somewhere


@pytest.mark.asyncio
async def test_description_says_other_arguments_are_rejected():
    """The description says an argument outside an operation's lists is rejected, not ignored."""
    tool = await cost_explorer_server.get_tool('cost-explorer')
    assert tool is not None and tool.description
    description = ' '.join(tool.description.split())
    assert (
        'Each operation takes only the arguments in its Required and Optional lists below; '
        'any other argument is rejected with a validation_error rather than ignored'
    ) in description
    assert (
        'The exceptions are granularity and prediction_interval_level, which an operation that '
        'does not list them ignores'
    ) in description
    assert 'the other operations reject both' in description
    assert 'the other operations take neither' not in description
