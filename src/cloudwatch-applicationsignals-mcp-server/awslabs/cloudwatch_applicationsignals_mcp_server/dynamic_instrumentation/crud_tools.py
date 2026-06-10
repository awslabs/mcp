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
    create code-based instrumentation and require an explicit code location plus
    explicit `capture_arguments`.

    Args:
        instrumentation_type: BREAKPOINT or PROBE.
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
        capture_arguments: Required for BREAKPOINT/PROBE. MCP does not infer argument names automatically.
        capture_return: Whether to capture return values for code instrumentation. Defaults to enabled.
        capture_stack_trace: Whether to capture stack traces for code instrumentation. Defaults to enabled.
        capture_locals: Optional list of local variable names to capture.
        max_hits: Optional capture limit for maximum number of hits.
        max_string_length: Optional capture limit for string truncation.
        max_collection_width: Optional capture limit for collection width.
        max_collection_depth: Optional capture limit for nested collection depth.
        max_stack_frames: Optional capture limit for stack frame count.
        max_stack_trace_size: Optional capture limit for stack trace size.
        max_object_depth: Optional capture limit for object traversal depth.
        max_fields_per_object: Optional capture limit for object field count.
        attribute_filters: Optional attribute filter groups forwarded to the AWS API.
        description: Free-form description stored with the instrumentation. Must be 50 characters or fewer.
        ttl_hours: Optional expiration duration in hours. Converted to an absolute UTC timestamp.

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
        - `capture_arguments=["*"]` is not supported; "*" is ignored if present.
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

    wildcard_removed = False
    if capture_arguments is None:
        return (
            'ERROR: capture_arguments is required for BREAKPOINT/PROBE code instrumentation.\n'
            'MCP does not infer argument names automatically.\n'
            'Inspect the source file directly and re-run with capture_arguments=[...].'
        )

    if '*' in capture_arguments:
        wildcard_removed = True
    capture_arguments = [arg for arg in capture_arguments if arg != '*']

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
        response = gateway.create_instrumentation_configuration(**request_kwargs)
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
        wildcard_removed=wildcard_removed,
        code_capture_locals=code_capture_locals,
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
        data = gateway.list_instrumentation_configurations(**request_kwargs)
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
        data = gateway.batch_delete_instrumentation_configurations(
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
        data = gateway.batch_delete_instrumentation_configurations(
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
        gateway.delete_instrumentation_configuration(
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
        data = gateway.get_instrumentation_configuration(
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
