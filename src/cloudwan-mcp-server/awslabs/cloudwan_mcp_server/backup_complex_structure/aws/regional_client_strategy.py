"""
Regional Client Strategy for AWS CloudWAN Operations.

This module provides optimized strategies for multi-region AWS client management with:
- Region-specific optimization rules
- Health tracking and failover capabilities
- Circuit breaker integration
- CloudWAN-specific service patterns
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable, TypeVar
import random
import functools

from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

T = TypeVar("T")


class RegionHealth(Enum):
    """Health status for AWS regions."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class RegionPreference(Enum):
    """Region preference modes for operation routing."""

    NEAREST = "nearest"  # Route to nearest region (lowest latency)
    BALANCED = "balanced"  # Balance across healthy regions
    PRIMARY_PREFERRED = "primary_preferred"  # Prefer primary, fallback to others
    SPECIFIC = "specific"  # Use specific regions for specific operations


class RegionalClientStrategy:
    """
    Strategy for optimizing multi-region AWS client operations.

    Features:
    - Region health tracking and scoring
    - Smart region selection based on service characteristics
    - Automatic fallback and retry logic
    - CloudWAN-specific regional optimizations
    - Circuit breaker integration
    """

    def __init__(
        self,
        regions: List[str],
        primary_region: Optional[str] = None,
        preference_mode: RegionPreference = RegionPreference.BALANCED,
        circuit_breaker_manager=None,
    ):
        """
        Initialize regional client strategy.

        Args:
            regions: List of AWS regions to use
            primary_region: Primary region (defaults to first region in list)
            preference_mode: Strategy for region selection
            circuit_breaker_manager: Optional circuit breaker manager
        """
        self.regions = regions.copy()
        self.primary_region = primary_region or (regions[0] if regions else "us-east-1")
        self.preference_mode = preference_mode
        self.circuit_breaker_manager = circuit_breaker_manager

        # Region health tracking
        self._region_health: Dict[str, RegionHealth] = {
            region: RegionHealth.HEALTHY for region in self.regions
        }
        self._health_metrics: Dict[str, Dict[str, Any]] = {
            region: {
                "last_success": datetime.now(timezone.utc),
                "last_failure": None,
                "latency_ms": {},  # service -> [recent_latencies]
                "error_count": 0,
                "success_count": 0,
                "throttling_count": 0,
            }
            for region in self.regions
        }

        # Region-specific service recommendations
        # CloudWAN/NetworkManager is only available in us-west-2
        self._service_region_requirements = {
            "networkmanager": ["us-west-2"],
        }

        # Latest service endpoint latencies
        self._service_latencies: Dict[str, Dict[str, float]] = (
            {}
        )  # service -> {region -> latency_ms}

        logger.info(
            f"RegionalClientStrategy initialized with {len(regions)} regions, "
            f"primary: {self.primary_region}, mode: {preference_mode.value}"
        )

    def update_region_health(
        self,
        region: str,
        service: str,
        is_success: bool,
        latency_ms: float,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Update health metrics for a region based on operation results.

        Args:
            region: AWS region
            service: AWS service name
            is_success: Whether operation was successful
            latency_ms: Operation latency in milliseconds
            error_type: Type of error if operation failed
        """
        if region not in self._region_health:
            logger.warning(f"Attempted to update health for unknown region: {region}")
            return

        current_time = datetime.now(timezone.utc)
        metrics = self._health_metrics[region]

        # Update latency tracking
        if service not in metrics["latency_ms"]:
            metrics["latency_ms"][service] = []

        latencies = metrics["latency_ms"][service]
        latencies.append(latency_ms)
        # Keep only last 100 latency samples
        if len(latencies) > 100:
            metrics["latency_ms"][service] = latencies[-100:]

        # Update success/failure metrics
        if is_success:
            metrics["last_success"] = current_time
            metrics["success_count"] += 1
        else:
            metrics["last_failure"] = current_time
            metrics["error_count"] += 1
            if error_type == "ThrottlingException":
                metrics["throttling_count"] += 1

        # Update global service latency tracking
        if service not in self._service_latencies:
            self._service_latencies[service] = {}
        self._service_latencies[service][region] = latency_ms

        # Evaluate region health based on metrics
        self._evaluate_region_health(region)

    def _evaluate_region_health(self, region: str) -> None:
        """
        Evaluate and update region health based on collected metrics.

        Args:
            region: AWS region to evaluate
        """
        metrics = self._health_metrics[region]
        current_time = datetime.now(timezone.utc)

        # Check for recent failures
        if metrics["last_failure"]:
            failure_age_seconds = (current_time - metrics["last_failure"]).total_seconds()
            if failure_age_seconds < 60:  # Within last minute
                # High error rate in last minute suggests degradation
                if metrics["error_count"] > 5:
                    self._region_health[region] = RegionHealth.DEGRADED
                    return

        # Check for high throttling rate
        if metrics["throttling_count"] > 10:
            self._region_health[region] = RegionHealth.DEGRADED
            return

        # Calculate success rate
        total_ops = metrics["success_count"] + metrics["error_count"]
        if total_ops > 20:  # Enough data for calculation
            success_rate = metrics["success_count"] / total_ops
            if success_rate < 0.7:  # Less than 70% success rate
                self._region_health[region] = RegionHealth.DEGRADED
                return
            elif success_rate > 0.95:  # Over 95% success rate
                self._region_health[region] = RegionHealth.HEALTHY
                return

        # Default to HEALTHY if no negative indicators
        if self._region_health[region] != RegionHealth.UNAVAILABLE:
            self._region_health[region] = RegionHealth.HEALTHY

    def select_region(
        self, service: str, operation: str = None, required_regions: List[str] = None
    ) -> str:
        """
        Select optimal region for operation based on strategy and health.

        Args:
            service: AWS service name
            operation: Optional operation name for operation-specific selection
            required_regions: Optional list of required regions

        Returns:
            Selected AWS region
        """
        # Check if service has region requirements (e.g., NetworkManager)
        if service in self._service_region_requirements:
            required = self._service_region_requirements[service]
            # CloudWAN special case
            if service == "networkmanager":
                return "us-west-2"  # NetworkManager is only available in us-west-2

            # For other services with requirements, find first healthy region
            for region in required:
                if (
                    region in self._region_health
                    and self._region_health[region] != RegionHealth.UNAVAILABLE
                ):
                    return region

            # If no healthy required regions, return first required region
            return required[0]

        # Handle explicitly required regions
        if required_regions:
            for region in required_regions:
                if (
                    region in self._region_health
                    and self._region_health[region] != RegionHealth.UNAVAILABLE
                ):
                    return region
            # If no healthy required regions, return first required region
            return required_regions[0]

        # Apply region preference strategy
        if self.preference_mode == RegionPreference.PRIMARY_PREFERRED:
            # Check if primary region is healthy
            if self._region_health[self.primary_region] != RegionHealth.UNAVAILABLE:
                return self.primary_region

            # Fall back to first healthy region
            for region in self.regions:
                if self._region_health[region] != RegionHealth.UNAVAILABLE:
                    return region
            # Last resort - return primary even if unhealthy
            return self.primary_region

        elif self.preference_mode == RegionPreference.BALANCED:
            # Get all healthy regions
            healthy_regions = [
                region
                for region in self.regions
                if self._region_health[region] != RegionHealth.UNAVAILABLE
            ]

            if not healthy_regions:
                # If no healthy regions, default to primary
                return self.primary_region

            # Weighted selection based on health
            weights = []
            for region in healthy_regions:
                if self._region_health[region] == RegionHealth.HEALTHY:
                    weights.append(2.0)  # Twice as likely to select healthy regions
                else:
                    weights.append(1.0)  # Less likely to select degraded regions

            # Normalize weights
            total = sum(weights)
            normalized_weights = [w / total for w in weights]

            # Select region based on weights
            return random.choices(healthy_regions, weights=normalized_weights, k=1)[0]

        elif self.preference_mode == RegionPreference.NEAREST:
            # Use service latency data if available
            if service in self._service_latencies and self._service_latencies[service]:
                # Sort regions by latency
                regions_by_latency = sorted(
                    self._service_latencies[service].items(),
                    key=lambda x: x[1],  # Sort by latency value
                )

                # Return lowest latency healthy region
                for region, _ in regions_by_latency:
                    if (
                        region in self._region_health
                        and self._region_health[region] != RegionHealth.UNAVAILABLE
                    ):
                        return region

            # Fallback to primary if no latency data
            return self.primary_region

        # Default - use primary region
        return self.primary_region

    def get_region_health(self, region: str) -> RegionHealth:
        """Get current health status for a region."""
        if region in self._region_health:
            return self._region_health[region]
        return RegionHealth.UNAVAILABLE

    def set_region_unavailable(self, region: str) -> None:
        """Explicitly mark a region as unavailable."""
        if region in self._region_health:
            self._region_health[region] = RegionHealth.UNAVAILABLE
            logger.warning(f"Region {region} marked as UNAVAILABLE")

    def reset_region_health(self, region: str) -> None:
        """Reset health status for a region."""
        if region in self._region_health:
            self._region_health[region] = RegionHealth.HEALTHY
            # Reset metrics
            self._health_metrics[region]["error_count"] = 0
            self._health_metrics[region]["throttling_count"] = 0
            logger.info(f"Region {region} health reset to HEALTHY")

    def get_all_healthy_regions(self) -> List[str]:
        """Get list of all healthy regions."""
        return [
            region
            for region, health in self._region_health.items()
            if health == RegionHealth.HEALTHY
        ]

    def get_all_degraded_regions(self) -> List[str]:
        """Get list of all degraded regions."""
        return [
            region
            for region, health in self._region_health.items()
            if health == RegionHealth.DEGRADED
        ]

    def get_region_metrics(self, region: str) -> Dict[str, Any]:
        """Get detailed metrics for a region."""
        if region in self._health_metrics:
            metrics = self._health_metrics[region].copy()

            # Calculate average latencies per service
            avg_latencies = {}
            for service, latencies in metrics["latency_ms"].items():
                if latencies:
                    avg_latencies[service] = sum(latencies) / len(latencies)
                else:
                    avg_latencies[service] = 0.0

            metrics["avg_latency_ms"] = avg_latencies
            metrics["health"] = self._region_health[region].value

            return metrics

        return {}

    def get_all_region_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all regions."""
        return {region: self.get_region_metrics(region) for region in self.regions}

    async def execute_in_optimal_region(
        self,
        service: str,
        operation: str,
        client_factory: Callable[[str], Any],
        operation_kwargs: Dict[str, Any] = None,
        required_regions: List[str] = None,
        max_retries: int = 2,
    ) -> Tuple[Any, str]:
        """
        Execute an AWS operation in the optimal region with automatic retry.

        Args:
            service: AWS service name
            operation: Operation name
            client_factory: Function that creates a client given a region
            operation_kwargs: Operation arguments
            required_regions: Optional list of required regions
            max_retries: Maximum number of retries

        Returns:
            Tuple of (operation result, region used)

        Raises:
            Exception: If operation fails in all attempted regions
        """
        operation_kwargs = operation_kwargs or {}
        attempts = 0
        tried_regions = set()
        last_exception = None

        while attempts <= max_retries:
            # Select region (avoiding previously tried regions if possible)
            available_regions = [r for r in self.regions if r not in tried_regions]

            if not available_regions:
                # If all regions tried, reset and try primary again
                region = self.primary_region
            else:
                # Use our region selection strategy on untried regions
                if required_regions:
                    available_required = [r for r in required_regions if r not in tried_regions]
                    if available_required:
                        region = self.select_region(service, operation, available_required)
                    else:
                        region = self.select_region(service, operation, required_regions)
                else:
                    region = self.select_region(service, operation)

            tried_regions.add(region)
            attempts += 1

            try:
                # Create client and prepare circuit breaker if available
                client = client_factory(region)
                start_time = time.time()
                circuit_breaker = None

                # Setup circuit breaker if available
                if self.circuit_breaker_manager:
                    circuit_breaker = self.circuit_breaker_manager.get_or_create_circuit_breaker(
                        service=service, operation=operation, region=region
                    )

                    # Check if circuit is open
                    if not circuit_breaker.check_circuit(service, region):
                        logger.warning(
                            f"Circuit breaker open for {service}.{operation} in {region}"
                        )
                        # Skip this region and try another
                        continue

                # Execute operation
                client_operation = getattr(client, operation)
                result = await client_operation(**operation_kwargs)

                # Record metrics
                latency_ms = (time.time() - start_time) * 1000
                self.update_region_health(region, service, True, latency_ms)

                # Record circuit breaker success
                if circuit_breaker:
                    circuit_breaker.record_success(service, region)

                # Return successful result with region used
                return result, region

            except Exception as e:
                last_exception = e
                latency_ms = (time.time() - start_time) * 1000

                # Classify error
                error_type = "Unknown"
                if isinstance(e, ClientError):
                    error_code = e.response.get("Error", {}).get("Code", "")
                    error_type = error_code

                # Update health metrics
                self.update_region_health(region, service, False, latency_ms, error_type=error_type)

                # Record circuit breaker failure
                if circuit_breaker:
                    circuit_breaker.record_failure(service, region)

                logger.warning(f"Operation {service}.{operation} failed in {region}: {str(e)}")

                # Continue to try other regions if available
                if attempts <= max_retries:
                    continue

                # If we've exhausted retries, raise the last exception
                raise last_exception

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise Exception(
            f"Failed to execute {service}.{operation} in any region after {attempts} attempts"
        )

    def execute_with_fallback_sync(
        self,
        service: str,
        operation: str,
        client_factory: Callable[[str], Any],
        operation_kwargs: Dict[str, Any] = None,
        required_regions: List[str] = None,
        max_retries: int = 2,
    ) -> Tuple[Any, str]:
        """
        Synchronous version of execute_in_optimal_region.

        Args:
            service: AWS service name
            operation: Operation name
            client_factory: Function that creates a client given a region
            operation_kwargs: Operation arguments
            required_regions: Optional list of required regions
            max_retries: Maximum number of retries

        Returns:
            Tuple of (operation result, region used)

        Raises:
            Exception: If operation fails in all attempted regions
        """
        operation_kwargs = operation_kwargs or {}
        attempts = 0
        tried_regions = set()
        last_exception = None

        while attempts <= max_retries:
            # Select region (avoiding previously tried regions if possible)
            available_regions = [r for r in self.regions if r not in tried_regions]

            if not available_regions:
                # If all regions tried, reset and try primary again
                region = self.primary_region
            else:
                # Use our region selection strategy on untried regions
                if required_regions:
                    available_required = [r for r in required_regions if r not in tried_regions]
                    if available_required:
                        region = self.select_region(service, operation, available_required)
                    else:
                        region = self.select_region(service, operation, required_regions)
                else:
                    region = self.select_region(service, operation)

            tried_regions.add(region)
            attempts += 1

            try:
                # Create client and prepare circuit breaker if available
                client = client_factory(region)
                start_time = time.time()
                circuit_breaker = None

                # Setup circuit breaker if available
                if self.circuit_breaker_manager:
                    circuit_breaker = self.circuit_breaker_manager.get_or_create_circuit_breaker(
                        service=service, operation=operation, region=region
                    )

                    # Check if circuit is open
                    if not circuit_breaker.check_circuit(service, region):
                        logger.warning(
                            f"Circuit breaker open for {service}.{operation} in {region}"
                        )
                        # Skip this region and try another
                        continue

                # Execute operation
                client_operation = getattr(client, operation)
                result = client_operation(**operation_kwargs)

                # Record metrics
                latency_ms = (time.time() - start_time) * 1000
                self.update_region_health(region, service, True, latency_ms)

                # Record circuit breaker success
                if circuit_breaker:
                    circuit_breaker.record_success(service, region)

                # Return successful result with region used
                return result, region

            except Exception as e:
                last_exception = e
                latency_ms = (time.time() - start_time) * 1000

                # Classify error
                error_type = "Unknown"
                if isinstance(e, ClientError):
                    error_code = e.response.get("Error", {}).get("Code", "")
                    error_type = error_code

                # Update health metrics
                self.update_region_health(region, service, False, latency_ms, error_type=error_type)

                # Record circuit breaker failure
                if circuit_breaker:
                    circuit_breaker.record_failure(service, region)

                logger.warning(f"Operation {service}.{operation} failed in {region}: {str(e)}")

                # Continue to try other regions if available
                if attempts <= max_retries:
                    continue

                # If we've exhausted retries, raise the last exception
                raise last_exception

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise Exception(
            f"Failed to execute {service}.{operation} in any region after {attempts} attempts"
        )

    def with_regional_fallback(
        self,
        service: str,
        client_factory: Callable[[str], Any],
        max_retries: int = 2,
        required_regions: List[str] = None,
    ) -> Callable:
        """
        Decorator for functions that need regional fallback.

        Args:
            service: AWS service name
            client_factory: Function that creates a client given a region
            max_retries: Maximum number of retries
            required_regions: Optional list of required regions

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.execute_in_optimal_region(
                    service=service,
                    operation=func.__name__,
                    client_factory=client_factory,
                    operation_kwargs=kwargs,
                    required_regions=required_regions,
                    max_retries=max_retries,
                )

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.execute_with_fallback_sync(
                    service=service,
                    operation=func.__name__,
                    client_factory=client_factory,
                    operation_kwargs=kwargs,
                    required_regions=required_regions,
                    max_retries=max_retries,
                )

            # Use appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator
