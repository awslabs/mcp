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

"""Tests for Seasonality enum."""

from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import Seasonality


class TestSeasonalityEnum:
    """Test Seasonality enum values and from_seconds conversion."""

    def test_enum_values_are_correct(self):
        """Test that enum values match expected seconds."""
        assert Seasonality.NONE.value == 0
        assert Seasonality.FIFTEEN_MINUTES.value == 15 * 60  # 900 seconds
        assert Seasonality.ONE_HOUR.value == 60 * 60  # 3600 seconds
        assert Seasonality.SIX_HOURS.value == 6 * 60 * 60  # 21600 seconds
        assert Seasonality.ONE_DAY.value == 24 * 60 * 60  # 86400 seconds
        assert Seasonality.ONE_WEEK.value == 7 * 24 * 60 * 60  # 604800 seconds

    def test_from_seconds_exact_match(self):
        """Test from_seconds with exact enum values."""
        assert Seasonality.from_seconds(0) == Seasonality.NONE
        assert Seasonality.from_seconds(900) == Seasonality.FIFTEEN_MINUTES
        assert Seasonality.from_seconds(3600) == Seasonality.ONE_HOUR
        assert Seasonality.from_seconds(21600) == Seasonality.SIX_HOURS
        assert Seasonality.from_seconds(86400) == Seasonality.ONE_DAY
        assert Seasonality.from_seconds(604800) == Seasonality.ONE_WEEK

    def test_from_seconds_within_threshold(self):
        """Test from_seconds with values within 10% threshold."""
        # 10% of 3600 (ONE_HOUR) = 360 seconds
        assert Seasonality.from_seconds(3600 + 350) == Seasonality.ONE_HOUR
        assert Seasonality.from_seconds(3600 - 350) == Seasonality.ONE_HOUR

        # 10% of 86400 (ONE_DAY) = 8640 seconds
        assert Seasonality.from_seconds(86400 + 8000) == Seasonality.ONE_DAY
        assert Seasonality.from_seconds(86400 - 8000) == Seasonality.ONE_DAY

        # 10% of 604800 (ONE_WEEK) = 60480 seconds
        assert Seasonality.from_seconds(604800 + 60000) == Seasonality.ONE_WEEK
        assert Seasonality.from_seconds(604800 - 60000) == Seasonality.ONE_WEEK

    def test_from_seconds_outside_threshold_returns_none(self):
        """Test from_seconds returns NONE when outside 10% threshold."""
        # Just outside 10% of ONE_HOUR (3600)
        assert Seasonality.from_seconds(3600 + 400) == Seasonality.NONE
        assert Seasonality.from_seconds(3600 - 400) == Seasonality.NONE

        # Just outside 10% of ONE_DAY (86400)
        assert Seasonality.from_seconds(86400 + 9000) == Seasonality.NONE
        assert Seasonality.from_seconds(86400 - 9000) == Seasonality.NONE

        # Random values not close to any enum
        assert Seasonality.from_seconds(5000) == Seasonality.NONE
        assert Seasonality.from_seconds(50000) == Seasonality.NONE
        assert Seasonality.from_seconds(1000000) == Seasonality.NONE

    def test_from_seconds_chooses_closest_match(self):
        """Test from_seconds chooses the closest enum value within threshold."""
        # Within 10% of ONE_HOUR (3600), closer than other values
        assert Seasonality.from_seconds(3700) == Seasonality.ONE_HOUR

        # Within 10% of SIX_HOURS (21600), closer than other values
        assert Seasonality.from_seconds(21000) == Seasonality.SIX_HOURS

        # Within 10% of ONE_DAY (86400), closer than other values
        assert Seasonality.from_seconds(85000) == Seasonality.ONE_DAY

    def test_from_seconds_with_float(self):
        """Test from_seconds handles float values."""
        assert Seasonality.from_seconds(3600.5) == Seasonality.ONE_HOUR
        assert Seasonality.from_seconds(86400.9) == Seasonality.ONE_DAY

    def test_from_seconds_edge_cases(self):
        """Test from_seconds with edge case values."""
        # Negative values
        assert Seasonality.from_seconds(-100) == Seasonality.NONE

        # Very large values
        assert Seasonality.from_seconds(10000000) == Seasonality.NONE

        # Zero
        assert Seasonality.from_seconds(0) == Seasonality.NONE

    def test_from_seconds_boundary_at_threshold(self):
        """Test from_seconds at 10% boundary (strictly less than)."""
        # Just under 10% threshold for ONE_HOUR (3600 * 0.1 = 360)
        assert Seasonality.from_seconds(3600 + 359) == Seasonality.ONE_HOUR
        assert Seasonality.from_seconds(3600 - 359) == Seasonality.ONE_HOUR

        # Exactly at 10% threshold returns NONE (< not <=)
        assert Seasonality.from_seconds(3600 + 360) == Seasonality.NONE
        assert Seasonality.from_seconds(3600 - 360) == Seasonality.NONE
