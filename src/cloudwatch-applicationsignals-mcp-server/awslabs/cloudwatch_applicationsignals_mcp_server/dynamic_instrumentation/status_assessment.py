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
"""Consolidated status assessment for dynamic instrumentation.

The "consolidated status check" answers a single question — *what is the
high-level state of this instrumentation right now?* — by querying three
status signals (ACTIVE, READY, ERROR) in priority order over a time window.

This module owns:

* The **time-window policy.** ACTIVE events are only meaningful after the
  instrumentation was created, so the ACTIVE query window is clamped to
  ``max(created_at, requested_start)``. READY and ERROR are checked against
  the full requested window.
* The **check ordering.** ACTIVE wins; otherwise READY wins; otherwise the
  ERROR check decides between ERROR and PENDING.
* The **verdict shape.** Returns a sealed sum type that the renderer
  dispatches on, instead of leaking three different argument tuples to
  three different renderers.

I/O lives in the caller. ``assess`` takes a ``check_status`` callable so
the policy can be tested without touching boto3.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple, Union


# A single check call: (status_label, start, end) → (has_events, events, error_or_None).
# Matches the existing ``_check_status_with_time_range`` shape.
CheckStatus = Callable[[str, datetime, datetime], Tuple[bool, List[dict], Optional[str]]]


@dataclass(frozen=True)
class TimeWindow:
    """The four ISO-formatted time strings every consolidated renderer needs."""

    created_at: str
    requested_start: str
    active_query_start: str
    query_end: str


@dataclass(frozen=True)
class _StatusCheckResult:
    has_events: bool
    events: List[dict]
    error: Optional[str]


@dataclass(frozen=True)
class Active:
    """ACTIVE events were found in the (clamped) ACTIVE window."""

    active: _StatusCheckResult


@dataclass(frozen=True)
class Ready:
    """ACTIVE not confirmed, but READY events were found."""

    active: _StatusCheckResult
    ready: _StatusCheckResult


@dataclass(frozen=True)
class ErrorOrPending:
    """Neither ACTIVE nor READY confirmed.

    The ERROR check decides between ERROR and PENDING based on whether
    ``error.has_events`` is true.
    """

    active: _StatusCheckResult
    ready: _StatusCheckResult
    error: _StatusCheckResult


Verdict = Union[Active, Ready, ErrorOrPending]


def _check_result(
    check: CheckStatus, status: str, start: datetime, end: datetime
) -> _StatusCheckResult:
    has_events, events, error = check(status, start, end)
    return _StatusCheckResult(has_events=has_events, events=events, error=error)


def _format_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def assess(
    *,
    created_at: datetime,
    requested_start: datetime,
    query_end: datetime,
    check_status: CheckStatus,
) -> Tuple[Verdict, TimeWindow]:
    """Run the consolidated status assessment.

    The caller is responsible for:

    * Parsing ISO inputs into ``datetime`` objects (string parsing is an input
      concern, not policy).
    * Verifying ``query_end > requested_start`` before calling — that error
      message is owned by the tool layer.
    * Providing a ``check_status`` callable that issues the AWS query.

    Returns a ``(verdict, time_window)`` pair. The renderer dispatches on
    the verdict type; both verdict and time_window are passed to the
    renderer.
    """
    requested_start_utc = requested_start.astimezone(timezone.utc)
    query_end_utc = query_end.astimezone(timezone.utc)
    created_at_utc = created_at.astimezone(timezone.utc)
    active_query_start_utc = max(created_at_utc, requested_start_utc)

    time_window = TimeWindow(
        created_at=_format_iso(created_at_utc),
        requested_start=_format_iso(requested_start_utc),
        active_query_start=_format_iso(active_query_start_utc),
        query_end=_format_iso(query_end_utc),
    )

    if query_end_utc > active_query_start_utc:
        active = _check_result(check_status, 'ACTIVE', active_query_start_utc, query_end_utc)
    else:
        active = _StatusCheckResult(
            has_events=False,
            events=[],
            error=(
                'Skipped: ACTIVE query window is empty after applying created_at clamp '
                f'(start={time_window.active_query_start}, end={time_window.query_end})'
            ),
        )

    if active.has_events:
        return Active(active=active), time_window

    ready = _check_result(check_status, 'READY', requested_start_utc, query_end_utc)
    if ready.has_events:
        return Ready(active=active, ready=ready), time_window

    error = _check_result(check_status, 'ERROR', requested_start_utc, query_end_utc)
    return ErrorOrPending(active=active, ready=ready, error=error), time_window
