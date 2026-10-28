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

import botocore.session
import functools
import os
from ..utilities.aws_service_base import create_aws_client, format_response, handle_aws_error
from ..utilities.constants import (
    ACCOUNT_SCOPE_MAP,
    ACTION_TYPE_DELETE,
    ACTION_TYPE_PURCHASE_RESERVED_INSTANCE,
    ACTION_TYPE_PURCHASE_SAVINGS_PLAN,
    ACTION_TYPE_STOP,
    LOOKBACK_PERIOD_MAP,
    OFFERING_CLASS_MAP,
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
from ..utilities.time_utils import format_timestamp_to_utc_iso
from fastmcp import Context, FastMCP
from typing import Any, Dict, FrozenSet, List, Optional


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

COMMITMENT PURCHASE DETAILS:
- For PurchaseReservedInstances, additional_details is the Cost Explorer reservation purchase
  recommendation for the recommendation's service, term, payment option and, for EC2, offering
  class; EstimatedBreakEvenInMonths is per RecommendationDetails row.
- Cost Explorer is asked for the recommendation's account scope (Payer or Linked), filtered to
  the recommendation's account when Linked. RecommendationDetails and
  SavingsPlansPurchaseRecommendationDetails then keep only the rows for the recommendation's
  own account (and, for EC2 RIs, its instance type and region). The summary is not recomputed
  from the kept rows: it totals every row Cost Explorer returned, which for RIs spans other
  instance types and regions, so use the kept row(s) for this recommendation. A top-level "note"
  key in additional_details counts dropped rows; "warning" means none matched.
- Savings Plans recommendations carry no break-even. They return EstimatedROI (estimated savings /
  Savings Plan cost x 100 over the lookback period), which is not a payback period.

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
            details = await get_savings_plans_recommendation(ctx, recommendation, ce_client)
            return scope_savings_plans_details(details, recommendation)
        elif action_type == ACTION_TYPE_PURCHASE_RESERVED_INSTANCE:
            # Handle Reserved Instance recommendations
            details = await get_reserved_instances_recommendation(ctx, recommendation, ce_client)
            return scope_reserved_instances_details(details, recommendation)
        else:
            return {'error': 'Unsupported action type for Cost Explorer data'}
    except Exception as e:
        await ctx.error(f'Error getting Cost Explorer data: {str(e)}')
        return {'error': f'Error getting Cost Explorer data: {str(e)}'}


def commitment_config(recommendation: Dict[str, Any], key_map: Dict[str, str]) -> tuple:
    """Return the (key, configuration) of the recommendation's commitment details."""
    recommended_details = recommendation.get('recommendedResourceDetails', {})
    key = next((k for k in recommended_details if k in key_map), None)
    if not key:
        return None, {}
    return key, recommended_details[key].get('configuration', {})


def linked_account(config: Dict[str, Any], recommendation: Dict[str, Any]) -> Optional[str]:
    """Return the account ID of a Linked recommendation, else None."""
    if config.get('accountScope') != 'Linked':
        return None
    return recommendation.get('accountId') or None


def linked_account_filter(
    config: Dict[str, Any], recommendation: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Cost Explorer Filter that narrows a Linked recommendation to its own account."""
    # Cost Explorer rejects an AccountId other than the caller's own account, so a
    # management account cannot name a member account there; LINKED_ACCOUNT can.
    account_id = linked_account(config, recommendation)
    if not account_id:
        return None
    return {'Dimensions': {'Key': 'LINKED_ACCOUNT', 'Values': [account_id]}}


@functools.lru_cache(maxsize=None)
def region_names(region_code: str) -> Optional[FrozenSet[str]]:
    """Names Cost Explorer may give a Region code in RI rows, or None if it is unknown."""
    for partition in botocore.session.get_session().get_data('endpoints').get('partitions', []):
        description = partition.get('regions', {}).get(region_code, {}).get('description')
        if description:
            # Cost Explorer names older European Regions 'EU (...)', e.g. 'EU (Paris)'.
            return frozenset(
                {region_code, description, description.replace('Europe (', 'EU (', 1)}
            )
    return None


def keep_matching_rows(rows: List[Dict[str, Any]], matches) -> tuple:
    """Return (kept rows, number of rows dropped)."""
    kept = [row for row in rows if matches(row)]
    return kept, len(rows) - len(kept)


def scope_reserved_instances_details(
    response: Dict[str, Any], recommendation: Dict[str, Any]
) -> Dict[str, Any]:
    """Keep only the RI rows for the recommendation's account, instance type and Region."""
    if 'Recommendations' not in response:
        return response
    ri_key, config = commitment_config(recommendation, SERVICE_MAP)
    account_id = linked_account(config, recommendation)
    criteria: Dict[str, str] = {'account': account_id} if account_id else {}
    instance_type = config.get('instanceType')
    region = config.get('reservedInstancesRegion')
    names = region_names(region) if region else None
    # Only EC2InstanceDetails is checked against the COH instance type and Region.
    if ri_key == 'ec2ReservedInstances':
        if instance_type:
            criteria['instance type'] = instance_type
        if names:
            criteria['region'] = region

    def matches(row: Dict[str, Any]) -> bool:
        ec2 = row.get('InstanceDetails', {}).get('EC2InstanceDetails', {})
        return (
            (not account_id or row.get('AccountId') == account_id)
            and ('instance type' not in criteria or ec2.get('InstanceType') == instance_type)
            and ('region' not in criteria or ec2.get('Region') in (names or ()))
        )

    dropped = kept = 0
    for ri in response['Recommendations']:
        rows, removed = keep_matching_rows(ri.get('RecommendationDetails', []), matches)
        ri['RecommendationDetails'] = rows
        dropped += removed
        kept += len(rows)
    return add_scope_notes(response, criteria, kept, dropped, 'RecommendationDetails')


def scope_savings_plans_details(
    details: Dict[str, Any], recommendation: Dict[str, Any]
) -> Dict[str, Any]:
    """Keep only the Savings Plans rows for a Linked recommendation's account."""
    if 'SavingsPlansPurchaseRecommendationDetails' not in details:
        return details
    _, config = commitment_config(recommendation, SAVINGS_PLANS_TYPE_MAP)
    account_id = linked_account(config, recommendation)
    criteria: Dict[str, str] = {'account': account_id} if account_id else {}
    rows, dropped = keep_matching_rows(
        details['SavingsPlansPurchaseRecommendationDetails'],
        lambda row: not account_id or row.get('AccountId') == account_id,
    )
    details['SavingsPlansPurchaseRecommendationDetails'] = rows
    return add_scope_notes(
        details, criteria, len(rows), dropped, 'SavingsPlansPurchaseRecommendationDetails'
    )


def add_scope_notes(
    result: Dict[str, Any], criteria: Dict[str, str], kept: int, dropped: int, rows_key: str
) -> Dict[str, Any]:
    """Say when rows were dropped (the summary still covers them) or none matched."""
    wanted = ', '.join(f'{name} {value}' for name, value in criteria.items()) or 'its scope'
    if kept == 0:
        result['warning'] = (
            f'Cost Explorer returned no {rows_key} row for this recommendation ({wanted}). '
            'Cost Explorer may have regenerated its recommendations since Cost Optimization '
            'Hub produced this one.'
        )
        if result.get('NextPageToken'):
            result['warning'] += ' Only the first page was read; the row may be on a later page.'
    elif dropped:
        result['note'] = (
            f'{rows_key} keeps only the {kept} row(s) for {wanted}; {dropped} other row(s) '
            "were dropped. Cost Explorer's summary still totals all of them, so use the kept "
            'row(s) for this recommendation.'
        )
    return result


def missing_details_error(recommended_details: Dict[str, Any], kind: str) -> Dict[str, Any]:
    """Explain why no supported commitment key was found in recommendedResourceDetails."""
    # boto3 parses a union member its service model does not know as
    # {'SDK_UNKNOWN_MEMBER': {'name': <member>}} and drops the member's configuration.
    unknown = recommended_details.get('SDK_UNKNOWN_MEMBER')
    if isinstance(unknown, dict):
        return {
            'error': (
                f"Cost Optimization Hub returned a '{unknown.get('name')}' recommendation, "
                f'which the installed AWS SDK cannot parse, so its {kind} purchase details '
                'are unavailable. Upgrade boto3/botocore to retrieve them.'
            )
        }
    return {
        'error': f'No {kind} details found. Available keys: {list(recommended_details.keys())}'
    }


async def get_savings_plans_recommendation(
    ctx: Context, recommendation: Dict[str, Any], ce_client
) -> Dict[str, Any]:
    """Get Savings Plans recommendation details from Cost Explorer."""
    # Get recommendation details
    recommended_details = recommendation.get('recommendedResourceDetails', {})

    # Find the Savings Plans key in recommended details
    savings_plans_key = next(
        (key for key in recommended_details if key in SAVINGS_PLANS_TYPE_MAP), None
    )

    if not savings_plans_key:
        return missing_details_error(recommended_details, 'Savings Plans')

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

    account_filter = linked_account_filter(config, recommendation)
    if account_filter:
        params['Filter'] = account_filter

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

    # Find the Reserved Instances (or DynamoDB reserved capacity) key in recommended details
    ri_key = next((key for key in recommended_details if key in SERVICE_MAP), None)

    if not ri_key:
        return missing_details_error(recommended_details, 'Reserved Instances')

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

    # Map account scope (when omitted, Cost Explorer uses the caller's own: PAYER for a payer)
    account_scope = config.get('accountScope')
    if account_scope in ACCOUNT_SCOPE_MAP:
        params['AccountScope'] = ACCOUNT_SCOPE_MAP[account_scope]

    account_filter = linked_account_filter(config, recommendation)
    if account_filter:
        params['Filter'] = account_filter

    # Map EC2 offering class; ServiceSpecification has no member for other services
    offering_class = config.get('offeringClass')
    if ri_key == 'ec2ReservedInstances' and offering_class in OFFERING_CLASS_MAP:
        params['ServiceSpecification'] = {
            'EC2Specification': {'OfferingClass': OFFERING_CLASS_MAP[offering_class]}
        }

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
            # Compute Optimizer's RDS API is GetRDSDatabaseRecommendations, keyed by
            # resourceArns; its results are under 'rdsDBRecommendations'.
            response = compute_optimizer.get_rds_database_recommendations(
                resourceArns=[resource_arn]
            )
            return response
        else:
            return {'error': f'Unsupported resource type: {resource_type}'}
    except Exception as e:
        await ctx.error(f'Error getting Compute Optimizer data: {str(e)}')
        return {'error': f'Error getting Compute Optimizer data: {str(e)}'}


def format_timestamp(timestamp: Any) -> Optional[str]:
    """Format a COH timestamp (datetime, epoch seconds or epoch ms) as a UTC ISO string."""
    return format_timestamp_to_utc_iso(timestamp)


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
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        # Template loading is optional, so we'll silently continue if not found
        pass

    return None
