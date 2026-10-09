#!/usr/bin/env uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1.8",
#     "tomlkit>=0.13.2"
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

import ast
import click
import logging
import re
import sys
import tomlkit
from pathlib import Path


# Names that carry a server's own version at runtime. A string literal assigned to
# any of these is a second copy of the version already declared in pyproject.toml.
VERSION_NAMES = frozenset(
    {
        '__version__',
        'MCP_SERVER_VERSION',
        'SERVER_VERSION',
    }
)

# Only literals that look like a version are compared. This keeps the check off
# unrelated strings that happen to be assigned to one of the names above.
VERSION_LITERAL_REGEX = re.compile(r'^\d+\.\d+\.\d+')


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    stream=sys.stderr,
)


def declared_version(package_dir: Path) -> str | None:
    """Read the version declared in a server's pyproject.toml, the source of truth."""
    pyproject = package_dir / 'pyproject.toml'
    if not pyproject.exists():
        return None
    data = tomlkit.parse(pyproject.read_text(encoding='utf-8'))
    project = data.get('project')
    if project is None:
        return None
    version = project.get('version')
    return str(version) if version is not None else None


def version_literals(source_file: Path) -> list[tuple[int, str, str]]:
    """Find version string literals assigned to a known version name.

    Returns (line number, assigned name, literal value) for each one. Parsing the
    AST rather than matching a regex is deliberate: an indirect assignment such as
    `__version__ = MCP_SERVER_VERSION` carries no literal and must not be mistaken
    for one, while the literal it points at lives in another file entirely.
    """
    try:
        tree = ast.parse(source_file.read_text(encoding='utf-8'), filename=str(source_file))
    except SyntaxError as e:
        raise ValueError(f'Cannot parse {source_file}: {e}')

    found: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [t.id for t in targets if isinstance(t, ast.Name) and t.id in VERSION_NAMES]
        if not names:
            continue
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        if not VERSION_LITERAL_REGEX.match(value.value):
            continue
        for name in names:
            found.append((node.lineno, name, value.value))
    return found


@click.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
def main(directory: str) -> int:
    """Check that no hardcoded version in a server disagrees with its pyproject.toml.

    The published version comes from pyproject.toml alone, so any version literal in
    the package is a duplicate that a release can leave behind. Reading the version
    from importlib.metadata instead removes the duplicate; this check catches the
    ones that remain before they ship a wrong version to AWS in the User-Agent.
    """
    package_dir = Path(directory)
    click.echo(f'Looking {directory}')

    awslabs_dir = package_dir / 'awslabs'
    if not awslabs_dir.exists():
        click.echo(f'✓ No awslabs directory in {directory}')
        return 0

    expected = declared_version(package_dir)
    if expected is None:
        click.echo(f'✓ No declared version in {directory}')
        return 0

    mismatches: list[str] = []
    for source_file in sorted(awslabs_dir.rglob('*.py')):
        for lineno, name, literal in version_literals(source_file):
            if literal != expected:
                mismatches.append(
                    f'{source_file}:{lineno}: {name} = {literal!r} but pyproject.toml '
                    f'declares {expected!r}'
                )

    if mismatches:
        for mismatch in mismatches:
            click.echo(f'✗ {mismatch}', err=True)
        click.echo(
            '  Read the version from importlib.metadata.version(<distribution>) so there '
            'is only one source of truth.',
            err=True,
        )
        sys.exit(1)

    click.echo(f'✓ OK: version in sync for {directory}')
    return 0


if __name__ == '__main__':
    main()
