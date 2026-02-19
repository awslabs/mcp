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

"""Unit tests for TransactGetItemsAccessPattern model."""

import math
import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    MAX_ITEM_SIZE_BYTES,
    MAX_TRANSACT_ITEMS,
    RCU_SIZE,
    TransactGetItemsAccessPattern,
    format_validation_errors,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestTransactGetItemsAccessPattern:
    """Tests for TransactGetItemsAccessPattern model."""

    @pytest.fixture
    def transactgetitems_pattern(self):
        """Base TransactGetItems access pattern for calculation tests."""
        return {
            'operation': 'TransactGetItems',
            'pattern': 'test',
            'description': 'test',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 4096,
            'item_count': 5,
        }

    class TestValid:
        """Tests for valid TransactGetItems creation."""

        def test_valid_transactgetitems_minimal(self, transactgetitems_pattern):
            """Test TransactGetItems with valid minimal data."""
            ap = TransactGetItemsAccessPattern(**transactgetitems_pattern)
            assert ap.operation == 'TransactGetItems'
            assert ap.item_count == 5

        def test_valid_transactgetitems_max_items(self, transactgetitems_pattern):
            """Test TransactGetItems with maximum items."""
            transactgetitems_pattern['item_count'] = MAX_TRANSACT_ITEMS
            ap = TransactGetItemsAccessPattern(**transactgetitems_pattern)
            assert ap.item_count == MAX_TRANSACT_ITEMS

    class TestInvalid:
        """Tests for invalid TransactGetItems creation."""

        def test_invalid_transactgetitems_exceeds_max(self, transactgetitems_pattern):
            """Test TransactGetItems exceeding maximum items."""
            transactgetitems_pattern['item_count'] = 101
            with pytest.raises(ValidationError) as exc_info:
                TransactGetItemsAccessPattern(**transactgetitems_pattern)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for TransactGetItemsAccessPattern\nitem_count\n  Value error, must be at most 100. item_count: 101 [type=value_error, input_value=101, input_type=int]'
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
                'operation': 'TransactGetItems',
                'pattern': 'test',
                'description': 'test',
                'table': 'test-table',
                'rps': 100,
                'item_size_bytes': 4096,
                'item_count': 5,
            }

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_TRANSACT_ITEMS),
        )
        def test_transaction_overhead_is_exactly_2x(self, item_size, item_count):
            """Transaction overhead is exactly 2x compared to base RCUs."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['item_count'] = item_count
            ap = TransactGetItemsAccessPattern(**self.base_pattern)

            base_rcus = math.ceil(item_size / RCU_SIZE) * item_count
            assert ap.calculate_rcus() == 2 * base_rcus

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_TRANSACT_ITEMS // 2),
        )
        def test_linear_scaling_with_item_count(self, item_size, item_count):
            """Doubling item_count exactly doubles RCUs."""
            self.base_pattern['item_size_bytes'] = item_size

            self.base_pattern['item_count'] = item_count
            ap_single = TransactGetItemsAccessPattern(**self.base_pattern)

            self.base_pattern['item_count'] = item_count * 2
            ap_double = TransactGetItemsAccessPattern(**self.base_pattern)

            assert ap_double.calculate_rcus() == 2.0 * ap_single.calculate_rcus()

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=MAX_TRANSACT_ITEMS),
        )
        def test_rcus_are_always_positive(self, item_size, item_count):
            """RCUs are always positive for valid inputs."""
            self.base_pattern['item_size_bytes'] = item_size
            self.base_pattern['item_count'] = item_count
            ap = TransactGetItemsAccessPattern(**self.base_pattern)
            assert ap.calculate_rcus() > 0

        @settings(max_examples=100)
        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            count1=st.integers(min_value=1, max_value=MAX_TRANSACT_ITEMS),
            count2=st.integers(min_value=1, max_value=MAX_TRANSACT_ITEMS),
        )
        def test_monotonicity_with_item_count(self, item_size, count1, count2):
            """More items means equal or more RCUs."""
            self.base_pattern['item_size_bytes'] = item_size

            self.base_pattern['item_count'] = count1
            ap1 = TransactGetItemsAccessPattern(**self.base_pattern)

            self.base_pattern['item_count'] = count2
            ap2 = TransactGetItemsAccessPattern(**self.base_pattern)

            if count1 <= count2:
                assert ap1.calculate_rcus() <= ap2.calculate_rcus()
            else:
                assert ap1.calculate_rcus() >= ap2.calculate_rcus()
