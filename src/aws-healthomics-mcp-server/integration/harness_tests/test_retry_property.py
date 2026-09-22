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


"""Property tests for the harness retry policy.

These tests are pure and offline: they exercise ``with_retries`` from
``integration/harness/mcp_client.py`` with injected fake ``sleep`` and ``now`` seams so no
real waiting, AWS access, or network I/O occurs. They live in ``integration/harness_tests/``
— separate from the opt-in-gated ``integration/tests/`` suite and from the offline
``tests/`` suite — and are not gated by the Opt_In_Signal.

Because ``with_retries`` is async, each generated scenario is driven synchronously via
``asyncio.run`` inside a normal Hypothesis test, which keeps example generation deterministic
and lets Hypothesis run many examples without async-fixture friction.

Validates: Requirements Remote transport end-to-end verification.
"""

from __future__ import annotations

import asyncio
from hypothesis import given, settings
from hypothesis import strategies as st
from integration.harness.mcp_client import with_retries


class _TransientError(Exception):
    """A transient failure the default ``is_transient`` predicate treats as retryable."""


async def _run_scenario(
    outcomes: list[bool],
    *,
    attempts: int,
    min_interval_s: float,
    start_time: float,
) -> tuple[int, list[float], object | None, BaseException | None, object]:
    """Drive ``with_retries`` over ``outcomes`` with a fake clock and fake sleep.

    ``outcomes[i]`` is ``True`` when the i-th attempt succeeds and ``False`` when it fails
    transiently. The fake ``sleep`` records each requested wait and advances the fake
    monotonic clock by that amount; since ``op`` is instantaneous in fake time, the clock only
    advances via sleeps. Returns the number of ``op`` invocations, the recorded waits, the
    returned value (or ``None`` if it raised), the raised exception (or ``None``), and the
    success sentinel for equality comparison.
    """
    recorded_waits: list[float] = []
    clock = {'now': start_time}

    async def fake_sleep(seconds: float) -> None:
        recorded_waits.append(seconds)
        clock['now'] += seconds

    def fake_now() -> float:
        return clock['now']

    remaining = iter(outcomes)
    invocations = {'count': 0}
    success_sentinel = object()

    async def op() -> object:
        invocations['count'] += 1
        succeeds = next(remaining)
        if succeeds:
            return success_sentinel
        raise _TransientError('transient failure')

    returned: object | None = None
    raised: BaseException | None = None
    try:
        returned = await with_retries(
            op,
            attempts=attempts,
            min_interval_s=min_interval_s,
            sleep=fake_sleep,
            now=fake_now,
        )
    except _TransientError as exc:
        raised = exc

    return invocations['count'], recorded_waits, returned, raised, success_sentinel


# Small positive spacings, including the default 1.0 second, so each retry requests a real
# wait and the ``min_interval_s > 0`` branch of the policy is exercised.
_min_intervals = st.sampled_from([0.5, 1.0, 1.5, 2.0, 3.0])

# Fake monotonic clock starting points, including negative and fractional origins, to show
# the policy depends only on elapsed differences rather than any absolute clock value.
_start_times = st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False)


# Feature: remote-deployment-integration-tests, Property: Retry policy respects the attempt
# budget and spacing
@settings(max_examples=200)
@given(
    additional_attempts=st.integers(min_value=0, max_value=5),
    min_interval_s=_min_intervals,
    start_time=_start_times,
    per_attempt_success=st.lists(st.booleans(), min_size=6, max_size=6),
)
def test_retry_policy_respects_budget_and_spacing(
    additional_attempts: int,
    min_interval_s: float,
    start_time: float,
    per_attempt_success: list[bool],
) -> None:
    """Property: Retry policy respects the attempt budget and spacing.

    For any sequence of transient-failure-then-outcome operations and any injected clock,
    ``with_retries`` makes at most ``attempts`` total attempts (the initial attempt plus up to
    ``attempts - 1`` additional ones, and never more than 4 under the default budget), waits at
    least ``min_interval_s`` seconds between consecutive attempts, stops at the first success,
    and returns success if and only if a success occurs within the attempt budget.

    Validates: Requirements Remote transport end-to-end verification.
    """
    attempts = 1 + additional_attempts
    # Only the first ``attempts`` outcomes are reachable within the budget.
    outcomes = per_attempt_success[:attempts]

    first_success = next((index for index, ok in enumerate(outcomes) if ok), None)
    success_within_budget = first_success is not None
    expected_invocations = (first_success + 1) if success_within_budget else attempts

    invocations, waits, returned, raised, success_sentinel = asyncio.run(
        _run_scenario(
            outcomes,
            attempts=attempts,
            min_interval_s=min_interval_s,
            start_time=start_time,
        )
    )

    # Attempt budget: stops at the first success and never exceeds the total budget. Under the
    # default budget of 4 this is at most 4 attempts.
    assert invocations == expected_invocations
    assert invocations <= attempts
    if attempts == 4:
        assert invocations <= 4

    # Outcome correspondence: success is returned iff a success occurs within the budget,
    # otherwise the last transient exception propagates.
    if success_within_budget:
        assert returned is success_sentinel
        assert raised is None
    else:
        assert returned is None
        assert isinstance(raised, _TransientError)

    # Spacing: a wait is requested only between consecutive attempts (never before the first
    # attempt and never after the last), and each requested wait is at least ``min_interval_s``.
    assert len(waits) == invocations - 1
    for wait in waits:
        assert wait >= min_interval_s
