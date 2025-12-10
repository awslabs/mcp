"""Unit tests for schema definitions and validation utilities."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import (
    DynamoDBOperation,
    DynamoDBType,
    FieldType,
    ParameterType,
    RangeCondition,
    ReturnType,
    ValidationError,
    ValidationResult,
    get_all_enum_classes,
    get_enum_values,
    is_valid_enum_value,
    suggest_enum_value,
    validate_data_type,
    validate_enum_field,
    validate_required_fields,
)


@pytest.mark.unit
class TestValidationDataClasses:
    """Unit tests for validation data classes."""

    def test_validation_error_and_result_functionality(self):
        """Test ValidationError and ValidationResult comprehensive functionality."""
        # Test ValidationError creation with default severity
        error = ValidationError(
            path='entities.User.fields[0].type',
            message='Invalid field type',
            suggestion="Use 'string' instead of 'str'",
        )
        assert error.path == 'entities.User.fields[0].type'
        assert error.message == 'Invalid field type'
        assert error.suggestion == "Use 'string' instead of 'str'"
        assert error.severity == 'error'

        # Test ValidationError with custom severity
        warning = ValidationError(
            path='entities.User.name',
            message='Field name should be descriptive',
            suggestion='Consider using a more descriptive name',
            severity='warning',
        )
        assert warning.severity == 'warning'

        # Test ValidationResult creation and methods
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

        # Test adding error
        result.add_error('test.path', 'Test error', 'Test suggestion')
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].path == 'test.path'
        assert result.errors[0].severity == 'error'

        # Test adding multiple errors
        errors = [
            ValidationError('path1', 'msg1', 'sug1'),
            ValidationError('path2', 'msg2', 'sug2'),
        ]
        result.add_errors(errors)
        assert len(result.errors) == 3

        # Test adding warning
        result.add_warning('test.path', 'Test warning', 'Test suggestion')
        assert result.is_valid is False  # Still false due to error
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == 'warning'


@pytest.mark.unit
class TestValidationUtilities:
    """Unit tests for validation utility functions."""

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
        }
        assert set(enum_classes.keys()) == expected_keys

        # Verify the mappings are correct
        assert enum_classes['FieldType'] == FieldType
        assert enum_classes['ReturnType'] == ReturnType
        assert enum_classes['DynamoDBOperation'] == DynamoDBOperation
        assert enum_classes['ParameterType'] == ParameterType
        assert enum_classes['RangeCondition'] == RangeCondition
        assert enum_classes['DynamoDBType'] == DynamoDBType


@pytest.mark.unit
class TestValidationFunctions:
    """Unit tests for validation functions."""

    def test_validation_functions_comprehensive(self):
        """Test all validation functions with various scenarios."""
        # Test validate_required_fields - all present
        data = {'name': 'test', 'type': 'string', 'required': True}
        required_fields = {'name', 'type', 'required'}
        errors = validate_required_fields(data, required_fields, 'test.field')
        assert errors == []

        # Test validate_required_fields - missing fields
        data = {'name': 'test'}
        errors = validate_required_fields(data, required_fields, 'test.field')
        assert len(errors) == 2
        missing_fields = {error.path.split('.')[-1] for error in errors}
        assert missing_fields == {'type', 'required'}
        for error in errors:
            assert (
                error.path.startswith('test.field.') and 'Missing required field' in error.message
            )

        # Test validate_enum_field - valid value
        assert validate_enum_field('string', FieldType, 'test.field', 'type') == []

        # Test validate_enum_field - invalid value
        errors = validate_enum_field('invalid_type', FieldType, 'test.field', 'type')
        assert len(errors) == 1 and "Invalid type value 'invalid_type'" in errors[0].message

        # Test validate_enum_field - non-string value
        errors = validate_enum_field(123, FieldType, 'test.field', 'type')
        assert len(errors) == 1 and 'must be a string, got int' in errors[0].message

        # Test validate_data_type - correct type
        assert validate_data_type('test_string', str, 'test.field', 'name') == []

        # Test validate_data_type - incorrect type
        errors = validate_data_type(123, str, 'test.field', 'name')
        assert len(errors) == 1 and 'must be str, got int' in errors[0].message
