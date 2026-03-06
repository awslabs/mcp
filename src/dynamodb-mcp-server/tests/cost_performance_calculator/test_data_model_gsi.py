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

"""Unit tests for GSI model."""

import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    GSI,
    MAX_ITEM_SIZE_BYTES,
    STORAGE_OVERHEAD_BYTES,
    WCU_SIZE,
    Table,
    format_validation_errors,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError


class TestGSI:
    """Tests for GSI model."""

    @pytest.fixture
    def valid_gsi_data(self):
        """Valid GSI data."""
        return {'name': 'test-gsi', 'item_size_bytes': 1000, 'item_count': 100}

    class TestValid:
        """Tests for valid GSI creation."""

        def test_valid_gsi_minimal(self, valid_gsi_data):
            """Test GSI with valid minimal data."""
            gsi = GSI(**valid_gsi_data)
            assert gsi.name == 'test-gsi'
            assert gsi.item_size_bytes == 1000
            assert gsi.item_count == 100

        def test_valid_gsi_max_size(self):
            """Test GSI with maximum item size."""
            gsi = GSI(name='test-gsi', item_size_bytes=MAX_ITEM_SIZE_BYTES, item_count=1)
            assert gsi.item_size_bytes == MAX_ITEM_SIZE_BYTES

    class TestInvalid:
        """Tests for invalid GSI creation."""

        def test_invalid_gsi_empty_name(self, valid_gsi_data):
            """Test GSI with empty name."""
            valid_gsi_data['name'] = ''
            with pytest.raises(ValidationError) as exc_info:
                GSI(**valid_gsi_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == "1 validation error for GSI\nname\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]"
            )
            assert format_validation_errors(exc_info.value) == 'name: cannot be empty. name: '

        def test_invalid_gsi_item_size_zero(self, valid_gsi_data):
            """Test GSI with zero item size."""
            valid_gsi_data['item_size_bytes'] = 0
            with pytest.raises(ValidationError) as exc_info:
                GSI(**valid_gsi_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for GSI\nitem_size_bytes\n  Input should be greater than or equal to 1 [type=greater_than_equal, input_value=0, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_size_bytes: must be at least 1. item_size_bytes: 0'
            )

        def test_invalid_gsi_item_size_exceeds_max(self, valid_gsi_data):
            """Test GSI with item size exceeding maximum."""
            valid_gsi_data['item_size_bytes'] = 409601
            with pytest.raises(ValidationError) as exc_info:
                GSI(**valid_gsi_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for GSI\nitem_size_bytes\n  Input should be less than or equal to 409600 [type=less_than_equal, input_value=409601, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_size_bytes: must be at most 409600. item_size_bytes: 409601'
            )

        def test_invalid_gsi_item_count_zero(self, valid_gsi_data):
            """Test GSI with zero item count."""
            valid_gsi_data['item_count'] = 0
            with pytest.raises(ValidationError) as exc_info:
                GSI(**valid_gsi_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for GSI\nitem_count\n  Input should be greater than 0 [type=greater_than, input_value=0, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_count: must be greater than 0. item_count: 0'
            )

        def test_invalid_gsi_negative_item_count(self, valid_gsi_data):
            """Test GSI with negative item count."""
            valid_gsi_data['item_count'] = -1
            with pytest.raises(ValidationError) as exc_info:
                GSI(**valid_gsi_data)
            assert (
                strip_pydantic_error_url(exc_info.value)
                == '1 validation error for GSI\nitem_count\n  Input should be greater than 0 [type=greater_than, input_value=-1, input_type=int]'
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'item_count: must be greater than 0. item_count: -1'
            )

    class TestStorageGb:
        """Property-based tests for storage_gb() method."""

        @pytest.fixture(autouse=True)
        def setup_base_data(self):
            """Set up base GSI data for storage property tests."""
            self.base_data = {'name': 'test-gsi'}

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=10_000_000),
        )
        def test_storage_is_always_positive(self, item_size_bytes, item_count):
            """Storage must always be positive for valid inputs."""
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes, item_count=item_count)
            assert gsi.storage_gb() > 0

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=5_000_000),
        )
        def test_storage_scales_linearly_with_item_count(self, item_size_bytes, item_count):
            """Doubling item_count must double storage."""
            gsi_single = GSI(
                **self.base_data, item_size_bytes=item_size_bytes, item_count=item_count
            )
            gsi_double = GSI(
                **self.base_data, item_size_bytes=item_size_bytes, item_count=item_count * 2
            )
            assert abs(gsi_double.storage_gb() - 2 * gsi_single.storage_gb()) < 1e-10

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=10_000_000),
        )
        def test_storage_exceeds_raw_data_size(self, item_size_bytes, item_count):
            """Storage must exceed raw data size due to overhead."""
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes, item_count=item_count)
            raw_storage_gb = (item_count * item_size_bytes) / (1024**3)
            assert gsi.storage_gb() > raw_storage_gb

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=10_000_000),
        )
        def test_overhead_per_item_is_constant(self, item_size_bytes, item_count):
            """Overhead per item must be exactly STORAGE_OVERHEAD_BYTES."""
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes, item_count=item_count)
            expected = (item_count * (item_size_bytes + STORAGE_OVERHEAD_BYTES)) / (1024**3)
            assert abs(gsi.storage_gb() - expected) < 1e-10

        @settings(max_examples=1000)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            item_count=st.integers(min_value=1, max_value=10_000_000),
        )
        def test_gsi_and_table_storage_are_identical(self, item_size_bytes, item_count):
            """GSI and Table must produce identical storage for the same inputs."""
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes, item_count=item_count)
            table = Table(  # type: ignore[call-arg]
                name='test-table', item_size_bytes=item_size_bytes, item_count=item_count
            )
            assert gsi.storage_gb() == table.storage_gb()

    class TestWriteWcus:
        """Property-based tests for write_wcus() method."""

        @pytest.fixture(autouse=True)
        def setup_base_data(self):
            """Set up base GSI data for write WCU property tests."""
            self.base_data = {'name': 'test-gsi', 'item_count': 100}

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
        )
        def test_wcus_are_always_positive_integers(self, item_size_bytes):
            """WCUs must always be >= 1 and an integer value."""
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes)
            wcus = gsi.write_wcus()
            assert wcus >= 1
            assert wcus == int(wcus)

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=WCU_SIZE),
        )
        def test_items_up_to_1kb_consume_exactly_1_wcu(self, item_size_bytes):
            """Items <= 1KB must consume exactly 1 WCU."""
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes)
            assert gsi.write_wcus() == 1

        @settings(max_examples=100)
        @given(
            multiplier=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES // WCU_SIZE),
        )
        def test_exact_kb_boundaries_consume_exact_wcus(self, multiplier):
            """Items at exact KB boundaries must consume exactly size/1024 WCUs."""
            item_size_bytes = multiplier * WCU_SIZE
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes)
            assert gsi.write_wcus() == multiplier

        @settings(max_examples=100)
        @given(
            item_size_bytes=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES).filter(
                lambda x: x % WCU_SIZE != 0
            ),
        )
        def test_non_boundary_values_round_up(self, item_size_bytes):
            """Non-boundary items must round up to next WCU."""
            gsi = GSI(**self.base_data, item_size_bytes=item_size_bytes)
            assert gsi.write_wcus() == item_size_bytes // WCU_SIZE + 1

        @settings(max_examples=100)
        @given(
            size_a=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
            size_b=st.integers(min_value=1, max_value=MAX_ITEM_SIZE_BYTES),
        )
        def test_monotonicity(self, size_a, size_b):
            """Larger items must never consume fewer WCUs."""
            gsi_a = GSI(**self.base_data, item_size_bytes=size_a)
            gsi_b = GSI(**self.base_data, item_size_bytes=size_b)
            if size_a <= size_b:
                assert gsi_a.write_wcus() <= gsi_b.write_wcus()
            else:
                assert gsi_a.write_wcus() >= gsi_b.write_wcus()
