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
Utility functions for ECS troubleshooting tools.

This module provides common utility functions used across ECS troubleshooting tools.
"""

import logging
from typing import Any, Dict, List, Optional

from botocore.client import BaseClient
from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.arn_parser import parse_arn
from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)

# Export these functions for use in other modules
__all__ = [
    "find_clusters",
    "find_services",
    "find_load_balancers",
    "find_task_definitions",
    "get_cloudformation_stack_if_exists",
]


async def find_clusters() -> List[str]:
    """
    Find ECS clusters.

    Returns
    -------
    List[str]
        List of cluster names.

    Raises
    ------
    Exception
        If there's an error communicating with AWS ECS service.
    """
    clusters: List[str] = []
    ecs_client = await get_aws_client("ecs")

    try:
        paginator = ecs_client.get_paginator("list_clusters")
        # boto3 paginator used as async iterator, type mismatch expected
        async for page in paginator.paginate():  # type: ignore
            if "clusterArns" not in page:
                continue

            for cluster_arn in page["clusterArns"]:
                parsed_arn = parse_arn(cluster_arn)
                if not parsed_arn:
                    continue

                cluster_name = parsed_arn.resource_name
                clusters.append(cluster_name)

        return clusters

    except ClientError as e:
        logger.warning(f"AWS client error finding clusters: {e}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error finding clusters: {e}")
        return []


async def find_services(cluster_name: str) -> List[str]:
    """
    Find ECS services in a specific cluster.

    Parameters
    ----------
    cluster_name : str
        Name of the cluster to find services in.

    Returns
    -------
    List[str]
        List of service names in the cluster.

    Raises
    ------
    Exception
        If there's an error communicating with AWS ECS service.
    """
    services: List[str] = []
    ecs_client = await get_aws_client("ecs")

    try:
        paginator = ecs_client.get_paginator("list_services")
        # boto3 paginator used as async iterator, type mismatch expected
        async for page in paginator.paginate(cluster=cluster_name):  # type: ignore
            if "serviceArns" not in page:
                continue

            for service_arn in page["serviceArns"]:
                parsed_arn = parse_arn(service_arn)
                if not parsed_arn:
                    continue

                service_name = parsed_arn.resource_name
                services.append(service_name)

        return services

    except ClientError as e:
        logger.warning(f"AWS client error listing services for cluster '{cluster_name}': {e}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error listing services for cluster '{cluster_name}': {e}")
        return []


async def find_load_balancers(cluster_name: str, service_name: str) -> List[Dict[str, Any]]:
    """
    Find load balancers associated with an ECS service.

    Parameters
    ----------
    cluster_name : str
        Name of the ECS cluster.
    service_name : str
        Name of the ECS service.

    Returns
    -------
    List[Dict[str, Any]]
        List of load balancer details.

    Raises
    ------
    Exception
        If there's an error communicating with AWS ECS or ELBv2 services.
    """
    ecs_client = await get_aws_client("ecs")
    elbv2_client = await get_aws_client("elbv2")

    load_balancers: List[Dict[str, Any]] = []

    try:
        # Get service details to find associated load balancers
        service_response = ecs_client.describe_services(
            cluster=cluster_name, services=[service_name]
        )

        if not service_response.get("services"):
            logger.warning(f"Service '{service_name}' not found in cluster '{cluster_name}'")
            return []

        service = service_response["services"][0]

        # Extract load balancer details from service
        service_load_balancers = service.get("loadBalancers", [])
        if not service_load_balancers:
            return []

        # Get target group ARNs from the service
        target_group_arns = [
            lb.get("targetGroupArn") for lb in service_load_balancers if "targetGroupArn" in lb
        ]

        if not target_group_arns:
            return []

        # Get load balancers associated with these target groups
        for target_group_arn in target_group_arns:
            # Get target group details
            target_group_response = elbv2_client.describe_target_groups(
                TargetGroupArns=[target_group_arn]
            )

            if not target_group_response.get("TargetGroups"):
                continue

            target_group = target_group_response["TargetGroups"][0]

            # Get associated load balancer ARNs
            lb_arns = target_group.get("LoadBalancerArns", [])

            if not lb_arns:
                continue

            # Get load balancer details
            lb_response = elbv2_client.describe_load_balancers(LoadBalancerArns=lb_arns)

            for lb in lb_response.get("LoadBalancers", []):
                load_balancers.append(lb)

        return load_balancers

    except ClientError as e:
        logger.warning(
            f"AWS client error finding load balancers for service '{service_name}' "
            f"in cluster '{cluster_name}': {e}"
        )
        return []
    except Exception as e:
        logger.warning(
            f"Unexpected error finding load balancers for service '{service_name}' "
            f"in cluster '{cluster_name}': {e}"
        )
        return []


async def find_task_definitions(
    cluster_name: Optional[str] = None,
    service_name: Optional[str] = None,
    stack_name: Optional[str] = None,
    family_prefix: Optional[str] = None,
    task_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find task definitions with flexible filtering options.

    This method allows you to find task definitions using multiple modes:
    1. By cluster and service name - gets the task definition actually in use
    2. By task ID - gets the task definition used by a specific task
    3. By stack name - finds task definitions related to a CloudFormation stack
    4. By family prefix - finds task definitions with matching family names

    At least one of cluster_name+service_name, task_id+cluster_name,
    stack_name, or family_prefix must be provided.

    Parameters
    ----------
    cluster_name : str, optional
        Name of the ECS cluster. Required if service_name or task_id is provided.
    service_name : str, optional
        Name of the ECS service. Requires cluster_name.
    stack_name : str, optional
        Name of the CloudFormation stack to find related task definitions.
    family_prefix : str, optional
        Prefix to filter task definition families (e.g., "my-app").
    task_id : str, optional
        ID of a task to get its task definition. Requires cluster_name.

    Returns
    -------
    List[Dict[str, Any]]
        List of task definition dictionaries with full details.

    Raises
    ------
    Exception
        If there's an error communicating with AWS services.
    """
    ecs_client = await get_aws_client("ecs")

    if not any(
        [(cluster_name and service_name), (cluster_name and task_id), stack_name, family_prefix]
    ):
        logger.warning(
            "At least one of: cluster_name+service_name, cluster_name+task_id, "
            "stack_name, or family_prefix must be provided"
        )
        return []

    try:
        if cluster_name and service_name:
            return await _get_task_definition_by_service(cluster_name, service_name, ecs_client)

        if cluster_name and task_id:
            return await _get_task_definition_by_task(task_id, cluster_name, ecs_client)

        if stack_name:
            return await _get_task_definitions_by_stack(stack_name, ecs_client)

        if family_prefix:
            return await _get_task_definitions_by_family_prefix(family_prefix, ecs_client)

    except ClientError as e:
        logger.warning(f"AWS client error in find_task_definitions: {e}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error in find_task_definitions: {e}")
        return []

    return []


async def get_cloudformation_stack_if_exists(resource_arn: str) -> Optional[Dict[str, Any]]:
    """
    Check if a resource is part of a CloudFormation stack and return stack details.

    Parameters
    ----------
    resource_arn : str
        ARN of the resource to check.

    Returns
    -------
    Optional[Dict[str, Any]]
        CloudFormation stack information if found, None otherwise.
        Contains keys: stack_name, stack_id, stack_status, creation_time,
        last_updated_time, and optionally error.

    Raises
    ------
    Exception
        If there's an error communicating with AWS services.
    """
    ecs_client = await get_aws_client("ecs")

    try:
        # Get resource tags
        tags_response = ecs_client.list_tags_for_resource(resourceArn=resource_arn)
        tags = tags_response.get("tags", [])

        # Look for CloudFormation tags
        stack_name = None
        stack_id = None

        for tag in tags:
            if tag.get("key") == "aws:cloudformation:stack-name":
                stack_name = tag.get("value")
            elif tag.get("key") == "aws:cloudformation:stack-id":
                stack_id = tag.get("value")

        if stack_name:
            # Get stack status
            cfn_client = await get_aws_client("cloudformation")
            try:
                stack_response = cfn_client.describe_stacks(StackName=stack_name)
                if stack_response.get("Stacks"):
                    stack = stack_response["Stacks"][0]
                    return {
                        "stack_name": stack_name,
                        "stack_id": stack_id,
                        "stack_status": stack.get("StackStatus"),
                        "creation_time": stack.get("CreationTime"),
                        "last_updated_time": stack.get("LastUpdatedTime"),
                    }
            except ClientError as e:
                logger.warning(f"AWS client error getting CloudFormation stack details: {e}")
                return {
                    "stack_name": stack_name,
                    "stack_id": stack_id,
                    "stack_status": "UNKNOWN",
                    "error": str(e),
                }

    except ClientError as e:
        logger.warning(f"AWS client error detecting CloudFormation stack for '{resource_arn}': {e}")
    except Exception as e:
        logger.warning(f"Unexpected error detecting CloudFormation stack for '{resource_arn}': {e}")

    return None


async def _get_task_definition_by_service(
    cluster_name: str, service_name: str, ecs_client: BaseClient
) -> List[Dict[str, Any]]:
    """
    Get task definition for a specific ECS service.

    Parameters
    ----------
    cluster_name : str
        Name of the ECS cluster.
    service_name : str
        Name of the ECS service.
    ecs_client : BaseClient
        Boto3 ECS client instance.

    Returns
    -------
    List[Dict[str, Any]]
        List containing the task definition dictionary if found.

    Raises
    ------
    Exception
        If there's an error communicating with AWS ECS service.
    """
    task_definitions: List[Dict[str, Any]] = []

    try:
        service_response = ecs_client.describe_services(
            cluster=cluster_name, services=[service_name]
        )

        if service_response.get("services"):
            service = service_response["services"][0]
            task_def_arn = service.get("taskDefinition")

            if task_def_arn:
                task_def_response = ecs_client.describe_task_definition(taskDefinition=task_def_arn)

                if "taskDefinition" in task_def_response:
                    task_definitions.append(task_def_response["taskDefinition"])

    except ClientError as e:
        logger.warning(f"AWS client error getting task definition by service: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error getting task definition by service: {e}")

    return task_definitions


async def _get_task_definition_by_task(
    task_id: str, cluster_name: str, ecs_client: BaseClient
) -> List[Dict[str, Any]]:
    """
    Get task definition for a specific ECS task.

    Parameters
    ----------
    task_id : str
        ID of the ECS task.
    cluster_name : str
        Name of the ECS cluster.
    ecs_client : BaseClient
        Boto3 ECS client instance.

    Returns
    -------
    List[Dict[str, Any]]
        List containing the task definition dictionary if found.

    Raises
    ------
    Exception
        If there's an error communicating with AWS ECS service.
    """
    task_definitions: List[Dict[str, Any]] = []

    try:
        task_response = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_id])

        if task_response.get("tasks"):
            task = task_response["tasks"][0]
            task_def_arn = task.get("taskDefinitionArn")

            if task_def_arn:
                task_def_response = ecs_client.describe_task_definition(taskDefinition=task_def_arn)

                if "taskDefinition" in task_def_response:
                    task_definitions.append(task_def_response["taskDefinition"])

    except ClientError as e:
        logger.warning(f"AWS client error getting task definition by task: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error getting task definition by task: {e}")

    return task_definitions


async def _get_task_definitions_by_stack(
    stack_name: str, ecs_client: BaseClient
) -> List[Dict[str, Any]]:
    """
    Get task definitions associated with a CloudFormation stack.

    Parameters
    ----------
    stack_name : str
        Name of the CloudFormation stack.
    ecs_client : BaseClient
        Boto3 ECS client instance.

    Returns
    -------
    List[Dict[str, Any]]
        List of task definition dictionaries found in the stack.

    Raises
    ------
    Exception
        If there's an error communicating with AWS services.
    """
    task_definitions: List[Dict[str, Any]] = []

    try:
        cfn_client = await get_aws_client("cloudformation")
        resources_response = cfn_client.list_stack_resources(StackName=stack_name)

        task_def_arns = []
        for resource in resources_response.get("StackResourceSummaries", []):
            if resource.get("ResourceType") == "AWS::ECS::TaskDefinition":
                task_def_arns.append(resource.get("PhysicalResourceId"))

        for task_def_arn in task_def_arns:
            if task_def_arn:
                task_def_response = ecs_client.describe_task_definition(taskDefinition=task_def_arn)

                if "taskDefinition" in task_def_response:
                    task_definitions.append(task_def_response["taskDefinition"])

    except ClientError as e:
        logger.warning(f"AWS client error getting task definitions by stack: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error getting task definitions by stack: {e}")

    return task_definitions


async def _get_task_definitions_by_family_prefix(
    family_prefix: str, ecs_client: BaseClient
) -> List[Dict[str, Any]]:
    """
    Get task definitions by family prefix.

    Parameters
    ----------
    family_prefix : str
        Prefix to filter task definition families.
    ecs_client : BaseClient
        Boto3 ECS client instance.

    Returns
    -------
    List[Dict[str, Any]]
        List of task definition dictionaries matching the family prefix.

    Raises
    ------
    Exception
        If there's an error communicating with AWS ECS service.
    """
    task_definitions: List[Dict[str, Any]] = []

    try:
        families_response = ecs_client.list_task_definition_families(
            familyPrefix=family_prefix, status="ACTIVE"
        )

        families = families_response.get("families", [])

        for family in families:
            task_defs_response = ecs_client.list_task_definitions(
                familyPrefix=family, status="ACTIVE", sort="DESC", maxResults=1
            )

            if task_defs_response.get("taskDefinitionArns"):
                task_def_arn = task_defs_response["taskDefinitionArns"][0]

                task_def_response = ecs_client.describe_task_definition(taskDefinition=task_def_arn)

                if "taskDefinition" in task_def_response:
                    task_definitions.append(task_def_response["taskDefinition"])

    except ClientError as e:
        logger.warning(f"AWS client error getting task definitions by family prefix: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error getting task definitions by family prefix: {e}")

    return task_definitions
