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

This module provides security analysis for ECS clusters including task definition security.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation

logger = logging.getLogger(__name__)


class DataAdapter:
    """Adapter for collecting ECS data for security analysis."""

    def __init__(self) -> None:
        """Initialize the DataAdapter."""
        self.logger = logger

    async def collect_cluster_data(self, cluster_name: str) -> Dict[str, Any]:
        """Collect basic cluster data for security analysis."""
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

    async def collect_task_definitions(self, cluster_name: str) -> Dict[str, Any]:
        """Collect task definitions for security analysis."""
        try:
            # Get services in cluster
            services_response = await ecs_api_operation("ListServices", {"cluster": cluster_name})
            if "error" in services_response:
                return {
                    "error": services_response["error"],
                    "task_definitions": [],
                    "status": "failed",
                }

            service_arns = services_response.get("serviceArns", [])
            if not service_arns:
                return {"task_definitions": [], "status": "success"}

            # Get service details to extract task definition ARNs
            describe_response = await ecs_api_operation(
                "DescribeServices", {"cluster": cluster_name, "services": service_arns}
            )
            if "error" in describe_response:
                return {
                    "error": describe_response["error"],
                    "task_definitions": [],
                    "status": "failed",
                }

            task_definitions = []
            for service in describe_response.get("services", []):
                task_def_arn = service.get("taskDefinition")
                if task_def_arn:
                    task_def_response = await ecs_api_operation(
                        "DescribeTaskDefinition", {"taskDefinition": task_def_arn}
                    )
                    if "taskDefinition" in task_def_response:
                        task_definitions.append(task_def_response["taskDefinition"])

            return {"task_definitions": task_definitions, "status": "success"}

        except Exception as e:
            self.logger.error(f"Error collecting task definitions: {e}")
            return {"error": str(e), "task_definitions": [], "status": "failed"}

    def _create_error_response(self, error: str, cluster_name: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "error": error,
            "cluster_name": cluster_name,
            "status": "failed",
        }


class SecurityAnalyzer:
    """ECS security analyzer with task definition support."""

    def __init__(self) -> None:
        """Initialize the SecurityAnalyzer."""
        self.logger = logger

    def analyze(
        self, cluster_data: Dict[str, Any], task_definitions_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform security analysis including Container Insights and task definition security."""
        try:
            recommendations = []

            # Check Container Insights
            recommendations.extend(self._check_container_insights(cluster_data))

            # Analyze task definition security if data is provided
            if task_definitions_data and task_definitions_data.get("status") == "success":
                task_definitions = task_definitions_data.get("task_definitions", [])
                cluster_name = cluster_data.get("cluster_name", "unknown")
                recommendations.extend(
                    self._analyze_container_security(task_definitions, cluster_name)
                )

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

    def _analyze_container_security(
        self, task_definitions: List[Dict[str, Any]], cluster_name: str
    ) -> List[Dict[str, Any]]:
        """Analyze container security configurations in task definitions."""
        recommendations = []

        for task_def in task_definitions:
            task_family = task_def.get("family", "unknown")

            for container in task_def.get("containerDefinitions", []):
                container_name = container.get("name", "unknown")
                resource = (
                    f"Container: {container_name} | Task: {task_family} | Cluster: {cluster_name}"
                )

                # Check for root user
                user = container.get("user")
                if user == "0" or user == "root" or not user:
                    recommendations.append(
                        {
                            "title": "Configure Container to Run as Non-Root User",
                            "severity": "High",
                            "category": "container_security",
                            "resource": resource,
                            "issue": "Container runs as root user, violating least privilege",
                            "recommendation": "Configure container to run as non-privileged user",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                # Check for read-only root filesystem
                if not container.get("readonlyRootFilesystem", False):
                    recommendations.append(
                        {
                            "title": "Enable Read-Only Root Filesystem",
                            "severity": "Medium",
                            "category": "container_security",
                            "resource": resource,
                            "issue": "Container root filesystem is writable",
                            "recommendation": "Enable readonlyRootFilesystem to prevent tampering",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                # Check for health checks
                if not container.get("healthCheck"):
                    recommendations.append(
                        {
                            "title": "Configure Container Health Check",
                            "severity": "Medium",
                            "category": "monitoring",
                            "resource": resource,
                            "issue": "Container lacks health check configuration",
                            "recommendation": "Configure health check for container monitoring",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

                # Check for privileged mode
                if container.get("privileged", False):
                    recommendations.append(
                        {
                            "title": "Avoid Privileged Container Mode",
                            "severity": "Critical",
                            "category": "container_security",
                            "resource": resource,
                            "issue": "Container runs in privileged mode with full host access",
                            "recommendation": "Remove privileged mode, use specific capabilities",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        return recommendations

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
    analysis_scope: Optional[str] = "comprehensive",
) -> Dict[str, Any]:
    """
    Perform security analysis of ECS clusters including task definition security.
    Now includes Container Insights monitoring and container security analysis.
    """
    try:
        logger.info("Starting ECS security analysis with task definition support")

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
                # Collect cluster data
                cluster_data = await data_adapter.collect_cluster_data(cluster_name)

                if cluster_data.get("status") == "failed":
                    logger.warning(f"Skipping cluster {cluster_name}: {cluster_data.get('error')}")
                    continue

                # Collect task definition data for comprehensive analysis
                task_definitions_data = None
                if analysis_scope == "comprehensive":
                    task_definitions_data = await data_adapter.collect_task_definitions(
                        cluster_name
                    )

                    if task_definitions_data.get("status") == "failed":
                        logger.warning(f"Task definition collection failed for {cluster_name}")

                # Perform security analysis
                analysis_result = security_analyzer.analyze(cluster_data, task_definitions_data)

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
    """Register the security analysis module with MCP."""

    @mcp.tool(name="analyze_ecs_security")
    async def analyze_ecs_security_tool(
        cluster_names: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        analysis_scope: Optional[str] = "comprehensive",
    ) -> Dict[str, Any]:
        """
        Perform security analysis of ECS clusters including task definition security.
        """
        return await analyze_ecs_security(cluster_names, regions, analysis_scope)
