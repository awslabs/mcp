"""Unit tests for validation_utils module."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.validation_utils import (
    ValidationError,
    ValidationResult,
)


@pytest.mark.unit
class TestValidationError:
    """Unit tests for ValidationError dataclass."""

    def test_creation_with_default_severity(self):
        """Test ValidationError creation with default severity."""
        error = ValidationError(
            path='entities.User.fields[0].type',
            message='Invalid field type',
            suggestion="Use 'string' instead of 'str'",
        )
        assert error.path == 'entities.User.fields[0].type'
        assert error.message == 'Invalid field type'
        assert error.suggestion == "Use 'string' instead of 'str'"
        assert error.severity == 'error'

    def test_creation_with_custom_severity(self):
        """Test ValidationError creation with custom severity."""
        warning = ValidationError(
            path='entities.User.name',
            message='Field name should be descriptive',
            suggestion='Consider using a more descriptive name',
            severity='warning',
        )
        assert warning.severity == 'warning'


@pytest.mark.unit
class TestValidationResult:
    """Unit tests for ValidationResult dataclass."""

    def test_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        """Test adding a single error."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_error('test.path', 'Test error', 'Test suggestion')
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].path == 'test.path'
        assert result.errors[0].severity == 'error'

    def test_add_errors(self):
        """Test adding multiple errors."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        errors = [
            ValidationError('path1', 'msg1', 'sug1'),
            ValidationError('path2', 'msg2', 'sug2'),
        ]
        result.add_errors(errors)
        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_warning('test.path', 'Test warning', 'Test suggestion')
        assert result.is_valid is True  # Warnings don't change is_valid
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == 'warning'

    def test_store_entity_info(self):
        """Test storing extracted entity information."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        entities = {'User', 'Order'}
        entity_fields = {'User': {'id', 'name'}, 'Order': {'id', 'total'}}

        result.store_entity_info(entities, entity_fields)

        assert result.extracted_entities == entities
        assert result.extracted_entity_fields == entity_fields

    def test_format_success(self):
        """Test formatting successful validation result."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        formatted = result.format('Test passed', 'Test failed')
        assert formatted == '✅ Test passed'

    def test_format_with_errors(self):
        """Test formatting validation result with errors."""
        result = ValidationResult(is_valid=False, errors=[], warnings=[])
        result.add_error('test.path', 'Test error message', 'Test suggestion')
        formatted = result.format('Test passed', 'Test failed')
        assert '❌ Test failed:' in formatted
        assert 'test.path: Test error message' in formatted
        assert '💡 Test suggestion' in formatted

    def test_format_with_warnings(self):
        """Test formatting validation result with warnings."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_warning('test.path', 'Test warning message', 'Test suggestion')
        formatted = result.format('Test passed', 'Test failed')
        assert '⚠️  Warnings:' in formatted
        assert 'test.path: Test warning message' in formatted
        assert '💡 Test suggestion' in formatted

    def test_format_with_errors_and_warnings(self):
        """Test formatting validation result with both errors and warnings."""
        result = ValidationResult(is_valid=False, errors=[], warnings=[])
        result.add_error('error.path', 'Error message', 'Error suggestion')
        result.add_warning('warning.path', 'Warning message', 'Warning suggestion')
        formatted = result.format('Test passed', 'Test failed')
        assert '❌ Test failed:' in formatted
        assert 'error.path: Error message' in formatted
        assert '⚠️  Warnings:' in formatted
        assert 'warning.path: Warning message' in formatted
