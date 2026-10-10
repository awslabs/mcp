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

"""Tests for the discovery models: the verbosity level each field carries, and serialization."""

import pytest
from awslabs.redshift_mcp_server.consts import (
    VERBOSITY_LEVEL_LOW,
    VERBOSITY_LEVEL_STANDARD,
    VERBOSITY_LEVELS,
)
from awslabs.redshift_mcp_server.models import (
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
)
from typing import Optional


DISCOVERY_MODELS = [RedshiftDatabase, RedshiftSchema, RedshiftTable, RedshiftColumn]

# The smallest set of values that satisfies each model's required fields.
REQUIRED_VALUES = {
    RedshiftDatabase: {'database_name': 'dev'},
    RedshiftSchema: {'database_name': 'dev', 'schema_name': 'public'},
    RedshiftTable: {'database_name': 'dev', 'schema_name': 'public', 'table_name': 'orders'},
    RedshiftColumn: {
        'database_name': 'dev',
        'schema_name': 'public',
        'table_name': 'orders',
        'column_name': 'id',
    },
}


def _response(values: dict) -> dict:
    """Build a single-row Data API result set from column name to value."""
    return {
        'ColumnMetadata': [{'name': name} for name in values],
        'Records': [[{'stringValue': value} for value in values.values()]],
    }


def _item(model_class):
    """Build one model instance carrying only its required fields."""
    return model_class.model_validate(REQUIRED_VALUES[model_class])


def _full_item(model_class):
    """Build one model instance with every field populated.

    Serialization drops None, so only an item with no null of its own can show that a
    missing key came from the requested level rather than from an absent value.
    """
    values = {
        name: 1 if field.annotation in (int, Optional[int]) else f'{name}-value'
        for name, field in model_class.model_fields.items()
    }
    return model_class.model_validate(values)


class TestVerbosityLevels:
    """Tests for the level each field is marked with, and for serializing onto a level."""

    def test_low_fields_are_pinned(self):
        """Low returns these fields and no others, so nothing can join it unnoticed.

        Low is the identifying names plus the object's type: enough to navigate to an object
        and write a well-typed predicate against it, with no permissions, ownership or
        physical design. Widening it would enlarge every low-verbosity response, so a field
        added to low fails this test until it is added here too.
        """
        assert RedshiftDatabase.fields_at_verbosity_level(VERBOSITY_LEVEL_LOW) == (
            'database_name',
            'database_type',
        )
        assert RedshiftSchema.fields_at_verbosity_level(VERBOSITY_LEVEL_LOW) == (
            'database_name',
            'schema_name',
            'schema_type',
        )
        assert RedshiftTable.fields_at_verbosity_level(VERBOSITY_LEVEL_LOW) == (
            'database_name',
            'schema_name',
            'table_name',
            'table_type',
        )
        assert RedshiftColumn.fields_at_verbosity_level(VERBOSITY_LEVEL_LOW) == (
            'database_name',
            'schema_name',
            'table_name',
            'column_name',
            'data_type',
        )

    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_standard_returns_every_declared_field(self, model_class):
        """Standard is what the tool returned before levels existed: every declared field."""
        assert model_class.fields_at_verbosity_level(VERBOSITY_LEVEL_STANDARD) == tuple(
            model_class.model_fields
        )

    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_low_is_contained_in_standard(self, model_class):
        """The levels are nested, so asking for more detail never drops a field."""
        low = set(model_class.fields_at_verbosity_level(VERBOSITY_LEVEL_LOW))
        assert low < set(model_class.fields_at_verbosity_level(VERBOSITY_LEVEL_STANDARD))

    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_unmarked_fields_default_to_standard(self, model_class):
        """Only the low fields carry a marker; everything else falls back to standard.

        The fallback is what keeps a field added later out of `low` without the author having
        to think about it. Marking every standard field instead would put the same word on two
        dozen declarations to say what the fallback already says.
        """
        standard_only = set(model_class.fields_at_verbosity_level(VERBOSITY_LEVEL_STANDARD)) - set(
            model_class.fields_at_verbosity_level(VERBOSITY_LEVEL_LOW)
        )
        assert standard_only, 'expected at least one standard-only field to assert on'
        assert all(
            model_class.field_verbosity_level(name) == VERBOSITY_LEVEL_STANDARD
            for name in standard_only
        )

    @pytest.mark.parametrize('level', list(VERBOSITY_LEVELS))
    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_serialization_follows_declaration_order(self, model_class, level):
        """A serialized item carries the level's fields, in the order they were declared.

        Asserting the order also asserts the set, so this covers both: no field above the
        level survives, and none at or below it goes missing.

        The order is the models' own, not the order a level happens to list, which is why a
        type field declared after the detail fields still reads last rather than jumping
        forward to sit with the names it shares a level with.
        """
        serialized = _full_item(model_class).at_verbosity_level(level).model_dump()

        assert list(serialized) == list(model_class.fields_at_verbosity_level(level))

    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_the_level_keeps_its_own_values(self, model_class):
        """Blanking the levels above leaves the ones at or below it untouched."""
        full = _full_item(model_class)
        low = full.at_verbosity_level(VERBOSITY_LEVEL_LOW)

        for name in model_class.fields_at_verbosity_level(VERBOSITY_LEVEL_LOW):
            assert getattr(low, name) == getattr(full, name)

    def test_a_null_field_is_dropped_at_its_own_level(self):
        """A field that is NULL in Redshift is absent rather than null in the response.

        None is the only signal serialization has, so a genuinely null value reads the same
        as one the level blanked. Standard callers see the key disappear, not carry null.
        """
        values = dict(REQUIRED_VALUES[RedshiftTable], table_type='TABLE')
        item = RedshiftTable.from_redshift_response(_response(values))[0]

        serialized = item.at_verbosity_level(VERBOSITY_LEVEL_STANDARD).model_dump()

        assert item.remarks is None
        assert 'remarks' not in serialized
