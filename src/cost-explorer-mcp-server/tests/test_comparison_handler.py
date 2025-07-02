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

"""Tests for comparison_handler module."""

import pytest
from awslabs.cost_explorer_mcp_server.comparison_handler import (
    get_cost_and_usage_comparisons,
    get_cost_comparison_drivers,
)
from awslabs.cost_explorer_mcp_server.models import DateRange
from unittest.mock import MagicMock, patch


@pytest.fixture
def valid_baseline_range():
    """Valid baseline date range."""
    return DateRange(start_date='2025-01-01', end_date='2025-02-01')


@pytest.fixture
def valid_comparison_range():
    """Valid comparison date range."""
    return DateRange(start_date='2025-02-01', end_date='2025-03-01')


@pytest.fixture
def mock_ce_client():
    """Mock Cost Explorer client."""
    with patch(
        'awslabs.cost_explorer_mcp_server.comparison_handler.get_cost_explorer_client'
    ) as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


class TestCostComparisons:
    """Test cost comparison functionality."""

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_with_tag_selector(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with tag selector."""
        # Mock responses for the comparison API with tag selector
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {
                        'Tags': {'Key': 'Environment', 'Values': ['Production']}
                    },
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '75.00',
                            'ComparisonTimePeriodAmount': '100.00',
                            'Difference': '25.00',
                            'Unit': 'USD',
                        }
                    },
                }
            ],
            'TotalCostAndUsage': {
                'UnblendedCost': {
                    'BaselineTimePeriodAmount': '75.00',
                    'ComparisonTimePeriodAmount': '100.00',
                    'Difference': '25.00',
                    'Unit': 'USD',
                }
            },
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'TAG', 'Key': 'Environment'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by={'Type': 'TAG', 'Key': 'Environment'},
                        filter_expression=None,
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'comparisons' in result

        # Verify tag-based group key format
        assert 'Environment:Production' in result['comparisons']
        assert result['comparisons']['Environment:Production']['baseline_value'] == 75.0
        assert result['comparisons']['Environment:Production']['comparison_value'] == 100.0
        assert result['comparisons']['Environment:Production']['absolute_change'] == 25.0
        assert result['comparisons']['Environment:Production']['percentage_change'] == 33.33

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_with_pagination(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with pagination."""
        # Mock first page response with NextPageToken
        mock_ce_client.get_cost_and_usage_comparisons.side_effect = [
            {
                'CostAndUsageComparisons': [
                    {
                        'CostAndUsageSelector': {'Dimensions': {'Values': ['EC2']}},
                        'Metrics': {
                            'UnblendedCost': {
                                'BaselineTimePeriodAmount': '60.00',
                                'ComparisonTimePeriodAmount': '90.00',
                                'Difference': '30.00',
                                'Unit': 'USD',
                            }
                        },
                    }
                ],
                'NextPageToken': 'NEXT_PAGE_TOKEN',
                'TotalCostAndUsage': {
                    'UnblendedCost': {
                        'BaselineTimePeriodAmount': '60.00',
                        'ComparisonTimePeriodAmount': '90.00',
                        'Difference': '30.00',
                        'Unit': 'USD',
                    }
                },
            },
            {
                'CostAndUsageComparisons': [
                    {
                        'CostAndUsageSelector': {'Dimensions': {'Values': ['S3']}},
                        'Metrics': {
                            'UnblendedCost': {
                                'BaselineTimePeriodAmount': '40.00',
                                'ComparisonTimePeriodAmount': '60.00',
                                'Difference': '20.00',
                                'Unit': 'USD',
                            }
                        },
                    }
                ],
                'TotalCostAndUsage': {
                    'UnblendedCost': {
                        'BaselineTimePeriodAmount': '100.00',
                        'ComparisonTimePeriodAmount': '150.00',
                        'Difference': '50.00',
                        'Unit': 'USD',
                    }
                },
            },
        ]

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify API calls - should be called twice due to pagination
        assert mock_ce_client.get_cost_and_usage_comparisons.call_count == 2

        # Verify the second call includes the NextPageToken
        second_call_args = mock_ce_client.get_cost_and_usage_comparisons.call_args_list[1][1]
        assert 'NextPageToken' in second_call_args
        assert second_call_args['NextPageToken'] == 'NEXT_PAGE_TOKEN'

        # Verify result structure combines both pages
        assert isinstance(result, dict)
        assert 'comparisons' in result
        assert len(result['comparisons']) == 2

        # Verify both services from different pages are included
        assert 'EC2' in result['comparisons']
        assert 'S3' in result['comparisons']

        # Verify the total values from the second page (which has the final totals)
        assert result['total_comparison']['baseline_value'] == 100.0
        assert result['total_comparison']['comparison_value'] == 150.0
        assert result['total_comparison']['absolute_change'] == 50.0
        assert result['total_comparison']['percentage_change'] == 50.0

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_with_cost_category_selector(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with cost category selector."""
        # Mock responses for the comparison API with cost category selector
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {
                        'CostCategories': {'Key': 'Department', 'Values': ['Engineering']}
                    },
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '120.00',
                            'ComparisonTimePeriodAmount': '150.00',
                            'Difference': '30.00',
                            'Unit': 'USD',
                        }
                    },
                }
            ],
            'TotalCostAndUsage': {
                'UnblendedCost': {
                    'BaselineTimePeriodAmount': '120.00',
                    'ComparisonTimePeriodAmount': '150.00',
                    'Difference': '30.00',
                    'Unit': 'USD',
                }
            },
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'COST_CATEGORY', 'Key': 'Department'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by={'Type': 'COST_CATEGORY', 'Key': 'Department'},
                        filter_expression=None,
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'comparisons' in result

        # Verify cost category-based group key format
        assert 'Department:Engineering' in result['comparisons']
        assert result['comparisons']['Department:Engineering']['baseline_value'] == 120.0
        assert result['comparisons']['Department:Engineering']['comparison_value'] == 150.0
        assert result['comparisons']['Department:Engineering']['absolute_change'] == 30.0
        assert result['comparisons']['Department:Engineering']['percentage_change'] == 25.0

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_basic(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test basic cost comparison."""
        # Mock responses for the comparison API
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['Total']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '100.00',
                            'ComparisonTimePeriodAmount': '150.00',
                            'Difference': '50.00',
                            'Unit': 'USD',
                        }
                    },
                }
            ],
            'TotalCostAndUsage': {
                'UnblendedCost': {
                    'BaselineTimePeriodAmount': '100.00',
                    'ComparisonTimePeriodAmount': '150.00',
                    'Difference': '50.00',
                    'Unit': 'USD',
                }
            },
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        filter_expression=None,
                        group_by='SERVICE',
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'baseline_period' in result
        assert 'comparison_period' in result
        assert 'total_comparison' in result

        # Verify the total values
        assert result['total_comparison']['baseline_value'] == 100.0
        assert result['total_comparison']['comparison_value'] == 150.0
        assert result['total_comparison']['absolute_change'] == 50.0
        assert result['total_comparison']['percentage_change'] == 50.0

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_with_groups(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with service groups."""
        # Mock responses for the comparison API with service groups
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['EC2']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '60.00',
                            'ComparisonTimePeriodAmount': '90.00',
                            'Difference': '30.00',
                            'Unit': 'USD',
                        }
                    },
                },
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['S3']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '40.00',
                            'ComparisonTimePeriodAmount': '60.00',
                            'Difference': '20.00',
                            'Unit': 'USD',
                        }
                    },
                },
            ],
            'TotalCostAndUsage': {
                'UnblendedCost': {
                    'BaselineTimePeriodAmount': '100.00',
                    'ComparisonTimePeriodAmount': '150.00',
                    'Difference': '50.00',
                    'Unit': 'USD',
                }
            },
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'comparisons' in result
        assert len(result['comparisons']) == 2

        # Verify service calculations
        assert 'EC2' in result['comparisons']
        assert 'S3' in result['comparisons']

        assert result['comparisons']['EC2']['baseline_value'] == 60.0
        assert result['comparisons']['EC2']['comparison_value'] == 90.0
        assert result['comparisons']['EC2']['absolute_change'] == 30.0
        assert result['comparisons']['EC2']['percentage_change'] == 50.0

        assert result['comparisons']['S3']['baseline_value'] == 40.0
        assert result['comparisons']['S3']['comparison_value'] == 60.0
        assert result['comparisons']['S3']['absolute_change'] == 20.0
        assert result['comparisons']['S3']['percentage_change'] == 50.0

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_with_filter(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with filter."""
        # Mock responses for the comparison API with filter
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['EC2']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '60.00',
                            'ComparisonTimePeriodAmount': '90.00',
                            'Difference': '30.00',
                            'Unit': 'USD',
                        }
                    },
                }
            ],
            'TotalCostAndUsage': {
                'UnblendedCost': {
                    'BaselineTimePeriodAmount': '60.00',
                    'ComparisonTimePeriodAmount': '90.00',
                    'Difference': '30.00',
                    'Unit': 'USD',
                }
            },
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
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value=filter_expr,
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        filter_expression=filter_expr,
                        group_by='SERVICE',
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify filter was passed to API call
        call_args = mock_ce_client.get_cost_and_usage_comparisons.call_args[1]
        assert 'Filter' in call_args
        assert call_args['Filter'] == filter_expr

        # Verify result structure
        assert isinstance(result, dict)
        assert 'total_comparison' in result
        assert result['total_comparison']['baseline_value'] == 60.0
        assert result['total_comparison']['comparison_value'] == 90.0

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_api_error(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with API error."""
        # Setup mock error
        mock_ce_client.get_cost_and_usage_comparisons.side_effect = Exception('API Error')

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'API Error' in result['error']

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_invalid_metric(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with invalid metric."""
        ctx = MagicMock()
        # Patch only the date validation to pass, let the metric validation run
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
            return_value=(True, ''),
        ):
            result = await get_cost_and_usage_comparisons(
                ctx,
                valid_baseline_range,
                valid_comparison_range,
                metric_for_comparison='InvalidMetric',  # Invalid metric
                group_by='SERVICE',
                filter_expression=None,
            )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Invalid metric_for_comparison' in result['error']
        # API should not be called with invalid parameters
        mock_ce_client.get_cost_and_usage_comparisons.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_validation_error(self, mock_ce_client):
        """Test cost comparison with validation error."""
        # Create invalid date ranges
        invalid_baseline = DateRange(start_date='2025-01-15', end_date='2025-02-15')
        invalid_comparison = DateRange(start_date='2025-02-15', end_date='2025-03-15')

        ctx = MagicMock()
        result = await get_cost_and_usage_comparisons(
            ctx, invalid_baseline, invalid_comparison, metric_for_comparison='UnblendedCost'
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        # API should not be called with invalid parameters
        mock_ce_client.get_cost_and_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_with_zero_baseline(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with zero baseline amount."""
        # Mock responses for the comparison API with zero baseline
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['NewService']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '0.00',
                            'ComparisonTimePeriodAmount': '50.00',
                            'Difference': '50.00',
                            'Unit': 'USD',
                        }
                    },
                }
            ],
            'TotalCostAndUsage': {
                'UnblendedCost': {
                    'BaselineTimePeriodAmount': '0.00',
                    'ComparisonTimePeriodAmount': '50.00',
                    'Difference': '50.00',
                    'Unit': 'USD',
                }
            },
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'comparisons' in result

        # Verify zero baseline handling
        assert 'NewService' in result['comparisons']
        assert result['comparisons']['NewService']['baseline_value'] == 0.0
        assert result['comparisons']['NewService']['comparison_value'] == 50.0
        assert result['comparisons']['NewService']['absolute_change'] == 50.0
        # When baseline is zero and comparison is positive, percentage should be 100%
        assert result['comparisons']['NewService']['percentage_change'] == 100.0

        # Verify total calculations with zero baseline
        assert result['total_comparison']['baseline_value'] == 0.0
        assert result['total_comparison']['comparison_value'] == 50.0
        assert result['total_comparison']['absolute_change'] == 50.0
        assert result['total_comparison']['percentage_change'] == 100.0

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_without_total_cost_and_usage(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison without TotalCostAndUsage in response."""
        # Mock responses for the comparison API without TotalCostAndUsage
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['EC2']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '60.00',
                            'ComparisonTimePeriodAmount': '90.00',
                            'Difference': '30.00',
                            'Unit': 'USD',
                        }
                    },
                },
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['S3']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '40.00',
                            'ComparisonTimePeriodAmount': '60.00',
                            'Difference': '20.00',
                            'Unit': 'USD',
                        }
                    },
                },
            ]
            # No TotalCostAndUsage key in response
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'comparisons' in result
        assert 'total_comparison' in result

        # Verify total calculations are derived from grouped data
        assert result['total_comparison']['baseline_value'] == 100.0  # 60 + 40
        assert result['total_comparison']['comparison_value'] == 150.0  # 90 + 60
        assert result['total_comparison']['absolute_change'] == 50.0  # 30 + 20
        assert result['total_comparison']['percentage_change'] == 50.0  # (50/100) * 100

        # Verify individual service data
        assert result['comparisons']['EC2']['baseline_value'] == 60.0
        assert result['comparisons']['S3']['baseline_value'] == 40.0

    @pytest.mark.asyncio
    async def test_get_cost_comparisons_with_zero_comparison(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost comparison with zero comparison amount."""
        # Mock responses for the comparison API with zero comparison
        mock_ce_client.get_cost_and_usage_comparisons.return_value = {
            'CostAndUsageComparisons': [
                {
                    'CostAndUsageSelector': {'Dimensions': {'Values': ['DeprecatedService']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '50.00',
                            'ComparisonTimePeriodAmount': '0.00',
                            'Difference': '-50.00',
                            'Unit': 'USD',
                        }
                    },
                }
            ],
            'TotalCostAndUsage': {
                'UnblendedCost': {
                    'BaselineTimePeriodAmount': '50.00',
                    'ComparisonTimePeriodAmount': '0.00',
                    'Difference': '-50.00',
                    'Unit': 'USD',
                }
            },
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_and_usage_comparisons(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        group_by='SERVICE',
                        filter_expression=None,
                    )

        # Verify API calls
        mock_ce_client.get_cost_and_usage_comparisons.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'comparisons' in result

        # Verify zero comparison handling
        assert 'DeprecatedService' in result['comparisons']
        assert result['comparisons']['DeprecatedService']['baseline_value'] == 50.0
        assert result['comparisons']['DeprecatedService']['comparison_value'] == 0.0
        assert result['comparisons']['DeprecatedService']['absolute_change'] == -50.0
        assert result['comparisons']['DeprecatedService']['percentage_change'] == -100.0


class TestCostDrivers:
    """Test cost driver analysis."""

    @pytest.mark.asyncio
    async def test_get_cost_drivers_with_tag_selector(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost driver analysis with tag selector."""
        # Mock response for cost drivers with tag selector
        mock_ce_client.get_cost_comparison_drivers.return_value = {
            'CostComparisonDrivers': [
                {
                    'CostSelector': {'Tags': {'Key': 'Environment', 'Values': ['Production']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '75.00',
                            'ComparisonTimePeriodAmount': '100.00',
                            'Difference': '25.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [
                        {
                            'Type': 'USAGE',
                            'Name': 'Increased EC2 usage',
                            'Metrics': {
                                'UnblendedCost': {
                                    'BaselineTimePeriodAmount': '50.00',
                                    'ComparisonTimePeriodAmount': '75.00',
                                    'Difference': '25.00',
                                    'Unit': 'USD',
                                },
                                'UsageQuantity': {
                                    'BaselineTimePeriodAmount': '100.00',
                                    'ComparisonTimePeriodAmount': '150.00',
                                    'Difference': '50.00',
                                    'Unit': 'Hours',
                                },
                            },
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation and helper functions
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'TAG', 'Key': 'Environment'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    with patch(
                        'awslabs.cost_explorer_mcp_server.comparison_handler.extract_group_key_from_complex_selector',
                        return_value='Production',
                    ):
                        with patch(
                            'awslabs.cost_explorer_mcp_server.comparison_handler.extract_usage_context_from_selector',
                            return_value={'tag': 'Environment:Production'},
                        ):
                            with patch(
                                'awslabs.cost_explorer_mcp_server.comparison_handler.create_detailed_group_key',
                                return_value='Environment:Production',
                            ):
                                result = await get_cost_comparison_drivers(
                                    ctx,
                                    valid_baseline_range,
                                    valid_comparison_range,
                                    metric_for_comparison='UnblendedCost',
                                    group_by={'Type': 'TAG', 'Key': 'Environment'},
                                    filter_expression=None,
                                )

        # Verify API call
        mock_ce_client.get_cost_comparison_drivers.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'driver_analysis' in result
        assert 'Environment:Production' in result['driver_analysis']

        # Verify driver data
        driver_data = result['driver_analysis']['Environment:Production']
        assert driver_data['baseline_value'] == 75.0
        assert driver_data['comparison_value'] == 100.0
        assert driver_data['absolute_change'] == 25.0
        assert driver_data['percentage_change'] == 33.33

        # Verify cost drivers
        assert len(driver_data['cost_drivers']) == 1
        assert driver_data['cost_drivers'][0]['type'] == 'USAGE'
        assert driver_data['cost_drivers'][0]['name'] == 'Increased EC2 usage'

        # Verify additional metrics
        assert 'UsageQuantity' in driver_data['cost_drivers'][0]['additional_metrics']
        usage_metric = driver_data['cost_drivers'][0]['additional_metrics']['UsageQuantity']
        assert usage_metric['baseline_value'] == 100.0
        assert usage_metric['comparison_value'] == 150.0
        assert usage_metric['absolute_change'] == 50.0
        assert usage_metric['percentage_change'] == 50.0
        assert usage_metric['unit'] == 'Hours'

    @pytest.mark.asyncio
    async def test_get_cost_drivers_with_cost_category_selector(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost driver analysis with cost category selector."""
        # Mock response for cost drivers with cost category selector
        mock_ce_client.get_cost_comparison_drivers.return_value = {
            'CostComparisonDrivers': [
                {
                    'CostSelector': {
                        'CostCategories': {'Key': 'Department', 'Values': ['Engineering']}
                    },
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '120.00',
                            'ComparisonTimePeriodAmount': '150.00',
                            'Difference': '30.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation and helper functions
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'COST_CATEGORY', 'Key': 'Department'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    with patch(
                        'awslabs.cost_explorer_mcp_server.comparison_handler.extract_group_key_from_complex_selector',
                        return_value='Engineering',
                    ):
                        with patch(
                            'awslabs.cost_explorer_mcp_server.comparison_handler.extract_usage_context_from_selector',
                            return_value={'cost_category': 'Department:Engineering'},
                        ):
                            with patch(
                                'awslabs.cost_explorer_mcp_server.comparison_handler.create_detailed_group_key',
                                return_value='Department:Engineering',
                            ):
                                result = await get_cost_comparison_drivers(
                                    ctx,
                                    valid_baseline_range,
                                    valid_comparison_range,
                                    metric_for_comparison='UnblendedCost',
                                    group_by={'Type': 'COST_CATEGORY', 'Key': 'Department'},
                                    filter_expression=None,
                                )

        # Verify API call
        mock_ce_client.get_cost_comparison_drivers.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'driver_analysis' in result
        assert 'Department:Engineering' in result['driver_analysis']

        # Verify driver data
        driver_data = result['driver_analysis']['Department:Engineering']
        assert driver_data['baseline_value'] == 120.0
        assert driver_data['comparison_value'] == 150.0
        assert driver_data['absolute_change'] == 30.0
        assert driver_data['percentage_change'] == 25.0

    @pytest.mark.asyncio
    async def test_get_cost_drivers_with_zero_baseline(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost driver analysis with zero baseline."""
        # Mock response for cost drivers with zero baseline
        mock_ce_client.get_cost_comparison_drivers.return_value = {
            'CostComparisonDrivers': [
                {
                    'CostSelector': {'Dimensions': {'Values': ['NewService']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '0.00',
                            'ComparisonTimePeriodAmount': '50.00',
                            'Difference': '50.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [
                        {
                            'Type': 'NEW_SERVICE',
                            'Name': 'New service adoption',
                            'Metrics': {
                                'UnblendedCost': {
                                    'BaselineTimePeriodAmount': '0.00',
                                    'ComparisonTimePeriodAmount': '50.00',
                                    'Difference': '50.00',
                                    'Unit': 'USD',
                                }
                            },
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation and helper functions
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    with patch(
                        'awslabs.cost_explorer_mcp_server.comparison_handler.extract_group_key_from_complex_selector',
                        return_value='NewService',
                    ):
                        with patch(
                            'awslabs.cost_explorer_mcp_server.comparison_handler.extract_usage_context_from_selector',
                            return_value={'service': 'NewService'},
                        ):
                            with patch(
                                'awslabs.cost_explorer_mcp_server.comparison_handler.create_detailed_group_key',
                                return_value='NewService',
                            ):
                                result = await get_cost_comparison_drivers(
                                    ctx,
                                    valid_baseline_range,
                                    valid_comparison_range,
                                    metric_for_comparison='UnblendedCost',
                                    group_by='SERVICE',
                                    filter_expression=None,
                                )

        # Verify API call
        mock_ce_client.get_cost_comparison_drivers.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'driver_analysis' in result
        assert 'NewService' in result['driver_analysis']

        # Verify driver data with zero baseline
        driver_data = result['driver_analysis']['NewService']
        assert driver_data['baseline_value'] == 0.0
        assert driver_data['comparison_value'] == 50.0
        assert driver_data['absolute_change'] == 50.0
        # When baseline is zero and comparison is positive, percentage should be 100%
        assert driver_data['percentage_change'] == 100.0

        # Verify cost driver with zero baseline
        assert len(driver_data['cost_drivers']) == 1
        assert driver_data['cost_drivers'][0]['baseline_value'] == 0.0
        assert driver_data['cost_drivers'][0]['comparison_value'] == 50.0
        assert driver_data['cost_drivers'][0]['absolute_change'] == 50.0
        assert driver_data['cost_drivers'][0]['percentage_change'] == 100.0

    @pytest.mark.asyncio
    async def test_get_cost_drivers_basic(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test basic cost driver analysis."""
        # Mock response for cost drivers
        mock_ce_client.get_cost_comparison_drivers.return_value = {
            'CostComparisonDrivers': [
                {
                    'CostSelector': {'Dimensions': {'Values': ['EC2']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '100.00',
                            'ComparisonTimePeriodAmount': '150.00',
                            'Difference': '50.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [
                        {
                            'Description': 'Increased usage of t3.large instances',
                            'Metrics': {
                                'UnblendedCost': {
                                    'BaselineTimePeriodAmount': '50.00',
                                    'ComparisonTimePeriodAmount': '75.00',
                                    'Difference': '25.00',
                                    'Unit': 'USD',
                                }
                            },
                        }
                    ],
                }
            ]
        }

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    with patch(
                        'awslabs.cost_explorer_mcp_server.comparison_handler.extract_group_key_from_complex_selector',
                        return_value='EC2',
                    ):
                        with patch(
                            'awslabs.cost_explorer_mcp_server.comparison_handler.extract_usage_context_from_selector',
                            return_value={'service': 'EC2'},
                        ):
                            with patch(
                                'awslabs.cost_explorer_mcp_server.comparison_handler.create_detailed_group_key',
                                return_value='EC2',
                            ):
                                result = await get_cost_comparison_drivers(
                                    ctx,
                                    valid_baseline_range,
                                    valid_comparison_range,
                                    metric_for_comparison='UnblendedCost',
                                    group_by='SERVICE',
                                    filter_expression=None,
                                )

        # Verify API call
        mock_ce_client.get_cost_comparison_drivers.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'driver_analysis' in result
        assert 'baseline_period' in result
        assert 'comparison_period' in result

    @pytest.mark.asyncio
    async def test_get_cost_drivers_with_pagination(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost driver analysis with pagination."""
        # Mock responses for the cost drivers API with pagination
        mock_ce_client.get_cost_comparison_drivers.side_effect = [
            {
                'CostComparisonDrivers': [
                    {
                        'CostSelector': {'Dimensions': {'Values': ['EC2']}},
                        'Metrics': {
                            'UnblendedCost': {
                                'BaselineTimePeriodAmount': '60.00',
                                'ComparisonTimePeriodAmount': '90.00',
                                'Difference': '30.00',
                                'Unit': 'USD',
                            }
                        },
                        'CostDrivers': [],
                    }
                ],
                'NextPageToken': 'NEXT_PAGE_TOKEN',
            },
            {
                'CostComparisonDrivers': [
                    {
                        'CostSelector': {'Dimensions': {'Values': ['S3']}},
                        'Metrics': {
                            'UnblendedCost': {
                                'BaselineTimePeriodAmount': '40.00',
                                'ComparisonTimePeriodAmount': '60.00',
                                'Difference': '20.00',
                                'Unit': 'USD',
                            }
                        },
                        'CostDrivers': [],
                    }
                ]
            },
        ]

        ctx = MagicMock()
        # Patch the validation and helper functions
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    with patch(
                        'awslabs.cost_explorer_mcp_server.comparison_handler.extract_group_key_from_complex_selector',
                        side_effect=['EC2', 'S3'],
                    ):
                        with patch(
                            'awslabs.cost_explorer_mcp_server.comparison_handler.extract_usage_context_from_selector',
                            side_effect=[{'service': 'EC2'}, {'service': 'S3'}],
                        ):
                            with patch(
                                'awslabs.cost_explorer_mcp_server.comparison_handler.create_detailed_group_key',
                                side_effect=['EC2', 'S3'],
                            ):
                                result = await get_cost_comparison_drivers(
                                    ctx,
                                    valid_baseline_range,
                                    valid_comparison_range,
                                    metric_for_comparison='UnblendedCost',
                                    group_by='SERVICE',
                                    filter_expression=None,
                                )

        # Verify API calls - should be called twice due to pagination
        assert mock_ce_client.get_cost_comparison_drivers.call_count == 2

        # Verify the second call includes the NextPageToken
        second_call_args = mock_ce_client.get_cost_comparison_drivers.call_args_list[1][1]
        assert 'NextPageToken' in second_call_args
        assert second_call_args['NextPageToken'] == 'NEXT_PAGE_TOKEN'

        # Verify result structure combines both pages
        assert isinstance(result, dict)
        assert 'driver_analysis' in result
        assert len(result['driver_analysis']) == 2

        # Verify both services from different pages are included
        assert 'EC2' in result['driver_analysis']
        assert 'S3' in result['driver_analysis']

        # Verify the total values
        assert result['total_analysis']['baseline_value'] == 100.0  # 60 + 40
        assert result['total_analysis']['comparison_value'] == 150.0  # 90 + 60
        assert result['total_analysis']['absolute_change'] == 50.0  # 30 + 20
        assert result['total_analysis']['percentage_change'] == 50.0  # (50/100) * 100

    @pytest.mark.asyncio
    async def test_get_cost_drivers_with_filter(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost driver analysis with filter."""
        # Mock response for cost drivers
        mock_ce_client.get_cost_comparison_drivers.return_value = {
            'CostComparisonDrivers': [
                {
                    'CostSelector': {'Dimensions': {'Values': ['EC2']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '60.00',
                            'ComparisonTimePeriodAmount': '90.00',
                            'Difference': '30.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [],
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
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value=filter_expr,
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    with patch(
                        'awslabs.cost_explorer_mcp_server.comparison_handler.extract_group_key_from_complex_selector',
                        return_value='EC2',
                    ):
                        with patch(
                            'awslabs.cost_explorer_mcp_server.comparison_handler.extract_usage_context_from_selector',
                            return_value={'service': 'EC2'},
                        ):
                            with patch(
                                'awslabs.cost_explorer_mcp_server.comparison_handler.create_detailed_group_key',
                                return_value='EC2',
                            ):
                                await get_cost_comparison_drivers(
                                    ctx,
                                    valid_baseline_range,
                                    valid_comparison_range,
                                    metric_for_comparison='UnblendedCost',
                                    filter_expression=filter_expr,
                                    group_by='SERVICE',
                                )

        # Verify API call
        mock_ce_client.get_cost_comparison_drivers.assert_called_once()

        # Verify filter was passed to API call
        call_args = mock_ce_client.get_cost_comparison_drivers.call_args[1]
        assert 'Filter' in call_args
        assert call_args['Filter'] == filter_expr

    @pytest.mark.asyncio
    async def test_get_cost_drivers_api_error(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost driver analysis with API error."""
        # Setup mock error
        mock_ce_client.get_cost_comparison_drivers.side_effect = Exception('API Error')

        ctx = MagicMock()
        # Patch the validation functions to bypass validation
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    result = await get_cost_comparison_drivers(
                        ctx,
                        valid_baseline_range,
                        valid_comparison_range,
                        metric_for_comparison='UnblendedCost',
                        filter_expression=None,
                        group_by='SERVICE',
                    )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'API Error' in result['error']

    @pytest.mark.asyncio
    async def test_get_cost_drivers_total_calculation(
        self, mock_ce_client, valid_baseline_range, valid_comparison_range
    ):
        """Test cost driver analysis total calculation."""
        # Mock response for cost drivers with multiple services
        mock_ce_client.get_cost_comparison_drivers.return_value = {
            'CostComparisonDrivers': [
                {
                    'CostSelector': {'Dimensions': {'Values': ['EC2']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '60.00',
                            'ComparisonTimePeriodAmount': '90.00',
                            'Difference': '30.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [],
                },
                {
                    'CostSelector': {'Dimensions': {'Values': ['S3']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '40.00',
                            'ComparisonTimePeriodAmount': '60.00',
                            'Difference': '20.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [],
                },
                {
                    'CostSelector': {'Dimensions': {'Values': ['RDS']}},
                    'Metrics': {
                        'UnblendedCost': {
                            'BaselineTimePeriodAmount': '50.00',
                            'ComparisonTimePeriodAmount': '40.00',
                            'Difference': '-10.00',
                            'Unit': 'USD',
                        }
                    },
                    'CostDrivers': [],
                },
            ]
        }

        ctx = MagicMock()
        # Patch the validation and helper functions
        with patch(
            'awslabs.cost_explorer_mcp_server.comparison_handler.validate_expression',
            return_value={},
        ):
            with patch(
                'awslabs.cost_explorer_mcp_server.comparison_handler.validate_group_by',
                return_value={'Type': 'DIMENSION', 'Key': 'SERVICE'},
            ):
                with patch(
                    'awslabs.cost_explorer_mcp_server.comparison_handler.validate_comparison_date_range',
                    return_value=(True, ''),
                ):
                    with patch(
                        'awslabs.cost_explorer_mcp_server.comparison_handler.extract_group_key_from_complex_selector',
                        side_effect=['EC2', 'S3', 'RDS'],
                    ):
                        with patch(
                            'awslabs.cost_explorer_mcp_server.comparison_handler.extract_usage_context_from_selector',
                            side_effect=[
                                {'service': 'EC2'},
                                {'service': 'S3'},
                                {'service': 'RDS'},
                            ],
                        ):
                            with patch(
                                'awslabs.cost_explorer_mcp_server.comparison_handler.create_detailed_group_key',
                                side_effect=['EC2', 'S3', 'RDS'],
                            ):
                                result = await get_cost_comparison_drivers(
                                    ctx,
                                    valid_baseline_range,
                                    valid_comparison_range,
                                    metric_for_comparison='UnblendedCost',
                                    group_by='SERVICE',
                                    filter_expression=None,
                                )

        # Verify API call
        mock_ce_client.get_cost_comparison_drivers.assert_called_once()

        # Verify result structure
        assert isinstance(result, dict)
        assert 'driver_analysis' in result
        assert len(result['driver_analysis']) == 3

        # Verify total calculation
        assert result['total_analysis']['baseline_value'] == 150.0  # 60 + 40 + 50
        assert result['total_analysis']['comparison_value'] == 190.0  # 90 + 60 + 40
        assert result['total_analysis']['absolute_change'] == 40.0  # 30 + 20 - 10
        assert result['total_analysis']['percentage_change'] == 26.67  # (40/150) * 100

        # Verify metadata
        assert result['metadata']['total_groups'] == 3

    @pytest.mark.asyncio
    async def test_get_cost_drivers_validation_error(self, mock_ce_client):
        """Test cost driver analysis with validation error."""
        # Create invalid date ranges
        invalid_baseline = DateRange(start_date='2025-01-15', end_date='2025-02-15')
        invalid_comparison = DateRange(start_date='2025-02-15', end_date='2025-03-15')

        ctx = MagicMock()
        result = await get_cost_comparison_drivers(
            ctx, invalid_baseline, invalid_comparison, metric_for_comparison='UnblendedCost'
        )

        # Verify error handling
        assert isinstance(result, dict)
        assert 'error' in result
        # API should not be called with invalid parameters
        mock_ce_client.get_cost_anomaly_drivers.assert_not_called()
