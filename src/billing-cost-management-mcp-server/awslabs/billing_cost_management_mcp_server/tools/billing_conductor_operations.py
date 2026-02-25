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

"""AWS Billing Conductor operations for the AWS Billing and Cost Management MCP server.

This module contains the individual operation handlers for the Billing Conductor tools.
Each operation handles the AWS API call, pagination, and response formatting.
"""

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from ..utilities.constants import REGION_US_EAST_1
from ..utilities.time_utils import epoch_seconds_to_utc_iso_string
from fastmcp import Context
from typing import Any, Dict, List, Optional


# AWS Billing Conductor is a global service that operates in us-east-1
BILLING_CONDUCTOR_DEFAULT_REGION = REGION_US_EAST_1


def _create_billing_conductor_client() -> Any:
    """Create a Billing Conductor client with the default region.

    Returns:
        boto3.client: AWS Billing Conductor client.
    """
    return create_aws_client('billingconductor', region_name=BILLING_CONDUCTOR_DEFAULT_REGION)


async def list_billing_groups(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List billing groups from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted billing group information.
    """
    try:
        request_params: Dict[str, Any] = {}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_billing_groups: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching billing groups page {page_count}')
            response = bc_client.list_billing_groups(**request_params)

            page_billing_groups = response.get('BillingGroups', [])
            all_billing_groups.extend(page_billing_groups)

            await ctx.info(
                f'Retrieved {len(page_billing_groups)} billing groups '
                f'(total: {len(all_billing_groups)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_billing_groups = _format_billing_groups(all_billing_groups)

        response_data: Dict[str, Any] = {
            'billing_groups': formatted_billing_groups,
            'total_count': len(formatted_billing_groups),
            'billing_period': billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingGroups', 'Billing Conductor')


def _format_billing_groups(billing_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format billing group objects from the AWS API response.

    Args:
        billing_groups: List of billing group objects from the AWS API.

    Returns:
        List of formatted billing group objects.
    """
    formatted_groups = []

    for bg in billing_groups:
        formatted_group: Dict[str, Any] = {
            'arn': bg.get('Arn'),
            'name': bg.get('Name'),
            'description': bg.get('Description'),
            'billing_group_type': bg.get('BillingGroupType'),
            'status': bg.get('Status'),
            'status_reason': bg.get('StatusReason'),
            'primary_account_id': bg.get('PrimaryAccountId'),
            'size': bg.get('Size'),
        }

        if 'ComputationPreference' in bg:
            formatted_group['computation_preference'] = {
                'pricing_plan_arn': bg['ComputationPreference'].get('PricingPlanArn'),
            }

        if 'AccountGrouping' in bg:
            account_grouping: Dict[str, Any] = {}
            if 'AutoAssociate' in bg['AccountGrouping']:
                account_grouping['auto_associate'] = bg['AccountGrouping']['AutoAssociate']
            if 'ResponsibilityTransferArn' in bg['AccountGrouping']:
                account_grouping['responsibility_transfer_arn'] = bg['AccountGrouping'][
                    'ResponsibilityTransferArn'
                ]
            formatted_group['account_grouping'] = account_grouping

        if 'CreationTime' in bg:
            formatted_group['creation_time'] = epoch_seconds_to_utc_iso_string(bg['CreationTime'])

        if 'LastModifiedTime' in bg:
            formatted_group['last_modified_time'] = epoch_seconds_to_utc_iso_string(
                bg['LastModifiedTime']
            )

        formatted_groups.append(formatted_group)

    return formatted_groups


async def list_account_associations(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List linked account associations from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted account association information.
    """
    try:
        request_params: Dict[str, Any] = {}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_linked_accounts: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching account associations page {page_count}')
            response = bc_client.list_account_associations(**request_params)

            page_linked_accounts = response.get('LinkedAccounts', [])
            all_linked_accounts.extend(page_linked_accounts)

            await ctx.info(
                f'Retrieved {len(page_linked_accounts)} linked accounts '
                f'(total: {len(all_linked_accounts)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_accounts = _format_linked_accounts(all_linked_accounts)

        response_data: Dict[str, Any] = {
            'linked_accounts': formatted_accounts,
            'total_count': len(formatted_accounts),
            'billing_period': billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listAccountAssociations', 'Billing Conductor')


def _format_linked_accounts(
    linked_accounts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format linked account objects from the AWS API response.

    Args:
        linked_accounts: List of linked account objects from the AWS API.

    Returns:
        List of formatted linked account objects.
    """
    formatted_accounts = []

    for account in linked_accounts:
        formatted_account: Dict[str, Any] = {
            'account_id': account.get('AccountId'),
            'account_name': account.get('AccountName'),
            'account_email': account.get('AccountEmail'),
        }

        if account.get('BillingGroupArn'):
            formatted_account['billing_group_arn'] = account['BillingGroupArn']

        formatted_accounts.append(formatted_account)

    return formatted_accounts


async def list_billing_group_cost_reports(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List billing group cost report summaries from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted billing group cost report information.
    """
    try:
        request_params: Dict[str, Any] = {}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_cost_reports: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching billing group cost reports page {page_count}')
            response = bc_client.list_billing_group_cost_reports(**request_params)

            page_cost_reports = response.get('BillingGroupCostReports', [])
            all_cost_reports.extend(page_cost_reports)

            await ctx.info(
                f'Retrieved {len(page_cost_reports)} cost reports '
                f'(total: {len(all_cost_reports)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_cost_reports = _format_billing_group_cost_reports(all_cost_reports)

        response_data: Dict[str, Any] = {
            'billing_group_cost_reports': formatted_cost_reports,
            'total_count': len(formatted_cost_reports),
            'billing_period': billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listBillingGroupCostReports', 'Billing Conductor'
        )


async def get_billing_group_cost_report(
    ctx: Context,
    arn: str,
    billing_period_range: Optional[str] = None,
    group_by: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get detailed cost report for a specific billing group.

    Args:
        ctx: The MCP context object.
        arn: The billing group ARN.
        billing_period_range: Optional JSON string with billing period range.
        group_by: Optional JSON string with group by attributes.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted billing group cost report results.
    """
    try:
        request_params: Dict[str, Any] = {'Arn': arn}

        parsed_range = parse_json(billing_period_range, 'billing_period_range')
        if parsed_range:
            request_params['BillingPeriodRange'] = parsed_range

        parsed_group_by = parse_json(group_by, 'group_by')
        if parsed_group_by:
            request_params['GroupBy'] = parsed_group_by

        bc_client = _create_billing_conductor_client()

        all_results: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching billing group cost report page {page_count}')
            response = bc_client.get_billing_group_cost_report(**request_params)

            page_results = response.get('BillingGroupCostReportResults', [])
            all_results.extend(page_results)

            await ctx.info(
                f'Retrieved {len(page_results)} cost report results '
                f'(total: {len(all_results)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_results = _format_billing_group_cost_report_results(all_results)

        response_data: Dict[str, Any] = {
            'billing_group_cost_report_results': formatted_results,
            'total_count': len(formatted_results),
            'arn': arn,
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'getBillingGroupCostReport', 'Billing Conductor'
        )


def _format_billing_group_cost_reports(
    cost_reports: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format billing group cost report objects from the AWS API response.

    Args:
        cost_reports: List of billing group cost report objects from the AWS API.

    Returns:
        List of formatted billing group cost report objects.
    """
    formatted_reports = []

    for report in cost_reports:
        formatted_report: Dict[str, Any] = {
            'arn': report.get('Arn'),
            'aws_cost': report.get('AWSCost'),
            'proforma_cost': report.get('ProformaCost'),
            'margin': report.get('Margin'),
            'margin_percentage': report.get('MarginPercentage'),
            'currency': report.get('Currency'),
        }

        formatted_reports.append(formatted_report)

    return formatted_reports


def _format_billing_group_cost_report_results(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format billing group cost report result objects from the AWS API response.

    Args:
        results: List of billing group cost report result objects from the AWS API.

    Returns:
        List of formatted billing group cost report result objects.
    """
    formatted_results = []

    for result in results:
        formatted_result: Dict[str, Any] = {
            'arn': result.get('Arn'),
            'aws_cost': result.get('AWSCost'),
            'proforma_cost': result.get('ProformaCost'),
            'margin': result.get('Margin'),
            'margin_percentage': result.get('MarginPercentage'),
            'currency': result.get('Currency'),
        }

        if 'Attributes' in result:
            formatted_result['attributes'] = [
                {'key': attr.get('Key'), 'value': attr.get('Value')}
                for attr in result['Attributes']
            ]

        formatted_results.append(formatted_result)

    return formatted_results


async def list_custom_line_items(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List custom line items from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted custom line item information.
    """
    try:
        request_params: Dict[str, Any] = {}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_custom_line_items: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching custom line items page {page_count}')
            response = bc_client.list_custom_line_items(**request_params)

            page_items = response.get('CustomLineItems', [])
            all_custom_line_items.extend(page_items)

            await ctx.info(
                f'Retrieved {len(page_items)} custom line items '
                f'(total: {len(all_custom_line_items)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_items = _format_custom_line_items(all_custom_line_items)

        response_data: Dict[str, Any] = {
            'custom_line_items': formatted_items,
            'total_count': len(formatted_items),
            'billing_period': billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listCustomLineItems', 'Billing Conductor')


async def list_custom_line_item_versions(
    ctx: Context,
    arn: str,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List versions for a specific custom line item.

    Args:
        ctx: The MCP context object.
        arn: The custom line item ARN.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted custom line item version information.
    """
    try:
        request_params: Dict[str, Any] = {'Arn': arn}

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_versions: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching custom line item versions page {page_count}')
            response = bc_client.list_custom_line_item_versions(**request_params)

            page_versions = response.get('CustomLineItemVersions', [])
            all_versions.extend(page_versions)

            await ctx.info(
                f'Retrieved {len(page_versions)} custom line item versions '
                f'(total: {len(all_versions)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_versions = _format_custom_line_item_versions(all_versions)

        response_data: Dict[str, Any] = {
            'custom_line_item_versions': formatted_versions,
            'total_count': len(formatted_versions),
            'arn': arn,
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listCustomLineItemVersions', 'Billing Conductor'
        )


async def list_resources_associated_to_custom_line_item(
    ctx: Context,
    arn: str,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List resources associated to a custom line item.

    Args:
        ctx: The MCP context object.
        arn: The custom line item ARN.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted associated resource information.
    """
    try:
        request_params: Dict[str, Any] = {'Arn': arn}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_resources: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching associated resources page {page_count}')
            response = bc_client.list_resources_associated_to_custom_line_item(
                **request_params
            )

            page_resources = response.get('AssociatedResources', [])
            all_resources.extend(page_resources)

            await ctx.info(
                f'Retrieved {len(page_resources)} associated resources '
                f'(total: {len(all_resources)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_resources = _format_associated_resources(all_resources)

        response_data: Dict[str, Any] = {
            'arn': arn,
            'associated_resources': formatted_resources,
            'total_count': len(formatted_resources),
            'billing_period': billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listResourcesAssociatedToCustomLineItem', 'Billing Conductor'
        )


def _format_custom_line_items(
    custom_line_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format custom line item objects from the AWS API response."""
    formatted_items = []

    for item in custom_line_items:
        formatted_item: Dict[str, Any] = {
            'arn': item.get('Arn'),
            'name': item.get('Name'),
            'description': item.get('Description'),
            'account_id': item.get('AccountId'),
            'billing_group_arn': item.get('BillingGroupArn'),
            'computation_rule': item.get('ComputationRule'),
            'currency_code': item.get('CurrencyCode'),
            'association_size': item.get('AssociationSize'),
            'product_code': item.get('ProductCode'),
        }

        if 'ChargeDetails' in item:
            formatted_item['charge_details'] = _format_charge_details(item['ChargeDetails'])

        if 'PresentationDetails' in item:
            formatted_item['presentation_details'] = {
                'service': item['PresentationDetails'].get('Service'),
            }

        if 'CreationTime' in item:
            formatted_item['creation_time'] = epoch_seconds_to_utc_iso_string(item['CreationTime'])

        if 'LastModifiedTime' in item:
            formatted_item['last_modified_time'] = epoch_seconds_to_utc_iso_string(
                item['LastModifiedTime']
            )

        formatted_items.append(formatted_item)

    return formatted_items


def _format_charge_details(charge_details: Dict[str, Any]) -> Dict[str, Any]:
    """Format charge details from the AWS API response."""
    formatted: Dict[str, Any] = {
        'type': charge_details.get('Type'),
    }

    if 'Flat' in charge_details:
        formatted['flat'] = {
            'charge_value': charge_details['Flat'].get('ChargeValue'),
        }

    if 'Percentage' in charge_details:
        formatted['percentage'] = {
            'percentage_value': charge_details['Percentage'].get('PercentageValue'),
        }

    if 'LineItemFilters' in charge_details:
        formatted['line_item_filters'] = _format_line_item_filters(
            charge_details['LineItemFilters']
        )

    return formatted


def _format_line_item_filters(
    line_item_filters: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format line item filters from the AWS API response."""
    formatted_filters = []

    for lif in line_item_filters:
        formatted_filter: Dict[str, Any] = {
            'attribute': lif.get('Attribute'),
            'match_option': lif.get('MatchOption'),
        }

        if 'AttributeValues' in lif:
            formatted_filter['attribute_values'] = lif['AttributeValues']

        if 'Values' in lif:
            formatted_filter['values'] = lif['Values']

        formatted_filters.append(formatted_filter)

    return formatted_filters


def _format_custom_line_item_versions(
    versions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format custom line item version objects from the AWS API response."""
    formatted_versions = []

    for version in versions:
        formatted_version: Dict[str, Any] = {
            'arn': version.get('Arn'),
            'name': version.get('Name'),
            'description': version.get('Description'),
            'account_id': version.get('AccountId'),
            'billing_group_arn': version.get('BillingGroupArn'),
            'computation_rule': version.get('ComputationRule'),
            'currency_code': version.get('CurrencyCode'),
            'association_size': version.get('AssociationSize'),
            'product_code': version.get('ProductCode'),
            'start_billing_period': version.get('StartBillingPeriod'),
            'end_billing_period': version.get('EndBillingPeriod'),
        }

        if 'ChargeDetails' in version:
            formatted_version['charge_details'] = _format_charge_details(
                version['ChargeDetails']
            )

        if 'PresentationDetails' in version:
            formatted_version['presentation_details'] = {
                'service': version['PresentationDetails'].get('Service'),
            }

        if 'StartTime' in version:
            formatted_version['start_time'] = epoch_seconds_to_utc_iso_string(version['StartTime'])

        if 'CreationTime' in version:
            formatted_version['creation_time'] = epoch_seconds_to_utc_iso_string(
                version['CreationTime']
            )

        if 'LastModifiedTime' in version:
            formatted_version['last_modified_time'] = epoch_seconds_to_utc_iso_string(
                version['LastModifiedTime']
            )

        formatted_versions.append(formatted_version)

    return formatted_versions


def _format_associated_resources(
    associated_resources: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format associated resource objects from the AWS API response."""
    formatted_resources = []

    for resource in associated_resources:
        formatted_resource: Dict[str, Any] = {
            'arn': resource.get('Arn'),
            'relationship': resource.get('Relationship'),
            'end_billing_period': resource.get('EndBillingPeriod'),
        }

        formatted_resources.append(formatted_resource)

    return formatted_resources


async def list_pricing_rules(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing rules from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted pricing rule information.
    """
    try:
        request_params: Dict[str, Any] = {}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_pricing_rules: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching pricing rules page {page_count}')
            response = bc_client.list_pricing_rules(**request_params)

            page_rules = response.get('PricingRules', [])
            all_pricing_rules.extend(page_rules)

            await ctx.info(
                f'Retrieved {len(page_rules)} pricing rules '
                f'(total: {len(all_pricing_rules)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_rules = _format_pricing_rules(all_pricing_rules)

        response_data: Dict[str, Any] = {
            'pricing_rules': formatted_rules,
            'total_count': len(formatted_rules),
            'billing_period': billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listPricingRules', 'Billing Conductor')


async def list_pricing_plans(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing plans from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted pricing plan information.
    """
    try:
        request_params: Dict[str, Any] = {}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        parsed_filters = parse_json(filters, 'filters')
        if parsed_filters:
            request_params['Filters'] = parsed_filters

        bc_client = _create_billing_conductor_client()

        all_pricing_plans: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(f'Fetching pricing plans page {page_count}')
            response = bc_client.list_pricing_plans(**request_params)

            page_plans = response.get('PricingPlans', [])
            all_pricing_plans.extend(page_plans)

            await ctx.info(
                f'Retrieved {len(page_plans)} pricing plans '
                f'(total: {len(all_pricing_plans)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        formatted_plans = _format_pricing_plans(all_pricing_plans)

        response_data: Dict[str, Any] = {
            'pricing_plans': formatted_plans,
            'total_count': len(formatted_plans),
            'billing_period': billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listPricingPlans', 'Billing Conductor')


async def list_pricing_rules_associated_to_pricing_plan(
    ctx: Context,
    pricing_plan_arn: str,
    billing_period: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing rules associated with a pricing plan.

    Args:
        ctx: The MCP context object.
        pricing_plan_arn: The ARN of the pricing plan.
        billing_period: Optional billing period in YYYY-MM format.
        max_results: Optional maximum number of results per page (1-100).
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the pricing rule ARNs associated with the pricing plan.
    """
    try:
        request_params: Dict[str, Any] = {'PricingPlanArn': pricing_plan_arn}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        if max_results is not None:
            request_params['MaxResults'] = max_results

        bc_client = _create_billing_conductor_client()

        all_pricing_rule_arns: List[str] = []
        current_token = next_token
        page_count = 0
        response_billing_period = None
        response_pricing_plan_arn = None

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(
                f'Fetching pricing rules associated to pricing plan page {page_count}'
            )
            response = bc_client.list_pricing_rules_associated_to_pricing_plan(
                **request_params
            )

            page_arns = response.get('PricingRuleArns', [])
            all_pricing_rule_arns.extend(page_arns)

            if response_billing_period is None:
                response_billing_period = response.get('BillingPeriod')
            if response_pricing_plan_arn is None:
                response_pricing_plan_arn = response.get('PricingPlanArn')

            await ctx.info(
                f'Retrieved {len(page_arns)} pricing rule ARNs '
                f'(total: {len(all_pricing_rule_arns)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        response_data: Dict[str, Any] = {
            'pricing_rule_arns': all_pricing_rule_arns,
            'total_count': len(all_pricing_rule_arns),
            'pricing_plan_arn': response_pricing_plan_arn or pricing_plan_arn,
            'billing_period': response_billing_period or billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listPricingRulesAssociatedToPricingPlan', 'Billing Conductor'
        )


async def list_pricing_plans_associated_with_pricing_rule(
    ctx: Context,
    pricing_rule_arn: str,
    billing_period: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing plans associated with a pricing rule.

    Args:
        ctx: The MCP context object.
        pricing_rule_arn: The ARN of the pricing rule.
        billing_period: Optional billing period in YYYY-MM format.
        max_results: Optional maximum number of results per page (1-100).
        max_pages: Maximum number of API pages to fetch.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the pricing plan ARNs associated with the pricing rule.
    """
    try:
        request_params: Dict[str, Any] = {'PricingRuleArn': pricing_rule_arn}

        if billing_period:
            request_params['BillingPeriod'] = billing_period

        if max_results is not None:
            request_params['MaxResults'] = max_results

        bc_client = _create_billing_conductor_client()

        all_pricing_plan_arns: List[str] = []
        current_token = next_token
        page_count = 0
        response_billing_period = None
        response_pricing_rule_arn = None

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['NextToken'] = current_token

            await ctx.info(
                f'Fetching pricing plans associated with pricing rule page {page_count}'
            )
            response = bc_client.list_pricing_plans_associated_with_pricing_rule(
                **request_params
            )

            page_arns = response.get('PricingPlanArns', [])
            all_pricing_plan_arns.extend(page_arns)

            if response_billing_period is None:
                response_billing_period = response.get('BillingPeriod')
            if response_pricing_rule_arn is None:
                response_pricing_rule_arn = response.get('PricingRuleArn')

            await ctx.info(
                f'Retrieved {len(page_arns)} pricing plan ARNs '
                f'(total: {len(all_pricing_plan_arns)})'
            )

            current_token = response.get('NextToken')
            if not current_token:
                break

        response_data: Dict[str, Any] = {
            'pricing_plan_arns': all_pricing_plan_arns,
            'total_count': len(all_pricing_plan_arns),
            'pricing_rule_arn': response_pricing_rule_arn or pricing_rule_arn,
            'billing_period': response_billing_period or billing_period or 'current',
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listPricingPlansAssociatedWithPricingRule', 'Billing Conductor'
        )


def _format_pricing_rules(pricing_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format pricing rule objects from the AWS API response."""
    formatted_rules = []

    for rule in pricing_rules:
        formatted_rule: Dict[str, Any] = {
            'arn': rule.get('Arn'),
            'name': rule.get('Name'),
            'description': rule.get('Description'),
            'type': rule.get('Type'),
            'scope': rule.get('Scope'),
            'modifier_percentage': rule.get('ModifierPercentage'),
            'associated_pricing_plan_count': rule.get('AssociatedPricingPlanCount'),
            'service': rule.get('Service'),
            'operation': rule.get('Operation'),
            'usage_type': rule.get('UsageType'),
            'billing_entity': rule.get('BillingEntity'),
        }

        if 'Tiering' in rule:
            tiering: Dict[str, Any] = {}
            free_tier = rule['Tiering'].get('FreeTier')
            if free_tier is not None:
                tiering['free_tier'] = {'activated': free_tier.get('Activated')}
            formatted_rule['tiering'] = tiering

        if 'CreationTime' in rule:
            formatted_rule['creation_time'] = epoch_seconds_to_utc_iso_string(rule['CreationTime'])

        if 'LastModifiedTime' in rule:
            formatted_rule['last_modified_time'] = epoch_seconds_to_utc_iso_string(
                rule['LastModifiedTime']
            )

        formatted_rules.append(formatted_rule)

    return formatted_rules


def _format_pricing_plans(pricing_plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format pricing plan objects from the AWS API response."""
    formatted_plans = []

    for plan in pricing_plans:
        formatted_plan: Dict[str, Any] = {
            'arn': plan.get('Arn'),
            'name': plan.get('Name'),
            'description': plan.get('Description'),
            'size': plan.get('Size'),
        }

        if 'CreationTime' in plan:
            formatted_plan['creation_time'] = epoch_seconds_to_utc_iso_string(plan['CreationTime'])

        if 'LastModifiedTime' in plan:
            formatted_plan['last_modified_time'] = epoch_seconds_to_utc_iso_string(
                plan['LastModifiedTime']
            )

        formatted_plans.append(formatted_plan)

    return formatted_plans
