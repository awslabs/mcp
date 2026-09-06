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
"""Formatting helpers for CRUD tool responses."""

from .capture import CodeCapture, capture_from_response
from .constants import SNAPSHOT_SIGNAL_TYPE
from .formatting import format_timestamp
from .location import Location, location_from_response, render_location_block
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _render_create_capture_limits(
    max_hits: Optional[int],
    max_string_length: Optional[int],
    max_collection_width: Optional[int],
    max_collection_depth: Optional[int],
    max_stack_frames: Optional[int],
    max_stack_trace_size: Optional[int],
    max_object_depth: Optional[int],
    max_fields_per_object: Optional[int],
) -> str:
    if not any(
        [
            max_hits,
            max_string_length,
            max_collection_width,
            max_collection_depth,
            max_stack_frames,
            max_stack_trace_size,
            max_object_depth,
            max_fields_per_object,
        ]
    ):
        return ''

    output = '\nCAPTURE LIMITS:\n'
    if max_hits:
        output += f'- Max Hits: {max_hits}\n'
    if max_string_length:
        output += f'- Max String Length: {max_string_length}\n'
    if max_collection_width:
        output += f'- Max Collection Width: {max_collection_width}\n'
    if max_collection_depth:
        output += f'- Max Collection Depth: {max_collection_depth}\n'
    if max_stack_frames:
        output += f'- Max Stack Frames: {max_stack_frames}\n'
    if max_stack_trace_size:
        output += f'- Max Stack Trace Size: {max_stack_trace_size}\n'
    if max_object_depth:
        output += f'- Max Object Depth: {max_object_depth}\n'
    if max_fields_per_object:
        output += f'- Max Fields Per Object: {max_fields_per_object}\n'
    return output


def render_create_success_message(
    response: Dict[str, Any],
    normalized_type: str,
    service: str,
    environment: str,
    location: Location,
    ttl_hours: Optional[int],
    capture_arguments: Optional[List[str]],
    code_capture_locals: Optional[List[str]],
    is_line_level: bool,
    code_capture_return: Optional[bool],
    code_capture_stack_trace: Optional[bool],
    max_hits: Optional[int],
    max_string_length: Optional[int],
    max_collection_width: Optional[int],
    max_collection_depth: Optional[int],
    max_stack_frames: Optional[int],
    max_stack_trace_size: Optional[int],
    max_object_depth: Optional[int],
    max_fields_per_object: Optional[int],
    attribute_filters: Optional[List[Dict[str, str]]],
) -> str:
    """Render the success message for a created instrumentation configuration."""
    location_hash = response.get('LocationHash', 'N/A')
    arn = response.get('ARN', 'N/A')
    created_at = format_timestamp(
        response.get('CreatedAt'),
        default=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    )
    actual_expires_at = format_timestamp(response.get('ExpiresAt'), default='')

    success_message = f"""Successfully created {normalized_type} instrumentation

INSTRUMENTATION CREATED:
- Type: {normalized_type}
- Service: {service}
- Environment: {environment}
- SignalType: {SNAPSHOT_SIGNAL_TYPE}
- ARN: {arn}
- CreatedAt: {created_at}
"""

    if actual_expires_at:
        suffix = (
            f' (requested {ttl_hours} hour{"s" if ttl_hours != 1 else ""})'
            if ttl_hours is not None
            else ''
        )
        success_message += f'- Expires: {actual_expires_at}{suffix}\n'
    else:
        success_message += '- Expires: Never (unless deleted)\n'

    success_message += '\nLOCATION:\n'
    success_message += render_location_block(location=location, location_hash=location_hash)
    success_message += '\nCAPTURE CONFIGURATION:\n'

    if not is_line_level:
        if capture_arguments:
            success_message += f'- Arguments: {", ".join(capture_arguments)}\n'
        else:
            success_message += '- Arguments: (none)\n'

    if code_capture_locals:
        success_message += f'- Local Variables: {", ".join(code_capture_locals)}\n'

    if not is_line_level:
        success_message += f'- Return Values: {"Enabled" if code_capture_return else "Disabled"}\n'
    success_message += f'- Stack Traces: {"Enabled" if code_capture_stack_trace else "Disabled"}\n'
    success_message += _render_create_capture_limits(
        max_hits=max_hits,
        max_string_length=max_string_length,
        max_collection_width=max_collection_width,
        max_collection_depth=max_collection_depth,
        max_stack_frames=max_stack_frames,
        max_stack_trace_size=max_stack_trace_size,
        max_object_depth=max_object_depth,
        max_fields_per_object=max_fields_per_object,
    )

    if attribute_filters:
        success_message += (
            f'\nATTRIBUTE FILTERS: {len(attribute_filters)} filter group(s) applied\n'
        )

    if normalized_type == 'PROBE':
        expected_ready = '~10-12 min'
    else:
        expected_ready = '~1-2 min'
    success_message += (
        f'\nNOTE: Allow {expected_ready} before this configuration reports READY. '
        'Status checks immediately after creation may return no events yet — '
        'wait and re-check rather than recreating.\n'
    )

    success_message += (
        f'\nTIP: Use this LocationHash to delete: '
        f'delete_instrumentation(location_hash="{location_hash}")'
    )
    return success_message


def render_list_instrumentations_output(
    data: Dict[str, Any],
    normalized_type: str,
    service: str,
    environment: str,
) -> str:
    """Render the output for a list-instrumentations result."""
    configs = data.get('LatestConfigurations', [])
    next_token_response = data.get('NextToken')

    if not configs:
        return f"""No active {normalized_type} instrumentations found

Service: {service}
Environment: {environment}

TIP: Use create_instrumentation to add instrumentations."""

    output = f"""Active {normalized_type} Instrumentations ({len(configs)} found)

Service: {service}
Environment: {environment}
Synced At: {format_timestamp(data.get('SyncedAt'))}

"""

    for index, config in enumerate(configs, 1):
        cap = capture_from_response(config.get('CaptureConfiguration', {}))

        output += f"""{'=' * 60}
INSTRUMENTATION #{index}
{'=' * 60}
LOCATION:
"""
        output += render_location_block(
            location=location_from_response(config.get('Location', {})),
            location_hash=config.get('LocationHash'),
        )

        output += '\nCAPTURE SETTINGS:\n'
        if isinstance(cap, CodeCapture):
            output += f'- Return: {"Enabled" if cap.capture_return else "Disabled"}\n'
            output += f'- Stack Traces: {"Enabled" if cap.capture_stack_trace else "Disabled"}\n'

            if cap.capture_arguments is None:
                output += '- Arguments: (not set)\n'
            elif cap.capture_arguments:
                output += f'- Arguments: {", ".join(cap.capture_arguments)}\n'
            else:
                output += '- Arguments: (empty list)\n'

            if cap.capture_locals is None:
                output += '- Locals: (not set)\n'
            elif cap.capture_locals:
                output += f'- Locals: {", ".join(cap.capture_locals)}\n'
            else:
                output += '- Locals: (empty list)\n'

            limits = cap.limits
            if not limits.is_empty():
                limit_strs = []
                if limits.max_hits is not None:
                    limit_strs.append(f'MaxHits={limits.max_hits}')
                if limits.max_string_length is not None:
                    limit_strs.append(f'MaxStringLen={limits.max_string_length}')
                if limits.max_collection_width is not None:
                    limit_strs.append(f'MaxCollWidth={limits.max_collection_width}')
                if limit_strs:
                    output += f'- Limits: {", ".join(limit_strs)}\n'
        else:
            output += '- Capture payload could not be parsed.\n'

        output += f"""
TIMING:
- Created: {format_timestamp(config.get('CreatedAt'))}
- Expires: {format_timestamp(config.get('ExpiresAt'), default='Never')}

Description: {config.get('Description', 'N/A')}
ARN: {config.get('ARN', 'N/A')}

"""

    if next_token_response:
        output += (
            f'\nPAGINATION: More results available. Use next_token="{next_token_response}" '
            'to retrieve next page.'
        )

    return output


def render_get_instrumentation_output(
    config: Dict[str, Any],
    service: str,
    environment: str,
) -> str:
    """Render the output for a single get-instrumentation result."""
    cap = capture_from_response(config.get('CaptureConfiguration', {}))

    output = f"""INSTRUMENTATION CONFIGURATION

TYPE: {config.get('InstrumentationType', 'N/A')}
SERVICE: {service}
ENVIRONMENT: {environment}
SIGNAL TYPE: {config.get('SignalType', SNAPSHOT_SIGNAL_TYPE)}

LOCATION:
"""
    output += render_location_block(
        location=location_from_response(config.get('Location', {})),
        location_hash=config.get('LocationHash'),
    )

    output += '\nCAPTURE CONFIGURATION:\n'
    if isinstance(cap, CodeCapture):
        output += f'- Return Values: {"Enabled" if cap.capture_return else "Disabled"}\n'
        output += f'- Stack Traces: {"Enabled" if cap.capture_stack_trace else "Disabled"}\n'
        if cap.capture_arguments is None:
            output += '- Arguments: (not set)\n'
        elif cap.capture_arguments:
            output += f'- Arguments: {", ".join(cap.capture_arguments)}\n'
        else:
            output += '- Arguments: (empty list)\n'
        if cap.capture_locals is None:
            output += '- Local Variables: (not set)\n'
        elif cap.capture_locals:
            output += f'- Local Variables: {", ".join(cap.capture_locals)}\n'
        else:
            output += '- Local Variables: (empty list)\n'

        limits = cap.limits
        if not limits.is_empty():
            output += '\nCAPTURE LIMITS:\n'
            if limits.max_hits is not None:
                output += f'- Max Hits: {limits.max_hits}\n'
            if limits.max_string_length is not None:
                output += f'- Max String Length: {limits.max_string_length}\n'
            if limits.max_collection_width is not None:
                output += f'- Max Collection Width: {limits.max_collection_width}\n'
            if limits.max_collection_depth is not None:
                output += f'- Max Collection Depth: {limits.max_collection_depth}\n'
            if limits.max_stack_frames is not None:
                output += f'- Max Stack Frames: {limits.max_stack_frames}\n'
            if limits.max_stack_trace_size is not None:
                output += f'- Max Stack Trace Size: {limits.max_stack_trace_size}\n'
            if limits.max_object_depth is not None:
                output += f'- Max Object Depth: {limits.max_object_depth}\n'
            if limits.max_fields_per_object is not None:
                output += f'- Max Fields Per Object: {limits.max_fields_per_object}\n'
    else:
        output += '- Capture payload could not be parsed.\n'

    if config.get('AttributeFilters'):
        output += f'\nATTRIBUTE FILTERS: {len(config["AttributeFilters"])} filter group(s)\n'
        for index, filter_group in enumerate(config['AttributeFilters'], 1):
            output += f'  Group {index}: {filter_group}\n'

    output += f"""
METADATA:
- Description: {config.get('Description', 'N/A')}
- Created: {format_timestamp(config.get('CreatedAt'))}
- Expires: {format_timestamp(config.get('ExpiresAt'), default='Never')}
- ARN: {config.get('ARN', 'N/A')}
"""
    return output


def _format_batch_delete_response(
    mode: str,
    data: Dict[str, Any],
    instrumentation_type: str,
    service: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    successful = data.get('SuccessfulDeletions', [])
    errors = data.get('Errors', [])
    deleted_count = data.get('DeletedCount', 0)

    output = f"""BATCH DELETE COMPLETED

Mode: {mode}
InstrumentationType: {instrumentation_type}
DeletedCount: {deleted_count}
SuccessfulDeletions: {len(successful)}
Errors: {len(errors)}
"""
    if service:
        output += f'Service: {service}\n'
    if environment:
        output += f'Environment: {environment}\n'

    if successful:
        output += '\nSUCCESSFUL DELETIONS:\n'
        for index, item in enumerate(successful, 1):
            resource_arn = item.get('ResourceArn')
            signal_type = item.get('SignalType')
            location_hash = item.get('LocationHash')
            if resource_arn:
                output += f'- Item {index}: ResourceArn={resource_arn}\n'
            else:
                output += (
                    f'- Item {index}: SignalType={signal_type or "N/A"} | '
                    f'LocationHash={location_hash or "N/A"}\n'
                )

    if errors:
        output += '\nDELETE ERRORS:\n'
        for index, item in enumerate(errors, 1):
            output += (
                f'- Item {index}: ResourceArn={item.get("ResourceArn", "N/A")} | '
                f'Code={item.get("Code", "N/A")} | '
                f'Message={item.get("Message", "N/A")}\n'
            )

    return output
