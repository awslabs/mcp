"""Tests for awslabs.etl_replatforming_mcp_server.models.exceptions"""

import pytest

from awslabs.etl_replatforming_mcp_server.models.exceptions import (
    ConversionError,
    ParsingError,
)


class TestExceptions:
    """Tests for awslabs.etl_replatforming_mcp_server.models.exceptions"""

    def test_conversion_error_base(self):
        """Test ConversionError base exception"""
        error = ConversionError('Base error message')
        assert str(error) == 'Base error message'
        assert isinstance(error, Exception)

    def test_conversion_error_with_context(self):
        """Test ConversionError with context"""
        context = {'file': 'test.py', 'line': 42}
        error = ConversionError('Error with context', context)
        assert str(error) == 'Error with context'
        assert error.context == context

    def test_parsing_error(self):
        """Test ParsingError exception"""
        error = ParsingError('Failed to parse workflow')
        assert str(error) == 'Failed to parse workflow'
        assert isinstance(error, ConversionError)

    def test_parsing_error_with_context(self):
        """Test ParsingError with context"""
        context = {'parser': 'airflow', 'task_id': 'test_task'}
        error = ParsingError('Parsing failed', context)
        assert str(error) == 'Parsing failed'
        assert error.context == context
        assert isinstance(error, ConversionError)

    def test_exception_inheritance_chain(self):
        """Test that ParsingError inherits from ConversionError"""
        parsing_error = ParsingError('test')
        assert isinstance(parsing_error, ConversionError)
        assert isinstance(parsing_error, Exception)

    def test_conversion_error_default_context(self):
        """Test ConversionError with default empty context"""
        error = ConversionError('Test message')
        assert error.context == {}

    def test_parsing_error_default_context(self):
        """Test ParsingError with default empty context"""
        error = ParsingError('Test message')
        assert error.context == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
