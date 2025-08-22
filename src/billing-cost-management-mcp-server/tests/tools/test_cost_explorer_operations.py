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

"""Unit tests for the cost_explorer_operations module."""

import pytest
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
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


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
                'Groups': [],
            }
        ]
    }

    mock_client.get_cost_and_usage_with_resources.return_value = {
        'ResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'},
                'Groups': [
                    {
                        'Keys': ['i-1234567890abcdef0'],
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

    mock_client.get_usage_forecast.return_value = {
        'Total': {'Amount': '1500.0', 'Unit': 'GB'},
        'ForecastResultsByTime': [
            {
                'TimePeriod': {'Start': '2023-02-01', 'End': '2023-02-28'},
                'MeanValue': '1500.0',
            }
        ],
    }

    mock_client.get_tags.return_value = {'Tags': ['Environment', 'Project']}
    mock_client.get_tag_values.return_value = {'TagValues': ['dev', 'prod', 'test']}

    mock_client.get_cost_categories.return_value = {'CostCategoryNames': ['Department', 'Team']}
    mock_client.get_cost_category_values.return_value = {
        'CostCategoryValues': ['Engineering', 'Marketing']
    }

    mock_client.get_savings_plans_utilization.return_value = {
        'SavingsPlansUtilizationsByTime': [
            {
                'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-31'},
                'Utilization': {'Utilization': '0.85'},
            }
        ]
    }

    return mock_client


@pytest.mark.asyncio
class TestGetCostAndUsage:
    """Tests for get_cost_and_usage function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_and_usage."""
        result = await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='DAILY',
        )

        mock_ce_client.get_cost_and_usage.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
        assert call_kwargs['Granularity'] == 'DAILY'
        assert call_kwargs['Metrics'] == ['UnblendedCost']  # Default metric

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_json_parameters(self, mock_context, mock_ce_client):
        """Test with JSON parameters for metrics, group_by, and filters."""
        metrics_json = '["UnblendedCost", "UsageQuantity"]'
        group_by_json = '[{"Type": "DIMENSION", "Key": "SERVICE"}]'
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            # Set up mock return values for parse_json calls
            mock_parse_json.side_effect = [
                ['UnblendedCost', 'UsageQuantity'],  # metrics
                [{'Type': 'DIMENSION', 'Key': 'SERVICE'}],  # group_by
                {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}},  # filter
            ]

            await get_cost_and_usage(
                mock_context,
                mock_ce_client,
                start_date='2023-01-01',
                end_date='2023-01-31',
                granularity='DAILY',
                metrics=metrics_json,
                group_by=group_by_json,
                filter_expr=filter_json,
            )

        # Verify the client was called with parsed parameters
        call_kwargs = mock_ce_client.get_cost_and_usage.call_args[1]
        assert 'Metrics' in call_kwargs
        assert 'GroupBy' in call_kwargs
        assert 'Filter' in call_kwargs

    async def test_with_pagination(self, mock_context, mock_ce_client):
        """Test pagination handling in get_cost_and_usage."""
        # Setup paginated responses
        mock_ce_client.get_cost_and_usage.side_effect = [
            {
                'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-01', 'End': '2023-01-02'}}],
                'NextPageToken': 'page2token',
            },
            {
                'ResultsByTime': [{'TimePeriod': {'Start': '2023-01-02', 'End': '2023-01-03'}}],
                'NextPageToken': None,
            },
        ]

        # Test actual pagination handling in the code
        result = await get_cost_and_usage(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            next_token='initial_token',
            max_pages=2,
        )

        # Verify response is successful
        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_and_usage."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_and_usage.side_effect = error

        # Don't mock handle_aws_error since we want to test the actual error path
        result = await get_cost_and_usage(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetCostAndUsageWithResources:
    """Tests for get_cost_and_usage_with_resources function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_and_usage_with_resources."""
        # We need to mock get_date_range to ensure our dates are used as is
        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.get_date_range',
            return_value=('2023-01-01', '2023-01-07'),
        ):
            result = await get_cost_and_usage_with_resources(
                mock_context,
                mock_ce_client,
                start_date='2023-01-01',
                end_date='2023-01-07',
                granularity='DAILY',
            )

            # Just verify that the function was called and returned success
            mock_ce_client.get_cost_and_usage_with_resources.assert_called_once()
            assert result['status'] == 'success'
            assert result['data'] is not None

    async def test_date_adjustment_for_14_day_limit(self, mock_context, mock_ce_client):
        """Test date adjustment for the 14-day limit of resource data."""
        # Setup a date more than 14 days ago
        today = datetime.now()
        old_date = (today - timedelta(days=20)).strftime('%Y-%m-%d')

        # Expected adjusted date (14 days ago)
        (today - timedelta(days=14)).strftime('%Y-%m-%d')

        await get_cost_and_usage_with_resources(
            mock_context,
            mock_ce_client,
            start_date=old_date,
            end_date=today.strftime('%Y-%m-%d'),
        )

        mock_ce_client.get_cost_and_usage_with_resources.assert_called_once()

    async def test_with_json_parameters(self, mock_context, mock_ce_client):
        """Test with JSON parameters for metrics, group_by, and filters."""
        metrics_json = '["UnblendedCost"]'
        group_by_json = '[{"Type": "RESOURCE", "Key": "RESOURCE_ID"}]'
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json'
        ) as mock_parse_json:
            # Set up mock return values for parse_json calls
            mock_parse_json.side_effect = [
                ['UnblendedCost'],  # metrics
                [{'Type': 'RESOURCE', 'Key': 'RESOURCE_ID'}],  # group_by
                {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}},  # filter
            ]

            await get_cost_and_usage_with_resources(
                mock_context,
                mock_ce_client,
                start_date='2023-01-01',
                end_date='2023-01-07',
                granularity='DAILY',
                metrics=metrics_json,
                group_by=group_by_json,
                filter_expr=filter_json,
            )

        # Verify the client was called with parsed parameters
        call_kwargs = mock_ce_client.get_cost_and_usage_with_resources.call_args[1]
        assert 'Metrics' in call_kwargs
        assert 'GroupBy' in call_kwargs
        assert 'Filter' in call_kwargs

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_and_usage_with_resources."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_and_usage_with_resources.side_effect = error

        # Test the actual error handling path
        result = await get_cost_and_usage_with_resources(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetDimensionValues:
    """Tests for get_dimension_values function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_dimension_values."""
        result = await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        mock_ce_client.get_dimension_values.assert_called_once()
        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
        assert call_kwargs['Dimension'] == 'SERVICE'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_search_string(self, mock_context, mock_ce_client):
        """Test get_dimension_values with search string."""
        await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
            search_string='AWS',
        )

        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert 'SearchString' in call_kwargs
        assert call_kwargs['SearchString'] == 'AWS'

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_dimension_values with filter expression."""
        filter_json = '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}'
        filter_dict = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_dimension_values(
                mock_context,
                mock_ce_client,
                dimension='SERVICE',
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_with_max_results(self, mock_context, mock_ce_client):
        """Test get_dimension_values with max_results parameter."""
        await get_dimension_values(
            mock_context,
            mock_ce_client,
            dimension='SERVICE',
            max_results=50,
        )

        call_kwargs = mock_ce_client.get_dimension_values.call_args[1]
        assert 'MaxResults' in call_kwargs
        assert call_kwargs['MaxResults'] == 50

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_dimension_values."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_dimension_values.side_effect = error

        # Test the actual error handling path
        result = await get_dimension_values(mock_context, mock_ce_client, dimension='SERVICE')

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetCostForecast:
    """Tests for get_cost_forecast function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_forecast."""
        result = await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            start_date='2023-02-01',
            end_date='2023-02-28',
        )

        mock_ce_client.get_cost_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-02-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-02-28'
        assert call_kwargs['Metric'] == 'UNBLENDED_COST'
        assert call_kwargs['Granularity'] == 'MONTHLY'  # Default
        assert call_kwargs['PredictionIntervalLevel'] == 80  # Default

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_default_future_dates(self, mock_context, mock_ce_client):
        """Test default future dates for forecasting."""
        await get_cost_forecast(mock_context, mock_ce_client, metric='UNBLENDED_COST')

        # Verify API was called with future dates
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert 'TimePeriod' in call_kwargs
        assert 'Start' in call_kwargs['TimePeriod']
        assert 'End' in call_kwargs['TimePeriod']

        # Start date should be tomorrow or later
        start_date = datetime.strptime(call_kwargs['TimePeriod']['Start'], '%Y-%m-%d')
        today = datetime.now()
        assert start_date > today  # Start date should be in the future

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_cost_forecast with filter expression."""
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'
        filter_dict = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_cost_forecast(
                mock_context,
                mock_ce_client,
                metric='UNBLENDED_COST',
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_with_custom_prediction_interval(self, mock_context, mock_ce_client):
        """Test get_cost_forecast with custom prediction interval."""
        await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            prediction_interval_level=95,
        )

        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_kwargs['PredictionIntervalLevel'] == 95

    async def test_with_different_granularity(self, mock_context, mock_ce_client):
        """Test get_cost_forecast with different granularity."""
        await get_cost_forecast(
            mock_context,
            mock_ce_client,
            metric='UNBLENDED_COST',
            granularity='DAILY',
        )

        call_kwargs = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_kwargs['Granularity'] == 'DAILY'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_forecast."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_forecast.side_effect = error

        # Test the actual error handling path
        result = await get_cost_forecast(mock_context, mock_ce_client, metric='UNBLENDED_COST')

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetUsageForecast:
    """Tests for get_usage_forecast function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_usage_forecast."""
        result = await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='STORAGE_FORECAST',
            start_date='2023-02-01',
            end_date='2023-02-28',
        )

        mock_ce_client.get_usage_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-02-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-02-28'
        assert call_kwargs['Metric'] == 'STORAGE_FORECAST'
        assert call_kwargs['Granularity'] == 'MONTHLY'  # Default
        assert call_kwargs['PredictionIntervalLevel'] == 80  # Default

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_default_future_dates(self, mock_context, mock_ce_client):
        """Test default future dates for forecasting."""
        await get_usage_forecast(mock_context, mock_ce_client, metric='STORAGE_FORECAST')

        # Verify API was called with future dates
        mock_ce_client.get_usage_forecast.assert_called_once()
        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert 'TimePeriod' in call_kwargs
        assert 'Start' in call_kwargs['TimePeriod']
        assert 'End' in call_kwargs['TimePeriod']

        # Start date should be tomorrow or later
        start_date = datetime.strptime(call_kwargs['TimePeriod']['Start'], '%Y-%m-%d')
        today = datetime.now()
        assert start_date > today  # Start date should be in the future

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_usage_forecast with filter expression."""
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon S3"]}}'
        filter_dict = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon S3']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_usage_forecast(
                mock_context,
                mock_ce_client,
                metric='STORAGE_FORECAST',
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_with_custom_prediction_interval(self, mock_context, mock_ce_client):
        """Test get_usage_forecast with custom prediction interval."""
        await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='STORAGE_FORECAST',
            prediction_interval_level=90,
        )

        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert call_kwargs['PredictionIntervalLevel'] == 90

    async def test_with_different_granularity(self, mock_context, mock_ce_client):
        """Test get_usage_forecast with different granularity."""
        await get_usage_forecast(
            mock_context,
            mock_ce_client,
            metric='STORAGE_FORECAST',
            granularity='DAILY',
        )

        call_kwargs = mock_ce_client.get_usage_forecast.call_args[1]
        assert call_kwargs['Granularity'] == 'DAILY'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_usage_forecast."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_usage_forecast.side_effect = error

        # Test the actual error handling path
        result = await get_usage_forecast(mock_context, mock_ce_client, metric='STORAGE_FORECAST')

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetTags:
    """Tests for get_tags function."""

    async def test_get_tags_basic(self, mock_context, mock_ce_client):
        """Test basic call to get_tags."""
        result = await get_tags(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        mock_ce_client.get_tags.assert_called_once()
        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_get_tag_values(self, mock_context, mock_ce_client):
        """Test get_tags with tag_key to get tag values."""
        result = await get_tags(
            mock_context,
            mock_ce_client,
            tag_key='Environment',
        )

        mock_ce_client.get_tags.assert_called_once()
        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert 'TagKey' in call_kwargs
        assert call_kwargs['TagKey'] == 'Environment'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_search_string(self, mock_context, mock_ce_client):
        """Test get_tags with search string."""
        await get_tags(
            mock_context,
            mock_ce_client,
            search_string='Env',
        )

        call_kwargs = mock_ce_client.get_tags.call_args[1]
        assert 'SearchString' in call_kwargs
        assert call_kwargs['SearchString'] == 'Env'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_tags."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_tags.side_effect = error

        # Test the actual error handling path
        result = await get_tags(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetCostCategories:
    """Tests for get_cost_categories function."""

    async def test_get_cost_categories_basic(self, mock_context, mock_ce_client):
        """Test basic call to get_cost_categories."""
        result = await get_cost_categories(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
        )

        mock_ce_client.get_cost_categories.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_categories.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_get_cost_category_values(self, mock_context, mock_ce_client):
        """Test get_cost_categories with cost_category_name to get values."""
        result = await get_cost_categories(
            mock_context,
            mock_ce_client,
            cost_category_name='Department',
        )

        mock_ce_client.get_cost_category_values.assert_called_once()
        call_kwargs = mock_ce_client.get_cost_category_values.call_args[1]
        assert 'CostCategoryName' in call_kwargs
        assert call_kwargs['CostCategoryName'] == 'Department'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_search_string(self, mock_context, mock_ce_client):
        """Test get_cost_categories with search string."""
        await get_cost_categories(
            mock_context,
            mock_ce_client,
            search_string='Dep',
        )

        call_kwargs = mock_ce_client.get_cost_categories.call_args[1]
        assert 'SearchString' in call_kwargs
        assert call_kwargs['SearchString'] == 'Dep'

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_cost_categories."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_cost_categories.side_effect = error

        # Test the actual error handling path
        result = await get_cost_categories(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result


@pytest.mark.asyncio
class TestGetSavingsPlansUtilization:
    """Tests for get_savings_plans_utilization function."""

    async def test_basic_call(self, mock_context, mock_ce_client):
        """Test basic call to get_savings_plans_utilization."""
        result = await get_savings_plans_utilization(
            mock_context,
            mock_ce_client,
            start_date='2023-01-01',
            end_date='2023-01-31',
            granularity='MONTHLY',
        )

        mock_ce_client.get_savings_plans_utilization.assert_called_once()
        call_kwargs = mock_ce_client.get_savings_plans_utilization.call_args[1]
        assert call_kwargs['TimePeriod']['Start'] == '2023-01-01'
        assert call_kwargs['TimePeriod']['End'] == '2023-01-31'
        assert call_kwargs['Granularity'] == 'MONTHLY'

        assert result['status'] == 'success'
        assert result['data'] is not None

    async def test_with_filter(self, mock_context, mock_ce_client):
        """Test get_savings_plans_utilization with filter expression."""
        filter_json = '{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"]}}'
        filter_dict = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}

        # Mock the parse_json function to return our dictionary
        original_parse_json = __import__(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base',
            fromlist=['parse_json'],
        ).parse_json

        def mock_parse_json(json_string, label):
            if json_string == filter_json and label == 'filter':
                return filter_dict
            return original_parse_json(json_string, label)

        with patch(
            'awslabs.billing_cost_management_mcp_server.utilities.aws_service_base.parse_json',
            side_effect=mock_parse_json,
        ):
            await get_savings_plans_utilization(
                mock_context,
                mock_ce_client,
                filter_expr=filter_json,
            )

            # Verify the client was called with parsed filter
            call_kwargs = mock_ce_client.get_savings_plans_utilization.call_args[1]
            assert 'Filter' in call_kwargs

    async def test_error_handling(self, mock_context, mock_ce_client):
        """Test error handling in get_savings_plans_utilization."""
        # Setup error
        error = Exception('Test error')
        mock_ce_client.get_savings_plans_utilization.side_effect = error

        # Test the actual error handling path
        result = await get_savings_plans_utilization(mock_context, mock_ce_client)

        # Verify error was properly handled
        assert result['status'] == 'error'
        assert 'message' in result
