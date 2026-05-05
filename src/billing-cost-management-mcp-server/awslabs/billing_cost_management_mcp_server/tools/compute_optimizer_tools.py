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

"""AWS Compute Optimizer tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from ..utilities.logging_utils import get_context_logger
from botocore.exceptions import ClientError
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


compute_optimizer_server = FastMCP(
    name='compute-optimizer-tools', instructions='Tools for working with AWS Compute Optimizer API'
)


@compute_optimizer_server.tool(
    name='compute-optimizer',
    description="""Retrieves recommendations from AWS Compute Optimizer.

IMPORTANT USAGE GUIDELINES:
- Focus on recommendations with the highest estimated savings first
- Include all relevant details when presenting specific recommendations

USE THIS TOOL FOR:
- **Performance optimization** (CPU, memory, network utilization analysis)
- **Performance-based rightsizing** (not cost-based)

DO NOT USE FOR: Cost optimization or idle detection (use cost-optimization-hub)

This tool supports the following operations:
1. get_ec2_instance_recommendations: Get recommendations for EC2 instances
2. get_auto_scaling_group_recommendations: Get recommendations for Auto Scaling groups
3. get_ebs_volume_recommendations: Get recommendations for EBS volumes
4. get_lambda_function_recommendations: Get recommendations for Lambda functions
5. get_rds_recommendations: Get recommendations for RDS instances
6. get_ecs_service_recommendations: Get recommendations for ECS services

Each operation can be filtered by AWS account IDs, regions, finding types, and more.

Common finding types include:
- UNDERPROVISIONED: The resource doesn't have enough capacity
- OVERPROVISIONED: The resource has excess capacity and could be downsized
- OPTIMIZED: The resource is already optimized
- NOT_OPTIMIZED: The resource can be optimized but specific finding type isn't available""",
)
async def compute_optimizer(
    ctx: Context,
    operation: str,
    max_results: Optional[int] = None,
    filters: Optional[str] = None,
    account_ids: Optional[str] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves recommendations from AWS Compute Optimizer.

    Args:
        ctx: The MCP context
        operation: The operation to perform (e.g., 'get_ec2_instance_recommendations')
        max_results: Maximum number of results to return (1-100)
        filters: Optional filter expression as JSON string
        account_ids: Optional list of AWS account IDs as JSON array string
        next_token: Optional pagination token from a previous response

    Returns:
        Dict containing the Compute Optimizer recommendations
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    try:
        # Log the request
        await ctx_logger.info(f'Compute Optimizer operation: {operation}')

        # Initialize Compute Optimizer client using shared utility
        co_client = create_aws_client('compute-optimizer', region_name='us-east-1')

        # Check enrollment status first to provide better error messages
        try:
            enrollment_status = co_client.get_enrollment_status()
            status = enrollment_status.get('status', '')

            # Map operations to required resource types
            resource_type_mapping = {
                'get_ec2_instance_recommendations': 'ec2Instance',
                'get_auto_scaling_group_recommendations': 'autoScalingGroup',
                'get_ebs_volume_recommendations': 'ebsVolume',
                'get_lambda_function_recommendations': 'lambdaFunction',
                'get_rds_recommendations': 'rdsDBInstance',
                'get_ecs_service_recommendations': 'ecsService',
            }

            # Get required resource type for current operation
            required_resource_type = resource_type_mapping.get(operation)

            # If we have a valid operation, check enrollment
            if required_resource_type:
                # Check overall enrollment status
                if status.upper() != 'ACTIVE':
                    return format_response(
                        'error',
                        {
                            'error_type': 'enrollment_error',
                            'enrollment_status': status,
                            'operation': operation,
                            'aws_error_code': 'ComputeOptimizerNotActive',
                            'aws_region': 'us-east-1',
                        },
                        'Compute Optimizer is not active. Please activate the service in the AWS Console first.',
                    )

        except ClientError as e:
            # Specific error handling for enrollment status checking
            aws_error = e.response.get('Error', {})
            error_code = aws_error.get('Code', 'UnknownError')

            if error_code == 'AccessDeniedException' or error_code == 'AccessDenied':
                await ctx_logger.warning(f'Access denied for enrollment status check: {str(e)}')
                # Continue execution even if we can't check enrollment
            else:
                # For other enrollment checking errors, log but continue
                await ctx_logger.warning(f'Could not check Compute Optimizer enrollment: {str(e)}')

        # Process the operation
        if operation == 'get_ec2_instance_recommendations':
            return await get_ec2_instance_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == 'get_auto_scaling_group_recommendations':
            return await get_auto_scaling_group_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == 'get_ebs_volume_recommendations':
            return await get_ebs_volume_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == 'get_lambda_function_recommendations':
            return await get_lambda_function_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == 'get_rds_recommendations':
            return await get_rds_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == 'get_ecs_service_recommendations':
            return await get_ecs_service_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        else:
            return format_response(
                'error',
                {
                    'error_type': 'invalid_operation',
                    'provided_operation': operation,
                    'valid_operations': [
                        'get_ec2_instance_recommendations',
                        'get_auto_scaling_group_recommendations',
                        'get_ebs_volume_recommendations',
                        'get_lambda_function_recommendations',
                        'get_rds_recommendations',
                        'get_ecs_service_recommendations',
                    ],
                },
                f"Unsupported operation: {operation}. Use 'get_ec2_instance_recommendations', 'get_auto_scaling_group_recommendations', 'get_ebs_volume_recommendations', 'get_lambda_function_recommendations', 'get_rds_recommendations' or 'get_ecs_service_recommendations'.",
            )

    except ClientError as e:
        # Specific handling for AWS service errors
        aws_error = e.response.get('Error', {})
        error_code = aws_error.get('Code', 'UnknownError')
        aws_message = aws_error.get('Message', 'No error message provided')
        request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'Unknown')
        http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 0)

        # Create detailed error response
        error_response = {
            'status': 'error',
            'error_type': 'access_denied',  # Default, will be overridden
            'message': 'An error occurred',  # Default, will be overridden
            'data': {
                'service': 'Compute Optimizer',
                'operation': operation,
                'aws_error_code': error_code,
                'aws_error_message': aws_message,
                'request_id': request_id,
                'http_status': http_status,
            },
        }

        # Handle specific error codes with improved messages
        if error_code == 'AccessDeniedException' or error_code == 'AccessDenied':
            error_response['error_type'] = 'access_denied'
            error_response['message'] = (
                f'Access denied for Compute Optimizer {operation}. Ensure you have the compute-optimizer:{operation} permission.'
            )
            error_response['resolution'] = (
                'Check your IAM permissions and ensure your role has the ComputeOptimizerReadOnlyAccess policy or equivalent permissions.'
            )
            await ctx_logger.error(
                f'Access denied error for {operation}: {aws_message}', exc_info=True
            )

        elif error_code == 'OptInRequiredException':
            error_response['error_type'] = 'opt_in_required'
            error_response['message'] = (
                'Compute Optimizer requires opt-in before accessing recommendations.'
            )
            error_response['resolution'] = (
                'Enable Compute Optimizer in the AWS Console for your account/organization.'
            )
            await ctx_logger.error(f'Opt-in required: {aws_message}', exc_info=True)

        elif error_code == 'ValidationException':
            error_response['error_type'] = 'validation_error'
            error_response['message'] = f'Compute Optimizer validation error: {aws_message}'
            error_response['resolution'] = (
                'Check your request parameters and ensure resources are correctly configured.'
            )
            await ctx_logger.error(
                f'Validation error for {operation}: {aws_message}', exc_info=True
            )

        elif error_code == 'ThrottlingException' or error_code == 'Throttling':
            error_response['error_type'] = 'throttling_error'
            error_response['message'] = (
                'The Compute Optimizer API is throttling your requests. Please try again later.'
            )
            error_response['resolution'] = (
                'Implement backoff retry logic or reduce request frequency.'
            )
            await ctx_logger.error(f'API throttling for {operation}: {aws_message}', exc_info=True)

        elif error_code == 'ServiceUnavailableException':
            error_response['error_type'] = 'service_unavailable'
            error_response['message'] = (
                'Compute Optimizer service is temporarily unavailable. Please try again later.'
            )
            error_response['resolution'] = (
                'This is a temporary condition. Retry after a brief wait.'
            )
            await ctx_logger.error(f'Service unavailable: {aws_message}', exc_info=True)

        elif error_code == 'ResourceNotFoundException':
            error_response['error_type'] = 'resource_not_found'
            error_response['message'] = f'The requested resource was not found: {aws_message}'
            error_response['resolution'] = (
                'Verify resource identifiers and ensure resources exist.'
            )
            await ctx_logger.error(f'Resource not found: {aws_message}', exc_info=True)

        else:
            # For other AWS errors, use the generic handler
            return await handle_aws_error(ctx, e, operation, 'Compute Optimizer')

        return error_response

    except ValueError as e:
        # Specific handling for validation errors
        error_details = {
            'status': 'error',
            'error_type': 'validation_error',
            'service': 'Compute Optimizer',
            'operation': operation,
            'message': f'Invalid parameter: {str(e)}',
            'details': str(e),
        }
        await ctx_logger.warning(f'Validation error in {operation}: {str(e)}')
        return error_details

    except Exception as e:
        # Add detailed logging for troubleshooting
        await ctx_logger.error(
            f'Unhandled exception in compute_optimizer: {e.__class__.__name__}: {str(e)}',
            exc_info=True,
        )

        # Use shared error handler for other unexpected exceptions
        return await handle_aws_error(ctx, e, operation, 'Compute Optimizer')


async def get_ec2_instance_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get EC2 instance recommendations."""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params['maxResults'] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params['filters'] = parse_json(filters, 'filters')

    # Parse the account IDs if provided
    if account_ids:
        request_params['accountIds'] = parse_json(account_ids, 'account_ids')

    # Add the next token if provided
    if next_token:
        request_params['nextToken'] = next_token

    # Make the API call
    response = co_client.get_ec2_instance_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        'recommendations': [],
        'next_token': response.get('nextToken'),
    }

    # Parse the recommendations
    for recommendation in response.get('instanceRecommendations', []):
        # Get the current instance details
        current_instance = {
            'instance_type': recommendation.get('currentInstanceType'),
            'instance_name': recommendation.get('instanceName'),
            'finding': recommendation.get('finding'),
        }

        # Get the recommended instance options
        instance_options = []
        for option in recommendation.get('recommendationOptions', []):
            instance_option = {
                'instance_type': option.get('instanceType'),
                'projected_utilization': option.get('projectedUtilization'),
                'performance_risk': option.get('performanceRisk'),
                'savings_opportunity': format_savings_opportunity(
                    option.get('savingsOpportunity', {})
                ),
            }
            instance_options.append(instance_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            'instance_arn': recommendation.get('instanceArn'),
            'account_id': recommendation.get('accountId'),
            'current_instance': current_instance,
            'recommendation_options': instance_options,
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
        }

        formatted_response['recommendations'].append(formatted_recommendation)

    return format_response('success', formatted_response)


async def get_auto_scaling_group_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get Auto Scaling group recommendations."""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params['maxResults'] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params['filters'] = parse_json(filters, 'filters')

    # Parse the account IDs if provided
    if account_ids:
        request_params['accountIds'] = parse_json(account_ids, 'account_ids')

    # Add the next token if provided
    if next_token:
        request_params['nextToken'] = next_token

    # Make the API call
    response = co_client.get_auto_scaling_group_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        'recommendations': [],
        'next_token': response.get('nextToken'),
    }

    # Parse the recommendations
    for recommendation in response.get('autoScalingGroupRecommendations', []):
        # Get the current configuration
        current_config = {
            'instance_type': recommendation.get('currentInstanceType'),
            'finding': recommendation.get('finding'),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get('recommendationOptions', []):
            recommended_option = {
                'instance_type': option.get('instanceType'),
                'projected_utilization': option.get('projectedUtilization'),
                'performance_risk': option.get('performanceRisk'),
                'savings_opportunity': format_savings_opportunity(
                    option.get('savingsOpportunity', {})
                ),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            'auto_scaling_group_arn': recommendation.get('autoScalingGroupArn'),
            'auto_scaling_group_name': recommendation.get('autoScalingGroupName'),
            'account_id': recommendation.get('accountId'),
            'current_configuration': current_config,
            'recommendation_options': recommended_options,
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
        }

        formatted_response['recommendations'].append(formatted_recommendation)

    return format_response('success', formatted_response)


async def get_ebs_volume_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get EBS volume recommendations."""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params['maxResults'] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params['filters'] = parse_json(filters, 'filters')

    # Parse the account IDs if provided
    if account_ids:
        request_params['accountIds'] = parse_json(account_ids, 'account_ids')

    # Add the next token if provided
    if next_token:
        request_params['nextToken'] = next_token

    # Make the API call
    response = co_client.get_ebs_volume_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        'recommendations': [],
        'next_token': response.get('nextToken'),
    }

    # Parse the recommendations
    for recommendation in response.get('volumeRecommendations', []):
        # Get the current configuration
        current_config = {
            'volume_type': recommendation.get('currentConfiguration', {}).get('volumeType'),
            'volume_size': recommendation.get('currentConfiguration', {}).get('volumeSize'),
            'volume_baseline_iops': recommendation.get('currentConfiguration', {}).get(
                'volumeBaselineIOPS'
            ),
            'volume_burst_iops': recommendation.get('currentConfiguration', {}).get(
                'volumeBurstIOPS'
            ),
            'finding': recommendation.get('finding'),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get('volumeRecommendationOptions', []):
            config = option.get('configuration', {})
            recommended_option = {
                'volume_type': config.get('volumeType'),
                'volume_size': config.get('volumeSize'),
                'volume_baseline_iops': config.get('volumeBaselineIOPS'),
                'volume_burst_iops': config.get('volumeBurstIOPS'),
                'performance_risk': option.get('performanceRisk'),
                'savings_opportunity': format_savings_opportunity(
                    option.get('savingsOpportunity', {})
                ),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            'volume_arn': recommendation.get('volumeArn'),
            'account_id': recommendation.get('accountId'),
            'current_configuration': current_config,
            'recommendation_options': recommended_options,
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
        }

        formatted_response['recommendations'].append(formatted_recommendation)

    return format_response('success', formatted_response)


async def get_lambda_function_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get Lambda function recommendations."""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params['maxResults'] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params['filters'] = parse_json(filters, 'filters')

    # Parse the account IDs if provided
    if account_ids:
        request_params['accountIds'] = parse_json(account_ids, 'account_ids')

    # Add the next token if provided
    if next_token:
        request_params['nextToken'] = next_token

    # Make the API call
    response = co_client.get_lambda_function_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        'recommendations': [],
        'next_token': response.get('nextToken'),
    }

    # Parse the recommendations
    for recommendation in response.get('lambdaFunctionRecommendations', []):
        # Get the current configuration
        current_config = {
            'memory_size': recommendation.get('currentMemorySize'),
            'finding': recommendation.get('finding'),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get('memorySizeRecommendationOptions', []):
            recommended_option = {
                'memory_size': option.get('memorySize'),
                'projected_utilization': option.get('projectedUtilization'),
                'rank': option.get('rank'),
                'savings_opportunity': format_savings_opportunity(
                    option.get('savingsOpportunity', {})
                ),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            'function_arn': recommendation.get('functionArn'),
            'function_name': recommendation.get('functionName'),
            'account_id': recommendation.get('accountId'),
            'current_configuration': current_config,
            'recommendation_options': recommended_options,
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
        }

        formatted_response['recommendations'].append(formatted_recommendation)

    return format_response('success', formatted_response)


async def get_rds_recommendations(ctx, co_client, max_results, filters, account_ids, next_token):
    """Get RDS instance recommendations.

    Args:
        ctx: MCP context
        co_client: AWS Compute Optimizer client
        max_results: Maximum number of results to return
        filters: Optional filters as JSON string
        account_ids: Optional list of account IDs as JSON string
        next_token: Pagination token

    Returns:
        Dict containing RDS instance recommendations
    """
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params['maxResults'] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params['filters'] = parse_json(filters, 'filters')

    # Parse the account IDs if provided
    if account_ids:
        request_params['accountIds'] = parse_json(account_ids, 'account_ids')

    # Add the next token if provided
    if next_token:
        request_params['nextToken'] = next_token

    # Make the API call
    await ctx_logger.info(
        f'Calling get_rds_database_recommendations with parameters: {request_params}'
    )
    response = co_client.get_rds_database_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        'recommendations': [],
        'next_token': response.get('nextToken'),
    }

    # Parse the recommendations
    for recommendation in response.get('rdsDBRecommendations', []):
        # Get the current configuration
        current_config = {
            'instance_class': recommendation.get('currentInstanceClass'),
            'finding': recommendation.get('finding'),
            'engine': recommendation.get('engine'),
            'engine_version': recommendation.get('engineVersion'),
            'storage_finding': recommendation.get('storageFinding'),
            'current_storage_configuration': recommendation.get('currentStorageConfiguration'),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get('recommendationOptions', []):
            recommended_option = {
                'instance_class': option.get('instanceClass'),
                'performance_risk': option.get('performanceRisk'),
                'savings_opportunity': format_savings_opportunity(
                    option.get('savingsOpportunity', {})
                ),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            'instance_arn': recommendation.get('instanceArn'),
            'instance_name': recommendation.get('instanceName'),
            'account_id': recommendation.get('accountId'),
            'current_configuration': current_config,
            'recommendation_options': recommended_options,
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
        }

        formatted_response['recommendations'].append(formatted_recommendation)

    return {'status': 'success', 'data': formatted_response}


async def get_ecs_service_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get ECS service recommendations."""
    # Get context logger for consistent logging
    ctx_logger = get_context_logger(ctx, __name__)

    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params['maxResults'] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params['filters'] = parse_json(filters, 'filters')

    # Parse the account IDs if provided
    if account_ids:
        request_params['accountIds'] = parse_json(account_ids, 'account_ids')

    # Add the next token if provided
    if next_token:
        request_params['nextToken'] = next_token

    # Make the API call
    await ctx_logger.info(
        f'Calling get_ecs_service_recommendations with parameters: {request_params}'
    )
    response = co_client.get_ecs_service_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        'recommendations': [],
        'next_token': response.get('nextToken'),
    }

    # Parse the recommendations
    for recommendation in response.get('ecsServiceRecommendations', []):
        # Get the current performance
        current_performance = recommendation.get('currentPerformance')
        formatted_current_performance = None
        if current_performance:
            formatted_current_performance = {
                'cpu_utilization': current_performance.get('cpuUtilization'),
                'memory_utilization': current_performance.get('memoryUtilization'),
            }

        # Get the current service configuration
        current_config = {
            'memory': recommendation.get('currentServiceConfiguration', {}).get('memory'),
            'cpu': recommendation.get('currentServiceConfiguration', {}).get('cpu'),
            'container_configurations': recommendation.get('currentServiceConfiguration', {}).get(
                'containerConfigurations', []
            ),
            'auto_scaling_group_arn': recommendation.get('currentServiceConfiguration', {}).get(
                'autoScalingGroupArn'
            ),
            'task_definition_arn': recommendation.get('currentServiceConfiguration', {}).get(
                'taskDefinitionArn'
            ),
            'finding': recommendation.get('finding'),
            'current_performance': formatted_current_performance,
        }

        # Get the utilization metrics
        utilization_metrics = []
        for metric in recommendation.get('utilizationMetrics', []):
            utilization_metric = {
                'name': metric.get('name'),
                'statistic': metric.get('statistic'),
                'value': metric.get('value'),
            }
            utilization_metrics.append(utilization_metric)

        # Get the recommended service configurations
        recommended_options = []
        for option in recommendation.get('serviceRecommendationOptions', []):
            # Format projected performance
            projected_performance = option.get('projectedPerformance')
            formatted_projected_performance = None
            if projected_performance:
                formatted_projected_performance = {
                    'cpu_utilization': projected_performance.get('cpuUtilization'),
                    'memory_utilization': projected_performance.get('memoryUtilization'),
                }

            recommended_option = {
                'memory': option.get('memory'),
                'cpu': option.get('cpu'),
                'container_recommendations': option.get('containerRecommendations', []),
                'projected_performance': formatted_projected_performance,
                'savings_opportunity': format_savings_opportunity(
                    option.get('savingsOpportunity', {})
                ),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            'service_arn': recommendation.get('serviceArn'),
            'account_id': recommendation.get('accountId'),
            'current_service_configuration': current_config,
            'utilization_metrics': utilization_metrics,
            'lookback_period_in_days': recommendation.get('lookbackPeriodInDays'),
            'launch_type': recommendation.get('launchType'),
            'recommendation_options': recommended_options,
            'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
            'tags': recommendation.get('tags', []),
        }

        formatted_response['recommendations'].append(formatted_recommendation)

    return format_response('success', formatted_response)


def format_savings_opportunity(savings_opportunity):
    """Format the savings opportunity for better readability."""
    if not savings_opportunity:
        return None

    return {
        'savings_percentage': savings_opportunity.get('savingsPercentage'),
        'estimated_monthly_savings': {
            'currency': savings_opportunity.get('estimatedMonthlySavings', {}).get('currency'),
            'value': savings_opportunity.get('estimatedMonthlySavings', {}).get('value'),
        },
    }


def format_timestamp(timestamp):
    """Format a timestamp to ISO format string."""
    if not timestamp:
        return None

    return timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
