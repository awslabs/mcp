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

"""AWS Billing operations for the AWS Billing and Cost Management MCP server.

This module contains the individual operation handlers for the Billing tools.
Each operation handles the AWS API call and response formatting.
"""

import calendar
from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    handle_aws_error,
    paginate_aws_items,
    parse_json,
    with_pagination,
)
from ..utilities.constants import REGION_US_EAST_1
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import (
    timestamp_to_utc_iso_string,
    utc_datetime_string_to_epoch_seconds,
)
from datetime import datetime, timezone
from fastmcp import Context
from typing import Any, Dict, Optional


# AWS Billing is a global service that operates in us-east-1
BILLING_DEFAULT_REGION = REGION_US_EAST_1


def _create_bvs_client() -> Any:
    """Create a Billing client with the default region.

    Returns:
        boto3.client: AWS Billing client.
    """
    return create_aws_client('billing', region_name=BILLING_DEFAULT_REGION)


async def get_billing_view(
    ctx: Context,
    arn: str,
) -> Dict[str, Any]:
    """Get the metadata associated to the specified billing view ARN.

    Args:
        ctx: The MCP context object.
        arn: The Amazon Resource Name (ARN) that can be used to uniquely identify
            the billing view.

    Returns:
        Dict containing the formatted billing view information.
    """
    try:
        request_params: Dict[str, Any] = {'arn': arn}

        bvs_client = _create_bvs_client()

        await ctx.info(f'Fetching billing view for ARN: {arn}')
        response = bvs_client.get_billing_view(**request_params)

        billing_view = response.get('billingView', {})
        formatted_billing_view = _format_get_billing_view_element(billing_view)

        await ctx.info('Successfully retrieved billing view')

        response_data: Dict[str, Any] = {
            'billing_view': formatted_billing_view,
        }

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'getBillingView', 'Billing')


# ListSourceViewsForBillingView: maxResults 1-100.
BVS_LIST_SOURCE_VIEWS_FOR_BILLING_VIEW = PageSpec(
    result_key='sourceViews',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


async def list_source_views_for_billing_view(
    ctx: Context,
    arn: str,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the source views (managed AWS billing views) associated with the billing view.

    Args:
        ctx: The MCP context object.
        arn: The Amazon Resource Name (ARN) that can be used to uniquely identify
            the billing view.
        max_items: Most source views to return. None fetches every page.
        next_token: Optional pagination token to continue from a previous response.

    Returns:
        Dict containing the list of source view ARNs associated with the billing view and a
        ``pagination`` block.
    """
    try:
        bvs_client = _create_bvs_client()

        source_views, _, pagination = await paginate_aws_items(
            ctx,
            'ListSourceViewsForBillingView',
            bvs_client.list_source_views_for_billing_view,
            {'arn': arn},
            BVS_LIST_SOURCE_VIEWS_FOR_BILLING_VIEW,
            max_items=max_items,
            next_token=next_token,
        )

        return format_response(
            'success', with_pagination({'source_views': source_views}, pagination)
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listSourceViewsForBillingView', 'Billing')


# ListBillingViews: maxResults 1-100.
BVS_LIST_BILLING_VIEWS = PageSpec(
    result_key='billingViews',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)

_SOURCE_ACCOUNT_EMPTY_HINT = (
    'No billing view matched source_account_id together with the other filters. This does '
    'not mean no view includes the account. source_account_id matches only a billing '
    "group's primary account (BILLING_GROUP views) or a billing transfer source account, "
    "never PRIMARY or CUSTOM views; with a time range, only that period's billing groups "
    'count. To find the billing group view that covers an account, get its billing '
    "group's primary account (from the payer account: list-account-associations, then "
    'list-billing-groups) and pass that ID; to see all views, call again without '
    'source_account_id.'
)


def _active_time_range(after: str, before: str) -> Dict[str, int]:
    """Build ListBillingViews' activeTimeRange, checking the rules the service enforces.

    The service rejects a range whose end is not strictly after its start, or whose
    ends fall in different UTC calendar months, with only "Failed to get billing view
    data for an invalid time range.", so name the rule here instead.

    Args:
        after: active_after_inclusive as given by the caller.
        before: active_before_inclusive as given by the caller.

    Returns:
        The activeTimeRange request member, in epoch seconds.

    Raises:
        ValueError: If a date is malformed or the range breaks a rule.
    """
    after_epoch = utc_datetime_string_to_epoch_seconds(after)
    before_epoch = utc_datetime_string_to_epoch_seconds(before)
    start = datetime.fromtimestamp(after_epoch, timezone.utc)
    end = datetime.fromtimestamp(before_epoch, timezone.utc)

    if end <= start:
        raise ValueError(
            f'active_before_inclusive ({before}) must be later than active_after_inclusive '
            f'({after}). A date-only value means 00:00:00 of that day; to cover a whole day, '
            'end with YYYY-MM-DDT23:59:59.'
        )
    if (start.year, start.month) != (end.year, end.month):
        last_day = calendar.monthrange(start.year, start.month)[1]
        raise ValueError(
            f'active_after_inclusive ({after}) and active_before_inclusive ({before}) must '
            'fall in the same UTC calendar month. Make one call per month; for the whole '
            f'month of the start, use {start:%Y-%m}-01T00:00:00 to '
            f'{start:%Y-%m}-{last_day:02d}T23:59:59.'
        )
    return {'activeAfterInclusive': after_epoch, 'activeBeforeInclusive': before_epoch}


async def list_billing_views(
    ctx: Context,
    active_after_inclusive: Optional[str] = None,
    active_before_inclusive: Optional[str] = None,
    arns: Optional[str] = None,
    billing_view_types: Optional[str] = None,
    names: Optional[str] = None,
    owner_account_id: Optional[str] = None,
    source_account_id: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the billing views available for a given time period.

    Every AWS account has a unique PRIMARY billing view that represents the billing
    data available by default. Accounts that use AWS Billing Conductor also have
    BILLING_GROUP billing views representing pro forma costs associated with each
    created billing group.

    Args:
        ctx: The MCP context object.
        active_after_inclusive: Optional UTC datetime string for the inclusive start of the
            active time range. Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be used together with active_before_inclusive. The time range must be
            within one UTC calendar month.
        active_before_inclusive: Optional UTC datetime string for the inclusive end of the
            active time range. Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be used together with active_after_inclusive, later than it and in the
            same UTC calendar month. A date-only value means 00:00:00 of that day;
            use YYYY-MM-DDT23:59:59 to include the whole day.
        arns: Optional JSON string containing a list of billing view ARNs to filter by
            (maximum 10 items).
        billing_view_types: Optional JSON string containing a list of billing view types
            to filter by (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER,
            BILLING_TRANSFER_SHOWBACK).
        names: Optional JSON string containing a list of StringSearch objects with
            searchOption and searchValue fields for filtering by name.
        owner_account_id: Optional owner account ID to filter by (12-digit AWS account ID).
        source_account_id: Optional 12-digit AWS account ID. The service returns only
            BILLING_GROUP views whose billing group's primary account is this ID and
            BILLING_TRANSFER / BILLING_TRANSFER_SHOWBACK views whose source account is this
            ID, never PRIMARY or CUSTOM views. With a time range, only that period's billing
            groups match. A complete empty result carries a ``hint``.
        max_items: Most billing views to return. None fetches every page.
        next_token: Optional pagination token to continue from a previous response.

    Returns:
        Dict containing the formatted billing view list information and a ``pagination`` block.
    """
    try:
        request_params: Dict[str, Any] = {}

        if active_after_inclusive or active_before_inclusive:
            if not active_after_inclusive or not active_before_inclusive:
                raise ValueError(
                    'Both active_after_inclusive and active_before_inclusive must be provided '
                    'together when specifying an active time range.'
                )
            request_params['activeTimeRange'] = _active_time_range(
                active_after_inclusive, active_before_inclusive
            )

        parsed_arns = parse_json(arns, 'arns')
        if parsed_arns:
            request_params['arns'] = parsed_arns

        parsed_billing_view_types = parse_json(billing_view_types, 'billing_view_types')
        if parsed_billing_view_types:
            request_params['billingViewTypes'] = parsed_billing_view_types

        parsed_names = parse_json(names, 'names')
        if parsed_names:
            request_params['names'] = parsed_names

        if owner_account_id:
            request_params['ownerAccountId'] = owner_account_id

        if source_account_id:
            request_params['sourceAccountId'] = source_account_id

        bvs_client = _create_bvs_client()

        billing_views, _, pagination = await paginate_aws_items(
            ctx,
            'ListBillingViews',
            bvs_client.list_billing_views,
            request_params,
            BVS_LIST_BILLING_VIEWS,
            max_items=max_items,
            next_token=next_token,
        )

        response_data: Dict[str, Any] = {
            'billing_views': [_format_list_billing_view_element(bv) for bv in billing_views],
        }
        # A complete empty source_account_id result is easy to misread as "no view
        # includes this account", which the filter cannot answer. A continuation or a
        # partial result says nothing about the whole query, so it gets no hint.
        no_match = (
            source_account_id
            and not billing_views
            and next_token is None
            and pagination['complete_dataset']
        )
        hint = _SOURCE_ACCOUNT_EMPTY_HINT if no_match else None
        return format_response('success', with_pagination(response_data, pagination), hint=hint)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingViews', 'Billing')


async def get_resource_policy(
    ctx: Context,
    resource_arn: str,
) -> Dict[str, Any]:
    """Get the resource-based policy document attached to the specified billing view resource.

    Resource-based policies control what cost management data is accessible to an account
    when using AWS Billing and Cost Management tools. Custom billing views use resource-based
    policies for sharing access with other accounts within and outside an organization via
    AWS Resource Access Manager (AWS RAM).

    Args:
        ctx: The MCP context object.
        resource_arn: The Amazon Resource Name (ARN) of the billing view resource
            to which the policy is attached to.

    Returns:
        Dict containing the resource-based policy document and resource ARN.
    """
    try:
        request_params: Dict[str, Any] = {'resourceArn': resource_arn}

        bvs_client = _create_bvs_client()

        await ctx.info(f'Fetching resource policy for ARN: {resource_arn}')
        response = bvs_client.get_resource_policy(**request_params)

        response_data: Dict[str, Any] = {
            'resource_arn': response.get('resourceArn'),
            'policy': response.get('policy'),
        }

        await ctx.info('Successfully retrieved resource policy')

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'getResourcePolicy', 'Billing')


# ListBillingViewSegments: maxResults 1-100.
BVS_LIST_BILLING_VIEW_SEGMENTS = PageSpec(
    result_key='items',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as ValidationException.
    caller_token_error_codes=frozenset({'ValidationException'}),
)


async def list_billing_view_segments(
    ctx: Context,
    arn: Optional[str] = None,
    begin_date_inclusive: Optional[str] = None,
    end_date_exclusive: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the segments of a billing view over a given time period.

    Each segment identifies the billing domain (PRO_FORMA or BILLABLE) and the account
    relationships that apply during its time range.

    If you don't provide an ARN, the response includes segments for the caller's
    PRIMARY billing view. If a mid-period change occurs, the response includes multiple
    segments, each with its own time range.

    Args:
        ctx: The MCP context object.
        arn: Optional ARN that uniquely identifies the billing view.
            If not provided, the caller's PRIMARY billing view is used.
            Must reference a primary billing view; custom billing views are not supported.
        begin_date_inclusive: Optional UTC datetime string for the inclusive start of the
            billing period. Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be provided together with end_date_exclusive.
            If omitted, the current billing period (calendar month in UTC) is used.
        end_date_exclusive: Optional UTC datetime string for the exclusive end of the
            billing period. Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be provided together with begin_date_inclusive.
            If omitted, the current billing period (calendar month in UTC) is used.
        max_items: Most segments to return. None fetches every page.
        next_token: Optional pagination token to continue from a previous response.

    Returns:
        Dict containing the list of billing view segments and a ``pagination`` block.
    """
    try:
        request_params: Dict[str, Any] = {}

        if arn:
            request_params['arn'] = arn

        if begin_date_inclusive or end_date_exclusive:
            if not begin_date_inclusive or not end_date_exclusive:
                raise ValueError(
                    'Both begin_date_inclusive and end_date_exclusive must be provided '
                    'together when specifying a time range.'
                )
            request_params['timeRange'] = {
                'beginDateInclusive': utc_datetime_string_to_epoch_seconds(begin_date_inclusive),
                'endDateExclusive': utc_datetime_string_to_epoch_seconds(end_date_exclusive),
            }

        bvs_client = _create_bvs_client()

        segments, _, pagination = await paginate_aws_items(
            ctx,
            'ListBillingViewSegments',
            bvs_client.list_billing_view_segments,
            request_params,
            BVS_LIST_BILLING_VIEW_SEGMENTS,
            max_items=max_items,
            next_token=next_token,
        )

        formatted_segments = [_format_billing_view_segment(segment) for segment in segments]

        converted = await convert_response_if_needed(
            ctx,
            with_pagination({'segments': formatted_segments}, pagination),
            'bvs_list_billing_view_segments',
        )
        return format_response('success', converted)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listBillingViewSegments', 'Billing')


def _format_billing_view_segment(segment: Dict[str, Any]) -> Dict[str, Any]:
    """Format a billing view segment element from the ListBillingViewSegments API response.

    Args:
        segment: A BillingViewSegmentsListElement object from the AWS API.

    Returns:
        Dict with formatted billing view segment fields.
    """
    formatted: Dict[str, Any] = {
        'domain': segment.get('domain'),
    }

    if 'managementAccountId' in segment:
        formatted['management_account_id'] = segment['managementAccountId']

    if 'billingGroupPrimaryAccountId' in segment:
        formatted['billing_group_primary_account_id'] = segment['billingGroupPrimaryAccountId']

    if 'billingTransferAccountId' in segment:
        formatted['billing_transfer_account_id'] = segment['billingTransferAccountId']

    if 'timeRange' in segment:
        time_range = segment['timeRange']
        formatted_time_range: Dict[str, Any] = {}
        if 'beginDateInclusive' in time_range:
            formatted_time_range['begin_date_inclusive'] = timestamp_to_utc_iso_string(
                time_range['beginDateInclusive']
            )
        if 'endDateExclusive' in time_range:
            formatted_time_range['end_date_exclusive'] = timestamp_to_utc_iso_string(
                time_range['endDateExclusive']
            )
        formatted['time_range'] = formatted_time_range

    return formatted


def _format_billing_view_common(billing_view: Dict[str, Any]) -> Dict[str, Any]:
    """Format the common fields shared between get and list billing view responses.

    These fields are present in both BillingViewElement (get) and
    BillingViewListElement (list) API responses.

    Args:
        billing_view: A billing view object from the AWS API.

    Returns:
        Dict with formatted common billing view fields.
    """
    formatted: Dict[str, Any] = {
        'arn': billing_view.get('arn'),
        'name': billing_view.get('name'),
        'description': billing_view.get('description'),
        'billing_view_type': billing_view.get('billingViewType'),
        'owner_account_id': billing_view.get('ownerAccountId'),
        'source_account_id': billing_view.get('sourceAccountId'),
    }

    if 'healthStatus' in billing_view:
        formatted['health_status'] = _format_health_status(billing_view['healthStatus'])

    return formatted


def _format_get_billing_view_element(billing_view: Dict[str, Any]) -> Dict[str, Any]:
    """Format a billing view element object from the GetBillingView API response.

    Extends the common billing view fields with additional fields only available
    in the GetBillingView response (BillingViewElement).

    Args:
        billing_view: A billing view element object from the AWS API.

    Returns:
        Dict with formatted billing view element fields.
    """
    formatted = _format_billing_view_common(billing_view)

    formatted['derived_view_count'] = billing_view.get('derivedViewCount')
    formatted['source_view_count'] = billing_view.get('sourceViewCount')

    if 'dataFilterExpression' in billing_view:
        formatted['data_filter_expression'] = _format_expression(
            billing_view['dataFilterExpression']
        )

    if 'createdAt' in billing_view:
        formatted['created_at'] = timestamp_to_utc_iso_string(billing_view['createdAt'])

    if 'updatedAt' in billing_view:
        formatted['updated_at'] = timestamp_to_utc_iso_string(billing_view['updatedAt'])

    if 'viewDefinitionLastUpdatedAt' in billing_view:
        formatted['view_definition_last_updated_at'] = timestamp_to_utc_iso_string(
            billing_view['viewDefinitionLastUpdatedAt']
        )

    return formatted


def _format_list_billing_view_element(billing_view: Dict[str, Any]) -> Dict[str, Any]:
    """Format a billing view list element object from the ListBillingViews API response.

    Uses only the common billing view fields available in the
    BillingViewListElement response.

    Args:
        billing_view: A billing view list element object from the AWS API.

    Returns:
        Dict with formatted billing view list element fields.
    """
    return _format_billing_view_common(billing_view)


def _format_expression(expression: Dict[str, Any]) -> Dict[str, Any]:
    """Format a data filter expression object from the AWS API response.

    Args:
        expression: An expression object from the AWS API.

    Returns:
        Dict with formatted expression fields.
    """
    formatted: Dict[str, Any] = {}

    if 'dimensions' in expression:
        formatted['dimensions'] = _format_dimension_values(expression['dimensions'])

    if 'tags' in expression:
        formatted['tags'] = _format_tag_values(expression['tags'])

    if 'costCategories' in expression:
        formatted['cost_categories'] = _format_cost_category_values(expression['costCategories'])

    if 'timeRange' in expression:
        formatted['time_range'] = _format_time_range(expression['timeRange'])

    return formatted


def _format_dimension_values(dimensions: Dict[str, Any]) -> Dict[str, Any]:
    """Format dimension values from the AWS API response.

    Args:
        dimensions: A dimension values object from the AWS API.

    Returns:
        Dict with formatted dimension values fields.
    """
    return {
        'key': dimensions.get('key'),
        'values': dimensions.get('values', []),
    }


def _format_tag_values(tags: Dict[str, Any]) -> Dict[str, Any]:
    """Format tag values from the AWS API response.

    Args:
        tags: A tag values object from the AWS API.

    Returns:
        Dict with formatted tag values fields.
    """
    return {
        'key': tags.get('key'),
        'values': tags.get('values', []),
    }


def _format_cost_category_values(cost_categories: Dict[str, Any]) -> Dict[str, Any]:
    """Format cost category values from the AWS API response.

    Args:
        cost_categories: A cost category values object from the AWS API.

    Returns:
        Dict with formatted cost category values fields.
    """
    return {
        'key': cost_categories.get('key'),
        'values': cost_categories.get('values', []),
    }


def _format_time_range(time_range: Dict[str, Any]) -> Dict[str, Any]:
    """Format a time range object from the AWS API response.

    Args:
        time_range: A time range object from the AWS API.

    Returns:
        Dict with formatted time range fields.
    """
    formatted: Dict[str, Any] = {}

    if 'beginDateInclusive' in time_range:
        formatted['begin_date_inclusive'] = timestamp_to_utc_iso_string(
            time_range['beginDateInclusive']
        )

    if 'endDateInclusive' in time_range:
        formatted['end_date_inclusive'] = timestamp_to_utc_iso_string(
            time_range['endDateInclusive']
        )

    return formatted


def _format_health_status(health_status: Dict[str, Any]) -> Dict[str, Any]:
    """Format a billing view health status object from the AWS API response.

    Args:
        health_status: A health status object from the AWS API.

    Returns:
        Dict with formatted health status fields.
    """
    formatted: Dict[str, Any] = {
        'status_code': health_status.get('statusCode'),
    }

    if 'statusReasons' in health_status:
        formatted['status_reasons'] = health_status['statusReasons']

    return formatted
