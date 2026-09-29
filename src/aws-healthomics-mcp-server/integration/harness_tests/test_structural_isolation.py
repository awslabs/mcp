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


"""Structural isolation smoke test for the offline test suite.

This test statically verifies that the Offline_Test_Suite (the top-level ``tests/``
directory) stays free of any dependency on the opt-in ``integration`` package. It
parses every ``*.py`` module under ``tests/`` with the ``ast`` module and asserts
that none of them import the ``integration`` package (neither ``import integration``,
``from integration ...``, nor ``import integration.something``).

The test lives in ``integration/harness_tests/`` — separate from the opt-in-gated
``integration/tests/`` suite (so it is not gated) and outside ``tests/`` (so it does
not itself violate the isolation rule it enforces). It is pure and offline: it only
reads and parses source files, with no AWS access or network activity.

Validates: Requirements Harness location and offline isolation.
"""

import ast
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walk up from ``start`` to the repo root.

    The repo root is the first ancestor directory that contains both a ``tests``
    directory and an ``integration`` directory, or, failing that, one that contains a
    ``pyproject.toml`` marker. Falls back to ``parents[2]`` (this file is at
    ``integration/harness_tests/test_structural_isolation.py``) if neither is found.
    """
    for candidate in [start, *start.parents]:
        has_tests = (candidate / 'tests').is_dir()
        has_integration = (candidate / 'integration').is_dir()
        if has_tests and has_integration:
            return candidate
        if (candidate / 'pyproject.toml').is_file() and has_tests:
            return candidate
    return start.parents[2]


def _imports_integration(tree: ast.AST) -> bool:
    """Return True if the parsed module imports the ``integration`` package.

    Detects ``import integration``, ``import integration.something``, and
    ``from integration ...``/``from integration.something ...`` forms by inspecting
    ``ast.Import`` and ``ast.ImportFrom`` nodes for a module named ``integration`` or
    one whose dotted path starts with ``integration.``.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == 'integration' or name.startswith('integration.'):
                    return True
        elif isinstance(node, ast.ImportFrom):
            # Ignore relative imports (level > 0); they cannot reach the top-level
            # ``integration`` package from within ``tests/``.
            module = node.module
            if node.level == 0 and module is not None:
                if module == 'integration' or module.startswith('integration.'):
                    return True
    return False


def _offline_test_files() -> list[Path]:
    """Return every ``*.py`` file under the top-level ``tests/`` directory.

    Excludes ``__pycache__`` directories. The list is sorted for deterministic
    reporting.
    """
    repo_root = _find_repo_root(Path(__file__).resolve())
    tests_dir = repo_root / 'tests'
    assert tests_dir.is_dir(), f'Expected offline test suite directory at {tests_dir}'
    files = [path for path in tests_dir.rglob('*.py') if '__pycache__' not in path.parts]
    return sorted(files)


def test_offline_suite_does_not_import_integration_package() -> None:
    """No module under ``tests/`` imports the ``integration`` package.

    Validates: Requirements Harness location and offline isolation.
    """
    offending: list[str] = []
    for path in _offline_test_files():
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(path))
        if _imports_integration(tree):
            offending.append(str(path))

    assert not offending, (
        'The offline test suite (tests/) must not import the integration package. '
        f'Offending files: {offending}'
    )
