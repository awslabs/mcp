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
"""Snapshot payload parsing helpers for snapshot tools."""

import json
import re
from typing import Dict


def _preview_captured_value(captured_value: object) -> object:
    """Return a compact preview for one snapshot CapturedValue."""
    if not isinstance(captured_value, dict):
        return captured_value

    preview: Dict[str, object] = {}
    value_type = captured_value.get('type')
    if value_type not in (None, ''):
        preview['type'] = value_type

    if captured_value.get('is_null') is True:
        preview['is_null'] = True
        return preview

    if 'not_captured_reason' in captured_value:
        preview['not_captured_reason'] = captured_value.get('not_captured_reason')
        return preview

    if 'value' in captured_value:
        preview['value'] = captured_value.get('value')
        if captured_value.get('truncated') is True:
            preview['truncated'] = True
        if 'size' in captured_value:
            preview['size'] = captured_value.get('size')
        return preview

    if isinstance(captured_value.get('fields'), dict):
        fields = captured_value['fields']
        # Expand one level: show primitive field values directly,
        # collapse nested objects to just their type.
        fields_preview: Dict[str, object] = {}
        for fname, fval in fields.items():
            if not isinstance(fval, dict):
                fields_preview[fname] = fval
                continue
            if fval.get('is_null') is True:
                fields_preview[fname] = None
            elif 'not_captured_reason' in fval:
                fields_preview[fname] = f'<{fval["not_captured_reason"]}>'
            elif 'value' in fval:
                fields_preview[fname] = fval['value']
            else:
                # Nested object/collection — show type only
                fields_preview[fname] = f'<{fval.get("type", "object")}>'
        preview['fields_preview'] = fields_preview
        if 'size' in captured_value:
            preview['size'] = captured_value.get('size')
        return preview

    if isinstance(captured_value.get('elements'), list):
        preview['element_count'] = len(captured_value['elements'])
        if captured_value['elements']:
            preview['first_element'] = _preview_captured_value(captured_value['elements'][0])
        return preview

    if isinstance(captured_value.get('entries'), list):
        preview['entry_count'] = len(captured_value['entries'])
        return preview

    return preview or captured_value


def _escape_logs_insights_regex(value: object) -> str:
    """Escape dynamic values for use inside a /.../ CloudWatch Logs Insights regex."""
    return re.escape(str(value)).replace('/', r'\/')


def _escape_logs_insights_string(value: object) -> str:
    """Escape a value for a double-quoted CloudWatch Logs Insights string literal.

    Logs Insights string literals are double-quoted with backslash escaping.
    Escape backslashes first (so the escapes added next are not themselves
    re-escaped), then double-quotes, so an embedded quote cannot terminate the
    literal and inject caller-controlled query syntax. This is distinct from
    ``_escape_logs_insights_regex``, which escapes for ``/.../`` regex context,
    not ``"..."`` literal context.
    """
    return str(value).replace('\\', '\\\\').replace('"', '\\"')


def _parse_snapshot_fields(result: dict) -> dict:
    """Extract key debugging fields from a raw CloudWatch Logs snapshot result.

    Handles the OTLP log record format where:
    - Metadata is in top-level `attributes` (aws.di.*)
    - Resource info is in `resource.attributes` (service.name, deployment.environment —
      the Java agent's autoconfig path may alternatively publish deployment.environment.name)
    - Captures and stack are nested under `body`
    - Trace/span IDs are at root level (`traceId`, `spanId`)
    - Stack frames use `file_path`/`line_number` (not `fileName`/`lineNumber`)
    - Return value key is `return_value` (not `returnValue`)
    """
    message = result.get('@message', '')
    try:
        snapshot_data = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        snapshot_data = {}

    if not isinstance(snapshot_data, dict):
        snapshot_data = {}

    attributes = snapshot_data.get('attributes', {})
    if not isinstance(attributes, dict):
        attributes = {}

    resource = snapshot_data.get('resource', {})
    if not isinstance(resource, dict):
        resource = {}
    resource_attributes = resource.get('attributes', {})
    if not isinstance(resource_attributes, dict):
        resource_attributes = {}

    body = snapshot_data.get('body', {})
    if not isinstance(body, dict):
        body = {}

    location = {
        'class_name': attributes.get('aws.di.class_name'),
        'method_name': attributes.get('aws.di.method_name'),
        'file_path': attributes.get('aws.di.file_path'),
        'code_unit': attributes.get('aws.di.code_unit'),
        'instrumentation_level': attributes.get('aws.di.instrumentation_level'),
        'instrumentation_type': attributes.get('aws.di.instrumentation_type'),
    }

    trace = {
        'traceId': snapshot_data.get('traceId'),
        'spanId': snapshot_data.get('spanId'),
    }

    stack = body.get('stack', [])
    if not isinstance(stack, list):
        stack = []

    captures = body.get('captures', {})
    if not isinstance(captures, dict):
        captures = {}

    entry_capture = captures.get('entry', {})
    if not isinstance(entry_capture, dict):
        entry_capture = {}

    return_capture = captures.get('return', {})
    if not isinstance(return_capture, dict):
        return_capture = {}

    line_captures = captures.get('lines', {})
    if not isinstance(line_captures, dict):
        line_captures = {}

    entry_arguments = entry_capture.get('arguments', {})
    if not isinstance(entry_arguments, dict):
        entry_arguments = {}

    entry_locals = entry_capture.get('locals', {})
    if not isinstance(entry_locals, dict):
        entry_locals = {}

    return_arguments = return_capture.get('arguments', {})
    if not isinstance(return_arguments, dict):
        return_arguments = {}

    return_locals = return_capture.get('locals', {})
    if not isinstance(return_locals, dict):
        return_locals = {}

    return_value = return_capture.get('return_value')
    throwable = return_capture.get('throwable', {})
    if not isinstance(throwable, dict):
        throwable = {}

    line_locals: Dict[str, list[str]] = {}
    line_local_previews: Dict[str, Dict[str, object]] = {}
    line_arguments: Dict[str, list[str]] = {}
    line_argument_previews: Dict[str, Dict[str, object]] = {}
    line_return_values: Dict[str, object] = {}
    line_throwables: Dict[str, object] = {}
    for line_number, line_capture in line_captures.items():
        if not isinstance(line_capture, dict):
            continue
        ln = str(line_number)

        locals_map = line_capture.get('locals', {})
        if isinstance(locals_map, dict) and locals_map:
            line_locals[ln] = list(locals_map.keys())
            line_local_previews[ln] = {
                name: _preview_captured_value(value) for name, value in locals_map.items()
            }

        args_map = line_capture.get('arguments', {})
        if isinstance(args_map, dict) and args_map:
            line_arguments[ln] = list(args_map.keys())
            line_argument_previews[ln] = {
                name: _preview_captured_value(value) for name, value in args_map.items()
            }

        ret_val = line_capture.get('return_value')
        if ret_val is not None:
            line_return_values[ln] = _preview_captured_value(ret_val)

        throwable_val = line_capture.get('throwable')
        if isinstance(throwable_val, dict) and throwable_val:
            line_throwables[ln] = {
                'type': throwable_val.get('type'),
                'message': throwable_val.get('message'),
                'stacktrace_frame_count': (
                    len(throwable_val.get('stacktrace', []))
                    if isinstance(throwable_val.get('stacktrace'), list)
                    else 0
                ),
            }

    duration_ms = attributes.get('aws.di.duration_ms')

    stack_preview = []
    for frame in stack[:5]:
        if not isinstance(frame, dict):
            continue
        stack_preview.append(
            {
                'file_path': frame.get('file_path'),
                'function': frame.get('function'),
                'line_number': frame.get('line_number'),
            }
        )

    def _line_key(value):
        """Order numeric line keys first (by value), non-numeric keys last (lexically).

        Returns a ``(group, sort_value)`` tuple so the two kinds never compare
        across types. A bare ``int(v) if v.isdigit() else v`` key would mix
        ``int`` and ``str`` and raise ``TypeError`` the moment a non-digit key
        appears alongside numeric ones (e.g. a negative line ``'-1'``, since
        ``'-1'.isdigit()`` is ``False``), crashing snapshot parsing.
        """
        text = str(value)
        if text.isdigit():
            return (0, int(text), '')
        return (1, 0, text)

    all_line_numbers = sorted(
        set(line_locals.keys())
        | set(line_arguments.keys())
        | set(line_return_values.keys())
        | set(line_throwables.keys()),
        key=_line_key,
    )

    return {
        '@timestamp': result.get('@timestamp'),
        'snapshot_id': attributes.get('aws.di.snapshot_id'),
        'timeUnixNano': snapshot_data.get('timeUnixNano'),
        'duration_ms': duration_ms,
        'location_hash': attributes.get('aws.di.location_hash'),
        'location': location,
        'trace': trace,
        'stack_preview': stack_preview,
        'stack_frame_count': len(stack),
        'entry_argument_names': list(entry_arguments.keys()),
        'entry_arguments': {
            name: _preview_captured_value(value) for name, value in entry_arguments.items()
        },
        'entry_local_names': list(entry_locals.keys()),
        'entry_locals': {
            name: _preview_captured_value(value) for name, value in entry_locals.items()
        },
        'return_argument_names': list(return_arguments.keys()),
        'return_arguments': {
            name: _preview_captured_value(value) for name, value in return_arguments.items()
        },
        'return_local_names': list(return_locals.keys()),
        'return_locals': {
            name: _preview_captured_value(value) for name, value in return_locals.items()
        },
        'return_value': _preview_captured_value(return_value)
        if return_value is not None
        else None,
        'throwable': (
            {
                'type': throwable.get('type'),
                'message': throwable.get('message'),
                'stacktrace_frame_count': (
                    len(throwable.get('stacktrace', []))
                    if isinstance(throwable.get('stacktrace'), list)
                    else 0
                ),
            }
            if throwable
            else None
        ),
        'line_numbers': all_line_numbers,
        'line_locals': line_locals,
        'line_local_previews': line_local_previews,
        'line_arguments': line_arguments if line_arguments else None,
        'line_argument_previews': line_argument_previews if line_argument_previews else None,
        'line_return_values': line_return_values if line_return_values else None,
        'line_throwables': line_throwables if line_throwables else None,
        'raw_snapshot': snapshot_data,
    }
