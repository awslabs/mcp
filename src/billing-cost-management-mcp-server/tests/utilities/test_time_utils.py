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

"""Unit tests for the time_utils module."""

import pytest
from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
    timestamp_to_utc_iso_string,
)
from datetime import datetime, timezone


class TestUtcDatetimeStringToEpochSeconds:
    """Tests for utc_datetime_string_to_epoch_seconds function."""

    def test_date_only_format(self):
        """Test conversion with date-only format YYYY-MM-DD."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            utc_datetime_string_to_epoch_seconds,
        )

        result = utc_datetime_string_to_epoch_seconds('2024-01-01')
        assert result == 1704067200  # 2024-01-01T00:00:00 UTC

    def test_datetime_format(self):
        """Test conversion with datetime format YYYY-MM-DDTHH:MM:SS."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            utc_datetime_string_to_epoch_seconds,
        )

        result = utc_datetime_string_to_epoch_seconds('2024-01-31T23:59:59')
        assert result == 1706745599  # 2024-01-31T23:59:59 UTC

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            utc_datetime_string_to_epoch_seconds,
        )

        with pytest.raises(ValueError, match='Invalid datetime format'):
            utc_datetime_string_to_epoch_seconds('not-a-date')


class TestEpochSecondsToUtcIsoStringDatetime:
    """Tests for timestamp_to_utc_iso_string with datetime inputs."""

    def test_datetime_with_timezone(self):
        """Test conversion with timezone-aware datetime."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            timestamp_to_utc_iso_string,
        )

        dt = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)
        result = timestamp_to_utc_iso_string(dt)
        assert result == '2023-11-14T22:13:20'

    def test_datetime_without_timezone(self):
        """Test conversion with naive datetime (no timezone)."""
        from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
            timestamp_to_utc_iso_string,
        )

        dt = datetime(2023, 11, 14, 22, 13, 20)
        result = timestamp_to_utc_iso_string(dt)
        assert result == '2023-11-14T22:13:20'


class TestEpochSecondsToUtcIsoString:
    """Tests for the timestamp_to_utc_iso_string function."""

    def test_known_timestamp(self):
        """Test conversion of a known epoch timestamp."""
        # 2023-11-14T22:13:20 UTC
        result = timestamp_to_utc_iso_string(1700000000)
        assert result == '2023-11-14T22:13:20'

    def test_unix_epoch_zero(self):
        """Test conversion of epoch zero (1970-01-01)."""
        result = timestamp_to_utc_iso_string(0)
        assert result == '1970-01-01T00:00:00'

    def test_float_timestamp(self):
        """Test conversion of a float timestamp with fractional seconds."""
        result = timestamp_to_utc_iso_string(1700000000.5)
        assert result == '2023-11-14T22:13:20.500000'

    def test_returns_string_without_timezone(self):
        """Test that the result does not contain timezone info."""
        result = timestamp_to_utc_iso_string(1700000000)
        assert '+' not in result
        assert 'Z' not in result

    def test_different_timestamps(self):
        """Test several different timestamps for correct formatting."""
        # 2023-11-15T10:00:00 UTC = 1700042400
        result = timestamp_to_utc_iso_string(1700042400)
        assert result == '2023-11-15T10:00:00'

        # 2025-01-01T00:00:00 UTC = 1735689600
        result = timestamp_to_utc_iso_string(1735689600)
        assert result == '2025-01-01T00:00:00'
