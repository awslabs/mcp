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

"""Simple tests for models module."""

import pytest
from awslabs.cost_explorer_mcp_server.models import DateRange, DimensionKey
from pydantic import ValidationError


class TestDateRange:
    """Test DateRange model validation."""

    def test_valid_date_range(self):
        """Test valid date range creation."""
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')
        assert date_range.start_date == '2025-01-01'
        assert date_range.end_date == '2025-01-31'

    def test_invalid_start_date_format(self):
        """Test invalid start date format."""
        with pytest.raises(ValidationError) as exc_info:
            DateRange(start_date='invalid-date', end_date='2025-01-31')
        assert 'start_date' in str(exc_info.value)

    def test_invalid_end_date_format(self):
        """Test invalid end date format."""
        with pytest.raises(ValidationError) as exc_info:
            DateRange(start_date='2025-01-01', end_date='invalid-date')
        assert 'end_date' in str(exc_info.value)

    def test_start_date_after_end_date(self):
        """Test start date after end date."""
        with pytest.raises(ValidationError) as exc_info:
            DateRange(start_date='2025-01-31', end_date='2025-01-01')
        assert 'cannot be after end date' in str(exc_info.value)

    def test_same_start_end_date(self):
        """Test same start and end date (should be valid)."""
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-01')
        assert date_range.start_date == date_range.end_date

    def test_future_dates(self):
        """Test future dates (should be valid)."""
        date_range = DateRange(start_date='2030-01-01', end_date='2030-12-31')
        assert date_range.start_date == '2030-01-01'
        assert date_range.end_date == '2030-12-31'


class TestDimensionKey:
    """Test DimensionKey model validation."""

    def test_valid_dimension_key(self):
        """Test valid dimension key creation."""
        dimension = DimensionKey(dimension_key='SERVICE')
        assert dimension.dimension_key == 'SERVICE'

    def test_valid_dimension_keys(self):
        """Test various valid dimension keys."""
        valid_keys = ['SERVICE', 'REGION', 'AZ', 'INSTANCE_TYPE', 'LINKED_ACCOUNT']

        for key in valid_keys:
            dimension = DimensionKey(dimension_key=key)
            assert dimension.dimension_key == key

    def test_lowercase_dimension_key(self):
        """Test lowercase dimension key (should be accepted)."""
        dimension = DimensionKey(dimension_key='service')
        assert dimension.dimension_key == 'service'

    def test_empty_dimension_key(self):
        """Test empty dimension key (should be accepted by current model)."""
        # Current model doesn't validate empty strings, so this should pass
        dimension = DimensionKey(dimension_key='')
        assert dimension.dimension_key == ''

    def test_none_dimension_key(self):
        """Test None dimension key."""
        with pytest.raises(ValidationError):
            # Type ignore because we're intentionally testing invalid input
            DimensionKey(dimension_key=None)  # type: ignore

    def test_dimension_key_str_representation(self):
        """Test string representation of DimensionKey."""
        dim_key = DimensionKey(dimension_key='SERVICE')
        str_repr = str(dim_key)
        assert 'SERVICE' in str_repr

    def test_dimension_key_repr_representation(self):
        """Test repr representation of DimensionKey."""
        dim_key = DimensionKey(dimension_key='SERVICE')
        repr_str = repr(dim_key)
        assert 'DimensionKey' in repr_str
        assert 'SERVICE' in repr_str

    def test_date_range_str_representation(self):
        """Test string representation of DateRange."""
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')
        str_repr = str(date_range)
        assert '2025-01-01' in str_repr
        assert '2025-01-31' in str_repr

    def test_date_range_repr_representation(self):
        """Test repr representation of DateRange."""
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')
        repr_str = repr(date_range)
        assert 'DateRange' in repr_str
        assert '2025-01-01' in repr_str

    def test_date_range_validate_with_granularity_valid(self):
        """Test DateRange validate_with_granularity with valid range."""
        date_range = DateRange(start_date='2025-01-01', end_date='2025-01-31')
        # Should not raise an exception
        date_range.validate_with_granularity('MONTHLY')

    def test_date_range_validate_with_granularity_invalid(self):
        """Test DateRange validate_with_granularity with invalid range."""
        # Create a date range that's too long for hourly granularity
        date_range = DateRange(start_date='2025-01-01', end_date='2025-02-01')

        # Should raise ValueError for hourly granularity (too long)
        with pytest.raises(ValueError):
            date_range.validate_with_granularity('HOURLY')
