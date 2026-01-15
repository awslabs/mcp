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

"""Instance sizing recommendations based on observed resource usage."""

import math
from .pricing_cache import PricingCache
from typing import Optional


class InstanceRecommender:
    """Recommends optimal instance types based on resource usage.

    This class analyzes observed CPU and memory usage to recommend
    the smallest instance type that accommodates the workload with headroom.

    The recommendation algorithm:
    1. Applies configurable headroom (default 20%) to observed usage
    2. Iterates through instance sizes from smallest to largest
    3. For each size, tries instance families in order: c (compute), m (general), r (memory)
    4. Returns the first instance that fits the required resources

    Attributes:
        SIZES: Instance sizes ordered from smallest to largest
        FAMILIES: Instance families ordered by memory ratio (lowest to highest)
        HIGH_PRIORITY_SAVINGS_THRESHOLD: Threshold for flagging high-priority savings (10%)
    """

    # Ordered by size for finding minimum
    SIZES = [
        'large',
        'xlarge',
        '2xlarge',
        '4xlarge',
        '8xlarge',
        '12xlarge',
        '16xlarge',
        '24xlarge',
        '32xlarge',
        '48xlarge',
    ]

    # Ordered by memory ratio (lowest to highest)
    FAMILIES = ['c', 'm', 'r']

    # Threshold for high-priority savings (10% of original cost)
    HIGH_PRIORITY_SAVINGS_THRESHOLD = 0.10

    # Minimum billable time in seconds (same as CostAnalyzer)
    MINIMUM_BILLABLE_SECONDS = 60

    def __init__(self, headroom: float = 0.20):
        """Initialize with headroom percentage.

        Args:
            headroom: Additional capacity buffer as a decimal (default 0.20 = 20%)

        Raises:
            ValueError: If headroom is negative
        """
        if headroom < 0:
            raise ValueError(f'Headroom must be non-negative, got {headroom}')
        self.headroom = headroom

    def recommend_instance(
        self,
        cpus_maximum: float,
        memory_maximum_gib: float,
    ) -> tuple[str, int, float]:
        """Find smallest instance type that fits observed usage plus headroom.

        The algorithm applies headroom to the observed usage, then finds the
        smallest instance type that can accommodate the required resources.
        Instance families are tried in order: c (compute), m (general), r (memory).

        Args:
            cpus_maximum: Maximum observed CPU usage
            memory_maximum_gib: Maximum observed memory usage in GiB

        Returns:
            Tuple of (instance_type, recommended_cpus, recommended_memory_gib)
            where recommended_cpus and recommended_memory_gib are the required
            resources after applying headroom (ceiling values).
        """
        # Apply headroom and calculate required resources
        cpus_required = math.ceil(cpus_maximum * (1.0 + self.headroom))
        memory_required = math.ceil(memory_maximum_gib * (1.0 + self.headroom))

        # Ensure minimums (at least 1 CPU and 1 GiB memory)
        cpus_required = max(1, cpus_required)
        memory_required = max(1, memory_required)

        # Iterate through sizes from smallest to largest
        for size in self.SIZES:
            cpu_count = PricingCache.SIZE_TO_CPUS[size]

            # Skip if this size doesn't have enough CPUs
            if cpu_count < cpus_required:
                continue

            # Try each family in order (c, m, r - by memory ratio)
            for family in self.FAMILIES:
                memory_ratio = PricingCache.FAMILY_MEMORY_RATIO[family]
                memory_count = cpu_count * memory_ratio

                # Check if this instance fits the memory requirement
                if memory_count >= memory_required:
                    instance_type = f'omics.{family}.{size}'
                    return instance_type, cpus_required, float(memory_required)

        # Fallback to largest instance if nothing else fits
        return 'omics.r.48xlarge', cpus_required, float(memory_required)

    def calculate_savings(
        self,
        current_cost: float,
        recommended_instance: str,
        running_seconds: float,
        region: str,
    ) -> Optional[float]:
        """Calculate potential savings from using recommended instance.

        Computes the cost difference between the current cost and the
        optimized cost using the recommended instance type.

        Args:
            current_cost: Current estimated cost in USD
            recommended_instance: Recommended instance type (e.g., "omics.m.xlarge")
            running_seconds: Task running time in seconds
            region: AWS region for pricing lookup

        Returns:
            Potential savings in USD (always >= 0), or None if pricing unavailable
        """
        recommended_price = PricingCache.get_price(recommended_instance, region)
        if recommended_price is None:
            return None

        # Apply minimum billable time (same as CostAnalyzer)
        billable_seconds = max(self.MINIMUM_BILLABLE_SECONDS, running_seconds)
        billable_hours = billable_seconds / 3600.0

        optimized_cost = recommended_price * billable_hours

        # Savings is always non-negative
        return max(0.0, current_cost - optimized_cost)

    def is_high_priority_saving(
        self,
        estimated_cost: float,
        potential_savings: float,
    ) -> bool:
        """Determine if savings exceed the high-priority threshold.

        A task is flagged as high-priority for optimization if the potential
        savings exceed 10% of the original estimated cost.

        Args:
            estimated_cost: Original estimated cost in USD
            potential_savings: Potential savings in USD

        Returns:
            True if savings exceed 10% of estimated cost, False otherwise
        """
        if estimated_cost <= 0:
            return False

        return potential_savings > (self.HIGH_PRIORITY_SAVINGS_THRESHOLD * estimated_cost)
