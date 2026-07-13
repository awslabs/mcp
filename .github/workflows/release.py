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
import click
import json
import logging
import re
import sys
import tomlkit
from dataclasses import dataclass
from pathlib import Path
from typing import NewType, Protocol


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    stream=sys.stderr,
)

Version = NewType('Version', str)
SemVerRegEx = r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
PACKAGE_NAME_REGEX = r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$'
DIRECTORY_NAME_REGEX = r'^[a-zA-Z0-9_-]+$'
MAX_VERSION_COMPONENT = sys.maxsize  # sys.maxsize is 9223372036854775807
MAX_PACKAGE_NAME_LENGTH = 100
MAX_PATH_DEPTH = 15


def validate_path_security(path: Path, allowed_base: Path = None) -> Path:
    """Validate path for security issues including path traversal.

    Args:
        path: Path to validate
        allowed_base: Optional base path that the resolved path must be within

    Returns:
        Resolved path if valid

    Raises:
        ValueError: If path is invalid or contains security issues
    """
    try:
        resolved_path = path.resolve()
        if len(resolved_path.parts) > MAX_PATH_DEPTH:
            raise ValueError(f'Path depth exceeds maximum allowed ({MAX_PATH_DEPTH}): {path}')
        if allowed_base:
            allowed_base_resolved = allowed_base.resolve()
            try:
                resolved_path.relative_to(allowed_base_resolved)
            except ValueError:
                raise ValueError(
                    f'Path traversal detected: {path} is outside allowed base {allowed_base}'
                )
        if not resolved_path.exists():
            raise ValueError(f'Path does not exist: {path}')
        logging.debug(f'Path validation successful: {resolved_path}')
        return resolved_path
    except Exception as e:
        logging.error(f'Path validation failed for {path}: {e}')
        raise ValueError(f'Invalid path: {path} - {e}')


def validate_package_name(name: str) -> str:
    """Validate and sanitize package name.

    Args:
        name: Package name to validate

    Returns:
        Validated package name

    Raises:
        ValueError: If package name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError('Package name cannot be empty or non-string')
    if len(name) > MAX_PACKAGE_NAME_LENGTH:
        raise ValueError(
            f'Package name exceeds maximum length ({MAX_PACKAGE_NAME_LENGTH}): {name}'
        )
    if not re.match(PACKAGE_NAME_REGEX, name):
        raise ValueError(f'Invalid package name format: {name}')
    suspicious_patterns = [
        r'\.\.',
        r'//',
        r'\\\\',
        r'[<>:"|?*]',
        r'^\.',  # Path traversal and invalid chars
        r'(con|prn|aux|nul|com[1-9]|lpt[1-9])$',  # Windows reserved names
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            raise ValueError(f'Package name contains suspicious pattern: {name}')
    logging.debug(f'Package name validation successful: {name}')
    return name


def validate_version_format(version: str) -> bool:
    """Validate version follows semantic versioning with additional security checks.

    Args:
        version: Version string to validate

    Returns:
        True if valid, False otherwise
    """
    if not version or not isinstance(version, str):
        return False
    if len(version) > 50:
        return False
    match = re.match(SemVerRegEx, version)
    if not match:
        return False
    try:
        major = int(match.group('major'))
        minor = int(match.group('minor'))
        patch = int(match.group('patch'))
        if any(component > MAX_VERSION_COMPONENT for component in [major, minor, patch]):
            logging.warning(
                f'Version component exceeds maximum ({MAX_VERSION_COMPONENT}): {version}'
            )
            if major >= MAX_VERSION_COMPONENT:
                logging.warning('Major version component is at maximum, failing validation')
                return False  # Bumping Major version back to zero doesn't make sense
            return True  # Allow large components for bumping to zero
    except (ValueError, TypeError):
        return False
    return True


def secure_file_read(file_path: Path, encoding: str = 'utf-8') -> str:
    """Securely read file with validation.

    Args:
        file_path: Path to file
        encoding: File encoding

    Returns:
        File content

    Raises:
        ValueError: If file cannot be read securely
    """
    validated_path = validate_path_security(file_path)
    try:
        file_size = validated_path.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError(f'File too large: {file_size} bytes')
        with open(validated_path, 'r', encoding=encoding) as f:
            content = f.read()
        logging.debug(f'File read successful: {validated_path}')
        return content
    except Exception as e:
        logging.error(f'Secure file read failed for {file_path}: {e}')
        raise ValueError(f'Cannot read file securely: {file_path} - {e}')


def secure_file_write(file_path: Path, content: str, encoding: str = 'utf-8') -> None:
    """Securely write file with validation.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding

    Raises:
        ValueError: If file cannot be written securely
    """
    if not content or not isinstance(content, str):
        raise ValueError('Content cannot be empty or non-string')
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise ValueError(f'Content too large: {len(content)} characters')
    try:
        parent_dir = file_path.parent
        validate_path_security(parent_dir)
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        file_path.chmod(0o644)
        logging.debug(f'File write successful: {file_path}')
    except Exception as e:
        logging.error(f'Secure file write failed for {file_path}: {e}')
        raise ValueError(f'Cannot write file securely: {file_path} - {e}')


class Package(Protocol):
    """The package protocol with security enhancements."""

    path: Path

    def package_name(self) -> str:
        """The package name."""
        ...

    def package_version(self) -> str:
        """The package version."""
        ...

    def bump_version(self) -> str:
        """Update the package version."""
        ...


@dataclass
class NpmPackage:
    """A NPM package with security enhancements."""

    path: Path

    def __post_init__(self):
        """Validate path on initialization."""
        self.path = validate_path_security(self.path)

    def package_name(self) -> str:
        """Get the package name from the package.json file with security validation."""
        try:
            package_json_path = self.path / 'package.json'
            content = secure_file_read(package_json_path)
            data = json.loads(content)
            if 'name' not in data:
                raise ValueError("No 'name' field in package.json")
            name = str(data['name'])
            return validate_package_name(name)
        except Exception as e:
            logging.error(f'Failed to get NPM package name from {self.path}: {e}')
            raise ValueError(f'Cannot read NPM package name: {e}')

    def package_version(self) -> str:
        """Get the package version from the package.json file with security validation."""
        try:
            package_json_path = self.path / 'package.json'
            content = secure_file_read(package_json_path)
            data = json.loads(content)
            if 'version' not in data:
                raise ValueError("No 'version' field in package.json")
            version = str(data['version'])
            if not validate_version_format(version):
                raise ValueError(f'Invalid version format: {version}')
            return version
        except Exception as e:
            logging.error(f'Failed to get NPM package version from {self.path}: {e}')
            raise ValueError(f'Cannot read NPM package version: {e}')

    def bump_version(self) -> str:
        """Update the package.json with a bumped version with security validation."""
        try:
            package_json_path = self.path / 'package.json'
            content = secure_file_read(package_json_path)
            data = json.loads(content)
            current_version = str(data.get('version', ''))
            if not validate_version_format(current_version):
                raise ValueError(f'Invalid current version format: {current_version}')
            matched = re.match(SemVerRegEx, current_version)
            if not matched:
                raise ValueError(f'Cannot parse version: {current_version}')
            major = int(matched.group('major'))
            minor = int(matched.group('minor'))
            patch = int(matched.group('patch'))
            patch += 1
            if patch > MAX_VERSION_COMPONENT:
                patch = 0
                minor += 1
                if minor > MAX_VERSION_COMPONENT:
                    minor = 0
                    major += 1
                    if major > MAX_VERSION_COMPONENT:
                        raise ValueError('Version overflow detected')
            new_version = f'{major}.{minor}.{patch}'
            if not validate_version_format(new_version):
                raise ValueError(f'Generated invalid version: {new_version}')
            data['version'] = new_version
            updated_content = json.dumps(data, indent=2, ensure_ascii=False)
            secure_file_write(package_json_path, updated_content)
            logging.info(f'NPM package version bumped: {current_version} -> {new_version}')
            return new_version

        except Exception as e:
            logging.error(f'Failed to bump NPM package version in {self.path}: {e}')
            raise ValueError(f'Cannot bump NPM package version: {e}')


@dataclass
class PyPiPackage:
    """A PyPi package with security enhancements."""

    path: Path

    def __post_init__(self):
        """Validate path on initialization."""
        self.path = validate_path_security(self.path)

    def package_name(self) -> str:
        """Get the package name from the pyproject.toml file with security validation."""
        try:
            pyproject_path = self.path / 'pyproject.toml'
            content = secure_file_read(pyproject_path)
            toml_data = tomlkit.parse(content)
            project_section = toml_data.get('project')
            if not project_section:
                raise ValueError('No project section in pyproject.toml')
            name = project_section.get('name')
            if not name:
                raise ValueError('No name in pyproject.toml project section')
            name_str = str(name)
            return validate_package_name(name_str)
        except Exception as e:
            logging.error(f'Failed to get PyPI package name from {self.path}: {e}')
            raise ValueError(f'Cannot read PyPI package name: {e}')

    def package_version(self) -> str:
        """Read the version from the pyproject.toml file with security validation."""
        try:
            pyproject_path = self.path / 'pyproject.toml'
            content = secure_file_read(pyproject_path)
            toml_data = tomlkit.parse(content)
            project_section = toml_data.get('project')
            if not project_section:
                raise ValueError('No project section in pyproject.toml')
            version = project_section.get('version')
            if not version:
                raise ValueError('No version in pyproject.toml project section')
            version_str = str(version)
            if not validate_version_format(version_str):
                raise ValueError(f'Invalid version format: {version_str}')
            return version_str
        except Exception as e:
            logging.error(f'Failed to get PyPI package version from {self.path}: {e}')
            raise ValueError(f'Cannot read PyPI package version: {e}')

    def bump_version(self) -> str:
        """Update version in pyproject.toml and __init__.py with security validation."""
        try:
            package_name = self.package_name()
            current_version = self.package_version()
            matched = re.match(SemVerRegEx, current_version)
            if not matched:
                raise ValueError(f'Cannot parse version: {current_version}')
            major = int(matched.group('major'))
            minor = int(matched.group('minor'))
            patch = int(matched.group('patch'))
            patch += 1
            if patch > MAX_VERSION_COMPONENT:
                patch = 0
                minor += 1
                if minor > MAX_VERSION_COMPONENT:
                    minor = 0
                    major += 1
                    if major > MAX_VERSION_COMPONENT:
                        raise ValueError('Version overflow detected')
            new_version = f'{major}.{minor}.{patch}'
            if not validate_version_format(new_version):
                raise ValueError(f'Generated invalid version: {new_version}')
            pyproject_path = self.path / 'pyproject.toml'
            content = secure_file_read(pyproject_path)
            data = tomlkit.parse(content)
            project_table = data.get('project')
            if project_table is None:
                raise ValueError('No project section in pyproject.toml')
            project_table['version'] = new_version
            updated_content = tomlkit.dumps(data)
            secure_file_write(pyproject_path, updated_content)
            if package_name.startswith('awslabs.'):
                module_name = package_name[8:].replace('-', '_')
                if not re.match(DIRECTORY_NAME_REGEX, module_name):
                    raise ValueError(f'Invalid module name derived from package: {module_name}')
                init_file = self.path / 'awslabs' / module_name / '__init__.py'
                try:
                    validate_path_security(init_file, self.path)
                    if init_file.exists():
                        init_content = secure_file_read(init_file)
                        version_pattern = (
                            r'__version__\s*=\s*(?P<start>[\'"])[^\'"]*(?P<end>[\'"])'
                        )
                        new_version_line = r'__version__ = \g<start>' + new_version + r'\g<end>'
                        if re.search(version_pattern, init_content):
                            updated_init_content = re.sub(
                                version_pattern, new_version_line, init_content
                            )
                            secure_file_write(init_file, updated_init_content)
                            click.echo(f"Updated {init_file}: __version__ = '{new_version}'")
                        else:
                            click.echo(f'Warning: No __version__ found in {init_file}')
                    else:
                        click.echo(f'Warning: {init_file} not found for package {package_name}')
                except ValueError as e:
                    click.echo(f'Warning: Cannot update __init__.py safely: {e}')
            else:
                click.echo(
                    f"Warning: Package {package_name} doesn't follow awslabs.* naming convention"
                )
            logging.info(f'PyPI package version bumped: {current_version} -> {new_version}')
            return new_version
        except Exception as e:
            logging.error(f'Failed to bump PyPI package version in {self.path}: {e}')
            raise ValueError(f'Cannot bump PyPI package version: {e}')


@click.group()
def cli():
    """Release management CLI with security enhancements."""
    pass


@cli.command('pin-dependencies')
@click.option('--directory', type=click.Path(exists=True, path_type=Path), default=Path.cwd())
def pin_dependencies(directory: Path) -> int:
    """Pin ALL dependencies (direct + transitive) to exact versions from uv.lock.

    Reads the uv.lock file in the given directory and:
    1. Rewrites existing dependencies in pyproject.toml to use == (exact) pins
    2. Adds all remaining transitive dependencies from uv.lock as new entries

    This ensures that packages published to PyPI install the exact same
    dependency tree that was tested during development — including every
    transitive dependency. This is appropriate for tool packages (MCP servers,
    CLIs) that run in isolated environments via uvx/pipx.

    Only registry (PyPI) packages are pinned; editable/local/path sources are
    skipped. Extras on dependency specifiers (e.g. mcp[cli]) are preserved.
    """
    try:
        validated_directory = validate_path_security(directory)
        pyproject_path = validated_directory / 'pyproject.toml'
        lock_path = validated_directory / 'uv.lock'

        if not pyproject_path.exists():
            raise ValueError(f'pyproject.toml not found in {validated_directory}')
        if not lock_path.exists():
            raise ValueError(f'uv.lock not found in {validated_directory}')

        # Parse uv.lock to build {normalized_name: (original_name, version)} mapping
        lock_content = secure_file_read(lock_path)
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # Python < 3.11
        lock_data = tomllib.loads(lock_content)
        locked_packages: dict[str, tuple[str, str]] = {}
        for pkg in lock_data.get('package', []):
            source = pkg.get('source', {})
            # Only pin registry packages (from PyPI), skip editable/local/path
            if 'editable' in source or 'directory' in source or 'path' in source:
                continue
            name = pkg.get('name', '')
            version = pkg.get('version', '')
            if name and version:
                locked_packages[_normalize_name(name)] = (name, version)

        logging.info(f'Loaded {len(locked_packages)} locked package versions from uv.lock')

        # Read and rewrite pyproject.toml
        pyproject_content = secure_file_read(pyproject_path)
        data = tomlkit.parse(pyproject_content)
        project_section = data.get('project')
        if not project_section:
            raise ValueError('No project section in pyproject.toml')

        # Get the project's own name so we don't add it as a dependency
        project_name = project_section.get('name', '')
        project_normalized = _normalize_name(str(project_name)) if project_name else ''

        dependencies = project_section.get('dependencies')
        if dependencies is None:
            dependencies = tomlkit.array()
            project_section['dependencies'] = dependencies

        # Track which locked packages are already covered by direct deps
        covered: set[str] = set()
        pinned_count = 0

        # Phase 1: Pin existing direct dependencies to their locked versions
        for i, dep_str in enumerate(dependencies):
            pkg_name = re.split(r'[><=!~\[;]', str(dep_str).strip())[0].strip()
            normalized = _normalize_name(pkg_name)
            covered.add(normalized)
            pinned = _pin_dependency(str(dep_str), locked_packages)
            if pinned != str(dep_str):
                dependencies[i] = pinned
                pinned_count += 1
                logging.info(f'Pinned: {dep_str} -> {pinned}')

        # Phase 2: Add all remaining transitive dependencies from uv.lock
        added_count = 0
        for normalized, (original_name, version) in sorted(locked_packages.items()):
            if normalized in covered:
                continue
            if normalized == project_normalized:
                continue
            dep_entry = f'{original_name}=={version}'
            dependencies.append(dep_entry)
            added_count += 1
            logging.info(f'Added transitive: {dep_entry}')

        if pinned_count == 0 and added_count == 0:
            click.echo('All dependencies already pinned, no changes needed')
            return 0

        updated_content = tomlkit.dumps(data)
        secure_file_write(pyproject_path, updated_content)
        click.echo(
            f'Pinned {pinned_count} direct + added {added_count} transitive '
            f'dependencies in {pyproject_path}'
        )
        return 0

    except Exception as e:
        logging.error(f'Pin dependencies failed: {e}')
        click.echo(f'Error: {e}', err=True)
        return 1


def _normalize_name(name: str) -> str:
    """Normalize a Python package name for comparison (PEP 503)."""
    return re.sub(r'[-_.]+', '-', name).lower()


def _pin_dependency(dep_str: str, locked_packages: dict[str, tuple[str, str]]) -> str:
    """Rewrite a dependency string to use == with the locked version.

    Handles dependency specifiers like:
      - "boto3>=1.40.5"        -> "boto3==1.42.62"
      - "mcp[cli]>=1.23.0"    -> "mcp[cli]==1.26.0"
      - "loguru==0.7.3"       -> "loguru==0.7.3" (unchanged)
      - "pkg ; python_version<'3.11'" -> preserves markers
    """
    # Split off environment markers (e.g. "; python_version < '3.11'")
    marker_sep = ';'
    marker_part = ''
    base = dep_str
    if marker_sep in dep_str:
        base, marker_part = dep_str.split(marker_sep, 1)
        marker_part = marker_sep + marker_part

    # Extract extras (e.g. [cli]) and package name
    extras = ''
    name_part = base.strip()
    if '[' in name_part:
        bracket_start = name_part.index('[')
        bracket_end = name_part.index(']') + 1
        extras = name_part[bracket_start:bracket_end]
        name_part = name_part[:bracket_start] + name_part[bracket_end:]

    # Extract just the package name (strip version specifiers)
    pkg_name = re.split(r'[><=!~]', name_part.strip())[0].strip()
    normalized = _normalize_name(pkg_name)

    if normalized not in locked_packages:
        logging.warning(f'No locked version found for {pkg_name}, keeping as-is')
        return dep_str

    _, locked_version = locked_packages[normalized]
    return f'{pkg_name}{extras}=={locked_version}{marker_part}'


@cli.command('bump-package')
@click.option('--directory', type=click.Path(exists=True, path_type=Path), default=Path.cwd())
def bump_package(directory: Path) -> int:
    """Updates the package version with a patch bump and security validation."""
    try:
        validated_directory = validate_path_security(directory)
        if not re.match(DIRECTORY_NAME_REGEX, validated_directory.name):
            raise ValueError(f'Invalid directory name format: {validated_directory.name}')
        logging.debug(f'Processing directory: {validated_directory}')
        pyproject_file = validated_directory / 'pyproject.toml'
        package_json_file = validated_directory / 'package.json'
        processed = False
        if pyproject_file.exists():
            logging.debug(f'Found PyPI package at {validated_directory}')
            try:
                package = PyPiPackage(validated_directory)
                name = package.package_name()
                version = package.bump_version()
                click.echo(f'{name}@{version}')
                processed = True
            except Exception as e:
                logging.error(f'Failed to process PyPI package: {e}')
                click.echo(f'Error processing PyPI package: {e}', err=True)
                return 1
        if package_json_file.exists():
            logging.debug(f'Found NPM package at {validated_directory}')
            try:
                package = NpmPackage(validated_directory)
                name = package.package_name()
                version = package.bump_version()
                click.echo(f'{name}@{version}')
                processed = True
            except Exception as e:
                logging.error(f'Failed to process NPM package: {e}')
                click.echo(f'Error processing NPM package: {e}', err=True)
                return 1
        if not processed:
            error_msg = f'No supported package files found in {validated_directory}'
            logging.error(error_msg)
            click.echo(error_msg, err=True)
            return 1
        return 0
    except Exception as e:
        logging.error(f'Bump package failed: {e}')
        click.echo(f'Error: {e}', err=True)
        return 1


if __name__ == '__main__':
    try:
        sys.exit(cli())
    except Exception as e:
        logging.critical(f'Critical error in release script: {e}')
        click.echo(f'Critical error: {e}', err=True)
        sys.exit(1)
