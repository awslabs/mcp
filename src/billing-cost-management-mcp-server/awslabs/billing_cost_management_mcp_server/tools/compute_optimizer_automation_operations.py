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
from ..utilities.aws_service_base import (
    PageSpec,
    create_aws_client,
    format_response,
    paginate_aws_items,
    parse_json,
    with_pagination,
)
from ..utilities.sql_utils import convert_response_if_needed
from ..utilities.time_utils import (
    _SUPPORTED_UTC_DATETIME_FORMATS,
    timestamp_to_utc_iso_string,
)
from datetime import datetime, timezone
from fastmcp import Context
from typing import Any, Callable, Dict, List, Optional, Tuple


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

    rule = _format_automation_rule(response)
    # A rule with no conditions may omit criteria; report it as empty rather than unread.
    rule['criteria'] = rule.get('criteria') or {}
    return format_response('success', {'automation_rule': rule})


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


# ===== Page specs =====
# Each list API pages with `nextToken` and accepts `maxResults` up to the limit in its
# service model (1000 for ListAccounts, 100 for everything else).

COA_LIST_ACCOUNTS = PageSpec(
    result_key='accounts',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=1000,
    page_size_param='maxResults',
)
COA_LIST_AUTOMATION_EVENTS = PageSpec(
    result_key='automationEvents',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)
COA_LIST_AUTOMATION_EVENT_STEPS = PageSpec(
    result_key='automationEventSteps',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)
COA_LIST_AUTOMATION_EVENT_SUMMARIES = PageSpec(
    result_key='automationEventSummaries',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)
COA_LIST_AUTOMATION_RULES = PageSpec(
    result_key='automationRules',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)
COA_LIST_RECOMMENDED_ACTIONS = PageSpec(
    result_key='recommendedActions',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)
COA_LIST_RECOMMENDED_ACTION_SUMMARIES = PageSpec(
    result_key='recommendedActionSummaries',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)
COA_LIST_AUTOMATION_RULE_PREVIEW = PageSpec(
    result_key='previewResults',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)
COA_LIST_AUTOMATION_RULE_PREVIEW_SUMMARIES = PageSpec(
    result_key='previewResultSummaries',
    token_param='nextToken',
    token_key_in_response='nextToken',
    page_max=100,
    page_size_param='maxResults',
    # The service reports a bad caller next_token as InvalidParameterValueException.
    caller_token_error_codes=frozenset({'InvalidParameterValueException'}),
)


def _format_account(account: Dict[str, Any]) -> Dict[str, Any]:
    """Format an enrolled-account object.

    Args:
        account: An account object from the AWS API.

    Returns:
        Dict with formatted account fields.
    """
    return {
        'account_id': account.get('accountId'),
        'status': account.get('status'),
        'organization_rule_mode': account.get('organizationRuleMode'),
        'status_reason': account.get('statusReason'),
        'last_updated_timestamp': _format_timestamp(account.get('lastUpdatedTimestamp')),
    }


async def list_accounts(
    ctx: Context,
    client: Any,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the accounts in the organization enrolled in Compute Optimizer.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of accounts.
    """
    accounts, pagination = await _paginate(
        ctx,
        'ListAccounts',
        client.list_accounts,
        {},
        COA_LIST_ACCOUNTS,
        _format_account,
        max_items,
        next_token,
    )

    return await _finalize_list_response(ctx, 'list_accounts', 'accounts', accounts, pagination)


async def list_automation_events(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_items: Optional[int] = None,
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
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation events.
    """
    all_events, pagination = await _collect_automation_events(
        ctx, client, filters, start_time, end_time, max_items, next_token
    )

    return await _finalize_list_response(
        ctx, 'list_automation_events', 'automation_events', all_events, pagination
    )


async def list_automation_event_steps(
    ctx: Context,
    client: Any,
    event_id: str,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the steps for a specific automation event.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        event_id: The ID of the automation event.
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation event steps.
    """
    all_steps, pagination = await _collect_automation_event_steps(
        ctx, client, event_id, max_items, next_token
    )

    return await _finalize_list_response(
        ctx, 'list_automation_event_steps', 'automation_event_steps', all_steps, pagination
    )


async def list_automation_event_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_items: Optional[int] = None,
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
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation event summaries.
    """
    all_summaries, pagination = await _collect_automation_event_summaries(
        ctx, client, filters, start_date, end_date, max_items, next_token
    )

    return await _finalize_list_response(
        ctx,
        'list_automation_event_summaries',
        'automation_event_summaries',
        all_summaries,
        pagination,
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
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List the automation rules matching the specified filters.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        filters: Optional JSON string list of {name, values} filter objects.
            Valid filter names: Name, RecommendedActionType, Status, RuleType,
            OrganizationConfigurationRuleApplyOrder, AccountId.
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of automation rules.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters

    all_rules, pagination = await _paginate(
        ctx,
        'ListAutomationRules',
        client.list_automation_rules,
        request_params,
        COA_LIST_AUTOMATION_RULES,
        _format_automation_rule,
        max_items,
        next_token,
    )

    return await _finalize_list_response(
        ctx, 'list_automation_rules', 'automation_rules', all_rules, pagination
    )


async def list_recommended_actions(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
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
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of recommended actions.
    """
    all_actions, pagination = await _collect_recommended_actions(
        ctx, client, filters, max_items, next_token
    )

    return await _finalize_list_response(
        ctx, 'list_recommended_actions', 'recommended_actions', all_actions, pagination
    )


async def list_recommended_action_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Provide a summary of recommended actions matching the specified filters.

    Args:
        ctx: The MCP context object.
        client: The Compute Optimizer Automation boto3 client.
        filters: Optional JSON string list of {name, values} filter objects.
            Same valid filter names as list_recommended_actions.
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the list of recommended action summaries.
    """
    all_summaries, pagination = await _collect_recommended_action_summaries(
        ctx, client, filters, max_items, next_token
    )

    return await _finalize_list_response(
        ctx,
        'list_recommended_action_summaries',
        'recommended_action_summaries',
        all_summaries,
        pagination,
    )


async def list_automation_rule_preview(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_items: Optional[int] = None,
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
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the rule preview results.
    """
    all_results, pagination = await _collect_automation_rule_preview(
        ctx,
        client,
        rule_type,
        recommended_action_types,
        organization_scope,
        criteria,
        max_items,
        next_token,
    )

    return await _finalize_list_response(
        ctx, 'list_automation_rule_preview', 'preview_results', all_results, pagination
    )


async def list_automation_rule_preview_summaries(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_items: Optional[int] = None,
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
        max_items: Total number of items to return. None fetches every page.
        next_token: Optional pagination token from a previous response.

    Returns:
        Dict containing the rule preview result summaries.
    """
    all_summaries, pagination = await _collect_automation_rule_preview_summaries(
        ctx,
        client,
        rule_type,
        recommended_action_types,
        organization_scope,
        criteria,
        max_items,
        next_token,
    )

    return await _finalize_list_response(
        ctx,
        'list_automation_rule_preview_summaries',
        'preview_result_summaries',
        all_summaries,
        pagination,
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


# ===== Pagination helpers (shared by single- and multi-region calls) =====


async def _paginate(
    ctx: Context,
    operation: str,
    api_call: Callable[..., Dict[str, Any]],
    request_params: Dict[str, Any],
    spec: PageSpec,
    formatter: Callable[[Dict[str, Any]], Dict[str, Any]],
    max_items: Optional[int],
    next_token: Optional[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch pages of a regional list API through the shared helper and format the items.

    The boto3 client is synchronous, so each page runs in a worker thread.

    Returns:
        The formatted items and the pagination block from ``paginate_aws_items``.
    """

    def call_in_thread(**params: Any) -> Any:
        return asyncio.to_thread(api_call, **params)

    items, _, pagination = await paginate_aws_items(
        ctx,
        operation,
        call_in_thread,
        request_params,
        spec,
        max_items=max_items,
        next_token=next_token,
    )
    return [formatter(item) for item in items], pagination


async def _collect_automation_events(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginate automation events, returning the items and the pagination block.

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

    return await _paginate(
        ctx,
        'ListAutomationEvents',
        client.list_automation_events,
        request_params,
        COA_LIST_AUTOMATION_EVENTS,
        _format_automation_event,
        max_items,
        next_token,
    )


async def _collect_automation_event_steps(
    ctx: Context,
    client: Any,
    event_id: str,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginate automation event steps, returning the items and the pagination block.

    See list_automation_event_steps for argument semantics.
    """
    return await _paginate(
        ctx,
        'ListAutomationEventSteps',
        client.list_automation_event_steps,
        {'eventId': event_id},
        COA_LIST_AUTOMATION_EVENT_STEPS,
        _format_automation_event_step,
        max_items,
        next_token,
    )


async def _collect_automation_event_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginate automation event summaries, returning items and the pagination block.

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

    return await _paginate(
        ctx,
        'ListAutomationEventSummaries',
        client.list_automation_event_summaries,
        request_params,
        COA_LIST_AUTOMATION_EVENT_SUMMARIES,
        _format_event_summary,
        max_items,
        next_token,
    )


async def _collect_recommended_actions(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginate recommended actions, returning the items and the pagination block.

    See list_recommended_actions for argument semantics.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters

    return await _paginate(
        ctx,
        'ListRecommendedActions',
        client.list_recommended_actions,
        request_params,
        COA_LIST_RECOMMENDED_ACTIONS,
        _format_recommended_action,
        max_items,
        next_token,
    )


async def _collect_recommended_action_summaries(
    ctx: Context,
    client: Any,
    filters: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginate recommended action summaries, returning items and the pagination block.

    See list_recommended_action_summaries for argument semantics.
    """
    request_params: Dict[str, Any] = {}

    parsed_filters = parse_json(filters, 'filters')
    if parsed_filters:
        request_params['filters'] = parsed_filters

    return await _paginate(
        ctx,
        'ListRecommendedActionSummaries',
        client.list_recommended_action_summaries,
        request_params,
        COA_LIST_RECOMMENDED_ACTION_SUMMARIES,
        _format_summary,
        max_items,
        next_token,
    )


def _rule_preview_request(
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str],
    criteria: Optional[str],
) -> Dict[str, Any]:
    """Build the request shared by the two rule preview operations."""
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
    return request_params


async def _collect_automation_rule_preview(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginate automation rule preview results, returning items and the pagination block.

    See list_automation_rule_preview for argument semantics.
    """
    return await _paginate(
        ctx,
        'ListAutomationRulePreview',
        client.list_automation_rule_preview,
        _rule_preview_request(rule_type, recommended_action_types, organization_scope, criteria),
        COA_LIST_AUTOMATION_RULE_PREVIEW,
        _format_recommended_action,
        max_items,
        next_token,
    )


async def _collect_automation_rule_preview_summaries(
    ctx: Context,
    client: Any,
    rule_type: str,
    recommended_action_types: str,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Paginate rule preview summaries, returning the items and the pagination block.

    See list_automation_rule_preview_summaries for argument semantics.
    """
    return await _paginate(
        ctx,
        'ListAutomationRulePreviewSummaries',
        client.list_automation_rule_preview_summaries,
        _rule_preview_request(rule_type, recommended_action_types, organization_scope, criteria),
        COA_LIST_AUTOMATION_RULE_PREVIEW_SUMMARIES,
        _format_summary,
        max_items,
        next_token,
    )


# ===== Shared helpers =====


async def _finalize_list_response(
    ctx: Context,
    operation: str,
    list_key: str,
    items: List[Dict[str, Any]],
    pagination: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a list response, offloading to SQL when it exceeds the size threshold.

    Every list operation routes through the size gate. The gate only offloads
    responses above the threshold (default 25KB) to a session SQLite table so the
    agent's context window isn't overloaded — smaller responses pass through
    inline unchanged. Gating uniformly (rather than by predicted size) keeps the
    behavior consistent and covers the less obvious large cases: free-form event
    descriptions, up to 1000 accounts per page, and tag-heavy recommended actions.

    Args:
        ctx: The MCP context object.
        operation: The tool operation name, used to prefix the SQL table.
        list_key: The response key holding the list of items (e.g. 'automation_rules').
        items: The formatted items to return.
        pagination: The pagination block from ``paginate_aws_items``.

    Returns:
        A format_response dict — either the inline list or the SQL offload sentinel.
    """
    response_data = await convert_response_if_needed(
        ctx,
        with_pagination({list_key: items}, pagination),
        f'compute_optimizer_automation_{operation}',
    )

    return format_response('success', response_data)


def _parse_datetime(value: str, parameter_name: str) -> Any:
    """Parse a UTC datetime string into a timezone-aware datetime for boto3.

    Args:
        value: A datetime string in YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS format (UTC),
            optionally ending in the ISO 8601 UTC designator 'Z'
            (e.g. 2026-07-10T00:00:00Z).
        parameter_name: Name of the parameter, used in error messages.

    Returns:
        A timezone-aware datetime object.

    Raises:
        ValueError: If the datetime string format is invalid.
    """
    # 'Z' names the UTC offset these strings are already interpreted in.
    text = value[:-1] if value.endswith(('Z', 'z')) else value
    for fmt in _SUPPORTED_UTC_DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(
        f"Invalid datetime format for {parameter_name}: '{value}'. "
        'Expected YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, optionally with a trailing Z (UTC).'
    )


def create_compute_optimizer_automation_client(region: Optional[str] = None) -> Any:
    """Create a Compute Optimizer Automation boto3 client.

    Args:
        region: Optional AWS region. Defaults to the AWS_REGION env var or us-east-1.

    Returns:
        boto3.client: The Compute Optimizer Automation client.
    """
    return create_aws_client('compute-optimizer-automation', region_name=region)


__all__ = [
    'create_compute_optimizer_automation_client',
    'get_automation_event',
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
    '_collect_automation_events',
    '_collect_automation_event_steps',
    '_collect_automation_event_summaries',
    '_collect_recommended_actions',
    '_collect_recommended_action_summaries',
    '_collect_automation_rule_preview',
    '_collect_automation_rule_preview_summaries',
]
