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

"""Tests for get_cost_and_usage function."""

import pytest
from awslabs.elasticache_mcp_server.tools.ce import GetCostAndUsageRequest, get_cost_and_usage
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_ce_client():
    """Create a mock Cost Explorer client."""
    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CostExplorerConnectionManager.get_connection'
    ) as mock_get_connection:
        mock_client = MagicMock()
        mock_get_connection.return_value = mock_client
        yield mock_client


class TestGetCostAndUsage:
    """Tests for the get_cost_and_usage function."""

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_daily(self, mock_ce_client):
        """Test getting daily cost and usage data."""
        expected_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-02'},
                    'Total': {
                        'BlendedCost': {'Amount': '10.0', 'Unit': 'USD'},
                        'UnblendedCost': {'Amount': '9.5', 'Unit': 'USD'},
                        'UsageQuantity': {'Amount': '24.0', 'Unit': 'Hours'},
                    },
                    'Groups': [
                        {
                            'Keys': ['Amazon ElastiCache', 'Production'],
                            'Metrics': {
                                'BlendedCost': {'Amount': '10.0', 'Unit': 'USD'},
                                'UnblendedCost': {'Amount': '9.5', 'Unit': 'USD'},
                                'UsageQuantity': {'Amount': '24.0', 'Unit': 'Hours'},
                            },
                        }
                    ],
                }
            ]
        }
        mock_ce_client.get_cost_and_usage.return_value = expected_response

        request = GetCostAndUsageRequest(time_period='2025-01-01/2025-01-02', granularity='DAILY')

        response = await get_cost_and_usage(request)

        mock_ce_client.get_cost_and_usage.assert_called_once_with(
            TimePeriod={'Start': '2025-01-01', 'End': '2025-01-02'},
            Granularity='DAILY',
            Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'TAG', 'Key': 'Environment'},
            ],
            Filter={'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon ElastiCache']}},
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_monthly(self, mock_ce_client):
        """Test getting monthly cost and usage data."""
        expected_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-02-01'},
                    'Total': {
                        'BlendedCost': {'Amount': '300.0', 'Unit': 'USD'},
                        'UnblendedCost': {'Amount': '285.0', 'Unit': 'USD'},
                        'UsageQuantity': {'Amount': '744.0', 'Unit': 'Hours'},
                    },
                    'Groups': [
                        {
                            'Keys': ['Amazon ElastiCache', 'Production'],
                            'Metrics': {
                                'BlendedCost': {'Amount': '300.0', 'Unit': 'USD'},
                                'UnblendedCost': {'Amount': '285.0', 'Unit': 'USD'},
                                'UsageQuantity': {'Amount': '744.0', 'Unit': 'Hours'},
                            },
                        }
                    ],
                }
            ]
        }
        mock_ce_client.get_cost_and_usage.return_value = expected_response

        request = GetCostAndUsageRequest(
            time_period='2025-01-01/2025-02-01', granularity='MONTHLY'
        )

        response = await get_cost_and_usage(request)

        mock_ce_client.get_cost_and_usage.assert_called_once_with(
            TimePeriod={'Start': '2025-01-01', 'End': '2025-02-01'},
            Granularity='MONTHLY',
            Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'TAG', 'Key': 'Environment'},
            ],
            Filter={'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon ElastiCache']}},
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_hourly(self, mock_ce_client):
        """Test getting hourly cost and usage data."""
        expected_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01T00:00:00Z', 'End': '2025-01-01T01:00:00Z'},
                    'Total': {
                        'BlendedCost': {'Amount': '0.42', 'Unit': 'USD'},
                        'UnblendedCost': {'Amount': '0.40', 'Unit': 'USD'},
                        'UsageQuantity': {'Amount': '1.0', 'Unit': 'Hours'},
                    },
                    'Groups': [
                        {
                            'Keys': ['Amazon ElastiCache', 'Production'],
                            'Metrics': {
                                'BlendedCost': {'Amount': '0.42', 'Unit': 'USD'},
                                'UnblendedCost': {'Amount': '0.40', 'Unit': 'USD'},
                                'UsageQuantity': {'Amount': '1.0', 'Unit': 'Hours'},
                            },
                        }
                    ],
                }
            ]
        }
        mock_ce_client.get_cost_and_usage.return_value = expected_response

        request = GetCostAndUsageRequest(time_period='2025-01-01/2025-01-02', granularity='HOURLY')

        response = await get_cost_and_usage(request)

        mock_ce_client.get_cost_and_usage.assert_called_once_with(
            TimePeriod={'Start': '2025-01-01', 'End': '2025-01-02'},
            Granularity='HOURLY',
            Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                {'Type': 'TAG', 'Key': 'Environment'},
            ],
            Filter={'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon ElastiCache']}},
        )
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_invalid_granularity(self, mock_ce_client):
        """Test getting cost and usage data with invalid granularity."""
        exception_class = 'ValidationException'
        error_message = 'Invalid granularity: INVALID'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_ce_client.exceptions, exception_class, mock_exception)
        mock_ce_client.get_cost_and_usage.side_effect = mock_exception(error_message)

        request = GetCostAndUsageRequest(
            time_period='2025-01-01/2025-01-02', granularity='INVALID'
        )

        response = await get_cost_and_usage(request)
        assert 'error' in response
        assert error_message in response['error']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_invalid_time_period(self, mock_ce_client):
        """Test getting cost and usage data with invalid time period."""
        exception_class = 'ValidationException'
        error_message = 'Invalid time period format'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_ce_client.exceptions, exception_class, mock_exception)
        mock_ce_client.get_cost_and_usage.side_effect = mock_exception(error_message)

        request = GetCostAndUsageRequest(time_period='invalid/format', granularity='DAILY')

        response = await get_cost_and_usage(request)
        assert 'error' in response
        assert error_message in response['error']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_future_date(self, mock_ce_client):
        """Test getting cost and usage data for future dates."""
        exception_class = 'DataUnavailableException'
        error_message = 'Data not available for future dates'
        mock_exception = type(exception_class, (Exception,), {})
        setattr(mock_ce_client.exceptions, exception_class, mock_exception)
        mock_ce_client.get_cost_and_usage.side_effect = mock_exception(error_message)

        request = GetCostAndUsageRequest(time_period='2026-01-01/2026-01-02', granularity='DAILY')

        response = await get_cost_and_usage(request)
        assert 'error' in response
        assert error_message in response['error']
