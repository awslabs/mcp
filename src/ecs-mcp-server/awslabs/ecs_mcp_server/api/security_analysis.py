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
import re
from typing import Any, Dict, List, Optional

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation
from awslabs.ecs_mcp_server.api.troubleshooting_tools.utils import (
    find_services,
    find_task_definitions,
)

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

    async def collect_task_definitions(
        self, cluster_name: str, region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Collect task definition data for IAM role analysis.

        Args:
            cluster_name: Name of the ECS cluster
            region: AWS region (default: us-east-1)

        Returns:
            Dictionary containing task definition data or error information
        """
        try:
            self.logger.info(f"Collecting task definitions for cluster {cluster_name} in {region}")

            # Use existing utility to find services in the cluster
            services = await find_services(cluster_name)

            if not services:
                self.logger.info(f"No services found in cluster {cluster_name}")
                return {"status": "success", "task_definitions": [], "cluster_name": cluster_name}

            # Collect task definitions for each service using existing utility
            task_definitions = []
            seen_task_def_arns = set()

            for service_name in services:
                task_defs = await find_task_definitions(
                    cluster_name=cluster_name, service_name=service_name
                )

                # Deduplicate task definitions by ARN
                for task_def in task_defs:
                    task_def_arn = task_def.get("taskDefinitionArn")
                    if task_def_arn and task_def_arn not in seen_task_def_arns:
                        seen_task_def_arns.add(task_def_arn)
                        task_definitions.append(task_def)

            self.logger.info(
                f"Successfully collected {len(task_definitions)} unique task definitions "
                f"for cluster {cluster_name}"
            )

            return {
                "status": "success",
                "task_definitions": task_definitions,
                "cluster_name": cluster_name,
            }

        except Exception as e:
            self.logger.error(f"Unexpected error collecting task definitions: {e}")
            return {"error": str(e), "cluster_name": cluster_name}

    async def collect_container_instances(
        self, cluster_name: str, region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Collect container instance data for security analysis.

        Args:
            cluster_name: Name of the ECS cluster
            region: AWS region (default: us-east-1)

        Returns:
            Dictionary containing container instance data or error information
        """
        try:
            self.logger.info(
                f"Collecting container instances for cluster {cluster_name} in {region}"
            )

            # List container instances
            list_response = await ecs_api_operation(
                "ListContainerInstances", {"cluster": cluster_name}
            )

            if "error" in list_response:
                self.logger.error(f"Error listing container instances: {list_response['error']}")
                return {"error": list_response["error"], "cluster_name": cluster_name}

            instance_arns = list_response.get("containerInstanceArns", [])

            if not instance_arns:
                self.logger.info(f"No container instances found in cluster {cluster_name}")
                return {
                    "status": "success",
                    "container_instances": [],
                    "cluster_name": cluster_name,
                }

            # Describe container instances
            describe_response = await ecs_api_operation(
                "DescribeContainerInstances",
                {"cluster": cluster_name, "containerInstances": instance_arns},
            )

            if "error" in describe_response:
                self.logger.error(
                    f"Error describing container instances: {describe_response['error']}"
                )
                return {"error": describe_response["error"], "cluster_name": cluster_name}

            instances = describe_response.get("containerInstances", [])
            self.logger.info(
                f"Successfully collected {len(instances)} container instances "
                f"for cluster {cluster_name}"
            )

            return {
                "status": "success",
                "container_instances": instances,
                "cluster_name": cluster_name,
            }

        except Exception as e:
            self.logger.error(f"Unexpected error collecting container instances: {e}")
            return {"error": str(e), "cluster_name": cluster_name}

    async def collect_capacity_providers(
        self, cluster_name: str, region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """
        Collect capacity provider data for security analysis.

        Args:
            cluster_name: Name of the ECS cluster
            region: AWS region (default: us-east-1)

        Returns:
            Dictionary containing capacity provider data or error information
        """
        try:
            self.logger.info(
                f"Collecting capacity providers for cluster {cluster_name} in {region}"
            )

            # Get cluster data to find capacity provider names
            cluster_response = await ecs_api_operation(
                "DescribeClusters", {"clusters": [cluster_name], "include": ["SETTINGS"]}
            )

            if "error" in cluster_response:
                self.logger.error(
                    f"Error getting cluster for capacity providers: {cluster_response['error']}"
                )
                return {"error": cluster_response["error"], "cluster_name": cluster_name}

            if not cluster_response.get("clusters"):
                return {"error": "Cluster not found", "cluster_name": cluster_name}

            cluster = cluster_response["clusters"][0]
            cp_names = cluster.get("capacityProviders", [])

            if not cp_names:
                self.logger.info(f"No capacity providers found in cluster {cluster_name}")
                return {
                    "status": "success",
                    "capacity_providers": [],
                    "cluster_name": cluster_name,
                }

            # Describe capacity providers
            describe_response = await ecs_api_operation(
                "DescribeCapacityProviders", {"capacityProviders": cp_names}
            )

            if "error" in describe_response:
                self.logger.error(
                    f"Error describing capacity providers: {describe_response['error']}"
                )
                return {"error": describe_response["error"], "cluster_name": cluster_name}

            providers = describe_response.get("capacityProviders", [])
            self.logger.info(
                f"Successfully collected {len(providers)} capacity providers "
                f"for cluster {cluster_name}"
            )

            return {
                "status": "success",
                "capacity_providers": providers,
                "cluster_name": cluster_name,
            }

        except Exception as e:
            self.logger.error(f"Unexpected error collecting capacity providers: {e}")
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
            ecs_data: Dictionary containing ECS cluster data and task definitions

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
        task_definitions = ecs_data.get("task_definitions", [])
        container_instances = ecs_data.get("container_instances", [])
        capacity_providers = ecs_data.get("capacity_providers", [])

        # Run security checks
        self._analyze_cluster_security(cluster_data)
        self._analyze_cluster_iam_security(cluster_data)
        self._analyze_logging_security(cluster_data)

        # Run enhanced cluster security checks
        self._analyze_enhanced_cluster_security(
            container_instances, cluster_data.get("clusterName", "unknown")
        )

        # Run capacity provider security checks
        self._analyze_capacity_providers(
            capacity_providers, cluster_data.get("clusterName", "unknown")
        )

        # Run IAM security checks for each task definition
        for task_def in task_definitions:
            self._analyze_iam_security(task_def, cluster_data.get("clusterName", "unknown"))

        # Run task definition security checks
        cluster_name = cluster_data.get("clusterName", "unknown")
        for task_def in task_definitions:
            self._analyze_task_definition_security(task_def, cluster_name)
            # Analyze image security for each container in the task definition
            for container in task_def.get("containerDefinitions", []):
                self._analyze_image_security(container, task_def.get("family", "unknown"))
            # Analyze container security configurations
            self._analyze_container_security(task_def, cluster_name)
            # Analyze container runtime security
            self._analyze_container_runtime_security(task_def, cluster_name)

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
        cluster_name = cluster.get("clusterName", "unknown")

        # Check for service-linked role
        service_linked_role = cluster.get("serviceLinkedRoleArn")
        if not service_linked_role:
            self.recommendations.append(
                {
                    "title": "Configure ECS Service-Linked Role",
                    "severity": "Medium",
                    "category": "IAM",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "No service-linked role configured for ECS cluster operations",
                    "recommendation": (
                        "Create and configure the AWSServiceRoleForECS service-linked role "
                        "for proper cluster management"
                    ),
                    "remediation_steps": [
                        "The service-linked role is typically created automatically",
                        (
                            "If missing, create it with: aws iam create-service-linked-role "
                            "--aws-service-name ecs.amazonaws.com"
                        ),
                    ],
                }
            )

    def _analyze_iam_security(self, task_def: Dict[str, Any], cluster_name: str) -> None:
        """Analyze IAM security for task definitions (advanced checks only)."""
        task_def_family = task_def.get("family", "unknown")
        task_role_arn = task_def.get("taskRoleArn")
        execution_role_arn = task_def.get("executionRoleArn")

        # Check for wildcard permissions in task role
        if task_role_arn and "*" in task_role_arn:
            self.recommendations.append(
                {
                    "title": "Avoid Wildcard Permissions in Task IAM Role",
                    "severity": "High",
                    "category": "IAM",
                    "resource": f"Task Definition: {task_def_family}",
                    "issue": "Task IAM role may contain overly permissive wildcard permissions",
                    "recommendation": (
                        "Review and restrict IAM permissions to follow principle of least privilege"
                    ),
                    "remediation_steps": [
                        "Review the IAM policy attached to the task role",
                        "Replace wildcard (*) permissions with specific resource ARNs",
                        "Use IAM Access Analyzer to identify unused permissions",
                    ],
                }
            )

        # Check for custom execution role (recommend managed policy)
        if execution_role_arn and "AmazonECSTaskExecutionRolePolicy" not in execution_role_arn:
            self.recommendations.append(
                {
                    "title": "Use Managed Execution Role Policy",
                    "severity": "Medium",
                    "category": "IAM",
                    "resource": f"Task Definition: {task_def_family}",
                    "issue": "Custom execution role may have unnecessary permissions",
                    "recommendation": (
                        "Use AWS managed AmazonECSTaskExecutionRolePolicy when possible"
                    ),
                    "remediation_steps": [
                        "Review the custom execution role permissions",
                        ("Consider using the AWS managed policy: AmazonECSTaskExecutionRolePolicy"),
                        ("Add additional permissions only if required for specific use cases"),
                    ],
                }
            )

        # Check for cross-account role usage
        if task_role_arn and ":role/" in task_role_arn:
            # Extract account ID from role ARN
            try:
                role_account = task_role_arn.split(":")[4]
                # Note: In a real implementation, you would compare with the current account ID
                # For now, we'll check if the account ID looks valid
                if role_account and len(role_account) == 12 and role_account.isdigit():
                    self.recommendations.append(
                        {
                            "title": "Review Cross-Account IAM Role Usage",
                            "severity": "Medium",
                            "category": "IAM",
                            "resource": f"Task Definition: {task_def_family}",
                            "issue": "Task role may be from a different AWS account",
                            "recommendation": (
                                "Verify cross-account role usage is intentional and "
                                "properly secured"
                            ),
                            "remediation_steps": [
                                (
                                    "Verify the trust relationship allows your account to assume "
                                    "the role"
                                ),
                                "Ensure the role has appropriate permissions for the task",
                                "Review CloudTrail logs for any unauthorized access attempts",
                            ],
                        }
                    )
            except (IndexError, ValueError):
                # Invalid ARN format, skip this check
                pass

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

    def _analyze_enhanced_cluster_security(
        self, container_instances: List[Dict[str, Any]], cluster_name: str
    ) -> None:
        """
        Analyze enhanced cluster security (ECS agent versions, connectivity, instance types).

        Args:
            container_instances: List of container instance data
            cluster_name: Name of the cluster
        """
        for instance in container_instances:
            instance_id = instance.get("ec2InstanceId", "unknown")

            # Check ECS agent version for known vulnerabilities
            version_info = instance.get("versionInfo", {})
            agent_version = version_info.get("agentVersion", "")

            if agent_version:
                try:
                    # Parse version (e.g., "1.68.2" -> [1, 68, 2])
                    version_parts = [int(x) for x in agent_version.split(".")]

                    # Flag versions older than 1.65.0 (versions with known security issues)
                    if len(version_parts) >= 2 and (
                        version_parts[0] < 1 or (version_parts[0] == 1 and version_parts[1] < 65)
                    ):
                        self.recommendations.append(
                            {
                                "title": "Critical ECS Agent Security Update Required",
                                "severity": "High",
                                "category": "Security",
                                "resource": f"Container Instance: {instance_id}",
                                "issue": (
                                    f"ECS agent version {agent_version} has known "
                                    "security vulnerabilities"
                                ),
                                "recommendation": (
                                    "Immediately update ECS agent to latest version to patch "
                                    "security vulnerabilities"
                                ),
                                "remediation_steps": [
                                    "Update the ECS agent on the container instance",
                                    "Consider using ECS-optimized AMIs with latest agent versions",
                                ],
                            }
                        )
                except (ValueError, IndexError):
                    # If version parsing fails, flag for investigation
                    self.recommendations.append(
                        {
                            "title": "Verify ECS Agent Version",
                            "severity": "Medium",
                            "category": "Security",
                            "resource": f"Container Instance: {instance_id}",
                            "issue": f"Cannot parse ECS agent version: {agent_version}",
                            "recommendation": (
                                "Verify ECS agent version and ensure it is up to date for security"
                            ),
                            "remediation_steps": [
                                "Check the ECS agent version manually",
                                "Update to a known stable version",
                            ],
                        }
                    )

            # Check for agent connectivity
            agent_connected = instance.get("agentConnected", False)
            if not agent_connected:
                self.recommendations.append(
                    {
                        "title": "ECS Agent Disconnected - Security Risk",
                        "severity": "High",
                        "category": "Security",
                        "resource": f"Container Instance: {instance_id}",
                        "issue": (
                            "ECS agent is disconnected, preventing security monitoring and updates"
                        ),
                        "recommendation": (
                            "Investigate and reconnect ECS agent to maintain security oversight"
                        ),
                        "remediation_steps": [
                            "Check network connectivity to ECS endpoints",
                            "Verify IAM permissions for the instance",
                            "Review CloudWatch logs for agent errors",
                        ],
                    }
                )

            # Check for legacy instance types with potential hardware vulnerabilities
            attributes = instance.get("attributes", [])
            instance_type_attr = next(
                (attr for attr in attributes if attr.get("name") == "ecs.instance-type"), None
            )
            if instance_type_attr:
                instance_type = instance_type_attr.get("value", "")
                # Flag instances from older generations with potential vulnerabilities
                if any(
                    old_gen in instance_type for old_gen in ["t1.", "m1.", "c1.", "m2.", "cr1."]
                ):
                    self.recommendations.append(
                        {
                            "title": "Legacy Instance Type Security Risk",
                            "severity": "Medium",
                            "category": "Security",
                            "resource": f"Container Instance: {instance_id}",
                            "issue": (
                                f"Instance type {instance_type} is from older generation with "
                                "potential hardware vulnerabilities"
                            ),
                            "recommendation": (
                                "Migrate to newer generation instance types with enhanced "
                                "security features"
                            ),
                            "remediation_steps": [
                                (
                                    "Plan migration to current generation instance types "
                                    "(t3, m5, c5, etc.)"
                                ),
                                "Test workloads on newer instance types",
                                "Update capacity providers or launch configurations",
                            ],
                        }
                    )

    def _analyze_capacity_providers(
        self, capacity_providers: List[Dict[str, Any]], cluster_name: str
    ) -> None:
        """
        Analyze capacity provider security configurations.

        Args:
            capacity_providers: List of capacity provider data
            cluster_name: Name of the cluster
        """
        for cp in capacity_providers:
            cp_name = cp.get("name", "unknown")

            # Check for capacity providers with security-relevant misconfigurations
            auto_scaling_group_provider = cp.get("autoScalingGroupProvider", {})
            if auto_scaling_group_provider:
                # Check if managed termination protection is disabled (security risk)
                managed_scaling = auto_scaling_group_provider.get("managedScaling", {})
                if managed_scaling.get("status") == "ENABLED":
                    termination_protection = auto_scaling_group_provider.get(
                        "managedTerminationProtection", "DISABLED"
                    )
                    if termination_protection == "DISABLED":
                        self.recommendations.append(
                            {
                                "title": "Enable Managed Termination Protection",
                                "severity": "Medium",
                                "category": "Security",
                                "resource": f"Capacity Provider: {cp_name}",
                                "issue": (
                                    "Managed termination protection is disabled, allowing "
                                    "uncontrolled instance termination"
                                ),
                                "recommendation": (
                                    "Enable managed termination protection to prevent "
                                    "unauthorized instance termination"
                                ),
                                "remediation_steps": [
                                    (
                                        "Update capacity provider with "
                                        "managedTerminationProtection=ENABLED"
                                    ),
                                    "Review auto-scaling policies for security implications",
                                ],
                            }
                        )

    def _analyze_task_definition_security(
        self, task_def: Dict[str, Any], cluster_name: str
    ) -> None:
        """
        Analyze task definition security configurations.

        Args:
            task_def: Task definition data
            cluster_name: Name of the cluster
        """
        task_family = task_def.get("family", "unknown")

        # Check task IAM role
        task_role_arn = task_def.get("taskRoleArn")
        if not task_role_arn:
            self.recommendations.append(
                {
                    "title": "Configure Task IAM Role",
                    "severity": "High",
                    "category": "IAM",
                    "resource": f"Task Definition: {task_family}",
                    "issue": "Missing task IAM role - containers will have no AWS API permissions",
                    "recommendation": (
                        "Configure task IAM role with minimal required permissions following "
                        "principle of least privilege"
                    ),
                    "remediation_steps": [
                        "Create an IAM role with necessary permissions for your application",
                        "Attach the role to the task definition using taskRoleArn parameter",
                        "Follow principle of least privilege when defining permissions",
                    ],
                }
            )

        # Check execution role
        execution_role_arn = task_def.get("executionRoleArn")
        if not execution_role_arn:
            self.recommendations.append(
                {
                    "title": "Configure Execution IAM Role",
                    "severity": "High",
                    "category": "IAM",
                    "resource": f"Task Definition: {task_family}",
                    "issue": (
                        "Missing execution IAM role - ECS agent cannot pull images or write logs"
                    ),
                    "recommendation": (
                        "Configure execution IAM role for ECS agent operations "
                        "(image pulling, logging, secrets)"
                    ),
                    "remediation_steps": [
                        "Create an IAM role with AmazonECSTaskExecutionRolePolicy",
                        "Attach the role to the task definition using executionRoleArn parameter",
                        "Add additional permissions if using Secrets Manager or Parameter Store",
                    ],
                }
            )

        # Check network mode
        network_mode = task_def.get("networkMode", "bridge")
        if network_mode == "host":
            self.recommendations.append(
                {
                    "title": "Avoid Host Network Mode",
                    "severity": "High",
                    "category": "Network",
                    "resource": f"Task Definition: {task_family}",
                    "issue": "Task uses host network mode, bypassing container network isolation",
                    "recommendation": (
                        "Use awsvpc network mode for better network isolation and security"
                    ),
                    "remediation_steps": [
                        "Change networkMode to 'awsvpc' in task definition",
                        "Update security groups and network configuration accordingly",
                        "Test application with new network mode",
                    ],
                }
            )

        # Check PID mode
        pid_mode = task_def.get("pidMode")
        if pid_mode == "host":
            self.recommendations.append(
                {
                    "title": "Avoid Host PID Mode",
                    "severity": "High",
                    "category": "Security",
                    "resource": f"Task Definition: {task_family}",
                    "issue": (
                        "Task uses host PID mode, allowing containers to see all host processes"
                    ),
                    "recommendation": "Remove pidMode or set to task for proper process isolation",
                    "remediation_steps": [
                        "Remove pidMode parameter from task definition",
                        "Or set pidMode to 'task' for proper isolation",
                        "Verify application doesn't require host PID access",
                    ],
                }
            )

        # Check IPC mode
        ipc_mode = task_def.get("ipcMode")
        if ipc_mode == "host":
            self.recommendations.append(
                {
                    "title": "Avoid Host IPC Mode",
                    "severity": "High",
                    "category": "Security",
                    "resource": f"Task Definition: {task_family}",
                    "issue": (
                        "Task uses host IPC mode, allowing containers to access host IPC resources"
                    ),
                    "recommendation": "Remove ipcMode or set to task for proper IPC isolation",
                    "remediation_steps": [
                        "Remove ipcMode parameter from task definition",
                        "Or set ipcMode to 'task' for proper isolation",
                        "Verify application doesn't require host IPC access",
                    ],
                }
            )

        # Check for privileged containers
        for container in task_def.get("containerDefinitions", []):
            container_name = container.get("name", "unknown")

            if container.get("privileged", False):
                self.recommendations.append(
                    {
                        "title": "Avoid Privileged Containers",
                        "severity": "Critical",
                        "category": "Security",
                        "resource": f"Container: {container_name}",
                        "issue": (
                            "Container runs in privileged mode with full access to host resources"
                        ),
                        "recommendation": (
                            "Remove privileged flag and use specific capabilities instead"
                        ),
                        "remediation_steps": [
                            "Set privileged to false in container definition",
                            "Use linuxParameters.capabilities to add only required capabilities",
                            "Review application requirements for privileged access",
                        ],
                    }
                )

    def _analyze_image_security(self, container: Dict[str, Any], task_family: str) -> None:
        """
        Analyze container image security.

        Args:
            container: Container definition data
            task_family: Task definition family name
        """
        container_name = container.get("name", "unknown")
        image = container.get("image", "")

        # Check if image is specified
        if not image:
            self.recommendations.append(
                {
                    "title": "Specify Container Image",
                    "severity": "High",
                    "category": "Security",
                    "resource": f"Container: {container_name}",
                    "issue": "No container image specified",
                    "recommendation": "Specify a valid container image from a trusted registry",
                    "remediation_steps": [
                        "Add image parameter to container definition",
                        "Use images from trusted registries (ECR, Docker Hub verified publishers)",
                        "Specify image with digest for immutability",
                    ],
                }
            )
            return

        # Check for 'latest' tag usage
        if image.endswith(":latest") or ":" not in image:
            self.recommendations.append(
                {
                    "title": "Avoid Using 'latest' Image Tag",
                    "severity": "Medium",
                    "category": "Security",
                    "resource": f"Container: {container_name}",
                    "issue": (
                        "Using 'latest' tag or no tag makes deployments unpredictable and "
                        "harder to audit"
                    ),
                    "recommendation": (
                        "Use specific version tags or image digests for reproducibility"
                    ),
                    "remediation_steps": [
                        "Tag images with specific versions (e.g., v1.2.3)",
                        "Or use image digest for immutability (e.g., @sha256:...)",
                        "Implement image tagging strategy in CI/CD pipeline",
                    ],
                }
            )

        # Check for ECR image scanning using regex for secure validation
        # ECR image format: {account-id}.dkr.ecr.{region}.amazonaws.com/{repo}:{tag}
        ecr_pattern = r"^\d+\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/"
        is_ecr_image = bool(re.match(ecr_pattern, image))

        if is_ecr_image:
            self.recommendations.append(
                {
                    "title": "Enable ECR Image Scanning",
                    "severity": "Medium",
                    "category": "Security",
                    "resource": f"Container: {container_name}",
                    "issue": "Ensure ECR image scanning is enabled for vulnerability detection",
                    "recommendation": (
                        "Enable ECR image scanning to detect vulnerabilities in container images"
                    ),
                    "remediation_steps": [
                        "Enable scan on push in ECR repository settings",
                        "Review scan findings regularly",
                        "Implement automated scanning in CI/CD pipeline",
                        "Set up alerts for critical vulnerabilities",
                    ],
                }
            )

    def _analyze_container_security(self, task_def: Dict[str, Any], cluster_name: str) -> None:
        """
        Analyze container security configurations.

        Args:
            task_def: Task definition data
            cluster_name: Name of the cluster
        """
        task_def_family = task_def.get("family", "unknown")
        containers = task_def.get("containerDefinitions", [])

        for container in containers:
            container_name = container.get("name", "unknown")

            # Check for privileged mode
            if container.get("privileged", False):
                self.recommendations.append(
                    {
                        "title": "Privileged Container Detected",
                        "severity": "Critical",
                        "category": "Security",
                        "resource": f"Task: {task_def_family}, Container: {container_name}",
                        "issue": "Container is running in privileged mode",
                        "recommendation": (
                            "Disable privileged mode unless absolutely necessary for the workload"
                        ),
                        "remediation_steps": [
                            "Remove 'privileged: true' from container definition",
                            "Use specific capabilities instead of privileged mode",
                            "Review security requirements and minimize permissions",
                        ],
                    }
                )

            # Check for root user
            user = container.get("user")
            if not user or user == "0" or user == "root":
                self.recommendations.append(
                    {
                        "title": "Container Running as Root User",
                        "severity": "High",
                        "category": "Security",
                        "resource": f"Task: {task_def_family}, Container: {container_name}",
                        "issue": "Container is running as root user",
                        "recommendation": (
                            "Configure container to run as non-root user for better security"
                        ),
                        "remediation_steps": [
                            "Add 'user' field with non-root UID (e.g., 'user: 1000')",
                            "Update Dockerfile to create and use non-root user",
                            "Test application with non-root permissions",
                        ],
                    }
                )

            # Check for read-only root filesystem
            if not container.get("readonlyRootFilesystem", False):
                self.recommendations.append(
                    {
                        "title": "Read-Only Root Filesystem Not Enabled",
                        "severity": "Medium",
                        "category": "Security",
                        "resource": f"Task: {task_def_family}, Container: {container_name}",
                        "issue": "Container root filesystem is writable",
                        "recommendation": (
                            "Enable read-only root filesystem to prevent runtime modifications"
                        ),
                        "remediation_steps": [
                            "Set 'readonlyRootFilesystem: true' in container definition",
                            "Use volume mounts for directories that need write access",
                            "Test application with read-only filesystem",
                        ],
                    }
                )

            # Check for Linux capabilities
            linux_params = container.get("linuxParameters", {})
            capabilities_add = linux_params.get("capabilities", {}).get("add", [])
            if capabilities_add:
                # Flag dangerous capabilities
                dangerous_caps = ["SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "SYS_MODULE"]
                found_dangerous = [cap for cap in capabilities_add if cap in dangerous_caps]
                if found_dangerous:
                    self.recommendations.append(
                        {
                            "title": "Dangerous Linux Capabilities Granted",
                            "severity": "High",
                            "category": "Security",
                            "resource": f"Task: {task_def_family}, Container: {container_name}",
                            "issue": (
                                f"Container has dangerous capabilities: "
                                f"{', '.join(found_dangerous)}"
                            ),
                            "recommendation": (
                                "Remove dangerous capabilities unless absolutely required"
                            ),
                            "remediation_steps": [
                                "Review if capabilities are truly needed",
                                "Use least privilege principle",
                                "Consider alternative approaches without elevated capabilities",
                            ],
                        }
                    )

    def _analyze_container_runtime_security(
        self, task_def: Dict[str, Any], cluster_name: str
    ) -> None:
        """
        Analyze container runtime security configurations.

        Args:
            task_def: Task definition data
            cluster_name: Name of the cluster
        """
        task_def_family = task_def.get("family", "unknown")
        containers = task_def.get("containerDefinitions", [])

        for container in containers:
            container_name = container.get("name", "unknown")
            linux_params = container.get("linuxParameters", {})

            # Check for init process
            if not linux_params.get("initProcessEnabled", False):
                self.recommendations.append(
                    {
                        "title": "Init Process Not Enabled",
                        "severity": "Low",
                        "category": "Security",
                        "resource": f"Task: {task_def_family}, Container: {container_name}",
                        "issue": "Init process is not enabled for proper signal handling",
                        "recommendation": (
                            "Enable init process to handle zombie processes and signals properly"
                        ),
                        "remediation_steps": [
                            "Set 'initProcessEnabled: true' in linuxParameters",
                            "Ensures proper cleanup of child processes",
                        ],
                    }
                )

            # Check for shared process namespace
            if linux_params.get("sharedMemorySize"):
                self.recommendations.append(
                    {
                        "title": "Review Shared Memory Configuration",
                        "severity": "Medium",
                        "category": "Security",
                        "resource": f"Task: {task_def_family}, Container: {container_name}",
                        "issue": "Shared memory is configured",
                        "recommendation": (
                            "Ensure shared memory size is appropriate and doesn't pose "
                            "security risks"
                        ),
                        "remediation_steps": [
                            "Review shared memory requirements",
                            "Set minimum necessary size",
                            "Monitor memory usage",
                        ],
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

            # Collect cluster data
            cluster_data = await adapter.collect_cluster_data(cluster_name, region)

            # Collect task definition data for IAM analysis
            task_def_data = await adapter.collect_task_definitions(cluster_name, region)

            # Collect container instance data for enhanced security analysis
            container_instance_data = await adapter.collect_container_instances(
                cluster_name, region
            )

            # Collect capacity provider data for security analysis
            capacity_provider_data = await adapter.collect_capacity_providers(cluster_name, region)

            # Combine data for analysis
            combined_data = {
                **cluster_data,
                "task_definitions": task_def_data.get("task_definitions", []),
                "container_instances": container_instance_data.get("container_instances", []),
                "capacity_providers": capacity_provider_data.get("capacity_providers", []),
            }

            # Analyze data
            analysis_result = analyzer.analyze(combined_data)
            results.append(analysis_result)

    # Aggregate results
    total_recommendations = sum(len(r.get("recommendations", [])) for r in results)

    return {
        "status": "success",
        "total_clusters_analyzed": len(results),
        "total_recommendations": total_recommendations,
        "results": results,
    }
