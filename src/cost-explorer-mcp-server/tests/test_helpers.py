"""Tests for the helpers module of the cost-explorer-mcp-server."""

from awslabs.cost_explorer_mcp_server.helpers import (
    get_dimension_values,
    get_tag_values,
    validate_expression,
    validate_group_by,
)
from unittest.mock import patch


class TestGetDimensionValues:
    """Tests for the get_dimension_values function."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.ce')
    def test_get_dimension_values_success(self, mock_ce):
        """Test successful retrieval of dimension values."""
        # Mock the AWS Cost Explorer response
        mock_response = {
            'DimensionValues': [
                {'Value': 'Amazon Elastic Compute Cloud - Compute'},
                {'Value': 'Amazon Simple Storage Service'},
                {'Value': 'Amazon Relational Database Service'},
            ]
        }
        mock_ce.get_dimension_values.return_value = mock_response

        # Call the function
        result = get_dimension_values('SERVICE', '2025-05-01', '2025-06-01')

        # Verify the function called the AWS API correctly
        mock_ce.get_dimension_values.assert_called_once_with(
            TimePeriod={'Start': '2025-05-01', 'End': '2025-06-01'}, Dimension='SERVICE'
        )

        # Verify the result
        assert result == {
            'dimension': 'SERVICE',
            'values': [
                'Amazon Elastic Compute Cloud - Compute',
                'Amazon Simple Storage Service',
                'Amazon Relational Database Service',
            ],
        }

    @patch('awslabs.cost_explorer_mcp_server.helpers.ce')
    def test_get_dimension_values_error(self, mock_ce):
        """Test error handling when retrieving dimension values."""
        # Mock the AWS Cost Explorer to raise an exception
        mock_ce.get_dimension_values.side_effect = Exception('API Error')

        # Call the function
        result = get_dimension_values('SERVICE', '2025-05-01', '2025-06-01')

        # Verify the result contains an error
        assert 'error' in result
        assert result['error'] == 'API Error'


class TestGetTagValues:
    """Tests for the get_tag_values function."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.ce')
    def test_get_tag_values_success(self, mock_ce):
        """Test successful retrieval of tag values."""
        # Mock the AWS Cost Explorer response
        mock_response = {'Tags': ['dev', 'prod', 'test']}
        mock_ce.get_tags.return_value = mock_response

        # Call the function
        result = get_tag_values('Environment', '2025-05-01', '2025-06-01')

        # Verify the function called the AWS API correctly
        mock_ce.get_tags.assert_called_once_with(
            TimePeriod={'Start': '2025-05-01', 'End': '2025-06-01'},
            TagKey='Environment',
        )

        # Verify the result
        assert result == {'tag_key': 'Environment', 'values': ['dev', 'prod', 'test']}

    @patch('awslabs.cost_explorer_mcp_server.helpers.ce')
    def test_get_tag_values_error(self, mock_ce):
        """Test error handling when retrieving tag values."""
        # Mock the AWS Cost Explorer to raise an exception
        mock_ce.get_tags.side_effect = Exception('API Error')

        # Call the function
        result = get_tag_values('Environment', '2025-05-01', '2025-06-01')

        # Verify the result contains an error
        assert 'error' in result
        assert result['error'] == 'API Error'


class TestValidateExpression:
    """Tests for the validate_expression function."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_dimension_values')
    def test_validate_dimensions_success(self, mock_get_dimension_values):
        """Test successful validation of a dimensions filter."""
        # Mock the get_dimension_values function
        mock_get_dimension_values.return_value = {
            'dimension': 'SERVICE',
            'values': [
                'Amazon Elastic Compute Cloud - Compute',
                'Amazon Simple Storage Service',
                'Amazon Relational Database Service',
            ],
        }

        # Create a test expression
        expression = {
            'Dimensions': {
                'Key': 'SERVICE',
                'Values': [
                    'Amazon Elastic Compute Cloud - Compute',
                    'Amazon Simple Storage Service',
                ],
                'MatchOptions': ['EQUALS'],
            }
        }

        # Call the function
        result = validate_expression(expression, '2025-05-01', '2025-06-01')

        # Verify the result is empty (valid)
        assert result == {}

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_dimension_values')
    def test_validate_dimensions_invalid_value(self, mock_get_dimension_values):
        """Test validation with an invalid dimension value."""
        # Mock the get_dimension_values function
        mock_get_dimension_values.return_value = {
            'dimension': 'SERVICE',
            'values': [
                'Amazon Elastic Compute Cloud - Compute',
                'Amazon Simple Storage Service',
                'Amazon Relational Database Service',
            ],
        }

        # Create a test expression with an invalid value
        expression = {
            'Dimensions': {
                'Key': 'SERVICE',
                'Values': ['Amazon Elastic Compute Cloud - Compute', 'Invalid Service'],
                'MatchOptions': ['EQUALS'],
            }
        }

        # Call the function
        result = validate_expression(expression, '2025-05-01', '2025-06-01')

        # Verify the result contains an error
        assert 'error' in result
        assert "Invalid value 'Invalid Service' for dimension 'SERVICE'" in result['error']

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_tag_values')
    def test_validate_tags_success(self, mock_get_tag_values):
        """Test successful validation of a tags filter."""
        # Mock the get_tag_values function
        mock_get_tag_values.return_value = {
            'tag_key': 'Environment',
            'values': ['dev', 'prod', 'test'],
        }

        # Create a test expression
        expression = {
            'Tags': {
                'Key': 'Environment',
                'Values': ['dev', 'prod'],
                'MatchOptions': ['EQUALS'],
            }
        }

        # Call the function
        result = validate_expression(expression, '2025-05-01', '2025-06-01')

        # Verify the result is empty (valid)
        assert result == {}

    def test_validate_logical_operators(self):
        """Test validation of logical operators."""
        # Test with multiple logical operators (invalid)
        expression = {
            'And': [
                {
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon EC2'],
                        'MatchOptions': ['EQUALS'],
                    }
                }
            ],
            'Or': [
                {
                    'Dimensions': {
                        'Key': 'REGION',
                        'Values': ['us-east-1'],
                        'MatchOptions': ['EQUALS'],
                    }
                }
            ],
        }
        result = validate_expression(expression, '2025-05-01', '2025-06-01')
        assert 'error' in result
        assert 'Only one logical operator' in result['error']

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_dimension_values')
    def test_validate_nested_expressions(self, mock_get_dimension_values):
        """Test validation of nested expressions with logical operators."""
        # Mock the get_dimension_values function
        mock_get_dimension_values.return_value = {
            'dimension': 'SERVICE',
            'values': [
                'Amazon Elastic Compute Cloud - Compute',
                'Amazon Simple Storage Service',
            ],
        }

        # Create a test expression with nested And
        expression = {
            'And': [
                {
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon Elastic Compute Cloud - Compute'],
                        'MatchOptions': ['EQUALS'],
                    }
                },
                {
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon Simple Storage Service'],
                        'MatchOptions': ['EQUALS'],
                    }
                },
            ]
        }

        # Call the function
        result = validate_expression(expression, '2025-05-01', '2025-06-01')

        # Verify the result is empty (valid)
        assert result == {}


class TestValidateGroupBy:
    """Tests for the validate_group_by function."""

    def test_validate_group_by_success(self):
        """Test successful validation of a group_by parameter."""
        # Test with valid group_by
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = validate_group_by(group_by)
        assert result == {}

    def test_validate_group_by_invalid_type(self):
        """Test validation with an invalid group_by type."""
        # Test with invalid type
        group_by = {'Type': 'INVALID', 'Key': 'SERVICE'}
        result = validate_group_by(group_by)
        assert 'error' in result
        assert 'Invalid group Type' in result['error']

    def test_validate_group_by_missing_keys(self):
        """Test validation with missing keys in group_by."""
        # Test with missing Key
        group_by = {'Type': 'DIMENSION'}
        result = validate_group_by(group_by)
        assert 'error' in result
        assert 'must be a dictionary with' in result['error']

        # Test with missing Type
        group_by = {'Key': 'SERVICE'}
        result = validate_group_by(group_by)
        assert 'error' in result
        assert 'must be a dictionary with' in result['error']
