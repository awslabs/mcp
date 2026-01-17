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

"""Unit tests for CostAnalyzer class."""

import pytest
from awslabs.aws_healthomics_mcp_server.analysis.cost_analyzer import CostAnalyzer
from awslabs.aws_healthomics_mcp_server.analysis.pricing_cache import PricingCache

# Property-Based Tests using Hypothesis
from hypothesis import given
from hypothesis import strategies as st
from unittest.mock import patch


class TestCostAnalyzerCalculateTaskCost:
    """Test cases for calculate_task_cost method."""

    def setup_method(self):
        """Clear pricing cache before each test."""
        PricingCache.clear_cache()

    def teardown_method(self):
        """Clear pricing cache after each test."""
        PricingCache.clear_cache()

    def test_calculate_task_cost_basic(self):
        """Test basic task cost calculation."""
        with patch.object(PricingCache, 'get_price', return_value=1.0):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_task_cost('omics.m.xlarge', 3600)  # 1 hour
            assert cost == 1.0

    def test_calculate_task_cost_minimum_billing(self):
        """Test that minimum billing time of 60 seconds is applied."""
        with patch.object(PricingCache, 'get_price', return_value=1.0):
            analyzer = CostAnalyzer('us-east-1')
            # 30 seconds should be billed as 60 seconds
            cost = analyzer.calculate_task_cost('omics.m.xlarge', 30)
            expected = 1.0 * (60 / 3600)  # 60 seconds at $1/hour
            assert cost == pytest.approx(expected)

    def test_calculate_task_cost_zero_runtime(self):
        """Test that zero runtime uses minimum billing time."""
        with patch.object(PricingCache, 'get_price', return_value=1.0):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_task_cost('omics.m.xlarge', 0)
            expected = 1.0 * (60 / 3600)  # 60 seconds minimum
            assert cost == pytest.approx(expected)

    def test_calculate_task_cost_above_minimum(self):
        """Test cost calculation when runtime exceeds minimum."""
        with patch.object(PricingCache, 'get_price', return_value=2.0):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_task_cost('omics.m.xlarge', 1800)  # 30 minutes
            expected = 2.0 * (1800 / 3600)  # 0.5 hours at $2/hour
            assert cost == pytest.approx(expected)

    def test_calculate_task_cost_pricing_unavailable(self):
        """Test that None is returned when pricing is unavailable."""
        with patch.object(PricingCache, 'get_price', return_value=None):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_task_cost('omics.m.xlarge', 3600)
            assert cost is None


class TestCostAnalyzerCalculateStorageCost:
    """Test cases for calculate_storage_cost method."""

    def setup_method(self):
        """Clear pricing cache before each test."""
        PricingCache.clear_cache()

    def teardown_method(self):
        """Clear pricing cache after each test."""
        PricingCache.clear_cache()

    def test_calculate_storage_cost_static(self):
        """Test static storage cost calculation."""
        with patch.object(PricingCache, 'get_price', return_value=0.01):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_storage_cost(
                storage_type='STATIC',
                storage_reserved_gib=1000,  # Below minimum, will be 1200
                storage_average_gib=500,
                running_seconds=3600,  # 1 hour
            )
            expected = 0.01 * 1200 * 1.0  # $0.01/GiB-hour * 1200 GiB * 1 hour
            assert cost == pytest.approx(expected)

    def test_calculate_storage_cost_dynamic(self):
        """Test dynamic storage cost calculation."""
        with patch.object(PricingCache, 'get_price', return_value=0.02):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_storage_cost(
                storage_type='DYNAMIC',
                storage_reserved_gib=1000,
                storage_average_gib=500,  # Uses average for dynamic
                running_seconds=3600,  # 1 hour
            )
            expected = 0.02 * 500 * 1.0  # $0.02/GiB-hour * 500 GiB * 1 hour
            assert cost == pytest.approx(expected)

    def test_calculate_storage_cost_pricing_unavailable(self):
        """Test that None is returned when pricing is unavailable."""
        with patch.object(PricingCache, 'get_price', return_value=None):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_storage_cost(
                storage_type='STATIC',
                storage_reserved_gib=1000,
                storage_average_gib=500,
                running_seconds=3600,
            )
            assert cost is None


class TestCostAnalyzerStaticStorageAllocation:
    """Test cases for _get_static_storage_allocation method."""

    def test_allocation_below_minimum(self):
        """Test allocation when capacity is below minimum."""
        analyzer = CostAnalyzer('us-east-1')
        assert analyzer._get_static_storage_allocation(500) == 1200.0
        assert analyzer._get_static_storage_allocation(1000) == 1200.0
        assert analyzer._get_static_storage_allocation(1199) == 1200.0

    def test_allocation_at_minimum(self):
        """Test allocation when capacity equals minimum."""
        analyzer = CostAnalyzer('us-east-1')
        assert analyzer._get_static_storage_allocation(1200) == 1200.0

    def test_allocation_above_minimum(self):
        """Test allocation when capacity exceeds minimum."""
        analyzer = CostAnalyzer('us-east-1')
        # 1201 should round up to 2400
        assert analyzer._get_static_storage_allocation(1201) == 2400.0
        # 2400 should stay at 2400
        assert analyzer._get_static_storage_allocation(2400) == 2400.0
        # 2401 should round up to 4800
        assert analyzer._get_static_storage_allocation(2401) == 4800.0

    def test_allocation_zero(self):
        """Test allocation when capacity is zero."""
        analyzer = CostAnalyzer('us-east-1')
        assert analyzer._get_static_storage_allocation(0) == 1200.0

    def test_allocation_large_capacity(self):
        """Test allocation for large capacity values."""
        analyzer = CostAnalyzer('us-east-1')
        # 10000 GiB should round up to ceil(10000/2400)*2400 = 5*2400 = 12000
        assert analyzer._get_static_storage_allocation(10000) == 12000.0


class TestCostAnalyzerConstants:
    """Test cases for CostAnalyzer constants."""

    def test_minimum_billable_seconds(self):
        """Test MINIMUM_BILLABLE_SECONDS constant."""
        assert CostAnalyzer.MINIMUM_BILLABLE_SECONDS == 60

    def test_static_storage_min_gib(self):
        """Test STATIC_STORAGE_MIN_GIB constant."""
        assert CostAnalyzer.STATIC_STORAGE_MIN_GIB == 1200

    def test_static_storage_increment_gib(self):
        """Test STATIC_STORAGE_INCREMENT_GIB constant."""
        assert CostAnalyzer.STATIC_STORAGE_INCREMENT_GIB == 2400


class TestCostAnalyzerPropertyBased:
    """Property-based tests for CostAnalyzer using Hypothesis."""

    def setup_method(self):
        """Clear pricing cache before each test."""
        PricingCache.clear_cache()

    def teardown_method(self):
        """Clear pricing cache after each test."""
        PricingCache.clear_cache()

    @given(running_seconds=st.floats(min_value=0, max_value=86400, allow_nan=False))
    def test_property_minimum_billable_time(self, running_seconds: float):
        """Property 1: Minimum Billable Time.

        For any task with running time R seconds, the billable time used in
        cost calculation SHALL be max(60, R).

        **Validates: Requirements 1.1, 1.3**
        **Feature: run-analyzer-enhancement, Property 1: Minimum Billable Time**
        """
        price_per_hour = 1.0  # Use $1/hour for easy verification

        with patch.object(PricingCache, 'get_price', return_value=price_per_hour):
            analyzer = CostAnalyzer('us-east-1')
            cost = analyzer.calculate_task_cost('omics.m.xlarge', running_seconds)

            # Calculate expected billable time
            expected_billable_seconds = max(CostAnalyzer.MINIMUM_BILLABLE_SECONDS, running_seconds)
            expected_billable_hours = expected_billable_seconds / 3600.0
            expected_cost = price_per_hour * expected_billable_hours

            assert cost is not None
            assert cost == pytest.approx(expected_cost, rel=1e-9)

            # Verify the property: billable time is always >= 60 seconds
            actual_billable_hours = cost / price_per_hour
            actual_billable_seconds = actual_billable_hours * 3600.0
            assert actual_billable_seconds >= CostAnalyzer.MINIMUM_BILLABLE_SECONDS

    @given(capacity=st.floats(min_value=0, max_value=100000, allow_nan=False))
    def test_property_static_storage_allocation_rounding(self, capacity: float):
        """Property 11: Static Storage Allocation Rounding.

        For any storage capacity C:
        - If C <= 1200, allocation SHALL be 1200 GiB
        - If C > 1200, allocation SHALL be ceil(C / 2400) * 2400 GiB

        **Validates: Requirements 11.1**
        **Feature: run-analyzer-enhancement, Property 11: Static Storage Allocation Rounding**
        """
        import math

        analyzer = CostAnalyzer('us-east-1')
        allocation = analyzer._get_static_storage_allocation(capacity)

        # Property: allocation is always >= minimum
        assert allocation >= CostAnalyzer.STATIC_STORAGE_MIN_GIB

        # Property: allocation follows the rounding rules
        if capacity <= CostAnalyzer.STATIC_STORAGE_MIN_GIB:
            # Below or at minimum: allocation is exactly the minimum
            assert allocation == CostAnalyzer.STATIC_STORAGE_MIN_GIB
        else:
            # Above minimum: allocation is ceil(C / 2400) * 2400
            expected = (
                math.ceil(capacity / CostAnalyzer.STATIC_STORAGE_INCREMENT_GIB)
                * CostAnalyzer.STATIC_STORAGE_INCREMENT_GIB
            )
            assert allocation == expected

        # Property: allocation is always a multiple of the increment (or the minimum)
        if allocation > CostAnalyzer.STATIC_STORAGE_MIN_GIB:
            assert allocation % CostAnalyzer.STATIC_STORAGE_INCREMENT_GIB == 0

        # Property: allocation is always >= capacity
        assert allocation >= capacity
