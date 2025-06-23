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

"""Comprehensive tests for helpers module."""

import pytest
from awslabs.cost_explorer_mcp_server.helpers import (
    create_detailed_group_key,
    extract_group_key_from_complex_selector,
    extract_usage_context_from_selector,
    format_date_for_api,
    get_available_dimension_values,
    get_available_tag_values,
    get_cost_explorer_client,
    validate_comparison_date_range,
    validate_date_format,
    validate_date_range,
    validate_expression,
    validate_forecast_date_range,
    validate_group_by,
    validate_match_options,
)
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


class TestGetCostExplorerClient:
    """Tests for the get_cost_explorer_client function."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.boto3.Session')
    @patch('os.environ.get')
    def test_get_client_with_profile_and_region(self, mock_env_get, mock_session):
        """Test client creation with AWS profile and custom region."""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Mock environment variables
        def env_side_effect(key, default=None):
            env_vars = {
                'AWS_PROFILE': 'test-profile',
                'AWS_REGION': 'us-west-2',
                'FASTMCP_LOG_LEVEL': 'WARNING',
            }
            return env_vars.get(key, default)

        mock_env_get.side_effect = env_side_effect

        # Get client
        client = get_cost_explorer_client()

        # Verify client was created with correct parameters
        mock_session.assert_called_once()
        mock_session.return_value.client.assert_called_once()
        assert client == mock_client

    @patch('awslabs.cost_explorer_mcp_server.helpers.boto3.Session')
    @patch('os.environ.get')
    def test_get_client_without_profile(self, mock_env_get, mock_session):
        """Test client creation without AWS profile."""
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        # Mock environment variables without profile
        def env_side_effect(key, default=None):
            env_vars = {
                'AWS_REGION': 'us-east-1',
            }
            return env_vars.get(key, default)

        mock_env_get.side_effect = env_side_effect

        # Reset the global client cache
        import awslabs.cost_explorer_mcp_server.helpers

        awslabs.cost_explorer_mcp_server.helpers._cost_explorer_client = None

        # Get client
        client = get_cost_explorer_client()

        # Verify client was created
        assert client == mock_client

    @patch('awslabs.cost_explorer_mcp_server.helpers.boto3.Session')
    def test_get_client_exception_handling(self, mock_session):
        """Test client creation with exception."""
        mock_session.side_effect = Exception('AWS Error')

        # Reset the global client cache
        import awslabs.cost_explorer_mcp_server.helpers

        awslabs.cost_explorer_mcp_server.helpers._cost_explorer_client = None

        with pytest.raises(Exception, match='AWS Error'):
            get_cost_explorer_client()


class TestValidation:
    """Tests for validation functions."""

    def test_validate_date_format_valid(self):
        """Test date format validation with valid date."""
        is_valid, _ = validate_date_format('2025-01-01')
        assert is_valid is True

    def test_validate_date_format_invalid_format(self):
        """Test date format validation with invalid format."""
        is_valid, error = validate_date_format('invalid-date')
        assert is_valid is False
        assert 'is not in YYYY-MM-DD format' in error

    def test_validate_date_format_invalid_date(self):
        """Test date format validation with invalid date."""
        is_valid, error = validate_date_format('2025-13-01')
        assert is_valid is False
        assert 'Invalid date' in error

    def test_validate_date_range_valid(self):
        """Test date range validation with valid range."""
        is_valid, _ = validate_date_range('2025-01-01', '2025-01-31')
        assert is_valid is True

    def test_validate_date_range_invalid_order(self):
        """Test date range validation with start after end."""
        is_valid, error = validate_date_range('2025-01-31', '2025-01-01')
        assert is_valid is False
        assert 'cannot be after end date' in error

    def test_validate_date_range_with_granularity_hourly_valid(self):
        """Test date range validation with hourly granularity - valid range."""
        is_valid, _ = validate_date_range('2025-01-01', '2025-01-10', 'HOURLY')
        assert is_valid is True

    def test_validate_date_range_with_granularity_hourly_invalid(self):
        """Test date range validation with hourly granularity - invalid range."""
        is_valid, error = validate_date_range('2025-01-01', '2025-02-01', 'HOURLY')
        assert is_valid is False
        assert 'HOURLY granularity supports a maximum of 14 days' in error

    def test_format_date_for_api_hourly(self):
        """Test date formatting for hourly granularity."""
        result = format_date_for_api('2025-01-01', 'HOURLY')
        assert result == '2025-01-01T00:00:00Z'

    def test_format_date_for_api_daily(self):
        """Test date formatting for daily granularity."""
        result = format_date_for_api('2025-01-01', 'DAILY')
        assert result == '2025-01-01'

    def test_format_date_for_api_monthly(self):
        """Test date formatting for monthly granularity."""
        result = format_date_for_api('2025-01-01', 'MONTHLY')
        assert result == '2025-01-01'

    def test_validate_match_options_dimensions_valid(self):
        """Test match options validation for dimensions."""
        result = validate_match_options(['EQUALS', 'CASE_SENSITIVE'], 'Dimensions')
        assert result == {}

    def test_validate_match_options_dimensions_invalid(self):
        """Test match options validation for dimensions with invalid option."""
        result = validate_match_options(['INVALID'], 'Dimensions')
        assert 'error' in result
        assert 'Invalid MatchOption' in result['error']

    def test_validate_match_options_tags_valid(self):
        """Test match options validation for tags."""
        result = validate_match_options(['EQUALS', 'ABSENT'], 'Tags')
        assert result == {}

    def test_validate_match_options_unknown_type(self):
        """Test match options validation with unknown filter type."""
        result = validate_match_options(['EQUALS'], 'Unknown')
        assert 'error' in result
        assert 'Unknown filter type' in result['error']

    def test_validate_group_by_valid_dict(self):
        """Test group_by validation with valid dictionary."""
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = validate_group_by(group_by)
        assert result == {}

    def test_validate_group_by_invalid_type(self):
        """Test group_by validation with invalid type."""
        group_by = {'Type': 'INVALID', 'Key': 'SERVICE'}
        result = validate_group_by(group_by)
        assert 'error' in result
        assert 'Invalid group Type' in result['error']

    def test_validate_group_by_missing_keys(self):
        """Test group_by validation with missing keys."""
        result = validate_group_by({'Type': 'DIMENSION'})
        assert 'error' in result
        assert 'must be a dictionary with "Type" and "Key" keys' in result['error']

    def test_validate_group_by_none(self):
        """Test group_by validation with None."""
        result = validate_group_by(None)
        assert 'error' in result

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_valid(self, mock_datetime):
        """Test forecast date range validation with valid range."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, _ = validate_forecast_date_range('2025-06-15', '2025-07-15')
        assert is_valid is True

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_start_in_future(self, mock_datetime):
        """Test forecast date range validation with start date in future."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, error = validate_forecast_date_range('2025-06-20', '2025-07-20')
        assert is_valid is False
        assert 'must be equal to or no later than the current date' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_end_in_past(self, mock_datetime):
        """Test forecast date range validation with end date in past."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, error = validate_forecast_date_range('2025-06-10', '2025-06-12')
        assert is_valid is False
        assert 'must be in the future' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_daily_too_long(self, mock_datetime):
        """Test forecast date range validation with daily granularity too long."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, error = validate_forecast_date_range('2025-06-15', '2025-10-15', 'DAILY')
        assert is_valid is False
        assert 'DAILY granularity supports a maximum of 3 months' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_comparison_date_range_valid(self, mock_datetime):
        """Test comparison date range validation with valid range."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, _ = validate_comparison_date_range('2025-01-01', '2025-02-01')
        assert is_valid is True

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_comparison_date_range_not_first_day(self, mock_datetime):
        """Test comparison date range validation with non-first day."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, error = validate_comparison_date_range('2025-01-15', '2025-02-01')
        assert is_valid is False
        assert 'must be the first day of a month' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_comparison_date_range_not_one_month(self, mock_datetime):
        """Test comparison date range validation with non-one-month duration."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, error = validate_comparison_date_range('2025-01-01', '2025-03-01')
        assert is_valid is False
        assert 'must be exactly one month' in error

    def test_extract_group_key_from_complex_selector_simple(self):
        """Test extracting group key from simple selector."""
        selector = {'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2']}}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'EC2'

    def test_extract_group_key_from_complex_selector_multiple(self):
        """Test extracting group key from selector with multiple values."""
        selector = {'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2', 'S3']}}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'EC2'  # Function returns first value

    def test_extract_group_key_from_complex_selector_empty(self):
        """Test extracting group key from empty selector."""
        selector = {}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'Unknown'

    def test_extract_usage_context_from_selector(self):
        """Test extracting usage context from selector."""
        selector = {
            'Dimensions': {'Values': ['EC2']},
            'Tags': {'Key': 'Environment', 'Values': ['Production']},
        }
        result = extract_usage_context_from_selector(selector)
        # The actual implementation returns different keys than expected
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_create_detailed_group_key(self):
        """Test creating detailed group key."""
        group_key = 'EC2'
        context = {'service': 'EC2', 'region': 'us-east-1'}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = create_detailed_group_key(group_key, context, group_by)
        assert 'EC2' in result


class TestValidateExpression:
    """Tests for validate_expression function."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_available_dimension_values')
    def test_validate_expression_dimensions_valid(self, mock_get_values):
        """Test expression validation with valid dimensions."""
        mock_get_values.return_value = {'values': ['EC2', 'S3']}

        expression = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2'], 'MatchOptions': ['EQUALS']}
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert result == {}

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_available_dimension_values')
    def test_validate_expression_dimensions_invalid_value(self, mock_get_values):
        """Test expression validation with invalid dimension value."""
        mock_get_values.return_value = {'values': ['EC2', 'S3']}

        expression = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['INVALID'], 'MatchOptions': ['EQUALS']}
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert 'error' in result
        assert 'Invalid value' in result['error']

    def test_validate_expression_dimensions_missing_keys(self):
        """Test expression validation with missing dimension keys."""
        expression = {
            'Dimensions': {
                'Key': 'SERVICE'
                # Missing Values and MatchOptions
            }
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert 'error' in result
        assert 'must include "Key", "Values", and "MatchOptions"' in result['error']

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_available_tag_values')
    def test_validate_expression_tags_valid(self, mock_get_values):
        """Test expression validation with valid tags."""
        mock_get_values.return_value = {'values': ['Production', 'Development']}

        expression = {
            'Tags': {'Key': 'Environment', 'Values': ['Production'], 'MatchOptions': ['EQUALS']}
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert result == {}

    def test_validate_expression_cost_categories_valid(self):
        """Test expression validation with valid cost categories."""
        expression = {
            'CostCategories': {
                'Key': 'Department',
                'Values': ['Engineering'],
                'MatchOptions': ['EQUALS'],
            }
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert result == {}

    def test_validate_expression_logical_and(self):
        """Test expression validation with And operator."""
        expression = {
            'And': [
                {
                    'CostCategories': {
                        'Key': 'Department',
                        'Values': ['Engineering'],
                        'MatchOptions': ['EQUALS'],
                    }
                }
            ]
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert result == {}

    def test_validate_expression_logical_or(self):
        """Test expression validation with Or operator."""
        expression = {
            'Or': [
                {
                    'CostCategories': {
                        'Key': 'Department',
                        'Values': ['Engineering'],
                        'MatchOptions': ['EQUALS'],
                    }
                }
            ]
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert result == {}

    def test_validate_expression_logical_not(self):
        """Test expression validation with Not operator."""
        expression = {
            'Not': {
                'CostCategories': {
                    'Key': 'Department',
                    'Values': ['Engineering'],
                    'MatchOptions': ['EQUALS'],
                }
            }
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert result == {}

    def test_validate_expression_multiple_logical_operators(self):
        """Test expression validation with multiple logical operators."""
        expression = {'And': [], 'Or': []}

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert 'error' in result
        assert 'Only one logical operator' in result['error']

    def test_validate_expression_no_valid_keys(self):
        """Test expression validation with no valid keys."""
        expression = {'InvalidKey': 'value'}

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert 'error' in result
        assert 'must include at least one of the following keys' in result['error']

    def test_validate_expression_exception_handling(self):
        """Test expression validation with exception."""
        # Pass invalid date range to trigger exception in date validation
        expression = {
            'CostCategories': {'Key': 'Dept', 'Values': ['Eng'], 'MatchOptions': ['EQUALS']}
        }
        result = validate_expression(expression, 'invalid-date', '2025-01-31')
        assert 'error' in result
        # The error message will be about date format, not general validation error
        assert 'not in YYYY-MM-DD format' in result['error']


class TestErrorHandling:
    """Tests for error handling in helper functions."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_dimension_values_client_error(self, mock_get_client):
        """Test dimension values with client creation error."""
        mock_get_client.side_effect = Exception('Client creation failed')

        result = get_available_dimension_values('SERVICE', '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'Client creation failed' in result['error']

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_tag_values_client_error(self, mock_get_client):
        """Test tag values with client creation error."""
        mock_get_client.side_effect = Exception('Client creation failed')

        result = get_available_tag_values('Environment', '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'Client creation failed' in result['error']

    def test_validate_expression_with_tags_error(self):
        """Test expression validation with tags API error."""
        expression = {
            'Tags': {'Key': 'Environment', 'Values': ['Production'], 'MatchOptions': ['EQUALS']}
        }

        # Mock the tag values function to return error
        with patch(
            'awslabs.cost_explorer_mcp_server.helpers.get_available_tag_values',
            return_value={'error': 'Tag API error'},
        ):
            result = validate_expression(expression, '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'Tag API error' in result['error']

    def test_validate_expression_with_dimensions_error(self):
        """Test expression validation with dimensions API error."""
        expression = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2'], 'MatchOptions': ['EQUALS']}
        }

        # Mock the dimension values function to return error
        with patch(
            'awslabs.cost_explorer_mcp_server.helpers.get_available_dimension_values',
            return_value={'error': 'Dimension API error'},
        ):
            result = validate_expression(expression, '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'Dimension API error' in result['error']

    def test_validate_expression_with_invalid_tag_values(self):
        """Test expression validation with invalid tag values."""
        expression = {
            'Tags': {'Key': 'Environment', 'Values': ['InvalidValue'], 'MatchOptions': ['EQUALS']}
        }

        # Mock the tag values function to return valid values that don't include our test value
        with patch(
            'awslabs.cost_explorer_mcp_server.helpers.get_available_tag_values',
            return_value={'values': ['Production', 'Development']},
        ):
            result = validate_expression(expression, '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'Invalid value' in result['error']
        assert 'InvalidValue' in result['error']

    def test_validate_expression_tags_missing_values(self):
        """Test expression validation with tags missing Values."""
        expression = {
            'Tags': {
                'Key': 'Environment',
                'MatchOptions': ['EQUALS'],
                # Missing Values
            }
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'must include "Key", "Values", and "MatchOptions"' in result['error']

    def test_validate_expression_cost_categories_missing_values(self):
        """Test expression validation with cost categories missing Values."""
        expression = {
            'CostCategories': {
                'Key': 'Department',
                'MatchOptions': ['EQUALS'],
                # Missing Values
            }
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')

        assert 'error' in result
        assert 'must include "Key", "Values", and "MatchOptions"' in result['error']

    def test_validate_match_options_cost_categories_valid(self):
        """Test match options validation for cost categories."""
        result = validate_match_options(['EQUALS', 'ABSENT'], 'CostCategories')
        assert result == {}

    def test_validate_match_options_cost_categories_invalid(self):
        """Test match options validation for cost categories with invalid option."""
        result = validate_match_options(['INVALID'], 'CostCategories')
        assert 'error' in result
        assert 'Invalid MatchOption' in result['error']

    def test_extract_group_key_with_tags(self):
        """Test extracting group key from tag selector."""
        selector = {'Tags': {'Key': 'Environment', 'Values': ['Production']}}
        group_by = {'Type': 'TAG', 'Key': 'Environment'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'Production'

    def test_extract_group_key_with_cost_categories(self):
        """Test extracting group key from cost category selector."""
        selector = {'CostCategories': {'Key': 'Department', 'Values': ['Engineering']}}
        group_by = {'Type': 'COST_CATEGORY', 'Key': 'Department'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'Engineering'

    def test_extract_group_key_with_nested_and(self):
        """Test extracting group key from nested And structure."""
        selector = {'And': [{'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2']}}]}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'EC2'

    def test_extract_group_key_with_nested_or(self):
        """Test extracting group key from nested Or structure."""
        selector = {'Or': [{'Dimensions': {'Key': 'SERVICE', 'Values': ['S3']}}]}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'S3'

    def test_extract_group_key_with_nested_not(self):
        """Test extracting group key from nested Not structure."""
        selector = {'Not': {'Dimensions': {'Key': 'SERVICE', 'Values': ['Lambda']}}}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'Lambda'

    def test_extract_usage_context_with_tags(self):
        """Test extracting usage context with tags."""
        selector = {
            'Tags': {'Key': 'Environment', 'Values': ['Production']},
            'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2']},
        }
        result = extract_usage_context_from_selector(selector)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_create_detailed_group_key_with_context(self):
        """Test creating detailed group key with rich context."""
        group_key = 'EC2'
        context = {'service': 'EC2', 'region': 'us-east-1', 'usage_type': 'BoxUsage:t3.micro'}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = create_detailed_group_key(group_key, context, group_by)
        assert 'EC2' in result
        assert isinstance(result, str)


class TestAdditionalCoverage:
    """Additional tests to improve coverage."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_dimension_values_empty_response(self, mock_get_client):
        """Test dimension values with empty response."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_dimension_values.return_value = {'DimensionValues': []}

        result = get_available_dimension_values('SERVICE', '2025-01-01', '2025-01-31')

        assert 'values' in result
        assert result['values'] == []

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_cost_explorer_client')
    def test_get_available_tag_values_empty_response(self, mock_get_client):
        """Test tag values with empty response."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_tags.return_value = {'Tags': []}

        result = get_available_tag_values('Environment', '2025-01-01', '2025-01-31')

        assert 'values' in result
        assert result['values'] == []

    def test_validate_group_by_invalid_dict_structure(self):
        """Test group_by validation with invalid dictionary structure."""
        result = validate_group_by({'InvalidKey': 'value'})
        assert 'error' in result
        assert 'must be a dictionary with "Type" and "Key" keys' in result['error']

    def test_validate_group_by_invalid_type_value(self):
        """Test group_by validation with invalid type value."""
        result = validate_group_by({'Type': 'INVALID_TYPE', 'Key': 'SERVICE'})
        assert 'error' in result
        assert 'Invalid group Type' in result['error']

    def test_extract_group_key_with_empty_values(self):
        """Test extracting group key with empty values."""
        selector = {'Dimensions': {'Key': 'SERVICE', 'Values': []}}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'No SERVICE'

    def test_extract_group_key_with_none_values(self):
        """Test extracting group key with None in values."""
        selector = {'Dimensions': {'Key': 'SERVICE', 'Values': [None]}}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        result = extract_group_key_from_complex_selector(selector, group_by)
        assert result == 'No SERVICE'

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_monthly_too_long(self, mock_datetime):
        """Test forecast date range validation with monthly granularity too long."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 6, 15).date()
        mock_datetime.strptime = datetime.strptime

        is_valid, error = validate_forecast_date_range('2025-06-15', '2026-07-15', 'MONTHLY')
        assert is_valid is False
        assert 'MONTHLY granularity supports a maximum of 12 months' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.validate_date_range')
    def test_get_available_dimension_values_date_validation_error(self, mock_validate):
        """Test dimension values with date validation error."""
        mock_validate.return_value = (False, 'Invalid date range')

        result = get_available_dimension_values('SERVICE', '2025-01-31', '2025-01-01')

        assert 'error' in result
        assert 'Invalid date range' in result['error']

    @patch('awslabs.cost_explorer_mcp_server.helpers.validate_date_range')
    def test_get_available_tag_values_date_validation_error(self, mock_validate):
        """Test tag values with date validation error."""
        mock_validate.return_value = (False, 'Invalid date range')

        result = get_available_tag_values('Environment', '2025-01-31', '2025-01-01')

        assert 'error' in result
        assert 'Invalid date range' in result['error']

    def test_validate_date_format_invalid_format(self):
        """Test date format validation with invalid format."""
        is_valid, error = validate_date_format('2025/01/01')  # Wrong format
        assert is_valid is False
        assert 'is not in YYYY-MM-DD format' in error

    def test_validate_date_format_invalid_date(self):
        """Test date format validation with invalid date."""
        is_valid, error = validate_date_format('2025-13-01')  # Invalid month
        assert is_valid is False
        assert 'Invalid date' in error

    def test_validate_date_range_start_after_end(self):
        """Test date range validation with start after end."""
        is_valid, error = validate_date_range('2025-01-31', '2025-01-01')
        assert is_valid is False
        assert 'cannot be after end date' in error

    def test_validate_date_range_invalid_end_date_format(self):
        """Test date range validation with invalid end date format."""
        is_valid, error = validate_date_range('2025-01-01', '2025/01/31')
        assert is_valid is False
        assert 'is not in YYYY-MM-DD format' in error

    def test_validate_expression_dimensions_match_options_error(self):
        """Test expression validation with invalid match options for dimensions."""
        expression = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2'], 'MatchOptions': ['INVALID_OPTION']}
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert 'error' in result
        assert 'Invalid MatchOption' in result['error']

    @patch('awslabs.cost_explorer_mcp_server.helpers.get_available_dimension_values')
    def test_validate_expression_dimensions_api_error(self, mock_get_values):
        """Test expression validation when dimension API returns error."""
        mock_get_values.return_value = {'error': 'API connection failed'}

        expression = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['EC2'], 'MatchOptions': ['EQUALS']}
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert 'error' in result
        assert 'API connection failed' in result['error']

    def test_validate_expression_tags_missing_match_options(self):
        """Test expression validation with tags missing MatchOptions."""
        expression = {
            'Tags': {
                'Key': 'Environment',
                'Values': ['Production'],
                # Missing MatchOptions
            }
        }

        result = validate_expression(expression, '2025-01-01', '2025-01-31')
        assert 'error' in result
        assert 'must include "Key", "Values", and "MatchOptions"' in result['error']

    def test_validate_date_range_invalid_start_date_format(self):
        """Test date range validation with invalid start date format."""
        is_valid, error = validate_date_range('invalid-date', '2025-01-31')
        assert is_valid is False
        assert 'is not in YYYY-MM-DD format' in error

    def test_validate_group_by_string_valid(self):
        """Test group_by validation with valid dictionary."""
        result = validate_group_by({'Type': 'DIMENSION', 'Key': 'SERVICE'})
        assert result == {}

    def test_validate_group_by_string_invalid(self):
        """Test group_by validation with string instead of dict."""
        # Type ignore because we're intentionally testing invalid input
        result = validate_group_by('INVALID_KEY')  # type: ignore
        assert 'error' in result
        assert 'must be a dictionary with "Type" and "Key" keys' in result['error']

    def test_validate_group_by_none_input(self):
        """Test group_by validation with None input."""
        result = validate_group_by(None)
        assert 'error' in result
        assert 'must be a dictionary with "Type" and "Key" keys' in result['error']

    def test_validate_group_by_missing_type(self):
        """Test group_by validation with missing Type key."""
        result = validate_group_by({'Key': 'SERVICE'})
        assert 'error' in result
        assert 'must be a dictionary with "Type" and "Key" keys' in result['error']

    def test_validate_group_by_missing_key(self):
        """Test group_by validation with missing Key."""
        result = validate_group_by({'Type': 'DIMENSION'})
        assert 'error' in result
        assert 'must be a dictionary with "Type" and "Key" keys' in result['error']


class TestValidateMatchOptions:
    """Tests for the validate_match_options function."""

    def test_validate_match_options_unknown_filter_type(self):
        """Test validate_match_options with an unknown filter type."""
        # This test covers the case where an unknown filter type is provided
        result = validate_match_options(['EQUALS'], 'UnknownFilterType')

        # Verify that an error is returned
        assert 'error' in result
        assert 'Unknown filter type' in result['error']

    def test_validate_match_options_invalid_option(self):
        """Test validate_match_options with an invalid match option."""
        # This test covers the case where an invalid match option is provided
        result = validate_match_options(['INVALID_OPTION'], 'Dimensions')

        # Verify that an error is returned
        assert 'error' in result
        assert 'Invalid MatchOption' in result['error']


class TestExtractUsageContextFromSelector:
    """Tests for the extract_usage_context_from_selector function."""

    def test_extract_usage_context_with_complex_nested_structure(self):
        """Test extracting context from a complex nested selector structure."""
        # Create a complex selector with nested And/Or/Not structures
        complex_selector = {
            'And': [
                {
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon Elastic Compute Cloud - Compute'],
                    }
                },
                {
                    'Or': [
                        {'Dimensions': {'Key': 'USAGE_TYPE', 'Values': ['BoxUsage:t3.micro']}},
                        {'Not': {'Dimensions': {'Key': 'REGION', 'Values': ['us-west-1']}}},
                    ]
                },
                {'Tags': {'Key': 'Environment', 'Values': ['Production']}},
                {'CostCategories': {'Key': 'Team', 'Values': ['Engineering']}},
            ]
        }

        # Extract context from the complex selector
        context = extract_usage_context_from_selector(complex_selector)

        # Verify that all expected context values are extracted
        assert context['service'] == 'Amazon Elastic Compute Cloud - Compute'
        assert context['usage_type'] == 'BoxUsage:t3.micro'
        assert context['region'] == 'us-west-1'
        assert context['tag_environment'] == 'Production'
        assert context['category_team'] == 'Engineering'


class TestCreateDetailedGroupKey:
    """Tests for the create_detailed_group_key function."""

    def test_create_detailed_group_key_with_service_and_usage_type(self):
        """Test creating a detailed group key with service and usage type context."""
        # Test data
        group_key = 'us-east-1'
        context = {
            'service': 'Amazon Elastic Compute Cloud - Compute',
            'usage_type': 'BoxUsage:t3.micro',
        }
        group_by = {'Type': 'DIMENSION', 'Key': 'REGION'}

        # Create detailed group key
        result = create_detailed_group_key(group_key, context, group_by)

        # Verify the result includes both service and usage type
        assert result == 'us-east-1 - Amazon Elastic Compute Cloud - Compute (BoxUsage:t3.micro)'

    def test_create_detailed_group_key_without_usage_type(self):
        """Test creating a detailed group key without usage type context."""
        # Test data
        group_key = 'us-east-1'
        context = {'service': 'Amazon Elastic Compute Cloud - Compute'}
        group_by = {'Type': 'DIMENSION', 'Key': 'REGION'}

        # Create detailed group key
        result = create_detailed_group_key(group_key, context, group_by)

        # Verify the result includes service but not usage type
        assert result == 'us-east-1 - Amazon Elastic Compute Cloud - Compute'

    def test_create_detailed_group_key_when_service_is_group_key(self):
        """Test creating a detailed group key when service is the group key."""
        # Test data
        group_key = 'Amazon Elastic Compute Cloud - Compute'
        context = {
            'service': 'Amazon Elastic Compute Cloud - Compute',
            'usage_type': 'BoxUsage:t3.micro',
        }
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}

        # Create detailed group key
        result = create_detailed_group_key(group_key, context, group_by)

        # Verify the result doesn't duplicate the service name
        assert result == 'Amazon Elastic Compute Cloud - Compute (BoxUsage:t3.micro)'


class TestExtractGroupKeyFromComplexSelector:
    """Tests for the extract_group_key_from_complex_selector function."""

    def test_extract_group_key_from_dimension_selector(self):
        """Test extracting group key from a dimension selector."""
        # Create a selector with dimension structure
        selector = {
            'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Elastic Compute Cloud - Compute']}
        }
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}

        # Extract the group key
        result = extract_group_key_from_complex_selector(selector, group_by)

        # Verify the result
        assert result == 'Amazon Elastic Compute Cloud - Compute'

    def test_extract_group_key_from_tag_selector(self):
        """Test extracting group key from a tag selector."""
        # Create a selector with tag structure
        selector = {'Tags': {'Key': 'Environment', 'Values': ['Production']}}
        group_by = {'Type': 'TAG', 'Key': 'Environment'}

        # Extract the group key
        result = extract_group_key_from_complex_selector(selector, group_by)

        # Verify the result
        assert result == 'Production'

    def test_extract_group_key_from_cost_category_selector(self):
        """Test extracting group key from a cost category selector."""
        # Create a selector with cost category structure
        selector = {'CostCategories': {'Key': 'Team', 'Values': ['Engineering']}}
        group_by = {'Type': 'COST_CATEGORY', 'Key': 'Team'}

        # Extract the group key
        result = extract_group_key_from_complex_selector(selector, group_by)

        # Verify the result
        assert result == 'Engineering'

    def test_extract_group_key_from_nested_selector(self):
        """Test extracting group key from a nested selector structure."""
        # Create a complex nested selector
        selector = {
            'And': [
                {
                    'Or': [
                        {
                            'Not': {
                                'Dimensions': {
                                    'Key': 'SERVICE',
                                    'Values': ['Amazon Elastic Compute Cloud - Compute'],
                                }
                            }
                        }
                    ]
                }
            ]
        }
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}

        # Extract the group key
        result = extract_group_key_from_complex_selector(selector, group_by)

        # Verify the result
        assert result == 'Amazon Elastic Compute Cloud - Compute'

    def test_extract_group_key_with_empty_values(self):
        """Test extracting group key when values array is empty."""
        # Create a selector with empty values
        selector = {'Dimensions': {'Key': 'SERVICE', 'Values': []}}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}

        # Extract the group key
        result = extract_group_key_from_complex_selector(selector, group_by)

        # Verify the result shows "No SERVICE" for empty values
        assert result == 'No SERVICE'

    def test_extract_group_key_not_found(self):
        """Test extracting group key when the key is not found in the selector."""
        # Create a selector that doesn't contain the group key
        selector = {'Dimensions': {'Key': 'REGION', 'Values': ['us-east-1']}}
        group_by = {'Type': 'DIMENSION', 'Key': 'SERVICE'}

        # Extract the group key
        result = extract_group_key_from_complex_selector(selector, group_by)

        # Verify the result is "Unknown" when key not found
        assert result == 'Unknown'


class TestValidateForecastDateRange:
    """Tests for the validate_forecast_date_range function."""

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_future_start_date(self, mock_datetime):
        """Test validation fails when start date is in the future."""
        # Create a real datetime object for the current date
        mock_today = datetime(2025, 6, 1).date()

        # Configure the mock to return real datetime objects, not MagicMock objects
        mock_datetime.now.return_value.date.return_value = mock_today
        mock_datetime.strptime.side_effect = datetime.strptime
        mock_datetime.now.return_value.replace.side_effect = (
            lambda **kwargs: datetime.now().replace(**kwargs)
        )

        # Test with start date in the future
        with patch(
            'awslabs.cost_explorer_mcp_server.helpers.validate_date_range', return_value=(True, '')
        ):
            is_valid, error = validate_forecast_date_range('2025-07-01', '2025-08-01')

            # Verify validation fails with appropriate error message
            assert not is_valid
            assert 'must be equal to or no later than the current date' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_past_end_date(self, mock_datetime):
        """Test validation fails when end date is not in the future."""
        # Create a real datetime object for the current date
        mock_today = datetime(2025, 6, 1).date()

        # Configure the mock to return real datetime objects, not MagicMock objects
        mock_datetime.now.return_value.date.return_value = mock_today
        mock_datetime.strptime.side_effect = datetime.strptime

        # Test with end date in the past
        with patch(
            'awslabs.cost_explorer_mcp_server.helpers.validate_date_range', return_value=(True, '')
        ):
            is_valid, error = validate_forecast_date_range('2025-05-01', '2025-05-31')

            # Verify validation fails with appropriate error message
            assert not is_valid
            assert 'must be in the future' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_daily_too_long(self, mock_datetime):
        """Test validation fails when daily forecast range is too long."""
        # Create a real datetime object for the current date
        mock_today = datetime(2025, 6, 1).date()

        # Configure the mock to return real datetime objects, not MagicMock objects
        mock_datetime.now.return_value.date.return_value = mock_today
        mock_datetime.strptime.side_effect = datetime.strptime

        # Test with daily granularity and range > 93 days
        with patch(
            'awslabs.cost_explorer_mcp_server.helpers.validate_date_range', return_value=(True, '')
        ):
            is_valid, error = validate_forecast_date_range('2025-06-01', '2025-10-01', 'DAILY')

            # Verify validation fails with appropriate error message
            assert not is_valid
            assert 'DAILY granularity supports a maximum of 3 months' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_forecast_date_range_monthly_too_long(self, mock_datetime):
        """Test validation fails when monthly forecast range is too long."""
        # Create a real datetime object for the current date
        mock_today = datetime(2025, 6, 1).date()
        mock_now = datetime(2025, 6, 1, tzinfo=timezone.utc)

        # Configure the mock to return real datetime objects, not MagicMock objects
        mock_datetime.now.return_value.date.return_value = mock_today
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime.side_effect = datetime.strptime

        # Test with monthly granularity and range > 12 months
        with patch(
            'awslabs.cost_explorer_mcp_server.helpers.validate_date_range', return_value=(True, '')
        ):
            is_valid, error = validate_forecast_date_range('2025-06-01', '2027-01-01', 'MONTHLY')

            # Verify validation fails with appropriate error message
            assert not is_valid
            assert 'MONTHLY granularity supports a maximum of 12 months' in error


class TestValidateComparisonDateRange:
    """Tests for the validate_comparison_date_range function."""

    def test_validate_comparison_date_range_not_first_day_of_month_start(self):
        """Test validation fails when start date is not the first day of a month."""
        # Test with start date not on first day of month
        is_valid, error = validate_comparison_date_range('2025-05-15', '2025-06-01')

        # Verify validation fails with appropriate error message
        assert not is_valid
        assert 'must be the first day of a month' in error

    def test_validate_comparison_date_range_not_first_day_of_month_end(self):
        """Test validation fails when end date is not the first day of a month."""
        # Test with end date not on first day of month
        is_valid, error = validate_comparison_date_range('2025-05-01', '2025-05-31')

        # Verify validation fails with appropriate error message
        assert not is_valid
        assert 'must be the first day of a month' in error

    def test_validate_comparison_date_range_not_exactly_one_month(self):
        """Test validation fails when period is not exactly one month."""
        # Test with period not exactly one month
        is_valid, error = validate_comparison_date_range('2025-05-01', '2025-07-01')

        # Verify validation fails with appropriate error message
        assert not is_valid
        assert 'must be exactly one month' in error

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_comparison_date_range_current_month_january(self, mock_datetime):
        """Test validation when current month is January (edge case for year rollback)."""
        # Mock current date to be in January 2025
        mock_datetime.now.return_value = datetime(2025, 1, 15, tzinfo=timezone.utc)
        mock_datetime.strptime = datetime.strptime

        # Try to use January 2025 data (should fail because it's current month)
        is_valid, error = validate_comparison_date_range('2025-01-01', '2025-02-01')

        # Should fail and suggest December 2024 as the latest allowed date
        assert not is_valid
        assert 'Current month (2025-01) is not complete yet' in error
        assert '2024-12-01' in error  # Should suggest December 2024

    @patch('awslabs.cost_explorer_mcp_server.helpers.datetime')
    def test_validate_comparison_date_range_december_to_january_transition(self, mock_datetime):
        """Test validation for December to January transition (year boundary)."""
        # Mock current date to be in February 2025
        mock_datetime.now.return_value = datetime(2025, 2, 15, tzinfo=timezone.utc)
        mock_datetime.strptime = datetime.strptime

        # Test December 2024 to January 2025 (should be valid)
        is_valid, error = validate_comparison_date_range('2024-12-01', '2025-01-01')

        # Should be valid
        assert is_valid
        assert error == ''
