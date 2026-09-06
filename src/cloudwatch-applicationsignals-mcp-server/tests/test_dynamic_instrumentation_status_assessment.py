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

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pure-function tests for the consolidated status assessment policy.

The assessment owns the priority order (ACTIVE → READY → ERROR/PENDING) and
the ACTIVE-window clamp. These tests exercise that policy with a fake
``check_status`` callable so no AWS stub is required.
"""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.dynamic_instrumentation.status_assessment import (
    Active,
    ErrorOrPending,
    Ready,
    TimeWindow,
    assess,
)
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple


def _fake_check(
    events_per_status: Dict[str, List[dict]], errors_per_status: Optional[Dict[str, str]] = None
):
    """Build a ``check_status`` callable backed by an in-memory script."""
    errors_per_status = errors_per_status or {}
    calls: List[Tuple[str, datetime, datetime]] = []

    def check(
        status: str, start: datetime, end: datetime
    ) -> Tuple[bool, List[dict], Optional[str]]:
        calls.append((status, start, end))
        if status in errors_per_status:
            return False, [], errors_per_status[status]
        events = events_per_status.get(status, [])
        return bool(events), events, None

    check.calls = calls  # type: ignore[attr-defined]
    return check


CREATED = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
START = datetime(2026, 5, 1, 12, 30, 0, tzinfo=timezone.utc)
END = datetime(2026, 5, 1, 13, 0, 0, tzinfo=timezone.utc)


class TestAssessmentPriority:
    """Verdict picks the highest-priority confirmed status."""

    def test_active_wins_when_active_has_events(self):
        """Active wins when active has events."""
        check = _fake_check({'ACTIVE': [{'Time': 'now'}], 'READY': [{'Time': 'ignored'}]})
        verdict, _ = assess(
            created_at=CREATED, requested_start=START, query_end=END, check_status=check
        )
        assert isinstance(verdict, Active)
        assert verdict.active.has_events is True
        # Should short-circuit before checking READY/ERROR.
        statuses_called = [s for s, _, _ in check.calls]  # type: ignore[attr-defined]
        assert statuses_called == ['ACTIVE']

    def test_ready_wins_when_active_empty_and_ready_has_events(self):
        """Ready wins when active empty and ready has events."""
        check = _fake_check({'READY': [{'Time': 'ready-event'}]})
        verdict, _ = assess(
            created_at=CREATED, requested_start=START, query_end=END, check_status=check
        )
        assert isinstance(verdict, Ready)
        assert verdict.ready.has_events is True
        assert verdict.active.has_events is False
        statuses_called = [s for s, _, _ in check.calls]  # type: ignore[attr-defined]
        assert statuses_called == ['ACTIVE', 'READY']

    def test_error_or_pending_when_active_and_ready_empty(self):
        """Error or pending when active and ready empty."""
        check = _fake_check({'ERROR': [{'Time': 'boom', 'ErrorCause': 'FILE_NOT_FOUND'}]})
        verdict, _ = assess(
            created_at=CREATED, requested_start=START, query_end=END, check_status=check
        )
        assert isinstance(verdict, ErrorOrPending)
        assert verdict.error.has_events is True
        assert verdict.error.events[0]['ErrorCause'] == 'FILE_NOT_FOUND'

    def test_pending_when_all_three_checks_empty(self):
        """Pending when all three checks empty."""
        check = _fake_check({})
        verdict, _ = assess(
            created_at=CREATED, requested_start=START, query_end=END, check_status=check
        )
        assert isinstance(verdict, ErrorOrPending)
        assert verdict.active.has_events is False
        assert verdict.ready.has_events is False
        assert verdict.error.has_events is False


class TestActiveWindowClamp:
    """ACTIVE is searched only after the resource was created."""

    def test_active_start_is_clamped_to_created_at_when_request_predates_creation(self):
        """Active start is clamped to created at when request predates creation."""
        # requested_start is *before* created_at — clamp must push ACTIVE start forward.
        requested_start = CREATED - timedelta(hours=1)
        end = CREATED + timedelta(minutes=30)
        check = _fake_check({})
        verdict, time_window = assess(
            created_at=CREATED, requested_start=requested_start, query_end=end, check_status=check
        )

        active_call = next(call for call in check.calls if call[0] == 'ACTIVE')  # type: ignore[attr-defined]
        _, active_start, active_end = active_call
        assert active_start == CREATED
        assert active_end == end
        assert time_window.active_query_start == '2026-05-01T12:00:00Z'
        assert time_window.requested_start == '2026-05-01T11:00:00Z'
        # And we keep going through READY/ERROR since ACTIVE was empty.
        assert isinstance(verdict, ErrorOrPending)

    def test_active_skipped_when_clamped_window_is_empty(self):
        """Active skipped when clamped window is empty."""
        # query_end is before created_at, so the clamped ACTIVE window collapses.
        requested_start = CREATED - timedelta(hours=2)
        end = CREATED - timedelta(minutes=30)
        check = _fake_check({'READY': [{'Time': 'ready'}]})
        verdict, time_window = assess(
            created_at=CREATED, requested_start=requested_start, query_end=end, check_status=check
        )

        # ACTIVE was *not* called at all — the policy short-circuits the empty window.
        statuses_called = [s for s, _, _ in check.calls]  # type: ignore[attr-defined]
        assert 'ACTIVE' not in statuses_called
        assert isinstance(verdict, Ready)
        assert verdict.active.has_events is False
        assert verdict.active.error is not None
        assert 'Skipped' in verdict.active.error
        # The skip-reason carries the clamped window for the renderer.
        assert time_window.active_query_start in verdict.active.error
        assert time_window.query_end in verdict.active.error


class TestCheckErrorsPropagate:
    """Errors from a check call are surfaced on the verdict, not raised."""

    def test_active_check_error_does_not_short_circuit(self):
        """Active check error does not short circuit."""
        check = _fake_check(
            events_per_status={'READY': [{'Time': 'ready'}]},
            errors_per_status={'ACTIVE': 'API error: boom'},
        )
        verdict, _ = assess(
            created_at=CREATED, requested_start=START, query_end=END, check_status=check
        )
        # ACTIVE failed → has_events False → fall through. READY then wins.
        assert isinstance(verdict, Ready)
        assert verdict.active.error == 'API error: boom'


class TestTimeWindowFormatting:
    """The TimeWindow view-model holds ISO strings the renderer needs."""

    def test_time_window_iso_strings_use_utc_z_suffix(self):
        """Time window iso strings use utc z suffix."""
        # Pass a non-UTC datetime; assessment should convert.
        non_utc = datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
        end = non_utc + timedelta(hours=2)
        check = _fake_check({})
        _, time_window = assess(
            created_at=non_utc, requested_start=non_utc, query_end=end, check_status=check
        )

        assert isinstance(time_window, TimeWindow)
        # 09:00 UTC-3 == 12:00 UTC.
        assert time_window.created_at == '2026-05-01T12:00:00Z'
        assert time_window.requested_start == '2026-05-01T12:00:00Z'
        assert time_window.query_end == '2026-05-01T14:00:00Z'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
