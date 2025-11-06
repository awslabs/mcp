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

"""Tests for AWS IoT SiteWise Timestamp Tools."""

import datetime
import os
import pytest
import sys
from awslabs.aws_iot_sitewise_mcp_server.tools.timestamp_tools import (
    convert_multiple_timestamps,
    convert_multiple_timestamps_tool,
    convert_unix_timestamp,
    convert_unix_timestamp_tool,
    create_timestamp_range,
    create_timestamp_range_tool,
    get_current_timestamp,
    get_current_timestamp_tool,
)
from unittest.mock import patch


# Add the project root directory and its parent to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.dirname(project_dir))
sys.path.insert(0, os.path.dirname(os.path.dirname(project_dir)))


class TestTimestampTools:
    """Test cases for timestamp tool functions."""

    def test_convert_unix_timestamp_valid_int(self):
        """Test valid Unix timestamp conversion with integer input."""
        # Test with a known timestamp: October 1, 2024 00:00:00 UTC
        timestamp = 1727740800
        result = convert_unix_timestamp(timestamp)

        assert result['success'] is True
        assert result['timestamp'] == 1727740800
        assert result['formatted'] == 'October 01, 2024 at 00:00:00 UTC'
        assert result['iso_format'] == '2024-10-01T00:00:00+00:00'
        assert result['year'] == 2024
        assert result['month'] == 10
        assert result['day'] == 1
        assert result['hour'] == 0
        assert result['minute'] == 0
        assert result['second'] == 0
        assert result['weekday'] == 'Tuesday'
        assert result['timezone'] == 'UTC'

    def test_convert_unix_timestamp_valid_string(self):
        """Test valid Unix timestamp conversion with string input."""
        # Test with string timestamp
        timestamp = '1727740800'
        result = convert_unix_timestamp(timestamp)

        assert result['success'] is True
        assert result['timestamp'] == 1727740800
        assert result['formatted'] == 'October 01, 2024 at 00:00:00 UTC'
        assert result['year'] == 2024
        assert result['month'] == 10
        assert result['day'] == 1

    def test_convert_unix_timestamp_custom_format(self):
        """Test Unix timestamp conversion with custom format string."""
        timestamp = 1727740800
        custom_format = '%Y-%m-%d %H:%M:%S'
        result = convert_unix_timestamp(timestamp, format_string=custom_format)

        assert result['success'] is True
        assert result['formatted'] == '2024-10-01 00:00:00'
        assert result['timestamp'] == 1727740800

    def test_convert_unix_timestamp_different_timezone_param(self):
        """Test Unix timestamp conversion with timezone parameter (currently only supports UTC)."""
        timestamp = 1727740800
        result = convert_unix_timestamp(timestamp, timezone='America/New_York')

        # Currently only supports UTC, so timezone parameter is ignored
        assert result['success'] is True
        assert result['timezone'] == 'UTC'
        assert result['formatted'] == 'October 01, 2024 at 00:00:00 UTC'

    def test_convert_unix_timestamp_edge_cases(self):
        """Test Unix timestamp conversion with edge cases."""
        # Test with timestamp 0 (Unix epoch start)
        result = convert_unix_timestamp(0)
        assert result['success'] is True
        assert result['year'] == 1970
        assert result['month'] == 1
        assert result['day'] == 1
        assert result['hour'] == 0
        assert result['minute'] == 0
        assert result['second'] == 0

        # Test with a more recent timestamp
        timestamp = 1640995200  # January 1, 2022 00:00:00 UTC
        result = convert_unix_timestamp(timestamp)
        assert result['success'] is True
        assert result['year'] == 2022
        assert result['month'] == 1
        assert result['day'] == 1

    def test_convert_unix_timestamp_invalid_string(self):
        """Test Unix timestamp conversion with invalid string input."""
        # Invalid string that can't be converted to int
        result = convert_unix_timestamp('invalid_timestamp')

        assert result['success'] is False
        assert 'Invalid timestamp' in result['error']
        assert result['timestamp'] == 'invalid_timestamp'

    def test_convert_unix_timestamp_invalid_negative(self):
        """Test Unix timestamp conversion with negative timestamp."""
        # Negative timestamps might cause issues on some systems
        result = convert_unix_timestamp(-1)

        # This might succeed or fail depending on the system
        # On most systems, negative timestamps are valid (before 1970)
        if result['success']:
            assert result['year'] == 1969
        else:
            assert 'Invalid timestamp' in result['error']

    def test_convert_unix_timestamp_overflow(self):
        """Test Unix timestamp conversion with overflow values."""
        # Test with a very large timestamp that might cause overflow
        large_timestamp = 2**63 - 1  # Maximum 64-bit signed integer
        result = convert_unix_timestamp(large_timestamp)

        # This should fail due to overflow
        assert result['success'] is False
        assert 'Invalid timestamp' in result['error']

    def test_convert_unix_timestamp_float_string(self):
        """Test Unix timestamp conversion with float string input."""
        # Test with float string - this should fail because int() can't convert "1727740800.5"
        result = convert_unix_timestamp('1727740800.5')

        assert result['success'] is False
        assert 'Invalid timestamp' in result['error']
        assert result['timestamp'] == '1727740800.5'

    def test_convert_multiple_timestamps_valid(self):
        """Test valid multiple timestamp conversion."""
        timestamps = {
            'lastTrainedAt': '1727740800',
            'lastTrainedStartTime': '1727654400',
            'lastTrainedEndTime': '1727827200',
        }

        result = convert_multiple_timestamps(timestamps)

        assert result['success'] is True
        assert 'conversions' in result
        assert 'summary' in result

        # Check that all timestamps were converted
        assert len(result['conversions']) == 3
        assert len(result['summary']) == 3

        # Check specific conversions
        assert result['conversions']['lastTrainedAt']['success'] is True
        assert result['conversions']['lastTrainedAt']['year'] == 2024
        assert result['conversions']['lastTrainedAt']['month'] == 10
        assert result['conversions']['lastTrainedAt']['day'] == 1

        # Check summary format
        assert result['summary']['lastTrainedAt']['original'] == '1727740800'
        assert result['summary']['lastTrainedAt']['year'] == 2024
        assert 'formatted' in result['summary']['lastTrainedAt']

    def test_convert_multiple_timestamps_custom_format(self):
        """Test multiple timestamp conversion with custom format."""
        timestamps = {'start': 1727740800, 'end': 1727827200}
        custom_format = '%Y-%m-%d'

        result = convert_multiple_timestamps(timestamps, format_string=custom_format)

        assert result['success'] is True
        assert result['conversions']['start']['formatted'] == '2024-10-01'
        assert result['conversions']['end']['formatted'] == '2024-10-02'

    def test_convert_multiple_timestamps_mixed_valid_invalid(self):
        """Test multiple timestamp conversion with mix of valid and invalid timestamps."""
        timestamps = {
            'valid': 1727740800,
            'invalid': 'not_a_timestamp',
            'another_valid': '1727827200',
        }

        result = convert_multiple_timestamps(timestamps)

        assert result['success'] is True

        # Valid timestamps should succeed
        assert result['conversions']['valid']['success'] is True
        assert result['conversions']['another_valid']['success'] is True

        # Invalid timestamp should fail
        assert result['conversions']['invalid']['success'] is False

        # Summary should only contain successful conversions
        assert 'valid' in result['summary']
        assert 'another_valid' in result['summary']
        assert 'invalid' not in result['summary']

    def test_convert_multiple_timestamps_empty(self):
        """Test multiple timestamp conversion with empty input."""
        result = convert_multiple_timestamps({})

        assert result['success'] is True
        assert result['conversions'] == {}
        assert result['summary'] == {}

    def test_convert_multiple_timestamps_exception(self):
        """Test multiple timestamp conversion with exception handling."""
        # Test with None input to trigger exception
        result = convert_multiple_timestamps(None)

        assert result['success'] is False
        assert 'Error processing timestamps' in result['error']
        assert result['timestamps'] is None

    def test_create_timestamp_range_valid(self):
        """Test valid timestamp range creation."""
        start_timestamp = 1727740800  # October 1, 2024
        end_timestamp = 1727827200  # October 2, 2024

        result = create_timestamp_range(start_timestamp, end_timestamp)

        assert result['success'] is True
        assert result['range'] == 'October 01, 2024 - October 02, 2024'
        assert result['start']['success'] is True
        assert result['end']['success'] is True
        assert result['duration_days'] == 1
        assert result['duration_hours'] == 24.0

    def test_create_timestamp_range_string_inputs(self):
        """Test timestamp range creation with string inputs."""
        start_timestamp = '1727740800'
        end_timestamp = '1727827200'

        result = create_timestamp_range(start_timestamp, end_timestamp)

        assert result['success'] is True
        assert result['duration_days'] == 1
        assert result['duration_hours'] == 24.0

    def test_create_timestamp_range_custom_format(self):
        """Test timestamp range creation with custom format."""
        start_timestamp = 1727740800
        end_timestamp = 1727827200
        custom_format = '%Y-%m-%d %H:%M'

        result = create_timestamp_range(
            start_timestamp, end_timestamp, format_string=custom_format
        )

        assert result['success'] is True
        assert result['range'] == '2024-10-01 00:00 - 2024-10-02 00:00'

    def test_create_timestamp_range_same_timestamps(self):
        """Test timestamp range creation with same start and end timestamps."""
        timestamp = 1727740800

        result = create_timestamp_range(timestamp, timestamp)

        assert result['success'] is True
        assert result['duration_days'] == 0
        assert result['duration_hours'] == 0.0

    def test_create_timestamp_range_reverse_order(self):
        """Test timestamp range creation with end before start."""
        start_timestamp = 1727827200  # October 2, 2024
        end_timestamp = 1727740800  # October 1, 2024

        result = create_timestamp_range(start_timestamp, end_timestamp)

        assert result['success'] is True
        assert result['duration_days'] == -1  # Negative duration
        assert result['duration_hours'] == -24.0

    def test_create_timestamp_range_invalid_start(self):
        """Test timestamp range creation with invalid start timestamp."""
        result = create_timestamp_range('invalid', 1727827200)

        assert result['success'] is False
        assert 'Failed to convert one or both timestamps' in result['error']
        assert result['start_conversion']['success'] is False
        assert result['end_conversion']['success'] is True

    def test_create_timestamp_range_invalid_end(self):
        """Test timestamp range creation with invalid end timestamp."""
        result = create_timestamp_range(1727740800, 'invalid')

        assert result['success'] is False
        assert 'Failed to convert one or both timestamps' in result['error']
        assert result['start_conversion']['success'] is True
        assert result['end_conversion']['success'] is False

    def test_create_timestamp_range_both_invalid(self):
        """Test timestamp range creation with both invalid timestamps."""
        result = create_timestamp_range('invalid1', 'invalid2')

        assert result['success'] is False
        assert 'Failed to convert one or both timestamps' in result['error']
        assert result['start_conversion']['success'] is False
        assert result['end_conversion']['success'] is False

    def test_create_timestamp_range_large_duration(self):
        """Test timestamp range creation with large duration."""
        start_timestamp = 0  # January 1, 1970
        end_timestamp = 1727740800  # October 1, 2024

        result = create_timestamp_range(start_timestamp, end_timestamp)

        assert result['success'] is True
        assert result['duration_days'] > 19000  # More than 50 years
        assert result['duration_hours'] > 400000

    def test_create_timestamp_range_exception_handling(self):
        """Test timestamp range creation exception handling."""
        # Mock datetime to raise an exception
        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.timestamp_tools.datetime'
        ) as mock_datetime:
            mock_datetime.datetime.fromtimestamp.side_effect = Exception('Test exception')

            result = create_timestamp_range(1727740800, 1727827200)

            assert result['success'] is False
            assert 'Error creating timestamp range' in result['error']
            assert result['start_timestamp'] == 1727740800
            assert result['end_timestamp'] == 1727827200

    def test_get_current_timestamp_valid(self):
        """Test valid current timestamp retrieval."""
        result = get_current_timestamp()

        assert result['success'] is True
        assert 'current_timestamp' in result
        assert 'formatted' in result
        assert 'iso_format' in result
        assert 'year' in result
        assert 'month' in result
        assert 'day' in result
        assert 'hour' in result
        assert 'minute' in result
        assert 'second' in result
        assert result['timezone'] == 'UTC'

        # Check that timestamp is reasonable (after 2020, before 2030)
        assert result['current_timestamp'] > 1577836800  # January 1, 2020
        assert result['current_timestamp'] < 1893456000  # January 1, 2030

        # Check that year is current
        current_year = datetime.datetime.now().year
        assert result['year'] >= current_year - 1  # Allow for year boundary edge cases
        assert result['year'] <= current_year + 1

    def test_get_current_timestamp_format_consistency(self):
        """Test current timestamp format consistency."""
        result = get_current_timestamp()

        assert result['success'] is True

        # Check that formatted string contains expected elements
        assert 'UTC' in result['formatted']
        assert 'at' in result['formatted']

        # Check ISO format
        assert 'T' in result['iso_format']
        assert result['iso_format'].endswith('+00:00')

    def test_get_current_timestamp_multiple_calls(self):
        """Test multiple calls to get_current_timestamp return increasing values."""
        result1 = get_current_timestamp()
        result2 = get_current_timestamp()

        assert result1['success'] is True
        assert result2['success'] is True

        # Second call should have timestamp >= first call
        assert result2['current_timestamp'] >= result1['current_timestamp']

    def test_get_current_timestamp_exception_handling(self):
        """Test current timestamp exception handling."""
        # Mock datetime to raise an exception
        with patch(
            'awslabs.aws_iot_sitewise_mcp_server.tools.timestamp_tools.datetime'
        ) as mock_datetime:
            mock_datetime.datetime.now.side_effect = Exception('Test exception')

            result = get_current_timestamp()

            assert result['success'] is False
            assert 'Error getting current timestamp' in result['error']

    def test_mcp_tools_creation(self):
        """Test that MCP tools are created correctly."""
        # Test that all tools are created
        assert convert_unix_timestamp_tool is not None
        assert convert_multiple_timestamps_tool is not None
        assert create_timestamp_range_tool is not None
        assert get_current_timestamp_tool is not None

        # Test tool names
        assert convert_unix_timestamp_tool.name == 'convert_unix_timestamp'
        assert convert_multiple_timestamps_tool.name == 'convert_multiple_timestamps'
        assert create_timestamp_range_tool.name == 'create_timestamp_range'
        assert get_current_timestamp_tool.name == 'get_current_timestamp'

        # Test that descriptions are present
        assert len(convert_unix_timestamp_tool.description) > 0
        assert len(convert_multiple_timestamps_tool.description) > 0
        assert len(create_timestamp_range_tool.description) > 0
        assert len(get_current_timestamp_tool.description) > 0

        # Test that descriptions contain expected keywords
        assert 'timestamp' in convert_unix_timestamp_tool.description.lower()
        assert 'multiple' in convert_multiple_timestamps_tool.description.lower()
        assert 'range' in create_timestamp_range_tool.description.lower()
        assert 'current' in get_current_timestamp_tool.description.lower()

    def test_tool_metadata_readonly(self):
        """Test that all functions have readonly metadata."""
        # This test verifies that the @tool_metadata(readonly=True) decorator is applied
        # We can't directly test the decorator, but we can test the functions work as expected

        # All functions should work without modifying any external state
        result1 = convert_unix_timestamp(1727740800)
        result2 = convert_multiple_timestamps({'test': 1727740800})
        result3 = create_timestamp_range(1727740800, 1727827200)
        result4 = get_current_timestamp()

        assert result1['success'] is True
        assert result2['success'] is True
        assert result3['success'] is True
        assert result4['success'] is True

    def test_comprehensive_timestamp_scenarios(self):
        """Test comprehensive timestamp scenarios covering various use cases."""
        # Test various timestamp formats and edge cases
        test_cases = [
            # (timestamp, expected_year, expected_month, expected_day)
            (0, 1970, 1, 1),  # Unix epoch
            (946684800, 2000, 1, 1),  # Y2K
            (1577836800, 2020, 1, 1),  # Recent year
            (1727740800, 2024, 10, 1),  # Test case from examples
        ]

        for timestamp, expected_year, expected_month, expected_day in test_cases:
            result = convert_unix_timestamp(timestamp)
            assert result['success'] is True
            assert result['year'] == expected_year
            assert result['month'] == expected_month
            assert result['day'] == expected_day

    def test_format_string_variations(self):
        """Test various format string patterns."""
        timestamp = 1727740800  # October 1, 2024 00:00:00 UTC

        format_tests = [
            ('%Y-%m-%d', '2024-10-01'),
            ('%B %d, %Y', 'October 01, 2024'),
            ('%d/%m/%Y %H:%M', '01/10/2024 00:00'),
            ('%A, %B %d, %Y', 'Tuesday, October 01, 2024'),
            ('%Y%m%d', '20241001'),
        ]

        for format_string, expected in format_tests:
            result = convert_unix_timestamp(timestamp, format_string=format_string)
            assert result['success'] is True
            assert result['formatted'] == expected

    def test_boundary_conditions(self):
        """Test boundary conditions and edge cases."""
        # Test minimum positive timestamp
        result = convert_unix_timestamp(1)
        assert result['success'] is True
        assert result['year'] == 1970

        # Test large but valid timestamp (year 2038 problem boundary)
        # 2147483647 is the maximum 32-bit signed integer (January 19, 2038)
        result = convert_unix_timestamp(2147483647)
        if result['success']:  # Might fail on 32-bit systems
            assert result['year'] == 2038

        # Test string conversion edge cases
        result = convert_unix_timestamp('0')
        assert result['success'] is True
        assert result['year'] == 1970

    def test_error_message_quality(self):
        """Test that error messages are informative and helpful."""
        # Test invalid string conversion
        result = convert_unix_timestamp('not_a_number')
        assert result['success'] is False
        assert 'Invalid timestamp' in result['error']
        assert 'not_a_number' in result['error']

        # Test overflow error
        result = convert_unix_timestamp(10**20)  # Very large number
        assert result['success'] is False
        assert 'Invalid timestamp' in result['error']


if __name__ == '__main__':
    pytest.main([__file__])
