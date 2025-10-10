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
API for ECS security analysis operations.

This module provides comprehensive security analysis for ECS clusters,
identifying misconfigurations and providing actionable recommendations.
"""

import logging
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation

logger = logging.getLogger(__name__)


async def analyze_ecs_security(
    cluster_names: List[str],
    regions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for ECS security analysis.

    Args:
        cluster_names: List of cluster names to analyze (required)
        regions: Optional list of regions (default: ["us-east-1"])

    Returns:
        Dictionary with analysis results and summary
    """
    if not cluster_names:
        return {
            "status": "error",
            "error": (
                "cluster_names is required. Please specify which clusters to analyze. "
                "Use ecs_resource_management tool to list available clusters first."
            ),
            "total_clusters_analyzed": 0,
            "total_recommendations": 0,
            "results": [],
        }

    regions = regions or ["us-east-1"]
    all_results = []
    errors = []

    for region in regions:
        try:
            # Analyze specified clusters
            clusters_to_analyze = cluster_names

            # Analyze each cluster
            for cluster_name in clusters_to_analyze:
                try:
                    # Collect data
                    adapter = DataAdapter(region)
                    cluster_data = await adapter.collect_cluster_data(cluster_name)

                    # Analyze security
                    analyzer = SecurityAnalyzer(cluster_name, region)
                    result = analyzer.analyze(cluster_data)

                    all_results.append(result)
                except Exception as e:
                    logger.error(f"Error analyzing cluster {cluster_name} in {region}: {e}")
                    errors.append(
                        {
                            "cluster": cluster_name,
                            "region": region,
                            "error": str(e),
                        }
                    )
        except Exception as e:
            logger.error(f"Error processing region {region}: {e}")
            errors.append(
                {
                    "region": region,
                    "error": str(e),
                }
            )

    # Calculate totals
    total_recommendations = sum(len(r.get("recommendations", [])) for r in all_results)

    response = {
        "status": "success" if all_results else "error",
        "total_clusters_analyzed": len(all_results),
        "total_recommendations": total_recommendations,
        "results": all_results,
    }

    if errors:
        response["errors"] = errors

    return response


async def _discover_clusters(region: str) -> Dict[str, Any]:
    """
    Discover all clusters in a region.

    Args:
        region: AWS region

    Returns:
        Dictionary with list of cluster names or error
    """
    try:
        response = await ecs_api_operation("ListClusters", {})

        if "error" in response:
            return {"error": response["error"]}

        cluster_arns = response.get("clusterArns", [])
        # Extract cluster names from ARNs
        cluster_names = [arn.split("/")[-1] for arn in cluster_arns]

        return {"clusters": cluster_names}
    except Exception as e:
        logger.error(f"Error discovering clusters in {region}: {e}")
        return {"error": str(e)}


class DataAdapter:
    """Adapter that uses existing MCP tools to collect ECS data."""

    def __init__(self, region: str):
        """
        Initialize DataAdapter.

        Args:
            region: AWS region
        """
        self.region = region

    async def collect_cluster_data(self, cluster_name: str) -> Dict[str, Any]:
        """
        Collect cluster data using existing ECS API operations.

        Args:
            cluster_name: Name of the cluster

        Returns:
            Dictionary with cluster data or error
        """
        try:
            response = await ecs_api_operation(
                "DescribeClusters",
                {"clusters": [cluster_name], "include": ["SETTINGS", "CONFIGURATIONS"]},
            )

            if "error" in response:
                return {"error": response["error"], "cluster_name": cluster_name}

            clusters = response.get("clusters", [])
            if not clusters:
                return {
                    "error": f"Cluster {cluster_name} not found",
                    "cluster_name": cluster_name,
                }

            return {"status": "success", "cluster": clusters[0]}
        except Exception as e:
            logger.error(f"Error collecting cluster data for {cluster_name}: {e}")
            return {"error": str(e), "cluster_name": cluster_name}


class SecurityAnalyzer:
    """Security analysis engine for ECS resources."""

    def __init__(self, cluster_name: str, region: str):
        """
        Initialize SecurityAnalyzer.

        Args:
            cluster_name: Name of the cluster being analyzed
            region: AWS region
        """
        self.cluster_name = cluster_name
        self.region = region
        self.recommendations = []

    def _add_recommendation(
        self,
        title: str,
        severity: str,
        category: str,
        resource: str,
        issue: str,
        recommendation: str,
        remediation_steps: List[str],
        documentation_links: List[str],
        resource_type: str = "Cluster",
    ) -> None:
        """
        Add a security recommendation with consistent structure.

        Args:
            title: Brief title of the issue
            severity: Severity level (High, Medium, Low)
            category: Category of the issue
            resource: Resource name
            issue: Description of the issue
            recommendation: Recommended action
            remediation_steps: List of CLI commands or steps
            documentation_links: List of AWS documentation URLs
            resource_type: Type of resource (default: Cluster)
        """
        self.recommendations.append(
            {
                "title": title,
                "severity": severity,
                "category": category,
                "resource": resource,
                "resource_type": resource_type,
                "cluster_name": self.cluster_name,
                "region": self.region,
                "issue": issue,
                "recommendation": recommendation,
                "remediation_steps": remediation_steps,
                "documentation_links": documentation_links,
            }
        )

    def analyze(self, ecs_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main analysis orchestrator.

        Args:
            ecs_data: Dictionary containing ECS resource data

        Returns:
            Dictionary with analysis results
        """
        self.recommendations = []

        if "error" in ecs_data:
            return {
                "status": "error",
                "error": ecs_data["error"],
                "cluster_name": ecs_data.get("cluster_name", "unknown"),
                "region": self.region,
                "recommendations": [],
                "summary": {"total_issues": 0, "by_severity": {}, "by_category": {}},
            }

        cluster_data = ecs_data.get("cluster", {})

        # Run security checks (will be implemented in subsequent subtasks)
        self._analyze_cluster_security(cluster_data)
        self._analyze_logging_security(cluster_data)

        # Generate summary
        summary = self._generate_summary()

        return {
            "status": "success",
            "cluster_name": cluster_data.get("clusterName", "unknown"),
            "region": self.region,
            "recommendations": self.recommendations,
            "summary": summary,
        }

    def _analyze_cluster_security(self, cluster: Dict[str, Any]) -> None:
        """
        Analyze cluster-level security.

        Checks:
        - Container Insights configuration
        - Execute command logging settings
        - Cluster status and availability

        Args:
            cluster: Cluster data dictionary
        """
        cluster_name = cluster.get("clusterName", "unknown")

        # Check Container Insights
        settings = cluster.get("settings", [])
        container_insights_enabled = any(
            s.get("name") == "containerInsights" and s.get("value") == "enabled" for s in settings
        )

        if not container_insights_enabled:
            self._add_recommendation(
                title="Container Insights Disabled",
                severity="Medium",
                category="Monitoring",
                resource=cluster_name,
                issue="Container Insights is not enabled for this cluster",
                recommendation=(
                    "Enable Container Insights to collect metrics and logs from your "
                    "containerized applications and microservices"
                ),
                remediation_steps=[
                    f"aws ecs update-cluster-settings --cluster {cluster_name} "
                    "--settings name=containerInsights,value=enabled"
                ],
                documentation_links=[
                    "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                    "cloudwatch-container-insights.html"
                ],
            )

        # Check execute command logging
        configuration = cluster.get("configuration", {})
        exec_config = configuration.get("executeCommandConfiguration", {})
        logging_config = exec_config.get("logging", "NONE")

        if logging_config == "NONE" or logging_config == "DEFAULT":
            severity = "High" if logging_config == "NONE" else "Medium"
            self._add_recommendation(
                title="Execute Command Logging Not Configured",
                severity=severity,
                category="Logging",
                resource=cluster_name,
                issue=(
                    f"Execute command logging is set to {logging_config}. "
                    "This means ECS Exec sessions are not being logged."
                ),
                recommendation=(
                    "Configure execute command logging to CloudWatch Logs or S3 "
                    "to maintain audit trails of interactive sessions"
                ),
                remediation_steps=[
                    f"aws ecs update-cluster --cluster {cluster_name} "
                    "--configuration executeCommandConfiguration="
                    "{logging=OVERRIDE,logConfiguration={cloudWatchLogGroupName="
                    f"/aws/ecs/{cluster_name}/exec}}"
                ],
                documentation_links=[
                    "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html"
                ],
            )

        # Check cluster status
        status = cluster.get("status", "UNKNOWN")
        if status != "ACTIVE":
            self._add_recommendation(
                title="Cluster Not Active",
                severity="High",
                category="Availability",
                resource=cluster_name,
                issue=f"Cluster status is {status}, not ACTIVE",
                recommendation=(
                    "Investigate why the cluster is not in ACTIVE state. "
                    "This may indicate a configuration or resource issue."
                ),
                remediation_steps=[
                    f"aws ecs describe-clusters --clusters {cluster_name} "
                    "--include SETTINGS,CONFIGURATIONS"
                ],
                documentation_links=[
                    "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/clusters.html"
                ],
            )

    def _analyze_logging_security(self, cluster: Dict[str, Any]) -> None:
        """
        Analyze logging security.

        Checks:
        - CloudWatch logging configuration
        - Log retention policies

        Args:
            cluster: Cluster data dictionary
        """
        cluster_name = cluster.get("clusterName", "unknown")

        # Check execute command logging configuration (detailed check)
        configuration = cluster.get("configuration", {})
        exec_config = configuration.get("executeCommandConfiguration", {})
        log_config = exec_config.get("logConfiguration", {})

        # Check if CloudWatch log group is configured
        cw_log_group = log_config.get("cloudWatchLogGroupName")
        if not cw_log_group:
            self._add_recommendation(
                title="CloudWatch Log Group Not Configured for ECS Exec",
                severity="Medium",
                category="Logging",
                resource=cluster_name,
                issue=(
                    "CloudWatch log group is not configured for ECS Exec sessions. "
                    "This limits audit capabilities."
                ),
                recommendation=(
                    "Configure a CloudWatch log group to capture ECS Exec session logs "
                    "for security auditing and compliance"
                ),
                remediation_steps=[
                    "# First, create a CloudWatch log group",
                    f"aws logs create-log-group --log-group-name /aws/ecs/{cluster_name}/exec",
                    "",
                    "# Then update the cluster configuration",
                    f"aws ecs update-cluster --cluster {cluster_name} "
                    "--configuration executeCommandConfiguration="
                    "{logging=OVERRIDE,logConfiguration={cloudWatchLogGroupName="
                    f"/aws/ecs/{cluster_name}/exec}}",
                ],
                documentation_links=[
                    "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                    "ecs-exec.html#ecs-exec-logging"
                ],
            )

        # Check if log encryption is enabled
        cw_encryption_enabled = log_config.get("cloudWatchEncryptionEnabled", False)
        if cw_log_group and not cw_encryption_enabled:
            self._add_recommendation(
                title="CloudWatch Logs Encryption Not Enabled",
                severity="Medium",
                category="Logging",
                resource=cluster_name,
                issue=(
                    "CloudWatch logs encryption is not enabled for ECS Exec sessions. "
                    "Logs may contain sensitive information."
                ),
                recommendation=(
                    "Enable CloudWatch logs encryption to protect sensitive data "
                    "in ECS Exec session logs"
                ),
                remediation_steps=[
                    f"aws ecs update-cluster --cluster {cluster_name} "
                    "--configuration executeCommandConfiguration="
                    "{logging=OVERRIDE,logConfiguration={cloudWatchLogGroupName="
                    f"{cw_log_group},cloudWatchEncryptionEnabled=true}}",
                ],
                documentation_links=[
                    "https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/"
                    "encrypt-log-data-kms.html"
                ],
            )

    def _generate_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics.

        Calculates:
        - Total issues by severity (High/Medium/Low)
        - Issues by category
        - Issues by cluster

        Returns:
            Dictionary with summary statistics
        """
        by_severity = {"High": 0, "Medium": 0, "Low": 0}
        by_category = {}

        for rec in self.recommendations:
            # Count by severity
            severity = rec.get("severity", "Unknown")
            if severity in by_severity:
                by_severity[severity] += 1

            # Count by category
            category = rec.get("category", "Unknown")
            by_category[category] = by_category.get(category, 0) + 1

        return {
            "total_issues": len(self.recommendations),
            "by_severity": by_severity,
            "by_category": by_category,
        }
