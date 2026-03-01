"""Unit tests for template parameter extraction system."""

import pytest
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.key_template_parser import (
    KeyTemplateParser,
)
from awslabs.dynamodb_mcp_server.repo_generation_tool.core.schema_definitions import Field


@pytest.mark.unit
class TestKeyTemplateParser:
    """Unit tests for KeyTemplateParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = KeyTemplateParser()

        # Sample entity fields for testing
        self.entity_fields = [
            Field(name='user_id', type='string', required=True),
            Field(name='status', type='string', required=False),
            Field(name='created_at', type='string', required=True),
            Field(name='score', type='integer', required=False),
        ]


@pytest.mark.unit
class TestExtractParameters(TestKeyTemplateParser):
    """Test parameter extraction from templates."""

    def test_extract_parameters_multiple_params(self):
        """Test extracting multiple parameters from template."""
        assert self.parser.extract_parameters('STATUS#{status}#USER#{user_id}') == [
            'status',
            'user_id',
        ]

    def test_extract_parameters_no_params(self):
        """Test extracting parameters from template with no parameters."""
        assert self.parser.extract_parameters('PROFILE') == []

    def test_extract_parameters_duplicate_params(self):
        """Test extracting parameters with duplicates (should return unique)."""
        assert self.parser.extract_parameters('USER#{user_id}#STATUS#{status}#USER#{user_id}') == [
            'user_id',
            'status',
        ]

    def test_extract_parameters_non_string_input(self):
        """Test extracting parameters from non-string input."""
        assert self.parser.extract_parameters(None) == []
        assert self.parser.extract_parameters(123) == []

    def test_extract_parameters_with_format_specifiers(self):
        """Test extracting parameters from templates with Python format specifiers."""
        # Integer format specifiers
        assert self.parser.extract_parameters('LESSON#{lesson_order:05d}') == ['lesson_order']
        assert self.parser.extract_parameters('SCORE#{score:04d}') == ['score']

        # Decimal format specifiers
        assert self.parser.extract_parameters('PRICE#{price:.2f}') == ['price']
        assert self.parser.extract_parameters('AMOUNT#{amount:,.2f}') == ['amount']

        # String format specifiers
        assert self.parser.extract_parameters('NAME#{name:>20}') == ['name']
        assert self.parser.extract_parameters('CODE#{code:<10}') == ['code']

        # Multiple params with format specs
        assert self.parser.extract_parameters('ORDER#{order_id:08d}#ITEM#{item_id:04d}') == [
            'order_id',
            'item_id',
        ]

        # Mixed: some with format specs, some without
        assert self.parser.extract_parameters('USER#{user_id}#SCORE#{score:05d}') == [
            'user_id',
            'score',
        ]


@pytest.mark.unit
class TestValidateParameters(TestKeyTemplateParser):
    """Test parameter validation against entity fields."""

    def test_validate_parameters_all_valid(self):
        """Test validation when all parameters exist in entity fields."""
        assert self.parser.validate_parameters(['user_id', 'status'], self.entity_fields) == []

    def test_validate_parameters_missing_field(self):
        """Test validation when parameter doesn't exist in entity fields."""
        errors = self.parser.validate_parameters(['user_id', 'invalid_field'], self.entity_fields)
        assert len(errors) == 1
        assert errors[0].path == 'template.parameter.invalid_field'
        assert "Template parameter 'invalid_field' not found in entity fields" in errors[0].message

    def test_validate_parameters_multiple_missing(self):
        """Test validation when multiple parameters are missing."""
        errors = self.parser.validate_parameters(
            ['invalid1', 'user_id', 'invalid2'], self.entity_fields
        )
        assert len(errors) == 2
        assert {error.path.split('.')[-1] for error in errors} == {'invalid1', 'invalid2'}

    def test_validate_parameters_empty_fields(self):
        """Test validation with empty entity fields."""
        errors = self.parser.validate_parameters(['user_id'], [])
        assert len(errors) == 1
        assert 'not found in entity fields' in errors[0].message


@pytest.mark.unit
class TestValidateTemplateSyntax(TestKeyTemplateParser):
    """Test template syntax validation."""

    def test_validate_syntax_valid_template(self):
        """Test validation of valid template syntax."""
        assert self.parser.validate_template_syntax('USER#{user_id}#STATUS#{status}') == []
        assert self.parser.validate_template_syntax('PROFILE') == []

    def test_validate_syntax_non_string(self):
        """Test validation of non-string template."""
        errors = self.parser.validate_template_syntax(None)
        assert len(errors) == 1
        assert 'Template must be a string' in errors[0].message

    def test_validate_syntax_empty_template(self):
        """Test validation of empty template."""
        assert len(self.parser.validate_template_syntax('')) == 1
        assert 'Template cannot be empty' in self.parser.validate_template_syntax('')[0].message

    def test_validate_syntax_unmatched_braces(self):
        """Test validation of template with unmatched braces."""
        errors = self.parser.validate_template_syntax('USER#{user_id}#{')
        assert len(errors) == 1
        assert 'Unmatched braces' in errors[0].message
        assert '2 opening, 1 closing' in errors[0].message

    def test_validate_syntax_empty_parameters(self):
        """Test validation of template with empty parameter placeholders."""
        errors = self.parser.validate_template_syntax('USER#{}#STATUS#{status}')
        assert len(errors) == 1
        assert 'empty parameter placeholders' in errors[0].message

    def test_validate_syntax_invalid_parameter_names(self):
        """Test validation of template with invalid parameter names."""
        errors = self.parser.validate_template_syntax('USER#{user id}#STATUS#{status}')
        assert len(errors) == 1
        assert 'invalid parameter names' in errors[0].message
        assert 'user id' in errors[0].message
