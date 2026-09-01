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

"""Tests for the discovery models: the verbosity level each field carries, and projection."""

import pytest
from awslabs.redshift_mcp_server.models import (
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
    VerbosityLevel,
)


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


class TestVerbosityLevels:
    """Tests for the level each field is marked with, and for projecting onto a level."""

    def test_low_fields_are_pinned(self):
        """Low returns these fields and no others, so nothing can join it unnoticed.

        Low is meant to be the identifying names alone: enough to navigate to an object and
        write a query against it, with no types, constraints, permissions or physical design.
        Widening it would enlarge every low-verbosity response, so a field added to low fails
        this test until it is added here too.
        """
        assert RedshiftDatabase.fields_for(VerbosityLevel.LOW) == ('database_name',)
        assert RedshiftSchema.fields_for(VerbosityLevel.LOW) == ('database_name', 'schema_name')
        assert RedshiftTable.fields_for(VerbosityLevel.LOW) == (
            'database_name',
            'schema_name',
            'table_name',
        )
        assert RedshiftColumn.fields_for(VerbosityLevel.LOW) == (
            'database_name',
            'schema_name',
            'table_name',
            'column_name',
        )

    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_standard_returns_every_declared_field(self, model_class):
        """Standard is what the tool returned before levels existed: every declared field."""
        assert model_class.fields_for(VerbosityLevel.STANDARD) == tuple(model_class.model_fields)

    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_low_is_contained_in_standard(self, model_class):
        """The levels are nested, so asking for more detail never drops a field."""
        low = set(model_class.fields_for(VerbosityLevel.LOW))
        assert low < set(model_class.fields_for(VerbosityLevel.STANDARD))

    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_unmarked_fields_default_to_standard(self, model_class):
        """Only the low fields carry a marker; everything else falls back to standard.

        The fallback is what keeps a field added later out of `low` without the author having
        to think about it. Marking every standard field instead would put the same word on two
        dozen declarations to say what the fallback already says.
        """
        standard_only = set(model_class.fields_for(VerbosityLevel.STANDARD)) - set(
            model_class.fields_for(VerbosityLevel.LOW)
        )
        assert standard_only, 'expected at least one standard-only field to assert on'
        assert all(
            model_class.field_level(name) is VerbosityLevel.STANDARD for name in standard_only
        )

    @pytest.mark.parametrize('level', list(VerbosityLevel))
    @pytest.mark.parametrize('model_class', DISCOVERY_MODELS)
    def test_keys_are_exactly_the_level_field_set(self, model_class, level):
        """An item carries the level's fields, no more and no fewer.

        Built from a result set that both omits declared columns and carries an undeclared
        one, so neither an absent column nor a surprise column changes the key set.
        """
        values = dict(REQUIRED_VALUES[model_class], a_column_from_a_later_release='surprise')
        item = model_class.from_redshift_response(_response(values))[0]

        assert set(item.project(level)) == set(model_class.fields_for(level))

    def test_identifying_names_come_first(self):
        """Projection follows declaration order, which keeps the low fields leading."""
        projected = _item(RedshiftColumn).project(VerbosityLevel.STANDARD)
        low = RedshiftColumn.fields_for(VerbosityLevel.LOW)

        assert list(projected)[: len(low)] == list(low)
