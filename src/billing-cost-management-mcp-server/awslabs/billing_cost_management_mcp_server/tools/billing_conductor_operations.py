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

import re
from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    first_page_fields,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    parse_json,
    with_pagination,
)
from ..utilities.constants import REGION_US_EAST_1
from ..utilities.time_utils import timestamp_to_utc_iso_string
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from fastmcp import Context
from typing import Any, Dict, List, Optional


# AWS Billing Conductor is a global service that operates in us-east-1
BILLING_CONDUCTOR_DEFAULT_REGION = REGION_US_EAST_1

# The service computes Margin as ProformaCost - AWSCost and MarginPercentage as Margin / AWSCost
# (0 when AWSCost is 0). The field name says percentage, but the value is a fraction.
MARGIN_NOTE = (
    'margin = proforma_cost - aws_cost; negative means the proforma cost is below the AWS cost. '
    'margin_percentage = margin / aws_cost as a fraction, not a percent: -0.25 means -25%; '
    'it is 0.0 when aws_cost is 0.'
)


def _create_billing_conductor_client() -> Any:
    """Create a Billing Conductor client with the default region.

    Returns:
        boto3.client: AWS Billing Conductor client.
    """
    return create_aws_client('billingconductor', region_name=BILLING_CONDUCTOR_DEFAULT_REGION)


def _bc_page_spec(result_key: str) -> PageSpec:
    """Build the PageSpec shared by the Billing Conductor lists that take MaxResults 1-100."""
    return PageSpec(
        result_key=result_key,
        token_param='NextToken',
        token_key_in_response='NextToken',
        page_max=100,
        page_size_param='MaxResults',
        # Billing Conductor reports a bad caller next_token as ValidationException.
        caller_token_error_codes=frozenset({'ValidationException'}),
    )


def _request_params(
    base: Optional[Dict[str, Any]] = None,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
) -> Dict[str, Any]:
    """Build request parameters shared by the Billing Conductor list operations.

    Args:
        base: Required parameters of the operation (e.g. ``Arn``).
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.

    Returns:
        Request parameters without the token or page size.
    """
    request_params: Dict[str, Any] = dict(base or {})
    if billing_period:
        request_params['BillingPeriod'] = billing_period
    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['Filters'] = parsed_filters
    return request_params


# The service's BillingPeriod pattern, anchored: YYYY-MM, with an optional leading zero.
_BILLING_PERIOD_PATTERN = re.compile(r'([0-9]{4})-(0?[1-9]|1[012])')

FUTURE_BILLING_PERIOD_NOTE = (
    'billing_period is after the current month (UTC), so this is a projection, not a record: '
    'Billing Conductor lists what is recorded today as in effect that month and leaves out items '
    'already set to end before then, such as a billing group whose primary account has left. '
    'Changes made between now and the start of that month are not shown.'
)


def _utc_today() -> date:
    """Return today's date in UTC. Tests patch this to pin the current billing period."""
    return datetime.now(timezone.utc).date()


def _current_billing_period() -> str:
    """Return the current UTC month as YYYY-MM."""
    today = _utc_today()
    return f'{today.year:04d}-{today.month:02d}'


def _is_future_billing_period(billing_period: Optional[str]) -> bool:
    """Return True when billing_period is a well-formed month after the current UTC month.

    A missing or malformed value is not future; the service validates the format.
    """
    match = _BILLING_PERIOD_PATTERN.fullmatch(billing_period or '')
    if not match:
        return False
    today = _utc_today()
    return (int(match.group(1)), int(match.group(2))) > (today.year, today.month)


def _reject_future_billing_period(billing_period: Optional[str], field: str, outcome: str) -> None:
    """Raise ValueError when a cost report is asked for a month that has not started.

    Args:
        billing_period: The requested month (YYYY-MM).
        field: The parameter name to quote in the message.
        outcome: What the service returns for that month, quoted in the message.

    Raises:
        ValueError: billing_period is after the current UTC month.
    """
    if _is_future_billing_period(billing_period):
        raise ValueError(
            f'{field} {billing_period} is after the current month ({_current_billing_period()}, '
            f'UTC). Billing Conductor has no costs for a month that has not started and {outcome}. '
            'Use the current month (month-to-date) or an earlier one.'
        )


def _future_period_fields(billing_period: Optional[str]) -> Dict[str, Any]:
    """Return the projection flag and note for a configuration list asked for a future month."""
    if not _is_future_billing_period(billing_period):
        return {}
    return {'billing_period_is_future': True, 'billing_period_note': FUTURE_BILLING_PERIOD_NOTE}


# ListBillingGroups: MaxResults 1-100.
BC_LIST_BILLING_GROUPS = _bc_page_spec('BillingGroups')


async def list_billing_groups(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List billing groups from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_items: Most billing groups to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted billing group information and a ``pagination`` block.
    """
    try:
        request_params = _request_params(billing_period=billing_period, filters=filters)
        bc_client = _create_billing_conductor_client()

        billing_groups, _, pagination = await paginate_aws_items(
            ctx,
            'ListBillingGroups',
            bc_client.list_billing_groups,
            request_params,
            BC_LIST_BILLING_GROUPS,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'billing_groups': _format_billing_groups(billing_groups),
            'billing_period': billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

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
            formatted_group['creation_time'] = timestamp_to_utc_iso_string(bg['CreationTime'])

        if 'LastModifiedTime' in bg:
            formatted_group['last_modified_time'] = timestamp_to_utc_iso_string(
                bg['LastModifiedTime']
            )

        formatted_groups.append(formatted_group)

    return formatted_groups


# ListAccountAssociations has no page-size parameter: the service returns up to 100 linked
# accounts per page and can return a short page with a token. With an AccountId/AccountIds
# filter it returns a single page (up to 30).
BC_LIST_ACCOUNT_ASSOCIATIONS = PageSpec(
    result_key='LinkedAccounts',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=100,
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


async def list_account_associations(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List linked account associations from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_items: Most linked accounts to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted account association information and a ``pagination`` block.
    """
    try:
        request_params = _request_params(billing_period=billing_period, filters=filters)
        bc_client = _create_billing_conductor_client()

        linked_accounts, _, pagination = await paginate_aws_items(
            ctx,
            'ListAccountAssociations',
            bc_client.list_account_associations,
            request_params,
            BC_LIST_ACCOUNT_ASSOCIATIONS,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'linked_accounts': _format_linked_accounts(linked_accounts),
            'billing_period': billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

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


# ListBillingGroupCostReports: MaxResults 1-100.
BC_LIST_BILLING_GROUP_COST_REPORTS = _bc_page_spec('BillingGroupCostReports')


async def list_billing_group_cost_reports(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List billing group cost report summaries from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_items: Most cost reports to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted billing group cost reports and a ``pagination`` block.
    """
    try:
        _reject_future_billing_period(
            billing_period, 'billing_period', 'returns $0 for every billing group'
        )
        request_params = _request_params(billing_period=billing_period, filters=filters)
        bc_client = _create_billing_conductor_client()

        cost_reports, _, pagination = await paginate_aws_items(
            ctx,
            'ListBillingGroupCostReports',
            bc_client.list_billing_group_cost_reports,
            request_params,
            BC_LIST_BILLING_GROUP_COST_REPORTS,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'billing_group_cost_reports': _format_billing_group_cost_reports(cost_reports),
            'billing_period': billing_period or 'current',
        }
        if cost_reports:
            response_data['margin_note'] = MARGIN_NOTE
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingGroupCostReports', 'Billing Conductor')


# GetBillingGroupCostReport: MaxResults 200-300. The token is bound to Arn, GroupBy and
# BillingPeriodRange and expires shortly after the first call; it is not bound to MaxResults, so
# each page can ask for a different size within the range. Every page is full except the last.
# A changed parameter or a malformed token fails with ValidationException, and an expired token
# can fail with ValidationException or InternalServerException. Either code on a call that
# carried a next_token means that token is unusable, so the helper maps it to
# invalid_next_token only then. The expired-token InternalServerException need not name the
# token, so this spec does not require the message to.
BC_GET_BILLING_GROUP_COST_REPORT = PageSpec(
    result_key='BillingGroupCostReportResults',
    token_param='NextToken',
    token_key_in_response='NextToken',
    page_max=300,
    page_size_param='MaxResults',
    page_min=200,
    caller_token_error_codes=frozenset({'ValidationException', 'InternalServerException'}),
    caller_token_message_required=False,
)


async def get_billing_group_cost_report(
    ctx: Context,
    arn: str,
    billing_period_range: Optional[str] = None,
    group_by: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Get detailed cost report for a specific billing group.

    Args:
        ctx: The MCP context object.
        arn: The billing group ARN.
        billing_period_range: Optional JSON string with billing period range.
        group_by: Optional JSON string with group by attributes.
        max_items: Most cost report results to return. None fetches every page. Pages hold 200
            to 300 results, so a max_items below 200 can return up to 200.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted billing group cost report results and a ``pagination``
        block.
    """
    try:
        request_params: Dict[str, Any] = {'Arn': arn}

        parsed_range = parse_json(billing_period_range, 'billing_period_range')
        if parsed_range:
            if isinstance(parsed_range, dict):
                _reject_future_billing_period(
                    parsed_range.get('InclusiveStartBillingPeriod'),
                    'InclusiveStartBillingPeriod',
                    'returns no results',
                )
            request_params['BillingPeriodRange'] = parsed_range

        parsed_group_by = parse_json(group_by, 'group_by')
        if parsed_group_by:
            request_params['GroupBy'] = parsed_group_by

        bc_client = _create_billing_conductor_client()

        results, _, pagination = await paginate_aws_items(
            ctx,
            'GetBillingGroupCostReport',
            bc_client.get_billing_group_cost_report,
            request_params,
            BC_GET_BILLING_GROUP_COST_REPORT,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'billing_group_cost_report_results': _format_billing_group_cost_report_results(
                results
            ),
            'arn': arn,
        }
        if results:
            response_data['margin_note'] = MARGIN_NOTE
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'getBillingGroupCostReport', 'Billing Conductor')


def _plain_decimal(value: Optional[str]) -> Optional[str]:
    """Rewrite a cost report amount string in plain decimal notation, digit for digit.

    The service can return a small or large amount in exponent form ("5.0E-7"). Decimal
    parses it exactly and format 'f' writes it without an exponent or any rounding. Returns
    None for a missing, non-numeric or non-finite value.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return format(number, 'f') if number.is_finite() else None


def _format_cost_report_base(report: Dict[str, Any]) -> Dict[str, Any]:
    """Format the common fields of a billing group cost report object.

    Args:
        report: A cost report object from the Billing Conductor API.

    Returns:
        Dict with formatted common Billing Conductor cost report fields.
    """
    formatted: Dict[str, Any] = {
        'arn': report.get('Arn'),
        'aws_cost': report.get('AWSCost'),
        'proforma_cost': report.get('ProformaCost'),
        'margin': report.get('Margin'),
        'margin_percentage': report.get('MarginPercentage'),
        'currency': report.get('Currency'),
    }
    formatted['decimal_values'] = {
        key: _plain_decimal(formatted[key])
        for key in ('aws_cost', 'proforma_cost', 'margin', 'margin_percentage')
    }
    return formatted


def _format_billing_group_cost_reports(
    cost_reports: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format billing group cost report objects from the AWS API response.

    Args:
        cost_reports: List of billing group cost report objects from the AWS API.

    Returns:
        List of formatted billing group cost report objects.
    """
    return [_format_cost_report_base(report) for report in cost_reports]


def _format_billing_group_cost_report_results(
    results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format billing group cost report result objects from the AWS API response.

    Extends the base cost report format with Attributes when present.

    Args:
        results: List of billing group cost report result objects from the AWS API.

    Returns:
        List of formatted billing group cost report result objects.
    """
    formatted_results = []

    for result in results:
        formatted_result = _format_cost_report_base(result)

        if 'Attributes' in result:
            formatted_result['attributes'] = [
                {'key': attr.get('Key'), 'value': attr.get('Value')}
                for attr in result['Attributes']
            ]

        formatted_results.append(formatted_result)

    return formatted_results


# ListCustomLineItems: MaxResults 1-100.
BC_LIST_CUSTOM_LINE_ITEMS = _bc_page_spec('CustomLineItems')


async def list_custom_line_items(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List custom line items from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_items: Most custom line items to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted custom line items and a ``pagination`` block.
    """
    try:
        request_params = _request_params(billing_period=billing_period, filters=filters)
        bc_client = _create_billing_conductor_client()

        custom_line_items, _, pagination = await paginate_aws_items(
            ctx,
            'ListCustomLineItems',
            bc_client.list_custom_line_items,
            request_params,
            BC_LIST_CUSTOM_LINE_ITEMS,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'custom_line_items': _format_custom_line_items(custom_line_items),
            'billing_period': billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listCustomLineItems', 'Billing Conductor')


# ListCustomLineItemVersions: MaxResults 1-100.
BC_LIST_CUSTOM_LINE_ITEM_VERSIONS = _bc_page_spec('CustomLineItemVersions')


async def list_custom_line_item_versions(
    ctx: Context,
    arn: str,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List versions for a specific custom line item.

    Args:
        ctx: The MCP context object.
        arn: The custom line item ARN.
        filters: Optional JSON string with filter criteria.
        max_items: Most versions to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted custom line item versions and a ``pagination`` block.
    """
    try:
        # No future-period check: BillingPeriodRange here selects versions, and a version can
        # legitimately start in a future month.
        request_params = _request_params({'Arn': arn}, filters=filters)
        bc_client = _create_billing_conductor_client()

        versions, _, pagination = await paginate_aws_items(
            ctx,
            'ListCustomLineItemVersions',
            bc_client.list_custom_line_item_versions,
            request_params,
            BC_LIST_CUSTOM_LINE_ITEM_VERSIONS,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'custom_line_item_versions': _format_custom_line_item_versions(versions),
            'arn': arn,
        }
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listCustomLineItemVersions', 'Billing Conductor')


# ListResourcesAssociatedToCustomLineItem: MaxResults 1-100.
BC_LIST_RESOURCES_ASSOCIATED_TO_CUSTOM_LINE_ITEM = _bc_page_spec('AssociatedResources')


async def list_resources_associated_to_custom_line_item(
    ctx: Context,
    arn: str,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List resources associated to a custom line item.

    Args:
        ctx: The MCP context object.
        arn: The custom line item ARN.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_items: Most associated resources to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted associated resources and a ``pagination`` block.
    """
    try:
        request_params = _request_params(
            {'Arn': arn}, billing_period=billing_period, filters=filters
        )
        bc_client = _create_billing_conductor_client()

        resources, _, pagination = await paginate_aws_items(
            ctx,
            'ListResourcesAssociatedToCustomLineItem',
            bc_client.list_resources_associated_to_custom_line_item,
            request_params,
            BC_LIST_RESOURCES_ASSOCIATED_TO_CUSTOM_LINE_ITEM,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'arn': arn,
            'associated_resources': _format_associated_resources(resources),
            'billing_period': billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listResourcesAssociatedToCustomLineItem', 'Billing Conductor'
        )


def _format_custom_line_item_base(item: Dict[str, Any]) -> Dict[str, Any]:
    """Format the common fields of a custom line item or version object.

    Args:
        item: A custom line item or version object from the AWS API.

    Returns:
        Dict with formatted common custom line item fields.
    """
    formatted: Dict[str, Any] = {
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
        formatted['charge_details'] = _format_charge_details(item['ChargeDetails'])

    if 'PresentationDetails' in item:
        formatted['presentation_details'] = {
            'service': item['PresentationDetails'].get('Service'),
        }

    if 'CreationTime' in item:
        formatted['creation_time'] = timestamp_to_utc_iso_string(item['CreationTime'])

    if 'LastModifiedTime' in item:
        formatted['last_modified_time'] = timestamp_to_utc_iso_string(item['LastModifiedTime'])

    return formatted


def _format_custom_line_items(
    custom_line_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format custom line item objects from the AWS API response."""
    return [_format_custom_line_item_base(item) for item in custom_line_items]


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
    """Format custom line item version objects from the AWS API response.

    Extends the base custom line item format with version-specific fields.
    """
    formatted_versions = []

    for version in versions:
        formatted_version = _format_custom_line_item_base(version)

        # CLI Version-specific fields
        formatted_version['start_billing_period'] = version.get('StartBillingPeriod')
        formatted_version['end_billing_period'] = version.get('EndBillingPeriod')

        if 'StartTime' in version:
            formatted_version['start_time'] = timestamp_to_utc_iso_string(version['StartTime'])

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


# ListPricingRules: MaxResults 1-100.
BC_LIST_PRICING_RULES = _bc_page_spec('PricingRules')


async def list_pricing_rules(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing rules from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_items: Most pricing rules to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted pricing rules and a ``pagination`` block.
    """
    try:
        request_params = _request_params(billing_period=billing_period, filters=filters)
        bc_client = _create_billing_conductor_client()

        pricing_rules, _, pagination = await paginate_aws_items(
            ctx,
            'ListPricingRules',
            bc_client.list_pricing_rules,
            request_params,
            BC_LIST_PRICING_RULES,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'pricing_rules': _format_pricing_rules(pricing_rules),
            'billing_period': billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listPricingRules', 'Billing Conductor')


# ListPricingPlans: MaxResults 1-100.
BC_LIST_PRICING_PLANS = _bc_page_spec('PricingPlans')


async def list_pricing_plans(
    ctx: Context,
    billing_period: Optional[str] = None,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing plans from AWS Billing Conductor.

    Args:
        ctx: The MCP context object.
        billing_period: Optional billing period in YYYY-MM format.
        filters: Optional JSON string with filter criteria.
        max_items: Most pricing plans to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the formatted pricing plans and a ``pagination`` block.
    """
    try:
        request_params = _request_params(billing_period=billing_period, filters=filters)
        bc_client = _create_billing_conductor_client()

        pricing_plans, _, pagination = await paginate_aws_items(
            ctx,
            'ListPricingPlans',
            bc_client.list_pricing_plans,
            request_params,
            BC_LIST_PRICING_PLANS,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'pricing_plans': _format_pricing_plans(pricing_plans),
            'billing_period': billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listPricingPlans', 'Billing Conductor')


# ListPricingRulesAssociatedToPricingPlan: MaxResults 1-100.
BC_LIST_PRICING_RULES_FOR_PLAN = _bc_page_spec('PricingRuleArns')


async def list_pricing_rules_associated_to_pricing_plan(
    ctx: Context,
    pricing_plan_arn: str,
    billing_period: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing rules associated with a pricing plan.

    Args:
        ctx: The MCP context object.
        pricing_plan_arn: The ARN of the pricing plan.
        billing_period: Optional billing period in YYYY-MM format.
        max_items: Most pricing rule ARNs to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the pricing rule ARNs associated with the pricing plan and a
        ``pagination`` block.
    """
    try:
        request_params = _request_params(
            {'PricingPlanArn': pricing_plan_arn}, billing_period=billing_period
        )
        bc_client = _create_billing_conductor_client()

        pricing_rule_arns, pages, pagination = await paginate_aws_items(
            ctx,
            'ListPricingRulesAssociatedToPricingPlan',
            bc_client.list_pricing_rules_associated_to_pricing_plan,
            request_params,
            BC_LIST_PRICING_RULES_FOR_PLAN,
            max_items=max_items,
            next_token=next_token,
        )

        first_page = first_page_fields(pages, ['BillingPeriod', 'PricingPlanArn'])
        response_data: Dict[str, Any] = {
            'pricing_rule_arns': pricing_rule_arns,
            'pricing_plan_arn': first_page.get('PricingPlanArn') or pricing_plan_arn,
            'billing_period': first_page.get('BillingPeriod') or billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

    except Exception as e:
        return await handle_aws_error(
            ctx, e, 'listPricingRulesAssociatedToPricingPlan', 'Billing Conductor'
        )


# ListPricingPlansAssociatedWithPricingRule: MaxResults 1-100.
BC_LIST_PRICING_PLANS_FOR_RULE = _bc_page_spec('PricingPlanArns')


async def list_pricing_plans_associated_with_pricing_rule(
    ctx: Context,
    pricing_rule_arn: str,
    billing_period: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List pricing plans associated with a pricing rule.

    Args:
        ctx: The MCP context object.
        pricing_rule_arn: The ARN of the pricing rule.
        billing_period: Optional billing period in YYYY-MM format.
        max_items: Most pricing plan ARNs to return. None fetches every page.
        next_token: Optional pagination token to continue from.

    Returns:
        Dict containing the pricing plan ARNs associated with the pricing rule and a
        ``pagination`` block.
    """
    try:
        request_params = _request_params(
            {'PricingRuleArn': pricing_rule_arn}, billing_period=billing_period
        )
        bc_client = _create_billing_conductor_client()

        pricing_plan_arns, pages, pagination = await paginate_aws_items(
            ctx,
            'ListPricingPlansAssociatedWithPricingRule',
            bc_client.list_pricing_plans_associated_with_pricing_rule,
            request_params,
            BC_LIST_PRICING_PLANS_FOR_RULE,
            max_items=max_items,
            next_token=next_token,
        )

        first_page = first_page_fields(pages, ['BillingPeriod', 'PricingRuleArn'])
        response_data: Dict[str, Any] = {
            'pricing_plan_arns': pricing_plan_arns,
            'pricing_rule_arn': first_page.get('PricingRuleArn') or pricing_rule_arn,
            'billing_period': first_page.get('BillingPeriod') or billing_period or 'current',
            **_future_period_fields(billing_period),
        }
        return format_response('success', with_pagination(response_data, pagination))

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
            formatted_rule['creation_time'] = timestamp_to_utc_iso_string(rule['CreationTime'])

        if 'LastModifiedTime' in rule:
            formatted_rule['last_modified_time'] = timestamp_to_utc_iso_string(
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
            formatted_plan['creation_time'] = timestamp_to_utc_iso_string(plan['CreationTime'])

        if 'LastModifiedTime' in plan:
            formatted_plan['last_modified_time'] = timestamp_to_utc_iso_string(
                plan['LastModifiedTime']
            )

        formatted_plans.append(formatted_plan)

    return formatted_plans


async def get_billing_transfer_preference(
    ctx: Context,
    responsibility_transfer_arn: str,
) -> Dict[str, Any]:
    """Get the auto billing group creation preference for a billing transfer.

    Args:
        ctx: The MCP context object.
        responsibility_transfer_arn: The ARN of the billing transfer whose
            preference to retrieve.

    Returns:
        Dict containing the formatted billing transfer preference.
    """
    try:
        bc_client = _create_billing_conductor_client()

        await ctx.info(f'Fetching billing transfer preference for {responsibility_transfer_arn}')
        response = bc_client.get_billing_transfer_preference(
            ResponsibilityTransferArn=responsibility_transfer_arn
        )

        return format_response('success', _format_billing_transfer_preference(response))

    except Exception as e:
        return await handle_aws_error(ctx, e, 'getBillingTransferPreference', 'Billing Conductor')


def _format_billing_transfer_preference(preference: Dict[str, Any]) -> Dict[str, Any]:
    """Format a billing transfer preference from the AWS API response.

    Args:
        preference: A GetBillingTransferPreference response from the Billing Conductor API.

    Returns:
        Dict with the formatted billing transfer preference fields.
    """
    formatted: Dict[str, Any] = {
        'responsibility_transfer_arn': preference.get('ResponsibilityTransferArn'),
    }

    auto_creation = preference.get('AutoBillingTransferBillingGroupCreation')
    if auto_creation is not None:
        formatted['auto_billing_transfer_billing_group_creation'] = {
            'enabled': auto_creation.get('Enabled'),
            'pricing_plan_arn': auto_creation.get('PricingPlanArn'),
        }

    # Empty when the preference has never been set for the billing transfer.
    if preference.get('LastModifiedTime') is not None:
        formatted['last_modified_time'] = timestamp_to_utc_iso_string(
            preference['LastModifiedTime']
        )

    return formatted
