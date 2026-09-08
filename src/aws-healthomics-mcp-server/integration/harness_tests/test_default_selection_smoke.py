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


"""Default-selection smoke test for the offline test suite.

This test verifies that the project's default ``uv run pytest`` invocation never runs
the opt-in remote-deployment integration tests: every integration test under
``integration/tests/`` must be skipped/deselected and contribute zero passed and zero
failed results to the default run.

Two complementary, offline checks establish this:

1. **Static configuration check.** The default ``uv run pytest`` selection is governed by
   ``[tool.pytest.ini_options].testpaths`` in ``pyproject.toml``. This test parses that
   file and asserts ``testpaths`` is exactly ``['tests']`` (so the default selection does
   not include ``integration/``) and that the ``integration`` marker is registered as a
   second line of defense.
2. **Actual-selection check.** This test runs pytest in a subprocess scoped to
   ``integration/tests/`` with the Opt_In_Signal removed from the environment, then parses
   the result summary and asserts zero passed, zero failed, zero errors, and that every
   collected item is reported as skipped. This directly demonstrates that the integration
   tests contribute zero passed/failed results when the activation signal is absent.

The test lives in ``integration/harness_tests/`` — separate from the opt-in-gated
``integration/tests/`` suite (so it is not itself gated) and outside ``tests/`` (so it does
not violate the offline-isolation rule). It is pure and offline: it reads a config file and
runs a scoped, self-terminating pytest subprocess with no AWS access or network activity.

Validates: Requirements Harness location and offline isolation.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


# The Opt_In_Signal environment variable that activates the integration suite. It is
# stripped from the subprocess environment so the scoped run observes the default,
# signal-absent behavior.
_OPT_IN_ENV = 'RUN_REMOTE_INTEGRATION_TESTS'

# Bound the subprocess run so the test always terminates quickly even if something hangs.
_SUBPROCESS_TIMEOUT_S = 180.0


def _repo_root() -> Path:
    """Return the repository root.

    This file lives at ``integration/harness_tests/test_default_selection_smoke.py``, so
    the repo root is two directories above the containing package.
    """
    return Path(__file__).resolve().parents[2]


def _load_pytest_config(pyproject_path: Path) -> dict:
    """Return the ``[tool.pytest.ini_options]`` table from ``pyproject.toml``.

    Prefers the stdlib ``tomllib`` (Python 3.11+), falls back to the third-party ``tomli``
    backport, and finally to a tolerant text parse if neither TOML parser is importable.
    """
    raw = pyproject_path.read_bytes()
    try:
        import tomllib  # type: ignore[import-not-found]

        return (
            tomllib.loads(raw.decode('utf-8'))
            .get('tool', {})
            .get('pytest', {})
            .get('ini_options', {})
        )
    except ModuleNotFoundError:
        pass
    try:
        import tomli

        return (
            tomli.loads(raw.decode('utf-8'))
            .get('tool', {})
            .get('pytest', {})
            .get('ini_options', {})
        )
    except ModuleNotFoundError:
        # Tolerant fallback: pull just the ``testpaths`` assignment out of the raw text.
        text = raw.decode('utf-8')
        match = re.search(r'^\s*testpaths\s*=\s*(\[[^\]]*\])', text, re.MULTILINE)
        testpaths: list[str] = []
        if match:
            testpaths = re.findall(r'["\']([^"\']+)["\']', match.group(1))
        return {'testpaths': testpaths}


def _parse_outcome_counts(output: str) -> dict[str, int]:
    """Return a mapping of pytest outcome name -> count parsed from a run's output.

    Scans the combined pytest output for the summary tokens (``N passed``, ``N failed``,
    ``N skipped``, ``N error(s)``, ``N deselected``). Missing tokens default to zero at the
    call site via ``dict.get``.
    """
    counts: dict[str, int] = {}
    for kind in ('passed', 'failed', 'skipped', 'error', 'errors', 'deselected'):
        match = re.search(rf'(\d+)\s+{kind}\b', output)
        if match:
            counts[kind] = int(match.group(1))
    return counts


def test_default_testpaths_excludes_integration() -> None:
    """The default selection collects only ``tests/`` and registers the integration marker.

    ``testpaths = ['tests']`` means a bare ``uv run pytest`` collects only the offline
    suite, so the integration tests under ``integration/tests/`` are never selected and
    contribute zero passed and zero failed results. The registered ``integration`` marker
    provides a ``-m 'not integration'`` second line of defense.

    Validates: Requirements Harness location and offline isolation.
    """
    pyproject_path = _repo_root() / 'pyproject.toml'
    assert pyproject_path.is_file(), f'Expected pyproject.toml at {pyproject_path}'

    config = _load_pytest_config(pyproject_path)

    assert config.get('testpaths') == ['tests'], (
        "Default pytest selection must be testpaths = ['tests'] so that a bare "
        "'uv run pytest' never collects integration/ tests. "
        f'Found: {config.get("testpaths")!r}'
    )

    markers = config.get('markers', [])
    assert any(str(marker).startswith('integration:') for marker in markers), (
        "The 'integration' marker must be registered so integration tests can be "
        f"deselected with -m 'not integration'. Found markers: {markers!r}"
    )


def test_scoped_integration_run_skips_all_without_signal() -> None:
    """A signal-absent pytest run scoped to integration/tests/ skips every test.

    Runs pytest in a subprocess against ``integration/tests/`` with the Opt_In_Signal
    removed from the environment, then asserts the run reports zero passed, zero failed,
    and zero errors while reporting a positive number of skipped tests. This directly
    demonstrates that, under the default (signal-absent) behavior, the integration tests
    contribute zero passed and zero failed results.

    Validates: Requirements Harness location and offline isolation.
    """
    repo_root = _repo_root()

    # Build an environment identical to the current one but with the Opt_In_Signal removed
    # so the subprocess observes the default, signal-absent behavior.
    child_env = {key: value for key, value in os.environ.items() if key != _OPT_IN_ENV}

    completed = subprocess.run(
        [
            sys.executable,
            '-m',
            'pytest',
            'integration/tests/',
            '-p',
            'no:cacheprovider',
            '-o',
            'addopts=',
            '-rs',
            '-q',
        ],
        cwd=str(repo_root),
        env=child_env,
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT_S,
    )

    output = completed.stdout + completed.stderr
    counts = _parse_outcome_counts(output)

    # A skipped-only run exits 0; a non-zero exit signals collection errors or failures.
    assert completed.returncode == 0, (
        'Scoped integration run without the Opt_In_Signal should exit cleanly (skips only). '
        f'Exit code: {completed.returncode}\nOutput:\n{output}'
    )

    assert counts.get('passed', 0) == 0, (
        f'Integration tests must contribute zero passed results by default. Output:\n{output}'
    )
    assert counts.get('failed', 0) == 0, (
        f'Integration tests must contribute zero failed results by default. Output:\n{output}'
    )
    assert counts.get('error', 0) == 0 and counts.get('errors', 0) == 0, (
        f'Integration collection/execution must produce no errors by default. Output:\n{output}'
    )
    assert counts.get('skipped', 0) > 0, (
        'Expected the integration tests to be reported as skipped without the Opt_In_Signal. '
        f'Output:\n{output}'
    )
