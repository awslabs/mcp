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

This module provides functions for analyzing ECS cluster security configurations
and generating security recommendations.
"""

import logging
import os
from typing import Any, Dict

import boto3

from awslabs.ecs_mcp_server.api.resource_management import ecs_api_operation
from awslabs.ecs_mcp_server.utils.aws import get_aws_config

logger = logging.getLogger(__name__)


def get_target_region() -> str:
    """
    Get the target AWS region for security analysis from environment variable.

    Returns:
        AWS region name from AWS_REGION environment variable (defaults to 'us-east-1')
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    logger.info(f"Using region from environment: {region}")
    return region


async def get_clusters_with_metadata(region: str) -> list[Dict[str, Any]]:
    """
    Get all ECS clusters in the specified region with their metadata.

    Args:
        region: AWS region to get clusters from

    Returns:
        List of cluster dictionaries with metadata

    Raises:
        Exception: If retrieving clusters fails
    """
    logger.info(f"Listing ECS clusters in region: {region}")

    try:
        # List cluster ARNs
        list_response = await ecs_api_operation(api_operation="ListClusters", api_params={})

        cluster_arns = list_response.get("clusterArns", [])

        if not cluster_arns:
            logger.info(f"No clusters found in region {region}")
            return []

        logger.info(f"Found {len(cluster_arns)} cluster(s) in region {region}")

        # Describe clusters to get metadata
        describe_response = await ecs_api_operation(
            api_operation="DescribeClusters",
            api_params={
                "clusters": cluster_arns,
                "include": ["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"],
            },
        )

        clusters = describe_response.get("clusters", [])

        # Format cluster information
        all_clusters = []
        for cluster in clusters:
            cluster_info = {
                "cluster_name": cluster.get("clusterName"),
                "cluster_arn": cluster.get("clusterArn"),
                "status": cluster.get("status"),
                "running_tasks_count": cluster.get("runningTasksCount", 0),
                "pending_tasks_count": cluster.get("pendingTasksCount", 0),
                "active_services_count": cluster.get("activeServicesCount", 0),
                "registered_container_instances_count": cluster.get(
                    "registeredContainerInstancesCount", 0
                ),
                "tags": {tag["key"]: tag["value"] for tag in cluster.get("tags", [])},
            }
            all_clusters.append(cluster_info)

        logger.info(f"Successfully retrieved metadata for {len(all_clusters)} cluster(s)")
        return all_clusters

    except Exception as e:
        logger.error(f"Error retrieving clusters in region {region}: {e}")
        raise Exception(f"Failed to retrieve clusters in region '{region}': {str(e)}") from e


def format_clusters_for_display(clusters: list[Dict[str, Any]], region: str) -> str:
    """
    Format cluster data into a user-friendly display string.

    Args:
        clusters: List of cluster dictionaries
        region: AWS region name

    Returns:
        Formatted string with cluster information for display
    """
    if not clusters:
        return f"""
No ECS clusters found in region: {region}

To create a cluster, you can use the AWS CLI:
```bash
aws ecs create-cluster --cluster-name my-cluster --region {region}
```

Or use the AWS Console to create a cluster in the ECS service.
"""

    # Build the formatted output
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📋 ECS CLUSTERS IN REGION: {region}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"Found {len(clusters)} cluster(s):",
        "",
    ]

    for i, cluster in enumerate(clusters, 1):
        cluster_name = cluster.get("cluster_name", "Unknown")
        status = cluster.get("status", "Unknown")
        running_tasks = cluster.get("running_tasks_count", 0)
        active_services = cluster.get("active_services_count", 0)

        lines.extend(
            [
                f"{i}. {cluster_name}",
                f"   Status: {status}",
                f"   Running Tasks: {running_tasks}",
                f"   Active Services: {active_services}",
                "",
            ]
        )

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "To analyze a specific cluster, call this tool again with:",
            "  cluster_names=['cluster-name']",
            "",
            "Example:",
            f"  analyze_ecs_security("
            f"cluster_names=['{clusters[0].get('cluster_name')}'], "
            f"region='{region}')",
            "",
        ]
    )

    return "\n".join(lines)


class ClusterNotFoundError(Exception):
    """Raised when one or more clusters cannot be found."""

    pass


async def validate_clusters(cluster_names: list[str], region: str) -> list[str]:
    """
    Validate that the specified clusters exist and return their ARNs.

    Args:
        cluster_names: List of cluster names to validate
        region: AWS region to check clusters in

    Returns:
        List of validated cluster ARNs

    Raises:
        ClusterNotFoundError: If one or more clusters are not found
    """
    logger.info(f"Validating {len(cluster_names)} cluster(s) in region {region}")

    try:
        # Describe clusters to validate they exist
        describe_response = await ecs_api_operation(
            api_operation="DescribeClusters",
            api_params={"clusters": cluster_names, "include": ["TAGS"]},
        )

        found_clusters = describe_response.get("clusters", [])
        failures = describe_response.get("failures", [])

        if failures:
            failed_names = [f["arn"] for f in failures]
            raise ClusterNotFoundError(f"Clusters not found in region '{region}': {failed_names}")

        if len(found_clusters) != len(cluster_names):
            found_names = [c["clusterName"] for c in found_clusters]
            missing = set(cluster_names) - set(found_names)
            raise ClusterNotFoundError(f"Clusters not found in region '{region}': {list(missing)}")

        cluster_arns = [cluster["clusterArn"] for cluster in found_clusters]
        logger.info(f"Successfully validated {len(cluster_arns)} cluster(s)")
        return cluster_arns

    except ClusterNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error validating clusters: {e}")
        raise Exception(f"Failed to validate clusters: {str(e)}") from e


async def collect_cluster_configuration(region: str, cluster_name: str) -> Dict[str, Any]:
    """
    Collect comprehensive configuration for an ECS cluster.

    This function gathers all security-relevant configuration data for analysis:
    - Cluster metadata and settings
    - Service configurations
    - Task definition configurations
    - Security group configurations
    - IAM role references

    Args:
        region: AWS region containing the cluster
        cluster_name: Name of the cluster to analyze

    Returns:
        Dictionary containing complete cluster configuration

    Note:
        This function collects data but does not perform security analysis.
        The analysis is performed by AI agents using the collected data.
    """
    logger.info(f"Collecting configuration for cluster '{cluster_name}' in region {region}")

    cluster_config = {
        "cluster_name": cluster_name,
        "region": region,
        "cluster_metadata": {},
        "services": [],
        "task_definitions": [],
        "security_groups": [],
        "collection_errors": [],
    }

    try:
        # Step 1: Collect cluster metadata
        logger.info(f"Step 1: Collecting cluster metadata for '{cluster_name}'")
        describe_response = await ecs_api_operation(
            api_operation="DescribeClusters",
            api_params={
                "clusters": [cluster_name],
                "include": ["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"],
            },
        )

        clusters = describe_response.get("clusters", [])
        if not clusters:
            raise Exception(f"Cluster '{cluster_name}' not found")

        cluster = clusters[0]
        cluster_config["cluster_metadata"] = {
            "cluster_arn": cluster.get("clusterArn"),
            "cluster_name": cluster.get("clusterName"),
            "status": cluster.get("status"),
            "running_tasks_count": cluster.get("runningTasksCount", 0),
            "pending_tasks_count": cluster.get("pendingTasksCount", 0),
            "active_services_count": cluster.get("activeServicesCount", 0),
            "registered_container_instances_count": cluster.get(
                "registeredContainerInstancesCount", 0
            ),
            "statistics": cluster.get("statistics", []),
            "tags": {tag["key"]: tag["value"] for tag in cluster.get("tags", [])},
            "settings": cluster.get("settings", []),
            "configuration": cluster.get("configuration", {}),
            "service_connect_defaults": cluster.get("serviceConnectDefaults", {}),
            "attachments": cluster.get("attachments", []),
        }

        logger.info(f"Successfully collected cluster metadata for '{cluster_name}'")

    except Exception as e:
        error_msg = f"Failed to collect cluster metadata: {str(e)}"
        logger.warning(error_msg)
        cluster_config["collection_errors"].append(error_msg)

    # Step 2: Collect service configurations
    try:
        logger.info(f"Step 2: Collecting service configurations for cluster '{cluster_name}'")
        services_response = await ecs_api_operation(
            api_operation="ListServices", api_params={"cluster": cluster_name}
        )

        service_arns = services_response.get("serviceArns", [])
        logger.info(f"Found {len(service_arns)} service(s) in cluster '{cluster_name}'")

        if service_arns:
            # Process services in batches (DescribeServices has a limit)
            batch_size = 10
            services_list = []
            services_with_errors = []

            for i in range(0, len(service_arns), batch_size):
                batch_arns = service_arns[i : i + batch_size]
                try:
                    describe_services_response = await ecs_api_operation(
                        api_operation="DescribeServices",
                        api_params={"cluster": cluster_name, "services": batch_arns},
                    )

                    services = describe_services_response.get("services", [])

                    for service in services:
                        try:
                            service_name = service.get("serviceName")
                            service_status = service.get("status")

                            # Log warning for non-active services
                            if service_status not in ["ACTIVE", "DRAINING"]:
                                logger.warning(
                                    f"Service {service_name} is in {service_status} state"
                                )

                            # Collect security group information
                            security_group_details = []
                            network_config = service.get("networkConfiguration", {})
                            awsvpc_config = network_config.get("awsvpcConfiguration", {})
                            security_group_ids = awsvpc_config.get("securityGroups", [])

                            if security_group_ids:
                                try:
                                    # Describe security groups
                                    ec2_client = boto3.client(
                                        "ec2", region_name=region, config=get_aws_config()
                                    )
                                    sg_response = ec2_client.describe_security_groups(
                                        GroupIds=security_group_ids
                                    )
                                    security_group_details.extend(
                                        [
                                            {
                                                "group_id": sg["GroupId"],
                                                "group_name": sg.get("GroupName", ""),
                                                "description": sg.get("Description", ""),
                                                "vpc_id": sg.get("VpcId", ""),
                                                "ingress_rules": sg.get("IpPermissions", []),
                                                "egress_rules": sg.get("IpPermissionsEgress", []),
                                                "tags": {
                                                    tag["Key"]: tag["Value"]
                                                    for tag in sg.get("Tags", [])
                                                },
                                            }
                                            for sg in sg_response.get("SecurityGroups", [])
                                        ]
                                    )
                                    logger.info(
                                        f"Collected {len(security_group_details)} "
                                        f"security group(s) for service {service_name}"
                                    )
                                except Exception as e:
                                    error_msg = (
                                        f"Failed to describe security groups "
                                        f"{security_group_ids}: {str(e)}"
                                    )
                                    logger.error(f"Service {service_name}: {error_msg}")
                                    services_with_errors.append(
                                        {"service_name": service_name, "error": error_msg}
                                    )

                            # Build service configuration
                            service_config = {
                                "service_name": service_name,
                                "service_arn": service.get("serviceArn"),
                                "cluster_arn": service.get("clusterArn"),
                                "task_definition": service.get("taskDefinition"),
                                "desired_count": service.get("desiredCount", 0),
                                "running_count": service.get("runningCount", 0),
                                "pending_count": service.get("pendingCount", 0),
                                "status": service_status,
                                "launch_type": service.get("launchType"),
                                "capacity_provider_strategy": service.get(
                                    "capacityProviderStrategy", []
                                ),
                                "platform_version": service.get("platformVersion"),
                                "platform_family": service.get("platformFamily"),
                                "network_configuration": network_config,
                                "security_groups": security_group_details,
                                "load_balancers": service.get("loadBalancers", []),
                                "service_registries": service.get("serviceRegistries", []),
                                "tags": {
                                    tag["key"]: tag["value"] for tag in service.get("tags", [])
                                },
                                "enable_execute_command": service.get(
                                    "enableExecuteCommand", False
                                ),
                                "health_check_grace_period_seconds": service.get(
                                    "healthCheckGracePeriodSeconds"
                                ),
                                "scheduling_strategy": service.get("schedulingStrategy"),
                                "deployment_controller": service.get("deploymentController", {}),
                                "service_connect_configuration": service.get(
                                    "serviceConnectConfiguration", {}
                                ),
                            }
                            services_list.append(service_config)

                        except Exception as e:
                            logger.error(f"Failed to process service: {e}")
                            services_with_errors.append(
                                {
                                    "service_name": service.get("serviceName", "Unknown"),
                                    "error": str(e),
                                }
                            )

                except Exception as e:
                    logger.error(f"Failed to describe services batch: {e}")
                    for arn in batch_arns:
                        service_name = arn.split("/")[-1]
                        services_with_errors.append({"service_name": service_name, "error": str(e)})

            cluster_config["services"] = services_list
            if services_with_errors:
                cluster_config["collection_errors"].extend(
                    [f"Service {s['service_name']}: {s['error']}" for s in services_with_errors]
                )
                logger.warning(
                    f"{len(services_with_errors)} service(s) had errors during collection"
                )

    except Exception as e:
        error_msg = f"Failed to collect service configurations: {str(e)}"
        logger.warning(error_msg)
        cluster_config["collection_errors"].append(error_msg)

    # Step 3: Collect task definition configurations
    try:
        logger.info(
            f"Step 3: Collecting task definition configurations for cluster '{cluster_name}'"
        )

        # Get unique task definition ARNs from services
        task_def_arns = set()
        for service in cluster_config["services"]:
            task_def_arn = service.get("task_definition")
            if task_def_arn:
                task_def_arns.add(task_def_arn)

        logger.info(f"Found {len(task_def_arns)} unique task definition(s) to describe")

        task_definitions_list = []
        for task_def_arn in task_def_arns:
            try:
                # Describe individual task definition
                task_def_response = await ecs_api_operation(
                    api_operation="DescribeTaskDefinition",
                    api_params={"taskDefinition": task_def_arn, "include": ["TAGS"]},
                )

                task_def = task_def_response.get("taskDefinition", {})
                task_def_config = {
                    "family": task_def.get("family"),
                    "task_definition_arn": task_def.get("taskDefinitionArn"),
                    "revision": task_def.get("revision"),
                    "status": task_def.get("status"),
                    "requires_compatibilities": task_def.get("requiresCompatibilities", []),
                    "network_mode": task_def.get("networkMode"),
                    "cpu": task_def.get("cpu"),
                    "memory": task_def.get("memory"),
                    "task_role_arn": task_def.get("taskRoleArn"),
                    "execution_role_arn": task_def.get("executionRoleArn"),
                    "container_definitions": task_def.get("containerDefinitions", []),
                    "volumes": task_def.get("volumes", []),
                    "placement_constraints": task_def.get("placementConstraints", []),
                    "requires_attributes": task_def.get("requiresAttributes", []),
                    "pid_mode": task_def.get("pidMode"),
                    "ipc_mode": task_def.get("ipcMode"),
                    "proxy_configuration": task_def.get("proxyConfiguration", {}),
                    "inference_accelerators": task_def.get("inferenceAccelerators", []),
                    "ephemeral_storage": task_def.get("ephemeralStorage", {}),
                    "runtime_platform": task_def.get("runtimePlatform", {}),
                    "tags": {tag["key"]: tag["value"] for tag in task_def_response.get("tags", [])},
                }
                task_definitions_list.append(task_def_config)

            except Exception as e:
                logger.warning(f"Failed to describe task definition '{task_def_arn}': {e}")
                cluster_config["collection_errors"].append(
                    f"Task definition {task_def_arn}: {str(e)}"
                )

        cluster_config["task_definitions"] = task_definitions_list
        logger.info(
            f"Successfully collected {len(task_definitions_list)} task definition configuration(s)"
        )

    except Exception as e:
        error_msg = f"Failed to collect task definition configurations: {str(e)}"
        logger.warning(error_msg)
        cluster_config["collection_errors"].append(error_msg)

    # Step 4: Collect unique security groups (deduplicated from services)
    try:
        logger.info("Step 4: Deduplicating security group configurations")
        unique_security_groups = {}

        for service in cluster_config["services"]:
            for sg in service.get("security_groups", []):
                sg_id = sg.get("group_id")
                if sg_id and sg_id not in unique_security_groups:
                    unique_security_groups[sg_id] = sg

        cluster_config["security_groups"] = list(unique_security_groups.values())
        logger.info(f"Found {len(unique_security_groups)} unique security group(s)")

    except Exception as e:
        error_msg = f"Failed to process security groups: {str(e)}"
        logger.warning(error_msg)
        cluster_config["collection_errors"].append(error_msg)

    # Log collection summary
    logger.info(
        f"Configuration collection complete for '{cluster_name}': "
        f"{len(cluster_config['services'])} services, "
        f"{len(cluster_config['task_definitions'])} task definitions, "
        f"{len(cluster_config['security_groups'])} security groups"
    )

    if cluster_config["collection_errors"]:
        logger.warning(
            f"Collection completed with {len(cluster_config['collection_errors'])} error(s)"
        )

    return cluster_config
