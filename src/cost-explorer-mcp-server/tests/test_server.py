"""Tests for the server module of the cost-explorer-mcp-server."""

import pytest
from awslabs.cost_explorer_mcp_server.server import (
    get_cost_and_usage,
    get_dimension_values_tool,
    get_tag_values_tool,
    get_today_date,
)
from unittest.mock import MagicMock, patch


class TestGetTodayDate:
    """Tests for the get_today_date function."""

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.datetime')
    async def test_get_today_date(self, mock_datetime):
        """Test the get_today_date function returns correct date formats."""
        # Mock the datetime.now() to return a fixed date
        mock_now = MagicMock()
        mock_now.strftime.side_effect = (
            lambda fmt: '2025-06-01' if fmt == '%Y-%m-%d' else '2025-06'
        )
        mock_datetime.now.return_value = mock_now

        # Create a mock context
        mock_context = MagicMock()

        # Call the function
        result = await get_today_date(mock_context)

        # Verify the result
        assert result == {'today_date': '2025-06-01', 'current_month': '2025-06'}


class TestGetDimensionValuesTool:
    """Tests for the get_dimension_values_tool function."""

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.get_dimension_values')
    async def test_get_dimension_values_success(self, mock_get_dimension_values):
        """Test successful retrieval of dimension values."""
        # Mock the get_dimension_values function
        mock_get_dimension_values.return_value = {
            'dimension': 'SERVICE',
            'values': ['Amazon EC2', 'Amazon S3', 'Amazon RDS'],
        }

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-06-01'
        dimension = MagicMock()
        dimension.dimension_key = 'SERVICE'

        # Call the function
        result = await get_dimension_values_tool(mock_context, date_range, dimension)

        # Verify the function called the helper correctly
        mock_get_dimension_values.assert_called_once_with('SERVICE', '2025-05-01', '2025-06-01')

        # Verify the result
        assert result == {
            'dimension': 'SERVICE',
            'values': ['Amazon EC2', 'Amazon S3', 'Amazon RDS'],
        }

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.get_dimension_values')
    async def test_get_dimension_values_error(self, mock_get_dimension_values):
        """Test error handling when retrieving dimension values."""
        # Mock the get_dimension_values function to raise an exception
        mock_get_dimension_values.side_effect = Exception('API Error')

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-06-01'
        dimension = MagicMock()
        dimension.dimension_key = 'SERVICE'

        # Call the function
        result = await get_dimension_values_tool(mock_context, date_range, dimension)

        # Verify the result contains an error
        assert 'error' in result
        assert 'Error getting dimension values' in result['error']


class TestGetTagValuesTool:
    """Tests for the get_tag_values_tool function."""

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.get_tag_values')
    async def test_get_tag_values_success(self, mock_get_tag_values):
        """Test successful retrieval of tag values."""
        # Mock the get_tag_values function
        mock_get_tag_values.return_value = {
            'tag_key': 'Environment',
            'values': ['dev', 'prod', 'test'],
        }

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-06-01'
        tag_key = 'Environment'

        # Call the function
        result = await get_tag_values_tool(mock_context, date_range, tag_key)

        # Verify the function called the helper correctly
        mock_get_tag_values.assert_called_once_with('Environment', '2025-05-01', '2025-06-01')

        # Verify the result
        assert result == {'tag_key': 'Environment', 'values': ['dev', 'prod', 'test']}

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.get_tag_values')
    async def test_get_tag_values_error(self, mock_get_tag_values):
        """Test error handling when retrieving tag values."""
        # Mock the get_tag_values function to raise an exception
        mock_get_tag_values.side_effect = Exception('API Error')

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-06-01'
        tag_key = 'Environment'

        # Call the function
        result = await get_tag_values_tool(mock_context, date_range, tag_key)

        # Verify the result contains an error
        assert 'error' in result
        assert 'Error getting tag values' in result['error']


class TestGetCostAndUsage:
    """Tests for the get_cost_and_usage function."""

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.validate_expression')
    @patch('awslabs.cost_explorer_mcp_server.server.validate_group_by')
    @patch('awslabs.cost_explorer_mcp_server.server.ce')
    async def test_get_cost_and_usage_success(
        self, mock_ce, mock_validate_group_by, mock_validate_expression
    ):
        """Test successful retrieval of cost and usage data."""
        # Mock the validation functions
        mock_validate_expression.return_value = {}
        mock_validate_group_by.return_value = {}

        # Mock the AWS Cost Explorer response
        mock_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '100.50', 'Unit': 'USD'}},
                        },
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {'UnblendedCost': {'Amount': '50.25', 'Unit': 'USD'}},
                        },
                    ],
                }
            ]
        }
        mock_ce.get_cost_and_usage.return_value = mock_response

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-05-31'
        granularity = 'MONTHLY'
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        filter_expression = {
            'Dimensions': {
                'Key': 'REGION',
                'Values': ['us-east-1'],
                'MatchOptions': ['EQUALS'],
            }
        }
        metric = 'UnblendedCost'

        # Call the function
        result = await get_cost_and_usage(
            mock_context, date_range, granularity, group_by, filter_expression, metric
        )

        # Verify the function called the AWS API correctly
        mock_ce.get_cost_and_usage.assert_called_once_with(
            TimePeriod={'Start': '2025-05-01', 'End': '2025-06-01'},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Metrics=['UnblendedCost'],
            Filter={
                'Dimensions': {
                    'Key': 'REGION',
                    'Values': ['us-east-1'],
                    'MatchOptions': ['EQUALS'],
                }
            },
        )

        # Verify the result contains the expected data
        assert 'GroupedCosts' in result
        assert '2025-05-01' in result['GroupedCosts']
        assert 'Amazon Elastic Compute Cloud - Compute' in result['GroupedCosts']['2025-05-01']
        assert 'Amazon Simple Storage Service' in result['GroupedCosts']['2025-05-01']

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.validate_expression')
    async def test_get_cost_and_usage_invalid_filter(self, mock_validate_expression):
        """Test handling of invalid filter expression."""
        # Mock the validation function to return an error
        mock_validate_expression.return_value = {'error': 'Invalid filter expression'}

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-05-31'
        granularity = 'MONTHLY'
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        filter_expression = {
            'Dimensions': {
                'Key': 'REGION',
                'Values': ['invalid-region'],
                'MatchOptions': ['EQUALS'],
            }
        }
        metric = 'UnblendedCost'

        # Call the function
        result = await get_cost_and_usage(
            mock_context, date_range, granularity, group_by, filter_expression, metric
        )

        # Verify the result contains the error
        assert 'error' in result
        assert result['error'] == 'Invalid filter expression'

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.validate_expression')
    @patch('awslabs.cost_explorer_mcp_server.server.validate_group_by')
    @patch('awslabs.cost_explorer_mcp_server.server.ce')
    async def test_get_cost_and_usage_with_usage_quantity(
        self, mock_ce, mock_validate_group_by, mock_validate_expression
    ):
        """Test retrieval of usage quantity data."""
        # Mock the validation functions
        mock_validate_expression.return_value = {}
        mock_validate_group_by.return_value = {}

        # Mock the AWS Cost Explorer response
        mock_response = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UsageQuantity': {'Amount': '730.0', 'Unit': 'Hrs'}},
                        },
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {'UsageQuantity': {'Amount': '1024.0', 'Unit': 'GB'}},
                        },
                    ],
                }
            ]
        }
        mock_ce.get_cost_and_usage.return_value = mock_response

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-05-31'
        granularity = 'MONTHLY'
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        filter_expression = None
        metric = 'UsageQuantity'

        # Call the function
        result = await get_cost_and_usage(
            mock_context, date_range, granularity, group_by, filter_expression, metric
        )

        # Verify the result contains the expected data with units
        assert 'GroupedCosts' in result
        assert "('2025-05-01', 'Amount')" in result['GroupedCosts']
        assert "('2025-05-01', 'Unit')" in result['GroupedCosts']
        assert (
            'Amazon Elastic Compute Cloud - Compute'
            in result['GroupedCosts']["('2025-05-01', 'Amount')"]
        )
        assert (
            'Amazon Simple Storage Service' in result['GroupedCosts']["('2025-05-01', 'Amount')"]
        )
        assert (
            result['GroupedCosts']["('2025-05-01', 'Unit')"][
                'Amazon Elastic Compute Cloud - Compute'
            ]
            == 'Hrs'
        )
        assert (
            result['GroupedCosts']["('2025-05-01', 'Unit')"]['Amazon Simple Storage Service']
            == 'GB'
        )

    @pytest.mark.asyncio
    @patch('awslabs.cost_explorer_mcp_server.server.validate_expression')
    @patch('awslabs.cost_explorer_mcp_server.server.validate_group_by')
    @patch('awslabs.cost_explorer_mcp_server.server.ce')
    async def test_get_cost_and_usage_with_pagination(
        self, mock_ce, mock_validate_group_by, mock_validate_expression
    ):
        """Test retrieval of cost data with pagination."""
        # Mock the validation functions
        mock_validate_expression.return_value = {}
        mock_validate_group_by.return_value = {}

        # Mock the AWS Cost Explorer responses with pagination
        mock_response1 = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Elastic Compute Cloud - Compute'],
                            'Metrics': {'UnblendedCost': {'Amount': '100.50', 'Unit': 'USD'}},
                        }
                    ],
                }
            ],
            'NextPageToken': 'token123',
        }
        mock_response2 = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-05-01', 'End': '2025-06-01'},
                    'Groups': [
                        {
                            'Keys': ['Amazon Simple Storage Service'],
                            'Metrics': {'UnblendedCost': {'Amount': '50.25', 'Unit': 'USD'}},
                        }
                    ],
                }
            ]
        }
        mock_ce.get_cost_and_usage.side_effect = [mock_response1, mock_response2]

        # Create a mock context and parameters
        mock_context = MagicMock()
        date_range = MagicMock()
        date_range.start_date = '2025-05-01'
        date_range.end_date = '2025-05-31'
        granularity = 'MONTHLY'
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        filter_expression = None
        metric = 'UnblendedCost'

        # Call the function
        result = await get_cost_and_usage(
            mock_context, date_range, granularity, group_by, filter_expression, metric
        )

        # Verify the function called the AWS API twice with the correct parameters
        assert mock_ce.get_cost_and_usage.call_count == 2
        mock_ce.get_cost_and_usage.assert_any_call(
            TimePeriod={'Start': '2025-05-01', 'End': '2025-06-01'},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Metrics=['UnblendedCost'],
        )
        mock_ce.get_cost_and_usage.assert_any_call(
            TimePeriod={'Start': '2025-05-01', 'End': '2025-06-01'},
            Granularity='MONTHLY',
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
            Metrics=['UnblendedCost'],
            NextPageToken='token123',
        )

        # Verify the result contains data from both pages
        assert 'GroupedCosts' in result
        assert '2025-05-01' in result['GroupedCosts']
        assert 'Amazon Elastic Compute Cloud - Compute' in result['GroupedCosts']['2025-05-01']
        assert 'Amazon Simple Storage Service' in result['GroupedCosts']['2025-05-01']
