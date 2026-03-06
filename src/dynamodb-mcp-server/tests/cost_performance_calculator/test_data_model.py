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

"""Unit tests for calculator data models."""

import pytest
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    GSI,
    MAX_BATCH_GET_ITEMS,
    MAX_BATCH_WRITE_ITEMS,
    MAX_GSIS_PER_TABLE,
    MAX_ITEM_SIZE_BYTES,
    DataModel,
    PutItemAccessPattern,
    QueryAccessPattern,
    Table,
    _customize_error_message,
    _format_location,
    format_validation_errors,
)
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError


def strip_pydantic_error_url(exc: ValidationError) -> str:
    """Get error string without the Pydantic URL suffix."""
    s = str(exc)
    if '\n    For further information' in s:
        s = s.split('\n    For further information')[0]
    return s


class TestDataModel:
    """Tests for DataModel model."""

    @pytest.fixture
    def minimal_calculator_input(self):
        """Minimal valid data model."""
        return {
            'access_pattern_list': [
                {
                    'operation': 'GetItem',
                    'pattern': 'get-user',
                    'description': 'Get user by ID',
                    'table': 'users',
                    'rps': 100,
                    'item_size_bytes': 1000,
                }
            ],
            'table_list': [{'name': 'users', 'item_count': 10000, 'item_size_bytes': 2000}],
        }

    def test_valid_calculator_input_minimal(self, minimal_calculator_input):
        """Test DataModel with minimal valid data."""
        calc_input = DataModel(**minimal_calculator_input)
        assert len(calc_input.access_pattern_list) == 1
        assert len(calc_input.table_list) == 1
        assert calc_input.table_list[0].name == 'users'

    def test_valid_calculator_input_multiple_access_patterns(self, minimal_calculator_input):
        """Test DataModel with multiple access patterns."""
        minimal_calculator_input['access_pattern_list'].append(
            {
                'operation': 'Query',
                'pattern': 'query-orders',
                'description': 'Query orders',
                'table': 'orders',
                'rps': 50,
                'item_size_bytes': 500,
                'item_count': 10,
            }
        )
        minimal_calculator_input['table_list'].append(
            {'name': 'orders', 'item_count': 50000, 'item_size_bytes': 1000}
        )
        calc_input = DataModel(**minimal_calculator_input)
        assert len(calc_input.access_pattern_list) == 2

    def test_invalid_calculator_input_empty_access_patterns(self, minimal_calculator_input):
        """Test DataModel with empty access pattern list."""
        minimal_calculator_input['access_pattern_list'] = []
        with pytest.raises(ValidationError) as exc_info:
            DataModel(**minimal_calculator_input)
        assert (
            strip_pydantic_error_url(exc_info.value)
            == '1 validation error for DataModel\naccess_pattern_list\n  Value error, access_pattern_list must contain at least one access pattern [type=value_error, input_value=[], input_type=list]'
        )
        assert (
            format_validation_errors(exc_info.value)
            == 'access_pattern_list: access_pattern_list must contain at least one access pattern'
        )

    def test_invalid_calculator_input_duplicate_table_names(self, minimal_calculator_input):
        """Test DataModel with duplicate table names."""
        minimal_calculator_input['table_list'].append(
            {'name': 'users', 'item_count': 2000, 'item_size_bytes': 3000}
        )
        with pytest.raises(ValidationError) as exc_info:
            DataModel(**minimal_calculator_input)
        assert (
            strip_pydantic_error_url(exc_info.value)
            == "1 validation error for DataModel\n  Value error, duplicate table name. name: \"users\" [type=value_error, input_value={'access_pattern_list': [...tem_size_bytes': 3000}]}, input_type=dict]"
        )
        assert format_validation_errors(exc_info.value) == 'duplicate table name. name: "users"'

    def test_invalid_calculator_input_table_not_found(self, minimal_calculator_input):
        """Test DataModel with access pattern referencing non-existent table."""
        minimal_calculator_input['table_list'][0]['name'] = 'orders'
        with pytest.raises(ValidationError) as exc_info:
            DataModel(**minimal_calculator_input)
        assert (
            strip_pydantic_error_url(exc_info.value)
            == "1 validation error for DataModel\n  Value error, table does not exist. table: \"users\" [type=value_error, input_value={'access_pattern_list': [...tem_size_bytes': 2000}]}, input_type=dict]"
        )
        assert format_validation_errors(exc_info.value) == 'table does not exist. table: "users"'

    def test_invalid_calculator_input_gsi_not_found(self, minimal_calculator_input):
        """Test DataModel with access pattern referencing non-existent GSI."""
        minimal_calculator_input['access_pattern_list'][0] = {
            'operation': 'Query',
            'pattern': 'query-user',
            'description': 'Query user',
            'table': 'users',
            'rps': 100,
            'item_size_bytes': 1000,
            'item_count': 10,
            'gsi': 'non-existent-gsi',
        }
        with pytest.raises(ValidationError) as exc_info:
            DataModel(**minimal_calculator_input)
        assert (
            strip_pydantic_error_url(exc_info.value)
            == '1 validation error for DataModel\n  Value error, GSI does not exist. gsi: "non-existent-gsi", table: "users" [type=value_error, input_value={\'access_pattern_list\': [...tem_size_bytes\': 2000}]}, input_type=dict]'
        )
        assert (
            format_validation_errors(exc_info.value)
            == 'GSI does not exist. gsi: "non-existent-gsi", table: "users"'
        )

    def test_invalid_calculator_input_gsi_list_not_found(self, minimal_calculator_input):
        """Test DataModel with write operation referencing non-existent GSI in list."""
        minimal_calculator_input['access_pattern_list'][0] = {
            'operation': 'PutItem',
            'pattern': 'put-user',
            'description': 'Put user',
            'table': 'users',
            'rps': 100,
            'item_size_bytes': 1000,
            'gsi_list': ['gsi-1', 'non-existent-gsi'],
        }
        minimal_calculator_input['table_list'][0]['gsi_list'] = [
            {'name': 'gsi-1', 'item_size_bytes': 1500, 'item_count': 500}
        ]
        with pytest.raises(ValidationError) as exc_info:
            DataModel(**minimal_calculator_input)
        assert (
            strip_pydantic_error_url(exc_info.value)
            == '1 validation error for DataModel\n  Value error, GSI does not exist. gsi: "non-existent-gsi", table: "users" [type=value_error, input_value={\'access_pattern_list\': [..., \'item_count\': 500}]}]}, input_type=dict]'
        )
        assert (
            format_validation_errors(exc_info.value)
            == 'GSI does not exist. gsi: "non-existent-gsi", table: "users"'
        )

    def test_invalid_calculator_input_ap_size_exceeds_table_size(self, minimal_calculator_input):
        """Test CalculatorInput with access pattern size exceeding table size."""
        minimal_calculator_input['access_pattern_list'][0]['item_size_bytes'] = 3000
        with pytest.raises(ValidationError) as exc_info:
            DataModel(**minimal_calculator_input)
        assert (
            strip_pydantic_error_url(exc_info.value)
            == "1 validation error for DataModel\n  Value error, item_size_bytes cannot exceed table item_size_bytes. access_pattern_size: 3000, table_size: 2000, table: \"users\" [type=value_error, input_value={'access_pattern_list': [...tem_size_bytes': 2000}]}, input_type=dict]"
        )
        assert (
            format_validation_errors(exc_info.value)
            == 'item_size_bytes cannot exceed table item_size_bytes. access_pattern_size: 3000, table_size: 2000, table: "users"'
        )

    def test_invalid_calculator_input_ap_size_exceeds_gsi_size(self, minimal_calculator_input):
        """Test DataModel with access pattern size exceeding GSI size."""
        minimal_calculator_input['access_pattern_list'][0] = {
            'operation': 'Query',
            'pattern': 'query-user',
            'description': 'Query user by email',
            'table': 'users',
            'rps': 100,
            'item_size_bytes': 2000,
            'item_count': 10,
            'gsi': 'email-index',
        }
        minimal_calculator_input['table_list'][0]['item_size_bytes'] = 3000
        minimal_calculator_input['table_list'][0]['gsi_list'] = [
            {'name': 'email-index', 'item_size_bytes': 1500, 'item_count': 1000}
        ]
        with pytest.raises(ValidationError) as exc_info:
            DataModel(**minimal_calculator_input)
        assert (
            strip_pydantic_error_url(exc_info.value)
            == "1 validation error for DataModel\n  Value error, item_size_bytes cannot exceed GSI item_size_bytes. access_pattern_size: 2000, gsi_size: 1500, gsi: \"email-index\" [type=value_error, input_value={'access_pattern_list': [... 'item_count': 1000}]}]}, input_type=dict]"
        )
        assert (
            format_validation_errors(exc_info.value)
            == 'item_size_bytes cannot exceed GSI item_size_bytes. access_pattern_size: 2000, gsi_size: 1500, gsi: "email-index"'
        )

    def test_valid_calculator_input_complex_scenario(self, minimal_calculator_input):
        """Test DataModel with complex valid scenario."""
        minimal_calculator_input['access_pattern_list'] = [
            {
                'operation': 'GetItem',
                'pattern': 'get-user',
                'description': 'Get user by ID',
                'table': 'users',
                'rps': 100,
                'item_size_bytes': 2000,
            },
            {
                'operation': 'Query',
                'pattern': 'query-by-email',
                'description': 'Query user by email',
                'table': 'users',
                'rps': 50,
                'item_size_bytes': 1500,
                'item_count': 1,
                'gsi': 'email-index',
            },
            {
                'operation': 'PutItem',
                'pattern': 'put-user',
                'description': 'Create user',
                'table': 'users',
                'rps': 20,
                'item_size_bytes': 2000,
                'gsi_list': ['email-index', 'status-index'],
            },
        ]
        minimal_calculator_input['table_list'][0] = {
            'name': 'users',
            'item_count': 10000,
            'item_size_bytes': 2500,
            'gsi_list': [
                {'name': 'email-index', 'item_size_bytes': 1500, 'item_count': 10000},
                {'name': 'status-index', 'item_size_bytes': 500, 'item_count': 10000},
            ],
        }
        calc_input = DataModel(**minimal_calculator_input)
        assert len(calc_input.access_pattern_list) == 3
        assert len(calc_input.table_list) == 1
        assert len(calc_input.table_list[0].gsi_list) == 2


class TestDataModelPropertyBased:
    """Property-based tests for DataModel validation."""

    @given(
        item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
        rps=st.integers(min_value=1, max_value=10000),
    )
    def test_valid_getitem_properties(self, item_size, rps):
        """Property test: valid GetItem access patterns should always succeed."""
        data = {
            'access_pattern_list': [
                {
                    'operation': 'GetItem',
                    'pattern': 'test-pattern',
                    'description': 'Test description',
                    'table': 'test-table',
                    'rps': rps,
                    'item_size_bytes': item_size,
                }
            ],
            'table_list': [
                {'name': 'test-table', 'item_count': 1000, 'item_size_bytes': MAX_ITEM_SIZE_BYTES}
            ],
        }
        calc_input = DataModel(**data)
        assert calc_input.access_pattern_list[0].item_size_bytes == item_size
        assert calc_input.access_pattern_list[0].rps == rps

    @given(
        table_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
        gsi_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
    )
    def test_gsi_size_constraint_property(self, table_size, gsi_size):
        """Property test: GSI size must not exceed table size."""
        data = {
            'table_list': [
                {
                    'name': 'test-table',
                    'item_count': 1000,
                    'item_size_bytes': table_size,
                    'gsi_list': [
                        {'name': 'test-gsi', 'item_size_bytes': gsi_size, 'item_count': 100}
                    ],
                }
            ],
            'access_pattern_list': [
                {
                    'operation': 'GetItem',
                    'pattern': 'test',
                    'description': 'test',
                    'table': 'test-table',
                    'rps': 1,
                    'item_size_bytes': 1,
                }
            ],
        }

        if gsi_size > table_size:
            with pytest.raises(ValidationError) as exc_info:
                DataModel(**data)
            err = strip_pydantic_error_url(exc_info.value)
            assert err.startswith(
                f'1 validation error for DataModel\ntable_list.0\n  Value error, GSI item_size_bytes cannot exceed table item_size_bytes. gsi_item_size_bytes: {gsi_size}, table_item_size_bytes: {table_size} [type=value_error, input_value='
            )
        else:
            calc_input = DataModel(**data)
            assert calc_input.table_list[0].gsi_list[0].item_size_bytes == gsi_size

    @given(item_count=st.integers(min_value=1, max_value=MAX_BATCH_GET_ITEMS))
    def test_batch_get_item_count_property(self, item_count):
        """Property test: BatchGetItem item_count within limits should succeed."""
        data = {
            'access_pattern_list': [
                {
                    'operation': 'BatchGetItem',
                    'pattern': 'test',
                    'description': 'test',
                    'table': 'test-table',
                    'rps': 1,
                    'item_size_bytes': 1000,
                    'item_count': item_count,
                }
            ],
            'table_list': [{'name': 'test-table', 'item_count': 1000, 'item_size_bytes': 2000}],
        }
        calc_input = DataModel(**data)
        assert calc_input.access_pattern_list[0].item_count == item_count  # type: ignore[union-attr]

    @given(item_count=st.integers(min_value=1, max_value=MAX_BATCH_WRITE_ITEMS))
    def test_batch_write_item_count_property(self, item_count):
        """Property test: BatchWriteItem item_count within limits should succeed."""
        data = {
            'access_pattern_list': [
                {
                    'operation': 'BatchWriteItem',
                    'pattern': 'test',
                    'description': 'test',
                    'table': 'test-table',
                    'rps': 1,
                    'item_size_bytes': 1000,
                    'item_count': item_count,
                }
            ],
            'table_list': [{'name': 'test-table', 'item_count': 1000, 'item_size_bytes': 2000}],
        }
        calc_input = DataModel(**data)
        assert calc_input.access_pattern_list[0].item_count == item_count  # type: ignore[union-attr]

    @given(gsi_count=st.integers(min_value=0, max_value=MAX_GSIS_PER_TABLE))
    def test_table_gsi_count_property(self, gsi_count):
        """Property test: tables with GSI count within limits should succeed."""
        gsi_list = [
            {'name': f'gsi-{i}', 'item_size_bytes': 1000, 'item_count': 100}
            for i in range(gsi_count)
        ]
        data = {
            'table_list': [
                {
                    'name': 'test-table',
                    'item_count': 1000,
                    'item_size_bytes': 2000,
                    'gsi_list': gsi_list,
                }
            ],
            'access_pattern_list': [
                {
                    'operation': 'GetItem',
                    'pattern': 'test',
                    'description': 'test',
                    'table': 'test-table',
                    'rps': 1,
                    'item_size_bytes': 1000,
                }
            ],
        }
        calc_input = DataModel(**data)
        assert len(calc_input.table_list[0].gsi_list) == gsi_count


class TestFormatLocation:
    """Tests for _format_location helper."""

    def test_simple_field(self):
        """Test formatting a simple field location."""
        assert _format_location(('name',)) == 'name'

    def test_nested_field(self):
        """Test formatting a nested field location."""
        assert _format_location(('table', 'name')) == 'table.name'

    def test_array_index(self):
        """Test formatting an array index location."""
        assert _format_location(('table_list', 3)) == 'table_list[3]'

    def test_array_with_field(self):
        """Test formatting an array index with nested field."""
        assert _format_location(('table_list', 3, 'item_count')) == 'table_list[3].item_count'

    def test_deeply_nested(self):
        """Test formatting a deeply nested location."""
        assert (
            _format_location(('table_list', 0, 'gsi_list', 2, 'name'))
            == 'table_list[0].gsi_list[2].name'
        )

    def test_empty_location(self):
        """Test formatting an empty location."""
        assert _format_location(()) == ''


class TestCustomizeErrorMessage:
    """Tests for _customize_error_message helper."""

    def test_string_too_short(self):
        """Test customizing string_too_short error."""
        error = {'type': 'string_too_short', 'loc': ('name',), 'input': '', 'ctx': {}}
        result = _customize_error_message(error)
        assert result == 'cannot be empty. name: '

    def test_greater_than(self):
        """Test customizing greater_than error."""
        error = {'type': 'greater_than', 'loc': ('item_count',), 'input': 0, 'ctx': {'gt': 0}}
        result = _customize_error_message(error)
        assert result == 'must be greater than 0. item_count: 0'

    def test_greater_than_equal(self):
        """Test customizing greater_than_equal error."""
        error = {'type': 'greater_than_equal', 'loc': ('size',), 'input': 0, 'ctx': {'ge': 1}}
        result = _customize_error_message(error)
        assert result == 'must be at least 1. size: 0'

    def test_less_than_equal(self):
        """Test customizing less_than_equal error."""
        error = {
            'type': 'less_than_equal',
            'loc': ('size',),
            'input': 500000,
            'ctx': {'le': 409600},
        }
        result = _customize_error_message(error)
        assert result == 'must be at most 409600. size: 500000'

    def test_unknown_error_type_falls_back(self):
        """Test that unknown error types fall back to Pydantic's message."""
        error = {
            'type': 'unknown_type',
            'loc': ('field',),
            'input': 'x',
            'msg': 'Original message',
        }
        result = _customize_error_message(error)
        assert result == 'Original message'

    def test_empty_context(self):
        """Test error with empty context."""
        error = {'type': 'string_too_short', 'loc': ('name',), 'input': '', 'ctx': {}}
        result = _customize_error_message(error)
        assert 'cannot be empty' in result


class TestFormatValidationErrors:
    """Tests for format_validation_errors function."""

    def test_gsi_constraint_error(self):
        """Test formatting GSI constraint validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GSI(name='test', item_size_bytes=0, item_count=100)
        result = format_validation_errors(exc_info.value)
        assert result == 'item_size_bytes: must be at least 1. item_size_bytes: 0'

    def test_gsi_string_too_short_error(self):
        """Test formatting GSI string too short error."""
        with pytest.raises(ValidationError) as exc_info:
            GSI(name='', item_size_bytes=1000, item_count=100)
        result = format_validation_errors(exc_info.value)
        assert result == 'name: cannot be empty. name: '

    def test_gsi_multiple_errors(self):
        """Test formatting multiple GSI validation errors."""
        with pytest.raises(ValidationError) as exc_info:
            GSI(name='', item_size_bytes=0, item_count=0)
        result = format_validation_errors(exc_info.value)
        lines = result.split('\n')
        assert len(lines) == 3
        assert 'name: cannot be empty. name: ' in lines
        assert 'item_size_bytes: must be at least 1. item_size_bytes: 0' in lines
        assert 'item_count: must be greater than 0. item_count: 0' in lines

    def test_table_model_validator_error(self):
        """Test formatting Table model validator error."""
        with pytest.raises(ValidationError) as exc_info:
            Table(
                name='test',
                item_count=1000,
                item_size_bytes=1000,
                gsi_list=[{'name': 'gsi-1', 'item_size_bytes': 2000, 'item_count': 100}],
            )
        result = format_validation_errors(exc_info.value)
        assert (
            result
            == 'GSI item_size_bytes cannot exceed table item_size_bytes. gsi_item_size_bytes: 2000, table_item_size_bytes: 1000'
        )

    def test_table_nested_array_error(self):
        """Test formatting Table error with nested array location."""
        with pytest.raises(ValidationError) as exc_info:
            Table(
                name='test',
                item_count=1000,
                item_size_bytes=2000,
                gsi_list=[
                    {'name': 'gsi-1', 'item_size_bytes': 1000, 'item_count': 100},
                    {'name': '', 'item_size_bytes': 1000, 'item_count': 100},
                ],
            )
        result = format_validation_errors(exc_info.value)
        assert result == 'gsi_list[1].name: cannot be empty. name: '

    def test_table_field_validator_error(self):
        """Test formatting Table field validator error (duplicate GSI names)."""
        with pytest.raises(ValidationError) as exc_info:
            Table(
                name='test',
                item_count=1000,
                item_size_bytes=2000,
                gsi_list=[
                    {'name': 'dup', 'item_size_bytes': 1000, 'item_count': 100},
                    {'name': 'dup', 'item_size_bytes': 1000, 'item_count': 100},
                ],
            )
        result = format_validation_errors(exc_info.value)
        assert result == 'gsi_list: duplicate GSI name. name: "dup"'

    def test_access_pattern_model_validator_error(self):
        """Test formatting access pattern model validator error."""
        with pytest.raises(ValidationError) as exc_info:
            QueryAccessPattern(
                operation='Query',
                pattern='test',
                description='test',
                table='test-table',
                rps=100,
                item_size_bytes=1000,
                item_count=10,
                gsi='test-gsi',
                strongly_consistent=True,
            )
        result = format_validation_errors(exc_info.value)
        assert (
            result
            == 'GSI does not support strongly consistent reads. gsi: "test-gsi", strongly_consistent: True'
        )

    def test_access_pattern_field_validator_error(self):
        """Test formatting access pattern field validator error."""
        with pytest.raises(ValidationError) as exc_info:
            PutItemAccessPattern(
                operation='PutItem',
                pattern='test',
                description='test',
                table='test-table',
                rps=100,
                item_size_bytes=1000,
                gsi_list=['gsi-1', ''],
            )
        result = format_validation_errors(exc_info.value)
        assert result == 'gsi_list: GSI name cannot be empty'

    def test_datamodel_cross_reference_error(self):
        """Test formatting DataModel cross-reference validation error."""
        with pytest.raises(ValidationError) as exc_info:
            DataModel(
                access_pattern_list=[
                    {
                        'operation': 'GetItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'non-existent',
                        'rps': 100,
                        'item_size_bytes': 1000,
                    }
                ],
                table_list=[{'name': 'test-table', 'item_count': 1000, 'item_size_bytes': 2000}],
            )
        result = format_validation_errors(exc_info.value)
        assert result == 'table does not exist. table: "non-existent"'

    def test_datamodel_empty_access_patterns_error(self):
        """Test formatting DataModel empty access patterns error."""
        with pytest.raises(ValidationError) as exc_info:
            DataModel(
                access_pattern_list=[],
                table_list=[{'name': 'test-table', 'item_count': 1000, 'item_size_bytes': 2000}],
            )
        result = format_validation_errors(exc_info.value)
        assert (
            result
            == 'access_pattern_list: access_pattern_list must contain at least one access pattern'
        )

    def test_missing_required_field(self):
        """Test formatting error for missing required field."""
        with pytest.raises(ValidationError) as exc_info:
            GSI(item_size_bytes=1000, item_count=100)  # type: ignore[call-arg]
        result = format_validation_errors(exc_info.value)
        assert result == 'name: Field required'

    def test_discriminated_union_error(self):
        """Test formatting discriminated union error (invalid operation type)."""
        with pytest.raises(ValidationError) as exc_info:
            DataModel(
                access_pattern_list=[
                    {
                        'operation': 'InvalidOperation',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 100,
                        'item_size_bytes': 1000,
                    }
                ],
                table_list=[{'name': 'test-table', 'item_count': 1000, 'item_size_bytes': 2000}],
            )
        result = format_validation_errors(exc_info.value)
        assert 'access_pattern_list[0]:' in result
        assert "Input tag 'InvalidOperation' found using 'operation'" in result
