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

"""Tests for the cloudtrail MCP Server."""

import pytest
from awslabs.cloudtrail_mcp_server.common import (
    parse_relative_time,
    parse_time_input,
    remove_null_values,
    validate_max_results,
)
from awslabs.cloudtrail_mcp_server.tools import CloudTrailTools
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch


def test_server_import():
    """Test that the server module can be imported without errors."""
    # This test ensures the server can be imported and initialized
    from awslabs.cloudtrail_mcp_server import server

    assert server is not None


def test_cloudtrail_tools_initialization():
    """Test CloudTrail tools can be initialized."""
    tools = CloudTrailTools()
    assert tools is not None


class TestCommonUtilities:
    """Test cases for common utility functions."""

    def test_parse_relative_time_valid_inputs(self):
        """Test parse_relative_time with valid inputs."""
        now = datetime.now(timezone.utc)

        # Test various time units
        result = parse_relative_time('1 hour ago')
        expected = now - timedelta(hours=1)
        assert abs((result - expected).total_seconds()) < 2  # Allow 2 second tolerance

        result = parse_relative_time('2 days ago')
        expected = now - timedelta(days=2)
        assert abs((result - expected).total_seconds()) < 2

        result = parse_relative_time('now')
        assert abs((result - now).total_seconds()) < 2

    def test_parse_relative_time_invalid_input(self):
        """Test parse_relative_time with invalid input."""
        with pytest.raises(ValueError):
            parse_relative_time('invalid time format')

    def test_parse_time_input_iso_format(self):
        """Test parse_time_input with ISO format."""
        iso_time = '2023-01-01T12:00:00Z'
        result = parse_time_input(iso_time)
        expected = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_time_input_relative_format(self):
        """Test parse_time_input with relative format."""
        result = parse_time_input('1 day ago')
        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=1)
        assert abs((result - expected).total_seconds()) < 2

    def test_validate_max_results(self):
        """Test validate_max_results function."""
        # Test default behavior
        assert validate_max_results(None, default=10, max_allowed=50) == 10

        # Test normal values
        assert validate_max_results(25, default=10, max_allowed=50) == 25

        # Test boundary conditions
        assert validate_max_results(0, default=10, max_allowed=50) == 1
        assert validate_max_results(100, default=10, max_allowed=50) == 50

    def test_remove_null_values(self):
        """Test remove_null_values function."""
        # Test with mixed data
        data = {
            'key1': 'value1',
            'key2': None,
            'key3': 'value3',
            'key4': None,
            'key5': 0,  # Should keep 0
            'key6': '',  # Should keep empty string
            'key7': False,  # Should keep False
        }

        result = remove_null_values(data)
        expected = {
            'key1': 'value1',
            'key3': 'value3',
            'key5': 0,
            'key6': '',
            'key7': False,
        }

        assert result == expected

        # Test with empty dict
        assert remove_null_values({}) == {}

        # Test with all None values
        assert remove_null_values({'a': None, 'b': None}) == {}

        # Test with no None values
        data_no_none = {'a': 1, 'b': 'test'}
        assert remove_null_values(data_no_none) == data_no_none

    def test_parse_time_input_various_formats(self):
        """Test parse_time_input with various ISO formats."""
        # Test different ISO formats
        test_cases = [
            ('2023-01-01T12:00:00Z', datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)),
            ('2023-01-01T12:00:00+00:00', datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)),
            ('2023-01-01 12:00:00', datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)),
            ('2023-01-01', datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        ]

        for input_str, expected in test_cases:
            result = parse_time_input(input_str)
            assert result == expected, f'Failed for input: {input_str}'

    def test_parse_time_input_invalid_format_with_comprehensive_error(self):
        """Test parse_time_input with invalid format shows comprehensive error message."""
        with pytest.raises(ValueError) as exc_info:
            parse_time_input('invalid-time-format')

        error_msg = str(exc_info.value)
        # Verify the error message contains comprehensive information
        assert "Unable to parse time input 'invalid-time-format'" in error_msg
        assert 'Relative time parsing error:' in error_msg
        assert 'ISO format errors:' in error_msg

    def test_parse_time_input_partially_invalid_iso_with_detailed_errors(self):
        """Test parse_time_input with partially valid ISO format shows detailed errors."""
        with pytest.raises(ValueError) as exc_info:
            parse_time_input('2023-13-45T99:99:99Z')  # Invalid month, day, and time

        error_msg = str(exc_info.value)
        # Should contain comprehensive error information
        assert 'Unable to parse time input' in error_msg
        assert 'Relative time parsing error:' in error_msg
        assert 'ISO format errors:' in error_msg

    def test_parse_time_input_edge_cases(self):
        """Test parse_time_input with various edge cases."""
        # Test cases that should still work
        valid_cases = [
            ('now', datetime.now(timezone.utc)),  # Should be close to current time
            ('1 minute ago', datetime.now(timezone.utc) - timedelta(minutes=1)),
            ('2023-01-01T00:00:00.000Z', datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)),
        ]

        for input_str, expected in valid_cases:
            result = parse_time_input(input_str)
            if input_str in ['now', '1 minute ago']:
                # Allow some tolerance for "now" and relative times
                assert abs((result - expected).total_seconds()) < 2
            else:
                assert result == expected, f'Failed for input: {input_str}'

    def test_parse_time_input_comprehensive_iso_formats(self):
        """Test parse_time_input with comprehensive ISO format coverage."""
        test_cases = [
            # Standard ISO formats
            ('2023-06-15T14:30:45Z', datetime(2023, 6, 15, 14, 30, 45, tzinfo=timezone.utc)),
            (
                '2023-06-15T14:30:45.123Z',
                datetime(2023, 6, 15, 14, 30, 45, 123000, tzinfo=timezone.utc),
            ),
            ('2023-06-15T14:30:45+02:00', datetime(2023, 6, 15, 12, 30, 45, tzinfo=timezone.utc)),
            ('2023-06-15T14:30:45-05:00', datetime(2023, 6, 15, 19, 30, 45, tzinfo=timezone.utc)),
            # Date only formats
            ('2023-06-15', datetime(2023, 6, 15, 0, 0, 0, tzinfo=timezone.utc)),
            # Space-separated formats
            ('2023-06-15 14:30:45', datetime(2023, 6, 15, 14, 30, 45, tzinfo=timezone.utc)),
        ]

        for input_str, expected in test_cases:
            result = parse_time_input(input_str)
            assert result == expected, f'Failed for input: {input_str}'

    def test_parse_relative_time_various_units(self):
        """Test parse_relative_time with various time units."""
        now = datetime.now(timezone.utc)

        test_cases = [
            ('1 second ago', timedelta(seconds=1)),
            ('5 minutes ago', timedelta(minutes=5)),
            ('3 hours ago', timedelta(hours=3)),
            ('2 days ago', timedelta(days=2)),
            ('1 week ago', timedelta(weeks=1)),
            ('2 months ago', timedelta(days=60)),  # Approximate
            ('1 year ago', timedelta(days=365)),  # Approximate
        ]

        for input_str, expected_delta in test_cases:
            result = parse_relative_time(input_str)
            expected = now - expected_delta
            # Allow 2 second tolerance
            assert abs((result - expected).total_seconds()) < 2, f'Failed for: {input_str}'


class TestCloudTrailToolsMocked:
    """Test CloudTrail tools with mocked AWS calls."""

    @patch('boto3.Session')
    def test_get_cloudtrail_client(self, mock_session):
        """Test _get_cloudtrail_client method."""
        # Setup mock
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client

        # Test
        tools = CloudTrailTools()
        result = tools._get_cloudtrail_client('us-east-1')

        # Verify
        assert result == mock_client
        mock_session.assert_called_once()
        # Just verify it was called with cloudtrail and some config
        mock_session.return_value.client.assert_called_once()
        call_args = mock_session.return_value.client.call_args
        assert call_args[0][0] == 'cloudtrail'
        assert 'config' in call_args[1]
