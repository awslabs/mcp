#!/usr/bin/env python3
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

# This file is part of the awslabs namespace.
# It is intentionally minimal to support PEP 420 namespace packages.
"""Script to verify that README files correctly reference package names from pyproject.toml files.

This script extracts the package name from a pyproject.toml file and checks if the README.md
file in the same directory correctly references this package name in installation instructions.
"""

import argparse
import base64
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import List, Tuple


try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print('Error: tomllib (Python 3.11+) or tomli package is required', file=sys.stderr)
        print('Please install tomli: pip install tomli', file=sys.stderr)
        sys.exit(1)


def extract_package_name(pyproject_path: Path) -> str:
    """Extract the package name from pyproject.toml file."""
    try:
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
        return data['project']['name']
    except (FileNotFoundError, KeyError) as e:
        raise ValueError(f'Failed to extract package name from {pyproject_path}: {e}')
    except Exception as e:
        # Handle both tomllib.TOMLDecodeError and tomli.TOMLDecodeError
        if 'TOML' in str(type(e).__name__):
            raise ValueError(f'Failed to parse TOML file {pyproject_path}: {e}')
        else:
            raise ValueError(f'Failed to extract package name from {pyproject_path}: {e}')


def extract_dependencies(pyproject_path: Path) -> List[str]:
    """Extract dependency names from pyproject.toml file."""
    try:
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
        dependencies = data.get('project', {}).get('dependencies', [])
        # Extract just the package names (remove version constraints)
        dep_names = []
        for dep in dependencies:
            # Remove version constraints (>=, ==, etc.) and extract just the package name
            dep_name = re.split(r'[>=<!=]', dep)[0].strip()
            dep_names.append(dep_name)
        return dep_names
    except (FileNotFoundError, KeyError):
        # If we can't extract dependencies, return empty list
        return []
    except Exception:
        # If we can't parse dependencies, return empty list
        return []


def extract_package_from_base64_config(config_b64: str) -> List[str]:
    """Extract package names from Base64 encoded or URL-encoded JSON config."""
    try:
        # First, try to URL decode in case it's URL-encoded
        try:
            config_b64 = urllib.parse.unquote(config_b64)
        except (ValueError, UnicodeDecodeError):
            pass  # If URL decoding fails, use original string

        # Try to parse as JSON directly first (for URL-encoded JSON)
        try:
            config = json.loads(config_b64)
        except json.JSONDecodeError:
            # If not JSON, try Base64 decoding
            config_json = base64.b64decode(config_b64).decode('utf-8')
            config = json.loads(config_json)

        # Look for package names in the config
        package_names = []

        # Check command field - handle both formats:
        # Format 1: {"command": "uvx", "args": ["package@version"]}
        # Format 2: {"command": "uvx package@version"}
        if 'command' in config:
            command = config['command']
            if command in ['uvx', 'uv']:
                # Format 1: check args array
                if 'args' in config and config['args']:
                    for arg in config['args']:
                        # Only consider it a package if it has @ and doesn't look like a URL or connection string
                        if '@' in arg and not arg.startswith(
                            ('http://', 'https://', 'postgresql://', 'mysql://', 'mongodb://')
                        ):
                            package_names.append(arg)
            elif command.startswith(('uvx ', 'uv ')):
                # Format 2: extract package from command string
                parts = command.split()
                if len(parts) >= 2:
                    package_arg = parts[1]
                    # Only consider it a package if it has @ and doesn't look like a URL or connection string
                    if '@' in package_arg and not package_arg.startswith(
                        ('http://', 'https://', 'postgresql://', 'mysql://', 'mongodb://')
                    ):
                        package_names.append(package_arg)

        return package_names
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, base64.binascii.Error):
        # If we can't decode, return empty list
        return []


def find_package_references_in_readme(
    readme_path: Path, dependencies: List[str] = None, verbose: bool = False
) -> List[Tuple[str, int]]:
    """Find all package name references in the README file with line numbers."""
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            content = ''.join(lines)
    except FileNotFoundError:
        return []

    # More specific patterns for package references in installation instructions
    patterns = [
        # uvx/uv tool run patterns with @version
        r'uvx\s+([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+)',
        r'uv\s+tool\s+run\s+--from\s+([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+)',
        # pip install patterns
        r'pip\s+install\s+([a-zA-Z0-9._-]+)',
        # JSON configuration patterns with @version
        r'"([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+)"',
        # Package names in JSON config (without version)
        r'"([a-zA-Z0-9._-]+)"\s*:\s*{[^}]*"command"\s*:\s*"uvx"',
        # Docker image patterns (only match actual image names, not command args)
        r'docker\s+run[^"]*"([a-zA-Z0-9._/-]+)"\s*:',
        # Cursor installation links - handled via Base64 config extraction
        # r'cursor\.com/en/install-mcp\?name=([a-zA-Z0-9._-]+)',  # Removed: name often contains display names
        # VS Code installation links (name parameter in URL) - only match package-like names
        r'vscode\.dev/redirect/mcp/install\?name=([a-zA-Z0-9._-]+)',
    ]

    references = []
    for pattern in patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
            # Calculate line number
            line_num = content[: match.start()].count('\n') + 1
            references.append((match.group(1), line_num))

    # Handle Base64/URL-encoded configs specially
    for match in re.finditer(r'config=([^&\s)]+)', content, re.IGNORECASE):
        config_str = match.group(1)
        line_num = content[: match.start()].count('\n') + 1
        config_packages = extract_package_from_base64_config(config_str)
        for package in config_packages:
            references.append((package, line_num))

    # Filter out common false positives
    filtered_references = []
    dependencies = dependencies or []

    for ref, line_num in references:
        # Skip very short references (likely false positives)
        if len(ref) < 3:
            continue
        # Skip common non-package words
        if ref.lower() in [
            '-e',
            '--',
            'pip',
            'uv',
            'uvx',
            'docker',
            'run',
            'install',
            'mcpservers',
            'command',
            'args',
            'env',
        ]:
            continue
        # Skip dependencies from pyproject.toml
        if ref in dependencies:
            continue
        # Skip AWS service references (e.g., aws.s3@ObjectCreated)
        if ref.startswith('aws.') and '@' in ref:
            continue
        # Skip AWS service names without version (e.g., aws.s3)
        if ref.startswith('aws.') and '.' in ref and '@' not in ref:
            continue
        # Skip if it looks like a command line flag
        if ref.startswith('-'):
            continue
        # Skip if it doesn't contain dots (package names usually have dots)
        # But allow package names that look like they could be valid (contain hyphens)
        if '.' not in ref and '@' not in ref and '-' not in ref:
            continue
        # Skip common false positives in code examples (word@something where word is not a package name)
        if '@' in ref and '.' not in ref:
            # Extract the part before @
            prefix = ref.split('@')[0].lower()
            # Different scenarios where the prefix is not a package name
            if prefix in ['asset', 'model', 'property', 'hierarchy']:
                continue
        filtered_references.append((ref, line_num))

    return filtered_references


def verify_package_name_consistency(
    package_name: str, references: List[Tuple[str, int]]
) -> Tuple[bool, List[str]]:
    """Verify that package references match the actual package name."""
    # Extract just the package name part (without version)
    base_package_name = package_name.split('@')[0] if '@' in package_name else package_name

    issues = []

    for ref, line_num in references:
        # Extract package name from reference (remove version if present)
        ref_package = ref.split('@')[0] if '@' in ref else ref

        if ref_package != base_package_name:
            issues.append(
                f"Package name mismatch: found '{ref_package}' but expected '{base_package_name}' (line {line_num})"
            )

    return len(issues) == 0, issues


def main():
    """Main function to verify package name consistency."""
    parser = argparse.ArgumentParser(
        description='Verify that README files correctly reference package names from pyproject.toml'
    )
    parser.add_argument(
        'package_dir', help='Path to the package directory (e.g., src/amazon-neptune-mcp-server)'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    pyproject_path = package_dir / 'pyproject.toml'
    readme_path = package_dir / 'README.md'

    if not package_dir.exists():
        print(f"Error: Package directory '{package_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not pyproject_path.exists():
        print(f"Error: pyproject.toml not found in '{package_dir}'", file=sys.stderr)
        sys.exit(1)

    if not readme_path.exists():
        print(f"Warning: README.md not found in '{package_dir}'", file=sys.stderr)
        sys.exit(0)

    try:
        # Extract package name from pyproject.toml
        package_name = extract_package_name(pyproject_path)
        if args.verbose:
            print(f'Package name from pyproject.toml: {package_name}')

        # Extract dependencies from pyproject.toml
        dependencies = extract_dependencies(pyproject_path)
        if args.verbose:
            print(f'Dependencies from pyproject.toml: {dependencies}')

        # Find package references in README
        references = find_package_references_in_readme(readme_path, dependencies, args.verbose)
        if args.verbose:
            print(f'Found {len(references)} package references in README')
            for ref, line_num in references:
                print(f'  - {ref} (line {line_num})')

        # Verify consistency
        is_consistent, issues = verify_package_name_consistency(package_name, references)

        if is_consistent:
            print(f'✅ Package name verification passed for {package_name}')
            if args.verbose:
                print(
                    'All package references in README match the package name from pyproject.toml'
                )
        else:
            print(f'❌ Package name verification failed for {package_name}')
            for issue in issues:
                print(f'  - {issue}')
            sys.exit(1)

    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'Unexpected error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
