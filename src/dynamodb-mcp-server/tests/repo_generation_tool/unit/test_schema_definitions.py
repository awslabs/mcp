"""Unit tests for schema definitions."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    VALID_FILTER_FUNCTIONS,
    VALID_FILTER_LOGICAL_OPERATORS,
    VALID_FILTER_OPERATORS,
    DynamoDBOperation,
    DynamoDBType,
    FieldType,
    FilterCondition,
    GSIProjectionType,
    ParameterType,
    RangeCondition,
    ReturnType,
    get_all_enum_classes,
    get_enum_values,
    is_valid_enum_value,
    suggest_enum_value,
    validate_data_type,
    validate_enum_field,
    validate_required_fields,
)


@pytest.mark.unit
class TestEnumUtilities:
    """Unit tests for enum utility functions."""

    def test_get_enum_values(self):
        """Test getting enum values as strings."""
        field_type_values = get_enum_values(FieldType)
        expected = ['string', 'integer', 'decimal', 'boolean', 'array', 'object', 'uuid']

        assert set(field_type_values) == set(expected)
        assert all(isinstance(value, str) for value in field_type_values)

    def test_is_valid_enum_value(self):
        """Test is_valid_enum_value with valid and invalid cases."""
        # Valid cases
        assert is_valid_enum_value('string', FieldType) is True
        assert is_valid_enum_value('Query', DynamoDBOperation) is True
        assert is_valid_enum_value('entity_list', ReturnType) is True

        # Invalid cases
        assert is_valid_enum_value('invalid_type', FieldType) is False
        assert is_valid_enum_value('GetItems', DynamoDBOperation) is False
        assert is_valid_enum_value('', FieldType) is False

    def test_suggest_enum_value_scenarios(self):
        """Test enum value suggestion for various input scenarios."""
        # Substring match
        suggestion = suggest_enum_value('str', FieldType)
        assert 'string' in suggestion and 'Valid options:' in suggestion

        # Prefix match
        suggestion = suggest_enum_value('int', FieldType)
        assert 'integer' in suggestion and 'Valid options:' in suggestion

        # No match case
        suggestion = suggest_enum_value('xyz', FieldType)
        assert 'Valid options:' in suggestion and 'string' in suggestion

    def test_get_all_enum_classes(self):
        """Test getting all enum classes mapping."""
        enum_classes = get_all_enum_classes()

        expected_keys = {
            'FieldType',
            'ReturnType',
            'DynamoDBOperation',
            'ParameterType',
            'DynamoDBType',
            'RangeCondition',
            'GSIProjectionType',
        }
        assert set(enum_classes.keys()) == expected_keys

        # Verify the mappings are correct
        assert enum_classes['FieldType'] == FieldType
        assert enum_classes['ReturnType'] == ReturnType
        assert enum_classes['DynamoDBOperation'] == DynamoDBOperation
        assert enum_classes['ParameterType'] == ParameterType
        assert enum_classes['RangeCondition'] == RangeCondition
        assert enum_classes['DynamoDBType'] == DynamoDBType
        assert enum_classes['GSIProjectionType'] == GSIProjectionType


@pytest.mark.unit
class TestFieldValidationHelpers:
    """Unit tests for field validation helper functions."""

    def test_validate_required_fields_all_present(self):
        """Test validate_required_fields when all fields are present."""
        data = {'name': 'test', 'type': 'string', 'required': True}
        required_fields = {'name', 'type', 'required'}
        errors = validate_required_fields(data, required_fields, 'test.field')
        assert errors == []

    def test_validate_required_fields_missing_fields(self):
        """Test validate_required_fields when fields are missing."""
        data = {'name': 'test'}
        required_fields = {'name', 'type', 'required'}
        errors = validate_required_fields(data, required_fields, 'test.field')
        assert len(errors) == 2
        missing_fields = {error.path.split('.')[-1] for error in errors}
        assert missing_fields == {'type', 'required'}
        for error in errors:
            assert error.path.startswith('test.field.')
            assert 'Missing required field' in error.message

    def test_validate_enum_field_valid_value(self):
        """Test validate_enum_field with valid enum value."""
        errors = validate_enum_field('string', FieldType, 'test.field', 'type')
        assert errors == []

    def test_validate_enum_field_invalid_value(self):
        """Test validate_enum_field with invalid enum value."""
        errors = validate_enum_field('invalid_type', FieldType, 'test.field', 'type')
        assert len(errors) == 1
        assert "Invalid type value 'invalid_type'" in errors[0].message

    def test_validate_enum_field_non_string_value(self):
        """Test validate_enum_field with non-string value."""
        errors = validate_enum_field(123, FieldType, 'test.field', 'type')
        assert len(errors) == 1
        assert 'must be a string, got int' in errors[0].message

    def test_validate_data_type_correct_type(self):
        """Test validate_data_type with correct type."""
        errors = validate_data_type('test_string', str, 'test.field', 'name')
        assert errors == []

    def test_validate_data_type_incorrect_type(self):
        """Test validate_data_type with incorrect type."""
        errors = validate_data_type(123, str, 'test.field', 'name')
        assert len(errors) == 1
        assert 'must be str, got int' in errors[0].message


@pytest.mark.unit
class TestFilterConditionDataclass:
    """Unit tests for FilterCondition dataclass and filter expression constants."""

    def test_filter_condition_comparison(self):
        """Test FilterCondition with comparison operator."""
        fc = FilterCondition(field='status', operator='<>', param='excluded_status')
        assert fc.field == 'status'
        assert fc.operator == '<>'
        assert fc.param == 'excluded_status'
        assert fc.function is None
        assert fc.param2 is None
        assert fc.params is None

    def test_filter_condition_between(self):
        """Test FilterCondition with between operator."""
        fc = FilterCondition(
            field='price', operator='between', param='min_price', param2='max_price'
        )
        assert fc.operator == 'between'
        assert fc.param == 'min_price'
        assert fc.param2 == 'max_price'

    def test_filter_condition_in(self):
        """Test FilterCondition with in operator."""
        fc = FilterCondition(field='status', operator='in', params=['s1', 's2', 's3'])
        assert fc.operator == 'in'
        assert fc.params == ['s1', 's2', 's3']

    def test_filter_condition_contains(self):
        """Test FilterCondition with contains function."""
        fc = FilterCondition(field='tags', function='contains', param='tag_val')
        assert fc.function == 'contains'
        assert fc.param == 'tag_val'
        assert fc.operator is None

    def test_filter_condition_begins_with(self):
        """Test FilterCondition with begins_with function."""
        fc = FilterCondition(field='name', function='begins_with', param='prefix')
        assert fc.function == 'begins_with'
        assert fc.param == 'prefix'

    def test_filter_condition_attribute_exists(self):
        """Test FilterCondition with attribute_exists function (no param)."""
        fc = FilterCondition(field='email_verified', function='attribute_exists')
        assert fc.function == 'attribute_exists'
        assert fc.param is None
        assert fc.param2 is None
        assert fc.params is None

    def test_filter_condition_attribute_not_exists(self):
        """Test FilterCondition with attribute_not_exists function (no param)."""
        fc = FilterCondition(field='deleted_at', function='attribute_not_exists')
        assert fc.function == 'attribute_not_exists'
        assert fc.param is None

    def test_filter_condition_size_comparison(self):
        """Test FilterCondition with size function and comparison operator."""
        fc = FilterCondition(field='items', function='size', operator='>', param='min_items')
        assert fc.function == 'size'
        assert fc.operator == '>'
        assert fc.param == 'min_items'

    def test_filter_condition_size_between(self):
        """Test FilterCondition with size function and between operator."""
        fc = FilterCondition(
            field='items', function='size', operator='between', param='min_c', param2='max_c'
        )
        assert fc.function == 'size'
        assert fc.operator == 'between'
        assert fc.param == 'min_c'
        assert fc.param2 == 'max_c'

    def test_filter_condition_minimal(self):
        """Test FilterCondition with only required field."""
        fc = FilterCondition(field='test_field')
        assert fc.field == 'test_field'
        assert fc.operator is None
        assert fc.function is None
        assert fc.param is None
        assert fc.param2 is None
        assert fc.params is None

    def test_valid_filter_operators_constant(self):
        """Test VALID_FILTER_OPERATORS contains all expected operators."""
        expected = {'=', '<>', '<', '<=', '>', '>=', 'between', 'in'}
        assert VALID_FILTER_OPERATORS == expected
        assert isinstance(VALID_FILTER_OPERATORS, frozenset)

    def test_valid_filter_functions_constant(self):
        """Test VALID_FILTER_FUNCTIONS contains all expected functions."""
        expected = {'contains', 'begins_with', 'attribute_exists', 'attribute_not_exists', 'size'}
        assert VALID_FILTER_FUNCTIONS == expected
        assert isinstance(VALID_FILTER_FUNCTIONS, frozenset)

    def test_valid_filter_logical_operators_constant(self):
        """Test VALID_FILTER_LOGICAL_OPERATORS contains AND and OR."""
        assert VALID_FILTER_LOGICAL_OPERATORS == {'AND', 'OR'}
        assert isinstance(VALID_FILTER_LOGICAL_OPERATORS, frozenset)
