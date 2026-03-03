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

"""Unit tests for cost_calculator module."""

import math
import pytest
from awslabs.dynamodb_mcp_server.cost_performance_calculator.cost_calculator import (
    RCU_PRICE,
    SECONDS_PER_MONTH,
    WCU_PRICE,
    calculate_cost,
)
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    MAX_ITEM_SIZE_BYTES,
    RCU_SIZE,
    WCU_SIZE,
    DataModel,
)
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.fixture
def base_table():
    """Base table for tests."""
    return {'name': 'test-table', 'item_count': 1000, 'item_size_bytes': MAX_ITEM_SIZE_BYTES}


@pytest.fixture
def base_access_pattern():
    """Base access pattern for tests."""
    return {
        'pattern': 'test-pattern',
        'description': 'Test description',
        'table': 'test-table',
        'rps': 100,
        'item_size_bytes': 1000,
    }


class TestCalculateCost:
    """Tests for calculate_cost function."""

    class TestReadOperations:
        """RCU calculation tests."""

        def test_getitem_eventually_consistent(self, base_table, base_access_pattern):
            """GetItem with eventually consistent read."""
            base_access_pattern['operation'] = 'GetItem'
            base_access_pattern['item_size_bytes'] = 4096  # Exactly 1 RCU
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            assert result.access_patterns[0].rcus == 0.5  # Eventually consistent = 0.5x
            assert result.access_patterns[0].wcus == 0.0

        def test_getitem_strongly_consistent(self, base_table, base_access_pattern):
            """GetItem with strongly consistent read."""
            base_access_pattern['operation'] = 'GetItem'
            base_access_pattern['item_size_bytes'] = 4096
            base_access_pattern['strongly_consistent'] = True
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            assert result.access_patterns[0].rcus == 1.0  # Strongly consistent = 1x
            assert result.access_patterns[0].wcus == 0.0

        def test_query_multiple_items(self, base_table, base_access_pattern):
            """Query returning multiple items."""
            base_access_pattern['operation'] = 'Query'
            base_access_pattern['item_size_bytes'] = 2048
            base_access_pattern['item_count'] = 10
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # 10 items * 2048 bytes = 20480 bytes total
            # ceil(20480 / 4096) = 5 RCUs * 0.5 (eventually consistent) = 2.5
            assert result.access_patterns[0].rcus == 2.5

        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            strongly_consistent=st.booleans(),
        )
        @settings(max_examples=100)
        def test_rcu_formula_property(self, item_size, strongly_consistent):
            """Property 1: RCU Calculation Formula.

            For any read access pattern with item_size_bytes and consistency mode,
            the calculated RCU SHALL equal ceil(total_size / 4096) * consistency_multiplier.

            **Validates: Requirements 6.1**
            """
            data = {
                'access_pattern_list': [
                    {
                        'operation': 'GetItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 1,
                        'item_size_bytes': item_size,
                        'strongly_consistent': strongly_consistent,
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000,
                        'item_size_bytes': MAX_ITEM_SIZE_BYTES,
                    }
                ],
            }
            result = calculate_cost(DataModel(**data))

            expected_rcus = math.ceil(item_size / RCU_SIZE)
            if not strongly_consistent:
                expected_rcus *= 0.5

            assert result.access_patterns[0].rcus == expected_rcus

    class TestWriteOperations:
        """WCU calculation tests."""

        def test_putitem_basic(self, base_table, base_access_pattern):
            """PutItem basic write."""
            base_access_pattern['operation'] = 'PutItem'
            base_access_pattern['item_size_bytes'] = 1024  # Exactly 1 WCU
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            assert result.access_patterns[0].wcus == 1.0
            assert result.access_patterns[0].rcus == 0.0

        def test_putitem_large_item(self, base_table, base_access_pattern):
            """PutItem with large item requiring multiple WCUs."""
            base_access_pattern['operation'] = 'PutItem'
            base_access_pattern['item_size_bytes'] = 3000  # ceil(3000/1024) = 3 WCUs
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            assert result.access_patterns[0].wcus == 3.0

        @given(item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES))
        @settings(max_examples=100)
        def test_wcu_formula_property(self, item_size):
            """Property 2: WCU Calculation Formula.

            For any write access pattern with item_size_bytes,
            the calculated WCU SHALL equal ceil(item_size / 1024).

            **Validates: Requirements 6.2**
            """
            data = {
                'access_pattern_list': [
                    {
                        'operation': 'PutItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 1,
                        'item_size_bytes': item_size,
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000,
                        'item_size_bytes': MAX_ITEM_SIZE_BYTES,
                    }
                ],
            }
            result = calculate_cost(DataModel(**data))

            expected_wcus = math.ceil(item_size / WCU_SIZE)
            assert result.access_patterns[0].wcus == expected_wcus

    class TestBatchOperations:
        """Batch operation tests."""

        def test_batchgetitem_per_item_calculation(self, base_table, base_access_pattern):
            """BatchGetItem charges per item, not total size."""
            base_access_pattern['operation'] = 'BatchGetItem'
            base_access_pattern['item_size_bytes'] = 2048
            base_access_pattern['item_count'] = 3
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # ceil(2048 / 4096) * 3 * 0.5 (eventually consistent) = 1 * 3 * 0.5 = 1.5 RCUs
            assert result.access_patterns[0].rcus == 1.5

        def test_batchgetitem_strongly_consistent(self, base_table, base_access_pattern):
            """BatchGetItem with strong consistency."""
            base_access_pattern['operation'] = 'BatchGetItem'
            base_access_pattern['item_size_bytes'] = 2048
            base_access_pattern['item_count'] = 3
            base_access_pattern['strongly_consistent'] = True
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # ceil(2048 / 4096) * 3 * 1.0 (strongly consistent) = 1 * 3 * 1.0 = 3.0 RCUs
            assert result.access_patterns[0].rcus == 3.0

        def test_batchwriteitem_per_item_calculation(self, base_table, base_access_pattern):
            """BatchWriteItem charges per item, not total size."""
            base_access_pattern['operation'] = 'BatchWriteItem'
            base_access_pattern['item_size_bytes'] = 1536
            base_access_pattern['item_count'] = 3
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # ceil(1536 / 1024) * 3 = 2 * 3 = 6 WCUs
            assert result.access_patterns[0].wcus == 6.0

    class TestTransactions:
        """Transaction capacity doubling tests."""

        def test_transact_get_items(self, base_table, base_access_pattern):
            """TransactGetItems doubles RCU."""
            base_access_pattern['operation'] = 'TransactGetItems'
            base_access_pattern['item_size_bytes'] = 4096
            base_access_pattern['item_count'] = 5
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # 5 items * 1 RCU each * 2 (transaction) = 10 RCUs
            assert result.access_patterns[0].rcus == 10.0

        def test_transact_write_items(self, base_table, base_access_pattern):
            """TransactWriteItems doubles WCU."""
            base_access_pattern['operation'] = 'TransactWriteItems'
            base_access_pattern['item_size_bytes'] = 1024
            base_access_pattern['item_count'] = 5
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # 5 items * 1 WCU each * 2 (transaction) = 10 WCUs
            assert result.access_patterns[0].wcus == 10.0

        @given(
            item_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=100),
        )
        @settings(max_examples=100)
        def test_transaction_capacity_doubling_property(self, item_size, item_count):
            """Property 3: Transaction Capacity Doubling.

            For any TransactGetItems or TransactWriteItems access pattern,
            the calculated capacity units SHALL be exactly 2x the non-transactional equivalent.

            **Validates: Requirements 6.3**
            """
            # Test TransactGetItems
            transact_get_data = {
                'access_pattern_list': [
                    {
                        'operation': 'TransactGetItems',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 1,
                        'item_size_bytes': item_size,
                        'item_count': item_count,
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000,
                        'item_size_bytes': MAX_ITEM_SIZE_BYTES,
                    }
                ],
            }
            result = calculate_cost(DataModel(**transact_get_data))

            # Non-transactional equivalent: ceil(item_size / 4096) * item_count
            base_rcus = math.ceil(item_size / RCU_SIZE) * item_count
            expected_rcus = 2 * base_rcus
            assert result.access_patterns[0].rcus == expected_rcus

            # Test TransactWriteItems
            transact_write_data = {
                'access_pattern_list': [
                    {
                        'operation': 'TransactWriteItems',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 1,
                        'item_size_bytes': item_size,
                        'item_count': item_count,
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000,
                        'item_size_bytes': MAX_ITEM_SIZE_BYTES,
                    }
                ],
            }
            result = calculate_cost(DataModel(**transact_write_data))

            # Non-transactional equivalent: ceil(item_size / 1024) * item_count
            base_wcus = math.ceil(item_size / WCU_SIZE) * item_count
            expected_wcus = 2 * base_wcus
            assert result.access_patterns[0].wcus == expected_wcus

    class TestGSIWriteAmplification:
        """GSI write amplification tests."""

        def test_putitem_with_gsi(self):
            """PutItem with GSI write amplification."""
            data = {
                'access_pattern_list': [
                    {
                        'operation': 'PutItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 100,
                        'item_size_bytes': 1024,
                        'gsi_list': ['gsi-1'],
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000,
                        'item_size_bytes': 2048,
                        'gsi_list': [
                            {'name': 'gsi-1', 'item_size_bytes': 512, 'item_count': 1000}
                        ],
                    }
                ],
            }
            result = calculate_cost(DataModel(**data))

            assert len(result.access_patterns[0].gsi_write_amplification) == 1
            gsi_amp = result.access_patterns[0].gsi_write_amplification[0]
            assert gsi_amp.gsi_name == 'gsi-1'
            assert gsi_amp.wcus == 1.0  # ceil(512/1024) = 1

        def test_putitem_with_multiple_gsis(self):
            """PutItem with multiple GSIs."""
            data = {
                'access_pattern_list': [
                    {
                        'operation': 'PutItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 100,
                        'item_size_bytes': 1024,
                        'gsi_list': ['gsi-1', 'gsi-2'],
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000,
                        'item_size_bytes': 2048,
                        'gsi_list': [
                            {'name': 'gsi-1', 'item_size_bytes': 512, 'item_count': 1000},
                            {'name': 'gsi-2', 'item_size_bytes': 1024, 'item_count': 1000},
                        ],
                    }
                ],
            }
            result = calculate_cost(DataModel(**data))

            assert len(result.access_patterns[0].gsi_write_amplification) == 2

        @given(
            gsi_size=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            gsi_count=st.integers(min_value=1, max_value=5),
        )
        @settings(max_examples=100)
        def test_gsi_write_amplification_property(self, gsi_size, gsi_count):
            """Property 4: GSI Write Amplification.

            For any write access pattern with a non-empty gsi_list,
            the CostModel SHALL include GSIWriteAmplification entries for each GSI,
            with WCU calculated using the GSI's item_size_bytes.

            **Validates: Requirements 6.4**
            """
            gsi_list = [
                {'name': f'gsi-{i}', 'item_size_bytes': gsi_size, 'item_count': 1000}
                for i in range(gsi_count)
            ]
            gsi_names = [f'gsi-{i}' for i in range(gsi_count)]

            data = {
                'access_pattern_list': [
                    {
                        'operation': 'PutItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 1,
                        'item_size_bytes': 1024,
                        'gsi_list': gsi_names,
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000,
                        'item_size_bytes': MAX_ITEM_SIZE_BYTES,
                        'gsi_list': gsi_list,
                    }
                ],
            }
            result = calculate_cost(DataModel(**data))

            # Verify we have amplification entries for each GSI
            assert len(result.access_patterns[0].gsi_write_amplification) == gsi_count

            # Verify WCU calculation for each GSI
            expected_wcus = math.ceil(gsi_size / WCU_SIZE)
            for gsi_amp in result.access_patterns[0].gsi_write_amplification:
                assert gsi_amp.wcus == expected_wcus

    class TestCostCalculation:
        """Cost calculation tests."""

        def test_read_cost_calculation(self, base_table, base_access_pattern):
            """Verify read cost calculation."""
            base_access_pattern['operation'] = 'GetItem'
            base_access_pattern['item_size_bytes'] = 4096
            base_access_pattern['rps'] = 100
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # 0.5 RCU * 100 RPS * SECONDS_PER_MONTH * RCU_PRICE
            expected_cost = 0.5 * 100 * SECONDS_PER_MONTH * RCU_PRICE
            assert result.access_patterns[0].cost == expected_cost

        def test_write_cost_calculation(self, base_table, base_access_pattern):
            """Verify write cost calculation."""
            base_access_pattern['operation'] = 'PutItem'
            base_access_pattern['item_size_bytes'] = 1024
            base_access_pattern['rps'] = 100
            data = DataModel(access_pattern_list=[base_access_pattern], table_list=[base_table])
            result = calculate_cost(data)

            # 1 WCU * 100 RPS * SECONDS_PER_MONTH * WCU_PRICE
            expected_cost = 1 * 100 * SECONDS_PER_MONTH * WCU_PRICE
            assert result.access_patterns[0].cost == expected_cost

    class TestStorageCalculation:
        """Storage calculation tests."""

        def test_table_storage(self):
            """Verify table storage calculation includes 100-byte overhead per item."""
            data = {
                'access_pattern_list': [
                    {
                        'operation': 'GetItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 1,
                        'item_size_bytes': 1000,
                    }
                ],
                'table_list': [
                    {'name': 'test-table', 'item_count': 1000000, 'item_size_bytes': 1024}
                ],
            }
            result = calculate_cost(DataModel(**data))

            # 1000000 items * (1024 bytes + 100 byte overhead) / 1024^3
            expected_storage_gb = (1000000 * (1024 + 100)) / (1024**3)
            assert result.tables[0].storage_gb == pytest.approx(expected_storage_gb)
            assert result.tables[0].storage_cost == pytest.approx(expected_storage_gb * 0.25)

        def test_gsi_storage(self):
            """Verify GSI storage calculation includes 100-byte overhead per item."""
            data = {
                'access_pattern_list': [
                    {
                        'operation': 'GetItem',
                        'pattern': 'test',
                        'description': 'test',
                        'table': 'test-table',
                        'rps': 1,
                        'item_size_bytes': 500,
                    }
                ],
                'table_list': [
                    {
                        'name': 'test-table',
                        'item_count': 1000000,
                        'item_size_bytes': 1024,
                        'gsi_list': [
                            {'name': 'gsi-1', 'item_size_bytes': 512, 'item_count': 1000000}
                        ],
                    }
                ],
            }
            result = calculate_cost(DataModel(**data))

            assert len(result.gsis) == 1
            # 1000000 items * (512 bytes + 100 byte overhead) / 1024^3
            expected_gsi_storage_gb = (1000000 * (512 + 100)) / (1024**3)
            assert result.gsis[0].storage_gb == pytest.approx(expected_gsi_storage_gb)
