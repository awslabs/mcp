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
"""Formatting helpers for snapshot tool responses."""

import json
from .constants import resolve_snapshot_log_group
from .snapshot_parsing import _parse_snapshot_fields
from typing import Any, Dict, List, Optional


_RAW_SNAPSHOT_SIZE_THRESHOLD = 10 * 1024  # 10 KB


def render_search_snapshots_for_status_event_output(
    service_name: str,
    environment: str,
    location_hash: str,
    custom_filters: Optional[List[str]],
    start_time_utc: str,
    end_time_utc: str,
    start_epoch: int,
    end_epoch: int,
    query_string: str,
    query_result: Dict[str, Any],
) -> str:
    """Render the snapshot-search response as JSON text."""
    log_group_name = resolve_snapshot_log_group(service_name)
    if query_result['status'] == 'Error':
        return json.dumps(
            {
                'status': 'ERROR',
                'service_name': service_name,
                'environment': environment,
                'log_group_name': log_group_name,
                'location_hash': location_hash,
                'custom_filters': custom_filters if custom_filters else [],
                'start_time_utc': start_time_utc,
                'end_time_utc': end_time_utc,
                'query_string': query_string,
                'error': query_result.get('error', 'Unknown error'),
            },
            indent=2,
        )

    if query_result['status'] == 'Polling Timeout':
        return json.dumps(
            {
                'queryId': query_result.get('queryId'),
                'status': 'TIMEOUT',
                'log_group_name': log_group_name,
                'service_name': service_name,
                'environment': environment,
                'location_hash': location_hash,
                'custom_filters': custom_filters if custom_filters else [],
                'start_time_utc': start_time_utc,
                'end_time_utc': end_time_utc,
                'query_string': query_string,
                'message': (
                    'Query did not complete within the requested timeout. '
                    'Use get-query-results with the returned queryId to retry.'
                ),
            },
            indent=2,
        )

    results = query_result['results']
    snapshot_summaries = []

    for result in results:
        try:
            snapshot_data = json.loads(result.get('@message', '{}'))
        except (json.JSONDecodeError, TypeError):
            snapshot_data = {}
        attributes = snapshot_data.get('attributes', {})
        if not isinstance(attributes, dict):
            attributes = {}
        snapshot_summaries.append(
            {
                '@timestamp': result.get('@timestamp'),
                'snapshot_id': attributes.get('aws.di.snapshot_id'),
                'location_hash': attributes.get('aws.di.location_hash'),
                'traceId': snapshot_data.get('traceId'),
                'spanId': snapshot_data.get('spanId'),
            }
        )

    output = {
        'queryId': query_result.get('queryId'),
        'status': query_result['status'],
        'log_group_name': log_group_name,
        'service_name': service_name,
        'environment': environment,
        'location_hash': location_hash,
        'custom_filters': custom_filters if custom_filters else [],
        'start_time_utc': start_time_utc,
        'end_time_utc': end_time_utc,
        'start_epoch': start_epoch,
        'end_epoch': end_epoch,
        'query_string': query_string,
        'messages': query_result.get('messages', []),
        'snapshot_summaries': snapshot_summaries,
        'results': results,
    }

    return json.dumps(output, indent=2)


def render_get_sample_snapshot_for_breakpoint_output(
    service_name: str,
    environment: str,
    location_hash: str,
    start_time_utc: str,
    end_time_utc: str,
    max_timeout: int,
    query_string: str,
    query_result: Dict[str, Any],
    include_raw: bool = False,
) -> str:
    """Render the sample-snapshot response as JSON text."""
    log_group_name = resolve_snapshot_log_group(service_name)
    if query_result['status'] == 'Error':
        return json.dumps(
            {
                'status': 'ERROR',
                'service_name': service_name,
                'environment': environment,
                'log_group_name': log_group_name,
                'location_hash': location_hash,
                'error': query_result.get('error', 'Unknown error'),
                'query_string': query_string,
            },
            indent=2,
        )

    if query_result['status'] == 'Polling Timeout':
        return json.dumps(
            {
                'status': 'TIMEOUT',
                'queryId': query_result.get('queryId'),
                'service_name': service_name,
                'environment': environment,
                'log_group_name': log_group_name,
                'location_hash': location_hash,
                'message': f'Query did not complete within {max_timeout} seconds.',
                'query_string': query_string,
            },
            indent=2,
        )

    if query_result['status'] != 'Complete':
        return json.dumps(
            {
                'status': query_result['status'],
                'queryId': query_result.get('queryId'),
                'service_name': service_name,
                'environment': environment,
                'log_group_name': log_group_name,
                'location_hash': location_hash,
                'query_string': query_string,
                'messages': query_result.get('messages', []),
            },
            indent=2,
        )

    results = query_result['results']
    if not results:
        return json.dumps(
            {
                'status': 'NO_SNAPSHOTS_FOUND',
                'queryId': query_result.get('queryId'),
                'service_name': service_name,
                'environment': environment,
                'log_group_name': log_group_name,
                'location_hash': location_hash,
                'time_range': {
                    'start': start_time_utc,
                    'end': end_time_utc,
                },
                'message': (
                    'No snapshots found in this window. Suggestions: '
                    '(1) Try an older ACTIVE event timestamp — older events have had more time '
                    'for CloudWatch Logs ingestion. '
                    '(2) If all timestamps fail, wait 1-2 minutes for ingestion delay. '
                    '(3) Verify the breakpoint is still ACTIVE and not DISABLED from max_hits exhaustion.'
                ),
                'query_string': query_string,
            },
            indent=2,
        )

    raw_message = results[0].get('@message', '{}')
    raw_size = len(raw_message.encode('utf-8'))
    use_parsed = raw_size > _RAW_SNAPSHOT_SIZE_THRESHOLD and not include_raw

    if use_parsed:
        parsed = _parse_snapshot_fields(results[0])
        parsed.pop('raw_snapshot', None)
        sample_snapshot = parsed
    else:
        try:
            sample_snapshot = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            sample_snapshot = {}

    output = {
        'status': 'SUCCESS',
        'queryId': query_result.get('queryId'),
        'service_name': service_name,
        'environment': environment,
        'log_group_name': log_group_name,
        'location_hash': location_hash,
        'time_range': {
            'start': start_time_utc,
            'end': end_time_utc,
        },
        'cloudwatch_timestamp': results[0].get('@timestamp'),
    }

    if use_parsed:
        output['note'] = (
            f'Raw snapshot was {raw_size:,} bytes and has been replaced with a '
            'compact parsed summary. To get the full raw snapshot, call this tool '
            'again with include_raw=True.'
        )

    output['sample_snapshot'] = sample_snapshot
    output['field_documentation'] = {
        'attributes.aws.di.snapshot_id': 'Unique snapshot identifier (UUID v4).',
        'timeUnixNano': 'Snapshot timestamp in nanoseconds since Unix epoch.',
        'attributes.aws.di.duration_ms': (
            'Function execution duration in milliseconds. '
            'Present for method-level breakpoints only; absent for line-level.'
        ),
        'resource.attributes.service.name': 'Service name from OTel resource.',
        'resource.attributes.deployment.environment': (
            'Deployment environment from OTel resource (legacy semconv key used by the Python agent '
            "and the Java agent's fallback path). Filter on both this key and "
            'resource.attributes.deployment.environment.name to cover every agent path.'
        ),
        'resource.attributes.deployment.environment.name': (
            'Deployment environment under the modern semconv key. The Java agent emits this via '
            'OTel autoconfiguration / OTEL_RESOURCE_ATTRIBUTES.'
        ),
        'attributes.aws.di.location_hash': (
            'Breakpoint identifier. Use in filters: attributes.aws.di.location_hash = "<value>"'
        ),
        'attributes.aws.di.*': (
            'Breakpoint location metadata: code_unit, class_name, method_name, file_path, '
            'instrumentation_level, instrumentation_type.'
        ),
        'traceId': (
            'OpenTelemetry trace ID (hex, 32 chars). Use to filter snapshots from the same request: '
            'traceId = "<value>"'
        ),
        'spanId': 'OpenTelemetry span ID (hex, 16 chars). Use with traceId for precise span correlation.',
        'body.stack': (
            'Call stack frames (file_path, function, line_number), top to bottom. '
            'First few frames are DI internals; application frames follow after.'
        ),
        'body.captures.entry.arguments.<name>': (
            'Input arguments at function entry (method-level only). '
            'Filter: @message like /"arguments"/ and @message like /"<name>"/'
        ),
        'body.captures.entry.locals.<name>': 'Local variables at function entry (method-level only).',
        'body.captures.return.return_value': (
            'Function return value (method-level only). '
            'Filter: @message like /"return_value"/ and @message like /"<value>"/'
        ),
        'body.captures.return.arguments.<name>': (
            'Arguments at function exit. Compare with entry arguments to detect mutation.'
        ),
        'body.captures.return.locals.<name>': 'Local variables at function exit (method-level only).',
        'body.captures.return.throwable': 'Exception info if function threw: type, message, stacktrace.',
        'body.captures.lines.<line>.locals.<name>': (
            'Local variables at a specific line (line-level only). '
            'Filter: @message like /"locals"/ and @message like /"<name>"/'
        ),
        'CapturedValue shapes': (
            "Each captured value has 'type' and one of: "
            "'value' (string representation for primitives/strings/numbers), "
            "'fields' (map of field name to CapturedValue, for objects/structs), "
            "'elements' (array of CapturedValue, for lists/arrays), "
            "'entries' (array of {key: CapturedValue, value: CapturedValue}, for maps/dicts), "
            "'is_null': true (for null values), "
            "'not_captured_reason' — the literal is agent-specific: Python emits lowercase "
            'camelCase (depth, fieldCount, timeout); Java emits uppercase enum names '
            '(DEPTH, TIMEOUT). Match both forms when filtering. '
            "Oversize collections/maps are signaled via 'truncated: true' plus 'size' (original element count), "
            'not via a not_captured_reason.'
        ),
    }
    output['messages'] = query_result.get('messages', [])

    return json.dumps(output, indent=2)
