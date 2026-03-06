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

"""Unit tests for PutItemAccessPattern model."""

import pytest
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    GSI,
    MAX_ITEM_SIZE_BYTES,
    WCU_SIZE,
    DeleteItemAccessPattern,
    PutItemAccessPattern,
    Table,
    UpdateItemAccessPattern,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestPutItemAccessPattern:
    """Tests for PutItemAccessPattern model."""

    @pytest.fixture
    def putitem_pattern(self):
        """Base PutItem access pattern for calculation tests."""
        return {
            'operation': 'PutItem',
            'pattern': 'test',
            'description': 'test',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 1000,
        }

    class TestValid:
        """Tests for valid PutItem creation."""

        def test_valid_putitem_minimal(self, putitem_pattern):
            """Test PutItem with valid minimal data."""
            ap = PutItemAccessPattern(**putitem_pattern)
            assert ap.operation == 'PutItem'
            assert ap.gsi_list == []

        def test_valid_putitem_with_gsi_list(self, putitem_pattern):
            """Test PutItem with GSI list."""
            putitem_pattern['gsi_list'] = ['gsi-1', 'gsi-2']
            ap = PutItemAccessPattern(**putitem_pattern)
            assert ap.gsi_list == ['gsi-1', 'gsi-2']

    class TestCalculateWcus:
        """Property-based tests for calculate_wcus() method."""

        @pytest.fixture(autouse=True)
        def setup_base_pattern(self):
            """Set up base pattern for property-based tests."""
            self.base_pattern = {
                'pattern': 'test',
                'description': 'test',
                'table': 'test-table',
                'rps': 100,
                'item_size_bytes': 1000,
            }

        @given(size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES))
        @settings(max_examples=100)
        def test_wcus_always_positive_integer(self, size):
            """WCUs are always positive integers (>= 1)."""
            ap = PutItemAccessPattern(
                **{**self.base_pattern, 'operation': 'PutItem', 'item_size_bytes': size}
            )
            wcus = ap.calculate_wcus()
            assert wcus >= 1
            assert wcus == int(wcus)

        @given(size=st.integers(min_value=1, max_value=WCU_SIZE))
        @settings(max_examples=100)
        def test_items_up_to_1kb_consume_exactly_1_wcu(self, size):
            """Items <= 1KB consume exactly 1 WCU."""
            ap = PutItemAccessPattern(
                **{**self.base_pattern, 'operation': 'PutItem', 'item_size_bytes': size}
            )
            wcus = ap.calculate_wcus()
            assert wcus == 1.0

        @given(n=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES // WCU_SIZE))
        @settings(max_examples=100)
        def test_exact_kb_boundaries_consume_exact_wcus(self, n):
            """Exact KB boundaries consume exact WCUs."""
            ap = PutItemAccessPattern(
                **{**self.base_pattern, 'operation': 'PutItem', 'item_size_bytes': n * WCU_SIZE}
            )
            wcus = ap.calculate_wcus()
            assert wcus == float(n)

        @given(
            n=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES // WCU_SIZE - 1),
            extra=st.integers(min_value=1, max_value=WCU_SIZE - 1),
        )
        @settings(max_examples=100)
        def test_non_boundary_values_round_up(self, n, extra):
            """Non-boundary values round up to the next WCU."""
            size = n * WCU_SIZE + extra
            if size > MAX_ITEM_SIZE_BYTES:
                return
            ap = PutItemAccessPattern(
                **{**self.base_pattern, 'operation': 'PutItem', 'item_size_bytes': size}
            )
            wcus = ap.calculate_wcus()
            assert wcus == float(n + 1)

        @given(
            size_a=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            size_b=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
        )
        @settings(max_examples=100)
        def test_monotonicity_larger_items_never_fewer_wcus(self, size_a, size_b):
            """Larger items never consume fewer WCUs."""
            ap_a = PutItemAccessPattern(
                **{**self.base_pattern, 'operation': 'PutItem', 'item_size_bytes': size_a}
            )
            ap_b = PutItemAccessPattern(
                **{**self.base_pattern, 'operation': 'PutItem', 'item_size_bytes': size_b}
            )
            if size_a <= size_b:
                assert ap_a.calculate_wcus() <= ap_b.calculate_wcus()
            else:
                assert ap_a.calculate_wcus() >= ap_b.calculate_wcus()

        @given(size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES))
        @settings(max_examples=100)
        def test_all_write_operations_produce_identical_wcus(self, size):
            """All three write operations produce identical WCUs for the same size."""
            put_ap = PutItemAccessPattern(
                **{**self.base_pattern, 'operation': 'PutItem', 'item_size_bytes': size}
            )
            update_ap = UpdateItemAccessPattern(
                **{**self.base_pattern, 'operation': 'UpdateItem', 'item_size_bytes': size}
            )
            delete_ap = DeleteItemAccessPattern(
                **{**self.base_pattern, 'operation': 'DeleteItem', 'item_size_bytes': size}
            )
            assert (
                put_ap.calculate_wcus() == update_ap.calculate_wcus() == delete_ap.calculate_wcus()
            )

    class TestCalculateGsiWcus:
        """Tests for calculate_gsi_wcus() method."""

        def test_putitem_calculate_gsi_wcus_no_gsis(self, putitem_pattern):
            """Test PutItem GSI WCU calculation with no GSIs."""
            putitem_pattern['gsi_list'] = []
            ap = PutItemAccessPattern(**putitem_pattern)
            table = Table(
                name='test-table',
                item_count=1000,
                item_size_bytes=2000,
                gsi_list=[],
            )
            gsi_wcus = ap.calculate_gsi_wcus(table)
            assert gsi_wcus == []

        def test_putitem_calculate_gsi_wcus_single_gsi(self, putitem_pattern):
            """Test PutItem GSI WCU calculation with single GSI."""
            putitem_pattern['gsi_list'] = ['gsi-1']
            ap = PutItemAccessPattern(**putitem_pattern)
            table = Table(
                name='test-table',
                item_count=1000,
                item_size_bytes=2000,
                gsi_list=[GSI(name='gsi-1', item_size_bytes=800, item_count=1000)],
            )
            gsi_wcus = ap.calculate_gsi_wcus(table)
            assert len(gsi_wcus) == 1
            assert gsi_wcus[0][0] == 'gsi-1'
            # 800 bytes = 1 WCU
            assert gsi_wcus[0][1] == 1.0

        def test_putitem_calculate_gsi_wcus_multiple_gsis(self, putitem_pattern):
            """Test PutItem GSI WCU calculation with multiple GSIs."""
            putitem_pattern['gsi_list'] = ['gsi-1', 'gsi-2']
            ap = PutItemAccessPattern(**putitem_pattern)
            table = Table(
                name='test-table',
                item_count=1000,
                item_size_bytes=2000,
                gsi_list=[
                    GSI(name='gsi-1', item_size_bytes=800, item_count=1000),
                    GSI(name='gsi-2', item_size_bytes=1500, item_count=1000),
                ],
            )
            gsi_wcus = ap.calculate_gsi_wcus(table)
            assert len(gsi_wcus) == 2
            assert gsi_wcus[0][0] == 'gsi-1'
            assert gsi_wcus[0][1] == 1.0  # 800 bytes = 1 WCU
            assert gsi_wcus[1][0] == 'gsi-2'
            assert gsi_wcus[1][1] == 2.0  # 1500 bytes = 2 WCUs

        def test_putitem_calculate_gsi_wcus_gsi_not_in_table(self, putitem_pattern):
            """Test PutItem GSI WCU calculation when GSI not in table."""
            putitem_pattern['gsi_list'] = ['gsi-1', 'non-existent-gsi']
            ap = PutItemAccessPattern(**putitem_pattern)
            table = Table(
                name='test-table',
                item_count=1000,
                item_size_bytes=2000,
                gsi_list=[GSI(name='gsi-1', item_size_bytes=800, item_count=1000)],
            )
            gsi_wcus = ap.calculate_gsi_wcus(table)
            # Should only return WCUs for gsi-1, skip non-existent-gsi
            assert len(gsi_wcus) == 1
            assert gsi_wcus[0][0] == 'gsi-1'

    class TestValidation:
        """Tests for validation logic."""

        def test_putitem_gsi_list_validation_empty_name(self, putitem_pattern):
            """Test PutItem rejects empty GSI name in list."""
            putitem_pattern['gsi_list'] = ['gsi-1', '']
            with pytest.raises(ValidationError) as exc_info:
                PutItemAccessPattern(**putitem_pattern)
            assert 'GSI name cannot be empty' in str(exc_info.value)

        def test_putitem_gsi_list_validation_duplicate_names(self, putitem_pattern):
            """Test PutItem rejects duplicate GSI names in list."""
            putitem_pattern['gsi_list'] = ['gsi-1', 'gsi-2', 'gsi-1']
            with pytest.raises(ValidationError) as exc_info:
                PutItemAccessPattern(**putitem_pattern)
            assert 'duplicate GSI name in gsi_list' in str(exc_info.value)
