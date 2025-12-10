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

"""Tests for the models module — BaseSchema exclude_none behavior."""

import json
from awslabs.redshift_mcp_server.models import (
    ExecutionPlan,
    ExecutionPlanNode,
    QueryResult,
    RedshiftColumn,
    RedshiftTable,
)


def _make_column(**overrides):
    """Helper to create a RedshiftColumn with all required fields."""
    defaults = {
        'database_name': 'dev',
        'schema_name': 'public',
        'table_name': 'users',
        'column_name': 'id',
        'ordinal_position': 1,
        'column_default': None,
        'is_nullable': 'YES',
        'data_type': 'integer',
        'character_maximum_length': None,
        'numeric_precision': None,
        'numeric_scale': None,
        'remarks': None,
        'redshift_encoding': None,
        'redshift_is_distkey': False,
        'redshift_sortkey_position': 0,
        'external_type': None,
        'external_partition_key': None,
        'stats_n_distinct': None,
        'stats_null_frac': None,
        'stats_avg_width': None,
        'stats_correlation': None,
        'stats_most_common_vals': None,
        'stats_most_common_freqs': None,
    }
    defaults.update(overrides)
    return RedshiftColumn(**defaults)


def _make_table(**overrides):
    """Helper to create a RedshiftTable with all required fields."""
    defaults = {
        'database_name': 'dev',
        'schema_name': 'public',
        'table_name': 'users',
        'table_acl': None,
        'table_type': 'TABLE',
        'remarks': None,
        'redshift_diststyle': None,
        'redshift_estimated_row_count': None,
        'stats_sequential_scans': None,
        'stats_sequential_tuples_read': None,
        'stats_rows_inserted': None,
        'stats_rows_updated': None,
        'stats_rows_deleted': None,
        'external_location': None,
        'external_parameters': None,
        'columns': None,
    }
    defaults.update(overrides)
    return RedshiftTable(**defaults)


def _make_plan_node(**overrides):
    """Helper to create an ExecutionPlanNode with all required fields."""
    defaults = {
        'node_id': 1,
        'parent_node_id': None,
        'level': 0,
        'operation': 'Seq Scan',
        'relation_name': None,
        'prefix': None,
        'distribution_type': None,
        'cost_startup': None,
        'cost_total': None,
        'rows': None,
        'width': None,
        'scan_relid': None,
        'join_type': None,
        'join_condition': None,
        'filter_condition': None,
        'sort_key': None,
        'agg_strategy': None,
        'data_movement': None,
        'output_columns': None,
    }
    defaults.update(overrides)
    return ExecutionPlanNode(**defaults)


class TestBaseSchemaExcludeNone:
    """Tests for BaseSchema exclude_none serialization."""

    def test_model_dump_excludes_none(self):
        """Test that model_dump excludes None fields by default."""
        column = _make_column(
            data_type='integer',
            redshift_encoding='lzo',
            redshift_is_distkey=True,
            redshift_sortkey_position=1,
        )
        dumped = column.model_dump()

        # Non-None fields should be present
        assert dumped['column_name'] == 'id'
        assert dumped['data_type'] == 'integer'
        assert dumped['redshift_is_distkey'] is True

        # None fields should be excluded
        assert 'character_maximum_length' not in dumped
        assert 'numeric_precision' not in dumped
        assert 'external_type' not in dumped
        assert 'stats_n_distinct' not in dumped
        assert 'stats_correlation' not in dumped

    def test_model_dump_json_excludes_none(self):
        """Test that model_dump_json excludes None fields by default."""
        column = _make_column(column_name='email', data_type='varchar(256)')
        json_str = column.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed['column_name'] == 'email'
        assert 'numeric_precision' not in parsed
        assert 'stats_n_distinct' not in parsed

    def test_model_dump_preserves_non_none(self):
        """Test that all non-None fields are preserved."""
        column = _make_column(
            column_default='nextval()',
            is_nullable='NO',
            numeric_precision=32,
            numeric_scale=0,
            redshift_encoding='lzo',
            redshift_is_distkey=True,
            redshift_sortkey_position=1,
            stats_n_distinct=-1.0,
            stats_null_frac=0.0,
            stats_avg_width=4,
            stats_correlation=0.99,
        )
        dumped = column.model_dump()

        assert dumped['column_default'] == 'nextval()'
        assert dumped['numeric_precision'] == 32
        assert dumped['stats_n_distinct'] == -1.0
        assert dumped['stats_correlation'] == 0.99

    def test_nested_model_excludes_none(self):
        """Test that nested models also exclude None fields."""
        table = _make_table(
            table_type='TABLE',
            redshift_diststyle='KEY',
            redshift_estimated_row_count=50000,
            columns=[
                _make_column(redshift_encoding='lzo'),
            ],
        )
        dumped = table.model_dump()

        # Table-level None fields excluded
        assert 'table_acl' not in dumped
        assert 'remarks' not in dumped
        assert 'external_location' not in dumped

        # Non-None fields present
        assert dumped['redshift_diststyle'] == 'KEY'
        assert dumped['redshift_estimated_row_count'] == 50000

        # Nested column also excludes None
        col = dumped['columns'][0]
        assert col['column_name'] == 'id'
        assert 'numeric_precision' not in col
        assert 'stats_n_distinct' not in col

    def test_execution_plan_excludes_none(self):
        """Test ExecutionPlan with nested nodes excludes None."""
        plan = ExecutionPlan(
            query_id='test-123',
            explained_query='SELECT 1',
            planning_time_ms=50,
            plan_nodes=[
                _make_plan_node(
                    relation_name='users',
                    cost_total=100.0,
                    rows=1000,
                ),
            ],
            human_readable_plan='XN Seq Scan on users',
            rule_based_suggestions=['Consider adding SORTKEY.'],
        )
        dumped = plan.model_dump()

        # Node should exclude None fields
        node = dumped['plan_nodes'][0]
        assert node['operation'] == 'Seq Scan'
        assert node['relation_name'] == 'users'
        assert 'join_type' not in node
        assert 'filter_condition' not in node
        assert 'agg_strategy' not in node
        assert 'distribution_type' not in node

    def test_exclude_none_can_be_overridden(self):
        """Test that exclude_none=False can be passed to include None fields."""
        column = _make_column()
        dumped = column.model_dump(exclude_none=False)

        # None fields should now be present
        assert 'numeric_precision' in dumped
        assert dumped['numeric_precision'] is None
        assert 'stats_n_distinct' in dumped
        assert dumped['stats_n_distinct'] is None

    def test_empty_list_preserved(self):
        """Test that empty lists are not excluded (they're not None)."""
        plan = ExecutionPlan(
            query_id='test-123',
            explained_query='SELECT 1',
            planning_time_ms=None,
            plan_nodes=[],
            human_readable_plan=None,
            rule_based_suggestions=[],
        )
        dumped = plan.model_dump()

        assert 'plan_nodes' in dumped
        assert dumped['plan_nodes'] == []
        assert 'rule_based_suggestions' in dumped
        assert dumped['rule_based_suggestions'] == []

    def test_query_result_preserves_null_values_in_rows(self):
        """Test that NULL values in user query results are preserved, not excluded.

        The exclude_none optimization only affects Pydantic model fields.
        Values inside rows (list[list]) are user data where None represents SQL NULL
        and must be preserved in the output.
        """
        result = QueryResult(
            columns=['null_col', 'int_col', 'str_col', 'another_null'],
            rows=[[None, 1, 'hello', None]],
            row_count=1,
            execution_time_ms=50,
            query_id='test-123',
        )
        dumped = result.model_dump()

        # NULL values inside rows must be preserved
        assert dumped['rows'] == [[None, 1, 'hello', None]]
        assert dumped['rows'][0][0] is None
        assert dumped['rows'][0][3] is None

        # Also verify via JSON serialization
        parsed = json.loads(result.model_dump_json())
        assert parsed['rows'] == [[None, 1, 'hello', None]]

    def test_query_result_excludes_none_fields(self):
        """Test that QueryResult model fields that are None are excluded."""
        result = QueryResult(
            columns=['id'],
            rows=[[1]],
            row_count=1,
            execution_time_ms=None,
            query_id='test-123',
        )
        dumped = result.model_dump()

        # execution_time_ms is None so should be excluded
        assert 'execution_time_ms' not in dumped
        # Required fields always present
        assert dumped['columns'] == ['id']
        assert dumped['query_id'] == 'test-123'

    def test_json_size_reduction_with_exclude_none(self):
        """Test that excluding None values significantly reduces JSON output size."""
        table = _make_table(
            redshift_diststyle='KEY',
            redshift_estimated_row_count=50000,
            columns=[_make_column(column_name=f'col{i}', data_type='integer') for i in range(10)],
        )

        json_with_none = table.model_dump_json(exclude_none=False)
        json_without_none = table.model_dump_json()  # exclude_none=True by default

        size_with = len(json_with_none)
        size_without = len(json_without_none)

        # Excluding None should reduce size by at least 30%
        reduction_pct = (size_with - size_without) / size_with * 100
        assert reduction_pct > 30, (
            f'Expected >30% reduction, got {reduction_pct:.1f}% '
            f'(with={size_with}, without={size_without})'
        )
