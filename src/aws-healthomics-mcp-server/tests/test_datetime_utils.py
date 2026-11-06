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

"""Unit tests for datetime utility functions."""

import pytest
from awslabs.aws_healthomics_mcp_server.utils.datetime_utils import (
    convert_datetime_to_string,
    datetime_to_iso,
    parse_iso_datetime_utc,
)
from datetime import datetime, timedelta, timezone


class TestDatetimeToIso:
    """Tests for datetime_to_iso function."""

    def test_converts_datetime_to_iso(self):
        """Test datetime conversion to ISO format."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = datetime_to_iso(dt)
        assert result == '2024-01-15T10:30:00+00:00'

    def test_returns_none_for_none_input(self):
        """Test None input returns None."""
        result = datetime_to_iso(None)
        assert result is None

    def test_handles_naive_datetime(self):
        """Test naive datetime conversion."""
        dt = datetime(2024, 6, 20, 14, 45, 30)
        result = datetime_to_iso(dt)
        assert result == '2024-06-20T14:45:30'


class TestConvertDatetimeToString:
    """Tests for convert_datetime_to_string function."""

    def test_converts_datetime_directly(self):
        """Test direct datetime conversion."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = convert_datetime_to_string(dt)
        assert result == '2024-01-15T10:30:00+00:00'

    def test_converts_datetime_in_dict(self):
        """Test datetime conversion in dictionary."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        data = {'timestamp': dt, 'name': 'test'}
        result = convert_datetime_to_string(data)
        assert result == {'timestamp': '2024-01-15T10:30:00+00:00', 'name': 'test'}

    def test_converts_datetime_in_list(self):
        """Test datetime conversion in list."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        data = [dt, 'test', 123]
        result = convert_datetime_to_string(data)
        assert result == ['2024-01-15T10:30:00+00:00', 'test', 123]

    def test_converts_nested_structures(self):
        """Test datetime conversion in nested structures."""
        dt1 = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        dt2 = datetime(2024, 2, 20, 15, 45, 0, tzinfo=timezone.utc)
        data = {
            'items': [
                {'timestamp': dt1, 'value': 1},
                {'timestamp': dt2, 'value': 2},
            ],
            'metadata': {'created': dt1},
        }
        result = convert_datetime_to_string(data)
        assert result == {
            'items': [
                {'timestamp': '2024-01-15T10:30:00+00:00', 'value': 1},
                {'timestamp': '2024-02-20T15:45:00+00:00', 'value': 2},
            ],
            'metadata': {'created': '2024-01-15T10:30:00+00:00'},
        }

    def test_preserves_non_datetime_values(self):
        """Test non-datetime values are preserved."""
        data = {'string': 'test', 'number': 42, 'boolean': True, 'none': None}
        result = convert_datetime_to_string(data)
        assert result == data


class TestParseIsoDatetimeUtc:
    """Tests for parse_iso_datetime_utc function."""

    @pytest.mark.parametrize(
        'value',
        [
            '2024-01-15T10:00:00',
            '2024-01-15T10:00',
            '2024-01-15T10:00:00.250',
            '2024-01-15',
        ],
    )
    def test_value_without_offset_is_treated_as_utc(self, value, non_utc_local_timezone):
        """A value without an offset is UTC, not the server's local time."""
        result = parse_iso_datetime_utc(value)
        assert result.utcoffset() == timedelta(0)
        expected = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        assert result == expected
        assert result.timestamp() == expected.timestamp()

    def test_naive_and_z_values_give_the_same_instant(self, non_utc_local_timezone):
        """The same wall-clock time with and without a trailing Z is the same instant."""
        naive = parse_iso_datetime_utc('2024-01-15T10:00:00')
        zulu = parse_iso_datetime_utc('2024-01-15T10:00:00Z')
        assert naive == zulu
        assert int(naive.timestamp() * 1000) == 1705312800000

    def test_trailing_z_is_utc(self):
        """A trailing Z parses as UTC."""
        result = parse_iso_datetime_utc('2024-01-15T10:00:00Z')
        assert result == datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    def test_explicit_offset_is_kept(self):
        """An explicit offset is not overwritten with UTC."""
        result = parse_iso_datetime_utc('2024-01-15T10:00:00-05:00')
        assert result.utcoffset() == timedelta(hours=-5)
        assert result == datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc)

    def test_invalid_value_raises_value_error(self):
        """An invalid value raises ValueError."""
        with pytest.raises(ValueError):
            parse_iso_datetime_utc('not-a-date')
