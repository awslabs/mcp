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

"""Script to verify that MCP tool names comply with naming conventions and length limits.

This script validates that tool names defined with @mcp.tool decorators follow
the requirements specified in DESIGN_GUIDELINES.md and issue #616:

ENFORCED (will fail):
- Maximum 64 characters for the fully qualified name (awslabs + server + tool)
  Format: awslabs<server_name>___<tool_name>
  Example: awslabsgit_repo_research_mcp_server___search_repos_on_github
- Must start with a letter (a-z, A-Z)
- Only alphanumeric characters, underscores (_), or hyphens (-)
- No spaces, commas, or special characters

RECOMMENDED (will warn):
- snake_case is recommended but not required
- Consistency within a server is important
"""

import argparse
import ast
import re
import sys
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


# Maximum length for fully qualified tool names
MAX_TOOL_NAME_LENGTH = 64

# Pattern for valid tool names: alphanumeric with underscores or hyphens
# Must start with a letter (a-z, A-Z)
VALID_TOOL_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_\-]*$')

# Pattern for recommended snake_case naming
SNAKE_CASE_PATTERN = re.compile(r'^[a-z][a-z0-9_]*$')


def extract_package_name(pyproject_path: Path) -> str:
    """Extract the package name from pyproject.toml file."""
    try:
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
        return data['project']['name']
    except (FileNotFoundError, KeyError) as e:
        raise ValueError(f'Failed to extract package name from {pyproject_path}: {e}')
    except Exception as e:
        if 'TOML' in str(type(e).__name__):
            raise ValueError(f'Failed to parse TOML file {pyproject_path}: {e}')
        else:
            raise ValueError(f'Failed to extract package name from {pyproject_path}: {e}')


def convert_package_name_to_server_format(package_name: str) -> str:
    """Convert package name to the format used in fully qualified tool names.

    Examples:
        awslabs.git-repo-research-mcp-server -> git_repo_research_mcp_server
        awslabs.nova-canvas-mcp-server -> nova_canvas_mcp_server
    """
    # Remove 'awslabs.' prefix if present
    if package_name.startswith('awslabs.'):
        package_name = package_name[8:]

    # Replace hyphens with underscores
    return package_name.replace('-', '_')


def calculate_fully_qualified_name(server_name: str, tool_name: str) -> str:
    """Calculate the fully qualified tool name as used by MCP clients.

    Format: awslabs<server_name>___<tool_name>

    Examples:
        awslabs + git_repo_research_mcp_server + ___ + search_repos_on_github
        = awslabsgit_repo_research_mcp_server___search_repos_on_github
    """
    return f'awslabs{server_name}___{tool_name}'


def find_tool_decorators(file_path: Path) -> List[Tuple[str, int]]:
    """Find all tool definitions in a Python file and extract tool names.

    Supports all tool registration patterns:
    - Pattern 1: @mcp.tool(name='tool_name')
    - Pattern 2: @mcp.tool() (uses function name)
    - Pattern 3: app.tool('tool_name')(function)
    - Pattern 4: mcp.tool()(function) (uses function name)
    - Pattern 5: self.mcp.tool(name='tool_name')(function)
    - Pattern 6: @<var>.tool(name='tool_name')

    Returns:
        List of tuples: (tool_name, line_number)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (FileNotFoundError, UnicodeDecodeError):
        return []

    tools = []

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError:
        # If we can't parse the file, skip it
        return []

    for node in ast.walk(tree):
        # PATTERN 1 & 2 & 6: Decorator patterns
        # @mcp.tool(name='...') or @mcp.tool() or @server.tool(name='...')
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    # Check if decorator is *.tool(...)
                    if isinstance(decorator.func, ast.Attribute) and decorator.func.attr == 'tool':
                        # Pattern 1: @mcp.tool(name='tool_name')
                        # Pattern 6: @server.tool(name='tool_name')
                        tool_name = None
                        for keyword in decorator.keywords:
                            if keyword.arg == 'name' and isinstance(keyword.value, ast.Constant):
                                tool_name = keyword.value.value
                                break

                        # Pattern 2: @mcp.tool() or @server.tool() - use function name
                        if tool_name is None:
                            tool_name = node.name

                        if tool_name:
                            tools.append((tool_name, node.lineno))

        # PATTERN 3, 4, 5: Method registration patterns
        # app.tool('name')(func) or mcp.tool()(func) or self.mcp.tool(name='...')(func)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            # Check if this is a chained call like app.tool('name')(func)
            if isinstance(call.func, ast.Call):
                inner_call = call.func
                if isinstance(inner_call.func, ast.Attribute) and inner_call.func.attr == 'tool':
                    tool_name = None

                    # Pattern 3 & 5: Explicit name in first argument or 'name' keyword
                    # app.tool('tool_name')(func) or self.mcp.tool(name='tool_name')(func)
                    if inner_call.args and isinstance(inner_call.args[0], ast.Constant):
                        tool_name = inner_call.args[0].value
                    else:
                        # Check for name keyword argument
                        for keyword in inner_call.keywords:
                            if keyword.arg == 'name' and isinstance(keyword.value, ast.Constant):
                                tool_name = keyword.value.value
                                break

                    # Pattern 4: mcp.tool()(func) - extract function name from argument
                    if tool_name is None:
                        # Get the function being passed to the tool decorator
                        if call.args:
                            func_arg = call.args[0]
                            # Handle simple name: my_function
                            if isinstance(func_arg, ast.Name):
                                tool_name = func_arg.id
                            # Handle attribute access: module.my_function
                            elif isinstance(func_arg, ast.Attribute):
                                tool_name = func_arg.attr

                    if tool_name and isinstance(tool_name, str):
                        tools.append((tool_name, node.lineno))

    return tools


def find_all_tools_in_package(package_dir: Path) -> List[Tuple[str, Path, int]]:
    """Find all tool definitions in a package directory.

    Returns:
        List of tuples: (tool_name, file_path, line_number)
    """
    all_tools = []

    # Search for Python files in the package
    for python_file in package_dir.rglob('*.py'):
        # Skip test files and virtual environments
        if (
            'test' in str(python_file)
            or '.venv' in str(python_file)
            or '__pycache__' in str(python_file)
        ):
            continue

        tools = find_tool_decorators(python_file)
        for tool_name, line_number in tools:
            all_tools.append((tool_name, python_file, line_number))

    return all_tools


def validate_tool_name(tool_name: str) -> Tuple[List[str], List[str]]:
    """Validate a tool name against naming conventions.

    Returns:
        Tuple of (errors, warnings)
        - errors: Critical validation failures (will fail the build)
        - warnings: Style recommendations (informational only)
    """
    errors = []
    warnings = []

    # Check if name is empty
    if not tool_name:
        errors.append('Tool name cannot be empty')
        return errors, warnings

    # Check length (MCP SEP-986: tool names should be 1-64 characters)
    if len(tool_name) > MAX_TOOL_NAME_LENGTH:
        errors.append(
            f"Tool name '{tool_name}' ({len(tool_name)} chars) exceeds the {MAX_TOOL_NAME_LENGTH} "
            f'character limit specified in MCP SEP-986. Please shorten the tool name.'
        )

    # Check if name matches the valid pattern
    if not VALID_TOOL_NAME_PATTERN.match(tool_name):
        if tool_name[0].isdigit():
            errors.append(f"Tool name '{tool_name}' cannot start with a number")
        elif not tool_name[0].isalpha():
            errors.append(f"Tool name '{tool_name}' must start with a letter")
        else:
            # Check for invalid characters (spaces, special chars except underscore and hyphen)
            invalid_chars = set(re.findall(r'[^a-zA-Z0-9_\-]', tool_name))
            if invalid_chars:
                errors.append(
                    f"Tool name '{tool_name}' contains invalid characters: {', '.join(sorted(invalid_chars))}. "
                    f'Only alphanumeric characters, underscores (_), and hyphens (-) are allowed'
                )

    # Warn if not using recommended snake_case
    if not errors and not SNAKE_CASE_PATTERN.match(tool_name):
        warnings.append(
            f"Tool name '{tool_name}' does not follow recommended snake_case convention. "
            f"Consider using snake_case (e.g., 'my_tool_name') for consistency with official MCP implementations."
        )

    return errors, warnings


def validate_tool_names(
    package_name: str, tools: List[Tuple[str, Path, int]], verbose: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """Validate all tool names in a package.

    Returns:
        Tuple of (is_valid, list_of_errors, list_of_warnings)
        - is_valid: True if no errors (warnings don't fail validation)
        - list_of_errors: Critical issues that fail the build
        - list_of_warnings: Recommendations that don't fail the build
    """
    errors = []
    warnings = []

    for tool_name, file_path, line_number in tools:
        # Validate tool name (length, characters, conventions)
        naming_errors, naming_warnings = validate_tool_name(tool_name)
        for error in naming_errors:
            errors.append(f'{file_path}:{line_number} - {error}')
        for warning in naming_warnings:
            warnings.append(f'{file_path}:{line_number} - {warning}')

        if verbose:
            status = '✓' if not naming_errors else '✗'
            style_note = ''
            if naming_warnings:
                style_note = ' (non-snake_case)'
            print(f'  {status} {tool_name} ({len(tool_name)} chars){style_note}')

    return len(errors) == 0, errors, warnings


def main():
    """Main function to verify tool name conventions."""
    parser = argparse.ArgumentParser(
        description='Verify that MCP tool names follow naming conventions and length limits'
    )
    parser.add_argument(
        'package_dir',
        help='Path to the package directory (e.g., src/git-repo-research-mcp-server)',
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    package_dir = Path(args.package_dir)
    pyproject_path = package_dir / 'pyproject.toml'

    if not package_dir.exists():
        print(f"Error: Package directory '{package_dir}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not pyproject_path.exists():
        print(f"Error: pyproject.toml not found in '{package_dir}'", file=sys.stderr)
        sys.exit(1)

    try:
        # Extract package name from pyproject.toml
        package_name = extract_package_name(pyproject_path)
        if args.verbose:
            print(f'Package name from pyproject.toml: {package_name}')

        # Find all tool definitions in the package
        tools = find_all_tools_in_package(package_dir)

        if not tools:
            print(f'✅ No MCP tools found in {package_name} (nothing to validate)')
            sys.exit(0)

        if args.verbose:
            print(f'Found {len(tools)} MCP tool(s) in {package_name}:')

        # Validate all tool names
        is_valid, errors, warnings = validate_tool_names(package_name, tools, args.verbose)

        # Print warnings if any (but don't fail)
        if warnings:
            print(f'\n⚠️  Found {len(warnings)} naming style recommendation(s):')
            for warning in warnings:
                print(f'  - {warning}')
            print(
                '\nNote: These are recommendations only. snake_case is preferred but not required.'
            )

        # Print result
        if is_valid:
            print(f'\n✅ Tool name verification passed for {package_name} ({len(tools)} tool(s))')
            sys.exit(0)
        else:
            print(f'\n❌ Tool name verification failed for {package_name}')
            print(f'\nFound {len(errors)} error(s):')
            for error in errors:
                print(f'  - {error}')
            print('\nPlease refer to DESIGN_GUIDELINES.md for tool naming conventions.')
            sys.exit(1)

    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'Unexpected error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
