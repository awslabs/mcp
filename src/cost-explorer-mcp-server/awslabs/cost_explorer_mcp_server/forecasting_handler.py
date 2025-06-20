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

"""Cost Explorer MCP server implementation.

Forecasting tools for Cost Explorer MCP Server.
"""

import os
import sys
from awslabs.cost_explorer_mcp_server.helpers import (
    get_cost_explorer_client,
    validate_expression,
    validate_forecast_date_range,
)
from awslabs.cost_explorer_mcp_server.models import DateRange
from datetime import datetime, timedelta, timezone
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, Optional


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))


async def get_cost_forecast(
    ctx: Context,
    date_range: DateRange,
    granularity: str = Field(
        'MONTHLY',
        description='The granularity at which forecast data is aggregated. Valid values are DAILY and MONTHLY. DAILY forecasts support up to 3 months, MONTHLY forecasts support up to 12 months. If not provided, defaults to MONTHLY.',
    ),
    filter_expression: Optional[Dict[str, Any]] = Field(
        None,
        description='Filter criteria as a Python dictionary to narrow down AWS cost forecasts. Supports filtering by Dimensions (SERVICE, REGION, etc.), Tags, or CostCategories. You can use logical operators (And, Or, Not) for complex filters. Same format as get_cost_and_usage filter_expression.',
    ),
    metric: str = Field(
        'UNBLENDED_COST',
        description='The metric to forecast. Valid values are AMORTIZED_COST,BLENDED_COST, NET_AMORTIZED_COST,NET_UNBLENDED_COST,UNBLENDED_COST. Note: UsageQuantity forecasting is not supported by AWS Cost Explorer.',
    ),
    prediction_interval_level: int = Field(
        80,
        description='The confidence level for the forecast prediction interval. Valid values are 80 and 95. Higher values provide wider confidence ranges.',
    ),
) -> Dict[str, Any]:
    """Retrieve AWS cost forecasts based on historical usage patterns.

    This tool generates cost forecasts for future periods using AWS Cost Explorer's machine learning models.
    Forecasts are based on your historical usage patterns and can help with budget planning and cost optimization.

    Important granularity limits:
    - DAILY forecasts: Maximum 3 months into the future
    - MONTHLY forecasts: Maximum 12 months into the future

    Note: The forecast start date must be equal to or no later than the current date, while the end date
    must be in the future. AWS automatically uses available historical data to generate forecasts.
    Forecasts return total costs and cannot be grouped by dimensions like services or regions.

    Example: Get monthly cost forecast for EC2 services for next quarter
        await get_cost_forecast(
            ctx=context,
            date_range={
                "start_date": "2025-06-19",  # Today or earlier
                "end_date": "2025-09-30"     # Future date
            },
            granularity="MONTHLY",
            filter_expression={
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": ["Amazon Elastic Compute Cloud - Compute"],
                    "MatchOptions": ["EQUALS"]
                }
            },
            metric="UNBLENDED_COST",
            prediction_interval_level=80
        )

    Args:
        ctx: MCP context
        date_range: The forecast period dates in YYYY-MM-DD format (start_date <= today, end_date > today)
        granularity: The granularity at which forecast data is aggregated (DAILY, MONTHLY)
        filter_expression: Filter criteria as a Python dictionary
        metric: Cost metric to forecast (UNBLENDED_COST, AMORTIZED_COST, etc.)
        prediction_interval_level: Confidence level for prediction intervals (80 or 95)

    Returns:
        Dictionary containing forecast data with confidence intervals and metadata
    """
    # Initialize variables at function scope
    forecast_start = date_range.start_date
    forecast_end = date_range.end_date

    try:
        # Process inputs - simplified granularity validation
        granularity = str(granularity).upper()

        if granularity not in ['DAILY', 'MONTHLY']:
            return {
                'error': f'Invalid granularity: {granularity}. Valid values for forecasting are DAILY and MONTHLY.'
            }

        # Validate forecast date range with granularity-specific limits
        is_valid, error = validate_forecast_date_range(forecast_start, forecast_end, granularity)
        if not is_valid:
            return {'error': error}

        # Validate prediction interval level
        if prediction_interval_level not in [80, 95]:
            return {
                'error': f'Invalid prediction_interval_level: {prediction_interval_level}. Valid values are 80 and 95.'
            }

        # Define valid forecast metrics
        valid_forecast_metrics = [
            'AMORTIZED_COST',
            'BLENDED_COST',
            'NET_AMORTIZED_COST',
            'NET_UNBLENDED_COST',
            'UNBLENDED_COST',
        ]

        if metric not in valid_forecast_metrics:
            return {
                'error': f'Invalid metric: {metric}. Valid values for forecasting are {", ".join(valid_forecast_metrics)}.'
            }

        # Process filter - reuse existing validation
        filter_criteria = filter_expression

        # Validate filter expression if provided (using historical data for validation)
        if filter_criteria:
            # Use a recent historical period for filter validation
            validation_end = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            validation_start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
                '%Y-%m-%d'
            )

            validation_result = validate_expression(
                filter_criteria, validation_start, validation_end
            )
            if 'error' in validation_result:
                return validation_result

        # Prepare API call parameters
        forecast_params = {
            'TimePeriod': {
                'Start': forecast_start,
                'End': forecast_end,
            },
            'Metric': metric,
            'Granularity': granularity,
            'PredictionIntervalLevel': prediction_interval_level,
        }

        # Add filter if provided
        if filter_criteria:
            forecast_params['Filter'] = filter_criteria

        # Get forecast data
        ce = get_cost_explorer_client()

        try:
            response = ce.get_cost_forecast(**forecast_params)
        except Exception as e:
            logger.error(f'Error calling Cost Explorer forecast API: {e}')
            return {
                'error': f'AWS Cost Explorer forecast API error: {str(e)},{str(forecast_start)}'
            }

        # Process forecast results
        forecast_data = {}
        total_forecast = 0.0
        total_lower_bound = 0.0
        total_upper_bound = 0.0

        for forecast_result in response.get('ForecastResultsByTime', []):
            period_start = forecast_result['TimePeriod']['Start']

            # Extract forecast values
            mean_value = float(forecast_result['MeanValue'])
            prediction_interval = (
                forecast_result.get('PredictionIntervalLowerBound', '0'),
                forecast_result.get('PredictionIntervalUpperBound', '0'),
            )
            lower_bound = float(prediction_interval[0])
            upper_bound = float(prediction_interval[1])

            forecast_data[period_start] = {
                'predicted_cost': round(mean_value, 2),
                'confidence_range': {
                    'lower_bound': round(lower_bound, 2),
                    'upper_bound': round(upper_bound, 2),
                },
            }

            # Accumulate totals
            total_forecast += mean_value
            total_lower_bound += lower_bound
            total_upper_bound += upper_bound

        # Build response
        result = {
            'forecast_period': f'{forecast_start} to {forecast_end}',
            'granularity': granularity,
            'metric': metric,
            'confidence_level': f'{prediction_interval_level}%',
            'predictions': forecast_data,
            'total_forecast': {
                'predicted_cost': round(total_forecast, 2),
                'confidence_range': {
                    'lower_bound': round(total_lower_bound, 2),
                    'upper_bound': round(total_upper_bound, 2),
                },
            },
            'metadata': {'currency': 'USD'},
        }

        return result

    except Exception as e:
        logger.error(
            f'Error generating cost forecast for period {forecast_start} to {forecast_end}: {e}'
        )
        return {'error': f'Error generating cost forecast: {str(e)}'}
