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
leveraging existing MCP tools for data collection.
"""

import logging
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation
from awslabs.ecs_mcp_server.api.troubleshooting_tools.utils import find_clusters

logger = logging.getLogger(__name__)


class DataAdapter:
    """Adapter that uses existing MCP tools to collect data for security analysis."""

    def __init__(self) -> None:
        """Initialize the DataAdapter."""
        self.logger = logger

    async def collect_cluster_data(
        self, cluster_name: str, region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Collect cluster data using existing resource management API.

        Args:
            cluster_name: Name of the ECS cluster
            region: AWS region (default: us-east-1)

        Returns:
            Dict containing cluster data or error information
        """
        try:
            self.logger.info(f"Collecting cluster data for {cluster_name}")

            # Use existing ecs_api_operation for ECS API calls
            cluster_response = await ecs_api_operation(
                "DescribeClusters", {"clusters": [cluster_name]}
            )

            if "error" in cluster_response:
                self.logger.error(f"Error collecting cluster data: {cluster_response['error']}")
                return {
                    "status": "error",
                    "error": cluster_response["error"],
                    "cluster_name": cluster_name,
                    "region": region,
                }

            clusters = cluster_response.get("clusters", [])
            if not clusters:
                self.logger.warning(f"No cluster found with name: {cluster_name}")
                return {
                    "status": "error",
                    "error": f"Cluster '{cluster_name}' not found",
                    "cluster_name": cluster_name,
                    "region": region,
                }

            cluster_data = clusters[0]

            return {
                "status": "success",
                "cluster": cluster_data,
                "cluster_name": cluster_name,
                "region": region,
            }

        except Exception as e:
            self.logger.error(f"Unexpected error collecting cluster data for {cluster_name}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "cluster_name": cluster_name,
                "region": region,
            }


class SecurityAnalyzer:
    """Security analysis engine for ECS resources."""

    def __init__(self) -> None:
        """Initialize the SecurityAnalyzer."""
        self.logger = logger

    def analyze(self, ecs_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze ECS data for security issues.

        Args:
            ecs_data: Dictionary containing ECS cluster data

        Returns:
            Dict containing security recommendations and summary
        """
        recommendations = []

        # Extract cluster data
        cluster_name = ecs_data.get("cluster_name", "Unknown")
        region = ecs_data.get("region", "us-east-1")
        cluster_info = ecs_data.get("cluster", {})

        # Analyze cluster security
        cluster_recommendations = self._analyze_cluster_security(cluster_name, cluster_info, region)
        recommendations.extend(cluster_recommendations)

        # Generate summary
        summary = {
            "total_findings": len(recommendations),
            "by_severity": _count_by_severity(recommendations),
            "by_category": _count_by_category(recommendations),
        }

        return {
            "status": "success",
            "recommendations": recommendations,
            "summary": summary,
            "cluster_name": cluster_name,
            "region": region,
        }

    def _analyze_cluster_security(
        self, cluster_name: str, cluster_info: Dict[str, Any], region: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze cluster-level security configurations.

        Args:
            cluster_name: Name of the cluster
            cluster_info: Cluster information from AWS API
            region: AWS region

        Returns:
            List of security recommendations
        """
        recommendations = []

        cluster_settings = cluster_info.get("settings", [])

        # Check Container Insights
        container_insights_enabled = any(
            setting.get("name") == "containerInsights" and setting.get("value") == "enabled"
            for setting in cluster_settings
        )

        if container_insights_enabled:
            self.logger.info(f"Container Insights enabled for {cluster_name}")
        else:
            self.logger.warning(
                f"Container Insights disabled for {cluster_name} - reduced security visibility"
            )
            recommendations.append(
                {
                    "title": "Enable Container Insights for Security Monitoring",
                    "severity": "Medium",
                    "category": "monitoring",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": (
                        "Container Insights monitoring is disabled, reducing visibility "
                        "into container performance and security"
                    ),
                    "recommendation": (
                        "Enable Container Insights for comprehensive monitoring "
                        "and security observability"
                    ),
                }
            )

        # Check cluster status
        status = cluster_info.get("status", "")
        if status != "ACTIVE":
            self.logger.warning(
                f"Cluster {cluster_name} status is {status}, not ACTIVE - "
                "potential availability issue"
            )
            recommendations.append(
                {
                    "title": "Review Cluster Status",
                    "severity": "High",
                    "category": "availability",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": f"Cluster status is {status}, not ACTIVE",
                    "recommendation": (
                        "Investigate and resolve cluster status issues to ensure proper operation"
                    ),
                }
            )

        return recommendations


async def analyze_ecs_security(
    cluster_names: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for ECS security analysis.

    Args:
        cluster_names: Optional list of cluster names to analyze
        regions: Optional list of regions to analyze

    Returns:
        Dict containing security analysis results
    """
    logger.info("Starting ECS security analysis")

    try:
        # Initialize adapter and analyzer
        adapter = DataAdapter()
        analyzer = SecurityAnalyzer()

        # Determine which clusters to analyze
        if not cluster_names:
            logger.info("No cluster names provided, discovering all clusters")
            cluster_names = await find_clusters()

            if not cluster_names:
                logger.warning("No clusters found")
                return {
                    "status": "success",
                    "message": "No ECS clusters found to analyze",
                    "recommendations": [],
                    "summary": {"total_findings": 0},
                }

        # Use default region if not specified
        if not regions:
            regions = ["us-east-1"]

        all_recommendations = []
        analyzed_clusters = []
        errors = []

        # Analyze each cluster
        for cluster_name in cluster_names:
            for region in regions:
                try:
                    logger.info(f"Analyzing cluster {cluster_name} in region {region}")
                    # Collect cluster data
                    cluster_data = await adapter.collect_cluster_data(cluster_name, region)

                    if cluster_data.get("status") == "error":
                        error_msg = cluster_data.get("error", "Unknown error")
                        logger.warning(
                            f"Failed to collect data for cluster {cluster_name} in "
                            f"{region}: {error_msg}"
                        )
                        errors.append(
                            {
                                "cluster": cluster_name,
                                "region": region,
                                "error": error_msg,
                            }
                        )
                        continue

                    # Analyze security
                    analysis_result = analyzer.analyze(cluster_data)
                    findings_count = len(analysis_result["recommendations"])
                    logger.info(
                        f"Completed analysis for {cluster_name} in {region}: "
                        f"{findings_count} findings"
                    )
                    all_recommendations.extend(analysis_result["recommendations"])
                    analyzed_clusters.append(cluster_name)

                except Exception as e:
                    logger.error(f"Error analyzing cluster {cluster_name}: {e}")
                    errors.append({"cluster": cluster_name, "region": region, "error": str(e)})

        # Generate overall summary
        summary = {
            "total_findings": len(all_recommendations),
            "clusters_analyzed": len(set(analyzed_clusters)),
            "by_severity": _count_by_severity(all_recommendations),
            "by_category": _count_by_category(all_recommendations),
        }

        logger.info(f"Security analysis completed. Found {len(all_recommendations)} findings")

        result = {
            "status": "success",
            "recommendations": all_recommendations,
            "summary": summary,
            "analyzed_clusters": list(set(analyzed_clusters)),
        }

        if errors:
            result["errors"] = errors

        return result

    except Exception as e:
        logger.error(f"Unexpected error in security analysis: {e}")
        return {"status": "error", "error": str(e)}


def _count_by_severity(recommendations: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Helper function to count recommendations by severity.

    Args:
        recommendations: List of security recommendations

    Returns:
        Dictionary with counts for each severity level (Critical, High, Medium, Low)
    """
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for rec in recommendations:
        severity = rec.get("severity", "Low")
        if severity in counts:
            counts[severity] += 1
    return counts


def _count_by_category(recommendations: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Helper function to count recommendations by category.

    Args:
        recommendations: List of security recommendations

    Returns:
        Dictionary with counts for each category
    """
    counts: Dict[str, int] = {}
    for rec in recommendations:
        category = rec.get("category", "other")
        counts[category] = counts.get(category, 0) + 1
    return counts
