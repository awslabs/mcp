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

"""Unit tests for BatchGetItemAccessPattern model."""

import math
import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    MAX_BATCH_GET_ITEMS,
    MAX_ITEM_SIZE_BYTES,
    RCU_SIZE,
    BatchGetItemAccessPattern,
    format_validation_errors,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestBatchGetItemAccessPattern:
    """Tests for BatchGetItemAccessPattern model."""

    @pytest.fixture
    def batchgetitem_pattern(self):
        """Base BatchGetItem access pattern with sensible defaults for all tests."""
        return {
            'operation': 'BatchGetItem',
            'pattern': 'test-pattern',
            'description': 'Test description',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 4096,
            'item_count': 10,
            'strongly_consistent': False,
        }

    class TestValid:
        """Tests for valid BatchGetItem creation."""

        def test_valid_batchgetitem_minimal(self, batchgetitem_pattern):
            """Test BatchGetItem with valid minimal data."""
            ap = BatchGetItemAccessPattern(**batchgetitem_pattern)
            assert ap.operation == 'BatchGetItem'
            assert ap.item_count == 10
            assert ap.strongly_consistent is False

        def test_valid_batchgetitem_max_items(self, batchgetitem_pattern):
            """Test BatchGetItem with maximum items."""
            batchgetitem_pattern['item_count'] = MAX_BATCH_GET_ITEMS
            ap = BatchGetItemAccessPattern(**batchgetitem_pattern)
            assert ap.item_count == MAX_BATCH_GET_ITEMS

    class TestInvalid:
        """Tests for invalid BatchGetItem creation."""

        def test_invalid_batchgetitem_exceeds_max(self, batchgetitem_pattern):
            """Test BatchGetItem exceeding maximum items."""
            batchgetitem_pattern['item_count'] = 101
            with pytest.raises(ValidationError) as exc_info:
                BatchGetItemAccessPattern(**batchgetitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for BatchGetItemAccessPattern\nitem_count\n  Value error, must be at most 100. item_count: 101 [type=value_error, input_value=101, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_count: must be at most 100. item_count: 101'
            )

    class TestCalculateRcus:
        """Property-based tests for calculate_rcus() method."""

        @pytest.fixture(autouse=True)
        def setup_base_pattern(self):
            """Set up base pattern for property-based tests."""
            self.base_pattern = {
                'operation': 'BatchGetItem',
                'pattern': 'test-pattern',
                'description': 'Test description',
                'table': 'test-table',
                'rps': 100,
                'item_size_bytes': 4096,
                'item_count': 10,
                'strongly_consistent': False,
            }

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_BATCH_GET_ITEMS // 2),
            strongly_consistent=st.booleans(),
        )
        def test_linear_scaling_with_item_count(self, item_size, item_count, strongly_consistent):
            """Doubling item_count exactly doubles RCUs."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['strongly_consistent'] = strongly_consistent

            self.base_pattern['item_count'] = item_count
            ap_single = BatchGetItemAccessPattern(**self.base_pattern)

            self.base_pattern['item_count'] = item_count * 2
            ap_double = BatchGetItemAccessPattern(**self.base_pattern)

            assert ap_double.calculate_rcus() == 2.0 * ap_single.calculate_rcus()

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_BATCH_GET_ITEMS),
        )
        def test_strong_consistency_is_double_eventual(self, item_size, item_count):
            """Strong consistency is exactly 2x eventual consistency."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['item_count'] = item_count

            self.base_pattern['strongly_consistent'] = False
            ap_eventual = BatchGetItemAccessPattern(**self.base_pattern)

            self.base_pattern['strongly_consistent'] = True
            ap_strong = BatchGetItemAccessPattern(**self.base_pattern)

            assert ap_strong.calculate_rcus() == 2.0 * ap_eventual.calculate_rcus()

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_BATCH_GET_ITEMS),
            strongly_consistent=st.booleans(),
        )
        def test_rcus_are_always_positive(self, item_size, item_count, strongly_consistent):
            """RCUs are always positive for valid inputs."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['item_count'] = item_count
            self.base_pattern['strongly_consistent'] = strongly_consistent
            ap = BatchGetItemAccessPattern(**self.base_pattern)
            assert ap.calculate_rcus() > 0

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_BATCH_GET_ITEMS),
            strongly_consistent=st.booleans(),
        )
        def test_equivalent_to_item_count_times_single_getitem_rcus(
            self, item_size, item_count, strongly_consistent
        ):
            """Batch RCUs equal item_count × single GetItem RCUs."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['item_count'] = item_count
            self.base_pattern['strongly_consistent'] = strongly_consistent
            ap = BatchGetItemAccessPattern(**self.base_pattern)

            consistency_multiplier = 1.0 if strongly_consistent else 0.5
            single_item_rcus = math.ceil(item_size / RCU_SIZE) * consistency_multiplier
            expected = single_item_rcus * item_count

            assert ap.calculate_rcus() == expected
