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
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
import click
import datetime
import json
import logging
import re
import subprocess
import sys
import tomlkit
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, NewType, Protocol


# Configure logging to stderr
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s', stream=sys.stderr)

Version = NewType('Version', str)
BuildRelease = NewType('BuildRelease', str)
GitHash = NewType('GitHash', str)

# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SemVerRegEx = r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'


class GitHashParamType(click.ParamType):
    """The GitHash paramater type."""

    name = 'git_hash'

    def convert(
        self, value: Any, param: click.Parameter | None, ctx: click.Context | None
    ) -> GitHash | None:
        """Convert the value to a GitHash."""
        if value is None:
            return None

        if not (8 <= len(value) <= 40):
            self.fail(f'Git hash must be between 8 and 40 characters, got {len(value)}')

        if not re.match(r'^[0-9a-fA-F]+$', value):
            self.fail('Git hash must contain only hex digits (0-9, a-f)')

        try:
            # Verify hash exists in repo
            command = ['git', 'rev-parse', '--verify', value]
            # The `value` is verified to match a GitHash above
            subprocess.run(command, check=True, shell=False, capture_output=True)  # nosec B603
        except subprocess.CalledProcessError:
            self.fail(f'Git hash {value} not found in repository')

        return GitHash(value.lower())


GIT_HASH = GitHashParamType()


class Package(Protocol):
    """The package protocol."""

    path: Path

    def package_name(self) -> str:
        """The package name."""
        ...

    def package_version(self) -> str:
        """The package version."""
        ...

    def update_version(self, build_release: BuildRelease) -> str:
        """Update the package version."""
        ...


@dataclass
class NpmPackage:
    """A NPM package."""

    path: Path

    def package_name(self) -> str:
        """Get the package name from the package.json file."""
        with open(self.path / 'package.json', 'r', encoding='utf-8') as f:
            return json.load(f)['name']

    def package_version(self) -> str:
        """Get the package version from the package.json file."""
        with open(self.path / 'package.json', 'r', encoding='utf-8') as f:
            return json.load(f)['version']

    def update_version(self, build_release: BuildRelease) -> str:
        """Update the package.json with a version."""
        with open(self.path / 'package.json', 'r+', encoding='utf-8') as f:
            data = json.load(f)
            matched = re.match(SemVerRegEx, data['version'])
            version = (
                '.'.join([matched.group('major'), matched.group('minor'), matched.group('patch')])
                + '+'
                + build_release
            )
            data['version'] = version
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
            return version


@dataclass
class PyPiPackage:
    """A PyPi package."""

    path: Path

    def package_name(self) -> str:
        """Get the package name from the pyproject.toml file."""
        with open(self.path / 'pyproject.toml', encoding='utf-8') as f:
            toml_data = tomlkit.parse(f.read())
            name = toml_data.get('project', {}).get('name')
            if not name:
                raise ValueError('No name in pyproject.toml project section')
            return str(name)

    def package_version(self) -> str:
        """Read the version from the pyproject.toml file."""
        with open(self.path / 'pyproject.toml', encoding='utf-8') as f:
            toml_data = tomlkit.parse(f.read())
            version = toml_data.get('project', {}).get('version')
            if not version:
                raise ValueError('No version in pyproject.toml project section')
            return str(version)

    def update_version(self, build_release: BuildRelease) -> str:
        """Update version in pyproject.toml."""
        version_str = self.package_version()
        with open(self.path / 'pyproject.toml', encoding='utf-8') as f:
            data = tomlkit.parse(f.read())
            # Access the version safely from tomlkit document
            project_table = data.get('project')
            if project_table is None:
                raise ValueError('No project section in pyproject.toml')
            matched = re.match(SemVerRegEx, version_str)
            version = (
                '.'.join([matched.group('major'), matched.group('minor'), matched.group('patch')])
                + '+'
                + build_release
            )

            # Update the version safely
            project_table['version'] = version

        with open(self.path / 'pyproject.toml', 'w', encoding='utf-8') as f:
            f.write(tomlkit.dumps(data))
        return version


def has_changes(path: Path, git_hash: GitHash) -> bool:
    """Check if any files changed between current state and git hash."""
    try:
        logging.debug('Checking changes in %s since %s', path, git_hash)  # import logging

        # Get the repository root directory
        command = ['git', 'rev-parse', '--show-toplevel']
        repo_root = subprocess.run(
            command,
            check=True,
            shell=False,
            capture_output=True,
            text=True,
        ).stdout.strip()

        try:
            # Get the relative path from repo root to package directory
            rel_path = path.relative_to(Path(repo_root))

            # Run git diff from repo root, but filter by package path
            command = ['git', 'diff', '--name-only', git_hash, '--', str(rel_path)]
            output = subprocess.run(
                command,
                cwd=repo_root,  # Run from repo root
                check=True,
                shell=False,
                capture_output=True,
                text=True,
            )

            logging.debug('Git command: git diff --name-only %s -- %s', git_hash, rel_path)
            logging.debug('Working directory: %s', repo_root)

            changed_files = [Path(f) for f in output.stdout.splitlines()]
            logging.debug('Changed files: %s', changed_files)

            relevant_files = [
                f for f in changed_files if f.suffix in ['.py', '.ts', '.toml', '.lock', '.json']
            ]
            logging.debug('Relevant files: %s', relevant_files)

            return len(relevant_files) >= 1
        except ValueError:
            # Handle case where path is not relative to repo_root
            logging.debug('Path error: %s is not inside repo root %s', path, repo_root)
            logging.debug('Using absolute path as fallback')

            # Use absolute path as fallback
            command = ['git', 'diff', '--name-only', git_hash]
            output = subprocess.run(
                command,
                check=True,
                shell=False,
                capture_output=True,
                text=True,
            )

            # Filter to only include files under the specified path
            path_str = str(path).rstrip('/') + '/'
            changed_files = [Path(f) for f in output.stdout.splitlines() if f.startswith(path_str)]

            relevant_files = [
                f for f in changed_files if f.suffix in ['.py', '.ts', '.toml', '.lock', '.json']
            ]
            return len(relevant_files) >= 1
    except subprocess.CalledProcessError as e:
        logging.error('Error executing git command: %s', e)
        return False


def gen_version() -> Version:
    """Generate release version based on current time."""
    now = datetime.datetime.now(datetime.UTC)
    return Version(f'{now.year}.{now.month}.{gen_buildrelease()}')


def gen_buildrelease() -> BuildRelease:
    """Generate version based on current UTC timestamp."""
    now = datetime.datetime.now(datetime.UTC)
    # return Patch(f"{int(now.timestamp())}")
    return BuildRelease(f'{now.year:04d}{now.day:02d}{now.hour:02d}{now.minute:02d}')


def find_changed_packages(directory: Path, git_hash: GitHash) -> Iterator[Package]:
    """This looks for changed packages."""
    # Debug info
    logging.debug('Searching for changed packages in %s since %s', directory, git_hash)

    # List all PyPI packages
    for path in directory.glob('*/pyproject.toml'):
        logging.debug('Found PyPI package at %s', path.parent)
        # Check if it has relevant changes
        if has_changes(path.parent, git_hash):
            yield PyPiPackage(path.parent)

    # List all NPM packages
    for path in directory.glob('*/package.json'):
        logging.debug('Found NPM package at %s', path.parent)
        # Check if it has relevant changes
        if has_changes(path.parent, git_hash):
            yield NpmPackage(path.parent)


@click.group()
def cli():
    """Simply pass."""
    pass


@cli.command('update-packages')
@click.option('--directory', type=click.Path(exists=True, path_type=Path), default=Path.cwd())
@click.argument('git_hash', type=GIT_HASH)
def update_packages(directory: Path, git_hash: GitHash) -> int:
    """Updates the package version with a patch."""
    # Detect package type
    path = directory.resolve(strict=True)
    build_release = gen_buildrelease()

    for package in find_changed_packages(path, git_hash):
        name = package.package_name()
        version = package.update_version(build_release)

        click.echo(f'{name}@{version}')

    return 0


@cli.command('generate-notes')
@click.option('--directory', type=click.Path(exists=True, path_type=Path), default=Path.cwd())
@click.argument('git_hash', type=GIT_HASH)
def generate_notes(directory: Path, git_hash: GitHash) -> int:
    """Generates detailed release notes."""
    # Detect package type
    path = directory.resolve(strict=True)
    release = gen_version()

    click.echo(f'# Release: {release}')
    click.echo('')
    click.echo('## Updated packages')
    for package in find_changed_packages(path, git_hash):
        name = package.package_name()
        version = package.package_version()
        click.echo(f'- {name}@{version}')
    click.echo('')

    return 0


@cli.command('generate-version')
def generate_version() -> int:
    """Generates a version."""
    # Detect package type
    click.echo(gen_version())
    return 0


@cli.command('generate-matrix')
@click.option('--directory', type=click.Path(exists=True, path_type=Path), default=Path.cwd())
@click.option('--npm', is_flag=True, default=False)
@click.option('--pypi', is_flag=True, default=False)
@click.argument('git_hash', type=GIT_HASH)
def generate_matrix(directory: Path, git_hash: GitHash, pypi: bool, npm: bool) -> int:
    """Outputs JSON for changes in the repository under a path."""
    # Detect package type
    path = directory.resolve(strict=True)

    changes = []
    for package in find_changed_packages(path, git_hash):
        pkg = package.path.relative_to(path)
        if npm and isinstance(package, NpmPackage):
            changes.append(str(pkg))
        if pypi and isinstance(package, PyPiPackage):
            changes.append(str(pkg))

    click.echo(json.dumps(changes))
    return 0


if __name__ == '__main__':
    sys.exit(cli())
