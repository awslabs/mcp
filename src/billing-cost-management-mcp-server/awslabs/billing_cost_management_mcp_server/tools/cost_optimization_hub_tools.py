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
AWS Cost Optimization Hub tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from typing import Any, Dict, Optional
from fastmcp import Context, FastMCP
from ..utilities.aws_service_base import (
    create_aws_client,
    parse_json,
    handle_aws_error,
    format_response
)
from .cost_optimization_hub_helpers import (
    list_recommendations,
    get_recommendation,
    list_recommendation_summaries
)

cost_optimization_hub_server = FastMCP(
    name="cost-optimization-hub-tools",
    instructions="Tools for working with AWS Cost Optimization Hub API"
)


@cost_optimization_hub_server.tool(
    name="cost_optimization_hub",
    description="""Retrieves recommendations from AWS Cost Optimization Hub.

IMPORTANT USAGE GUIDELINES:
- Before using this tool, provide a 1-3 sentence explanation starting with "EXPLANATION:"
- Focus on recommendations with the highest estimated savings first
- Include all relevant details when presenting specific recommendations

Supported Operations:
1. get_recommendation_summaries: High-level overview of savings opportunities grouped by a dimension
2. list_recommendations: Detailed list of specific recommendations
3. get_recommendation: Get detailed information about a specific recommendation

IMPORTANT: 'get_recommendation_summaries' operation REQUIRES a 'group_by' parameter.

Cost Optimization Hub provides recommendations across multiple AWS services, including:
- EC2 instances (right-sizing, Graviton migration)
- EBS volumes (unused volumes, IOPS optimization)
- RDS instances (right-sizing, engine optimization)
- Lambda functions (memory size optimization)
- S3 buckets (storage class optimization)
- And more

Each recommendation includes:
- The resource ARN and ID
- The estimated monthly savings
- The current state of the resource
- The recommended state of the resource
- Implementation steps""",
)
async def cost_optimization_hub(
    ctx: Context,
    operation: str,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    max_results: Optional[int] = None,
    next_token: Optional[str] = None,
    filters: Optional[str] = None,
    group_by: Optional[str] = None,
    include_all_recommendations: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Retrieves recommendations from AWS Cost Optimization Hub.

    Args:
        ctx: The MCP context
        operation: The operation to perform ('list_recommendations', 'get_recommendation', or 'list_recommendation_summaries')
        resource_id: Resource ID for get_recommendation operation
        resource_type: Resource type for get_recommendation operation
        max_results: Maximum number of results to return (1-100)
        next_token: Pagination token for subsequent requests
        filters: Optional filter expression as JSON string
        group_by: Optional grouping parameter for list_recommendation_summaries

    Returns:
        Dict containing the Cost Optimization Hub recommendations
    """
    try:
        # Log the request
        await ctx.info(f"Cost Optimization Hub operation: {operation}")

        # Initialize Cost Optimization Hub client using shared utility
        coh_client = create_aws_client("cost-optimization-hub", "us-east-1")
        
        # Validate operation-specific requirements
        if operation == "get_recommendation_summaries":
            if not group_by:
                return format_response(
                    "error",
                    {},
                    "group_by parameter is required for get_recommendation_summaries operation"
                )
                
        elif operation == "get_recommendation":
            if not resource_id or not resource_type:
                return format_response(
                    "error",
                    {},
                    "Both resource_id and resource_type are required for get_recommendation operation"
                )

        # Execute the appropriate operation
        if operation == "get_recommendation_summaries":
            # Parse filters if provided
            parsed_filters = parse_json(filters, "filters") if filters else None
            return await list_recommendation_summaries(
                ctx, coh_client, max_results, next_token, parsed_filters, group_by
            )
            
        elif operation == "list_recommendations":
            # Parse filters if provided
            parsed_filters = parse_json(filters, "filters") if filters else None
            return await list_recommendations(
                ctx, coh_client, max_results, next_token, parsed_filters, include_all_recommendations
            )
            
        elif operation == "get_recommendation":
            return await get_recommendation(
                ctx, coh_client, resource_id, resource_type
            )
            
        else:
            # Return error for unsupported operations
            return format_response(
                "error",
                {
                    "supported_operations": [
                        "get_recommendation_summaries",
                        "list_recommendations",
                        "get_recommendation"
                    ]
                },
                f"Unsupported operation: {operation}. Use 'get_recommendation_summaries', 'list_recommendations', or 'get_recommendation'."
            )

    except Exception as e:
        # Use shared error handler
        return await handle_aws_error(ctx, e, operation, "Cost Optimization Hub")

