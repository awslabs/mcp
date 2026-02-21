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

"""Unit tests for QueryAccessPattern model."""

import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    MAX_ITEM_SIZE_BYTES,
    RCU_SIZE,
    QueryAccessPattern,
    ScanAccessPattern,
    format_validation_errors,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestQueryAccessPattern:
    """Tests for QueryAccessPattern model."""

    @pytest.fixture
    def query_pattern(self):
        """Base Query access pattern with sensible defaults for all tests."""
        return {
            'operation': 'Query',
            'pattern': 'test-pattern',
            'description': 'Test description',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 1000,
            'item_count': 10,
            'strongly_consistent': False,
        }

    class TestValid:
        """Tests for valid Query creation."""

        def test_valid_query_minimal(self, query_pattern):
            """Test Query with valid minimal data."""
            ap = QueryAccessPattern(**query_pattern)
            assert ap.operation == 'Query'
            assert ap.item_count == 10
            assert ap.gsi is None
            assert ap.strongly_consistent is False

        def test_valid_query_with_all_options(self, query_pattern):
            """Test Query with all options on base table."""
            query_pattern['item_count'] = 50
            query_pattern['strongly_consistent'] = True
            ap = QueryAccessPattern(**query_pattern)
            assert ap.item_count == 50
            assert ap.gsi is None
            assert ap.strongly_consistent is True

        def test_valid_query_with_gsi(self, query_pattern):
            """Test Query with GSI (eventually consistent)."""
            query_pattern['item_count'] = 50
            query_pattern['gsi'] = 'test-gsi'
            ap = QueryAccessPattern(**query_pattern)
            assert ap.item_count == 50
            assert ap.gsi == 'test-gsi'
            assert ap.strongly_consistent is False

    class TestInvalid:
        """Tests for invalid Query creation."""

        def test_invalid_query_gsi_with_strong_consistency(self, query_pattern):
            """Test Query rejects GSI with strong consistency."""
            query_pattern['item_count'] = 50
            query_pattern['gsi'] = 'test-gsi'
            query_pattern['strongly_consistent'] = True
            with pytest.raises(ValidationError) as exc_info:
                QueryAccessPattern(**query_pattern)
            err = strip_pydantic_error_url(exc_info.value)
            assert err.startswith(
                '1 validation error for QueryAccessPattern\n  Value error, GSI does not support strongly consistent reads. gsi: "test-gsi", strongly_consistent: True [type=value_error, input_value='
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'GSI does not support strongly consistent reads. gsi: "test-gsi", strongly_consistent: True'
            )

        def test_invalid_query_zero_item_count(self, query_pattern):
            """Test Query with zero item count."""
            query_pattern['item_count'] = 0
            with pytest.raises(ValidationError) as exc_info:
                QueryAccessPattern(**query_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for QueryAccessPattern\nitem_count\n  Input should be greater than 0 [type=greater_than, input_value=0, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_count: must be greater than 0. item_count: 0'
            )

    class TestCalculateRcus:
        """Property-based tests for calculate_rcus() method."""

        @pytest.fixture(autouse=True)
        def setup_base_pattern(self):
            """Set up base Query pattern for RCU property tests."""
            self.base_pattern = {
                'operation': 'Query',
                'pattern': 'test-pattern',
                'description': 'Test description',
                'table': 'test-table',
                'rps': 100,
                'item_size_bytes': 1000,
                'item_count': 10,
                'strongly_consistent': False,
            }

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=10_000),
        )
        def test_eventually_consistent_is_half_of_strongly_consistent(
            self, item_size_bytes, item_count
        ):
            """Eventually consistent RCUs must be exactly half of strongly consistent."""
            ec_pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count,
                'strongly_consistent': False,
            }
            sc_pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count,
                'strongly_consistent': True,
            }
            ec_rcus = QueryAccessPattern(**ec_pattern).calculate_rcus()
            sc_rcus = QueryAccessPattern(**sc_pattern).calculate_rcus()
            assert ec_rcus == sc_rcus / 2

        @settings(max_examples=100)
        @given(
            multiplier=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES // RCU_SIZE),
            item_count=st.integers(min_value=1, max_value=5_000),
        )
        def test_linear_scaling_with_item_count(self, multiplier, item_count):
            """Doubling item_count must double RCUs when item_size is RCU-aligned."""
            item_size_bytes = multiplier * RCU_SIZE
            single_pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count,
                'strongly_consistent': True,
            }
            double_pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count * 2,
                'strongly_consistent': True,
            }
            single_rcus = QueryAccessPattern(**single_pattern).calculate_rcus()
            double_rcus = QueryAccessPattern(**double_pattern).calculate_rcus()
            assert double_rcus == single_rcus * 2

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=10_000),
        )
        def test_rcus_are_always_positive(self, item_size_bytes, item_count):
            """RCUs must always be positive for valid inputs."""
            pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count,
            }
            rcus = QueryAccessPattern(**pattern).calculate_rcus()
            assert rcus > 0

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            count_a=st.integers(min_value=1, max_value=10_000),
            count_b=st.integers(min_value=1, max_value=10_000),
        )
        def test_monotonicity_with_item_count(self, item_size_bytes, count_a, count_b):
            """More items must never consume fewer RCUs."""
            pattern_a = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': count_a,
                'strongly_consistent': True,
            }
            pattern_b = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': count_b,
                'strongly_consistent': True,
            }
            rcus_a = QueryAccessPattern(**pattern_a).calculate_rcus()
            rcus_b = QueryAccessPattern(**pattern_b).calculate_rcus()
            if count_a <= count_b:
                assert rcus_a <= rcus_b
            else:
                assert rcus_a >= rcus_b

        @settings(max_examples=1000)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=10_000),
            strongly_consistent=st.booleans(),
        )
        def test_query_and_scan_rcus_are_identical(
            self, item_size_bytes, item_count, strongly_consistent
        ):
            """Query and Scan must produce identical RCUs for the same inputs."""
            pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count,
                'strongly_consistent': strongly_consistent,
            }
            query_rcus = QueryAccessPattern(**pattern).calculate_rcus()
            scan_pattern = {**pattern, 'operation': 'Scan'}
            scan_rcus = ScanAccessPattern(**scan_pattern).calculate_rcus()
            assert query_rcus == scan_rcus
