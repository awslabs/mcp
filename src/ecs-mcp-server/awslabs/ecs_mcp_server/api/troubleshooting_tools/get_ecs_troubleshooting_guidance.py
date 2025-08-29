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
Initial entry point for ECS troubleshooting guidance.

This module provides a function to analyze symptoms and recommend specific diagnostic paths
for troubleshooting ECS deployments.
"""

import inspect
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.api.troubleshooting_tools.utils import (
    find_load_balancers,
    find_services,
    find_task_definitions,
    get_cloudformation_stack_if_exists,
)
from awslabs.ecs_mcp_server.utils.arn_parser import parse_arn
from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)

# Export these functions for testing purposes
__all__ = [
    "get_ecs_troubleshooting_guidance",
    "validate_container_images",
    "collect_cluster_details",
    "collect_service_details",
    "collect_task_details",
    "generate_assessment",
]


async def handle_aws_api_call(func, error_value=None, *args, **kwargs):
    """Execute AWS API calls with standardized error handling."""
    try:
        result = func(*args, **kwargs)
        if inspect.iscoroutine(result):
            result = await result
        return result
    except ClientError as e:
        logger.warning(
            f"API error in {func.__name__ if hasattr(func, '__name__') else 'unknown'}: {e}"
        )
        return error_value
    except Exception as e:
        logger.exception(
            f"Unexpected error in {func.__name__ if hasattr(func, '__name__') else 'unknown'}: {e}"
        )
        return error_value


def is_ecr_image(image_uri: str) -> bool:
    """Determine if an image is from ECR."""
    import re

    try:
        if not (image_uri.startswith("http://") or image_uri.startswith("https://")):
            parse_uri = urlparse(f"https://{image_uri}")
        else:
            parse_uri = urlparse(image_uri)

        hostname = parse_uri.netloc.lower()

        # Check for malformed hostnames (double dots, etc.)
        if ".." in hostname or hostname.startswith(".") or hostname.endswith("."):
            return False

        # Ensure the hostname ends with amazonaws.com (proper domain validation)
        if not hostname.endswith(".amazonaws.com"):
            return False

        # Check for proper ECR hostname structure: account-id.dkr.ecr.region.amazonaws.com
        ecr_pattern = r"^\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com$"

        return bool(re.match(ecr_pattern, hostname))

    except Exception:
        return False


def parse_ecr_image_uri(image_uri: str) -> Tuple[str, str]:
    """Parse an ECR image URI into repository name and tag."""
    try:
        # Parse repository name and tag
        if ":" in image_uri:
            repo_uri, tag = image_uri.split(":", 1)
        else:
            repo_uri, tag = image_uri, "latest"

        # Extract repository name from URI
        if repo_uri.startswith("arn:"):
            parsed_arn = parse_arn(repo_uri)
            if parsed_arn:
                repo_name = parsed_arn.resource_name
            else:
                repo_name = repo_uri.split("/")[-1]
        else:
            repo_name = repo_uri.split("/")[-1]

        return repo_name, tag
    except Exception as e:
        logger.error(f"Failed to parse ECR image URI {image_uri}: {e}")
        return "", ""


async def validate_image(image_uri: str) -> Dict[str, Any]:
    """
    Validate if a container image exists and is accessible.

    A unified function that handles both ECR and external images.

    Parameters
    ----------
    image_uri : str
        The container image URI to validate

    Returns
    -------
    Dict[str, Any]
        Dictionary with validation results
    """
    # Initialize result structure
    result = {"image": image_uri, "exists": "false", "error": None}

    # Determine image type
    if is_ecr_image(image_uri):
        # ECR image logic
        result["repository_type"] = "ecr"
        ecr_client = await get_aws_client("ecr")

        # Parse repository name and tag
        repo_name, tag = parse_ecr_image_uri(image_uri)
        if not repo_name:
            result["error"] = "Failed to parse ECR image URI"
            return result

        # Check if repository exists
        try:
            # Just check if the repository exists
            ecr_client.describe_repositories(repositoryNames=[repo_name])

            # Check if image with tag exists
            try:
                # Just check if the image exists
                ecr_client.describe_images(repositoryName=repo_name, imageIds=[{"imageTag": tag}])
                result["exists"] = "true"
            except ClientError as e:
                if e.response["Error"]["Code"] == "ImageNotFoundException":
                    result["error"] = f"Image with tag {tag} not found in repository {repo_name}"
                else:
                    result["error"] = str(e)
        except ClientError as e:
            if e.response["Error"]["Code"] == "RepositoryNotFoundException":
                result["error"] = f"Repository {repo_name} not found"
            else:
                result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)
    else:
        # External image logic (Docker Hub, etc.)
        result["repository_type"] = "external"
        result["exists"] = "unknown"  # We can't easily check these

    return result


async def validate_container_images(task_definitions: List[Dict]) -> List[Dict]:
    """Validate container images in task definitions."""
    results = []

    for task_def in task_definitions:
        for container in task_def.get("containerDefinitions", []):
            image = container.get("image", "")

            # Use the unified validate_image function
            result = await validate_image(image)

            # Add task and container context
            result.update(
                {
                    "task_definition": task_def.get("taskDefinitionArn", ""),
                    "container_name": container.get("name", ""),
                }
            )

            results.append(result)

    return results


def _format_service_info(service: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format service information into standardized dictionary structure.

    Parameters
    ----------
    service : Dict[str, Any]
        Raw service dictionary from ECS describe_services response

    Returns
    -------
    Dict[str, Any]
        Formatted service information dictionary
    """
    return {
        "name": service["serviceName"],
        "arn": service.get("serviceArn"),
        "status": service["status"],
        "taskDefinition": service.get("taskDefinition"),
        "desiredCount": service.get("desiredCount", 0),
        "runningCount": service.get("runningCount", 0),
        "pendingCount": service.get("pendingCount", 0),
        "platformVersion": service.get("platformVersion"),
        "launchType": service.get("launchType"),
    }


async def collect_cluster_details(
    cluster_name: str, ecs_client
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Collect ECS cluster details and return cluster information with ARN.

    Parameters
    ----------
    cluster_name : str
        The name of the ECS cluster to describe
    ecs_client : BaseClient
        Boto3 ECS client instance

    Returns
    -------
    Tuple[List[Dict[str, Any]], Optional[str]]
        Tuple containing (cluster_details_list, cluster_arn)
    """
    try:
        clusters_response = ecs_client.describe_clusters(clusters=[cluster_name])
        cluster_details = []
        cluster_arn = None

        if "clusters" in clusters_response and clusters_response["clusters"]:
            for cluster in clusters_response["clusters"]:
                cluster_arn = cluster.get("clusterArn")
                cluster_info = {
                    "name": cluster["clusterName"],
                    "arn": cluster_arn,
                    "status": cluster["status"],
                    "runningTasksCount": cluster.get("runningTasksCount", 0),
                    "pendingTasksCount": cluster.get("pendingTasksCount", 0),
                    "activeServicesCount": cluster.get("activeServicesCount", 0),
                    "registeredContainerInstancesCount": cluster.get(
                        "registeredContainerInstancesCount", 0
                    ),
                }
                cluster_details.append(cluster_info)

        return cluster_details, cluster_arn

    except Exception as e:
        logger.warning(f"Error collecting cluster details for {cluster_name}: {e}")
        return [], None


async def collect_service_details(
    cluster_name: str, service_name: Optional[str], ecs_client
) -> List[Dict[str, Any]]:
    """
    Collect ECS service details for specific service or all services in cluster.

    Parameters
    ----------
    cluster_name : str
        The name of the ECS cluster
    service_name : Optional[str]
        The name of specific service, or None for cluster-wide discovery
    ecs_client : BaseClient
        Boto3 ECS client instance

    Returns
    -------
    List[Dict[str, Any]]
        List of service details dictionaries
    """
    try:
        if service_name:
            # Get specific service details
            service_response = ecs_client.describe_services(
                cluster=cluster_name, services=[service_name]
            )
            services = service_response.get("services", [])
        else:
            # Cluster-wide discovery using existing utils function
            service_names = await find_services(cluster_name=cluster_name)
            service_names = service_names[:50]  # Limit to 50 services

            if service_names:
                services_response = ecs_client.describe_services(
                    cluster=cluster_name, services=service_names
                )
                services = services_response.get("services", [])
            else:
                services = []

        # Format all services using the helper function
        return [_format_service_info(service) for service in services]

    except Exception as e:
        logger.warning(f"Error collecting service details for cluster {cluster_name}: {e}")
        return []


async def collect_task_details(
    cluster_name: str, service_name: Optional[str]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Collect task-related details including task definitions, load balancers, and image validation.

    Parameters
    ----------
    cluster_name : str
        The name of the ECS cluster
    service_name : Optional[str]
        The name of specific service, if applicable

    Returns
    -------
    Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]
        Tuple containing (task_definitions, load_balancers, image_check_results)
    """
    task_definitions = []
    load_balancers = []
    image_check_results = []

    try:
        if service_name:
            # Get task definitions and load balancers using existing utils functions
            task_definitions = await find_task_definitions(
                cluster_name=cluster_name, service_name=service_name
            )
            load_balancers = await find_load_balancers(
                cluster_name=cluster_name, service_name=service_name
            )

        # Validate container images if we have task definitions
        if task_definitions:
            image_check_results = await validate_container_images(task_definitions)

    except Exception as e:
        logger.warning(f"Error collecting task details for cluster {cluster_name}: {e}")

    return task_definitions, load_balancers, image_check_results


def generate_assessment(
    cluster_name: str,
    service_name: Optional[str],
    cluster_details: List[Dict[str, Any]],
    service_details: List[Dict[str, Any]],
    task_definitions: List[Dict[str, Any]],
    load_balancers: List[Dict[str, Any]],
    cloudformation_info: Optional[Dict[str, Any]],
) -> str:
    """
    Generate human-readable assessment text from collected data.

    Parameters
    ----------
    cluster_name : str
        The name of the ECS cluster
    service_name : Optional[str]
        The name of specific service, if applicable
    cluster_details : List[Dict[str, Any]]
        List of cluster details
    service_details : List[Dict[str, Any]]
        List of service details
    task_definitions : List[Dict[str, Any]]
        List of task definitions
    load_balancers : List[Dict[str, Any]]
        List of load balancers
    cloudformation_info : Optional[Dict[str, Any]]
        CloudFormation stack information, if applicable

    Returns
    -------
    str
        Formatted assessment string
    """
    assessment = f"Analyzed ECS cluster '{cluster_name}'"
    if service_name:
        assessment += f" and service '{service_name}'"

    if cluster_details:
        cluster = cluster_details[0]
        assessment += f". Cluster status: {cluster['status']}"
        assessment += f", running tasks: {cluster['runningTasksCount']}"
        assessment += f", pending tasks: {cluster['pendingTasksCount']}"
        assessment += f", active services: {cluster['activeServicesCount']}"

    if service_details:
        assessment += f". Found {len(service_details)} service(s)"

    if task_definitions:
        assessment += f", {len(task_definitions)} task definition(s)"

    if load_balancers:
        assessment += f", {len(load_balancers)} load balancer(s)"

    if cloudformation_info:
        stack_name = cloudformation_info["stack_name"]
        stack_status = cloudformation_info["stack_status"]
        assessment += f". CloudFormation stack: {stack_name} ({stack_status})"

    return assessment


async def get_ecs_troubleshooting_guidance(
    cluster_name: str,
    service_name: Optional[str] = None,
    symptoms_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initial entry point that analyzes ECS deployment state and collects troubleshooting information.

    Parameters
    ----------
    cluster_name : str
        The name of the ECS cluster to troubleshoot
    service_name : str, optional
        The name of the ECS service to troubleshoot
    symptoms_description : str, optional
        Description of symptoms experienced by the user

    Returns
    -------
    Dict[str, Any]
        Initial assessment and collected troubleshooting data
    """
    try:
        # Initialize response structure
        response = {"status": "success", "assessment": "", "raw_data": {}}

        # Initialize AWS clients
        ecs_client = await get_aws_client("ecs")

        # Store input parameters
        response["raw_data"]["cluster_name"] = cluster_name
        if service_name:
            response["raw_data"]["service_name"] = service_name
        if symptoms_description:
            response["raw_data"]["symptoms_description"] = symptoms_description

        # 1. Collect cluster details
        cluster_details, cluster_arn = await collect_cluster_details(cluster_name, ecs_client)
        response["raw_data"]["cluster_details"] = cluster_details

        # Return error if cluster not found
        if not cluster_details:
            return {
                "status": "error",
                "error": f"Cluster '{cluster_name}' not found.",
                "assessment": (
                    f"Error analyzing deployment: Cluster '{cluster_name}' "
                    f"not found or inaccessible."
                ),
            }

        # 2. Collect service details
        service_details = await collect_service_details(cluster_name, service_name, ecs_client)
        response["raw_data"]["service_details"] = service_details

        # 3. Check for CloudFormation
        cloudformation_info = None
        if cluster_arn:
            cloudformation_info = await get_cloudformation_stack_if_exists(cluster_arn)
            if cloudformation_info:
                response["raw_data"]["cloudformation_stack"] = cloudformation_info

        # 4. Collect task-related details
        task_definitions, load_balancers, image_check_results = await collect_task_details(
            cluster_name, service_name
        )
        response["raw_data"]["task_definitions"] = task_definitions
        response["raw_data"]["load_balancers"] = load_balancers
        response["raw_data"]["image_check_results"] = image_check_results

        # 5. Generate assessment
        assessment = generate_assessment(
            cluster_name,
            service_name,
            cluster_details,
            service_details,
            task_definitions,
            load_balancers,
            cloudformation_info,
        )
        response["assessment"] = assessment

        return response

    except Exception as e:
        logger.exception("Error in get_ecs_troubleshooting_guidance: %s", str(e))
        return {
            "status": "error",
            "error": str(e),
            "assessment": f"Error analyzing deployment: {str(e)}",
        }
