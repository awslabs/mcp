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
"""Formatting helpers for status tool responses."""

from .constants import SNAPSHOT_SIGNAL_TYPE, resolve_snapshot_log_group
from .formatting import format_timestamp
from .location import location_from_response, render_location_block
from .status_assessment import Active, ErrorOrPending, Ready, TimeWindow, Verdict
from typing import Any, Dict, List, Optional


def render_get_instrumentation_configuration_status_output(
    data: Dict[str, Any],
    normalized_type: str,
    service: str,
    environment: str,
    requested_status: str,
) -> str:
    """Render the explicit status-history response."""
    events = data.get('Events', [])

    output = f"""INSTRUMENTATION STATUS

TYPE: {normalized_type}
SERVICE: {data.get('Service', service)}
ENVIRONMENT: {data.get('Environment', environment)}
SIGNAL TYPE: {data.get('SignalType', SNAPSHOT_SIGNAL_TYPE)}
REQUESTED STATUS FILTER: {requested_status}
CURRENT STATUS: {data.get('Status', 'N/A')}

LOCATION:
"""
    output += render_location_block(
        location=location_from_response(data.get('Location', {})),
        location_hash=data.get('LocationHash'),
    )
    output += f'- Events Returned: {len(events)}\n'

    if events:
        output += f'- Status Confirmation: CONFIRMED ({requested_status} events present)\n'
    else:
        output += f'- Status Confirmation: NOT CONFIRMED (no {requested_status} events)\n'

    output += (
        '- Interpretation Rule: Do not treat CURRENT STATUS as confirmed unless '
        'STATUS EVENTS contain entries.\n'
    )

    if requested_status == 'ACTIVE' and not events:
        output += (
            '- ACTIVE Clarification: Breakpoint is not confirmed as hit yet. '
            'If READY is not yet confirmed, check READY first. '
            'Otherwise wait for traffic and poll ACTIVE again.\n'
        )

    output += '\nSTATUS EVENTS:\n'
    if not events:
        output += f'- No {requested_status} status events found\n'
    else:
        for index, event in enumerate(events, 1):
            event_time = format_timestamp(event.get('Time'))
            error_cause = event.get('ErrorCause')
            output += f'- Event {index}: {event_time}'
            if error_cause:
                output += f' | ErrorCause: {error_cause}'
            output += '\n'

    next_token_response = data.get('NextToken')
    if next_token_response:
        output += (
            f'\nPAGINATION: More results available. Use next_token="{next_token_response}" '
            'to retrieve next page.'
        )

    return output


def _render_status_section(
    title: str,
    start_time: str,
    end_time: str,
    has_events: bool,
    events: List[dict],
    error: Optional[str],
    include_error_cause: bool = False,
) -> str:
    output = f'{title} STATUS:\n'
    output += f'- Time Window: {start_time} to {end_time}\n'
    if error:
        if error.startswith('Skipped:'):
            output += f'- Check Skipped: {error}\n'
        else:
            output += f'- Check Failed: {error}\n'
        return output

    if has_events:
        output += f'- Confirmed: YES ({len(events)} event(s))\n'
        for index, event in enumerate(events[:3], 1):
            output += f'  - Event {index}: {format_timestamp(event.get("Time"))}'
            if include_error_cause:
                output += f' | ErrorCause: {event.get("ErrorCause", "Unknown")}'
            output += '\n'
        if len(events) > 3:
            output += f'  - ... and {len(events) - 3} more\n'
    else:
        output += f'- Confirmed: NO (no {title} events found)\n'
    return output


def render_consolidated_active_status_output(
    location_hash: str,
    service: str,
    environment: str,
    normalized_type: str,
    created_at: str,
    requested_start_str: str,
    active_query_start_str: str,
    query_end_str: str,
    active_has_events: bool,
    active_events: List[dict],
    active_error: Optional[str],
) -> str:
    """Render a consolidated status response when ACTIVE is confirmed or checked first."""
    output = f"""CONSOLIDATED STATUS CHECK

INSTRUMENTATION INFO:
- LocationHash: {location_hash}
- Service: {service}
- Environment: {environment}
- Type: {normalized_type}

TIME RANGE:
- Created At: {created_at}
- Requested Start: {requested_start_str}
- ACTIVE Query Start: {active_query_start_str}
- Query End: {query_end_str}

"""
    output += _render_status_section(
        title='ACTIVE',
        start_time=active_query_start_str,
        end_time=query_end_str,
        has_events=active_has_events,
        events=active_events,
        error=active_error,
    )
    output += '\n'

    if active_has_events:
        output += (
            'SNAPSHOT QUERY TIP: Try these timestamps with search_snapshots_for_status_event\n'
            f'  (log group: "{resolve_snapshot_log_group(service)}")\n'
            '  Oldest first — older events are more likely to have snapshots ingested:\n'
        )
        for idx, event in enumerate(reversed(active_events[:5])):
            label = ' (oldest, try first)' if idx == 0 else ''
            if idx == len(active_events[:5]) - 1 and idx > 0:
                label = ' (most recent)'
            output += f'  - status_timestamp="{format_timestamp(event.get("Time"), default="")}"{label}\n'
        output += '\n'
        output += 'OVERALL STATUS: ACTIVE ✓ (breakpoint is being hit)\n'
        return output

    output += 'OVERALL STATUS: ACTIVE not confirmed yet\n'
    return output


def render_consolidated_ready_status_output(
    location_hash: str,
    service: str,
    environment: str,
    normalized_type: str,
    created_at: str,
    requested_start_str: str,
    active_query_start_str: str,
    query_end_str: str,
    active_has_events: bool,
    active_events: List[dict],
    active_error: Optional[str],
    ready_has_events: bool,
    ready_events: List[dict],
    ready_error: Optional[str],
) -> str:
    """Render a consolidated status response when READY is the best confirmed state."""
    output = render_consolidated_active_status_output(
        location_hash=location_hash,
        service=service,
        environment=environment,
        normalized_type=normalized_type,
        created_at=created_at,
        requested_start_str=requested_start_str,
        active_query_start_str=active_query_start_str,
        query_end_str=query_end_str,
        active_has_events=active_has_events,
        active_events=active_events,
        active_error=active_error,
    )
    if output.endswith('OVERALL STATUS: ACTIVE not confirmed yet\n'):
        output = output[: -len('OVERALL STATUS: ACTIVE not confirmed yet\n')]

    output += _render_status_section(
        title='READY',
        start_time=requested_start_str,
        end_time=query_end_str,
        has_events=ready_has_events,
        events=ready_events,
        error=ready_error,
    )
    output += '\nOVERALL STATUS: READY (waiting for traffic)\n'
    return output


def render_consolidated_error_or_pending_status_output(
    location_hash: str,
    service: str,
    environment: str,
    normalized_type: str,
    created_at: str,
    requested_start_str: str,
    active_query_start_str: str,
    query_end_str: str,
    active_has_events: bool,
    active_events: List[dict],
    active_error: Optional[str],
    ready_has_events: bool,
    ready_events: List[dict],
    ready_error: Optional[str],
    error_has_events: bool,
    error_events: List[dict],
    error_error: Optional[str],
) -> str:
    """Render a consolidated status response for ERROR or PENDING outcomes."""
    output = render_consolidated_active_status_output(
        location_hash=location_hash,
        service=service,
        environment=environment,
        normalized_type=normalized_type,
        created_at=created_at,
        requested_start_str=requested_start_str,
        active_query_start_str=active_query_start_str,
        query_end_str=query_end_str,
        active_has_events=active_has_events,
        active_events=active_events,
        active_error=active_error,
    )
    if output.endswith('OVERALL STATUS: ACTIVE not confirmed yet\n'):
        output = output[: -len('OVERALL STATUS: ACTIVE not confirmed yet\n')]

    output += '\n'
    output += _render_status_section(
        title='READY',
        start_time=requested_start_str,
        end_time=query_end_str,
        has_events=ready_has_events,
        events=ready_events,
        error=ready_error,
    )
    output += '\n'
    output += _render_status_section(
        title='ERROR',
        start_time=requested_start_str,
        end_time=query_end_str,
        has_events=error_has_events,
        events=error_events,
        error=error_error,
        include_error_cause=True,
    )

    output += '\nOVERALL STATUS: '
    if error_has_events:
        error_cause = error_events[0].get('ErrorCause', 'Unknown') if error_events else 'Unknown'
        output += f'ERROR ({error_cause})\n'
        output += '\nTROUBLESHOOTING:\n'
        if error_cause == 'FILE_NOT_FOUND':
            output += '- Verify file_path is correct\n'
        elif error_cause == 'METHOD_NOT_FOUND':
            output += '- Verify method_name and code_unit are correct\n'
            output += '- Check if the function is loaded at runtime\n'
        elif error_cause == 'LINE_NOT_EXECUTABLE':
            output += (
                '- Verify line_number points to executable code (not comment/blank/declaration)\n'
            )
        else:
            output += f'- Check instrumentation configuration for {error_cause}\n'
    else:
        output += 'PENDING (no ACTIVE, READY, or ERROR events yet - wait longer or check configuration)\n'
        output += '\nNOTE: Status events can take 1-2 minutes to appear after creation.\n'

    return output


def render_status_assessment(
    verdict: Verdict,
    *,
    location_hash: str,
    service: str,
    environment: str,
    normalized_type: str,
    time_window: TimeWindow,
) -> str:
    """Dispatch a ``Verdict`` to the appropriate consolidated-status renderer.

    Each existing renderer keeps its own prose contract; this function only
    routes. New renderers should be added as ``Verdict`` variants gain
    distinct presentation.
    """
    common = {
        'location_hash': location_hash,
        'service': service,
        'environment': environment,
        'normalized_type': normalized_type,
        'created_at': time_window.created_at,
        'requested_start_str': time_window.requested_start,
        'active_query_start_str': time_window.active_query_start,
        'query_end_str': time_window.query_end,
    }

    if isinstance(verdict, Active):
        return render_consolidated_active_status_output(
            **common,
            active_has_events=verdict.active.has_events,
            active_events=verdict.active.events,
            active_error=verdict.active.error,
        )

    if isinstance(verdict, Ready):
        return render_consolidated_ready_status_output(
            **common,
            active_has_events=verdict.active.has_events,
            active_events=verdict.active.events,
            active_error=verdict.active.error,
            ready_has_events=verdict.ready.has_events,
            ready_events=verdict.ready.events,
            ready_error=verdict.ready.error,
        )

    if isinstance(verdict, ErrorOrPending):
        return render_consolidated_error_or_pending_status_output(
            **common,
            active_has_events=verdict.active.has_events,
            active_events=verdict.active.events,
            active_error=verdict.active.error,
            ready_has_events=verdict.ready.has_events,
            ready_events=verdict.ready.events,
            ready_error=verdict.ready.error,
            error_has_events=verdict.error.has_events,
            error_events=verdict.error.events,
            error_error=verdict.error.error,
        )

    raise TypeError(f'Unknown Verdict variant: {type(verdict).__name__}')
