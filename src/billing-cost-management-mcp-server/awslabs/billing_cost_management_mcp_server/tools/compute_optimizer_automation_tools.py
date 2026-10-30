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

Compute Optimizer Automation is a regional service. Pass `regions` to query several
regions concurrently and merge the results; operations that return region-scoped data
(events, recommended actions, and their summaries and previews) stamp each item with its
region. With no `regions`, a single call targets the AWS_REGION env var or us-east-1.
"""

import asyncio
import botocore.session
import json
from ..utilities.aws_service_base import (
    format_response,
    handle_aws_error,
    parse_json,
    partial_data_warning,
    with_pagination,
)
from ..utilities.constants import PAGINATION_LIMIT_TEXT
from ..utilities.error_contract import classify_error, combine_guidance
from ..utilities.regional_fanout import (
    collect_regional_pages,
    encode_regional_next_token,
    fan_out_regions,
    is_regional_next_token,
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
    _rule_preview_request,
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
from botocore.exceptions import ParamValidationError
from botocore.validate import ParamValidator
from fastmcp import Context, FastMCP
from functools import lru_cache
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple


_SERVICE_NAME = 'Compute Optimizer Automation'
_BOTO_SERVICE_NAME = 'compute-optimizer-automation'
_MAX_CONCURRENT_REGIONS = 8
_RESOURCE_NOT_FOUND_ERROR_TYPE = 'ResourceNotFoundException'
# Top-level error_type for a multi-region failure whose regions failed for different reasons.
_MULTI_REGION_ERROR_TYPE = 'multi_region_error'

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
# account-scoped), so fanning them out would repeat identical data. They accept
# at most one region. Every other operation can span the requested regions.
_SINGLE_REGION_OPERATIONS = {
    'get_automation_rule',
    'list_tags_for_resource',
    'list_automation_rules',
    'get_enrollment_configuration',
    'list_accounts',
}

_PREVIEW_API_NAMES = {
    'list_automation_rule_preview': 'ListAutomationRulePreview',
    'list_automation_rule_preview_summaries': 'ListAutomationRulePreviewSummaries',
}


@lru_cache(maxsize=1)
def _preview_input_shapes() -> Dict[str, Any]:
    """Return {preview operation: botocore input shape}, or {} if the model cannot be loaded."""
    try:
        service_model: Any = botocore.session.get_session().get_service_model(_BOTO_SERVICE_NAME)
        return {
            operation: service_model.operation_model(api_name).input_shape
            for operation, api_name in _PREVIEW_API_NAMES.items()
        }
    except Exception:
        return {}


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


# The request model types every filter value as a free string, so the values a filter accepts are
# read from the enum on the matching member of the operation's response. This maps a filter name
# to that response member, and each operation to the list call whose response carries it.
_FILTER_VALUE_MEMBERS: Dict[str, str] = {
    'ResourceType': 'resourceType',
    'RecommendedActionType': 'recommendedActionType',
    'EventType': 'eventType',
    'EventStatus': 'eventStatus',
    'Status': 'status',
    'RuleType': 'ruleType',
}
_FILTER_VALUE_SOURCE_API: Dict[str, str] = {
    'list_automation_events': 'ListAutomationEvents',
    'list_automation_event_summaries': 'ListAutomationEvents',
    'list_automation_rules': 'ListAutomationRules',
    'list_recommended_actions': 'ListRecommendedActions',
    'list_recommended_action_summaries': 'ListRecommendedActions',
}
# For these the API answers an unknown value with an empty success, so an unknown value is
# rejected locally. The other enum filters are folded but passed through: the API already
# rejects an unknown value for them and names the valid ones.
_STRICT_VALUE_FILTERS = frozenset({'ResourceType', 'EventStatus'})


def _filter_value_key(value: str) -> str:
    """Fold a filter value for matching: case- and underscore-insensitive."""
    return value.casefold().replace('_', '')


def _member_key(name: str) -> str:
    """Fold a response member name for matching: case-insensitive, singular/plural agnostic."""
    return name.casefold().removesuffix('s')


def _collect_response_enums(shape: Any, found: Dict[str, List[str]], seen: set) -> None:
    """Collect {member name: enum values} from a response shape, first occurrence wins."""
    if shape is None or id(shape) in seen:
        return
    seen.add(id(shape))
    if shape.type_name == 'list':
        _collect_response_enums(shape.member, found, seen)
    elif shape.type_name == 'structure':
        for name, member in shape.members.items():
            target = member.member if member.type_name == 'list' else member
            values = getattr(target, 'enum', None)
            if values:
                found.setdefault(name, list(values))
            _collect_response_enums(member, found, seen)


def _response_enums(service_model: Any, api_name: str) -> Dict[str, List[str]]:
    """Return {member name: enum values} for one API's response, or {} if it cannot be read."""
    found: Dict[str, List[str]] = {}
    try:
        _collect_response_enums(service_model.operation_model(api_name).output_shape, found, set())
    except Exception:
        return {}
    return found


@lru_cache(maxsize=1)
def _filter_values_by_operation() -> Dict[str, Dict[str, List[str]]]:
    """Build {operation: {filter name: accepted values}} for the enum-valued filters.

    Read offline from the installed botocore service model. Returns an empty map if the
    model cannot be loaded (value normalization is then skipped and AWS validates).
    """
    result: Dict[str, Dict[str, List[str]]] = {}
    try:
        service_model: Any = botocore.session.get_session().get_service_model(_BOTO_SERVICE_NAME)
    except Exception:
        return result

    for operation, api_name in _FILTER_VALUE_SOURCE_API.items():
        by_key = {
            _member_key(name): values
            for name, values in _response_enums(service_model, api_name).items()
        }
        values_by_filter = {
            filter_name: by_key[_member_key(member)]
            for filter_name, member in _FILTER_VALUE_MEMBERS.items()
            if _member_key(member) in by_key
        }
        if values_by_filter:
            result[operation] = values_by_filter
    return result


def _normalize_filter_values(
    operation: str, filters: Optional[str]
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Fold filter values onto the spelling the API matches and reject values it mishandles.

    The API compares filter values exactly and, for several filters, answers a value it
    does not match with an empty success. This folds enum values (case and underscores),
    lowercases EBS volume types, and rejects locally: an unknown ResourceType or
    EventStatus, a RestartNeeded other than true/false (the API treats it as false), and a
    LookBackPeriodInDays that is not a whole number (the API fails with an internal error).
    Run after _validate_filters, so the JSON and the filter names are already valid.

    Returns:
        (filters to send, None), or (original filters, error response) when a value is
        rejected. The original string is returned when nothing changed.
    """
    if not filters:
        return filters, None
    try:
        parsed = parse_json(filters, 'filters')
    except ValueError:
        return filters, None
    if not isinstance(parsed, list):
        return filters, None

    known = _filter_values_by_operation().get(operation, {})
    normalized: List[Any] = []
    invalid: Dict[str, List[Any]] = {}
    for item in parsed:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get('name'), str)
            or not isinstance(item.get('values'), list)
        ):
            normalized.append(item)
            continue
        name, values = item['name'], item['values']
        if name in known:
            canonical = {_filter_value_key(v): v for v in known[name]}
            values = [
                canonical.get(_filter_value_key(v), v) if isinstance(v, str) else v for v in values
            ]
            if name in _STRICT_VALUE_FILTERS and any(v not in known[name] for v in values):
                invalid[name] = [v for v in values if v not in known[name]]
        elif name == 'RestartNeeded':
            keys = [str(v).casefold() if isinstance(v, (str, bool)) else None for v in values]
            if any(k not in ('true', 'false') for k in keys):
                invalid[name] = [v for v, k in zip(values, keys) if k not in ('true', 'false')]
            else:
                values = keys
        elif name == 'LookBackPeriodInDays':
            days = [
                str(int(v))
                if (isinstance(v, int) and not isinstance(v, bool))
                or (isinstance(v, str) and v.strip().isdecimal())
                else None
                for v in values
            ]
            if any(d is None for d in days):
                invalid[name] = [v for v, d in zip(values, days) if d is None]
            else:
                values = days
        elif name == 'CurrentResourceDetailsEbsVolumeType':
            # Matching is case-sensitive and every EBS volume type is lowercase (gp2, io1).
            values = [v.lower() if isinstance(v, str) else v for v in values]
        normalized.append({**item, 'values': values})

    if invalid:
        valid = {
            name: known[name]
            if name in known
            else ['true', 'false']
            if name == 'RestartNeeded'
            else 'a whole number of days'
            for name in invalid
        }
        return filters, _validation_error(
            operation,
            {
                'operation': operation,
                'invalid_filter_values': invalid,
                'valid_filter_values': valid,
            },
            'Invalid filter value(s) for '
            + '; '.join(
                f'{name}: {", ".join(str(v) for v in bad)}' for name, bad in invalid.items()
            )
            + '. Valid values: '
            + '; '.join(
                f'{name}: {", ".join(vals) if isinstance(vals, list) else vals}'
                for name, vals in valid.items()
            )
            + '.',
        )
    return (filters if normalized == parsed else json.dumps(normalized)), None


def _validation_error(operation: str, data: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Return an error response for a local parameter-validation failure.

    Sets the same top-level `error_type`, `operation`, and `service` fields that
    handle_aws_error attaches to AWS-side errors, so callers can tell a bad parameter
    apart from a service failure without parsing the message.
    """
    return format_response(
        'error',
        data,
        message,
        error_type='validation_error',
        operation=operation,
        service=_SERVICE_NAME,
    )


def _multi_region_error_type(
    region_errors: Dict[str, Dict[str, Any]], regions_not_found: List[str]
) -> str:
    """Classify a failure in which no queried region succeeded.

    Per-region error types are keyed by region name, which changes from call to call,
    so the shared type is promoted to the top level when every failed region agrees.
    Otherwise the failure is reported as a multi_region_error, and callers can still
    read the per-region detail from `region_errors`.
    """
    error_types = {error.get('error_type') for error in region_errors.values()}
    if regions_not_found:
        error_types.add(_RESOURCE_NOT_FOUND_ERROR_TYPE)
    if len(error_types) == 1:
        error_type = error_types.pop()
        if error_type:
            return error_type
    return _MULTI_REGION_ERROR_TYPE


def _multi_region_guidance(
    region_errors: Dict[str, Dict[str, Any]], regions_not_found: List[str]
) -> Tuple[str, Optional[str]]:
    """Return the (retry_strategy, hint) for a failure in which no queried region succeeded.

    Derived from each region's own error_type and http_status, which stay nested in
    region_errors, so the top-level multi_region_error or a promoted type alone would
    lose them (e.g. throttled in one region and a 5xx in another is still transient).
    A region's own retry_strategy, when its error set one, wins over that mapping.
    """
    guidance = [
        (error['retry_strategy'], error.get('hint'))
        if error.get('retry_strategy')
        else classify_error(error.get('error_type'), error.get('http_status'))
        for error in region_errors.values()
    ]
    if regions_not_found:
        guidance.append(classify_error(_RESOURCE_NOT_FOUND_ERROR_TYPE))
    return combine_guidance(guidance)


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

**Regions:** Compute Optimizer Automation is a regional service. Omit `regions` to query a
single region (the AWS_REGION env var, or us-east-1). Pass `regions` as a list — e.g.
["us-east-1", "eu-west-1"] — to query those regions concurrently and merge the results: each
item includes its `region` and the response includes `regions_queried`. Duplicate entries are
collapsed. Account-global operations (get_automation_rule, get_enrollment_configuration,
list_accounts, list_automation_rules, list_tags_for_resource) accept at most one region —
rules are global resources, so fanning them out would repeat identical data.

Supported operations (pass via the `operation` parameter):

1. get_enrollment_configuration: Current Automation enrollment status for the account.
   Params: (none)
2. get_automation_event: Details about a single automation event (one execution of a
   recommended action). Params: event_id (required). With `regions`, `found_in_region` names
   the region holding the event.
3. get_automation_rule: Details about a single automation rule, including its criteria
   ({} for a rule with no conditions) and tags. Params: rule_arn (required)
4. list_accounts: Organization accounts enrolled in Compute Optimizer and whether they
   enabled Automation (management/delegated-admin only). Params: max_items, next_token
5. list_automation_events: Automation events matching filters (created within the past
   year). Params: filters, start_time, end_time, max_items, next_token
6. list_automation_event_steps: Steps for a specific automation event.
   Params: event_id (required), max_items, next_token. With `regions`, `found_in_region`
   names the region holding the event and `regions_not_found` the regions without it.
7. list_automation_event_summaries: Aggregated automation-event counts and savings.
   Params: filters, start_date, end_date, max_items, next_token. If start_date and end_date
   are omitted, the summary covers all events from the past year.
8. list_automation_rules: Automation rules matching filters.
   Params: filters, max_items, next_token
9. list_recommended_actions: Recommended actions matching filters.
   Params: filters, max_items, next_token
10. list_recommended_action_summaries: Aggregated recommended-action counts and savings.
    Params: filters, max_items, next_token
11. list_automation_rule_preview: Preview the recommended actions a rule config would
    match, without creating the rule. Params: rule_type (required),
    recommended_action_types (required), organization_scope, criteria, max_items,
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

Filter values:
- ResourceType takes EbsVolume. RecommendedActionType and EventType take
  SnapshotAndDeleteUnattachedEbsVolume or UpgradeEbsVolumeType. EventStatus takes Ready,
  InProgress, Complete, Failed, Cancelled, RollbackReady, RollbackInProgress,
  RollbackComplete or RollbackFailed. Status takes Active or Inactive. RuleType takes
  OrganizationRule or AccountRule. Case and underscores are folded, and an unknown
  ResourceType or EventStatus is rejected with the valid values (the API would return an
  empty result).
- RestartNeeded takes true or false. LookBackPeriodInDays takes a whole number of days.
- CurrentResourceDetailsEbsVolumeType, ResourceTagsKey and ResourceTagsValue match
  case-sensitive substrings of the resource details or tags, so a short value matches more
  than intended (io matches every volume, not only io1). Use a full value such as gp2 or io1.
  ResourceTagsKey and ResourceTagsValue each search keys and values, so a key filter also
  matches tag values and the reverse. EBS volume types are lowercased for you.

PAGINATION (list_* operations only; the get_* operations and list_tags_for_resource take
neither max_items nor next_token):
- max_items is the total number of items returned. If it is omitted, the tool fetches every page for """
    + PAGINATION_LIMIT_TEXT
    + """, then returns a partial result.
  Pass it, or narrow the filters, for queries that can be large.
- With `regions`, max_items applies PER REGION: each region returns up to max_items items, so
  a response can hold up to max_items x len(regions) items.
- If the response has complete_dataset: false, call again with a larger max_items, continue
  with pagination.next_token (pass it back unchanged with otherwise identical parameters,
  including the same `regions` list), or state in the answer that the result is partial.
  pagination.items_returned counts the items in this response only; do not report it as a
  total when the result is partial.
- A multi-region response may also include `region_errors` ({region: structured error}) for
  regions that failed while others succeeded.

Examples:
- {"operation": "get_enrollment_configuration"}
- {"operation": "get_automation_event", "event_id": "abc123"}
- {"operation": "list_automation_events", "regions": ["us-east-1", "eu-west-1"]}
- {"operation": "list_automation_events", "filters": "[{\"name\": \"EventStatus\", \"values\": [\"Complete\"]}]"}
- {"operation": "list_automation_rule_preview", "rule_type": "AccountRule", "recommended_action_types": "[\"UpgradeEbsVolumeType\"]"}""",
)
async def compute_optimizer_automation(
    ctx: Context,
    operation: str,
    regions: Optional[List[str]] = None,
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
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve data from AWS Compute Optimizer Automation.

    Args:
        ctx: The MCP context object.
        operation: The operation to perform (see VALID_OPERATIONS).
        regions: Optional list of AWS regions to query concurrently and merge. If omitted
            or empty, a single call targets the AWS_REGION env var or us-east-1.
            Account-global operations accept at most one region.
        event_id: Automation event ID (get_automation_event, list_automation_event_steps).
        rule_arn: Automation rule ARN (get_automation_rule).
        resource_arn: Resource ARN (list_tags_for_resource).
        filters: Optional JSON string list of {name, values} filter objects.
        start_time: Optional inclusive start datetime for list_automation_events (UTC;
            YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, trailing Z allowed).
        end_time: Optional exclusive end datetime for list_automation_events (UTC;
            YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, trailing Z allowed).
        start_date: Optional inclusive start date for list_automation_event_summaries.
        end_date: Optional exclusive end date for list_automation_event_summaries.
        rule_type: Rule type for the preview operations ('OrganizationRule'/'AccountRule').
        recommended_action_types: JSON string array of action types for the preview operations.
        organization_scope: Optional JSON string {accountIds: [...]} for the preview operations.
        criteria: Optional JSON string of rule criteria conditions for the preview operations.
        max_items: Total number of items to return across all pages (per region when
            regions is set). Omit it to fetch every page. List operations only.
        next_token: The pagination.next_token from a previous response; continue with
            otherwise identical parameters, including the same `regions` list. List
            operations only.

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

        # Fold filter values onto the API's spelling and reject values it would mishandle.
        filters, filter_error = _normalize_filter_values(operation, filters)
        if filter_error is not None:
            return filter_error

        # Parse operation-specific structured inputs before creating one client
        # or fanning out across regions. Handlers still parse them when building
        # requests; this pass ensures malformed input fails once and consistently.
        parse_error = _validate_parseable_params(
            operation,
            start_time=start_time,
            end_time=end_time,
            rule_type=rule_type,
            recommended_action_types=recommended_action_types,
            organization_scope=organization_scope,
            criteria=criteria,
        )
        if parse_error is not None:
            return parse_error

        requested_regions, regions_error = _resolve_requested_regions(operation, regions)
        if regions_error is not None:
            return regions_error

        # A list of regions spans them concurrently and merges the results. Account-global
        # operations and an omitted list use one call with the service's native shape.
        if requested_regions and operation not in _SINGLE_REGION_OPERATIONS:
            return await dispatch_multi_region(
                ctx,
                operation,
                requested_regions,
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
                max_items=max_items,
                next_token=next_token,
            )

        # Catch the actionable cross-mode mistake locally instead of sending an encoded
        # regional map to AWS as though it were a native service token.
        if is_regional_next_token(next_token):
            return _validation_error(
                operation,
                {'operation': operation, 'parameter': 'next_token'},
                'A multi-region next_token cannot be used for a single-region request. '
                'Pass the same `regions` list the token was produced with, or omit '
                'next_token to start a new query.',
            )

        return await dispatch_regional(
            ctx,
            operation,
            region=requested_regions[0] if requested_regions else None,
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
            max_items=max_items,
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
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create one regional client and dispatch an operation to its handler."""
    client = create_compute_optimizer_automation_client(region)

    handlers = {
        'get_automation_event': lambda: get_automation_event(ctx, client, str(event_id)),
        'get_automation_rule': lambda: get_automation_rule(ctx, client, str(rule_arn)),
        'get_enrollment_configuration': lambda: get_enrollment_configuration(ctx, client),
        'list_accounts': lambda: list_accounts(ctx, client, max_items, next_token),
        'list_automation_events': lambda: list_automation_events(
            ctx, client, filters, start_time, end_time, max_items, next_token
        ),
        'list_automation_event_steps': lambda: list_automation_event_steps(
            ctx, client, str(event_id), max_items, next_token
        ),
        'list_automation_event_summaries': lambda: list_automation_event_summaries(
            ctx, client, filters, start_date, end_date, max_items, next_token
        ),
        'list_automation_rules': lambda: list_automation_rules(
            ctx, client, filters, max_items, next_token
        ),
        'list_recommended_actions': lambda: list_recommended_actions(
            ctx, client, filters, max_items, next_token
        ),
        'list_recommended_action_summaries': lambda: list_recommended_action_summaries(
            ctx, client, filters, max_items, next_token
        ),
        'list_automation_rule_preview': lambda: list_automation_rule_preview(
            ctx,
            client,
            str(rule_type),
            str(recommended_action_types),
            organization_scope,
            criteria,
            max_items,
            next_token,
        ),
        'list_automation_rule_preview_summaries': lambda: list_automation_rule_preview_summaries(
            ctx,
            client,
            str(rule_type),
            str(recommended_action_types),
            organization_scope,
            criteria,
            max_items,
            next_token,
        ),
        'list_tags_for_resource': lambda: list_tags_for_resource(ctx, client, str(resource_arn)),
    }

    handler = handlers.get(operation)
    if handler is None:
        return _validation_error(
            operation,
            {'provided_operation': operation, 'valid_operations': VALID_OPERATIONS},
            f'Unsupported operation: {operation}. Valid operations: {", ".join(VALID_OPERATIONS)}.',
        )

    return await handler()


async def dispatch_multi_region(
    ctx: Context,
    operation: str,
    regions: List[str],
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
    max_items: Optional[int] = None,
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a fan-out operation across the requested regions."""
    if operation == 'get_automation_event':
        return await _get_automation_event_multi_region(ctx, str(event_id), regions)

    regions_tokens, token_error = parse_regional_next_token(
        next_token, regions, operation=operation, service_name=_SERVICE_NAME
    )
    if token_error is not None:
        return token_error

    # Each entry: (list_key, collect(client, token) -> (items, pagination), not_found_is_empty).
    global_handlers = {
        'list_automation_events': (
            'automation_events',
            lambda client, token: _collect_automation_events(
                ctx, client, filters, start_time, end_time, max_items, token
            ),
            False,
        ),
        'list_automation_event_steps': (
            'automation_event_steps',
            lambda client, token: _collect_automation_event_steps(
                ctx, client, str(event_id), max_items, token
            ),
            True,
        ),
        'list_automation_event_summaries': (
            'automation_event_summaries',
            lambda client, token: _collect_automation_event_summaries(
                ctx, client, filters, start_date, end_date, max_items, token
            ),
            False,
        ),
        'list_recommended_actions': (
            'recommended_actions',
            lambda client, token: _collect_recommended_actions(
                ctx, client, filters, max_items, token
            ),
            False,
        ),
        'list_recommended_action_summaries': (
            'recommended_action_summaries',
            lambda client, token: _collect_recommended_action_summaries(
                ctx, client, filters, max_items, token
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
                max_items,
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
                max_items,
                token,
            ),
            False,
        ),
    }

    spec = global_handlers.get(operation)
    if spec is None:
        return _validation_error(
            operation,
            {'provided_operation': operation, 'valid_operations': VALID_OPERATIONS},
            f'Unsupported operation: {operation}. Valid operations: {", ".join(VALID_OPERATIONS)}.',
        )

    list_key, collect, not_found_is_empty = spec
    return await _run_multi_region_list(
        ctx, operation, list_key, regions_tokens, collect, not_found_is_empty
    )


def _partition_resource_not_found_errors(
    region_errors: Dict[str, Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Separate not-found outcomes from other regional errors."""
    regions_not_found = [
        region
        for region, error in region_errors.items()
        if error.get('error_type') == _RESOURCE_NOT_FOUND_ERROR_TYPE
    ]
    other_errors = {
        region: error
        for region, error in region_errors.items()
        if error.get('error_type') != _RESOURCE_NOT_FOUND_ERROR_TYPE
    }
    return other_errors, regions_not_found


async def _run_multi_region_list(
    ctx: Context,
    operation: str,
    list_key: str,
    regions_tokens: Dict[str, Optional[str]],
    collect: Callable[
        [Any, Optional[str]], Awaitable[Tuple[List[Dict[str, Any]], Dict[str, Any]]]
    ],
    not_found_is_empty: bool = False,
) -> Dict[str, Any]:
    """Run and merge a regional list operation.

    Each region pages independently, so `max_items` applies per region. The regional
    service tokens are bundled into one opaque token by the regional fan-out helpers.
    """
    region_paginations: Dict[str, Dict[str, Any]] = {}

    async def worker(
        region: str, token: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        client = await asyncio.to_thread(create_compute_optimizer_automation_client, region)
        items, pagination = await collect(client, token)
        region_paginations[region] = pagination
        return items, pagination.get('next_token')

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
            error_type=_RESOURCE_NOT_FOUND_ERROR_TYPE,
            operation=operation,
            service=_SERVICE_NAME,
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
        retry_strategy, hint = _multi_region_guidance(region_errors, regions_not_found)
        return format_response(
            'error',
            data,
            message,
            error_type=_multi_region_error_type(region_errors, regions_not_found),
            operation=operation,
            service=_SERVICE_NAME,
            retry_strategy=retry_strategy,
            hint=hint,
        )

    # A region that returned not found does not hold the resource, so a single successful
    # region is where it was found.
    lookup: Dict[str, Any] = {}
    if not_found_is_empty:
        if successful_regions == 1:
            lookup['found_in_region'] = outcomes.successful_regions[0]
        if regions_not_found:
            lookup['regions_not_found'] = regions_not_found

    return await _finalize_multi_region_list_response(
        ctx,
        operation,
        list_key,
        outcomes.items,
        list(regions_tokens),
        outcomes.next_tokens,
        {region: region_paginations[region] for region in outcomes.successful_regions},
        region_errors,
        lookup,
    )


async def _finalize_multi_region_list_response(
    ctx: Context,
    operation: str,
    list_key: str,
    items: List[Dict[str, Any]],
    regions_queried: List[str],
    region_next_tokens: Dict[str, str],
    region_paginations: Dict[str, Dict[str, Any]],
    region_errors: Dict[str, Dict[str, Any]],
    lookup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a merged multi-region list response, offloading to SQL when large."""
    offload_metadata: Dict[str, Any] = {'regions_queried': regions_queried, **(lookup or {})}
    if region_errors:
        offload_metadata['region_errors'] = region_errors
    response_data: Dict[str, Any] = {list_key: items, **offload_metadata}

    response_data = await convert_response_if_needed(
        ctx,
        with_pagination(
            response_data,
            _merge_region_paginations(
                len(items), region_next_tokens, region_paginations, region_errors
            ),
        ),
        f'compute_optimizer_automation_{operation}',
        **offload_metadata,
    )
    return format_response('success', response_data)


def _merge_region_paginations(
    items_returned: int,
    region_next_tokens: Dict[str, str],
    region_paginations: Dict[str, Dict[str, Any]],
    region_errors: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Combine each region's pagination block into one for the merged response.

    The merged result is partial when any region is, or when a region failed outright.
    Regional service tokens are bundled into one opaque token. A region cut short by a
    failed page keeps its own warning, since it says whether a continuation can retry
    that page. A region that failed outright has no token, so the warning says to query
    it again on its own. ``has_more`` is true only when there is a token to continue
    with, so a result whose only gap is a failed region is partial with ``has_more``
    false.
    """
    partial_regions = [
        region
        for region, pagination in region_paginations.items()
        if not pagination.get('complete_dataset', True)
    ]
    failed_regions = sorted(region_errors or {})
    incomplete = bool(partial_regions or failed_regions)
    next_token = encode_regional_next_token(region_next_tokens) if region_next_tokens else None
    merged: Dict[str, Any] = {
        'complete_dataset': not incomplete,
        'has_more': next_token is not None,
        'next_token': next_token,
        'items_returned': items_returned,
    }
    if incomplete:
        warning = partial_data_warning(items_returned)
        if failed_regions:
            warning += (
                f' Regions {", ".join(failed_regions)} failed (see region_errors) and are not '
                'in next_token; call again with only those regions, without next_token.'
            )
        for region in partial_regions:
            pagination = region_paginations[region]
            regional_warning = pagination.get('warning')
            if regional_warning and regional_warning != partial_data_warning(
                pagination.get('items_returned', 0)
            ):
                warning += f' Region {region}: {regional_warning}'
        merged['warning'] = warning
    return merged


async def _get_automation_event_multi_region(
    ctx: Context, event_id: str, regions: List[str]
) -> Dict[str, Any]:
    """Locate an automation event by ID across the requested regions."""

    async def worker(region: str, request_event_id: str) -> Optional[Dict[str, Any]]:
        client = await asyncio.to_thread(create_compute_optimizer_automation_client, region)
        return await asyncio.to_thread(client.get_automation_event, eventId=request_event_id)

    await ctx.info(f'Searching {len(regions)} region(s) for automation event {event_id}')
    outcomes = await fan_out_regions(
        dict.fromkeys(regions, event_id),
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
                    'regions_queried': list(regions),
                },
            )

    data: Dict[str, Any] = {'event_id': event_id, 'regions_queried': list(regions)}
    region_errors, regions_not_found = _partition_resource_not_found_errors(outcomes.errors)
    if region_errors:
        data['region_errors'] = region_errors
        data['regions_not_found'] = regions_not_found
        retry_strategy, hint = _multi_region_guidance(region_errors, regions_not_found)
        return format_response(
            'error',
            data,
            f'Could not determine whether automation event {event_id} exists because '
            f'{len(region_errors)} of {len(regions)} region(s) could not be searched. '
            'Review region_errors and follow retry_strategy.',
            error_type=_multi_region_error_type(region_errors, regions_not_found),
            operation='get_automation_event',
            service=_SERVICE_NAME,
            retry_strategy=retry_strategy,
            hint=hint,
        )
    return format_response(
        'error',
        data,
        f'Automation event {event_id} was not found in any of the {len(regions)} '
        'region(s) queried.',
        error_type=_RESOURCE_NOT_FOUND_ERROR_TYPE,
        operation='get_automation_event',
        service=_SERVICE_NAME,
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
        return _validation_error(
            operation,
            {'operation': operation, 'missing_parameters': missing},
            f'Missing required parameter(s) for {operation}: {", ".join(missing)}.',
        )

    return None


def _resolve_requested_regions(
    operation: str, regions: Optional[List[str]]
) -> Tuple[List[str], Optional[Dict[str, Any]]]:
    """Normalize the requested `regions` list, or return a validation response.

    Duplicates collapse while preserving order. An empty or omitted list means a single
    call to the default region.

    Args:
        operation: The requested operation.
        regions: The raw `regions` value supplied by the caller, if any.

    Returns:
        The deduplicated regions and None, or an empty list and an error response.
    """
    if not regions:
        return [], None

    if isinstance(regions, str) or not isinstance(regions, (list, tuple)):
        return [], _validation_error(
            operation,
            {'operation': operation, 'parameter': 'regions'},
            'The regions parameter must be a list of AWS region names, e.g. '
            '["us-east-1", "eu-west-1"].',
        )

    if any(not isinstance(region, str) or not region.strip() for region in regions):
        return [], _validation_error(
            operation,
            {'operation': operation, 'parameter': 'regions', 'regions': list(regions)},
            'Every entry in regions must be a non-empty AWS region name.',
        )

    deduplicated = list(dict.fromkeys(region.strip() for region in regions))

    if operation in _SINGLE_REGION_OPERATIONS and len(deduplicated) > 1:
        return [], _validation_error(
            operation,
            {
                'operation': operation,
                'parameter': 'regions',
                'regions': deduplicated,
                'account_global_operations': sorted(_SINGLE_REGION_OPERATIONS),
            },
            f'{operation} returns account-global data and accepts at most one region; '
            f'{len(deduplicated)} were provided. Pass a single region or omit regions.',
        )

    return deduplicated, None


def _validate_parseable_params(
    operation: str,
    start_time: Optional[str],
    end_time: Optional[str],
    rule_type: Optional[str],
    recommended_action_types: Optional[str],
    organization_scope: Optional[str],
    criteria: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Validate structured operation inputs before client creation or fan-out.

    A preview request is checked against the botocore input shape, so a bad criteria or
    scope shape fails once here instead of once per region.

    Returns:
        An error response for an OrganizationRule preview without organization_scope,
        otherwise None.

    Raises:
        ValueError: If a datetime or JSON input cannot be parsed.
        ParamValidationError: If a preview request does not match the botocore input shape.
    """
    if operation == 'list_automation_events':
        if start_time:
            _parse_datetime(start_time, 'start_time')
        if end_time:
            _parse_datetime(end_time, 'end_time')

    if operation in _PREVIEW_API_NAMES:
        request = _rule_preview_request(
            str(rule_type), str(recommended_action_types), organization_scope, criteria
        )
        # organizationScope is optional in the model, but AWS rejects an OrganizationRule
        # without it in every region.
        if rule_type == 'OrganizationRule' and 'organizationScope' not in request:
            return _validation_error(
                operation,
                {'operation': operation, 'parameter': 'organization_scope'},
                'An OrganizationRule preview requires organization_scope, e.g. '
                '{"accountIds": ["111122223333"]}. Use rule_type AccountRule to preview only '
                'the calling account.',
            )
        input_shape = _preview_input_shapes().get(operation)
        if input_shape is not None:
            report = ParamValidator().validate(request, input_shape)
            if report.has_errors():
                raise ParamValidationError(report=report.generate_report())

    return None


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
        return _validation_error(
            operation,
            {'operation': operation, 'filters': filters},
            f'Invalid JSON for filters parameter: {e}',
        )

    if not isinstance(parsed, list):
        return _validation_error(
            operation,
            {'operation': operation, 'filters': filters},
            'The filters parameter must be a JSON array of {name, values} objects.',
        )

    invalid = [
        item.get('name')
        for item in parsed
        if isinstance(item, dict) and item.get('name') not in valid_names
    ]
    if invalid:
        return _validation_error(
            operation,
            {
                'operation': operation,
                'invalid_filter_names': invalid,
                'valid_filter_names': valid_names,
            },
            f'Invalid filter name(s) for {operation}: {", ".join(str(n) for n in invalid)}. '
            f'Valid filter names: {", ".join(valid_names)}.',
        )

    return None
