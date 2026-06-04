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
import pydantic_core
from awslabs.redshift_mcp_server.models import BaseSchema
from pydantic import Field
from typing import Optional


class DummySchema(BaseSchema):
    """Minimal test schema to verify BaseSchema behavior."""

    required_field: str = Field(..., description='Always present')
    optional_field: Optional[str] = Field(None, description='May be None')
    optional_int: Optional[int] = Field(None, description='May be None')


class TestBaseSchemaExcludeNone:
    """Tests for BaseSchema exclude_none serialization."""

    def test_model_dump_excludes_none(self):
        """Test that model_dump excludes None fields."""
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)
        dumped = obj.model_dump()

        assert dumped == {'required_field': 'hello'}
        assert 'optional_field' not in dumped
        assert 'optional_int' not in dumped

    def test_model_dump_json_excludes_none(self):
        """Test that model_dump_json excludes None fields."""
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)
        parsed = json.loads(obj.model_dump_json())

        assert parsed == {'required_field': 'hello'}
        assert 'optional_field' not in parsed

    def test_pydantic_core_to_json_excludes_none(self):
        """Test that pydantic_core.to_json also excludes None fields.

        This is the serialization path used by FastMCP when converting tool results
        to TextContent. Without the model_serializer, this would include all None fields.
        """
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)
        raw_json = pydantic_core.to_json(obj, indent=2)
        parsed = json.loads(raw_json)

        assert parsed == {'required_field': 'hello'}
        assert 'optional_field' not in parsed
        assert 'optional_int' not in parsed

    def test_model_dump_preserves_non_none(self):
        """Test that non-None optional fields are preserved."""
        obj = DummySchema(required_field='hello', optional_field='world', optional_int=42)
        dumped = obj.model_dump()

        assert dumped == {'required_field': 'hello', 'optional_field': 'world', 'optional_int': 42}

    def test_json_size_reduction(self):
        """Test that excluding None reduces JSON size."""
        obj = DummySchema(required_field='hello', optional_field=None, optional_int=None)

        json_without = pydantic_core.to_json(obj)
        json_with = json.dumps(
            {'required_field': 'hello', 'optional_field': None, 'optional_int': None}
        ).encode()

        assert len(json_without) < len(json_with)

    def test_nested_model_excludes_none_recursively(self):
        """Nested BaseSchema models also exclude None when serialized together."""

        class Inner(BaseSchema):
            name: str = Field(...)
            value: Optional[int] = Field(default=None)

        class Outer(BaseSchema):
            label: str = Field(...)
            items: list[Inner] = Field(default_factory=list)
            note: Optional[str] = Field(default=None)

        obj = Outer(
            label='test',
            items=[Inner(name='a', value=None), Inner(name='b', value=42)],
        )
        dumped = obj.model_dump()

        assert 'note' not in dumped
        assert dumped['items'][0] == {'name': 'a'}
        assert dumped['items'][1] == {'name': 'b', 'value': 42}

    def test_false_and_zero_values_preserved(self):
        """Falsy non-None values (False, 0, empty string) are preserved."""
        obj = DummySchema(required_field='', optional_field='', optional_int=0)
        dumped = obj.model_dump()

        assert dumped['required_field'] == ''
        assert dumped['optional_field'] == ''
        assert dumped['optional_int'] == 0


class TestExecutionPlanModels:
    """Tests for the ExecutionPlan/ExecutionPlanNode models."""

    # ExecutionPlan default factories ---------------------------------------------

    def test_execution_plan_notes_defaults_to_empty_list(self):
        """`notes` defaults to an empty list."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        plan = ExecutionPlan(
            query_id='q1',
            explained_query='SELECT 1',
            plan_text='',
            plan_nodes=[],
        )

        assert plan.notes == []

    def test_execution_plan_table_designs_defaults_to_empty_list(self):
        """`table_designs` defaults to an empty list."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        plan = ExecutionPlan(
            query_id='q1',
            explained_query='SELECT 1',
            plan_text='',
            plan_nodes=[],
        )

        assert plan.table_designs == []

    def test_execution_plan_rule_based_suggestions_defaults_to_empty_list(self):
        """`rule_based_suggestions` defaults to an empty list."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        plan = ExecutionPlan(
            query_id='q1',
            explained_query='SELECT 1',
            plan_text='',
            plan_nodes=[],
        )

        assert plan.rule_based_suggestions == []

    def test_execution_plan_default_factories_produce_independent_lists(self):
        """Each ExecutionPlan instance gets its own list (no mutable-default sharing)."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        plan_a = ExecutionPlan(
            query_id='qa',
            explained_query='SELECT 1',
            plan_text='',
            plan_nodes=[],
        )
        plan_b = ExecutionPlan(
            query_id='qb',
            explained_query='SELECT 2',
            plan_text='',
            plan_nodes=[],
        )

        plan_a.notes.append('note-a')
        plan_a.table_designs.append(None)  # type: ignore[arg-type]
        plan_a.rule_based_suggestions.append('sug-a')

        assert plan_b.notes == []
        assert plan_b.table_designs == []
        assert plan_b.rule_based_suggestions == []

    # plan_text behavior ----------------------------------------------------------

    def test_execution_plan_plan_text_round_trip_preserves_newlines_and_indent(self):
        """`plan_text` is a single string preserved byte-for-byte across model_dump."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        text = (
            'XN Limit  (cost=0.00..0.10 rows=5 width=231)\n'
            '  ->  XN Index Scan using pg_class_oid_index on pg_class  '
            '(cost=0.00..29.79 rows=1466 width=231)\n'
            '        Index Cond: (oid > 1000::oid)'
        )
        plan = ExecutionPlan(
            query_id='q1',
            explained_query='SELECT 1',
            plan_text=text,
            plan_nodes=[],
        )

        dumped = plan.model_dump()
        assert dumped['plan_text'] == text

        restored = ExecutionPlan.model_validate(dumped)
        assert restored.plan_text == text

    def test_execution_plan_plan_text_empty_string_preserved(self):
        """An empty `plan_text` survives serialization (not stripped as None)."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        plan = ExecutionPlan(
            query_id='q1',
            explained_query='SELECT 1',
            plan_text='',
            plan_nodes=[],
        )
        dumped = plan.model_dump()

        # Empty string is a falsy *non-None* value: BaseSchema's
        # exclude-None serializer must keep it.
        assert dumped['plan_text'] == ''

    # Removed fields --------------------------------------------------------------

    def test_execution_plan_field_set_matches_design(self):
        """ExecutionPlan field set matches the contract."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        expected = {
            'query_id',
            'explained_query',
            'planning_time_ms',
            'plan_text',
            'plan_nodes',
            'table_designs',
            'notes',
            'rule_based_suggestions',
        }
        assert set(ExecutionPlan.model_fields.keys()) == expected

    # BaseSchema exclude-None behavior on new models ------------------------------

    def test_execution_plan_node_excludes_none_on_serialization(self):
        """ExecutionPlanNode inherits BaseSchema's exclude-None behavior."""
        from awslabs.redshift_mcp_server.models import ExecutionPlanNode

        node = ExecutionPlanNode(level=0, operation='Seq Scan')
        dumped = node.model_dump()

        # Required fields present, all None-valued optional fields stripped.
        assert dumped == {'level': 0, 'operation': 'Seq Scan'}
        for none_field in (
            'relation_name',
            'alias',
            'distribution_type',
            'cost_startup',
            'cost_total',
            'rows',
            'width',
            'join_condition',
            'filter_condition',
            'sort_key',
            'merge_key',
            'agg_strategy',
            'data_movement',
        ):
            assert none_field not in dumped

    def test_execution_plan_node_preserves_set_optional_fields(self):
        """ExecutionPlanNode keeps non-None optional fields in the dump."""
        from awslabs.redshift_mcp_server.models import ExecutionPlanNode

        node = ExecutionPlanNode(
            level=1,
            operation='Hash Join',
            distribution_type='DS_BCAST_INNER',
            cost_total=42.0,
            rows=100,
        )
        dumped = node.model_dump()

        assert dumped['distribution_type'] == 'DS_BCAST_INNER'
        assert dumped['cost_total'] == 42.0
        assert dumped['rows'] == 100
        # Optional fields left as None must not leak through.
        assert 'relation_name' not in dumped
        assert 'filter_condition' not in dumped

    def test_execution_plan_excludes_none_on_serialization(self):
        """ExecutionPlan inherits BaseSchema's exclude-None behavior."""
        from awslabs.redshift_mcp_server.models import ExecutionPlan

        plan = ExecutionPlan(
            query_id='q-1',
            explained_query='SELECT 1',
            plan_text='',
            plan_nodes=[],
        )
        dumped = plan.model_dump()

        # `planning_time_ms` was left None and must be stripped.
        assert 'planning_time_ms' not in dumped
        # Required and default-factory fields remain.
        assert dumped['query_id'] == 'q-1'
        assert dumped['explained_query'] == 'SELECT 1'
        assert dumped['plan_text'] == ''
        assert dumped['plan_nodes'] == []
        assert dumped['table_designs'] == []
        assert dumped['notes'] == []
        assert dumped['rule_based_suggestions'] == []
