"""Cache configuration module for CloudWAN MCP server."""

from pydantic import BaseSettings, Field


class CacheConfig(BaseSettings):
    """Configuration for caching behavior."""
    client_pool_size: int = 100
    idle_timeout_seconds: int = 300
    max_memory_mb: int = 512
    cleanup_interval_seconds: int = 60
    health_check_interval: int = 30

    class Config:
        """Pydantic configuration."""
        env_prefix = "CLOUDWAN_CACHE_"
        case_sensitive = False


class MonitoringConfig(BaseSettings):
    """Configuration for monitoring and circuit breakers."""
    metrics_interval: float = Field(1.0, env="CLOUDWAN_METRICS_INTERVAL")
    circuit_breaker_threshold: int = Field(5, env="CLOUDWAN_CIRCUIT_BREAKER_THRESHOLD")
    health_check_timeout: float = Field(5.0, env="CLOUDWAN_HEALTH_CHECK_TIMEOUT")


class ProductionConfig(BaseSettings):
    """Production-ready configuration combining cache and monitoring."""
    cache: CacheConfig = Field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
