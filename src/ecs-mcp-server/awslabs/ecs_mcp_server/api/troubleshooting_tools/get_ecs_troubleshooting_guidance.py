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

from awslabs.ecs_mcp_server.utils.arn_parser import parse_arn
from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)

# Export these functions for testing purposes
__all__ = [
    "get_ecs_troubleshooting_guidance",
    "get_task_definitions",
    "validate_container_images",
    "find_related_task_definitions",
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


async def find_clusters(app_name: str) -> List[str]:
    """Find ECS clusters related to the application."""
    clusters = []
    ecs = await get_aws_client("ecs")

    cluster_list = await handle_aws_api_call(ecs.list_clusters, {"clusterArns": []})
    if not cluster_list or "clusterArns" not in cluster_list:
        return clusters

    for cluster_arn in cluster_list["clusterArns"]:
        parsed_arn = parse_arn(cluster_arn)
        if parsed_arn and app_name.lower() in parsed_arn.resource_name.lower():
            clusters.append(parsed_arn.resource_name)

    return clusters


async def find_services(app_name: str, cluster_name: str) -> List[str]:
    """Find ECS services in a specific cluster related to the application."""
    services = []
    ecs = await get_aws_client("ecs")

    try:
        service_list = ecs.list_services(cluster=cluster_name)

        if not isinstance(service_list, dict):
            return services

        if not service_list or "serviceArns" not in service_list:
            return services

        for service_arn in service_list["serviceArns"]:
            parsed_arn = parse_arn(service_arn)
            if parsed_arn and app_name.lower() in parsed_arn.resource_name.lower():
                services.append(parsed_arn.resource_name)
    except Exception as e:
        logger.warning(f"Error listing services for cluster {cluster_name}: {e}")

    return services


async def find_load_balancers(app_name: str) -> List[Dict[str, Any]]:
    """Find load balancers related to the application."""
    load_balancers = []
    elbv2 = await get_aws_client("elbv2")

    lb_list = await handle_aws_api_call(elbv2.describe_load_balancers, {"LoadBalancers": []})

    if not lb_list or "LoadBalancers" not in lb_list:
        return load_balancers

    for lb in lb_list["LoadBalancers"]:
        if app_name.lower() in lb.get("LoadBalancerName", "").lower():
            load_balancers.append(lb.get("LoadBalancerName"))

    return load_balancers


async def get_task_definitions(app_name: str) -> List[Dict[str, Any]]:
    """
    Find task definitions related to the application using simple name matching.

    This function retrieves all task definition families matching the app name pattern,
    then gets the latest revision of each family to return complete task definition objects.

    Parameters
    ----------
    app_name : str
        The name of the application to find task definitions for

    Returns
    -------
    List[Dict[str, Any]]
        List of task definition dictionaries with full details
    """
    task_definitions = []
    ecs = await get_aws_client("ecs")
    app_name_lower = app_name.lower()

    try:
        # Get list of task definition ARNs
        paginator = ecs.get_paginator("list_task_definitions")
        families_by_latest = {}

        # Use pagination to handle large lists efficiently
        for page in paginator.paginate(status="ACTIVE", maxResults=100):
            for arn in page.get("taskDefinitionArns", []):
                parsed_arn = parse_arn(arn)
                if not parsed_arn:
                    continue

                # Extract family and revision directly using the parsed ARN
                resource_parts = parsed_arn.resource_id.split(":")
                family = resource_parts[0]
                revision = int(resource_parts[1]) if len(resource_parts) > 1 else 0

                # Check if app name is in the family name
                if app_name_lower in family.lower():
                    # Track only the latest revision
                    if family not in families_by_latest or revision > families_by_latest[family][1]:
                        families_by_latest[family] = (arn, revision)

        # Get task definitions for the latest revision of each matching family
        for arn, _ in families_by_latest.values():
            task_def_response = await handle_aws_api_call(
                ecs.describe_task_definition, None, taskDefinition=arn
            )
            if task_def_response and "taskDefinition" in task_def_response:
                task_definitions.append(task_def_response["taskDefinition"])

    except ClientError as e:
        logger.warning(f"Error finding task definitions: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error finding task definitions: {e}")

    return task_definitions


async def discover_resources(app_name: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Main resource discovery coordinator function.

    Discovers all ECS resources related to the given application name including
    clusters, services, task definitions, and load balancers.

    Parameters
    ----------
    app_name : str
        The name of the application to discover resources for

    Returns
    -------
    Tuple[Dict[str, Any], List[Dict[str, Any]]]
        Tuple containing:
        - Dictionary of resource IDs grouped by type
        - List of complete task definition objects
    """
    resources = {
        "clusters": await find_clusters(app_name),
        "services": [],
        "task_definitions": [],
        "load_balancers": await find_load_balancers(app_name),
    }

    # Find services for each discovered cluster and default cluster
    for cluster in resources["clusters"] + ["default"]:
        services = await find_services(app_name, cluster)
        resources["services"].extend(services)

    # Get task definitions
    task_defs = await get_task_definitions(app_name)

    # For task definitions, extract and format the resource ID
    for task_def in task_defs:
        if "taskDefinitionArn" in task_def:
            parsed_arn = parse_arn(task_def["taskDefinitionArn"])
            if parsed_arn:
                resources["task_definitions"].append(parsed_arn.resource_id)

    return resources, task_defs


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
        ecr = await get_aws_client("ecr")

        # Parse repository name and tag
        repo_name, tag = parse_ecr_image_uri(image_uri)
        if not repo_name:
            result["error"] = "Failed to parse ECR image URI"
            return result

        # Check if repository exists
        try:
            # Just check if the repository exists without storing the result
            ecr.describe_repositories(repositoryNames=[repo_name])

            # Check if image with tag exists
            try:
                # Just check if the image exists without storing the result
                ecr.describe_images(repositoryName=repo_name, imageIds=[{"imageTag": tag}])
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


async def get_stack_status(app_name: str) -> str:
    """Get CloudFormation stack status for the application."""
    cloudformation = await get_aws_client("cloudformation")
    try:
        cf_response = cloudformation.describe_stacks(StackName=app_name)
        if cf_response["Stacks"]:
            return cf_response["Stacks"][0]["StackStatus"]
        return "NOT_FOUND"
    except ClientError as e:
        # Handle specific CloudFormation errors
        if e.response["Error"]["Code"] == "AccessDenied":
            # For AccessDenied (test case), this should propagate to the caller
            # to be treated as an error
            raise e
        return "NOT_FOUND"


def create_assessment(app_name: str, stack_status: str, resources: Dict) -> str:
    """Create a human-readable assessment of the application's state."""
    if stack_status == "NOT_FOUND":
        assessment = (
            f"CloudFormation stack '{app_name}' does not exist. "
            f"Infrastructure deployment may have failed or not been attempted."
        )

        # Add information about related resources if found
        if resources["task_definitions"]:
            assessment += f" Found {len(resources['task_definitions'])} related task definitions."

        if resources["clusters"]:
            assessment += (
                f" Found similar clusters that may be related: {', '.join(resources['clusters'])}."
            )

    elif "ROLLBACK" in stack_status or "FAILED" in stack_status:
        assessment = (
            f"CloudFormation stack '{app_name}' exists but is in a failed state: {stack_status}."
        )

    elif "IN_PROGRESS" in stack_status:
        assessment = (
            f"CloudFormation stack '{app_name}' is currently being created/updated: {stack_status}."
        )

    elif stack_status == "CREATE_COMPLETE" and not resources["clusters"]:
        assessment = (
            f"CloudFormation stack '{app_name}' exists and is complete, "
            f"but no related ECS clusters were found."
        )

    elif stack_status == "CREATE_COMPLETE" and resources["clusters"]:
        cluster_name = resources["clusters"][0]
        assessment = (
            f"CloudFormation stack '{app_name}' and ECS cluster '{cluster_name}' both exist."
        )

    else:
        assessment = f"CloudFormation stack '{app_name}' is in status: {stack_status}."

    return assessment


async def find_related_task_definitions(app_name: str) -> List[Dict[str, Any]]:
    """
    Find task definitions related to the application.

    This is a wrapper around get_task_definitions for testing purposes.

    Parameters
    ----------
    app_name : str
        The name of the application to find task definitions for

    Returns
    -------
    List[Dict[str, Any]]
        List of task definition dictionaries with full details
    """
    return await get_task_definitions(app_name)


async def get_cluster_details(cluster_names: List[str]) -> List[Dict[str, Any]]:
    """Get detailed information about ECS clusters."""
    if not cluster_names:
        return []

    ecs = await get_aws_client("ecs")
    clusters_info = await handle_aws_api_call(
        ecs.describe_clusters, {"clusters": [], "failures": []}, clusters=cluster_names
    )

    if not clusters_info or "clusters" not in clusters_info:
        return []

    detailed_clusters = []
    for cluster in clusters_info.get("clusters", []):
        cluster_info = {
            "name": cluster["clusterName"],
            "status": cluster["status"],
            "exists": True,
            "runningTasksCount": cluster.get("runningTasksCount", 0),
            "pendingTasksCount": cluster.get("pendingTasksCount", 0),
            "activeServicesCount": cluster.get("activeServicesCount", 0),
            "registeredContainerInstancesCount": cluster.get(
                "registeredContainerInstancesCount", 0
            ),
        }
        detailed_clusters.append(cluster_info)

    return detailed_clusters


async def get_ecs_troubleshooting_guidance(
    app_name: str, symptoms_description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Initial entry point that analyzes ECS deployment state and collects troubleshooting information.

    Parameters
    ----------
    app_name : str
        The name of the application/stack to troubleshoot
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

        # 1. Discover resources and collect raw task definitions
        resources, task_definitions = await discover_resources(app_name)
        response["raw_data"]["related_resources"] = resources
        response["raw_data"]["task_definitions"] = task_definitions

        # 2. Get detailed cluster information
        clusters = await get_cluster_details(resources["clusters"])
        response["raw_data"]["clusters"] = clusters

        try:
            # 3. Check stack status
            stack_status = await get_stack_status(app_name)
            response["raw_data"]["cloudformation_status"] = stack_status
        except ClientError as e:
            # Handle auth error or other ClientError
            error_msg = str(e)
            response["status"] = "error"
            response["error"] = error_msg
            response["assessment"] = f"Error accessing stack information: {error_msg}"
            return response

        # 4. Check container images
        image_check_results = await validate_container_images(task_definitions)
        response["raw_data"]["image_check_results"] = image_check_results

        # Store symptoms description as raw input if provided
        if symptoms_description:
            response["raw_data"]["symptoms_description"] = symptoms_description

        # Create assessment
        response["assessment"] = create_assessment(app_name, stack_status, resources)

        return response

    except Exception as e:
        logger.exception("Error in get_ecs_troubleshooting_guidance: %s", str(e))
        return {
            "status": "error",
            "error": str(e),
            "assessment": f"Error analyzing deployment: {str(e)}",
        }
