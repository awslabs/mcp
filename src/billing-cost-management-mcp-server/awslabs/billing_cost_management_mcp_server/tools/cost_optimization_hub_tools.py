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

"""AWS Cost Optimization Hub tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from ..utilities.constants import (
    COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES,
    OPERATION_GET_RECOMMENDATION,
    OPERATION_LIST_RECOMMENDATION_SUMMARIES,
    OPERATION_LIST_RECOMMENDATIONS,
)
from .cost_optimization_hub_helpers import (
    get_recommendation,
    list_recommendation_summaries,
    list_recommendations,
)
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


cost_optimization_hub_server = FastMCP(
    name='cost-optimization-hub-tools',
    instructions='Tools for working with AWS Cost Optimization Hub API',
)


@cost_optimization_hub_server.tool(
    name='cost-optimization',
    description="""Retrieves cost optimization recommendations from AWS Cost Optimization Hub.

IMPORTANT USAGE GUIDELINES:
- Focus on recommendations with the highest estimated savings first
- Include all relevant details when presenting specific recommendations

USE THIS TOOL FOR:
- **Idle/unused resource detection** (EC2, RDS, EBS, Lambda, etc.)
- **Cost savings recommendations** (rightsizing, stopping, deleting resources)
- **Reserved Instance and Savings Plans purchase recommendations**
- **Cross-service cost optimization analysis**
- **Monthly cost reduction opportunities**

DO NOT USE FOR: Performance optimization (use compute-optimizer)

Supported Operations:
1. list_recommendation_summaries: High-level overview of savings opportunities grouped by a dimension
2. list_recommendations: Detailed list of specific recommendations
3. get_recommendation: Get detailed information about a specific recommendation

IMPORTANT: 'list_recommendation_summaries' operation REQUIRES a 'group_by' parameter.
Valid 'group_by' values: AccountId, Region, ActionType, ResourceType, RestartNeeded, RollbackPossible, ImplementationEffort

CRITICAL PARAMETER REQUIREMENTS:
- 'filters' parameter must be passed as JSON string format
- 'max_results' must be integer (not string)
- 'get_recommendation' requires both 'resource_id' AND 'resource_type' parameters
- Service only available in us-east-1 region

Available Filter Parameters (pass as JSON string):
- resourceTypes: ['Ec2Instance', 'LambdaFunction', 'EbsVolume', 'EcsService', 'Ec2AutoScalingGroup', 'Ec2InstanceSavingsPlans', 'ComputeSavingsPlans', 'SageMakerSavingsPlans', 'Ec2ReservedInstances', 'RdsReservedInstances', 'OpenSearchReservedInstances', 'RedshiftReservedInstances', 'ElastiCacheReservedInstances', 'RdsDbInstanceStorage', 'RdsDbInstance', 'DynamoDbReservedCapacity', 'MemoryDbReservedInstances']
- actionTypes: ['Rightsize', 'Stop', 'Upgrade', 'PurchaseSavingsPlans', 'PurchaseReservedInstances', 'MigrateToGraviton', 'Delete', 'ScaleIn']
- implementationEfforts: ['VeryLow', 'Low', 'Medium', 'High', 'VeryHigh']
- regions: AWS region codes (e.g., ["us-east-1", "us-west-2"])
- accountIds: List of AWS account IDs
- restartNeeded: boolean
- rollbackPossible: boolean

Cost Optimization Hub provides recommendations across multiple AWS services, including:
- EC2 instances (right-sizing, Graviton migration)
- EBS volumes (unused volumes, IOPS optimization)
- RDS instances (right-sizing, engine optimization)
- Lambda functions (memory size optimization)
- SP/RI
- And more

Each recommendation includes:
- The resource ARN and ID
- The estimated monthly savings
- The current state of the resource
- The recommended state of the resource
""",
)
async def cost_optimization_hub(
    ctx: Context,
    operation: str,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    max_results: Optional[int] = None,
    filters: Optional[str] = None,
    group_by: Optional[str] = None,
    include_all_recommendations: Optional[bool] = None,
) -> Dict[str, Any]:
    """Retrieves recommendations from AWS Cost Optimization Hub.

    Args:
        ctx: The MCP context
        operation: The operation to perform ('list_recommendations', 'get_recommendation', or 'list_recommendation_summaries')
        resource_id: Resource ID for get_recommendation operation
        resource_type: Resource type for get_recommendation operation
        max_results: Maximum total results to return across all pages; None means all available results
        filters: Optional filter expression as JSON string
        group_by: Optional grouping parameter for list_recommendation_summaries
        include_all_recommendations: Whether to include all recommendations

    Returns:
        Dict containing the Cost Optimization Hub recommendations

    Note:
        This function automatically fetches all pages of results and combines them into
        a single response when multiple pages are available.
    """
    try:
        # Log the request
        await ctx.info(f'Cost Optimization Hub operation: {operation}')

        # Initialize Cost Optimization Hub client using shared utility
        coh_client = create_aws_client('cost-optimization-hub', region_name='us-east-1')
        await ctx.info('Created Cost Optimization Hub client in region us-east-1')

        # Validate operation-specific requirements
        if operation == OPERATION_LIST_RECOMMENDATION_SUMMARIES:
            if not group_by:
                return format_response(
                    'error',
                    {'valid_group_by_values': COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES},
                    'group_by parameter is required for list_recommendation_summaries operation. Must be one of: ACCOUNT_ID, RECOMMENDATION_TYPE, RESOURCE_TYPE, TAG, USAGE_TYPE',
                )

            # Validate the group_by value is one of the allowed values
            if group_by not in COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES:
                return format_response(
                    'error',
                    {
                        'provided_group_by': group_by,
                        'valid_group_by_values': COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES,
                    },
                    f'Invalid group_by value: {group_by}. Must be one of: {", ".join(COST_OPTIMIZATION_HUB_VALID_GROUP_BY_VALUES)}',
                )

        elif operation == OPERATION_GET_RECOMMENDATION:
            if not resource_id or not resource_type:
                return format_response(
                    'error',
                    {},
                    'Both resource_id and resource_type are required for get_recommendation operation',
                )

        # Execute the appropriate operation
        if operation == OPERATION_LIST_RECOMMENDATION_SUMMARIES:
            try:
                # Parse filters if provided
                parsed_filters = parse_json(filters, 'filters') if filters else None

                effective_group_by = str(group_by) if group_by else 'RESOURCE_TYPE'
                await ctx.info(f'Using group_by: {effective_group_by}')

                result = await list_recommendation_summaries(
                    ctx,
                    coh_client,
                    group_by=effective_group_by,
                    max_results=int(max_results) if max_results else None,
                    filters=parsed_filters,
                )

                # Add the operation parameters to the response for diagnostics
                if result.get('status') == 'success' and isinstance(result.get('data'), dict):
                    result['data']['operation_parameters'] = {
                        'group_by': effective_group_by,
                        'max_results': max_results,
                        'filters': filters,
                    }

                return result

            except Exception as recommendation_error:
                await ctx.error(
                    f'Error in list_recommendation_summaries: {str(recommendation_error)}'
                )

                # Create a detailed error response
                return format_response(
                    'error',
                    {
                        'error_type': 'service_error',
                        'service': 'Cost Optimization Hub',
                        'operation': 'list_recommendation_summaries',
                        'message': str(recommendation_error),
                        'group_by': group_by or 'RESOURCE_TYPE',
                    },
                    'Error fetching recommendation summaries from Cost Optimization Hub.',
                )

        elif operation == OPERATION_LIST_RECOMMENDATIONS:
            try:
                # Parse filters if provided
                parsed_filters = parse_json(filters, 'filters') if filters else None

                result = await list_recommendations(
                    ctx, coh_client, max_results, parsed_filters, include_all_recommendations
                )

                # Add the operation parameters to the response for diagnostics
                if result.get('status') == 'success' and isinstance(result.get('data'), dict):
                    result['data']['operation_parameters'] = {
                        'max_results': max_results,
                        'filters': filters,
                        'include_all_recommendations': include_all_recommendations,
                    }

                return result

            except Exception as recommendation_error:
                await ctx.error(f'Error in list_recommendations: {str(recommendation_error)}')

                # Create a detailed error response
                return format_response(
                    'error',
                    {
                        'error_type': 'service_error',
                        'service': 'Cost Optimization Hub',
                        'operation': 'list_recommendations',
                        'message': str(recommendation_error),
                    },
                    'Error fetching recommendations from Cost Optimization Hub.',
                )

        elif operation == OPERATION_GET_RECOMMENDATION:
            if not resource_id or not resource_type:
                return format_response(
                    'error',
                    {
                        'message': 'Both resource_id and resource_type are required for get_recommendation operation'
                    },
                )
            return await get_recommendation(ctx, coh_client, str(resource_id), str(resource_type))

        else:
            # Return error for unsupported operations
            return format_response(
                'error',
                {
                    'supported_operations': [
                        OPERATION_LIST_RECOMMENDATION_SUMMARIES,
                        OPERATION_LIST_RECOMMENDATIONS,
                        OPERATION_GET_RECOMMENDATION,
                    ]
                },
                f"Unsupported operation: {operation}. Use '{OPERATION_LIST_RECOMMENDATION_SUMMARIES}', '{OPERATION_LIST_RECOMMENDATIONS}', or '{OPERATION_GET_RECOMMENDATION}'.",
            )

    except Exception as e:
        await ctx.error(f'Error in Cost Optimization Hub operation {operation}: {str(e)}')
        return await handle_aws_error(ctx, e, operation, 'Cost Optimization Hub')
