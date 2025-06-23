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

"""Tests for forecasting_handler module."""

import pytest
from awslabs.cost_explorer_mcp_server.forecasting_handler import get_cost_forecast
from awslabs.cost_explorer_mcp_server.models import DateRange
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


@pytest.fixture
def future_date_range():
    """Future date range for forecasting."""
    # Use current date as start to avoid validation errors
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
    return DateRange(start_date=today, end_date=end_date)


@pytest.fixture
def mock_ce_client():
    """Mock Cost Explorer client."""
    with patch(
        'awslabs.cost_explorer_mcp_server.forecasting_handler.get_cost_explorer_client'
    ) as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestCostForecast:
    """Test cost forecasting functionality."""

    @pytest.mark.asyncio
    async def test_get_cost_forecast_monthly(self, mock_ce_client, future_date_range):
        """Test cost forecast with monthly granularity."""
        # Setup mock response
        mock_ce_client.get_cost_forecast.return_value = {
            'Total': {'Amount': '500.00', 'Unit': 'USD'},
            'ForecastResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-06-01', 'End': '2025-07-01'},
                    'MeanValue': '150.00',
                    'PredictionIntervalLowerBound': '120.00',
                    'PredictionIntervalUpperBound': '180.00',
                },
                {
                    'TimePeriod': {'Start': '2025-07-01', 'End': '2025-08-01'},
                    'MeanValue': '160.00',
                    'PredictionIntervalLowerBound': '130.00',
                    'PredictionIntervalUpperBound': '190.00',
                },
                {
                    'TimePeriod': {'Start': '2025-08-01', 'End': '2025-09-01'},
                    'MeanValue': '190.00',
                    'PredictionIntervalLowerBound': '150.00',
                    'PredictionIntervalUpperBound': '230.00',
                },
            ],
        }

        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify API call parameters
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_args = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_args['Granularity'] == 'MONTHLY'
        assert call_args['TimePeriod']['Start'] == future_date_range.start_date
        assert call_args['TimePeriod']['End'] == future_date_range.end_date

        # Verify result structure
        assert isinstance(result, dict)
        assert 'total_forecast' in result
        assert 'confidence_level' in result
        # Verify total_forecast has some value (could be string or number)
        assert result['total_forecast'] is not None

    @pytest.mark.asyncio
    async def test_get_cost_forecast_daily(self, mock_ce_client, future_date_range):
        """Test cost forecast with daily granularity."""
        # Setup mock response
        mock_ce_client.get_cost_forecast.return_value = {
            'Total': {'Amount': '500.00', 'Unit': 'USD'},
            'ForecastResultsByTime': [
                {'TimePeriod': {'Start': '2025-06-20', 'End': '2025-06-21'}, 'MeanValue': '5.00'},
                {'TimePeriod': {'Start': '2025-06-21', 'End': '2025-06-22'}, 'MeanValue': '5.10'},
                {'TimePeriod': {'Start': '2025-06-22', 'End': '2025-06-23'}, 'MeanValue': '5.20'},
                # More days would be here in a real response
            ],
        }

        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='DAILY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify API call parameters
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_args = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_args['Granularity'] == 'DAILY'

        # Verify result structure
        assert isinstance(result, dict)
        assert 'total_forecast' in result
        assert 'confidence_level' in result
        assert 'granularity' in result
        assert result['granularity'] == 'DAILY'

    @pytest.mark.asyncio
    async def test_get_cost_forecast_with_filter(self, mock_ce_client, future_date_range):
        """Test cost forecast with service filter."""
        # Setup mock response
        mock_ce_client.get_cost_forecast.return_value = {
            'Total': {'Amount': '200.00', 'Unit': 'USD'},
            'ForecastResultsByTime': [
                {'TimePeriod': {'Start': '2025-06-01', 'End': '2025-07-01'}, 'MeanValue': '200.00'}
            ],
        }

        # Create filter expression
        filter_expr = {
            'Dimensions': {
                'Key': 'SERVICE',
                'Values': ['Amazon Elastic Compute Cloud - Compute'],
                'MatchOptions': ['EQUALS'],
            }
        }

        ctx = MagicMock()
        # Patch validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.forecasting_handler.validate_expression',
            return_value=filter_expr,
        ):
            result = await get_cost_forecast(
                ctx,
                future_date_range,
                granularity='MONTHLY',
                filter_expression=filter_expr,
                metric='UNBLENDED_COST',
                prediction_interval_level=80,
            )

        # Verify API call parameters
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_args = mock_ce_client.get_cost_forecast.call_args[1]
        assert 'Filter' in call_args
        assert call_args['Filter'] == filter_expr

        # Verify result structure
        assert isinstance(result, dict)
        assert 'total_forecast' in result
        assert 'confidence_level' in result
        assert 'granularity' in result

    @pytest.mark.asyncio
    async def test_get_cost_forecast_with_metric(self, mock_ce_client, future_date_range):
        """Test cost forecast with different metrics."""
        # Setup mock response
        mock_ce_client.get_cost_forecast.return_value = {
            'Total': {'Amount': '300.00', 'Unit': 'USD'},
            'ForecastResultsByTime': [],
        }

        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='AMORTIZED_COST',
            prediction_interval_level=80,
        )

        # Verify API call parameters
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_args = mock_ce_client.get_cost_forecast.call_args[1]
        assert 'Metric' in call_args
        assert call_args['Metric'] == 'AMORTIZED_COST'

        # Verify result structure
        assert isinstance(result, dict)
        assert 'total_forecast' in result

    @pytest.mark.asyncio
    async def test_get_cost_forecast_with_prediction_interval(
        self, mock_ce_client, future_date_range
    ):
        """Test cost forecast with prediction interval."""
        # Setup mock response
        mock_ce_client.get_cost_forecast.return_value = {
            'Total': {'Amount': '300.00', 'Unit': 'USD'},
            'ForecastResultsByTime': [],
        }

        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=95,
        )

        # Verify API call parameters
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_args = mock_ce_client.get_cost_forecast.call_args[1]
        assert 'PredictionIntervalLevel' in call_args
        assert call_args['PredictionIntervalLevel'] == 95

        # Verify result structure
        assert isinstance(result, dict)
        assert 'total_forecast' in result

    @pytest.mark.asyncio
    async def test_get_cost_forecast_api_error(self, mock_ce_client, future_date_range):
        """Test cost forecast with API error."""
        # Setup mock error
        mock_ce_client.get_cost_forecast.side_effect = Exception('Forecast API Error')

        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Forecast API Error' in result['error']

    @pytest.mark.asyncio
    async def test_get_cost_forecast_validation_error(self, mock_ce_client):
        """Test cost forecast with validation error."""
        # Use invalid date range (past dates)
        invalid_date_range = DateRange(start_date='2024-01-01', end_date='2024-02-01')

        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            invalid_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        # API should not be called with invalid parameters
        mock_ce_client.get_cost_forecast.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_forecast_with_blended_cost(self, mock_ce_client, future_date_range):
        """Test cost forecast with BlendedCost metric."""
        # Setup mock response
        mock_ce_client.get_cost_forecast.return_value = {
            'Total': {'Amount': '400.00', 'Unit': 'USD'},
            'ForecastResultsByTime': [],
        }

        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='BLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify API call parameters
        mock_ce_client.get_cost_forecast.assert_called_once()
        call_args = mock_ce_client.get_cost_forecast.call_args[1]
        assert call_args['Metric'] == 'BLENDED_COST'

        # Verify result structure
        assert isinstance(result, dict)
        assert 'total_forecast' in result

    @pytest.mark.asyncio
    async def test_get_cost_forecast_invalid_granularity(self, mock_ce_client, future_date_range):
        """Test cost forecast with invalid granularity."""
        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='INVALID',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid granularity' in result['error']
        assert 'DAILY and MONTHLY' in result['error']
        # API should not be called
        mock_ce_client.get_cost_forecast.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_forecast_invalid_prediction_interval(
        self, mock_ce_client, future_date_range
    ):
        """Test cost forecast with invalid prediction interval."""
        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=90,  # Invalid - only 80 and 95 are valid
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid prediction_interval_level' in result['error']
        assert '80 and 95' in result['error']
        # API should not be called
        mock_ce_client.get_cost_forecast.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_forecast_invalid_metric(self, mock_ce_client, future_date_range):
        """Test cost forecast with invalid metric."""
        ctx = MagicMock()
        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='INVALID_METRIC',  # Invalid metric
            prediction_interval_level=80,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid metric' in result['error']
        assert 'Valid values for forecasting' in result['error']
        # API should not be called
        mock_ce_client.get_cost_forecast.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_forecast_filter_validation_error(
        self, mock_ce_client, future_date_range
    ):
        """Test cost forecast with filter validation error."""
        ctx = MagicMock()

        # Mock validate_expression to return an error
        with patch(
            'awslabs.cost_explorer_mcp_server.forecasting_handler.validate_expression',
            return_value={'error': 'Invalid filter'},
        ):
            result = await get_cost_forecast(
                ctx,
                future_date_range,
                granularity='MONTHLY',
                filter_expression={'invalid': 'filter'},
                metric='UNBLENDED_COST',
                prediction_interval_level=80,
            )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid filter' in result['error']
        # API should not be called
        mock_ce_client.get_cost_forecast.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_forecast_api_exception(self, mock_ce_client, future_date_range):
        """Test cost forecast with API exception."""
        ctx = MagicMock()

        # Mock the API to raise an exception
        mock_ce_client.get_cost_forecast.side_effect = Exception('API Error')

        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'API Error' in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.forecasting_handler.logger')
    async def test_get_cost_forecast_error_logging(
        self, mock_logger, mock_ce_client, future_date_range
    ):
        """Test cost forecast error logging."""
        ctx = MagicMock()

        # Mock the API to raise an exception
        error_message = 'Detailed API Error'
        mock_ce_client.get_cost_forecast.side_effect = Exception(error_message)

        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify error logging was called
        mock_logger.error.assert_called_once()
        log_call_args = mock_logger.error.call_args[0][0]
        assert 'Error calling Cost Explorer forecast API' in log_call_args
        assert error_message in log_call_args

        # Verify error response
        assert 'error' in result
        assert error_message in result['error']

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.forecasting_handler.get_cost_explorer_client')
    async def test_get_cost_forecast_client_creation_exception(self, mock_get_client, future_date_range):
        """Test cost forecast with client creation exception."""
        ctx = MagicMock()

        # Mock client creation to raise an exception
        mock_get_client.side_effect = Exception('Client creation failed')

        result = await get_cost_forecast(
            ctx,
            future_date_range,
            granularity='MONTHLY',
            filter_expression=None,
            metric='UNBLENDED_COST',
            prediction_interval_level=80,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Error generating cost forecast' in result['error']
        assert 'Client creation failed' in result['error']
