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

"""Validation utilities for AWS AppSync MCP Server."""

import re
from typing import List


def validate_graphql_schema(definition: str) -> List[str]:
    """Validate GraphQL schema definition and return list of issues."""
    issues = []

    # Basic syntax checks
    if not definition.strip():
        issues.append('Schema definition cannot be empty')
        return issues

    # Check for required Query type
    if not re.search(r'\btype\s+Query\s*\{', definition, re.IGNORECASE):
        issues.append('Schema must include a Query type')

    # Check for balanced braces
    open_braces = definition.count('{')
    close_braces = definition.count('}')
    if open_braces != close_braces:
        issues.append(f'Unbalanced braces: {open_braces} opening, {close_braces} closing')

    # Security check for dangerous patterns
    dangerous_patterns = get_dangerous_patterns()
    found_patterns = [pattern for pattern in dangerous_patterns if pattern in definition]
    if found_patterns:
        issues.append(
            f'Potentially dangerous patterns detected in the schema: {", ".join(found_patterns)}'
        )

    return issues


# Security-related constants and utilities
# These are used to prevent command injection and other security issues


def get_dangerous_patterns() -> List[str]:
    """Get a list of dangerous patterns for command injection detection.

    Returns:
        List of dangerous patterns to check for
    """
    # Dangerous patterns that could indicate command injection attempts
    # Separated by platform for better organization and maintainability
    patterns = [
        '|',
        ';',
        '&',
        '&&',
        '||',  # Command chaining
        '>',
        '>>',
        '<',  # Redirection
        '`',
        '$(',  # Command substitution
        '--',  # Double dash options
        'rm',
        'mv',
        'cp',  # Potentially dangerous commands
        '/bin/',
        '/usr/bin/',  # Path references
        '../',
        './',  # Directory traversal
        # Unix/Linux specific dangerous patterns
        'sudo',  # Privilege escalation
        'chmod',
        'chown',  # File permission changes
        'su',  # Switch user
        'bash',
        'sh',
        'zsh',  # Shell execution
        'curl',
        'wget',  # Network access
        'ssh',
        'scp',  # Remote access
        'eval',  # Command evaluation
        'exec',  # Command execution
        'source',  # Script sourcing
        # Windows specific dangerous patterns
        'cmd',
        'powershell',
        'pwsh',  # Command shells
        'net',  # Network commands
        'reg',  # Registry access
        'runas',  # Privilege escalation
        'del',
        'rmdir',  # File deletion
        'start',  # Process execution
        'taskkill',  # Process termination
        'sc',  # Service control
        'schtasks',  # Scheduled tasks
        'wmic',  # WMI commands
        '%SYSTEMROOT%',
        '%WINDIR%',  # System directories
        '.bat',
        '.cmd',
        '.ps1',  # Script files
    ]
    return patterns
