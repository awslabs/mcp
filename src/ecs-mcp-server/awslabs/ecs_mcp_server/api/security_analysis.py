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

"""Security Analysis API for ECS MCP Server.

This module provides security analysis for ECS clusters.
Minimal implementation for PR #2 - basic Container Insights check only.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation

logger = logging.getLogger(__name__)


class DataAdapter:
    """
    Minimal adapter for collecting ECS cluster data for security analysis.
    """

    def __init__(self) -> None:
        """Initialize the DataAdapter."""
        self.logger = logger

    async def collect_cluster_data(self, cluster_name: str) -> Dict[str, Any]:
        """
        Collect basic cluster data for security analysis.

        Args:
            cluster_name: Name of the ECS cluster

        Returns:
            Dictionary containing cluster data
        """
        try:
            self.logger.info(f"Collecting cluster data for {cluster_name}")

            cluster_response = await ecs_api_operation(
                "DescribeClusters", {"clusters": [cluster_name]}
            )

            if "error" in cluster_response:
                return self._create_error_response(cluster_response["error"], cluster_name)

            clusters = cluster_response.get("clusters", [])
            if not clusters:
                return self._create_error_response(
                    f"Cluster '{cluster_name}' not found", cluster_name
                )

            return {
                "cluster": clusters[0],
                "cluster_name": cluster_name,
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error collecting cluster data for {cluster_name}: {e}")
            return self._create_error_response(str(e), cluster_name)

    def _create_error_response(self, error: str, cluster_name: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "error": error,
            "cluster_name": cluster_name,
            "status": "failed",
        }


class SecurityAnalyzer:
    """
    Minimal ECS security analyzer focusing only on Container Insights.
    """

    def __init__(self) -> None:
        """Initialize the SecurityAnalyzer."""
        self.logger = logger

    def analyze(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform minimal security analysis focusing on Container Insights.

        Args:
            cluster_data: Dictionary containing cluster information

        Returns:
            Dictionary containing security analysis results
        """
        try:
            recommendations = self._check_container_insights(cluster_data)

            return {
                "recommendations": recommendations,
                "total_issues": len(recommendations),
                "analysis_summary": self._generate_summary(recommendations),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
            }

        except Exception as e:
            self.logger.error(f"Error in security analysis: {e}")
            return {
                "error": str(e),
                "recommendations": [],
                "total_issues": 0,
                "analysis_summary": {},
                "status": "failed",
            }

    def _check_container_insights(self, cluster_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if Container Insights is enabled."""
        cluster_info = cluster_data.get("cluster", {})
        cluster_name = cluster_data.get("cluster_name", "unknown")

        cluster_settings = cluster_info.get("settings", [])
        container_insights_enabled = any(
            setting.get("name") == "containerInsights" and setting.get("value") == "enabled"
            for setting in cluster_settings
        )

        if not container_insights_enabled:
            return [
                {
                    "title": "Enable Container Insights for Security Monitoring",
                    "severity": "Medium",
                    "category": "monitoring",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "Container Insights monitoring is disabled",
                    "recommendation": "Enable Container Insights for security observability",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ]

        return []

    def _generate_summary(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate basic analysis summary."""
        severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        category_counts = {}

        for rec in recommendations:
            severity = rec.get("severity", "Unknown")
            category = rec.get("category", "unknown")

            if severity in severity_counts:
                severity_counts[severity] += 1

            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "total_recommendations": len(recommendations),
        }


async def analyze_ecs_security(
    cluster_names: Optional[List[str]] = None,
    regions: Optional[List[str]] = None,
    analysis_scope: Optional[str] = "basic",
) -> Dict[str, Any]:
    """
    Perform minimal security analysis of ECS clusters.
    Focuses only on Container Insights monitoring check.

    Args:
        cluster_names: List of cluster names to analyze
        regions: Optional list of regions (not used in minimal implementation)
        analysis_scope: Scope of analysis (not used in minimal implementation)

    Returns:
        Dictionary containing security analysis results
    """
    try:
        logger.info("Starting minimal ECS security analysis")

        if not cluster_names:
            return {
                "error": "cluster_names parameter is required",
                "recommendations": [],
                "total_issues": 0,
                "analysis_summary": {},
                "status": "failed",
            }

        data_adapter = DataAdapter()
        security_analyzer = SecurityAnalyzer()
        all_recommendations = []

        for cluster_name in cluster_names:
            try:
                cluster_data = await data_adapter.collect_cluster_data(cluster_name)

                if cluster_data.get("status") == "failed":
                    logger.warning(f"Skipping cluster {cluster_name}: {cluster_data.get('error')}")
                    continue

                analysis_result = security_analyzer.analyze(cluster_data)

                if analysis_result.get("status") == "success":
                    all_recommendations.extend(analysis_result.get("recommendations", []))

            except Exception as e:
                logger.error(f"Error analyzing cluster {cluster_name}: {e}")

        return {
            "recommendations": all_recommendations,
            "total_issues": len(all_recommendations),
            "analysis_summary": security_analyzer._generate_summary(all_recommendations),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error in analyze_ecs_security: {e}")
        return {
            "error": str(e),
            "recommendations": [],
            "total_issues": 0,
            "analysis_summary": {},
            "status": "failed",
        }


def register_module(mcp) -> None:
    """
    Register the security analysis module with MCP.

    Args:
        mcp: The MCP server instance
    """

    @mcp.tool(name="analyze_ecs_security")
    async def analyze_ecs_security_tool(
        cluster_names: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        analysis_scope: Optional[str] = "basic",
    ) -> Dict[str, Any]:
        """
        Perform minimal security analysis of ECS clusters.

        Args:
            cluster_names: List of cluster names to analyze
            regions: Optional list of regions (not used in minimal implementation)
            analysis_scope: Scope of analysis (not used in minimal implementation)

        Returns:
            Dictionary containing security analysis results
        """
        return await analyze_ecs_security(cluster_names, regions, analysis_scope)
