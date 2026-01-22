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

"""Cost calculation logic for HealthOmics tasks and runs."""

import math
from .pricing_cache import PricingCache
from typing import Optional


class CostAnalyzer:
    """Calculates costs for HealthOmics tasks and runs.

    This class handles cost estimation using AWS Pricing API data,
    including minimum billable time and storage cost calculations.

    Attributes:
        MINIMUM_BILLABLE_SECONDS: Minimum billable time for tasks (60 seconds)
        STATIC_STORAGE_MIN_GIB: Minimum static storage allocation (1200 GiB)
        STATIC_STORAGE_INCREMENT_GIB: Static storage allocation increment (2400 GiB)
    """

    MINIMUM_BILLABLE_SECONDS = 60
    STATIC_STORAGE_MIN_GIB = 1200
    STATIC_STORAGE_INCREMENT_GIB = 2400

    def __init__(self, region: str):
        """Initialize CostAnalyzer.

        Args:
            region: AWS region for pricing lookups
        """
        self.region = region

    def calculate_task_cost(
        self,
        instance_type: str,
        running_seconds: float,
    ) -> Optional[float]:
        """Calculate cost for a single task.

        Uses the formula: billable_hours * price_per_hour
        where billable_hours = max(60, running_seconds) / 3600

        Args:
            instance_type: HealthOmics instance type (e.g., "omics.m.xlarge")
            running_seconds: Task running time in seconds

        Returns:
            Estimated cost in USD, or None if pricing unavailable
        """
        price_per_hour = PricingCache.get_price(instance_type, self.region)
        if price_per_hour is None:
            return None

        # Apply minimum billable time (60 seconds)
        billable_seconds = max(self.MINIMUM_BILLABLE_SECONDS, running_seconds)
        billable_hours = billable_seconds / 3600.0

        return price_per_hour * billable_hours

    def calculate_storage_cost(
        self,
        storage_type: str,
        storage_reserved_gib: float,
        storage_average_gib: float,
        running_seconds: float,
    ) -> Optional[float]:
        """Calculate storage cost based on type.

        For STATIC storage: uses allocated storage (rounded up to increment)
        For DYNAMIC storage: uses average storage usage

        Args:
            storage_type: 'STATIC' or 'DYNAMIC'
            storage_reserved_gib: Reserved storage capacity in GiB
            storage_average_gib: Average storage usage in GiB
            running_seconds: Run duration in seconds

        Returns:
            Storage cost in USD, or None if pricing unavailable
        """
        if storage_type == 'STATIC':
            allocated = self._get_static_storage_allocation(storage_reserved_gib)
            resource_type = 'Run Storage'
        else:
            allocated = storage_average_gib
            resource_type = 'Dynamic Run Storage'

        price_per_gib_hour = PricingCache.get_price(resource_type, self.region)
        if price_per_gib_hour is None:
            return None

        gib_hours = allocated * (running_seconds / 3600.0)
        return price_per_gib_hour * gib_hours

    def _get_static_storage_allocation(self, capacity: float) -> float:
        """Calculate actual static storage allocation.

        Static storage is allocated with:
        - Minimum of 1200 GiB
        - Increments of 2400 GiB above the minimum

        Args:
            capacity: Requested storage capacity in GiB

        Returns:
            Actual allocated storage in GiB (rounded up to increment)
        """
        if capacity <= self.STATIC_STORAGE_MIN_GIB:
            return float(self.STATIC_STORAGE_MIN_GIB)

        # Round up to the nearest increment of 2400 GiB
        return float(
            math.ceil(capacity / self.STATIC_STORAGE_INCREMENT_GIB)
            * self.STATIC_STORAGE_INCREMENT_GIB
        )
