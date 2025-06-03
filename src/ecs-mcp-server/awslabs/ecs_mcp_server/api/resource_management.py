# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""
API for ECS resource management operations.

This module provides functions for listing and describing ECS resources
using a consistent interface.
"""

import logging
from typing import Any, Dict, Optional

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


async def ecs_resource_management(
    action: str,
    resource_type: str,
    identifier: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for ECS resource management operations.

    Args:
        action: Action to perform ("list" or "describe")
        resource_type: Type of ECS resource
        identifier: Resource identifier (name or ARN) for "describe" actions
        filters: Filters for list operations

    Returns:
        Dictionary containing the requested resource information
    """
    # Normalize inputs
    action = action.lower() if action else ""
    resource_type = resource_type.lower() if resource_type else ""
    filters = filters or {}

    logger.info(f"ECS resource management: {action} {resource_type} {identifier} {filters}")

    # Validate action
    if action not in ["list", "describe"]:
        raise ValueError(f"Unsupported action: {action}. Must be 'list' or 'describe'")

    # Route to the appropriate handler based on action and resource_type
    if resource_type == "cluster":
        if action == "list":
            return await list_clusters(filters)
        elif action == "describe":
            if not identifier:
                raise ValueError("Identifier is required for describe_cluster")
            return await describe_cluster(identifier, filters)

    elif resource_type == "service":
        if action == "list":
            return await list_services(filters)
        elif action == "describe":
            if not identifier:
                raise ValueError("Identifier is required for describe_service")
            if "cluster" not in filters:
                raise ValueError("Cluster filter is required for describe_service")
            return await describe_service(identifier, filters)

    elif resource_type == "task":
        if action == "list":
            return await list_tasks(filters)
        elif action == "describe":
            if not identifier:
                raise ValueError("Identifier is required for describe_task")
            if "cluster" not in filters:
                raise ValueError("Cluster filter is required for describe_task")
            return await describe_task(identifier, filters)

    elif resource_type == "task_definition":
        if action == "list":
            return await list_task_definitions(filters)
        elif action == "describe":
            if not identifier:
                raise ValueError("Identifier is required for describe_task_definition")
            return await describe_task_definition(identifier)

    elif resource_type == "container_instance":
        if action == "list":
            return await list_container_instances(filters)
        elif action == "describe":
            if not identifier:
                raise ValueError("Identifier is required for describe_container_instance")
            if "cluster" not in filters:
                raise ValueError("Cluster filter is required for describe_container_instance")
            return await describe_container_instance(identifier, filters)

    elif resource_type == "capacity_provider":
        if action == "list":
            return await list_capacity_providers(filters)
        elif action == "describe":
            if not identifier:
                raise ValueError("Identifier is required for describe_capacity_provider")
            return await describe_capacity_provider(identifier)

    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")

    # Default return if no specific handler was called
    return {
        "error": f"No handler found for action '{action}' on resource type '{resource_type}'",
        "status": "failed",
    }


# ============ CLUSTER OPERATIONS ============


async def list_clusters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lists all ECS clusters with optional filtering.

    Args:
        filters: Optional filters (not currently used for clusters)

    Returns:
        Dictionary containing ECS clusters
    """
    logger.info(f"Listing ECS clusters with filters: {filters}")

    try:
        ecs_client = await get_aws_client("ecs")
        response = ecs_client.list_clusters()
        cluster_arns = response.get("clusterArns", [])

        # If we have clusters, get more details
        clusters = []
        if cluster_arns:
            # Describe clusters in batches of 100 (API limit)
            for i in range(0, len(cluster_arns), 100):
                batch = cluster_arns[i : i + 100]
                cluster_details = ecs_client.describe_clusters(
                    clusters=batch, include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
                )
                clusters.extend(cluster_details.get("clusters", []))

        return {
            "clusters": clusters,
            "count": len(clusters),
        }
    except Exception as e:
        logger.error(f"Error listing ECS clusters: {e}")
        return {"error": str(e), "clusters": [], "count": 0}


async def describe_cluster(cluster: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gets detailed information about a specific ECS cluster.

    Args:
        cluster: Name or ARN of the cluster
        filters: Optional filters (not currently used for describe_cluster)

    Returns:
        Dictionary containing cluster details
    """
    logger.info(f"Describing ECS cluster: {cluster}")

    try:
        ecs_client = await get_aws_client("ecs")
        response = ecs_client.describe_clusters(
            clusters=[cluster], include=["ATTACHMENTS", "SETTINGS", "STATISTICS", "TAGS"]
        )

        if not response.get("clusters"):
            return {"error": f"Cluster {cluster} not found", "cluster": None}

        cluster_details = response["clusters"][0]

        # Get additional information for this cluster
        service_count = 0
        task_count = 0

        # Get service count
        services_response = ecs_client.list_services(cluster=cluster)
        service_count = len(services_response.get("serviceArns", []))

        # Get task count (both running and stopped)
        running_tasks_response = ecs_client.list_tasks(cluster=cluster, desiredStatus="RUNNING")
        stopped_tasks_response = ecs_client.list_tasks(cluster=cluster, desiredStatus="STOPPED")
        running_tasks = len(running_tasks_response.get("taskArns", []))
        stopped_tasks = len(stopped_tasks_response.get("taskArns", []))
        task_count = running_tasks + stopped_tasks

        return {
            "cluster": cluster_details,
            "service_count": service_count,
            "task_count": task_count,
            "running_task_count": len(running_tasks_response.get("taskArns", [])),
        }
    except Exception as e:
        logger.error(f"Error describing ECS cluster: {e}")
        return {"error": str(e), "cluster": None}


# ============ SERVICE OPERATIONS ============


async def list_services(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lists ECS services with optional filtering by cluster.

    Args:
        filters: Filters for services
            - cluster: Optional cluster name or ARN to filter by

    Returns:
        Dictionary containing ECS services
    """
    logger.info(f"Listing ECS services with filters: {filters}")

    try:
        ecs_client = await get_aws_client("ecs")
        cluster_name = filters.get("cluster")

        services = []

        # If no cluster specified, get all clusters first
        clusters = []
        if cluster_name:
            clusters = [cluster_name]
        else:
            clusters_response = ecs_client.list_clusters()
            clusters = clusters_response.get("clusterArns", [])

        for cluster in clusters:
            # Get services for this cluster
            service_arns = []
            paginator = ecs_client.get_paginator("list_services")

            # Use the paginator to get all services
            for page in paginator.paginate(cluster=cluster):
                service_arns.extend(page.get("serviceArns", []))

            # If we found services, describe them
            if service_arns:
                # Describe services in batches of 10 (API limit)
                for i in range(0, len(service_arns), 10):
                    batch = service_arns[i : i + 10]
                    service_details = ecs_client.describe_services(
                        cluster=cluster, services=batch, include=["TAGS"]
                    )
                    services.extend(service_details.get("services", []))

        return {
            "services": services,
            "count": len(services),
        }
    except Exception as e:
        logger.error(f"Error listing ECS services: {e}")
        return {"error": str(e), "services": [], "count": 0}


async def describe_service(service: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gets detailed information about a specific ECS service.

    Args:
        service: Name or ARN of the service
        filters: Filters for describing the service
            - cluster: Required cluster name or ARN

    Returns:
        Dictionary containing service details
    """
    logger.info(f"Describing ECS service: {service} in cluster: {filters.get('cluster')}")

    try:
        cluster = filters.get("cluster")
        ecs_client = await get_aws_client("ecs")

        response = ecs_client.describe_services(
            cluster=cluster, services=[service], include=["TAGS"]
        )

        if not response.get("services"):
            return {"error": f"Service {service} not found in cluster {cluster}", "service": None}

        service_details = response["services"][0]

        # Get task counts
        running_tasks = ecs_client.list_tasks(
            cluster=cluster, serviceName=service, desiredStatus="RUNNING"
        )

        stopped_tasks = ecs_client.list_tasks(
            cluster=cluster, serviceName=service, desiredStatus="STOPPED"
        )

        # Get deployment events
        events = service_details.get("events", [])
        recent_events = events[:10] if events else []  # Get the 10 most recent events

        return {
            "service": service_details,
            "running_task_count": len(running_tasks.get("taskArns", [])),
            "stopped_task_count": len(stopped_tasks.get("taskArns", [])),
            "recent_events": recent_events,
        }
    except Exception as e:
        logger.error(f"Error describing ECS service: {e}")
        return {"error": str(e), "service": None}


# ============ TASK OPERATIONS ============


async def list_tasks(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lists ECS tasks with optional filtering.

    Args:
        filters: Filters for tasks
            - cluster: Optional cluster name or ARN to filter by
            - service: Optional service name or ARN to filter by
            - status: Optional status to filter by (RUNNING, STOPPED)

    Returns:
        Dictionary containing ECS tasks
    """
    logger.info(f"Listing ECS tasks with filters: {filters}")

    try:
        ecs_client = await get_aws_client("ecs")
        cluster_name = filters.get("cluster")
        service_name = filters.get("service")
        status = filters.get("status", "").upper()  # Default to all

        tasks = []

        # If no cluster specified, get all clusters first
        clusters = []
        if cluster_name:
            clusters = [cluster_name]
        else:
            clusters_response = ecs_client.list_clusters()
            clusters = clusters_response.get("clusterArns", [])

        for cluster in clusters:
            params = {"cluster": cluster}
            if service_name:
                params["serviceName"] = service_name
            if status in ["RUNNING", "STOPPED"]:
                params["desiredStatus"] = status

            task_arns = []
            paginator = ecs_client.get_paginator("list_tasks")

            for page in paginator.paginate(**params):
                task_arns.extend(page.get("taskArns", []))

            if task_arns:
                # Describe tasks in batches of 100 (API limit)
                for i in range(0, len(task_arns), 100):
                    batch = task_arns[i : i + 100]
                    task_details = ecs_client.describe_tasks(
                        cluster=cluster, tasks=batch, include=["TAGS"]
                    )
                    tasks.extend(task_details.get("tasks", []))

        # Count by status
        running_count = sum(1 for task in tasks if task.get("lastStatus") == "RUNNING")
        stopped_count = sum(1 for task in tasks if task.get("lastStatus") == "STOPPED")
        failed_count = sum(
            1
            for task in tasks
            if task.get("lastStatus") == "STOPPED" and task.get("stopCode") != "TaskSucceeded"
        )

        return {
            "tasks": tasks,
            "count": len(tasks),
            "running_count": running_count,
            "stopped_count": stopped_count,
            "failed_count": failed_count,
        }
    except Exception as e:
        logger.error(f"Error listing ECS tasks: {e}")
        return {"error": str(e), "tasks": [], "count": 0}


async def describe_task(task: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gets detailed information about a specific ECS task.

    Args:
        task: Task ARN or ID
        filters: Filters for describing the task
            - cluster: Required cluster name or ARN

    Returns:
        Dictionary containing task details
    """
    logger.info(f"Describing ECS task: {task} in cluster: {filters.get('cluster')}")

    try:
        cluster = filters.get("cluster")
        ecs_client = await get_aws_client("ecs")

        response = ecs_client.describe_tasks(cluster=cluster, tasks=[task], include=["TAGS"])

        if not response.get("tasks"):
            return {"error": f"Task {task} not found in cluster {cluster}", "task": None}

        task_details = response["tasks"][0]

        # Get task definition details
        task_definition_arn = task_details.get("taskDefinitionArn")
        task_definition = None

        if task_definition_arn:
            td_response = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)
            task_definition = td_response.get("taskDefinition")

        # Calculate container statuses
        container_statuses = []
        for container in task_details.get("containers", []):
            container_status = {
                "name": container.get("name"),
                "image": container.get("image"),
                "status": container.get("lastStatus"),
                "exit_code": container.get("exitCode"),
                "reason": container.get("reason"),
                "health_status": container.get("healthStatus"),
            }
            container_statuses.append(container_status)

        return {
            "task": task_details,
            "task_definition": task_definition,
            "container_statuses": container_statuses,
            "is_failed": (
                task_details.get("lastStatus") == "STOPPED"
                and task_details.get("stopCode") != "TaskSucceeded"
            ),
            "stop_reason": task_details.get("stoppedReason"),
        }
    except Exception as e:
        logger.error(f"Error describing ECS task: {e}")
        return {"error": str(e), "task": None}


# ============ TASK DEFINITION OPERATIONS ============


async def list_task_definitions(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lists task definitions with optional filtering.

    Args:
        filters: Filters for task definitions
            - family: Optional family prefix to filter by
            - status: Optional status (ACTIVE or INACTIVE)
            - max_results: Optional maximum number of results

    Returns:
        Dictionary containing task definitions
    """
    logger.info(f"Listing task definitions with filters: {filters}")

    try:
        ecs_client = await get_aws_client("ecs")

        params = {}
        if "family" in filters:
            params["familyPrefix"] = filters["family"]
        if "status" in filters and filters["status"] in ["ACTIVE", "INACTIVE"]:
            params["status"] = filters["status"]
        else:
            params["status"] = "ACTIVE"  # Default to ACTIVE
        if "max_results" in filters and isinstance(filters["max_results"], int):
            params["maxResults"] = filters["max_results"]

        response = ecs_client.list_task_definitions(**params)
        task_definition_arns = response.get("taskDefinitionArns", [])

        # Optionally get details for each task definition
        task_definitions = []
        if "include_details" in filters and filters["include_details"]:
            for arn in task_definition_arns:
                td_response = ecs_client.describe_task_definition(taskDefinition=arn)
                task_definitions.append(td_response.get("taskDefinition"))

        return {
            "task_definition_arns": task_definition_arns,
            "task_definitions": task_definitions if task_definitions else None,
            "count": len(task_definition_arns),
            "next_token": response.get("nextToken"),
        }
    except Exception as e:
        logger.error(f"Error listing task definitions: {e}")
        return {"error": str(e), "task_definition_arns": [], "count": 0}


async def describe_task_definition(task_definition: str) -> Dict[str, Any]:
    """
    Gets detailed information about a specific task definition.

    Args:
        task_definition: Task definition family:revision or ARN

    Returns:
        Dictionary containing task definition details
    """
    logger.info(f"Describing task definition: {task_definition}")

    try:
        ecs_client = await get_aws_client("ecs")

        response = ecs_client.describe_task_definition(taskDefinition=task_definition)

        if not response.get("taskDefinition"):
            return {
                "error": f"Task definition {task_definition} not found",
                "task_definition": None,
            }

        task_def = response["taskDefinition"]

        # Get a count of services using this task definition
        # This is expensive, so make it optional in the future
        services_using = []

        # Check if this is the latest active revision
        family = task_def.get("family")
        is_latest = False

        if family:
            # List active task definitions for this family
            list_response = ecs_client.list_task_definitions(
                familyPrefix=family, status="ACTIVE", sort="DESC"
            )

            # If our task definition is the first one, it's the latest
            has_task_defs = list_response.get("taskDefinitionArns")
            is_first_task_def = has_task_defs and list_response["taskDefinitionArns"][
                0
            ] == task_def.get("taskDefinitionArn")
            if is_first_task_def:
                is_latest = True

        return {
            "task_definition": task_def,
            "services_using": services_using,
            "tags": response.get("tags", []),
            "is_latest": is_latest,
        }
    except Exception as e:
        logger.error(f"Error describing task definition: {e}")
        return {"error": str(e), "task_definition": None}


# ============ CONTAINER INSTANCE OPERATIONS ============


async def list_container_instances(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lists container instances with optional filtering.

    Args:
        filters: Filters for container instances
            - cluster: Required cluster name or ARN
            - status: Optional status filter (ACTIVE, DRAINING)

    Returns:
        Dictionary containing container instances
    """
    logger.info(f"Listing container instances with filters: {filters}")

    try:
        cluster = filters.get("cluster")
        if not cluster:
            return {
                "error": "Cluster is required for listing container instances",
                "container_instances": [],
                "count": 0,
            }

        ecs_client = await get_aws_client("ecs")

        params = {"cluster": cluster}
        if "status" in filters and filters["status"] in ["ACTIVE", "DRAINING"]:
            params["status"] = filters["status"]

        response = ecs_client.list_container_instances(**params)
        container_instance_arns = response.get("containerInstanceArns", [])

        # Get details for container instances
        container_instances = []
        if container_instance_arns:
            ci_details = ecs_client.describe_container_instances(
                cluster=cluster, containerInstances=container_instance_arns
            )
            container_instances = ci_details.get("containerInstances", [])

        return {
            "container_instances": container_instances,
            "count": len(container_instances),
            "next_token": response.get("nextToken"),
        }
    except Exception as e:
        logger.error(f"Error listing container instances: {e}")
        return {"error": str(e), "container_instances": [], "count": 0}


async def describe_container_instance(
    container_instance: str, filters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Gets detailed information about a specific container instance.

    Args:
        container_instance: Container instance ARN or ID
        filters: Filters for describing the container instance
            - cluster: Required cluster name or ARN

    Returns:
        Dictionary containing container instance details
    """
    cluster = filters.get("cluster")
    logger.info(f"Describing container instance: {container_instance} in cluster: {cluster}")

    try:
        cluster = filters.get("cluster")
        ecs_client = await get_aws_client("ecs")

        response = ecs_client.describe_container_instances(
            cluster=cluster, containerInstances=[container_instance]
        )

        if not response.get("containerInstances"):
            return {
                "error": f"Container instance {container_instance} not found in cluster {cluster}",
                "container_instance": None,
            }

        container_instance_details = response["containerInstances"][0]

        # Get EC2 instance details
        ec2_instance_id = container_instance_details.get("ec2InstanceId")
        ec2_details = None

        if ec2_instance_id:
            ec2_client = await get_aws_client("ec2")
            ec2_response = ec2_client.describe_instances(InstanceIds=[ec2_instance_id])

            if ec2_response.get("Reservations") and ec2_response["Reservations"]:
                ec2_details = ec2_response["Reservations"][0]["Instances"][0]

        # Get tasks running on this instance
        running_task_arns = ecs_client.list_tasks(
            cluster=cluster, containerInstance=container_instance, desiredStatus="RUNNING"
        ).get("taskArns", [])

        return {
            "container_instance": container_instance_details,
            "ec2_instance": ec2_details,
            "running_task_count": len(running_task_arns),
            "running_tasks": running_task_arns,
        }
    except Exception as e:
        logger.error(f"Error describing container instance: {e}")
        return {"error": str(e), "container_instance": None}


# ============ CAPACITY PROVIDER OPERATIONS ============


async def list_capacity_providers(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lists capacity providers.

    Args:
        filters: Filters for capacity providers (not currently used)

    Returns:
        Dictionary containing capacity providers
    """
    logger.info("Listing capacity providers")

    try:
        ecs_client = await get_aws_client("ecs")

        response = ecs_client.describe_capacity_providers()
        capacity_providers = response.get("capacityProviders", [])

        return {
            "capacity_providers": capacity_providers,
            "count": len(capacity_providers),
            "next_token": response.get("nextToken"),
        }
    except Exception as e:
        logger.error(f"Error listing capacity providers: {e}")
        return {"error": str(e), "capacity_providers": [], "count": 0}


async def describe_capacity_provider(capacity_provider: str) -> Dict[str, Any]:
    """
    Gets detailed information about a specific capacity provider.

    Args:
        capacity_provider: Capacity provider name or ARN

    Returns:
        Dictionary containing capacity provider details
    """
    logger.info(f"Describing capacity provider: {capacity_provider}")

    try:
        ecs_client = await get_aws_client("ecs")

        response = ecs_client.describe_capacity_providers(capacityProviders=[capacity_provider])

        if not response.get("capacityProviders"):
            return {
                "error": f"Capacity provider {capacity_provider} not found",
                "capacity_provider": None,
            }

        capacity_provider_details = response["capacityProviders"][0]

        # Get clusters using this capacity provider
        clusters_response = ecs_client.list_clusters()
        cluster_arns = clusters_response.get("clusterArns", [])

        clusters_using = []
        for cluster_arn in cluster_arns:
            cluster_details = ecs_client.describe_clusters(
                clusters=[cluster_arn], include=["ATTACHMENTS", "SETTINGS"]
            )

            if cluster_details.get("clusters"):
                cluster = cluster_details["clusters"][0]
                capacity_provider_strategy = cluster.get("capacityProviders", [])

                if capacity_provider in capacity_provider_strategy:
                    clusters_using.append(
                        {
                            "cluster_name": cluster.get("clusterName"),
                            "cluster_arn": cluster.get("clusterArn"),
                        }
                    )

        return {
            "capacity_provider": capacity_provider_details,
            "clusters_using": clusters_using,
            "clusters_using_count": len(clusters_using),
        }
    except Exception as e:
        logger.error(f"Error describing capacity provider: {e}")
        return {"error": str(e), "capacity_provider": None}
