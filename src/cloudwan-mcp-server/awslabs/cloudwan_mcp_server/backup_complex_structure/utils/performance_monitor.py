"""
Performance Monitoring and Benchmarking for CloudWAN MCP Server.

This module provides comprehensive performance monitoring, benchmarking,
and optimization tracking for the CloudWAN MCP server components.
"""

import asyncio
import logging
import time
import psutil
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics container."""
    
    # Timing metrics
    operation_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    total_operations: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Resource metrics
    memory_usage_mb: List[float] = field(default_factory=list)
    cpu_usage_percent: List[float] = field(default_factory=list)
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_memory_mb: float = 0.0
    
    # Error metrics
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Async/await performance
    async_operation_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    thread_pool_wait_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    # Tool loading performance
    tool_load_times: Dict[str, float] = field(default_factory=dict)
    tool_load_errors: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "summary": self._calculate_summary(),
            "timing": {
                "operations": {op: {
                    "count": len(times),
                    "avg_ms": sum(times) * 1000 / len(times) if times else 0,
                    "min_ms": min(times) * 1000 if times else 0,
                    "max_ms": max(times) * 1000 if times else 0,
                    "total_ms": sum(times) * 1000
                } for op, times in self.operation_times.items()},
                "async_operations": {op: {
                    "count": len(times),
                    "avg_ms": sum(times) * 1000 / len(times) if times else 0,
                    "p95_ms": self._percentile(times, 95) * 1000 if times else 0
                } for op, times in self.async_operation_times.items()},
                "thread_pool_waits": {op: {
                    "count": len(times),
                    "avg_ms": sum(times) * 1000 / len(times) if times else 0,
                    "p95_ms": self._percentile(times, 95) * 1000 if times else 0
                } for op, times in self.thread_pool_wait_times.items()}
            },
            "resources": {
                "memory": {
                    "current_mb": self.memory_usage_mb[-1] if self.memory_usage_mb else 0,
                    "avg_mb": sum(self.memory_usage_mb) / len(self.memory_usage_mb) if self.memory_usage_mb else 0,
                    "peak_mb": max(self.memory_usage_mb) if self.memory_usage_mb else 0
                },
                "cpu": {
                    "current_percent": self.cpu_usage_percent[-1] if self.cpu_usage_percent else 0,
                    "avg_percent": sum(self.cpu_usage_percent) / len(self.cpu_usage_percent) if self.cpu_usage_percent else 0,
                    "peak_percent": max(self.cpu_usage_percent) if self.cpu_usage_percent else 0
                }
            },
            "cache": {
                "hit_ratio": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "memory_mb": self.cache_memory_mb
            },
            "tools": {
                "load_times": self.tool_load_times,
                "load_errors": self.tool_load_errors,
                "avg_load_time": sum(self.tool_load_times.values()) / len(self.tool_load_times) if self.tool_load_times else 0
            },
            "errors": dict(self.error_counts)
        }
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate performance summary."""
        total_ops = sum(self.total_operations.values())
        avg_response_time = 0
        
        if self.operation_times:
            all_times = []
            for times in self.operation_times.values():
                all_times.extend(times)
            avg_response_time = sum(all_times) * 1000 / len(all_times) if all_times else 0
        
        return {
            "total_operations": total_ops,
            "avg_response_time_ms": avg_response_time,
            "current_memory_mb": self.memory_usage_mb[-1] if self.memory_usage_mb else 0,
            "cache_hit_ratio": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "total_errors": sum(self.error_counts.values()),
            "tools_loaded": len(self.tool_load_times),
            "tools_failed": len(self.tool_load_errors)
        }
    
    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for CloudWAN MCP Server.
    
    Features:
    - Real-time performance tracking
    - Async/await operation monitoring
    - Memory and CPU usage tracking
    - Cache performance analysis
    - Tool loading benchmarks
    - Automated performance alerts
    """
    
    def __init__(self, collection_interval: float = 5.0, history_size: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            collection_interval: Seconds between metric collections
            history_size: Maximum number of metrics to keep in memory
        """
        self.metrics = PerformanceMetrics()
        self.collection_interval = collection_interval
        self.history_size = history_size
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        # Recent metrics for trending
        self._recent_metrics = deque(maxlen=history_size)
        
        # Performance thresholds for alerts
        self.thresholds = {
            "max_memory_mb": 128,
            "max_response_time_ms": 5000,
            "min_cache_hit_ratio": 0.80,
            "max_error_rate": 0.05
        }
    
    async def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level performance metrics."""
        try:
            # Memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            
            with self._lock:
                self.metrics.memory_usage_mb.append(memory_mb)
                self.metrics.cpu_usage_percent.append(cpu_percent)
                
                # Trim history to prevent unbounded growth
                if len(self.metrics.memory_usage_mb) > self.history_size:
                    self.metrics.memory_usage_mb = self.metrics.memory_usage_mb[-self.history_size:]
                if len(self.metrics.cpu_usage_percent) > self.history_size:
                    self.metrics.cpu_usage_percent = self.metrics.cpu_usage_percent[-self.history_size:]
            
            # Check thresholds and alert if needed
            await self._check_performance_thresholds(memory_mb, cpu_percent)
                
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
    
    async def _check_performance_thresholds(self, memory_mb: float, cpu_percent: float) -> None:
        """Check performance thresholds and generate alerts."""
        alerts = []
        
        if memory_mb > self.thresholds["max_memory_mb"]:
            alerts.append(f"High memory usage: {memory_mb:.1f}MB > {self.thresholds['max_memory_mb']}MB")
        
        # Calculate current cache hit ratio
        total_cache_ops = self.metrics.cache_hits + self.metrics.cache_misses
        if total_cache_ops > 0:
            hit_ratio = self.metrics.cache_hits / total_cache_ops
            if hit_ratio < self.thresholds["min_cache_hit_ratio"]:
                alerts.append(f"Low cache hit ratio: {hit_ratio:.2%} < {self.thresholds['min_cache_hit_ratio']:.2%}")
        
        if alerts:
            for alert in alerts:
                logger.warning(f"PERFORMANCE ALERT: {alert}")
    
    @asynccontextmanager
    async def monitor_operation(self, operation_name: str):
        """
        Context manager to monitor operation performance.
        
        Args:
            operation_name: Name of the operation being monitored
        """
        start_time = time.time()
        thread_start = time.thread_time()
        
        try:
            yield
        except Exception as e:
            with self._lock:
                self.metrics.error_counts[operation_name] += 1
            raise
        finally:
            duration = time.time() - start_time
            thread_duration = time.thread_time() - thread_start
            
            with self._lock:
                self.metrics.operation_times[operation_name].append(duration)
                self.metrics.total_operations[operation_name] += 1
                
                # Track thread pool wait time (difference between wall time and CPU time)
                if duration > thread_duration:
                    wait_time = duration - thread_duration
                    self.metrics.thread_pool_wait_times[operation_name].append(wait_time)
    
    @asynccontextmanager
    async def monitor_async_operation(self, operation_name: str):
        """
        Context manager specifically for monitoring async operations.
        
        Args:
            operation_name: Name of the async operation being monitored
        """
        start_time = time.time()
        
        try:
            yield
        except Exception as e:
            with self._lock:
                self.metrics.error_counts[f"async_{operation_name}"] += 1
            raise
        finally:
            duration = time.time() - start_time
            
            with self._lock:
                self.metrics.async_operation_times[operation_name].append(duration)
    
    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self.metrics.cache_hits += 1
    
    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.metrics.cache_misses += 1
    
    def update_cache_memory(self, memory_mb: float) -> None:
        """Update cache memory usage."""
        with self._lock:
            self.metrics.cache_memory_mb = memory_mb
    
    def record_tool_load(self, tool_name: str, load_time: float, error: Optional[str] = None) -> None:
        """Record tool loading performance."""
        with self._lock:
            if error:
                self.metrics.tool_load_errors[tool_name] = error
            else:
                self.metrics.tool_load_times[tool_name] = load_time
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return self.metrics.to_dict()
    
    def get_performance_report(self) -> str:
        """Generate a human-readable performance report."""
        metrics_dict = self.get_metrics()
        
        report = []
        report.append("=== CloudWAN MCP Server Performance Report ===")
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        summary = metrics_dict["summary"]
        report.append("PERFORMANCE SUMMARY:")
        report.append(f"  Total Operations: {summary['total_operations']}")
        report.append(f"  Average Response Time: {summary['avg_response_time_ms']:.2f}ms")
        report.append(f"  Current Memory Usage: {summary['current_memory_mb']:.1f}MB")
        report.append(f"  Cache Hit Ratio: {summary['cache_hit_ratio']:.2%}")
        report.append(f"  Total Errors: {summary['total_errors']}")
        report.append(f"  Tools Loaded: {summary['tools_loaded']}")
        report.append("")
        
        # Resource usage
        resources = metrics_dict["resources"]
        report.append("RESOURCE UTILIZATION:")
        report.append(f"  Memory - Current: {resources['memory']['current_mb']:.1f}MB, Peak: {resources['memory']['peak_mb']:.1f}MB")
        report.append(f"  CPU - Current: {resources['cpu']['current_percent']:.1f}%, Peak: {resources['cpu']['peak_percent']:.1f}%")
        report.append("")
        
        # Top operations by time
        if metrics_dict["timing"]["operations"]:
            report.append("TOP OPERATIONS BY RESPONSE TIME:")
            ops = sorted(metrics_dict["timing"]["operations"].items(), 
                        key=lambda x: x[1]["avg_ms"], reverse=True)[:5]
            for op_name, op_data in ops:
                report.append(f"  {op_name}: {op_data['avg_ms']:.2f}ms avg ({op_data['count']} calls)")
            report.append("")
        
        # Async performance
        if metrics_dict["timing"]["async_operations"]:
            report.append("ASYNC OPERATION PERFORMANCE:")
            async_ops = metrics_dict["timing"]["async_operations"]
            for op_name, op_data in async_ops.items():
                report.append(f"  {op_name}: {op_data['avg_ms']:.2f}ms avg, {op_data['p95_ms']:.2f}ms p95")
            report.append("")
        
        # Tool loading performance
        if metrics_dict["tools"]["load_times"]:
            report.append("TOOL LOADING PERFORMANCE:")
            tool_times = sorted(metrics_dict["tools"]["load_times"].items(), 
                              key=lambda x: x[1], reverse=True)
            for tool_name, load_time in tool_times:
                report.append(f"  {tool_name}: {load_time:.3f}s")
            report.append(f"  Average Load Time: {metrics_dict['tools']['avg_load_time']:.3f}s")
            
            if metrics_dict["tools"]["load_errors"]:
                report.append("  FAILED TOOLS:")
                for tool_name, error in metrics_dict["tools"]["load_errors"].items():
                    report.append(f"    {tool_name}: {error}")
            report.append("")
        
        # Recommendations
        report.append("PERFORMANCE RECOMMENDATIONS:")
        report.extend(self._generate_recommendations(metrics_dict))
        
        return "\n".join(report)
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        # Memory recommendations
        current_memory = metrics["resources"]["memory"]["current_mb"]
        if current_memory > 100:
            recommendations.append(f"  • High memory usage ({current_memory:.1f}MB) - consider increasing cache eviction")
        
        # Cache recommendations
        hit_ratio = metrics["cache"]["hit_ratio"]
        if hit_ratio < 0.8 and hit_ratio > 0:
            recommendations.append(f"  • Low cache hit ratio ({hit_ratio:.2%}) - consider increasing cache size")
        
        # Response time recommendations
        avg_response = metrics["summary"]["avg_response_time_ms"]
        if avg_response > 1000:
            recommendations.append(f"  • Slow response times ({avg_response:.2f}ms) - investigate bottlenecks")
        
        # Async performance recommendations
        if metrics["timing"]["thread_pool_waits"]:
            max_wait = max(op["avg_ms"] for op in metrics["timing"]["thread_pool_waits"].values())
            if max_wait > 100:
                recommendations.append(f"  • High thread pool wait times ({max_wait:.2f}ms) - consider increasing thread pool size")
        
        # Tool loading recommendations
        if metrics["tools"]["avg_load_time"] > 0.5:
            recommendations.append(f"  • Slow tool loading ({metrics['tools']['avg_load_time']:.3f}s avg) - consider lazy loading optimization")
        
        if not recommendations:
            recommendations.append("  • Performance looks good! No specific recommendations at this time.")
        
        return recommendations


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor