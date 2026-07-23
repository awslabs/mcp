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

"""AWS Compute Optimizer Automation operations for the AWS Billing and Cost Management MCP server.

This module contains the individual operation handlers for the Compute Optimizer
Automation tool. Each operation handles the AWS API call and response formatting.
"""

import asyncio
import base64
import binascii
import json
from ..utilities.aws_service_base import (
    create_aws_client,
    format_response,
    handle_aws_error,
    parse_json,
)
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import (
    _SUPPORTED_UTC_DATETIME_FORMATS,
    timestamp_to_utc_iso_string,
)
from datetime import datetime, timezone
from fastmcp import Context
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple


# The AWS regions where Compute Optimizer Automation is available. The service is
# absent from botocore's endpoints.json (it ships only an endpoint rule set), so
# there is no local API to enumerate its regions; this list is maintained by hand.
COMPUTE_OPTIMIZER_AUTOMATION_REGIONS = [
    'ap-northeast-1',
    'ap-northeast-2',
    'ap-northeast-3',
    'ap-south-1',
    'ap-southeast-1',
    'ap-southeast-2',
    'ca-central-1',
    'eu-central-1',
    'eu-north-1',
    'eu-west-1',
    'eu-west-2',
    'eu-west-3',
    'sa-east-1',
    'us-east-1',
    'us-east-2',
    'us-west-1',
    'us-west-2',
]

# Cap on regions queried concurrently during a global fan-out.
_MAX_CONCURRENT_REGIONS = 8
_SERVICE_NAME = 'Compute Optimizer Automation'


# ===== Formatting helpers =====


def _format_timestamp(timestamp: Any) -> Optional[str]:
    """None-guard around the shared timestamp_to_utc_iso_string helper.

    Args:
        timestamp: A datetime (or None) returned by boto3.

    Returns:
        ISO 8601 string, or None if no timestamp was provided.
    """
    if timestamp is None:
        return None
    return timestamp_to_utc_iso_string(timestamp)


def _format_savings(savings: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format an estimatedMonthlySavings object.

    Args:
        savings: The savings object from the AWS API.

    Returns:
        Dict with formatted savings fields, or None if not present.
    """
    if not savings:
        return None

    return {
        'currency': savings.get('currency'),
        'before_discount_savings': savings.get('beforeDiscountSavings'),
        'after_discount_savings': savings.get('afterDiscountSavings'),
        'savings_estimation_mode': savings.get('savingsEstimationMode'),
    }


def _format_tags(tags: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Format a list of tag key-value pairs.

    Args:
        tags: The list of tag objects from the AWS API.

    Returns:
        List of formatted tag dicts.
    """
    return [{'key': tag.get('key'), 'value': tag.get('value')} for tag in (tags or [])]


def _format_resource_details(details: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format a resource details tagged union.

    Args:
        details: The resource details object from the AWS API.

    Returns:
        Dict with formatted resource details, or None if not present.
    """
    if not details:
        return None

    ebs_volume = details.get('ebsVolume')
    if ebs_volume:
        config = ebs_volume.get('configuration', {})
        return {
            'ebs_volume': {
                'configuration': {
                    'type': config.get('type'),
                    'size_in_gib': config.get('sizeInGib'),
                    'iops': config.get('iops'),
                    'throughput': config.get('throughput'),
                }
            }
        }

    # Preserve any unknown union members rather than dropping them.
    return dict(details)


def _format_automation_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Format an automation event object (shared by get/list operations).

    Args:
        event: An automation event object from the AWS API.

    Returns:
        Dict with formatted automation event fields.
    """
    return {
        'event_id': event.get('eventId'),
        'event_description': event.get('eventDescription'),
        'event_type': event.get('eventType'),
        'event_status': event.get('eventStatus'),
        'event_status_reason': event.get('eventStatusReason'),
        'resource_arn': event.get('resourceArn'),
        'resource_id': event.get('resourceId'),
        'recommended_action_id': event.get('recommendedActionId'),
        'account_id': event.get('accountId'),
        'region': event.get('region'),
        'rule_id': event.get('ruleId'),
        'resource_type': event.get('resourceType'),
        'created_timestamp': _format_timestamp(event.get('createdTimestamp')),
        'completed_timestamp': _format_timestamp(event.get('completedTimestamp')),
        'estimated_monthly_savings': _format_savings(event.get('estimatedMonthlySavings')),
    }


def _format_automation_event_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """Format an automation event step object.

    Args:
        step: An automation event step object from the AWS API.

    Returns:
        Dict with formatted step fields.
    """
    return {
        'event_id': step.get('eventId'),
        'step_id': step.get('stepId'),
        'step_type': step.get('stepType'),
        'step_status': step.get('stepStatus'),
        'resource_id': step.get('resourceId'),
        'start_timestamp': _format_timestamp(step.get('startTimestamp')),
        'completed_timestamp': _format_timestamp(step.get('completedTimestamp')),
        'estimated_monthly_savings': _format_savings(step.get('estimatedMonthlySavings')),
    }


def _format_automation_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    """Format an automation rule object (shared by get/list operations).

    The get operation returns additional fields (criteria, tags) that are absent
    from list responses; those are only added when present.

    Args:
        rule: An automation rule object from the AWS API.

    Returns:
        Dict with formatted automation rule fields.
    """
    formatted: Dict[str, Any] = {
        'rule_arn': rule.get('ruleArn'),
        'rule_id': rule.get('ruleId'),
        'name': rule.get('name'),
        'description': rule.get('description'),
        'rule_type': rule.get('ruleType'),
        'rule_revision': rule.get('ruleRevision'),
        'account_id': rule.get('accountId'),
        'organization_configuration': _format_organization_configuration(
            rule.get('organizationConfiguration')
        ),
        'priority': rule.get('priority'),
        'recommended_action_types': rule.get('recommendedActionTypes', []),
        'schedule': _format_schedule(rule.get('schedule')),
        'status': rule.get('status'),
        'created_timestamp': _format_timestamp(rule.get('createdTimestamp')),
        'last_updated_timestamp': _format_timestamp(rule.get('lastUpdatedTimestamp')),
    }

    # Fields only present in the GetAutomationRule response.
    if 'criteria' in rule:
        formatted['criteria'] = rule.get('criteria')
    if 'tags' in rule:
        formatted['tags'] = _format_tags(rule.get('tags'))

    return formatted


def _format_organization_configuration(
    org_config: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Format an organizationConfiguration object.

    Args:
        org_config: The organization configuration object from the AWS API.

    Returns:
        Dict with formatted fields, or None if not present.
    """
    if not org_config:
        return None

    return {
        'rule_apply_order': org_config.get('ruleApplyOrder'),
        'account_ids': org_config.get('accountIds', []),
    }


def _format_schedule(schedule: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Format a schedule object.

    Args:
        schedule: The schedule object from the AWS API.

    Returns:
        Dict with formatted schedule fields, or None if not present.
    """
    if not schedule:
        return None

    return {
        'schedule_expression': schedule.get('scheduleExpression'),
        'schedule_expression_timezone': schedule.get('scheduleExpressionTimezone'),
        'execution_window_in_minutes': schedule.get('executionWindowInMinutes'),
    }


def _format_recommended_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Format a recommended action object (shared by list actions and rule preview).

    Args:
        action: A recommended action object from the AWS API.

    Returns:
        Dict with formatted recommended action fields.
    """
    return {
        'recommended_action_id': action.get('recommendedActionId'),
        'resource_arn': action.get('resourceArn'),
        'resource_id': action.get('resourceId'),
        'account_id': action.get('accountId'),
        'region': action.get('region'),
        'resource_type': action.get('resourceType'),
        'look_back_period_in_days': action.get('lookBackPeriodInDays'),
        'recommended_action_type': action.get('recommendedActionType'),
        'current_resource_summary': action.get('currentResourceSummary'),
        'current_resource_details': _format_resource_details(action.get('currentResourceDetails')),
        'recommended_resource_summary': action.get('recommendedResourceSummary'),
        'recommended_resource_details': _format_resource_details(
            action.get('recommendedResourceDetails')
        ),
        'restart_needed': action.get('restartNeeded'),
        'estimated_monthly_savings': _format_savings(action.get('estimatedMonthlySavings')),
        'resource_tags': _format_tags(action.get('resourceTags')),
    }


def _format_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Format a recommended action / rule preview summary object.

    Args:
        summary: A summary object from the AWS API.

    Returns:
        Dict with formatted summary fields.
    """
    total = summary.get('total', {}) or {}
    return {
        'key': summary.get('key'),
        'total': {
            'recommended_action_count': total.get('recommendedActionCount'),
            'estimated_monthly_savings': _format_savings(total.get('estimatedMonthlySavings')),
        },
    }


# ===== Operation handlers =====


async def get_automation_event(
    ctx: Context,
    client: Any,
    event_id: str,
) -> Dict[str, Any]:
    """Retrieve details about a specific automation event.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        event_id: The ID of the automation event to retrieve.

    Returns:
        Dict containing the formatted automation event.
    """
    await ctx.info(f'Fetching automation event {event_id}')
    response = await asyncio.to_thread(client.get_automation_event, eventId=event_id)

    return format_response('success', {'automation_event': _format_automation_event(response)})


async def get_automation_rule(
    ctx: Context,
    client: Any,
    rule_arn: str,
) -> Dict[str, Any]:
    """Retrieve details about a specific automation rule.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        rule_arn: The ARN of the automation rule to retrieve.

    Returns:
        Dict containing the formatted automation rule.
    """
    await ctx.info(f'Fetching automation rule {rule_arn}')
    response = await asyncio.to_thread(client.get_automation_rule, ruleArn=rule_arn)

    return format_response('success', {'automation_rule': _format_automation_rule(response)})


async def get_enrollment_configuration(
    ctx: Context,
    client: Any,
) -> Dict[str, Any]:
    """Retrieve the current enrollment configuration for Compute Optimizer Automation.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.

    Returns:
        Dict containing the formatted enrollment configuration.
    """
    await ctx.info('Fetching enrollment configuration')
    response = await asyncio.to_thread(client.get_enrollment_configuration)

    enrollment = {
        'status': response.get('status'),
        'status_reason': response.get('statusReason'),
        'organization_rule_mode': response.get('organizationRuleMode'),
        'last_updated_timestamp': _format_timestamp(response.get('lastUpdatedTimestamp')),
    }

    return format_response('success', {'enrollment_configuration': enrollment})


async def list_accounts(
    ctx: Context,
    client: Any,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the accounts in the organization enrolled in Compute Optimizer.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of accounts.
    """
    request_params: Dict[str, Any] = {}
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_accounts: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching accounts page {page_count}')
        response = await asyncio.to_thread(client.list_accounts, **request_params)

        for account in response.get('accounts', []):
            all_accounts.append(
                {
                    'account_id': account.get('accountId'),
                    'status': account.get('status'),
                    'organization_rule_mode': account.get('organizationRuleMode'),
                    'status_reason': account.get('statusReason'),
                    'last_updated_timestamp': _format_timestamp(
                        account.get('lastUpdatedTimestamp')
                    ),
                }
            )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return await _finalize_list_response(
        ctx, 'list_accounts', 'accounts', all_accounts, current_token
    )


async def list_automation_events(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List automation events matching the specified filters.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        filters: Optional JSON string list of {name, values} filter objects.
            Valid filter names: AccountId, ResourceType, EventType, EventStatus.
        start_time: Optional inclusive start of the time range (YYYY-MM-DD or
            YYYY-MM-DDTHH:MM:SS, interpreted as UTC).
        end_time: Optional exclusive end of the time range (same format).
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation events.
    """
    all_events, current_token = await _collect_automation_events(
        ctx, client, filters, start_time, end_time, max_results, max_pages, next_token
    )

    return await _finalize_list_response(
        ctx, 'list_automation_events', 'automation_events', all_events, current_token
    )


async def list_automation_event_steps(
    ctx: Context,
    client: Any,
    event_id: str,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the steps for a specific automation event.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        event_id: The ID of the automation event.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation event steps.
    """
    all_steps, current_token = await _collect_automation_event_steps(
        ctx, client, event_id, max_results, max_pages, next_token
    )

    return await _finalize_list_response(
        ctx, 'list_automation_event_steps', 'automation_event_steps', all_steps, current_token
    )


async def list_automation_event_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Provide a summary of automation events matching the specified filters.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        filters: Optional JSON string list of {name, values} filter objects.
            Valid filter names: AccountId, ResourceType, EventType, EventStatus.
        start_date: Optional inclusive start date string for filtering.
        end_date: Optional exclusive end date string for filtering.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation event summaries.
    """
    all_summaries, current_token = await _collect_automation_event_summaries(
        ctx, client, filters, start_date, end_date, max_results, max_pages, next_token
    )

    return await _finalize_list_response(
        ctx,
        'list_automation_event_summaries',
        'automation_event_summaries',
        all_summaries,
        current_token,
    )


def _format_event_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Format an automation event summary object.

    Args:
        summary: An automation event summary object from the AWS API.

    Returns:
        Dict with formatted summary fields.
    """
    time_period = summary.get('timePeriod', {}) or {}
    total = summary.get('total', {}) or {}
    return {
        'key': summary.get('key'),
        'dimensions': [
            {'key': dim.get('key'), 'value': dim.get('value')}
            for dim in summary.get('dimensions', [])
        ],
        'time_period': {
            'start_time_inclusive': _format_timestamp(time_period.get('startTimeInclusive')),
            'end_time_exclusive': _format_timestamp(time_period.get('endTimeExclusive')),
        },
        'total': {
            'automation_event_count': total.get('automationEventCount'),
            'estimated_monthly_savings': _format_savings(total.get('estimatedMonthlySavings')),
        },
    }


async def list_automation_rules(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the automation rules matching the specified filters.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        filters: Optional JSON string list of {name, values} filter objects.
            Valid filter names: Name, RecommendedActionType, Status, RuleType,
            OrganizationConfigurationRuleApplyOrder, AccountId.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation rules.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_rules: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching automation rules page {page_count}')
        response = await asyncio.to_thread(client.list_automation_rules, **request_params)

        all_rules.extend(
            _format_automation_rule(rule) for rule in response.get('automationRules', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return await _finalize_list_response(
        ctx, 'list_automation_rules', 'automation_rules', all_rules, current_token
    )


async def list_recommended_actions(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the recommended actions matching the specified filters.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        filters: Optional JSON string list of {name, values} filter objects.
            Valid filter names: ResourceType, RecommendedActionType, ResourceId,
            LookBackPeriodInDays, CurrentResourceDetailsEbsVolumeType, ResourceTagsKey,
            ResourceTagsValue, AccountId, RestartNeeded.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of recommended actions.
    """
    all_actions, current_token = await _collect_recommended_actions(
        ctx, client, filters, max_results, max_pages, next_token
    )

    return await _finalize_list_response(
        ctx, 'list_recommended_actions', 'recommended_actions', all_actions, current_token
    )


async def list_recommended_action_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Provide a summary of recommended actions matching the specified filters.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        filters: Optional JSON string list of {name, values} filter objects.
            Same valid filter names as list_recommended_actions.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of recommended action summaries.
    """
    all_summaries, current_token = await _collect_recommended_action_summaries(
        ctx, client, filters, max_results, max_pages, next_token
    )

    return await _finalize_list_response(
        ctx,
        'list_recommended_action_summaries',
        'recommended_action_summaries',
        all_summaries,
        current_token,
    )


async def list_automation_rule_preview(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Preview the recommended actions matching an automation rule configuration.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        rule_type: The type of rule ('OrganizationRule' or 'AccountRule'). Required.
        recommended_action_types: JSON string array of recommended action types to
            include. Required.
        organization_scope: Optional JSON string with an accountIds list.
        criteria: Optional JSON string of the rule criteria conditions.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the rule preview results.
    """
    all_results, current_token = await _collect_automation_rule_preview(
        ctx,
        client,
        rule_type,
        recommended_action_types,
        organization_scope,
        criteria,
        max_results,
        max_pages,
        next_token,
    )

    return await _finalize_list_response(
        ctx, 'list_automation_rule_preview', 'preview_results', all_results, current_token
    )


async def list_automation_rule_preview_summaries(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Summarize the recommended actions matching a rule preview configuration.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        rule_type: The type of rule ('OrganizationRule' or 'AccountRule'). Required.
        recommended_action_types: JSON string array of recommended action types to
            include. Required.
        organization_scope: Optional JSON string with an accountIds list.
        criteria: Optional JSON string of the rule criteria conditions.
        max_results: Optional maximum number of results per page.
        max_pages: Maximum number of API pages to fetch. Defaults to 10.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the rule preview result summaries.
    """
    all_summaries, current_token = await _collect_automation_rule_preview_summaries(
        ctx,
        client,
        rule_type,
        recommended_action_types,
        organization_scope,
        criteria,
        max_results,
        max_pages,
        next_token,
    )

    return await _finalize_list_response(
        ctx,
        'list_automation_rule_preview_summaries',
        'preview_result_summaries',
        all_summaries,
        current_token,
    )


async def list_tags_for_resource(
    ctx: Context,
    client: Any,
    resource_arn: str,
) -> Dict[str, Any]:
    """List the tags for a specified resource.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        resource_arn: The ARN of the resource to list tags for.

    Returns:
        Dict containing the list of tags.
    """
    await ctx.info(f'Fetching tags for resource {resource_arn}')
    response = await asyncio.to_thread(client.list_tags_for_resource, resourceArn=resource_arn)

    return format_response('success', {'tags': _format_tags(response.get('tags'))})


# ===== Multi-region collection helpers =====


async def _collect_automation_events(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Paginate automation events, returning the items and any leftover token.

    See list_automation_events for argument semantics.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters
    if start_time:
        request_params['startTimeInclusive'] = _parse_datetime(start_time, 'start_time')
    if end_time:
        request_params['endTimeExclusive'] = _parse_datetime(end_time, 'end_time')
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_events: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching automation events page {page_count}')
        response = await asyncio.to_thread(client.list_automation_events, **request_params)

        all_events.extend(
            _format_automation_event(event) for event in response.get('automationEvents', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return all_events, current_token


async def _collect_automation_event_steps(
    ctx: Context,
    client: Any,
    event_id: str,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Paginate automation event steps, returning the items and any leftover token.

    See list_automation_event_steps for argument semantics.
    """
    request_params: Dict[str, Any] = {'eventId': event_id}
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_steps: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching automation event steps page {page_count} for event {event_id}')
        response = await asyncio.to_thread(client.list_automation_event_steps, **request_params)

        all_steps.extend(
            _format_automation_event_step(step)
            for step in response.get('automationEventSteps', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return all_steps, current_token


async def _collect_automation_event_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Paginate automation event summaries, returning items and any leftover token.

    See list_automation_event_summaries for argument semantics.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters
    if start_date:
        request_params['startDateInclusive'] = start_date
    if end_date:
        request_params['endDateExclusive'] = end_date
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_summaries: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching automation event summaries page {page_count}')
        response = await asyncio.to_thread(
            client.list_automation_event_summaries, **request_params
        )

        all_summaries.extend(
            _format_event_summary(summary)
            for summary in response.get('automationEventSummaries', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return all_summaries, current_token


async def _collect_recommended_actions(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Paginate recommended actions, returning the items and any leftover token.

    See list_recommended_actions for argument semantics.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_actions: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching recommended actions page {page_count}')
        response = await asyncio.to_thread(client.list_recommended_actions, **request_params)

        all_actions.extend(
            _format_recommended_action(action) for action in response.get('recommendedActions', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return all_actions, current_token


async def _collect_recommended_action_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Paginate recommended action summaries, returning items and any leftover token.

    See list_recommended_action_summaries for argument semantics.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_summaries: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching recommended action summaries page {page_count}')
        response = await asyncio.to_thread(
            client.list_recommended_action_summaries, **request_params
        )

        all_summaries.extend(
            _format_summary(summary) for summary in response.get('recommendedActionSummaries', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return all_summaries, current_token


async def _collect_automation_rule_preview(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Paginate automation rule preview results, returning items and any leftover token.

    See list_automation_rule_preview for argument semantics.
    """
    request_params: Dict[str, Any] = {
        'ruleType': rule_type,
        'recommendedActionTypes': parse_json(recommended_action_types, 'recommended_action_types'),
    }

    parsed_scope = parse_json(organization_scope, 'organization_scope')
    if parsed_scope:
        request_params['organizationScope'] = parsed_scope
    parsed_criteria = parse_json(criteria, 'criteria')
    if parsed_criteria:
        request_params['criteria'] = parsed_criteria
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_results: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching automation rule preview page {page_count}')
        response = await asyncio.to_thread(client.list_automation_rule_preview, **request_params)

        all_results.extend(
            _format_recommended_action(result) for result in response.get('previewResults', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return all_results, current_token


async def _collect_automation_rule_preview_summaries(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Paginate rule preview summaries, returning the items and any leftover token.

    See list_automation_rule_preview_summaries for argument semantics.
    """
    request_params: Dict[str, Any] = {
        'ruleType': rule_type,
        'recommendedActionTypes': parse_json(recommended_action_types, 'recommended_action_types'),
    }

    parsed_scope = parse_json(organization_scope, 'organization_scope')
    if parsed_scope:
        request_params['organizationScope'] = parsed_scope
    parsed_criteria = parse_json(criteria, 'criteria')
    if parsed_criteria:
        request_params['criteria'] = parsed_criteria
    if max_results is not None:
        request_params['maxResults'] = max_results

    all_summaries: List[Dict[str, Any]] = []
    current_token = next_token
    page_count = 0

    while page_count < max_pages:
        page_count += 1
        if current_token:
            request_params['nextToken'] = current_token

        await ctx.info(f'Fetching automation rule preview summaries page {page_count}')
        response = await asyncio.to_thread(
            client.list_automation_rule_preview_summaries, **request_params
        )

        all_summaries.extend(
            _format_summary(summary) for summary in response.get('previewResultSummaries', [])
        )

        current_token = response.get('nextToken')
        if not current_token:
            break

    return all_summaries, current_token


# ===== Multi-region fan-out =====


def _encode_global_next_token(region_next_tokens: Dict[str, str]) -> str:
    """Encode per-region pagination state as one opaque tool token."""
    payload = json.dumps(region_next_tokens, separators=(',', ':'), sort_keys=True)
    return base64.b64encode(payload.encode('utf-8')).decode('ascii')


def _parse_global_next_token(
    next_token: Optional[str],
) -> Tuple[Dict[str, Optional[str]], Optional[Dict[str, Any]]]:
    """Resolve a global token into the regions and AWS tokens to resume.

    Global pagination state is an opaque base64-encoded JSON object. Callers must
    return the token unchanged; the regional map is an implementation detail.
    """
    if not next_token:
        return dict.fromkeys(COMPUTE_OPTIMIZER_AUTOMATION_REGIONS), None

    try:
        decoded = base64.b64decode(next_token.encode('ascii'), validate=True).decode('utf-8')
        parsed = json.loads(decoded)
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as e:
        return {}, format_response(
            'error',
            {
                'parameter': 'next_token',
                'supported_regions': COMPUTE_OPTIMIZER_AUTOMATION_REGIONS,
            },
            'Invalid global next_token. If this token came from a global response, pass '
            'it back unchanged. If it came from an explicit-region query, pass `region` '
            f'along with it. Decode error: {e}',
        )

    if not isinstance(parsed, dict):
        return {}, format_response(
            'error',
            {'parameter': 'next_token'},
            'Invalid global next_token: decoded pagination state must be a non-empty '
            'region-to-token map. Pass the previous global response next_token unchanged.',
        )
    if not parsed:
        return {}, format_response(
            'error',
            {'parameter': 'next_token'},
            'Invalid global next_token: the regional pagination map is empty. Start a new '
            'global query by omitting next_token.',
        )

    invalid_tokens = sorted(
        region
        for region, token in parsed.items()
        if not isinstance(region, str) or not isinstance(token, str) or not token.strip()
    )
    if invalid_tokens:
        return {}, format_response(
            'error',
            {'parameter': 'next_token', 'invalid_regions': invalid_tokens},
            'Invalid global next_token: every regional token must be a non-empty string. '
            'Pass the previous global response next_token unchanged.',
        )

    unknown_regions = sorted(set(parsed) - set(COMPUTE_OPTIMIZER_AUTOMATION_REGIONS))
    if unknown_regions:
        return {}, format_response(
            'error',
            {
                'parameter': 'next_token',
                'unsupported_regions': unknown_regions,
                'supported_regions': COMPUTE_OPTIMIZER_AUTOMATION_REGIONS,
            },
            'Invalid global next_token: it contains unsupported region key(s): '
            f'{", ".join(unknown_regions)}. Pass the previous global response next_token '
            'unchanged.',
        )

    return dict(parsed), None


def _is_resource_not_found(error: Exception) -> bool:
    """Return True if the error is a Compute Optimizer Automation not-found error.

    Recognizes both a real botocore ClientError (via its error code) and a bare
    exception class named ResourceNotFoundException.
    """
    response = getattr(error, 'response', None)
    if isinstance(response, dict):
        if response.get('Error', {}).get('Code') == 'ResourceNotFoundException':
            return True
    return type(error).__name__ == 'ResourceNotFoundException'


async def _format_region_error(
    ctx: Context, error: Exception, operation: str
) -> Dict[str, Any]:
    """Classify a regional failure using the shared AWS error handler."""
    classified = await handle_aws_error(ctx, error, operation, _SERVICE_NAME)
    useful_fields = (
        'error_type',
        'message',
        'request_id',
        'http_status',
        'boto_error_type',
        'exception_type',
        'details',
    )
    return {field: classified[field] for field in useful_fields if field in classified}


async def run_global_list(
    ctx: Context,
    operation: str,
    list_key: str,
    regions_tokens: Dict[str, Optional[str]],
    collect: Callable[[Any, Optional[str]], Awaitable[Tuple[List[Dict[str, Any]], Optional[str]]]],
    not_found_is_empty: bool = False,
) -> Dict[str, Any]:
    """Fan a list operation out across regions concurrently and merge the results.

    Args:
        ctx: The MCP context object.
        operation: The tool operation name, used to prefix the SQL table.
        list_key: The response key holding the merged list of items.
        regions_tokens: Map of region -> start token (None to start from the first
            page). Only these regions are queried; pass every Automation region for a
            fresh global call, or a subset to resume specific regions.
        collect: Coroutine (client, start_token) -> (items, leftover_token) that
            paginates one region. Built by the dispatcher to close over the
            operation's parameters.
        not_found_is_empty: When True, a ResourceNotFoundException from a region is
            treated as an empty result rather than a per-region error (used by
            list_automation_event_steps, whose event lives in a single region).

    Returns:
        A format_response dict with the merged items (or the SQL offload sentinel),
        the regions queried, an opaque leftover token, and any typed per-region errors.
        If no region could be searched, an error response with the per-region outcomes.
    """
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REGIONS)

    async def query_region(
        region: str, token: Optional[str]
    ) -> Tuple[
        str,
        List[Dict[str, Any]],
        Optional[str],
        Optional[Dict[str, Any]],
        bool,
    ]:
        async with semaphore:
            try:
                client = await asyncio.to_thread(
                    create_compute_optimizer_automation_client, region
                )
                items, leftover = await collect(client, token)
                return region, items, leftover, None, False
            except Exception as e:
                if not_found_is_empty and _is_resource_not_found(e):
                    return region, [], None, None, True
                error = await _format_region_error(ctx, e, operation)
                return region, [], None, error, False

    results = await asyncio.gather(
        *(query_region(region, token) for region, token in regions_tokens.items())
    )

    merged: List[Dict[str, Any]] = []
    region_next_tokens: Dict[str, str] = {}
    region_errors: Dict[str, Dict[str, Any]] = {}
    regions_not_found: List[str] = []
    successful_regions = 0
    for region, items, leftover, error, not_found in results:
        if not_found:
            regions_not_found.append(region)
            continue
        if error is not None:
            region_errors[region] = error
            continue
        successful_regions += 1
        for item in items:
            # Events and recommended actions already carry the resource's region;
            # summaries and steps do not, so stamp the queried region on them.
            if not item.get('region'):
                item['region'] = region
            merged.append(item)
        if leftover:
            region_next_tokens[region] = leftover

    if not_found_is_empty and regions_not_found and not region_errors and not successful_regions:
        return format_response(
            'error',
            {
                'operation': operation,
                'regions_queried': list(regions_tokens),
                'regions_not_found': regions_not_found,
            },
            f'The requested resource was not found in any of the {len(regions_not_found)} '
            f'region(s) queried for {operation}.',
        )

    if region_errors and not successful_regions:
        data: Dict[str, Any] = {
            'operation': operation,
            'regions_queried': list(regions_tokens),
            'region_errors': region_errors,
        }
        if regions_not_found:
            data['regions_not_found'] = regions_not_found
        if regions_not_found:
            message = (
                f'Could not determine whether the requested resource exists for {operation}: '
                f'{len(region_errors)} region(s) failed and {len(regions_not_found)} returned '
                'not found.'
            )
        else:
            message = f'All {len(region_errors)} region(s) failed for {operation}.'
        return format_response(
            'error',
            data,
            message,
        )

    return await _finalize_global_list_response(
        ctx,
        operation,
        list_key,
        merged,
        list(regions_tokens),
        region_next_tokens,
        region_errors,
    )


async def _finalize_global_list_response(
    ctx: Context,
    operation: str,
    list_key: str,
    items: List[Dict[str, Any]],
    regions_queried: List[str],
    region_next_tokens: Dict[str, str],
    region_errors: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a merged multi-region list response, offloading to SQL when large.

    Mirrors _finalize_list_response for the global fan-out. The item list is stored
    first so the SQL records converter extracts it (regions_queried is also a list),
    and the opaque token and typed error map are passed as metadata so they survive
    an offload.

    Args:
        ctx: The MCP context object.
        operation: The tool operation name, used to prefix the SQL table.
        list_key: The response key holding the merged list of items.
        items: The merged, region-annotated items.
        regions_queried: The regions that were queried.
        region_next_tokens: Map of region -> leftover token for regions with more data.
        region_errors: Map of region -> structured error for regions that failed.

    Returns:
        A format_response dict — either the inline merged list or the SQL offload sentinel.
    """
    response_data: Dict[str, Any] = {list_key: items, 'count': len(items)}
    response_data['regions_queried'] = regions_queried
    global_next_token = None
    if region_next_tokens:
        global_next_token = _encode_global_next_token(region_next_tokens)
        response_data['next_token'] = global_next_token
    if region_errors:
        response_data['region_errors'] = region_errors

    offload_metadata: Dict[str, Any] = {'regions_queried': regions_queried}
    if global_next_token:
        # Keep the public key stable even when the generic SQL converter also
        # derives its next_page_token pagination envelope.
        offload_metadata['next_token'] = global_next_token
    if region_errors:
        offload_metadata['region_errors'] = region_errors

    response_data = await convert_response_if_needed(
        ctx,
        response_data,
        f'compute_optimizer_automation_{operation}',
        pagination_token_key='next_token',
        **offload_metadata,
    )

    return format_response('success', response_data)


async def get_automation_event_global(ctx: Context, event_id: str) -> Dict[str, Any]:
    """Locate an automation event by ID across all Automation regions.

    Event IDs carry no region, so this fans out get_automation_event concurrently.
    A ResourceNotFoundException in a region is a miss; other errors are recorded
    per region.

    Args:
        ctx: The MCP context object.
        event_id: The ID of the automation event to retrieve.

    Returns:
        The event and the region it was found in, or an error response listing the
        regions searched (and any per-region errors) when no region has it.
    """
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REGIONS)

    async def lookup(
        region: str,
    ) -> Tuple[
        str,
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
        bool,
    ]:
        async with semaphore:
            try:
                client = await asyncio.to_thread(
                    create_compute_optimizer_automation_client, region
                )
                response = await asyncio.to_thread(client.get_automation_event, eventId=event_id)
                return region, response, None, False
            except Exception as e:
                if _is_resource_not_found(e):
                    return region, None, None, True
                error = await _format_region_error(ctx, e, 'get_automation_event')
                return region, None, error, False

    await ctx.info(f'Searching all Automation regions for automation event {event_id}')
    results = await asyncio.gather(
        *(lookup(region) for region in COMPUTE_OPTIMIZER_AUTOMATION_REGIONS)
    )

    region_errors: Dict[str, Dict[str, Any]] = {}
    regions_not_found: List[str] = []
    for region, response, error, not_found in results:
        if not_found:
            regions_not_found.append(region)
            continue
        if error is not None:
            region_errors[region] = error
        elif response is not None:
            data = {
                'automation_event': _format_automation_event(response),
                'found_in_region': region,
            }
            return format_response('success', data)

    data: Dict[str, Any] = {
        'event_id': event_id,
        'regions_queried': list(COMPUTE_OPTIMIZER_AUTOMATION_REGIONS),
    }
    if region_errors:
        data['region_errors'] = region_errors
        data['regions_not_found'] = regions_not_found
        return format_response(
            'error',
            data,
            f'Could not determine whether automation event {event_id} exists because '
            f'{len(region_errors)} of {len(COMPUTE_OPTIMIZER_AUTOMATION_REGIONS)} region(s) '
            'could not be searched. Review region_errors and retry.',
        )
    return format_response(
        'error', data, f'Automation event {event_id} was not found in any region.'
    )


# ===== Shared helpers =====


async def _finalize_list_response(
    ctx: Context,
    operation: str,
    list_key: str,
    items: List[Dict[str, Any]],
    next_token: Optional[str],
) -> Dict[str, Any]:
    """Build a list response, offloading to SQL when it exceeds the size threshold.

    Every list operation routes through the size gate. The gate only offloads
    responses above the threshold (default 25KB) to a session SQLite table so the
    agent's context window isn't overloaded — smaller responses pass through
    inline unchanged. Gating uniformly (rather than by predicted size) keeps the
    behavior consistent and covers the less obvious large cases: free-form event
    descriptions, up to 1000 accounts, and tag-heavy recommended actions.

    Args:
        ctx: The MCP context object.
        operation: The tool operation name, used to prefix the SQL table.
        list_key: The response key holding the list of items (e.g. 'automation_rules').
        items: The formatted items to return.
        next_token: Pagination token to surface when more results remain.

    Returns:
        A format_response dict — either the inline list or the SQL offload sentinel.
    """
    response_data: Dict[str, Any] = {list_key: items, 'count': len(items)}
    if next_token:
        response_data['next_token'] = next_token

    response_data = await convert_response_if_needed(
        ctx,
        response_data,
        f'compute_optimizer_automation_{operation}',
        pagination_token_key='next_token',
    )

    return format_response('success', response_data)


def _parse_datetime(value: str, parameter_name: str) -> Any:
    """Parse a UTC datetime string into a timezone-aware datetime for boto3.

    Args:
        value: A datetime string in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format (UTC).
        parameter_name: Name of the parameter, used in error messages.

    Returns:
        A timezone-aware datetime object.

    Raises:
        ValueError: If the datetime string format is invalid.
    """
    for fmt in _SUPPORTED_UTC_DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(
        f"Invalid datetime format for {parameter_name}: '{value}'. "
        'Expected YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS (UTC).'
    )


def create_compute_optimizer_automation_client(region: Optional[str] = None) -> Any:
    """Create a Compute Optimizer Automation boto3 client.

    Args:
        region: Optional AWS region. Defaults to the AWS_REGION env var or us-east-1.

    Returns:
        boto3.client: The Compute Optimizer Automation client.
    """
    return create_aws_client('compute-optimizer-automation', region_name=region)


# Re-export for tools module to catch broad errors uniformly.
__all__ = [
    'COMPUTE_OPTIMIZER_AUTOMATION_REGIONS',
    '_encode_global_next_token',
    '_parse_global_next_token',
    'create_compute_optimizer_automation_client',
    'get_automation_event',
    'get_automation_event_global',
    'get_automation_rule',
    'get_enrollment_configuration',
    'list_accounts',
    'list_automation_events',
    'list_automation_event_steps',
    'list_automation_event_summaries',
    'list_automation_rules',
    'list_recommended_actions',
    'list_recommended_action_summaries',
    'list_automation_rule_preview',
    'list_automation_rule_preview_summaries',
    'list_tags_for_resource',
    'run_global_list',
    '_collect_automation_events',
    '_collect_automation_event_steps',
    '_collect_automation_event_summaries',
    '_collect_recommended_actions',
    '_collect_recommended_action_summaries',
    '_collect_automation_rule_preview',
    '_collect_automation_rule_preview_summaries',
    'handle_aws_error',
]
