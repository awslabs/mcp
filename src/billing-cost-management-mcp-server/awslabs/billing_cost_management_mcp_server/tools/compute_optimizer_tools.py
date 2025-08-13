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

"""
AWS Compute Optimizer tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from typing import Any, Dict, Optional
from fastmcp import Context, FastMCP
from ..utilities.aws_service_base import (
    create_aws_client,
    handle_aws_error,
    format_response,
    parse_json
)

compute_optimizer_server = FastMCP(
    name="compute-optimizer-tools", instructions="Tools for working with AWS Compute Optimizer API"
)


@compute_optimizer_server.tool(
    name="compute_optimizer",
    description="""Retrieves recommendations from AWS Compute Optimizer.

IMPORTANT USAGE GUIDELINES:
- Before using this tool, provide a 1-3 sentence explanation starting with "EXPLANATION:"
- Start with EC2 instance recommendations if the user is not specific about resource types
- Focus on recommendations with the highest estimated savings first
- Include all relevant details when presenting specific recommendations

This tool supports the following operations:
1. get_ec2_instance_recommendations: Get recommendations for EC2 instances
2. get_auto_scaling_group_recommendations: Get recommendations for Auto Scaling groups
3. get_ebs_volume_recommendations: Get recommendations for EBS volumes
4. get_lambda_function_recommendations: Get recommendations for Lambda functions
5. get_rds_recommendations: Get recommendations for RDS instances

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
    """
    Retrieves recommendations from AWS Compute Optimizer.

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
    try:
        # Log the request
        await ctx.info(f"Compute Optimizer operation: {operation}")

        # Initialize Compute Optimizer client using shared utility
        co_client = create_aws_client("compute-optimizer", region_name="us-east-1")

        if operation == "get_ec2_instance_recommendations":
            return await get_ec2_instance_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == "get_auto_scaling_group_recommendations":
            return await get_auto_scaling_group_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == "get_ebs_volume_recommendations":
            return await get_ebs_volume_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == "get_lambda_function_recommendations":
            return await get_lambda_function_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        elif operation == "get_rds_recommendations":
            return await get_rds_recommendations(
                ctx, co_client, max_results, filters, account_ids, next_token
            )
        else:
            return format_response(
                "error", 
                {}, 
                f"Unsupported operation: {operation}. Use 'get_ec2_instance_recommendations', 'get_auto_scaling_group_recommendations', 'get_ebs_volume_recommendations', 'get_lambda_function_recommendations', or 'get_rds_recommendations'."
            )

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(ctx, e, "compute_optimizer", "Compute Optimizer")


async def get_ec2_instance_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get EC2 instance recommendations"""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params["maxResults"] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params["filters"] = parse_json(filters, "filters")

    # Parse the account IDs if provided
    if account_ids:
        request_params["accountIds"] = parse_json(account_ids, "account_ids")

    # Add the next token if provided
    if next_token:
        request_params["nextToken"] = next_token

    # Make the API call
    response = co_client.get_ec2_instance_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        "recommendations": [],
        "next_token": response.get("nextToken"),
    }

    # Parse the recommendations
    for recommendation in response.get("instanceRecommendations", []):
        # Get the current instance details
        current_instance = {
            "instance_type": recommendation.get("currentInstanceType"),
            "instance_name": recommendation.get("instanceName"),
            "finding": recommendation.get("finding"),
        }

        # Get the recommended instance options
        instance_options = []
        for option in recommendation.get("recommendationOptions", []):
            instance_option = {
                "instance_type": option.get("instanceType"),
                "projected_utilization": option.get("projectedUtilization"),
                "performance_risk": option.get("performanceRisk"),
                "savings_opportunity": format_savings_opportunity(option.get("savingsOpportunity", {})),
            }
            instance_options.append(instance_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            "instance_arn": recommendation.get("instanceArn"),
            "account_id": recommendation.get("accountId"),
            "current_instance": current_instance,
            "recommendation_options": instance_options,
            "last_refresh_timestamp": format_timestamp(recommendation.get("lastRefreshTimestamp")),
        }

        formatted_response["recommendations"].append(formatted_recommendation)

    return format_response("success", formatted_response)


async def get_auto_scaling_group_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get Auto Scaling group recommendations"""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params["maxResults"] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params["filters"] = parse_json(filters, "filters")

    # Parse the account IDs if provided
    if account_ids:
        request_params["accountIds"] = parse_json(account_ids, "account_ids")

    # Add the next token if provided
    if next_token:
        request_params["nextToken"] = next_token

    # Make the API call
    response = co_client.get_auto_scaling_group_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        "recommendations": [],
        "next_token": response.get("nextToken"),
    }

    # Parse the recommendations
    for recommendation in response.get("autoScalingGroupRecommendations", []):
        # Get the current configuration
        current_config = {
            "instance_type": recommendation.get("currentInstanceType"),
            "finding": recommendation.get("finding"),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get("recommendationOptions", []):
            recommended_option = {
                "instance_type": option.get("instanceType"),
                "projected_utilization": option.get("projectedUtilization"),
                "performance_risk": option.get("performanceRisk"),
                "savings_opportunity": format_savings_opportunity(option.get("savingsOpportunity", {})),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            "auto_scaling_group_arn": recommendation.get("autoScalingGroupArn"),
            "auto_scaling_group_name": recommendation.get("autoScalingGroupName"),
            "account_id": recommendation.get("accountId"),
            "current_configuration": current_config,
            "recommendation_options": recommended_options,
            "last_refresh_timestamp": format_timestamp(recommendation.get("lastRefreshTimestamp")),
        }

        formatted_response["recommendations"].append(formatted_recommendation)

    return format_response("success", formatted_response)


async def get_ebs_volume_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get EBS volume recommendations"""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params["maxResults"] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params["filters"] = parse_json(filters, "filters")

    # Parse the account IDs if provided
    if account_ids:
        request_params["accountIds"] = parse_json(account_ids, "account_ids")

    # Add the next token if provided
    if next_token:
        request_params["nextToken"] = next_token

    # Make the API call
    response = co_client.get_ebs_volume_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        "recommendations": [],
        "next_token": response.get("nextToken"),
    }

    # Parse the recommendations
    for recommendation in response.get("volumeRecommendations", []):
        # Get the current configuration
        current_config = {
            "volume_type": recommendation.get("currentConfiguration", {}).get("volumeType"),
            "volume_size": recommendation.get("currentConfiguration", {}).get("volumeSize"),
            "volume_baseline_iops": recommendation.get("currentConfiguration", {}).get("volumeBaselineIOPS"),
            "volume_burst_iops": recommendation.get("currentConfiguration", {}).get("volumeBurstIOPS"),
            "finding": recommendation.get("finding"),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get("volumeRecommendationOptions", []):
            config = option.get("configuration", {})
            recommended_option = {
                "volume_type": config.get("volumeType"),
                "volume_size": config.get("volumeSize"),
                "volume_baseline_iops": config.get("volumeBaselineIOPS"),
                "volume_burst_iops": config.get("volumeBurstIOPS"),
                "performance_risk": option.get("performanceRisk"),
                "savings_opportunity": format_savings_opportunity(option.get("savingsOpportunity", {})),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            "volume_arn": recommendation.get("volumeArn"),
            "account_id": recommendation.get("accountId"),
            "current_configuration": current_config,
            "recommendation_options": recommended_options,
            "last_refresh_timestamp": format_timestamp(recommendation.get("lastRefreshTimestamp")),
        }

        formatted_response["recommendations"].append(formatted_recommendation)

    return format_response("success", formatted_response)


async def get_lambda_function_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get Lambda function recommendations"""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params["maxResults"] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params["filters"] = parse_json(filters, "filters")

    # Parse the account IDs if provided
    if account_ids:
        request_params["accountIds"] = parse_json(account_ids, "account_ids")

    # Add the next token if provided
    if next_token:
        request_params["nextToken"] = next_token

    # Make the API call
    response = co_client.get_lambda_function_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        "recommendations": [],
        "next_token": response.get("nextToken"),
    }

    # Parse the recommendations
    for recommendation in response.get("lambdaFunctionRecommendations", []):
        # Get the current configuration
        current_config = {
            "memory_size": recommendation.get("currentMemorySize"),
            "finding": recommendation.get("finding"),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get("memorySizeRecommendationOptions", []):
            recommended_option = {
                "memory_size": option.get("memorySize"),
                "projected_utilization": option.get("projectedUtilization"),
                "rank": option.get("rank"),
                "savings_opportunity": format_savings_opportunity(option.get("savingsOpportunity", {})),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            "function_arn": recommendation.get("functionArn"),
            "function_name": recommendation.get("functionName"),
            "account_id": recommendation.get("accountId"),
            "current_configuration": current_config,
            "recommendation_options": recommended_options,
            "last_refresh_timestamp": format_timestamp(recommendation.get("lastRefreshTimestamp")),
        }

        formatted_response["recommendations"].append(formatted_recommendation)

    return format_response("success", formatted_response)


async def get_rds_recommendations(
    ctx, co_client, max_results, filters, account_ids, next_token
):
    """Get RDS instance recommendations"""
    # Prepare the request parameters
    request_params = {}

    if max_results:
        request_params["maxResults"] = int(max_results)

    # Parse the filters if provided
    if filters:
        request_params["filters"] = parse_json(filters, "filters")

    # Parse the account IDs if provided
    if account_ids:
        request_params["accountIds"] = parse_json(account_ids, "account_ids")

    # Add the next token if provided
    if next_token:
        request_params["nextToken"] = next_token

    # Make the API call
    response = co_client.get_rds_instance_recommendations(**request_params)

    # Format the response for better readability
    formatted_response: Dict[str, Any] = {
        "recommendations": [],
        "next_token": response.get("nextToken"),
    }

    # Parse the recommendations
    for recommendation in response.get("instanceRecommendations", []):
        # Get the current configuration
        current_config = {
            "instance_class": recommendation.get("currentInstanceClass"),
            "finding": recommendation.get("finding"),
        }

        # Get the recommended options
        recommended_options = []
        for option in recommendation.get("recommendationOptions", []):
            recommended_option = {
                "instance_class": option.get("instanceClass"),
                "performance_risk": option.get("performanceRisk"),
                "savings_opportunity": format_savings_opportunity(option.get("savingsOpportunity", {})),
            }
            recommended_options.append(recommended_option)

        # Create the formatted recommendation
        formatted_recommendation = {
            "instance_arn": recommendation.get("instanceArn"),
            "instance_name": recommendation.get("instanceName"),
            "account_id": recommendation.get("accountId"),
            "current_configuration": current_config,
            "recommendation_options": recommended_options,
            "last_refresh_timestamp": format_timestamp(recommendation.get("lastRefreshTimestamp")),
        }

        formatted_response["recommendations"].append(formatted_recommendation)

    return format_response("success", formatted_response)


def format_savings_opportunity(savings_opportunity):
    """Format the savings opportunity for better readability"""
    if not savings_opportunity:
        return None

    return {
        "savings_percentage": savings_opportunity.get("savingsPercentage"),
        "estimated_monthly_savings": {
            "currency": savings_opportunity.get("estimatedMonthlySavings", {}).get("currency"),
            "value": savings_opportunity.get("estimatedMonthlySavings", {}).get("value"),
        },
    }


def format_timestamp(timestamp):
    """Format a timestamp to ISO format string"""
    if not timestamp:
        return None

    return timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)