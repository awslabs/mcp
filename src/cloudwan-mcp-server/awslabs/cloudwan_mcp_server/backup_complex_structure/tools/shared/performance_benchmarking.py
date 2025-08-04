"""
Performance benchmarking tools for analyzer migrations.

This module provides comprehensive performance benchmarking capabilities
for measuring the success and optimization of analyzer migrations. It includes
metrics collection, performance analysis, and reporting features.

Key Features:
- Migration performance metrics
- Adapter efficiency analysis
- Concurrent processing benchmarks
- Memory usage monitoring
- Throughput analysis
- Cache effectiveness measurement
- Regression detection
- Performance reporting

Usage Example:
```python
from awslabs.cloudwan_mcp_server.tools.shared.performance_benchmarking import (
    MigrationBenchmarker, PerformanceReporter
)

# Create benchmarker
benchmarker = MigrationBenchmarker()

# Run benchmarks
results = await benchmarker.run_full_benchmark_suite(analyzer, test_data)

# Generate report
reporter = PerformanceReporter()
report = reporter.generate_comprehensive_report(results)
```
"""

import time
import psutil
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, TypeVar
from functools import wraps
import json
import csv

from .migration_adapters import BaseModelAdapter, MigrationPatterns


T = TypeVar('T')


# =============================================================================
# Performance Metrics Data Classes
# =============================================================================

@dataclass
class PerformanceMetric:
    """Individual performance metric measurement."""
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    test_name: str
    metrics: List[PerformanceMetric] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    duration: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    def add_metric(self, name: str, value: float, unit: str, **metadata) -> None:
        """Add a performance metric to this result."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            metadata=metadata
        )
        self.metrics.append(metric)
    
    def get_metric(self, name: str) -> Optional[PerformanceMetric]:
        """Get a specific metric by name."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_name": self.test_name,
            "success": self.success,
            "error_message": self.error_message,
            "duration": self.duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metrics": [m.to_dict() for m in self.metrics]
        }


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results."""
    suite_name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    summary_metrics: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def add_result(self, result: BenchmarkResult) -> None:
        """Add a benchmark result to the suite."""
        self.results.append(result)
    
    def get_success_rate(self) -> float:
        """Calculate overall success rate."""
        if not self.results:
            return 0.0
        successful = sum(1 for r in self.results if r.success)
        return successful / len(self.results)
    
    def get_average_duration(self) -> float:
        """Calculate average test duration."""
        if not self.results:
            return 0.0
        durations = [r.duration for r in self.results]
        return statistics.mean(durations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "suite_name": self.suite_name,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "success_rate": self.get_success_rate(),
            "average_duration": self.get_average_duration(),
            "summary_metrics": self.summary_metrics,
            "results": [r.to_dict() for r in self.results]
        }


# =============================================================================
# Benchmark Decorators and Utilities
# =============================================================================

def benchmark_test(test_name: str = None):
    """Decorator to automatically benchmark a test method."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> BenchmarkResult:
            name = test_name or func.__name__
            result = BenchmarkResult(test_name=name)
            
            # Record system state before
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            cpu_before = process.cpu_percent()
            
            try:
                start_time = time.time()
                result.start_time = datetime.now()
                
                # Execute the test
                await func(*args, **kwargs)
                
                end_time = time.time()
                result.end_time = datetime.now()
                result.duration = end_time - start_time
                result.success = True
                
                # Record system state after
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                cpu_after = process.cpu_percent()
                
                # Add performance metrics
                result.add_metric("duration", result.duration, "seconds")
                result.add_metric("memory_usage", memory_after - memory_before, "MB")
                result.add_metric("cpu_usage", max(cpu_after, cpu_before), "percent")
                
            except Exception as e:
                result.success = False
                result.error_message = str(e)
                result.end_time = datetime.now()
                result.duration = time.time() - start_time
            
            return result
        return wrapper
    return decorator


def measure_memory_usage(func: Callable) -> Callable:
    """Decorator to measure memory usage of a function."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        result = await func(*args, **kwargs)
        
        memory_after = process.memory_info().rss
        memory_used = (memory_after - memory_before) / 1024 / 1024  # MB
        
        # Add memory usage to result if it's a BenchmarkResult
        if isinstance(result, BenchmarkResult):
            result.add_metric("memory_usage", memory_used, "MB")
        
        return result
    return wrapper


# =============================================================================
# Benchmark Test Implementations
# =============================================================================

class MigrationBenchmarker:
    """
    Comprehensive benchmarking suite for analyzer migrations.
    
    Provides a complete set of performance tests for evaluating
    migration success, optimization effectiveness, and regression detection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize benchmarker with configuration.
        
        Args:
            config: Configuration dictionary with benchmark settings
        """
        self.config = config or {}
        self.baseline_results: Optional[BenchmarkSuite] = None
        
        # Default performance thresholds
        self.thresholds = {
            "adapter_creation_per_second": 50,
            "concurrent_processing_per_second": 10,
            "max_single_operation_time": 0.1,
            "max_batch_operation_time": 5.0,
            "memory_usage_limit_mb": 500,
            "cpu_usage_limit_percent": 80,
            "cache_hit_rate_minimum": 0.8,
            "error_rate_maximum": 0.05
        }
        self.thresholds.update(self.config.get("thresholds", {}))
    
    async def run_full_benchmark_suite(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkSuite:
        """
        Run complete benchmark suite for analyzer migration.
        
        Args:
            analyzer: Analyzer instance to benchmark
            test_data: Test data dictionary with keys for different data types
            
        Returns:
            Complete benchmark suite results
        """
        suite = BenchmarkSuite(suite_name=f"{analyzer.__class__.__name__}_migration_benchmark")
        start_time = time.time()
        
        # Run individual benchmarks
        benchmarks = [
            self.benchmark_adapter_creation,
            self.benchmark_concurrent_processing,
            self.benchmark_shared_model_integration,
            self.benchmark_security_enhancements,
            self.benchmark_caching_effectiveness,
            self.benchmark_memory_efficiency,
            self.benchmark_response_generation,
            self.benchmark_error_handling
        ]
        
        for benchmark_func in benchmarks:
            try:
                result = await benchmark_func(analyzer, test_data)
                suite.add_result(result)
            except Exception as e:
                error_result = BenchmarkResult(
                    test_name=benchmark_func.__name__,
                    success=False,
                    error_message=str(e)
                )
                suite.add_result(error_result)
        
        suite.execution_time = time.time() - start_time
        
        # Generate summary metrics
        suite.summary_metrics = self._generate_summary_metrics(suite)
        
        return suite
    
    @benchmark_test("adapter_creation_performance")
    async def benchmark_adapter_creation(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark adapter creation performance."""
        result = BenchmarkResult(test_name="adapter_creation_performance")
        
        # Get test data
        peer_data = test_data.get("peers", [])
        route_data = test_data.get("routes", [])
        
        if not peer_data and not route_data:
            # Create synthetic data for testing
            peer_data = self._generate_synthetic_peer_data(100)
            route_data = self._generate_synthetic_route_data(100)
        
        # Test peer adapter creation
        start_time = time.time()
        peer_adapters = []
        for data in peer_data:
            # Dynamically import adapter class
            if hasattr(analyzer, '__module__'):
                module = __import__(analyzer.__module__, fromlist=[''])
                if hasattr(module, 'BGPPeerInfoAdapter'):
                    adapter = module.BGPPeerInfoAdapter(data)
                    peer_adapters.append(adapter)
        
        creation_time = time.time() - start_time
        
        if peer_adapters:
            adapters_per_second = len(peer_adapters) / creation_time
            result.add_metric("peer_adapters_per_second", adapters_per_second, "adapters/sec")
            result.add_metric("peer_creation_time", creation_time, "seconds")
        
        # Test batch creation
        if peer_data:
            start_time = time.time()
            batch_adapters = MigrationPatterns.create_adapter_batch(
                module.BGPPeerInfoAdapter if hasattr(module, 'BGPPeerInfoAdapter') else None,
                peer_data
            )
            batch_creation_time = time.time() - start_time
            
            if batch_adapters:
                batch_rate = len(batch_adapters) / batch_creation_time
                result.add_metric("batch_creation_rate", batch_rate, "adapters/sec")
                result.add_metric("batch_creation_time", batch_creation_time, "seconds")
    
    @benchmark_test("concurrent_processing_performance")
    async def benchmark_concurrent_processing(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark concurrent processing performance."""
        result = BenchmarkResult(test_name="concurrent_processing_performance")
        
        # Create adapters for concurrent processing test
        all_data = []
        all_data.extend(test_data.get("peers", []))
        all_data.extend(test_data.get("routes", []))
        all_data.extend(test_data.get("metrics", []))
        
        if not all_data:
            all_data = self._generate_synthetic_mixed_data(200)
        
        # Create mock adapters
        adapters = []
        for data in all_data[:50]:  # Limit to reasonable number
            adapter = MockAdapter(data)
            adapters.append(adapter)
        
        # Test concurrent processing
        start_time = time.time()
        stats = await MigrationPatterns.process_adapters_concurrently(
            adapters,
            max_workers=10
        )
        processing_time = time.time() - start_time
        
        # Calculate metrics
        throughput = stats.total_models / processing_time
        result.add_metric("concurrent_throughput", throughput, "models/sec")
        result.add_metric("concurrent_processing_time", processing_time, "seconds")
        result.add_metric("success_rate", stats.success_rate, "ratio")
        result.add_metric("fallback_rate", stats.fallback_rate, "ratio")
    
    @benchmark_test("shared_model_integration_performance")
    async def benchmark_shared_model_integration(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark shared model integration performance."""
        result = BenchmarkResult(test_name="shared_model_integration_performance")
        
        # Test shared model creation performance
        peer_data = test_data.get("peers", [])[:20]  # Limit for performance
        
        if not peer_data:
            peer_data = self._generate_synthetic_peer_data(20)
        
        enhancement_count = 0
        total_creation_time = 0
        
        for data in peer_data:
            if hasattr(analyzer, '__module__'):
                module = __import__(analyzer.__module__, fromlist=[''])
                if hasattr(module, 'BGPPeerInfoAdapter'):
                    adapter = module.BGPPeerInfoAdapter(data)
                    
                    start_time = time.time()
                    shared_model = adapter.get_shared_model()
                    creation_time = time.time() - start_time
                    
                    total_creation_time += creation_time
                    
                    if shared_model is not None:
                        enhancement_count += 1
        
        # Calculate metrics
        if peer_data:
            enhancement_rate = enhancement_count / len(peer_data)
            avg_creation_time = total_creation_time / len(peer_data)
            
            result.add_metric("enhancement_rate", enhancement_rate, "ratio")
            result.add_metric("avg_shared_model_creation_time", avg_creation_time, "seconds")
            result.add_metric("total_models_tested", len(peer_data), "count")
    
    @benchmark_test("security_enhancement_performance")
    async def benchmark_security_enhancements(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark security enhancement performance."""
        result = BenchmarkResult(test_name="security_enhancement_performance")
        
        # Test security analysis performance
        all_data = []
        all_data.extend(test_data.get("peers", [])[:10])
        all_data.extend(test_data.get("routes", [])[:10])
        
        if not all_data:
            all_data = self._generate_synthetic_mixed_data(20)
        
        # Create mock adapters
        adapters = [MockAdapter(data) for data in all_data]
        
        # Test security analysis if analyzer has the capability
        if hasattr(analyzer, 'enhance_security_analysis'):
            start_time = time.time()
            security_results = analyzer.enhance_security_analysis(adapters)
            security_analysis_time = time.time() - start_time
            
            result.add_metric("security_analysis_time", security_analysis_time, "seconds")
            result.add_metric("models_analyzed", len(adapters), "count")
            
            if "security_score" in security_results:
                result.add_metric("security_score", security_results["security_score"], "score")
            
            threats_detected = len(security_results.get("threats_detected", []))
            result.add_metric("threats_detected", threats_detected, "count")
    
    @benchmark_test("caching_effectiveness")
    async def benchmark_caching_effectiveness(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark caching effectiveness."""
        result = BenchmarkResult(test_name="caching_effectiveness")
        
        # Test caching with repeated access
        peer_data = test_data.get("peers", [])[:1] if test_data.get("peers") else [self._generate_synthetic_peer_data(1)[0]]
        
        if hasattr(analyzer, '__module__'):
            module = __import__(analyzer.__module__, fromlist=[''])
            if hasattr(module, 'BGPPeerInfoAdapter'):
                adapter = module.BGPPeerInfoAdapter(peer_data[0])
                
                # First access (cache miss)
                start_time = time.time()
                first_result = adapter.get_transformed_data() if hasattr(adapter, 'get_transformed_data') else None
                first_access_time = time.time() - start_time
                
                # Second access (cache hit)
                start_time = time.time()
                second_result = adapter.get_transformed_data() if hasattr(adapter, 'get_transformed_data') else None
                second_access_time = time.time() - start_time
                
                # Calculate cache effectiveness
                if first_access_time > 0:
                    cache_improvement = max(0, (first_access_time - second_access_time) / first_access_time)
                    result.add_metric("cache_improvement_ratio", cache_improvement, "ratio")
                
                result.add_metric("first_access_time", first_access_time, "seconds")
                result.add_metric("second_access_time", second_access_time, "seconds")
                
                # Get cache statistics if available
                if hasattr(adapter, 'get_cache_stats'):
                    cache_stats = adapter.get_cache_stats()
                    if "hit_rate" in cache_stats:
                        result.add_metric("cache_hit_rate", cache_stats["hit_rate"], "ratio")
    
    @benchmark_test("memory_efficiency")
    @measure_memory_usage
    async def benchmark_memory_efficiency(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark memory usage efficiency."""
        result = BenchmarkResult(test_name="memory_efficiency")
        
        # Test memory usage with large dataset
        large_dataset = []
        large_dataset.extend(test_data.get("peers", []) * 10)  # Multiply existing data
        large_dataset.extend(test_data.get("routes", []) * 10)
        
        if not large_dataset:
            large_dataset = self._generate_synthetic_mixed_data(500)
        
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create adapters and measure memory
        adapters = [MockAdapter(data) for data in large_dataset[:100]]  # Limit to prevent memory issues
        
        memory_after_adapters = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process adapters
        if adapters:
            stats = await MigrationPatterns.process_adapters_concurrently(
                adapters,
                max_workers=5
            )
        
        memory_after_processing = process.memory_info().rss / 1024 / 1024  # MB
        
        # Calculate memory metrics
        adapter_memory = memory_after_adapters - memory_before
        processing_memory = memory_after_processing - memory_after_adapters
        total_memory = memory_after_processing - memory_before
        
        result.add_metric("adapter_memory_usage", adapter_memory, "MB")
        result.add_metric("processing_memory_usage", processing_memory, "MB")
        result.add_metric("total_memory_usage", total_memory, "MB")
        result.add_metric("memory_per_adapter", adapter_memory / len(adapters) if adapters else 0, "MB/adapter")
        
        return result
    
    @benchmark_test("response_generation_performance") 
    async def benchmark_response_generation(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark response generation performance."""
        result = BenchmarkResult(test_name="response_generation_performance")
        
        # Test response generation if analyzer has enhanced response
        if hasattr(analyzer, '__module__'):
            module = __import__(analyzer.__module__, fromlist=[''])
            
            # Look for enhanced response class
            enhanced_response_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, '__bases__') and 
                    any('Enhanced' in base.__name__ for base in attr.__bases__ if hasattr(base, '__name__'))):
                    enhanced_response_class = attr
                    break
            
            if enhanced_response_class:
                # Create test adapters
                test_adapters = [MockAdapter(data) for data in test_data.get("peers", [])[:5]]
                
                # Time response creation and enhancement
                start_time = time.time()
                response = enhanced_response_class(
                    analysis_type="test_analysis",
                    timestamp=datetime.now(),
                    status="success"
                )
                
                if hasattr(response, 'add_adapters') and test_adapters:
                    response.add_adapters(test_adapters)
                
                response_time = time.time() - start_time
                
                result.add_metric("response_generation_time", response_time, "seconds")
                result.add_metric("adapters_processed", len(test_adapters), "count")
                
                # Test enhancement summary generation
                if hasattr(response, 'get_enhancement_summary'):
                    start_time = time.time()
                    summary = response.get_enhancement_summary()
                    summary_time = time.time() - start_time
                    
                    result.add_metric("enhancement_summary_time", summary_time, "seconds")
                    if summary and isinstance(summary, dict):
                        result.add_metric("summary_fields_count", len(summary), "count")
        
        return result
    
    @benchmark_test("error_handling_performance")
    async def benchmark_error_handling(
        self, 
        analyzer: Any, 
        test_data: Dict[str, List[Dict[str, Any]]]
    ) -> BenchmarkResult:
        """Benchmark error handling performance."""
        result = BenchmarkResult(test_name="error_handling_performance")
        
        # Test error handling with invalid data
        invalid_data = [
            {"invalid": "data"},
            {"missing": "required_fields"},
            {},  # Empty data
            None  # None data - will cause error in adapter creation
        ]
        
        error_count = 0
        total_time = 0
        
        for data in invalid_data:
            if data is None:
                continue  # Skip None data to avoid adapter creation errors
                
            try:
                start_time = time.time()
                adapter = MockAdapter(data)
                shared_model = adapter.get_shared_model()
                errors = adapter.get_transformation_errors()
                processing_time = time.time() - start_time
                
                total_time += processing_time
                
                if errors or shared_model is None:
                    error_count += 1
                    
            except Exception:
                error_count += 1
                total_time += time.time() - start_time
        
        # Calculate error handling metrics
        valid_data_count = len([d for d in invalid_data if d is not None])
        if valid_data_count > 0:
            error_rate = error_count / valid_data_count
            avg_error_handling_time = total_time / valid_data_count
            
            result.add_metric("error_rate", error_rate, "ratio")
            result.add_metric("avg_error_handling_time", avg_error_handling_time, "seconds")
            result.add_metric("errors_detected", error_count, "count")
        
        return result
    
    def _generate_summary_metrics(self, suite: BenchmarkSuite) -> Dict[str, Any]:
        """Generate summary metrics for benchmark suite."""
        summary = {
            "overall_performance_score": 0,
            "performance_grade": "F",
            "threshold_compliance": {},
            "recommendations": []
        }
        
        # Check threshold compliance
        for result in suite.results:
            for metric in result.metrics:
                threshold_key = f"{metric.name}_threshold"
                if threshold_key in self.thresholds:
                    threshold = self.thresholds[threshold_key]
                    compliant = self._check_threshold_compliance(metric, threshold)
                    summary["threshold_compliance"][metric.name] = compliant
        
        # Calculate overall performance score
        compliant_count = sum(1 for compliant in summary["threshold_compliance"].values() if compliant)
        total_thresholds = len(summary["threshold_compliance"])
        if total_thresholds > 0:
            score = (compliant_count / total_thresholds) * 100
            summary["overall_performance_score"] = score
            
            # Assign grade
            if score >= 90:
                summary["performance_grade"] = "A"
            elif score >= 80:
                summary["performance_grade"] = "B"
            elif score >= 70:
                summary["performance_grade"] = "C"
            elif score >= 60:
                summary["performance_grade"] = "D"
            else:
                summary["performance_grade"] = "F"
        
        # Generate recommendations
        summary["recommendations"] = self._generate_recommendations(suite)
        
        return summary
    
    def _check_threshold_compliance(self, metric: PerformanceMetric, threshold: float) -> bool:
        """Check if metric complies with threshold."""
        # Simple comparison - in practice, this would be more sophisticated
        if "per_second" in metric.name or "rate" in metric.name:
            return metric.value >= threshold
        elif "time" in metric.name:
            return metric.value <= threshold
        else:
            return metric.value <= threshold
    
    def _generate_recommendations(self, suite: BenchmarkSuite) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        for result in suite.results:
            if not result.success:
                recommendations.append(
                    f"Fix issues in {result.test_name}: {result.error_message}"
                )
            
            # Check for slow operations
            duration_metric = result.get_metric("duration")
            if duration_metric and duration_metric.value > 1.0:
                recommendations.append(
                    f"Optimize {result.test_name} - duration {duration_metric.value:.2f}s exceeds 1s"
                )
        
        if not recommendations:
            recommendations.append("Performance looks good - no specific recommendations")
        
        return recommendations
    
    def _generate_synthetic_peer_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate synthetic peer data for testing."""
        from ...models.shared.enums import BGPPeerState
        
        data = []
        for i in range(count):
            data.append({
                "peer_asn": 65000 + i,
                "local_asn": 64512,
                "peer_ip": f"192.168.{i//256}.{i%256}",
                "state": BGPPeerState.ESTABLISHED,
                "uptime": 3600 + i,
                "routes_received": 100 + i,
                "routes_advertised": 50 + i,
                "region": f"us-west-{i%3 + 1}",
                "hold_timer": 180,
                "keepalive_timer": 60,
                "flap_count": i % 5
            })
        return data
    
    def _generate_synthetic_route_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate synthetic route data for testing."""
        from ...models.shared.enums import BGPRouteType
        
        data = []
        for i in range(count):
            data.append({
                "prefix": f"10.{i//256}.{i%256}.0/24",
                "next_hop": f"192.168.{i//256}.{i%256}",
                "as_path": [64512, 65000 + (i % 100)],
                "origin": "IGP",
                "route_type": BGPRouteType.PROPAGATED,
                "is_best_path": i % 2 == 0,
                "is_valid": True,
                "validation_errors": [],
                "region": f"us-west-{i%3 + 1}"
            })
        return data
    
    def _generate_synthetic_mixed_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate mixed synthetic data for testing."""
        peer_data = self._generate_synthetic_peer_data(count // 2)
        route_data = self._generate_synthetic_route_data(count // 2)
        return peer_data + route_data


# =============================================================================
# Mock Adapter for Testing
# =============================================================================

class MockAdapter(BaseModelAdapter):
    """Mock adapter for testing purposes."""
    
    def transform_data(self) -> Dict[str, Any]:
        """Transform data (mock implementation)."""
        return {
            "mock_field": self._data.get("mock_field", "mock_value"),
            "processed": True
        }
    
    def create_shared_model(self) -> Optional[Any]:
        """Create mock shared model."""
        if self._data and isinstance(self._data, dict) and len(self._data) > 1:
            return {"mock_shared_model": True, "data": self.transform_data()}
        return None


# =============================================================================
# Performance Reporting
# =============================================================================

class PerformanceReporter:
    """
    Performance reporting and analysis tools.
    
    Provides comprehensive reporting capabilities for benchmark results
    including trend analysis, regression detection, and export functionality.
    """
    
    def __init__(self):
        self.report_templates = {
            "summary": self._generate_summary_report,
            "detailed": self._generate_detailed_report,
            "regression": self._generate_regression_report,
            "comparison": self._generate_comparison_report
        }
    
    def generate_comprehensive_report(
        self, 
        suite: BenchmarkSuite, 
        baseline: Optional[BenchmarkSuite] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Args:
            suite: Current benchmark suite results
            baseline: Optional baseline results for comparison
            
        Returns:
            Comprehensive report dictionary
        """
        report = {
            "metadata": {
                "suite_name": suite.suite_name,
                "timestamp": suite.timestamp.isoformat(),
                "execution_time": suite.execution_time,
                "test_count": len(suite.results)
            },
            "summary": self._generate_summary_report(suite),
            "detailed_results": self._generate_detailed_report(suite),
            "performance_analysis": self._analyze_performance_trends(suite),
            "recommendations": self._generate_detailed_recommendations(suite)
        }
        
        if baseline:
            report["regression_analysis"] = self._generate_regression_report(suite, baseline)
            report["comparison"] = self._generate_comparison_report(suite, baseline)
        
        return report
    
    def export_to_json(self, report: Dict[str, Any], file_path: str) -> None:
        """Export report to JSON file."""
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
    
    def export_to_csv(self, suite: BenchmarkSuite, file_path: str) -> None:
        """Export metrics to CSV file."""
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Test Name', 'Metric Name', 'Value', 'Unit', 'Timestamp'])
            
            for result in suite.results:
                for metric in result.metrics:
                    writer.writerow([
                        result.test_name,
                        metric.name,
                        metric.value,
                        metric.unit,
                        metric.timestamp.isoformat()
                    ])
    
    def _generate_summary_report(self, suite: BenchmarkSuite) -> Dict[str, Any]:
        """Generate summary report section."""
        return {
            "overall_success_rate": suite.get_success_rate(),
            "average_test_duration": suite.get_average_duration(),
            "total_execution_time": suite.execution_time,
            "performance_grade": suite.summary_metrics.get("performance_grade", "N/A"),
            "performance_score": suite.summary_metrics.get("overall_performance_score", 0)
        }
    
    def _generate_detailed_report(self, suite: BenchmarkSuite) -> List[Dict[str, Any]]:
        """Generate detailed results report."""
        detailed_results = []
        
        for result in suite.results:
            result_detail = {
                "test_name": result.test_name,
                "success": result.success,
                "duration": result.duration,
                "error_message": result.error_message,
                "metrics": {}
            }
            
            for metric in result.metrics:
                result_detail["metrics"][metric.name] = {
                    "value": metric.value,
                    "unit": metric.unit,
                    "metadata": metric.metadata
                }
            
            detailed_results.append(result_detail)
        
        return detailed_results
    
    def _generate_regression_report(
        self, 
        current: BenchmarkSuite, 
        baseline: BenchmarkSuite
    ) -> Dict[str, Any]:
        """Generate regression analysis report."""
        regression_analysis = {
            "performance_delta": {},
            "regressions_detected": [],
            "improvements_detected": [],
            "overall_regression_score": 0
        }
        
        # Compare matching tests
        baseline_tests = {r.test_name: r for r in baseline.results}
        
        for current_result in current.results:
            test_name = current_result.test_name
            if test_name in baseline_tests:
                baseline_result = baseline_tests[test_name]
                
                # Compare durations
                duration_delta = current_result.duration - baseline_result.duration
                regression_analysis["performance_delta"][test_name] = {
                    "duration_delta": duration_delta,
                    "duration_delta_percent": (
                        (duration_delta / baseline_result.duration * 100)
                        if baseline_result.duration > 0 else 0
                    )
                }
                
                # Detect significant regressions (>20% slower)
                if duration_delta > baseline_result.duration * 0.2:
                    regression_analysis["regressions_detected"].append({
                        "test_name": test_name,
                        "regression_type": "performance",
                        "delta": duration_delta,
                        "delta_percent": duration_delta / baseline_result.duration * 100
                    })
                
                # Detect improvements (>10% faster)
                elif duration_delta < -baseline_result.duration * 0.1:
                    regression_analysis["improvements_detected"].append({
                        "test_name": test_name,
                        "improvement_type": "performance", 
                        "delta": abs(duration_delta),
                        "delta_percent": abs(duration_delta) / baseline_result.duration * 100
                    })
        
        return regression_analysis
    
    def _generate_comparison_report(
        self, 
        current: BenchmarkSuite, 
        baseline: BenchmarkSuite
    ) -> Dict[str, Any]:
        """Generate comparison report."""
        return {
            "current_success_rate": current.get_success_rate(),
            "baseline_success_rate": baseline.get_success_rate(),
            "success_rate_delta": current.get_success_rate() - baseline.get_success_rate(),
            "current_avg_duration": current.get_average_duration(),
            "baseline_avg_duration": baseline.get_average_duration(),
            "duration_delta": current.get_average_duration() - baseline.get_average_duration()
        }
    
    def _analyze_performance_trends(self, suite: BenchmarkSuite) -> Dict[str, Any]:
        """Analyze performance trends in the suite."""
        analysis = {
            "slowest_tests": [],
            "fastest_tests": [],
            "most_memory_intensive": [],
            "highest_throughput": []
        }
        
        # Sort tests by duration
        sorted_by_duration = sorted(suite.results, key=lambda r: r.duration, reverse=True)
        analysis["slowest_tests"] = [
            {"name": r.test_name, "duration": r.duration} 
            for r in sorted_by_duration[:3]
        ]
        analysis["fastest_tests"] = [
            {"name": r.test_name, "duration": r.duration} 
            for r in sorted_by_duration[-3:]
        ]
        
        # Find memory intensive tests
        memory_tests = []
        throughput_tests = []
        
        for result in suite.results:
            memory_metric = result.get_metric("memory_usage")
            if memory_metric:
                memory_tests.append({
                    "name": result.test_name,
                    "memory_usage": memory_metric.value
                })
            
            throughput_metric = result.get_metric("concurrent_throughput")
            if throughput_metric:
                throughput_tests.append({
                    "name": result.test_name,
                    "throughput": throughput_metric.value
                })
        
        analysis["most_memory_intensive"] = sorted(
            memory_tests, key=lambda x: x["memory_usage"], reverse=True
        )[:3]
        analysis["highest_throughput"] = sorted(
            throughput_tests, key=lambda x: x["throughput"], reverse=True
        )[:3]
        
        return analysis
    
    def _generate_detailed_recommendations(self, suite: BenchmarkSuite) -> List[Dict[str, Any]]:
        """Generate detailed recommendations."""
        recommendations = []
        
        # Analyze each test for recommendations
        for result in suite.results:
            if not result.success:
                recommendations.append({
                    "priority": "critical",
                    "category": "reliability",
                    "test": result.test_name,
                    "issue": "Test failure",
                    "description": result.error_message,
                    "recommendation": f"Fix test failure in {result.test_name}"
                })
            
            # Performance recommendations
            if result.duration > 5.0:
                recommendations.append({
                    "priority": "high",
                    "category": "performance",
                    "test": result.test_name,
                    "issue": "Slow execution",
                    "description": f"Test took {result.duration:.2f} seconds",
                    "recommendation": "Consider optimizing algorithm or reducing test data size"
                })
            
            # Memory recommendations
            memory_metric = result.get_metric("memory_usage")
            if memory_metric and memory_metric.value > 100:  # > 100MB
                recommendations.append({
                    "priority": "medium",
                    "category": "memory",
                    "test": result.test_name,
                    "issue": "High memory usage",
                    "description": f"Memory usage: {memory_metric.value:.1f} MB",
                    "recommendation": "Consider implementing memory optimization or garbage collection"
                })
        
        return sorted(recommendations, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x["priority"]])


# =============================================================================
# Export Summary
# =============================================================================

__all__ = [
    # Data Classes
    'PerformanceMetric',
    'BenchmarkResult', 
    'BenchmarkSuite',
    
    # Main Classes
    'MigrationBenchmarker',
    'PerformanceReporter',
    'MockAdapter',
    
    # Decorators
    'benchmark_test',
    'measure_memory_usage'
]