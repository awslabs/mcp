"""Helper functions for the Cost Explorer MCP server."""

import logging
from typing import Dict, Any, List
import boto3

# Set up logging
logger = logging.getLogger(__name__)

# Initialize AWS Cost Explorer client
ce = boto3.client('ce')

def get_dimension_values(key: str, billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    """Get available values for a specific dimension."""
    try:
        response = ce.get_dimension_values(
            TimePeriod={
                'Start': billing_period_start,
                'End': billing_period_end
            },
            Dimension=key.upper()
        )
        dimension_values = response['DimensionValues']
        values = [value['Value'] for value in dimension_values]
        return {'dimension': key.upper(), 'values': values}
    except Exception as e:
        logger.error(f"Error getting dimension values: {e}")
        return {'error': str(e)}


def get_tag_values(tag_key: str, billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    """Get available values for a specific tag key."""
    try:
        response = ce.get_tags(
            TimePeriod={'Start': billing_period_start,
                        'End': billing_period_end},
            TagKey=tag_key
        )
        tag_values = response['Tags']
        return {'tag_key': tag_key, 'values': tag_values}
    except Exception as e:
        logger.error(f"Error getting tag values: {e}")
        return {'error': str(e)}



def validate_expression(expression: Dict[str, Any], billing_period_start: str, billing_period_end: str) -> Dict[str, Any]:
    """
    Recursively validate the filter expression.
    
    Args:
        expression: The filter expression to validate
        billing_period_start: Start date of the billing period
        billing_period_end: End date of the billing period
        
    Returns:
        Empty dictionary if valid, or an error dictionary
    """
    try:
        if 'Dimensions' in expression:
            dimension = expression['Dimensions']
            if 'Key' not in dimension or 'Values' not in dimension or 'MatchOptions' not in dimension:
                return {'error': 'Dimensions filter must include "Key", "Values", and "MatchOptions".'}

            dimension_key = dimension['Key']
            dimension_values = dimension['Values']
            valid_values_response = get_dimension_values(
                dimension_key, billing_period_start, billing_period_end)
            if 'error' in valid_values_response:
                return {'error': valid_values_response['error']}
            valid_values = valid_values_response['values']
            for value in dimension_values:
                if value not in valid_values:
                    return {'error': f"Invalid value '{value}' for dimension '{dimension_key}'. Valid values are: {valid_values}"}

        if 'Tags' in expression:
            tag = expression['Tags']
            if 'Key' not in tag or 'Values' not in tag or 'MatchOptions' not in tag:
                return {'error': 'Tags filter must include "Key", "Values", and "MatchOptions".'}

            tag_key = tag['Key']
            tag_values = tag['Values']
            valid_tag_values_response = get_tag_values(
                tag_key, billing_period_start, billing_period_end)
            if 'error' in valid_tag_values_response:
                return {'error': valid_tag_values_response['error']}
            valid_tag_values = valid_tag_values_response['values']
            for value in tag_values:
                if value not in valid_tag_values:
                    return {'error': f"Invalid value '{value}' for tag '{tag_key}'. Valid values are: {valid_tag_values}"}

        if 'CostCategories' in expression:
            cost_category = expression['CostCategories']
            if 'Key' not in cost_category or 'Values' not in cost_category or 'MatchOptions' not in cost_category:
                return {'error': 'CostCategories filter must include "Key", "Values", and "MatchOptions".'}

        logical_operators = ['And', 'Or', 'Not']
        logical_count = sum(1 for op in logical_operators if op in expression)

        if logical_count > 1:
            return {'error': 'Only one logical operator (And, Or, Not) is allowed per expression in filter parameter.'}

        if logical_count == 0 and len(expression) > 1:
            return {'error': 'Filter parameter with multiple expressions require a logical operator (And, Or, Not).'}

        if 'And' in expression:
            if not isinstance(expression['And'], list):
                return {'error': 'And expression must be a list of expressions.'}
            for sub_expression in expression['And']:
                result = validate_expression(
                    sub_expression, billing_period_start, billing_period_end)
                if 'error' in result:
                    return result

        if 'Or' in expression:
            if not isinstance(expression['Or'], list):
                return {'error': 'Or expression must be a list of expressions.'}
            for sub_expression in expression['Or']:
                result = validate_expression(
                    sub_expression, billing_period_start, billing_period_end)
                if 'error' in result:
                    return result

        if 'Not' in expression:
            if not isinstance(expression['Not'], dict):
                return {'error': 'Not expression must be a single expression.'}
            result = validate_expression(
                expression['Not'], billing_period_start, billing_period_end)
            if 'error' in result:
                return result

        if not any(k in expression for k in ['Dimensions', 'Tags', 'CostCategories', 'And', 'Or', 'Not']):
            return {'error': 'Filter Expression must include at least one of the following keys: "Dimensions", "Tags", "CostCategories", "And", "Or", "Not".'}

        return {}
    except Exception as e:
        return {'error': f'Error validating expression: {str(e)}'}


def validate_group_by(group_by: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the group_by parameter.
    
    Args:
        group_by: The group_by dictionary to validate
        
    Returns:
        Empty dictionary if valid, or an error dictionary
    """
    try:
        if not isinstance(group_by, dict) or 'Type' not in group_by or 'Key' not in group_by:
            return {'error': 'group_by must be a dictionary with "Type" and "Key" keys.'}
        
        if group_by['Type'].upper() not in ['DIMENSION', 'TAG', 'COST_CATEGORY']:
            return {'error': 'Invalid group Type. Valid types are DIMENSION, TAG, and COST_CATEGORY.'}
        
        return {}
    except Exception as e:
        return {'error': f'Error validating group_by: {str(e)}'}
