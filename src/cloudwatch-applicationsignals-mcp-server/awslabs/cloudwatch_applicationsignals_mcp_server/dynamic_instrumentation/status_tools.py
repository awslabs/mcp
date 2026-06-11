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
"""MCP tool entrypoints for status queries and reporting."""

from . import application_signals_gateway as gateway
from .constants import SNAPSHOT_SIGNAL_TYPE
from .location import parse_lookup_inputs
from .status_assessment import assess
from .status_rendering import (
    render_get_instrumentation_configuration_status_output,
    render_status_assessment,
)
from .validation import (
    is_valid_location_hash,
    normalize_instrumentation_type,
    validate_snapshot_signal,
)
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _check_status_with_time_range(
    *,
    service: str,
    environment: str,
    instrumentation_type: str,
    location_identifier: Dict[str, Any],
    status: str,
    start_time: datetime,
    end_time: datetime,
    signal_type: str = SNAPSHOT_SIGNAL_TYPE,
) -> Tuple[bool, List[dict], Optional[str]]:
    """Check whether status events exist for the configuration in a time range."""
    try:
        data = gateway.get_instrumentation_configuration_status(
            InstrumentationType=instrumentation_type,
            Service=service,
            Environment=environment,
            SignalType=signal_type,
            Status=status,
            LocationIdentifier=location_identifier,
            StartTime=start_time,
            EndTime=end_time,
        )
    except gateway.GatewayError as err:
        return False, [], f'API error: {err.original_exc}'

    events = data.get('Events', []) if isinstance(data, dict) else []
    return len(events) > 0, events, None


def _render_status_identifier_help() -> str:
    return """ERROR: Must provide one of:
- location_hash
- language + file_path (for code location identifier)

Usage:
1. Get by hash (preferred):
   get_instrumentation_configuration_status(location_hash="abc123...")

2. Get by code location:
   get_instrumentation_configuration_status(language="Python", file_path="/app/file.py", ...)"""


def _parse_iso_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 timestamp, accepting trailing 'Z' as UTC.

    A naive input (no 'Z' or offset, e.g. ``2025-02-03T18:42:00``) is assumed
    to be UTC rather than host-local. Without this, downstream ``astimezone``
    calls in ``assess()`` would reinterpret it in the host timezone — on a
    UTC-8 host ``18:42`` becomes ``02:42Z``, shifting the whole status query
    window and causing ACTIVE/READY events to be missed.
    """
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_instrumentation_configuration_status(
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
    status: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_results: int = 100,
    next_token: Optional[str] = None,
    signal_type: str = SNAPSHOT_SIGNAL_TYPE,
) -> str:
    """Get status-event history for one instrumentation configuration and one explicit status.

    This API is intentionally strict: callers must provide exactly one status
    filter because AWS defaults can be ambiguous. The response distinguishes
    between the backend's current status field and status confirmation based on
    returned events.

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
        status: Required. Must be READY, ACTIVE, ERROR, or DISABLED.
        start_time: Optional ISO 8601 lower bound for returned events.
        end_time: Optional ISO 8601 upper bound for returned events.
        max_results: Maximum number of events to request. Defaults to 100.
        next_token: Optional AWS pagination token from a previous response.
        signal_type: Must be SNAPSHOT.

    Returns:
        A human-readable status report with location details, event count,
        confirmation guidance, and pagination hints when additional events exist.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error
    signal_error = validate_snapshot_signal(signal_type)
    if signal_error:
        return signal_error

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
            return _render_status_identifier_help()
        return f'ERROR: {location_error}'
    if location is None:
        # Defensive: parsers return (loc, None) or (None, error_text). This
        # branch should be unreachable, but we return a user-facing error
        # string (not ``raise``) so the tool's "always returns a string"
        # contract holds even if a future parser bug fires this path.
        return 'ERROR: Internal error resolving location. Please report this issue.'
    target_desc = location.describe()

    requested_status = (status or '').strip().upper()
    allowed_statuses = {'READY', 'ACTIVE', 'ERROR', 'DISABLED'}
    if not requested_status:
        return """ERROR: status is required

This API cannot return all statuses in one call.
If status is omitted, AWS defaults to ACTIVE, which is ambiguous.

Use explicit status checks in this order:
1. status="READY"
2. status="ACTIVE" (only after READY is confirmed by events)
3. status="ERROR" (if READY not confirmed)
4. status="DISABLED" (when checking max-hits scenarios)"""

    if requested_status not in allowed_statuses:
        return (
            'ERROR: invalid status. Must be one of: READY, ACTIVE, ERROR, DISABLED '
            f'(received: {status})'
        )

    request_kwargs: Dict[str, Any] = {
        'InstrumentationType': normalized_type,
        'Service': service,
        'Environment': environment,
        'SignalType': SNAPSHOT_SIGNAL_TYPE,
        'Status': requested_status,
        'LocationIdentifier': location.to_identifier(),
    }

    if start_time:
        try:
            request_kwargs['StartTime'] = _parse_iso_timestamp(start_time)
        except ValueError as exc:
            return f'ERROR: Invalid start_time format. Expected ISO 8601. Error: {exc}'
    if end_time:
        try:
            request_kwargs['EndTime'] = _parse_iso_timestamp(end_time)
        except ValueError as exc:
            return f'ERROR: Invalid end_time format. Expected ISO 8601. Error: {exc}'
    if max_results != 100:
        request_kwargs['MaxResults'] = max_results
    if next_token:
        request_kwargs['NextToken'] = next_token

    try:
        data = gateway.get_instrumentation_configuration_status(**request_kwargs)
    except gateway.GatewayError as err:
        return gateway.render_error(
            err,
            action='get instrumentation status',
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
            troubleshooting=['Use get_instrumentation to verify the configuration exists'],
        )

    return render_get_instrumentation_configuration_status_output(
        data=data,
        normalized_type=normalized_type,
        service=service,
        environment=environment,
        requested_status=requested_status,
    )


def check_instrumentation_status(
    service: str,
    environment: str,
    instrumentation_type: str,
    location_hash: str,
    start_time: str,
    end_time: str,
    signal_type: str = SNAPSHOT_SIGNAL_TYPE,
) -> str:
    """Run a consolidated READY/ACTIVE/ERROR status check over a time window.

    This helper is opinionated: it first fetches the instrumentation creation
    time, clamps the ACTIVE search window so it does not start before creation,
    and then checks ACTIVE, READY, and ERROR in order to produce a single
    high-level interpretation.

    Args:
        service: Backend service identifier.
        environment: Backend environment identifier.
        instrumentation_type: BREAKPOINT or PROBE.
        location_hash: Required 16-character lowercase hex location hash for the target configuration.
        start_time: Required ISO 8601 lower bound for the overall check window.
        end_time: Required ISO 8601 upper bound for the overall check window.
        signal_type: Must be SNAPSHOT.

    Returns:
        A human-readable consolidated assessment such as ACTIVE, READY, ERROR, or
        PENDING, plus troubleshooting guidance and snapshot-query hints when applicable.
    """
    normalized_type, type_error = normalize_instrumentation_type(instrumentation_type)
    if type_error:
        return type_error
    signal_error = validate_snapshot_signal(signal_type)
    if signal_error:
        return signal_error

    if not is_valid_location_hash(location_hash):
        return 'ERROR: location_hash must be a 16-character hex string'

    try:
        created_at_response = gateway.get_instrumentation_configuration(
            InstrumentationType=normalized_type,
            Service=service,
            Environment=environment,
            SignalType=SNAPSHOT_SIGNAL_TYPE,
            LocationIdentifier={'LocationHash': location_hash},
        )
    except gateway.GatewayError as err:
        return f'ERROR: Failed to fetch created_at: Exception: {err.original_exc}'

    config = (
        created_at_response.get('Configuration', {})
        if isinstance(created_at_response, dict)
        else {}
    )
    if not config:
        return f'ERROR: Failed to fetch created_at: No instrumentation found for LocationHash {location_hash}'
    created_dt = config.get('CreatedAt')
    if created_dt is None:
        return 'ERROR: Failed to fetch created_at: CreatedAt not found in instrumentation configuration'

    try:
        start_dt = _parse_iso_timestamp(start_time)
    except ValueError as exc:
        return f'ERROR: Invalid start_time format. Expected ISO 8601. Error: {exc}'

    try:
        query_end_dt = _parse_iso_timestamp(end_time)
    except ValueError as exc:
        return f'ERROR: Invalid end_time format. Expected ISO 8601. Error: {exc}'

    if query_end_dt <= start_dt:
        return 'ERROR: end_time must be later than start_time'

    location_identifier = {'LocationHash': location_hash}

    def check_status(
        status: str, start: datetime, end: datetime
    ) -> Tuple[bool, List[dict], Optional[str]]:
        return _check_status_with_time_range(
            service=service,
            environment=environment,
            instrumentation_type=normalized_type,
            location_identifier=location_identifier,
            status=status,
            start_time=start,
            end_time=end,
            signal_type=SNAPSHOT_SIGNAL_TYPE,
        )

    verdict, time_window = assess(
        created_at=created_dt,
        requested_start=start_dt,
        query_end=query_end_dt,
        check_status=check_status,
    )

    return render_status_assessment(
        verdict,
        location_hash=location_hash,
        service=service,
        environment=environment,
        normalized_type=normalized_type,
        time_window=time_window,
    )
