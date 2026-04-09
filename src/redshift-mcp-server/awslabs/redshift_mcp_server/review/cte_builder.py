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
        WITH <query_name>_raw AS (<base_sql>),
        <query_name> AS (SELECT * FROM <query_name>_raw WHERE <population_criteria>)
        SELECT COUNT(*) FROM <query_name> WHERE <criteria>

    The filtered CTE keeps the original query_name so that subselect
    references in Criteria (e.g. ``SELECT sum(col) FROM WLMConfig``)
    resolve against the already-filtered population.

    Pre-processing:
    - Trailing semicolons are stripped from base_sql.
    - If base_sql starts with ``WITH [RECURSIVE]``, its CTEs are
      flattened into the outer WITH clause to avoid nested WITH
      issues in Redshift. This ensures subselect references in
      Criteria resolve correctly against the query_name CTE.
    """
    base_sql = base_sql.rstrip().rstrip(';')

    # Split out any inner WITH [RECURSIVE] CTEs
    is_recursive, inner_ctes, final_select = _extract_ctes(base_sql)

    # Recursive CTEs can't be flattened into sibling CTEs (Redshift planner
    # limitation), so keep the WITH RECURSIVE at the top level and use a
    # subquery for the final SELECT.
    if is_recursive:
        if population_criteria:
            return (
                f'WITH RECURSIVE {inner_ctes} '
                f'SELECT COUNT(*) FROM ('
                f'SELECT * FROM ({final_select}) AS {query_name}_raw '
                f'WHERE {population_criteria}'
                f') AS {query_name} WHERE {criteria}'
            )
        return (
            f'WITH RECURSIVE {inner_ctes} '
            f'SELECT COUNT(*) FROM ({final_select}) AS {query_name} '
            f'WHERE {criteria}'
        )

    if population_criteria:
        raw_name = f'{query_name}_raw'
        if inner_ctes:
            return (
                f'WITH {inner_ctes}, '
                f'{raw_name} AS ({final_select}), '
                f'{query_name} AS (SELECT * FROM {raw_name} WHERE {population_criteria}) '
                f'SELECT COUNT(*) FROM {query_name} WHERE {criteria}'
            )
        return (
            f'WITH {raw_name} AS ({base_sql}), '
            f'{query_name} AS (SELECT * FROM {raw_name} WHERE {population_criteria}) '
            f'SELECT COUNT(*) FROM {query_name} WHERE {criteria}'
        )

    if inner_ctes:
        return (
            f'WITH {inner_ctes}, '
            f'{query_name} AS ({final_select}) '
            f'SELECT COUNT(*) FROM {query_name} WHERE {criteria}'
        )
    return (
        f'WITH {query_name} AS ({base_sql}) '
        f'SELECT COUNT(*) FROM {query_name} WHERE {criteria}'
    )


# Matches WITH [RECURSIVE] at the start
_WITH_PREFIX = re.compile(r'^WITH\s+(RECURSIVE\s+)?', re.IGNORECASE)


def _extract_ctes(sql: str) -> tuple[bool, str | None, str]:
    """Split a SQL starting with WITH [RECURSIVE] into (is_recursive, cte_definitions, final_select).

    Returns (False, None, original_sql) if the SQL doesn't start with WITH.
    """
    match = _WITH_PREFIX.match(sql)
    if not match:
        return False, None, sql

    is_recursive = bool(match.group(1))
    remainder = sql[match.end():]
    last_top_select = _find_last_top_level_select(remainder)
    if last_top_select is None:
        return False, None, sql

    cte_defs = remainder[:last_top_select].rstrip().rstrip(',').rstrip()
    final_select = remainder[last_top_select:]

    return is_recursive, cte_defs, final_select


def _find_last_top_level_select(sql: str) -> int | None:
    """Find the character index of the last top-level SELECT in a SQL fragment."""
    depth = 0
    last_top_select = None
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == "'":
            i += 1
            while i < len(sql) and sql[i] != "'":
                i += 1
        elif depth == 0 and sql[i:i + 6].upper() == 'SELECT':
            last_top_select = i
        i += 1
    return last_top_select


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
