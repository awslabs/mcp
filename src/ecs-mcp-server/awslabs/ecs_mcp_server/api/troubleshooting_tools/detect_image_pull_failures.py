"""
Specialized tool for detecting container image pull failures.

This module provides a function to find related task definitions and check if their
container images exist and are accessible, helping to diagnose image pull failures in ECS.
"""

import logging
from typing import Any, Dict, List

from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    get_task_definitions as _get_task_definitions,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    validate_container_images as _validate_container_images,
)

logger = logging.getLogger(__name__)


# Re-export these functions for testing purposes
async def get_task_definitions(app_name: str) -> List[Dict[str, Any]]:
    """
    Find task definitions related to the application.

    This is a wrapper around the function in get_ecs_troubleshooting_guidance.

    Parameters
    ----------
    app_name : str
        The name of the application to find task definitions for

    Returns
    -------
    List[Dict[str, Any]]
        List of task definition dictionaries with full details
    """
    return await _get_task_definitions(app_name)


async def validate_container_images(task_definitions: List[Dict]) -> List[Dict]:
    """
    Validate container images in task definitions.

    This is a wrapper around the function in get_ecs_troubleshooting_guidance.

    Parameters
    ----------
    task_definitions : List[Dict]
        List of task definition dictionaries

    Returns
    -------
    List[Dict]
        List of validation results for each container image
    """
    return await _validate_container_images(task_definitions)


async def detect_image_pull_failures(app_name: str) -> Dict[str, Any]:
    """
    Specialized tool for detecting image pull failures.

    Parameters
    ----------
    app_name : str
        Application name to check for image pull failures

    Returns
    -------
    Dict[str, Any]
        Dictionary with image issues analysis and recommendations
    """
    try:
        response = {
            "status": "success",
            "image_issues": [],
            "assessment": "",
            "recommendations": [],
        }

        # Find related task definitions
        try:
            task_definitions = await get_task_definitions(app_name)
        except Exception as e:
            logger.exception("Error getting task definitions: %s", str(e))
            return {
                "status": "error",
                "error": str(e),
                "assessment": f"Error checking for image pull failures: {str(e)}",
                "image_issues": [],
            }

        if not task_definitions:
            response["assessment"] = f"No task definitions found related to {app_name}"
            response["recommendations"].append("Check if your task definition is named differently")
            return response

        # Check container images
        try:
            image_results = await validate_container_images(task_definitions)
        except Exception as e:
            logger.exception("Error validating container images: %s", str(e))
            return {
                "status": "error",
                "error": str(e),
                "assessment": f"Error validating container images: {str(e)}",
                "image_issues": [],
            }

        # Analyze results
        failed_images = [result for result in image_results if result["exists"] != "true"]

        if failed_images:
            response["assessment"] = (
                f"Found {len(failed_images)} container image(s) that may be causing pull failures"
            )
            response["image_issues"] = failed_images

            for failed in failed_images:
                task_def_arn = failed.get("task_definition", "")
                task_def_name = task_def_arn.split("/")[-1] if task_def_arn else "unknown"
                container_name = failed.get("container_name", "unknown")

                if failed["repository_type"] == "ecr":
                    response["recommendations"].append(
                        f"ECR image '{failed['image']}' not found in task definition "
                        f"'{task_def_name}', container '{container_name}'. "
                        f"Check if the repository exists and the image has been pushed."
                    )
                elif failed["exists"] == "unknown":
                    response["recommendations"].append(
                        f"External image '{failed['image']}' in task definition "
                        f"'{task_def_name}', container '{container_name}' "
                        f"cannot be verified without pulling. Verify that the image exists, "
                        f"is spelled correctly, and is publicly accessible or has proper "
                        f"credentials configured in your task execution role."
                    )
                else:
                    response["recommendations"].append(
                        f"Image '{failed['image']}' in task definition "
                        f"'{task_def_name}', container '{container_name}' "
                        f"has issues. Check the image reference and ensure it points to a "
                        f"valid repository."
                    )
        else:
            response["assessment"] = "All container images appear to be valid and accessible."

        # Add recommendations based on task_definition analysis
        for task_def in task_definitions:
            task_def_arn = task_def.get("taskDefinitionArn", "")
            task_def_name = task_def_arn.split("/")[-1] if task_def_arn else "unknown"

            # Check if task definition has execution role for ECR image pulling
            execution_role_arn = task_def.get("executionRoleArn")
            if not execution_role_arn and any(
                "ecr" in container.get("image", "")
                for container in task_def.get("containerDefinitions", [])
            ):
                response["recommendations"].append(
                    f"Task definition '{task_def_name}' uses ECR images but does not have "
                    f"an execution role. Add an executionRole with AmazonECR-ReadOnly permissions."
                )

        return response
    except Exception as e:
        logger.exception("Error in detect_image_pull_failures: %s", str(e))
        return {
            "status": "error",
            "error": str(e),
            "assessment": f"Error checking for image pull failures: {str(e)}",
            "image_issues": [],
        }
