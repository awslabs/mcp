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

"""AWS Compute Optimizer Automation tools for the AWS Billing and Cost Management MCP server.

Provides a single MCP tool exposing Compute Optimizer Automation operations via an
`operation` dispatch parameter, matching the pattern used by compute_optimizer and
cost_optimization_hub in this package.

Compute Optimizer Automation lets customers implement Compute Optimizer recommendations,
either automatically via rules or on demand.

Compute Optimizer Automation is a regional service, but this tool presents it globally:
with no `region`, operations that return region-scoped data (events, recommended actions,
and their summaries and previews) query every Automation region concurrently and merge the
results. Pass a `region` to target a single region.
"""

import asyncio
import botocore.session
from ..utilities.aws_service_base import format_response, handle_aws_error, parse_json
from ..utilities.regional_fanout import (
    collect_regional_pages,
    encode_regional_next_token,
    fan_out_regions,
    parse_regional_next_token,
)
from ..utilities.sql_utils import convert_response_if_needed
from .compute_optimizer_automation_operations import (
    _collect_automation_event_steps,
    _collect_automation_event_summaries,
    _collect_automation_events,
    _collect_automation_rule_preview,
    _collect_automation_rule_preview_summaries,
    _collect_recommended_action_summaries,
    _collect_recommended_actions,
    _format_automation_event,
    _parse_datetime,
    create_compute_optimizer_automation_client,
    get_automation_event,
    get_automation_rule,
    get_enrollment_configuration,
    list_accounts,
    list_automation_event_steps,
    list_automation_event_summaries,
    list_automation_events,
    list_automation_rule_preview,
    list_automation_rule_preview_summaries,
    list_automation_rules,
    list_recommended_action_summaries,
    list_recommended_actions,
    list_tags_for_resource,
)
from botocore import xform_name
from fastmcp import Context, FastMCP
from functools import lru_cache
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple


_SERVICE_NAME = 'Compute Optimizer Automation'
_BOTO_SERVICE_NAME = 'compute-optimizer-automation'
_MAX_CONCURRENT_REGIONS = 8

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

# The operations this tool supports, in the order presented to callers.
VALID_OPERATIONS = [
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
]

# Operations whose data is account-global: a single regional endpoint returns
# everything (rules are global resources; enrollment and account lists are
# account-scoped), so with no explicit region they use one default-region call
# rather than fanning out. Every other operation fans out across all regions.
_SINGLE_REGION_OPERATIONS = {
    'get_automation_rule',
    'list_tags_for_resource',
    'list_automation_rules',
    'get_enrollment_configuration',
    'list_accounts',
}


@lru_cache(maxsize=1)
def _valid_filter_names_by_operation() -> Dict[str, List[str]]:
    """Build the map of snake_case operation -> valid `filters` names from the boto model.

    The filter-name enums (RecommendedActionFilterName, etc.) are read from the installed
    botocore service model rather than hardcoded, so new filter names are supported
    automatically whenever boto3 is upgraded. The model is loaded offline (no AWS call).

    Returns:
        Mapping of operation name (as accepted by this tool) to the list of valid filter
        names. Operations without a `filters` input are omitted. Returns an empty map if
        the service model cannot be loaded (validation is then skipped and AWS validates).
    """
    result: Dict[str, List[str]] = {}
    try:
        service_model: Any = botocore.session.get_session().get_service_model(_BOTO_SERVICE_NAME)
    except Exception:
        # Older boto3 without this service, or model load failure: skip local validation.
        return result

    for op_name in service_model.operation_names:
        input_shape = service_model.operation_model(op_name).input_shape
        if input_shape is None:
            continue
        filters_member = input_shape.members.get('filters')
        if filters_member is None or filters_member.type_name != 'list':
            continue
        name_member = filters_member.member.members.get('name')
        enum_values = getattr(name_member, 'enum', None)
        if enum_values:
            # xform_name maps the model operation name to the snake_case `operation`
            # value this tool accepts (e.g. ListRecommendedActions -> list_recommended_actions).
            result[xform_name(op_name)] = list(enum_values)

    return result


compute_optimizer_automation_server = FastMCP(
    name='compute-optimizer-automation-tools',
    instructions='Tools for working with the AWS Compute Optimizer Automation API',
)


@compute_optimizer_automation_server.tool(
    name='compute-optimizer-automation',
    description="""Retrieves data from AWS Compute Optimizer Automation.

Compute Optimizer Automation lets customers implement Compute Optimizer recommendations,
either automatically via rules or on demand.

USE THIS TOOL FOR:
- **Automation enrollment status** (is the account enrolled in Compute Optimizer Automation?)
- **Automation rules** (list/inspect rules that auto-apply recommendations, their schedules, criteria)
- **Automation events** (executions of a recommended action, their steps, status, and realized savings)
- **Recommended actions** already surfaced for automation (what a rule would/did act on)
- **Rule previews** (dry-run what a rule config would match before creating it)

DO NOT USE FOR:
- Compute Optimizer's raw per-resource rightsizing recommendations, e.g. "what EBS/EC2
  changes are recommended?" (use compute-optimizer)
- Cost savings / idle-resource recommendations across services (use cost-optimization)

Distinction: this tool covers the *automation* layer — rules, events, and the recommended
actions those rules operate on. It does not generate Compute Optimizer recommendations
itself; for those use the compute-optimizer tool.

**Regions:** By default this tool is global. With no `region`, operations that return
region-scoped data (get_automation_event, list_automation_events,
list_automation_event_steps, list_recommended_actions, the *_summaries, and the rule
preview operations) query every Compute Optimizer Automation region concurrently and merge
the results; each item includes its `region`, and the response includes `regions_queried`.
Account-global operations (get_automation_rule, get_enrollment_configuration, list_accounts,
list_automation_rules, list_tags_for_resource) use a single call — rules are global
resources. Specify a `region` to target one region (defaults to the AWS_REGION env var or
us-east-1 for the account-global operations).

Supported operations (pass via the `operation` parameter):

1. get_enrollment_configuration: Current Automation enrollment status for the account.
   Params: (none)
2. get_automation_event: Details about a single automation event (one execution of a
   recommended action). Params: event_id (required)
3. get_automation_rule: Details about a single automation rule, including its criteria
   and tags. Params: rule_arn (required)
4. list_accounts: Organization accounts enrolled in Compute Optimizer and whether they
   enabled Automation (management/delegated-admin only). Params: max_results, next_token
5. list_automation_events: Automation events matching filters (created within the past
   year). Params: filters, start_time, end_time, max_results, next_token
6. list_automation_event_steps: Steps for a specific automation event.
   Params: event_id (required), max_results, next_token
7. list_automation_event_summaries: Aggregated automation-event counts and savings.
   Params: filters, start_date, end_date, max_results, next_token
8. list_automation_rules: Automation rules matching filters.
   Params: filters, max_results, next_token
9. list_recommended_actions: Recommended actions matching filters.
   Params: filters, max_results, next_token
10. list_recommended_action_summaries: Aggregated recommended-action counts and savings.
    Params: filters, max_results, next_token
11. list_automation_rule_preview: Preview the recommended actions a rule config would
    match, without creating the rule. Params: rule_type (required),
    recommended_action_types (required), organization_scope, criteria, max_results,
    next_token
12. list_automation_rule_preview_summaries: Aggregated summary of a rule preview.
    Params: same as list_automation_rule_preview
13. list_tags_for_resource: Tags for a resource (e.g. an automation rule).
    Params: resource_arn (required)

Filter parameters (`filters`) are passed as a JSON string array of {name, values} objects.
Valid filter names by operation:
- list_automation_events / list_automation_event_summaries: AccountId, ResourceType,
  EventType, EventStatus
- list_automation_rules: Name, RecommendedActionType, Status, RuleType,
  OrganizationConfigurationRuleApplyOrder, AccountId
- list_recommended_actions / list_recommended_action_summaries: ResourceType,
  RecommendedActionType, ResourceId, LookBackPeriodInDays,
  CurrentResourceDetailsEbsVolumeType, ResourceTagsKey, ResourceTagsValue, AccountId,
  RestartNeeded

List operations paginate automatically up to max_pages (default 10, applied per region in
global mode). The returned `count` is the number of items in this response, not a grand
total. When more results remain, pass the returned opaque `next_token` string back
unchanged. Tokens from global and explicit-region queries are not interchangeable.
A global response may also include `region_errors` ({region: structured error}) for
regions that failed while others succeeded.

Examples:
- {"operation": "get_enrollment_configuration"}
- {"operation": "get_automation_event", "event_id": "abc123"}
- {"operation": "list_automation_events", "filters": "[{\"name\": \"EventStatus\", \"values\": [\"Complete\"]}]"}
- {"operation": "list_automation_rule_preview", "rule_type": "AccountRule", "recommended_action_types": "[\"UpgradeEbsVolumeType\"]"}""",
)
async def compute_optimizer_automation(
    ctx: Context,
    operation: str,
    region: Optional[str] = None,
    event_id: Optional[str] = None,
    rule_arn: Optional[str] = None,
    resource_arn: Optional[str] = None,
    filters: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    rule_type: Optional[str] = None,
    recommended_action_types: Optional[str] = None,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve data from AWS Compute Optimizer Automation.

    Args:
        ctx: The MCP context object.
        operation: The operation to perform (see VALID_OPERATIONS).
        region: Optional AWS region. If omitted, region-scoped operations query all
            Compute Optimizer Automation regions and merge; account-global operations
            default to the AWS_REGION env var or us-east-1.
        event_id: Automation event ID (get_automation_event, list_automation_event_steps).
        rule_arn: Automation rule ARN (get_automation_rule).
        resource_arn: Resource ARN (list_tags_for_resource).
        filters: Optional JSON string list of {name, values} filter objects.
        start_time: Optional inclusive start datetime for list_automation_events (UTC).
        end_time: Optional exclusive end datetime for list_automation_events (UTC).
        start_date: Optional inclusive start date for list_automation_event_summaries.
        end_date: Optional exclusive end date for list_automation_event_summaries.
        rule_type: Rule type for the preview operations ('OrganizationRule'/'AccountRule').
        recommended_action_types: JSON string array of action types for the preview operations.
        organization_scope: Optional JSON string {accountIds: [...]} for the preview operations.
        criteria: Optional JSON string of rule criteria conditions for the preview operations.
        max_results: Optional maximum number of results per page (list operations).
        max_pages: Maximum number of API pages to fetch (list operations). Defaults to 10.
            Applied per region in global mode.
        next_token: Optional pagination token from a previous response (list operations).
            Pass the opaque string from the previous response back unchanged. Global
            tokens and explicit-region tokens are not interchangeable.

    Returns:
        Dict containing the requested Compute Optimizer Automation data.
    """
    try:
        await ctx.info(f'Compute Optimizer Automation operation: {operation}')

        # Validate required parameters before creating a client.
        validation_error = _validate_operation_params(
            operation,
            event_id=event_id,
            rule_arn=rule_arn,
            resource_arn=resource_arn,
            rule_type=rule_type,
            recommended_action_types=recommended_action_types,
        )
        if validation_error is not None:
            return validation_error

        # Validate the filters JSON and filter names before calling AWS.
        filter_error = _validate_filters(operation, filters)
        if filter_error is not None:
            return filter_error

        # Parse operation-specific structured inputs before creating one client
        # or fanning out across regions. Handlers still parse them when building
        # requests; this pass ensures malformed input fails once and consistently.
        _validate_parseable_params(
            operation,
            start_time=start_time,
            end_time=end_time,
            recommended_action_types=recommended_action_types,
            organization_scope=organization_scope,
            criteria=criteria,
        )

        # With no explicit region, most operations fan out across all Automation
        # regions; account-global operations still use a single default-region call.
        if region is None and operation not in _SINGLE_REGION_OPERATIONS:
            return await dispatch_global(
                ctx,
                operation,
                event_id=event_id,
                filters=filters,
                start_time=start_time,
                end_time=end_time,
                start_date=start_date,
                end_date=end_date,
                rule_type=rule_type,
                recommended_action_types=recommended_action_types,
                organization_scope=organization_scope,
                criteria=criteria,
                max_results=max_results,
                max_pages=max_pages,
                next_token=next_token,
            )

        # Single-region path: an explicit region, or an account-global operation.
        # Catch the actionable cross-mode mistake locally instead of sending an
        # encoded regional map to AWS as though it were a native service token.
        if next_token:
            _, global_token_error = parse_regional_next_token(
                next_token, COMPUTE_OPTIMIZER_AUTOMATION_REGIONS
            )
            if global_token_error is None:
                return format_response(
                    'error',
                    {'operation': operation, 'parameter': 'next_token'},
                    'A global next_token is only valid when region is omitted. With an '
                    'explicit region, pass the next_token returned by that same '
                    'explicit-region query.',
                )

        return await dispatch_regional(
            ctx,
            operation,
            region=region,
            event_id=event_id,
            rule_arn=rule_arn,
            resource_arn=resource_arn,
            filters=filters,
            start_time=start_time,
            end_time=end_time,
            start_date=start_date,
            end_date=end_date,
            rule_type=rule_type,
            recommended_action_types=recommended_action_types,
            organization_scope=organization_scope,
            criteria=criteria,
            max_results=max_results,
            max_pages=max_pages,
            next_token=next_token,
        )

    except Exception as e:
        return await handle_aws_error(ctx, e, operation, _SERVICE_NAME)


async def dispatch_regional(
    ctx: Context,
    operation: str,
    region: Optional[str] = None,
    event_id: Optional[str] = None,
    rule_arn: Optional[str] = None,
    resource_arn: Optional[str] = None,
    filters: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    rule_type: Optional[str] = None,
    recommended_action_types: Optional[str] = None,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create one regional client and dispatch an operation to its handler."""
    client = create_compute_optimizer_automation_client(region)

    handlers = {
        'get_automation_event': lambda: get_automation_event(ctx, client, str(event_id)),
        'get_automation_rule': lambda: get_automation_rule(ctx, client, str(rule_arn)),
        'get_enrollment_configuration': lambda: get_enrollment_configuration(ctx, client),
        'list_accounts': lambda: list_accounts(ctx, client, max_results, max_pages, next_token),
        'list_automation_events': lambda: list_automation_events(
            ctx, client, filters, start_time, end_time, max_results, max_pages, next_token
        ),
        'list_automation_event_steps': lambda: list_automation_event_steps(
            ctx, client, str(event_id), max_results, max_pages, next_token
        ),
        'list_automation_event_summaries': lambda: list_automation_event_summaries(
            ctx, client, filters, start_date, end_date, max_results, max_pages, next_token
        ),
        'list_automation_rules': lambda: list_automation_rules(
            ctx, client, filters, max_results, max_pages, next_token
        ),
        'list_recommended_actions': lambda: list_recommended_actions(
            ctx, client, filters, max_results, max_pages, next_token
        ),
        'list_recommended_action_summaries': lambda: list_recommended_action_summaries(
            ctx, client, filters, max_results, max_pages, next_token
        ),
        'list_automation_rule_preview': lambda: list_automation_rule_preview(
            ctx,
            client,
            str(rule_type),
            str(recommended_action_types),
            organization_scope,
            criteria,
            max_results,
            max_pages,
            next_token,
        ),
        'list_automation_rule_preview_summaries': lambda: list_automation_rule_preview_summaries(
            ctx,
            client,
            str(rule_type),
            str(recommended_action_types),
            organization_scope,
            criteria,
            max_results,
            max_pages,
            next_token,
        ),
        'list_tags_for_resource': lambda: list_tags_for_resource(ctx, client, str(resource_arn)),
    }

    handler = handlers.get(operation)
    if handler is None:
        return format_response(
            'error',
            {'provided_operation': operation, 'valid_operations': VALID_OPERATIONS},
            f'Unsupported operation: {operation}. Valid operations: {", ".join(VALID_OPERATIONS)}.',
        )

    return await handler()


async def dispatch_global(
    ctx: Context,
    operation: str,
    event_id: Optional[str] = None,
    filters: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    rule_type: Optional[str] = None,
    recommended_action_types: Optional[str] = None,
    organization_scope: Optional[str] = None,
    criteria: Optional[str] = None,
    max_results: Optional[int] = None,
    max_pages: int = 10,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a fan-out operation across all Compute Optimizer Automation regions."""
    if operation == 'get_automation_event':
        return await _get_automation_event_global(ctx, str(event_id))

    regions_tokens, token_error = parse_regional_next_token(
        next_token, COMPUTE_OPTIMIZER_AUTOMATION_REGIONS
    )
    if token_error is not None:
        return token_error

    # Each entry: (list_key, collect(client, token) -> (items, token), not_found_is_empty).
    global_handlers = {
        'list_automation_events': (
            'automation_events',
            lambda client, token: _collect_automation_events(
                ctx, client, filters, start_time, end_time, max_results, max_pages, token
            ),
            False,
        ),
        'list_automation_event_steps': (
            'automation_event_steps',
            lambda client, token: _collect_automation_event_steps(
                ctx, client, str(event_id), max_results, max_pages, token
            ),
            True,
        ),
        'list_automation_event_summaries': (
            'automation_event_summaries',
            lambda client, token: _collect_automation_event_summaries(
                ctx, client, filters, start_date, end_date, max_results, max_pages, token
            ),
            False,
        ),
        'list_recommended_actions': (
            'recommended_actions',
            lambda client, token: _collect_recommended_actions(
                ctx, client, filters, max_results, max_pages, token
            ),
            False,
        ),
        'list_recommended_action_summaries': (
            'recommended_action_summaries',
            lambda client, token: _collect_recommended_action_summaries(
                ctx, client, filters, max_results, max_pages, token
            ),
            False,
        ),
        'list_automation_rule_preview': (
            'preview_results',
            lambda client, token: _collect_automation_rule_preview(
                ctx,
                client,
                str(rule_type),
                str(recommended_action_types),
                organization_scope,
                criteria,
                max_results,
                max_pages,
                token,
            ),
            False,
        ),
        'list_automation_rule_preview_summaries': (
            'preview_result_summaries',
            lambda client, token: _collect_automation_rule_preview_summaries(
                ctx,
                client,
                str(rule_type),
                str(recommended_action_types),
                organization_scope,
                criteria,
                max_results,
                max_pages,
                token,
            ),
            False,
        ),
    }

    spec = global_handlers.get(operation)
    if spec is None:
        return format_response(
            'error',
            {'provided_operation': operation, 'valid_operations': VALID_OPERATIONS},
            f'Unsupported operation: {operation}. Valid operations: {", ".join(VALID_OPERATIONS)}.',
        )

    list_key, collect, not_found_is_empty = spec
    return await _run_global_list(
        ctx, operation, list_key, regions_tokens, collect, not_found_is_empty
    )


def _partition_resource_not_found_errors(
    region_errors: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Separate not-found outcomes from other regional errors."""
    regions_not_found = [
        region
        for region, error in region_errors.items()
        if error.get('error_type') == 'ResourceNotFoundException'
    ]
    other_errors = {
        region: error
        for region, error in region_errors.items()
        if error.get('error_type') != 'ResourceNotFoundException'
    }
    return other_errors, regions_not_found


async def _run_global_list(
    ctx: Context,
    operation: str,
    list_key: str,
    regions_tokens: Dict[str, Optional[str]],
    collect: Callable[[Any, Optional[str]], Awaitable[Tuple[List[Dict[str, Any]], Optional[str]]]],
    not_found_is_empty: bool = False,
) -> Dict[str, Any]:
    """Run and merge a regional list operation."""

    async def worker(
        region: str, token: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        client = await asyncio.to_thread(create_compute_optimizer_automation_client, region)
        return await collect(client, token)

    outcomes = await collect_regional_pages(
        regions_tokens,
        worker,
        ctx=ctx,
        operation=operation,
        service_name=_SERVICE_NAME,
        max_concurrency=_MAX_CONCURRENT_REGIONS,
    )

    region_errors = outcomes.errors
    regions_not_found: List[str] = []
    if not_found_is_empty:
        region_errors, regions_not_found = _partition_resource_not_found_errors(region_errors)

    successful_regions = len(outcomes.successful_regions)
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
            message = (
                f'Could not determine whether the requested resource exists for {operation}: '
                f'{len(region_errors)} region(s) failed and {len(regions_not_found)} returned '
                'not found.'
            )
        else:
            message = f'All {len(region_errors)} region(s) failed for {operation}.'
        return format_response('error', data, message)

    return await _finalize_global_list_response(
        ctx,
        operation,
        list_key,
        outcomes.items,
        list(regions_tokens),
        outcomes.next_tokens,
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
    """Build a merged multi-region list response, offloading to SQL when large."""
    response_data: Dict[str, Any] = {
        list_key: items,
        'count': len(items),
        'regions_queried': regions_queried,
    }
    global_next_token = None
    if region_next_tokens:
        global_next_token = encode_regional_next_token(region_next_tokens)
        response_data['next_token'] = global_next_token
    if region_errors:
        response_data['region_errors'] = region_errors

    offload_metadata: Dict[str, Any] = {'regions_queried': regions_queried}
    if global_next_token:
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


async def _get_automation_event_global(ctx: Context, event_id: str) -> Dict[str, Any]:
    """Locate an automation event by ID across all Automation regions."""

    async def worker(region: str, request_event_id: str) -> Optional[Dict[str, Any]]:
        client = await asyncio.to_thread(create_compute_optimizer_automation_client, region)
        return await asyncio.to_thread(client.get_automation_event, eventId=request_event_id)

    await ctx.info(f'Searching all Automation regions for automation event {event_id}')
    outcomes = await fan_out_regions(
        dict.fromkeys(COMPUTE_OPTIMIZER_AUTOMATION_REGIONS, event_id),
        worker,
        ctx=ctx,
        operation='get_automation_event',
        service_name=_SERVICE_NAME,
        max_concurrency=_MAX_CONCURRENT_REGIONS,
    )

    for region, response in outcomes.successes.items():
        if response is not None:
            return format_response(
                'success',
                {
                    'automation_event': _format_automation_event(response),
                    'found_in_region': region,
                },
            )

    data: Dict[str, Any] = {
        'event_id': event_id,
        'regions_queried': list(COMPUTE_OPTIMIZER_AUTOMATION_REGIONS),
    }
    region_errors, regions_not_found = _partition_resource_not_found_errors(outcomes.errors)
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


def _validate_operation_params(
    operation: str,
    event_id: Optional[str],
    rule_arn: Optional[str],
    resource_arn: Optional[str],
    rule_type: Optional[str],
    recommended_action_types: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Validate that operation-specific required parameters are present.

    Args:
        operation: The requested operation.
        event_id: Provided event_id, if any.
        rule_arn: Provided rule_arn, if any.
        resource_arn: Provided resource_arn, if any.
        rule_type: Provided rule_type, if any.
        recommended_action_types: Provided recommended_action_types, if any.

    Returns:
        An error response dict if a required parameter is missing, otherwise None.
    """
    # Map each operation to the parameters it requires.
    required: Dict[str, Any] = {
        'get_automation_event': [('event_id', event_id)],
        'list_automation_event_steps': [('event_id', event_id)],
        'get_automation_rule': [('rule_arn', rule_arn)],
        'list_tags_for_resource': [('resource_arn', resource_arn)],
        'list_automation_rule_preview': [
            ('rule_type', rule_type),
            ('recommended_action_types', recommended_action_types),
        ],
        'list_automation_rule_preview_summaries': [
            ('rule_type', rule_type),
            ('recommended_action_types', recommended_action_types),
        ],
    }

    missing = [name for name, value in required.get(operation, []) if not value]
    if missing:
        return format_response(
            'error',
            {'operation': operation, 'missing_parameters': missing},
            f'Missing required parameter(s) for {operation}: {", ".join(missing)}.',
        )

    return None


def _validate_parseable_params(
    operation: str,
    start_time: Optional[str],
    end_time: Optional[str],
    recommended_action_types: Optional[str],
    organization_scope: Optional[str],
    criteria: Optional[str],
) -> None:
    """Validate structured operation inputs before client creation or fan-out."""
    if operation == 'list_automation_events':
        if start_time:
            _parse_datetime(start_time, 'start_time')
        if end_time:
            _parse_datetime(end_time, 'end_time')

    if operation in {
        'list_automation_rule_preview',
        'list_automation_rule_preview_summaries',
    }:
        parse_json(recommended_action_types, 'recommended_action_types')
        if organization_scope:
            parse_json(organization_scope, 'organization_scope')
        if criteria:
            parse_json(criteria, 'criteria')


def _validate_filters(operation: str, filters: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate the `filters` JSON string and its filter names for an operation.

    Returns a friendly error response (rather than surfacing a raw JSON error or an
    AWS ValidationException) when the filters are malformed or use an unknown filter
    name. Returns None when filters are absent or valid.

    Args:
        operation: The requested operation.
        filters: The raw JSON string supplied for the `filters` parameter, if any.

    Returns:
        An error response dict if the filters are invalid, otherwise None.
    """
    if not filters:
        return None

    valid_names = _valid_filter_names_by_operation().get(operation)
    if valid_names is None:
        # Operation does not accept filters, or the boto model is unavailable; skip
        # local validation and let AWS validate. The handler won't forward filters for
        # non-filter operations.
        return None

    try:
        parsed = parse_json(filters, 'filters')
    except ValueError as e:
        return format_response(
            'error',
            {'operation': operation, 'filters': filters},
            f'Invalid JSON for filters parameter: {e}',
        )

    if not isinstance(parsed, list):
        return format_response(
            'error',
            {'operation': operation, 'filters': filters},
            'The filters parameter must be a JSON array of {name, values} objects.',
        )

    invalid = [
        item.get('name')
        for item in parsed
        if isinstance(item, dict) and item.get('name') not in valid_names
    ]
    if invalid:
        return format_response(
            'error',
            {
                'operation': operation,
                'invalid_filter_names': invalid,
                'valid_filter_names': valid_names,
            },
            f'Invalid filter name(s) for {operation}: {", ".join(str(n) for n in invalid)}. '
            f'Valid filter names: {", ".join(valid_names)}.',
        )

    return None
