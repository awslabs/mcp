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

"""CTE-based SQL generation for signal evaluation."""

import re

_MODIFICATION_PATTERN = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b',
    re.IGNORECASE,
)


def build_signal_query(
    query_name: str,
    base_sql: str,
    criteria: str,
    population_criteria: str | None = None,
) -> str:
    """Generate a CTE-based signal query that returns COUNT(*).

    Simple signal (no PopulationCriteria):
        WITH <query_name> AS (<base_sql>)
        SELECT COUNT(*) FROM <query_name> WHERE <criteria>

    With PopulationCriteria:
        WITH <query_name> AS (<base_sql>),
        filtered AS (SELECT * FROM <query_name> WHERE <population_criteria>)
        SELECT COUNT(*) FROM filtered WHERE <criteria>
    """
    if population_criteria:
        return (
            f'WITH {query_name} AS ({base_sql}), '
            f'filtered AS (SELECT * FROM {query_name} WHERE {population_criteria}) '
            f'SELECT COUNT(*) FROM filtered WHERE {criteria}'
        )
    return (
        f'WITH {query_name} AS ({base_sql}) '
        f'SELECT COUNT(*) FROM {query_name} WHERE {criteria}'
    )


def validate_sql_readonly(sql: str) -> None:
    """Reject SQL containing modification keywords outside string literals.

    Strips single-quoted string literals before checking, so values like
    ``query_type = 'INSERT'`` are allowed. Raises ValueError if a
    modification keyword is found as a standalone word.
    """
    stripped = re.sub(r"'[^']*'", "''", sql)
    match = _MODIFICATION_PATTERN.search(stripped)
    if match:
        raise ValueError(f'SQL contains disallowed keyword: {match.group().upper()}')
