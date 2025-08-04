"""
NetworkManager Client Factory for CloudWAN MCP.

This module provides specialized client management for AWS Network Manager with:
- CloudWAN-specific configurations and optimizations
- Cross-region coordination for CloudWAN operations
- Efficient credential management
- Caching layer for NetworkManager responses
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
try:
    import aioboto3
    AIOBOTO3_AVAILABLE = True
except ImportError:
    AIOBOTO3_AVAILABLE = False
    aioboto3 = None
from botocore.config import Config

from .regional_client_strategy import (
    RegionalClientStrategy,
    RegionPreference,
)
from .circuit_breaker import CircuitBreakerManager
from .redis_cache import RedisCache

logger = logging.getLogger(__name__)


class NetworkManagerClientFactory:
    """
    Specialized client factory for AWS Network Manager service.

    Features:
    - Optimized for NetworkManager's us-west-2-only requirements
    - Response caching for expensive operations
    - Automatic credential management
    - Cross-region coordination for CloudWAN resources
    - Performance optimization for bulk operations
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        regions: Optional[List[str]] = None,
        circuit_breaker_manager: Optional[CircuitBreakerManager] = None,
        cache: Optional[RedisCache] = None,
        retry_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize NetworkManager client factory.

        Args:
            profile: AWS profile name
            regions: List of AWS regions for CloudWAN resources
            circuit_breaker_manager: Optional circuit breaker manager
            cache: Optional cache for NetworkManager responses
            retry_config: Optional retry configuration
        """
        # Network Manager is only available in us-west-2
        self.primary_region = "us-west-2"

        # Additional regions for cross-region CloudWAN resources
        self.regions = regions or ["us-east-1", "us-west-2", "eu-west-1"]
        if self.primary_region not in self.regions:
            self.regions.append(self.primary_region)

        self.profile = profile
        self.circuit_breaker_manager = circuit_breaker_manager
        self.cache = cache

        # Network Manager specific configurations
        self.retry_config = retry_config or {
            "max_attempts": 5,
            "mode": "adaptive",
            "total_max_attempts": 10,
        }

        # Configure boto3 client settings
        self.boto_config = Config(
            region_name=self.primary_region,
            retries=self.retry_config,
            connect_timeout=30,
            read_timeout=60,
            parameter_validation=True,
            max_pool_connections=25,
        )

        # Initialize regional strategy with NetworkManager primary region
        self.regional_strategy = RegionalClientStrategy(
            regions=self.regions,
            primary_region=self.primary_region,
            preference_mode=RegionPreference.PRIMARY_PREFERRED,
            circuit_breaker_manager=circuit_breaker_manager,
        )

        # Client caches
        self._sync_client = None
        self._async_client = None
        self._sync_clients_by_region = {}
        self._async_clients_by_region = {}

        # Operation response cache
        self._operation_cache = {}
        self._cache_ttl = {
            # Short cache for dynamic operations
            "get_core_network_telemetry": 60,  # 1 minute
            "get_route_analysis": 300,  # 5 minutes
            # Longer cache for more static operations
            "describe_global_networks": 3600,  # 1 hour
            "list_core_networks": 3600,  # 1 hour
            "get_core_network_policy": 3600,  # 1 hour
            # Default TTL
            "default": 300,  # 5 minutes
        }

        logger.info(
            f"NetworkManagerClientFactory initialized - Primary region: {self.primary_region}"
        )

    def get_sync_client(self, region: Optional[str] = None) -> boto3.client:
        """
        Get or create synchronous NetworkManager client.

        Args:
            region: Optional region (defaults to primary region)

        Returns:
            Boto3 NetworkManager client
        """
        # NetworkManager is only available in us-west-2
        target_region = "us-west-2"

        if target_region in self._sync_clients_by_region:
            return self._sync_clients_by_region[target_region]

        # Create new client
        session = boto3.Session(profile_name=self.profile)
        client = session.client(
            "networkmanager", region_name=target_region, config=self.boto_config
        )

        # Cache client
        self._sync_clients_by_region[target_region] = client
        self._sync_client = client  # Default client

        return client

    async def get_async_client(self, region: Optional[str] = None) -> Any:
        """
        Get or create asynchronous NetworkManager client.

        Args:
            region: Optional region (defaults to primary region)

        Returns:
            AioBoto3 NetworkManager client
        """
        # NetworkManager is only available in us-west-2
        target_region = "us-west-2"

        if target_region in self._async_clients_by_region:
            return self._async_clients_by_region[target_region]

        # Create new client
        session = aioboto3.Session(profile_name=self.profile)
        client = session.client(
            "networkmanager", region_name=target_region, config=self.boto_config
        )

        # Cache client
        self._async_clients_by_region[target_region] = client
        self._async_client = client  # Default client

        return client

    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation and arguments."""
        # Sort kwargs to ensure consistent key generation
        sorted_items = sorted(kwargs.items())
        args_str = json.dumps(sorted_items, sort_keys=True)

        # Create unique key
        return f"networkmanager:{operation}:{args_str}"

    def _get_ttl_for_operation(self, operation: str) -> int:
        """Get appropriate TTL for operation from configuration."""
        return self._cache_ttl.get(operation, self._cache_ttl["default"])

    async def execute_with_cache(
        self, operation: str, force_refresh: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """
        Execute NetworkManager operation with caching.

        Args:
            operation: Operation name
            force_refresh: Force refresh from API
            **kwargs: Operation arguments

        Returns:
            Operation response
        """
        cache_key = self._get_cache_key(operation, **kwargs)

        # Check cache first
        if not force_refresh and self.cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for {operation}")
                return cached_result

        # Check local cache if Redis not available
        if not force_refresh and cache_key in self._operation_cache:
            cache_entry = self._operation_cache[cache_key]
            if cache_entry["expires_at"] > datetime.now(timezone.utc):
                logger.debug(f"Local cache hit for {operation}")
                return cache_entry["data"]

        # Execute operation
        client = await self.get_async_client()
        try:
            async with client:
                operation_func = getattr(client, operation)
                result = await operation_func(**kwargs)
        except Exception as e:
            logger.error(f"NetworkManager operation {operation} failed: {str(e)}")
            raise

        # Cache result
        ttl = self._get_ttl_for_operation(operation)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        # Store in local cache
        self._operation_cache[cache_key] = {
            "data": result,
            "expires_at": expires_at,
        }

        # Store in Redis if available
        if self.cache:
            await self.cache.set(cache_key, result, ttl=ttl)

        return result

    def execute_with_cache_sync(
        self, operation: str, force_refresh: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """
        Synchronous version of execute_with_cache.

        Args:
            operation: Operation name
            force_refresh: Force refresh from API
            **kwargs: Operation arguments

        Returns:
            Operation response
        """
        cache_key = self._get_cache_key(operation, **kwargs)

        # Check local cache
        if not force_refresh and cache_key in self._operation_cache:
            cache_entry = self._operation_cache[cache_key]
            if cache_entry["expires_at"] > datetime.now(timezone.utc):
                logger.debug(f"Local cache hit for {operation}")
                return cache_entry["data"]

        # Execute operation
        client = self.get_sync_client()
        try:
            operation_func = getattr(client, operation)
            result = operation_func(**kwargs)
        except Exception as e:
            logger.error(f"NetworkManager operation {operation} failed: {str(e)}")
            raise

        # Cache result
        ttl = self._get_ttl_for_operation(operation)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        # Store in local cache
        self._operation_cache[cache_key] = {
            "data": result,
            "expires_at": expires_at,
        }

        return result

    async def list_global_networks(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        List AWS Global Networks with caching.

        Args:
            force_refresh: Force refresh from API

        Returns:
            Global Networks response
        """
        return await self.execute_with_cache("describe_global_networks", force_refresh)

    async def list_core_networks(
        self, global_network_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        List Core Networks with caching.

        Args:
            global_network_id: Global Network ID
            force_refresh: Force refresh from API

        Returns:
            Core Networks response
        """
        return await self.execute_with_cache(
            "list_core_networks", force_refresh, GlobalNetworkId=global_network_id
        )

    async def get_core_network_policy(
        self, core_network_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get Core Network policy with caching.

        Args:
            core_network_id: Core Network ID
            force_refresh: Force refresh from API

        Returns:
            Core Network policy response
        """
        return await self.execute_with_cache(
            "get_core_network_policy", force_refresh, CoreNetworkId=core_network_id
        )

    async def describe_global_network_resources(
        self,
        global_network_id: str,
        resource_region: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Get resources for a Global Network with caching.

        Args:
            global_network_id: Global Network ID
            resource_region: Optional region to filter resources
            force_refresh: Force refresh from API

        Returns:
            Global Network resources response
        """
        kwargs = {"GlobalNetworkId": global_network_id}
        if resource_region:
            kwargs["RegisteredRegion"] = resource_region

        return await self.execute_with_cache("describe_global_networks", force_refresh, **kwargs)

    async def get_network_function_groups(
        self, core_network_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get Network Function Groups with caching.

        Args:
            core_network_id: Core Network ID
            force_refresh: Force refresh from API

        Returns:
            Network Function Groups response
        """
        # This operation requires parsing the policy, since NFGs are defined there
        policy_response = await self.get_core_network_policy(
            core_network_id=core_network_id, force_refresh=force_refresh
        )

        # Extract NFGs from policy
        policy_string = policy_response.get("CoreNetworkPolicy", {}).get("PolicyDocument", "{}")
        policy = json.loads(policy_string)

        # Extract network function groups from policy
        network_function_groups = policy.get("network-function-groups", [])

        return {
            "CoreNetworkId": core_network_id,
            "NetworkFunctionGroups": network_function_groups,
        }

    async def analyze_cross_region_attachments(
        self, core_network_id: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze cross-region Core Network attachments.

        Args:
            core_network_id: Core Network ID
            force_refresh: Force refresh from API

        Returns:
            Cross-region attachment analysis
        """
        # Get core network policy first
        policy_response = await self.get_core_network_policy(
            core_network_id=core_network_id, force_refresh=force_refresh
        )

        # Get all attachments
        attachments_response = await self.execute_with_cache(
            "get_core_network_policy_attachments",
            force_refresh,
            CoreNetworkId=core_network_id,
        )

        # Get all segments from policy
        policy_string = policy_response.get("CoreNetworkPolicy", {}).get("PolicyDocument", "{}")
        policy = json.loads(policy_string)
        segments = policy.get("segments", [])

        # Analyze attachments by region
        attachments_by_region = {}
        for attachment in attachments_response.get("CoreNetworkPolicyAttachments", []):
            region = attachment.get("Region", "unknown")
            if region not in attachments_by_region:
                attachments_by_region[region] = []
            attachments_by_region[region].append(attachment)

        # Calculate cross-region connectivity
        cross_region_connectivity = []
        for region1, attachments1 in attachments_by_region.items():
            for region2, attachments2 in attachments_by_region.items():
                if region1 != region2:
                    connectivity = {
                        "source_region": region1,
                        "destination_region": region2,
                        "attachment_count": len(attachments1),
                        "destination_attachment_count": len(attachments2),
                    }
                    cross_region_connectivity.append(connectivity)

        return {
            "CoreNetworkId": core_network_id,
            "TotalAttachments": len(attachments_response.get("CoreNetworkPolicyAttachments", [])),
            "AttachmentsByRegion": attachments_by_region,
            "CrossRegionConnectivity": cross_region_connectivity,
            "SegmentCount": len(segments),
        }

    async def list_all_attachments_by_segment(
        self, core_network_id: str, force_refresh: bool = False
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Get all Core Network attachments organized by segment.

        Args:
            core_network_id: Core Network ID
            force_refresh: Force refresh from API

        Returns:
            Attachments by segment
        """
        attachments_response = await self.execute_with_cache(
            "list_attachments", force_refresh, CoreNetworkId=core_network_id
        )

        # Organize attachments by segment
        attachments_by_segment = {}

        for attachment in attachments_response.get("Attachments", []):
            segment_name = attachment.get("SegmentName", "unknown")
            attachment_type = attachment.get("AttachmentType", "unknown")

            if segment_name not in attachments_by_segment:
                attachments_by_segment[segment_name] = {}

            if attachment_type not in attachments_by_segment[segment_name]:
                attachments_by_segment[segment_name][attachment_type] = []

            attachments_by_segment[segment_name][attachment_type].append(attachment)

        return attachments_by_segment

    def clear_cache(self, operation: Optional[str] = None) -> None:
        """
        Clear operation cache.

        Args:
            operation: Optional specific operation to clear
        """
        if operation:
            # Clear only entries for specified operation
            keys_to_remove = [
                key
                for key in self._operation_cache
                if key.startswith(f"networkmanager:{operation}:")
            ]
            for key in keys_to_remove:
                self._operation_cache.pop(key, None)

            # Clear Redis cache if available
            if self.cache:
                asyncio.create_task(self.cache.delete_pattern(f"networkmanager:{operation}:*"))

            logger.info(f"Cleared cache for NetworkManager operation: {operation}")
        else:
            # Clear all entries
            self._operation_cache.clear()

            # Clear Redis cache if available
            if self.cache:
                asyncio.create_task(self.cache.delete_pattern("networkmanager:*"))

            logger.info("Cleared all NetworkManager operation caches")

    def set_cache_ttl(self, operation: str, ttl_seconds: int) -> None:
        """
        Set cache TTL for specific operation.

        Args:
            operation: Operation name
            ttl_seconds: TTL in seconds
        """
        self._cache_ttl[operation] = ttl_seconds
        logger.info(f"Set cache TTL for {operation} to {ttl_seconds}s")

    async def close(self) -> None:
        """Clean up resources."""
        # Close all async clients
        for client in self._async_clients_by_region.values():
            try:
                await client.__aexit__(None, None, None)
            except Exception:
                pass

        self._async_clients_by_region.clear()
        self._async_client = None
        logger.info("NetworkManagerClientFactory closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Can't await close() in __exit__, so just clean up sync resources
        self._sync_clients_by_region.clear()
        self._sync_client = None
