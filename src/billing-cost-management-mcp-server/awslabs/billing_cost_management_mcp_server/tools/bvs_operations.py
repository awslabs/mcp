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

from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from ..utilities.constants import REGION_US_EAST_1
from ..utilities.time_utils import (
    epoch_seconds_to_utc_iso_string,
    utc_datetime_string_to_epoch_seconds,
)
from fastmcp import Context
from typing import Any, Dict, List, Optional


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


async def list_source_views_for_billing_view(
    ctx: Context,
    arn: str,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the source views (managed AWS billing views) associated with the billing view.

    Args:
        ctx: The MCP context object.
        arn: The Amazon Resource Name (ARN) that can be used to uniquely identify
            the billing view.
        max_results: Optional maximum number of entries a paginated response contains.
            Valid range: 1-100.
        max_pages: Maximum number of API pages to fetch. Each page returns up to
            max_results results. Defaults to 10.
        next_token: Optional pagination token to continue from a previous response.

    Returns:
        Dict containing the list of source view ARNs associated with the billing view.
    """
    try:
        request_params: Dict[str, Any] = {'arn': arn}

        if max_results is not None:
            request_params['maxResults'] = max_results

        bvs_client = _create_bvs_client()

        all_source_views: List[str] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['nextToken'] = current_token

            await ctx.info(f'Fetching source views for billing view {arn} (page {page_count})')
            response = bvs_client.list_source_views_for_billing_view(**request_params)

            page_source_views = response.get('sourceViews', [])
            all_source_views.extend(page_source_views)

            await ctx.info(
                f'Retrieved {len(page_source_views)} source views (total: {len(all_source_views)})'
            )

            current_token = response.get('nextToken')
            if not current_token:
                break

        await ctx.info('Successfully listed source views for billing view')

        response_data: Dict[str, Any] = {
            'source_views': all_source_views,
            'total_count': len(all_source_views),
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

    except Exception as e:
        return await handle_aws_error(ctx, e, 'listSourceViewsForBillingView', 'Billing')


async def list_billing_views(
    ctx: Context,
    active_after_inclusive: Optional[str] = None,
    active_before_inclusive: Optional[str] = None,
    arns: Optional[str] = None,
    billing_view_types: Optional[str] = None,
    max_results: Optional[int] = None,
    names: Optional[str] = None,
    owner_account_id: Optional[str] = None,
    source_account_id: Optional[str] = None,
    max_pages: int = 10,
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
            within one calendar month.
        active_before_inclusive: Optional UTC datetime string for the inclusive end of the
            active time range. Format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).
            Must be used together with active_after_inclusive. The time range must be
            within one calendar month.
        arns: Optional JSON string containing a list of billing view ARNs to filter by
            (maximum 10 items).
        billing_view_types: Optional JSON string containing a list of billing view types
            to filter by (PRIMARY, BILLING_GROUP, CUSTOM, BILLING_TRANSFER,
            BILLING_TRANSFER_SHOWBACK).
        max_results: Optional maximum number of billing views to retrieve per page.
            Default is 100. Valid range: 1-100.
        names: Optional JSON string containing a list of StringSearch objects with
            searchOption and searchValue fields for filtering by name.
        owner_account_id: Optional owner account ID to filter by (12-digit AWS account ID).
        source_account_id: Optional source account ID to filter by (12-digit AWS account ID).
        max_pages: Maximum number of API pages to fetch. Each page returns up to
            max_results results. Defaults to 10.
        next_token: Optional pagination token to continue from a previous response.

    Returns:
        Dict containing the formatted billing view list information.
    """
    try:
        request_params: Dict[str, Any] = {}

        if active_after_inclusive or active_before_inclusive:
            if not active_after_inclusive or not active_before_inclusive:
                raise ValueError(
                    'Both active_after_inclusive and active_before_inclusive must be provided '
                    'together when specifying an active time range.'
                )
            request_params['activeTimeRange'] = {
                'activeAfterInclusive': utc_datetime_string_to_epoch_seconds(
                    active_after_inclusive
                ),
                'activeBeforeInclusive': utc_datetime_string_to_epoch_seconds(
                    active_before_inclusive
                ),
            }

        parsed_arns = parse_json(arns, 'arns')
        if parsed_arns:
            request_params['arns'] = parsed_arns

        parsed_billing_view_types = parse_json(billing_view_types, 'billing_view_types')
        if parsed_billing_view_types:
            request_params['billingViewTypes'] = parsed_billing_view_types

        if max_results is not None:
            request_params['maxResults'] = max_results

        parsed_names = parse_json(names, 'names')
        if parsed_names:
            request_params['names'] = parsed_names

        if owner_account_id:
            request_params['ownerAccountId'] = owner_account_id

        if source_account_id:
            request_params['sourceAccountId'] = source_account_id

        bvs_client = _create_bvs_client()

        all_billing_views: List[Dict[str, Any]] = []
        current_token = next_token
        page_count = 0

        while page_count < max_pages:
            page_count += 1
            if current_token:
                request_params['nextToken'] = current_token

            await ctx.info(f'Fetching billing views page {page_count}')
            response = bvs_client.list_billing_views(**request_params)

            page_billing_views = response.get('billingViews', [])
            all_billing_views.extend(page_billing_views)

            await ctx.info(
                f'Retrieved {len(page_billing_views)} billing views '
                f'(total: {len(all_billing_views)})'
            )

            current_token = response.get('nextToken')
            if not current_token:
                break

        formatted_billing_views = [
            _format_list_billing_view_element(bv) for bv in all_billing_views
        ]

        await ctx.info('Successfully listed billing views')

        response_data: Dict[str, Any] = {
            'billing_views': formatted_billing_views,
            'total_count': len(formatted_billing_views),
        }

        if current_token:
            response_data['next_token'] = current_token

        return format_response('success', response_data)

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
        formatted['created_at'] = epoch_seconds_to_utc_iso_string(billing_view['createdAt'])

    if 'updatedAt' in billing_view:
        formatted['updated_at'] = epoch_seconds_to_utc_iso_string(billing_view['updatedAt'])

    if 'viewDefinitionLastUpdatedAt' in billing_view:
        formatted['view_definition_last_updated_at'] = epoch_seconds_to_utc_iso_string(
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
        formatted['begin_date_inclusive'] = epoch_seconds_to_utc_iso_string(
            time_range['beginDateInclusive']
        )

    if 'endDateInclusive' in time_range:
        formatted['end_date_inclusive'] = epoch_seconds_to_utc_iso_string(
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
