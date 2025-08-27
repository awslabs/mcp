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

"""Helper functions for AWS Cost Optimization Hub operations.

These functions handle the specific operations for the Cost Optimization Hub tool.
"""

from ..utilities.aws_service_base import format_response
from ..utilities.logging_utils import get_context_logger
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import Context
from typing import Any, Dict, Optional


def format_timestamp(timestamp: Any) -> Optional[str]:
    """Format a timestamp to ISO format string.

    Args:
        timestamp: Timestamp from Cost Optimization Hub API

    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return None

    try:
        # Check if it's already a datetime object
        if isinstance(timestamp, datetime):
            return timestamp.isoformat()
        else:
            # Assume it's a Unix timestamp in milliseconds
            from datetime import timezone

            return (
                datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                .astimezone()
                .replace(tzinfo=None)
                .isoformat()
            )
    except Exception as e:
        return str(f'Error: {e}, Timestamp: {timestamp}')


async def list_recommendations(
    ctx: Context,
    coh_client: Any,
    max_results: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
    include_all_recommendations: Optional[bool] = None,
) -> Dict[str, Any]:
    """List recommendations from Cost Optimization Hub.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        max_results: Maximum total results to return across all pages; None means all available
        filters: Optional filters dictionary
        include_all_recommendations: Whether to include all recommendations

    Returns:
        Dict containing recommendations from all pages
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            'includeAllRecommendations': bool(include_all_recommendations or False)
        }

        if filters:
            request_params['filter'] = dict(filters)

        # Initialize collection for all recommendations across pages
        all_recommendations = []
        current_token = None
        page_count = 0

        # Loop to handle pagination automatically
        while True:
            # Update token if we're on a subsequent page
            if current_token:
                request_params['nextToken'] = current_token

            # Add max_results for this page
            if max_results:
                remaining_results = max_results - len(all_recommendations)
                if remaining_results <= 0:
                    break
                request_params['maxResults'] = min(100, remaining_results)
            else:
                request_params['maxResults'] = 100

            # Make the API call for this page
            page_count += 1
            await ctx_logger.info(
                f'Fetching page {page_count} of recommendations from Cost Optimization Hub'
            )
            response = coh_client.list_recommendations(**request_params)

            # Process this page of recommendations
            recommendations = response.get('items', [])
            await ctx_logger.info(
                f'Retrieved {len(recommendations)} recommendations on page {page_count}'
            )

            # Add recommendations from this page to our collection
            all_recommendations.extend(recommendations)

            # Check if we've reached the user's requested max_results
            if max_results and len(all_recommendations) >= max_results:
                # Truncate to exact max_results
                all_recommendations = all_recommendations[:max_results]
                await ctx_logger.info(f'Reached user-specified maximum of {max_results} results')
                break

            # Check for next page
            current_token = response.get('nextToken')

            # If no more pages, break the loop
            if not current_token:
                break

        # Format all collected recommendations
        formatted_recommendations = []

        await ctx_logger.info(
            f'Processing {len(all_recommendations)} total recommendations from {page_count} page(s)'
        )

        # Handle empty recommendations
        if not all_recommendations:
            await ctx_logger.info('No recommendations found across any pages')
            return format_response(
                'success',
                {
                    'recommendations': [],
                },
            )

        # Process all recommendations
        for item in all_recommendations:
            recommendation = {
                'recommendation_id': item.get('recommendationId'),
                'account_id': item.get('accountId'),
                'region': item.get('region'),
                'resource_id': item.get('resourceId'),
                'resource_arn': item.get('resourceArn'),
                'action_type': item.get('actionType'),
                'current_resource_type': item.get('currentResourceType'),
                'recommended_resource_type': item.get('recommendedResourceType'),
                'current_resource_summary': item.get('currentResourceSummary'),
                'recommended_resource_summary': item.get('recommendedResourceSummary'),
                'estimated_monthly_savings': item.get('estimatedMonthlySavings'),
                'estimated_savings_percentage': item.get('estimatedSavingsPercentage'),
                'estimated_monthly_cost': item.get('estimatedMonthlyCost'),
                'currency_code': item.get('currencyCode'),
                'implementation_effort': item.get('implementationEffort'),
                'last_refresh_timestamp': format_timestamp(item.get('lastRefreshTimestamp')),
                'lookback_period_in_days': item.get('recommendationLookbackPeriodInDays'),
            }
            formatted_recommendations.append(recommendation)

        # Return formatted response
        return format_response(
            'success',
            {
                'recommendations': formatted_recommendations,
            },
        )

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')

        if error_code == 'ValidationException':
            await ctx_logger.warning(f'Cost Optimization Hub validation error: {error_message}')
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                f'Cost Optimization Hub validation error: {error_message}',
            )
        elif error_code == 'AccessDeniedException':
            await ctx_logger.error(f'Access denied for Cost Optimization Hub: {error_message}')
            return format_response(
                'error',
                {'error_code': error_code},
                'Access denied for Cost Optimization Hub. Ensure you have the necessary permissions: cost-optimization-hub:ListRecommendations.',
            )
        elif error_code == 'ResourceNotFoundException':
            await ctx_logger.warning(f'Cost Optimization Hub resource not found: {error_message}')
            return format_response(
                'error',
                {'error_code': error_code},
                'Cost Optimization Hub resources not found. The service may not be enabled in this account or region.',
            )
        else:
            # Re-raise for other errors to be handled by the parent try-catch
            raise

    except Exception as e:
        # Let the parent try-catch handle other exceptions
        await ctx_logger.error(f'Unexpected error in list_recommendations: {str(e)}')
        raise


async def get_recommendation(
    ctx: Context, coh_client: Any, resource_id: str, resource_type: str
) -> Dict[str, Any]:
    """Get detailed information about a specific recommendation.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        resource_id: Recommendation ID to retrieve
        resource_type: Resource type (for compatibility, not used in API call)

    Returns:
        Dict containing detailed recommendation information
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Prepare the request parameters
        request_params = {'recommendationId': resource_id}

        # Make the API call
        await ctx_logger.info(f'Fetching recommendation {resource_id}')
        response = coh_client.get_recommendation(**request_params)

        # The response IS the recommendation data
        recommendation = response

        if not recommendation:
            await ctx_logger.warning(
                f'No recommendation found for resource {resource_id} of type {resource_type}'
            )
            return format_response(
                'warning',
                {
                    'resource_id': resource_id,
                    'resource_type': resource_type,
                    'message': 'No recommendation found for the specified resource.',
                },
                'No recommendation found. The resource may not have optimization opportunities, or the resource ID/type may be incorrect.',
            )

        # Build response using actual API fields
        formatted_response = {
            'recommendation_id': recommendation.get('recommendationId'),
            'account_id': recommendation.get('accountId'),
            'resource_id': recommendation.get('resourceId'),
            'resource_arn': recommendation.get('resourceArn'),
            'current_resource_type': recommendation.get('currentResourceType'),
            'recommended_resource_type': recommendation.get('recommendedResourceType'),
            'region': recommendation.get('region'),
            'action_type': recommendation.get('actionType'),
            'estimated_monthly_savings': recommendation.get('estimatedMonthlySavings'),
            'estimated_savings_percentage': recommendation.get('estimatedSavingsPercentage'),
            'estimated_monthly_cost': recommendation.get('estimatedMonthlyCost'),
            'currency_code': recommendation.get('currencyCode'),
            'implementation_effort': recommendation.get('implementationEffort'),
            'source': recommendation.get('source'),
            'last_refresh_timestamp': str(recommendation.get('lastRefreshTimestamp')),
            'lookback_period_in_days': recommendation.get('recommendationLookbackPeriodInDays'),
            'cost_calculation_lookback_period_in_days': recommendation.get(
                'costCalculationLookbackPeriodInDays'
            ),
            'restart_needed': recommendation.get('restartNeeded'),
            'rollback_possible': recommendation.get('rollbackPossible'),
        }

        # Add complex nested fields if they exist
        if 'recommendedResourceDetails' in recommendation:
            formatted_response['recommended_resource_details'] = recommendation.get(
                'recommendedResourceDetails'
            )

        if 'tags' in recommendation:
            formatted_response['tags'] = recommendation.get('tags')

        # Return formatted response
        return format_response('success', formatted_response)

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')

        if error_code == 'ValidationException':
            await ctx_logger.warning(f'Validation error in get_recommendation: {error_message}')
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                f'Cost Optimization Hub validation error: {error_message}',
            )
        elif error_code == 'AccessDeniedException':
            await ctx_logger.error(
                f'Access denied for Cost Optimization Hub get_recommendation: {error_message}'
            )
            return format_response(
                'error',
                {'error_code': error_code},
                'Access denied for Cost Optimization Hub. Ensure you have the necessary permissions: cost-optimization-hub:GetRecommendation.',
            )
        elif error_code == 'ResourceNotFoundException':
            await ctx_logger.warning(f'Resource not found: {error_message}')
            return format_response(
                'warning',
                {
                    'error_code': error_code,
                    'resource_id': resource_id,
                    'resource_type': resource_type,
                },
                f'Resource {resource_id} of type {resource_type} not found in Cost Optimization Hub.',
            )
        else:
            # Re-raise for other errors
            raise

    except Exception as e:
        await ctx_logger.error(f'Unexpected error in get_recommendation: {str(e)}')
        raise


async def list_recommendation_summaries(
    ctx: Context,
    coh_client: Any,
    group_by: str,
    max_results: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """List recommendation summaries from Cost Optimization Hub.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        group_by: Grouping parameter
        max_results: Maximum total results to return across all pages; None means all available
        filters: Optional filters dictionary

    Returns:
        Dict containing recommendation summaries from all pages
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Prepare the request parameters
        request_params: Dict[str, Any] = {'groupBy': str(group_by)}

        if filters:
            request_params['filter'] = dict(filters)

        # Initialize collection for all summaries across pages
        all_summaries = []
        current_token = None
        page_count = 0
        response = None  # Initialize to store last response

        # Loop to handle pagination automatically
        while True:
            # Update token if we're on a subsequent page
            if current_token:
                request_params['nextToken'] = current_token

            # Add max_results for this page
            if max_results:
                remaining_results = max_results - len(all_summaries)
                if remaining_results <= 0:
                    break
                request_params['maxResults'] = min(100, remaining_results)
            else:
                request_params['maxResults'] = 100

            # Make the API call for this page
            page_count += 1
            await ctx_logger.info(
                f'Fetching page {page_count} of recommendation summaries grouped by {group_by}'
            )
            response = coh_client.list_recommendation_summaries(**request_params)

            # Process this page of summaries
            summaries = response.get('items', [])
            await ctx_logger.info(
                f'Retrieved {len(summaries)} recommendation summaries on page {page_count}'
            )

            # Add summaries from this page to our collection
            all_summaries.extend(summaries)

            # Check if we've reached the user's requested max_results
            if max_results and len(all_summaries) >= max_results:
                # Truncate to exact max_results
                all_summaries = all_summaries[:max_results]
                await ctx_logger.info(f'Reached user-specified maximum of {max_results} results')
                break

            # Check for next page
            current_token = response.get('nextToken')

            # If no more pages, break the loop
            if not current_token:
                break

        # Format all collected summaries
        formatted_summaries = []

        await ctx_logger.info(
            f'Processing {len(all_summaries)} total recommendation summaries from {page_count} page(s)'
        )

        # Handle empty summaries
        if not all_summaries:
            await ctx_logger.info('No recommendation summaries found across any pages')
            formatted_response = {
                'group_by': group_by,
                'currency_code': 'USD',
                'estimated_total_savings': 0,
                'summaries': [],
            }
            return format_response('success', formatted_response)

        # Process all summaries
        for item in all_summaries:
            formatted_summary = {
                'group': item.get('group'),
                'estimated_monthly_savings': item.get('estimatedMonthlySavings'),
                'recommendation_count': item.get('recommendationCount'),
            }
            formatted_summaries.append(formatted_summary)

        # Format response
        formatted_response = {
            'group_by': response.get('groupBy') if response else group_by,
            'currency_code': response.get('currencyCode', 'USD') if response else 'USD',
            'estimated_total_savings': response.get('estimatedTotalDedupedSavings')
            if response
            else None,
            'summaries': formatted_summaries,
        }

        # Add metrics if present
        if response and 'metrics' in response:
            formatted_response['metrics'] = {
                'savings_percentage': response['metrics'].get('savingsPercentage')
            }

        # Return formatted response
        return format_response('success', formatted_response)

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')
        await ctx_logger.error(
            f'AWS ClientError in list_recommendation_summaries: {error_code} - {error_message}'
        )

        if error_code == 'ValidationException':
            return format_response(
                'error',
                {
                    'error_code': error_code,
                    'error_message': error_message,
                    'valid_group_by_values': [
                        'ACCOUNT_ID',
                        'RECOMMENDATION_TYPE',
                        'RESOURCE_TYPE',
                        'TAG',
                        'USAGE_TYPE',
                    ],
                },
                f'Invalid parameters for recommendation summaries: {error_message}. Valid group_by values are: ACCOUNT_ID, RECOMMENDATION_TYPE, RESOURCE_TYPE, TAG, USAGE_TYPE.',
            )
        elif error_code in ['AccessDeniedException', 'UnauthorizedException']:
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                'Access denied for Cost Optimization Hub. Ensure you have the necessary permissions: cost-optimization-hub:ListRecommendationSummaries.',
            )
        elif error_code == 'ResourceNotFoundException':
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                'Cost Optimization Hub resources not found. The service may not be enabled in this account or region.',
            )
        else:
            # For other AWS errors, format a user-friendly response
            return format_response(
                'error',
                {
                    'error_code': error_code,
                    'error_message': error_message,
                    'request_id': e.response.get('ResponseMetadata', {}).get(
                        'RequestId', 'Unknown'
                    ),
                },
                f'AWS Error: {error_message}',
            )

    except Exception as e:
        # Handle non-AWS errors
        await ctx_logger.error(f'Unexpected error in list_recommendation_summaries: {str(e)}')
        return format_response(
            'error',
            {
                'error_type': 'service_error',
                'service': 'Cost Optimization Hub',
                'operation': 'list_recommendation_summaries',
                'message': str(e),
            },
            'Error retrieving recommendation summaries. Try using list_recommendations operation instead.',
        )
