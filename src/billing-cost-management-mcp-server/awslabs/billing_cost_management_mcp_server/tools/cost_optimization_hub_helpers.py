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
from fastmcp import Context
from typing import Any, Dict, List, Optional


def format_currency_amount(amount: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format currency amount for better readability.

    Args:
        amount: Currency amount from Cost Optimization Hub API

    Returns:
        Formatted currency amount dictionary
    """
    if not amount:
        return None

    return {
        'amount': amount.get('amount'),
        'currency': amount.get('currency'),
        'formatted': f'{amount.get("amount")} {amount.get("currency")}',
    }


def format_timestamp(timestamp: Any) -> Optional[str]:
    """Format a timestamp to ISO format string.

    Args:
        timestamp: Timestamp from Cost Optimization Hub API

    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return None

    return timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)


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
        request_params: dict = {
            'includeAllRecommendations': bool(include_all_recommendations or False)
        }

        # For pagination, we'll use a reasonable page size to fetch data in chunks
        # The actual max_results parameter is used to limit the total results returned
        page_size = min(100, max_results if max_results else 100)
        request_params['maxResults'] = page_size

        if filters:
            request_params['filter'] = dict(filters)

        # Check if Cost Optimization Hub is enabled
        try:
            # Make a test call to check if the service is available
            await ctx_logger.info('Checking Cost Optimization Hub service status')
            service_status = coh_client.get_enrollment_status()
            enrollment_status = service_status.get('status', 'UNKNOWN')
            
            if enrollment_status != 'ENROLLED':
                await ctx_logger.warning(f'Cost Optimization Hub is not enrolled. Status: {enrollment_status}')
                return format_response(
                    'warning',
                    {
                        'enrollment_status': enrollment_status,
                        'recommendations': [],
                        'message': 'Cost Optimization Hub is not enrolled for this account.',
                    },
                    'Cost Optimization Hub is not enrolled. Please enroll in the AWS Console first.'
                )
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDeniedException':
                await ctx_logger.warning('Access denied when checking Cost Optimization Hub enrollment status')
            else:
                # For other client errors, continue - the service might still work
                await ctx_logger.warning(f"Couldn't check enrollment status: {str(e)}")
        except Exception as e:
            # Non-ClientError exceptions when checking enrollment - log but continue
            await ctx_logger.warning(f"Error checking enrollment status: {str(e)}")

        # Initialize collection for all recommendations across pages
        all_recommendations = []
        current_token = None
        page_count = 0
        
        # Loop to handle pagination automatically
        while True:
            # Update token if we're on a subsequent page
            if current_token:
                request_params['nextToken'] = current_token
            
            # Make the API call for this page
            page_count += 1
            await ctx_logger.info(f'Fetching page {page_count} of recommendations from Cost Optimization Hub')
            response = coh_client.list_recommendations(**request_params)
            
            # Process this page of recommendations
            recommendations = response.get('recommendations', [])
            await ctx_logger.info(f'Retrieved {len(recommendations)} recommendations on page {page_count}')
            
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
                
            # Log that we're continuing to next page
            await ctx_logger.info(f'Moving to page {page_count + 1} with token: {current_token[:10]}... (truncated)')

        # Format all collected recommendations
        formatted_recommendations = []
        
        await ctx_logger.info(f'Processing {len(all_recommendations)} total recommendations from {page_count} page(s)')
        
        # Handle empty recommendations
        if not all_recommendations:
            await ctx_logger.info('No recommendations found across any pages')
            return format_response(
                'success',
                {
                    'recommendations': [],
                    'page_count': page_count,
                    'message': 'No recommendations found. This could be because there are no optimization opportunities, or because Cost Optimization Hub has not yet generated recommendations.'
                }
            )

        # Process all recommendations
        for rec in all_recommendations:
            formatted_rec = {
                'resource_id': rec.get('resourceId'),
                'resource_type': rec.get('resourceType'),
                'account_id': rec.get('accountId'),
                'estimated_monthly_savings': format_currency_amount(
                    rec.get('estimatedMonthlySavings')
                ),
                'status': rec.get('status'),
                'last_refresh_timestamp': format_timestamp(rec.get('lastRefreshTimestamp')),
                'recommendation_id': rec.get('recommendationId'),
            }

            # Add source if present
            if 'source' in rec:
                formatted_rec['source'] = rec.get('source')

            # Add lookback period if present
            if 'lookbackPeriodInDays' in rec:
                formatted_rec['lookback_period_in_days'] = rec.get('lookbackPeriodInDays')

            formatted_recommendations.append(formatted_rec)

        # Return formatted response with pagination information
        return format_response('success', {
            'recommendations': formatted_recommendations,
            'page_count': page_count,
            'total_recommendations': len(formatted_recommendations)
        })
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')
        
        if error_code == 'ValidationException':
            await ctx_logger.warning(f"Cost Optimization Hub validation error: {error_message}")
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                f'Cost Optimization Hub validation error: {error_message}'
            )
        elif error_code == 'AccessDeniedException':
            await ctx_logger.error(f"Access denied for Cost Optimization Hub: {error_message}")
            return format_response(
                'error',
                {'error_code': error_code},
                'Access denied for Cost Optimization Hub. Ensure you have the necessary permissions: cost-optimization-hub:ListRecommendations.'
            )
        elif error_code == 'ResourceNotFoundException':
            await ctx_logger.warning(f"Cost Optimization Hub resource not found: {error_message}")
            return format_response(
                'error',
                {'error_code': error_code},
                'Cost Optimization Hub resources not found. The service may not be enabled in this account or region.'
            )
        else:
            # Re-raise for other errors to be handled by the parent try-catch
            raise
            
    except Exception as e:
        # Let the parent try-catch handle other exceptions
        await ctx_logger.error(f"Unexpected error in list_recommendations: {str(e)}")
        raise


async def get_recommendation(
    ctx: Context, coh_client: Any, resource_id: str, resource_type: str
) -> Dict[str, Any]:
    """Get detailed information about a specific recommendation.

    Args:
        ctx: MCP context
        coh_client: Cost Optimization Hub client
        resource_id: Resource ID
        resource_type: Resource type

    Returns:
        Dict containing detailed recommendation information
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)
    
    try:
        # Prepare the request parameters
        request_params = {'resourceId': resource_id, 'resourceType': resource_type}

        # Make the API call
        await ctx_logger.info(f'Fetching recommendation for resource {resource_id} of type {resource_type}')
        response = coh_client.get_recommendation(**request_params)

        # Format the recommendation for better readability
        recommendation = response.get('recommendation', {})
        
        if not recommendation:
            await ctx_logger.warning(f"No recommendation found for resource {resource_id} of type {resource_type}")
            return format_response(
                'warning',
                {
                    'resource_id': resource_id,
                    'resource_type': resource_type,
                    'message': f'No recommendation found for the specified resource.'
                },
                'No recommendation found. The resource may not have optimization opportunities, or the resource ID/type may be incorrect.'
            )

        formatted_response = {
            'resource_id': recommendation.get('resourceId'),
            'resource_type': recommendation.get('resourceType'),
            'account_id': recommendation.get('accountId'),
            'estimated_monthly_savings': format_currency_amount(
                recommendation.get('estimatedMonthlySavings')
            ),
            'status': recommendation.get('status'),
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
            'recommendation_id': recommendation.get('recommendationId'),
        }

        # Add source if present
        if 'source' in recommendation:
            formatted_response['source'] = recommendation.get('source')

        # Add lookback period if present
        if 'lookbackPeriodInDays' in recommendation:
            formatted_response['lookback_period_in_days'] = recommendation.get('lookbackPeriodInDays')

        # Add current resource details
        current_resource = recommendation.get('currentResource', {})
        formatted_response['current_resource'] = {
            'resource_details': current_resource.get('resourceDetails', {})
        }

        # Add recommended resource details
        recommended_resources = []
        for recommended in recommendation.get('recommendedResources', []):
            recommended_resource = {
                'resource_details': recommended.get('resourceDetails', {}),
                'estimated_monthly_savings': format_currency_amount(
                    recommended.get('estimatedMonthlySavings')
                ),
            }

            # Add cost breakdown if present
            if 'costBreakdown' in recommended:
                cost_breakdown = []
                for breakdown in recommended.get('costBreakdown', []):
                    cost_breakdown.append(
                        {
                            'description': breakdown.get('description'),
                            'amount': format_currency_amount(breakdown.get('amount')),
                        }
                    )
                recommended_resource['cost_breakdown'] = cost_breakdown

            recommended_resources.append(recommended_resource)

        formatted_response['recommended_resources'] = recommended_resources

        # Add implementation steps if present
        if 'implementationEffort' in recommendation:
            implementation = recommendation.get('implementationEffort', {})
            formatted_response['implementation_effort'] = {
                'effort_level': implementation.get('effortLevel'),
                'required_actions': implementation.get('requiredActions', []),
            }

        # Return formatted response
        return format_response('success', formatted_response)
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')
        
        if error_code == 'ValidationException':
            await ctx_logger.warning(f"Validation error in get_recommendation: {error_message}")
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                f'Cost Optimization Hub validation error: {error_message}'
            )
        elif error_code == 'AccessDeniedException':
            await ctx_logger.error(f"Access denied for Cost Optimization Hub get_recommendation: {error_message}")
            return format_response(
                'error',
                {'error_code': error_code},
                'Access denied for Cost Optimization Hub. Ensure you have the necessary permissions: cost-optimization-hub:GetRecommendation.'
            )
        elif error_code == 'ResourceNotFoundException':
            await ctx_logger.warning(f"Resource not found: {error_message}")
            return format_response(
                'warning',
                {'error_code': error_code, 'resource_id': resource_id, 'resource_type': resource_type},
                f'Resource {resource_id} of type {resource_type} not found in Cost Optimization Hub.'
            )
        else:
            # Re-raise for other errors
            raise
            
    except Exception as e:
        await ctx_logger.error(f"Unexpected error in get_recommendation: {str(e)}")
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
        request_params = {'groupBy': str(group_by)}
        
        # For pagination, we'll use a reasonable page size to fetch data in chunks
        # The actual max_results parameter is used to limit the total results returned
        page_size = min(100, max_results if max_results else 100)
        request_params['maxResults'] = page_size
            
        if filters:
            request_params['filter'] = dict(filters)
        
        # Initialize collection for all summaries across pages
        all_summaries = []
        current_token = None
        page_count = 0
        
        # Loop to handle pagination automatically
        while True:
            # Update token if we're on a subsequent page
            if current_token:
                request_params['nextToken'] = current_token
                
            # Make the API call for this page
            page_count += 1
            await ctx_logger.info(f'Fetching page {page_count} of recommendation summaries grouped by {group_by}')
            response = coh_client.list_recommendation_summaries(**request_params)
            
            # Process this page of summaries
            summaries = response.get('summaries', [])
            await ctx_logger.info(f'Retrieved {len(summaries)} recommendation summaries on page {page_count}')
            
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
                
            # Log that we're continuing to next page
            await ctx_logger.info(f'Moving to page {page_count + 1} with token: {current_token[:10]}... (truncated)')

        # Format all collected summaries
        formatted_summaries = []
        
        await ctx_logger.info(f'Processing {len(all_summaries)} total recommendation summaries from {page_count} page(s)')
        
        # Handle empty summaries
        if not all_summaries:
            await ctx_logger.info('No recommendation summaries found across any pages')
            return format_response(
                'success',
                {
                    'summaries': [],
                    'page_count': page_count,
                    'message': 'No recommendation summaries found. This could be because there are no optimization opportunities.'
                }
            )

        # Process all summaries
        for summary in all_summaries:
            formatted_summary = {
                'dimension_value': summary.get('dimensionValue'),
                'recommendation_count': summary.get('recommendationCount'),
                'estimated_monthly_savings': format_currency_amount(
                    summary.get('estimatedMonthlySavings')
                ),
            }
            formatted_summaries.append(formatted_summary)

        # Return formatted response with pagination information
        return format_response('success', {
            'summaries': formatted_summaries,
            'page_count': page_count,
            'total_summaries': len(formatted_summaries),
            'group_by': group_by
        })
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'An unknown error occurred')
        await ctx_logger.error(f"AWS ClientError in list_recommendation_summaries: {error_code} - {error_message}")
        
        if error_code == 'ValidationException':
            return format_response(
                'error',
                {
                    'error_code': error_code, 
                    'error_message': error_message,
                    'valid_group_by_values': ['ACCOUNT_ID', 'RECOMMENDATION_TYPE', 'RESOURCE_TYPE', 'TAG', 'USAGE_TYPE']
                },
                f'Invalid parameters for recommendation summaries: {error_message}. Valid group_by values are: ACCOUNT_ID, RECOMMENDATION_TYPE, RESOURCE_TYPE, TAG, USAGE_TYPE.'
            )
        elif error_code in ['AccessDeniedException', 'UnauthorizedException']:
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                'Access denied for Cost Optimization Hub. Ensure you have the necessary permissions: cost-optimization-hub:ListRecommendationSummaries.'
            )
        elif error_code == 'ResourceNotFoundException':
            return format_response(
                'error',
                {'error_code': error_code, 'error_message': error_message},
                'Cost Optimization Hub resources not found. The service may not be enabled in this account or region.'
            )
        else:
            # For other AWS errors, format a user-friendly response
            return format_response(
                'error',
                {
                    'error_code': error_code, 
                    'error_message': error_message,
                    'request_id': e.response.get('ResponseMetadata', {}).get('RequestId', 'Unknown')
                },
                f'AWS Error: {error_message}'
            )
            
    except Exception as e:
        # Handle non-AWS errors
        await ctx_logger.error(f"Unexpected error in list_recommendation_summaries: {str(e)}")
        return format_response(
            'error',
            {
                'error_type': 'service_error',
                'service': 'Cost Optimization Hub', 
                'operation': 'list_recommendation_summaries',
                'message': str(e)
            },
            'Error retrieving recommendation summaries. Try using list_recommendations operation instead.'
        )
