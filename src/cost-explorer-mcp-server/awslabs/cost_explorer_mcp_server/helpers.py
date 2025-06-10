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
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


# Set up logging
logger = logging.getLogger(__name__)

# Initialize AWS Cost Explorer client
ce = boto3.client('ce')


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


def get_dimension_values(
    key: str, billing_period_start: str, billing_period_end: str
) -> Dict[str, Any]:
    """Get available values for a specific dimension."""
    # Validate date formats
    is_valid_start, error_start = validate_date_format(billing_period_start)
    if not is_valid_start:
        return {'error': error_start}

    is_valid_end, error_end = validate_date_format(billing_period_end)
    if not is_valid_end:
        return {'error': error_end}

    # Validate date range
    if billing_period_start > billing_period_end:
        return {
            'error': f"Start date '{billing_period_start}' cannot be after end date '{billing_period_end}'"
        }

    try:
        response = ce.get_dimension_values(
            TimePeriod={'Start': billing_period_start, 'End': billing_period_end},
            Dimension=key.upper(),
        )
        dimension_values = response['DimensionValues']
        values = [value['Value'] for value in dimension_values]
        return {'dimension': key.upper(), 'values': values}
    except Exception as e:
        logger.error(f'Error getting dimension values: {e}')
        return {'error': str(e)}


def get_tag_values(
    tag_key: str, billing_period_start: str, billing_period_end: str
) -> Dict[str, Any]:
    """Get available values for a specific tag key."""
    # Validate date formats
    is_valid_start, error_start = validate_date_format(billing_period_start)
    if not is_valid_start:
        return {'error': error_start}

    is_valid_end, error_end = validate_date_format(billing_period_end)
    if not is_valid_end:
        return {'error': error_end}

    # Validate date range
    if billing_period_start > billing_period_end:
        return {
            'error': f"Start date '{billing_period_start}' cannot be after end date '{billing_period_end}'"
        }

    try:
        response = ce.get_tags(
            TimePeriod={'Start': billing_period_start, 'End': billing_period_end},
            TagKey=tag_key,
        )
        tag_values = response['Tags']
        return {'tag_key': tag_key, 'values': tag_values}
    except Exception as e:
        logger.error(f'Error getting tag values: {e}')
        return {'error': str(e)}


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
    # Validate date formats
    is_valid_start, error_start = validate_date_format(billing_period_start)
    if not is_valid_start:
        return {'error': error_start}

    is_valid_end, error_end = validate_date_format(billing_period_end)
    if not is_valid_end:
        return {'error': error_end}

    # Validate date range
    if billing_period_start > billing_period_end:
        return {
            'error': f"Start date '{billing_period_start}' cannot be after end date '{billing_period_end}'"
        }

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

            dimension_key = dimension['Key']
            dimension_values = dimension['Values']
            valid_values_response = get_dimension_values(
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

            tag_key = tag['Key']
            tag_values = tag['Values']
            valid_tag_values_response = get_tag_values(
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

        if group_by['Type'].upper() not in ['DIMENSION', 'TAG', 'COST_CATEGORY']:
            return {
                'error': 'Invalid group Type. Valid types are DIMENSION, TAG, and COST_CATEGORY.'
            }

        return {}
    except Exception as e:
        return {'error': f'Error validating group_by: {str(e)}'}
