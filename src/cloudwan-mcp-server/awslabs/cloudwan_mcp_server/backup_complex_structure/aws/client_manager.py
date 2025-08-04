"""
AWS Client Manager for CloudWAN MCP Server.

This module provides centralized AWS client management with credential handling,
session management, STS AssumeRole support, and memory-optimized LRU caching.
"""

import asyncio
import boto3
import collections
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError
from botocore.config import Config

from ..config import CloudWANConfig

logger = logging.getLogger(__name__)


class AWSClientError(Exception):
    """Custom exception for AWS client errors."""
    pass


class LRUClientCache:
    """Thread-safe LRU cache with memory limits for AWS clients."""
    
    def __init__(self, max_memory_mb: int = 64, max_clients: int = 100):
        self.max_memory = max_memory_mb * 1024 * 1024  # Convert MB to bytes
        self.max_clients = max_clients
        self._cache = collections.OrderedDict()
        self._current_memory = 0
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        
        # Estimated overhead per client connection (adjust based on profiling)
        self._client_overhead = 2048  # 2KB baseline per client
        
    def get_client(self, key: str) -> Optional[Any]:
        """Get client with LRU tracking and memory checks."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                client = self._cache.pop(key)
                self._cache[key] = client
                self.hits += 1
                
                # Update performance monitor
                try:
                    from ..utils.performance_monitor import get_performance_monitor
                    monitor = get_performance_monitor()
                    monitor.record_cache_hit()
                except Exception:
                    pass  # Don't let monitoring failures break functionality
                
                return client
            
            self.misses += 1
            
            # Update performance monitor
            try:
                from ..utils.performance_monitor import get_performance_monitor
                monitor = get_performance_monitor()
                monitor.record_cache_miss()
            except Exception:
                pass
                
            return None
    
    def add_client(self, key: str, client: Any) -> None:
        """Add client with memory tracking and eviction."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                self._cache.pop(key)
            
            # Estimate memory usage
            client_size = self._estimate_client_size(client) + self._client_overhead
            
            # Add new client
            self._cache[key] = client
            self._current_memory += client_size
            
            # Update performance monitor with cache memory usage
            try:
                from ..utils.performance_monitor import get_performance_monitor
                monitor = get_performance_monitor()
                monitor.update_cache_memory(self._current_memory / (1024 * 1024))  # Convert to MB
            except Exception:
                pass
            
            # Evict while over limits
            while (len(self._cache) > self.max_clients or 
                   self._current_memory > self.max_memory):
                if not self._evict_oldest():
                    break  # No more items to evict
    
    def _evict_oldest(self) -> bool:
        """Evict least recently used entry. Returns True if evicted, False if cache empty."""
        if not self._cache:
            return False
            
        key, client = self._cache.popitem(last=False)
        client_size = self._estimate_client_size(client) + self._client_overhead
        self._current_memory = max(0, self._current_memory - client_size)
        logger.debug(f"Evicted client {key}, freed {client_size} bytes")
        return True
    
    def _estimate_client_size(self, client: Any) -> int:
        """Estimate memory usage of boto3 client or async wrapper."""
        # Handle AsyncClientWrapper differently
        if hasattr(client, '_client'):
            # This is an AsyncClientWrapper - estimate both wrapper and underlying client
            wrapper_size = sys.getsizeof(client)
            underlying_size = sys.getsizeof(client._client)
            # Factor for internal service models, event system, etc.
            return (wrapper_size + underlying_size * 6)  # Optimized multiplier
        else:
            # Regular boto3 client
            base_size = sys.getsizeof(client)
            # Factor for internal service models, event system, etc.
            return base_size * 6  # Reduced from 8 to 6 based on profiling
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self._lock:
            total_requests = self.hits + self.misses
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": self.hits / total_requests if total_requests > 0 else 0,
                "current_memory_mb": round(self._current_memory / (1024 * 1024), 2),
                "max_memory_mb": round(self.max_memory / (1024 * 1024), 2),
                "memory_utilization": self._current_memory / self.max_memory if self.max_memory > 0 else 0,
                "num_clients": len(self._cache),
                "max_clients": self.max_clients,
                "client_utilization": len(self._cache) / self.max_clients if self.max_clients > 0 else 0
            }
    
    def clear(self) -> None:
        """Clear cache completely."""
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
            self.hits = 0
            self.misses = 0
            logger.info("LRU client cache cleared")
    
    def purge_under_pressure(self, target_memory_mb: int) -> int:
        """Emergency purge to meet memory target. Returns number of evicted clients."""
        target_memory = target_memory_mb * 1024 * 1024
        evicted_count = 0
        
        with self._lock:
            while self._current_memory > target_memory and self._cache:
                if self._evict_oldest():
                    evicted_count += 1
                else:
                    break
        
        logger.warning(f"Memory pressure purge: evicted {evicted_count} clients, "
                      f"current memory: {self._current_memory / (1024 * 1024):.2f}MB")
        return evicted_count


class CredentialManager:
    """Handles AWS credential management with STS AssumeRole support."""
    
    def __init__(self, config: CloudWANConfig):
        self.config = config
        self._assumed_credentials: Optional[Dict[str, Any]] = None
        self._credentials_expiry: Optional[datetime] = None
        self._refresh_lock = threading.Lock()
        
    def get_session(self) -> boto3.Session:
        """Get AWS session with appropriate credentials."""
        if self.config.aws.assume_role_arn:
            return self._get_assumed_role_session()
        else:
            # Use default session with profile if specified
            return boto3.Session(profile_name=self.config.aws.default_profile)
    
    def _get_assumed_role_session(self) -> boto3.Session:
        """Get session with assumed role credentials."""
        with self._refresh_lock:
            # Check if credentials need refresh
            if (self._assumed_credentials is None or 
                self._credentials_expiry is None or
                datetime.now() >= self._credentials_expiry - timedelta(minutes=5)):
                
                self._refresh_assumed_role_credentials()
            
            # Create session with assumed role credentials
            return boto3.Session(
                aws_access_key_id=self._assumed_credentials['AccessKeyId'],
                aws_secret_access_key=self._assumed_credentials['SecretAccessKey'],
                aws_session_token=self._assumed_credentials['SessionToken']
            )
    
    def _refresh_assumed_role_credentials(self) -> None:
        """Refresh assumed role credentials."""
        try:
            # Use base session to assume role
            base_session = boto3.Session(
                profile_name=self.config.aws.default_profile or self.config.aws.backup_profile
            )
            sts = base_session.client('sts')
            
            # Assume role
            response = sts.assume_role(
                RoleArn=self.config.aws.assume_role_arn,
                RoleSessionName=f"cloudwan-mcp-{int(time.time())}",
                DurationSeconds=min(
                    max(self.config.aws.min_session_duration, 900),
                    self.config.aws.max_session_duration
                )
            )
            
            credentials = response['Credentials']
            self._assumed_credentials = {
                'AccessKeyId': credentials['AccessKeyId'],
                'SecretAccessKey': credentials['SecretAccessKey'],
                'SessionToken': credentials['SessionToken']
            }
            self._credentials_expiry = credentials['Expiration']
            
            logger.info(f"Successfully assumed role: {self.config.aws.assume_role_arn}")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDenied':
                logger.error(f"Access denied when assuming role: {self.config.aws.assume_role_arn}")
                if self.config.aws.backup_profile:
                    logger.info(f"Falling back to backup profile: {self.config.aws.backup_profile}")
                    # Fall back to backup profile session
                    raise AWSClientError("Role assumption failed, fallback to backup profile")
            else:
                logger.error(f"Failed to assume role: {e}")
                raise AWSClientError(f"Role assumption failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during role assumption: {e}")
            raise AWSClientError(f"Role assumption failed: {e}")


class AsyncClientWrapper:
    """
    High-performance wrapper class to make boto3 clients async-compatible.
    
    This wrapper handles the async/sync bridge for boto3 clients that are
    inherently synchronous but need to work in async contexts with optimized
    thread pool management.
    """
    
    # Shared thread pool executor across all instances for better resource utilization
    _shared_executor: Optional[ThreadPoolExecutor] = None
    _executor_lock = threading.Lock()
    _instance_count = 0
    
    def __init__(self, boto3_client):
        """
        Initialize the async wrapper with shared thread pool.
        
        Args:
            boto3_client: The boto3 client to wrap
        """
        self._client = boto3_client
        self._method_cache = {}  # Cache wrapped methods for better performance
        
        # Initialize shared executor on first instance
        with AsyncClientWrapper._executor_lock:
            AsyncClientWrapper._instance_count += 1
            if AsyncClientWrapper._shared_executor is None:
                AsyncClientWrapper._shared_executor = ThreadPoolExecutor(
                    max_workers=8,  # Increased for better concurrency
                    thread_name_prefix="aws-async-shared"
                )
    
    def __getattr__(self, name):
        """
        Dynamically wrap boto3 client methods to be async with caching.
        
        Args:
            name: Method name to wrap
            
        Returns:
            Async-wrapped method
        """
        # Check method cache first for performance
        if name in self._method_cache:
            return self._method_cache[name]
            
        if hasattr(self._client, name):
            attr = getattr(self._client, name)
            
            # If it's a callable method, wrap it in async
            if callable(attr):
                async def async_method(*args, **kwargs):
                    loop = asyncio.get_event_loop()
                    try:
                        # Execute sync method in shared thread pool
                        result = await loop.run_in_executor(
                            AsyncClientWrapper._shared_executor,
                            lambda: attr(*args, **kwargs)
                        )
                        return result
                    except Exception as e:
                        logger.error(f"Error in async {name} for {self._client._service_model.service_name}: {e}")
                        raise
                
                # Cache the wrapped method
                self._method_cache[name] = async_method
                return async_method
            else:
                # Return non-callable attributes as-is
                return attr
        
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        with AsyncClientWrapper._executor_lock:
            AsyncClientWrapper._instance_count -= 1
            # Clean up shared executor when no more instances exist
            if AsyncClientWrapper._instance_count == 0 and AsyncClientWrapper._shared_executor:
                AsyncClientWrapper._shared_executor.shutdown(wait=False)
                AsyncClientWrapper._shared_executor = None
    
    def __del__(self):
        """Cleanup on deletion."""
        with AsyncClientWrapper._executor_lock:
            if AsyncClientWrapper._instance_count > 0:
                AsyncClientWrapper._instance_count -= 1


class AWSClientManager:
    """Centralized AWS client manager with memory-optimized LRU caching."""
    
    def __init__(self, config: CloudWANConfig):
        self.config = config
        self.credential_manager = CredentialManager(config)
        
        # Initialize LRU cache with configured limits
        self._client_cache = LRUClientCache(
            max_memory_mb=config.tools.client_cache_memory_mb,
            max_clients=config.tools.max_cached_clients
        )
        
        self._cache_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="aws-client")
        
        # Configure retry settings
        self.client_config = Config(
            retries={'max_attempts': config.aws.max_retries, 'mode': 'adaptive'},
            max_pool_connections=50,
            read_timeout=config.aws.timeout_seconds,
            connect_timeout=config.aws.timeout_seconds
        )
        
    def get_client(self, service_name: str, region: str) -> boto3.client:
        """Get synchronous AWS client with LRU caching and memory management."""
        cache_key = f"{service_name}:{region}"
        
        # Try cache first
        client = self._client_cache.get_client(cache_key)
        if client:
            return client
            
        # Create new client
        try:
            session = self.credential_manager.get_session()
            
            # Check for custom endpoint
            client_kwargs = {
                "service_name": service_name,
                "region_name": region,
                "config": self.client_config
            }
            
            # Add custom endpoint if configured for this service
            if (self.config.aws.custom_endpoints and 
                isinstance(self.config.aws.custom_endpoints, dict) and
                service_name in self.config.aws.custom_endpoints):
                endpoint_url = self.config.aws.custom_endpoints[service_name]
                
                # For NetworkManager, validate region compatibility
                if service_name == "networkmanager":
                    # Extract region from custom endpoint
                    endpoint_region = self._extract_region_from_endpoint(endpoint_url)
                    if endpoint_region and endpoint_region != region:
                        logger.warning(
                            f"Custom NetworkManager endpoint is for {endpoint_region} but client requested {region}. "
                            f"Using custom endpoint region {endpoint_region}"
                        )
                        # Override the region to match the endpoint
                        client_kwargs["region_name"] = endpoint_region
                        cache_key = f"{service_name}:{endpoint_region}"  # Update cache key
                
                client_kwargs["endpoint_url"] = endpoint_url
                logger.info(f"Using custom endpoint for {service_name} in {client_kwargs['region_name']}: {endpoint_url}")
            
            client = session.client(**client_kwargs)
            
            # Add to cache with memory tracking
            self._client_cache.add_client(cache_key, client)
            logger.debug(f"Created and cached {service_name} client for {region}")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create {service_name} client for region {region}: {e}")
            raise AWSClientError(f"Client creation failed: {e}")
    
    def get_sync_client(self, service_name: str, region: str) -> boto3.client:
        """Get synchronous AWS client - alias for get_client for backward compatibility."""
        return self.get_client(service_name, region)
    
    async def get_client_async(self, service_name: str, region: str) -> AsyncClientWrapper:
        """Get async-wrapped AWS client with LRU caching and memory management."""
        cache_key = f"{service_name}:{region}:async"
        
        # Monitor the async client creation performance
        try:
            from ..utils.performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
        except ImportError:
            monitor = None
        
        if monitor:
            async with monitor.monitor_async_operation(f"get_client_async_{service_name}"):
                return await self._get_client_async_impl(service_name, region, cache_key)
        else:
            return await self._get_client_async_impl(service_name, region, cache_key)
    
    async def _get_client_async_impl(self, service_name: str, region: str, cache_key: str) -> AsyncClientWrapper:
        # Try cache first for async wrapper
        wrapped_client = self._client_cache.get_client(cache_key)
        if wrapped_client:
            return wrapped_client
            
        # Create new async wrapped client
        try:
            # Get synchronous client first
            sync_client = self.get_client(service_name, region)
            
            # Wrap it for async usage
            async_client = AsyncClientWrapper(sync_client)
            
            # Cache the async wrapper separately
            self._client_cache.add_client(cache_key, async_client)
            logger.debug(f"Created and cached async {service_name} client for {region}")
            return async_client
            
        except Exception as e:
            logger.error(f"Failed to create async {service_name} client for region {region}: {e}")
            raise AWSClientError(f"Async client creation failed: {e}")
    
    def _extract_region_from_endpoint(self, endpoint_url: str) -> Optional[str]:
        """Extract AWS region from custom endpoint URL."""
        import re
        # Match AWS region pattern (e.g., us-west-2, eu-central-1)
        region_pattern = r'\\.([a-z]{2}-[a-z]+-\\d+)\\.'
        match = re.search(region_pattern, endpoint_url)
        if match:
            return match.group(1)
        return None
    
    def get_session(self) -> boto3.Session:
        """Get AWS session."""
        return self.credential_manager.get_session()
    
    def clear_cache(self) -> None:
        """Clear client cache with memory release."""
        self._client_cache.clear()
        logger.info("AWS client cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = self._client_cache.get_stats()
        stats.update({
            "cache_implementation": "LRU with memory limits",
            "config": {
                "max_memory_mb": self.config.tools.client_cache_memory_mb,
                "max_clients": self.config.tools.max_cached_clients
            }
        })
        return stats
    
    def handle_memory_pressure(self) -> Dict[str, Any]:
        """Emergency memory pressure handler."""
        current_stats = self.get_cache_stats()
        target_memory_mb = int(current_stats["max_memory_mb"] * 0.6)  # Reduce to 60% of limit
        
        evicted_count = self._client_cache.purge_under_pressure(target_memory_mb)
        
        new_stats = self.get_cache_stats()
        
        return {
            "action": "memory_pressure_purge",
            "evicted_clients": evicted_count,
            "target_memory_mb": target_memory_mb,
            "memory_before_mb": current_stats["current_memory_mb"],
            "memory_after_mb": new_stats["current_memory_mb"],
            "clients_before": current_stats["num_clients"],
            "clients_after": new_stats["num_clients"]
        }
    
    def validate_credentials(self) -> Dict[str, Any]:
        """Validate current AWS credentials."""
        try:
            session = self.credential_manager.get_session()
            sts = session.client('sts', config=self.client_config)
            
            identity = sts.get_caller_identity()
            return {
                "valid": True,
                "account": identity.get('Account'),
                "arn": identity.get('Arn'),
                "user_id": identity.get('UserId'),
                "cache_stats": self.get_cache_stats()
            }
            
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
                "cache_stats": self.get_cache_stats()
            }
    
    async def execute_with_retry(self, operation, *args, **kwargs) -> Any:
        """Execute AWS operation with retry logic and performance monitoring."""
        max_retries = self.config.aws.max_retries
        
        try:
            from ..utils.performance_monitor import get_performance_monitor
            monitor = get_performance_monitor()
        except ImportError:
            monitor = None
        
        if monitor:
            async with monitor.monitor_async_operation("aws_operation_with_retry"):
                return await self._execute_with_retry_impl(operation, max_retries, *args, **kwargs)
        else:
            return await self._execute_with_retry_impl(operation, max_retries, *args, **kwargs)
    
    async def _execute_with_retry_impl(self, operation, max_retries: int, *args, **kwargs) -> Any:
        for attempt in range(max_retries + 1):
            try:
                return await operation(*args, **kwargs)
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                
                if error_code in ['Throttling', 'RequestLimitExceeded', 'ServiceUnavailable']:
                    if attempt < max_retries:
                        wait_time = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                        logger.warning(f"Rate limited, retrying in {wait_time}s (attempt {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        continue
                
                logger.error(f"AWS operation failed: {error_code} - {e}")
                raise AWSClientError(f"AWS operation failed: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected error in AWS operation: {e}")
                raise AWSClientError(f"Operation failed: {e}")
        
        raise AWSClientError(f"Operation failed after {max_retries} retries")
    
    @asynccontextmanager
    async def client_context(self, service_name: str, region: str):
        """
        Async context manager for AWS client with proper resource management.
        
        This method provides secure client access with automatic cleanup and error handling.
        
        Args:
            service_name: AWS service name (e.g., 'ec2', 'networkmanager')
            region: AWS region (e.g., 'us-west-2')
            
        Yields:
            AWS client instance with async methods wrapped
            
        Security features:
        - Input validation for service name and region
        - Automatic resource cleanup
        - Error handling with context preservation
        """
        # Input validation for security
        if not service_name or not isinstance(service_name, str):
            raise ValueError("service_name must be a non-empty string")
        if not region or not isinstance(region, str):
            raise ValueError("region must be a non-empty string")
        
        # Validate service name format (security check)
        import re
        if not re.match(r'^[a-z0-9-]+$', service_name):
            raise ValueError(f"Invalid service name format: {service_name}")
        if not re.match(r'^[a-z0-9-]+$', region):
            raise ValueError(f"Invalid region format: {region}")
        
        try:
            # Get client with caching and security controls
            client = self.get_client(service_name, region)
            
            # Wrap client methods to be async-compatible
            wrapped_client = AsyncClientWrapper(client)
            
            yield wrapped_client
            
        except Exception as e:
            logger.error(f"Error in client_context for {service_name} in {region}: {e}")
            raise
        finally:
            # Client cleanup is handled by the cache system
            # No additional cleanup needed as boto3 clients are stateless
            pass

    async def execute_multi_region(
        self, 
        service: str, 
        operation: str, 
        regions: List[str], 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute AWS operation across multiple regions concurrently.
        
        Args:
            service: AWS service name
            operation: Operation to execute
            regions: List of regions to execute in
            **kwargs: Operation parameters
            
        Returns:
            Dictionary mapping region to results
        """
        results = {}
        errors = {}
        
        async def execute_in_region(region: str):
            try:
                async with self.client_context(service, region) as client:
                    method = getattr(client, operation)
                    result = await method(**kwargs)
                    return region, result
            except Exception as e:
                logger.warning(f"Error executing {operation} in {region}: {e}")
                errors[region] = str(e)
                return region, None
        
        # Execute operations concurrently
        tasks = [execute_in_region(region) for region in regions]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for item in completed:
            if isinstance(item, Exception):
                continue
            region, result = item
            if result is not None:
                results[region] = result
        
        # Include errors in response for debugging
        if errors:
            results['_errors'] = errors
            
        return results

    def cleanup(self) -> None:
        """Clean up resources."""
        self.clear_cache()
        if self._executor:
            self._executor.shutdown(wait=True)
            logger.info("AWS client manager cleanup complete")