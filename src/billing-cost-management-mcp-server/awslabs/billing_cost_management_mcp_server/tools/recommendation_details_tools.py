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

"""AWS Cost Optimization Hub enhanced recommendation details tools for the AWS Billing and Cost Management MCP server.

Updated to use shared utility functions.
"""

import os
from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from ..utilities.constants import (
    ACCOUNT_SCOPE_MAP,
    ACTION_TYPE_DELETE,
    ACTION_TYPE_PURCHASE_RESERVED_INSTANCE,
    ACTION_TYPE_PURCHASE_SAVINGS_PLAN,
    ACTION_TYPE_STOP,
    LOOKBACK_PERIOD_MAP,
    PAYMENT_OPTION_MAP,
    RESOURCE_TYPE_EBS_VOLUME,
    RESOURCE_TYPE_EC2_ASG,
    RESOURCE_TYPE_EC2_INSTANCE,
    RESOURCE_TYPE_ECS_SERVICE,
    RESOURCE_TYPE_LAMBDA_FUNCTION,
    RESOURCE_TYPE_RDS,
    SAVINGS_PLANS_TYPE_MAP,
    SERVICE_MAP,
    TERM_MAP,
)
from datetime import datetime
from fastmcp import Context, FastMCP
from typing import Any, Dict, Optional


recommendation_details_server = FastMCP(
    name='recommendation-details-tools',
    instructions='Tools for working with AWS Cost Optimization Hub enhanced recommendation details',
)


@recommendation_details_server.tool(
    name='rec-details',
    description="""Get detailed cost optimization recommendation with integrated data from multiple AWS services.

This tool combines data from:
- Cost Optimization Hub (base recommendation)
- AWS Compute Optimizer (detailed metrics for compute resources)
- Cost Explorer (Savings Plans/RI purchase recommendations)

It provides comprehensive analysis with utilization metrics, savings calculations, and implementation guidance.

RESPONSE FORMATTING INSTRUCTIONS:
The tool may return both raw recommendation data and a formatting template.
When presenting the recommendation:
1. If a template is provided, use it to organize your response
2. If no template is provided, structure your response in a clear, logical manner
3. Always include key information like resource details, savings amounts, and implementation steps
4. Ensure all numeric values (costs, savings, metrics) are included
5. Add natural language explanations to make the information more accessible""",
)
async def get_recommendation_details(ctx: Context, recommendation_id: str) -> Dict[str, Any]:
    """Get enhanced recommendation details with integrated data from multiple AWS services.

    Args:
        ctx: The MCP context object
        recommendation_id: ID of the recommendation to retrieve details for

    Returns:
        Dict containing the enhanced recommendation details
    """
    try:
        await ctx.info(f'Getting recommendation details for: {recommendation_id}')

        # Get base recommendation from Cost Optimization Hub using shared utility
        coh_client = create_aws_client('cost-optimization-hub', region_name='us-east-1')
        base_recommendation = coh_client.get_recommendation(recommendationId=recommendation_id)

        # Process the recommendation with additional data
        response = await process_recommendation(ctx, base_recommendation)

        return format_response('success', response)

    except Exception as e:
        # Use shared error handler for consistent error reporting
        return await handle_aws_error(
            ctx, e, 'get_recommendation_details', 'Cost Optimization Hub'
        )


async def process_recommendation(ctx: Context, recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """Process a recommendation with additional data from appropriate services."""
    action_type = recommendation.get('actionType')

    # Create result dictionary with base recommendation
    result: Dict[str, Any] = {'base_recommendation': format_base_recommendation(recommendation)}

    # Add additional data based on recommendation type
    if action_type in [ACTION_TYPE_PURCHASE_SAVINGS_PLAN, ACTION_TYPE_PURCHASE_RESERVED_INSTANCE]:
        # Get Cost Explorer data for Savings Plans or Reserved Instances
        additional_data = await get_cost_explorer_data(ctx, recommendation)
        result['additional_details'] = additional_data
    else:
        # Get Compute Optimizer data for other recommendation types
        additional_data = await get_compute_optimizer_data(ctx, recommendation)
        result['additional_details'] = additional_data

    # Get the appropriate template
    template_content = get_template_for_recommendation(
        recommendation, result['additional_details']
    )
    if template_content:
        result['template'] = template_content
        result['formatting_instructions'] = """
FORMATTING INSTRUCTIONS:
Use the provided template to organize your response about this recommendation.
The template provides specific guidance on structure, content, and formatting.
Replace template variables with actual data from the recommendation.
Follow the template's rules and examples exactly."""

    return result


def format_base_recommendation(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """Format the base recommendation from Cost Optimization Hub."""
    formatted = {
        'recommendation_id': recommendation.get('recommendationId'),
        'account_id': recommendation.get('accountId'),
        'region': recommendation.get('region'),
        'resource_id': recommendation.get('resourceId'),
        'resource_arn': recommendation.get('resourceArn'),
        'action_type': recommendation.get('actionType'),
        'current_resource_type': recommendation.get('currentResourceType'),
        'recommended_resource_type': recommendation.get('recommendedResourceType'),
        'estimated_monthly_savings': recommendation.get('estimatedMonthlySavings'),
        'estimated_savings_percentage': recommendation.get('estimatedSavingsPercentage'),
        'estimated_monthly_cost': recommendation.get('estimatedMonthlyCost'),
        'currency_code': recommendation.get('currencyCode'),
        'implementation_effort': recommendation.get('implementationEffort'),
        'last_refresh_timestamp': format_timestamp(recommendation.get('lastRefreshTimestamp')),
        'lookback_period_in_days': recommendation.get('recommendationLookbackPeriodInDays'),
        'cost_calculation_lookback_period_in_days': recommendation.get(
            'costCalculationLookbackPeriodInDays'
        ),
        'estimated_savings_over_lookback_period': recommendation.get(
            'estimatedSavingsOverCostCalculationLookbackPeriod'
        ),
    }

    # Add current resource details if present
    if 'currentResourceDetails' in recommendation:
        formatted['current_resource_details'] = recommendation['currentResourceDetails']

    # Add recommended resource details if present
    if 'recommendedResourceDetails' in recommendation:
        formatted['recommended_resource_details'] = recommendation['recommendedResourceDetails']

    return formatted


async def get_cost_explorer_data(ctx: Context, recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """Get additional data from Cost Explorer for Savings Plans or Reserved Instance recommendations."""
    action_type = recommendation.get('actionType')

    # Initialize Cost Explorer client using shared utility
    ce_client = create_aws_client('ce')

    try:
        if action_type == ACTION_TYPE_PURCHASE_SAVINGS_PLAN:
            # Handle Savings Plans recommendations
            return await get_savings_plans_recommendation(ctx, recommendation, ce_client)
        elif action_type == ACTION_TYPE_PURCHASE_RESERVED_INSTANCE:
            # Handle Reserved Instance recommendations
            return await get_reserved_instances_recommendation(ctx, recommendation, ce_client)
        else:
            return {'error': 'Unsupported action type for Cost Explorer data'}
    except Exception as e:
        await ctx.error(f'Error getting Cost Explorer data: {str(e)}')
        return {'error': f'Error getting Cost Explorer data: {str(e)}'}


async def get_savings_plans_recommendation(
    ctx: Context, recommendation: Dict[str, Any], ce_client
) -> Dict[str, Any]:
    """Get Savings Plans recommendation details from Cost Explorer."""
    # Get recommendation details
    recommended_details = recommendation.get('recommendedResourceDetails', {})

    # Find the Savings Plans key in recommended details
    savings_plans_key = None
    for key in recommended_details.keys():
        if key.endswith('SavingsPlans'):
            savings_plans_key = key
            break

    if not savings_plans_key:
        return {
            'error': f'No Savings Plans details found. Available keys: {list(recommended_details.keys())}'
        }

    # Extract configuration
    config = recommended_details[savings_plans_key].get('configuration', {})
    lookback_period = recommendation.get('recommendationLookbackPeriodInDays')

    # Build parameters for Cost Explorer API
    params = {}

    # Map savings plans type
    if savings_plans_key in SAVINGS_PLANS_TYPE_MAP:
        params['SavingsPlansType'] = SAVINGS_PLANS_TYPE_MAP[savings_plans_key]

    # Map term
    term = config.get('term')
    if term and term in TERM_MAP:
        params['TermInYears'] = TERM_MAP[term]

    # Map payment option
    payment_option = config.get('paymentOption')
    if payment_option and payment_option in PAYMENT_OPTION_MAP:
        params['PaymentOption'] = PAYMENT_OPTION_MAP[payment_option]

    # Map account scope
    account_scope = config.get('accountScope')
    if account_scope and account_scope in ACCOUNT_SCOPE_MAP:
        params['AccountScope'] = ACCOUNT_SCOPE_MAP[account_scope]

    # Only proceed if we have the required parameters
    if not all(
        key in params
        for key in ['SavingsPlansType', 'TermInYears', 'PaymentOption', 'AccountScope']
    ):
        return {
            'error': f'Missing required parameters for Cost Explorer API. Available config: {config}'
        }

    # Add lookback period if available
    if lookback_period is not None and lookback_period in LOOKBACK_PERIOD_MAP:
        lookback_value = LOOKBACK_PERIOD_MAP.get(lookback_period)
        if lookback_value is not None:
            params['LookbackPeriodInDays'] = lookback_value

    try:
        # Call Cost Explorer API
        response = ce_client.get_savings_plans_purchase_recommendation(**params)
        return response.get('SavingsPlansPurchaseRecommendation', {})
    except Exception as e:
        await ctx.error(f'Error getting Savings Plans recommendation: {str(e)}')
        return {'error': f'Error getting Savings Plans recommendation: {str(e)}'}


async def get_reserved_instances_recommendation(
    ctx: Context, recommendation: Dict[str, Any], ce_client
) -> Dict[str, Any]:
    """Get Reserved Instance recommendation details from Cost Explorer."""
    # Get recommendation details
    recommended_details = recommendation.get('recommendedResourceDetails', {})

    # Find the Reserved Instances key in recommended details
    ri_key = None
    for key in recommended_details.keys():
        if key.endswith('ReservedInstances'):
            ri_key = key
            break

    if not ri_key:
        return {
            'error': f'No Reserved Instances details found. Available keys: {list(recommended_details.keys())}'
        }

    # Extract configuration
    config = recommended_details[ri_key].get('configuration', {})
    lookback_period = recommendation.get('recommendationLookbackPeriodInDays')

    # Build parameters for Cost Explorer API
    params = {}

    # Map service
    if ri_key in SERVICE_MAP:
        params['Service'] = SERVICE_MAP[ri_key]

    # Map term
    term = config.get('term')
    if term and term in TERM_MAP:
        params['TermInYears'] = TERM_MAP[term]

    # Map payment option
    payment_option = config.get('paymentOption')
    if payment_option and payment_option in PAYMENT_OPTION_MAP:
        params['PaymentOption'] = PAYMENT_OPTION_MAP[payment_option]

    # Only proceed if we have the required parameters
    if not all(key in params for key in ['Service', 'TermInYears', 'PaymentOption']):
        return {
            'error': f'Missing required parameters for Cost Explorer API. Available config: {config}'
        }

    # Add lookback period if available
    if lookback_period is not None and lookback_period in LOOKBACK_PERIOD_MAP:
        lookback_value = LOOKBACK_PERIOD_MAP.get(lookback_period)
        if lookback_value is not None:
            params['LookbackPeriodInDays'] = lookback_value

    try:
        # Call Cost Explorer API
        response = ce_client.get_reservation_purchase_recommendation(**params)
        return response
    except Exception as e:
        await ctx.error(f'Error getting Reserved Instance recommendation: {str(e)}')
        return {'error': f'Error getting Reserved Instance recommendation: {str(e)}'}


async def get_compute_optimizer_data(
    ctx: Context, recommendation: Dict[str, Any]
) -> Dict[str, Any]:
    """Get additional data from Compute Optimizer for compute resource recommendations."""
    action_type = recommendation.get('actionType')
    resource_type = recommendation.get('currentResourceType')
    resource_arn = recommendation.get('resourceArn')
    region_name = recommendation.get('region')

    if not resource_arn:
        return {'error': 'No resource ARN found in recommendation'}

    try:
        # Initialize Compute Optimizer client using shared utility
        compute_optimizer = create_aws_client('compute-optimizer', region_name=region_name)

        # Handle Stop and Delete recommendations
        if action_type in [ACTION_TYPE_STOP, ACTION_TYPE_DELETE]:
            response = compute_optimizer.get_idle_recommendations(resourceArns=[resource_arn])
            return response

        # Handle resource-specific recommendations
        if resource_type == RESOURCE_TYPE_ECS_SERVICE:
            response = compute_optimizer.get_ecs_service_recommendations(
                serviceArns=[resource_arn]
            )
            return response
        elif resource_type == RESOURCE_TYPE_LAMBDA_FUNCTION:
            response = compute_optimizer.get_lambda_function_recommendations(
                functionArns=[resource_arn]
            )
            return response
        elif resource_type == RESOURCE_TYPE_EBS_VOLUME:
            response = compute_optimizer.get_ebs_volume_recommendations(volumeArns=[resource_arn])
            return response
        elif resource_type == RESOURCE_TYPE_EC2_INSTANCE:
            response = compute_optimizer.get_ec2_instance_recommendations(
                instanceArns=[resource_arn]
            )
            # Strip recommendation options to reduce response size
            if 'instanceRecommendations' in response:
                for instance in response['instanceRecommendations']:
                    if 'recommendationOptions' in instance:
                        del instance['recommendationOptions']
            return response
        elif resource_type == RESOURCE_TYPE_EC2_ASG:
            response = compute_optimizer.get_auto_scaling_group_recommendations(
                autoScalingGroupArns=[resource_arn]
            )
            return response
        elif resource_type == RESOURCE_TYPE_RDS:
            response = compute_optimizer.get_rds_instance_recommendations(
                instanceArns=[resource_arn]
            )
            return response
        else:
            return {'error': f'Unsupported resource type: {resource_type}'}
    except Exception as e:
        await ctx.error(f'Error getting Compute Optimizer data: {str(e)}')
        return {'error': f'Error getting Compute Optimizer data: {str(e)}'}


def format_timestamp(timestamp: Optional[int]) -> Optional[str]:
    """Format Unix timestamp to ISO format string."""
    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(timestamp / 1000).isoformat()
    except Exception as e:
        return str(f'Error: {e}, Timestamp: {timestamp}')  # Return as string if conversion fails


def get_template_for_recommendation(
    recommendation: Dict[str, Any], additional_details: Dict[str, Any]
) -> Optional[str]:
    """Get the appropriate template for a recommendation based on its type."""
    action_type = recommendation.get('actionType')
    resource_type = recommendation.get('currentResourceType')

    # Map recommendation types to template files
    template_map = {
        'PurchaseSavingsPlans': 'savings_plans.template',
        'PurchaseReservedInstances': 'reserved_instances.template',
        'Stop': 'idle.template',
        'Delete': 'idle.template',
        'Ec2Instance': 'ec2_instance.template',
        'Ec2AutoScalingGroup': 'ec2_asg.template',
        'EbsVolume': 'ebs_volume.template',
        'EcsService': 'ecs_service.template',
        'LambdaFunction': 'lambda_function.template',
        'RdsDbInstance': 'rds_database.template',
    }

    # Determine template file
    template_file = None
    if action_type in template_map:
        template_file = template_map[action_type]
    elif resource_type in template_map:
        template_file = template_map[resource_type]

    if not template_file:
        return None

    # Load template content
    try:
        # Update path to use our project structure
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(
            current_dir, '..', 'templates', 'recommendation_templates', template_file
        )

        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                return f.read()
    except Exception:
        # Template loading is optional, so we'll silently continue if not found
        pass

    return None
