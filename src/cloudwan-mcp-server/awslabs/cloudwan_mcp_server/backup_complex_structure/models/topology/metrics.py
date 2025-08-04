"""
Network metrics and performance monitoring models for CloudWAN MCP Server.

This module provides comprehensive network metrics collection, analysis, and
monitoring models. Designed to support operational monitoring, performance
optimization, and health assessment across multi-region CloudWAN topologies.

Key Features:
- Real-time network performance metrics collection
- Connection-level quality monitoring and SLA tracking
- Topology-wide health assessment and anomaly detection  
- Historical trend analysis and capacity planning metrics
- Integration with CloudWatch, VPC Flow Logs, and other data sources
- Business-level KPIs and service impact correlation

Metric Categories:
- Performance: Latency, throughput, packet loss, jitter
- Utilization: Bandwidth, capacity, resource consumption
- Availability: Uptime, SLA compliance, failure rates
- Quality: Error rates, retransmissions, quality scores
- Business: Cost efficiency, service impact, user experience
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from uuid import uuid4
import statistics
import logging
from collections import defaultdict

from pydantic import BaseModel, Field, ConfigDict

from ..shared.base import TimestampMixin
from ..shared.enums import HealthStatus

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of network metrics."""
    
    # Performance metrics
    LATENCY = "latency"
    THROUGHPUT = "throughput"  
    BANDWIDTH = "bandwidth"
    PACKET_LOSS = "packet_loss"
    JITTER = "jitter"
    
    # Utilization metrics
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    NETWORK_UTILIZATION = "network_utilization"
    STORAGE_UTILIZATION = "storage_utilization"
    CAPACITY_UTILIZATION = "capacity_utilization"
    
    # Quality metrics
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    AVAILABILITY = "availability"
    UPTIME = "uptime"
    RELIABILITY = "reliability"
    
    # Business metrics
    COST_PER_GB = "cost_per_gb"
    SERVICE_LEVEL = "service_level"
    USER_EXPERIENCE = "user_experience"
    COMPLIANCE_SCORE = "compliance_score"
    
    # CloudWAN specific
    ATTACHMENT_STATE_CHANGES = "attachment_state_changes"
    ROUTE_PROPAGATION_LATENCY = "route_propagation_latency"
    POLICY_VIOLATIONS = "policy_violations"
    SEGMENT_TRAFFIC = "segment_traffic"


class MetricUnit(str, Enum):
    """Units for network metrics."""
    
    # Time units
    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "min"
    HOURS = "h"
    
    # Data units
    BITS = "bits"
    BYTES = "bytes"
    KILOBYTES = "KB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"
    TERABYTES = "TB"
    
    # Rate units
    BITS_PER_SECOND = "bps"
    KILOBITS_PER_SECOND = "Kbps"
    MEGABITS_PER_SECOND = "Mbps"
    GIGABITS_PER_SECOND = "Gbps"
    PACKETS_PER_SECOND = "pps"
    
    # Percentage
    PERCENT = "%"
    RATIO = "ratio"
    
    # Count
    COUNT = "count"
    FREQUENCY = "frequency"
    
    # Currency
    USD = "usd"
    COST_UNITS = "cost_units"


class AggregationType(str, Enum):
    """Types of metric aggregation."""
    
    AVERAGE = "average"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    SUM = "sum"
    COUNT = "count"
    PERCENTILE_50 = "p50"
    PERCENTILE_90 = "p90"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"
    STANDARD_DEVIATION = "stddev"
    VARIANCE = "variance"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MetricDataPoint(TimestampMixin):
    """
    Individual metric data point with timestamp and value.
    
    Represents a single measurement at a specific point in time,
    with support for multi-dimensional metrics and metadata.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )
    
    # Core data point attributes
    metric_name: str = Field(description="Name of the metric")
    value: Union[float, int] = Field(description="Metric value")
    unit: MetricUnit = Field(description="Unit of measurement")
    
    # Dimensional attributes
    dimensions: Dict[str, str] = Field(
        default_factory=dict,
        description="Metric dimensions (region, element_id, etc.)"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional tags for categorization"
    )
    
    # Quality indicators
    quality_score: float = Field(
        default=1.0,
        ge=0.0, le=1.0,
        description="Data quality score (0.0-1.0)"
    )
    confidence_interval: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Confidence interval for the measurement"
    )
    
    # Source information
    source: str = Field(
        default="unknown",
        description="Data source (cloudwatch, flow_logs, etc.)"
    )
    collection_method: str = Field(
        default="polling",
        description="Collection method (polling, streaming, event-driven)"
    )
    
    # Context
    business_context: Optional[str] = Field(
        default=None,
        description="Business context for this metric"
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Correlation ID for related metrics"
    )

    def is_anomalous(self, baseline_value: float, threshold_percent: float = 20.0) -> bool:
        """Check if data point is anomalous compared to baseline."""
        if baseline_value == 0:
            return abs(self.value) > 0
        
        deviation_percent = abs((self.value - baseline_value) / baseline_value) * 100
        return deviation_percent > threshold_percent
    
    def get_normalized_value(self, target_unit: MetricUnit) -> float:
        """Convert value to target unit."""
        # Basic unit conversion logic (simplified)
        conversion_factors = {
            (MetricUnit.MILLISECONDS, MetricUnit.SECONDS): 0.001,
            (MetricUnit.SECONDS, MetricUnit.MILLISECONDS): 1000,
            (MetricUnit.MEGABYTES, MetricUnit.GIGABYTES): 0.001,
            (MetricUnit.GIGABYTES, MetricUnit.MEGABYTES): 1000,
            (MetricUnit.MEGABITS_PER_SECOND, MetricUnit.GIGABITS_PER_SECOND): 0.001,
            (MetricUnit.GIGABITS_PER_SECOND, MetricUnit.MEGABITS_PER_SECOND): 1000,
        }
        
        factor = conversion_factors.get((self.unit, target_unit), 1.0)
        return self.value * factor
    
    def to_summary(self) -> Dict[str, Any]:
        """Get summary representation of data point."""
        return {
            "metric": self.metric_name,
            "value": self.value,
            "unit": self.unit.value,
            "timestamp": self.created_at.isoformat(),
            "dimensions": self.dimensions,
            "quality": self.quality_score,
            "source": self.source
        }


class TimeSeriesData(BaseModel):
    """
    Time series data container for metric collection.
    
    Manages a collection of metric data points over time with
    aggregation, analysis, and trend detection capabilities.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )
    
    # Series identification
    series_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique time series identifier"
    )
    metric_name: str = Field(description="Name of the metric")
    dimensions: Dict[str, str] = Field(
        default_factory=dict,
        description="Common dimensions for all data points"
    )
    
    # Data points
    data_points: List[MetricDataPoint] = Field(
        default_factory=list,
        description="Time series data points"
    )
    start_time: Optional[datetime] = Field(
        default=None,
        description="Start time of the series"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="End time of the series"
    )
    
    # Aggregation settings
    resolution_seconds: int = Field(
        default=60,
        description="Time resolution in seconds"
    )
    max_data_points: int = Field(
        default=10000,
        description="Maximum number of data points to retain"
    )
    
    # Series statistics
    data_point_count: int = Field(
        default=0,
        description="Number of data points"
    )
    average_value: Optional[float] = Field(
        default=None,
        description="Average value across all points"
    )
    min_value: Optional[float] = Field(
        default=None,
        description="Minimum value"
    )
    max_value: Optional[float] = Field(
        default=None,
        description="Maximum value"
    )
    
    # Trend analysis
    trend_direction: Optional[str] = Field(
        default=None,
        description="Trend direction (increasing, decreasing, stable)"
    )
    trend_strength: Optional[float] = Field(
        default=None,
        description="Trend strength (0.0-1.0)"
    )
    anomaly_count: int = Field(
        default=0,
        description="Number of detected anomalies"
    )

    def add_data_point(self, data_point: MetricDataPoint) -> None:
        """Add data point to time series."""
        self.data_points.append(data_point)
        self.data_point_count += 1
        
        # Update time bounds
        if self.start_time is None or data_point.created_at < self.start_time:
            self.start_time = data_point.created_at
        if self.end_time is None or data_point.created_at > self.end_time:
            self.end_time = data_point.created_at
        
        # Maintain max data points limit
        if len(self.data_points) > self.max_data_points:
            self.data_points.pop(0)
        
        # Recalculate statistics
        self._update_statistics()
    
    def _update_statistics(self) -> None:
        """Update series statistics."""
        if not self.data_points:
            return
        
        values = [dp.value for dp in self.data_points]
        self.average_value = statistics.mean(values)
        self.min_value = min(values)
        self.max_value = max(values)
        
        # Simple trend detection
        if len(values) >= 3:
            recent_avg = statistics.mean(values[-3:])
            older_avg = statistics.mean(values[-6:-3]) if len(values) >= 6 else self.average_value
            
            if recent_avg > older_avg * 1.1:
                self.trend_direction = "increasing"
                self.trend_strength = min(1.0, (recent_avg - older_avg) / older_avg)
            elif recent_avg < older_avg * 0.9:
                self.trend_direction = "decreasing"
                self.trend_strength = min(1.0, (older_avg - recent_avg) / older_avg)
            else:
                self.trend_direction = "stable"
                self.trend_strength = 0.0
    
    def get_aggregate_value(self, aggregation: AggregationType, 
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> Optional[float]:
        """Get aggregated value for specified time range."""
        # Filter data points by time range
        filtered_points = self.data_points
        if start_time:
            filtered_points = [dp for dp in filtered_points if dp.created_at >= start_time]
        if end_time:
            filtered_points = [dp for dp in filtered_points if dp.created_at <= end_time]
        
        if not filtered_points:
            return None
        
        values = [dp.value for dp in filtered_points]
        
        if aggregation == AggregationType.AVERAGE:
            return statistics.mean(values)
        elif aggregation == AggregationType.MINIMUM:
            return min(values)
        elif aggregation == AggregationType.MAXIMUM:
            return max(values)
        elif aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.COUNT:
            return len(values)
        elif aggregation == AggregationType.PERCENTILE_50:
            return statistics.median(values)
        elif aggregation == AggregationType.PERCENTILE_90:
            return statistics.quantiles(values, n=10)[8] if len(values) > 1 else values[0]
        elif aggregation == AggregationType.PERCENTILE_95:
            return statistics.quantiles(values, n=20)[18] if len(values) > 1 else values[0]
        elif aggregation == AggregationType.PERCENTILE_99:
            return statistics.quantiles(values, n=100)[98] if len(values) > 1 else values[0]
        elif aggregation == AggregationType.STANDARD_DEVIATION:
            return statistics.stdev(values) if len(values) > 1 else 0.0
        elif aggregation == AggregationType.VARIANCE:
            return statistics.variance(values) if len(values) > 1 else 0.0
        
        return None
    
    def detect_anomalies(self, method: str = "statistical", 
                        threshold: float = 2.0) -> List[MetricDataPoint]:
        """Detect anomalous data points."""
        if len(self.data_points) < 3:
            return []
        
        anomalies = []
        values = [dp.value for dp in self.data_points]
        
        if method == "statistical":
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0
            
            for dp in self.data_points:
                if std_val > 0 and abs(dp.value - mean_val) > (threshold * std_val):
                    anomalies.append(dp)
        
        elif method == "percentile":
            # Use IQR method
            sorted_values = sorted(values)
            q1 = statistics.quantiles(sorted_values, n=4)[0] if len(sorted_values) > 1 else sorted_values[0]
            q3 = statistics.quantiles(sorted_values, n=4)[2] if len(sorted_values) > 1 else sorted_values[0]
            iqr = q3 - q1
            
            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)
            
            for dp in self.data_points:
                if dp.value < lower_bound or dp.value > upper_bound:
                    anomalies.append(dp)
        
        self.anomaly_count = len(anomalies)
        return anomalies
    
    def get_trend_summary(self) -> Dict[str, Any]:
        """Get trend analysis summary."""
        return {
            "direction": self.trend_direction,
            "strength": self.trend_strength,
            "data_points": self.data_point_count,
            "time_span_hours": ((self.end_time - self.start_time).total_seconds() / 3600 
                               if self.start_time and self.end_time else 0),
            "anomalies": self.anomaly_count,
            "statistics": {
                "average": self.average_value,
                "min": self.min_value,
                "max": self.max_value,
                "range": (self.max_value - self.min_value 
                         if self.min_value is not None and self.max_value is not None else 0)
            }
        }


class NetworkMetrics(TimestampMixin):
    """
    Network-level performance metrics for topology elements.
    
    Aggregates various network performance indicators for comprehensive
    monitoring and analysis of network element health and performance.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )
    
    # Target identification
    element_id: str = Field(description="Network element identifier")
    element_type: str = Field(description="Type of network element")
    region: str = Field(description="AWS region")
    
    # Time series data
    latency_series: Optional[TimeSeriesData] = Field(
        default=None,
        description="Latency measurements over time"
    )
    throughput_series: Optional[TimeSeriesData] = Field(
        default=None,
        description="Throughput measurements over time"
    )
    packet_loss_series: Optional[TimeSeriesData] = Field(
        default=None,
        description="Packet loss measurements over time"
    )
    utilization_series: Optional[TimeSeriesData] = Field(
        default=None,
        description="Utilization measurements over time"
    )
    
    # Current metrics snapshot
    current_latency_ms: Optional[float] = Field(
        default=None,
        description="Current latency in milliseconds"
    )
    current_throughput_mbps: Optional[float] = Field(
        default=None,
        description="Current throughput in Mbps"
    )
    current_packet_loss_rate: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Current packet loss rate"
    )
    current_utilization: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Current utilization percentage"
    )
    
    # Performance thresholds
    latency_threshold_ms: float = Field(
        default=100.0,
        description="Latency threshold in milliseconds"
    )
    packet_loss_threshold: float = Field(
        default=0.01,
        description="Packet loss threshold (1%)"
    )
    utilization_threshold: float = Field(
        default=0.8,
        description="Utilization threshold (80%)"
    )
    
    # Health indicators
    performance_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Overall performance score"
    )
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Current health status"
    )
    
    # SLA tracking
    sla_target_availability: float = Field(
        default=0.999,
        ge=0.0, le=1.0,
        description="SLA target availability"
    )
    current_availability: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Current availability"
    )
    sla_violations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="SLA violations in current period"
    )
    
    # Business metrics
    cost_per_gb: Optional[float] = Field(
        default=None,
        description="Cost per GB processed"
    )
    user_experience_score: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="User experience score"
    )

    def initialize_time_series(self) -> None:
        """Initialize time series data containers."""
        base_dimensions = {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "region": self.region
        }
        
        self.latency_series = TimeSeriesData(
            metric_name="latency",
            dimensions=base_dimensions
        )
        self.throughput_series = TimeSeriesData(
            metric_name="throughput", 
            dimensions=base_dimensions
        )
        self.packet_loss_series = TimeSeriesData(
            metric_name="packet_loss",
            dimensions=base_dimensions
        )
        self.utilization_series = TimeSeriesData(
            metric_name="utilization",
            dimensions=base_dimensions
        )
    
    def add_latency_measurement(self, latency_ms: float, source: str = "cloudwatch") -> None:
        """Add latency measurement."""
        if not self.latency_series:
            self.initialize_time_series()
        
        data_point = MetricDataPoint(
            metric_name="latency",
            value=latency_ms,
            unit=MetricUnit.MILLISECONDS,
            source=source,
            dimensions={"element_id": self.element_id}
        )
        
        self.latency_series.add_data_point(data_point)
        self.current_latency_ms = latency_ms
        self._update_performance_score()
    
    def add_throughput_measurement(self, throughput_mbps: float, source: str = "cloudwatch") -> None:
        """Add throughput measurement."""
        if not self.throughput_series:
            self.initialize_time_series()
        
        data_point = MetricDataPoint(
            metric_name="throughput",
            value=throughput_mbps,
            unit=MetricUnit.MEGABITS_PER_SECOND,
            source=source,
            dimensions={"element_id": self.element_id}
        )
        
        self.throughput_series.add_data_point(data_point)
        self.current_throughput_mbps = throughput_mbps
        self._update_performance_score()
    
    def add_packet_loss_measurement(self, loss_rate: float, source: str = "flow_logs") -> None:
        """Add packet loss measurement."""
        if not self.packet_loss_series:
            self.initialize_time_series()
        
        data_point = MetricDataPoint(
            metric_name="packet_loss",
            value=loss_rate,
            unit=MetricUnit.RATIO,
            source=source,
            dimensions={"element_id": self.element_id}
        )
        
        self.packet_loss_series.add_data_point(data_point)
        self.current_packet_loss_rate = loss_rate
        self._update_performance_score()
    
    def add_utilization_measurement(self, utilization: float, source: str = "cloudwatch") -> None:
        """Add utilization measurement."""
        if not self.utilization_series:
            self.initialize_time_series()
        
        data_point = MetricDataPoint(
            metric_name="utilization",
            value=utilization,
            unit=MetricUnit.PERCENT,
            source=source,
            dimensions={"element_id": self.element_id}
        )
        
        self.utilization_series.add_data_point(data_point)
        self.current_utilization = utilization
        self._update_performance_score()
    
    def _update_performance_score(self) -> None:
        """Update overall performance score."""
        score = 1.0
        
        # Latency impact
        if self.current_latency_ms is not None:
            if self.current_latency_ms > self.latency_threshold_ms * 2:
                score -= 0.3
            elif self.current_latency_ms > self.latency_threshold_ms:
                score -= 0.1
        
        # Packet loss impact  
        if self.current_packet_loss_rate is not None:
            if self.current_packet_loss_rate > self.packet_loss_threshold * 5:
                score -= 0.4
            elif self.current_packet_loss_rate > self.packet_loss_threshold:
                score -= 0.2
        
        # Utilization impact
        if self.current_utilization is not None:
            if self.current_utilization > 0.9:
                score -= 0.2
            elif self.current_utilization > self.utilization_threshold:
                score -= 0.1
        
        self.performance_score = max(0.0, score)
        
        # Update health status based on score
        if self.performance_score >= 0.9:
            self.health_status = HealthStatus.HEALTHY
        elif self.performance_score >= 0.7:
            self.health_status = HealthStatus.WARNING
        elif self.performance_score >= 0.5:
            self.health_status = HealthStatus.DEGRADED
        else:
            self.health_status = HealthStatus.UNHEALTHY
    
    def check_sla_compliance(self) -> bool:
        """Check if current metrics meet SLA targets."""
        # Simple SLA check based on availability and performance
        availability_ok = self.current_availability >= self.sla_target_availability
        performance_ok = self.performance_score >= 0.8
        
        return availability_ok and performance_ok
    
    def record_sla_violation(self, violation_type: str, description: str) -> None:
        """Record SLA violation."""
        violation = {
            "type": violation_type,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_score": self.performance_score,
            "availability": self.current_availability
        }
        
        self.sla_violations.append(violation)
        
        # Keep only recent violations (last 100)
        if len(self.sla_violations) > 100:
            self.sla_violations.pop(0)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            "element_id": self.element_id,
            "element_type": self.element_type,
            "region": self.region,
            "current_metrics": {
                "latency_ms": self.current_latency_ms,
                "throughput_mbps": self.current_throughput_mbps,
                "packet_loss_rate": self.current_packet_loss_rate,
                "utilization": self.current_utilization
            },
            "performance": {
                "score": self.performance_score,
                "health_status": self.health_status.value
            },
            "sla": {
                "target_availability": self.sla_target_availability,
                "current_availability": self.current_availability,
                "compliant": self.check_sla_compliance(),
                "violations_count": len(self.sla_violations)
            },
            "thresholds": {
                "latency_ms": self.latency_threshold_ms,
                "packet_loss": self.packet_loss_threshold,
                "utilization": self.utilization_threshold
            },
            "business": {
                "cost_per_gb": self.cost_per_gb,
                "user_experience": self.user_experience_score
            }
        }


class ConnectivityMetrics(TimestampMixin):
    """
    Connection-specific metrics for monitoring network links.
    
    Tracks performance, quality, and operational characteristics of
    individual network connections in the topology.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )
    
    # Connection identification
    connection_id: str = Field(description="Network connection identifier")
    source_element_id: str = Field(description="Source element ID")
    target_element_id: str = Field(description="Target element ID")
    connection_type: str = Field(description="Type of connection")
    
    # Performance metrics
    latency_ms: Optional[float] = Field(
        default=None,
        description="Connection latency in milliseconds"
    )
    bandwidth_utilization: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Bandwidth utilization ratio"
    )
    packet_loss_rate: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Packet loss rate"
    )
    jitter_ms: Optional[float] = Field(
        default=None,
        description="Network jitter in milliseconds"
    )
    
    # Quality indicators
    connection_quality_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Overall connection quality score"
    )
    stability_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Connection stability score"
    )
    
    # Availability tracking
    uptime_percentage: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Connection uptime percentage"
    )
    failure_count: int = Field(
        default=0,
        description="Number of connection failures"
    )
    last_failure: Optional[datetime] = Field(
        default=None,
        description="Last connection failure timestamp"
    )
    mean_time_to_recovery_minutes: Optional[float] = Field(
        default=None,
        description="Mean time to recovery in minutes"
    )
    
    # Traffic statistics
    bytes_transmitted: int = Field(
        default=0,
        description="Total bytes transmitted"
    )
    bytes_received: int = Field(
        default=0,
        description="Total bytes received"
    )
    packets_transmitted: int = Field(
        default=0,
        description="Total packets transmitted"
    )
    packets_received: int = Field(
        default=0,
        description="Total packets received"
    )
    
    # Cost and business metrics
    data_transfer_cost: Optional[float] = Field(
        default=None,
        description="Data transfer cost for this connection"
    )
    business_criticality: str = Field(
        default="medium",
        description="Business criticality level"
    )
    
    # Time series for trend analysis
    latency_history: List[Tuple[datetime, float]] = Field(
        default_factory=list,
        description="Recent latency measurements"
    )
    bandwidth_history: List[Tuple[datetime, float]] = Field(
        default_factory=list,
        description="Recent bandwidth utilization"
    )

    def update_latency(self, latency_ms: float) -> None:
        """Update connection latency."""
        self.latency_ms = latency_ms
        self.latency_history.append((datetime.now(timezone.utc), latency_ms))
        
        # Keep only recent history (last 100 measurements)
        if len(self.latency_history) > 100:
            self.latency_history.pop(0)
        
        self._update_quality_score()
    
    def update_bandwidth_utilization(self, utilization: float) -> None:
        """Update bandwidth utilization."""
        self.bandwidth_utilization = utilization
        self.bandwidth_history.append((datetime.now(timezone.utc), utilization))
        
        # Keep only recent history
        if len(self.bandwidth_history) > 100:
            self.bandwidth_history.pop(0)
        
        self._update_quality_score()
    
    def record_failure(self) -> None:
        """Record connection failure."""
        self.failure_count += 1
        self.last_failure = datetime.now(timezone.utc)
        self._update_quality_score()
    
    def record_traffic(self, bytes_tx: int, bytes_rx: int, 
                      packets_tx: int = 0, packets_rx: int = 0) -> None:
        """Record traffic statistics."""
        self.bytes_transmitted += bytes_tx
        self.bytes_received += bytes_rx
        self.packets_transmitted += packets_tx
        self.packets_received += packets_rx
        
        # Update cost if pricing is available
        if hasattr(self, '_data_transfer_rate_per_gb'):
            total_gb = (bytes_tx + bytes_rx) / (1024**3)
            self.data_transfer_cost = (self.data_transfer_cost or 0) + (total_gb * self._data_transfer_rate_per_gb)
    
    def _update_quality_score(self) -> None:
        """Update connection quality score."""
        score = 1.0
        
        # Latency impact
        if self.latency_ms is not None:
            if self.latency_ms > 200:
                score -= 0.3
            elif self.latency_ms > 100:
                score -= 0.1
        
        # Packet loss impact
        if self.packet_loss_rate is not None:
            score -= min(0.4, self.packet_loss_rate * 10)
        
        # Failure impact
        if self.failure_count > 0:
            score -= min(0.3, self.failure_count * 0.05)
        
        # Utilization impact (too high utilization)
        if self.bandwidth_utilization is not None and self.bandwidth_utilization > 0.9:
            score -= 0.2
        
        self.connection_quality_score = max(0.0, score)
        
        # Calculate stability score based on consistency
        if len(self.latency_history) > 3:
            recent_latencies = [l[1] for l in self.latency_history[-5:]]
            if recent_latencies:
                avg_latency = sum(recent_latencies) / len(recent_latencies)
                if avg_latency > 0:
                    variance = sum((l - avg_latency) ** 2 for l in recent_latencies) / len(recent_latencies)
                    stability = 1.0 - min(1.0, variance / (avg_latency ** 2))
                    self.stability_score = max(0.0, stability)
    
    def get_throughput_mbps(self) -> Optional[float]:
        """Calculate current throughput in Mbps."""
        if not self.bandwidth_history:
            return None
        
        # Get recent bandwidth measurements and calculate throughput
        recent_measurements = self.bandwidth_history[-10:]  # Last 10 measurements
        if len(recent_measurements) < 2:
            return None
        
        # Simple throughput calculation based on utilization trend
        avg_utilization = sum(m[1] for m in recent_measurements) / len(recent_measurements)
        
        # Assume 1 Gbps base capacity (simplified)
        base_capacity_mbps = 1000.0
        return avg_utilization * base_capacity_mbps
    
    def is_high_latency(self, threshold_ms: float = 100.0) -> bool:
        """Check if connection has high latency."""
        return self.latency_ms is not None and self.latency_ms > threshold_ms
    
    def is_congested(self, threshold: float = 0.8) -> bool:
        """Check if connection is congested."""
        return (self.bandwidth_utilization is not None and 
                self.bandwidth_utilization > threshold)
    
    def get_availability_percentage(self) -> float:
        """Calculate availability percentage."""
        if self.uptime_percentage is not None:
            return self.uptime_percentage * 100
        
        # Simple calculation based on failures
        # Assume 24 hour period for calculation
        if self.failure_count == 0:
            return 100.0
        
        # Estimate downtime based on failures and recovery time
        recovery_time = self.mean_time_to_recovery_minutes or 10  # Default 10 minutes
        total_downtime_minutes = self.failure_count * recovery_time
        total_period_minutes = 24 * 60  # 24 hours
        
        uptime_percentage = max(0, 1.0 - (total_downtime_minutes / total_period_minutes))
        return uptime_percentage * 100
    
    def get_connectivity_summary(self) -> Dict[str, Any]:
        """Get comprehensive connectivity metrics summary."""
        return {
            "connection_id": self.connection_id,
            "source_element": self.source_element_id,
            "target_element": self.target_element_id,
            "connection_type": self.connection_type,
            "performance": {
                "latency_ms": self.latency_ms,
                "bandwidth_utilization": self.bandwidth_utilization,
                "packet_loss_rate": self.packet_loss_rate,
                "jitter_ms": self.jitter_ms,
                "throughput_mbps": self.get_throughput_mbps()
            },
            "quality": {
                "quality_score": self.connection_quality_score,
                "stability_score": self.stability_score,
                "is_high_latency": self.is_high_latency(),
                "is_congested": self.is_congested()
            },
            "availability": {
                "uptime_percentage": self.get_availability_percentage(),
                "failure_count": self.failure_count,
                "last_failure": self.last_failure.isoformat() if self.last_failure else None,
                "mttr_minutes": self.mean_time_to_recovery_minutes
            },
            "traffic": {
                "bytes_transmitted": self.bytes_transmitted,
                "bytes_received": self.bytes_received,
                "packets_transmitted": self.packets_transmitted,
                "packets_received": self.packets_received
            },
            "business": {
                "criticality": self.business_criticality,
                "cost": self.data_transfer_cost
            }
        }


class TopologyMetrics(TimestampMixin):
    """
    Topology-wide metrics for comprehensive network analysis.
    
    Aggregates metrics across all elements and connections to provide
    holistic view of network topology health and performance.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )
    
    # Topology identification
    topology_id: str = Field(description="Topology identifier")
    topology_name: str = Field(description="Topology name")
    scope: str = Field(description="Topology scope")
    
    # Overall health metrics
    overall_health_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Overall topology health score"
    )
    element_health_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of element health statuses"
    )
    connection_health_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of connection health statuses"
    )
    
    # Performance aggregates
    average_latency_ms: Optional[float] = Field(
        default=None,
        description="Average latency across all connections"
    )
    max_latency_ms: Optional[float] = Field(
        default=None,
        description="Maximum latency in topology"
    )
    total_throughput_gbps: Optional[float] = Field(
        default=None,
        description="Total throughput in Gbps"
    )
    average_utilization: Optional[float] = Field(
        default=None,
        description="Average utilization across elements"
    )
    
    # Availability metrics
    overall_availability: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Overall topology availability"
    )
    critical_path_availability: Optional[float] = Field(
        default=None,
        description="Availability of most critical paths"
    )
    
    # Capacity and scaling
    capacity_utilization_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of capacity utilization levels"
    )
    elements_near_capacity: List[str] = Field(
        default_factory=list,
        description="Elements approaching capacity limits"
    )
    
    # Anomalies and issues
    active_anomalies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Currently active anomalies"
    )
    performance_degradations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Elements with performance degradation"
    )
    
    # Business impact
    service_impact_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Business service impact score"
    )
    cost_efficiency_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Cost efficiency score"
    )
    
    # Regional distribution
    region_health_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Health scores by region"
    )
    cross_region_latency: Dict[str, float] = Field(
        default_factory=dict,
        description="Cross-region latency measurements"
    )

    def update_from_element_metrics(self, element_metrics: List[NetworkMetrics]) -> None:
        """Update topology metrics from element metrics."""
        if not element_metrics:
            return
        
        # Calculate health distribution
        health_counts = defaultdict(int)
        performance_scores = []
        utilizations = []
        
        for metrics in element_metrics:
            health_counts[metrics.health_status.value] += 1
            performance_scores.append(metrics.performance_score)
            if metrics.current_utilization is not None:
                utilizations.append(metrics.current_utilization)
        
        self.element_health_distribution = dict(health_counts)
        
        # Calculate overall scores
        if performance_scores:
            self.overall_health_score = sum(performance_scores) / len(performance_scores)
        
        if utilizations:
            self.average_utilization = sum(utilizations) / len(utilizations)
            
            # Identify elements near capacity
            self.elements_near_capacity = [
                metrics.element_id for metrics in element_metrics
                if metrics.current_utilization is not None and metrics.current_utilization > 0.8
            ]
    
    def update_from_connection_metrics(self, connection_metrics: List[ConnectivityMetrics]) -> None:
        """Update topology metrics from connection metrics."""
        if not connection_metrics:
            return
        
        # Calculate connection health distribution
        quality_scores = []
        latencies = []
        throughputs = []
        
        for metrics in connection_metrics:
            quality_scores.append(metrics.connection_quality_score)
            if metrics.latency_ms is not None:
                latencies.append(metrics.latency_ms)
            
            throughput = metrics.get_throughput_mbps()
            if throughput is not None:
                throughputs.append(throughput)
        
        # Calculate aggregates
        if latencies:
            self.average_latency_ms = sum(latencies) / len(latencies)
            self.max_latency_ms = max(latencies)
        
        if throughputs:
            self.total_throughput_gbps = sum(throughputs) / 1000  # Convert to Gbps
    
    def detect_topology_anomalies(self) -> List[Dict[str, Any]]:
        """Detect topology-wide anomalies."""
        anomalies = []
        
        # Check for overall poor health
        if self.overall_health_score < 0.6:
            anomalies.append({
                "type": "poor_overall_health",
                "severity": "high",
                "description": f"Overall health score is {self.overall_health_score:.2f}",
                "affected_scope": "topology-wide"
            })
        
        # Check for high latency
        if self.max_latency_ms and self.max_latency_ms > 500:
            anomalies.append({
                "type": "high_latency",
                "severity": "medium",
                "description": f"Maximum latency is {self.max_latency_ms:.2f}ms",
                "affected_scope": "connectivity"
            })
        
        # Check for capacity issues
        if len(self.elements_near_capacity) > len(self.element_health_distribution) * 0.3:
            anomalies.append({
                "type": "capacity_pressure",
                "severity": "medium",
                "description": f"{len(self.elements_near_capacity)} elements near capacity",
                "affected_elements": self.elements_near_capacity
            })
        
        self.active_anomalies = anomalies
        return anomalies
    
    def calculate_service_impact(self) -> float:
        """Calculate business service impact score."""
        impact_factors = []
        
        # Health impact
        health_impact = 1.0 - self.overall_health_score
        impact_factors.append(health_impact * 0.4)
        
        # Availability impact
        availability_impact = 1.0 - self.overall_availability
        impact_factors.append(availability_impact * 0.3)
        
        # Capacity impact
        if self.average_utilization is not None:
            capacity_impact = max(0, self.average_utilization - 0.8) / 0.2
            impact_factors.append(capacity_impact * 0.2)
        
        # Anomaly impact
        anomaly_impact = min(1.0, len(self.active_anomalies) / 10.0)
        impact_factors.append(anomaly_impact * 0.1)
        
        self.service_impact_score = min(1.0, sum(impact_factors))
        return self.service_impact_score
    
    def get_topology_summary(self) -> Dict[str, Any]:
        """Get comprehensive topology metrics summary."""
        return {
            "topology": {
                "id": self.topology_id,
                "name": self.topology_name,
                "scope": self.scope
            },
            "health": {
                "overall_score": self.overall_health_score,
                "element_distribution": self.element_health_distribution,
                "connection_distribution": self.connection_health_distribution
            },
            "performance": {
                "average_latency_ms": self.average_latency_ms,
                "max_latency_ms": self.max_latency_ms,
                "total_throughput_gbps": self.total_throughput_gbps,
                "average_utilization": self.average_utilization
            },
            "availability": {
                "overall": self.overall_availability,
                "critical_path": self.critical_path_availability
            },
            "capacity": {
                "elements_near_capacity": len(self.elements_near_capacity),
                "utilization_distribution": self.capacity_utilization_distribution
            },
            "issues": {
                "active_anomalies": len(self.active_anomalies),
                "performance_degradations": len(self.performance_degradations)
            },
            "business": {
                "service_impact": self.service_impact_score,
                "cost_efficiency": self.cost_efficiency_score
            },
            "regional": {
                "regions": list(self.region_health_scores.keys()),
                "cross_region_latency": self.cross_region_latency
            }
        }


class NetworkHealth(TimestampMixin):
    """
    Comprehensive network health assessment model.
    
    Provides unified health assessment across all network components
    with business impact analysis and operational recommendations.
    """
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True
    )
    
    # Assessment identification
    assessment_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique assessment identifier"
    )
    topology_id: str = Field(description="Associated topology ID")
    
    # Overall health indicators
    overall_health_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Overall network health score"
    )
    health_status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Overall health status"
    )
    
    # Component health breakdown
    element_health_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Health scores by element ID"
    )
    connection_health_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Health scores by connection ID"
    )
    service_health_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Health scores by service/application"
    )
    
    # Critical issues
    critical_issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Critical issues requiring immediate attention"
    )
    warnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Warning-level issues"
    )
    
    # Business impact assessment
    business_impact_level: str = Field(
        default="unknown",
        description="Business impact level (critical, high, medium, low)"
    )
    affected_services: List[str] = Field(
        default_factory=list,
        description="List of affected business services"
    )
    estimated_user_impact: Optional[int] = Field(
        default=None,
        description="Estimated number of affected users"
    )
    
    # Operational recommendations
    immediate_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Immediate actions recommended"
    )
    preventive_actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Preventive actions for future issues"
    )
    
    # Trend analysis
    health_trend: str = Field(
        default="stable",
        description="Health trend (improving, degrading, stable)"
    )
    trend_confidence: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Confidence in trend analysis"
    )
    
    # SLA and compliance
    sla_compliance_status: bool = Field(
        default=True,
        description="Whether network meets SLA requirements"
    )
    compliance_violations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Current compliance violations"
    )

    def add_critical_issue(self, issue_type: str, description: str, 
                          affected_components: List[str], 
                          severity: AlertSeverity = AlertSeverity.CRITICAL) -> None:
        """Add critical issue to assessment."""
        issue = {
            "id": str(uuid4()),
            "type": issue_type,
            "description": description,
            "severity": severity.value,
            "affected_components": affected_components,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "resolved": False
        }
        
        if severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH):
            self.critical_issues.append(issue)
        else:
            self.warnings.append(issue)
    
    def add_recommendation(self, action_type: str, description: str, 
                          priority: str, estimated_effort: str = "unknown") -> None:
        """Add operational recommendation."""
        recommendation = {
            "id": str(uuid4()),
            "type": action_type,
            "description": description,
            "priority": priority,
            "estimated_effort": estimated_effort,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        if priority in ("critical", "high"):
            self.immediate_actions.append(recommendation)
        else:
            self.preventive_actions.append(recommendation)
    
    def calculate_overall_health(self, element_metrics: List[NetworkMetrics],
                               connection_metrics: List[ConnectivityMetrics]) -> None:
        """Calculate overall health from component metrics."""
        # Collect all health scores
        all_scores = []
        
        # Element health scores
        for metrics in element_metrics:
            score = metrics.performance_score
            self.element_health_scores[metrics.element_id] = score
            all_scores.append(score)
        
        # Connection health scores
        for metrics in connection_metrics:
            score = metrics.connection_quality_score
            self.connection_health_scores[metrics.connection_id] = score
            all_scores.append(score)
        
        # Calculate weighted average (elements have higher weight)
        if all_scores:
            element_weight = 0.7
            connection_weight = 0.3
            
            element_avg = (sum(self.element_health_scores.values()) / 
                          len(self.element_health_scores)) if self.element_health_scores else 0.0
            connection_avg = (sum(self.connection_health_scores.values()) / 
                             len(self.connection_health_scores)) if self.connection_health_scores else 0.0
            
            self.overall_health_score = (element_avg * element_weight + 
                                       connection_avg * connection_weight)
        else:
            self.overall_health_score = 0.0
        
        # Determine health status
        if self.overall_health_score >= 0.9:
            self.health_status = HealthStatus.HEALTHY
        elif self.overall_health_score >= 0.7:
            self.health_status = HealthStatus.WARNING
        elif self.overall_health_score >= 0.5:
            self.health_status = HealthStatus.DEGRADED
        elif self.overall_health_score >= 0.3:
            self.health_status = HealthStatus.UNHEALTHY
        else:
            self.health_status = HealthStatus.CRITICAL
    
    def assess_business_impact(self) -> None:
        """Assess business impact of current health status."""
        # Determine impact level based on health score and critical issues
        if self.health_status == HealthStatus.CRITICAL or len(self.critical_issues) > 0:
            self.business_impact_level = "critical"
            self.estimated_user_impact = 10000  # High estimate for critical issues
        elif self.health_status == HealthStatus.UNHEALTHY:
            self.business_impact_level = "high"
            self.estimated_user_impact = 1000
        elif self.health_status == HealthStatus.DEGRADED:
            self.business_impact_level = "medium"
            self.estimated_user_impact = 100
        else:
            self.business_impact_level = "low"
            self.estimated_user_impact = 0
        
        # Identify affected services based on poor-performing elements
        for element_id, score in self.element_health_scores.items():
            if score < 0.7:  # Poor performance threshold
                service_name = f"service_for_{element_id}"  # Simplified mapping
                if service_name not in self.affected_services:
                    self.affected_services.append(service_name)
    
    def generate_recommendations(self) -> None:
        """Generate operational recommendations based on assessment."""
        # Critical issues recommendations
        if len(self.critical_issues) > 0:
            self.add_recommendation(
                "incident_response",
                "Investigate and resolve critical network issues immediately",
                "critical",
                "2-4 hours"
            )
        
        # Poor performing elements
        poor_elements = [elem_id for elem_id, score in self.element_health_scores.items() 
                        if score < 0.6]
        if poor_elements:
            self.add_recommendation(
                "performance_optimization",
                f"Optimize performance for {len(poor_elements)} poorly performing elements",
                "high",
                "1-2 days"
            )
        
        # Capacity planning
        near_capacity_count = len([score for score in self.element_health_scores.values() 
                                  if score < 0.8])  # Simplified capacity check
        if near_capacity_count > len(self.element_health_scores) * 0.3:
            self.add_recommendation(
                "capacity_planning",
                "Review and expand network capacity for overloaded elements",
                "medium",
                "1-2 weeks"
            )
        
        # General health maintenance
        if self.overall_health_score < 0.9:
            self.add_recommendation(
                "health_maintenance",
                "Implement regular health monitoring and maintenance procedures",
                "low",
                "ongoing"
            )
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health assessment report."""
        return {
            "assessment_id": self.assessment_id,
            "topology_id": self.topology_id,
            "timestamp": self.created_at.isoformat(),
            "overall": {
                "health_score": self.overall_health_score,
                "health_status": self.health_status.value,
                "trend": self.health_trend,
                "trend_confidence": self.trend_confidence
            },
            "components": {
                "elements_assessed": len(self.element_health_scores),
                "connections_assessed": len(self.connection_health_scores),
                "services_assessed": len(self.service_health_scores),
                "avg_element_health": (sum(self.element_health_scores.values()) / 
                                     len(self.element_health_scores)) if self.element_health_scores else 0.0,
                "avg_connection_health": (sum(self.connection_health_scores.values()) / 
                                        len(self.connection_health_scores)) if self.connection_health_scores else 0.0
            },
            "issues": {
                "critical_count": len(self.critical_issues),
                "warning_count": len(self.warnings),
                "critical_issues": self.critical_issues[:5],  # Top 5 critical issues
                "recent_warnings": self.warnings[:10]  # Top 10 warnings
            },
            "business_impact": {
                "impact_level": self.business_impact_level,
                "affected_services": self.affected_services,
                "estimated_user_impact": self.estimated_user_impact
            },
            "recommendations": {
                "immediate_actions": len(self.immediate_actions),
                "preventive_actions": len(self.preventive_actions),
                "top_immediate": self.immediate_actions[:3],  # Top 3 immediate actions
                "top_preventive": self.preventive_actions[:5]  # Top 5 preventive actions
            },
            "compliance": {
                "sla_compliant": self.sla_compliance_status,
                "violations": len(self.compliance_violations)
            }
        }


# Export all classes
__all__ = [
    'MetricType',
    'MetricUnit',
    'AggregationType',
    'AlertSeverity',
    'MetricDataPoint',
    'TimeSeriesData',
    'NetworkMetrics',
    'ConnectivityMetrics',
    'TopologyMetrics',
    'NetworkHealth',
]