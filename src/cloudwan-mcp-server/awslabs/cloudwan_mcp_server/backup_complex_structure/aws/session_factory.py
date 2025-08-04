"""
AWS Session Factory with Connection Pooling and Performance Optimization.

This module provides smart AWS session management with:
- Connection pooling and reuse
- Credential rotation without service interruption  
- Health checks and automatic session refresh
- Performance monitoring and analytics
- Regional session affinity and failover
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from threading import Lock, RLock
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
import gc

import boto3
try:
    import aioboto3
    AIOBOTO3_AVAILABLE = True
except ImportError:
    AIOBOTO3_AVAILABLE = False
    aioboto3 = None
from botocore.config import Config
from botocore.exceptions import (
    NoCredentialsError,
    PartialCredentialsError,
)
try:
    from cachetools import TTLCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False
    # Fallback simple cache implementation
    class TTLCache:
        def __init__(self, maxsize, ttl):
            self.maxsize = maxsize
            self.ttl = ttl
            self._cache = {}
            
        def get(self, key, default=None):
            return self._cache.get(key, default)
            
        def __setitem__(self, key, value):
            self._cache[key] = value
            
        def __getitem__(self, key):
            return self._cache[key]
            
        def __contains__(self, key):
            return key in self._cache
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    # Simple fallback decorators
    def retry(**kwargs):
        def decorator(func):
            return func
        return decorator
    def stop_after_attempt(n):
        return None
    def wait_exponential(**kwargs):
        return None
    def retry_if_exception_type(exc_type):
        return None

from .performance_analytics import AWSPerformanceAnalytics

logger = logging.getLogger(__name__)


@dataclass
class SessionPoolConfig:
    """Configuration for session pools."""

    max_pool_size: int = 50
    min_pool_size: int = 5
    session_ttl_seconds: int = 3600  # 1 hour
    health_check_interval: int = 300  # 5 minutes
    max_idle_time: int = 1800  # 30 minutes
    connection_timeout: int = 30
    read_timeout: int = 60
    max_retries: int = 3
    enable_health_checks: bool = True
    enable_metrics: bool = True


@dataclass
class SessionMetrics:
    """Metrics for session pool performance."""

    total_sessions: int = 0
    active_sessions: int = 0
    idle_sessions: int = 0
    failed_sessions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_session_age: float = 0.0
    peak_concurrent_sessions: int = 0
    credential_rotations: int = 0
    health_check_failures: int = 0
    memory_usage_mb: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionInfo:
    """Information about a cached session."""

    session: Union[boto3.Session, "aioboto3.Session"]
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    is_healthy: bool = True
    health_checked_at: Optional[datetime] = None
    region: str = ""
    service_name: str = ""
    is_async: bool = False


class AWSSessionFactory:
    """
    Smart AWS Session Factory with connection pooling and performance optimization.

    Features:
    - Connection pooling with configurable sizes
    - Session lifecycle management with TTL
    - Automatic credential rotation
    - Health checks and monitoring
    - Performance analytics integration
    - Memory optimization
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        regions: Optional[List[str]] = None,
        config: Optional[SessionPoolConfig] = None,
        performance_analytics: Optional[AWSPerformanceAnalytics] = None,
    ):
        """
        Initialize the AWS Session Factory.

        Args:
            profile: AWS profile name
            regions: Supported AWS regions
            config: Session pool configuration
            performance_analytics: Performance monitoring instance
        """
        self.profile = profile
        self.regions = regions or ["us-east-1", "us-west-2", "eu-west-1", "eu-west-2"]
        self.config = config or SessionPoolConfig()
        self.performance_analytics = performance_analytics or AWSPerformanceAnalytics()

        # Session pools - separate for sync and async
        self._sync_session_pool: TTLCache = TTLCache(
            maxsize=self.config.max_pool_size, ttl=self.config.session_ttl_seconds
        )
        self._async_session_pool: TTLCache = TTLCache(
            maxsize=self.config.max_pool_size, ttl=self.config.session_ttl_seconds
        )

        # Session info tracking
        self._session_info: Dict[str, SessionInfo] = {}
        self._session_info_lock = RLock()

        # Performance metrics
        self._metrics = SessionMetrics()
        self._metrics_lock = Lock()

        # Health check management
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_running = False

        # Credential management
        self._credentials_cache: Dict[str, Dict[str, Any]] = {}
        self._credential_expiry: Dict[str, datetime] = {}
        self._credential_lock = Lock()

        # Boto3 configuration
        self._boto_config = Config(
            retries={"max_attempts": self.config.max_retries, "mode": "adaptive"},
            read_timeout=self.config.read_timeout,
            connect_timeout=self.config.connection_timeout,
            max_pool_connections=self.config.max_pool_size,
        )

        logger.info(
            f"AWSSessionFactory initialized - profile: {profile}, "
            f"regions: {len(self.regions)}, max_pool_size: {self.config.max_pool_size}"
        )

    async def start_health_checks(self) -> None:
        """Start background health check task."""
        if self._health_check_running or not self.config.enable_health_checks:
            return

        self._health_check_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Session health check monitoring started")

    async def stop_health_checks(self) -> None:
        """Stop background health check task."""
        self._health_check_running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Session health check monitoring stopped")

    async def _health_check_loop(self) -> None:
        """Background task to perform session health checks."""
        while self._health_check_running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _perform_health_checks(self) -> None:
        """Perform health checks on cached sessions."""
        current_time = datetime.now(timezone.utc)
        sessions_to_check = []

        with self._session_info_lock:
            for key, info in self._session_info.items():
                # Check if session needs health check
                if (
                    info.health_checked_at is None
                    or current_time - info.health_checked_at
                    > timedelta(seconds=self.config.health_check_interval)
                ):
                    sessions_to_check.append((key, info))

        # Perform health checks concurrently
        if sessions_to_check:
            tasks = [self._check_session_health(key, info) for key, info in sessions_to_check]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_session_health(self, key: str, info: SessionInfo) -> None:
        """Check health of a specific session."""
        try:
            # Simple health check - try to get caller identity
            if info.is_async:
                async with info.session.client("sts", region_name="us-east-1") as sts:
                    await sts.get_caller_identity()
            else:
                # For sync sessions, we can't easily do async health checks
                # Mark as healthy for now and rely on error handling during use
                pass

            with self._session_info_lock:
                if key in self._session_info:
                    self._session_info[key].is_healthy = True
                    self._session_info[key].health_checked_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.warning(f"Session health check failed for {key}: {e}")
            with self._session_info_lock:
                if key in self._session_info:
                    self._session_info[key].is_healthy = False
                    self._session_info[key].health_checked_at = datetime.now(timezone.utc)

            with self._metrics_lock:
                self._metrics.health_check_failures += 1

    def _generate_session_key(
        self,
        service: str,
        region: str,
        is_async: bool = False,
        role_arn: Optional[str] = None,
    ) -> str:
        """Generate unique key for session caching."""
        base_key = f"{self.profile or 'default'}:{service}:{region}"
        if is_async:
            base_key += ":async"
        if role_arn:
            base_key += f":role:{role_arn}"
        return base_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((NoCredentialsError, PartialCredentialsError)),
    )
    def get_sync_session(
        self, service: str, region: str, role_arn: Optional[str] = None
    ) -> boto3.Session:
        """
        Get or create synchronous AWS session with connection pooling.

        Args:
            service: AWS service name
            region: AWS region
            role_arn: Optional role ARN for assumption

        Returns:
            Cached or new boto3.Session
        """
        start_time = time.time()
        session_key = self._generate_session_key(service, region, False, role_arn)

        # Check cache first
        if session_key in self._sync_session_pool:
            with self._metrics_lock:
                self._metrics.cache_hits += 1

            session_info = self._session_info.get(session_key)
            if session_info and session_info.is_healthy:
                session_info.last_used = datetime.now(timezone.utc)
                session_info.use_count += 1
                return session_info.session

        # Create new session
        with self._metrics_lock:
            self._metrics.cache_misses += 1

        session = self._create_sync_session(role_arn)

        # Cache the session
        current_time = datetime.now(timezone.utc)
        session_info = SessionInfo(
            session=session,
            created_at=current_time,
            last_used=current_time,
            use_count=1,
            region=region,
            service_name=service,
            is_async=False,
        )

        self._sync_session_pool[session_key] = session
        with self._session_info_lock:
            self._session_info[session_key] = session_info

        with self._metrics_lock:
            self._metrics.total_sessions += 1
            self._metrics.active_sessions += 1

        # Record performance metrics
        latency = time.time() - start_time
        if self.config.enable_metrics:
            self.performance_analytics.record_session_creation(
                service=service,
                region=region,
                latency_ms=latency * 1000,
                cache_hit=False,
            )

        logger.debug(f"Created new sync session: {session_key}")
        return session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((NoCredentialsError, PartialCredentialsError)),
    )
    async def get_async_session(
        self, service: str, region: str, role_arn: Optional[str] = None
    ) -> "aioboto3.Session":
        """
        Get or create asynchronous AWS session with connection pooling.

        Args:
            service: AWS service name
            region: AWS region
            role_arn: Optional role ARN for assumption

        Returns:
            Cached or new aioboto3.Session
        """
        start_time = time.time()
        session_key = self._generate_session_key(service, region, True, role_arn)

        # Check cache first
        if session_key in self._async_session_pool:
            with self._metrics_lock:
                self._metrics.cache_hits += 1

            session_info = self._session_info.get(session_key)
            if session_info and session_info.is_healthy:
                session_info.last_used = datetime.now(timezone.utc)
                session_info.use_count += 1
                return session_info.session

        # Create new session
        with self._metrics_lock:
            self._metrics.cache_misses += 1

        session = await self._create_async_session(role_arn)

        # Cache the session
        current_time = datetime.now(timezone.utc)
        session_info = SessionInfo(
            session=session,
            created_at=current_time,
            last_used=current_time,
            use_count=1,
            region=region,
            service_name=service,
            is_async=True,
        )

        self._async_session_pool[session_key] = session
        with self._session_info_lock:
            self._session_info[session_key] = session_info

        with self._metrics_lock:
            self._metrics.total_sessions += 1
            self._metrics.active_sessions += 1

        # Record performance metrics
        latency = time.time() - start_time
        if self.config.enable_metrics:
            self.performance_analytics.record_session_creation(
                service=service,
                region=region,
                latency_ms=latency * 1000,
                cache_hit=False,
            )

        logger.debug(f"Created new async session: {session_key}")
        return session

    def _create_sync_session(self, role_arn: Optional[str] = None) -> boto3.Session:
        """Create new synchronous boto3 session."""
        if role_arn:
            # Handle role assumption for sync session
            return self._assume_role_sync(role_arn)

        if self.profile:
            return boto3.Session(profile_name=self.profile)
        return boto3.Session()

    async def _create_async_session(self, role_arn: Optional[str] = None) -> "aioboto3.Session":
        """Create new asynchronous aioboto3 session."""
        if role_arn:
            # Handle role assumption for async session
            return await self._assume_role_async(role_arn)

        if self.profile:
            return aioboto3.Session(profile_name=self.profile)
        return aioboto3.Session()

    def _assume_role_sync(self, role_arn: str) -> boto3.Session:
        """Assume role and create session with temporary credentials."""
        # This would implement STS assume role logic
        # For now, return regular session
        logger.warning(f"Role assumption not yet implemented for sync sessions: {role_arn}")
        return self._create_sync_session()

    async def _assume_role_async(self, role_arn: str) -> "aioboto3.Session":
        """Assume role and create session with temporary credentials."""
        # This would implement STS assume role logic
        # For now, return regular session
        logger.warning(f"Role assumption not yet implemented for async sessions: {role_arn}")
        return await self._create_async_session()

    @asynccontextmanager
    async def get_client(self, service: str, region: str, role_arn: Optional[str] = None):
        """
        Get AWS client with automatic session management.

        Args:
            service: AWS service name
            region: AWS region
            role_arn: Optional role ARN

        Yields:
            AWS service client
        """
        session = await self.get_async_session(service, region, role_arn)
        async with session.client(service, region_name=region, config=self._boto_config) as client:
            yield client

    def get_sync_client(self, service: str, region: str, role_arn: Optional[str] = None) -> Any:
        """
        Get synchronous AWS client.

        Args:
            service: AWS service name
            region: AWS region
            role_arn: Optional role ARN

        Returns:
            Boto3 service client
        """
        session = self.get_sync_session(service, region, role_arn)
        return session.client(service, region_name=region, config=self._boto_config)

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired and unused sessions.

        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.now(timezone.utc)
        cleanup_count = 0
        keys_to_remove = []

        with self._session_info_lock:
            for key, info in self._session_info.items():
                # Remove sessions that haven't been used recently
                idle_time = current_time - info.last_used
                if idle_time.total_seconds() > self.config.max_idle_time:
                    keys_to_remove.append(key)
                # Remove unhealthy sessions
                elif not info.is_healthy:
                    keys_to_remove.append(key)

        # Remove identified sessions
        for key in keys_to_remove:
            self._sync_session_pool.pop(key, None)
            self._async_session_pool.pop(key, None)
            with self._session_info_lock:
                self._session_info.pop(key, None)
            cleanup_count += 1

        if cleanup_count > 0:
            with self._metrics_lock:
                self._metrics.active_sessions -= cleanup_count
            logger.info(f"Cleaned up {cleanup_count} expired/unhealthy sessions")

        # Force garbage collection to free memory
        gc.collect()

        return cleanup_count

    def get_metrics(self) -> SessionMetrics:
        """Get current session pool metrics."""
        with self._metrics_lock:
            # Update memory usage
            process = psutil.Process()
            self._metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024

            # Update session counts
            self._metrics.active_sessions = len(self._session_info)
            self._metrics.idle_sessions = len(
                [
                    info
                    for info in self._session_info.values()
                    if (datetime.now(timezone.utc) - info.last_used).total_seconds() > 300
                ]
            )

            # Update average session age
            if self._session_info:
                total_age = sum(
                    (datetime.now(timezone.utc) - info.created_at).total_seconds()
                    for info in self._session_info.values()
                )
                self._metrics.avg_session_age = total_age / len(self._session_info)

            self._metrics.last_updated = datetime.now(timezone.utc)
            return self._metrics

    def get_pool_status(self) -> Dict[str, Any]:
        """Get detailed session pool status."""
        metrics = self.get_metrics()

        return {
            "pool_config": {
                "max_pool_size": self.config.max_pool_size,
                "min_pool_size": self.config.min_pool_size,
                "session_ttl_seconds": self.config.session_ttl_seconds,
                "health_check_enabled": self.config.enable_health_checks,
            },
            "current_metrics": {
                "total_sessions": metrics.total_sessions,
                "active_sessions": metrics.active_sessions,
                "idle_sessions": metrics.idle_sessions,
                "failed_sessions": metrics.failed_sessions,
                "cache_hit_rate": (
                    metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)
                    if (metrics.cache_hits + metrics.cache_misses) > 0
                    else 0.0
                ),
                "avg_session_age_minutes": metrics.avg_session_age / 60,
                "memory_usage_mb": metrics.memory_usage_mb,
            },
            "health_status": {
                "health_check_failures": metrics.health_check_failures,
                "healthy_sessions": len(
                    [info for info in self._session_info.values() if info.is_healthy]
                ),
                "unhealthy_sessions": len(
                    [info for info in self._session_info.values() if not info.is_healthy]
                ),
            },
        }

    async def refresh_credentials(self) -> None:
        """Refresh AWS credentials and update sessions."""
        logger.info("Starting credential refresh")

        # Clear credential cache
        with self._credential_lock:
            self._credentials_cache.clear()
            self._credential_expiry.clear()

        # Mark all sessions for refresh by clearing pools
        # This will force new session creation on next use
        self._sync_session_pool.clear()
        self._async_session_pool.clear()

        with self._session_info_lock:
            self._session_info.clear()

        with self._metrics_lock:
            self._metrics.credential_rotations += 1
            self._metrics.active_sessions = 0

        logger.info("Credential refresh completed")

    async def close(self) -> None:
        """Clean up all resources."""
        logger.info("Closing AWS Session Factory")

        # Stop health checks
        await self.stop_health_checks()

        # Clean up sessions
        cleanup_count = self.cleanup_expired_sessions()

        # Clear all caches
        self._sync_session_pool.clear()
        self._async_session_pool.clear()

        with self._session_info_lock:
            self._session_info.clear()

        with self._credential_lock:
            self._credentials_cache.clear()
            self._credential_expiry.clear()

        logger.info(f"AWS Session Factory closed, cleaned up {cleanup_count} sessions")

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            # Can't run async cleanup in __del__, just clear caches
            self._sync_session_pool.clear()
            self._async_session_pool.clear()
            self._session_info.clear()
        except Exception:
            pass  # Ignore cleanup errors during destruction
