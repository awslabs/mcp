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

import logging
import re
from typing import Any, Dict, List, Optional

# Literal type not used in PR1, will be added in PR2 when needed
from .resource_management import ecs_api_operation
from .troubleshooting_tools.fetch_network_configuration import fetch_network_configuration
from .troubleshooting_tools.utils import find_clusters, find_task_definitions

logger = logging.getLogger(__name__)


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
                "capacity_providers": capacity_providers_response.get("capacityProviders", [])
                if "error" not in capacity_providers_response
                else [],
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
                # Use direct ECS API call to list services
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

                    # Get task definition using existing utility
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
                        "tags": service_tags_response.get("tags", [])
                        if "error" not in service_tags_response
                        else [],
                        "running_tasks": tasks_response.get("taskArns", [])
                        if "error" not in tasks_response
                        else [],
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
        self.data_adapter = DataAdapter()

        # Security validation patterns
        self._security_patterns = {
            "docker_hub_official": re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$"),
            "docker_hub_user": re.compile(
                r"^[a-z0-9]+(?:[._-][a-z0-9]+)*/[a-z0-9]+(?:[._-][a-z0-9]+)*$"
            ),
            "ecr_public": re.compile(
                r"^public\.ecr\.aws/[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._/-]*$"
            ),
            "ecr_private": re.compile(
                r"^[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/[a-z0-9][a-z0-9._/-]*$"
            ),
            "sensitive_keys": re.compile(
                r"(?i)(password|secret|key|token|credential)", re.IGNORECASE
            ),
            "structured_data": re.compile(r'[{}\[\]":]'),
        }

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

    def _format_resource_name(self, resource_type: str, resource_name: str) -> str:
        """Format resource name for consistent reporting."""
        return f"{resource_type}: {resource_name}"

    def _format_resource_name(self, resource_type: str, resource_name: str) -> str:
        """Format resource name for consistent reporting."""
        return f"{resource_type}: {resource_name}"

    # Placeholder methods for security analysis - will be implemented in PR2
    def _analyze_cluster_security(self, *args, **kwargs):
        """Placeholder for cluster security analysis - implemented in PR2."""
        pass

    def _analyze_service_security(self, *args, **kwargs):
        """Placeholder for service security analysis - implemented in PR2."""
        pass

    def _analyze_task_definition_security(self, *args, **kwargs):
        """Placeholder for task definition security analysis - implemented in PR2."""
        pass

    def _analyze_container_security(self, *args, **kwargs):
        """Placeholder for container security analysis - implemented in PR2."""
        pass

    def _analyze_network_security(self, *args, **kwargs):
        """Placeholder for network security analysis - implemented in PR2."""
        pass

    def _analyze_capacity_providers(self, *args, **kwargs):
        """Placeholder for capacity provider analysis - implemented in PR2."""
        pass

    def _analyze_iam_security(self, *args, **kwargs):
        """Placeholder for IAM security analysis - implemented in PR2."""
        pass

    def _analyze_logging_security(self, *args, **kwargs):
        """Placeholder for logging security analysis - implemented in PR2."""
        pass

    def _analyze_secrets_security(self, *args, **kwargs):
        """Placeholder for secrets security analysis - implemented in PR2."""
        pass

    def _analyze_compliance_security(self, *args, **kwargs):
        """Placeholder for compliance security analysis - implemented in PR2."""
        pass
