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

"""Tests for cost_usage_handler module."""

import pytest
from awslabs.cost_explorer_mcp_server.cost_usage_handler import get_cost_and_usage
from awslabs.cost_explorer_mcp_server.models import DateRange
from unittest.mock import MagicMock, patch


@pytest.fixture
def valid_date_range():
    """Valid date range for testing."""
    return DateRange(start_date='2025-01-01', end_date='2025-01-31')


@pytest.fixture
def mock_ce_client():
    """Mock Cost Explorer client."""
    with patch(
        'awslabs.cost_explorer_mcp_server.cost_usage_handler.get_cost_explorer_client'
    ) as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestCostAndUsage:
    """Test cost and usage functionality."""

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_missing_amount(self, mock_ce_client, valid_date_range):
        """Test cost and usage with missing Amount in metric data."""
        # Setup mock response with missing Amount
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Unit': 'USD'}},  # Missing Amount
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert "'Amount' not found in metric data" in result['error']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_missing_unit(self, mock_ce_client, valid_date_range):
        """Test cost and usage with missing Unit in metric data."""
        # Setup mock response with missing Unit
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UsageQuantity': {'Amount': '100.00'}},  # Missing Unit
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UsageQuantity',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify result - should handle missing Unit gracefully
        assert isinstance(result, dict)
        assert 'GroupedUsage' in result
        # Should use 'Unknown' as the default unit
        assert (
            result['GroupedUsage']['2025-01-01']['Amazon Elastic Compute Cloud - Compute']['unit']
            == 'Unknown'
        )

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_monthly(self, mock_ce_client, valid_date_range):
        """Test cost and usage with monthly granularity."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Total': {'UnblendedCost': {'Amount': '100.00', 'Unit': 'USD'}},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                        },
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {'UnblendedCost': {'Amount': '40.00', 'Unit': 'USD'}},
                        },
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UnblendedCost',
                    group_by='SERVICE',  # Explicitly pass this to avoid Field object
                    filter_expression=None,  # Explicitly pass None
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_daily(self, mock_ce_client, valid_date_range):
        """Test cost and usage with daily granularity."""
        # Setup mock response with multiple days
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-02'},
                    'Total': {'UnblendedCost': {'Amount': '10.00', 'Unit': 'USD'}},
                    'Groups': [],
                },
                {
                    'TimePeriod': {'Start': '2025-01-02', 'End': '2025-01-03'},
                    'Total': {'UnblendedCost': {'Amount': '12.00', 'Unit': 'USD'}},
                    'Groups': [],
                },
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='DAILY',
                    metric='UnblendedCost',
                    group_by='SERVICE',  # Explicitly pass this to avoid Field object
                    filter_expression=None,  # Explicitly pass None
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result
        # For daily data with no groups, we expect either empty GroupedCosts or a message
        assert 'GroupedCosts' in result or 'message' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_filter(self, mock_ce_client, valid_date_range):
        """Test cost and usage with service filter."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Total': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                    'Groups': [],
                }
            ]
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
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value=filter_expr,
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    filter_expression=filter_expr,
                    metric='UnblendedCost',
                    group_by='SERVICE',  # Explicitly pass this to avoid Field object
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_group_by(self, mock_ce_client, valid_date_range):
        """Test cost and usage with group by parameter."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Total': {'UnblendedCost': {'Amount': '100.00', 'Unit': 'USD'}},
                    'Groups': [
                        {
                            'Keys': ['us-east-1'],
                            'Metrics': {'UnblendedCost': {'Amount': '70.00', 'Unit': 'USD'}},
                        },
                        {
                            'Keys': ['us-west-2'],
                            'Metrics': {'UnblendedCost': {'Amount': '30.00', 'Unit': 'USD'}},
                        },
                    ],
                }
            ]
        }

        # Create group_by parameter
        group_by = {'Type': 'DIMENSION', 'Key': 'REGION'}

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
            return_value=group_by,
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    group_by=group_by,
                    metric='UnblendedCost',
                    filter_expression=None,  # Explicitly pass None
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_metrics(self, mock_ce_client, valid_date_range):
        """Test cost and usage with different metrics."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Total': {'UsageQuantity': {'Amount': '720', 'Unit': 'Hours'}},
                    'Groups': [],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UsageQuantity',
                    group_by='SERVICE',  # Explicitly pass this to avoid Field object
                    filter_expression=None,  # Explicitly pass None
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_dataframe_processing(self, mock_ce_client, valid_date_range):
        """Test cost and usage with DataFrame processing."""
        # Setup mock response with multiple dates for DataFrame processing
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-02'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '20.00', 'Unit': 'USD'}},
                        },
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {'UnblendedCost': {'Amount': '10.00', 'Unit': 'USD'}},
                        },
                    ],
                },
                {
                    'TimePeriod': {'Start': '2025-01-02', 'End': '2025-01-03'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '25.00', 'Unit': 'USD'}},
                        },
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {'UnblendedCost': {'Amount': '15.00', 'Unit': 'USD'}},
                        },
                    ],
                },
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='DAILY',
                    metric='UnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify result structure
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

        # Verify DataFrame processing
        grouped_costs = result['GroupedCosts']

        # Check dates
        assert '2025-01-01' in grouped_costs
        assert '2025-01-02' in grouped_costs

        # Check services in date entries
        assert 'Amazon Elastic Compute Cloud - Compute' in grouped_costs['2025-01-01']
        assert 'Amazon Simple Storage Service' in grouped_costs['2025-01-01']

        # Check values
        assert grouped_costs['2025-01-01']['Amazon Elastic Compute Cloud - Compute'] == 20.0
        assert grouped_costs['2025-01-01']['Amazon Simple Storage Service'] == 10.0
        assert grouped_costs['2025-01-02']['Amazon Elastic Compute Cloud - Compute'] == 25.0
        assert grouped_costs['2025-01-02']['Amazon Simple Storage Service'] == 15.0

        # Check totals
        assert 'Service Total' in grouped_costs
        assert grouped_costs['Service Total']['Amazon Elastic Compute Cloud - Compute'] == 45.0
        assert grouped_costs['Service Total']['Amazon Simple Storage Service'] == 25.0

        # Check row totals
        assert 'Total UnblendedCost' in grouped_costs['2025-01-01']
        assert grouped_costs['2025-01-01']['Total UnblendedCost'] == 30.0
        assert grouped_costs['2025-01-02']['Total UnblendedCost'] == 40.0

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_dataframe_error(self, mock_ce_client, valid_date_range):
        """Test cost and usage with DataFrame processing error."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                # Patch pandas DataFrame to raise an exception
                with patch('pandas.DataFrame.from_dict', side_effect=Exception('DataFrame error')):
                    result = await get_cost_and_usage(
                        ctx,
                        valid_date_range,
                        granularity='MONTHLY',
                        metric='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'DataFrame error' in result['error']
        # Should include raw data in the error response
        assert 'raw_data' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_api_error(self, mock_ce_client, valid_date_range):
        """Test cost and usage with API error."""
        # Setup mock error
        mock_ce_client.get_cost_and_usage.side_effect = Exception('API Error')

        ctx = MagicMock()
        result = await get_cost_and_usage(
            ctx,
            valid_date_range,
            granularity='MONTHLY',
            metric='UnblendedCost',
            group_by='SERVICE',  # Explicitly pass this to avoid Field object
            filter_expression=None,  # Explicitly pass None
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        # Don't check exact error message, just that it contains our error
        assert 'API Error' in str(result['error'])

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_validation_error(self, mock_ce_client):
        """Test cost and usage with validation error."""
        # Use a valid date range but mock a validation error
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        ctx = MagicMock()
        # Test with invalid granularity to trigger validation error
        result = await get_cost_and_usage(
            ctx,
            valid_date_range,
            granularity='INVALID',
            metric='UnblendedCost',
            group_by='SERVICE',
            filter_expression=None,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        # API should not be called with invalid parameters
        mock_ce_client.get_cost_and_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_hourly_granularity(self, mock_ce_client):
        """Test cost and usage with hourly granularity."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-02')

        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01T00:00:00Z', 'End': '2025-01-01T01:00:00Z'},
                    'Total': {'UnblendedCost': {'Amount': '1.00', 'Unit': 'USD'}},
                    'Groups': [],
                }
            ]
        }

        ctx = MagicMock()
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='HOURLY',
                    metric='UnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()
        call_args = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_args['Granularity'] == 'HOURLY'

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_cost_metric_processing(
        self, mock_ce_client, valid_date_range
    ):
        """Test cost and usage with cost metric processing."""
        # Setup mock response for cost metrics
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                        },
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {'UnblendedCost': {'Amount': '40.00', 'Unit': 'USD'}},
                        },
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify result structure for cost metrics
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

        # Verify cost data processing
        grouped_costs = result['GroupedCosts']
        assert '2025-01-01' in grouped_costs
        assert 'Amazon Elastic Compute Cloud - Compute' in grouped_costs['2025-01-01']
        assert grouped_costs['2025-01-01']['Amazon Elastic Compute Cloud - Compute'] == 60.0
        assert grouped_costs['2025-01-01']['Amazon Simple Storage Service'] == 40.0

        # Verify totals are calculated
        assert 'Service Total' in grouped_costs
        assert grouped_costs['Service Total']['Amazon Elastic Compute Cloud - Compute'] == 60.0
        assert grouped_costs['Service Total']['Amazon Simple Storage Service'] == 40.0

        # Verify row totals
        assert 'Total UnblendedCost' in grouped_costs['2025-01-01']
        assert grouped_costs['2025-01-01']['Total UnblendedCost'] == 100.0

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_usage_metric_processing(
        self, mock_ce_client, valid_date_range
    ):
        """Test cost and usage with usage metric processing."""
        # Setup mock response for usage metrics
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['BoxUsage:t2.micro'],
                            'Metrics': {'UsageQuantity': {'Amount': '720.00', 'Unit': 'Hours'}},
                        },
                        {
                            'Keys': ['BoxUsage:t2.small'],
                            'Metrics': {'UsageQuantity': {'Amount': '360.00', 'Unit': 'Hours'}},
                        },
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UsageQuantity',
                    group_by='USAGE_TYPE',
                    filter_expression=None,
                )

        # Verify result structure for usage metrics
        assert isinstance(result, dict)
        assert 'GroupedUsage' in result
        assert 'metadata' in result

        # Verify usage data processing
        grouped_usage = result['GroupedUsage']
        assert '2025-01-01' in grouped_usage
        assert 'BoxUsage:t2.micro' in grouped_usage['2025-01-01']
        assert grouped_usage['2025-01-01']['BoxUsage:t2.micro']['amount'] == 720.0
        assert grouped_usage['2025-01-01']['BoxUsage:t2.micro']['unit'] == 'Hours'
        assert grouped_usage['2025-01-01']['BoxUsage:t2.small']['amount'] == 360.0
        assert grouped_usage['2025-01-01']['BoxUsage:t2.small']['unit'] == 'Hours'

        # Verify metadata
        assert result['metadata']['metric'] == 'UsageQuantity'
        assert result['metadata']['grouped_by'] == 'USAGE_TYPE'

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_usage_quantity(self, mock_ce_client):
        """Test cost and usage with UsageQuantity metric."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-02-01'},
                    'Total': {'UsageQuantity': {'Amount': '100', 'Unit': 'Hours'}},
                    'Groups': [],
                }
            ]
        }

        ctx = MagicMock()
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UsageQuantity',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()
        call_args = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_args['Metrics'] == ['UsageQuantity']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_empty_results(self, mock_ce_client):
        """Test cost and usage with empty results."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        # Setup mock response with empty results
        mock_ce_client.get_cost_and_usage.return_value = {'ResultsByTime': []}

        ctx = MagicMock()
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify result structure
        assert isinstance(result, dict)
        # Should handle empty results gracefully
        assert 'message' in result or 'GroupedCosts' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_invalid_metric(self, mock_ce_client):
        """Test cost and usage with invalid metric."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        ctx = MagicMock()
        result = await get_cost_and_usage(
            ctx,
            valid_date_range,
            granularity='MONTHLY',
            metric='INVALID_METRIC',  # Invalid metric
            group_by='SERVICE',
            filter_expression=None,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        # API should not be called with invalid parameters
        mock_ce_client.get_cost_and_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_date_validation_error(self, mock_ce_client):
        """Test cost and usage with date validation error."""
        # Use a valid DateRange but test hourly granularity with too long range
        long_date_range = DateRange(start_date='2025-01-01', end_date='2025-02-01')

        ctx = MagicMock()
        result = await get_cost_and_usage(
            ctx,
            long_date_range,
            granularity='HOURLY',  # This should fail validation for long range
            metric='UnblendedCost',
            group_by='SERVICE',
            filter_expression=None,
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        # API should not be called with invalid parameters
        mock_ce_client.get_cost_and_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_group_by_validation_error(self, mock_ce_client):
        """Test cost and usage with group_by validation error."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        ctx = MagicMock()
        # Patch validation to return error
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
            return_value={'error': 'Invalid group_by'},
        ):
            result = await get_cost_and_usage(
                ctx,
                valid_date_range,
                granularity='MONTHLY',
                metric='UnblendedCost',
                group_by='INVALID',
                filter_expression=None,
            )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid group_by' in result['error']
        # API should not be called
        mock_ce_client.get_cost_and_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_filter_validation_error(self, mock_ce_client):
        """Test cost and usage with filter validation error."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        ctx = MagicMock()
        # Patch validation to return error
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={'error': 'Invalid filter'},
        ):
            result = await get_cost_and_usage(
                ctx,
                valid_date_range,
                granularity='MONTHLY',
                metric='UnblendedCost',
                group_by='SERVICE',
                filter_expression={'invalid': 'filter'},
            )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid filter' in result['error']
        # API should not be called
        mock_ce_client.get_cost_and_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_net_costs(self, mock_ce_client):
        """Test cost and usage with Net cost metrics."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-02-01'},
                    'Total': {'NetUnblendedCost': {'Amount': '80.00', 'Unit': 'USD'}},
                    'Groups': [],
                }
            ]
        }

        ctx = MagicMock()
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='NetUnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()
        call_args = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_args['Metrics'] == ['NetUnblendedCost']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_amortized_cost(self, mock_ce_client):
        """Test cost and usage with AmortizedCost metric."""
        valid_date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')

        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-02-01'},
                    'Total': {'AmortizedCost': {'Amount': '1000', 'Unit': 'USD'}},
                    'Groups': [],
                }
            ]
        }

        ctx = MagicMock()
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='AmortizedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify API call parameters
        mock_ce_client.get_cost_and_usage.assert_called_once()
        call_args = mock_ce_client.get_cost_and_usage.call_args[1]
        assert call_args['Metrics'] == ['AmortizedCost']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_json_serialization(self, mock_ce_client, valid_date_range):
        """Test cost and usage with successful JSON serialization."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                # Test successful JSON serialization
                with patch('json.dumps', return_value='{"test": "value"}'):
                    result = await get_cost_and_usage(
                        ctx,
                        valid_date_range,
                        granularity='MONTHLY',
                        metric='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify result structure
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_json_serialization_failure(
        self, mock_ce_client, valid_date_range
    ):
        """Test cost and usage with JSON serialization failure."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                # Test JSON serialization failure
                with patch('json.dumps', side_effect=TypeError('Cannot serialize')):
                    result = await get_cost_and_usage(
                        ctx,
                        valid_date_range,
                        granularity='MONTHLY',
                        metric='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify result structure - should still return a result after stringifying keys
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_missing_metric_in_response(
        self, mock_ce_client, valid_date_range
    ):
        """Test cost and usage with missing metric in response."""
        # Setup mock response with missing metric
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {
                                'BlendedCost': {'Amount': '60.00', 'Unit': 'USD'}
                            },  # Different metric than requested
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UnblendedCost',  # Request UnblendedCost but response has BlendedCost
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'not found in response' in result['error']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_metric_data_processing_error(
        self, mock_ce_client, valid_date_range
    ):
        """Test cost and usage with metric data processing error."""
        # Setup mock response with invalid Amount
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {
                                'UnblendedCost': {'Amount': 'not-a-number', 'Unit': 'USD'}
                            },  # Invalid amount
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Error processing metric data' in result['error']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_empty_keys(self, mock_ce_client, valid_date_range):
        """Test cost and usage with empty keys in group."""
        # Setup mock response with empty keys
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': [],  # Empty keys
                            'Metrics': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                result = await get_cost_and_usage(
                    ctx,
                    valid_date_range,
                    granularity='MONTHLY',
                    metric='UnblendedCost',
                    group_by='SERVICE',
                    filter_expression=None,
                )

        # Verify result - should handle empty keys gracefully
        assert isinstance(result, dict)
        # Should return empty GroupedCosts or a message
        assert 'GroupedCosts' in result or 'message' in result

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_json_serialization_fallback(
        self, mock_ce_client, valid_date_range
    ):
        """Test cost and usage with JSON serialization fallback to stringify_keys."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '60.00', 'Unit': 'USD'}},
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.cost_usage_handler.validate_group_by',
                return_value={},
            ):
                # Force JSON serialization to fail, which should trigger stringify_keys
                with patch('json.dumps', side_effect=TypeError('Cannot serialize')):
                    result = await get_cost_and_usage(
                        ctx,
                        valid_date_range,
                        granularity='MONTHLY',
                        metric='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify that the function handled the serialization issue gracefully
        assert isinstance(result, dict)
        assert 'GroupedCosts' in result
        # The result should still be valid even after stringify_keys processing
        grouped_costs = result['GroupedCosts']
        assert '2025-01-01' in grouped_costs
        assert 'Amazon Elastic Compute Cloud - Compute' in grouped_costs['2025-01-01']

    @pytest.mark.asyncio
    async def test_get_cost_and_usage_with_string_group_by(self, mock_ce_client, valid_date_range):
        """Test cost and usage with string group_by conversion."""
        # Setup mock response
        mock_ce_client.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-01-01', 'End': '2025-01-31'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '100.00', 'Unit': 'USD'}},
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        result = await get_cost_and_usage(
            ctx,
            valid_date_range,
            granularity='MONTHLY',
            metric='UnblendedCost',
            group_by='SERVICE',  # String instead of dict
            filter_expression=None,
        )

        # Verify successful response
        assert 'GroupedCosts' in result
        assert len(result['GroupedCosts']) > 0

        # Verify API call parameters - should convert string to dict
        mock_ce_client.get_cost_and_usage.assert_called_once()
        call_args = mock_ce_client.get_cost_and_usage.call_args[1]
        assert 'GroupBy' in call_args
        assert call_args['GroupBy'][0]['Type'] == 'DIMENSION'
        assert call_args['GroupBy'][0]['Key'] == 'SERVICE'
