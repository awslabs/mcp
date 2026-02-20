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

"""Unit tests for BatchWriteItemAccessPattern model."""

import math
import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    GSI,
    MAX_BATCH_WRITE_ITEMS,
    MAX_ITEM_SIZE_BYTES,
    WCU_SIZE,
    BatchWriteItemAccessPattern,
    Table,
    format_validation_errors,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestBatchWriteItemAccessPattern:
    """Tests for BatchWriteItemAccessPattern model."""

    @pytest.fixture
    def batchwriteitem_pattern(self):
        """Base BatchWriteItem access pattern with sensible defaults."""
        return {
            'operation': 'BatchWriteItem',
            'pattern': 'test-pattern',
            'description': 'Test description',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 1000,
            'item_count': 10,
        }

    class TestValid:
        """Tests for valid BatchWriteItem creation."""

        def test_valid_batchwriteitem_minimal(self, batchwriteitem_pattern):
            """Test BatchWriteItem with valid minimal data."""
            ap = BatchWriteItemAccessPattern(**batchwriteitem_pattern)
            assert ap.operation == 'BatchWriteItem'
            assert ap.item_count == 10
            assert ap.gsi_list == []

        def test_valid_batchwriteitem_max_items(self, batchwriteitem_pattern):
            """Test BatchWriteItem with maximum items."""
            batchwriteitem_pattern['item_count'] = MAX_BATCH_WRITE_ITEMS
            ap = BatchWriteItemAccessPattern(**batchwriteitem_pattern)
            assert ap.item_count == MAX_BATCH_WRITE_ITEMS

    class TestInvalid:
        """Tests for invalid BatchWriteItem creation."""

        def test_invalid_batchwriteitem_exceeds_max(self, batchwriteitem_pattern):
            """Test BatchWriteItem exceeding maximum items."""
            batchwriteitem_pattern['item_count'] = 26
            with pytest.raises(ValidationError) as exc_info:
                BatchWriteItemAccessPattern(**batchwriteitem_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for BatchWriteItemAccessPattern\nitem_count\n  Value error, must be at most 25. item_count: 26 [type=value_error, input_value=26, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_count: must be at most 25. item_count: 26'
            )

    class TestCalculateWcus:
        """Property-based tests for calculate_wcus() method."""

        @pytest.fixture(autouse=True)
        def setup_base_pattern(self):
            """Set up base pattern for property-based tests."""
            self.base_pattern = {
                'operation': 'BatchWriteItem',
                'pattern': 'test-pattern',
                'description': 'Test description',
                'table': 'test-table',
                'rps': 100,
                'item_size_bytes': 1000,
                'item_count': 10,
            }

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_BATCH_WRITE_ITEMS // 2),
        )
        def test_linear_scaling_with_item_count(self, item_size_bytes, item_count):
            """Doubling item_count doubles WCUs."""
            pattern = {**self.base_pattern, 'item_size_bytes': item_size_bytes}
            pattern_single = {**pattern, 'item_count': item_count}
            pattern_double = {**pattern, 'item_count': item_count * 2}
            ap_single = BatchWriteItemAccessPattern(**pattern_single)
            ap_double = BatchWriteItemAccessPattern(**pattern_double)
            assert ap_double.calculate_wcus() == 2 * ap_single.calculate_wcus()

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_BATCH_WRITE_ITEMS),
        )
        def test_equivalent_to_item_count_times_single_write(self, item_size_bytes, item_count):
            """WCUs equal item_count times the WCU cost of a single item."""
            pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count,
            }
            ap = BatchWriteItemAccessPattern(**pattern)
            expected = math.ceil(item_size_bytes / WCU_SIZE) * item_count
            assert ap.calculate_wcus() == expected

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_BATCH_WRITE_ITEMS),
        )
        def test_wcus_always_positive(self, item_size_bytes, item_count):
            """WCUs are always positive for valid inputs."""
            pattern = {
                **self.base_pattern,
                'item_size_bytes': item_size_bytes,
                'item_count': item_count,
            }
            ap = BatchWriteItemAccessPattern(**pattern)
            assert ap.calculate_wcus() > 0

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count_a=st.integers(min_value=1, max_value=MAX_BATCH_WRITE_ITEMS),
            item_count_b=st.integers(min_value=1, max_value=MAX_BATCH_WRITE_ITEMS),
        )
        def test_monotonicity_with_item_count(self, item_size_bytes, item_count_a, item_count_b):
            """More items means equal or more WCUs."""
            pattern = {**self.base_pattern, 'item_size_bytes': item_size_bytes}
            ap_a = BatchWriteItemAccessPattern(**{**pattern, 'item_count': item_count_a})
            ap_b = BatchWriteItemAccessPattern(**{**pattern, 'item_count': item_count_b})
            if item_count_a <= item_count_b:
                assert ap_a.calculate_wcus() <= ap_b.calculate_wcus()
            else:
                assert ap_a.calculate_wcus() >= ap_b.calculate_wcus()

    class TestCalculateGsiWcus:
        """Tests for calculate_gsi_wcus() method."""

        def test_batchwriteitem_calculate_gsi_wcus_with_item_count(self, batchwriteitem_pattern):
            """Test BatchWriteItem GSI WCU calculation multiplies by item_count."""
            batchwriteitem_pattern['item_size_bytes'] = 1000
            batchwriteitem_pattern['gsi_list'] = ['gsi-1']
            ap = BatchWriteItemAccessPattern(**batchwriteitem_pattern)
            table = Table(
                name='test-table',
                item_count=1000,
                item_size_bytes=2000,
                gsi_list=[GSI(name='gsi-1', item_size_bytes=800, item_count=1000)],
            )
            gsi_wcus = ap.calculate_gsi_wcus(table)
            assert len(gsi_wcus) == 1
            assert gsi_wcus[0][0] == 'gsi-1'
            # 1 WCU per item * 10 items = 10.0
            assert gsi_wcus[0][1] == 10.0
