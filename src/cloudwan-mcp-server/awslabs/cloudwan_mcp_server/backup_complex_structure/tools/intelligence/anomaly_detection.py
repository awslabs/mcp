"""
CloudWAN AI/ML Anomaly Detection Tool.

This module provides machine learning-based anomaly detection for CloudWAN
network metrics, identifying unusual patterns and potential issues before
they impact production.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import pandas as pd
from dataclasses import dataclass
from enum import Enum

from mcp.types import TextContent
from ...aws.client_manager import AWSClientManager
from ...models.intelligence import AnomalyDetectionResponse, AnomalyEvent
from ..base import BaseMCPTool
from ...config import CloudWANConfig


logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Types of anomalies detected."""

    BANDWIDTH_SPIKE = "bandwidth_spike"
    LATENCY_INCREASE = "latency_increase"
    PACKET_LOSS = "packet_loss"
    ROUTE_FLAPPING = "route_flapping"
    CONNECTION_DROPS = "connection_drops"
    UNUSUAL_TRAFFIC_PATTERN = "unusual_traffic_pattern"
    BGP_INSTABILITY = "bgp_instability"
    ATTACHMENT_ISSUES = "attachment_issues"


@dataclass
class MetricPoint:
    """A single metric data point."""

    timestamp: datetime
    value: float
    metric_name: str
    resource_id: str
    region: str
    metadata: Dict[str, Any]


@dataclass
class AnomalyScore:
    """Anomaly detection score and details."""

    score: float
    severity: str  # low, medium, high, critical
    confidence: float
    contributing_factors: List[str]
    recommended_actions: List[str]


class CloudWANAnomalyDetector(BaseMCPTool):
    """
    AI/ML-powered anomaly detection for CloudWAN metrics.

    Uses Isolation Forest algorithm for unsupervised anomaly detection,
    combined with statistical analysis and pattern recognition.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig = None):
        super().__init__(aws_manager, config or CloudWANConfig())
        self._tool_name = "detect_cloudwan_anomalies"
        self._description = "AI/ML-based anomaly detection for CloudWAN metrics"

        # ML models
        self.isolation_forest = IsolationForest(
            contamination=0.1,  # Expected anomaly rate
            random_state=42,
            n_estimators=100,
        )
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=3)

        # Thresholds
        self.severity_thresholds = {
            "low": 0.3,
            "medium": 0.5,
            "high": 0.7,
            "critical": 0.9,
        }

    @property
    def tool_name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "description": "Time range for analysis (e.g., '1h', '24h', '7d')",
                    "default": "1h",
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific metrics to analyze",
                    "default": ["all"],
                },
                "resource_filter": {
                    "type": "object",
                    "description": "Filter by resource type or ID",
                    "properties": {
                        "core_network_id": {"type": "string"},
                        "attachment_id": {"type": "string"},
                        "segment_name": {"type": "string"},
                    },
                },
                "sensitivity": {
                    "type": "number",
                    "description": "Detection sensitivity (0.01-0.3)",
                    "default": 0.1,
                },
                "include_predictions": {
                    "type": "boolean",
                    "description": "Include future anomaly predictions",
                    "default": True,
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs) -> List[TextContent]:
        """Execute anomaly detection analysis."""
        try:
            time_range = kwargs.get("time_range", "1h")
            metrics = kwargs.get("metrics", ["all"])
            resource_filter = kwargs.get("resource_filter", {})
            sensitivity = kwargs.get("sensitivity", 0.1)
            include_predictions = kwargs.get("include_predictions", True)

            logger.info(f"Starting AI/ML anomaly detection for {time_range}")

            # Step 1: Collect metrics
            metrics_data = await self._collect_cloudwan_metrics(
                time_range, metrics, resource_filter
            )

            if not metrics_data:
                return [
                    TextContent(
                        type="text",
                        text="No metrics data available for the specified time range",
                    )
                ]

            # Step 2: Preprocess data
            feature_matrix, labels = self._preprocess_metrics(metrics_data)

            # Step 3: Train/update model
            if feature_matrix.shape[0] > 10:  # Minimum samples needed
                self._train_anomaly_model(feature_matrix, sensitivity)

            # Step 4: Detect anomalies
            anomalies = self._detect_anomalies(feature_matrix, metrics_data, labels)

            # Step 5: Analyze patterns
            patterns = self._analyze_anomaly_patterns(anomalies)

            # Step 6: Generate predictions (if requested)
            predictions = []
            if include_predictions:
                predictions = await self._predict_future_anomalies(metrics_data, patterns)

            # Step 7: Build response
            response = self._build_anomaly_response(anomalies, patterns, predictions, metrics_data)

            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error during anomaly detection: {str(e)}")]

    async def _collect_cloudwan_metrics(
        self, time_range: str, metrics: List[str], resource_filter: Dict[str, Any]
    ) -> List[MetricPoint]:
        """Collect CloudWatch metrics for CloudWAN resources."""
        # Parse time range
        end_time = datetime.utcnow()
        start_time = self._parse_time_range(time_range, end_time)

        metric_points = []

        # Define metric queries
        metric_definitions = self._get_metric_definitions(metrics)

        # Collect metrics from CloudWatch
        async with self.aws_manager.client_context("cloudwatch", "us-east-1") as cw:
            for metric_def in metric_definitions:
                try:
                    response = await cw.get_metric_statistics(
                        Namespace=metric_def["namespace"],
                        MetricName=metric_def["name"],
                        Dimensions=self._build_dimensions(metric_def, resource_filter),
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=300,  # 5-minute intervals
                        Statistics=["Average", "Maximum", "Minimum"],
                    )

                    # Convert to MetricPoint objects
                    for datapoint in response.get("Datapoints", []):
                        metric_points.append(
                            MetricPoint(
                                timestamp=datapoint["Timestamp"],
                                value=datapoint["Average"],
                                metric_name=metric_def["name"],
                                resource_id=resource_filter.get("core_network_id", "unknown"),
                                region="global",
                                metadata={
                                    "max": datapoint.get("Maximum"),
                                    "min": datapoint.get("Minimum"),
                                    "unit": datapoint.get("Unit", "None"),
                                },
                            )
                        )

                except Exception as e:
                    logger.warning(f"Failed to collect metric {metric_def['name']}: {e}")

        # Sort by timestamp
        metric_points.sort(key=lambda x: x.timestamp)

        return metric_points

    def _preprocess_metrics(self, metrics_data: List[MetricPoint]) -> Tuple[np.ndarray, List[str]]:
        """Preprocess metrics into feature matrix for ML model."""
        # Group by timestamp
        df = pd.DataFrame(
            [
                {
                    "timestamp": m.timestamp,
                    "metric": m.metric_name,
                    "value": m.value,
                    "resource": m.resource_id,
                }
                for m in metrics_data
            ]
        )

        # Pivot to create feature matrix
        feature_df = df.pivot_table(
            index="timestamp", columns="metric", values="value", aggfunc="mean"
        )

        # Fill missing values
        feature_df = feature_df.fillna(method="ffill").fillna(0)

        # Add derived features
        self._add_derived_features(feature_df)

        # Convert to numpy array
        feature_matrix = feature_df.values
        labels = feature_df.columns.tolist()

        return feature_matrix, labels

    def _add_derived_features(self, df: pd.DataFrame) -> None:
        """Add derived features for better anomaly detection."""
        # Rolling statistics
        for col in df.columns:
            if col in df:
                df[f"{col}_rolling_mean"] = df[col].rolling(window=6).mean()
                df[f"{col}_rolling_std"] = df[col].rolling(window=6).std()
                df[f"{col}_rate_change"] = df[col].pct_change()

        # Fill any NaN values created by rolling operations
        df.fillna(0, inplace=True)

    def _train_anomaly_model(self, feature_matrix: np.ndarray, sensitivity: float) -> None:
        """Train or update the anomaly detection model."""
        # Update contamination parameter based on sensitivity
        self.isolation_forest.contamination = sensitivity

        # Scale features
        scaled_features = self.scaler.fit_transform(feature_matrix)

        # Apply PCA for dimensionality reduction
        if feature_matrix.shape[1] > 3:
            reduced_features = self.pca.fit_transform(scaled_features)
        else:
            reduced_features = scaled_features

        # Train Isolation Forest
        self.isolation_forest.fit(reduced_features)

    def _detect_anomalies(
        self,
        feature_matrix: np.ndarray,
        metrics_data: List[MetricPoint],
        labels: List[str],
    ) -> List[AnomalyEvent]:
        """Detect anomalies in the metric data."""
        anomalies = []

        # Scale and reduce features
        scaled_features = self.scaler.transform(feature_matrix)
        if feature_matrix.shape[1] > 3:
            reduced_features = self.pca.transform(scaled_features)
        else:
            reduced_features = scaled_features

        # Predict anomalies
        anomaly_labels = self.isolation_forest.predict(reduced_features)
        anomaly_scores = self.isolation_forest.score_samples(reduced_features)

        # Process detected anomalies
        for i, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
            if label == -1:  # Anomaly detected
                # Find corresponding metrics
                timestamp_idx = i % len(metrics_data)
                if timestamp_idx < len(metrics_data):
                    metric_point = metrics_data[timestamp_idx]

                    # Calculate severity
                    severity = self._calculate_severity(abs(score))

                    # Identify contributing factors
                    factors = self._identify_contributing_factors(
                        feature_matrix[i], labels, scaled_features[i]
                    )

                    # Generate recommendations
                    recommendations = self._generate_recommendations(
                        metric_point, factors, severity
                    )

                    anomalies.append(
                        AnomalyEvent(
                            timestamp=metric_point.timestamp.isoformat(),
                            anomaly_type=self._classify_anomaly_type(factors),
                            severity=severity,
                            confidence=min(abs(score), 1.0),
                            affected_resources=[metric_point.resource_id],
                            description=self._generate_anomaly_description(metric_point, factors),
                            metrics={metric_point.metric_name: metric_point.value},
                            recommended_actions=recommendations,
                            root_cause_analysis=factors,
                        )
                    )

        return anomalies

    def _calculate_severity(self, anomaly_score: float) -> str:
        """Calculate anomaly severity based on score."""
        for severity, threshold in sorted(
            self.severity_thresholds.items(), key=lambda x: x[1], reverse=True
        ):
            if anomaly_score >= threshold:
                return severity
        return "low"

    def _identify_contributing_factors(
        self, feature_vector: np.ndarray, labels: List[str], scaled_vector: np.ndarray
    ) -> List[str]:
        """Identify which metrics contributed most to the anomaly."""
        factors = []

        # Find features with highest deviation
        mean_values = np.mean(self.scaler.transform(feature_vector.reshape(1, -1)), axis=0)
        deviations = np.abs(scaled_vector - mean_values)

        # Get top contributing features
        top_indices = np.argsort(deviations)[-3:][::-1]

        for idx in top_indices:
            if idx < len(labels):
                factor = f"{labels[idx]}: {deviations[idx]:.2f} std deviations"
                factors.append(factor)

        return factors

    def _classify_anomaly_type(self, factors: List[str]) -> str:
        """Classify the type of anomaly based on contributing factors."""
        factor_text = " ".join(factors).lower()

        if "bandwidth" in factor_text or "bytes" in factor_text:
            return AnomalyType.BANDWIDTH_SPIKE.value
        elif "latency" in factor_text or "delay" in factor_text:
            return AnomalyType.LATENCY_INCREASE.value
        elif "packet" in factor_text and "loss" in factor_text:
            return AnomalyType.PACKET_LOSS.value
        elif "route" in factor_text:
            return AnomalyType.ROUTE_FLAPPING.value
        elif "connection" in factor_text:
            return AnomalyType.CONNECTION_DROPS.value
        elif "bgp" in factor_text:
            return AnomalyType.BGP_INSTABILITY.value
        else:
            return AnomalyType.UNUSUAL_TRAFFIC_PATTERN.value

    def _generate_anomaly_description(self, metric_point: MetricPoint, factors: List[str]) -> str:
        """Generate human-readable description of the anomaly."""
        return (
            f"Anomaly detected in {metric_point.metric_name} for "
            f"{metric_point.resource_id} at {metric_point.timestamp}. "
            f"Value: {metric_point.value}. Contributing factors: {', '.join(factors)}"
        )

    def _generate_recommendations(
        self, metric_point: MetricPoint, factors: List[str], severity: str
    ) -> List[str]:
        """Generate actionable recommendations based on anomaly type."""
        recommendations = []

        # Generic recommendations
        recommendations.append(f"Investigate {metric_point.resource_id} for issues")

        # Specific recommendations based on metric type
        if "bandwidth" in metric_point.metric_name.lower():
            recommendations.extend(
                [
                    "Check for DDoS attacks or traffic spikes",
                    "Review bandwidth limits and scaling policies",
                    "Analyze traffic patterns for unusual sources",
                ]
            )
        elif "latency" in metric_point.metric_name.lower():
            recommendations.extend(
                [
                    "Check network path and routing",
                    "Verify inspection VPC performance",
                    "Review NFG configurations for suboptimal routing",
                ]
            )
        elif "packet_loss" in metric_point.metric_name.lower():
            recommendations.extend(
                [
                    "Check physical connectivity and link health",
                    "Review security group rules for drops",
                    "Verify MTU settings across the path",
                ]
            )

        # Severity-based recommendations
        if severity in ["high", "critical"]:
            recommendations.insert(0, "IMMEDIATE ACTION REQUIRED")
            recommendations.append("Consider opening a support case with AWS")

        return recommendations

    def _analyze_anomaly_patterns(self, anomalies: List[AnomalyEvent]) -> Dict[str, Any]:
        """Analyze patterns in detected anomalies."""
        if not anomalies:
            return {}

        patterns = {
            "temporal_patterns": self._find_temporal_patterns(anomalies),
            "resource_patterns": self._find_resource_patterns(anomalies),
            "severity_distribution": self._calculate_severity_distribution(anomalies),
            "anomaly_types": self._categorize_anomaly_types(anomalies),
            "correlation_analysis": self._analyze_correlations(anomalies),
        }

        return patterns

    def _find_temporal_patterns(self, anomalies: List[AnomalyEvent]) -> Dict[str, Any]:
        """Find temporal patterns in anomalies."""
        timestamps = [datetime.fromisoformat(a.timestamp) for a in anomalies]

        # Hour of day analysis
        hour_distribution = {}
        for ts in timestamps:
            hour = ts.hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1

        # Day of week analysis
        day_distribution = {}
        for ts in timestamps:
            day = ts.strftime("%A")
            day_distribution[day] = day_distribution.get(day, 0) + 1

        return {
            "hour_distribution": hour_distribution,
            "day_distribution": day_distribution,
            "peak_hours": sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
        }

    def _find_resource_patterns(self, anomalies: List[AnomalyEvent]) -> Dict[str, Any]:
        """Find resource-based patterns in anomalies."""
        resource_counts = {}
        for anomaly in anomalies:
            for resource in anomaly.affected_resources:
                resource_counts[resource] = resource_counts.get(resource, 0) + 1

        return {
            "affected_resources": resource_counts,
            "most_affected": sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        }

    def _calculate_severity_distribution(self, anomalies: List[AnomalyEvent]) -> Dict[str, int]:
        """Calculate distribution of anomaly severities."""
        distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for anomaly in anomalies:
            distribution[anomaly.severity] += 1
        return distribution

    def _categorize_anomaly_types(self, anomalies: List[AnomalyEvent]) -> Dict[str, int]:
        """Categorize anomalies by type."""
        type_counts = {}
        for anomaly in anomalies:
            type_counts[anomaly.anomaly_type] = type_counts.get(anomaly.anomaly_type, 0) + 1
        return type_counts

    def _analyze_correlations(self, anomalies: List[AnomalyEvent]) -> Dict[str, Any]:
        """Analyze correlations between anomalies."""
        # Simple correlation: anomalies occurring within 5 minutes of each other
        correlated_groups = []
        used_indices = set()

        for i, anomaly1 in enumerate(anomalies):
            if i in used_indices:
                continue

            group = [anomaly1]
            used_indices.add(i)

            for j, anomaly2 in enumerate(anomalies[i + 1 :], start=i + 1):
                if j in used_indices:
                    continue

                time_diff = abs(
                    datetime.fromisoformat(anomaly1.timestamp)
                    - datetime.fromisoformat(anomaly2.timestamp)
                )

                if time_diff <= timedelta(minutes=5):
                    group.append(anomaly2)
                    used_indices.add(j)

            if len(group) > 1:
                correlated_groups.append(group)

        return {
            "correlated_anomaly_groups": len(correlated_groups),
            "correlation_details": [
                {
                    "size": len(group),
                    "types": list(set(a.anomaly_type for a in group)),
                    "resources": list(set(r for a in group for r in a.affected_resources)),
                }
                for group in correlated_groups
            ],
        }

    async def _predict_future_anomalies(
        self, historical_data: List[MetricPoint], patterns: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Predict potential future anomalies based on patterns."""
        predictions = []

        # Simple prediction based on temporal patterns
        if patterns.get("temporal_patterns", {}).get("peak_hours"):
            peak_hours = patterns["temporal_patterns"]["peak_hours"]

            for hour, count in peak_hours[:3]:
                predictions.append(
                    {
                        "prediction_type": "temporal",
                        "time_window": f"Next occurrence at {hour:02d}:00",
                        "probability": min(count / len(historical_data), 0.8),
                        "expected_severity": "medium",
                        "recommended_preemptive_actions": [
                            f"Monitor resources closely around {hour:02d}:00",
                            "Consider scaling resources before peak time",
                            "Review recent changes that might impact this time window",
                        ],
                    }
                )

        # Resource-based predictions
        if patterns.get("resource_patterns", {}).get("most_affected"):
            for resource, count in patterns["resource_patterns"]["most_affected"][:2]:
                if count > 3:  # Repeated anomalies
                    predictions.append(
                        {
                            "prediction_type": "resource",
                            "resource_id": resource,
                            "probability": min(count / 10, 0.9),
                            "expected_severity": "high" if count > 5 else "medium",
                            "recommended_preemptive_actions": [
                                f"Perform health check on {resource}",
                                "Review recent configuration changes",
                                "Consider redundancy options",
                            ],
                        }
                    )

        return predictions

    def _build_anomaly_response(
        self,
        anomalies: List[AnomalyEvent],
        patterns: Dict[str, Any],
        predictions: List[Dict[str, Any]],
        metrics_data: List[MetricPoint],
    ) -> AnomalyDetectionResponse:
        """Build the final anomaly detection response."""
        return AnomalyDetectionResponse(
            detection_timestamp=datetime.utcnow().isoformat(),
            time_range_analyzed=(
                f"{metrics_data[0].timestamp} to {metrics_data[-1].timestamp}"
                if metrics_data
                else "N/A"
            ),
            total_metrics_analyzed=len(metrics_data),
            anomalies_detected=len(anomalies),
            anomaly_events=anomalies,
            pattern_analysis=patterns,
            predictions=predictions,
            summary={
                "critical_anomalies": sum(1 for a in anomalies if a.severity == "critical"),
                "high_severity_anomalies": sum(1 for a in anomalies if a.severity == "high"),
                "most_affected_resources": patterns.get("resource_patterns", {}).get(
                    "most_affected", []
                ),
                "predominant_anomaly_types": sorted(
                    patterns.get("anomaly_types", {}).items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:3],
            },
            health_score=self._calculate_health_score(anomalies, len(metrics_data)),
            recommendations=self._generate_overall_recommendations(anomalies, patterns),
        )

    def _calculate_health_score(self, anomalies: List[AnomalyEvent], total_metrics: int) -> float:
        """Calculate overall health score (0-100)."""
        if total_metrics == 0:
            return 100.0

        # Weight anomalies by severity
        severity_weights = {"low": 0.1, "medium": 0.3, "high": 0.6, "critical": 1.0}

        weighted_anomalies = sum(severity_weights.get(a.severity, 0.1) for a in anomalies)

        # Calculate score
        anomaly_ratio = weighted_anomalies / total_metrics
        health_score = max(0, 100 * (1 - anomaly_ratio))

        return round(health_score, 2)

    def _generate_overall_recommendations(
        self, anomalies: List[AnomalyEvent], patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate overall recommendations based on all findings."""
        recommendations = []

        # Critical anomalies
        critical_count = sum(1 for a in anomalies if a.severity == "critical")
        if critical_count > 0:
            recommendations.append(
                f"URGENT: {critical_count} critical anomalies detected. Immediate investigation required."
            )

        # Pattern-based recommendations
        if patterns.get("temporal_patterns", {}).get("peak_hours"):
            recommendations.append(
                "Anomalies show temporal patterns. Consider scheduling maintenance outside peak hours."
            )

        if patterns.get("correlation_analysis", {}).get("correlated_anomaly_groups"):
            recommendations.append(
                "Multiple correlated anomalies detected. This may indicate systemic issues."
            )

        # Resource-specific recommendations
        most_affected = patterns.get("resource_patterns", {}).get("most_affected", [])
        if most_affected:
            top_resource = most_affected[0][0]
            recommendations.append(
                f"Resource {top_resource} is experiencing repeated anomalies. Consider dedicated monitoring."
            )

        # General recommendations
        if not anomalies:
            recommendations.append("No anomalies detected. Network is operating normally.")
        else:
            recommendations.append("Enable CloudWatch alarms for detected anomaly patterns.")
            recommendations.append("Review AWS CloudWAN best practices for optimization.")

        return recommendations

    def _parse_time_range(self, time_range: str, end_time: datetime) -> datetime:
        """Parse time range string to datetime."""
        # Simple parser for time ranges like "1h", "24h", "7d"
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            return end_time - timedelta(hours=hours)
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            return end_time - timedelta(days=days)
        elif time_range.endswith("m"):
            minutes = int(time_range[:-1])
            return end_time - timedelta(minutes=minutes)
        else:
            # Default to 1 hour
            return end_time - timedelta(hours=1)

    def _get_metric_definitions(self, metrics: List[str]) -> List[Dict[str, Any]]:
        """Get CloudWatch metric definitions for CloudWAN."""
        if "all" in metrics:
            return [
                {
                    "namespace": "AWS/CloudWAN",
                    "name": "BytesIn",
                    "dimensions": ["CoreNetworkId", "AttachmentId"],
                },
                {
                    "namespace": "AWS/CloudWAN",
                    "name": "BytesOut",
                    "dimensions": ["CoreNetworkId", "AttachmentId"],
                },
                {
                    "namespace": "AWS/CloudWAN",
                    "name": "PacketsIn",
                    "dimensions": ["CoreNetworkId", "AttachmentId"],
                },
                {
                    "namespace": "AWS/CloudWAN",
                    "name": "PacketsOut",
                    "dimensions": ["CoreNetworkId", "AttachmentId"],
                },
                {
                    "namespace": "AWS/CloudWAN",
                    "name": "PacketDropCount",
                    "dimensions": ["CoreNetworkId", "AttachmentId"],
                },
                {
                    "namespace": "AWS/NetworkManager",
                    "name": "ConnectionsUp",
                    "dimensions": ["GlobalNetworkId"],
                },
                {
                    "namespace": "AWS/NetworkManager",
                    "name": "ConnectionsDown",
                    "dimensions": ["GlobalNetworkId"],
                },
            ]

        # Filter specific metrics
        metric_map = {
            "bandwidth": ["BytesIn", "BytesOut"],
            "packets": ["PacketsIn", "PacketsOut", "PacketDropCount"],
            "connections": ["ConnectionsUp", "ConnectionsDown"],
            "latency": ["Latency", "Jitter"],
        }

        definitions = []
        for metric in metrics:
            if metric in metric_map:
                for metric_name in metric_map[metric]:
                    definitions.append(
                        {
                            "namespace": "AWS/CloudWAN",
                            "name": metric_name,
                            "dimensions": ["CoreNetworkId", "AttachmentId"],
                        }
                    )

        return definitions

    def _build_dimensions(
        self, metric_def: Dict[str, Any], resource_filter: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Build CloudWatch dimensions for metric query."""
        dimensions = []

        if resource_filter.get("core_network_id"):
            dimensions.append(
                {"Name": "CoreNetworkId", "Value": resource_filter["core_network_id"]}
            )

        if resource_filter.get("attachment_id"):
            dimensions.append({"Name": "AttachmentId", "Value": resource_filter["attachment_id"]})

        if resource_filter.get("global_network_id"):
            dimensions.append(
                {
                    "Name": "GlobalNetworkId",
                    "Value": resource_filter["global_network_id"],
                }
            )

        return dimensions


# Integration with MCP tools registry
def register_anomaly_detection_tool(server, aws_manager, config):
    """Register the anomaly detection tool with the MCP server."""
    tool = CloudWANAnomalyDetector(aws_manager, config)
    server.add_tool(tool)
    logger.info("Registered CloudWAN AI/ML Anomaly Detection tool")
