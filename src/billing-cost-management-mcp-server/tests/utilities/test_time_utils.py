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

from awslabs.billing_cost_management_mcp_server.utilities.time_utils import (
    epoch_seconds_to_utc_iso_string,
)


class TestEpochSecondsToUtcIsoString:
    """Tests for the epoch_seconds_to_utc_iso_string function."""

    def test_known_timestamp(self):
        """Test conversion of a known epoch timestamp."""
        # 2023-11-14T22:13:20 UTC
        result = epoch_seconds_to_utc_iso_string(1700000000)
        assert result == '2023-11-14T22:13:20'

    def test_unix_epoch_zero(self):
        """Test conversion of epoch zero (1970-01-01)."""
        result = epoch_seconds_to_utc_iso_string(0)
        assert result == '1970-01-01T00:00:00'

    def test_float_timestamp(self):
        """Test conversion of a float timestamp with fractional seconds."""
        result = epoch_seconds_to_utc_iso_string(1700000000.5)
        assert result == '2023-11-14T22:13:20.500000'

    def test_returns_string_without_timezone(self):
        """Test that the result does not contain timezone info."""
        result = epoch_seconds_to_utc_iso_string(1700000000)
        assert '+' not in result
        assert 'Z' not in result

    def test_different_timestamps(self):
        """Test several different timestamps for correct formatting."""
        # 2023-11-15T10:00:00 UTC = 1700042400
        result = epoch_seconds_to_utc_iso_string(1700042400)
        assert result == '2023-11-15T10:00:00'

        # 2025-01-01T00:00:00 UTC = 1735689600
        result = epoch_seconds_to_utc_iso_string(1735689600)
        assert result == '2025-01-01T00:00:00'
