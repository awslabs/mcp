"""
AWS Performance Analytics and Monitoring.

This module provides comprehensive performance monitoring and analytics for AWS operations:
- API call latency and throughput tracking
- Memory usage optimization monitoring
- Connection pool performance analytics
- Cost optimization insights
- CloudWatch integration for metrics export
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from threading import Lock, RLock
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

import boto3

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Core performance metrics data structure."""

    timestamp: datetime
    service: str
    region: str
    operation: str
    latency_ms: float
    success: bool
    error_code: Optional[str] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    connection_pool_size: Optional[int] = None
    cache_hit: Optional[bool] = None


@dataclass
class AggregatedMetrics:
    """Aggregated performance metrics over time periods."""

    service: str
    region: str
    time_period: str  # "1m", "5m", "15m", "1h", "1d"
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    error_rate: float = 0.0
    throughput_rps: float = 0.0
    avg_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    cache_hit_rate: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CostMetrics:
    """Cost optimization metrics."""

    service: str
    region: str
    api_calls_count: int = 0
    estimated_cost_usd: float = 0.0
    cost_per_call_usd: float = 0.0
    optimization_potential: float = 0.0  # Percentage
    recommendations: List[str] = field(default_factory=list)


class PerformanceAnalyticsConfig:
    """Configuration for performance analytics."""

    def __init__(
        self,
        enable_cloudwatch: bool = False,
        cloudwatch_namespace: str = "CloudWAN/MCP",
        retention_hours: int = 24,
        aggregation_intervals: List[str] = None,
        enable_cost_tracking: bool = True,
        max_metrics_in_memory: int = 10000,
        export_interval_seconds: int = 300,  # 5 minutes
    ):
        self.enable_cloudwatch = enable_cloudwatch
        self.cloudwatch_namespace = cloudwatch_namespace
        self.retention_hours = retention_hours
        self.aggregation_intervals = aggregation_intervals or ["1m", "5m", "15m", "1h"]
        self.enable_cost_tracking = enable_cost_tracking
        self.max_metrics_in_memory = max_metrics_in_memory
        self.export_interval_seconds = export_interval_seconds


class AWSPerformanceAnalytics:
    """
    Comprehensive AWS performance analytics and monitoring system.

    Features:
    - Real-time performance metrics collection
    - Automatic aggregation over multiple time windows
    - Cost optimization analysis
    - CloudWatch integration
    - Memory and CPU monitoring
    - Connection pool analytics
    """

    def __init__(
        self,
        config: Optional[PerformanceAnalyticsConfig] = None,
        profile: Optional[str] = None,
    ):
        """
        Initialize AWS Performance Analytics.

        Args:
            config: Analytics configuration
            profile: AWS profile for CloudWatch export
        """
        self.config = config or PerformanceAnalyticsConfig()
        self.profile = profile

        # Raw metrics storage
        self._raw_metrics: deque = deque(maxlen=self.config.max_metrics_in_memory)
        self._raw_metrics_lock = Lock()

        # Aggregated metrics storage
        self._aggregated_metrics: Dict[str, Dict[str, AggregatedMetrics]] = defaultdict(dict)
        self._aggregation_lock = RLock()

        # Cost tracking
        self._cost_metrics: Dict[str, CostMetrics] = {}
        self._cost_lock = Lock()

        # Service-specific pricing (simplified)
        self._service_pricing = {
            "ec2": {"DescribeInstances": 0.001, "DescribeVpcs": 0.001},
            "networkmanager": {"GetGlobalNetworks": 0.005, "GetCoreNetworks": 0.005},
            "sts": {"GetCallerIdentity": 0.0005, "AssumeRole": 0.001},
            "logs": {"FilterLogEvents": 0.002, "DescribeLogGroups": 0.001},
        }

        # Background tasks
        self._aggregation_task: Optional[asyncio.Task] = None
        self._export_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # CloudWatch client
        self._cloudwatch_client: Optional[Any] = None
        if self.config.enable_cloudwatch:
            self._initialize_cloudwatch()

        # System monitoring
        self._system_metrics: Dict[str, Any] = {}
        self._last_system_update = time.time()

        logger.info(
            f"AWSPerformanceAnalytics initialized - "
            f"cloudwatch: {self.config.enable_cloudwatch}, "
            f"retention: {self.config.retention_hours}h"
        )

    def _initialize_cloudwatch(self) -> None:
        """Initialize CloudWatch client for metrics export."""
        try:
            if self.profile:
                session = boto3.Session(profile_name=self.profile)
                self._cloudwatch_client = session.client("cloudwatch")
            else:
                self._cloudwatch_client = boto3.client("cloudwatch")

            logger.info("CloudWatch client initialized for metrics export")
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}")
            self.config.enable_cloudwatch = False

    async def start_background_tasks(self) -> None:
        """Start background analytics and export tasks."""
        if self._running:
            return

        self._running = True

        # Start aggregation task
        self._aggregation_task = asyncio.create_task(self._aggregation_loop())

        # Start export task if CloudWatch is enabled
        if self.config.enable_cloudwatch:
            self._export_task = asyncio.create_task(self._export_loop())

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Performance analytics background tasks started")

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        self._running = False

        tasks = [self._aggregation_task, self._export_task, self._cleanup_task]

        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("Performance analytics background tasks stopped")

    def record_api_call(
        self,
        service: str,
        operation: str,
        region: str,
        latency_ms: float,
        success: bool,
        error_code: Optional[str] = None,
        cache_hit: Optional[bool] = None,
    ) -> None:
        """
        Record AWS API call performance metrics.

        Args:
            service: AWS service name
            operation: API operation name
            region: AWS region
            latency_ms: Call latency in milliseconds
            success: Whether the call succeeded
            error_code: Error code if failed
            cache_hit: Whether result came from cache
        """
        # Update system metrics
        self._update_system_metrics()

        # Create performance metric
        metric = PerformanceMetrics(
            timestamp=datetime.now(timezone.utc),
            service=service,
            region=region,
            operation=operation,
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
            memory_usage_mb=self._system_metrics.get("memory_mb"),
            cpu_usage_percent=self._system_metrics.get("cpu_percent"),
            cache_hit=cache_hit,
        )

        # Store raw metric
        with self._raw_metrics_lock:
            self._raw_metrics.append(metric)

        # Update cost tracking
        if self.config.enable_cost_tracking:
            self._update_cost_metrics(service, operation, region)

        logger.debug(
            f"Recorded API call: {service}.{operation} in {region} - "
            f"{latency_ms:.2f}ms, success: {success}"
        )

    def record_session_creation(
        self,
        service: str,
        region: str,
        latency_ms: float,
        cache_hit: bool,
    ) -> None:
        """Record AWS session creation metrics."""
        self.record_api_call(
            service=service,
            operation="CreateSession",
            region=region,
            latency_ms=latency_ms,
            success=True,
            cache_hit=cache_hit,
        )

    def record_task_execution(
        self,
        service: str,
        region: str,
        duration_ms: float,
        success: bool,
        error_code: Optional[str] = None,
    ) -> None:
        """Record thread pool task execution metrics."""
        self.record_api_call(
            service=service,
            operation="TaskExecution",
            region=region,
            latency_ms=duration_ms,
            success=success,
            error_code=error_code,
        )

    def _update_system_metrics(self) -> None:
        """Update system resource metrics."""
        current_time = time.time()

        # Update system metrics every 30 seconds to reduce overhead
        if current_time - self._last_system_update < 30:
            return

        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking

            self._system_metrics = {
                "memory_mb": memory.used / 1024 / 1024,
                "memory_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "timestamp": current_time,
            }

            self._last_system_update = current_time

        except Exception as e:
            logger.warning(f"Failed to update system metrics: {e}")

    def _update_cost_metrics(self, service: str, operation: str, region: str) -> None:
        """Update cost tracking metrics."""
        cost_key = f"{service}:{region}"

        with self._cost_lock:
            if cost_key not in self._cost_metrics:
                self._cost_metrics[cost_key] = CostMetrics(service=service, region=region)

            cost_metric = self._cost_metrics[cost_key]
            cost_metric.api_calls_count += 1

            # Calculate estimated cost
            operation_cost = self._service_pricing.get(service, {}).get(operation, 0.001)
            cost_metric.estimated_cost_usd += operation_cost
            cost_metric.cost_per_call_usd = (
                cost_metric.estimated_cost_usd / cost_metric.api_calls_count
            )

    async def _aggregation_loop(self) -> None:
        """Background task for metrics aggregation."""
        while self._running:
            try:
                await self._aggregate_metrics()
                await asyncio.sleep(60)  # Aggregate every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Aggregation loop error: {e}")
                await asyncio.sleep(60)

    async def _aggregate_metrics(self) -> None:
        """Aggregate raw metrics into time-based buckets."""
        current_time = datetime.now(timezone.utc)

        # Get raw metrics to process
        with self._raw_metrics_lock:
            metrics_to_process = list(self._raw_metrics)

        if not metrics_to_process:
            return

        # Group metrics by service, region, and time intervals
        for interval in self.config.aggregation_intervals:
            interval_seconds = self._parse_interval(interval)
            time_bucket = self._get_time_bucket(current_time, interval_seconds)

            # Group metrics by service and region
            grouped_metrics = defaultdict(list)
            for metric in metrics_to_process:
                if (current_time - metric.timestamp).total_seconds() <= interval_seconds:
                    key = f"{metric.service}:{metric.region}:{interval}:{time_bucket}"
                    grouped_metrics[key].append(metric)

            # Create aggregated metrics
            with self._aggregation_lock:
                for key, metrics in grouped_metrics.items():
                    service, region, interval_str, time_bucket_str = key.split(":")
                    agg_key = f"{service}:{region}:{interval_str}"

                    if agg_key not in self._aggregated_metrics:
                        self._aggregated_metrics[agg_key] = {}

                    self._aggregated_metrics[agg_key][time_bucket_str] = (
                        self._create_aggregated_metric(service, region, interval_str, metrics)
                    )

    def _parse_interval(self, interval: str) -> int:
        """Parse interval string to seconds."""
        if interval.endswith("m"):
            return int(interval[:-1]) * 60
        elif interval.endswith("h"):
            return int(interval[:-1]) * 3600
        elif interval.endswith("d"):
            return int(interval[:-1]) * 86400
        else:
            return 60  # Default to 1 minute

    def _get_time_bucket(self, timestamp: datetime, interval_seconds: int) -> str:
        """Get time bucket for aggregation."""
        bucket_start = timestamp.replace(second=0, microsecond=0)
        bucket_start = bucket_start.replace(
            minute=(bucket_start.minute // (interval_seconds // 60)) * (interval_seconds // 60)
        )
        return bucket_start.isoformat()

    def _create_aggregated_metric(
        self,
        service: str,
        region: str,
        time_period: str,
        metrics: List[PerformanceMetrics],
    ) -> AggregatedMetrics:
        """Create aggregated metric from raw metrics."""
        if not metrics:
            return AggregatedMetrics(service=service, region=region, time_period=time_period)

        latencies = [m.latency_ms for m in metrics]
        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]
        cached = [m for m in metrics if m.cache_hit is True]
        memory_values = [m.memory_usage_mb for m in metrics if m.memory_usage_mb is not None]
        cpu_values = [m.cpu_usage_percent for m in metrics if m.cpu_usage_percent is not None]

        return AggregatedMetrics(
            service=service,
            region=region,
            time_period=time_period,
            total_requests=len(metrics),
            successful_requests=len(successful),
            failed_requests=len(failed),
            avg_latency_ms=statistics.mean(latencies),
            p50_latency_ms=statistics.median(latencies),
            p95_latency_ms=(
                statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)
            ),
            p99_latency_ms=(
                statistics.quantiles(latencies, n=100)[98]
                if len(latencies) > 100
                else max(latencies)
            ),
            max_latency_ms=max(latencies),
            min_latency_ms=min(latencies),
            error_rate=len(failed) / len(metrics),
            throughput_rps=len(metrics) / self._parse_interval(time_period),
            avg_memory_mb=statistics.mean(memory_values) if memory_values else 0.0,
            avg_cpu_percent=statistics.mean(cpu_values) if cpu_values else 0.0,
            cache_hit_rate=len(cached) / len(metrics) if metrics else 0.0,
            start_time=min(m.timestamp for m in metrics),
            end_time=max(m.timestamp for m in metrics),
        )

    async def _export_loop(self) -> None:
        """Background task for CloudWatch metrics export."""
        while self._running:
            try:
                await self._export_to_cloudwatch()
                await asyncio.sleep(self.config.export_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Export loop error: {e}")
                await asyncio.sleep(300)  # Wait longer on error

    async def _export_to_cloudwatch(self) -> None:
        """Export aggregated metrics to CloudWatch."""
        if not self._cloudwatch_client:
            return

        current_time = datetime.now(timezone.utc)
        metric_data = []

        with self._aggregation_lock:
            for agg_key, time_buckets in self._aggregated_metrics.items():
                service, region, interval = agg_key.split(":")

                for time_bucket, agg_metric in time_buckets.items():
                    # Only export recent metrics
                    if (current_time - agg_metric.end_time).total_seconds() > 3600:
                        continue

                    # Create CloudWatch metric data
                    base_dimensions = [
                        {"Name": "Service", "Value": service},
                        {"Name": "Region", "Value": region},
                        {"Name": "Interval", "Value": interval},
                    ]

                    metric_data.extend(
                        [
                            {
                                "MetricName": "RequestCount",
                                "Dimensions": base_dimensions,
                                "Value": agg_metric.total_requests,
                                "Unit": "Count",
                                "Timestamp": agg_metric.end_time,
                            },
                            {
                                "MetricName": "AvgLatency",
                                "Dimensions": base_dimensions,
                                "Value": agg_metric.avg_latency_ms,
                                "Unit": "Milliseconds",
                                "Timestamp": agg_metric.end_time,
                            },
                            {
                                "MetricName": "ErrorRate",
                                "Dimensions": base_dimensions,
                                "Value": agg_metric.error_rate * 100,
                                "Unit": "Percent",
                                "Timestamp": agg_metric.end_time,
                            },
                            {
                                "MetricName": "Throughput",
                                "Dimensions": base_dimensions,
                                "Value": agg_metric.throughput_rps,
                                "Unit": "Count/Second",
                                "Timestamp": agg_metric.end_time,
                            },
                        ]
                    )

        # Send metrics to CloudWatch in batches
        if metric_data:
            try:
                # CloudWatch accepts max 20 metrics per call
                for i in range(0, len(metric_data), 20):
                    batch = metric_data[i : i + 20]
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._cloudwatch_client.put_metric_data(
                            Namespace=self.config.cloudwatch_namespace, MetricData=batch
                        ),
                    )

                logger.debug(f"Exported {len(metric_data)} metrics to CloudWatch")

            except Exception as e:
                logger.error(f"Failed to export metrics to CloudWatch: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up old metrics."""
        while self._running:
            try:
                await self._cleanup_old_metrics()
                await asyncio.sleep(3600)  # Cleanup every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)

    async def _cleanup_old_metrics(self) -> None:
        """Clean up old aggregated metrics to prevent memory leaks."""
        current_time = datetime.now(timezone.utc)
        retention_cutoff = current_time - timedelta(hours=self.config.retention_hours)

        with self._aggregation_lock:
            keys_to_remove = []

            for agg_key, time_buckets in self._aggregated_metrics.items():
                buckets_to_remove = []

                for time_bucket, agg_metric in time_buckets.items():
                    if agg_metric.end_time < retention_cutoff:
                        buckets_to_remove.append(time_bucket)

                for bucket in buckets_to_remove:
                    del time_buckets[bucket]

                if not time_buckets:
                    keys_to_remove.append(agg_key)

            for key in keys_to_remove:
                del self._aggregated_metrics[key]

        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} old metric aggregations")

    def get_performance_summary(
        self,
        service: Optional[str] = None,
        region: Optional[str] = None,
        time_period: str = "1h",
    ) -> Dict[str, Any]:
        """
        Get performance summary for specified filters.

        Args:
            service: Filter by service name
            region: Filter by region
            time_period: Time period for aggregation

        Returns:
            Performance summary dictionary
        """
        with self._aggregation_lock:
            matching_metrics = []

            for agg_key, time_buckets in self._aggregated_metrics.items():
                agg_service, agg_region, agg_interval = agg_key.split(":")

                if (
                    (service and agg_service != service)
                    or (region and agg_region != region)
                    or (agg_interval != time_period)
                ):
                    continue

                # Get the most recent time bucket
                if time_buckets:
                    latest_bucket = max(time_buckets.keys())
                    matching_metrics.append(time_buckets[latest_bucket])

        if not matching_metrics:
            return {"error": "No metrics found for specified filters"}

        # Aggregate across all matching metrics
        total_requests = sum(m.total_requests for m in matching_metrics)
        total_successful = sum(m.successful_requests for m in matching_metrics)
        total_failed = sum(m.failed_requests for m in matching_metrics)

        all_latencies = []
        for m in matching_metrics:
            all_latencies.extend([m.avg_latency_ms] * m.total_requests)

        return {
            "summary": {
                "total_requests": total_requests,
                "success_rate": (total_successful / total_requests if total_requests > 0 else 0),
                "error_rate": (total_failed / total_requests if total_requests > 0 else 0),
                "avg_latency_ms": (statistics.mean(all_latencies) if all_latencies else 0),
                "total_throughput_rps": sum(m.throughput_rps for m in matching_metrics),
            },
            "by_service_region": [
                {
                    "service": m.service,
                    "region": m.region,
                    "requests": m.total_requests,
                    "success_rate": (
                        m.successful_requests / m.total_requests if m.total_requests > 0 else 0
                    ),
                    "avg_latency_ms": m.avg_latency_ms,
                    "p95_latency_ms": m.p95_latency_ms,
                    "throughput_rps": m.throughput_rps,
                    "cache_hit_rate": m.cache_hit_rate,
                }
                for m in matching_metrics
            ],
            "filters": {
                "service": service,
                "region": region,
                "time_period": time_period,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_cost_analysis(self) -> Dict[str, Any]:
        """Get cost analysis and optimization recommendations."""
        with self._cost_lock:
            cost_metrics = list(self._cost_metrics.values())

        if not cost_metrics:
            return {"message": "No cost data available"}

        total_cost = sum(c.estimated_cost_usd for c in cost_metrics)
        total_calls = sum(c.api_calls_count for c in cost_metrics)

        # Sort by cost to identify most expensive services
        cost_metrics.sort(key=lambda x: x.estimated_cost_usd, reverse=True)

        # Generate optimization recommendations
        recommendations = []
        for cost_metric in cost_metrics[:5]:  # Top 5 most expensive
            if cost_metric.api_calls_count > 1000:
                recommendations.append(
                    f"Consider caching for {cost_metric.service} in {cost_metric.region} "
                    f"({cost_metric.api_calls_count} calls, ${cost_metric.estimated_cost_usd:.4f})"
                )

        return {
            "total_estimated_cost_usd": total_cost,
            "total_api_calls": total_calls,
            "avg_cost_per_call": total_cost / total_calls if total_calls > 0 else 0,
            "cost_by_service": [
                {
                    "service": c.service,
                    "region": c.region,
                    "api_calls": c.api_calls_count,
                    "estimated_cost_usd": c.estimated_cost_usd,
                    "cost_per_call_usd": c.cost_per_call_usd,
                }
                for c in cost_metrics
            ],
            "optimization_recommendations": recommendations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health and resource utilization."""
        self._update_system_metrics()

        # Get recent performance trends
        with self._raw_metrics_lock:
            recent_metrics = [
                m
                for m in self._raw_metrics
                if (datetime.now(timezone.utc) - m.timestamp).total_seconds() < 300
            ]

        success_rate = (
            len([m for m in recent_metrics if m.success]) / len(recent_metrics)
            if recent_metrics
            else 1.0
        )

        avg_latency = (
            statistics.mean([m.latency_ms for m in recent_metrics]) if recent_metrics else 0.0
        )

        return {
            "system_resources": self._system_metrics,
            "recent_performance": {
                "requests_last_5min": len(recent_metrics),
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency,
            },
            "metrics_storage": {
                "raw_metrics_count": len(self._raw_metrics),
                "aggregated_keys": len(self._aggregated_metrics),
                "memory_usage_estimate_mb": (
                    len(self._raw_metrics) * 0.001  # Rough estimate
                    + len(self._aggregated_metrics) * 0.01
                ),
            },
            "configuration": {
                "cloudwatch_enabled": self.config.enable_cloudwatch,
                "cost_tracking_enabled": self.config.enable_cost_tracking,
                "retention_hours": self.config.retention_hours,
                "max_metrics_in_memory": self.config.max_metrics_in_memory,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def export_metrics_to_file(self, file_path: str) -> None:
        """Export all metrics to a JSON file."""
        try:
            with self._raw_metrics_lock:
                raw_data = [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "service": m.service,
                        "region": m.region,
                        "operation": m.operation,
                        "latency_ms": m.latency_ms,
                        "success": m.success,
                        "error_code": m.error_code,
                        "memory_usage_mb": m.memory_usage_mb,
                        "cpu_usage_percent": m.cpu_usage_percent,
                        "cache_hit": m.cache_hit,
                    }
                    for m in self._raw_metrics
                ]

            with self._aggregation_lock:
                agg_data = {}
                for agg_key, time_buckets in self._aggregated_metrics.items():
                    agg_data[agg_key] = {
                        bucket: {
                            "service": m.service,
                            "region": m.region,
                            "time_period": m.time_period,
                            "total_requests": m.total_requests,
                            "successful_requests": m.successful_requests,
                            "failed_requests": m.failed_requests,
                            "avg_latency_ms": m.avg_latency_ms,
                            "p95_latency_ms": m.p95_latency_ms,
                            "error_rate": m.error_rate,
                            "throughput_rps": m.throughput_rps,
                            "cache_hit_rate": m.cache_hit_rate,
                            "start_time": m.start_time.isoformat(),
                            "end_time": m.end_time.isoformat(),
                        }
                        for bucket, m in time_buckets.items()
                    }

            export_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "raw_metrics": raw_data,
                "aggregated_metrics": agg_data,
                "cost_metrics": {
                    key: {
                        "service": c.service,
                        "region": c.region,
                        "api_calls_count": c.api_calls_count,
                        "estimated_cost_usd": c.estimated_cost_usd,
                        "cost_per_call_usd": c.cost_per_call_usd,
                    }
                    for key, c in self._cost_metrics.items()
                },
                "system_metrics": self._system_metrics,
            }

            with open(file_path, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported metrics to {file_path}")

        except Exception as e:
            logger.error(f"Failed to export metrics to file: {e}")
            raise

    async def close(self) -> None:
        """Clean up analytics resources."""
        logger.info("Closing AWS Performance Analytics")
        await self.stop_background_tasks()

        # Clear all data
        with self._raw_metrics_lock:
            self._raw_metrics.clear()

        with self._aggregation_lock:
            self._aggregated_metrics.clear()

        with self._cost_lock:
            self._cost_metrics.clear()

        logger.info("AWS Performance Analytics closed")

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            # Can't run async cleanup in __del__, just clear data
            self._raw_metrics.clear()
            self._aggregated_metrics.clear()
            self._cost_metrics.clear()
        except Exception:
            pass  # Ignore cleanup errors during destruction
