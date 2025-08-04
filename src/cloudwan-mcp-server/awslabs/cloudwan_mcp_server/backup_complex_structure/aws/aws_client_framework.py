"""
AWS Client Management Framework for CloudWAN MCP.

This module provides an integrated framework for AWS client management with:
- Multi-region operation support
- Specialized CloudWAN client handling
- Efficient credential management and session pooling
- Circuit breaker pattern for resilience
- Performance optimization for AWS operations
"""

import logging
from typing import Any, Dict, List, Optional

from .regional_client_strategy import (
    RegionHealth,
)
from .client_registry import ClientRegistry, ClientType
from .optimized_multi_region_executor import (
    OptimizedMultiRegionExecutor,
    ExecutionMode,
    MultiRegionResult,
)
from .circuit_breaker import (
    CircuitBreakerManager,
)
from .redis_cache import RedisCache
from .session_factory import SessionPoolConfig
from .thread_pool_manager import ThreadPoolConfig

logger = logging.getLogger(__name__)


class AWSClientFramework:
    """
    Integrated AWS Client Management Framework for CloudWAN MCP.

    This class provides a unified interface to all client management components:
    - Client Registry for standardized client creation
    - Regional Client Strategy for region health tracking and selection
    - Network Manager Client Factory for CloudWAN operations
    - Multi-Region Executor for parallel operations
    - Circuit Breaker Manager for resilience

    Features:
    - Centralized AWS client management
    - Multi-region operation orchestration
    - CloudWAN-specific optimizations
    - Performance tracking and optimization
    - Resilience patterns with circuit breakers
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        regions: Optional[List[str]] = None,
        primary_region: Optional[str] = None,
        enable_circuit_breaker: bool = True,
        enable_redis_cache: bool = False,
        redis_config: Optional[Dict[str, Any]] = None,
        session_config: Optional[SessionPoolConfig] = None,
        thread_config: Optional[ThreadPoolConfig] = None,
        max_concurrency: int = 5,
        default_executor_mode: ExecutionMode = ExecutionMode.PARALLEL,
    ):
        """
        Initialize AWS Client Management Framework.

        Args:
            profile: AWS profile name
            regions: List of AWS regions
            primary_region: Primary region (defaults to first region in list)
            enable_circuit_breaker: Whether to enable circuit breaker pattern
            enable_redis_cache: Whether to enable Redis caching
            redis_config: Redis configuration
            session_config: Session pool configuration
            thread_config: Thread pool configuration
            max_concurrency: Maximum concurrent operations
            default_executor_mode: Default execution mode for multi-region executor
        """
        # Set up regions
        self.regions = regions or ["us-east-1", "us-west-2", "eu-west-1"]
        if primary_region and primary_region not in self.regions:
            self.regions.append(primary_region)
        self.primary_region = primary_region or self.regions[0]

        # Set up circuit breaker if enabled
        self.circuit_breaker_manager = None
        if enable_circuit_breaker:
            self.circuit_breaker_manager = CircuitBreakerManager()

        # Set up Redis cache if enabled
        self.cache = None
        if enable_redis_cache:
            redis_config = redis_config or {}
            self.cache = RedisCache(**redis_config)

        # Initialize client registry
        self.client_registry = ClientRegistry(
            profile=profile,
            regions=self.regions,
            circuit_breaker_manager=self.circuit_breaker_manager,
            cache=self.cache,
            session_config=session_config,
        )

        # Initialize regional strategy from client registry
        self.regional_strategy = self.client_registry.regional_strategy

        # Initialize specialized client factories
        self.network_manager = self.client_registry.get_network_manager_client()

        # Initialize multi-region executor
        self.executor = OptimizedMultiRegionExecutor(
            client_registry=self.client_registry,
            max_concurrency=max_concurrency,
            default_regions=self.regions,
            default_mode=default_executor_mode,
        )

        logger.info(
            f"AWSClientFramework initialized with {len(self.regions)} regions, "
            f"primary: {self.primary_region}, circuit breaker: {enable_circuit_breaker}"
        )

    async def execute_multi_region(
        self,
        service: str,
        operation: str,
        regions: Optional[List[str]] = None,
        operation_kwargs: Optional[Dict[str, Any]] = None,
        mode: Optional[ExecutionMode] = None,
        timeout: Optional[float] = None,
        client_type: ClientType = ClientType.OPTIMIZED,
    ) -> MultiRegionResult:
        """
        Execute operation across multiple regions.

        Args:
            service: AWS service name
            operation: Operation name
            regions: Regions to execute in (defaults to all configured regions)
            operation_kwargs: Arguments for the operation
            mode: Execution mode
            timeout: Operation timeout in seconds
            client_type: Type of client to use

        Returns:
            Multi-region operation result
        """
        return await self.executor.execute(
            service=service,
            operation=operation,
            regions=regions,
            operation_kwargs=operation_kwargs,
            mode=mode,
            timeout=timeout,
            client_type=client_type,
        )

    async def execute_with_fallback(
        self,
        service: str,
        operation: str,
        operation_kwargs: Optional[Dict[str, Any]] = None,
        regions: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        client_type: ClientType = ClientType.OPTIMIZED,
    ) -> Any:
        """
        Execute operation with regional fallback until success.

        Args:
            service: AWS service name
            operation: Operation name
            operation_kwargs: Arguments for the operation
            regions: Regions to try (defaults to all configured regions)
            timeout: Operation timeout in seconds
            client_type: Type of client to use

        Returns:
            Operation result

        Raises:
            Exception: If operation fails in all regions
        """
        result = await self.executor.execute(
            service=service,
            operation=operation,
            regions=regions,
            operation_kwargs=operation_kwargs,
            mode=ExecutionMode.FALLBACK,
            timeout=timeout,
            client_type=client_type,
        )

        if result.success_count == 0:
            raise Exception(f"Operation {service}.{operation} failed in all regions")

        return result.primary_result

    async def execute_fastest(
        self,
        service: str,
        operation: str,
        operation_kwargs: Optional[Dict[str, Any]] = None,
        regions: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        client_type: ClientType = ClientType.OPTIMIZED,
    ) -> Any:
        """
        Execute operation in all regions and return first successful result.

        Args:
            service: AWS service name
            operation: Operation name
            operation_kwargs: Arguments for the operation
            regions: Regions to try (defaults to all configured regions)
            timeout: Operation timeout in seconds
            client_type: Type of client to use

        Returns:
            Operation result

        Raises:
            Exception: If operation fails in all regions
        """
        result = await self.executor.execute(
            service=service,
            operation=operation,
            regions=regions,
            operation_kwargs=operation_kwargs,
            mode=ExecutionMode.FASTEST,
            timeout=timeout,
            client_type=client_type,
        )

        if result.success_count == 0:
            raise Exception(f"Operation {service}.{operation} failed in all regions")

        return result.primary_result

    async def execute_async_multi_region(
        self,
        service: str,
        operation: str,
        regions: List[str],
        **kwargs
    ) -> MultiRegionResult:
        """Async multi-region execution with aioboto3."""
        tasks = []
        async with aioboto3.Session() as session:
            for region in regions:
                client = await session.client(service, region)
                tasks.append(self._execute_async_operation(client, operation, kwargs))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return self._process_async_results(results)

    async def _execute_async_operation(self, client, operation, kwargs):
        try:
            result = await getattr(client, operation)(**kwargs)
            return {'status': 'success', 'result': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    async def get_client(
        self,
        service: str,
        region: Optional[str] = None,
        client_type: ClientType = ClientType.STANDARD,
    ) -> Any:
        """
        Get an AWS client from the registry.

        Args:
            service: AWS service name
            region: Optional region (defaults to best region from strategy)
            client_type: Type of client to create

        Returns:
            AWS client instance
        """
        return await self.client_registry.get_client(service, region, client_type)

    def get_sync_client(
        self,
        service: str,
        region: Optional[str] = None,
        client_type: ClientType = ClientType.STANDARD,
    ) -> Any:
        """
        Get a synchronous AWS client from the registry.

        Args:
            service: AWS service name
            region: Optional region (defaults to best region from strategy)
            client_type: Type of client to create

        Returns:
            AWS client instance
        """
        return self.client_registry.get_sync_client(service, region, client_type)

    async def get_network_manager_resources(
        self,
        core_network_id: Optional[str] = None,
        global_network_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Get comprehensive CloudWAN resources.

        Args:
            core_network_id: Optional Core Network ID
            global_network_id: Optional Global Network ID
            force_refresh: Force refresh from API

        Returns:
            Dictionary of CloudWAN resources
        """
        # First get global networks
        global_networks_response = await self.network_manager.list_global_networks(force_refresh)
        global_networks = global_networks_response.get("GlobalNetworks", [])

        # If specific global network requested, filter list
        if global_network_id:
            global_networks = [
                gn for gn in global_networks if gn.get("GlobalNetworkId") == global_network_id
            ]

        # If no global networks found, return empty result
        if not global_networks:
            return {
                "GlobalNetworks": [],
                "CoreNetworks": [],
                "NetworkFunctionGroups": [],
            }

        # Use first global network if not specified
        target_global_network = global_networks[0]
        target_global_network_id = target_global_network["GlobalNetworkId"]

        # Get core networks for this global network
        core_networks_response = await self.network_manager.list_core_networks(
            target_global_network_id, force_refresh
        )
        core_networks = core_networks_response.get("CoreNetworks", [])

        # If specific core network requested, filter list
        if core_network_id:
            core_networks = [
                cn for cn in core_networks if cn.get("CoreNetworkId") == core_network_id
            ]

        # If no core networks found, return just global networks
        if not core_networks:
            return {
                "GlobalNetworks": global_networks,
                "CoreNetworks": [],
                "NetworkFunctionGroups": [],
            }

        # Use first core network if not specified
        target_core_network = core_networks[0]
        target_core_network_id = target_core_network["CoreNetworkId"]

        # Get network function groups for this core network
        network_function_groups = await self.network_manager.get_network_function_groups(
            target_core_network_id, force_refresh
        )

        # Get policy for this core network
        policy_response = await self.network_manager.get_core_network_policy(
            target_core_network_id, force_refresh
        )

        # Return comprehensive resources
        return {
            "GlobalNetworks": global_networks,
            "CoreNetworks": core_networks,
            "NetworkFunctionGroups": network_function_groups.get("NetworkFunctionGroups", []),
            "CoreNetworkPolicy": policy_response.get("CoreNetworkPolicy", {}),
        }

    def get_region_health(self, region: str) -> RegionHealth:
        """Get health status for a region."""
        return self.regional_strategy.get_region_health(region)

    def get_all_region_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all regions."""
        return self.regional_strategy.get_all_region_metrics()

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        return self.executor.get_execution_stats()

    def get_regional_service_stats(self, service: str) -> Dict[str, Dict[str, Any]]:
        """Get regional statistics for a service."""
        return self.executor.get_regional_stats(service)

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        if not self.circuit_breaker_manager:
            return {"enabled": False}

        return {
            "enabled": True,
            "status": self.circuit_breaker_manager.get_global_health_status(),
        }

    async def close(self) -> None:
        """Securely clean up all resources"""
        await self.client_registry.close()
        
        # Securely clear cache
        await self._secure_cache_clear()
        
        # Rotate encryption keys
        self.credential_manager._rotate_encryption_keys()
        
        logger.info("Secure framework shutdown completed")

    async def _secure_cache_clear(self):
        """Securely clear client cache"""
        for client in self._client_cache._cache.values():
            if hasattr(client, 'close'):
                await client.close()
            # Scrub client metadata
            del client.__dict__
        
        self._client_cache.clear()
        logger.debug("Secure cache clearance completed")

    async def execute_with_regional_strategy(self, service, operation, **kwargs):
        """Execute with constant-time characteristics"""
        start = time.perf_counter()
        result = await super().execute_with_regional_strategy(service, operation, **kwargs)
        elapsed = time.perf_counter() - start
        
        # Add random delay to prevent timing analysis
        jitter = secrets.randbelow(50) / 1000  # 0-50ms jitter
        await anyio.sleep(jitter)
        
        return result

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
