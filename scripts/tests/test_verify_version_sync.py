#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pytest>=8.0.0"
# ]
# ///
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

import os
import pytest
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / 'verify_version_sync.py'


def _make_package(tmp_path: Path, pyproject: str) -> Path:
    """Create a bare package directory with the given pyproject.toml content.

    Args:
        tmp_path: Pytest's per-test temporary directory.
        pyproject: Full text to write as the package's pyproject.toml.

    Returns:
        The package directory, ready to have an awslabs/ tree added to it.
    """
    package_dir = tmp_path / 'pkg'
    package_dir.mkdir()
    (package_dir / 'pyproject.toml').write_text(pyproject, encoding='utf-8')
    return package_dir


def _write_module(package_dir: Path, relative_path: str, content: str) -> None:
    """Write a Python module under a package directory, creating parents as needed.

    Args:
        package_dir: The package directory returned by `_make_package`.
        relative_path: Path relative to `package_dir`, e.g. `awslabs/pkg/__init__.py`.
        content: Source text for the module.
    """
    module_path = package_dir / relative_path
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text(content, encoding='utf-8')


def _run(package_dir: Path) -> subprocess.CompletedProcess:
    """Invoke verify_version_sync.py against a package directory, the same way CI does.

    Args:
        package_dir: Directory to pass as the script's `directory` argument.

    Returns:
        The completed subprocess, with stdout/stderr captured as text, so the
        caller can assert on the real exit code rather than a mocked result.
    """
    # The script's click.echo() calls carry literal U+2713/U+2717 checkmarks. Force
    # UTF-8 so this is deterministic on every platform, matching ubuntu-latest's
    # default rather than a Windows console's cp1252 default, which cannot encode
    # them and would otherwise fail every run for a reason unrelated to this check.
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run(
        ['uv', 'run', '--script', str(SCRIPT), str(package_dir)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_matching_literal_passes(tmp_path: Path) -> None:
    """A version literal that agrees with pyproject.toml is not a violation."""
    package_dir = _make_package(tmp_path, '[project]\nname = "pkg"\nversion = "1.2.3"\n')
    _write_module(package_dir, 'awslabs/pkg/__init__.py', "__version__ = '1.2.3'\n")

    result = _run(package_dir)

    assert result.returncode == 0, result.stderr


def test_mismatched_literal_fails(tmp_path: Path) -> None:
    """A version literal that disagrees with pyproject.toml blocks with a non-zero exit."""
    package_dir = _make_package(tmp_path, '[project]\nname = "pkg"\nversion = "1.2.3"\n')
    _write_module(package_dir, 'awslabs/pkg/__init__.py', "__version__ = '9.9.9'\n")

    result = _run(package_dir)

    assert result.returncode == 1
    assert '9.9.9' in result.stderr
    assert '1.2.3' in result.stderr


def test_indirect_assignment_without_literal_passes(tmp_path: Path) -> None:
    """`__version__ = NAME` with no literal is the correct convention, not a failure.

    The value assigned is a Name node, not a string Constant, so the AST walk in
    `version_literals` must skip it even though a literal with an unrelated name
    exists elsewhere in the tree.
    """
    package_dir = _make_package(tmp_path, '[project]\nname = "pkg"\nversion = "3.0.0"\n')
    _write_module(
        package_dir,
        'awslabs/pkg/__init__.py',
        'from ._meta import SOME_NAME\n__version__ = SOME_NAME\n',
    )
    _write_module(package_dir, 'awslabs/pkg/_meta.py', "SOME_NAME = '1.2.3'\n")

    result = _run(package_dir)

    assert result.returncode == 0, result.stderr


def test_literal_in_nested_non_init_module_is_caught(tmp_path: Path) -> None:
    """A version literal buried in a nested, non-__init__.py module is still found.

    This is the release script's blind spot: its regex only ever looked at
    __init__.py. The AST walk here uses `Path.rglob('*.py')`, so a literal in
    awslabs/pkg/utilities/consts.py must be caught too.
    """
    package_dir = _make_package(tmp_path, '[project]\nname = "pkg"\nversion = "2.0.0"\n')
    _write_module(package_dir, 'awslabs/pkg/__init__.py', '')
    _write_module(package_dir, 'awslabs/pkg/utilities/consts.py', "SERVER_VERSION = '1.0.0'\n")

    result = _run(package_dir)

    assert result.returncode == 1
    assert 'utilities' in result.stderr
    assert 'consts.py' in result.stderr


def test_no_awslabs_directory_passes(tmp_path: Path) -> None:
    """A package with no awslabs/ tree at all has nothing to check."""
    package_dir = _make_package(tmp_path, '[project]\nname = "pkg"\nversion = "1.0.0"\n')

    result = _run(package_dir)

    assert result.returncode == 0, result.stderr


def test_no_version_key_passes(tmp_path: Path) -> None:
    """A pyproject.toml with no version key has no source of truth to compare against."""
    package_dir = _make_package(tmp_path, '[project]\nname = "pkg"\n')
    _write_module(package_dir, 'awslabs/pkg/__init__.py', "__version__ = '1.2.3'\n")

    result = _run(package_dir)

    assert result.returncode == 0, result.stderr


if __name__ == '__main__':
    sys.exit(pytest.main([__file__]))
