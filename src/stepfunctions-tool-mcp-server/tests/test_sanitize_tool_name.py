"""Tests for the sanitize_tool_name function."""

import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import sanitize_tool_name


class TestSanitizeName:
    """Tests for the sanitize_tool_name function."""

    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_PREFIX', 'prefix-')
    def test_sanitize_name_prefix_removal(self):
        """Test removing prefix from state machine name."""
        # Set up test data
        name = 'prefix-state-machine'

        # Call the function
        result = sanitize_tool_name(name)

        # Verify results
        assert result == 'state_machine'

    def test_sanitize_name_invalid_chars(self):
        """Test replacing invalid characters with underscores."""
        # Set up test cases
        test_cases = [
            ('function-name', 'function_name'),
            ('name.with.dots', 'name_with_dots'),
            ('name:with:colons', 'name_with_colons'),
            ('name@with@at', 'name_with_at'),
            ('mixed!@#$%^chars', 'mixed______chars'),
            ('multiple---dashes', 'multiple___dashes'),
        ]

        # Test each case
        for input_name, expected in test_cases:
            result = sanitize_tool_name(input_name)
            assert result == expected

    def test_sanitize_name_numeric_start(self):
        """Test handling names that start with numbers."""
        # Set up test cases
        test_cases = [
            ('123function', '_123function'),
            ('456_name', '_456_name'),
            ('789-name', '_789_name'),
            ('0function', '_0function'),
        ]

        # Test each case
        for input_name, expected in test_cases:
            result = sanitize_tool_name(input_name)
            assert result == expected

    def test_sanitize_name_already_valid(self):
        """Test handling already valid names."""
        # Set up test cases
        test_cases = [
            'valid_name',
            'another_valid_name',
            '_starts_with_underscore',
            'ends_with_underscore_',
            'contains_numbers_123',
        ]

        # Test each case
        for name in test_cases:
            result = sanitize_tool_name(name)
            assert result == name

    def test_sanitize_name_edge_cases(self):
        """Test edge cases for name sanitization."""
        # Set up test cases
        test_cases = [
            ('', ''),  # Empty string
            ('!@#$%^', '______'),  # Only invalid characters
            ('   spaces   ', '___spaces___'),  # Spaces
            ('\ttabs\t', '_tabs_'),  # Tabs
            ('\nnewlines\n', '_newlines_'),  # Newlines
            ('mixed\t@#$\nchars', 'mixed_____chars'),  # Mixed whitespace and special chars
        ]

        # Test each case
        for input_name, expected in test_cases:
            result = sanitize_tool_name(input_name)
            assert result == expected

    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_PREFIX', 'prefix-')
    def test_sanitize_name_complex_cases(self):
        """Test complex combinations of sanitization rules."""
        # Set up test cases
        test_cases = [
            ('prefix-123-function@name', '_123_function_name'),  # Prefix and invalid chars
            (
                'prefix-456.name!with#chars',
                '_456_name_with_chars',
            ),  # Prefix, numbers, and special chars
            ('prefix-789_already_valid', '_789_already_valid'),  # Prefix with valid name
            ('prefix-000!@#valid', '_000___valid'),  # Prefix, numbers, and mixed chars
        ]

        # Test each case
        for input_name, expected in test_cases:
            result = sanitize_tool_name(input_name)
            assert result == expected
