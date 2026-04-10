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

"""Tests for CTE builder SQL generation."""

import pytest
import re
from awslabs.redshift_mcp_server.review.config_loader import (
    load_queries_config,
    load_signals_config,
)
from awslabs.redshift_mcp_server.review.cte_builder import (
    build_signal_query,
    validate_sql_readonly,
)
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent.parent / 'awslabs' / 'redshift_mcp_server' / 'config'


def _load_all_signals():
    """Load all signals paired with their query SQL for parameterized tests.

    Returns a list of tuples:
        (test_id, query_name, base_sql, signal_name, criteria, population_criteria)
    """
    queries = load_queries_config(CONFIG_DIR / 'queries.json')
    signals = load_signals_config(CONFIG_DIR / 'signals.json')
    params = []
    for section_name, section in signals.items():
        base_sql = queries[section_name]['SQL']
        for signal in section['Signals']:
            test_id = f'{section_name}::{signal["Signal"][:50]}'
            params.append(
                pytest.param(
                    section_name,
                    base_sql,
                    signal['Signal'],
                    signal['Criteria'],
                    signal.get('PopulationCriteria'),
                    id=test_id,
                )
            )
    return params


ALL_SIGNALS = _load_all_signals()


# ---------------------------------------------------------------------------
# Property 1: CTE SQL Structure Correctness (simple criteria)
# ---------------------------------------------------------------------------


class TestSimpleCriteriaSQLStructure:
    """Verify SQL structure for signals without PopulationCriteria."""

    def test_contains_with_clause(self):
        """Generated SQL starts with a WITH clause using the query name as CTE alias."""
        sql = build_signal_query('TestQuery', 'SELECT 1', 'col > 10')
        assert sql.startswith('WITH TestQuery AS (')

    def test_contains_select_count(self):
        """Generated SQL uses SELECT COUNT(*) not SELECT *."""
        sql = build_signal_query('TestQuery', 'SELECT 1', 'col > 10')
        assert 'SELECT COUNT(*)' in sql

    def test_contains_where_clause(self):
        """Generated SQL includes the criteria as the WHERE clause."""
        sql = build_signal_query('TestQuery', 'SELECT 1', 'col > 10')
        assert sql.endswith('WHERE col > 10')

    def test_base_sql_embedded_in_cte(self):
        """The base SQL is embedded inside the CTE body."""
        base = 'SELECT id, name FROM my_table WHERE active = true'
        sql = build_signal_query('MyQuery', base, 'id > 5')
        assert f'AS ({base})' in sql

    def test_selects_from_cte_alias(self):
        """The outer SELECT references the CTE alias, not the original table."""
        sql = build_signal_query('NodeDetails', 'SELECT * FROM stv_nodes', 'node_type = 1')
        assert 'FROM NodeDetails WHERE' in sql

    def test_simple_structure_matches_template(self):
        """Full SQL matches the expected simple template exactly."""
        sql = build_signal_query('Q', 'SELECT 1', 'x > 0')
        assert sql == 'WITH Q AS (SELECT 1) SELECT COUNT(*) FROM Q WHERE x > 0'


# ---------------------------------------------------------------------------
# Property 2: PopulationCriteria Two-Stage Filtering
# ---------------------------------------------------------------------------


class TestPopulationCriteriaTwoStageFiltering:
    """Verify SQL structure for signals with PopulationCriteria."""

    def test_contains_filtered_intermediate_cte(self):
        """Generated SQL uses _raw suffix for base CTE and query_name for filtered."""
        sql = build_signal_query('Q', 'SELECT 1', 'x > 0', population_criteria='active = true')
        assert 'Q_raw AS (SELECT 1)' in sql
        assert 'Q AS (SELECT * FROM Q_raw WHERE active = true)' in sql

    def test_outer_select_from_filtered(self):
        """The outer SELECT references the query_name CTE (filtered population)."""
        sql = build_signal_query('Q', 'SELECT 1', 'x > 0', population_criteria='active = true')
        assert 'FROM Q WHERE x > 0' in sql

    def test_population_criteria_applied_before_criteria(self):
        """PopulationCriteria appears before Criteria in the SQL."""
        sql = build_signal_query('Q', 'SELECT 1', 'x > 0', population_criteria='y < 100')
        pop_pos = sql.index('y < 100')
        criteria_pos = sql.rindex('x > 0')
        assert pop_pos < criteria_pos

    def test_population_criteria_structure_matches_template(self):
        """Full SQL matches the expected two-stage template."""
        sql = build_signal_query('Q', 'SELECT 1', 'x > 0', population_criteria='y < 100')
        expected = (
            'WITH Q_raw AS (SELECT 1), '
            'Q AS (SELECT * FROM Q_raw WHERE y < 100) '
            'SELECT COUNT(*) FROM Q WHERE x > 0'
        )
        assert sql == expected

    def test_both_cte_aliases_present(self):
        """Both the raw CTE and the filtered CTE are present."""
        sql = build_signal_query('WLMConfig', 'SELECT 1', 'x > 0', population_criteria='y = 1')
        assert 'WITH WLMConfig_raw AS (' in sql
        assert 'WLMConfig AS (SELECT * FROM WLMConfig_raw' in sql

    def test_population_criteria_uses_select_count(self):
        """Even with PopulationCriteria, the outer query uses SELECT COUNT(*)."""
        sql = build_signal_query('Q', 'SELECT 1', 'x > 0', population_criteria='y = 1')
        assert 'SELECT COUNT(*) FROM Q' in sql


# ---------------------------------------------------------------------------
# Subselect Criteria — correct CTE alias resolution
# ---------------------------------------------------------------------------


class TestSubselectCriteria:
    """Verify signals with subselect expressions produce valid SQL."""

    def test_recursive_with_population_criteria(self):
        """Recursive CTE with PopulationCriteria uses nested subquery."""
        base = 'WITH recursive nums(n) as (SELECT 1 UNION ALL SELECT n+1 FROM nums WHERE n<5) SELECT n, n%2 as grp FROM nums'
        sql = build_signal_query('Q', base, 'n > 3', population_criteria='grp = 0')
        assert sql.startswith('WITH RECURSIVE')
        assert 'AS Q_raw' in sql
        assert 'AS Q WHERE' in sql
        assert 'WHERE grp = 0' in sql

    def test_recursive_without_population_criteria(self):
        """Recursive CTE without PopulationCriteria uses simple subquery."""
        base = 'WITH recursive nums(n) as (SELECT 1 UNION ALL SELECT n+1 FROM nums WHERE n<5) SELECT n FROM nums'
        sql = build_signal_query('Q', base, 'n > 3')
        assert sql.startswith('WITH RECURSIVE')
        assert ') AS Q WHERE n > 3' in sql

    def test_subselect_referencing_same_cte(self):
        """Subselect referencing the CTE name resolves correctly."""
        criteria = '100*abs(val - (select min(val) from NodeDetails))/val >= 10'
        sql = build_signal_query('NodeDetails', 'SELECT val FROM stv_nodes', criteria)
        # The CTE alias 'NodeDetails' appears both in the WITH and in the subselect
        assert sql.count('NodeDetails') >= 2
        assert 'WITH NodeDetails AS (' in sql
        assert 'select min(val) from NodeDetails' in sql

    def test_subselect_with_aggregate_sum(self):
        """Subselect with SUM aggregate resolves correctly."""
        criteria = (
            '(select sum(slots) from WLMConfig where service_class_id not in (5,14,15)) > 20'
        )
        sql = build_signal_query('WLMConfig', 'SELECT * FROM stv_wlm', criteria)
        assert 'select sum(slots) from WLMConfig' in sql
        assert 'WITH WLMConfig AS (' in sql

    def test_subselect_with_count_aggregate(self):
        """Subselect with COUNT aggregate resolves correctly."""
        criteria = "(select count(1) from WLMConfig where wlm_mode='manual') > 0"
        sql = build_signal_query(
            'WLMConfig',
            'SELECT * FROM stv_wlm',
            criteria,
            population_criteria='service_class_id <> 5',
        )
        assert 'select count(1) from WLMConfig' in sql
        assert 'FROM WLMConfig WHERE' in sql

    def test_subselect_with_multiple_subqueries(self):
        """Criteria with multiple subselects both resolve to the CTE alias."""
        criteria = (
            "(select count(1) from WLMConfig where service_class_category = 'Manual WLM') = 1 "
            "OR (select count(1) from WLMConfig where service_class_category = 'Auto WLM') = 1"
        )
        sql = build_signal_query('WLMConfig', 'SELECT 1', criteria, population_criteria='x = 1')
        # CTE alias appears in WITH (as _raw), named CTE, + 2 subselects = at least 3
        assert sql.count('WLMConfig') >= 3

    def test_workload_evaluation_subselect(self):
        """WorkloadEvaluation signal with sum/division subselect."""
        criteria = '(select sum(total_query_minutes_in_day)/1440 from WorkloadEvaluation)*100 < 75'
        sql = build_signal_query('WorkloadEvaluation', 'SELECT 1', criteria)
        assert 'from WorkloadEvaluation' in sql
        assert 'WITH WorkloadEvaluation AS (' in sql


# ---------------------------------------------------------------------------
# Property 7: All 55 signals — parameterized tests
# ---------------------------------------------------------------------------


class TestAll55Signals:
    """Parameterized tests over all 55 signals from signals.json."""

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_produces_select_count(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """Every signal produces SQL with SELECT COUNT(*)."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        assert 'SELECT COUNT(*)' in sql

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_contains_correct_cte_alias(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """Every signal's SQL contains the query_name as a CTE or subquery alias."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        if population_criteria:
            assert f'{query_name}_raw AS (' in sql or f') AS {query_name}_raw' in sql
        else:
            assert f'{query_name} AS (' in sql or f') AS {query_name}' in sql

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_contains_correct_where_clause(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """Every signal's SQL ends with the correct WHERE clause."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        assert sql.endswith(f'WHERE {criteria}')

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_no_select_star_in_outer_query(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """No signal produces SELECT * as the outer query (must be SELECT COUNT(*))."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        # Find the outer SELECT (after the last CTE definition)
        # The outer query is the part after the last ')' that closes a CTE
        # We check that the outer SELECT is COUNT(*), not bare *
        outer_match = re.search(r'\)\s+SELECT\s+', sql)
        if outer_match:
            outer_select = sql[outer_match.start() :]
            assert 'SELECT COUNT(*)' in outer_select
            # Ensure no bare "SELECT *" (without COUNT) in the outer query
            assert not re.search(r'SELECT\s+\*\s+FROM', outer_select)

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_base_sql_embedded(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """Every signal's SQL embeds the base SQL (or its final SELECT if flattened)."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        clean_base = base_sql.rstrip().rstrip(';')
        has_inner_ctes = re.match(r'^WITH\s+', clean_base, re.IGNORECASE)
        if has_inner_ctes:
            # Inner CTEs are flattened or kept at top level; verify query_name appears
            assert f'{query_name} AS (' in sql or f') AS {query_name}' in sql
        elif population_criteria:
            assert f'{query_name}_raw AS ({clean_base})' in sql
        else:
            assert f'{query_name} AS ({clean_base})' in sql

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_population_criteria_when_present(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """Signals with PopulationCriteria use the _raw / query_name CTE pattern."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        is_recursive = bool(re.match(r'^WITH\s+RECURSIVE', base_sql.strip(), re.IGNORECASE))
        if population_criteria:
            if is_recursive:
                assert f') AS {query_name}_raw' in sql or f'{query_name}_raw AS (' in sql
            else:
                assert f'{query_name}_raw AS (' in sql
                assert f'{query_name} AS (SELECT * FROM {query_name}_raw WHERE' in sql
                assert f'FROM {query_name} WHERE' in sql
        else:
            if not is_recursive:
                assert '_raw' not in sql
            assert f'FROM {query_name} WHERE' in sql or f'AS {query_name} WHERE' in sql


# ---------------------------------------------------------------------------
# Property 7: Round-trip structural equivalence
# ---------------------------------------------------------------------------


class TestRoundTripStructuralEquivalence:
    """Verify structural elements can be extracted back from generated SQL."""

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_round_trip_cte_alias(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """The query_name appears as a CTE or subquery alias in the generated SQL."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        is_recursive = bool(re.match(r'^WITH\s+RECURSIVE', base_sql.strip(), re.IGNORECASE))
        if is_recursive:
            assert f') AS {query_name}' in sql
        elif population_criteria:
            assert f'{query_name}_raw AS (' in sql
            assert f'{query_name} AS (SELECT * FROM {query_name}_raw' in sql
        else:
            assert f'{query_name} AS (' in sql

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_round_trip_criteria(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """The criteria can be extracted from the tail of the generated SQL."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        # The SQL always ends with "WHERE <criteria>"
        where_idx = sql.rfind('WHERE ')
        assert where_idx != -1
        extracted_criteria = sql[where_idx + len('WHERE ') :]
        assert extracted_criteria == criteria

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_round_trip_population_criteria(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """PopulationCriteria can be extracted from the filtered CTE when present."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        if population_criteria:
            marker_start = f'{query_name} AS (SELECT * FROM {query_name}_raw WHERE '
            marker_end = ') SELECT COUNT(*)'
            start_idx = sql.index(marker_start) + len(marker_start)
            end_idx = sql.index(marker_end, start_idx)
            extracted = sql[start_idx:end_idx]
            assert extracted == population_criteria

    @pytest.mark.parametrize(
        'query_name, base_sql, signal_name, criteria, population_criteria',
        ALL_SIGNALS,
    )
    def test_round_trip_base_sql(
        self, query_name, base_sql, signal_name, criteria, population_criteria
    ):
        """The base SQL content is present in the generated SQL."""
        sql = build_signal_query(query_name, base_sql, criteria, population_criteria)
        clean_base = base_sql.rstrip().rstrip(';')
        has_inner_ctes = bool(re.match(r'^WITH\s+', clean_base, re.IGNORECASE))
        if has_inner_ctes:
            # Flattened or subquery: verify query_name and SELECT COUNT(*) present
            assert 'SELECT COUNT(*)' in sql
            assert query_name in sql
        elif population_criteria:
            start_marker = f'{query_name}_raw AS ('
            idx = sql.index(start_marker) + len(start_marker)
            end_marker = f'), {query_name} AS'
            end_idx = sql.index(end_marker, idx)
            assert sql[idx:end_idx] == clean_base
        else:
            start_marker = f'{query_name} AS ('
            idx = sql.index(start_marker) + len(start_marker)
            end_marker = ') SELECT COUNT(*)'
            end_idx = sql.index(end_marker, idx)
            assert sql[idx:end_idx] == clean_base


# ---------------------------------------------------------------------------
# Property 5: SQL Modification Keyword Rejection
# ---------------------------------------------------------------------------

_MODIFICATION_KEYWORDS = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']


class TestSQLValidationModificationKeywordsRejected:
    """Modification keywords as standalone words outside string literals are rejected."""

    @pytest.mark.parametrize('keyword', _MODIFICATION_KEYWORDS)
    def test_rejects_uppercase_keyword(self, keyword):
        """Uppercase modification keyword is rejected."""
        sql = f'{keyword} INTO my_table VALUES (1)'
        with pytest.raises(ValueError, match=keyword.upper()):
            validate_sql_readonly(sql)

    @pytest.mark.parametrize('keyword', _MODIFICATION_KEYWORDS)
    def test_rejects_lowercase_keyword(self, keyword):
        """Lowercase modification keyword is rejected."""
        sql = f'{keyword.lower()} into my_table values (1)'
        with pytest.raises(ValueError, match=keyword.upper()):
            validate_sql_readonly(sql)

    @pytest.mark.parametrize('keyword', _MODIFICATION_KEYWORDS)
    def test_rejects_mixed_case_keyword(self, keyword):
        """Mixed-case modification keyword is rejected."""
        mixed = keyword[0] + keyword[1:].lower()
        sql = f'{mixed} into my_table values (1)'
        with pytest.raises(ValueError, match=keyword.upper()):
            validate_sql_readonly(sql)

    @pytest.mark.parametrize('keyword', _MODIFICATION_KEYWORDS)
    def test_rejects_keyword_mid_statement(self, keyword):
        """Keyword appearing in the middle of a SQL statement is rejected."""
        sql = f'WITH cte AS (SELECT 1) {keyword} INTO t VALUES (1)'
        with pytest.raises(ValueError, match=keyword.upper()):
            validate_sql_readonly(sql)

    def test_accepts_clean_select(self):
        """A plain SELECT statement passes validation."""
        validate_sql_readonly('SELECT COUNT(*) FROM my_table WHERE x > 0')

    def test_accepts_cte_select(self):
        """A CTE-based SELECT statement passes validation."""
        sql = 'WITH Q AS (SELECT id FROM t) SELECT COUNT(*) FROM Q WHERE id > 5'
        validate_sql_readonly(sql)


class TestSQLValidationKeywordsInsideStringLiterals:
    """Keywords inside single-quoted string literals are allowed."""

    @pytest.mark.parametrize('keyword', _MODIFICATION_KEYWORDS)
    def test_keyword_in_string_literal_allowed(self, keyword):
        """Keyword inside a string literal does not trigger rejection."""
        sql = f"SELECT COUNT(*) FROM queries WHERE query_type = '{keyword}'"
        validate_sql_readonly(sql)

    def test_insert_in_where_value(self):
        """'INSERT' as a column value in a WHERE clause is allowed."""
        sql = "SELECT COUNT(*) FROM log WHERE operation = 'INSERT' AND status = 'ok'"
        validate_sql_readonly(sql)

    def test_multiple_keywords_in_literals(self):
        """Multiple keywords inside string literals are all allowed."""
        sql = "SELECT * FROM t WHERE a = 'DELETE' AND b = 'DROP' AND c = 'TRUNCATE'"
        validate_sql_readonly(sql)

    def test_keyword_in_literal_with_surrounding_text(self):
        """Keyword embedded in a longer string literal is allowed."""
        sql = "SELECT * FROM t WHERE msg = 'Please do not DELETE this record'"
        validate_sql_readonly(sql)


class TestSQLValidationColumnNamesContainingKeywords:
    """Column names that contain keyword substrings are allowed."""

    def test_delete_flag_column(self):
        """Column name 'delete_flag' is not rejected (DELETE is a substring, not a word)."""
        validate_sql_readonly('SELECT COUNT(*) FROM t WHERE delete_flag > 0')

    def test_updated_at_column(self):
        """Column name 'updated_at' is not rejected (UPDATE is a substring)."""
        validate_sql_readonly('SELECT COUNT(*) FROM t WHERE updated_at IS NOT NULL')

    def test_insert_count_column(self):
        """Column name 'insert_count' is not rejected (INSERT is a substring)."""
        validate_sql_readonly('SELECT COUNT(*) FROM t WHERE insert_count > 100')

    def test_created_by_column(self):
        """Column name 'created_by' is not rejected (CREATE is a substring)."""
        validate_sql_readonly("SELECT COUNT(*) FROM t WHERE created_by = 'admin'")

    def test_alter_ego_column(self):
        """Column name 'alter_ego' is not rejected (ALTER is a substring)."""
        validate_sql_readonly('SELECT COUNT(*) FROM t WHERE alter_ego IS NOT NULL')

    def test_drop_rate_column(self):
        """Column name 'drop_rate' is not rejected (DROP is a substring)."""
        validate_sql_readonly('SELECT COUNT(*) FROM t WHERE drop_rate < 0.05')

    def test_truncated_column(self):
        """Column name 'truncated' is not rejected (TRUNCATE is a substring)."""
        validate_sql_readonly('SELECT COUNT(*) FROM t WHERE truncated = false')
