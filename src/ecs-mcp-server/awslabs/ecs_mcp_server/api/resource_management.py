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
API for ECS resource management operations.

This module provides functions for executing ECS API operations
using a consistent interface.
"""

import copy
import logging
import re
from typing import Any, Dict, Set

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)

# Operations that return sensitive data (environment variables, secrets, etc.)
# These require ALLOW_SENSITIVE_DATA=true or their responses will be sanitized.
SENSITIVE_DATA_OPERATIONS: Set[str] = {
    "DescribeTaskDefinition",
    "DescribeTasks",
}

# List of supported ECS API operations
SUPPORTED_ECS_OPERATIONS = [
    "CreateCapacityProvider",
    "CreateCluster",
    "CreateExpressGatewayService",
    "CreateService",
    "CreateTaskSet",
    "DeleteAccountSetting",
    "DeleteAttributes",
    "DeleteCapacityProvider",
    "DeleteCluster",
    "DeleteExpressGatewayService",
    "DeleteService",
    "DeleteTaskDefinitions",
    "DeleteTaskSet",
    "DeregisterContainerInstance",
    "DeregisterTaskDefinition",
    "DescribeCapacityProviders",
    "DescribeClusters",
    "DescribeContainerInstances",
    "DescribeExpressGatewayService",
    "DescribeServiceDeployments",
    "DescribeServiceRevisions",
    "DescribeServices",
    "DescribeTaskDefinition",
    "DescribeTasks",
    "DescribeTaskSets",
    "DiscoverPollEndpoint",
    "ExecuteCommand",
    "GetTaskProtection",
    "ListAccountSettings",
    "ListAttributes",
    "ListClusters",
    "ListContainerInstances",
    "ListExpressGatewayServices",
    "ListServiceDeployments",
    "ListServices",
    "ListServicesByNamespace",
    "ListTagsForResource",
    "ListTaskDefinitionFamilies",
    "ListTaskDefinitions",
    "ListTasks",
    "PutAccountSetting",
    "PutAccountSettingDefault",
    "PutAttributes",
    "PutClusterCapacityProviders",
    "RegisterContainerInstance",
    "RegisterTaskDefinition",
    "RunTask",
    "StartTask",
    "StopServiceDeployment",
    "StopTask",
    "SubmitAttachmentStateChanges",
    "SubmitContainerStateChange",
    "SubmitTaskStateChange",
    "TagResource",
    "UntagResource",
    "UpdateCapacityProvider",
    "UpdateCluster",
    "UpdateClusterSettings",
    "UpdateContainerAgent",
    "UpdateContainerInstancesState",
    "UpdateExpressGatewayService",
    "UpdateService",
    "UpdateServicePrimaryTaskSet",
    "UpdateTaskProtection",
    "UpdateTaskSet",
]


def camel_to_snake(name):
    """
    Convert CamelCase to snake_case.

    This function is used to convert AWS API operation names from their CamelCase format
    (as documented in AWS API references and used in our SUPPORTED_ECS_OPERATIONS list)
    to the snake_case format required by boto3 client methods.

    Examples:
        "CreateCluster" -> "create_cluster"
        "DescribeServices" -> "describe_services"
        "UpdateTaskProtection" -> "update_task_protection"

    Args:
        name: CamelCase string (e.g., "CreateCluster")

    Returns:
        snake_case string (e.g., "create_cluster")
    """
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def _sanitize_sensitive_response(response: Dict[str, Any], api_operation: str) -> Dict[str, Any]:
    """
    Sanitize sensitive fields from API responses when ALLOW_SENSITIVE_DATA is false.

    For DescribeTaskDefinition: redacts containerDefinitions[].environment values
    and containerDefinitions[].secrets.
    For DescribeTasks: redacts containers[].environment values and overrides.

    Args:
        response: The raw API response
        api_operation: The operation that produced the response

    Returns:
        A sanitized copy of the response with sensitive fields redacted
    """
    sanitized = copy.deepcopy(response)

    if api_operation == "DescribeTaskDefinition":
        task_def = sanitized.get("taskDefinition", {})
        for container in task_def.get("containerDefinitions", []):
            # Redact environment variable values (keep names for debugging)
            for env_var in container.get("environment", []):
                env_var["value"] = "[REDACTED]"
            # Remove secrets entirely (they reference SSM/Secrets Manager ARNs)
            if "secrets" in container:
                container["secrets"] = [
                    {"name": s.get("name", ""), "valueFrom": "[REDACTED]"}
                    for s in container["secrets"]
                ]

    elif api_operation == "DescribeTasks":
        for task in sanitized.get("tasks", []):
            # Redact container overrides environment values
            for override in task.get("overrides", {}).get("containerOverrides", []):
                for env_var in override.get("environment", []):
                    env_var["value"] = "[REDACTED]"
            # Redact container-level environment from containers
            for container in task.get("containers", []):
                for env_var in container.get("environment", []):
                    env_var["value"] = "[REDACTED]"

    return sanitized


async def ecs_api_operation(api_operation: str, api_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an ECS API operation with the provided parameters.

    Args:
        api_operation: The boto3 ECS API operation to execute (camelCase)
        api_params: Dictionary of parameters to pass to the API operation

    Returns:
        Dictionary containing the API response

    Note:
        Operations starting with "Describe" or "List" are read-only.
        All other operations require WRITE permission (ALLOW_WRITE=true).
        Operations in SENSITIVE_DATA_OPERATIONS have their responses sanitized
        when ALLOW_SENSITIVE_DATA is not set to true.
    """
    # Validate the API operation
    if api_operation not in SUPPORTED_ECS_OPERATIONS:
        supported_ops = ", ".join(SUPPORTED_ECS_OPERATIONS)
        raise ValueError(
            f"Unsupported API operation: {api_operation}. Must be one of: {supported_ops}"
        )

    # Import here to avoid circular imports
    from awslabs.ecs_mcp_server.utils.config import get_config

    config = get_config()

    # Check if this is a write operation (not starting with "Describe" or "List")
    if not api_operation.startswith("Describe") and not api_operation.startswith("List"):
        # Check if write operations are allowed
        if not config.get("allow-write", False):
            return {
                "status": "error",
                "error": (
                    f"Operation {api_operation} requires WRITE permission. "
                    f"Set ALLOW_WRITE=true in your environment to enable write operations."
                ),
            }

    logger.info(f"Executing ECS API operation: {api_operation} with params: {api_params}")

    try:
        # Get the ECS client
        ecs_client = await get_aws_client("ecs")

        # Convert api_operation (CamelCase) to the method name (snake_case)
        method_name = camel_to_snake(api_operation)

        # Get the method
        method = getattr(ecs_client, method_name)

        # Execute the API operation with the provided parameters
        response = method(**api_params)

        # Sanitize sensitive data if the operation returns sensitive information
        # and ALLOW_SENSITIVE_DATA is not enabled
        if api_operation in SENSITIVE_DATA_OPERATIONS and not config.get(
            "allow-sensitive-data", False
        ):
            response = _sanitize_sensitive_response(response, api_operation)

        return response
    except Exception as e:
        logger.error(f"Error executing ECS API operation {api_operation}: {e}")
        return {"error": str(e), "status": "failed"}
