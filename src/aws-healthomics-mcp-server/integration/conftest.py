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


"""Opt-in gating for the remote-deployment integration test harness.

This ``conftest.py`` implements the two independent gates described in the design
("Opt-in gating mechanism"):

1. **Master opt-in signal.** A ``pytest_collection_modifyitems`` hook applies a
   ``pytest.mark.skip`` to every collected item under ``integration/tests/`` when
   the Opt_In_Signal (``RUN_REMOTE_INTEGRATION_TESTS``) is absent, at collection
   time. Because the skip is applied during collection and nothing here builds an
   AWS client (no session-scoped/autouse fixture constructs one, and no boto3
   client is created at import or collection time), the suite completes both its
   collection and execution phases without constructing an AWS client, resolving
   AWS credentials, or opening a network connection (Req 1.2, 1.3, 1.4).

2. **Per-test dependency gate.** When the signal *is* present, a test resolves its
   required configuration inputs (endpoint references, table name, region) lazily
   through the :func:`require_inputs` fixture. A missing input raises
   ``pytest.skip`` naming the missing dependency, so the test is skipped rather
   than failed (Req 1.5, 1.6).

The gate itself is guarded so it only affects items under ``integration/tests/``;
the harness's own offline unit/property tests for the pure-logic utilities are not
gated (they never touch AWS).
"""

import os
import pytest
from collections.abc import Mapping, Sequence
from integration.harness.opt_in import (
    is_opt_in_enabled,
    missing_required_inputs,
    skip_reason,
)
from pathlib import Path


# The directory whose tests are gated behind the Opt_In_Signal. Items outside
# this directory (e.g. the harness's own offline unit/property tests) are never
# skipped by the collection hook.
_INTEGRATION_TESTS_DIR = Path(__file__).parent / 'tests'


def _is_under_integration_tests(item: pytest.Item) -> bool:
    """Return True iff ``item`` was collected from under ``integration/tests/``.

    Guards the collection hook so it never skips the harness's offline
    unit/property tests, which live outside ``integration/tests/`` and must run as
    part of the normal offline suite.
    """
    item_path = getattr(item, 'path', None)
    if item_path is None:
        # Fall back to the legacy py.path ``fspath`` attribute if ``path`` is
        # unavailable on this pytest version.
        fspath = getattr(item, 'fspath', None)
        if fspath is None:
            return False
        item_path = Path(str(fspath))
    try:
        item_path.resolve().relative_to(_INTEGRATION_TESTS_DIR.resolve())
    except ValueError:
        return False
    return True


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip every integration test at collection time when the signal is absent.

    When the Opt_In_Signal is not present (or not truthy), each item under
    ``integration/tests/`` receives a ``pytest.mark.skip`` carrying the reason
    that names the required environment variable. Applying the skip here — during
    collection — guarantees that no AWS client is built and no credentials are
    resolved during collection or execution (Req 1.2, 1.3, 1.4).

    When the signal is present, this hook does nothing and the per-test
    dependency gate (:func:`require_inputs`) governs each test.
    """
    if is_opt_in_enabled(os.environ):
        return

    skip_marker = pytest.mark.skip(reason=skip_reason())
    for item in items:
        if _is_under_integration_tests(item):
            item.add_marker(skip_marker)


@pytest.fixture
def integration_env() -> Mapping[str, str]:
    """Return the process environment used to resolve integration inputs.

    Exposed as a fixture so tests (and the :func:`require_inputs` factory) read a
    single, overridable source of configuration. Kept lazy — the environment is
    only read when a test actually requests it.
    """
    return os.environ


@pytest.fixture
def require_inputs(integration_env: Mapping[str, str]):
    """Return a resolver that fetches required inputs or skips naming the missing.

    The returned callable takes the names of the configuration inputs a test
    depends on (endpoint references, table name, region, ...) and returns a
    mapping of those names to their resolved values. If any required input is
    absent or blank, it raises ``pytest.skip`` with a reason naming exactly the
    missing inputs, so the test is skipped rather than reported passed or failed
    (Req 1.6).

    Resolution is lazy: nothing is read until a test invokes the resolver, and no
    AWS client is constructed here.
    """

    def _resolve(required: Sequence[str]) -> dict[str, str]:
        missing = missing_required_inputs(required, integration_env)
        if missing:
            pytest.skip('Missing required integration input(s): ' + ', '.join(missing))
        return {name: integration_env[name] for name in required}

    return _resolve
