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


"""Unit tests for the opt-in gate and the collection gating hook.

These tests are pure and offline. They cover two things:

- **Part A — the opt-in gate** (``integration/harness/opt_in.py``): example-based checks that
  ``is_opt_in_enabled`` recognizes truthy signals and rejects absent, blank, and non-truthy
  values, and that ``skip_reason`` names the ``RUN_REMOTE_INTEGRATION_TESTS`` env var.
- **Part B — the collection gating hook** (``integration/conftest.py``): a direct unit test of
  ``pytest_collection_modifyitems`` driving it with fake collected items to prove that, with the
  Opt_In_Signal absent, every item under ``integration/tests/`` is skipped with a reason naming
  the env var, that items outside ``integration/tests/`` are left untouched, and that the gating
  path constructs no AWS client (boto3 is patched to raise if touched).

The tests live in ``integration/harness_tests/`` — separate from the opt-in-gated
``integration/tests/`` suite and from the offline ``tests/`` suite — and are not gated by the
Opt_In_Signal. No AWS access or network activity occurs.

Validates: Requirements Harness location and offline isolation.
"""

import integration.conftest as conftest_module
import pytest
from integration.conftest import pytest_collection_modifyitems
from integration.harness.opt_in import OPT_IN_ENV, is_opt_in_enabled, skip_reason
from pathlib import Path
from types import SimpleNamespace


# --- Part A: opt-in gate unit tests -----------------------------------------------------------

# Values accepted as "enabled" by the gate. Mixed case and surrounding whitespace are included to
# exercise the case-insensitive, whitespace-trimmed parse. Kept in sync with the module's
# ``_ENABLE_VALUES`` set (true/1/yes/on/enabled).
_TRUTHY_VALUES = [
    'true',
    'TRUE',
    'True',
    '1',
    'yes',
    'YES',
    'on',
    'ON',
    'enabled',
    'ENABLED',
    '  true  ',
    '\tyes\n',
    ' on ',
]

# Values that must NOT enable the suite: explicit disable words, blanks, and unrecognized text.
_NON_TRUTHY_VALUES = [
    'false',
    'FALSE',
    '0',
    'no',
    'off',
    'disabled',
    'maybe',
    '',
    ' ',
    '   ',
    '\t',
    '\n',
    ' \t\n ',
    'truthy',
    'yess',
    '2',
]


@pytest.mark.parametrize('value', _TRUTHY_VALUES)
def test_is_opt_in_enabled_true_for_truthy_values(value: str) -> None:
    """A present, truthy signal enables the suite regardless of case/whitespace.

    Validates: Requirements Harness location and offline isolation.
    """
    assert is_opt_in_enabled({OPT_IN_ENV: value}) is True


@pytest.mark.parametrize('value', _NON_TRUTHY_VALUES)
def test_is_opt_in_enabled_false_for_non_truthy_values(value: str) -> None:
    """A present but non-truthy or blank signal does not enable the suite.

    Validates: Requirements Harness location and offline isolation.
    """
    assert is_opt_in_enabled({OPT_IN_ENV: value}) is False


def test_is_opt_in_enabled_false_when_absent() -> None:
    """An absent signal key does not enable the suite.

    Validates: Requirements Harness location and offline isolation.
    """
    assert is_opt_in_enabled({}) is False
    # Other, unrelated keys present must not accidentally enable the suite.
    assert is_opt_in_enabled({'SOME_OTHER_VAR': 'true'}) is False


def test_skip_reason_names_the_opt_in_env_var() -> None:
    """The skip reason names the ``RUN_REMOTE_INTEGRATION_TESTS`` env var.

    Validates: Requirements Harness location and offline isolation.
    """
    reason = skip_reason()

    assert OPT_IN_ENV in reason
    assert 'RUN_REMOTE_INTEGRATION_TESTS' in reason
    assert reason.strip() != ''


# --- Part B: collection gating hook unit test -------------------------------------------------


class _FakeItem:
    """A minimal stand-in for a collected pytest item.

    Exposes only what ``pytest_collection_modifyitems`` (and its
    ``_is_under_integration_tests`` guard) touches: a ``path`` attribute and an
    ``add_marker`` method that records applied markers for inspection.
    """

    def __init__(self, path: Path) -> None:
        """Record the item's collection ``path`` and prepare marker capture."""
        self.path = path
        self.applied_markers: list[object] = []

    def add_marker(self, marker: object) -> None:
        """Record a marker the hook applies to this item."""
        self.applied_markers.append(marker)


def _integration_tests_dir() -> Path:
    """Return the real ``<repo>/integration/tests`` directory.

    Derived from this test file's location (``integration/harness_tests/``) so it matches the
    directory the hook keys off (``integration/conftest.py`` -> ``tests``).
    """
    return Path(__file__).resolve().parent.parent / 'tests'


def _skip_reasons(item: _FakeItem) -> list[str]:
    """Extract the ``reason`` of every ``skip`` marker applied to ``item``.

    ``pytest.mark.skip(reason=...)`` yields a ``MarkDecorator`` whose ``name`` is ``'skip'`` and
    whose ``kwargs`` carry the ``reason``; this reads those back out.
    """
    reasons: list[str] = []
    for marker in item.applied_markers:
        name = getattr(marker, 'name', None)
        kwargs = getattr(marker, 'kwargs', {})
        if name == 'skip' and 'reason' in kwargs:
            reasons.append(kwargs['reason'])
    return reasons


def test_collection_skips_integration_items_and_builds_no_aws_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the signal absent, integration items are skipped and no AWS client is built.

    Drives ``pytest_collection_modifyitems`` directly with fake items: two under the real
    ``integration/tests/`` directory and one outside it. Asserts that every integration item
    receives a ``skip`` marker whose reason names ``RUN_REMOTE_INTEGRATION_TESTS``, that the
    outside item is left untouched, and that running the hook constructs no AWS client (boto3 is
    patched to raise if touched, proving the gating path never reaches it).

    Validates: Requirements Harness location and offline isolation.
    """
    # Ensure the Opt_In_Signal is absent so the hook takes the skip-all branch.
    monkeypatch.delenv(OPT_IN_ENV, raising=False)

    # Fail loudly if the gating path ever tries to construct an AWS client. The hook reads only
    # ``os.environ`` via ``is_opt_in_enabled``, so nothing below should ever be called.
    import boto3
    import botocore.session

    def _raise_if_called(*args: object, **kwargs: object) -> object:
        raise AssertionError('collection gating must not construct an AWS client')

    monkeypatch.setattr(boto3, 'client', _raise_if_called)
    monkeypatch.setattr(boto3, 'Session', _raise_if_called)
    monkeypatch.setattr(botocore.session, 'Session', _raise_if_called)

    tests_dir = _integration_tests_dir()
    integration_items = [
        _FakeItem(tests_dir / 'test_agentcore_transport.py'),
        _FakeItem(tests_dir / 'test_cross_tenant_isolation.py'),
    ]
    outside_item = _FakeItem(Path(__file__).resolve())
    items = [*integration_items, outside_item]

    # ``config`` is unused by the skip-all branch; a placeholder keeps the signature satisfied.
    pytest_collection_modifyitems(SimpleNamespace(), items)  # type: ignore[arg-type]

    # Every integration item is skipped with a reason naming the env var.
    for item in integration_items:
        reasons = _skip_reasons(item)
        assert reasons, f'expected a skip marker on {item.path}'
        assert all(OPT_IN_ENV in reason for reason in reasons)

    # The item outside integration/tests/ is left untouched.
    assert outside_item.applied_markers == []


def test_collection_does_not_skip_when_opt_in_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """With the signal present, the hook leaves integration items unskipped.

    When ``RUN_REMOTE_INTEGRATION_TESTS`` is truthy the collection hook is a no-op; the per-test
    dependency gate (not this hook) governs each test.

    Validates: Requirements Harness location and offline isolation.
    """
    monkeypatch.setenv(OPT_IN_ENV, 'true')

    tests_dir = _integration_tests_dir()
    item = _FakeItem(tests_dir / 'test_agentcore_transport.py')

    pytest_collection_modifyitems(SimpleNamespace(), [item])  # type: ignore[arg-type]

    assert item.applied_markers == []


def test_gating_guard_uses_fspath_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """The guard falls back to the legacy ``fspath`` attribute when ``path`` is absent.

    Some pytest versions expose the collection location as ``fspath`` rather than ``path``. This
    drives the hook with an item that exposes only ``fspath`` under ``integration/tests/`` and
    asserts it is still skipped with the naming reason.

    Validates: Requirements Harness location and offline isolation.
    """
    monkeypatch.delenv(OPT_IN_ENV, raising=False)

    tests_dir = _integration_tests_dir()
    # Object exposing only ``fspath`` (no ``path``) to exercise the fallback branch.
    fspath_item = SimpleNamespace(
        fspath=str(tests_dir / 'test_credential_safety.py'),
        applied_markers=[],
    )
    fspath_item.add_marker = fspath_item.applied_markers.append  # type: ignore[attr-defined]

    pytest_collection_modifyitems(SimpleNamespace(), [fspath_item])  # type: ignore[arg-type,list-item]

    reasons = [
        marker.kwargs['reason']
        for marker in fspath_item.applied_markers
        if getattr(marker, 'name', None) == 'skip' and 'reason' in getattr(marker, 'kwargs', {})
    ]
    assert reasons
    assert all(OPT_IN_ENV in reason for reason in reasons)


def test_conftest_module_imports_no_boto3_at_module_load() -> None:
    """Loading the gating conftest imports no boto3 module attribute.

    A defensive check that the conftest module namespace exposes no ``boto3``/``botocore`` symbol,
    reinforcing that importing and running the gate never pulls in an AWS client library.

    Validates: Requirements Harness location and offline isolation.
    """
    assert not hasattr(conftest_module, 'boto3')
    assert not hasattr(conftest_module, 'botocore')
