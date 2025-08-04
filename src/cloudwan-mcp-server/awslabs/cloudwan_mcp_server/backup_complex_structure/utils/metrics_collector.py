"""
Metrics collection utilities for CloudWAN MCP Server.

This module provides functionality to collect and aggregate metrics
for performance monitoring and analysis.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from threading import Lock
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
import asyncio


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    custom_data: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics for CloudWAN operations.
    
    This class provides functionality to track operation performance,
    resource usage, and custom metrics.
    """
    
    def __init__(self):
        """Initialize the metrics collector."""
        self.logger = logging.getLogger(__name__)
        self._metrics: List[OperationMetrics] = []
        self._lock = Lock()
        self._operation_counters: Dict[str, int] = {}
        self._enabled = True
    
    def enable(self):
        """Enable metrics collection."""
        self._enabled = True
    
    def disable(self):
        """Disable metrics collection."""
        self._enabled = False
    
    def start_operation(self, operation_name: str) -> OperationMetrics:
        """
        Start tracking an operation.
        
        Args:
            operation_name: Name of the operation to track
            
        Returns:
            OperationMetrics object for this operation
        """
        if not self._enabled:
            return OperationMetrics(operation_name=operation_name, start_time=time.time())
        
        metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time()
        )
        
        # Capture initial resource usage
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                metrics.resource_usage['cpu_percent_start'] = process.cpu_percent()
                metrics.resource_usage['memory_mb_start'] = process.memory_info().rss / 1024 / 1024
            except Exception as e:
                self.logger.debug(f"Failed to capture initial resource usage: {e}")
        
        with self._lock:
            self._operation_counters[operation_name] = self._operation_counters.get(operation_name, 0) + 1
            self._metrics.append(metrics)
        
        return metrics
    
    def end_operation(self, metrics: OperationMetrics, success: bool = True, error_message: Optional[str] = None):
        """
        End tracking an operation.
        
        Args:
            metrics: The OperationMetrics object returned by start_operation
            success: Whether the operation was successful
            error_message: Error message if operation failed
        """
        if not self._enabled:
            return
        
        metrics.end_time = time.time()
        metrics.duration = metrics.end_time - metrics.start_time
        metrics.success = success
        metrics.error_message = error_message
        
        # Capture final resource usage
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                metrics.resource_usage['cpu_percent_end'] = process.cpu_percent()
                metrics.resource_usage['memory_mb_end'] = process.memory_info().rss / 1024 / 1024
                
                # Calculate deltas if we have start values
                if 'memory_mb_start' in metrics.resource_usage:
                    metrics.resource_usage['memory_delta_mb'] = (
                        metrics.resource_usage['memory_mb_end'] - metrics.resource_usage['memory_mb_start']
                    )
            except Exception as e:
                self.logger.debug(f"Failed to capture final resource usage: {e}")
    
    def add_custom_metric(self, metrics: OperationMetrics, key: str, value: Any):
        """
        Add a custom metric to an operation.
        
        Args:
            metrics: The OperationMetrics object
            key: Metric key
            value: Metric value
        """
        if not self._enabled:
            return
        
        metrics.custom_data[key] = value
    
    def get_metrics(self, operation_name: Optional[str] = None) -> List[OperationMetrics]:
        """
        Get collected metrics.
        
        Args:
            operation_name: If specified, only return metrics for this operation
            
        Returns:
            List of OperationMetrics
        """
        with self._lock:
            if operation_name:
                return [m for m in self._metrics if m.operation_name == operation_name]
            return self._metrics.copy()
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            Dictionary containing statistics
        """
        metrics = self.get_metrics(operation_name)
        
        if not metrics:
            return {}
        
        completed_metrics = [m for m in metrics if m.duration is not None]
        
        if not completed_metrics:
            return {
                'total_operations': len(metrics),
                'completed_operations': 0
            }
        
        durations = [m.duration for m in completed_metrics]
        success_count = len([m for m in completed_metrics if m.success])
        
        return {
            'total_operations': len(metrics),
            'completed_operations': len(completed_metrics),
            'success_rate': success_count / len(completed_metrics) if completed_metrics else 0,
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_duration': sum(durations)
        }
    
    def clear_metrics(self):
        """Clear all collected metrics."""
        with self._lock:
            self._metrics.clear()
            self._operation_counters.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all collected metrics.
        
        Returns:
            Dictionary containing metrics summary
        """
        with self._lock:
            operation_names = list(set(m.operation_name for m in self._metrics))
            
            summary = {
                'total_operations': len(self._metrics),
                'unique_operation_types': len(operation_names),
                'operation_counts': self._operation_counters.copy()
            }
            
            # Add per-operation stats
            summary['operation_stats'] = {}
            for op_name in operation_names:
                summary['operation_stats'][op_name] = self.get_operation_stats(op_name)
            
            return summary


# Global metrics collector instance
global_metrics = MetricsCollector()


def track_operation(operation_name: str):
    """
    Decorator to track operation metrics.
    
    Args:
        operation_name: Name of the operation to track
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                metrics = global_metrics.start_operation(operation_name)
                try:
                    result = await func(*args, **kwargs)
                    global_metrics.end_operation(metrics, success=True)
                    return result
                except Exception as e:
                    global_metrics.end_operation(metrics, success=False, error_message=str(e))
                    raise
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                metrics = global_metrics.start_operation(operation_name)
                try:
                    result = func(*args, **kwargs)
                    global_metrics.end_operation(metrics, success=True)
                    return result
                except Exception as e:
                    global_metrics.end_operation(metrics, success=False, error_message=str(e))
                    raise
            return sync_wrapper
    return decorator