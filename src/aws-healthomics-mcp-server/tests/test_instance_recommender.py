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

"""Unit and property-based tests for InstanceRecommender class."""

import math
import pytest
from awslabs.aws_healthomics_mcp_server.analysis.instance_recommender import InstanceRecommender
from awslabs.aws_healthomics_mcp_server.analysis.pricing_cache import PricingCache
from hypothesis import assume, given
from hypothesis import strategies as st
from unittest.mock import patch


class TestInstanceRecommenderRecommendInstance:
    """Test cases for recommend_instance method."""

    def test_recommend_instance_small_workload(self):
        """Test recommendation for small workload."""
        recommender = InstanceRecommender(headroom=0.20)
        instance, cpus, memory = recommender.recommend_instance(1.0, 2.0)

        # With 20% headroom: ceil(1.0 * 1.2) = 2 CPUs, ceil(2.0 * 1.2) = 3 GiB
        assert cpus == 2
        assert memory == 3.0
        # Should fit in omics.c.large (2 CPUs, 4 GiB)
        assert instance == 'omics.c.large'

    def test_recommend_instance_memory_heavy(self):
        """Test recommendation for memory-heavy workload."""
        recommender = InstanceRecommender(headroom=0.20)
        instance, cpus, memory = recommender.recommend_instance(2.0, 12.0)

        # With 20% headroom: ceil(2.0 * 1.2) = 3 CPUs, ceil(12.0 * 1.2) = 15 GiB
        assert cpus == 3
        assert memory == 15.0
        # c.xlarge has 4 CPUs, 8 GiB - not enough memory
        # m.xlarge has 4 CPUs, 16 GiB - fits!
        assert instance == 'omics.m.xlarge'

    def test_recommend_instance_cpu_heavy(self):
        """Test recommendation for CPU-heavy workload."""
        recommender = InstanceRecommender(headroom=0.20)
        instance, cpus, memory = recommender.recommend_instance(30.0, 32.0)

        # With 20% headroom: ceil(30.0 * 1.2) = 36 CPUs, ceil(32.0 * 1.2) = 39 GiB
        assert cpus == 36
        assert memory == 39.0
        # Need at least 36 CPUs - 12xlarge has 48 CPUs
        # c.12xlarge has 48 CPUs, 96 GiB - fits!
        assert instance == 'omics.c.12xlarge'

    def test_recommend_instance_zero_usage(self):
        """Test recommendation with zero usage."""
        recommender = InstanceRecommender(headroom=0.20)
        instance, cpus, memory = recommender.recommend_instance(0.0, 0.0)

        # Should use minimums: 1 CPU, 1 GiB
        assert cpus == 1
        assert memory == 1.0
        # Smallest instance that fits
        assert instance == 'omics.c.large'

    def test_recommend_instance_custom_headroom(self):
        """Test recommendation with custom headroom."""
        recommender = InstanceRecommender(headroom=0.50)  # 50% headroom
        instance, cpus, memory = recommender.recommend_instance(2.0, 4.0)

        # With 50% headroom: ceil(2.0 * 1.5) = 3 CPUs, ceil(4.0 * 1.5) = 6 GiB
        assert cpus == 3
        assert memory == 6.0

    def test_recommend_instance_fallback_to_largest(self):
        """Test fallback to largest instance for extreme requirements."""
        recommender = InstanceRecommender(headroom=0.20)
        instance, cpus, memory = recommender.recommend_instance(200.0, 2000.0)

        # Requirements exceed all available instances
        assert instance == 'omics.r.48xlarge'

    def test_negative_headroom_raises_error(self):
        """Test that negative headroom raises ValueError."""
        with pytest.raises(ValueError, match='Headroom must be non-negative, got -0.1'):
            InstanceRecommender(headroom=-0.1)

    def test_negative_headroom_large_value_raises_error(self):
        """Test that large negative headroom raises ValueError."""
        with pytest.raises(ValueError, match='Headroom must be non-negative, got -1.0'):
            InstanceRecommender(headroom=-1.0)

    def test_zero_headroom_allowed(self):
        """Test that zero headroom is allowed."""
        recommender = InstanceRecommender(headroom=0.0)
        instance, cpus, memory = recommender.recommend_instance(2.0, 4.0)

        # With 0% headroom: ceil(2.0 * 1.0) = 2 CPUs, ceil(4.0 * 1.0) = 4 GiB
        assert cpus == 2
        assert memory == 4.0
        assert instance == 'omics.c.large'


class TestInstanceRecommenderCalculateSavings:
    """Test cases for calculate_savings method."""

    def setup_method(self):
        """Clear pricing cache before each test."""
        PricingCache.clear_cache()

    def teardown_method(self):
        """Clear pricing cache after each test."""
        PricingCache.clear_cache()

    def test_calculate_savings_basic(self):
        """Test basic savings calculation."""
        with patch.object(PricingCache, 'get_price', return_value=0.50):
            recommender = InstanceRecommender()
            savings = recommender.calculate_savings(
                current_cost=1.0,
                recommended_instance='omics.c.large',
                running_seconds=3600,  # 1 hour
                region='us-east-1',
            )
            # Optimized cost: $0.50/hour * 1 hour = $0.50
            # Savings: $1.00 - $0.50 = $0.50
            assert savings == pytest.approx(0.50)

    def test_calculate_savings_no_savings(self):
        """Test when recommended instance costs more."""
        with patch.object(PricingCache, 'get_price', return_value=2.0):
            recommender = InstanceRecommender()
            savings = recommender.calculate_savings(
                current_cost=1.0,
                recommended_instance='omics.r.xlarge',
                running_seconds=3600,
                region='us-east-1',
            )
            # Optimized cost: $2.00/hour * 1 hour = $2.00
            # Savings: max(0, $1.00 - $2.00) = $0.00
            assert savings == 0.0

    def test_calculate_savings_minimum_billing(self):
        """Test savings calculation with minimum billing time."""
        with patch.object(PricingCache, 'get_price', return_value=1.0):
            recommender = InstanceRecommender()
            savings = recommender.calculate_savings(
                current_cost=0.10,  # Current cost for short task
                recommended_instance='omics.c.large',
                running_seconds=30,  # 30 seconds, will be billed as 60
                region='us-east-1',
            )
            # Optimized cost: $1.00/hour * (60/3600) hours = $0.0167
            # Savings: max(0, $0.10 - $0.0167) = $0.0833
            expected_optimized = 1.0 * (60 / 3600)
            expected_savings = max(0, 0.10 - expected_optimized)
            assert savings == pytest.approx(expected_savings)

    def test_calculate_savings_pricing_unavailable(self):
        """Test when pricing is unavailable."""
        with patch.object(PricingCache, 'get_price', return_value=None):
            recommender = InstanceRecommender()
            savings = recommender.calculate_savings(
                current_cost=1.0,
                recommended_instance='omics.c.large',
                running_seconds=3600,
                region='us-east-1',
            )
            assert savings is None


class TestInstanceRecommenderHighPrioritySaving:
    """Test cases for is_high_priority_saving method."""

    def test_high_priority_above_threshold(self):
        """Test when savings exceed 10% threshold."""
        recommender = InstanceRecommender()
        # 15% savings should be high priority
        assert recommender.is_high_priority_saving(100.0, 15.0) is True

    def test_high_priority_at_threshold(self):
        """Test when savings exactly at 10% threshold."""
        recommender = InstanceRecommender()
        # Exactly 10% should NOT be high priority (> not >=)
        assert recommender.is_high_priority_saving(100.0, 10.0) is False

    def test_high_priority_below_threshold(self):
        """Test when savings below 10% threshold."""
        recommender = InstanceRecommender()
        # 5% savings should not be high priority
        assert recommender.is_high_priority_saving(100.0, 5.0) is False

    def test_high_priority_zero_cost(self):
        """Test with zero estimated cost."""
        recommender = InstanceRecommender()
        assert recommender.is_high_priority_saving(0.0, 10.0) is False

    def test_high_priority_negative_cost(self):
        """Test with negative estimated cost."""
        recommender = InstanceRecommender()
        assert recommender.is_high_priority_saving(-10.0, 5.0) is False


# Property-Based Tests using Hypothesis


class TestInstanceRecommenderPropertyBased:
    """Property-based tests for InstanceRecommender using Hypothesis."""

    @given(
        cpus_maximum=st.floats(min_value=0.0, max_value=150.0, allow_nan=False),
        memory_maximum_gib=st.floats(min_value=0.0, max_value=1500.0, allow_nan=False),
        headroom=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def test_property_recommended_instance_fits_required_resources(
        self, cpus_maximum: float, memory_maximum_gib: float, headroom: float
    ):
        """Property 3: Recommended Instance Fits Required Resources.

        For any task with maximum observed CPU usage C and memory usage M,
        and headroom H, the recommended instance type SHALL have at least
        ceil(C * (1 + H)) CPUs and ceil(M * (1 + H)) GiB memory.

        Note: When requirements exceed the largest available instance (omics.r.48xlarge
        with 192 CPUs and 1536 GiB), the system falls back to that instance. This test
        filters out such edge cases to focus on the core property.

        **Validates: Requirements 3.1, 3.3, 6.5**
        **Feature: run-analyzer-enhancement, Property 3: Recommended Instance Fits Required Resources**
        """
        # Calculate expected required resources
        expected_cpus = max(1, math.ceil(cpus_maximum * (1.0 + headroom)))
        expected_memory = max(1, math.ceil(memory_maximum_gib * (1.0 + headroom)))

        # Skip cases where requirements exceed the largest instance
        # omics.r.48xlarge has 192 CPUs and 1536 GiB (192 * 8)
        max_cpus = 192
        max_memory = 1536
        assume(expected_cpus <= max_cpus and expected_memory <= max_memory)

        recommender = InstanceRecommender(headroom=headroom)
        instance_type, required_cpus, required_memory = recommender.recommend_instance(
            cpus_maximum, memory_maximum_gib
        )

        # Property: returned required values match expected calculation
        assert required_cpus == expected_cpus
        assert required_memory == float(expected_memory)

        # Property: recommended instance has enough resources
        instance_cpus, instance_memory = PricingCache.get_instance_specs(instance_type)

        # The instance must have at least the required resources
        assert instance_cpus >= required_cpus, (
            f'Instance {instance_type} has {instance_cpus} CPUs but requires {required_cpus}'
        )
        assert instance_memory >= required_memory, (
            f'Instance {instance_type} has {instance_memory} GiB but requires {required_memory}'
        )

    @given(
        estimated_cost=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
        minimum_cost=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
    )
    def test_property_savings_calculation_correctness(
        self, estimated_cost: float, minimum_cost: float
    ):
        """Property 4: Savings Calculation Correctness.

        For any task with estimated cost E and minimum cost M,
        the potential savings SHALL equal max(0, E - M).

        **Validates: Requirements 4.1, 4.2**
        **Feature: run-analyzer-enhancement, Property 4: Savings Calculation Correctness**
        """
        # We test the savings calculation by mocking the pricing API
        # to return a price that results in the minimum_cost
        recommender = InstanceRecommender()

        # Calculate what price would give us the minimum_cost for 1 hour
        running_seconds = 3600.0  # 1 hour for simplicity
        price_per_hour = minimum_cost  # Price that gives minimum_cost for 1 hour

        with patch.object(PricingCache, 'get_price', return_value=price_per_hour):
            savings = recommender.calculate_savings(
                current_cost=estimated_cost,
                recommended_instance='omics.c.large',
                running_seconds=running_seconds,
                region='us-east-1',
            )

            # Property: savings equals max(0, estimated_cost - minimum_cost)
            expected_savings = max(0.0, estimated_cost - minimum_cost)
            assert savings is not None
            assert savings == pytest.approx(expected_savings, rel=1e-9)

            # Property: savings is always non-negative
            assert savings >= 0.0

    @given(
        estimated_cost=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False),
        savings_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def test_property_high_priority_savings_threshold(
        self, estimated_cost: float, savings_ratio: float
    ):
        """Property 5: High-Priority Savings Threshold.

        For any task with estimated cost E and potential savings S,
        the task SHALL be flagged as high-priority if and only if S > 0.1 * E.

        **Validates: Requirements 4.4**
        **Feature: run-analyzer-enhancement, Property 5: High-Priority Savings Threshold**
        """
        recommender = InstanceRecommender()

        # Calculate potential savings as a ratio of estimated cost
        potential_savings = estimated_cost * savings_ratio

        is_high_priority = recommender.is_high_priority_saving(
            estimated_cost=estimated_cost,
            potential_savings=potential_savings,
        )

        # Property: high priority if and only if savings > 10% of estimated cost
        threshold = InstanceRecommender.HIGH_PRIORITY_SAVINGS_THRESHOLD
        expected_high_priority = potential_savings > (threshold * estimated_cost)

        assert is_high_priority == expected_high_priority, (
            f'Expected high_priority={expected_high_priority} for '
            f'savings={potential_savings}, cost={estimated_cost}, '
            f'threshold={threshold * estimated_cost}'
        )
