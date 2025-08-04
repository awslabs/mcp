"""
AWS Client Registry for CloudWAN MCP.

This module provides a central registry for AWS clients with:
- Standard client configuration and management
- Service-specific optimizations
- Credential management
- Client lifecycle tracking
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

import boto3
import aioboto3
from botocore.config import Config

from .regional_client_strategy import RegionalClientStrategy, RegionPreference
from .network_manager_client_factory import NetworkManagerClientFactory
from .circuit_breaker import CircuitBreakerManager
from .redis_cache import RedisCache
from .session_factory import AWSSessionFactory, SessionPoolConfig

logger = logging.getLogger(__name__)


class ClientType(Enum):
    """Types of AWS clients."""

    STANDARD = "standard"  # Regular AWS service client
    OPTIMIZED = "optimized"  # Optimized client with regional strategy
    CLOUDWAN = "cloudwan"  # CloudWAN-specific optimized client


class ClientRegistry:
    """
    Central registry for AWS client management.

    Features:
    - Standardized client creation and configuration
    - Service-specific client factories
    - Credential and session management
    - Client lifecycle tracking
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        regions: Optional[List[str]] = None,
        circuit_breaker_manager: Optional[CircuitBreakerManager] = None,
        cache: Optional[RedisCache] = None,
        session_config: Optional[SessionPoolConfig] = None,
    ):
        """
        Initialize client registry.

        Args:
            profile: AWS profile name
            regions: List of AWS regions
            circuit_breaker_manager: Optional circuit breaker manager
            cache: Optional Redis cache
            session_config: Optional session pool configuration
        """
        self.profile = profile
        self.regions = regions or ["us-east-1", "us-west-2", "eu-west-1"]
        self.circuit_breaker_manager = circuit_breaker_manager
        self.cache = cache
        self.session_config = session_config

        # Initialize session factory
        self.session_factory = AWSSessionFactory(
            profile=profile, regions=self.regions, config=session_config
        )

        # Initialize regional strategy
        self.regional_strategy = RegionalClientStrategy(
            regions=self.regions,
            preference_mode=RegionPreference.BALANCED,
            circuit_breaker_manager=circuit_breaker_manager,
        )

        # Service-specific client factories
        self.network_manager_factory = NetworkManagerClientFactory(
            profile=profile,
            regions=self.regions,
            circuit_breaker_manager=circuit_breaker_manager,
            cache=cache,
        )

        # Client caches by service and region
        self._sync_clients = {}  # (service, region) -> client
        self._async_clients = {}  # (service, region) -> client

        # Specialized client factories
        self._specialized_factories = {"networkmanager": self.network_manager_factory}

        # Default client configurations by service
        self._default_configs = {
            # CloudWAN services
            "networkmanager": Config(
                region_name="us-west-2",  # Only available in us-west-2
                retries={"max_attempts": 5, "mode": "adaptive"},
                connect_timeout=30,
                read_timeout=60,
            ),
            # Frequently used services
            "ec2": Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=20,
                read_timeout=30,
            ),
            "cloudwatch": Config(
                retries={"max_attempts": 4, "mode": "adaptive"},
                connect_timeout=15,
                read_timeout=45,
            ),
            # Default configuration
            "default": Config(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=30,
            ),
        }

        logger.info(f"ClientRegistry initialized with {len(self.regions)} regions")

    def _get_config_for_service(self, service_name: str) -> Config:
        """Get appropriate configuration for a service."""
        if service_name in self._default_configs:
            return self._default_configs[service_name]
        return self._default_configs["default"]

    def _get_client_cache_key(self, service: str, region: str, is_async: bool) -> str:
        """Generate cache key for client cache."""
        async_prefix = "async" if is_async else "sync"
        return f"{async_prefix}:{service}:{region}"

    async def get_client(
        self,
        service: str,
        region: Optional[str] = None,
        client_type: ClientType = ClientType.STANDARD,
    ) -> Any:
        """
        Get or create an asynchronous AWS client.

        Args:
            service: AWS service name
            region: Optional region (defaults to best region from strategy)
            client_type: Type of client to create

        Returns:
            AioBoto3 service client
        """
        # Handle specialized service factories
        if service == "networkmanager":
            return await self.network_manager_factory.get_async_client()

        # Determine region to use
        if not region:
            region = self.regional_strategy.select_region(service)

        # Check if client already exists in cache
        cache_key = self._get_client_cache_key(service, region, True)
        if cache_key in self._async_clients:
            return self._async_clients[cache_key]

        # Create appropriate client based on type
        if client_type == ClientType.OPTIMIZED:
            # Create optimized client with regional strategy
            client = await self.session_factory.get_async_session(service, region)
            config = self._get_config_for_service(service)
            async_client = await client.client(
                service, region_name=region, config=config
            ).__aenter__()

            # Cache client
            self._async_clients[cache_key] = async_client
            return async_client
        else:
            # Create standard client
            config = self._get_config_for_service(service)
            session = aioboto3.Session(profile_name=self.profile)
            client = await session.client(service, region_name=region, config=config).__aenter__()

            # Cache client
            self._async_clients[cache_key] = client
            return client

    def get_sync_client(
        self,
        service: str,
        region: Optional[str] = None,
        client_type: ClientType = ClientType.STANDARD,
    ) -> Any:
        """
        Get or create a synchronous AWS client.

        Args:
            service: AWS service name
            region: Optional region (defaults to best region from strategy)
            client_type: Type of client to create

        Returns:
            Boto3 service client
        """
        # Handle specialized service factories
        if service == "networkmanager":
            return self.network_manager_factory.get_sync_client()

        # Determine region to use
        if not region:
            region = self.regional_strategy.select_region(service)

        # Check if client already exists in cache
        cache_key = self._get_client_cache_key(service, region, False)
        if cache_key in self._sync_clients:
            return self._sync_clients[cache_key]

        # Create appropriate client based on type
        if client_type == ClientType.OPTIMIZED:
            # Create optimized client with session factory
            client = self.session_factory.get_sync_client(service, region)

            # Cache client
            self._sync_clients[cache_key] = client
            return client
        else:
            # Create standard client
            config = self._get_config_for_service(service)
            session = boto3.Session(profile_name=self.profile)
            client = session.client(service, region_name=region, config=config)

            # Cache client
            self._sync_clients[cache_key] = client
            return client

    def get_network_manager_client(self) -> NetworkManagerClientFactory:
        """
        Get the specialized NetworkManager client factory.

        Returns:
            NetworkManagerClientFactory instance
        """
        return self.network_manager_factory

    async def execute_with_regional_strategy(
        self,
        service: str,
        operation: str,
        operation_kwargs: Dict[str, Any] = None,
        regions: Optional[List[str]] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Execute operation with optimal region selection and fallback.

        Args:
            service: AWS service name
            operation: Operation name
            operation_kwargs: Operation arguments
            regions: Optional list of regions to try
            max_retries: Maximum number of retries

        Returns:
            Operation response

        Raises:
            Exception: If operation fails in all regions
        """
        operation_kwargs = operation_kwargs or {}

        # Create client factory function for regional strategy
        async def client_factory(region: str) -> Any:
            return await self.get_client(service, region)

        # Execute with regional fallback
        result, region = await self.regional_strategy.execute_in_optimal_region(
            service=service,
            operation=operation,
            client_factory=client_factory,
            operation_kwargs=operation_kwargs,
            required_regions=regions,
            max_retries=max_retries,
        )

        return result

    def execute_with_regional_strategy_sync(
        self,
        service: str,
        operation: str,
        operation_kwargs: Dict[str, Any] = None,
        regions: Optional[List[str]] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Synchronous version of execute_with_regional_strategy.

        Args:
            service: AWS service name
            operation: Operation name
            operation_kwargs: Operation arguments
            regions: Optional list of regions to try
            max_retries: Maximum number of retries

        Returns:
            Operation response

        Raises:
            Exception: If operation fails in all regions
        """
        operation_kwargs = operation_kwargs or {}

        # Create client factory function for regional strategy
        def client_factory(region: str) -> Any:
            return self.get_sync_client(service, region)

        # Execute with regional fallback
        result, region = self.regional_strategy.execute_with_fallback_sync(
            service=service,
            operation=operation,
            client_factory=client_factory,
            operation_kwargs=operation_kwargs,
            required_regions=regions,
            max_retries=max_retries,
        )

        return result

    def regional_client(
        self, service: str, regions: Optional[List[str]] = None, max_retries: int = 2
    ) -> Callable:
        """
        Decorator for functions that need regional fallback.

        Args:
            service: AWS service name
            regions: Optional list of regions to try
            max_retries: Maximum number of retries

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            # Determine if function is async or sync
            if asyncio.iscoroutinefunction(func):

                async def async_wrapper(*args, **kwargs):
                    return await self.execute_with_regional_strategy(
                        service=service,
                        operation=func.__name__,
                        operation_kwargs=kwargs,
                        regions=regions,
                        max_retries=max_retries,
                    )

                return async_wrapper
            else:

                def sync_wrapper(*args, **kwargs):
                    return self.execute_with_regional_strategy_sync(
                        service=service,
                        operation=func.__name__,
                        operation_kwargs=kwargs,
                        regions=regions,
                        max_retries=max_retries,
                    )

                return sync_wrapper

        return decorator

    async def close(self) -> None:
        """Clean up resources."""
        # Close all async clients
        for client in self._async_clients.values():
            try:
                await client.__aexit__(None, None, None)
            except Exception:
                pass

        # Close session factory
        await self.session_factory.close()

        # Close network manager factory
        await self.network_manager_factory.close()

        logger.info("ClientRegistry closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
