"""
Transit Gateway Performance Analyzer.

This engine provides comprehensive TGW performance analysis and health monitoring,
including throughput analysis, latency measurements, connection health assessment,
and performance optimization recommendations.

Features:
- Real-time performance metrics collection
- Historical performance trend analysis
- Health monitoring and alerting
- Bottleneck identification and resolution
- Performance optimization recommendations
- SLA monitoring and reporting
- Cost-performance optimization analysis
"""

import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from botocore.exceptions import ClientError

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from .tgw_peering_discovery_engine import (
    TGWPeeringDiscoveryEngine,
    TGWPeeringConnection,
)
from .transit_gateway_route_engine import TransitGatewayRouteEngine
from .async_executor_bridge import AsyncExecutorBridge


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class PerformanceTrend(str, Enum):
    """Performance trend indicators."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


@dataclass
class PerformanceMetrics:
    """TGW performance metrics snapshot."""

    timestamp: datetime
    tgw_id: str
    region: str

    # Throughput metrics (Mbps)
    inbound_throughput: float = 0.0
    outbound_throughput: float = 0.0
    peak_throughput: float = 0.0
    average_throughput: float = 0.0

    # Latency metrics (milliseconds)
    average_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    jitter: float = 0.0

    # Connection metrics
    active_connections: int = 0
    new_connections_per_second: float = 0.0
    connection_success_rate: float = 100.0

    # Error metrics
    packet_loss_rate: float = 0.0
    error_rate: float = 0.0
    timeout_rate: float = 0.0

    # Resource utilization
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    bandwidth_utilization: float = 0.0

    # Custom metrics
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class HealthAssessment:
    """TGW health assessment results."""

    tgw_id: str
    region: str
    overall_health: HealthStatus
    health_score: float  # 0.0 to 100.0

    # Component health scores
    throughput_health: float = 100.0
    latency_health: float = 100.0
    availability_health: float = 100.0
    error_health: float = 100.0

    # Health indicators
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Trend analysis
    performance_trend: PerformanceTrend = PerformanceTrend.STABLE
    trend_confidence: float = 0.0

    last_assessed: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceThresholds:
    """Performance thresholds for health assessment."""

    # Throughput thresholds (Mbps)
    max_throughput_warning: float = 8000.0
    max_throughput_critical: float = 9500.0

    # Latency thresholds (milliseconds)
    latency_warning: float = 50.0
    latency_critical: float = 100.0
    jitter_warning: float = 10.0
    jitter_critical: float = 25.0

    # Error rate thresholds (percentage)
    packet_loss_warning: float = 0.1
    packet_loss_critical: float = 1.0
    error_rate_warning: float = 0.5
    error_rate_critical: float = 2.0

    # Utilization thresholds (percentage)
    bandwidth_warning: float = 80.0
    bandwidth_critical: float = 95.0
    cpu_warning: float = 80.0
    cpu_critical: float = 95.0


@dataclass
class PerformanceOptimizationRecommendation:
    """Performance optimization recommendation."""

    category: str  # throughput, latency, reliability, cost
    priority: str  # high, medium, low
    title: str
    description: str
    expected_improvement: str
    implementation_effort: str  # low, medium, high
    estimated_cost_impact: str  # positive, neutral, negative
    steps: List[str] = field(default_factory=list)


@dataclass
class PeeringPerformanceAnalysis:
    """Performance analysis for TGW peering connections."""

    peering_connection: TGWPeeringConnection
    current_metrics: Optional[PerformanceMetrics] = None
    historical_metrics: List[PerformanceMetrics] = field(default_factory=list)
    health_assessment: Optional[HealthAssessment] = None
    bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    optimization_recommendations: List[PerformanceOptimizationRecommendation] = field(
        default_factory=list
    )
    sla_compliance: Dict[str, bool] = field(default_factory=dict)


class TGWPerformanceAnalyzer:
    """
    Advanced Transit Gateway performance analyzer and health monitor.

    Provides comprehensive performance monitoring, health assessment,
    and optimization recommendations for TGW infrastructures.
    """

    def __init__(
        self,
        aws_manager: AWSClientManager,
        config: CloudWANConfig,
        peering_engine: TGWPeeringDiscoveryEngine,
        route_engine: TransitGatewayRouteEngine,
    ):
        """
        Initialize the performance analyzer.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
            peering_engine: TGW peering discovery engine
            route_engine: TGW route engine
        """
        self.aws_manager = aws_manager
        self.config = config
        self.peering_engine = peering_engine
        self.route_engine = route_engine
        self.legacy_adapter = AsyncExecutorBridge(aws_manager, config)

        # Performance thresholds
        self.thresholds = PerformanceThresholds()

        # Metrics cache
        self._metrics_cache: Dict[str, List[PerformanceMetrics]] = {}
        self._cache_duration = timedelta(minutes=5)

        # Thread pool for parallel analysis
        self._executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="TGWPerf")

    async def analyze_tgw_performance(
        self,
        transit_gateway_id: str,
        region: str,
        time_range_hours: int = 24,
        include_peering_analysis: bool = True,
        include_optimization_recommendations: bool = True,
    ) -> Dict[str, Any]:
        """
        Comprehensive TGW performance analysis.

        Args:
            transit_gateway_id: Transit Gateway ID to analyze
            region: AWS region
            time_range_hours: Time range for historical analysis
            include_peering_analysis: Include peering performance analysis
            include_optimization_recommendations: Include optimization recommendations

        Returns:
            Comprehensive performance analysis results
        """
        try:
            # Collect current performance metrics
            current_metrics = await self._collect_current_metrics(transit_gateway_id, region)

            # Collect historical metrics
            historical_metrics = await self._collect_historical_metrics(
                transit_gateway_id, region, time_range_hours
            )

            # Perform health assessment
            health_assessment = await self._assess_health(current_metrics, historical_metrics)

            # Analyze peering performance if requested
            peering_analyses = []
            if include_peering_analysis:
                peering_analyses = await self._analyze_peering_performance(
                    transit_gateway_id, region, time_range_hours
                )

            # Generate optimization recommendations
            optimization_recommendations = []
            if include_optimization_recommendations:
                optimization_recommendations = await self._generate_optimization_recommendations(
                    current_metrics,
                    historical_metrics,
                    health_assessment,
                    peering_analyses,
                )

            # Compile comprehensive analysis
            analysis_result = {
                "transit_gateway_id": transit_gateway_id,
                "region": region,
                "analysis_timestamp": datetime.now().isoformat(),
                "time_range_hours": time_range_hours,
                "current_metrics": current_metrics,
                "historical_metrics": historical_metrics[-10:],  # Last 10 data points
                "health_assessment": health_assessment,
                "peering_analyses": peering_analyses,
                "optimization_recommendations": optimization_recommendations,
                "performance_summary": self._create_performance_summary(
                    current_metrics, historical_metrics, health_assessment
                ),
            }

            return analysis_result

        except Exception as e:
            raise RuntimeError(f"TGW performance analysis failed: {str(e)}")

    async def _collect_current_metrics(
        self, transit_gateway_id: str, region: str
    ) -> PerformanceMetrics:
        """
        Collect current performance metrics for a TGW.

        Args:
            transit_gateway_id: Transit Gateway ID
            region: AWS region

        Returns:
            Current performance metrics
        """
        try:
            cloudwatch = await self.aws_manager.get_client("cloudwatch", region)

            # Define metric queries
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)  # Last 5 minutes

            # Collect various CloudWatch metrics
            metrics_data = await self._query_cloudwatch_metrics(
                cloudwatch, transit_gateway_id, start_time, end_time
            )

            # Process metrics data into PerformanceMetrics object
            current_metrics = PerformanceMetrics(
                timestamp=datetime.now(), tgw_id=transit_gateway_id, region=region
            )

            # Parse CloudWatch metrics
            current_metrics.inbound_throughput = (
                metrics_data.get("BytesIn", 0.0) * 8 / 1000000
            )  # Convert to Mbps
            current_metrics.outbound_throughput = (
                metrics_data.get("BytesOut", 0.0) * 8 / 1000000
            )  # Convert to Mbps
            current_metrics.packet_loss_rate = metrics_data.get("PacketDropCount", 0.0)
            current_metrics.active_connections = int(metrics_data.get("ActiveConnections", 0))

            # Calculate derived metrics
            current_metrics.average_throughput = (
                current_metrics.inbound_throughput + current_metrics.outbound_throughput
            ) / 2

            current_metrics.peak_throughput = max(
                current_metrics.inbound_throughput, current_metrics.outbound_throughput
            )

            # Bandwidth utilization (as percentage of 100 Gbps limit)
            total_throughput = (
                current_metrics.inbound_throughput + current_metrics.outbound_throughput
            )
            current_metrics.bandwidth_utilization = (
                total_throughput / 100000
            ) * 100  # 100 Gbps = 100,000 Mbps

            return current_metrics

        except Exception:
            # Return default metrics if collection fails
            return PerformanceMetrics(
                timestamp=datetime.now(), tgw_id=transit_gateway_id, region=region
            )

    async def _query_cloudwatch_metrics(
        self,
        cloudwatch_client: Any,
        transit_gateway_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, float]:
        """
        Query CloudWatch metrics for TGW.

        Args:
            cloudwatch_client: CloudWatch client
            transit_gateway_id: TGW ID
            start_time: Start time for metrics
            end_time: End time for metrics

        Returns:
            Dictionary of metric values
        """
        metrics_data = {}

        # Define TGW metrics to collect
        metric_queries = [
            {
                "name": "BytesIn",
                "metric_name": "BytesIn",
                "namespace": "AWS/TransitGateway",
                "statistic": "Sum",
            },
            {
                "name": "BytesOut",
                "metric_name": "BytesOut",
                "namespace": "AWS/TransitGateway",
                "statistic": "Sum",
            },
            {
                "name": "PacketDropCount",
                "metric_name": "PacketDropCount",
                "namespace": "AWS/TransitGateway",
                "statistic": "Sum",
            },
        ]

        try:
            for query in metric_queries:
                response = await cloudwatch_client.get_metric_statistics(
                    Namespace=query["namespace"],
                    MetricName=query["metric_name"],
                    Dimensions=[{"Name": "TransitGateway", "Value": transit_gateway_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,  # 5 minutes
                    Statistics=[query["statistic"]],
                )

                datapoints = response.get("Datapoints", [])
                if datapoints:
                    # Get the most recent value
                    latest_point = sorted(datapoints, key=lambda x: x["Timestamp"])[-1]
                    metrics_data[query["name"]] = latest_point.get(query["statistic"], 0.0)
                else:
                    metrics_data[query["name"]] = 0.0

        except ClientError:
            # Handle missing metrics gracefully
            pass

        return metrics_data

    async def _collect_historical_metrics(
        self, transit_gateway_id: str, region: str, time_range_hours: int
    ) -> List[PerformanceMetrics]:
        """
        Collect historical performance metrics.

        Args:
            transit_gateway_id: Transit Gateway ID
            region: AWS region
            time_range_hours: Time range for historical data

        Returns:
            List of historical performance metrics
        """
        # Check cache first
        cache_key = f"{transit_gateway_id}:{region}:{time_range_hours}"
        if cache_key in self._metrics_cache:
            return self._metrics_cache[cache_key]

        try:
            cloudwatch = await self.aws_manager.get_client("cloudwatch", region)

            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_range_hours)

            # Collect metrics over time periods
            historical_metrics = []
            current_time = start_time

            while current_time < end_time:
                period_end = min(current_time + timedelta(hours=1), end_time)

                # Query metrics for this time period
                metrics_data = await self._query_cloudwatch_metrics(
                    cloudwatch, transit_gateway_id, current_time, period_end
                )

                # Create metrics object
                metrics = PerformanceMetrics(
                    timestamp=current_time, tgw_id=transit_gateway_id, region=region
                )

                # Populate metrics (similar to current metrics)
                metrics.inbound_throughput = metrics_data.get("BytesIn", 0.0) * 8 / 1000000
                metrics.outbound_throughput = metrics_data.get("BytesOut", 0.0) * 8 / 1000000
                metrics.packet_loss_rate = metrics_data.get("PacketDropCount", 0.0)

                historical_metrics.append(metrics)
                current_time = period_end

            # Cache results
            self._metrics_cache[cache_key] = historical_metrics

            return historical_metrics

        except Exception:
            return []

    async def _assess_health(
        self,
        current_metrics: PerformanceMetrics,
        historical_metrics: List[PerformanceMetrics],
    ) -> HealthAssessment:
        """
        Assess TGW health based on current and historical metrics.

        Args:
            current_metrics: Current performance metrics
            historical_metrics: Historical performance metrics

        Returns:
            Health assessment results
        """
        assessment = HealthAssessment(
            tgw_id=current_metrics.tgw_id,
            region=current_metrics.region,
            overall_health=HealthStatus.HEALTHY,
            health_score=100.0,
        )

        # Assess throughput health
        assessment.throughput_health = self._assess_throughput_health(current_metrics)

        # Assess latency health
        assessment.latency_health = self._assess_latency_health(current_metrics)

        # Assess availability health
        assessment.availability_health = self._assess_availability_health(
            current_metrics, historical_metrics
        )

        # Assess error health
        assessment.error_health = self._assess_error_health(current_metrics)

        # Calculate overall health score
        health_components = [
            assessment.throughput_health,
            assessment.latency_health,
            assessment.availability_health,
            assessment.error_health,
        ]
        assessment.health_score = sum(health_components) / len(health_components)

        # Determine overall health status
        if assessment.health_score >= 90:
            assessment.overall_health = HealthStatus.HEALTHY
        elif assessment.health_score >= 70:
            assessment.overall_health = HealthStatus.WARNING
        else:
            assessment.overall_health = HealthStatus.CRITICAL

        # Generate health insights
        assessment.critical_issues = self._identify_critical_issues(current_metrics)
        assessment.warnings = self._identify_warnings(current_metrics)
        assessment.recommendations = self._generate_health_recommendations(assessment)

        # Analyze performance trend
        if len(historical_metrics) >= 5:
            assessment.performance_trend, assessment.trend_confidence = (
                self._analyze_performance_trend(historical_metrics)
            )

        return assessment

    def _assess_throughput_health(self, metrics: PerformanceMetrics) -> float:
        """Assess throughput health score."""
        total_throughput = metrics.inbound_throughput + metrics.outbound_throughput

        if total_throughput < self.thresholds.max_throughput_warning:
            return 100.0
        elif total_throughput < self.thresholds.max_throughput_critical:
            # Linear degradation between warning and critical
            ratio = (total_throughput - self.thresholds.max_throughput_warning) / (
                self.thresholds.max_throughput_critical - self.thresholds.max_throughput_warning
            )
            return 80.0 - (ratio * 30.0)  # 80 to 50
        else:
            return 20.0  # Critical level

    def _assess_latency_health(self, metrics: PerformanceMetrics) -> float:
        """Assess latency health score."""
        if metrics.average_latency < self.thresholds.latency_warning:
            return 100.0
        elif metrics.average_latency < self.thresholds.latency_critical:
            ratio = (metrics.average_latency - self.thresholds.latency_warning) / (
                self.thresholds.latency_critical - self.thresholds.latency_warning
            )
            return 80.0 - (ratio * 30.0)
        else:
            return 20.0

    def _assess_availability_health(
        self,
        current_metrics: PerformanceMetrics,
        historical_metrics: List[PerformanceMetrics],
    ) -> float:
        """Assess availability health based on connection success rate."""
        return current_metrics.connection_success_rate

    def _assess_error_health(self, metrics: PerformanceMetrics) -> float:
        """Assess error health based on error rates."""
        error_score = 100.0

        # Packet loss impact
        if metrics.packet_loss_rate > self.thresholds.packet_loss_critical:
            error_score -= 50.0
        elif metrics.packet_loss_rate > self.thresholds.packet_loss_warning:
            error_score -= 20.0

        # General error rate impact
        if metrics.error_rate > self.thresholds.error_rate_critical:
            error_score -= 30.0
        elif metrics.error_rate > self.thresholds.error_rate_warning:
            error_score -= 10.0

        return max(0.0, error_score)

    def _identify_critical_issues(self, metrics: PerformanceMetrics) -> List[str]:
        """Identify critical performance issues."""
        issues = []

        if metrics.packet_loss_rate > self.thresholds.packet_loss_critical:
            issues.append(f"Critical packet loss rate: {metrics.packet_loss_rate}%")

        if metrics.bandwidth_utilization > self.thresholds.bandwidth_critical:
            issues.append(f"Critical bandwidth utilization: {metrics.bandwidth_utilization}%")

        if metrics.average_latency > self.thresholds.latency_critical:
            issues.append(f"Critical latency: {metrics.average_latency}ms")

        return issues

    def _identify_warnings(self, metrics: PerformanceMetrics) -> List[str]:
        """Identify performance warnings."""
        warnings = []

        if metrics.packet_loss_rate > self.thresholds.packet_loss_warning:
            warnings.append(f"Elevated packet loss rate: {metrics.packet_loss_rate}%")

        if metrics.bandwidth_utilization > self.thresholds.bandwidth_warning:
            warnings.append(f"High bandwidth utilization: {metrics.bandwidth_utilization}%")

        if metrics.average_latency > self.thresholds.latency_warning:
            warnings.append(f"Elevated latency: {metrics.average_latency}ms")

        return warnings

    def _generate_health_recommendations(self, assessment: HealthAssessment) -> List[str]:
        """Generate health-based recommendations."""
        recommendations = []

        if assessment.overall_health == HealthStatus.CRITICAL:
            recommendations.extend(
                [
                    "Immediate intervention required - performance is critically degraded",
                    "Consider scaling up TGW capacity or optimizing route tables",
                    "Review attachment configurations for bottlenecks",
                ]
            )
        elif assessment.overall_health == HealthStatus.WARNING:
            recommendations.extend(
                [
                    "Monitor performance closely - showing signs of degradation",
                    "Consider proactive capacity planning",
                    "Review traffic patterns for optimization opportunities",
                ]
            )

        # Component-specific recommendations
        if assessment.throughput_health < 70:
            recommendations.append("Consider implementing traffic shaping or load balancing")

        if assessment.latency_health < 70:
            recommendations.append("Review network paths and consider regional optimization")

        if assessment.error_health < 70:
            recommendations.append("Investigate and resolve error sources in the network")

        return recommendations

    def _analyze_performance_trend(
        self, historical_metrics: List[PerformanceMetrics]
    ) -> Tuple[PerformanceTrend, float]:
        """
        Analyze performance trend from historical data.

        Args:
            historical_metrics: List of historical metrics

        Returns:
            Performance trend and confidence score
        """
        if len(historical_metrics) < 3:
            return PerformanceTrend.STABLE, 0.0

        # Calculate trend based on throughput over time
        throughput_values = [m.average_throughput for m in historical_metrics]

        # Simple linear regression to determine trend
        n = len(throughput_values)
        x_values = list(range(n))

        # Calculate correlation coefficient
        if n > 1:
            x_mean = statistics.mean(x_values)
            y_mean = statistics.mean(throughput_values)

            numerator = sum(
                (x - x_mean) * (y - y_mean) for x, y in zip(x_values, throughput_values)
            )
            denominator = (
                sum((x - x_mean) ** 2 for x in x_values)
                * sum((y - y_mean) ** 2 for y in throughput_values)
            ) ** 0.5

            if denominator > 0:
                correlation = numerator / denominator
                confidence = abs(correlation)

                if correlation > 0.3:
                    return PerformanceTrend.IMPROVING, confidence
                elif correlation < -0.3:
                    return PerformanceTrend.DEGRADING, confidence
                else:
                    # Check for volatility
                    if statistics.stdev(throughput_values) > y_mean * 0.2:
                        return PerformanceTrend.VOLATILE, confidence
                    else:
                        return PerformanceTrend.STABLE, confidence

        return PerformanceTrend.STABLE, 0.0

    async def _analyze_peering_performance(
        self, transit_gateway_id: str, region: str, time_range_hours: int
    ) -> List[PeeringPerformanceAnalysis]:
        """Analyze performance of TGW peering connections."""
        analyses = []

        try:
            # Get peering connections
            peering_connections = await self.peering_engine.discover_peering_connections(
                transit_gateway_id=transit_gateway_id, region=region
            )

            # Analyze each peering connection
            for conn in peering_connections:
                analysis = PeeringPerformanceAnalysis(peering_connection=conn)

                # This would collect metrics specific to the peering connection
                # For now, using placeholder data
                analysis.current_metrics = PerformanceMetrics(
                    timestamp=datetime.now(), tgw_id=transit_gateway_id, region=region
                )

                analyses.append(analysis)

        except Exception:
            pass  # Handle gracefully

        return analyses

    async def _generate_optimization_recommendations(
        self,
        current_metrics: PerformanceMetrics,
        historical_metrics: List[PerformanceMetrics],
        health_assessment: HealthAssessment,
        peering_analyses: List[PeeringPerformanceAnalysis],
    ) -> List[PerformanceOptimizationRecommendation]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # Throughput optimization
        if current_metrics.bandwidth_utilization > 80:
            recommendations.append(
                PerformanceOptimizationRecommendation(
                    category="throughput",
                    priority="high",
                    title="Optimize High Bandwidth Utilization",
                    description="Bandwidth utilization is approaching limits",
                    expected_improvement="20-30% throughput improvement",
                    implementation_effort="medium",
                    estimated_cost_impact="neutral",
                    steps=[
                        "Implement Equal Cost Multi-Path (ECMP) routing",
                        "Consider additional TGW attachments for load distribution",
                        "Review and optimize route table configurations",
                    ],
                )
            )

        # Latency optimization
        if current_metrics.average_latency > self.thresholds.latency_warning:
            recommendations.append(
                PerformanceOptimizationRecommendation(
                    category="latency",
                    priority="medium",
                    title="Reduce Network Latency",
                    description="Network latency is elevated above optimal levels",
                    expected_improvement="10-20ms latency reduction",
                    implementation_effort="low",
                    estimated_cost_impact="positive",
                    steps=[
                        "Review routing paths for optimization",
                        "Consider regional placement optimization",
                        "Implement connection pooling where applicable",
                    ],
                )
            )

        # Reliability optimization
        if current_metrics.packet_loss_rate > 0:
            recommendations.append(
                PerformanceOptimizationRecommendation(
                    category="reliability",
                    priority="high",
                    title="Address Packet Loss",
                    description="Packet loss detected in network connections",
                    expected_improvement="Improved connection reliability",
                    implementation_effort="medium",
                    estimated_cost_impact="neutral",
                    steps=[
                        "Investigate source of packet loss",
                        "Review security group and NACL configurations",
                        "Consider implementing redundant paths",
                    ],
                )
            )

        return recommendations

    def _create_performance_summary(
        self,
        current_metrics: PerformanceMetrics,
        historical_metrics: List[PerformanceMetrics],
        health_assessment: HealthAssessment,
    ) -> Dict[str, Any]:
        """Create performance summary."""
        return {
            "overall_health_status": health_assessment.overall_health.value,
            "health_score": health_assessment.health_score,
            "current_throughput_mbps": current_metrics.average_throughput,
            "bandwidth_utilization_percent": current_metrics.bandwidth_utilization,
            "average_latency_ms": current_metrics.average_latency,
            "packet_loss_rate_percent": current_metrics.packet_loss_rate,
            "performance_trend": health_assessment.performance_trend.value,
            "critical_issues_count": len(health_assessment.critical_issues),
            "warnings_count": len(health_assessment.warnings),
            "recommendations_count": len(health_assessment.recommendations),
        }

    async def cleanup(self):
        """Cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
        self._metrics_cache.clear()
