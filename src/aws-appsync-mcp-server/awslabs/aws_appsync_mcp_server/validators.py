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

    return issues
