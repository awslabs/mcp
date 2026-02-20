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

"""Unit tests for GetItemAccessPattern model."""

import math
import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    MAX_ITEM_SIZE_BYTES,
    RCU_SIZE,
    GetItemAccessPattern,
    format_validation_errors,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestGetItemAccessPattern:
    """Tests for GetItemAccessPattern model."""

    @pytest.fixture
    def getitem_pattern(self):
        """Base GetItem access pattern for all tests."""
        return {
            'operation': 'GetItem',
            'pattern': 'test-pattern',
            'description': 'Test description',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 1000,
            'strongly_consistent': False,
        }

    class TestValid:
        """Tests for valid GetItem creation."""

        def test_valid_getitem_minimal(self, getitem_pattern):
            """Test GetItem with valid minimal data."""
            ap = GetItemAccessPattern(**getitem_pattern)
            assert ap.operation == 'GetItem'
            assert ap.strongly_consistent is False

        def test_valid_getitem_strongly_consistent(self, getitem_pattern):
            """Test GetItem with strong consistency."""
            getitem_pattern['strongly_consistent'] = True
            ap = GetItemAccessPattern(**getitem_pattern)
            assert ap.strongly_consistent is True

    class TestInvalid:
        """Tests for invalid GetItem creation."""

        def test_invalid_getitem_empty_pattern(self, getitem_pattern):
            """Test GetItem with empty pattern."""
            getitem_pattern['pattern'] = ''
            with pytest.raises(ValidationError) as exc_info:
                GetItemAccessPattern(**getitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == "1 validation error for GetItemAccessPattern\npattern\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]"
            )
            assert (
                format_validation_errors(exc_info.value) == 'pattern: cannot be empty. pattern: '
            )

        def test_invalid_getitem_empty_description(self, getitem_pattern):
            """Test GetItem with empty description."""
            getitem_pattern['description'] = ''
            with pytest.raises(ValidationError) as exc_info:
                GetItemAccessPattern(**getitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == "1 validation error for GetItemAccessPattern\ndescription\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]"
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'description: cannot be empty. description: '
            )

        def test_invalid_getitem_empty_table(self, getitem_pattern):
            """Test GetItem with empty table."""
            getitem_pattern['table'] = ''
            with pytest.raises(ValidationError) as exc_info:
                GetItemAccessPattern(**getitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == "1 validation error for GetItemAccessPattern\ntable\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]"
            )
            assert format_validation_errors(exc_info.value) == 'table: cannot be empty. table: '

        def test_invalid_getitem_zero_rps(self, getitem_pattern):
            """Test GetItem with zero RPS."""
            getitem_pattern['rps'] = 0
            with pytest.raises(ValidationError) as exc_info:
                GetItemAccessPattern(**getitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for GetItemAccessPattern\nrps\n  Input should be greater than 0 [type=greater_than, input_value=0, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value) == 'rps: must be greater than 0.0. rps: 0'
            )

        def test_invalid_getitem_negative_rps(self, getitem_pattern):
            """Test GetItem with negative RPS."""
            getitem_pattern['rps'] = -1
            with pytest.raises(ValidationError) as exc_info:
                GetItemAccessPattern(**getitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for GetItemAccessPattern\nrps\n  Input should be greater than 0 [type=greater_than, input_value=-1, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'rps: must be greater than 0.0. rps: -1'
            )

        def test_invalid_getitem_item_size_exceeds_max(self, getitem_pattern):
            """Test GetItem with item size exceeding maximum."""
            getitem_pattern['item_size_bytes'] = 409601
            with pytest.raises(ValidationError) as exc_info:
                GetItemAccessPattern(**getitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for GetItemAccessPattern\nitem_size_bytes\n  Input should be less than or equal to 409600 [type=less_than_equal, input_value=409601, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_size_bytes: must be at most 409600. item_size_bytes: 409601'
            )

    class TestCalculateRcus:
        """Property-based tests for calculate_rcus() method."""

        @pytest.fixture(autouse=True)
        def setup_base_pattern(self):
            """Set up base pattern for property-based tests."""
            self.base_pattern = {
                'operation': 'GetItem',
                'pattern': 'test-pattern',
                'description': 'Test description',
                'table': 'test-table',
                'rps': 100,
                'item_size_bytes': 1000,
                'strongly_consistent': False,
            }

        @settings(max_examples=100)
        @given(item_size=st.integers(min_value=1, max_value=RCU_SIZE))
        def test_small_item_eventual_consistency_half_rcu(self, item_size):
            """Items <= 4KB with eventual consistency consume exactly 0.5 RCU."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['strongly_consistent'] = False
            ap = GetItemAccessPattern(**self.base_pattern)
            assert ap.calculate_rcus() == 0.5

        @settings(max_examples=100)
        @given(item_size=st.integers(min_value=1, max_value=RCU_SIZE))
        def test_small_item_strong_consistency_one_rcu(self, item_size):
            """Items <= 4KB with strong consistency consume exactly 1.0 RCU."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['strongly_consistent'] = True
            ap = GetItemAccessPattern(**self.base_pattern)
            assert ap.calculate_rcus() == 1.0

        @settings(max_examples=100)
        @given(item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES))
        def test_strong_consistency_is_double_eventual(self, item_size):
            """Strong consistency is exactly 2x eventual consistency."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['strongly_consistent'] = False
            ap_eventual = GetItemAccessPattern(**self.base_pattern)
            self.base_pattern['strongly_consistent'] = True
            ap_strong = GetItemAccessPattern(**self.base_pattern)
            assert ap_strong.calculate_rcus() == 2.0 * ap_eventual.calculate_rcus()

        @settings(max_examples=100)
        @given(n=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES // RCU_SIZE))
        def test_exact_4kb_boundaries(self, n):
            """Exact 4KB boundaries consume exact RCUs (no ceiling overhead)."""
            item_size = n * RCU_SIZE
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['strongly_consistent'] = True
            ap = GetItemAccessPattern(**self.base_pattern)
            expected = math.ceil(item_size / RCU_SIZE) * 1.0
            assert ap.calculate_rcus() == expected
            # Also verify the value equals n exactly (no ceiling rounding)
            assert ap.calculate_rcus() == float(n)

        @settings(max_examples=100)
        @given(
            size_a=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            size_b=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            strongly_consistent=st.booleans(),
        )
        def test_monotonicity(self, size_a, size_b, strongly_consistent):
            """Larger items never consume fewer RCUs."""
            self.base_pattern['strongly_consistent'] = strongly_consistent
            self.base_pattern['item_size_bytes'] = size_a
            ap_a = GetItemAccessPattern(**self.base_pattern)
            self.base_pattern['item_size_bytes'] = size_b
            ap_b = GetItemAccessPattern(**self.base_pattern)
            if size_a <= size_b:
                assert ap_a.calculate_rcus() <= ap_b.calculate_rcus()
            else:
                assert ap_a.calculate_rcus() >= ap_b.calculate_rcus()

    class TestConsistencyMultiplier:
        """Tests for consistency_multiplier() method."""

        def test_getitem_consistency_multiplier_eventually_consistent(self, getitem_pattern):
            """Test consistency multiplier for eventually consistent reads."""
            ap = GetItemAccessPattern(**getitem_pattern)
            assert ap.consistency_multiplier() == 0.5

        def test_getitem_consistency_multiplier_strongly_consistent(self, getitem_pattern):
            """Test consistency multiplier for strongly consistent reads."""
            getitem_pattern['strongly_consistent'] = True
            ap = GetItemAccessPattern(**getitem_pattern)
            assert ap.consistency_multiplier() == 1.0
