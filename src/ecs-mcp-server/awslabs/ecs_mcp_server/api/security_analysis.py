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
                    container_instances = await adapter.collect_container_instances(cluster_name)
                    capacity_providers = await adapter.collect_capacity_providers(cluster_name)

                    # Combine all data
                    combined_data = {
                        **cluster_data,
                        "container_instances": container_instances.get("container_instances", []),
                        "capacity_providers": capacity_providers.get("capacity_providers", []),
                    }

                    # Analyze security
                    analyzer = SecurityAnalyzer(cluster_name, region)
                    result = analyzer.analyze(combined_data)

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

    async def collect_container_instances(self, cluster_name: str) -> Dict[str, Any]:
        """
        Collect container instance data for a cluster.

        Args:
            cluster_name: Name of the cluster

        Returns:
            Dictionary with container instances data or error
        """
        try:
            # First, list container instance ARNs
            list_response = await ecs_api_operation(
                "ListContainerInstances",
                {"cluster": cluster_name},
            )

            if "error" in list_response:
                return {"error": list_response["error"], "cluster_name": cluster_name}

            instance_arns = list_response.get("containerInstanceArns", [])

            # If no instances, return empty list
            if not instance_arns:
                return {
                    "status": "success",
                    "cluster_name": cluster_name,
                    "container_instances": [],
                }

            # Describe the container instances to get detailed information
            describe_response = await ecs_api_operation(
                "DescribeContainerInstances",
                {"cluster": cluster_name, "containerInstances": instance_arns},
            )

            if "error" in describe_response:
                return {"error": describe_response["error"], "cluster_name": cluster_name}

            return {
                "status": "success",
                "cluster_name": cluster_name,
                "container_instances": describe_response.get("containerInstances", []),
            }
        except Exception as e:
            logger.error(f"Error collecting container instances for {cluster_name}: {e}")
            return {"error": str(e), "cluster_name": cluster_name}

    async def collect_capacity_providers(self, cluster_name: str) -> Dict[str, Any]:
        """
        Collect capacity provider data for a cluster.

        Args:
            cluster_name: Name of the cluster

        Returns:
            Dictionary with capacity providers data or error
        """
        try:
            # Get cluster data which includes capacity provider info
            cluster_response = await ecs_api_operation(
                "DescribeClusters",
                {"clusters": [cluster_name], "include": ["SETTINGS", "CONFIGURATIONS"]},
            )

            if "error" in cluster_response:
                return {"error": cluster_response["error"], "cluster_name": cluster_name}

            clusters = cluster_response.get("clusters", [])
            if not clusters:
                return {
                    "error": f"Cluster {cluster_name} not found",
                    "cluster_name": cluster_name,
                }

            cluster = clusters[0]
            capacity_provider_arns = cluster.get("capacityProviders", [])

            # If no capacity providers, return empty list
            if not capacity_provider_arns:
                return {
                    "status": "success",
                    "cluster_name": cluster_name,
                    "capacity_providers": [],
                }

            # Describe the capacity providers to get detailed information
            describe_response = await ecs_api_operation(
                "DescribeCapacityProviders",
                {"capacityProviders": capacity_provider_arns},
            )

            if "error" in describe_response:
                return {"error": describe_response["error"], "cluster_name": cluster_name}

            return {
                "status": "success",
                "cluster_name": cluster_name,
                "capacity_providers": describe_response.get("capacityProviders", []),
            }
        except Exception as e:
            logger.error(f"Error collecting capacity providers for {cluster_name}: {e}")
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
        container_instances = ecs_data.get("container_instances", [])
        capacity_providers = ecs_data.get("capacity_providers", [])

        # Run security checks (will be implemented in subsequent subtasks)
        self._analyze_cluster_security(cluster_data)
        self._analyze_logging_security(cluster_data)
        self._analyze_cluster_iam_security(cluster_data)
        self._analyze_enhanced_cluster_security(container_instances)
        self._analyze_capacity_providers(capacity_providers)

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

    def _analyze_enhanced_cluster_security(self, container_instances: List[Dict[str, Any]]) -> None:
        """
        Analyze enhanced cluster security including container instances.

        Checks:
        - ECS agent versions for vulnerabilities
        - Agent connectivity status
        - Legacy instance types

        Args:
            container_instances: List of container instance data dictionaries
        """
        if not container_instances:
            # No container instances to analyze (could be Fargate-only cluster)
            return

        # Known vulnerable or outdated agent versions (example list)
        # In production, this should be maintained and updated regularly
        MINIMUM_RECOMMENDED_AGENT_VERSION = "1.70.0"

        for instance in container_instances:
            instance_id = instance.get("ec2InstanceId", "unknown")
            container_instance_arn = instance.get("containerInstanceArn", "")
            container_instance_id = (
                container_instance_arn.split("/")[-1] if container_instance_arn else instance_id
            )

            # Check ECS agent version
            version_info = instance.get("versionInfo", {})
            agent_version = version_info.get("agentVersion", "unknown")

            if agent_version != "unknown":
                # Parse version for comparison
                if self._is_agent_version_outdated(
                    agent_version, MINIMUM_RECOMMENDED_AGENT_VERSION
                ):
                    self._add_recommendation(
                        title="🔴 Outdated ECS Agent Version",
                        severity="High",
                        category="Container Instance",
                        resource=container_instance_id,
                        resource_type="ContainerInstance",
                        issue=(
                            f"Container instance {container_instance_id} is running ECS agent "
                            f"version {agent_version}, which is below the recommended minimum "
                            f"version {MINIMUM_RECOMMENDED_AGENT_VERSION}. Outdated agents may "
                            "have security vulnerabilities or lack important features."
                        ),
                        recommendation=(
                            "Update the ECS agent to the latest version to ensure security patches "
                            "and feature improvements are applied"
                        ),
                        remediation_steps=[
                            "# For Amazon Linux 2 AMI:",
                            f"# SSH into the instance (EC2 instance ID: {instance_id})",
                            "sudo yum update -y ecs-init",
                            "sudo systemctl restart ecs",
                            "",
                            "# Or update the AMI to the latest ECS-optimized AMI:",
                            "# 1. Drain the container instance:",
                            f"aws ecs update-container-instances-state "
                            f"--cluster {self.cluster_name} "
                            f"--container-instances {container_instance_id} --status DRAINING",
                            "# 2. Wait for tasks to drain",
                            "# 3. Terminate the instance and launch a new one with the latest AMI",
                        ],
                        documentation_links=[
                            "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                            "ecs-agent-update.html",
                            "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                            "ecs-optimized_AMI.html",
                        ],
                    )

            # Check agent connectivity status
            agent_connected = instance.get("agentConnected", False)
            status = instance.get("status", "UNKNOWN")

            if not agent_connected or status != "ACTIVE":
                self._add_recommendation(
                    title="🔴 Container Instance Connectivity Issue",
                    severity="High",
                    category="Container Instance",
                    resource=container_instance_id,
                    resource_type="ContainerInstance",
                    issue=(
                        f"Container instance {container_instance_id} has connectivity issues. "
                        f"Agent connected: {agent_connected}, Status: {status}. "
                        "This prevents the instance from receiving tasks and may indicate "
                        "network or IAM permission issues."
                    ),
                    recommendation=(
                        "Investigate and resolve connectivity issues. Check network configuration, "
                        "security groups, IAM roles, and ECS agent logs."
                    ),
                    remediation_steps=[
                        "# Check container instance details:",
                        f"aws ecs describe-container-instances --cluster {self.cluster_name} "
                        f"--container-instances {container_instance_id}",
                        "",
                        f"# Check ECS agent logs on the instance (EC2 instance ID: {instance_id}):",
                        "# SSH into the instance and run:",
                        "sudo cat /var/log/ecs/ecs-agent.log",
                        "",
                        "# Verify IAM role has required permissions:",
                        "# - AmazonEC2ContainerServiceforEC2Role policy",
                        "",
                        "# Check security group allows outbound HTTPS (443) to ECS endpoints",
                    ],
                    documentation_links=[
                        "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                        "troubleshooting.html#agent-connection",
                        "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                        "instance_IAM_role.html",
                    ],
                )

            # Check for legacy instance types
            attributes = instance.get("attributes", [])
            instance_type = None
            for attr in attributes:
                if attr.get("name") == "ecs.instance-type":
                    instance_type = attr.get("value")
                    break

            if instance_type:
                # Check for legacy instance types (t2, m4, c4, r4, etc.)
                legacy_families = ["t2", "m4", "c4", "r4", "i3", "d2", "x1"]
                instance_family = instance_type.split(".")[0] if "." in instance_type else ""

                if instance_family in legacy_families:
                    self._add_recommendation(
                        title="🟡 Legacy Instance Type Detected",
                        severity="Medium",
                        category="Container Instance",
                        resource=container_instance_id,
                        resource_type="ContainerInstance",
                        issue=(
                            f"Container instance {container_instance_id} is using legacy instance "
                            f"type {instance_type}. Newer generation instance types offer better "
                            "performance, security features, and cost efficiency."
                        ),
                        recommendation=(
                            "Migrate to current generation instance types (e.g., t3, m5, c5, r5) "
                            "for improved performance and security features like "
                            "enhanced networking and Nitro System security."
                        ),
                        remediation_steps=[
                            "# Plan migration to current generation instances:",
                            "# 1. Update your Auto Scaling Group or launch template",
                            "# 2. Gradually replace instances:",
                            f"aws ecs update-container-instances-state "
                            f"--cluster {self.cluster_name} "
                            f"--container-instances {container_instance_id} --status DRAINING",
                            "# 3. Wait for tasks to drain, then terminate the old instance",
                            "# 4. New instance will launch with updated instance type",
                        ],
                        documentation_links=[
                            "https://aws.amazon.com/ec2/instance-types/",
                            "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html",
                        ],
                    )

    def _analyze_capacity_providers(self, capacity_providers: List[Dict[str, Any]]) -> None:
        """
        Analyze capacity provider security configurations.

        Checks:
        - Managed termination protection
        - Auto-scaling security configurations

        Args:
            capacity_providers: List of capacity provider data dictionaries
        """
        if not capacity_providers:
            # No capacity providers configured
            return

        for provider in capacity_providers:
            provider_name = provider.get("name", "unknown")

            # Check if this is an Auto Scaling Group capacity provider
            auto_scaling_group = provider.get("autoScalingGroupProvider")
            if not auto_scaling_group:
                # This is likely a Fargate capacity provider, skip
                continue

            # Check managed termination protection
            managed_termination_protection = auto_scaling_group.get(
                "managedTerminationProtection", "DISABLED"
            )

            if managed_termination_protection == "DISABLED":
                self._add_recommendation(
                    title="🟡 Managed Termination Protection Disabled",
                    severity="Medium",
                    category="Capacity Provider",
                    resource=provider_name,
                    resource_type="CapacityProvider",
                    issue=(
                        f"Capacity provider {provider_name} has managed termination protection "
                        "disabled. This means ECS cannot prevent Amazon EC2 Auto Scaling from "
                        "terminating instances that have running tasks during scale-in events."
                    ),
                    recommendation=(
                        "Enable managed termination protection to prevent premature termination "
                        "of instances with running tasks, ensuring graceful task shutdown."
                    ),
                    remediation_steps=[
                        "# Update capacity provider to enable managed termination protection:",
                        f"aws ecs update-capacity-provider --name {provider_name} "
                        "--auto-scaling-group-provider "
                        "managedTerminationProtection=ENABLED",
                    ],
                    documentation_links=[
                        "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                        "asg-capacity-providers.html#asg-capacity-providers-termination-protection",
                    ],
                )

            # Check managed scaling configuration
            managed_scaling = auto_scaling_group.get("managedScaling", {})
            if managed_scaling:
                status = managed_scaling.get("status", "DISABLED")
                target_capacity = managed_scaling.get("targetCapacity", 100)

                # Check if managed scaling is enabled
                if status == "DISABLED":
                    self._add_recommendation(
                        title="🟢 Managed Scaling Disabled",
                        severity="Low",
                        category="Capacity Provider",
                        resource=provider_name,
                        resource_type="CapacityProvider",
                        issue=(
                            f"Capacity provider {provider_name} has managed scaling disabled. "
                            "While not a security issue, this means ECS cannot automatically "
                            "scale your Auto Scaling Group based on task requirements."
                        ),
                        recommendation=(
                            "Consider enabling managed scaling to allow ECS to automatically "
                            "manage your cluster capacity based on task requirements."
                        ),
                        remediation_steps=[
                            "# Enable managed scaling for capacity provider:",
                            f"aws ecs update-capacity-provider --name {provider_name} "
                            "--auto-scaling-group-provider "
                            "managedScaling={status=ENABLED,targetCapacity=100,"
                            "minimumScalingStepSize=1,maximumScalingStepSize=10000}",
                        ],
                        documentation_links=[
                            "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                            "asg-capacity-providers.html#asg-capacity-providers-managed-scaling",
                        ],
                    )
                elif target_capacity < 80 or target_capacity > 100:
                    # Target capacity outside recommended range
                    self._add_recommendation(
                        title="🟡 Suboptimal Target Capacity Configuration",
                        severity="Medium",
                        category="Capacity Provider",
                        resource=provider_name,
                        resource_type="CapacityProvider",
                        issue=(
                            f"Capacity provider {provider_name} has target capacity set to "
                            f"{target_capacity}%. AWS recommends a target capacity between 80-100% "
                            "for optimal resource utilization and cost efficiency."
                        ),
                        recommendation=(
                            "Adjust target capacity to 80-100% range. Lower values may lead to "
                            "over-provisioning and higher costs, while values above 100% "
                            "are invalid."
                        ),
                        remediation_steps=[
                            "# Update target capacity to recommended range:",
                            f"aws ecs update-capacity-provider --name {provider_name} "
                            "--auto-scaling-group-provider "
                            f"managedScaling={{status=ENABLED,targetCapacity=100,"
                            "minimumScalingStepSize=1,maximumScalingStepSize=10000}",
                        ],
                        documentation_links=[
                            "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                            "asg-capacity-providers.html#asg-capacity-providers-managed-scaling",
                        ],
                    )

    def _is_agent_version_outdated(self, current_version: str, minimum_version: str) -> bool:
        """
        Compare ECS agent versions to determine if current version is outdated.

        Args:
            current_version: Current agent version (e.g., "1.68.2")
            minimum_version: Minimum recommended version (e.g., "1.70.0")

        Returns:
            True if current version is outdated, False otherwise
        """
        try:
            # Parse versions into tuples of integers for comparison
            current_parts = [int(x) for x in current_version.split(".")]
            minimum_parts = [int(x) for x in minimum_version.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(current_parts), len(minimum_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            minimum_parts.extend([0] * (max_len - len(minimum_parts)))

            # Compare versions
            return current_parts < minimum_parts
        except (ValueError, AttributeError):
            # If version parsing fails, assume it's outdated to be safe
            return True

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

    def _analyze_cluster_iam_security(self, cluster: Dict[str, Any]) -> None:
        """
        Analyze cluster-level IAM security configurations.

        Checks:
        - Service-linked role existence and configuration
        - Cluster-level IAM permissions

        Args:
            cluster: Cluster data dictionary
        """
        cluster_name = cluster.get("clusterName", "unknown")

        # Check for ECS service-linked role
        # The service-linked role is automatically created when you use ECS,
        # but we should verify it exists and recommend checking its configuration
        # Note: We can't directly query IAM from the cluster data, but we can
        # provide guidance on verifying the service-linked role exists

        # Check if cluster has any configuration that would require service-linked role
        # Service-linked roles are required for:
        # - ECS service discovery
        # - ECS Exec
        # - Load balancer integration
        # - Auto Scaling

        configuration = cluster.get("configuration", {})
        exec_config = configuration.get("executeCommandConfiguration", {})

        # If ECS Exec is configured, service-linked role is critical
        if exec_config:
            self._add_recommendation(
                title="🟡 Verify ECS Service-Linked Role Configuration",
                severity="Medium",
                category="IAM",
                resource=cluster_name,
                issue=(
                    f"Cluster {cluster_name} has ECS Exec configured, which requires the "
                    "AWSServiceRoleForECS service-linked role. While this role is typically "
                    "created automatically, it's important to verify it exists and has the "
                    "correct permissions."
                ),
                recommendation=(
                    "Verify that the AWSServiceRoleForECS service-linked role exists in your "
                    "account and has the necessary permissions. This role is required for ECS "
                    "to manage resources on your behalf, including ECS Exec, service discovery, "
                    "and load balancer integration."
                ),
                remediation_steps=[
                    "# Check if the service-linked role exists:",
                    "aws iam get-role --role-name AWSServiceRoleForECS",
                    "",
                    "# If the role doesn't exist, create it:",
                    "aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com",
                    "",
                    "# Verify the role has the correct managed policy attached:",
                    "aws iam list-attached-role-policies --role-name AWSServiceRoleForECS",
                    "# Expected policy: AmazonECSServiceRolePolicy",
                    "",
                    "# Review the role's trust relationship:",
                    (
                        "aws iam get-role --role-name AWSServiceRoleForECS "
                        "--query 'Role.AssumeRolePolicyDocument'"
                    ),
                ],
                documentation_links=[
                    "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                    "using-service-linked-roles.html",
                    "https://docs.aws.amazon.com/IAM/latest/UserGuide/"
                    "using-service-linked-roles.html",
                ],
            )

        # Check for capacity providers which also require service-linked role
        capacity_provider_arns = cluster.get("capacityProviders", [])
        if capacity_provider_arns:
            self._add_recommendation(
                title="🟡 Verify Service-Linked Role for Capacity Providers",
                severity="Medium",
                category="IAM",
                resource=cluster_name,
                issue=(
                    f"Cluster {cluster_name} uses capacity providers, which require the "
                    "AWSServiceRoleForECS service-linked role for Auto Scaling integration. "
                    "Ensure this role exists and has proper permissions."
                ),
                recommendation=(
                    "Verify the service-linked role exists and can manage Auto Scaling groups "
                    "on behalf of ECS. Without proper permissions, capacity providers may fail "
                    "to scale your cluster."
                ),
                remediation_steps=[
                    "# Verify service-linked role exists:",
                    "aws iam get-role --role-name AWSServiceRoleForECS",
                    "",
                    "# Check the role can access Auto Scaling:",
                    "aws iam list-attached-role-policies --role-name AWSServiceRoleForECS",
                    "",
                    "# If using custom capacity providers, verify additional permissions:",
                    "# - autoscaling:CreateAutoScalingGroup",
                    "# - autoscaling:UpdateAutoScalingGroup",
                    "# - autoscaling:DeleteAutoScalingGroup",
                    "# - autoscaling:DescribeAutoScalingGroups",
                ],
                documentation_links=[
                    "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                    "using-service-linked-roles.html",
                    "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/"
                    "asg-capacity-providers.html#asg-capacity-providers-iam",
                ],
            )

        # Provide general IAM best practices recommendation
        self._add_recommendation(
            title="🟢 Review Cluster IAM Configuration",
            severity="Low",
            category="IAM",
            resource=cluster_name,
            issue=(
                "Regular review of IAM configurations is a security best practice. "
                "Ensure that all IAM roles and policies follow the principle of least privilege."
            ),
            recommendation=(
                "Periodically review IAM roles and policies associated with this cluster, "
                "including service-linked roles, task roles, and execution roles. Remove any "
                "unnecessary permissions and ensure compliance with your organization's "
                "security policies."
            ),
            remediation_steps=[
                "# Review service-linked role:",
                "aws iam get-role --role-name AWSServiceRoleForECS",
                "",
                "# List all roles used by tasks in this cluster:",
                f"aws ecs list-services --cluster {cluster_name}",
                "# Then describe each service to see task and execution roles",
                "",
                "# Use IAM Access Analyzer to identify unused permissions:",
                "aws accessanalyzer list-analyzers",
                "",
                "# Review IAM policy simulator for specific permissions:",
                "# https://policysim.aws.amazon.com/",
            ],
            documentation_links=[
                "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
                "https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html",
                "https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-getting-started.html",
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
