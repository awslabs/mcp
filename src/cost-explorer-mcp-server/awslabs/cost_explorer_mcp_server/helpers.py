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

"""Helper functions for the Cost Explorer MCP server."""

import boto3
import os
import re
import sys
from awslabs.cost_explorer_mcp_server.constants import (
    VALID_DIMENSIONS,
    VALID_GROUP_BY_DIMENSIONS,
    VALID_GROUP_BY_TYPES,
    VALID_MATCH_OPTIONS,
)
from datetime import datetime, timezone
from loguru import logger
from typing import Any, Dict, Optional, Tuple


# Configure Loguru logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Global client cache
_cost_explorer_client = None


def get_cost_explorer_client():
    """Get Cost Explorer client with proper session management and caching.

    Returns:
        boto3.client: Configured Cost Explorer client (cached after first call)
    """
    global _cost_explorer_client

    if _cost_explorer_client is None:
        try:
            # Read environment variables dynamically
            aws_region = os.environ.get('AWS_REGION', 'us-east-1')
            aws_profile = os.environ.get('AWS_PROFILE')

            if aws_profile:
                _cost_explorer_client = boto3.Session(
                    profile_name=aws_profile, region_name=aws_region
                ).client('ce')
            else:
                _cost_explorer_client = boto3.Session(region_name=aws_region).client('ce')
        except Exception as e:
            logger.error(f'Error creating Cost Explorer client: {str(e)}')
            raise

    return _cost_explorer_client


def validate_dimension_key(dimension_key: str) -> Dict[str, Any]:
    """Validate that the dimension key is supported by AWS Cost Explorer.

    Args:
        dimension_key: The dimension key to validate

    Returns:
        Empty dictionary if valid, or an error dictionary
    """
    try:
        dimension_upper = dimension_key.upper()
        if dimension_upper not in VALID_DIMENSIONS:
            return {
                'error': f"Invalid dimension key '{dimension_key}'. Valid dimensions are: {', '.join(VALID_DIMENSIONS)}"
            }
        return {}
    except Exception as e:
        return {'error': f'Error validating dimension key: {str(e)}'}


def get_available_dimension_values(
    key: str, billing_period_start: str, billing_period_end: str
) -> Dict[str, Any]:
    """Get available values for a specific dimension."""
    # Validate dimension key first
    dimension_validation = validate_dimension_key(key)
    if 'error' in dimension_validation:
        return dimension_validation

    # Validate date range (no granularity constraint for dimension values)
    is_valid, error_message = validate_date_range(billing_period_start, billing_period_end)
    if not is_valid:
        return {'error': error_message}

    try:
        ce = get_cost_explorer_client()
        response = ce.get_dimension_values(
            TimePeriod={'Start': billing_period_start, 'End': billing_period_end},
            Dimension=key.upper(),
        )
        dimension_values = response['DimensionValues']
        values = [value['Value'] for value in dimension_values]
        return {'dimension': key.upper(), 'values': values}
    except Exception as e:
        logger.error(
            f'Error getting dimension values for {key.upper()} ({billing_period_start} to {billing_period_end}): {e}'
        )
        return {'error': str(e)}


def get_available_tag_values(
    tag_key: str, billing_period_start: str, billing_period_end: str
) -> Dict[str, Any]:
    """Get available values for a specific tag key."""
    # Validate date range (no granularity constraint for tag values)
    is_valid, error_message = validate_date_range(billing_period_start, billing_period_end)
    if not is_valid:
        return {'error': error_message}

    try:
        ce = get_cost_explorer_client()
        response = ce.get_tags(
            TimePeriod={'Start': billing_period_start, 'End': billing_period_end},
            TagKey=tag_key,
        )
        tag_values = response['Tags']
        return {'tag_key': tag_key, 'values': tag_values}
    except Exception as e:
        logger.error(
            f'Error getting tag values for {tag_key} ({billing_period_start} to {billing_period_end}): {e}'
        )
        return {'error': str(e)}


def validate_date_format(date_str: str) -> Tuple[bool, str]:
    """Validate that a date string is in YYYY-MM-DD format and is a valid date.

    Args:
        date_str: The date string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check format with regex
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False, f"Date '{date_str}' is not in YYYY-MM-DD format"

    # Check if it's a valid date
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True, ''
    except ValueError as e:
        return False, f"Invalid date '{date_str}': {str(e)}"


def format_date_for_api(date_str: str, granularity: str) -> str:
    """Format date string appropriately for AWS Cost Explorer API based on granularity.

    Args:
        date_str: Date string in YYYY-MM-DD format
        granularity: The granularity (DAILY, MONTHLY, HOURLY)

    Returns:
        Formatted date string appropriate for the API call
    """
    if granularity.upper() == 'HOURLY':
        # For hourly granularity, AWS expects datetime format
        # Convert YYYY-MM-DD to YYYY-MM-DDTHH:MM:SSZ
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%dT00:00:00Z')
    else:
        # For DAILY and MONTHLY, use the original date format
        return date_str


def validate_date_range(
    start_date: str, end_date: str, granularity: Optional[str] = None
) -> Tuple[bool, str]:
    """Validate date range with format and logical checks.

    Args:
        start_date: The start date string in YYYY-MM-DD format
        end_date: The end date string in YYYY-MM-DD format
        granularity: Optional granularity to check specific constraints

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate start date format
    is_valid_start, error_start = validate_date_format(start_date)
    if not is_valid_start:
        return False, error_start

    # Validate end date format
    is_valid_end, error_end = validate_date_format(end_date)
    if not is_valid_end:
        return False, error_end

    # Validate date range logic
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    if start_dt > end_dt:
        return False, f"Start date '{start_date}' cannot be after end date '{end_date}'"

    # Validate granularity-specific constraints
    if granularity and granularity.upper() == 'HOURLY':
        # HOURLY granularity supports maximum 14 days
        date_diff = (end_dt - start_dt).days
        if date_diff > 14:
            return (
                False,
                f'HOURLY granularity supports a maximum of 14 days. Current range is {date_diff} days ({start_date} to {end_date}). Please use a shorter date range.',
            )

    return True, ''


def validate_match_options(match_options: list, filter_type: str) -> Dict[str, Any]:
    """Validate MatchOptions based on filter type.

    Args:
        match_options: List of match options to validate
        filter_type: Type of filter ('Dimensions', 'Tags', 'CostCategories')

    Returns:
        Empty dictionary if valid, or an error dictionary
    """
    if filter_type not in VALID_MATCH_OPTIONS:
        return {'error': f'Unknown filter type: {filter_type}'}

    valid_options = VALID_MATCH_OPTIONS[filter_type]

    for option in match_options:
        if option not in valid_options:
            return {
                'error': f"Invalid MatchOption '{option}' for {filter_type}. Valid values are: {valid_options}"
            }

    return {}


def validate_expression(
    expression: Dict[str, Any], billing_period_start: str, billing_period_end: str
) -> Dict[str, Any]:
    """Recursively validate the filter expression.

    Args:
        expression: The filter expression to validate
        billing_period_start: Start date of the billing period
        billing_period_end: End date of the billing period

    Returns:
        Empty dictionary if valid, or an error dictionary
    """
    # Validate date range (no granularity constraint for filter validation)
    is_valid, error_message = validate_date_range(billing_period_start, billing_period_end)
    if not is_valid:
        return {'error': error_message}

    try:
        if 'Dimensions' in expression:
            dimension = expression['Dimensions']
            if (
                'Key' not in dimension
                or 'Values' not in dimension
                or 'MatchOptions' not in dimension
            ):
                return {
                    'error': 'Dimensions filter must include "Key", "Values", and "MatchOptions".'
                }

            # Validate MatchOptions for Dimensions
            match_options_result = validate_match_options(dimension['MatchOptions'], 'Dimensions')
            if 'error' in match_options_result:
                return match_options_result

            dimension_key = dimension['Key']
            dimension_values = dimension['Values']
            valid_values_response = get_available_dimension_values(
                dimension_key, billing_period_start, billing_period_end
            )
            if 'error' in valid_values_response:
                return {'error': valid_values_response['error']}
            valid_values = valid_values_response['values']
            for value in dimension_values:
                if value not in valid_values:
                    return {
                        'error': f"Invalid value '{value}' for dimension '{dimension_key}'. Valid values are: {valid_values}"
                    }

        if 'Tags' in expression:
            tag = expression['Tags']
            if 'Key' not in tag or 'Values' not in tag or 'MatchOptions' not in tag:
                return {'error': 'Tags filter must include "Key", "Values", and "MatchOptions".'}

            # Validate MatchOptions for Tags
            match_options_result = validate_match_options(tag['MatchOptions'], 'Tags')
            if 'error' in match_options_result:
                return match_options_result

            tag_key = tag['Key']
            tag_values = tag['Values']
            valid_tag_values_response = get_available_tag_values(
                tag_key, billing_period_start, billing_period_end
            )
            if 'error' in valid_tag_values_response:
                return {'error': valid_tag_values_response['error']}
            valid_tag_values = valid_tag_values_response['values']
            for value in tag_values:
                if value not in valid_tag_values:
                    return {
                        'error': f"Invalid value '{value}' for tag '{tag_key}'. Valid values are: {valid_tag_values}"
                    }

        if 'CostCategories' in expression:
            cost_category = expression['CostCategories']
            if (
                'Key' not in cost_category
                or 'Values' not in cost_category
                or 'MatchOptions' not in cost_category
            ):
                return {
                    'error': 'CostCategories filter must include "Key", "Values", and "MatchOptions".'
                }

            # Validate MatchOptions for CostCategories
            match_options_result = validate_match_options(
                cost_category['MatchOptions'], 'CostCategories'
            )
            if 'error' in match_options_result:
                return match_options_result

        logical_operators = ['And', 'Or', 'Not']
        logical_count = sum(1 for op in logical_operators if op in expression)

        if logical_count > 1:
            return {
                'error': 'Only one logical operator (And, Or, Not) is allowed per expression in filter parameter.'
            }

        if logical_count == 0 and len(expression) > 1:
            return {
                'error': 'Filter parameter with multiple expressions require a logical operator (And, Or, Not).'
            }

        if 'And' in expression:
            if not isinstance(expression['And'], list):
                return {'error': 'And expression must be a list of expressions.'}
            for sub_expression in expression['And']:
                result = validate_expression(
                    sub_expression, billing_period_start, billing_period_end
                )
                if 'error' in result:
                    return result

        if 'Or' in expression:
            if not isinstance(expression['Or'], list):
                return {'error': 'Or expression must be a list of expressions.'}
            for sub_expression in expression['Or']:
                result = validate_expression(
                    sub_expression, billing_period_start, billing_period_end
                )
                if 'error' in result:
                    return result

        if 'Not' in expression:
            if not isinstance(expression['Not'], dict):
                return {'error': 'Not expression must be a single expression.'}
            result = validate_expression(
                expression['Not'], billing_period_start, billing_period_end
            )
            if 'error' in result:
                return result

        if not any(
            k in expression for k in ['Dimensions', 'Tags', 'CostCategories', 'And', 'Or', 'Not']
        ):
            return {
                'error': 'Filter Expression must include at least one of the following keys: "Dimensions", "Tags", "CostCategories", "And", "Or", "Not".'
            }

        return {}
    except Exception as e:
        return {'error': f'Error validating expression: {str(e)}'}


def validate_group_by(group_by: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate the group_by parameter.

    Args:
        group_by: The group_by dictionary to validate

    Returns:
        Empty dictionary if valid, or an error dictionary
    """
    try:
        if (
            group_by is None
            or not isinstance(group_by, dict)
            or 'Type' not in group_by
            or 'Key' not in group_by
        ):
            return {'error': 'group_by must be a dictionary with "Type" and "Key" keys.'}

        group_type = group_by['Type'].upper()
        group_key = group_by['Key']

        if group_type not in VALID_GROUP_BY_TYPES:
            return {
                'error': f'Invalid group Type: {group_type}. Valid types are {", ".join(VALID_GROUP_BY_TYPES)}.'
            }

        # Validate dimension key if type is DIMENSION
        if group_type == 'DIMENSION':
            dimension_upper = group_key.upper()
            if dimension_upper not in VALID_GROUP_BY_DIMENSIONS:
                return {
                    'error': f'Invalid dimension key for GROUP BY: {group_key}. Valid values for the DIMENSION type are {", ".join(VALID_GROUP_BY_DIMENSIONS)}.'
                }

        return {}
    except Exception as e:
        return {'error': f'Error validating group_by: {str(e)}'}


def validate_forecast_date_range(
    start_date: str, end_date: str, granularity: str = 'MONTHLY'
) -> Tuple[bool, str]:
    """Validate that forecast dates meet AWS Cost Explorer requirements.

    Args:
        start_date: The forecast start date string in YYYY-MM-DD format
        end_date: The forecast end date string in YYYY-MM-DD format
        granularity: The granularity for the forecast (DAILY or MONTHLY)

    Returns:
        Tuple of (is_valid, error_message)
    """
    # First validate basic date format and range
    is_valid, error = validate_date_range(start_date, end_date)
    if not is_valid:
        return False, error

    today = datetime.now(timezone.utc).date()
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    # AWS requires start date to be equal to or no later than current date
    if start_dt > today:
        return (
            False,
            f"Forecast start date '{start_date}' must be equal to or no later than the current date ({today})",
        )

    # End date must be in the future
    if end_dt <= today:
        return False, f"Forecast end date '{end_date}' must be in the future (after {today})"

    # AWS Cost Explorer forecast granularity-specific limits
    date_diff = (end_dt - start_dt).days

    if granularity.upper() == 'DAILY':
        # DAILY forecasts support maximum 3 months (approximately 93 days)
        if date_diff > 93:
            return (
                False,
                f'DAILY granularity supports a maximum of 3 months (93 days). Current range is {date_diff} days ({start_date} to {end_date}). Please use a shorter date range or MONTHLY granularity.',
            )
    elif granularity.upper() == 'MONTHLY':
        # MONTHLY forecasts support maximum 12 months
        max_forecast_date = datetime.now(timezone.utc).date().replace(year=today.year + 1)
        if end_dt > max_forecast_date:
            return (
                False,
                f"MONTHLY granularity supports a maximum of 12 months in the future. Forecast end date '{end_date}' exceeds the limit (max: {max_forecast_date}).",
            )

    return True, ''


def validate_comparison_date_range(start_date: str, end_date: str) -> Tuple[bool, str]:
    """Validate that comparison dates meet AWS Cost Explorer comparison API requirements.

    Args:
        start_date: The start date string in YYYY-MM-DD format
        end_date: The end date string in YYYY-MM-DD format

    Returns:
        Tuple of (is_valid, error_message)
    """
    # First validate basic date format and range
    is_valid, error = validate_date_range(start_date, end_date)
    if not is_valid:
        return False, error

    today = datetime.now(timezone.utc).date()
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    # AWS requires start date to be equal to or no later than current date
    if start_dt > today:
        return (
            False,
            f"Comparison start date '{start_date}' must be equal to or no later than the current date ({today})",
        )

    # Must start on the first day of a month
    if start_dt.day != 1:
        return (
            False,
            f"Comparison start date '{start_date}' must be the first day of a month (e.g., 2025-01-01)",
        )

    # Must end on the first day of a month (exclusive end date)
    if end_dt.day != 1:
        return (
            False,
            f"Comparison end date '{end_date}' must be the first day of a month (e.g., 2025-02-01)",
        )

    # Comparison periods can only go up to the last complete month
    # Calculate the first day of current month (last complete month boundary)
    current_month_start = today.replace(day=1)
    # The comparison period (start_date) cannot be in the current month or future
    if start_dt >= current_month_start:
        # Calculate last complete month for user guidance
        if current_month_start.month == 1:
            last_complete_month = current_month_start.replace(
                year=current_month_start.year - 1, month=12
            )
        else:
            last_complete_month = current_month_start.replace(month=current_month_start.month - 1)
        return (
            False,
            f'Comparison periods can only include complete months. Current month ({current_month_start.strftime("%Y-%m")}) is not complete yet. Latest allowed start date: {last_complete_month.strftime("%Y-%m-%d")}',
        )

    # Must be exactly one month duration
    # Calculate expected end date (first day of next month)
    if start_dt.month == 12:
        expected_end = start_dt.replace(year=start_dt.year + 1, month=1)
    else:
        expected_end = start_dt.replace(month=start_dt.month + 1)

    if end_dt != expected_end:
        return (
            False,
            f"Comparison period must be exactly one month. For start date '{start_date}', end date should be '{expected_end.strftime('%Y-%m-%d')}'",
        )

    # Check 13-month lookback limit (38 months if multi-year enabled, but we'll use 13 as conservative)
    thirteen_months_ago = today.replace(day=1)
    for _ in range(13):
        if thirteen_months_ago.month == 1:
            thirteen_months_ago = thirteen_months_ago.replace(
                year=thirteen_months_ago.year - 1, month=12
            )
        else:
            thirteen_months_ago = thirteen_months_ago.replace(month=thirteen_months_ago.month - 1)

    if start_dt < thirteen_months_ago:
        return (
            False,
            f"Comparison start date '{start_date}' cannot be more than 13 months ago (earliest: {thirteen_months_ago.strftime('%Y-%m-%d')})",
        )

    return True, ''


def extract_group_key_from_complex_selector(
    selector: Dict[str, Any], group_by: Dict[str, str]
) -> str:
    """Extract group key from complex CostSelector structures dynamically.

    Args:
        selector: The CostSelector dictionary from API response
        group_by: The GroupBy dictionary with Type and Key

    Returns:
        String representing the group key
    """
    group_type = group_by.get('Type', '').upper()
    group_key = group_by.get('Key', '')

    def search_for_group_key(sel_part):
        """Recursively search for the group key in any part of the selector."""
        if isinstance(sel_part, dict):
            # Check if this is the structure we're looking for
            if group_type == 'DIMENSION' and 'Dimensions' in sel_part:
                dim_info = sel_part['Dimensions']
                if dim_info.get('Key') == group_key and 'Values' in dim_info:
                    values = dim_info['Values']
                    return values[0] if values and values[0] else f'No {group_key}'

            elif group_type == 'TAG' and 'Tags' in sel_part:
                tag_info = sel_part['Tags']
                if tag_info.get('Key') == group_key and 'Values' in tag_info:
                    values = tag_info['Values']
                    return values[0] if values and values[0] else f'No {group_key}'

            elif group_type == 'COST_CATEGORY' and 'CostCategories' in sel_part:
                cc_info = sel_part['CostCategories']
                if cc_info.get('Key') == group_key and 'Values' in cc_info:
                    values = cc_info['Values']
                    return values[0] if values and values[0] else f'No {group_key}'

            # Recursively search in nested structures
            for key, value in sel_part.items():
                if key in ['And', 'Or'] and isinstance(value, list):
                    for item in value:
                        result = search_for_group_key(item)
                        if result:
                            return result
                elif key == 'Not' and isinstance(value, dict):
                    result = search_for_group_key(value)
                    if result:
                        return result

        return None

    result = search_for_group_key(selector)
    return result if result else 'Unknown'


def extract_usage_context_from_selector(selector: Dict[str, Any]) -> Dict[str, str]:
    """Extract all available context from complex selectors dynamically.

    Args:
        selector: The CostSelector dictionary from API response

    Returns:
        Dictionary with all available context information
    """
    context = {}

    def extract_from_structure(sel_part):
        """Recursively extract context from any part of the selector."""
        if isinstance(sel_part, dict):
            # Extract from Dimensions
            if 'Dimensions' in sel_part:
                dim_info = sel_part['Dimensions']
                key = dim_info.get('Key', '')
                values = dim_info.get('Values', [])
                if values and values[0]:  # Skip empty values
                    context[key.lower()] = values[0]

            # Extract from Tags
            if 'Tags' in sel_part:
                tag_info = sel_part['Tags']
                tag_key = tag_info.get('Key', '')
                values = tag_info.get('Values', [])
                if values and values[0]:
                    context[f'tag_{tag_key.lower()}'] = values[0]

            # Extract from CostCategories
            if 'CostCategories' in sel_part:
                cc_info = sel_part['CostCategories']
                cc_key = cc_info.get('Key', '')
                values = cc_info.get('Values', [])
                if values and values[0]:
                    context[f'category_{cc_key.lower()}'] = values[0]

            # Recursively process nested structures
            for key, value in sel_part.items():
                if key in ['And', 'Or'] and isinstance(value, list):
                    for item in value:
                        extract_from_structure(item)
                elif key == 'Not' and isinstance(value, dict):
                    extract_from_structure(value)

    extract_from_structure(selector)
    return context


def create_detailed_group_key(
    group_key: str, context: Dict[str, str], group_by: Dict[str, str]
) -> str:
    """Create a detailed group key that includes relevant context.

    Since AWS always includes SERVICE and USAGE_TYPE, we can use them for context.

    Args:
        group_key: The primary group key extracted from the selector
        context: Additional context from the selector
        group_by: The GroupBy dictionary with Type and Key

    Returns:
        Enhanced group key with context
    """
    # Get the always-present context
    service = context.get('service', '')
    usage_type = context.get('usage_type', '')

    # Create a meaningful key based on what's available
    parts = [group_key]

    # Add service context if it's not the group key itself
    if service and group_by.get('Key') != 'SERVICE':
        parts.append(service)

    # Add usage type in parentheses for specificity
    if usage_type:
        return f'{" - ".join(parts)} ({usage_type})'

    return ' - '.join(parts)
