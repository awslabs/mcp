# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
API for ECS security analysis.

This module provides comprehensive security analysis for ECS clusters,
including cluster security, IAM security, and logging security checks.
"""

import logging
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation

logger = logging.getLogger(__name__)


class DataAdapter:
    """Adapter that uses existing MCP tools to collect ECS data."""

    def __init__(self) -> None:
        """Initialize the DataAdapter."""
        self.logger = logger

    async def collect_cluster_data(
        self, cluster_name: str, region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Collect cluster data using existing ECS API operations.

        Args:
            cluster_name: Name of the ECS cluster
            region: AWS region (default: us-east-1)

        Returns:
            Dictionary containing cluster data or error information
        """
        try:
            self.logger.info(f"Collecting cluster data for {cluster_name} in {region}")

            # Use existing ecs_api_operation to describe cluster
            response = await ecs_api_operation(
                "DescribeClusters",
                {"clusters": [cluster_name], "include": ["SETTINGS", "CONFIGURATIONS", "TAGS"]},
            )

            if "error" in response:
                self.logger.error(f"Error collecting cluster data: {response['error']}")
                return {"error": response["error"], "cluster_name": cluster_name}

            if not response.get("clusters"):
                self.logger.warning(f"No cluster found with name: {cluster_name}")
                return {"error": "Cluster not found", "cluster_name": cluster_name}

            cluster_data = response["clusters"][0]
            self.logger.info(f"Successfully collected data for cluster: {cluster_name}")

            return {"status": "success", "cluster": cluster_data, "region": region}

        except Exception as e:
            self.logger.error(f"Unexpected error collecting cluster data: {e}")
            return {"error": str(e), "cluster_name": cluster_name}


class SecurityAnalyzer:
    """Security analysis engine for ECS resources."""

    def __init__(self) -> None:
        """Initialize the SecurityAnalyzer."""
        self.logger = logger
        self.recommendations: List[Dict[str, Any]] = []

    def analyze(self, ecs_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main analysis orchestrator.

        Args:
            ecs_data: Dictionary containing ECS cluster data

        Returns:
            Dictionary containing security recommendations and summary
        """
        self.recommendations = []

        if "error" in ecs_data:
            self.logger.error(f"Cannot analyze data with errors: {ecs_data['error']}")
            return {
                "status": "error",
                "error": ecs_data["error"],
                "recommendations": [],
                "summary": {"total_issues": 0},
            }

        cluster_data = ecs_data.get("cluster", {})

        # Run security checks
        self._analyze_cluster_security(cluster_data)
        self._analyze_cluster_iam_security(cluster_data)
        self._analyze_logging_security(cluster_data)

        # Generate summary
        summary = self._generate_summary()

        return {
            "status": "success",
            "recommendations": self.recommendations,
            "summary": summary,
            "cluster_name": cluster_data.get("clusterName", "unknown"),
        }

    def _analyze_cluster_security(self, cluster: Dict[str, Any]) -> None:
        """Analyze cluster-level security (Container Insights, execute command, status)."""
        cluster_name = cluster.get("clusterName", "unknown")

        # Check Container Insights
        settings = cluster.get("settings", [])
        container_insights_enabled = any(
            s.get("name") == "containerInsights" and s.get("value") == "enabled" for s in settings
        )

        if not container_insights_enabled:
            self.recommendations.append(
                {
                    "title": "Container Insights Disabled",
                    "severity": "Medium",
                    "category": "Monitoring",
                    "resource": cluster_name,
                    "issue": "Container Insights is not enabled for this cluster",
                    "recommendation": "Enable Container Insights to collect metrics and logs",
                    "remediation_steps": [
                        f"aws ecs update-cluster-settings --cluster {cluster_name} "
                        "--settings name=containerInsights,value=enabled"
                    ],
                }
            )

        # Check execute command configuration
        exec_cmd_config = cluster.get("configuration", {}).get("executeCommandConfiguration", {})
        if not exec_cmd_config.get("logging"):
            self.recommendations.append(
                {
                    "title": "Execute Command Logging Not Configured",
                    "severity": "Medium",
                    "category": "Logging",
                    "resource": cluster_name,
                    "issue": "Execute command logging is not configured",
                    "recommendation": "Configure logging for execute command sessions",
                    "remediation_steps": ["Configure CloudWatch Logs or S3 for audit trails"],
                }
            )

        # Check cluster status
        if cluster.get("status") != "ACTIVE":
            self.recommendations.append(
                {
                    "title": "Cluster Not Active",
                    "severity": "High",
                    "category": "Availability",
                    "resource": cluster_name,
                    "issue": f"Cluster status is {cluster.get('status')}, not ACTIVE",
                    "recommendation": "Investigate why cluster is not in ACTIVE state",
                    "remediation_steps": ["Check cluster events and IAM permissions"],
                }
            )

    def _analyze_cluster_iam_security(self, cluster: Dict[str, Any]) -> None:
        """Analyze cluster IAM security (service-linked roles)."""
        if not cluster.get("configuration"):
            self.recommendations.append(
                {
                    "title": "Missing Cluster Configuration",
                    "severity": "Medium",
                    "category": "IAM",
                    "resource": cluster.get("clusterName", "unknown"),
                    "issue": "Cluster configuration is not properly set up",
                    "recommendation": "Ensure cluster has proper IAM service-linked roles",
                    "remediation_steps": ["Verify AWSServiceRoleForECS exists"],
                }
            )

    def _analyze_logging_security(self, cluster: Dict[str, Any]) -> None:
        """Analyze logging security (CloudWatch logging)."""
        exec_cmd_config = cluster.get("configuration", {}).get("executeCommandConfiguration", {})
        logging_config = exec_cmd_config.get("logging")

        if not logging_config or logging_config == "NONE":
            self.recommendations.append(
                {
                    "title": "CloudWatch Logging Not Enabled",
                    "severity": "Medium",
                    "category": "Logging",
                    "resource": cluster.get("clusterName", "unknown"),
                    "issue": "CloudWatch logging is not enabled for execute command",
                    "recommendation": "Enable CloudWatch logging for audit and compliance",
                    "remediation_steps": ["Configure CloudWatch log group and retention policies"],
                }
            )

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics for security analysis."""
        summary = {
            "total_issues": len(self.recommendations),
            "by_severity": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
            "by_category": {},
        }
        for rec in self.recommendations:
            severity = rec.get("severity", "Low")
            category = rec.get("category", "Other")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
        return summary


async def analyze_ecs_security(
    cluster_names: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for ECS security analysis.

    Args:
        cluster_names: List of cluster names to analyze (optional)
        regions: List of AWS regions to analyze (optional, default: ["us-east-1"])

    Returns:
        Dictionary containing security analysis results
    """
    logger.info("Starting ECS security analysis")

    if regions is None:
        regions = ["us-east-1"]

    results = []
    adapter = DataAdapter()
    analyzer = SecurityAnalyzer()

    # If no cluster names provided, discover clusters
    if not cluster_names:
        logger.info("No cluster names provided, discovering clusters")
        try:
            response = await ecs_api_operation("ListClusters", {})
            if "error" in response:
                return {
                    "status": "error",
                    "error": f"Failed to list clusters: {response['error']}",
                    "results": [],
                }

            cluster_arns = response.get("clusterArns", [])
            if not cluster_arns:
                return {
                    "status": "success",
                    "message": "No clusters found",
                    "results": [],
                }

            # Extract cluster names from ARNs
            cluster_names = [arn.split("/")[-1] for arn in cluster_arns]
            logger.info(f"Discovered {len(cluster_names)} clusters")

        except Exception as e:
            logger.error(f"Error discovering clusters: {e}")
            return {"status": "error", "error": str(e), "results": []}

    # Analyze each cluster
    for cluster_name in cluster_names:
        for region in regions:
            logger.info(f"Analyzing cluster {cluster_name} in region {region}")

            # Collect data
            cluster_data = await adapter.collect_cluster_data(cluster_name, region)

            # Analyze data
            analysis_result = analyzer.analyze(cluster_data)
            results.append(analysis_result)

    # Aggregate results
    total_recommendations = sum(len(r.get("recommendations", [])) for r in results)

    return {
        "status": "success",
        "total_clusters_analyzed": len(results),
        "total_recommendations": total_recommendations,
        "results": results,
    }
