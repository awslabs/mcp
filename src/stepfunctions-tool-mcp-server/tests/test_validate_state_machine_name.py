"""Tests for the validate_state_machine_name function."""

import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import validate_state_machine_name


class TestValidateName:
    """Tests for the validate_state_machine_name function."""

    def test_validate_name_no_filters(self):
        """Test name validation with no filters configured."""
        # Set up test cases
        test_cases = [
            'any-state-machine',
            'test-machine',
            'prefix-machine',
            '',  # Empty name
            'machine1',
            'machine-with-hyphens',
            'machine_with_underscores',
        ]

        # Test each case
        for name in test_cases:
            result = validate_state_machine_name(name)
            assert result is True

    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_PREFIX', 'test-')
    def test_validate_name_prefix_filter(self):
        """Test name validation with prefix filter."""
        # Set up test cases
        test_cases = [
            ('test-state-machine', True),  # Valid prefix
            ('test-another-machine', True),  # Valid prefix
            ('other-state-machine', False),  # Invalid prefix
            ('testing-machine', False),  # Similar but invalid prefix
            ('test-', True),  # Just the prefix
            ('test', False),  # Incomplete prefix
            ('', False),  # Empty name
        ]

        # Test each case
        for name, expected in test_cases:
            result = validate_state_machine_name(name)
            assert result is expected

    @patch(
        'awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_LIST',
        ['machine1', 'machine2', 'test-machine'],
    )
    def test_validate_name_list_filter(self):
        """Test name validation with list filter."""
        # Set up test cases
        test_cases = [
            ('machine1', True),  # In list
            ('machine2', True),  # In list
            ('test-machine', True),  # In list
            ('machine3', False),  # Not in list
            ('test-machine-2', False),  # Similar but not in list
            ('', False),  # Empty name
        ]

        # Test each case
        for name, expected in test_cases:
            result = validate_state_machine_name(name)
            assert result is expected

    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_PREFIX', 'test-')
    @patch(
        'awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_LIST', ['machine1', 'machine2']
    )
    def test_validate_name_both_filters(self):
        """Test name validation with both prefix and list filters."""
        # Set up test cases
        test_cases = [
            ('test-state-machine', True),  # Matches prefix
            ('machine1', True),  # In list
            ('machine2', True),  # In list
            ('other-machine', False),  # No match
            ('test-machine1', True),  # Matches prefix
            ('test', False),  # Incomplete prefix
            ('', False),  # Empty name
        ]

        # Test each case
        for name, expected in test_cases:
            result = validate_state_machine_name(name)
            assert result is expected

    def test_validate_name_edge_cases(self):
        """Test edge cases for name validation."""
        # Test with no filters
        assert validate_state_machine_name('') is True
        assert validate_state_machine_name(' ') is True
        assert validate_state_machine_name('\t') is True
        assert validate_state_machine_name('\n') is True

        # Test with prefix
        with patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_PREFIX', 'test-'):
            assert validate_state_machine_name('') is False
            assert validate_state_machine_name(' ') is False
            assert validate_state_machine_name('test-') is True
            assert validate_state_machine_name('test- ') is True

        # Test with list
        with patch(
            'awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_LIST', ['name1', 'name2']
        ):
            assert validate_state_machine_name('') is False
            assert validate_state_machine_name(' ') is False
            assert validate_state_machine_name('name1 ') is False
            assert validate_state_machine_name(' name1') is False

    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_PREFIX', '')
    @patch('awslabs.stepfunctions_tool_mcp_server.server.STATE_MACHINE_LIST', [])
    def test_validate_name_empty_filters(self):
        """Test name validation with explicitly empty filters."""
        # Set up test cases
        test_cases = [
            'any-machine',
            'test-machine',
            'machine1',
            '',
            ' ',
            'machine-with-spaces ',
            ' prefixed-machine',
        ]

        # Test each case
        for name in test_cases:
            result = validate_state_machine_name(name)
            assert result is True
