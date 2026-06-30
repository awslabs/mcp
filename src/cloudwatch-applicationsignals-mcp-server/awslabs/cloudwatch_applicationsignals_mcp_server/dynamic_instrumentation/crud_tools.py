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
"""MCP tool entrypoints for create/list/get/delete instrumentation operations."""

from . import application_signals_gateway as gateway
from .capture import CaptureLimits, CodeCapture
from .constants import SNAPSHOT_SIGNAL_TYPE
from .crud_rendering import (
    _format_batch_delete_response,
    render_create_success_message,
    render_get_instrumentation_output,
    render_list_instrumentations_output,
)
from .location import parse_create_inputs, parse_lookup_inputs
from .validation import (
    _format_code_location_troubleshooting,
    normalize_instrumentation_type,
    validate_capture_names,
    validate_probe_constraints,
)
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def create_instrumentation(
    instrumentation_type: str,
    service: str,
    environment: str,
    language: Optional[str] = None,
    file_path: Optional[str] = None,
    code_unit: Optional[str] = None,
    class_name: Optional[str] = None,
    method_name: Optional[str] = None,
    line_number: Optional[int] = None,
    capture_arguments: Optional[List[str]] = None,
    capture_return: Optional[bool] = None,
    capture_stack_trace: Optional[bool] = None,
    capture_locals: Optional[List[str]] = None,
    max_hits: Optional[int] = None,
    max_string_length: Optional[int] = None,
    max_collection_width: Optional[int] = None,
    max_collection_depth: Optional[int] = None,
    max_stack_frames: Optional[int] = None,
    max_stack_trace_size: Optional[int] = None,
    max_object_depth: Optional[int] = None,
    max_fields_per_object: Optional[int] = None,
    attribute_filters: Optional[List[Dict[str, str]]] = None,
    description: str = 'MCP dynamic instrumentation',
    ttl_hours: Optional[int] = None,
) -> str:
    """Create a dynamic instrumentation configuration for BREAKPOINT or PROBE.

    This is the main creation entrypoint for the MCP server. BREAKPOINT and PROBE
    create code-based instrumentation and require an explicit code location. Set
    capture_arguments for method/function-level targets and capture_locals for
    line-level targets.

    **Primary RCA use — capture the runtime values that telemetry and source code
    cannot show.** Reach for this tool when an incident's stack trace tells you WHERE
    an exception threw but not WHY: the exception message is a generic symptom
    (`/ by zero`, NullPointerException, IndexOutOfBoundsException, ClassCastException),
    only a subset of requests fail, and the deciding value lives in runtime state that
    no span, log, metric, or trace recorded — a downstream response body field, a DB
    row, a cache entry, a method argument, or a local variable. Source code only
    reveals the code path, not which live input took it; a BREAKPOINT at the throwing
    line capturing the relevant arguments/locals records the actual values on the next
    failing request, with no redeploy and no added logging. This converts a
    source-only hypothesis ("this divisor could be zero" / "this field could be null")
    into a confirmed root cause backed by the exact runtime value that triggered the
    failure. After the breakpoint is ACTIVE and a failing request hits it, read the
    captured state with `get_sample_snapshot_for_breakpoint`.

    Args:
        instrumentation_type: BREAKPOINT or PROBE. PROBE is method/function-level only
            (no line_number) and is not supported for JavaScript. Unlike BREAKPOINT,
            PROBE has no max_hits cap — it fires on every hit, which makes it suited to
            long-running observation/monitoring without worrying about hitting a limit.
            The trade-off: a PROBE never expires on its own, so you must delete it
            explicitly when done.
        service: Backend service identifier used by the AWS API.
        environment: Backend environment identifier used by the AWS API.
        language: Required for BREAKPOINT/PROBE code instrumentation.
            Typically Python or Java.
        file_path: Required for BREAKPOINT/PROBE.
        code_unit: Module/package name for code instrumentation.
            For Python, use the dotted runtime import path for the defining module,
            or "__main__" only when the target file is executed directly as the
            process entry script.
        class_name: Optional class name for class-based targets. Java should use the simple class name only.
        method_name: Optional function or method name for method-level instrumentation.
        line_number: Optional 1-based line number for line-level instrumentation.
        capture_arguments: A list of argument names to capture, for method/function-level
            instrumentation (when line_number is not set). MCP does not infer argument names
            automatically. Provide explicit names; an empty list and the wildcard "*" are
            rejected. Omit to capture no arguments.
        capture_return: Whether to capture return values for code instrumentation. Defaults to enabled.
        capture_stack_trace: Whether to capture stack traces for code instrumentation. Defaults to enabled.
        capture_locals: A list of local variable names to capture, for line-level
            instrumentation (when line_number is set). MCP does not infer variable names
            automatically. Provide explicit names; an empty list and the wildcard "*" are
            rejected. Omit to capture no locals.
        max_hits: Optional capture limit for maximum number of hits. Applies to BREAKPOINT
            only; PROBE has no max_hits (it fires on every hit) and the value is ignored.
        max_string_length: Optional capture limit for string truncation.
        max_collection_width: Optional capture limit for collection width.
        max_collection_depth: Optional capture limit for nested collection depth.
        max_stack_frames: Optional capture limit for stack frame count.
        max_stack_trace_size: Optional capture limit for stack trace size.
        max_object_depth: Optional capture limit for object traversal depth.
        max_fields_per_object: Optional capture limit for object field count.
        attribute_filters: Optional list of resource-attribute filter groups that scope
            which service instances the instrumentation applies to. Each group is a
            dict of OpenTelemetry resource-attribute names to exact-match values
            (e.g. {"service.version": "1.2.0", "deployment.environment": "prod"}).
            Matching is exact (no wildcards/patterns); conditions are AND-ed within a
            group and groups are OR-ed together. Up to 10 groups; keys and values must
            be 1-50 and 1-100 characters respectively. Omit to apply to all instances.
        description: Free-form description stored with the instrumentation. Must be 50 characters or fewer.
        ttl_hours: Optional expiration duration in hours. Converted to an absolute UTC
            timestamp. Ignored for PROBE — a PROBE does not expire on its own and must be
            deleted explicitly, so set up cleanup accordingly.

    Notes:
        - BREAKPOINT/PROBE require `language` and `file_path`.
        - For Python, set `code_unit` to the dotted runtime import path for
          the module that defines the target code, such as
          `services.billing`.
        - For Python, do not use a filename or filesystem path as `code_unit`.
        - For Python, use `code_unit="__main__"` only when the target file
          is executed directly as the process entry script.
        - For Java, set `code_unit` to the package name and keep `class_name` as the simple class name only.
        - `line_number` is only for line-level breakpoints and must be 1-based.
        - Target an executable statement when setting `line_number`. Python/Java ignore a
          non-executable line (blank/comment/decorator/signature) and the breakpoint never
          fires; JavaScript slides the breakpoint to the next parseable line. Choose the
          line deliberately.
        - PROBE is method/function-level only: not supported for JavaScript, and
          `line_number` is ignored.
        - PROBE has no `max_hits` and fires on every hit (unlike BREAKPOINT). This makes
          it suited to long-running observation/monitoring without worrying about a hit
          limit — but a PROBE does not expire on its own (`ttl_hours` is ignored), so you
          must delete it explicitly when you are done.
        - `capture_arguments` and `capture_locals` reject `["*"]` and empty lists; omit to capture none.
        - `SignalType` is always SNAPSHOT.
        - `description` must be 50 characters or fewer.
        - Inspect the source file directly before calling this tool — choose `code_unit`,
          `capture_arguments`, and method/class names explicitly.

    Returns:
        A human-readable success or failure message. Success responses include the
        created LocationHash, resolved location details, and a delete hint.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error

    probe_error = validate_probe_constraints(normalized_type, language, line_number)
    if probe_error:
        return probe_error

    location, location_error = parse_create_inputs(
        normalized_type=normalized_type,
        language=language,
        file_path=file_path,
        code_unit=code_unit,
        class_name=class_name,
        method_name=method_name,
        line_number=line_number,
    )
    if location_error:
        return location_error
    if location is None:
        # Defensive: parsers return (loc, None) or (None, error_text). This
        # branch should be unreachable, but we return a user-facing error
        # string (not ``raise``) so the tool's "always returns a string"
        # contract holds even if a future parser bug fires this path.
        return 'ERROR: Internal error resolving location. Please report this issue.'

    location_troubleshooting = _format_code_location_troubleshooting(
        language=language,
        file_path=file_path,
        code_unit=code_unit,
        class_name=class_name,
        method_name=method_name,
        line_number=line_number,
    )

    capture_arguments_error = validate_capture_names('capture_arguments', capture_arguments)
    if capture_arguments_error:
        return capture_arguments_error
    capture_locals_error = validate_capture_names('capture_locals', capture_locals)
    if capture_locals_error:
        return capture_locals_error

    # Line-level instrumentation (line_number set) fires mid-function, where only
    # locals carry data — arguments/return values are call-boundary concepts that
    # do not apply. A line-level config without capture_locals would capture
    # nothing useful, so require it. (JavaScript is always line-level per its
    # location rules, so this requirement always applies to JavaScript.)
    is_line_level = line_number is not None
    if is_line_level and not capture_locals:
        return (
            'ERROR: line-level instrumentation (line_number set) requires capture_locals.\n'
            'At a specific line, only local variables carry data — arguments and return '
            'values apply to method/function-level targets (no line_number).\n'
            'Provide capture_locals=[...] with the local variable names to capture.'
        )

    code_capture_return = True if capture_return is None else capture_return
    code_capture_stack_trace = True if capture_stack_trace is None else capture_stack_trace
    code_capture_locals = capture_locals

    capture = CodeCapture(
        capture_return=code_capture_return,
        capture_stack_trace=code_capture_stack_trace,
        capture_arguments=capture_arguments,
        capture_locals=code_capture_locals,
        limits=CaptureLimits(
            max_hits=max_hits,
            max_string_length=max_string_length,
            max_collection_width=max_collection_width,
            max_collection_depth=max_collection_depth,
            max_stack_frames=max_stack_frames,
            max_stack_trace_size=max_stack_trace_size,
            max_object_depth=max_object_depth,
            max_fields_per_object=max_fields_per_object,
        ),
    )

    target_desc = location.describe()

    request_kwargs: Dict[str, Any] = {
        'InstrumentationType': normalized_type,
        'Service': service,
        'Environment': environment,
        'SignalType': SNAPSHOT_SIGNAL_TYPE,
        'Location': location.to_api_payload(),
        'CaptureConfiguration': capture.to_api_payload(),
        'Description': description,
    }
    if ttl_hours is not None:
        request_kwargs['ExpiresAt'] = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    if attribute_filters:
        request_kwargs['AttributeFilters'] = attribute_filters

    try:
        response = gateway.call('create_instrumentation_configuration', **request_kwargs)
    except gateway.GatewayError as err:
        return gateway.render_error(
            err,
            action=f'create {normalized_type} instrumentation',
            attempted_label='ATTEMPTED CONFIGURATION:',
            attempted={
                'Type': normalized_type,
                'Target': target_desc,
                'Service': service,
                'Environment': environment,
            },
            possible_causes=[
                'AWS credentials missing or scoped to a different account',
                'Invalid service or environment identifier',
                'Instrumentation already exists at this location',
                'Invalid location/capture payload',
                'AWS API endpoint not accessible',
            ],
            troubleshooting=[
                'Verify AWS credentials: aws configure list',
                'Check service name and environment match your deployment',
                'Try listing existing instrumentations with list_instrumentations',
            ],
            trailer=location_troubleshooting,
        )

    return render_create_success_message(
        response=response,
        normalized_type=normalized_type,
        service=service,
        environment=environment,
        location=location,
        ttl_hours=ttl_hours,
        capture_arguments=capture_arguments,
        code_capture_locals=code_capture_locals,
        is_line_level=is_line_level,
        code_capture_return=code_capture_return,
        code_capture_stack_trace=code_capture_stack_trace,
        max_hits=max_hits,
        max_string_length=max_string_length,
        max_collection_width=max_collection_width,
        max_collection_depth=max_collection_depth,
        max_stack_frames=max_stack_frames,
        max_stack_trace_size=max_stack_trace_size,
        max_object_depth=max_object_depth,
        max_fields_per_object=max_fields_per_object,
        attribute_filters=attribute_filters,
    )


def list_instrumentations(
    service: str,
    environment: str,
    instrumentation_type: str,
    synced_at: Optional[str] = None,
    max_results: int = 100,
    next_token: Optional[str] = None,
) -> str:
    """List active instrumentation configurations for one service, environment, and type.

    Args:
        service: Backend service identifier.
        environment: Backend environment identifier.
        instrumentation_type: BREAKPOINT or PROBE.
        synced_at: Optional AWS pagination/synchronization cursor timestamp.
        max_results: Maximum number of configurations to request. Defaults to 100.
        next_token: Optional AWS pagination token from a previous response.

    Returns:
        A human-readable list of configurations with location details, capture
        settings, timing metadata, and pagination guidance when more results exist.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error

    request_kwargs: Dict[str, Any] = {
        'Service': service,
        'Environment': environment,
        'InstrumentationType': normalized_type,
    }
    if synced_at:
        request_kwargs['SyncedAt'] = synced_at
    if max_results != 100:
        request_kwargs['MaxResults'] = max_results
    if next_token:
        request_kwargs['NextToken'] = next_token

    try:
        data = gateway.call('list_instrumentation_configurations', **request_kwargs)
    except gateway.GatewayError as err:
        return gateway.render_error(
            err,
            action='list instrumentations',
            attempted={
                'Service': service,
                'Environment': environment,
                'InstrumentationType': normalized_type,
            },
        )

    return render_list_instrumentations_output(
        data=data,
        normalized_type=normalized_type,
        service=service,
        environment=environment,
    )


def batch_delete_instrumentations_by_scope(
    service: str,
    environment: str,
    instrumentation_type: str,
) -> str:
    """Batch delete instrumentation configurations by scope.

    This deletes all configurations that match the provided service, environment,
    and instrumentation type.

    Args:
        service: Backend service identifier.
        environment: Backend environment identifier.
        instrumentation_type: BREAKPOINT or PROBE.

    Returns:
        A human-readable batch delete summary including deleted count, successful
        deletions, and any per-item errors returned by the backend.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error

    deletion_target = {
        'Scope': {
            'Service': service,
            'Environment': environment,
            'InstrumentationType': normalized_type,
        }
    }

    try:
        data = gateway.call(
            'batch_delete_instrumentation_configurations',
            DeletionTarget=deletion_target,
        )
    except gateway.GatewayError as err:
        return gateway.render_error(
            err,
            action='batch delete instrumentation configurations (scope mode)',
            attempted={
                'Service': service,
                'Environment': environment,
                'InstrumentationType': normalized_type,
            },
        )

    return _format_batch_delete_response(
        mode='Scope',
        data=data,
        instrumentation_type=normalized_type,
        service=service,
        environment=environment,
    )


def batch_delete_instrumentations_by_arns(
    resource_arns: List[str],
    instrumentation_type: str,
) -> str:
    """Batch delete instrumentation configurations by explicit resource ARN list.

    Args:
        resource_arns: One to fifty instrumentation resource ARNs.
        instrumentation_type: BREAKPOINT or PROBE.

    Notes:
        - The request is rejected when `resource_arns` is empty.
        - The request is rejected when more than 50 ARNs are provided.
        - All ARN values must be non-empty strings.

    Returns:
        A human-readable batch delete summary including deleted count, successful
        deletions, and any per-item errors returned by the backend.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error
    if not resource_arns:
        return 'ERROR: resource_arns must contain at least one ARN.'
    if len(resource_arns) > 50:
        return 'ERROR: resource_arns can include at most 50 ARNs per request.'

    invalid_arns = [arn for arn in resource_arns if not isinstance(arn, str) or not arn.strip()]
    if invalid_arns:
        return 'ERROR: resource_arns must contain non-empty ARN strings only.'

    deletion_target = {
        'ResourceArns': {
            'ResourceArns': resource_arns,
            'InstrumentationType': normalized_type,
        }
    }

    try:
        data = gateway.call(
            'batch_delete_instrumentation_configurations',
            DeletionTarget=deletion_target,
        )
    except gateway.GatewayError as err:
        return gateway.render_error(
            err,
            action='batch delete instrumentation configurations (resource ARN mode)',
            attempted={
                'InstrumentationType': normalized_type,
                'ResourceArnCount': len(resource_arns),
            },
        )

    return _format_batch_delete_response(
        mode='ResourceArns',
        data=data,
        instrumentation_type=normalized_type,
    )


def _render_location_identifier_help(action: str) -> str:
    return f"""ERROR: Must provide one of:
- location_hash
- language + file_path (for code locations)

Usage:
1. {action} by hash:
   {action}_instrumentation(location_hash="abc123...")

2. {action} by code location:
   {action}_instrumentation(language="Python", file_path="/app/file.py", ...)"""


def delete_instrumentation(
    service: str,
    environment: str,
    instrumentation_type: str,
    location_hash: Optional[str] = None,
    language: Optional[str] = None,
    file_path: Optional[str] = None,
    code_unit: Optional[str] = None,
    class_name: Optional[str] = None,
    method_name: Optional[str] = None,
    line_number: Optional[int] = None,
) -> str:
    """Delete a single instrumentation configuration.

    The target can be resolved by `location_hash` or by a full location
    description. The target can be resolved by `location_hash` or by a full code
    location description.

    Args:
        service: Backend service identifier.
        environment: Backend environment identifier.
        instrumentation_type: BREAKPOINT or PROBE.
        location_hash: Preferred identifier for an existing configuration.
        language: Code language for code-location lookup.
        file_path: Code file path for code-location lookup.
        code_unit: Optional module/package name for code-location lookup.
        class_name: Optional class name for code-location lookup.
        method_name: Optional function/method name for code-location lookup.
        line_number: Optional 1-based line number for code-location lookup.

    Returns:
        A human-readable success or failure message describing the deletion target
        and troubleshooting guidance when lookup or deletion fails.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error

    location, location_error = parse_lookup_inputs(
        normalized_type=normalized_type,
        location_hash=location_hash,
        language=language,
        file_path=file_path,
        code_unit=code_unit,
        class_name=class_name,
        method_name=method_name,
        line_number=line_number,
        allow_code_location_lookup=True,
    )
    if location_error:
        if 'missing location identifier input' in location_error:
            return _render_location_identifier_help('delete')
        return f'ERROR: {location_error}'
    if location is None:
        # Defensive: parsers return (loc, None) or (None, error_text). This
        # branch should be unreachable, but we return a user-facing error
        # string (not ``raise``) so the tool's "always returns a string"
        # contract holds even if a future parser bug fires this path.
        return 'ERROR: Internal error resolving location. Please report this issue.'
    target_desc = location.describe()

    try:
        gateway.call(
            'delete_instrumentation_configuration',
            InstrumentationType=normalized_type,
            Service=service,
            Environment=environment,
            SignalType=SNAPSHOT_SIGNAL_TYPE,
            LocationIdentifier=location.to_identifier(),
        )
    except gateway.GatewayError as err:
        return gateway.render_error(
            err,
            action=f'delete {normalized_type} instrumentation',
            attempted_label='ATTEMPTED TO DELETE:',
            attempted={
                'Target': target_desc,
                'Service': service,
                'Environment': environment,
            },
            possible_causes=[
                "Instrumentation doesn't exist at this location",
                "Location parameters don't match exactly",
                'Wrong service or environment identifier',
                'Already deleted',
            ],
            troubleshooting=['Use list_instrumentations to see exact configuration details'],
        )

    return f"""Successfully deleted {normalized_type} instrumentation

Target: {target_desc}
Service: {service}
Environment: {environment}

TIP: Use list_instrumentations to verify removal."""


def get_instrumentation(
    service: str,
    environment: str,
    instrumentation_type: str,
    location_hash: Optional[str] = None,
    language: Optional[str] = None,
    file_path: Optional[str] = None,
    code_unit: Optional[str] = None,
    class_name: Optional[str] = None,
    method_name: Optional[str] = None,
    line_number: Optional[int] = None,
) -> str:
    """Get the full backend configuration for a single instrumentation target.

    The target can be resolved by `location_hash` or by a full location
    description. The target can be resolved by `location_hash` or by a full code
    location description.

    Args:
        service: Backend service identifier.
        environment: Backend environment identifier.
        instrumentation_type: BREAKPOINT or PROBE.
        location_hash: Preferred identifier for an existing configuration.
        language: Code language for code-location lookup.
        file_path: Code file path for code-location lookup.
        code_unit: Optional module/package name for code-location lookup.
        class_name: Optional class name for code-location lookup.
        method_name: Optional function/method name for code-location lookup.
        line_number: Optional 1-based line number for code-location lookup.

    Returns:
        A human-readable configuration report including location details, capture
        configuration, attribute filters, and backend metadata such as ARN and timestamps.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error

    location, location_error = parse_lookup_inputs(
        normalized_type=normalized_type,
        location_hash=location_hash,
        language=language,
        file_path=file_path,
        code_unit=code_unit,
        class_name=class_name,
        method_name=method_name,
        line_number=line_number,
        allow_code_location_lookup=True,
    )
    if location_error:
        if 'missing location identifier input' in location_error:
            return _render_location_identifier_help('get')
        return f'ERROR: {location_error}'
    if location is None:
        # Defensive: parsers return (loc, None) or (None, error_text). This
        # branch should be unreachable, but we return a user-facing error
        # string (not ``raise``) so the tool's "always returns a string"
        # contract holds even if a future parser bug fires this path.
        return 'ERROR: Internal error resolving location. Please report this issue.'
    target_desc = location.describe()

    try:
        data = gateway.call(
            'get_instrumentation_configuration',
            InstrumentationType=normalized_type,
            Service=service,
            Environment=environment,
            SignalType=SNAPSHOT_SIGNAL_TYPE,
            LocationIdentifier=location.to_identifier(),
        )
    except gateway.GatewayError as err:
        return gateway.render_error(
            err,
            action='get instrumentation',
            attempted_label='ATTEMPTED TO RETRIEVE:',
            attempted={
                'Target': target_desc,
                'Service': service,
                'Environment': environment,
            },
            possible_causes=[
                "Instrumentation doesn't exist at this location",
                "Location parameters don't match exactly",
                'Wrong service or environment identifier',
            ],
            troubleshooting=['Use list_instrumentations to see all active instrumentations'],
        )

    config = data.get('Configuration', {}) if isinstance(data, dict) else {}
    if not config:
        return f'No instrumentation found for {target_desc}'

    return render_get_instrumentation_output(
        config=config,
        service=service,
        environment=environment,
    )
