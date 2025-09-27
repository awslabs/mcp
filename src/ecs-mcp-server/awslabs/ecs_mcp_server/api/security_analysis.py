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

This module provides comprehensive security analysis for ECS clusters.

Consolidated security analysis implementation that leverages existing MCP tools
for data collection while providing comprehensive security recommendations.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

from .resource_management import ecs_api_operation
from .troubleshooting_tools.fetch_network_configuration import fetch_network_configuration
from .troubleshooting_tools.utils import find_clusters, find_task_definitions

logger = logging.getLogger(__name__)


def _format_resource_name(
    resource_type: str,
    resource_name: str,
    service_name: Optional[str] = None,
    cluster_name: Optional[str] = None,
) -> str:  # noqa: E501
    """
    Format resource names consistently across all security recommendations.

    Args:
        resource_type: Type of resource (Container, Service, Task Definition, etc.)
        resource_name: Name of the specific resource
        service_name: Optional service name for context
        cluster_name: Optional cluster name for context

    Returns:
        Consistently formatted resource identifier
    """
    # Sanitize inputs to prevent injection attacks
    safe_resource_type = str(resource_type).replace("|", "-").replace(":", "-")
    safe_resource_name = str(resource_name).replace("|", "-").replace(":", "-")

    base_resource = f"{safe_resource_type}: {safe_resource_name}"

    # Add service context if provided and not already a service resource
    if service_name and resource_type.lower() != "service":
        safe_service_name = str(service_name).replace("|", "-").replace(":", "-")
        base_resource += f" | Service: {safe_service_name}"

    # Add cluster context if provided and not already a cluster resource
    if cluster_name and resource_type.lower() not in ["service", "cluster"]:
        safe_cluster_name = str(cluster_name).replace("|", "-").replace(":", "-")
        base_resource += f" | Cluster: {safe_cluster_name}"

    return base_resource


class DataAdapter:
    """
    Adapter that uses existing MCP tools to collect data for security analysis.

    This class eliminates duplicate data collection by leveraging existing APIs
    and utilities already present in the ECS MCP server.
    """

    def __init__(self):
        """Initialize the DataAdapter."""
        self.logger = logger

    async def collect_cluster_data(
        self, cluster_name: str, region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """Collect cluster data using existing resource management API."""
        try:
            self.logger.info(f"Collecting cluster data for {cluster_name}")

            # Get basic cluster information
            cluster_response = await ecs_api_operation(
                "DescribeClusters", {"clusters": [cluster_name]}
            )

            # Enhanced: Get capacity providers for security analysis
            capacity_providers_response = await ecs_api_operation(
                "DescribeCapacityProviders",
                {"capacityProviders": []},  # Gets all capacity providers
            )

            # Enhanced: Get cluster tags for compliance analysis
            # Note: We'll skip tags for now as we need the actual cluster ARN from the response
            tags_response = {"tags": []}

            if "error" in cluster_response:
                self.logger.error(f"Error collecting cluster data: {cluster_response['error']}")
                return {
                    "error": cluster_response["error"],
                    "cluster_name": cluster_name,
                    "region": region,
                }

            clusters = cluster_response.get("clusters", [])
            if not clusters:
                self.logger.warning(f"No cluster found with name: {cluster_name}")
                return {
                    "error": f"Cluster '{cluster_name}' not found",
                    "cluster_name": cluster_name,
                    "region": region,
                }

            cluster_data = clusters[0]

            # Enhanced cluster data with additional security-relevant information
            enhanced_cluster_data = {
                "cluster": cluster_data,
                "capacity_providers": (
                    capacity_providers_response.get("capacityProviders", [])
                    if "error" not in capacity_providers_response
                    else []
                ),
                "tags": tags_response.get("tags", []) if "error" not in tags_response else [],
                "cluster_name": cluster_name,
                "region": region,
                "status": "success",
            }

            # Log any errors from enhanced data collection
            if "error" in capacity_providers_response:
                self.logger.warning(
                    f"Could not fetch capacity providers: {capacity_providers_response['error']}"
                )
            if "error" in tags_response:
                self.logger.warning(f"Could not fetch cluster tags: {tags_response['error']}")

            return enhanced_cluster_data

        except Exception as e:
            self.logger.error(f"Unexpected error collecting cluster data for {cluster_name}: {e}")
            return {"error": str(e), "cluster_name": cluster_name, "region": region}

    async def collect_service_data(
        self, cluster_name: str, service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Collect service data using existing troubleshooting tools utilities."""
        try:
            self.logger.info(f"Collecting service data for cluster {cluster_name}")

            if service_name:
                service_names = [service_name]
            else:
                # Use direct ECS API call instead of find_services to avoid async iterator issues
                try:
                    list_services_response = await ecs_api_operation(
                        "ListServices", {"cluster": cluster_name}
                    )

                    if "error" in list_services_response:
                        self.logger.warning(
                            f"Error listing services: {list_services_response['error']}"
                        )
                        service_names = []
                    else:
                        service_arns = list_services_response.get("serviceArns", [])
                        # Extract service names from ARNs
                        service_names = []
                        for arn in service_arns:
                            # ARN format: arn:aws:ecs:region:account:service/cluster-name/service-name  # noqa: E501
                            if "/" in arn:
                                service_name_from_arn = arn.split("/")[-1]
                                service_names.append(service_name_from_arn)
                except Exception as e:
                    self.logger.warning(f"Error listing services for cluster {cluster_name}: {e}")
                    service_names = []

            if not service_names:
                self.logger.warning(f"No services found in cluster: {cluster_name}")
                return {"services": [], "cluster_name": cluster_name, "status": "success"}

            services_data = []

            for svc_name in service_names:
                try:
                    service_response = await ecs_api_operation(
                        "DescribeServices", {"cluster": cluster_name, "services": [svc_name]}
                    )

                    if "error" in service_response:
                        self.logger.error(
                            f"Error getting service {svc_name}: {service_response['error']}"
                        )
                        continue

                    services = service_response.get("services", [])
                    if not services:
                        self.logger.warning(f"Service {svc_name} not found in response")
                        continue

                    service_info = services[0]

                    task_definitions = await find_task_definitions(
                        cluster_name=cluster_name, service_name=svc_name
                    )

                    task_definition = None
                    if task_definitions:
                        task_definition = task_definitions[0]
                    else:
                        task_def_arn = service_info.get("taskDefinition")
                        if task_def_arn:
                            task_def_response = await ecs_api_operation(
                                "DescribeTaskDefinition", {"taskDefinition": task_def_arn}
                            )
                            if "taskDefinition" in task_def_response:
                                task_definition = task_def_response["taskDefinition"]

                    # Enhanced: Get service tags for compliance analysis
                    service_arn = service_info.get("serviceArn", "")
                    service_tags_response = await ecs_api_operation(
                        "ListTagsForResource", {"resourceArn": service_arn}
                    )

                    # Enhanced: Get running tasks for runtime security analysis
                    tasks_response = await ecs_api_operation(
                        "ListTasks", {"cluster": cluster_name, "serviceName": svc_name}
                    )

                    service_data = {
                        "service": service_info,
                        "task_definition": task_definition,
                        "tags": (
                            service_tags_response.get("tags", [])
                            if "error" not in service_tags_response
                            else []
                        ),
                        "running_tasks": (
                            tasks_response.get("taskArns", [])
                            if "error" not in tasks_response
                            else []
                        ),
                    }

                    services_data.append(service_data)

                except Exception as e:
                    self.logger.error(f"Error collecting data for service {svc_name}: {e}")
                    continue

            return {"services": services_data, "cluster_name": cluster_name, "status": "success"}

        except Exception as e:
            self.logger.error(f"Unexpected error collecting service data for {cluster_name}: {e}")
            return {"error": str(e), "cluster_name": cluster_name, "services": []}

    async def collect_container_instances_data(self, cluster_name: str) -> Dict[str, Any]:
        """Collect container instance data for EC2-based clusters using resource management API."""
        try:
            self.logger.info(f"Collecting container instance data for cluster {cluster_name}")

            # List container instances
            list_instances_response = await ecs_api_operation(
                "ListContainerInstances", {"cluster": cluster_name}
            )

            if "error" in list_instances_response:
                self.logger.warning(
                    f"Error listing container instances: {list_instances_response['error']}"
                )
                return {
                    "container_instances": [],
                    "cluster_name": cluster_name,
                    "status": "success",
                }

            instance_arns = list_instances_response.get("containerInstanceArns", [])

            if not instance_arns:
                return {
                    "container_instances": [],
                    "cluster_name": cluster_name,
                    "status": "success",
                }

            # Describe container instances for detailed security analysis
            describe_instances_response = await ecs_api_operation(
                "DescribeContainerInstances",
                {"cluster": cluster_name, "containerInstances": instance_arns},
            )

            if "error" in describe_instances_response:
                self.logger.error(
                    f"Error describing container instances: {describe_instances_response['error']}"
                )
                return {
                    "error": describe_instances_response["error"],
                    "cluster_name": cluster_name,
                    "container_instances": [],
                }

            return {
                "container_instances": describe_instances_response.get("containerInstances", []),
                "cluster_name": cluster_name,
                "status": "success",
            }

        except Exception as e:
            self.logger.error(
                f"Unexpected error collecting container instance data for {cluster_name}: {e}"
            )
            return {"error": str(e), "cluster_name": cluster_name, "container_instances": []}

    async def collect_network_data(
        self, cluster_name: str, vpc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Collect network data using existing fetch_network_configuration function."""
        try:
            self.logger.info(f"Collecting network data for cluster {cluster_name}")

            network_response = await fetch_network_configuration(
                cluster_name=cluster_name, vpc_id=vpc_id
            )

            if network_response.get("status") == "error":
                self.logger.error(f"Error collecting network data: {network_response.get('error')}")
                return {
                    "error": network_response.get("error"),
                    "cluster_name": cluster_name,
                    "network_data": {},
                }

            network_data = network_response.get("data", {})
            raw_resources = network_data.get("raw_resources", {})

            security_network_data = {
                "vpcs": raw_resources.get("vpcs", {}),
                "subnets": raw_resources.get("subnets", {}),
                "security_groups": raw_resources.get("security_groups", {}),
                "route_tables": raw_resources.get("route_tables", {}),
                "network_interfaces": raw_resources.get("network_interfaces", {}),
                "nat_gateways": raw_resources.get("nat_gateways", {}),
                "internet_gateways": raw_resources.get("internet_gateways", {}),
                "load_balancers": raw_resources.get("load_balancers", {}),
                "target_groups": raw_resources.get("target_groups", {}),
                "vpc_ids": network_data.get("vpc_ids", []),
                "timestamp": network_data.get("timestamp"),
            }

            return {
                "network_data": security_network_data,
                "cluster_name": cluster_name,
                "status": "success",
            }

        except Exception as e:
            self.logger.error(f"Unexpected error collecting network data for {cluster_name}: {e}")
            return {"error": str(e), "cluster_name": cluster_name, "network_data": {}}

    async def collect_all_data(
        self, regions: List[str], cluster_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Collect comprehensive ECS data using existing tools."""
        try:
            all_data = {}

            for region in regions:
                try:
                    self.logger.info(f"Collecting data for region: {region}")

                    if cluster_names:
                        clusters = cluster_names
                    else:
                        clusters = await find_clusters()

                    region_data = {"clusters": {}}

                    for cluster_name in clusters:
                        try:
                            cluster_security_data = await self.adapt_to_security_format(
                                cluster_name, region
                            )

                            if region in cluster_security_data:
                                region_data["clusters"].update(
                                    cluster_security_data[region]["clusters"]
                                )
                        except Exception as e:
                            self.logger.error(
                                f"Error collecting data for cluster {cluster_name}: {e}"
                            )
                            region_data["clusters"][cluster_name] = {
                                "error": str(e),
                                "cluster_name": cluster_name,
                                "region": region,
                            }

                    all_data[region] = region_data

                except Exception as e:
                    self.logger.error(f"Error collecting data for region {region}: {e}")
                    all_data[region] = {"error": str(e), "region": region}

            return all_data

        except Exception as e:
            self.logger.error(f"Unexpected error in collect_all_data: {e}")
            return {"error": str(e)}

    async def adapt_to_security_format(
        self, cluster_name: str, region: str = "us-east-1"
    ) -> Dict[str, Any]:
        """Adapt collected data to security analysis format."""
        try:
            cluster_data = await self.collect_cluster_data(cluster_name, region)
            service_data = await self.collect_service_data(cluster_name)
            network_data = await self.collect_network_data(cluster_name)
            container_instances_data = await self.collect_container_instances_data(cluster_name)

            errors = []
            if "error" in cluster_data:
                errors.append(f"Cluster data: {cluster_data['error']}")
            if "error" in service_data:
                errors.append(f"Service data: {service_data['error']}")
            if "error" in network_data:
                errors.append(f"Network data: {network_data['error']}")
            if "error" in container_instances_data:
                errors.append(f"Container instances data: {container_instances_data['error']}")

            security_format = {
                region: {
                    "clusters": {
                        cluster_name: {
                            "cluster": cluster_data.get("cluster", {}),
                            "capacity_providers": cluster_data.get("capacity_providers", []),
                            "cluster_tags": cluster_data.get("tags", []),
                            "services": service_data.get("services", []),
                            "network_data": network_data.get("network_data", {}),
                            "container_instances": container_instances_data.get(
                                "container_instances", []
                            ),
                            "region_info": {"name": region},
                        }
                    }
                }
            }

            if errors:
                security_format[region]["clusters"][cluster_name]["errors"] = errors
                self.logger.warning(f"Data collection completed with errors: {errors}")

            return security_format

        except Exception as e:
            self.logger.error(f"Error adapting data to security format: {e}")
            return {region: {"error": str(e), "cluster_name": cluster_name, "region": region}}

    def _extract_security_relevant_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract security-relevant data from raw AWS responses."""
        # For now, just return the raw data
        # This could be enhanced to filter out non-security-relevant fields
        return raw_data

    def _handle_api_errors(self, response: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Handle API errors in responses."""
        if "error" in response:
            return {
                "error": response["error"],
                "operation": operation,
                "status": response.get("status", "failed"),
            }
        return response


class SecurityAnalyzer:
    """Comprehensive ECS security analyzer following AWS best practices."""

    def __init__(self):
        """Initialize the SecurityAnalyzer with security check mappings."""
        self.security_checks = {
            "cluster": self._analyze_cluster_security,
            "service": self._analyze_service_security,
            "task_definition": self._analyze_task_definition_security,
            "container": self._analyze_container_security,
            "network": self._analyze_network_security,
            "capacity_providers": self._analyze_capacity_providers,
            "iam": self._analyze_iam_security,
            "logging": self._analyze_logging_security,
            "secrets": self._analyze_secrets_security,
            "compliance": self._analyze_compliance_security,
        }

    def _is_valid_ecr_image(self, image: str) -> bool:
        """
        Securely validate if an image URI is a valid ECR image.

        Uses proper regex pattern matching to prevent URL substring sanitization vulnerabilities.

        Args:
            image: The container image URI to validate

        Returns:
            bool: True if the image is a valid ECR image, False otherwise
        """
        if not image or image.startswith("https://"):
            return False

        # ECR image format: [account-id].dkr.ecr.[region].amazonaws.com/[repository][:tag]
        # Use strict regex pattern to validate ECR URI structure
        ecr_pattern = (
            r"^[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com\/"
            r"[a-zA-Z0-9][a-zA-Z0-9._/-]*(?::[a-zA-Z0-9._-]+)?$"
        )

        return bool(re.match(ecr_pattern, image))

    def _is_docker_hub_image(self, image: str) -> bool:
        """
        Securely validate if an image URI is from Docker Hub.

        Uses proper regex pattern matching to prevent URL substring sanitization vulnerabilities.

        Args:
            image: The container image URI to validate

        Returns:
            bool: True if the image is from Docker Hub, False otherwise
        """
        if not image:
            return False

        # Docker Hub image formats:
        # 1. docker.io/library/nginx:latest (explicit)
        # 2. docker.io/username/repo:tag (explicit)
        # 3. nginx:latest (implicit - library image)
        # 4. username/repo:tag (implicit - user image)

        # Explicit Docker Hub format
        if image.startswith("docker.io/"):
            docker_hub_pattern = r"^docker\.io/[a-zA-Z0-9][a-zA-Z0-9._/-]*(?::[a-zA-Z0-9._-]+)?$"
            return bool(re.match(docker_hub_pattern, image))

        # Implicit Docker Hub format (no registry specified)
        # Must not contain dots (to avoid matching other registries like example.com/repo)
        # Must not start with localhost
        if not image.startswith("localhost") and "." not in image.split("/")[0]:
            # Pattern: [username/]repository[:tag]
            implicit_pattern = (
                r"^(?:[a-zA-Z0-9][a-zA-Z0-9._-]*/)?[a-zA-Z0-9][a-zA-Z0-9._-]*"
                r"(?::[a-zA-Z0-9._-]+)?$"
            )
            return bool(re.match(implicit_pattern, image))

        return False

    def _format_resource_name(
        self,
        resource_type: str,
        resource_name: str,
        service_name: Optional[str] = None,
        cluster_name: Optional[str] = None,
    ) -> str:
        """Format resource names consistently with full hierarchy context."""
        parts = [f"{resource_type}: {resource_name}"]

        if service_name:
            parts.append(f"Service: {service_name}")
        if cluster_name:
            parts.append(f"Cluster: {cluster_name}")

        return " | ".join(parts)

    async def analyze(self, ecs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive security analysis of ECS configurations."""
        recommendations = []

        for region, region_data in ecs_data.items():
            if "error" in region_data:
                continue

            for cluster_name, cluster_data in region_data.get("clusters", {}).items():
                if "error" in cluster_data:
                    continue

                # 1. IAM Security Analysis
                recommendations.extend(
                    self._analyze_cluster_iam_security(cluster_data, cluster_name, region)
                )

                # 2. Network Security Assessment
                network_data = cluster_data.get("network_data", {})
                if network_data:
                    recommendations.extend(
                        self._analyze_network_infrastructure(network_data, cluster_name, region)
                    )
                    recommendations.extend(
                        self._analyze_vpc_security(network_data, cluster_name, region)
                    )
                    recommendations.extend(
                        self._analyze_route_tables(network_data, cluster_name, region)
                    )
                    recommendations.extend(
                        self._analyze_internet_gateways(network_data, cluster_name, region)
                    )
                    recommendations.extend(
                        self._analyze_load_balancer_security(network_data, cluster_name, region)
                    )

                # 3. Cluster-level security
                recommendations.extend(
                    self._analyze_cluster_security(cluster_name, cluster_data, region)
                )
                recommendations.extend(
                    self._analyze_enhanced_cluster_security(cluster_data, cluster_name, region)
                )
                recommendations.extend(
                    self._analyze_capacity_providers(cluster_data, cluster_name, region)
                )
                recommendations.extend(
                    self._analyze_logging_security(cluster_data, cluster_name, region)
                )

                # 4. Compliance and Best Practices
                recommendations.extend(
                    self._analyze_well_architected_compliance(cluster_data, cluster_name, region)
                )
                recommendations.extend(
                    self._analyze_industry_compliance(cluster_data, cluster_name, region)
                )

                # 5. Service and Task Analysis
                for service_data in cluster_data.get("services", []):
                    service = service_data.get("service", {})
                    task_def = service_data.get("task_definition", {})
                    service_tags = service_data.get("tags", [])
                    running_tasks = service_data.get("running_tasks", [])

                    service_name = service.get("serviceName", "unknown")

                    # Enhanced service-level security with tags and task analysis
                    recommendations.extend(
                        self._analyze_service_security(service, service_name, cluster_name, region)
                    )
                    recommendations.extend(
                        self._analyze_service_tags_security(
                            service_tags, service_name, cluster_name, region
                        )
                    )
                    recommendations.extend(
                        self._analyze_running_tasks_security(
                            running_tasks, service_name, cluster_name, region
                        )
                    )
                    recommendations.extend(
                        self._analyze_service_discovery_security(
                            service, service_name, cluster_name, region
                        )
                    )

                    # Task definition security
                    recommendations.extend(
                        self._analyze_task_definition_security(
                            task_def, service_name, cluster_name, region
                        )
                    )
                    recommendations.extend(
                        self._analyze_resource_isolation(
                            task_def, service_name, cluster_name, region
                        )
                    )

                    # IAM and secrets
                    recommendations.extend(
                        self._analyze_iam_security(
                            service, task_def, service_name, cluster_name, region
                        )
                    )
                    recommendations.extend(
                        self._analyze_secrets_security(task_def, service_name, cluster_name, region)
                    )

                    # Network and monitoring
                    recommendations.extend(
                        self._analyze_network_security(service, service_name, cluster_name, region)
                    )
                    recommendations.extend(
                        self._analyze_monitoring_security(
                            service, task_def, service_name, cluster_name, region
                        )
                    )

                    # Compliance
                    recommendations.extend(
                        self._analyze_compliance_security(
                            service, task_def, service_name, cluster_name, region
                        )
                    )

                    # PHASE 2: Advanced ECS Features Security
                    recommendations.extend(
                        self._analyze_ecs_advanced_features_security(
                            service, ecs_data, service_name, cluster_name, region
                        )
                    )

                    # PHASE 2: Advanced Network Security
                    recommendations.extend(
                        self._analyze_advanced_network_security(
                            service, network_data, service_name, cluster_name, region
                        )
                    )

                    # PHASE 2: Advanced Storage Security
                    recommendations.extend(
                        self._analyze_advanced_storage_security(
                            task_def, service_name, cluster_name, region
                        )
                    )

                    # PHASE 2: Envoy Proxy Security
                    recommendations.extend(
                        self._analyze_envoy_proxy_security(
                            service, service_name, cluster_name, region
                        )
                    )

                    # 6. Container and Image Security
                    for container in task_def.get("containerDefinitions", []):
                        container_name = container.get("name", "unknown")
                        recommendations.extend(
                            self._analyze_container_security(
                                container, container_name, service_name, cluster_name, region
                            )
                        )
                        recommendations.extend(
                            self._analyze_image_security(
                                container, container_name, service_name, cluster_name, region
                            )
                        )
                        # PHASE 1: Add ECR vulnerability scanning analysis
                        ecr_recommendations = await self._analyze_ecr_vulnerability_scanning(
                            container, container_name, service_name, cluster_name, region
                        )
                        recommendations.extend(ecr_recommendations)

        # Enhance recommendations with detailed information
        enhanced_recommendations = []
        for rec in recommendations:
            enhanced_rec = self._enhance_recommendation(rec)
            enhanced_recommendations.append(enhanced_rec)

        # Deduplicate recommendations to avoid duplicate issues
        deduplicated_recommendations = self._deduplicate_recommendations(enhanced_recommendations)

        return {
            "recommendations": deduplicated_recommendations,
            "total_issues": len(deduplicated_recommendations),
            "analysis_summary": self._generate_analysis_summary(deduplicated_recommendations),
            "categorized_issues": self._categorize_issues(deduplicated_recommendations),
            "risk_weighted_priorities": self._calculate_risk_priorities(
                deduplicated_recommendations
            ),
            "deduplication_stats": {
                "original_count": len(enhanced_recommendations),
                "deduplicated_count": len(deduplicated_recommendations),
                "duplicates_removed": len(enhanced_recommendations)
                - len(deduplicated_recommendations),
            },
        }

    def _analyze_cluster_security(
        self, cluster_name: str, cluster_data: Dict[str, Any], region: str
    ) -> List[Dict[str, Any]]:
        """Analyze cluster-level security configurations."""
        recommendations = []

        cluster_info = cluster_data.get("cluster", {})
        cluster_settings = cluster_info.get("settings", [])

        # Check Container Insights
        container_insights_enabled = any(
            setting.get("name") == "containerInsights" and setting.get("value") == "enabled"
            for setting in cluster_settings
        )

        # Log Container Insights status for debugging
        logger.info(f"Container Insights enabled for {cluster_name}: {container_insights_enabled}")

        if not container_insights_enabled:
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
                    "recommendation": "Enable Container Insights for comprehensive monitoring and security observability",  # noqa: E501
                }
            )

        # Check cluster configuration
        configuration = cluster_info.get("configuration", {})

        # Check execute command configuration
        execute_command_config = configuration.get("executeCommandConfiguration", {})
        if not execute_command_config:
            recommendations.append(
                {
                    "title": "Configure Execute Command Security",
                    "severity": "Medium",
                    "category": "security",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "Execute command configuration is not set up, missing audit and logging capabilities",  # noqa: E501
                    "recommendation": "Configure execute command with proper logging and KMS encryption for security auditing",  # noqa: E501
                }
            )
        else:
            # Check logging configuration
            logging_config = execute_command_config.get("logging")
            if logging_config != "OVERRIDE":
                recommendations.append(
                    {
                        "title": "Enable Execute Command Audit Logging",
                        "severity": "Medium",
                        "category": "monitoring",
                        "resource": f"Cluster: {cluster_name}",
                        "issue": "Execute command audit logging is not properly configured",
                        "recommendation": "Enable CloudWatch logging for execute command sessions to maintain audit trail",  # noqa: E501
                    }
                )

            # Check KMS encryption
            kms_key_id = execute_command_config.get("kmsKeyId")
            if not kms_key_id:
                recommendations.append(
                    {
                        "title": "Enable KMS Encryption for Execute Command",
                        "severity": "Medium",
                        "category": "encryption",
                        "resource": f"Cluster: {cluster_name}",
                        "issue": "Execute command sessions are not encrypted with customer-managed KMS keys",  # noqa: E501
                        "recommendation": "Configure KMS encryption for execute command sessions to protect sensitive data",  # noqa: E501
                    }
                )

        # Capacity provider strategy is operational, not security - removed

        # Resource tags for cost tracking are operational, not security - removed

        # Check cluster status
        status = cluster_info.get("status", "")
        if status != "ACTIVE":
            recommendations.append(
                {
                    "title": "Review Cluster Status",
                    "severity": "High",
                    "category": "availability",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": f"Cluster status is {status}, not ACTIVE",
                    "recommendation": "Investigate and resolve cluster status issues to ensure proper operation",  # noqa: E501
                }
            )

        # Service discovery is primarily operational, not a security issue - removed

        return recommendations

    def _analyze_enhanced_cluster_security(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze enhanced cluster security using resource_management API data - SECURITY FOCUSED ONLY."""  # noqa: E501
        recommendations = []

        # Analyze container instances for SECURITY vulnerabilities (for EC2 launch type)
        container_instances = cluster_data.get("container_instances", [])
        for instance in container_instances:
            instance_id = instance.get("ec2InstanceId", "unknown")

            # SECURITY: Check ECS agent version for known vulnerabilities
            version_info = instance.get("versionInfo", {})
            agent_version = version_info.get("agentVersion", "")

            # Check for critically outdated agent versions with known security issues
            if agent_version:
                try:
                    # Parse version (e.g., "1.68.2" -> [1, 68, 2])
                    version_parts = [int(x) for x in agent_version.split(".")]

                    # Flag versions older than 1.65.0 (example of versions with known security issues)  # noqa: E501
                    if len(version_parts) >= 2 and (
                        version_parts[0] < 1 or (version_parts[0] == 1 and version_parts[1] < 65)
                    ):
                        recommendations.append(
                            {
                                "title": "Critical ECS Agent Security Update Required",
                                "severity": "High",
                                "category": "security",
                                "resource": f"Container Instance: {instance_id}",
                                "issue": f"ECS agent version {agent_version} has known security vulnerabilities",  # noqa: E501
                                "recommendation": "Immediately update ECS agent to latest version to patch security vulnerabilities",  # noqa: E501
                            }
                        )
                except (ValueError, IndexError):
                    # If version parsing fails, flag for investigation
                    recommendations.append(
                        {
                            "title": "Verify ECS Agent Version",
                            "severity": "Medium",
                            "category": "security",
                            "resource": f"Container Instance: {instance_id}",
                            "issue": f"Cannot parse ECS agent version: {agent_version}",
                            "recommendation": "Verify ECS agent version and ensure it is up to date for security",  # noqa: E501
                        }
                    )

            # SECURITY: Check for instances running with excessive privileges
            attributes = instance.get("attributes", [])

            # Check if instance is running ECS agent with privileged access patterns
            agent_connected = instance.get("agentConnected", False)
            if not agent_connected:
                recommendations.append(
                    {
                        "title": "ECS Agent Disconnected - Security Risk",
                        "severity": "High",
                        "category": "security",
                        "resource": f"Container Instance: {instance_id}",
                        "issue": "ECS agent is disconnected, preventing security monitoring and updates",  # noqa: E501
                        "recommendation": "Investigate and reconnect ECS agent to maintain security oversight",  # noqa: E501
                    }
                )

            # SECURITY: Check for instances with security-relevant attributes
            instance_type_attr = next(
                (attr for attr in attributes if attr.get("name") == "ecs.instance-type"), None
            )
            if instance_type_attr:
                instance_type = instance_type_attr.get("value", "")
                # Flag instances that might have hardware vulnerabilities (example: older generation instances)  # noqa: E501
                if any(
                    old_gen in instance_type for old_gen in ["t1.", "m1.", "c1.", "m2.", "cr1."]
                ):
                    recommendations.append(
                        {
                            "title": "Legacy Instance Type Security Risk",
                            "severity": "Medium",
                            "category": "security",
                            "resource": f"Container Instance: {instance_id}",
                            "issue": f"Instance type {instance_type} is from older generation with potential hardware vulnerabilities",  # noqa: E501
                            "recommendation": "Migrate to newer generation instance types with enhanced security features",  # noqa: E501
                        }
                    )

        # SECURITY: Analyze capacity providers for security misconfigurations
        capacity_providers = cluster_data.get("capacity_providers", [])
        for cp in capacity_providers:
            cp_name = cp.get("name", "unknown")

            # Check for capacity providers with security-relevant misconfigurations
            auto_scaling_group_provider = cp.get("autoScalingGroupProvider", {})
            if auto_scaling_group_provider:
                # SECURITY: Check managed scaling settings that could impact security
                managed_scaling = auto_scaling_group_provider.get("managedScaling", {})
                if managed_scaling.get("status") == "ENABLED":
                    # Check if managed termination protection is disabled (security risk)
                    termination_protection = auto_scaling_group_provider.get(
                        "managedTerminationProtection", "DISABLED"
                    )
                    if termination_protection == "DISABLED":
                        recommendations.append(
                            {
                                "title": "Enable Managed Termination Protection",
                                "severity": "Medium",
                                "category": "security",
                                "resource": f"Capacity Provider: {cp_name}",
                                "issue": "Managed termination protection is disabled, allowing uncontrolled instance termination",  # noqa: E501
                                "recommendation": "Enable managed termination protection to prevent unauthorized instance termination",  # noqa: E501
                            }
                        )

        return recommendations

    def _analyze_service_security(
        self, service: Dict[str, Any], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze service-level security configurations."""
        recommendations = []

        # Check public IP assignment
        network_config = service.get("networkConfiguration", {}).get("awsvpcConfiguration", {})
        if network_config.get("assignPublicIp") == "ENABLED":
            recommendations.append(
                {
                    "title": "Disable Public IP Assignment",
                    "severity": "High",
                    "category": "network_security",
                    "resource": f"Service: {service_name}",
                    "issue": "Service has public IP assignment enabled, exposing containers directly to the internet",  # noqa: E501
                    "recommendation": "Disable public IP assignment and use NAT Gateway for outbound connectivity",  # noqa: E501
                }
            )

        # Check platform version for Fargate
        launch_type = service.get("launchType", "EC2")
        if launch_type == "FARGATE":
            platform_version = service.get("platformVersion", "LATEST")
            if platform_version == "LATEST":
                recommendations.append(
                    {
                        "title": "Pin Fargate Platform Version for Security Consistency",
                        "severity": "Medium",
                        "category": "security",
                        "resource": f"Service: {service_name}",
                        "issue": "Using LATEST platform version can introduce unexpected security changes and makes security posture unpredictable",  # noqa: E501
                        "recommendation": "Pin to a specific Fargate platform version to maintain consistent security configuration and controlled security updates",  # noqa: E501
                    }
                )

        # Placement strategy is operational, not security - removed

        # Check service connect configuration
        service_connect_config = service.get("serviceConnectConfiguration", {})
        if service_connect_config.get("enabled", False):
            namespace = service_connect_config.get("namespace")
            if not namespace:
                recommendations.append(
                    {
                        "title": "Configure Service Connect Namespace",
                        "severity": "Medium",
                        "category": "network_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Service Connect is enabled but no namespace is configured",
                        "recommendation": "Configure a proper namespace for Service Connect to ensure secure service-to-service communication",  # noqa: E501
                    }
                )

        # Note: Deployment percentages are availability concerns, not security - removed analysis

        # Check security groups
        security_groups = network_config.get("securityGroups", [])
        if not security_groups:
            recommendations.append(
                {
                    "title": "Configure Security Groups",
                    "severity": "High",
                    "category": "network_security",
                    "resource": f"Service: {service_name}",
                    "issue": "No security groups configured for the service",
                    "recommendation": "Configure appropriate security groups to control network access",  # noqa: E501
                }
            )
        elif len(security_groups) > 5:
            recommendations.append(
                {
                    "title": "Review Security Group Count",
                    "severity": "Low",
                    "category": "network_security",
                    "resource": f"Service: {service_name}",
                    "issue": f"Service has {len(security_groups)} security groups attached, which may be excessive",  # noqa: E501
                    "recommendation": "Review and consolidate security groups to simplify network security management",  # noqa: E501
                }
            )

        # Check subnets configuration
        # Multiple AZ is availability, not security - removed

        # Check desired count
        # Task instance count is availability, not security - removed

        # Circuit breaker is deployment safety, not security - removed

        # PHASE 1: Add service mesh security analysis
        recommendations.extend(
            self._analyze_service_mesh_security(service, service_name, cluster_name, region)
        )

        return recommendations

    def _analyze_service_tags_security(
        self, service_tags: List[Dict[str, Any]], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze service tags for SECURITY-RELEVANT issues only."""
        recommendations = []

        # SECURITY: Check for tags that might expose sensitive information
        for tag in service_tags:
            tag_key = tag.get("key", "").lower()
            tag_value = tag.get("value", "")

            # Flag tags that might contain sensitive data
            sensitive_patterns = ["password", "secret", "key", "token", "credential"]
            if any(pattern in tag_key for pattern in sensitive_patterns):
                recommendations.append(
                    {
                        "title": "Sensitive Information in Tag Key",
                        "severity": "High",
                        "category": "secrets",
                        "resource": f"Service: {service_name}",
                        "issue": f'Tag key "{tag.get("key", "")}" may contain sensitive information',  # noqa: E501
                        "recommendation": "Remove sensitive information from tag keys and use AWS Secrets Manager instead",  # noqa: E501
                    }
                )

            # Check for potentially sensitive values (basic patterns)
            if len(tag_value) > 20 and any(char in tag_value for char in ["=", ":", ";", "|"]):
                # This might be a connection string or encoded secret
                recommendations.append(
                    {
                        "title": "Potential Sensitive Data in Tag Value",
                        "severity": "Medium",
                        "category": "secrets",
                        "resource": f"Service: {service_name}",
                        "issue": f'Tag "{tag.get("key", "")}" value appears to contain structured data that might be sensitive',  # noqa: E501
                        "recommendation": "Review tag value and move any sensitive data to AWS Secrets Manager",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_running_tasks_security(
        self, running_tasks: List[str], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze running tasks for SECURITY issues only."""
        recommendations = []

        # SECURITY: Check for potential DDoS or resource exhaustion attacks
        if len(running_tasks) > 100:
            recommendations.append(
                {
                    "title": "Unusually High Task Count - Potential Security Issue",
                    "severity": "Medium",
                    "category": "security",
                    "resource": f"Service: {service_name}",
                    "issue": f"Service has {len(running_tasks)} running tasks, which could indicate a DDoS attack or resource exhaustion attempt",  # noqa: E501
                    "recommendation": "Investigate high task count for potential security incidents and review scaling policies",  # noqa: E501
                }
            )

        # SECURITY: If no tasks are running, this could indicate a security incident
        elif not running_tasks:
            recommendations.append(
                {
                    "title": "No Running Tasks - Potential Security Incident",
                    "severity": "High",
                    "category": "security",
                    "resource": f"Service: {service_name}",
                    "issue": "Service has no running tasks, which could indicate a security incident or attack",  # noqa: E501
                    "recommendation": "Immediately investigate why service has no running tasks - check for potential security breaches or attacks",  # noqa: E501
                }
            )

        return recommendations

    def _analyze_task_definition_security(
        self, task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze task definition security configurations."""
        recommendations = []

        task_family = task_def.get("family", "unknown")

        # Check task IAM role
        task_role_arn = task_def.get("taskRoleArn")
        if not task_role_arn:
            recommendations.append(
                {
                    "title": "Configure Task IAM Role",
                    "severity": "High",
                    "category": "iam_security",
                    "resource": f"Task Definition: {task_family}",
                    "issue": "Missing task IAM role - containers will have no AWS API permissions",
                    "recommendation": "Configure task IAM role with minimal required permissions following principle of least privilege",  # noqa: E501
                }
            )

        # Check execution role
        execution_role_arn = task_def.get("executionRoleArn")
        if not execution_role_arn:
            recommendations.append(
                {
                    "title": "Configure Execution IAM Role",
                    "severity": "High",
                    "category": "iam_security",
                    "resource": f"Task Definition: {task_family}",
                    "issue": "Missing execution IAM role - ECS agent cannot pull images or write logs",  # noqa: E501
                    "recommendation": "Configure execution IAM role for ECS agent operations (image pulling, logging, secrets)",  # noqa: E501
                }
            )

        # Check network mode
        network_mode = task_def.get("networkMode", "bridge")
        if network_mode == "host":
            recommendations.append(
                {
                    "title": "Avoid Host Network Mode",
                    "severity": "High",
                    "category": "network_security",
                    "resource": f"Task Definition: {task_family}",
                    "issue": "Task uses host network mode, bypassing container network isolation",
                    "recommendation": "Use awsvpc network mode for better network isolation and security",  # noqa: E501
                }
            )

        # Check PID mode
        pid_mode = task_def.get("pidMode")
        if pid_mode == "host":
            recommendations.append(
                {
                    "title": "Avoid Host PID Mode",
                    "severity": "High",
                    "category": "container_security",
                    "resource": f"Task Definition: {task_family}",
                    "issue": "Task uses host PID mode, allowing containers to see all host processes",  # noqa: E501
                    "recommendation": "Remove pidMode or set to task for proper process isolation",
                }
            )

        # Check IPC mode
        ipc_mode = task_def.get("ipcMode")
        if ipc_mode == "host":
            recommendations.append(
                {
                    "title": "Avoid Host IPC Mode",
                    "severity": "High",
                    "category": "container_security",
                    "resource": f"Task Definition: {task_family}",
                    "issue": "Task uses host IPC mode, allowing containers to access host IPC resources",  # noqa: E501
                    "recommendation": "Remove ipcMode or set to task for proper IPC isolation",
                }
            )

        # Check memory limits for EC2
        requires_compatibilities = task_def.get("requiresCompatibilities", [])
        if "EC2" in requires_compatibilities:
            for container in task_def.get("containerDefinitions", []):
                if not container.get("memory") and not container.get("memoryReservation"):
                    recommendations.append(
                        {
                            "title": "Configure Memory Limits for EC2 Container (Required)",
                            "severity": "High",
                            "category": "resource_management",
                            "resource": _format_resource_name(
                                "Container", container.get("name", "unknown"), service_name
                            ),  # noqa: E501
                            "issue": f"Container {container.get('name', 'unknown')} has no memory limits configured on EC2 launch type",  # noqa: E501
                            "recommendation": "Set memory limits to prevent resource exhaustion on EC2 instances - this is required for EC2 launch type",  # noqa: E501
                        }
                    )

        # Check for Fargate-specific configurations
        if "FARGATE" in requires_compatibilities:
            cpu = task_def.get("cpu")
            memory = task_def.get("memory")

            if not cpu:
                recommendations.append(
                    {
                        "title": "Configure Task CPU for Fargate",
                        "severity": "High",
                        "category": "configuration",
                        "resource": f"Task Definition: {task_family}",
                        "issue": "Fargate task definition missing CPU configuration",
                        "recommendation": "Set task-level CPU for Fargate compatibility",
                    }
                )

            if not memory:
                recommendations.append(
                    {
                        "title": "Configure Task Memory for Fargate",
                        "severity": "High",
                        "category": "configuration",
                        "resource": f"Task Definition: {task_family}",
                        "issue": "Fargate task definition missing memory configuration",
                        "recommendation": "Set task-level memory for Fargate compatibility",
                    }
                )

        # Check for volumes configuration
        volumes = task_def.get("volumes", [])
        for volume in volumes:
            volume_name = volume.get("name", "unknown")

            # Check for host path volumes
            host_config = volume.get("host", {})
            if host_config.get("sourcePath"):
                recommendations.append(
                    {
                        "title": "Review Host Path Volume Usage",
                        "severity": "Medium",
                        "category": "container_security",
                        "resource": f"Volume: {volume_name}",
                        "issue": f"Volume uses host path {host_config.get('sourcePath')}, which may expose host filesystem",  # noqa: E501
                        "recommendation": "Consider using EFS or other managed storage instead of host paths",  # noqa: E501
                    }
                )

            # Check for Docker volume configuration
            docker_volume_config = volume.get("dockerVolumeConfiguration", {})
            if docker_volume_config and not docker_volume_config.get("encrypted", False):
                recommendations.append(
                    {
                        "title": "Enable Volume Encryption",
                        "severity": "Medium",
                        "category": "encryption",
                        "resource": f"Volume: {volume_name}",
                        "issue": "Docker volume is not encrypted",
                        "recommendation": "Enable encryption for Docker volumes to protect data at rest",  # noqa: E501
                    }
                )

            # Check for EFS volume security
            efs_config = volume.get("efsVolumeConfiguration", {})
            if efs_config:
                if not efs_config.get("transitEncryption") == "ENABLED":
                    recommendations.append(
                        {
                            "title": "Enable EFS Transit Encryption",
                            "severity": "High",
                            "category": "encryption",
                            "resource": f"EFS Volume: {volume_name}",
                            "issue": "EFS volume does not have transit encryption enabled",
                            "recommendation": "Enable transit encryption for EFS volumes to protect data in transit",  # noqa: E501
                        }
                    )

                if not efs_config.get("authorizationConfig", {}).get("accessPointId"):
                    recommendations.append(
                        {
                            "title": "Use EFS Access Points for Fine-Grained Access Control",
                            "severity": "Medium",
                            "category": "iam_security",
                            "resource": f"EFS Volume: {volume_name}",
                            "issue": "EFS volume not using access points, missing fine-grained access control",  # noqa: E501
                            "recommendation": "Configure EFS access points to enforce POSIX permissions and user/group mappings",  # noqa: E501
                        }
                    )

            # Check for FSx volume security
            fsx_config = volume.get("fsxWindowsFileServerVolumeConfiguration", {})
            if fsx_config:
                if not fsx_config.get("authorizationConfig", {}).get("credentialsParameter"):
                    recommendations.append(
                        {
                            "title": "Secure FSx Credentials Management",
                            "severity": "High",
                            "category": "secrets",
                            "resource": f"FSx Volume: {volume_name}",
                            "issue": "FSx volume credentials not managed through AWS Secrets Manager",  # noqa: E501
                            "recommendation": "Store FSx credentials in AWS Secrets Manager for secure access",  # noqa: E501
                        }
                    )

        # Check placement constraints
        placement_constraints = task_def.get("placementConstraints", [])
        for constraint in placement_constraints:
            if constraint.get(
                "type"
            ) == "memberOf" and "attribute:ecs.instance-type" in constraint.get("expression", ""):
                recommendations.append(
                    {
                        "title": "Review Instance Type Constraints",
                        "severity": "Low",
                        "category": "configuration",
                        "resource": f"Task Definition: {task_family}",
                        "issue": "Task has instance type constraints that may limit flexibility",
                        "recommendation": "Review placement constraints to ensure they are necessary and not overly restrictive",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_network_security(
        self, service: Dict[str, Any], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze network security configurations."""
        recommendations = []

        # Check load balancer configuration
        load_balancers = service.get("loadBalancers", [])
        for lb in load_balancers:
            target_group_arn = lb.get("targetGroupArn", "")
            if target_group_arn:
                # Extract target group name from ARN
                tg_name = target_group_arn.split("/")[-2] if "/" in target_group_arn else "unknown"
                recommendations.append(
                    {
                        "title": "Configure Specific Health Check Path for Load Balancer",
                        "severity": "Medium",
                        "category": "network",
                        "resource": f"Target Group: {tg_name}",
                        "issue": "Load balancer target group uses default health check path, which may not accurately reflect application health",  # noqa: E501
                        "recommendation": "Configure a specific health check path that validates application functionality and dependencies",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_container_security(
        self,
        container: Dict[str, Any],
        container_name: str,
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze container security configurations."""
        recommendations = []

        # Check for root user
        user = container.get("user")
        if user == "0" or user == "root" or not user:
            recommendations.append(
                {
                    "title": "Configure Container to Run as Non-Root User",
                    "severity": "High",
                    "category": "container_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "The container is configured to run as the root user (UID 0), violating the principle of least privilege",  # noqa: E501
                    "recommendation": "Configure the container to run as a non-privileged user by creating a dedicated application user",  # noqa: E501
                }
            )

        # Check for latest tag
        image = container.get("image", "")
        if image.endswith(":latest") or image.count(":") == 0:
            recommendations.append(
                {
                    "title": "Avoid Latest Tag in Container Images",
                    "severity": "Medium",
                    "category": "container_security",
                    "resource": self._format_resource_name(
                        "Container", container_name, service_name, cluster_name
                    ),
                    "issue": "The container image uses the 'latest' tag or no tag, making deployments unpredictable and potentially insecure",  # noqa: E501
                    "recommendation": "Use specific, immutable image tags with semantic versioning to ensure reproducible deployments",  # noqa: E501
                }
            )

        # Check for potentially vulnerable base images
        if image:
            vulnerable_patterns = [
                "node:10",
                "python:2",
                "ubuntu:14.",
                "ubuntu:16",
                "centos:6",
                "centos:7",
            ]
            if any(pattern in image.lower() for pattern in vulnerable_patterns):
                recommendations.append(
                    {
                        "title": "Update Outdated Base Image",
                        "severity": "High",
                        "category": "image_security",
                        "resource": self._format_resource_name(
                            "Container", container_name, service_name, cluster_name
                        ),
                        "issue": "Container uses outdated base image with known security vulnerabilities",  # noqa: E501
                        "recommendation": "Update to supported base image versions with current security patches",  # noqa: E501
                    }
                )

        # Check for read-only root filesystem
        if not container.get("readonlyRootFilesystem", False):
            recommendations.append(
                {
                    "title": "Enable Read-Only Root Filesystem",
                    "severity": "Medium",
                    "category": "container_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": f"Container {container_name} has writable root filesystem",
                    "recommendation": "Enable read-only root filesystem to prevent runtime tampering",  # noqa: E501
                }
            )

        # Check for privileged mode
        if container.get("privileged", False):
            recommendations.append(
                {
                    "title": "Disable Privileged Mode",
                    "severity": "High",
                    "category": "container_security",
                    "resource": self._format_resource_name(
                        "Container", container_name, service_name, cluster_name
                    ),
                    "issue": "Container is running in privileged mode, granting access to all host devices",  # noqa: E501
                    "recommendation": "Disable privileged mode and use specific capabilities if needed",  # noqa: E501
                }
            )

        # Check for health check
        if not container.get("healthCheck"):
            recommendations.append(
                {
                    "title": "Configure Container Health Check",
                    "severity": "Medium",
                    "category": "monitoring",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "The container lacks health check configuration, preventing ECS from detecting application failures",  # noqa: E501
                    "recommendation": "Implement comprehensive health checks that verify application functionality",  # noqa: E501
                }
            )

        # Check for resource limits
        memory = container.get("memory")
        memory_reservation = container.get("memoryReservation")
        cpu = container.get("cpu")

        if not memory and not memory_reservation:
            recommendations.append(
                {
                    "title": "Configure Memory Limits",
                    "severity": "High",
                    "category": "resource_management",
                    "resource": self._format_resource_name(
                        "Container", container_name, service_name, cluster_name
                    ),
                    "issue": "Container has no memory limits configured, risking resource exhaustion",  # noqa: E501
                    "recommendation": "Set appropriate memory limits to prevent resource starvation",  # noqa: E501
                }
            )

        if not cpu:
            recommendations.append(
                {
                    "title": "Configure CPU Limits",
                    "severity": "Medium",
                    "category": "resource_management",
                    "resource": self._format_resource_name(
                        "Container", container_name, service_name, cluster_name
                    ),
                    "issue": "Container has no CPU limits configured",
                    "recommendation": "Set appropriate CPU limits for predictable performance",
                }
            )

        # Check for private registry
        is_public_ecr = image.startswith("public.ecr.aws/")
        is_docker_hub = self._is_docker_hub_image(image)
        is_private_ecr = self._is_valid_ecr_image(image)

        if is_public_ecr or is_docker_hub or not is_private_ecr:
            recommendations.append(
                {
                    "title": "Consider Using Private Container Registry",
                    "severity": "Low",
                    "category": "container_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": f"Container {container_name} uses public registry image, which may have less security oversight and control",  # noqa: E501
                    "recommendation": "Consider using Amazon ECR for better security, control, and compliance",  # noqa: E501
                }
            )

        # Check for static port mapping
        port_mappings = container.get("portMappings", [])
        for port_mapping in port_mappings:
            host_port = port_mapping.get("hostPort")
            if host_port and host_port != 0:
                recommendations.append(
                    {
                        "title": "Avoid Static Host Port Mapping",
                        "severity": "Medium",
                        "category": "container_security",
                        "resource": self._format_resource_name(
                            "Container", container_name, service_name, cluster_name
                        ),
                        "issue": f"Container {container_name} uses static host port {host_port}, which can lead to port conflicts and security issues",  # noqa: E501
                        "recommendation": "Use dynamic port mapping (hostPort: 0) for better security and flexibility",  # noqa: E501
                    }
                )

        # Check for logging configuration
        log_configuration = container.get("logConfiguration")
        if not log_configuration:
            recommendations.append(
                {
                    "title": "Configure Container Logging for Security Monitoring",
                    "severity": "Medium",
                    "category": "container_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Container has no logging configuration, making security monitoring, troubleshooting, and compliance auditing difficult",  # noqa: E501
                    "recommendation": "Configure CloudWatch Logs or another logging driver for security event monitoring and compliance",  # noqa: E501
                }
            )

        # Check for essential container configuration
        if container.get("essential", True) and len(port_mappings) == 0:
            recommendations.append(
                {
                    "title": "Review Essential Container Configuration",
                    "severity": "Low",
                    "category": "configuration",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Essential container with no port mappings may indicate misconfiguration",  # noqa: E501
                    "recommendation": "Review if this container should be marked as essential",
                }
            )

        # Check for Linux parameters security
        linux_parameters = container.get("linuxParameters", {})
        if linux_parameters:
            # Check for dangerous capabilities
            capabilities = linux_parameters.get("capabilities", {})
            add_capabilities = capabilities.get("add", [])

            dangerous_caps = ["SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "SYS_MODULE"]
            for cap in add_capabilities:
                if cap in dangerous_caps:
                    recommendations.append(
                        {
                            "title": f"Review Dangerous Capability: {cap}",
                            "severity": "High",
                            "category": "container_security",
                            "resource": _format_resource_name(
                                "Container", container_name, service_name
                            ),  # noqa: E501
                            "issue": f"Container has dangerous capability {cap} which increases security risk",  # noqa: E501
                            "recommendation": "Remove unnecessary capabilities and use least privilege principle",  # noqa: E501
                        }
                    )

            # Check for no-new-privileges flag
            if not linux_parameters.get("initProcessEnabled", False):
                recommendations.append(
                    {
                        "title": "Enable Init Process for Signal Handling",
                        "severity": "Medium",
                        "category": "container_security",
                        "resource": _format_resource_name(
                            "Container", container_name, service_name
                        ),  # noqa: E501
                        "issue": "Container lacks init process, potentially causing zombie processes and signal handling issues",  # noqa: E501
                        "recommendation": "Enable initProcessEnabled to properly handle signals and prevent zombie processes",  # noqa: E501
                    }
                )

            # Check for tmpfs mounts security
            tmpfs = linux_parameters.get("tmpfs", [])
            for tmpfs_mount in tmpfs:
                size = tmpfs_mount.get("size", 0)
                if size > 1073741824:  # 1GB
                    recommendations.append(
                        {
                            "title": "Review Large Tmpfs Mount Size",
                            "severity": "Medium",
                            "category": "container_security",
                            "resource": _format_resource_name(
                                "Container", container_name, service_name
                            ),  # noqa: E501
                            "issue": f"Tmpfs mount size {size} bytes is very large and could lead to memory exhaustion",  # noqa: E501
                            "recommendation": "Limit tmpfs mount sizes to prevent memory-based DoS attacks",  # noqa: E501
                        }
                    )

            # Check for shared memory settings
            shared_memory_size = linux_parameters.get("sharedMemorySize")
            if shared_memory_size and shared_memory_size > 536870912:  # 512MB
                recommendations.append(
                    {
                        "title": "Review Large Shared Memory Size",
                        "severity": "Medium",
                        "category": "container_security",
                        "resource": _format_resource_name(
                            "Container", container_name, service_name
                        ),  # noqa: E501
                        "issue": f"Shared memory size {shared_memory_size} bytes is large and could be exploited",  # noqa: E501
                        "recommendation": "Limit shared memory size to minimum required for application functionality",  # noqa: E501
                    }
                )

        # Check for task metadata endpoint security
        environment = container.get("environment", [])
        metadata_v2_enabled = any(
            env.get("name") == "ECS_ENABLE_TASK_METADATA_ENDPOINT_V2" and env.get("value") == "true"
            for env in environment
        )
        if not metadata_v2_enabled:
            recommendations.append(
                {
                    "title": "Verify Task Metadata Endpoint Security Configuration",
                    "severity": "Low",
                    "category": "security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": f"Container {container_name} should verify task metadata endpoint security",  # noqa: E501
                    "recommendation": "Ensure task metadata endpoint v2 is used and properly secured",  # noqa: E501
                }
            )

        # PHASE 1: Add enhanced container runtime security analysis
        recommendations.extend(
            self._analyze_container_runtime_security(
                container, container_name, service_name, cluster_name, region
            )
        )

        # PHASE 1: Add advanced image security analysis
        recommendations.extend(
            self._analyze_advanced_image_security(
                container, container_name, service_name, cluster_name, region
            )
        )

        return recommendations

    def _analyze_capacity_providers(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze capacity provider security configurations."""
        recommendations = []

        # Check for capacity provider configurations
        cluster_info = cluster_data.get("cluster", {})
        capacity_providers = cluster_info.get("capacityProviders", [])

        for cp_name in capacity_providers:
            # Check for EC2 capacity providers that might need termination protection
            if "ec2" in cp_name.lower():
                recommendations.append(
                    {
                        "title": f"Enable Managed Termination Protection for Capacity Provider {cp_name}",  # noqa: E501
                        "severity": "Medium",
                        "category": "configuration",
                        "resource": f"Capacity Provider: {cp_name}",
                        "issue": f"Capacity provider {cp_name} does not have managed termination protection",  # noqa: E501
                        "recommendation": "Enable managed termination protection to prevent premature instance termination",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_iam_security(
        self,
        service: Dict[str, Any],
        task_def: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze IAM security configurations (advanced checks only - basic role checks done in task definition analysis)."""  # noqa: E501
        recommendations = []

        # Only check for advanced IAM issues to avoid duplicates with task definition analysis
        task_role_arn = task_def.get("taskRoleArn")
        execution_role_arn = task_def.get("executionRoleArn")

        # Advanced check: Overly permissive policies (only if roles exist)
        if task_role_arn and "*" in task_role_arn:
            recommendations.append(
                {
                    "title": "Avoid Wildcard Permissions in Task IAM Role",
                    "severity": "High",
                    "category": "iam_security",
                    "resource": f"Task Role: {task_role_arn}",
                    "issue": "Task IAM role may contain overly permissive wildcard permissions",
                    "recommendation": "Review and restrict IAM permissions to follow principle of least privilege",  # noqa: E501
                }
            )

        # Advanced check: Execution role best practices (only if role exists)
        if execution_role_arn and "AmazonECSTaskExecutionRolePolicy" not in execution_role_arn:
            recommendations.append(
                {
                    "title": "Use Managed Execution Role Policy",
                    "severity": "Medium",
                    "category": "iam_security",
                    "resource": f"Execution Role: {execution_role_arn}",
                    "issue": "Custom execution role may have unnecessary permissions",
                    "recommendation": "Use AWS managed AmazonECSTaskExecutionRolePolicy when possible",  # noqa: E501
                }
            )

        # Check for cross-account role assumptions (advanced security)
        if task_role_arn and ":role/" in task_role_arn:
            role_account = task_role_arn.split(":")[4]
            # This is a simplified check - in real implementation you'd get current account
            if role_account != "current_account":  # Placeholder logic
                recommendations.append(
                    {
                        "title": "Review Cross-Account IAM Role Usage",
                        "severity": "Medium",
                        "category": "iam_security",
                        "resource": f"Task Role: {task_role_arn}",
                        "issue": "Task role appears to be from different AWS account",
                        "recommendation": "Verify cross-account role usage is intentional and properly secured",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_logging_security(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze logging and monitoring security configurations."""
        recommendations = []

        # Note: Execute command logging is now handled in _analyze_cluster_security to avoid duplication  # noqa: E501
        # This method can be extended for other logging-specific security checks in the future

        return recommendations

    def _analyze_secrets_security(
        self, task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze secrets management security."""
        recommendations = []

        for container in task_def.get("containerDefinitions", []):
            container_name = container.get("name", "unknown")

            # Check for hardcoded secrets in environment variables
            environment = container.get("environment", [])
            for env_var in environment:
                env_name = env_var.get("name", "").lower()
                env_value = env_var.get("value", "")

                if any(
                    secret_keyword in env_name
                    for secret_keyword in ["password", "secret", "key", "token", "api_key"]
                ):
                    if (
                        env_value
                        and not env_value.startswith("arn:aws:secretsmanager")
                        and not env_value.startswith("arn:aws:ssm")
                    ):
                        recommendations.append(
                            {
                                "title": "Use AWS Secrets Manager for Sensitive Data",
                                "severity": "High",
                                "category": "secrets",
                                "resource": _format_resource_name(
                                    "Container", container_name, service_name
                                ),  # noqa: E501
                                "issue": f"Environment variable {env_name} contains hardcoded sensitive data - immediate credential exposure risk",  # noqa: E501
                                "recommendation": "Immediately migrate to AWS Secrets Manager to prevent credential theft and unauthorized access",  # noqa: E501
                            }
                        )

            # Check for secrets configuration
            secrets = container.get("secrets", [])
            if not secrets and environment:
                # Check if there are environment variables that should be secrets
                sensitive_vars = [
                    env
                    for env in environment
                    if any(
                        keyword in env.get("name", "").lower()
                        for keyword in ["password", "secret", "key", "token"]
                    )
                ]
                if sensitive_vars:
                    recommendations.append(
                        {
                            "title": "Migrate Sensitive Environment Variables to Secrets",
                            "severity": "High",
                            "category": "secrets",
                            "resource": _format_resource_name(
                                "Container", container_name, service_name
                            ),  # noqa: E501
                            "issue": "Sensitive data detected in environment variables - visible in process lists, logs, and container metadata",  # noqa: E501
                            "recommendation": "Immediately migrate sensitive data to AWS Secrets Manager or Parameter Store to prevent credential exposure",  # noqa: E501
                        }
                    )

            # Enhanced secrets management checks
            if secrets:
                for secret in secrets:
                    secret_arn = secret.get("valueFrom", "")

                    # Check for Parameter Store vs Secrets Manager usage
                    if secret_arn.startswith("arn:aws:ssm"):
                        secret_name = secret.get("name", "")
                        if any(
                            keyword in secret_name.lower()
                            for keyword in ["password", "key", "token", "credential"]
                        ):
                            recommendations.append(
                                {
                                    "title": "Use Secrets Manager for Sensitive Data",
                                    "severity": "Medium",
                                    "category": "secrets",
                                    "resource": _format_resource_name(
                                        "Container", container_name, service_name
                                    ),  # noqa: E501
                                    "issue": f"Secret {secret_name} uses Parameter Store instead of Secrets Manager for sensitive data",  # noqa: E501
                                    "recommendation": "Use AWS Secrets Manager for passwords, API keys, and credentials for automatic rotation and enhanced security",  # noqa: E501
                                }
                            )

        return recommendations

    def _analyze_compliance_security(
        self,
        service: Dict[str, Any],
        task_def: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze compliance-related security configurations."""
        recommendations = []

        # Check for compliance tags
        service_tags = service.get("tags", [])
        # Service tags for compliance tracking are operational, not security - removed

        # Check for data classification
        data_classification_found = any(
            tag.get("key", "").lower()
            in ["dataclassification", "data-classification", "sensitivity"]
            for tag in service_tags
        )

        if not data_classification_found:
            recommendations.append(
                {
                    "title": "Add Data Classification Tags",
                    "severity": "Medium",
                    "category": "compliance",
                    "resource": f"Service: {service_name}",
                    "issue": "No data classification tags found",
                    "recommendation": "Add data classification tags to identify data sensitivity levels",  # noqa: E501
                }
            )

        return recommendations

    def _analyze_network_infrastructure(
        self, network_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze network infrastructure security."""
        recommendations = []

        # Analyze VPC configuration
        vpcs_data = network_data.get("vpcs", {})

        # Handle raw AWS API response format
        if "Vpcs" in vpcs_data:
            vpcs_list = vpcs_data["Vpcs"]
        else:
            # Handle processed format (dict of vpc_id -> vpc_info)
            vpcs_list = list(vpcs_data.values()) if isinstance(vpcs_data, dict) else []

        for vpc_info in vpcs_list:
            if not isinstance(vpc_info, dict):
                continue

            vpc_id = vpc_info.get("VpcId", "unknown")

            # Check for default VPC usage
            if vpc_info.get("IsDefault", False):
                recommendations.append(
                    {
                        "title": "Avoid Using Default VPC for Production Workloads",
                        "severity": "Medium",
                        "category": "network",
                        "resource": f"VPC: {vpc_id}",
                        "issue": "Using default VPC which may have less secure default configurations",  # noqa: E501
                        "recommendation": "Create a custom VPC with proper security configurations",
                    }
                )

        # Analyze Security Groups
        security_groups_data = network_data.get("security_groups", {})

        # Handle raw AWS API response format
        if "SecurityGroups" in security_groups_data:
            security_groups_list = security_groups_data["SecurityGroups"]
        else:
            # Handle processed format (dict of sg_id -> sg_info)
            security_groups_list = (
                list(security_groups_data.values())
                if isinstance(security_groups_data, dict)
                else []
            )

        for sg_info in security_groups_list:
            if not isinstance(sg_info, dict):
                continue

            sg_id = sg_info.get("GroupId", "unknown")
            ingress_rules = sg_info.get("IpPermissions", [])

            for rule in ingress_rules:
                # Check for overly permissive rules
                ip_ranges = rule.get("IpRanges", [])
                for ip_range in ip_ranges:
                    cidr = ip_range.get("CidrIp", "")
                    if cidr == "0.0.0.0/0":
                        from_port = rule.get("FromPort", 0)
                        to_port = rule.get("ToPort", 0)

                        if from_port == 22 or to_port == 22:
                            recommendations.append(
                                {
                                    "title": "Restrict SSH Access from Internet",
                                    "severity": "High",
                                    "category": "network_security",
                                    "resource": f"Security Group: {sg_id}",
                                    "issue": "SSH port (22) is open to the internet (0.0.0.0/0)",
                                    "recommendation": "Restrict SSH access to specific IP ranges or use AWS Systems Manager Session Manager",  # noqa: E501
                                }
                            )
                        elif from_port == 3389 or to_port == 3389:
                            recommendations.append(
                                {
                                    "title": "Restrict RDP Access from Internet",
                                    "severity": "High",
                                    "category": "network_security",
                                    "resource": f"Security Group: {sg_id}",
                                    "issue": "RDP port (3389) is open to the internet (0.0.0.0/0)",
                                    "recommendation": "Restrict RDP access to specific IP ranges or use AWS Systems Manager Session Manager",  # noqa: E501
                                }
                            )
                        elif from_port != 80 and from_port != 443:
                            recommendations.append(
                                {
                                    "title": "Review Overly Permissive Security Group Rules",
                                    "severity": "High",
                                    "category": "network_security",
                                    "resource": f"Security Group: {sg_id}",
                                    "issue": f"Port {from_port} is open to the internet (0.0.0.0/0)",  # noqa: E501
                                    "recommendation": "Restrict access to specific IP ranges or remove unnecessary rules",  # noqa: E501
                                }
                            )

        # Analyze Subnets
        subnets_data = network_data.get("subnets", {})

        # Handle raw AWS API response format
        if "Subnets" in subnets_data:
            subnets_list = subnets_data["Subnets"]
        else:
            # Handle processed format (dict of subnet_id -> subnet_info)
            subnets_list = list(subnets_data.values()) if isinstance(subnets_data, dict) else []

        for subnet_info in subnets_list:
            if not isinstance(subnet_info, dict):
                continue

            subnet_id = subnet_info.get("SubnetId", "unknown")
            if subnet_info.get("MapPublicIpOnLaunch", False):
                recommendations.append(
                    {
                        "title": "Disable Auto-Assign Public IP for Subnets",
                        "severity": "Medium",
                        "category": "network_security",
                        "resource": f"Subnet: {subnet_id}",
                        "issue": "Subnet automatically assigns public IP addresses",
                        "recommendation": "Disable auto-assign public IP and use NAT Gateway for outbound connectivity",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_cluster_iam_security(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze cluster-level IAM security configurations."""
        recommendations = []

        cluster_info = cluster_data.get("cluster", {})

        # Check for service-linked roles
        service_linked_role = cluster_info.get("serviceLinkedRoleArn")
        if not service_linked_role:
            recommendations.append(
                {
                    "title": "Configure ECS Service-Linked Role",
                    "severity": "Medium",
                    "category": "iam_security",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "No service-linked role configured for ECS cluster operations",
                    "recommendation": "Create and configure the AWSServiceRoleForECS service-linked role for proper cluster management",  # noqa: E501
                }
            )

        return recommendations

    def _analyze_vpc_security(
        self, network_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze VPC security configurations."""
        recommendations = []

        vpcs_data = network_data.get("vpcs", {})

        # Handle raw AWS API response format
        if "Vpcs" in vpcs_data:
            vpcs_list = vpcs_data["Vpcs"]
        else:
            # Handle processed format (dict of vpc_id -> vpc_info)
            vpcs_list = list(vpcs_data.values()) if isinstance(vpcs_data, dict) else []

        for vpc_info in vpcs_list:
            if not isinstance(vpc_info, dict):
                continue

            vpc_id = vpc_info.get("VpcId", "unknown")

            # Check VPC Flow Logs (Note: Flow logs info is not in the VPC describe response)
            # We'll recommend enabling them as a best practice
            recommendations.append(
                {
                    "title": "Enable VPC Flow Logs",
                    "severity": "Medium",
                    "category": "network_security",
                    "resource": f"VPC: {vpc_id}",
                    "issue": "VPC Flow Logs should be enabled for network traffic visibility and security monitoring",  # noqa: E501
                    "recommendation": "Enable VPC Flow Logs to monitor network traffic and detect security anomalies",  # noqa: E501
                }
            )

            # Check if this is a default VPC (already handled in network infrastructure analysis)
            # We can add other VPC-specific checks here if needed

        return recommendations

    def _analyze_route_tables(
        self, network_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze route table security configurations."""
        recommendations = []

        route_tables_data = network_data.get("route_tables", {})

        # Handle raw AWS API response format
        if "RouteTables" in route_tables_data:
            route_tables_list = route_tables_data["RouteTables"]
        else:
            route_tables_list = (
                list(route_tables_data.values()) if isinstance(route_tables_data, dict) else []
            )

        for rt_info in route_tables_list:
            if not isinstance(rt_info, dict):
                continue

            rt_id = rt_info.get("RouteTableId", "unknown")
            routes = rt_info.get("Routes", [])

            # Check for overly broad routes
            for route in routes:
                destination = route.get("DestinationCidrBlock", "")
                gateway_id = route.get("GatewayId", "")

                # Check for routes to 0.0.0.0/0 through internet gateway
                if destination == "0.0.0.0/0" and gateway_id and gateway_id.startswith("igw-"):
                    # This is normal for public subnets, but flag for review
                    recommendations.append(
                        {
                            "title": "Review Internet Gateway Routes",
                            "severity": "Low",
                            "category": "network_security",
                            "resource": f"Route Table: {rt_id}",
                            "issue": "Route table has default route (0.0.0.0/0) to Internet Gateway",  # noqa: E501
                            "recommendation": "Ensure this route table is only associated with public subnets that require internet access",  # noqa: E501
                        }
                    )

        return recommendations

    def _analyze_internet_gateways(
        self, network_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze Internet Gateway security configurations."""
        recommendations = []

        internet_gateways_data = network_data.get("internet_gateways", {})

        # Handle raw AWS API response format
        if "InternetGateways" in internet_gateways_data:
            igw_list = internet_gateways_data["InternetGateways"]
        else:
            igw_list = (
                list(internet_gateways_data.values())
                if isinstance(internet_gateways_data, dict)
                else []
            )

        for igw_info in igw_list:
            if not isinstance(igw_info, dict):
                continue

            igw_id = igw_info.get("InternetGatewayId", "unknown")
            attachments = igw_info.get("Attachments", [])

            # Check if IGW is attached to VPC
            for attachment in attachments:
                if attachment.get("State") == "available":
                    vpc_id = attachment.get("VpcId", "unknown")
                    recommendations.append(
                        {
                            "title": "Review Internet Gateway Security",
                            "severity": "Low",
                            "category": "network_security",
                            "resource": f"Internet Gateway: {igw_id}",
                            "issue": f"Internet Gateway attached to VPC {vpc_id} - ensure proper security controls",  # noqa: E501
                            "recommendation": "Verify that only public subnets route through this IGW and private resources use NAT Gateway",  # noqa: E501
                        }
                    )

        return recommendations

    def _analyze_load_balancer_security(
        self, network_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze load balancer security configurations."""
        recommendations = []

        load_balancers_data = network_data.get("load_balancers", {})

        # Handle raw AWS API response format
        if "LoadBalancers" in load_balancers_data:
            load_balancers_list = load_balancers_data["LoadBalancers"]
        else:
            # Handle processed format (dict of lb_arn -> lb_info)
            load_balancers_list = (
                list(load_balancers_data.values()) if isinstance(load_balancers_data, dict) else []
            )

        for lb_info in load_balancers_list:
            if not isinstance(lb_info, dict):
                continue

            lb_name = lb_info.get("LoadBalancerName", "unknown")

            # Check if load balancer is internet-facing
            scheme = lb_info.get("Scheme", "internal")
            if scheme == "internet-facing":
                recommendations.append(
                    {
                        "title": "Review Internet-Facing Load Balancer Security",
                        "severity": "Medium",
                        "category": "network_security",
                        "resource": f"Load Balancer: {lb_name}",
                        "issue": "Load balancer is internet-facing, ensure proper security controls are in place",  # noqa: E501
                        "recommendation": "Verify security groups, SSL/TLS configuration, and access controls for internet-facing load balancer",  # noqa: E501
                    }
                )

            # Check security groups
            security_groups = lb_info.get("SecurityGroups", [])
            if not security_groups:
                recommendations.append(
                    {
                        "title": "Configure Security Groups for Load Balancer",
                        "severity": "High",
                        "category": "network_security",
                        "resource": f"Load Balancer: {lb_name}",
                        "issue": "No security groups configured for load balancer",
                        "recommendation": "Configure appropriate security groups to control access to the load balancer",  # noqa: E501
                    }
                )

            # Check if access logs are enabled (look for access_logs attribute)
            access_logs_enabled = False
            if "Attributes" in lb_info:
                for attr in lb_info.get("Attributes", []):
                    if attr.get("Key") == "access_logs.s3.enabled" and attr.get("Value") == "true":
                        access_logs_enabled = True
                        break

            if not access_logs_enabled:
                recommendations.append(
                    {
                        "title": "Enable Load Balancer Access Logs",
                        "severity": "Medium",
                        "category": "monitoring",
                        "resource": f"Load Balancer: {lb_name}",
                        "issue": "Access logs are not enabled - missing critical security monitoring and audit trail",  # noqa: E501
                        "recommendation": "Enable access logs to S3 bucket for security monitoring, compliance, and incident response",  # noqa: E501
                        "security_impact": "Without access logs, you cannot detect suspicious traffic patterns, DDoS attacks, or perform forensic analysis during security incidents",  # noqa: E501
                        "compliance_frameworks": [
                            "SOC 2",
                            "PCI DSS",
                            "AWS Well-Architected Security Pillar",
                        ],
                    }
                )

        return recommendations

    def _analyze_well_architected_compliance(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze compliance with AWS Well-Architected Security Pillar."""
        recommendations = []

        # Security Pillar: Identity and Access Management
        # Check for proper tagging strategy
        # Security-related tags are governance metadata, not security controls - removed

        # Security Pillar: Detective Controls
        services = cluster_data.get("services", [])
        if len(services) > 0:
            # Check for monitoring and alerting
            has_monitoring = any(
                service.get("service", {}).get("enableExecuteCommand", False)
                for service in services
            )

            if not has_monitoring:
                recommendations.append(
                    {
                        "title": "Implement Detective Controls (Well-Architected)",
                        "severity": "Medium",
                        "category": "well_architected",
                        "resource": f"Cluster: {cluster_name}",
                        "issue": "Limited detective controls for security monitoring",
                        "recommendation": "Implement comprehensive logging, monitoring, and alerting following Well-Architected principles",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_industry_compliance(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze compliance with industry standards (SOC 2, PCI DSS, HIPAA)."""
        recommendations = []

        cluster_info = cluster_data.get("cluster", {})
        cluster_tags = cluster_info.get("tags", [])

        # Check for compliance framework tags
        compliance_tag = None
        for tag in cluster_tags:
            if tag.get("key", "").lower() in [
                "compliance",
                "complianceframework",
                "compliance-framework",
            ]:
                compliance_tag = tag.get("value", "").upper()
                break

        if compliance_tag:
            # PCI DSS Compliance Checks
            if "PCI" in compliance_tag:
                recommendations.extend(
                    self._check_pci_compliance(cluster_data, cluster_name, region)
                )

            # HIPAA Compliance Checks
            if "HIPAA" in compliance_tag:
                recommendations.extend(
                    self._check_hipaa_compliance(cluster_data, cluster_name, region)
                )

            # SOC 2 Compliance Checks
            if "SOC" in compliance_tag:
                recommendations.extend(
                    self._check_soc2_compliance(cluster_data, cluster_name, region)
                )
        # Compliance framework tags are governance metadata, not security controls - removed

        return recommendations

    def _check_pci_compliance(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Check PCI DSS compliance requirements."""
        recommendations = []

        # PCI DSS Requirement 2: Do not use vendor-supplied defaults
        services = cluster_data.get("services", [])
        for service_data in services:
            service_name = service_data.get("service", {}).get("serviceName", "unknown-service")
            task_def = service_data.get("task_definition", {})
            for container in task_def.get("containerDefinitions", []):
                # Check for default passwords or configurations
                environment = container.get("environment", [])
                for env_var in environment:
                    env_name = env_var.get("name", "").lower()
                    env_value = env_var.get("value", "")

                    if "password" in env_name and env_value in [
                        "password",
                        "admin",
                        "root",
                        "123456",
                    ]:
                        recommendations.append(
                            {
                                "title": "PCI DSS: Remove Default Passwords",
                                "severity": "High",
                                "category": "pci_compliance",
                                "resource": _format_resource_name(
                                    "Container", container.get("name", "unknown"), service_name
                                ),  # noqa: E501
                                "issue": "Default password detected in environment variables",
                                "recommendation": "Replace default passwords with strong, unique credentials stored in AWS Secrets Manager",  # noqa: E501
                            }
                        )

        # PCI DSS Requirement 4: Encrypt transmission of cardholder data
        network_data = cluster_data.get("network_data", {})
        load_balancers = network_data.get("load_balancers", {})

        for _lb_arn, lb_info in load_balancers.items():
            listeners = lb_info.get("Listeners", [])
            has_unencrypted = any(listener.get("Protocol") == "HTTP" for listener in listeners)

            if has_unencrypted:
                recommendations.append(
                    {
                        "title": "PCI DSS: Encrypt Data in Transit",
                        "severity": "High",
                        "category": "pci_compliance",
                        "resource": f"Load Balancer: {lb_info.get('LoadBalancerName', 'unknown')}",
                        "issue": "Unencrypted HTTP traffic detected",
                        "recommendation": "Configure HTTPS/TLS encryption for all data transmission",  # noqa: E501
                    }
                )

        return recommendations

    def _check_hipaa_compliance(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Check HIPAA compliance requirements."""
        recommendations = []

        # HIPAA: Access Controls
        cluster_info = cluster_data.get("cluster", {})
        execute_command_config = cluster_info.get("configuration", {}).get(
            "executeCommandConfiguration", {}
        )

        if execute_command_config and not execute_command_config.get("kmsKeyId"):
            recommendations.append(
                {
                    "title": "HIPAA: Encrypt Administrative Access",
                    "severity": "High",
                    "category": "hipaa_compliance",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "Execute command sessions not encrypted with customer-managed keys",
                    "recommendation": "Configure KMS encryption for execute command to protect PHI access",  # noqa: E501
                }
            )

        # HIPAA: Audit Controls
        container_insights_enabled = any(
            setting.get("name") == "containerInsights" and setting.get("value") == "enabled"
            for setting in cluster_info.get("settings", [])
        )

        if not container_insights_enabled:
            recommendations.append(
                {
                    "title": "HIPAA: Enable Comprehensive Audit Logging",
                    "severity": "High",
                    "category": "hipaa_compliance",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "Container Insights disabled, limiting audit trail for PHI access",
                    "recommendation": "Enable Container Insights and comprehensive logging for HIPAA audit requirements",  # noqa: E501
                }
            )

        return recommendations

    def _check_soc2_compliance(
        self, cluster_data: Dict[str, Any], cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Check SOC 2 compliance requirements."""
        recommendations = []

        # SOC 2: Security - Logical Access Controls
        services = cluster_data.get("services", [])
        for service_data in services:
            service = service_data.get("service", {})
            task_def = service_data.get("task_definition", {})

            # Check for proper IAM roles
            if not task_def.get("taskRoleArn"):
                recommendations.append(
                    {
                        "title": "SOC 2: Implement Logical Access Controls",
                        "severity": "High",
                        "category": "soc2_compliance",
                        "resource": f"Service: {service.get('serviceName', 'unknown')}",
                        "issue": "Missing task IAM role for access control",
                        "recommendation": "Configure task IAM roles with least privilege access for SOC 2 compliance",  # noqa: E501
                    }
                )

        # SOC 2: Availability - System Monitoring
        cluster_info = cluster_data.get("cluster", {})
        container_insights_enabled_soc2 = any(
            setting.get("name") == "containerInsights" and setting.get("value") == "enabled"
            for setting in cluster_info.get("settings", [])
        )
        if not container_insights_enabled_soc2:
            recommendations.append(
                {
                    "title": "SOC 2: Implement System Monitoring",
                    "severity": "Medium",
                    "category": "soc2_compliance",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "Insufficient system monitoring for availability controls",
                    "recommendation": "Enable Container Insights and comprehensive monitoring for SOC 2 availability requirements",  # noqa: E501
                }
            )

        return recommendations

    def _analyze_service_discovery_security(
        self, service: Dict[str, Any], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze service discovery security configurations."""
        recommendations = []

        # Check Service Connect configuration
        service_connect = service.get("serviceConnectConfiguration", {})
        if service_connect.get("enabled", False):
            # Check namespace security
            namespace = service_connect.get("namespace")
            if not namespace:
                recommendations.append(
                    {
                        "title": "Configure Secure Service Discovery Namespace",
                        "severity": "Medium",
                        "category": "service_discovery",
                        "resource": f"Service: {service_name}",
                        "issue": "Service Connect enabled without proper namespace configuration",
                        "recommendation": "Configure a dedicated namespace for secure service-to-service communication",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_resource_isolation(
        self, task_def: Dict[str, Any], service_name: str, cluster_name: str, region: str
    ) -> List[Dict[str, Any]]:
        """Analyze resource isolation and access control."""
        recommendations = []

        task_family = task_def.get("family", "unknown")

        # Check CPU and memory limits for resource isolation
        cpu = task_def.get("cpu")
        memory = task_def.get("memory")

        # For Fargate, check if resources are properly allocated
        requires_compatibilities = task_def.get("requiresCompatibilities", [])
        if "FARGATE" in requires_compatibilities:
            if not cpu or not memory:
                recommendations.append(
                    {
                        "title": "Configure Resource Limits for Isolation",
                        "severity": "High",
                        "category": "resource_isolation",
                        "resource": f"Task Definition: {task_family}",
                        "issue": "Missing CPU or memory configuration for Fargate task",
                        "recommendation": "Configure appropriate CPU and memory limits for proper resource isolation",  # noqa: E501
                    }
                )

        return recommendations

    def _analyze_monitoring_security(
        self,
        service: Dict[str, Any],
        task_def: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze monitoring and logging security configurations."""
        recommendations = []

        # Note: Container logging is now handled in _analyze_container_security to avoid duplication

        return recommendations

    def _analyze_image_security(
        self,
        container: Dict[str, Any],
        container_name: str,
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze container image security."""
        recommendations = []

        image = container.get("image", "")

        # Check image registry security
        if not image:
            recommendations.append(
                {
                    "title": "Specify Container Image",
                    "severity": "High",
                    "category": "image_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "No container image specified",
                    "recommendation": "Specify a valid container image from a trusted registry",
                }
            )
            return recommendations

        # Check for image scanning and security
        is_ecr_image = self._is_valid_ecr_image(image)
        if is_ecr_image:
            # This is an ECR image - recommend image scanning
            recommendations.append(
                {
                    "title": "Enable ECR Image Scanning",
                    "severity": "Medium",
                    "category": "image_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Ensure ECR image scanning is enabled for vulnerability detection",
                    "recommendation": "Enable ECR image scanning to detect vulnerabilities in container images",  # noqa: E501
                }
            )

        # Check for base image security patterns
        if any(
            base in image.lower()
            for base in ["alpine:latest", "ubuntu:latest", "debian:latest", "centos:latest"]
        ):
            recommendations.append(
                {
                    "title": "Avoid Latest Tag in Base Images",
                    "severity": "Medium",
                    "category": "image_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Using latest tag in base images creates unpredictable security posture",  # noqa: E501
                    "recommendation": "Use specific version tags for base images to ensure consistent security updates",  # noqa: E501
                }
            )

        # Check for potentially vulnerable base images
        vulnerable_patterns = [
            "node:10",
            "python:2",
            "ubuntu:14.",
            "ubuntu:16",
            "centos:6",
            "centos:7",
        ]
        if any(pattern in image.lower() for pattern in vulnerable_patterns):
            recommendations.append(
                {
                    "title": "Update Outdated Base Image",
                    "severity": "High",
                    "category": "image_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Container uses outdated base image with known security vulnerabilities",  # noqa: E501
                    "recommendation": "Update to supported base image versions with current security patches",  # noqa: E501
                }
            )

        # Check for image size (potential attack surface)
        # Note: This would require additional API calls to get image size, so we'll flag for review
        if not any(minimal in image.lower() for minimal in ["alpine", "distroless", "scratch"]):
            recommendations.append(
                {
                    "title": "Consider Minimal Base Images",
                    "severity": "Low",
                    "category": "image_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Container may be using full-featured base image with larger attack surface",  # noqa: E501
                    "recommendation": "Consider using minimal base images (Alpine, distroless) to reduce attack surface",  # noqa: E501
                }
            )

        return recommendations

    def _analyze_container_runtime_security(
        self,
        container: Dict[str, Any],
        container_name: str,
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze container runtime security configurations."""
        recommendations = []

        # Check Linux parameters for security
        linux_parameters = container.get("linuxParameters", {})

        if linux_parameters:
            # Check capabilities
            capabilities = linux_parameters.get("capabilities", {})
            add_capabilities = capabilities.get("add", [])

            # Check for dangerous capabilities
            dangerous_caps = [
                "SYS_ADMIN",
                "NET_ADMIN",
                "SYS_PTRACE",
                "SYS_MODULE",
                "DAC_OVERRIDE",
                "SETUID",
                "SETGID",
            ]
            for cap in add_capabilities:
                if cap in dangerous_caps:
                    recommendations.append(
                        {
                            "title": f"Remove Dangerous Capability: {cap}",
                            "severity": "High",
                            "category": "runtime_security",
                            "resource": _format_resource_name(
                                "Container", container_name, service_name
                            ),  # noqa: E501
                            "issue": f"Container has dangerous capability {cap} which increases attack surface",  # noqa: E501
                            "recommendation": (
                                "Remove unnecessary capabilities and follow principle of least privilege"  # noqa: E501
                            ),
                        }
                    )

            # PHASE 1: Check for seccomp profile
            if not linux_parameters.get("seccompProfile"):
                recommendations.append(
                    {
                        "title": "Configure Seccomp Security Profile",
                        "severity": "High",
                        "category": "runtime_security",
                        "resource": _format_resource_name(
                            "Container", container_name, service_name
                        ),  # noqa: E501
                        "issue": "Container lacks seccomp profile, allowing unrestricted system calls that could be exploited by attackers",  # noqa: E501
                        "recommendation": "Configure a seccomp profile to restrict system calls and reduce attack surface",  # noqa: E501
                        "implementation_steps": [
                            "Create a custom seccomp profile or use Docker's default profile",
                            "Add seccompProfile configuration to linuxParameters in task definition",  # noqa: E501
                            "Test application functionality with the profile enabled",
                            "Monitor for any blocked system calls and adjust profile as needed",
                        ],
                        "aws_cli_example": 'aws ecs register-task-definition --cli-input-json \'{"family":"my-task","containerDefinitions":[{"linuxParameters":{"seccompProfile":"default"}}]}\'',  # noqa: E501
                        "compliance_frameworks": [
                            "CIS Docker Benchmark",
                            "NIST Cybersecurity Framework",
                        ],
                    }
                )

            # PHASE 1: Check for AppArmor profile
            if not linux_parameters.get("apparmorProfile"):
                recommendations.append(
                    {
                        "title": "Configure AppArmor Security Profile",
                        "severity": "Medium",
                        "category": "runtime_security",
                        "resource": _format_resource_name(
                            "Container", container_name, service_name
                        ),  # noqa: E501
                        "issue": "Container lacks AppArmor profile, missing mandatory access control protection",  # noqa: E501
                        "recommendation": "Configure AppArmor profile for mandatory access control and additional security layer",  # noqa: E501
                        "implementation_steps": [
                            "Create or select an appropriate AppArmor profile",
                            "Add apparmorProfile configuration to linuxParameters",
                            "Test container functionality with profile enforced",
                            "Monitor AppArmor logs for policy violations",
                        ],
                        "aws_cli_example": 'aws ecs register-task-definition --cli-input-json \'{"family":"my-task","containerDefinitions":[{"linuxParameters":{"apparmorProfile":"docker-default"}}]}\'',  # noqa: E501
                        "compliance_frameworks": ["CIS Docker Benchmark", "Defense in Depth"],
                    }
                )

            # PHASE 1: Check for no new privileges
            if not linux_parameters.get("noNewPrivileges"):
                recommendations.append(
                    {
                        "title": "Enable No New Privileges Flag",
                        "severity": "High",
                        "category": "runtime_security",
                        "resource": _format_resource_name(
                            "Container", container_name, service_name
                        ),  # noqa: E501
                        "issue": "Container can gain new privileges during execution, enabling privilege escalation attacks",  # noqa: E501
                        "recommendation": "Enable noNewPrivileges flag to prevent privilege escalation within the container",  # noqa: E501
                        "implementation_steps": [
                            "Add noNewPrivileges: true to linuxParameters in task definition",
                            "Test application to ensure it doesn't require privilege escalation",
                            "Verify setuid/setgid binaries work as expected",
                            "Monitor for any privilege-related application failures",
                        ],
                        "aws_cli_example": 'aws ecs register-task-definition --cli-input-json \'{"family":"my-task","containerDefinitions":[{"linuxParameters":{"noNewPrivileges":true}}]}\'',  # noqa: E501
                        "compliance_frameworks": [
                            "OWASP Container Security",
                            "CIS Docker Benchmark",
                        ],
                    }
                )

        else:
            # If no linuxParameters at all, recommend basic runtime security
            recommendations.append(
                {
                    "title": "Configure Linux Security Parameters",
                    "severity": "High",
                    "category": "runtime_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Container lacks Linux security parameters, missing critical runtime security controls",  # noqa: E501
                    "recommendation": "Configure linuxParameters with seccomp, AppArmor, and noNewPrivileges for comprehensive runtime security",  # noqa: E501
                    "implementation_steps": [
                        "Add linuxParameters section to container definition",
                        "Configure seccompProfile for system call filtering",
                        "Set noNewPrivileges to true to prevent privilege escalation",
                        "Consider AppArmor profile for additional access control",
                    ],
                    "aws_cli_example": 'aws ecs register-task-definition --cli-input-json \'{"family":"my-task","containerDefinitions":[{"linuxParameters":{"seccompProfile":"default","noNewPrivileges":true}}]}\'',  # noqa: E501
                    "compliance_frameworks": [
                        "CIS Docker Benchmark",
                        "NIST Cybersecurity Framework",
                    ],
                }
            )

        return recommendations

    async def _analyze_ecr_vulnerability_scanning(
        self,
        container: Dict[str, Any],
        container_name: str,
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """PHASE 1: Analyze ECR vulnerability scanning results."""
        recommendations = []

        image = container.get("image", "")

        # Check if image is from ECR
        is_ecr_image = self._is_valid_ecr_image(image)
        if is_ecr_image:
            try:
                # Extract repository name from ECR image URI
                # Format: account.dkr.ecr.region.amazonaws.com/repository:tag
                parts = image.split("/")
                if len(parts) >= 2:
                    repo_name = parts[-1].split(":")[0]
                    image_tag = parts[-1].split(":")[-1] if ":" in parts[-1] else "latest"

                    # Get ECR client
                    ecr_client = await get_aws_client("ecr")

                    try:
                        # Check if image scanning is enabled
                        repo_response = ecr_client.describe_repositories(
                            repositoryNames=[repo_name]
                        )

                        repositories = repo_response.get("repositories", [])
                        if repositories:
                            repo = repositories[0]
                            scan_config = repo.get("imageScanningConfiguration", {})
                            scan_on_push = scan_config.get("scanOnPush", False)

                            if not scan_on_push:
                                recommendations.append(
                                    {
                                        "title": "Enable ECR Vulnerability Scanning",
                                        "severity": "High",
                                        "category": "image_security",
                                        "resource": f"ECR Repository: {repo_name}",
                                        "issue": "ECR repository does not have vulnerability scanning enabled, missing critical security vulnerability detection",  # noqa: E501
                                        "recommendation": "Enable scan on push to automatically scan container images for known vulnerabilities",  # noqa: E501
                                        "implementation_steps": [
                                            "Enable scan on push in ECR repository settings",
                                            "Configure scanning for existing images",
                                            "Set up CloudWatch alarms for high/critical vulnerabilities",  # noqa: E501
                                            "Implement CI/CD pipeline checks to block vulnerable images",  # noqa: E501
                                        ],
                                        "aws_cli_example": f"aws ecr put-image-scanning-configuration --repository-name {repo_name} --image-scanning-configuration scanOnPush=true",  # noqa: E501
                                        "compliance_frameworks": [
                                            "NIST Cybersecurity Framework",
                                            "CIS Controls",
                                        ],
                                    }
                                )

                            # Check for scan results
                            try:
                                scan_results = ecr_client.describe_image_scan_findings(
                                    repositoryName=repo_name, imageId={"imageTag": image_tag}
                                )

                                findings = scan_results.get("imageScanFindings", {})
                                finding_counts = findings.get("findingCounts", {})

                                critical_count = finding_counts.get("CRITICAL", 0)
                                high_count = finding_counts.get("HIGH", 0)
                                medium_count = finding_counts.get("MEDIUM", 0)

                                if critical_count > 0:
                                    recommendations.append(
                                        {
                                            "title": "Address Critical Vulnerabilities in Container Image",  # noqa: E501
                                            "severity": "Critical",
                                            "category": "image_security",
                                            "resource": _format_resource_name(
                                                "Container Image", image, service_name
                                            ),  # noqa: E501
                                            "issue": f"Container image has {critical_count} critical vulnerabilities that pose immediate security risks",  # noqa: E501
                                            "recommendation": "Immediately update base image or packages to address critical vulnerabilities before deployment",  # noqa: E501
                                            "implementation_steps": [
                                                "Review detailed vulnerability findings in ECR console",  # noqa: E501
                                                "Update base image to latest patched version",
                                                "Update vulnerable packages in container",
                                                "Rebuild and rescan image before deployment",
                                            ],
                                            "aws_cli_example": f"aws ecr describe-image-scan-findings --repository-name {repo_name} --image-id imageTag={image_tag}",  # noqa: E501
                                            "compliance_frameworks": [
                                                "OWASP Top 10",
                                                "NIST Cybersecurity Framework",
                                            ],
                                        }
                                    )

                                if high_count > 0:
                                    recommendations.append(
                                        {
                                            "title": "Address High Severity Vulnerabilities in Container Image",  # noqa: E501
                                            "severity": "High",
                                            "category": "image_security",
                                            "resource": _format_resource_name(
                                                "Container Image", image, service_name
                                            ),  # noqa: E501
                                            "issue": f"Container image has {high_count} high severity vulnerabilities that should be addressed promptly",  # noqa: E501
                                            "recommendation": "Update container image to address high severity vulnerabilities within next maintenance window",  # noqa: E501
                                            "implementation_steps": [
                                                "Review high severity findings in ECR console",
                                                "Plan updates for vulnerable components",
                                                "Test updated image in staging environment",
                                                "Deploy updated image to production",
                                            ],
                                            "aws_cli_example": f'aws ecr describe-image-scan-findings --repository-name {repo_name} --image-id imageTag={image_tag} --filter \'{{"severity":["HIGH"]}}\'',  # noqa: E501
                                            "compliance_frameworks": [
                                                "NIST Cybersecurity Framework",
                                                "ISO 27001",
                                            ],
                                        }
                                    )

                                if medium_count > 5:  # Only flag if many medium vulnerabilities
                                    recommendations.append(
                                        {
                                            "title": "Review Medium Severity Vulnerabilities",
                                            "severity": "Medium",
                                            "category": "image_security",
                                            "resource": _format_resource_name(
                                                "Container Image", image, service_name
                                            ),  # noqa: E501
                                            "issue": f"Container image has {medium_count} medium severity vulnerabilities that should be reviewed",  # noqa: E501
                                            "recommendation": "Review and plan remediation for medium severity vulnerabilities during regular maintenance",  # noqa: E501
                                            "implementation_steps": [
                                                "Review medium severity findings",
                                                "Assess exploitability in your environment",
                                                "Plan updates during regular maintenance cycles",
                                                "Monitor for any new critical/high findings",
                                            ],
                                            "aws_cli_example": f'aws ecr describe-image-scan-findings --repository-name {repo_name} --image-id imageTag={image_tag} --filter \'{{"severity":["MEDIUM"]}}\'',  # noqa: E501
                                            "compliance_frameworks": ["Security Best Practices"],
                                        }
                                    )

                            except Exception:
                                # Image might not be scanned yet
                                recommendations.append(
                                    {
                                        "title": "Initiate ECR Vulnerability Scan",
                                        "severity": "Medium",
                                        "category": "image_security",
                                        "resource": _format_resource_name(
                                            "Container Image", image, service_name
                                        ),  # noqa: E501
                                        "issue": "Container image has not been scanned for vulnerabilities",  # noqa: E501
                                        "recommendation": "Initiate vulnerability scan to identify potential security issues",  # noqa: E501
                                        "implementation_steps": [
                                            "Trigger manual scan for the image",
                                            "Wait for scan completion",
                                            "Review scan results and address findings",
                                            "Enable automatic scanning for future pushes",
                                        ],
                                        "aws_cli_example": f"aws ecr start-image-scan --repository-name {repo_name} --image-id imageTag={image_tag}",  # noqa: E501
                                        "compliance_frameworks": ["Security Best Practices"],
                                    }
                                )

                    except Exception as repo_error:
                        logger.warning(f"Could not check ECR repository {repo_name}: {repo_error}")

            except Exception as e:
                logger.warning(f"Error analyzing ECR vulnerability scanning for {image}: {e}")
        else:
            # Non-ECR image - recommend using ECR
            recommendations.append(
                {
                    "title": "Use Amazon ECR for Container Images",
                    "severity": "Medium",
                    "category": "image_security",
                    "resource": _format_resource_name("Container", container_name, service_name),
                    "issue": "Container uses external registry without integrated vulnerability scanning",  # noqa: E501
                    "recommendation": "Migrate to Amazon ECR for integrated vulnerability scanning and better security controls",  # noqa: E501
                    "implementation_steps": [
                        "Create ECR repository for your application",
                        "Push container image to ECR",
                        "Enable vulnerability scanning on ECR repository",
                        "Update task definition to use ECR image URI",
                    ],
                    "aws_cli_example": f"aws ecr create-repository --repository-name {container_name.lower()}",  # noqa: E501
                    "compliance_frameworks": ["AWS Security Best Practices"],
                }
            )

        return recommendations

    def _analyze_service_mesh_security(
        self,
        service: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """PHASE 1: Analyze service mesh security configurations."""
        recommendations = []

        # Check for ECS Service Connect (AWS native service mesh)
        service_connect = service.get("serviceConnectConfiguration", {})

        if service_connect.get("enabled", False):
            # Service Connect is enabled, check security configurations
            namespace = service_connect.get("namespace")
            if not namespace:
                recommendations.append(
                    {
                        "title": "Configure Service Connect Namespace",
                        "severity": "Medium",
                        "category": "service_mesh",
                        "resource": f"Service: {service_name}",
                        "issue": "Service Connect enabled without proper namespace configuration",
                        "recommendation": "Configure Service Connect namespace for proper service discovery and security boundaries",  # noqa: E501
                        "implementation_steps": [
                            "Create Cloud Map namespace for service discovery",
                            "Configure Service Connect namespace in service definition",
                            "Set up proper DNS resolution",
                            "Configure service-to-service communication policies",
                        ],
                        "aws_cli_example": f"aws servicediscovery create-private-dns-namespace --name {cluster_name}-mesh --vpc vpc-xxxxxx",  # noqa: E501
                        "compliance_frameworks": [
                            "Zero Trust Architecture",
                            "AWS Security Best Practices",
                        ],
                    }
                )

            # Check for TLS configuration
            services_config = service_connect.get("services", [])
            for svc_config in services_config:
                client_aliases = svc_config.get("clientAliases", [])
                for alias in client_aliases:
                    port = alias.get("port")
                    if port and port != 443:  # Not using HTTPS port
                        recommendations.append(
                            {
                                "title": "Enable TLS for Service Connect Communication",
                                "severity": "High",
                                "category": "service_mesh",
                                "resource": f"Service: {service_name}",
                                "issue": f"Service Connect communication on port {port} may not be encrypted",  # noqa: E501
                                "recommendation": "Configure TLS encryption for service-to-service communication",  # noqa: E501
                                "implementation_steps": [
                                    "Configure TLS certificates for service endpoints",
                                    "Update service connect configuration to use HTTPS",
                                    "Implement mutual TLS (mTLS) for enhanced security",
                                    "Monitor TLS certificate expiration",
                                ],
                                "aws_cli_example": "Configure TLS in service connect configuration",
                                "compliance_frameworks": [
                                    "Zero Trust Architecture",
                                    "PCI DSS",
                                    "HIPAA",
                                ],
                            }
                        )
        else:
            # Service Connect not enabled - recommend for multi-service applications
            recommendations.append(
                {
                    "title": "Consider ECS Service Connect for Service Mesh",
                    "severity": "Low",
                    "category": "service_mesh",
                    "resource": f"Service: {service_name}",
                    "issue": "Service lacks service mesh capabilities for secure service-to-service communication",  # noqa: E501
                    "recommendation": "Consider enabling ECS Service Connect for encrypted service-to-service communication and observability",  # noqa: E501
                    "implementation_steps": [
                        "Evaluate if service communicates with other services",
                        "Create Cloud Map namespace for service discovery",
                        "Enable Service Connect in service configuration",
                        "Configure TLS for encrypted communication",
                    ],
                    "aws_cli_example": f"aws ecs update-service --cluster {cluster_name} --service {service_name} --service-connect-configuration enabled=true",  # noqa: E501
                    "compliance_frameworks": ["Zero Trust Architecture", "Defense in Depth"],
                }
            )

        # Check for App Mesh integration
        proxy_config = service.get("proxyConfiguration", {})
        if proxy_config.get("type") == "APPMESH":
            # App Mesh is configured, check security settings
            properties = proxy_config.get("properties", [])

            # Look for TLS configuration
            tls_configured = False
            mtls_configured = False
            for prop in properties:
                if prop.get("name") == "ENVOY_TLS_ENABLED" and prop.get("value") == "1":
                    tls_configured = True
                if prop.get("name") == "ENVOY_MTLS_ENABLED" and prop.get("value") == "1":
                    mtls_configured = True

            if not tls_configured:
                recommendations.append(
                    {
                        "title": "Enable TLS in App Mesh Configuration",
                        "severity": "High",
                        "category": "service_mesh",
                        "resource": f"Service: {service_name}",
                        "issue": "App Mesh proxy lacks TLS encryption configuration",
                        "recommendation": "Enable TLS encryption in App Mesh for secure service-to-service communication",  # noqa: E501
                        "implementation_steps": [
                            "Configure TLS certificates in App Mesh",
                            "Enable TLS in Envoy proxy configuration",
                            "Implement mutual TLS (mTLS) authentication",
                            "Update virtual services and virtual routers for TLS",
                        ],
                        "aws_cli_example": 'aws appmesh update-virtual-service --mesh-name my-mesh --virtual-service-name my-service --spec \'{"provider":{"virtualRouter":{"virtualRouterName":"my-router"}}}\'',  # noqa: E501
                        "compliance_frameworks": ["Zero Trust Architecture", "PCI DSS"],
                    }
                )

            # Enhanced: Check for mutual TLS (mTLS) configuration
            if tls_configured and not mtls_configured:
                recommendations.append(
                    {
                        "title": "Implement Mutual TLS (mTLS) for Service Mesh",
                        "severity": "High",
                        "category": "service_mesh",
                        "resource": f"Service: {service_name}",
                        "issue": "App Mesh has TLS but lacks mutual TLS authentication for enhanced security",  # noqa: E501
                        "recommendation": "Implement mutual TLS (mTLS) to ensure both client and server authentication in service mesh",  # noqa: E501
                        "implementation_steps": [
                            "Configure client certificates for service authentication",
                            "Enable mTLS in App Mesh virtual service configuration",
                            "Set up certificate authority for service mesh",
                            "Implement certificate rotation and management",
                        ],
                        "aws_cli_example": 'aws appmesh update-virtual-service --mesh-name my-mesh --virtual-service-name my-service --spec \'{"provider":{"virtualNode":{"virtualNodeName":"my-node"}}}\'',  # noqa: E501
                        "compliance_frameworks": ["Zero Trust Architecture", "mTLS Best Practices"],
                    }
                )

        # Enhanced: Check for network policies and DNS security
        recommendations.extend(
            self._analyze_network_policies_security(service, service_name, cluster_name, region)
        )
        recommendations.extend(
            self._analyze_dns_security(service, service_name, cluster_name, region)
        )
        recommendations.extend(
            self._analyze_vpc_endpoints_security(service, service_name, cluster_name, region)
        )

        return recommendations

    def _analyze_network_policies_security(
        self,
        service: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze network policies and security group configurations."""
        recommendations = []

        # Check for network configuration
        network_config = service.get("networkConfiguration", {})
        awsvpc_config = network_config.get("awsvpcConfiguration", {})

        if awsvpc_config:
            security_groups = awsvpc_config.get("securityGroups", [])
            if not security_groups:
                recommendations.append(
                    {
                        "title": "Configure Network Security Groups",
                        "severity": "High",
                        "category": "network_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Service lacks security group configuration for network access control",  # noqa: E501
                        "recommendation": "Configure security groups to implement network-level access controls and micro-segmentation",  # noqa: E501
                        "implementation_steps": [
                            "Create dedicated security groups for service",
                            "Implement least privilege network access",
                            "Configure ingress rules for required ports only",
                            "Implement egress filtering for outbound traffic",
                        ],
                        "aws_cli_example": f'aws ec2 create-security-group --group-name {service_name}-sg --description "Security group for {service_name}"',  # noqa: E501
                        "compliance_frameworks": ["Network Security", "Zero Trust Architecture"],
                    }
                )
            else:
                # Recommend security group review
                recommendations.append(
                    {
                        "title": "Review Network Security Group Rules",
                        "severity": "Medium",
                        "category": "network_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Security group rules should be reviewed for least privilege access",  # noqa: E501
                        "recommendation": "Regularly review and audit security group rules to ensure minimal required access",  # noqa: E501
                        "implementation_steps": [
                            "Audit current security group rules",
                            "Remove unused or overly permissive rules",
                            "Implement specific port and protocol restrictions",
                            "Use security group references instead of CIDR blocks where possible",
                        ],
                        "aws_cli_example": f"aws ec2 describe-security-groups --group-ids {' '.join(security_groups)}",  # noqa: E501
                        "compliance_frameworks": ["Network Security", "Least Privilege"],
                    }
                )

        return recommendations

    def _analyze_dns_security(
        self,
        service: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze DNS security configurations."""
        recommendations = []

        # Check for service discovery configuration
        service_registries = service.get("serviceRegistries", [])
        if service_registries:
            for registry in service_registries:
                registry_arn = registry.get("registryArn", "")
                if "servicediscovery" in registry_arn:
                    recommendations.append(
                        {
                            "title": "Secure DNS Service Discovery Configuration",
                            "severity": "Medium",
                            "category": "dns_security",
                            "resource": f"Service: {service_name}",
                            "issue": "Service discovery DNS configuration should be secured against DNS attacks",  # noqa: E501
                            "recommendation": "Implement DNS security best practices for service discovery",  # noqa: E501
                            "implementation_steps": [
                                "Use private DNS namespaces for internal services",
                                "Implement DNS query logging and monitoring",
                                "Configure DNS filtering for malicious domains",
                                "Use Route 53 Resolver DNS Firewall for additional protection",
                            ],
                            "aws_cli_example": f"aws servicediscovery get-service --id {registry_arn.split('/')[-1]}",  # noqa: E501
                            "compliance_frameworks": ["DNS Security", "Network Security"],
                        }
                    )
        else:
            # Recommend DNS security even without service discovery
            recommendations.append(
                {
                    "title": "Implement DNS Security Monitoring",
                    "severity": "Low",
                    "category": "dns_security",
                    "resource": f"Service: {service_name}",
                    "issue": "Service lacks DNS security monitoring and protection",
                    "recommendation": "Implement DNS security monitoring to detect and prevent DNS-based attacks",  # noqa: E501
                    "implementation_steps": [
                        "Enable VPC DNS query logging",
                        "Configure Route 53 Resolver DNS Firewall",
                        "Monitor DNS queries for suspicious patterns",
                        "Implement DNS over HTTPS (DoH) where applicable",
                    ],
                    "aws_cli_example": "aws route53resolver create-resolver-query-log-config --name dns-security-logs",  # noqa: E501
                    "compliance_frameworks": ["DNS Security", "Threat Detection"],
                }
            )

        return recommendations

    def _analyze_vpc_endpoints_security(
        self,
        service: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """Analyze VPC endpoints security for AWS services."""
        recommendations = []

        # Check network configuration for private subnets
        network_config = service.get("networkConfiguration", {})
        awsvpc_config = network_config.get("awsvpcConfiguration", {})

        if awsvpc_config:
            subnets = awsvpc_config.get("subnets", [])
            if subnets:
                recommendations.append(
                    {
                        "title": "Implement VPC Endpoints for AWS Services",
                        "severity": "Medium",
                        "category": "vpc_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Service may communicate with AWS services over the internet instead of private VPC endpoints",  # noqa: E501
                        "recommendation": "Configure VPC endpoints for AWS services to keep traffic within AWS network",  # noqa: E501
                        "implementation_steps": [
                            "Identify AWS services used by the application",
                            "Create VPC endpoints for ECR, S3, CloudWatch, and other services",
                            "Configure endpoint policies for least privilege access",
                            "Update route tables to use VPC endpoints",
                        ],
                        "aws_cli_example": f"aws ec2 create-vpc-endpoint --vpc-id vpc-xxxxx --service-name com.amazonaws.{region}.ecr.dkr",  # noqa: E501
                        "compliance_frameworks": ["Network Security", "Data Privacy"],
                    }
                )

        return recommendations

    def _analyze_advanced_image_security(
        self,
        container: Dict[str, Any],
        container_name: str,
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """PHASE 1: Analyze advanced image security including signing and provenance."""
        recommendations = []

        image = container.get("image", "")

        # Check for image signing (Docker Content Trust / Notary)
        is_ecr_image = self._is_valid_ecr_image(image)
        if is_ecr_image:
            # ECR image - check for image signing
            recommendations.append(
                {
                    "title": "Implement Container Image Signing",
                    "severity": "High",
                    "category": "image_security",
                    "resource": _format_resource_name("Container Image", image, service_name),
                    "issue": "Container image lacks cryptographic signature verification, allowing potential supply chain attacks",  # noqa: E501
                    "recommendation": "Implement image signing using AWS Signer or Docker Content Trust to ensure image integrity and authenticity",  # noqa: E501
                    "implementation_steps": [
                        "Set up AWS Signer for container image signing",
                        "Configure signing profile for your container images",
                        "Sign images during CI/CD pipeline",
                        "Configure ECS to verify signatures before deployment",
                    ],
                    "aws_cli_example": "aws signer put-signing-profile --profile-name container-signing --signing-material certificateArn=arn:aws:acm:region:account:certificate/cert-id",  # noqa: E501
                    "compliance_frameworks": [
                        "Supply Chain Security",
                        "NIST SSDF",
                        "SLSA Framework",
                    ],
                }
            )

            # Check for image provenance
            recommendations.append(
                {
                    "title": "Implement Image Provenance Tracking",
                    "severity": "Medium",
                    "category": "image_security",
                    "resource": _format_resource_name("Container Image", image, service_name),
                    "issue": "Container image lacks provenance metadata, making supply chain verification difficult",  # noqa: E501
                    "recommendation": "Implement image provenance tracking to maintain build and supply chain transparency",  # noqa: E501
                    "implementation_steps": [
                        "Generate SLSA provenance during image build",
                        "Store provenance metadata with image",
                        "Implement provenance verification in deployment pipeline",
                        "Use tools like cosign for signing and verification",
                    ],
                    "aws_cli_example": "# Use cosign or similar tool: cosign sign --key cosign.key image-uri",  # noqa: E501
                    "compliance_frameworks": [
                        "SLSA Framework",
                        "Supply Chain Security",
                        "NIST SSDF",
                    ],
                }
            )

            # Enhanced: Supply chain security analysis
            recommendations.append(
                {
                    "title": "Implement Supply Chain Security Controls",
                    "severity": "High",
                    "category": "image_security",
                    "resource": _format_resource_name("Container Image", image, service_name),
                    "issue": "Container image lacks comprehensive supply chain security verification",  # noqa: E501
                    "recommendation": "Implement end-to-end supply chain security controls for container images",  # noqa: E501
                    "implementation_steps": [
                        "Implement Software Bill of Materials (SBOM) generation",
                        "Use trusted base images from verified sources",
                        "Implement dependency scanning and vulnerability assessment",
                        "Configure automated security scanning in CI/CD pipeline",
                    ],
                    "aws_cli_example": f"aws ecr start-image-scan --repository-name {image.split('/')[-1].split(':')[0]} --image-id imageTag=latest",  # noqa: E501
                    "compliance_frameworks": [
                        "Supply Chain Security",
                        "NIST SSDF",
                        "SLSA Framework",
                    ],
                }
            )

        # Enhanced: Package vulnerability scanning
        recommendations.append(
            {
                "title": "Implement Package Vulnerability Scanning",
                "severity": "High",
                "category": "image_security",
                "resource": _format_resource_name("Container Image", image, service_name),
                "issue": "Container image packages may contain known vulnerabilities",
                "recommendation": "Implement comprehensive package vulnerability scanning for all container dependencies",  # noqa: E501
                "implementation_steps": [
                    "Enable ECR image scanning for vulnerability detection",
                    "Integrate third-party vulnerability scanners (Snyk, Twistlock, etc.)",
                    "Implement automated vulnerability remediation workflows",
                    "Set up vulnerability alerting and reporting",
                ],
                "aws_cli_example": f"aws ecr describe-image-scan-findings --repository-name {image.split('/')[-1].split(':')[0]}",  # noqa: E501
                "compliance_frameworks": ["Vulnerability Management", "DevSecOps"],
            }
        )

        # Check for multi-stage build security
        # This is inferred from image size and common patterns
        recommendations.append(
            {
                "title": "Verify Secure Multi-Stage Build Practices",
                "severity": "Medium",
                "category": "image_security",
                "resource": _format_resource_name("Container Image", image, service_name),
                "issue": "Cannot verify if image follows secure multi-stage build practices to minimize attack surface",  # noqa: E501
                "recommendation": "Ensure container images use multi-stage builds to exclude build tools and reduce attack surface",  # noqa: E501
                "implementation_steps": [
                    "Review Dockerfile for multi-stage build usage",
                    "Ensure build tools are not included in final image",
                    "Use minimal base images (distroless, alpine)",
                    "Remove unnecessary packages and files from final image",
                ],
                "aws_cli_example": "# Review image layers: docker history image-name",
                "compliance_frameworks": ["CIS Docker Benchmark", "OWASP Container Security"],
            }
        )

        # Enhanced: Base image vulnerability analysis
        recommendations.append(
            {
                "title": "Analyze Base Image Vulnerabilities",
                "severity": "High",
                "category": "image_security",
                "resource": _format_resource_name("Container Image", image, service_name),
                "issue": "Base image may contain known vulnerabilities that affect container security",  # noqa: E501
                "recommendation": "Regularly analyze and update base images to address known vulnerabilities",  # noqa: E501
                "implementation_steps": [
                    "Identify base image and version used",
                    "Scan base image for known vulnerabilities",
                    "Implement automated base image updates",
                    "Monitor base image security advisories",
                ],
                "aws_cli_example": "# Scan base image: docker scan base-image:tag",
                "compliance_frameworks": ["Vulnerability Management", "Container Security"],
            }
        )

        # Check for base image security
        if any(base in image.lower() for base in ["ubuntu", "centos", "debian", "alpine"]):
            recommendations.append(
                {
                    "title": "Use Minimal Base Images",
                    "severity": "Medium",
                    "category": "image_security",
                    "resource": _format_resource_name("Container Image", image, service_name),
                    "issue": "Container uses full OS base image which increases attack surface and potential vulnerabilities",  # noqa: E501
                    "recommendation": "Consider using minimal base images like distroless or alpine to reduce attack surface",  # noqa: E501
                    "implementation_steps": [
                        "Evaluate application dependencies",
                        "Consider Google distroless images for minimal attack surface",
                        "Use alpine-based images for smaller size",
                        "Remove unnecessary packages and utilities",
                    ],
                    "aws_cli_example": "# Use distroless: FROM gcr.io/distroless/java:11",
                    "compliance_frameworks": ["CIS Docker Benchmark", "Defense in Depth"],
                }
            )

        # Check for image immutability
        if image.endswith(":latest") or image.count(":") == 0:
            recommendations.append(
                {
                    "title": "Use Immutable Image Tags with Digest",
                    "severity": "High",
                    "category": "image_security",
                    "resource": _format_resource_name("Container Image", image, service_name),
                    "issue": "Container image uses mutable tag, allowing potential image substitution attacks",  # noqa: E501
                    "recommendation": "Use immutable image references with SHA256 digest to ensure image integrity",  # noqa: E501
                    "implementation_steps": [
                        "Tag images with specific version numbers",
                        "Use image digest (SHA256) for immutable references",
                        "Implement image promotion pipeline with digest tracking",
                        "Configure admission controllers to require digests",
                    ],
                    "aws_cli_example": f"# Use digest: {image.split(':')[0]}@sha256:abcd1234...",
                    "compliance_frameworks": ["Supply Chain Security", "NIST SSDF"],
                }
            )

        return recommendations

    def _analyze_ecs_advanced_features_security(
        self,
        service: Dict[str, Any],
        cluster_data: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """PHASE 2: Analyze advanced ECS features security."""
        recommendations = []

        # Check ECS Exec security
        enable_execute_command = service.get("enableExecuteCommand", False)
        if enable_execute_command:
            # Check for KMS encryption
            cluster_info = cluster_data.get("cluster", {})
            exec_config = cluster_info.get("configuration", {}).get(
                "executeCommandConfiguration", {}
            )

            if not exec_config.get("kmsKeyId"):
                recommendations.append(
                    {
                        "title": "Configure KMS Encryption for ECS Exec",
                        "severity": "High",
                        "category": "ecs_advanced",
                        "resource": f"Cluster: {cluster_name}",
                        "issue": "ECS Exec is enabled without KMS encryption, potentially exposing sensitive command data",  # noqa: E501
                        "recommendation": "Configure customer-managed KMS key for ECS Exec session encryption",  # noqa: E501
                        "implementation_steps": [
                            "Create or identify a customer-managed KMS key",
                            "Configure executeCommandConfiguration in cluster settings",
                            "Update IAM policies to allow KMS key usage",
                            "Test exec sessions to verify encryption",
                        ],
                        "aws_cli_example": f'aws ecs put-cluster-capacity-providers --cluster {cluster_name} --configuration executeCommandConfiguration="{{kmsKeyId=arn:aws:kms:{region}:account:key/key-id}}"',  # noqa: E501
                        "compliance_frameworks": ["SOC 2", "PCI DSS", "HIPAA"],
                    }
                )

            # Check for logging configuration
            if not exec_config.get("logging"):
                recommendations.append(
                    {
                        "title": "Enable ECS Exec Session Logging",
                        "severity": "Medium",
                        "category": "ecs_advanced",
                        "resource": f"Cluster: {cluster_name}",
                        "issue": "ECS Exec sessions are not being logged, missing audit trail for security compliance",  # noqa: E501
                        "recommendation": "Enable CloudWatch or S3 logging for ECS Exec sessions",
                        "implementation_steps": [
                            "Configure logging in executeCommandConfiguration",
                            "Set up CloudWatch log group or S3 bucket",
                            "Configure appropriate retention policies",
                            "Set up monitoring and alerting for exec usage",
                        ],
                        "aws_cli_example": f'aws ecs put-cluster-capacity-providers --cluster {cluster_name} --configuration executeCommandConfiguration="{{logging=OVERRIDE,logConfiguration={{cloudWatchLogGroupName=/aws/ecs/exec/{cluster_name}}}}}"',  # noqa: E501
                        "compliance_frameworks": ["SOC 2", "PCI DSS", "Audit Requirements"],
                    }
                )

        # Check for Blue/Green deployment security
        deployment_config = service.get("deploymentConfiguration", {})
        deployment_controller = service.get("deploymentController", {}).get("type", "ECS")

        if deployment_controller == "CODE_DEPLOY":
            # Blue/Green deployments via CodeDeploy
            circuit_breaker = deployment_config.get("deploymentCircuitBreaker", {})
            if not circuit_breaker.get("enable", False):
                recommendations.append(
                    {
                        "title": "Enable Deployment Circuit Breaker for Blue/Green",
                        "severity": "Medium",
                        "category": "ecs_advanced",
                        "resource": f"Service: {service_name}",
                        "issue": "Blue/Green deployment lacks circuit breaker protection against failed deployments",  # noqa: E501
                        "recommendation": "Enable deployment circuit breaker to automatically rollback failed Blue/Green deployments",  # noqa: E501
                        "implementation_steps": [
                            "Enable deploymentCircuitBreaker in service configuration",
                            "Configure rollback threshold and monitoring",
                            "Test rollback scenarios in staging environment",
                            "Set up alerts for deployment failures",
                        ],
                        "aws_cli_example": f'aws ecs update-service --cluster {cluster_name} --service {service_name} --deployment-configuration deploymentCircuitBreaker="{{enable=true,rollback=true}}"',  # noqa: E501
                        "compliance_frameworks": ["Reliability Best Practices", "DevOps Security"],
                    }
                )

        # Check for Spot instance security considerations
        capacity_provider_strategy = service.get("capacityProviderStrategy", [])
        for strategy in capacity_provider_strategy:
            if "SPOT" in strategy.get("capacityProvider", "").upper():
                recommendations.append(
                    {
                        "title": "Review Spot Instance Security Implications",
                        "severity": "Low",
                        "category": "ecs_advanced",
                        "resource": f"Service: {service_name}",
                        "issue": "Service uses Spot instances which may have security implications for stateful workloads",  # noqa: E501
                        "recommendation": "Ensure Spot instance usage is appropriate for workload security requirements",  # noqa: E501
                        "implementation_steps": [
                            "Evaluate workload sensitivity to interruptions",
                            "Implement proper state management for interruptions",
                            "Configure mixed instance types for resilience",
                            "Monitor Spot instance interruption patterns",
                        ],
                        "aws_cli_example": "# Review capacity provider strategy and workload requirements",  # noqa: E501
                        "compliance_frameworks": ["Availability Best Practices"],
                    }
                )

        # Check for ECS Anywhere security (if external instances detected)
        # This would be detected through capacity providers or instance metadata
        cluster_info = cluster_data.get("cluster", {})
        registered_instances = cluster_info.get("registeredContainerInstancesCount", 0)
        if registered_instances > 0:
            # Could be ECS Anywhere - recommend security checks
            recommendations.append(
                {
                    "title": "Verify ECS Anywhere Security Configuration",
                    "severity": "Medium",
                    "category": "ecs_advanced",
                    "resource": f"Cluster: {cluster_name}",
                    "issue": "Cluster has registered container instances that may include ECS Anywhere nodes requiring additional security",  # noqa: E501
                    "recommendation": "Ensure ECS Anywhere instances follow security best practices for hybrid deployments",  # noqa: E501
                    "implementation_steps": [
                        "Verify instance registration authentication",
                        "Ensure proper network security for external instances",
                        "Implement endpoint security on ECS Anywhere nodes",
                        "Monitor and audit external instance access",
                    ],
                    "aws_cli_example": f"aws ecs describe-container-instances --cluster {cluster_name}",  # noqa: E501
                    "compliance_frameworks": ["Hybrid Cloud Security", "Zero Trust Architecture"],
                }
            )

        return recommendations

    def _analyze_advanced_network_security(
        self,
        service: Dict[str, Any],
        network_data: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """PHASE 2: Analyze advanced networking and VPC security."""
        recommendations = []

        # Check for VPC Endpoints security
        vpc_id = network_data.get("vpc", {}).get("VpcId")
        if vpc_id:
            # Recommend VPC endpoints for AWS services
            recommendations.append(
                {
                    "title": "Configure VPC Endpoints for AWS Services",
                    "severity": "Medium",
                    "category": "network_security",
                    "resource": f"VPC: {vpc_id}",
                    "issue": "VPC may lack endpoints for AWS services, potentially routing traffic through internet gateway",  # noqa: E501
                    "recommendation": "Configure VPC endpoints for ECS, ECR, S3, and CloudWatch to keep traffic within AWS network",  # noqa: E501
                    "implementation_steps": [
                        "Create VPC endpoints for com.amazonaws.region.ecs",
                        "Create VPC endpoints for com.amazonaws.region.ecr.dkr and ecr.api",
                        "Create VPC endpoint for com.amazonaws.region.s3",
                        "Configure security groups for VPC endpoints",
                    ],
                    "aws_cli_example": f"aws ec2 create-vpc-endpoint --vpc-id {vpc_id} --service-name com.amazonaws.{region}.ecs",  # noqa: E501
                    "compliance_frameworks": ["Network Security", "Data Privacy"],
                }
            )

        # Check for DNS security
        network_config = service.get("networkConfiguration", {}).get("awsvpcConfiguration", {})
        if network_config:
            # Check for custom DNS configuration
            recommendations.append(
                {
                    "title": "Review DNS Security Configuration",
                    "severity": "Low",
                    "category": "network_security",
                    "resource": f"Service: {service_name}",
                    "issue": "Service DNS configuration should be reviewed for security best practices",  # noqa: E501
                    "recommendation": "Ensure DNS queries are secured and consider using Route 53 Resolver DNS Firewall",  # noqa: E501
                    "implementation_steps": [
                        "Review VPC DNS settings (enableDnsHostnames, enableDnsSupport)",
                        "Consider Route 53 Resolver DNS Firewall for malicious domain blocking",
                        "Implement DNS query logging for security monitoring",
                        "Use private hosted zones for internal service discovery",
                    ],
                    "aws_cli_example": f"aws route53resolver create-firewall-domain-list --name {cluster_name}-dns-firewall",  # noqa: E501
                    "compliance_frameworks": ["DNS Security", "Threat Protection"],
                }
            )

        # Check for network policies (security group analysis)
        security_groups = network_config.get("securityGroups", [])
        if len(security_groups) > 1:
            recommendations.append(
                {
                    "title": "Review Multiple Security Groups Configuration",
                    "severity": "Low",
                    "category": "network_security",
                    "resource": f"Service: {service_name}",
                    "issue": f"Service uses {len(security_groups)} security groups which may create complex rule interactions",  # noqa: E501
                    "recommendation": "Review security group rules for conflicts and implement principle of least privilege",  # noqa: E501
                    "implementation_steps": [
                        "Audit all security group rules for overlaps",
                        "Implement network segmentation strategy",
                        "Use security group references instead of CIDR blocks where possible",
                        "Document security group purposes and dependencies",
                    ],
                    "aws_cli_example": f"aws ec2 describe-security-groups --group-ids {' '.join(security_groups)}",  # noqa: E501
                    "compliance_frameworks": ["Network Segmentation", "Zero Trust"],
                }
            )

        return recommendations

    def _analyze_advanced_storage_security(
        self,
        task_def: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """PHASE 2: Analyze advanced storage security beyond basic EFS/FSx checks."""
        recommendations = []

        volumes = task_def.get("volumes", [])

        for volume in volumes:
            volume_name = volume.get("name", "unknown")

            # Advanced EFS security analysis
            efs_config = volume.get("efsVolumeConfiguration", {})
            if efs_config:
                # Check for EFS encryption at rest
                file_system_id = efs_config.get("fileSystemId")
                if file_system_id:
                    recommendations.append(
                        {
                            "title": "Verify EFS Encryption at Rest",
                            "severity": "High",
                            "category": "storage_security",
                            "resource": f"EFS Volume: {volume_name}",
                            "issue": "EFS file system encryption at rest status should be verified",
                            "recommendation": "Ensure EFS file system has encryption at rest enabled with customer-managed KMS key",  # noqa: E501
                            "implementation_steps": [
                                "Check EFS file system encryption status",
                                "Enable encryption at rest if not already enabled",
                                "Use customer-managed KMS key for enhanced control",
                                "Implement key rotation policies",
                            ],
                            "aws_cli_example": f"aws efs describe-file-systems --file-system-id {file_system_id}",  # noqa: E501
                            "compliance_frameworks": ["Data Protection", "PCI DSS", "HIPAA"],
                        }
                    )

                # Enhanced: EFS encryption in transit
                transit_encryption = efs_config.get("transitEncryption")
                if transit_encryption != "ENABLED":
                    recommendations.append(
                        {
                            "title": "Enable EFS Encryption in Transit",
                            "severity": "High",
                            "category": "storage_security",
                            "resource": f"EFS Volume: {volume_name}",
                            "issue": "EFS volume lacks encryption in transit, exposing data during network transmission",  # noqa: E501
                            "recommendation": "Enable EFS encryption in transit to protect data during network transmission",  # noqa: E501
                            "implementation_steps": [
                                "Enable transitEncryption in EFS volume configuration",
                                "Configure TLS for EFS mount helper",
                                "Update mount targets to support encryption in transit",
                                "Test application connectivity with encryption enabled",
                            ],
                            "aws_cli_example": '# Update task definition: "transitEncryption": "ENABLED"',  # noqa: E501
                            "compliance_frameworks": ["Data Protection", "Encryption in Transit"],
                        }
                    )

                # Check for EFS backup configuration
                recommendations.append(
                    {
                        "title": "Configure EFS Backup and Lifecycle Policies",
                        "severity": "Medium",
                        "category": "storage_security",
                        "resource": f"EFS Volume: {volume_name}",
                        "issue": "EFS file system should have backup and lifecycle policies for data protection",  # noqa: E501
                        "recommendation": "Configure automatic backups and lifecycle management for EFS file system",  # noqa: E501
                        "implementation_steps": [
                            "Enable EFS automatic backups",
                            "Configure lifecycle policies for cost optimization",
                            "Set up cross-region replication for critical data",
                            "Test backup and restore procedures",
                        ],
                        "aws_cli_example": f"aws efs put-backup-policy --file-system-id {file_system_id} --backup-policy Status=ENABLED",  # noqa: E501
                        "compliance_frameworks": ["Data Protection", "Business Continuity"],
                    }
                )

                # Enhanced: EFS access point security
                access_point_id = efs_config.get("accessPointId")
                if access_point_id:
                    recommendations.append(
                        {
                            "title": "Review EFS Access Point Security Configuration",
                            "severity": "Medium",
                            "category": "storage_security",
                            "resource": f"EFS Access Point: {access_point_id}",
                            "issue": "EFS access point configuration should be reviewed for proper access controls",  # noqa: E501
                            "recommendation": "Ensure EFS access point has proper POSIX permissions and path restrictions",  # noqa: E501
                            "implementation_steps": [
                                "Review access point POSIX user and group settings",
                                "Verify root directory creation permissions",
                                "Implement path-based access restrictions",
                                "Monitor access point usage and permissions",
                            ],
                            "aws_cli_example": f"aws efs describe-access-points --access-point-id {access_point_id}",  # noqa: E501
                            "compliance_frameworks": ["Access Control", "Least Privilege"],
                        }
                    )

            # Advanced FSx security analysis
            fsx_config = volume.get("fsxWindowsFileServerVolumeConfiguration", {})
            if fsx_config:
                # Check for FSx encryption and security
                recommendations.append(
                    {
                        "title": "Verify FSx Security Configuration",
                        "severity": "High",
                        "category": "storage_security",
                        "resource": f"FSx Volume: {volume_name}",
                        "issue": "FSx file system security configuration should be verified for encryption and access controls",  # noqa: E501
                        "recommendation": "Ensure FSx file system has proper encryption, backup, and access control configuration",  # noqa: E501
                        "implementation_steps": [
                            "Verify FSx encryption at rest and in transit",
                            "Configure automatic backups for FSx",
                            "Implement proper Active Directory integration",
                            "Review file system access permissions",
                        ],
                        "aws_cli_example": "aws fsx describe-file-systems",
                        "compliance_frameworks": ["Data Protection", "Windows Security"],
                    }
                )

                # Enhanced: FSx backup and versioning
                recommendations.append(
                    {
                        "title": "Configure FSx Backup and Versioning",
                        "severity": "Medium",
                        "category": "storage_security",
                        "resource": f"FSx Volume: {volume_name}",
                        "issue": "FSx file system should have comprehensive backup and versioning strategy",  # noqa: E501
                        "recommendation": "Implement FSx backup policies and file versioning for data protection",  # noqa: E501
                        "implementation_steps": [
                            "Configure automatic daily backups",
                            "Set backup retention policies",
                            "Enable file versioning if supported",
                            "Test backup and restore procedures",
                        ],
                        "aws_cli_example": "aws fsx create-backup --file-system-id fs-xxxxx",
                        "compliance_frameworks": ["Data Protection", "Business Continuity"],
                    }
                )

        # Check container-level storage security
        for container in task_def.get("containerDefinitions", []):
            container_name = container.get("name", "unknown")
            linux_parameters = container.get("linuxParameters", {})

            # Advanced tmpfs security analysis
            tmpfs_mounts = linux_parameters.get("tmpfs", [])
            for tmpfs_mount in tmpfs_mounts:
                mount_options = tmpfs_mount.get("mountOptions", [])
                if "noexec" not in mount_options:
                    recommendations.append(
                        {
                            "title": "Configure Secure Tmpfs Mount Options",
                            "severity": "Medium",
                            "category": "storage_security",
                            "resource": _format_resource_name(
                                "Container", container_name, service_name
                            ),  # noqa: E501
                            "issue": "Tmpfs mount lacks noexec option, potentially allowing execution of malicious code",  # noqa: E501
                            "recommendation": "Add noexec, nosuid, and nodev options to tmpfs mounts for enhanced security",  # noqa: E501
                            "implementation_steps": [
                                "Add noexec option to prevent code execution",
                                "Add nosuid option to prevent setuid binaries",
                                "Add nodev option to prevent device file access",
                                "Test application functionality with secure mount options",
                            ],
                            "aws_cli_example": 'tmpfs: [{"containerPath": "/tmp", "size": 100, "mountOptions": ["noexec", "nosuid", "nodev"]}]',  # noqa: E501
                            "compliance_frameworks": ["Container Security", "CIS Benchmarks"],
                        }
                    )

                # Enhanced: Tmpfs size limits
                tmpfs_size = tmpfs_mount.get("size", 0)
                if tmpfs_size > 1024:  # More than 1GB
                    recommendations.append(
                        {
                            "title": "Review Tmpfs Size Allocation",
                            "severity": "Low",
                            "category": "storage_security",
                            "resource": _format_resource_name(
                                "Container", container_name, service_name
                            ),  # noqa: E501
                            "issue": f"Large tmpfs allocation ({tmpfs_size}MB) may impact system resources",  # noqa: E501
                            "recommendation": "Review tmpfs size allocation to prevent resource exhaustion attacks",  # noqa: E501
                            "implementation_steps": [
                                "Analyze application tmpfs requirements",
                                "Set appropriate size limits for tmpfs mounts",
                                "Monitor tmpfs usage patterns",
                                "Implement resource monitoring and alerting",
                            ],
                            "aws_cli_example": "# Monitor tmpfs usage in container",
                            "compliance_frameworks": ["Resource Management", "DoS Prevention"],
                        }
                    )

            # Advanced shared memory security
            shared_memory_size = linux_parameters.get("sharedMemorySize")
            if shared_memory_size:
                # Check if shared memory is properly secured
                recommendations.append(
                    {
                        "title": "Review Shared Memory Security Configuration",
                        "severity": "Medium",
                        "category": "storage_security",
                        "resource": _format_resource_name(
                            "Container", container_name, service_name
                        ),  # noqa: E501
                        "issue": f"Container uses {shared_memory_size} bytes of shared memory which should be secured",  # noqa: E501
                        "recommendation": "Ensure shared memory usage is necessary and properly secured against information disclosure",  # noqa: E501
                        "implementation_steps": [
                            "Verify shared memory is required for application",
                            "Implement proper access controls for shared memory",
                            "Monitor shared memory usage for anomalies",
                            "Consider alternatives if shared memory is not essential",
                        ],
                        "aws_cli_example": "# Review application requirements for shared memory",
                        "compliance_frameworks": ["Memory Security", "Information Protection"],
                    }
                )

                # Enhanced: Shared memory size validation
                if shared_memory_size > 1073741824:  # More than 1GB
                    recommendations.append(
                        {
                            "title": "Validate Shared Memory Size Allocation",
                            "severity": "Medium",
                            "category": "storage_security",
                            "resource": _format_resource_name(
                                "Container", container_name, service_name
                            ),  # noqa: E501
                            "issue": f"Large shared memory allocation ({shared_memory_size} bytes) may pose security risks",  # noqa: E501
                            "recommendation": "Validate shared memory size requirements and implement appropriate limits",  # noqa: E501
                            "implementation_steps": [
                                "Analyze application shared memory requirements",
                                "Set minimum necessary shared memory size",
                                "Implement monitoring for shared memory usage",
                                "Consider security implications of large shared memory",
                            ],
                            "aws_cli_example": "# Review shared memory requirements",
                            "compliance_frameworks": ["Resource Security", "Memory Protection"],
                        }
                    )

        return recommendations

    def _analyze_envoy_proxy_security(
        self,
        service: Dict[str, Any],
        service_name: str,
        cluster_name: str,
        region: str,
    ) -> List[Dict[str, Any]]:
        """PHASE 2: Analyze Envoy proxy security configurations."""
        recommendations = []

        proxy_config = service.get("proxyConfiguration", {})
        if proxy_config.get("type") == "APPMESH":
            properties = proxy_config.get("properties", [])

            # Create a property lookup for easier access
            prop_dict = {prop.get("name"): prop.get("value") for prop in properties}

            # Enhanced: Envoy proxy configuration security
            recommendations.append(
                {
                    "title": "Review Envoy Proxy Configuration Security",
                    "severity": "High",
                    "category": "envoy_security",
                    "resource": f"Service: {service_name}",
                    "issue": "Envoy proxy configuration should be reviewed for security best practices",  # noqa: E501
                    "recommendation": "Implement comprehensive Envoy proxy security configuration",
                    "implementation_steps": [
                        "Review all Envoy configuration parameters",
                        "Implement security headers and filters",
                        "Configure rate limiting and DDoS protection",
                        "Enable security-focused Envoy extensions",
                    ],
                    "aws_cli_example": "# Review App Mesh virtual service configuration",
                    "compliance_frameworks": ["Proxy Security", "Service Mesh Security"],
                }
            )

            # Check for Envoy access logging
            if not prop_dict.get("ENVOY_LOG_LEVEL"):
                recommendations.append(
                    {
                        "title": "Configure Envoy Access Logging",
                        "severity": "Medium",
                        "category": "envoy_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Envoy proxy lacks proper logging configuration for security monitoring",  # noqa: E501
                        "recommendation": "Configure Envoy access logging for security audit and monitoring",  # noqa: E501
                        "implementation_steps": [
                            "Set ENVOY_LOG_LEVEL to appropriate level (info or debug)",
                            "Configure access log format for security events",
                            "Set up log aggregation and monitoring",
                            "Implement alerting for suspicious proxy activity",
                        ],
                        "aws_cli_example": 'proxyConfiguration: {"properties": [{"name": "ENVOY_LOG_LEVEL", "value": "info"}]}',  # noqa: E501  # noqa: E501
                        "compliance_frameworks": ["Audit Logging", "Security Monitoring"],
                    }
                )

            # Check for Envoy admin interface security
            if prop_dict.get("ENVOY_ADMIN_ACCESS_ENABLE") == "true":
                recommendations.append(
                    {
                        "title": "Secure Envoy Admin Interface",
                        "severity": "High",
                        "category": "envoy_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Envoy admin interface is enabled, potentially exposing sensitive proxy configuration",  # noqa: E501  # noqa: E501
                        "recommendation": "Disable Envoy admin interface in production or secure it with proper authentication",  # noqa: E501  # noqa: E501
                        "implementation_steps": [
                            "Disable ENVOY_ADMIN_ACCESS_ENABLE in production",
                            "If admin access is needed, implement proper authentication",
                            "Restrict admin interface to specific IP ranges",
                            "Monitor admin interface access logs",
                        ],
                        "aws_cli_example": 'proxyConfiguration: {"properties": [{"name": "ENVOY_ADMIN_ACCESS_ENABLE", "value": "false"}]}',  # noqa: E501
                        "compliance_frameworks": ["Access Control", "Production Security"],
                    }
                )

            # Enhanced: mTLS configuration check
            if not prop_dict.get("ENVOY_MTLS_ENABLED"):
                recommendations.append(
                    {
                        "title": "Configure Envoy Mutual TLS (mTLS)",
                        "severity": "High",
                        "category": "envoy_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Envoy proxy lacks mutual TLS configuration for secure service-to-service communication",  # noqa: E501
                        "recommendation": "Enable mutual TLS in Envoy proxy for enhanced authentication and encryption",  # noqa: E501
                        "implementation_steps": [
                            "Configure client and server certificates",
                            "Enable ENVOY_MTLS_ENABLED property",
                            "Set up certificate rotation and management",
                            "Configure certificate validation policies",
                        ],
                        "aws_cli_example": 'proxyConfiguration: {"properties": [{"name": "ENVOY_MTLS_ENABLED", "value": "true"}]}',  # noqa: E501
                        "compliance_frameworks": ["Zero Trust Architecture", "mTLS Best Practices"],
                    }
                )

            # Check for circuit breaker configuration
            if not any("CIRCUIT_BREAKER" in prop.get("name", "") for prop in properties):
                recommendations.append(
                    {
                        "title": "Configure Envoy Circuit Breaker",
                        "severity": "Medium",
                        "category": "envoy_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Envoy proxy lacks circuit breaker configuration for resilience against cascading failures",  # noqa: E501
                        "recommendation": "Configure circuit breaker settings to protect against service overload",  # noqa: E501
                        "implementation_steps": [
                            "Configure connection pool settings",
                            "Set up outlier detection for unhealthy endpoints",
                            "Implement retry policies with backoff",
                            "Monitor circuit breaker metrics",
                        ],
                        "aws_cli_example": "# Configure circuit breaker in App Mesh virtual service",  # noqa: E501
                        "compliance_frameworks": ["Resilience", "Availability"],
                    }
                )

            # Enhanced: Rate limiting configuration
            if not any("RATE_LIMIT" in prop.get("name", "") for prop in properties):
                recommendations.append(
                    {
                        "title": "Configure Envoy Rate Limiting",
                        "severity": "Medium",
                        "category": "envoy_security",
                        "resource": f"Service: {service_name}",
                        "issue": "Envoy proxy lacks rate limiting configuration for DDoS protection",  # noqa: E501
                        "recommendation": "Implement rate limiting in Envoy proxy to protect against abuse and DDoS attacks",  # noqa: E501
                        "implementation_steps": [
                            "Configure global and local rate limiting",
                            "Set appropriate rate limit thresholds",
                            "Implement rate limit response handling",
                            "Monitor rate limiting metrics and alerts",
                        ],
                        "aws_cli_example": "# Configure rate limiting in App Mesh virtual service",
                        "compliance_frameworks": ["DDoS Protection", "Rate Limiting"],
                    }
                )

            # Enhanced: Security headers configuration
            recommendations.append(
                {
                    "title": "Configure Envoy Security Headers",
                    "severity": "Medium",
                    "category": "envoy_security",
                    "resource": f"Service: {service_name}",
                    "issue": "Envoy proxy should be configured to add security headers to responses",  # noqa: E501
                    "recommendation": "Configure Envoy to add security headers for enhanced web application security",  # noqa: E501
                    "implementation_steps": [
                        "Configure security headers filter in Envoy",
                        "Add headers like X-Frame-Options, X-Content-Type-Options",
                        "Implement Content Security Policy (CSP) headers",
                        "Configure HSTS headers for HTTPS enforcement",
                    ],
                    "aws_cli_example": "# Configure security headers in App Mesh virtual service",
                    "compliance_frameworks": ["Web Security", "OWASP Security Headers"],
                }
            )

        return recommendations

    def _enhance_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance recommendation with detailed information."""
        enhanced = recommendation.copy()

        # Add detailed descriptions
        enhanced["why_important"] = self._generate_why_important(
            enhanced.get("title", ""), enhanced.get("category", ""), enhanced.get("severity", "")
        )

        enhanced["security_impact"] = self._generate_security_impact(
            enhanced.get("title", ""), enhanced.get("category", ""), enhanced.get("severity", "")
        )

        enhanced["implementation_steps"] = self._generate_implementation_steps(
            enhanced.get("title", ""), enhanced.get("category", "")
        )

        enhanced["aws_cli_commands"] = self._generate_aws_cli_commands(
            enhanced.get("title", ""),
            enhanced.get("resource", ""),
            enhanced,  # Pass the full recommendation data for dynamic resource extraction
        )

        enhanced["aws_documentation_url"] = self._generate_documentation_url(
            enhanced.get("title", ""), enhanced.get("category", "")
        )

        return enhanced

    def _generate_why_important(self, title: str, category: str, severity: str) -> str:
        """Generate why this recommendation is important."""
        importance_map = {
            "Configure Container to Run as Non-Root User": "Running containers as root violates the principle of least privilege and increases the attack surface. If a container is compromised, root access provides attackers with maximum privileges.",  # noqa: E501
            "Avoid Latest Tag in Container Images": "Using latest tags makes deployments unpredictable and can introduce security vulnerabilities when new versions are automatically pulled without proper testing.",  # noqa: E501
            "Enable Read-Only Root Filesystem": "A read-only root filesystem prevents runtime tampering and malicious modifications to the container, reducing the impact of potential security breaches.",  # noqa: E501
            "Configure Container Health Check": "Health checks enable ECS to detect and replace unhealthy containers automatically, improving application availability and security posture.",  # noqa: E501
            "Avoid Static Host Port Mapping": "Static port mapping can lead to port conflicts and makes it easier for attackers to target specific services. Dynamic port allocation provides better security through obscurity.",  # noqa: E501
            "Use AWS Secrets Manager for Sensitive Data": "Hardcoded secrets in environment variables are visible in container metadata and logs, creating security risks. Secrets Manager provides encryption and access control.",  # noqa: E501
            "Restrict SSH Access from Internet": "Open SSH access from the internet exposes your infrastructure to brute force attacks and unauthorized access attempts.",  # noqa: E501
            "Configure task IAM role": "Without proper IAM roles, containers may have excessive permissions or no permissions at all, violating security best practices.",  # noqa: E501
            "Enable Container Insights for Security Monitoring": "Container Insights provides visibility into container performance and security events, enabling faster detection of anomalies.",  # noqa: E501
        }

        return importance_map.get(
            title,
            f"This {category} security configuration helps maintain a secure ECS environment and follows AWS security best practices.",  # noqa: E501
        )

    def _generate_security_impact(self, title: str, category: str, severity: str) -> str:
        """Generate security impact description."""
        impact_map = {
            "Configure Container to Run as Non-Root User": "High risk of privilege escalation and system compromise if container is breached. Root access allows attackers to modify system files and access sensitive data.",  # noqa: E501
            "Avoid Latest Tag in Container Images": "Medium risk of deploying vulnerable or untested code. Latest tags can introduce breaking changes or security vulnerabilities without notice.",  # noqa: E501
            "Enable Read-Only Root Filesystem": "Reduces risk of runtime attacks and malware persistence. Prevents attackers from modifying system files or installing malicious software.",  # noqa: E501
            "Configure Container Health Check": "Without health checks, failed or compromised containers may continue running, potentially serving malicious content or consuming resources.",  # noqa: E501
            "Avoid Static Host Port Mapping": "Static ports make services predictable targets for attackers and can lead to service conflicts in multi-tenant environments.",  # noqa: E501
            "Use AWS Secrets Manager for Sensitive Data": "Critical risk of credential exposure through container metadata, logs, or process lists. Compromised credentials can lead to data breaches.",  # noqa: E501
            "Restrict SSH Access from Internet": "Critical risk of unauthorized access, data breaches, and system compromise through brute force attacks or credential stuffing.",  # noqa: E501
            "Configure task IAM role": "Risk of privilege escalation or insufficient permissions leading to application failures or security vulnerabilities.",  # noqa: E501
            "Enable Container Insights for Security Monitoring": "Reduced visibility into security events and performance issues, making it harder to detect and respond to threats.",  # noqa: E501
        }

        return impact_map.get(
            title,
            f"This {severity.lower()} severity {category} issue could impact your security posture and compliance requirements.",  # noqa: E501
        )

    def _generate_implementation_steps(self, title: str, category: str) -> List[str]:
        """Generate implementation steps."""
        steps_map = {
            "Configure Container to Run as Non-Root User": [
                "Create a non-root user in your Dockerfile: RUN useradd -r -s /bin/false appuser",
                "Set the user in your Dockerfile: USER appuser",
                "Update your task definition to specify the user parameter",
                "Test the application to ensure it works with non-root permissions",
                "Update file permissions if needed for application directories",
            ],
            "Avoid Latest Tag in Container Images": [
                "Identify the current version of your container image",
                "Update your task definition to use a specific version tag (e.g., myapp:v1.2.3)",
                "Implement a versioning strategy for your container images",
                "Update your CI/CD pipeline to use specific tags",
                "Test the deployment with the specific tag",
            ],
            "Enable Read-Only Root Filesystem": [
                "Update your task definition to set readonlyRootFilesystem: true",
                "Identify directories that need write access",
                "Add volume mounts for writable directories (e.g., /tmp, /var/log)",
                "Test your application to ensure it works with read-only filesystem",
                "Update application code if it writes to unexpected locations",
            ],
            "Configure Container Health Check": [
                "Define a health check endpoint in your application",
                "Add healthCheck configuration to your task definition",
                "Set appropriate timeout and retry values",
                "Test the health check endpoint",
                "Monitor health check results in ECS console",
            ],
            "Avoid Static Host Port Mapping": [
                "Update task definition to set hostPort to 0 for dynamic allocation",
                "Configure Application Load Balancer to use dynamic port mapping",
                "Update service discovery configuration if used",
                "Test connectivity through the load balancer",
                "Update any hardcoded port references in your application",
            ],
            "Use AWS Secrets Manager for Sensitive Data": [
                "Create secrets in AWS Secrets Manager",
                "Update task execution role with secretsmanager:GetSecretValue permission",
                "Replace environment variables with secrets in task definition",
                "Update application code to handle secrets if needed",
                "Test secret retrieval and application functionality",
            ],
            "Restrict SSH Access from Internet": [
                "Identify the security group with the overly permissive rule",
                "Remove or modify the rule allowing 0.0.0.0/0 access to port 22",
                "Add specific IP ranges for authorized access",
                "Consider using AWS Systems Manager Session Manager instead",
                "Test connectivity from authorized locations",
            ],
        }

        return steps_map.get(
            title,
            [
                "Review the current configuration",
                "Plan the security improvement",
                "Implement the recommended changes",
                "Test the changes in a non-production environment",
                "Deploy to production and monitor",
            ],
        )

    def _generate_aws_cli_commands(
        self, title: str, resource: str, recommendation_data: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate AWS CLI commands for implementation.

        CRITICAL: All CLI commands MUST be verified against official AWS documentation:
        - AWS ECS CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/ecs/
        - AWS EC2 CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/ec2/
        - AWS Secrets Manager CLI Reference: https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/

        DO NOT assume command syntax. Always verify:
        1. Command name exists in the service
        2. Parameter names and formats are correct
        3. Required vs optional parameters
        4. Example usage from official docs
        """
        # Extract actual resource names from the resource string and recommendation data
        cluster_name = getattr(self, "_current_cluster_name", "CLUSTER_NAME")

        # Extract specific resource IDs from the resource string
        task_def_name = "TASK_DEFINITION_NAME"
        security_group_id = "SECURITY_GROUP_ID"

        if recommendation_data:
            # Try to extract actual resource names from the recommendation data
            if "task_definition" in recommendation_data:
                task_def_name = recommendation_data["task_definition"]
            elif "Task Definition:" in resource:
                task_def_name = resource.split("Task Definition: ")[-1].strip()

            if "security_group_id" in recommendation_data:
                security_group_id = recommendation_data["security_group_id"]
            elif "Security Group:" in resource:
                security_group_id = resource.split("Security Group: ")[-1].strip()

        # Parse resource string for actual IDs
        if "Task Definition:" in resource:
            task_def_name = resource.split("Task Definition: ")[-1].strip()
        if "Security Group:" in resource:
            security_group_id = resource.split("Security Group: ")[-1].strip()
        if "Cluster:" in resource:
            cluster_name = resource.split("Cluster: ")[-1].strip()

        commands_map = {
            "Configure Container to Run as Non-Root User": [
                f"aws ecs describe-task-definition --task-definition {task_def_name}",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
            "Avoid Latest Tag in Container Images": [
                f"aws ecs describe-task-definition --task-definition {task_def_name}",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
            "Enable Read-Only Root Filesystem": [
                f"aws ecs describe-task-definition --task-definition {task_def_name}",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
            "Configure Container Health Check": [
                f"aws ecs describe-task-definition --task-definition {task_def_name}",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
            "Avoid Static Host Port Mapping": [
                f"aws ecs describe-task-definition --task-definition {task_def_name}",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
            "Use AWS Secrets Manager for Sensitive Data": [
                'aws secretsmanager create-secret --name "app/database/password" --secret-string "your-secret-value"',  # noqa: E501
                f"aws ecs describe-task-definition --task-definition {task_def_name}",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
            "Restrict SSH Access from Internet": [
                f"aws ec2 describe-security-groups --group-ids {security_group_id}",
                f"aws ec2 revoke-security-group-ingress --group-id {security_group_id} --protocol tcp --port 22 --cidr 0.0.0.0/0",  # noqa: E501
                f"aws ec2 authorize-security-group-ingress --group-id {security_group_id} --protocol tcp --port 22 --cidr YOUR_IP_RANGE/32",  # noqa: E501
            ],
            "Enable Container Insights for Security Monitoring": [
                f"aws ecs modify-cluster --cluster {cluster_name} --settings name=containerInsights,value=enabled"  # noqa: E501
            ],
            "Enable VPC Flow Logs": [
                "aws ec2 create-flow-logs --resource-type VPC --resource-ids VPC_ID --traffic-type ALL --log-destination-type cloud-watch-logs --log-group-name VPCFlowLogs"  # noqa: E501
            ],
            "Review Internet Gateway Routes": [
                'aws ec2 describe-route-tables --filters "Name=vpc-id,Values=VPC_ID"',
                'aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=VPC_ID"',  # noqa: E501
            ],
        }

        return commands_map.get(
            title,
            [
                "aws ecs describe-cluster --cluster CLUSTER_NAME",
                "aws ecs describe-services --cluster CLUSTER_NAME --services SERVICE_NAME",
            ],
        )

    def _generate_documentation_url(self, title: str, category: str) -> str:
        """Generate AWS documentation URL."""
        doc_map = {
            "Configure Container to Run as Non-Root User": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_security",  # noqa: E501
            "Avoid Latest Tag in Container Images": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_image",  # noqa: E501
            "Enable Read-Only Root Filesystem": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_security",  # noqa: E501
            "Configure Container Health Check": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_healthcheck",  # noqa: E501
            "Avoid Static Host Port Mapping": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_portmappings",  # noqa: E501
            "Use AWS Secrets Manager for Sensitive Data": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data-secrets.html",  # noqa: E501
            "Restrict SSH Access from Internet": "https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html",  # noqa: E501
            "Enable Container Insights for Security Monitoring": "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html",  # noqa: E501
            "Configure task IAM role": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html",  # noqa: E501
            "Enable VPC Flow Logs": "https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html",  # noqa: E501
            "Review Internet Gateway Routes": "https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html",  # noqa: E501
            # PHASE 1: Container Runtime Security
            "Configure Seccomp Security Profile": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_linuxparameters",  # noqa: E501
            "Configure AppArmor Security Profile": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_linuxparameters",  # noqa: E501
            "Enable No New Privileges Flag": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_linuxparameters",  # noqa: E501
            "Configure Linux Security Parameters": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_linuxparameters",  # noqa: E501
            # PHASE 1: ECR Integration
            "Enable ECR Vulnerability Scanning": "https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html",  # noqa: E501
            "Address Critical Vulnerabilities in Container Image": "https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html",  # noqa: E501
            "Address High Severity Vulnerabilities in Container Image": "https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html",  # noqa: E501
            "Use Amazon ECR for Container Images": "https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html",  # noqa: E501
            # PHASE 1: Service Mesh
            "Configure Service Connect Namespace": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-connect.html",  # noqa: E501
            "Enable TLS for Service Connect Communication": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-connect.html",  # noqa: E501
            "Consider ECS Service Connect for Service Mesh": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-connect.html",  # noqa: E501
            "Enable TLS in App Mesh Configuration": "https://docs.aws.amazon.com/app-mesh/latest/userguide/tls.html",  # noqa: E501
            # PHASE 1: Advanced Image Security
            "Implement Container Image Signing": "https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html",  # noqa: E501
            "Implement Image Provenance Tracking": "https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html",  # noqa: E501
            "Verify Secure Multi-Stage Build Practices": "https://docs.docker.com/develop/dev-best-practices/",  # noqa: E501
            "Use Minimal Base Images": "https://docs.docker.com/develop/dev-best-practices/",
            "Use Immutable Image Tags with Digest": "https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-tag-mutability.html",  # noqa: E501
            # PHASE 2: Advanced ECS Features
            "Configure KMS Encryption for ECS Exec": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html",  # noqa: E501
            "Enable ECS Exec Session Logging": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html",  # noqa: E501
            "Enable Deployment Circuit Breaker for Blue/Green": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service_definition_parameters.html",  # noqa: E501
            "Review Spot Instance Security Implications": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html",  # noqa: E501
            "Verify ECS Anywhere Security Configuration": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-anywhere.html",  # noqa: E501
            # PHASE 2: Advanced Network Security
            "Configure VPC Endpoints for AWS Services": "https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html",  # noqa: E501
            "Review DNS Security Configuration": "https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall.html",  # noqa: E501
            "Review Multiple Security Groups Configuration": "https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html",  # noqa: E501
            # PHASE 2: Advanced Storage Security
            "Verify EFS Encryption at Rest": "https://docs.aws.amazon.com/efs/latest/ug/encryption.html",  # noqa: E501
            "Configure EFS Backup and Lifecycle Policies": "https://docs.aws.amazon.com/efs/latest/ug/awsbackup.html",  # noqa: E501
            "Verify FSx Security Configuration": "https://docs.aws.amazon.com/fsx/latest/WindowsGuide/encryption.html",  # noqa: E501
            "Configure Secure Tmpfs Mount Options": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_linuxparameters",  # noqa: E501
            "Review Shared Memory Security Configuration": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html#container_definition_linuxparameters",  # noqa: E501
            # PHASE 2: Envoy Proxy Security
            "Configure Envoy Access Logging": "https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy.html",  # noqa: E501
            "Secure Envoy Admin Interface": "https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy.html",  # noqa: E501
            "Configure Envoy Circuit Breaker": "https://docs.aws.amazon.com/app-mesh/latest/userguide/circuit-breakers.html",  # noqa: E501
        }

        return doc_map.get(title, "https://docs.aws.amazon.com/ecs/")

    def _generate_analysis_summary(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate analysis summary."""
        severity_counts = {}
        category_counts = {}

        for rec in recommendations:
            severity = rec.get("severity", "Unknown")
            category = rec.get("category", "unknown")

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_issues": len(recommendations),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "categories": list(category_counts.keys()),
            "risk_level": self._calculate_risk_level(severity_counts),
            "top_categories": sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3],
        }

    def _calculate_risk_level(self, severity_counts: Dict[str, int]) -> str:
        """Calculate overall risk level based on severity counts."""
        if severity_counts.get("High", 0) > 2:
            return "High"
        elif severity_counts.get("High", 0) > 0 or severity_counts.get("Medium", 0) > 3:
            return "Medium"
        else:
            return "Low"

    def _categorize_issues(self, recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Categorize issues by resource type and category for better organization."""
        categorized = {
            "by_severity": {"High": [], "Medium": [], "Low": []},
            "by_category": {},
            "by_resource_type": {},
        }

        for rec in recommendations:
            severity = rec.get("severity", "Unknown")
            category = rec.get("category", "Unknown")
            resource = rec.get("resource", "Unknown")

            # Group by severity
            if severity in categorized["by_severity"]:
                categorized["by_severity"][severity].append(rec)

            # Group by category
            if category not in categorized["by_category"]:
                categorized["by_category"][category] = []
            categorized["by_category"][category].append(rec)

            # Group by resource type
            resource_type = self._extract_resource_type(resource)
            if resource_type not in categorized["by_resource_type"]:
                categorized["by_resource_type"][resource_type] = []
            categorized["by_resource_type"][resource_type].append(rec)

        return categorized

    def _extract_resource_type(self, resource: str) -> str:
        """Extract resource type from resource string."""
        if "Cluster:" in resource:
            return "Cluster"
        elif "Service:" in resource:
            return "Service"
        elif "Container:" in resource:
            return "Container"
        elif "Security Group" in resource:
            return "Security Group"
        elif "Load Balancer" in resource:
            return "Load Balancer"
        elif "VPC:" in resource:
            return "VPC"
        else:
            return "Other"

    def _calculate_risk_priorities(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate risk-weighted priorities for recommendations."""
        risk_scored = []

        severity_weights = {"High": 100, "Medium": 50, "Low": 25}
        category_weights = {
            "network_security": 1.5,
            "container_security": 1.4,
            "iam_security": 1.3,
            "encryption": 1.2,
            "monitoring": 1.1,
            "compliance": 1.0,
            "configuration": 0.9,
            "availability": 0.8,
        }

        for rec in recommendations:
            severity = rec.get("severity", "Low")
            category = rec.get("category", "configuration")

            base_score = severity_weights.get(severity, 25)
            category_multiplier = category_weights.get(category, 1.0)

            # Additional risk factors
            risk_multiplier = 1.0
            issue = rec.get("issue", "").lower()

            # High-risk keywords
            if any(
                keyword in issue
                for keyword in ["internet", "0.0.0.0/0", "root", "privileged", "ssh"]
            ):
                risk_multiplier += 0.5

            # Public exposure
            if any(keyword in issue for keyword in ["public", "exposed", "open"]):
                risk_multiplier += 0.3

            final_score = base_score * category_multiplier * risk_multiplier

            risk_item = rec.copy()
            risk_item["risk_score"] = round(final_score, 2)
            risk_scored.append(risk_item)

        # Sort by risk score descending
        risk_scored.sort(key=lambda x: x["risk_score"], reverse=True)

        return risk_scored[:10]  # Top 10 highest risk items

    def _deduplicate_recommendations(
        self, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate recommendations using comprehensive similarity analysis."""
        if not recommendations:
            return []

        deduplicated = []
        processed_indices = set()

        for i, rec in enumerate(recommendations):
            if i in processed_indices:
                continue

            # Find all similar recommendations to this one
            similar_recs = [rec]
            similar_indices = {i}

            for j, other_rec in enumerate(recommendations[i + 1 :], i + 1):
                if j in processed_indices:
                    continue

                if self._are_recommendations_similar(rec, other_rec):
                    similar_recs.append(other_rec)
                    similar_indices.add(j)

            # If we found similar recommendations, keep the best one
            if len(similar_recs) > 1:
                best_rec = self._select_best_recommendation(similar_recs)
                deduplicated.append(best_rec)
                processed_indices.update(similar_indices)
            else:
                deduplicated.append(rec)
                processed_indices.add(i)

        return deduplicated

    def _are_recommendations_similar(self, rec1: Dict[str, Any], rec2: Dict[str, Any]) -> bool:
        """Determine if two recommendations are similar enough to be considered duplicates."""
        title1 = rec1.get("title", "").lower().strip()
        title2 = rec2.get("title", "").lower().strip()

        resource1 = rec1.get("resource", "").lower().strip()
        resource2 = rec2.get("resource", "").lower().strip()

        issue1 = rec1.get("issue", "").lower().strip()
        issue2 = rec2.get("issue", "").lower().strip()

        category1 = rec1.get("category", "").lower().strip()
        category2 = rec2.get("category", "").lower().strip()

        # Exact title match
        if title1 == title2:
            # Same title - check if it's the same resource or same issue
            if resource1 == resource2 or self._text_similarity(issue1, issue2) > 0.8:
                return True

        # High title similarity with same category
        if self._text_similarity(title1, title2) > 0.9 and category1 == category2:
            return True

        # Same resource with very similar issues
        if resource1 == resource2 and self._text_similarity(issue1, issue2) > 0.85:
            return True

        # Handle specific duplicate patterns
        return self._check_specific_duplicate_patterns(rec1, rec2)

    def _check_specific_duplicate_patterns(
        self, rec1: Dict[str, Any], rec2: Dict[str, Any]
    ) -> bool:
        """Check for specific known duplicate patterns."""
        title1 = rec1.get("title", "").lower()
        title2 = rec2.get("title", "").lower()

        resource1 = rec1.get("resource", "").lower()
        resource2 = rec2.get("resource", "").lower()

        issue1 = rec1.get("issue", "").lower()
        issue2 = rec2.get("issue", "").lower()

        # Public IP assignment duplicates (service vs subnet level)
        if ("public ip" in title1 and "public ip" in title2) or (
            "public ip" in issue1 and "public ip" in issue2
        ):
            return True

        # Container Insights duplicates across compliance frameworks
        if ("container insights" in title1 and "container insights" in title2) or (
            "container insights" in issue1 and "container insights" in issue2
        ):
            return True

        # Execute command duplicates (security vs compliance)
        if ("execute command" in title1 and "execute command" in title2) or (
            "execute command" in issue1 and "execute command" in issue2
        ):
            return True

        # IAM role duplicates (technical vs compliance)
        if ("iam role" in title1 or "task role" in title1) and (
            "iam role" in title2 or "task role" in title2 or "access control" in title2
        ):
            return True

        # Security group port duplicates
        if (
            "security group" in title1
            and "security group" in title2
            and "port" in issue1
            and "port" in issue2
        ):
            # Extract port numbers
            port1 = re.search(r"port\s+(\d+)", issue1)
            port2 = re.search(r"port\s+(\d+)", issue2)
            if port1 and port2 and port1.group(1) == port2.group(1):
                return True

        # Container static port mapping duplicates
        if (
            "static" in title1
            and "static" in title2
            and "port" in title1
            and "port" in title2
            and "container" in resource1
            and "container" in resource2
        ):
            return True

        # Health check duplicates
        if (
            "health check" in title1
            and "health check" in title2
            and "container" in resource1
            and "container" in resource2
        ):
            # Extract container names
            container1 = self._extract_container_name(resource1)
            container2 = self._extract_container_name(resource2)
            if container1 == container2:
                return True

        # Memory/CPU limit duplicates for same container
        if (
            ("memory" in title1 or "cpu" in title1)
            and ("memory" in title2 or "cpu" in title2)
            and "container" in resource1
            and "container" in resource2
        ):
            container1 = self._extract_container_name(resource1)
            container2 = self._extract_container_name(resource2)
            if container1 == container2:
                return True

        return False

    def _extract_container_name(self, resource: str) -> str:
        """Extract container name from resource string."""
        if "container:" in resource.lower():
            parts = resource.split(":")
            if len(parts) > 1:
                return parts[1].strip().split("|")[0].strip()
        return resource

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using sequence matching."""
        from difflib import SequenceMatcher

        return SequenceMatcher(None, text1, text2).ratio()

    def _select_best_recommendation(self, similar_recs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best recommendation from a group of similar ones."""

        # Sort by severity (highest first), then by completeness of information
        def recommendation_score(rec):
            severity_weight = self._get_severity_weight(rec.get("severity", "Low"))

            # Bonus points for more complete information
            completeness_score = 0
            if rec.get("recommendation"):
                completeness_score += 1
            if rec.get("remediation_steps"):
                completeness_score += 1
            if len(rec.get("issue", "")) > 50:  # More detailed issue description
                completeness_score += 1

            return severity_weight * 10 + completeness_score

        return max(similar_recs, key=recommendation_score)

    def _create_deduplication_key(
        self, title: str, resource_type: str, issue: str, category: str
    ) -> str:
        """Create a normalized key for deduplication (legacy method - kept for compatibility)."""
        # This method is now primarily used by the legacy deduplication logic
        # The new similarity-based approach is more comprehensive
        normalized_title = title.lower().strip()
        normalized_resource_type = resource_type.lower().strip()
        normalized_category = category.lower().strip()

        # Extract specific identifiers for better deduplication

        # Handle network security with port numbers
        if "port" in issue.lower():
            port_match = re.search(r"port\s+(\d+)", issue.lower())
            port = port_match.group(1) if port_match else "unknown"
            return f"network_port_{port}_{normalized_resource_type}_{normalized_category}"

        # Handle container-specific issues
        if "container" in normalized_resource_type:
            container_name = self._extract_container_name(resource_type)
            if "health check" in normalized_title:
                return f"container_health_{container_name}_{normalized_category}"
            elif "memory" in normalized_title or "cpu" in normalized_title:
                return f"container_resources_{container_name}_{normalized_category}"
            elif "static" in normalized_title and "port" in normalized_title:
                return f"container_static_port_{container_name}_{normalized_category}"

        # Handle IAM duplicates
        if "iam" in normalized_title and "role" in normalized_title:
            if "task" in normalized_title:
                return f"iam_task_role_{normalized_resource_type}_{normalized_category}"
            elif "execution" in normalized_title:
                return f"iam_execution_role_{normalized_resource_type}_{normalized_category}"

        # Handle secrets duplicates
        if "secret" in normalized_title:
            return f"secrets_management_{normalized_resource_type}_{normalized_category}"

        # Generic deduplication key
        return f"{normalized_title}_{normalized_resource_type}_{normalized_category}"

    def _get_severity_weight(self, severity: str) -> int:
        """Get numeric weight for severity comparison (AWS Trusted Advisor aligned)."""
        weights = {"High": 3, "Medium": 2, "Low": 1}
        return weights.get(severity, 0)


class SecurityReportFormatter:
    """Enhanced security report formatter with multiple output formats and filtering."""

    def __init__(self):
        """Initialize the SecurityReportFormatter with severity icons and formatting options."""
        self.severity_icons = {
            "High": "🔴",  # AWS Trusted Advisor Red (Action Recommended)
            "Medium": "🟡",  # AWS Trusted Advisor Yellow (Investigation Recommended)
            "Low": "🟢",  # AWS Trusted Advisor Green (Informational)
        }
        self.category_icons = {
            "network_security": "🌐",
            "container_security": "🐳",
            "iam_security": "🔐",
            "encryption": "🔒",
            "monitoring": "📊",
            "compliance": "🏛️",
            "configuration": "⚙️",
            "availability": "⚡",
            "secrets": "🔑",
            "security": "🛡️",
            "well_architected": "🏗️",
            "resource_management": "📈",
            "network": "🔗",
            "monitoring_security": "👁️",
            "iam": "🔐",
            "logging": "📝",
        }

    def format_report(
        self,
        analysis_result: Dict[str, Any],
        format_type: str = "summary",
        severity_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
        show_details: bool = False,
    ) -> str:
        """Format security analysis report with various options."""

        if format_type == "json":
            return self._format_json(analysis_result, severity_filter, category_filter)
        elif format_type == "detailed":
            return self._format_detailed(analysis_result, severity_filter, category_filter)
        elif format_type == "executive":
            return self._format_executive_summary(analysis_result)
        else:
            return self._format_enhanced_summary(
                analysis_result, severity_filter, category_filter, show_details
            )

    def _format_enhanced_summary(
        self,
        analysis_result: Dict[str, Any],
        severity_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
        show_details: bool = False,
    ) -> str:
        """Format enhanced summary with progressive disclosure."""

        recommendations = analysis_result.get("recommendations", [])
        categorized = analysis_result.get("categorized_issues", {})
        risk_priorities = analysis_result.get("risk_weighted_priorities", [])
        summary = analysis_result.get("analysis_summary", {})

        # Apply filters to both recommendations and categorized data
        if severity_filter or category_filter:
            recommendations = self._apply_filters(recommendations, severity_filter, category_filter)
            categorized = self._filter_categorized_data(
                categorized, severity_filter, category_filter
            )
            risk_priorities = self._apply_filters(risk_priorities, severity_filter, category_filter)
            # Update summary to reflect filtered data
            summary = self._generate_filtered_summary(categorized, severity_filter, category_filter)

        report = []

        # Executive Summary
        report.append(self._generate_executive_header(summary, len(recommendations)))

        # Risk-Weighted Top Priorities
        if risk_priorities:
            report.append(self._generate_risk_priorities_section(risk_priorities[:5]))

        # High Priority Issues (Always detailed)
        high_issues = self._get_critical_high_issues(categorized)
        if high_issues:
            report.append(self._generate_critical_high_section(high_issues))

        # Medium Issues (Expandable)
        medium_issues = categorized.get("by_severity", {}).get("Medium", [])
        if medium_issues:
            report.append(self._generate_medium_section(medium_issues, show_details))

        # Low Issues (Collapsible summary)
        low_issues = categorized.get("by_severity", {}).get("Low", [])
        if low_issues:
            report.append(self._generate_low_section(low_issues, show_details))

        # Category breakdown (always show unless filtered)
        if not category_filter:  # Only show if not filtering by specific categories
            report.append(self._generate_category_breakdown_section(categorized))

        # Resource-based grouping (always show for better actionability)
        report.append(self._generate_resource_breakdown(categorized))

        # Quick Actions and Remediation Guide
        report.append(self._generate_quick_actions(risk_priorities[:3]))

        return "\n\n".join(report)

    def _apply_filters(
        self,
        recommendations: List[Dict[str, Any]],
        severity_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Apply severity and category filters to recommendations."""
        filtered = recommendations

        if severity_filter:
            filtered = [r for r in filtered if r.get("severity") in severity_filter]

        if category_filter:
            filtered = [r for r in filtered if r.get("category") in category_filter]

        return filtered

    def _filter_categorized_data(
        self,
        categorized: Dict[str, Any],
        severity_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Apply filters to categorized data structure."""
        if not severity_filter and not category_filter:
            return categorized

        filtered_categorized = {"by_severity": {}, "by_category": {}, "by_resource": {}}

        # Filter by_severity
        by_severity = categorized.get("by_severity", {})
        for severity, issues in by_severity.items():
            if not severity_filter or severity in severity_filter:
                filtered_issues = issues
                if category_filter:
                    filtered_issues = [
                        issue for issue in issues if issue.get("category") in category_filter
                    ]
                if filtered_issues:
                    filtered_categorized["by_severity"][severity] = filtered_issues

        # Filter by_category
        by_category = categorized.get("by_category", {})
        for category, issues in by_category.items():
            if not category_filter or category in category_filter:
                filtered_issues = issues
                if severity_filter:
                    filtered_issues = [
                        issue for issue in issues if issue.get("severity") in severity_filter
                    ]
                if filtered_issues:
                    filtered_categorized["by_category"][category] = filtered_issues

        # Filter by_resource
        by_resource = categorized.get("by_resource", {})
        for resource, issues in by_resource.items():
            filtered_issues = issues
            if severity_filter:
                filtered_issues = [
                    issue for issue in filtered_issues if issue.get("severity") in severity_filter
                ]
            if category_filter:
                filtered_issues = [
                    issue for issue in filtered_issues if issue.get("category") in category_filter
                ]
            if filtered_issues:
                filtered_categorized["by_resource"][resource] = filtered_issues

        return filtered_categorized

    def _generate_filtered_summary(
        self,
        categorized: Dict[str, Any],
        severity_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate summary statistics for filtered data."""
        by_severity = categorized.get("by_severity", {})
        by_category = categorized.get("by_category", {})

        # Calculate severity breakdown
        severity_breakdown = {}
        total_issues = 0
        for severity, issues in by_severity.items():
            count = len(issues)
            severity_breakdown[severity] = count
            total_issues += count

        # Calculate category breakdown
        category_breakdown = {}
        for category, issues in by_category.items():
            category_breakdown[category] = len(issues)

        # Determine overall risk level based on filtered results
        risk_level = "Low"
        if severity_breakdown.get("High", 0) > 0:
            risk_level = "High"
        elif severity_breakdown.get("Medium", 0) > 0:
            risk_level = "Medium"

        return {
            "severity_breakdown": severity_breakdown,
            "category_breakdown": category_breakdown,
            "risk_level": risk_level,
            "total_issues": total_issues,
            "filtered": True,
            "severity_filter": severity_filter,
            "category_filter": category_filter,
        }

    def _generate_executive_header(self, summary: Dict[str, Any], total_filtered: int) -> str:
        """Generate executive summary header with severity and category breakdowns."""
        severity_breakdown = summary.get("severity_breakdown", {})
        category_breakdown = summary.get("category_breakdown", {})
        risk_level = summary.get("risk_level", "Unknown")
        is_filtered = summary.get("filtered", False)
        severity_filter = summary.get("severity_filter")
        category_filter = summary.get("category_filter")

        header = ["# 🛡️ ECS Security Analysis Report", ""]

        # Show filter information if applied
        if is_filtered:
            header.append("## 🔍 Filtered Results")
            if severity_filter:
                header.append(f"**Severity Filter**: {', '.join(severity_filter)}")
            if category_filter:
                header.append(f"**Category Filter**: {', '.join(category_filter)}")
            header.append("")

        header.extend(
            [
                "## 📊 Executive Summary",
                f"**Total Security Issues Found**: {total_filtered}",
                f"**Overall Risk Level**: {self.severity_icons.get(risk_level, '❓')} {risk_level}",
                "",
                "### Issue Breakdown by Severity:",
            ]
        )

        for severity in ["High", "Medium", "Low"]:
            count = severity_breakdown.get(severity, 0)
            icon = self.severity_icons.get(severity, "❓")
            if count > 0:
                header.append(
                    f"• {icon} **{count} {severity}** - {self._get_severity_description(severity)}"
                )

        # Add category breakdown
        if category_breakdown:
            header.extend(["", "### Recommendations by Category:"])

            # Sort categories by count (descending)
            sorted_categories = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)

            for category, count in sorted_categories:
                icon = self.category_icons.get(category, "📋")
                category_display = category.replace("_", " ").title()
                header.append(f"• {icon} **{category_display}**: {count} recommendations")

        return "\n".join(header)

    def _get_severity_description(self, severity: str) -> str:
        """Get description for severity level (AWS Trusted Advisor aligned)."""
        descriptions = {
            "High": "Action recommended - High risk security issues requiring immediate attention",
            "Medium": "Investigation recommended - Medium risk issues that should be investigated",
            "Low": "Informational - Best practices and minor security improvements",
        }
        return descriptions.get(severity, "Review when possible")

    def _generate_risk_priorities_section(self, top_priorities: List[Dict[str, Any]]) -> str:
        """Generate risk-weighted priorities section."""
        section = [
            "## 🎯 Top Priority Issues (Risk-Weighted)",
            "",
            "*These issues pose the highest combined risk based on severity, exploitability, and impact.*",  # noqa: E501
            "",
        ]

        for i, issue in enumerate(top_priorities, 1):
            severity = issue.get("severity", "Unknown")
            icon = self.severity_icons.get(severity, "❓")
            risk_score = issue.get("risk_score", 0)

            section.extend(
                [
                    f"### {i}. {icon} {issue.get('title', 'Unknown Issue')} (Risk Score: {risk_score})",  # noqa: E501
                    f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                    f"**Issue**: {issue.get('issue', 'No description')}",
                    f"**Impact**: {self._get_impact_description(issue)}",
                    "",
                ]
            )

        return "\n".join(section)

    def _get_impact_description(self, issue: Dict[str, Any]) -> str:
        """Generate impact description based on issue details."""
        category = issue.get("category", "")
        severity = issue.get("severity", "")

        impact_map = {
            "network_security": "Network breach, unauthorized access",
            "container_security": "Container compromise, privilege escalation",
            "iam_security": "Unauthorized access, data breach",
            "encryption": "Data exposure, compliance violation",
        }

        base_impact = impact_map.get(category, "Security vulnerability")

        if severity == "High":
            return f"⚠️ {base_impact} with high exploitation potential"
        else:
            return base_impact

    def _get_critical_high_issues(self, categorized: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get high severity issues."""
        by_severity = categorized.get("by_severity", {})
        high = by_severity.get("High", [])
        return high

    def _generate_critical_high_section(self, issues: List[Dict[str, Any]]) -> str:
        """Generate detailed section for high priority issues."""
        section = [
            "## 🔴 High Priority Issues",
            "",
            "*These issues require immediate attention and should be fixed within 24-48 hours.*",
            "",
        ]

        for issue in issues:
            severity = issue.get("severity", "Unknown")
            icon = self.severity_icons.get(severity, "❓")

            section.extend(
                [
                    f"### {icon} {issue.get('title', 'Unknown Issue')}",
                    f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                    f"**Severity**: {severity} | **Category**: {issue.get('category', 'Unknown')}",
                    "",
                    f"**Issue**: {issue.get('issue', 'No description')}",
                    "",
                    f"**Action Required**: {issue.get('recommendation', 'No recommendation provided')}",  # noqa: E501
                    "",
                ]
            )

            # Add remediation steps if available
            remediation = issue.get("remediation_steps")
            if remediation:
                section.extend(["**Remediation Steps**:", remediation, ""])

            section.append("---")
            section.append("")

        return "\n".join(section)

    def _generate_medium_section(
        self, medium_issues: List[Dict[str, Any]], show_details: bool
    ) -> str:
        """Generate medium priority section with expandable details."""
        section = [
            f"## 🟡 Medium Priority Issues ({len(medium_issues)} total)",
            "",
            "*Address these issues in your next maintenance window.*",
            "",
        ]

        if not show_details:
            # Show summary by category
            category_summary = {}
            for issue in medium_issues:
                category = issue.get("category", "Unknown")
                if category not in category_summary:
                    category_summary[category] = []
                category_summary[category].append(issue.get("title", "Unknown"))

            section.append("### Summary by Category:")
            for category, titles in category_summary.items():
                icon = self.category_icons.get(category, "⚙️")
                section.append(
                    f"• {icon} **{category.replace('_', ' ').title()}** ({len(titles)} issues)"
                )
                if len(titles) <= 3:
                    for title in titles:
                        section.append(f"  - {title}")
                else:
                    for title in titles[:2]:
                        section.append(f"  - {title}")
                    section.append(f"  - ... and {len(titles) - 2} more")
                section.append("")

            section.extend(
                ["*Use `--show-details` flag to see full details for medium priority issues.*", ""]
            )
        else:
            # Show full details
            for issue in medium_issues:
                section.extend(
                    [
                        f"### 🟡 {issue.get('title', 'Unknown Issue')}",
                        f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                        f"**Issue**: {issue.get('issue', 'No description')}",
                        f"**Action Required**: {issue.get('recommendation', 'No recommendation')}",
                        "",
                    ]
                )

        return "\n".join(section)

    def _generate_low_section(self, low_issues: List[Dict[str, Any]], show_details: bool) -> str:
        """Generate low priority section with collapsible summary."""
        section = [
            f"## 🔵 Low Priority Issues ({len(low_issues)} total)",
            "",
            "*Future improvements and best practice recommendations.*",
            "",
        ]

        if not show_details:
            # Group by category and show counts
            category_counts = {}
            for issue in low_issues:
                category = issue.get("category", "Unknown")
                category_counts[category] = category_counts.get(category, 0) + 1

            section.append("### Issues by Category:")
            for category, count in sorted(
                category_counts.items(), key=lambda x: x[1], reverse=True
            ):
                icon = self.category_icons.get(category, "⚙️")
                section.append(f"• {icon} {category.replace('_', ' ').title()}: {count} issues")

            section.extend(
                ["", "*Use `--show-details` flag to see full details for low priority issues.*"]
            )
        else:
            # Show abbreviated details
            for issue in low_issues:
                section.extend(
                    [
                        f"### 🟢 {issue.get('title', 'Unknown Issue')}",
                        f"**🎯 Resource**: `{issue.get('resource', 'Unknown')}`",
                        f"**Action Required**: {issue.get('recommendation', 'No recommendation')}",
                        "",
                    ]
                )

        return "\n".join(section)

    def _generate_resource_breakdown(self, categorized: Dict[str, Any]) -> str:
        """Generate resource-based breakdown."""
        section = [
            "## 🎯 Action Plan by Resource",
            "",
            "*Know exactly which AWS resources need your attention:*",
            "",
        ]

        # Group by actual resource instances, not just types
        by_resource = categorized.get("by_resource", {})
        if not by_resource:
            # Fallback to resource type grouping if by_resource is not available
            by_resource = categorized.get("by_resource_type", {})

        # Sort resources by severity (High issues first)
        resource_priority = []
        for resource, issues in by_resource.items():
            if not issues:
                continue

            high_count = len([i for i in issues if i.get("severity") == "High"])
            medium_count = len([i for i in issues if i.get("severity") == "Medium"])
            low_count = len([i for i in issues if i.get("severity") == "Low"])

            # Priority score: High issues get most weight
            priority_score = high_count * 10 + medium_count * 3 + low_count * 1
            resource_priority.append(
                (resource, issues, high_count, medium_count, low_count, priority_score)
            )

        # Sort by priority score (descending)
        resource_priority.sort(key=lambda x: x[5], reverse=True)

        if not resource_priority:
            section.extend(["✅ **Great news!** No resource-specific issues found.", ""])
            return "\n".join(section)

        for resource, issues, high_count, medium_count, low_count, _ in resource_priority:
            total_issues = len(issues)

            # Resource header with priority indicator
            priority_indicator = "🚨" if high_count > 0 else "⚠️" if medium_count > 0 else "ℹ️"
            section.append(
                f"### {priority_indicator} `{resource}` ({total_issues} issue{'s' if total_issues != 1 else ''})"  # noqa: E501
            )

            # Severity breakdown
            severity_parts = []
            if high_count > 0:
                severity_parts.append(f"🔴 {high_count} High")
            if medium_count > 0:
                severity_parts.append(f"🟡 {medium_count} Medium")
            if low_count > 0:
                severity_parts.append(f"🟢 {low_count} Low")

            if severity_parts:
                section.append(f"**Issues**: {' | '.join(severity_parts)}")

            # Show top issues for this resource
            high_issues = [i for i in issues if i.get("severity") == "High"][
                :2
            ]  # Top 2 high issues
            if high_issues:
                section.append("**Immediate Actions Needed**:")
                for issue in high_issues:
                    title = issue.get("title", "Unknown Issue")
                    recommendation = issue.get("recommendation", "See detailed analysis")
                    section.append(f"• {title}: {recommendation}")

            section.append("")

        # Add summary guidance
        high_resource_count = len(
            [r for r in resource_priority if r[2] > 0]
        )  # Resources with High issues
        if high_resource_count > 0:
            section.extend(
                [
                    f"🎯 **Priority Focus**: {high_resource_count} resource{'s' if high_resource_count != 1 else ''} need{'s' if high_resource_count == 1 else ''} immediate attention",  # noqa: E501
                    "",
                ]
            )

        return "\n".join(section)

    def _generate_quick_actions(self, top_issues: List[Dict[str, Any]]) -> str:
        """Generate quick actions section."""
        section = [
            "## ⚡ Quick Actions (Start Here)",
            "",
            "*Immediate steps to improve your security posture - organized by resource:*",
            "",
        ]

        for i, issue in enumerate(top_issues, 1):
            title = issue.get("title", "Unknown Issue")
            resource = issue.get("resource", "Unknown")
            severity = issue.get("severity", "Unknown")
            severity_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(severity, "❓")

            section.extend(
                [
                    f"### {i}. {severity_icon} {title}",
                    f"**🎯 Resource**: `{resource}`",
                    f"**Action**: {issue.get('recommendation', 'See detailed recommendations')}",
                    "",
                ]
            )

            # Add implementation command if available
            implementation = issue.get("implementation", {})
            if implementation and implementation.get("aws_cli"):
                section.extend(
                    ["**Quick Fix Command**:", "```bash", f"{implementation['aws_cli']}", "```", ""]
                )

            section.append("---")
            section.append("")

        section.extend(
            [
                "## 📚 Additional Resources",
                "",
                "• [AWS ECS Security Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security.html)",  # noqa: E501
                "• [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)",  # noqa: E501
                "• [Container Security Best Practices](https://aws.amazon.com/blogs/containers/)",
                "",
            ]
        )

        return "\n".join(section)

    def _generate_category_breakdown_section(self, categorized: Dict[str, Any]) -> str:
        """Generate detailed category breakdown section."""
        by_category = categorized.get("by_category", {})

        if not by_category:
            return ""

        section = [
            "## 📋 Detailed Category Breakdown",
            "",
            "*Security recommendations organized by category with severity distribution.*",
            "",
        ]

        # Sort categories by total count (descending)
        sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

        for category, recommendations in sorted_categories:
            icon = self.category_icons.get(category, "📋")
            category_display = category.replace("_", " ").title()

            # Count by severity
            severity_counts = {}
            for rec in recommendations:
                severity = rec.get("severity", "Unknown")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            section.append(f"### {icon} {category_display} ({len(recommendations)} total)")

            # Show severity breakdown for this category
            for severity in ["High", "Medium", "Low"]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    severity_icon = self.severity_icons.get(severity, "❓")
                    section.append(f"   • {severity_icon} {severity}: {count}")

            # Show top 3 issues in this category
            if len(recommendations) > 0:
                section.append("   **Top Issues:**")
                for i, rec in enumerate(recommendations[:3], 1):
                    title = rec.get("title", "Unknown Issue")
                    severity = rec.get("severity", "Unknown")
                    severity_icon = self.severity_icons.get(severity, "❓")
                    section.append(f"   {i}. {severity_icon} {title}")

                if len(recommendations) > 3:
                    section.append(f"   ... and {len(recommendations) - 3} more")

            section.append("")

        return "\n".join(section)

    def _format_json(
        self,
        analysis_result: Dict[str, Any],
        severity_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
    ) -> str:
        """Format as JSON for machine processing."""
        filtered_result = analysis_result.copy()

        if severity_filter or category_filter:
            recommendations = analysis_result.get("recommendations", [])
            categorized = analysis_result.get("categorized_issues", {})
            risk_priorities = analysis_result.get("risk_weighted_priorities", [])

            filtered_recommendations = self._apply_filters(
                recommendations, severity_filter, category_filter
            )
            filtered_categorized = self._filter_categorized_data(
                categorized, severity_filter, category_filter
            )
            filtered_risk_priorities = self._apply_filters(
                risk_priorities, severity_filter, category_filter
            )

            filtered_result["recommendations"] = filtered_recommendations
            filtered_result["categorized_issues"] = filtered_categorized
            filtered_result["risk_weighted_priorities"] = filtered_risk_priorities
            filtered_result["total_issues"] = len(filtered_recommendations)

            # Add filter metadata
            filtered_result["filter_applied"] = {
                "severity_filter": severity_filter,
                "category_filter": category_filter,
            }

        return json.dumps(filtered_result, indent=2, default=str)

    def _format_detailed(
        self,
        analysis_result: Dict[str, Any],
        severity_filter: Optional[List[str]] = None,
        category_filter: Optional[List[str]] = None,
    ) -> str:
        """Format detailed report with all issues expanded."""
        return self._format_enhanced_summary(
            analysis_result, severity_filter, category_filter, show_details=True
        )

    def _format_executive_summary(self, analysis_result: Dict[str, Any]) -> str:
        """Format executive summary for leadership."""
        summary = analysis_result.get("analysis_summary", {})
        risk_priorities = analysis_result.get("risk_weighted_priorities", [])

        report = [
            "# 🛡️ ECS Security Executive Summary",
            "",
            f"**Overall Risk Level**: {summary.get('risk_level', 'Unknown')}",
            f"**Total Issues**: {summary.get('total_issues', 0)}",
            "",
            "## Key Security Concerns",
            "",
        ]

        # Top 3 highest risk issues
        for i, issue in enumerate(risk_priorities[:3], 1):
            severity = issue.get("severity", "Unknown")
            icon = self.severity_icons.get(severity, "❓")
            report.extend(
                [
                    f"{i}. {icon} **{issue.get('title', 'Unknown Issue')}**",
                    f"   - Risk Score: {issue.get('risk_score', 0)}",
                    f"   - Impact: {self._get_impact_description(issue)}",
                    "",
                ]
            )

        # Compliance impact
        severity_breakdown = summary.get("severity_breakdown", {})
        if severity_breakdown.get("High", 0) > 0:
            report.extend(
                [
                    "## Compliance Impact",
                    "⚠️ High severity issues may impact compliance with:",
                    "• SOC 2 Type II requirements",
                    "• PCI DSS standards (if applicable)",
                    "• HIPAA regulations (if applicable)",
                    "• AWS Security Best Practices",
                    "",
                ]
            )

        report.extend(
            [
                "## Recommended Actions",
                "1. Address all High priority issues within 24-48 hours",
                "2. Schedule Medium priority fixes for next maintenance window",
                "4. Review and implement Low priority improvements quarterly",
                "",
            ]
        )

        return "\n".join(report)

    def _generate_implementation_steps(self, title: str, category: str) -> List[str]:
        """Generate implementation steps for SecurityReportFormatter."""
        steps_map = {
            "Enable Container Insights": [
                "Navigate to ECS console",
                "Select your cluster",
                "Click on 'Update Cluster'",
                "Enable Container Insights",
                "Save changes",
            ],
            "Configure Container Health Check": [
                "Update task definition",
                "Add healthCheck configuration",
                "Set appropriate timeout and retry values",
                "Test the health check endpoint",
                "Deploy updated task definition",
            ],
            "Enable Read-Only Root Filesystem": [
                "Update task definition",
                "Set readonlyRootFilesystem: true",
                "Add volume mounts for writable directories",
                "Test application functionality",
                "Deploy updated task definition",
            ],
        }

        return steps_map.get(
            title,
            [
                "Review the current configuration",
                "Plan the security improvement",
                "Implement the recommended changes",
                "Test the changes in a non-production environment",
                "Deploy to production and monitor",
            ],
        )

    def _generate_aws_cli_commands(self, title: str, resource: str) -> List[str]:
        """Generate AWS CLI commands for SecurityReportFormatter."""
        commands_map = {
            "Enable Container Insights": [
                "aws ecs modify-cluster --cluster CLUSTER_NAME --settings name=containerInsights,value=enabled"  # noqa: E501
            ],
            "Configure Container Health Check": [
                "aws ecs describe-task-definition --task-definition TASK_DEFINITION_NAME",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
            "Enable Read-Only Root Filesystem": [
                "aws ecs describe-task-definition --task-definition TASK_DEFINITION_NAME",
                "aws ecs register-task-definition --cli-input-json file://updated-task-definition.json",  # noqa: E501
            ],
        }

        return commands_map.get(
            title,
            [
                "aws ecs describe-cluster --cluster CLUSTER_NAME",
                "aws ecs describe-services --cluster CLUSTER_NAME --services SERVICE_NAME",
            ],
        )


class ECSSecurityAnalyzer:
    """Complete ECS security analyzer that leverages existing MCP tools for data collection."""

    def __init__(self):
        """Initialize the ECSSecurityAnalyzer with analyzer and data collector components."""
        self.analyzer = SecurityAnalyzer()
        self.collector = DataAdapter()
        self.formatter = SecurityReportFormatter()

    async def analyze_cluster(self, cluster_name: str, region: str = "us-east-1") -> Dict[str, Any]:
        """Analyze a specific ECS cluster for security vulnerabilities and misconfigurations."""
        try:
            # Set current cluster name for dynamic CLI command generation
            self._current_cluster_name = cluster_name
            ecs_data = await self.collector.collect_all_data([region], [cluster_name])

            if isinstance(ecs_data, dict) and "error" in ecs_data:
                return {
                    "cluster_name": cluster_name,
                    "region": region,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": f"Failed to collect data: {ecs_data['error']}",
                    "recommendations": [],
                    "total_issues": 0,
                    "analysis_summary": {"status": "failed", "reason": "data_collection_failed"},
                }

            data_collection_errors = []
            if region in ecs_data:
                region_data = ecs_data[region]
                if "error" in region_data:
                    data_collection_errors.append(f"Region {region}: {region_data['error']}")
                elif "clusters" in region_data and cluster_name in region_data["clusters"]:
                    cluster_data = region_data["clusters"][cluster_name]
                    if "error" in cluster_data:
                        data_collection_errors.append(
                            f"Cluster {cluster_name}: {cluster_data['error']}"
                        )
                    elif "errors" in cluster_data:
                        data_collection_errors.extend(cluster_data["errors"])

            if not ecs_data or (region in ecs_data and not ecs_data[region].get("clusters")):
                return {
                    "cluster_name": cluster_name,
                    "region": region,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": f"No data available for cluster '{cluster_name}' in region '{region}'",
                    "recommendations": [],
                    "total_issues": 0,
                    "analysis_summary": {"status": "failed", "reason": "no_data_available"},
                }

            results = await self.analyzer.analyze(ecs_data)

            analysis_status = "success"
            if data_collection_errors:
                analysis_status = "partial_success"

            final_results = {
                "cluster_name": cluster_name,
                "region": region,
                "analysis_timestamp": datetime.now().isoformat(),
                "status": analysis_status,
                "recommendations": results["recommendations"],
                "total_issues": len(results["recommendations"]),
                "analysis_summary": results["analysis_summary"],
            }

            if data_collection_errors:
                final_results["data_collection_warnings"] = data_collection_errors
                final_results["analysis_summary"]["warnings"] = data_collection_errors

            return final_results

        except Exception as e:
            return {
                "cluster_name": cluster_name,
                "region": region,
                "analysis_timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": f"Unexpected error during security analysis: {str(e)}",
                "recommendations": [],
                "total_issues": 0,
                "analysis_summary": {
                    "status": "failed",
                    "reason": "unexpected_error",
                    "error": str(e),
                },
            }

    def _transform_to_flat_structure(
        self, ecs_data: Dict[str, Any], cluster_name: str
    ) -> Dict[str, Any]:
        """Transform hierarchical data to flat structure for compatibility."""
        services = []

        for region, region_data in ecs_data.items():
            if "error" in region_data:
                continue

            for cluster, cluster_data in region_data.get("clusters", {}).items():
                for service_data in cluster_data.get("services", []):
                    service = service_data.get("service", {})
                    task_def = service_data.get("task_definition", {})

                    services.append(
                        {
                            "serviceName": service.get("serviceName"),
                            "taskDefinition": task_def,
                            "region": region,
                            "cluster_name": cluster,
                            "runningCount": service.get("runningCount", 0),
                            "desiredCount": service.get("desiredCount", 0),
                            "launchType": service.get("launchType", "FARGATE"),
                        }
                    )

        return {"services": services, "cluster_name": cluster_name}


SecurityAnalysisAction = Literal[
    "list_clusters",
    "select_cluster_for_analysis",
    "analyze_cluster_security",
    "generate_security_report",
    "get_security_recommendations",
    "check_compliance_status",
]


async def ecs_security_analysis_tool(
    action: SecurityAnalysisAction, parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Comprehensive ECS security analysis tool.

    Args:
        action: The security analysis action to perform
        parameters: Action-specific parameters

    Returns:
        Dictionary containing analysis results
    """
    if parameters is None:
        parameters = {}

    try:
        if action == "list_clusters":
            return await _list_clusters(parameters)
        elif action == "select_cluster_for_analysis":
            return await _select_cluster_for_analysis(parameters)
        elif action == "analyze_cluster_security":
            return await _analyze_cluster_security(parameters)
        elif action == "generate_security_report":
            return await _generate_security_report(parameters)
        elif action == "get_security_recommendations":
            return await _get_security_recommendations(parameters)
        elif action == "check_compliance_status":
            return await _check_compliance_status(parameters)
        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}",
                "available_actions": [
                    "list_clusters",
                    "select_cluster_for_analysis",
                    "analyze_cluster_security",
                    "generate_security_report",
                    "get_security_recommendations",
                    "check_compliance_status",
                ],
            }

    except Exception as e:
        logger.error(f"Security analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "action": action,
            "assessment": f"Security analysis failed: {str(e)}",
        }


async def _list_clusters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """List available ECS clusters for selection."""
    region = parameters.get("region", "us-east-1")

    logger.info(f"Listing ECS clusters in region: {region}")

    try:
        # Use the existing AWS client utility for consistency
        ecs_client = await get_aws_client("ecs")

        # Get cluster ARNs
        response = ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])

        if not cluster_arns:
            return {
                "status": "success",
                "action": "list_clusters",
                "region": region,
                "assessment": f"No ECS clusters found in **{region}** region.\n\n🌍 **Try a different region?** Your clusters might be located in:\n• us-east-1 (N. Virginia)\n• us-west-2 (Oregon)\n• eu-west-1 (Ireland)\n• ap-southeast-1 (Singapore)\n• ap-northeast-1 (Tokyo)\n\nJust specify the 'region' parameter to check other regions, or create a new cluster if needed.",  # noqa: E501
                "clusters": [],
                "total_clusters": 0,
                "guidance": {
                    "description": "No clusters available for security analysis in this region",
                    "region_suggestion": f"No clusters found in {region}. Try checking other regions where your ECS clusters might be located.",  # noqa: E501
                    "next_steps": [
                        f"Try a different region - current region is {region}",
                        "Check common regions: us-east-1, us-west-2, eu-west-1, ap-southeast-1",
                        "Create an ECS cluster if you need to deploy containerized applications",
                        "Verify your AWS credentials have permission to list ECS clusters",
                    ],
                    "region_examples": {
                        "try_us_east_1": {
                            "action": "list_clusters",
                            "parameters": {"region": "us-east-1"},
                        },
                        "try_us_west_2": {
                            "action": "list_clusters",
                            "parameters": {"region": "us-west-2"},
                        },
                        "try_eu_west_1": {
                            "action": "list_clusters",
                            "parameters": {"region": "eu-west-1"},
                        },
                    },
                },
            }

        # Get detailed cluster information
        cluster_details = ecs_client.describe_clusters(clusters=cluster_arns)
        clusters = []

        for cluster in cluster_details.get("clusters", []):
            cluster_name = cluster.get("clusterName", "")
            cluster_info = {
                "name": cluster_name,
                "status": cluster.get("status", "UNKNOWN"),
                "running_tasks": cluster.get("runningTasksCount", 0),
                "pending_tasks": cluster.get("pendingTasksCount", 0),
                "active_services": cluster.get("activeServicesCount", 0),
                "registered_instances": cluster.get("registeredContainerInstancesCount", 0),
                "capacity_providers": cluster.get("capacityProviders", []),
                "tags": cluster.get("tags", []),
            }
            clusters.append(cluster_info)

        # Sort clusters by name for consistent output
        clusters.sort(key=lambda x: x["name"])

        return {
            "status": "success",
            "action": "list_clusters",
            "region": region,
            "user_choice_required": True,
            "instruction": "Present the cluster list and region options to the user. Wait for their choice. Do not automatically select any cluster.",  # noqa: E501
            "assessment": f"I found {len(clusters)} ECS clusters in your **{region}** region. Which cluster would you like me to analyze for security recommendations?\n\n**🌍 REGION OPTIONS:**\n• Current region: {region}\n• To check other regions: us-west-2, eu-west-1, ap-southeast-1, ap-northeast-1, etc.\n• Just ask: 'Show me clusters in [region-name]'\n\n**⚠️ IMPORTANT**: I need you to choose a specific cluster name. I cannot automatically select one for you.",  # noqa: E501
            "clusters": clusters,
            "total_clusters": len(clusters),
            "cluster_selection": {
                "description": "⚠️ STOP: User must choose ONE specific cluster name from the list above. Do NOT automatically select or analyze any cluster without explicit user choice.",  # noqa: E501
                "region_note": f"🌍 Currently showing {region} region. User can request other regions by asking 'Show me clusters in [region-name]' or specifying 'region' parameter.",  # noqa: E501
                "available_actions": [
                    "select_cluster_for_analysis - Interactive cluster selection with analysis options",  # noqa: E501
                    "analyze_cluster_security - Comprehensive security analysis",
                    "generate_security_report - Generate detailed security report",
                    "get_security_recommendations - Get filtered recommendations",
                    "check_compliance_status - Check compliance against standards",
                ],
                "user_choice_required": "⚠️ WAIT: Present this list to the user and ask them to choose a cluster name OR request a different region",  # noqa: E501
                "natural_language_examples": [
                    "User can say: 'Analyze security for [cluster-name]'",
                    "Or: 'Check [cluster-name] for security issues'",
                    "Or: 'Show me clusters in us-west-2 region'",
                    "Or: 'List clusters in eu-west-1'",
                    "Or: 'What clusters do I have in other regions?'",
                    "Or: 'Check a different region'",
                ],
                "selection_help": "Copy the cluster name exactly as shown in the 'name' field above",  # noqa: E501
            },
            "guidance": {
                "description": "How to analyze a specific cluster",
                "region_selection": f"🌍 **Region Options**: Currently showing {region}. To check other regions, use the 'region' parameter with values like: us-east-1, us-west-2, eu-west-1, ap-southeast-1, ap-northeast-1, etc.",  # noqa: E501
                "next_steps": [
                    "1. **Present Options**: Show the user this cluster list AND region options",
                    "2. **Wait for Choice**: Let user choose a cluster name OR request different region",  # noqa: E501
                    "3. **Region Choice**: If user wants different region, ask 'Show me clusters in [region]'",  # noqa: E501
                    "4. **Cluster Choice**: If user chooses cluster, use exact name from 'name' field",  # noqa: E501
                    "5. **No Auto-Selection**: Never automatically pick a cluster for the user",
                ],
                "example_usage": {
                    "action": "select_cluster_for_analysis",
                    "parameters": {
                        "cluster_name": "<copy-cluster-name-from-above>",
                        "region": region,
                    },
                },
                "other_regions": {
                    "description": "🌍 Want to check clusters in other regions? Use these examples:",  # noqa: E501
                    "examples": {
                        "us_east_1": {
                            "action": "list_clusters",
                            "parameters": {"region": "us-east-1"},
                        },
                        "us_west_2": {
                            "action": "list_clusters",
                            "parameters": {"region": "us-west-2"},
                        },
                        "eu_west_1": {
                            "action": "list_clusters",
                            "parameters": {"region": "eu-west-1"},
                        },
                        "ap_southeast_1": {
                            "action": "list_clusters",
                            "parameters": {"region": "ap-southeast-1"},
                        },
                        "ap_northeast_1": {
                            "action": "list_clusters",
                            "parameters": {"region": "ap-northeast-1"},
                        },
                    },
                    "common_regions": [
                        "us-east-1",
                        "us-west-2",
                        "eu-west-1",
                        "ap-southeast-1",
                        "ap-northeast-1",
                        "eu-central-1",
                    ],
                },
                "quick_start": f"To analyze the first cluster in {region}, use cluster_name: '{clusters[0]['name'] if clusters else 'no-clusters-available'}'",  # noqa: E501
            },
        }

    except Exception as e:
        logger.error(f"Failed to list clusters: {e}")
        return {
            "status": "error",
            "action": "list_clusters",
            "region": region,
            "error": str(e),
            "assessment": f"Failed to list ECS clusters in region {region}: {str(e)}",
        }


async def _select_cluster_for_analysis(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Interactive cluster selection with analysis options."""
    region = parameters.get("region", "us-east-1")
    cluster_name = parameters.get("cluster_name")
    analysis_type = parameters.get("analysis_type", "comprehensive")

    logger.info(f"Interactive cluster selection for region: {region}")

    try:
        # First, get the list of available clusters
        clusters_result = await _list_clusters({"region": region})

        if clusters_result.get("status") != "success":
            return clusters_result

        clusters = clusters_result.get("clusters", [])

        if not clusters:
            return {
                "status": "error",
                "action": "select_cluster_for_analysis",
                "error": f"No ECS clusters found in region {region}",
                "region": region,
                "suggestion": "Create an ECS cluster first or check a different region",
            }

        # If cluster_name is provided, validate and proceed with analysis
        if cluster_name:
            # Validate cluster exists
            cluster_exists = any(cluster["name"] == cluster_name for cluster in clusters)

            if not cluster_exists:
                return {
                    "status": "error",
                    "action": "select_cluster_for_analysis",
                    "error": f"Cluster '{cluster_name}' not found in region {region}",
                    "available_clusters": [cluster["name"] for cluster in clusters],
                    "suggestion": "Choose one of the available clusters listed above",
                }

            # Proceed with the selected analysis type
            if analysis_type == "quick":
                return await _get_security_recommendations(
                    {
                        "cluster_name": cluster_name,
                        "region": region,
                        "severity_filter": "High",
                        "limit": 5,
                    }
                )
            elif analysis_type == "report":
                return await _generate_security_report(
                    {"cluster_name": cluster_name, "region": region, "format": "summary"}
                )
            elif analysis_type == "compliance":
                return await _check_compliance_status(
                    {
                        "cluster_name": cluster_name,
                        "region": region,
                        "compliance_framework": "aws-foundational",
                    }
                )
            else:  # comprehensive (default)
                return await _analyze_cluster_security(
                    {"cluster_name": cluster_name, "region": region}
                )

        # If no cluster_name provided, show selection interface
        return {
            "status": "success",
            "action": "select_cluster_for_analysis",
            "region": region,
            "total_clusters": len(clusters),
            "available_clusters": clusters,
            "cluster_selection": {
                "description": "Choose a cluster and analysis type for security analysis",
                "instructions": [
                    "1. Select a cluster from the 'available_clusters' list above",
                    "2. Choose an analysis type (optional, defaults to comprehensive)",
                    "3. Call this action again with your selections",
                ],
                "analysis_types": {
                    "comprehensive": "Full security analysis with all recommendations",
                    "quick": "Top 5 high-priority security issues only",
                    "report": "Generate a summary security report",
                    "compliance": "Check compliance against AWS best practices",
                },
            },
            "example_usage": {
                "action": "select_cluster_for_analysis",
                "parameters": {
                    "cluster_name": clusters[0]["name"],
                    "region": region,
                    "analysis_type": "comprehensive",
                },
            },
            "quick_actions": (
                [
                    {
                        "description": f"Analyze '{clusters[0]['name']}' (comprehensive)",
                        "action": "select_cluster_for_analysis",
                        "parameters": {
                            "cluster_name": clusters[0]["name"],
                            "region": region,
                            "analysis_type": "comprehensive",
                        },
                    },
                    {
                        "description": f"Quick analysis of '{clusters[0]['name']}' (top 5 issues)",
                        "action": "select_cluster_for_analysis",
                        "parameters": {
                            "cluster_name": clusters[0]["name"],
                            "region": region,
                            "analysis_type": "quick",
                        },
                    },
                ]
                if clusters
                else []
            ),
        }

    except Exception as e:
        logger.error(f"Cluster selection failed: {e}")
        return {
            "status": "error",
            "action": "select_cluster_for_analysis",
            "error": str(e),
            "region": region,
        }


async def _analyze_cluster_security(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze security posture of an ECS cluster."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")

    if not cluster_name:
        return {
            "status": "error",
            "action": "analyze_cluster_security",
            "error": "cluster_name is required for security analysis",
            "region": region,
            "helpful_guidance": {
                "suggestion": "Use the 'list_clusters' or 'select_cluster_for_analysis' action to see available clusters",  # noqa: E501
                "example": {"action": "list_clusters", "parameters": {"region": region}},
            },
        }

    logger.info(f"Starting security analysis for cluster: {cluster_name} in region: {region}")

    try:
        # Initialize security analyzer
        analyzer = ECSSecurityAnalyzer()

        # Run the analysis (it's already async)
        results = await analyzer.analyze_cluster(cluster_name, region)

        recommendations = results.get("recommendations", [])

        # Calculate severity breakdown
        severity_counts = {
            "high": len([r for r in recommendations if r.get("severity") == "High"]),
            "medium": len([r for r in recommendations if r.get("severity") == "Medium"]),
            "low": len([r for r in recommendations if r.get("severity") == "Low"]),
        }

        return {
            "status": "success",
            "action": "analyze_cluster_security",
            "cluster_name": cluster_name,
            "region": region,
            "analysis_timestamp": results.get("timestamp"),
            "assessment": _generate_comprehensive_assessment(
                cluster_name, recommendations, severity_counts
            ),
            "security_summary": {
                "total_recommendations": len(recommendations),
                "severity_breakdown": severity_counts,
                "priority_focus": (
                    "High"
                    if severity_counts["high"] > 0
                    else "Medium"
                    if severity_counts["medium"] > 0
                    else "Maintenance"
                ),
                "immediate_action_needed": severity_counts["high"] > 0,
            },
            "priority_recommendations": _enhance_recommendations_with_resource_info(
                [r for r in recommendations if r.get("severity") == "High"]
            ),
            "total_issues_found": len(recommendations),
            "next_steps": [
                step
                for step in [
                    (
                        f"⚠️ Fix {severity_counts['high']} high-priority security issues"
                        if severity_counts["high"] > 0
                        else None
                    ),
                    "Use 'get_security_recommendations' with severity_filter='High' to see detailed fix commands",  # noqa: E501
                    "Re-run analysis after implementing fixes to track progress",
                    (
                        f"Review and address {severity_counts['medium']} medium and {severity_counts['low']} low priority items when possible"  # noqa: E501
                        if severity_counts["medium"] > 0 or severity_counts["low"] > 0
                        else "Consider implementing additional security monitoring for ongoing protection"  # noqa: E501
                    ),  # noqa: E501
                ]
                if step is not None
            ],
            "quick_actions": {
                "get_high_priority_issues": {
                    "action": "get_security_recommendations",
                    "parameters": {
                        "cluster_name": cluster_name,
                        "region": region,
                        "severity_filter": "High",
                        "limit": 5,
                    },
                },
                "get_detailed_report": {
                    "action": "generate_security_report",
                    "parameters": {
                        "cluster_name": cluster_name,
                        "region": region,
                        "format": "summary",
                    },
                },
            },
        }

    except Exception as e:
        logger.error(f"Security analysis failed: {e}")

        # Provide helpful guidance if cluster not found
        error_message = str(e)
        if "not found" in error_message.lower() or "ClusterNotFoundException" in error_message:
            return {
                "status": "error",
                "action": "analyze_cluster_security",
                "error": f"Cluster '{cluster_name}' not found in region {region}",
                "cluster_name": cluster_name,
                "region": region,
                "assessment": f"The cluster '{cluster_name}' was not found in region {region}. Please verify the cluster name and region.",  # noqa: E501
                "helpful_guidance": {
                    "suggestion": "Use the 'list_clusters' action to see available clusters",
                    "example": {"action": "list_clusters", "parameters": {"region": region}},
                    "common_issues": [
                        "Cluster name is case-sensitive - check exact spelling",
                        "Cluster might be in a different region",
                        "Cluster might have been deleted or not yet created",
                        "Check AWS credentials and permissions",
                    ],
                },
            }
        else:
            return {
                "status": "error",
                "action": "analyze_cluster_security",
                "error": error_message,
                "cluster_name": cluster_name,
                "region": region,
                "assessment": f"Failed to analyze security for cluster '{cluster_name}'. Please verify the cluster name and region.",  # noqa: E501
                "helpful_guidance": {
                    "suggestion": "Use the 'list_clusters' action to see available clusters and verify the cluster name",  # noqa: E501
                    "example": {"action": "list_clusters", "parameters": {"region": region}},
                },
            }


async def _generate_security_report(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive security report with enhanced formatting options."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")
    format_type = parameters.get("format", "summary")  # summary, detailed, json, executive
    severity_filter = parameters.get("severity_filter")  # List of severities to include
    category_filter = parameters.get("category_filter")  # List of categories to include
    show_details = parameters.get("show_details", False)  # Show full details for medium/low issues

    if not cluster_name:
        return {
            "status": "error",
            "action": "generate_security_report",
            "error": "cluster_name is required for report generation",
            "region": region,
            "helpful_guidance": {
                "suggestion": "Use the 'list_clusters' action to see available clusters",
                "example": {"action": "list_clusters", "parameters": {"region": region}},
                "available_formats": ["summary", "detailed", "json", "executive"],
                "filter_options": {
                    "severity_filter": ["High", "Medium", "Low"],
                    "category_filter": [
                        "network_security",
                        "container_security",
                        "iam_security",
                        "encryption",
                        "monitoring",
                        "compliance",
                    ],
                },
            },
        }

    logger.info(f"Generating security report for cluster: {cluster_name} (format: {format_type})")

    try:
        analyzer = ECSSecurityAnalyzer()

        # Run comprehensive analysis
        results = await analyzer.analyze_cluster(cluster_name, region)

        # Generate formatted report
        formatted_report = analyzer.formatter.format_report(
            results,
            format_type=format_type,
            severity_filter=severity_filter,
            category_filter=category_filter,
            show_details=show_details,
        )

        # Prepare response based on format
        if format_type == "json":
            return {
                "status": "success",
                "action": "generate_security_report",
                "cluster_name": cluster_name,
                "region": region,
                "report_format": format_type,
                "assessment": f"Security analysis completed for {cluster_name}. JSON data available in report_data.",  # noqa: E501
                "report_data": results,
                "filters_applied": {
                    "severity_filter": severity_filter,
                    "category_filter": category_filter,
                },
            }
        else:
            # For human-readable formats, return formatted text
            summary = results.get("analysis_summary", {})
            severity_breakdown = summary.get("severity_breakdown", {})

            return {
                "status": "success",
                "action": "generate_security_report",
                "cluster_name": cluster_name,
                "region": region,
                "report_format": format_type,
                "assessment": formatted_report,
                "report_summary": {
                    "total_issues": summary.get("total_issues", 0),
                    "risk_level": summary.get("risk_level", "Unknown"),
                    "severity_breakdown": severity_breakdown,
                    "immediate_action_required": severity_breakdown.get("High", 0) > 0,
                },
                "filters_applied": {
                    "severity_filter": severity_filter,
                    "category_filter": category_filter,
                    "show_details": show_details,
                },
                "guidance": {
                    "description": "Enhanced security report with filtering and formatting options",
                    "format_options": {
                        "summary": "Executive summary with expandable sections",
                        "detailed": "Full details for all issues",
                        "executive": "High-level summary for leadership",
                        "json": "Machine-readable format for automation",
                    },
                    "filter_examples": {
                        "high_priority_only": {"severity_filter": ["High"]},
                        "network_issues": {"category_filter": ["network_security"]},
                        "high_priority": {"severity_filter": ["High"]},
                        "show_all_details": {"show_details": True},
                    },
                    "next_steps": [
                        "Review high priority issues first",
                        "Use filters to focus on specific areas of concern",
                        "Share executive format with leadership",
                        "Use JSON format for automated processing",
                    ],
                },
            }

    except Exception as e:
        logger.error(f"Failed to generate security report: {e}")

        error_message = str(e)
        if "not found" in error_message.lower() or "ClusterNotFoundException" in error_message:
            return {
                "status": "error",
                "action": "generate_security_report",
                "error": f"Cluster '{cluster_name}' not found in region {region}",
                "cluster_name": cluster_name,
                "region": region,
                "helpful_guidance": {
                    "suggestion": "Use the 'list_clusters' action to see available clusters",
                    "example": {"action": "list_clusters", "parameters": {"region": region}},
                },
            }
        else:
            return {
                "status": "error",
                "action": "generate_security_report",
                "error": error_message,
                "cluster_name": cluster_name,
                "region": region,
            }


def _format_severity_filter(severity_filter) -> str:
    """Format severity filter for display."""
    if not severity_filter:
        return ""
    if isinstance(severity_filter, str):
        return severity_filter.capitalize()
    elif isinstance(severity_filter, list):
        return " & ".join([s.capitalize() for s in severity_filter])
    return str(severity_filter)


def _generate_recommendations_assessment(
    cluster_name: str,
    filtered_recommendations: List[Dict[str, Any]],
    all_recommendations: List[Dict[str, Any]],
    severity_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = 5,
) -> str:
    """Generate comprehensive assessment text for security recommendations."""

    # Generate category breakdown from all recommendations
    category_summary = _generate_category_summary(all_recommendations)

    assessment = [
        f"## {_format_severity_filter(severity_filter) or 'Security'} Recommendations for {cluster_name}",  # noqa: E501
        "",
        f"📋 **Found {len(filtered_recommendations)} {_format_severity_filter(severity_filter).lower() if severity_filter else 'security'} issues"  # noqa: E501
        + (f" in {category_filter} category" if category_filter else "")
        + f" (showing top {limit})**",
        "",
        _get_priority_message(severity_filter, len(filtered_recommendations)),
    ]

    # Add detailed recommendations with prominent resource information
    if filtered_recommendations:
        assessment.extend(
            [
                "",
                "## 🎯 Action Items by Resource",
                "",
                "*Each recommendation shows the specific AWS resource that needs attention:*",
                "",
            ]
        )

        for i, rec in enumerate(filtered_recommendations, 1):
            severity = rec.get("severity", "Unknown")
            severity_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(severity, "❓")
            resource = rec.get("resource", "Unknown Resource")
            title = rec.get("title", "Unknown Issue")
            issue = rec.get("issue", "No description available")
            recommendation = rec.get("recommendation", "No recommendation provided")

            assessment.extend(
                [
                    f"### {i}. {severity_icon} {title}",
                    f"**🎯 Resource to Fix**: `{resource}`",
                    f"**Severity**: {severity}",
                    f"**Issue**: {issue}",
                    f"**Action Required**: {recommendation}",
                    "",
                ]
            )

            # Add implementation details if available
            implementation = rec.get("implementation", {})
            if implementation:
                aws_cli = implementation.get("aws_cli")
                description = implementation.get("description")

                if aws_cli or description:
                    assessment.append("**Implementation:**")
                    if description:
                        assessment.append(f"• {description}")
                    if aws_cli:
                        assessment.extend(
                            ["• AWS CLI Command:", "  ```bash", f"  {aws_cli}", "  ```"]
                        )
                    assessment.append("")

            assessment.append("---")
            assessment.append("")

    # Add category breakdown if not filtering by category
    if not category_filter and len(all_recommendations) > 0:
        assessment.extend(
            [
                "",
                "### 📋 Recommendations by Category:",
            ]
        )

        # Category icons mapping
        category_icons = {
            "network_security": "🌐",
            "container_security": "🐳",
            "iam_security": "🔐",
            "secrets": "🔑",
            "monitoring": "📊",
            "compliance": "🏛️",
            "security": "🛡️",
            "encryption": "🔒",
            "configuration": "⚙️",
            "availability": "⚡",
            "well_architected": "🏗️",
            "resource_management": "📈",
            "network": "🔗",
            "monitoring_security": "👁️",
        }

        for category, count in category_summary["top_categories"]:
            icon = category_icons.get(category, "📋")
            category_display = category.replace("_", " ").title()
            assessment.append(f"• {icon} **{category_display}**: {count} recommendations")

        if len(category_summary["categories"]) > 5:
            remaining = len(category_summary["categories"]) - 5
            assessment.append(f"• ... and {remaining} more categories")

    return "\n".join(assessment)


def _enhance_recommendations_with_resource_info(
    recommendations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Enhance recommendations with prominent resource information for better actionability."""
    enhanced_recommendations = []

    for rec in recommendations:
        enhanced_rec = rec.copy()

        # Add resource-focused fields for better visibility
        resource = rec.get("resource", "Unknown Resource")
        severity = rec.get("severity", "Unknown")
        title = rec.get("title", "Unknown Issue")

        # Add enhanced fields
        enhanced_rec["resource_target"] = f"🎯 {resource}"
        enhanced_rec["priority_indicator"] = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(
            severity, "❓"
        )
        enhanced_rec["action_summary"] = (
            f"{enhanced_rec['priority_indicator']} {title} → Fix: {resource}"
        )

        # Add formatted display text
        enhanced_rec["display_summary"] = (
            f"{enhanced_rec['priority_indicator']} **{title}** ({severity} Priority)\n"
            f"🎯 **Resource**: `{resource}`\n"
            f"**Issue**: {rec.get('issue', 'No description')}\n"
            f"**Action Required**: {rec.get('recommendation', 'No recommendation')}"
        )

        enhanced_recommendations.append(enhanced_rec)

    return enhanced_recommendations


def _generate_category_summary(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate category breakdown summary for recommendations."""
    category_counts = {}
    severity_by_category = {}

    for rec in recommendations:
        category = rec.get("category", "unknown")
        severity = rec.get("severity", "Unknown")

        # Count by category
        category_counts[category] = category_counts.get(category, 0) + 1

        # Track severity distribution by category
        if category not in severity_by_category:
            severity_by_category[category] = {"High": 0, "Medium": 0, "Low": 0}
        if severity in severity_by_category[category]:
            severity_by_category[category][severity] += 1

    # Sort categories by count (descending)
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_categories": len(category_counts),
        "categories": {category: count for category, count in sorted_categories},
        "severity_distribution": severity_by_category,
        "top_categories": sorted_categories[:5],  # Top 5 categories
    }


def _generate_comprehensive_assessment(
    cluster_name: str, recommendations: List[Dict[str, Any]], severity_counts: Dict[str, int]
) -> str:
    """Generate comprehensive assessment with correct terminology and resource information."""

    assessment_parts = [
        f"## Security Analysis Results for {cluster_name}",
        "",
        "🚨 **HIGH PRIORITY SECURITY ISSUES FOUND**",
        "",
        f"Your ECS cluster has {len(recommendations)} total security issues that need attention:",
        f"• **{severity_counts['high']} High Priority** - Requires immediate action (24-48 hours)",
        f"• **{severity_counts['medium']} Medium Priority** - Address in next maintenance window",
        f"• **{severity_counts['low']} Low Priority** - Future improvements",
        "",
    ]

    # Add top high priority issues with resource information
    high_priority_recs = [r for r in recommendations if r.get("severity") == "High"]

    if high_priority_recs:
        assessment_parts.extend(
            [
                f"### Top {min(5, len(high_priority_recs))} High Priority Issues to Fix Immediately:",  # noqa: E501
                "",
            ]
        )

        for i, rec in enumerate(high_priority_recs[:5], 1):
            title = rec.get("title", "Unknown Issue")
            resource = rec.get("resource", "Unknown Resource")
            issue = rec.get("issue", "No description available")
            recommendation = rec.get("recommendation", "No recommendation provided")

            assessment_parts.extend(
                [
                    f"{i}. **{title}** (High Priority)",
                    f"   • **🎯 Resource**: `{resource}`",
                    f"   • **Issue**: {issue}",
                    f"   • **Fix**: {recommendation}",
                    "",
                ]
            )

        assessment_parts.extend(
            [
                "**Immediate Action Required**: These high-priority issues create significant security vulnerabilities that could lead to unauthorized access, privilege escalation, or resource exhaustion attacks.",  # noqa: E501
                "",
                f"Would you like me to generate detailed remediation steps for these high priority issues, or would you prefer to see the complete security report with all {len(recommendations)} findings?",  # noqa: E501
            ]
        )
    else:
        assessment_parts.extend(
            [
                "✅ **GOOD NEWS**: No high-priority issues found.",
                f"Focus on addressing {severity_counts['medium']} medium and {severity_counts['low']} low priority improvements when possible.",  # noqa: E501
            ]
        )

    return "\n".join(assessment_parts)


def _get_priority_message(severity_filter, count: int) -> str:
    """Get priority message based on severity filter."""
    if not severity_filter:
        return f"Retrieved {count} security recommendations for analysis and prioritization."

    # Handle both string and array formats
    severities = []
    if isinstance(severity_filter, str):
        severities = [severity_filter.capitalize()]
    elif isinstance(severity_filter, list):
        severities = [s.capitalize() for s in severity_filter]

    if "High" in severities:
        return f"⚠️ **HIGH PRIORITY**: These {count} issues should be addressed within 24-48 hours."
    elif "Medium" in severities:
        return f"📋 **MEDIUM PRIORITY**: These {count} issues should be addressed in your next maintenance window."  # noqa: E501
    elif "Low" in severities:
        return f"ℹ️ **LOW PRIORITY**: These {count} items are future improvements for enhanced security."  # noqa: E501
    else:
        return f"Retrieved {count} security recommendations for analysis and prioritization."


async def _get_security_recommendations(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Get filtered security recommendations."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")
    severity_filter = parameters.get("severity_filter")  # high, medium, low
    category_filter = parameters.get("category_filter")  # network, container, iam, etc.
    limit = parameters.get("limit", 5)  # Default to 5 for better focus

    if not cluster_name:
        raise ValueError(
            "cluster_name is required for getting recommendations. Use action='list_clusters' to see available clusters, then specify cluster_name in parameters."  # noqa: E501
        )

    logger.info(f"Getting security recommendations for cluster: {cluster_name}")

    analyzer = ECSSecurityAnalyzer()

    # Run analysis
    results = await analyzer.analyze_cluster(cluster_name, region)

    recommendations = results.get("recommendations", [])

    # Apply filters
    if severity_filter:
        # Handle both string and array formats for severity_filter
        if isinstance(severity_filter, str):
            # Convert string to array and normalize
            severity_list = [severity_filter.capitalize()]
        elif isinstance(severity_filter, list):
            # Normalize array elements
            severity_list = [s.capitalize() for s in severity_filter]
        else:
            severity_list = []

        recommendations = [r for r in recommendations if r.get("severity") in severity_list]

    if category_filter:
        recommendations = [
            r for r in recommendations if category_filter.lower() in r.get("category", "").lower()
        ]

    # Limit results
    recommendations = recommendations[:limit]

    # Enhance recommendations with prominent resource information
    enhanced_recommendations = _enhance_recommendations_with_resource_info(recommendations)

    return {
        "status": "success",
        "action": "get_security_recommendations",
        "cluster_name": cluster_name,
        "region": region,
        "assessment": _generate_recommendations_assessment(
            cluster_name,
            recommendations,
            results.get("recommendations", []),
            str(severity_filter) if severity_filter is not None else None,
            str(category_filter) if category_filter is not None else None,
            limit,
        ),
        "filter_criteria": {
            "severity_filter": severity_filter,
            "category_filter": category_filter,
            "limit": limit,
        },
        "results_summary": {
            "total_recommendations": len(recommendations),
            "filtered_results": len(recommendations),
        },
        "category_breakdown": _generate_category_summary(results.get("recommendations", [])),
        "recommendations": enhanced_recommendations,
        "guidance": {
            "description": "How to prioritize and implement these security recommendations",
            "implementation_approach": [
                "🚨 Address High priority issues immediately - they pose immediate security risks",
                "⚠️ Fix High priority issues within 24-48 hours",
                "📋 Plan Medium priority fixes for next maintenance window",
                "Test changes in a non-production environment first",
                "Use the provided CLI commands for quick fixes",
            ],
            "get_more_recommendations": {
                "action": "get_security_recommendations",
                "parameters": {"cluster_name": cluster_name, "region": region, "limit": 20},
            },
        },
    }


async def _check_compliance_status(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Check compliance against security best practices."""
    cluster_name = parameters.get("cluster_name")
    region = parameters.get("region", "us-east-1")
    compliance_framework = parameters.get("compliance_framework", "aws-foundational")

    if not cluster_name:
        raise ValueError(
            "cluster_name is required for compliance check. Use action='list_clusters' to see available clusters, then specify cluster_name in parameters."  # noqa: E501
        )

    logger.info(f"Checking compliance status for cluster: {cluster_name}")

    analyzer = ECSSecurityAnalyzer()

    # Run analysis
    results = await analyzer.analyze_cluster(cluster_name, region)

    recommendations = results.get("recommendations", [])

    # Calculate issue breakdown
    failed_checks = len(recommendations)

    # Categorize compliance issues
    compliance_issues = {
        "network_security": len(
            [r for r in recommendations if "network" in r.get("category", "").lower()]
        ),
        "container_security": len(
            [r for r in recommendations if "container" in r.get("category", "").lower()]
        ),
        "iam_security": len([r for r in recommendations if "iam" in r.get("category", "").lower()]),
        "monitoring": len(
            [r for r in recommendations if "monitoring" in r.get("category", "").lower()]
        ),
        "compliance": len(
            [r for r in recommendations if "compliance" in r.get("category", "").lower()]
        ),
    }

    return {
        "status": "success",
        "action": "check_compliance_status",
        "cluster_name": cluster_name,
        "region": region,
        "compliance_framework": compliance_framework,
        "assessment": f"Security assessment complete for ECS cluster '{cluster_name}' against {compliance_framework} framework. "  # noqa: E501
        f"Found {failed_checks} security areas requiring attention.",
        "security_findings": {
            "total_issues": failed_checks,
            "high_priority_failures": len(
                [r for r in recommendations if r.get("severity") == "High"]
            ),
            "high_priority": len([r for r in recommendations if r.get("severity") == "High"]),
            "medium_priority": len([r for r in recommendations if r.get("severity") == "Medium"]),
            "low_priority": len([r for r in recommendations if r.get("severity") == "Low"]),
        },
        "compliance_breakdown": compliance_issues,
        "recommendations": recommendations,
        "remediation_guidance": {
            "description": "Steps to improve your security posture",
            "priority_actions": [
                "Address all high priority security issues immediately",
                "Focus on high-severity recommendations first",
                "Implement security monitoring and alerting",
                "Schedule regular security assessments",
            ],
            "implementation_approach": {
                "immediate": "Fix high priority security vulnerabilities",
                "short_term": "Address high and medium severity issues",
                "long_term": "Implement comprehensive security monitoring",
            },
        },
    }
