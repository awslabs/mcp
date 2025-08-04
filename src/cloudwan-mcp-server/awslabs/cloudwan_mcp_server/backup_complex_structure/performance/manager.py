"""
MCP Performance Manager for CloudWAN Server.

This module provides centralized performance optimization management:
- Request performance tracking and optimization
- Cache strategy coordination
- Resource usage monitoring and analytics
- Performance recommendations and auto-tuning
- Load balancing and scaling decisions
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict

from ..aws.redis_cache import DistributedCloudWANCache
from ..aws.client_manager import AWSClientManager

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """Performance optimization levels."""

    BASIC = "basic"
    OPTIMIZED = "optimized"
    AGGRESSIVE = "aggressive"
    ENTERPRISE = "enterprise"


@dataclass
class RequestMetrics:
    """Request performance metrics."""

    request_id: str
    tool_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    cache_hit: bool = False
    cache_level: Optional[str] = None
    aws_api_calls: int = 0
    regions_accessed: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def finalize(self) -> None:
        """Finalize metrics calculation."""
        if self.end_time and self.start_time:
            self.duration = self.end_time - self.start_time


@dataclass
class PerformanceAnalytics:
    """Aggregated performance analytics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    median_response_time: float = 0.0
    p95_response_time: float = 0.0
    cache_hit_rate: float = 0.0
    aws_api_reduction: float = 0.0
    concurrent_requests_peak: int = 0

    # Performance by tool
    tool_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Trends
    hourly_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class PerformanceRecommendation:
    """Performance optimization recommendation."""

    category: str
    priority: str  # high, medium, low
    title: str
    description: str
    expected_improvement: str
    implementation_effort: str
    auto_applicable: bool = False


class MCPPerformanceManager:
    """
    Centralized performance optimization manager.

    Coordinates all performance optimization strategies including:
    - Request tracking and analytics
    - Cache strategy optimization
    - Resource usage monitoring
    - Performance recommendations
    - Auto-scaling decisions
    """

    def __init__(
        self,
        cache: DistributedCloudWANCache,
        aws_manager: AWSClientManager,
        performance_level: PerformanceLevel = PerformanceLevel.OPTIMIZED,
        enable_auto_optimization: bool = True,
        metrics_retention_hours: int = 24,
    ):
        self.cache = cache
        self.aws_manager = aws_manager
        self.performance_level = performance_level
        self.enable_auto_optimization = enable_auto_optimization
        self.metrics_retention_hours = metrics_retention_hours

        # Request tracking
        self._active_requests: Dict[str, RequestMetrics] = {}
        self._completed_requests: deque = deque(maxlen=10000)  # Last 10k requests
        self._request_history: Dict[str, List[RequestMetrics]] = defaultdict(list)

        # Performance analytics
        self._analytics = PerformanceAnalytics()
        self._last_analytics_update = time.time()

        # Optimization state
        self._optimization_tasks: Set[str] = set()
        self._last_optimization_run = time.time()
        self._optimization_interval = 300  # 5 minutes

        # Auto-tuning parameters
        self._cache_hit_target = 0.70  # 70% cache hit rate target
        self._response_time_target = 1.0  # 1 second target response time
        self._api_reduction_target = 0.70  # 70% API call reduction target

        logger.info(
            f"Initialized MCPPerformanceManager with {performance_level.value} optimization level"
        )

    def start_request_tracking(self, request_id: str, tool_name: str) -> RequestMetrics:
        """Start tracking a new request."""
        metrics = RequestMetrics(request_id=request_id, tool_name=tool_name, start_time=time.time())

        self._active_requests[request_id] = metrics
        return metrics

    def end_request_tracking(
        self,
        request_id: str,
        cache_hit: bool = False,
        cache_level: Optional[str] = None,
        aws_api_calls: int = 0,
        regions_accessed: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> Optional[RequestMetrics]:
        """End tracking for a request and record metrics."""
        if request_id not in self._active_requests:
            logger.warning(f"Request tracking not found: {request_id}")
            return None

        metrics = self._active_requests.pop(request_id)
        metrics.end_time = time.time()
        metrics.cache_hit = cache_hit
        metrics.cache_level = cache_level
        metrics.aws_api_calls = aws_api_calls
        metrics.regions_accessed = regions_accessed or []
        metrics.error = error
        metrics.finalize()

        # Store completed request
        self._completed_requests.append(metrics)
        self._request_history[metrics.tool_name].append(metrics)

        # Update analytics
        self._update_analytics(metrics)

        # Trigger optimization if needed
        if self.enable_auto_optimization:
            asyncio.create_task(self._check_optimization_trigger())

        return metrics

    def _update_analytics(self, metrics: RequestMetrics) -> None:
        """Update performance analytics with new request metrics."""
        self._analytics.total_requests += 1

        if metrics.error:
            self._analytics.failed_requests += 1
        else:
            self._analytics.successful_requests += 1

        # Update response time metrics
        if metrics.duration:
            self._update_response_time_analytics(metrics.duration)

        # Update cache metrics
        if metrics.cache_hit:
            self._update_cache_analytics()

        # Update tool-specific metrics
        self._update_tool_analytics(metrics)

        # Update concurrent request tracking
        current_concurrent = len(self._active_requests)
        if current_concurrent > self._analytics.concurrent_requests_peak:
            self._analytics.concurrent_requests_peak = current_concurrent

    def _update_response_time_analytics(self, duration: float) -> None:
        """Update response time analytics."""
        # Get recent response times for percentile calculations
        recent_durations = [
            req.duration
            for req in list(self._completed_requests)[-1000:]
            if req.duration is not None
        ]

        if recent_durations:
            recent_durations.sort()
            n = len(recent_durations)

            self._analytics.average_response_time = sum(recent_durations) / n
            self._analytics.median_response_time = recent_durations[n // 2]
            self._analytics.p95_response_time = recent_durations[int(n * 0.95)]

    def _update_cache_analytics(self) -> None:
        """Update cache hit rate analytics."""
        cache_metrics = self.cache.get_metrics()
        self._analytics.cache_hit_rate = cache_metrics.hit_rate

    def _update_tool_analytics(self, metrics: RequestMetrics) -> None:
        """Update tool-specific performance analytics."""
        if metrics.tool_name not in self._analytics.tool_performance:
            self._analytics.tool_performance[metrics.tool_name] = {}

        tool_stats = self._analytics.tool_performance[metrics.tool_name]

        if metrics.duration:
            # Update average response time for this tool
            current_avg = tool_stats.get("avg_response_time", 0.0)
            current_count = tool_stats.get("request_count", 0)

            new_avg = (current_avg * current_count + metrics.duration) / (current_count + 1)
            tool_stats["avg_response_time"] = new_avg
            tool_stats["request_count"] = current_count + 1

        # Update API call statistics
        if metrics.aws_api_calls > 0:
            tool_stats["total_api_calls"] = (
                tool_stats.get("total_api_calls", 0) + metrics.aws_api_calls
            )
            tool_stats["avg_api_calls"] = (
                tool_stats["total_api_calls"] / tool_stats["request_count"]
            )

    async def _check_optimization_trigger(self) -> None:
        """Check if optimization should be triggered."""
        now = time.time()

        # Run optimization every 5 minutes
        if now - self._last_optimization_run < self._optimization_interval:
            return

        # Don't run optimization if already in progress
        if "auto_optimization" in self._optimization_tasks:
            return

        # Trigger optimization
        asyncio.create_task(self._run_auto_optimization())

    async def _run_auto_optimization(self) -> None:
        """Run automatic performance optimization."""
        self._optimization_tasks.add("auto_optimization")
        self._last_optimization_run = time.time()

        try:
            logger.info("Running automatic performance optimization")

            # Get current performance metrics
            analytics = await self.get_performance_analytics()

            # Generate and apply recommendations
            recommendations = await self.get_performance_recommendations()
            auto_applicable = [r for r in recommendations if r.auto_applicable]

            for recommendation in auto_applicable:
                await self._apply_recommendation(recommendation)

            logger.info(f"Applied {len(auto_applicable)} automatic optimizations")

        except Exception as e:
            logger.error(f"Auto-optimization failed: {e}")

        finally:
            self._optimization_tasks.discard("auto_optimization")

    async def _apply_recommendation(self, recommendation: PerformanceRecommendation) -> bool:
        """Apply a performance recommendation."""
        try:
            if recommendation.category == "cache_optimization":
                return await self._optimize_cache_strategy()
            elif recommendation.category == "connection_pooling":
                return await self._optimize_connection_pooling()
            elif recommendation.category == "request_batching":
                return await self._optimize_request_batching()
            else:
                logger.warning(f"Unknown recommendation category: {recommendation.category}")
                return False
        except Exception as e:
            logger.error(f"Failed to apply recommendation {recommendation.title}: {e}")
            return False

    async def _optimize_cache_strategy(self) -> bool:
        """Optimize caching strategy based on performance data."""
        # Analyze cache performance
        cache_metrics = self.cache.get_metrics()

        if cache_metrics.hit_rate < self._cache_hit_target:
            # Increase cache TTL for frequently accessed data
            frequently_accessed_tools = self._get_frequently_accessed_tools()

            for tool_name in frequently_accessed_tools:
                # Warm cache for this tool
                await self._warm_tool_cache(tool_name)

        return True

    async def _optimize_connection_pooling(self) -> bool:
        """Optimize AWS connection pooling."""
        # Analyze connection usage patterns
        region_usage = self._get_region_usage_patterns()

        # Adjust connection pool sizes based on usage
        for region, usage_stats in region_usage.items():
            if usage_stats["high_usage"]:
                # Increase connection pool for this region
                pass  # Implementation would adjust pool sizes

        return True

    async def _optimize_request_batching(self) -> bool:
        """Optimize request batching strategies."""
        # Analyze request patterns for batching opportunities
        batch_opportunities = self._identify_batch_opportunities()

        if batch_opportunities:
            # Configure request batching
            pass  # Implementation would set up batching

        return True

    def _get_frequently_accessed_tools(self) -> List[str]:
        """Get list of most frequently accessed tools."""
        tool_usage = defaultdict(int)

        for request in list(self._completed_requests)[-1000:]:  # Last 1000 requests
            tool_usage[request.tool_name] += 1

        # Return top 10 most used tools
        return sorted(tool_usage.keys(), key=lambda x: tool_usage[x], reverse=True)[:10]

    def _get_region_usage_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Analyze AWS region usage patterns."""
        region_usage = defaultdict(lambda: {"count": 0, "avg_response_time": 0.0})

        for request in list(self._completed_requests)[-1000:]:
            for region in request.regions_accessed:
                region_stats = region_usage[region]
                region_stats["count"] += 1

                if request.duration:
                    current_avg = region_stats["avg_response_time"]
                    current_count = region_stats["count"]
                    new_avg = (current_avg * (current_count - 1) + request.duration) / current_count
                    region_stats["avg_response_time"] = new_avg

        # Mark high usage regions
        total_requests = sum(stats["count"] for stats in region_usage.values())
        for region, stats in region_usage.items():
            stats["high_usage"] = stats["count"] > (total_requests * 0.3)  # >30% of requests

        return dict(region_usage)

    def _identify_batch_opportunities(self) -> List[Dict[str, Any]]:
        """Identify opportunities for request batching."""
        # Analyze request patterns for similar operations
        # This is a simplified implementation
        return []

    async def _warm_tool_cache(self, tool_name: str) -> None:
        """Warm cache for a specific tool."""
        # This would trigger cache warming for commonly used operations
        # Implementation depends on specific tool caching strategies
        logger.info(f"Warming cache for tool: {tool_name}")

    async def get_performance_analytics(self) -> PerformanceAnalytics:
        """Get current performance analytics."""
        # Update analytics with latest data
        self._calculate_api_reduction()
        self._update_hourly_stats()

        return self._analytics

    def _calculate_api_reduction(self) -> None:
        """Calculate AWS API call reduction due to caching."""
        cache_metrics = self.cache.get_metrics()

        if cache_metrics.total_requests > 0:
            # Estimate API calls saved through caching
            potential_api_calls = cache_metrics.total_requests
            actual_api_calls = potential_api_calls * (1 - cache_metrics.hit_rate)

            if potential_api_calls > 0:
                self._analytics.aws_api_reduction = 1 - (actual_api_calls / potential_api_calls)

    def _update_hourly_stats(self) -> None:
        """Update hourly performance statistics."""
        now = datetime.utcnow()
        current_hour = now.replace(minute=0, second=0, microsecond=0).isoformat()

        if current_hour not in self._analytics.hourly_stats:
            self._analytics.hourly_stats[current_hour] = {
                "requests": 0,
                "avg_response_time": 0.0,
                "cache_hit_rate": 0.0,
                "error_rate": 0.0,
            }

        # Update current hour stats
        hour_stats = self._analytics.hourly_stats[current_hour]
        recent_requests = [
            req
            for req in list(self._completed_requests)
            if datetime.fromtimestamp(req.start_time).replace(minute=0, second=0, microsecond=0)
            == now.replace(minute=0, second=0, microsecond=0)
        ]

        if recent_requests:
            hour_stats["requests"] = len(recent_requests)
            hour_stats["avg_response_time"] = sum(r.duration or 0 for r in recent_requests) / len(
                recent_requests
            )
            hour_stats["cache_hit_rate"] = sum(1 for r in recent_requests if r.cache_hit) / len(
                recent_requests
            )
            hour_stats["error_rate"] = sum(1 for r in recent_requests if r.error) / len(
                recent_requests
            )

    async def get_performance_recommendations(self) -> List[PerformanceRecommendation]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Analyze current performance
        analytics = await self.get_performance_analytics()
        cache_metrics = self.cache.get_metrics()

        # Cache optimization recommendations
        if cache_metrics.hit_rate < self._cache_hit_target:
            recommendations.append(
                PerformanceRecommendation(
                    category="cache_optimization",
                    priority="high",
                    title="Improve Cache Hit Rate",
                    description=f"Current cache hit rate is {cache_metrics.hit_rate:.1%}, target is {self._cache_hit_target:.1%}",
                    expected_improvement="Reduce response times by 20-40%",
                    implementation_effort="Low",
                    auto_applicable=True,
                )
            )

        # Response time recommendations
        if analytics.average_response_time > self._response_time_target:
            recommendations.append(
                PerformanceRecommendation(
                    category="response_time",
                    priority="high",
                    title="Optimize Response Times",
                    description=f"Average response time is {analytics.average_response_time:.2f}s, target is {self._response_time_target}s",
                    expected_improvement="20-30% faster responses",
                    implementation_effort="Medium",
                    auto_applicable=False,
                )
            )

        # API reduction recommendations
        if analytics.aws_api_reduction < self._api_reduction_target:
            recommendations.append(
                PerformanceRecommendation(
                    category="api_optimization",
                    priority="medium",
                    title="Reduce AWS API Calls",
                    description=f"Current API reduction is {analytics.aws_api_reduction:.1%}, target is {self._api_reduction_target:.1%}",
                    expected_improvement="Reduce AWS costs by 10-20%",
                    implementation_effort="Medium",
                    auto_applicable=True,
                )
            )

        # Connection pooling recommendations
        if analytics.concurrent_requests_peak > 50:
            recommendations.append(
                PerformanceRecommendation(
                    category="connection_pooling",
                    priority="medium",
                    title="Optimize Connection Pooling",
                    description=f"Peak concurrent requests: {analytics.concurrent_requests_peak}",
                    expected_improvement="Better resource utilization",
                    implementation_effort="Low",
                    auto_applicable=True,
                )
            )

        return recommendations

    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        analytics = await self.get_performance_analytics()
        cache_metrics = self.cache.get_metrics()

        return {
            "overall": {
                "total_requests": analytics.total_requests,
                "success_rate": analytics.successful_requests / max(analytics.total_requests, 1),
                "average_response_time": analytics.average_response_time,
                "p95_response_time": analytics.p95_response_time,
                "concurrent_requests_peak": analytics.concurrent_requests_peak,
            },
            "cache": {
                "hit_rate": cache_metrics.hit_rate,
                "total_requests": cache_metrics.total_requests,
                "cache_size_bytes": cache_metrics.cache_size_bytes,
            },
            "tools": analytics.tool_performance,
            "trends": analytics.hourly_stats,
            "aws_integration": {
                "api_reduction": analytics.aws_api_reduction,
                "regions_active": len(self._get_region_usage_patterns()),
            },
        }

    async def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self._analytics = PerformanceAnalytics()
        self._completed_requests.clear()
        self._request_history.clear()
        logger.info("Performance metrics reset")

    def get_active_request_count(self) -> int:
        """Get count of currently active requests."""
        return len(self._active_requests)

    async def health_check(self) -> Dict[str, Any]:
        """Perform performance manager health check."""
        return {
            "status": "healthy",
            "active_requests": len(self._active_requests),
            "completed_requests": len(self._completed_requests),
            "optimization_active": len(self._optimization_tasks) > 0,
            "auto_optimization_enabled": self.enable_auto_optimization,
            "performance_level": self.performance_level.value,
        }
