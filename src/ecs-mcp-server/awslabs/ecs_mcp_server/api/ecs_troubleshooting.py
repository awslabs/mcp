"""
ECS troubleshooting tool that aggregates all troubleshooting functionality.

This module provides a single entry point for all ECS troubleshooting operations
that were previously available as separate tools.
"""

import inspect
import logging
from typing import Any, Dict, Literal, Optional

from awslabs.ecs_mcp_server.api.troubleshooting_tools.detect_image_pull_failures import (
    detect_image_pull_failures,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_cloudformation_status import (
    fetch_cloudformation_status,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_network_configuration import (
    fetch_network_configuration,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_service_events import (
    fetch_service_events,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_task_failures import (
    fetch_task_failures,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.fetch_task_logs import (
    fetch_task_logs,
)
from awslabs.ecs_mcp_server.api.troubleshooting_tools.get_ecs_troubleshooting_guidance import (
    get_ecs_troubleshooting_guidance,
)

logger = logging.getLogger(__name__)

# Type definitions
TroubleshootingAction = Literal[
    "get_ecs_troubleshooting_guidance",
    "fetch_cloudformation_status",
    "fetch_service_events",
    "fetch_task_failures",
    "fetch_task_logs",
    "detect_image_pull_failures",
    "fetch_network_configuration",
]

# Combined actions configuration with inline parameter transformers and documentation
ACTIONS = {
    "get_ecs_troubleshooting_guidance": {
        "func": get_ecs_troubleshooting_guidance,
        "required_params": ["app_name"],
        "optional_params": ["symptoms_description"],
        "transformer": lambda app_name, params: {
            "app_name": app_name,
            "symptoms_description": params.get("symptoms_description"),
        },
        "description": "Initial assessment and data collection",
        "param_descriptions": {
            "app_name": "The name of the application/stack to troubleshoot",
            "symptoms_description": "Description of symptoms experienced by the user",
        },
        "example": (
            'action="get_ecs_troubleshooting_guidance", '
            'parameters={"symptoms_description": "ALB returning 503 errors"}'
        ),
    },
    "fetch_cloudformation_status": {
        "func": fetch_cloudformation_status,
        "required_params": ["stack_id"],
        "optional_params": [],
        "transformer": lambda app_name, params: {"stack_id": params.get("stack_id", app_name)},
        "description": "Infrastructure-level diagnostics for CloudFormation stacks",
        "param_descriptions": {"stack_id": "The CloudFormation stack identifier to analyze"},
        "example": 'action="fetch_cloudformation_status", parameters={"stack_id": "my-app-stack"}',
    },
    "fetch_service_events": {
        "func": fetch_service_events,
        "required_params": ["app_name", "cluster_name", "service_name"],
        "optional_params": ["time_window", "start_time", "end_time"],
        "transformer": lambda app_name, params: {
            "app_name": app_name,
            "cluster_name": params["cluster_name"],
            "service_name": params["service_name"],
            "time_window": params.get("time_window", 3600),
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
        },
        "description": "Service-level diagnostics for ECS services",
        "param_descriptions": {
            "app_name": "The name of the application to analyze",
            "cluster_name": "The name of the ECS cluster",
            "service_name": "The name of the ECS service to analyze",
            "time_window": "Time window in seconds to look back for events (default: 3600)",
            "start_time": (
                "Explicit start time for the analysis window "
                "(UTC, takes precedence over time_window if provided)"
            ),
            "end_time": (
                "Explicit end time for the analysis window "
                "(UTC, defaults to current time if not provided)"
            ),
        },
        "example": (
            'action="fetch_service_events", '
            'parameters={"cluster_name": "my-cluster", "service_name": "my-service", '
            '"time_window": 7200}'
        ),
    },
    "fetch_task_failures": {
        "func": fetch_task_failures,
        "required_params": ["app_name", "cluster_name"],
        "optional_params": ["time_window", "start_time", "end_time"],
        "transformer": lambda app_name, params: {
            "app_name": app_name,
            "cluster_name": params["cluster_name"],
            "time_window": params.get("time_window", 3600),
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
        },
        "description": "Task-level diagnostics for ECS task failures",
        "param_descriptions": {
            "app_name": "The name of the application to analyze",
            "cluster_name": "The name of the ECS cluster",
            "time_window": "Time window in seconds to look back for failures (default: 3600)",
            "start_time": (
                "Explicit start time for the analysis window "
                "(UTC, takes precedence over time_window if provided)"
            ),
            "end_time": (
                "Explicit end time for the analysis window "
                "(UTC, defaults to current time if not provided)"
            ),
        },
        "example": (
            'action="fetch_task_failures", '
            'parameters={"cluster_name": "my-cluster", "time_window": 3600}'
        ),
    },
    "fetch_task_logs": {
        "func": fetch_task_logs,
        "required_params": ["app_name", "cluster_name"],
        "optional_params": ["task_id", "time_window", "filter_pattern", "start_time", "end_time"],
        "transformer": lambda app_name, params: {
            "app_name": app_name,
            "cluster_name": params["cluster_name"],
            "task_id": params.get("task_id"),
            "time_window": params.get("time_window", 3600),
            "filter_pattern": params.get("filter_pattern"),
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
        },
        "description": "Application-level diagnostics through CloudWatch logs",
        "param_descriptions": {
            "app_name": "The name of the application to analyze",
            "cluster_name": "The name of the ECS cluster",
            "task_id": "Specific task ID to retrieve logs for",
            "time_window": "Time window in seconds to look back for logs (default: 3600)",
            "filter_pattern": "CloudWatch logs filter pattern",
            "start_time": (
                "Explicit start time for the analysis window "
                "(UTC, takes precedence over time_window if provided)"
            ),
            "end_time": (
                "Explicit end time for the analysis window "
                "(UTC, defaults to current time if not provided)"
            ),
        },
        "example": (
            'action="fetch_task_logs", '
            'parameters={"cluster_name": "my-cluster", "filter_pattern": "ERROR", '
            '"time_window": 1800}'
        ),
    },
    "detect_image_pull_failures": {
        "func": detect_image_pull_failures,
        "required_params": ["app_name"],
        "optional_params": [],
        "transformer": lambda app_name, params: {"app_name": app_name},
        "description": "Specialized tool for detecting container image pull failures",
        "param_descriptions": {"app_name": "Application name to check for image pull failures"},
        "example": 'action="detect_image_pull_failures", parameters={}',
    },
    "fetch_network_configuration": {
        "func": fetch_network_configuration,
        "required_params": ["app_name"],
        "optional_params": ["vpc_id", "cluster_name"],
        "transformer": lambda app_name, params: {
            "app_name": app_name,
            "vpc_id": params.get("vpc_id"),
            "cluster_name": params.get("cluster_name"),
        },
        "description": "Network-level diagnostics for ECS deployments",
        "param_descriptions": {
            "app_name": "The name of the application to analyze",
            "vpc_id": "Specific VPC ID to analyze",
            "cluster_name": "Specific ECS cluster name",
        },
        "example": (
            'action="fetch_network_configuration", '
            'parameters={"vpc_id": "vpc-12345678", '
            '"cluster_name": "my-cluster"}'
        ),
    },
}


def generate_troubleshooting_docs():
    """Generate documentation for the troubleshooting tools based on the ACTIONS dictionary."""

    # Generate the main body of the documentation
    actions_docs = []
    quick_usage_examples = []

    for action_name, action_data in ACTIONS.items():
        # Build the action documentation
        action_doc = f"### {len(actions_docs) + 1}. {action_name}\n"
        action_doc += f"{action_data['description']}\n"

        # Required parameters
        action_doc += "- Required: " + ", ".join(action_data["required_params"]) + "\n"

        # Optional parameters if any
        if action_data.get("optional_params"):
            optional_params_with_desc = []
            for param in action_data.get("optional_params", []):
                desc = action_data["param_descriptions"].get(param, "")
                optional_params_with_desc.append(f"{param} ({desc})")
            if optional_params_with_desc:
                action_doc += "- Optional: " + ", ".join(optional_params_with_desc) + "\n"

        # Example usage
        action_doc += f"- Example: {action_data['example']}\n"

        actions_docs.append(action_doc)

        # Build a quick usage example
        example = f"# {action_data['description']}\n"
        example += f'action: "{action_name}"\n'

        # Extract parameters from the example string
        import re

        params_match = re.search(r"parameters=\{(.*?)\}", action_data["example"])
        if params_match:
            params_str = params_match.group(1)
            example += f"parameters: {{{params_str}}}\n"
        else:
            example += "parameters: {}\n"

        quick_usage_examples.append(example)

    # Combine all documentation sections
    doc_header = """
ECS troubleshooting tool with multiple diagnostic actions.

This tool provides access to all ECS troubleshooting operations through a single
interface. Use the 'action' parameter to specify which troubleshooting operation
to perform.

## Available Actions and Parameters:

"""

    doc_examples = """
## Quick Usage Examples:

```
"""

    doc_footer = """```

Parameters:
    app_name: Application/stack name (required for most actions)
    action: The troubleshooting action to perform (see available actions above)
    parameters: Action-specific parameters (see parameter specifications above)

Returns:
    Results from the selected troubleshooting action
"""

    # Combine all the documentation parts
    full_doc = (
        doc_header
        + "\n".join(actions_docs)
        + doc_examples
        + "\n".join(quick_usage_examples)
        + doc_footer
    )

    return full_doc


def _validate_action(action: str) -> None:
    """Validate that the action is supported."""
    if action not in ACTIONS:
        valid_actions = ", ".join(ACTIONS.keys())
        raise ValueError(f"Invalid action '{action}'. Valid actions: {valid_actions}")


def _validate_parameters(action: str, app_name: Optional[str], parameters: Dict[str, Any]) -> None:
    """Validate required parameters for the given action."""
    required = ACTIONS[action]["required_params"]

    # Check app_name if required
    if "app_name" in required and (not app_name or not app_name.strip()):
        raise ValueError(f"app_name is required for action '{action}'")

    # Check other required parameters
    for param in required:
        if param != "app_name" and param not in parameters:
            raise ValueError(f"Missing required parameter '{param}' for action '{action}'")


# Pre-generate the documentation once to avoid regenerating it on each call
TROUBLESHOOTING_DOCS = generate_troubleshooting_docs()


async def ecs_troubleshooting_tool(
    app_name: Optional[str] = None,
    action: TroubleshootingAction = "get_ecs_troubleshooting_guidance",
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    ECS troubleshooting tool.

    This tool provides access to all ECS troubleshooting operations through a single
    interface. Use the 'action' parameter to specify which troubleshooting operation
    to perform.

    Args:
        app_name: Application/stack name (required for most actions)
        action: The troubleshooting action to perform
        parameters: Action-specific parameters

    Returns:
        Results from the selected troubleshooting action

    Raises:
        ValueError: If action is invalid or required parameters are missing
    """
    # NOTE: The full documentation is available in the TROUBLESHOOTING_DOCS variable
    try:
        if parameters is None:
            parameters = {}

        # Validate action
        _validate_action(action)

        # Check security permissions for sensitive data actions
        sensitive_data_actions = [
            "fetch_task_logs",
            "fetch_service_events",
            "fetch_task_failures",
            "fetch_network_configuration",
        ]
        if action in sensitive_data_actions:
            # Import here to avoid circular imports
            from awslabs.ecs_mcp_server.utils.config import get_config

            # Check if sensitive data access is allowed
            config = get_config()
            if not config.get("allow-sensitive-data", False):
                return {
                    "status": "error",
                    "error": (
                        f"Action {action} is not allowed without ALLOW_SENSITIVE_DATA=true "
                        f"in your environment due to potential exposure of sensitive information."
                    ),
                }

        # Validate parameters
        _validate_parameters(action, app_name, parameters)

        # Get action configuration
        action_config = ACTIONS[action]

        # Transform parameters using action-specific transformer
        func_params = action_config["transformer"](app_name, parameters)

        # Call the function and await it if it's a coroutine
        result = action_config["func"](**func_params)
        if inspect.iscoroutine(result):
            result = await result

        return result

    except ValueError as e:
        logger.error(f"Parameter validation error: {str(e)}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.exception(f"Error in ecs_troubleshooting_tool: {str(e)}")
        return {"status": "error", "error": f"Internal error: {str(e)}"}
