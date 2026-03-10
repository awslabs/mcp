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

"""Query validation for Neptune MCP Server.

Provides safeguards against unrestricted query execution by validating
queries before they are sent to Neptune. The server defaults to read-only
mode; use --allow-writes to enable mutations.
"""

import re


# openCypher keywords that mutate data
_OPENCYPHER_MUTATING_PATTERN = re.compile(
    r'\b(CREATE|MERGE|DELETE|DETACH\s+DELETE|REMOVE|DROP|CALL)\b'
    r'|'
    r'(?<![.\w])SET(?![.\w])',
    re.IGNORECASE,
)

# Gremlin steps that mutate data
_GREMLIN_MUTATING_PATTERN = re.compile(
    r'\.(addV|addE|mergeV|mergeE|drop|property|sideEffect)\s*\(',
    re.IGNORECASE,
)

# Module-level read-only flag — defaults to True (safe by default).
# Set to False via set_read_only(False) when --allow-writes is passed.
read_only = True


def set_read_only(value: bool) -> None:
    """Set the read-only mode for query validation."""
    global read_only
    read_only = value


def validate_opencypher_query(query: str) -> None:
    """Validate an openCypher query for safety.

    When in read-only mode, blocks mutating keywords.

    Raises:
        PermissionError: If a mutating query is submitted in read-only mode.
    """
    if read_only and _OPENCYPHER_MUTATING_PATTERN.search(query):
        raise PermissionError(
            'Mutating openCypher queries are blocked in read-only mode. '
            'Use --allow-writes to enable mutations.'
        )


def validate_gremlin_query(query: str) -> None:
    """Validate a Gremlin query for safety.

    When in read-only mode, blocks mutating steps.

    Raises:
        PermissionError: If a mutating query is submitted in read-only mode.
    """
    if read_only and _GREMLIN_MUTATING_PATTERN.search(query):
        raise PermissionError(
            'Mutating Gremlin queries are blocked in read-only mode. '
            'Use --allow-writes to enable mutations.'
        )
