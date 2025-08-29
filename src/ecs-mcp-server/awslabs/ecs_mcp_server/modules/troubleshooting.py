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
Troubleshooting module for ECS MCP Server.
This module provides tools and prompts for troubleshooting ECS deployments.
"""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ecs_mcp_server.api.ecs_troubleshooting import (
    TroubleshootingAction,
    ecs_troubleshooting_tool,
)


def register_troubleshooting_prompts(mcp: FastMCP, prompt_groups: Dict[str, List[str]]) -> None:
    """
    Register multiple prompt patterns that all return the same tool.

    Args:
        mcp: FastMCP instance
        prompt_groups: Dict mapping descriptions to pattern lists
    """
    for description, patterns in prompt_groups.items():
        for pattern in patterns:

            def create_handler(pattern_val: str, desc: str):
                def prompt_handler():
                    return ["ecs_troubleshooting_tool"]

                # Create a valid function name from the pattern
                safe_name = (
                    pattern_val.replace(" ", "_")
                    .replace(".*", "any")
                    .replace("'", "")
                    .replace('"', "")
                )
                safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in safe_name)
                prompt_handler.__name__ = f"{safe_name}_prompt"
                prompt_handler.__doc__ = desc
                return prompt_handler

            mcp.prompt(pattern)(create_handler(pattern, description))


def register_module(mcp: FastMCP) -> None:
    """Register troubleshooting module tools and prompts with the MCP server."""

    @mcp.tool(
        name="ecs_troubleshooting_tool",
        annotations=None,
    )
    async def mcp_ecs_troubleshooting_tool(
        action: TroubleshootingAction = "get_ecs_troubleshooting_guidance",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        ECS troubleshooting tool with multiple diagnostic actions.

        This tool provides access to all ECS troubleshooting operations through a single interface.
        Use the 'action' parameter to specify which troubleshooting operation to perform.

        ## Available Actions and Parameters:

        ### 1. get_ecs_troubleshooting_guidance
        Initial assessment and data collection
        - Required: cluster_name
        - Optional: service_name (Name of the ECS service to troubleshoot),
                   symptoms_description (Description of symptoms experienced by the user)
        - Example: action="get_ecs_troubleshooting_guidance",
                   parameters={"cluster_name": "my-cluster", "service_name": "my-service",
                               "symptoms_description": "ALB returning 503 errors"}

        ### 2. fetch_cloudformation_status
        Infrastructure-level diagnostics for CloudFormation stacks
        - Required: stack_id
        - Example: action="fetch_cloudformation_status", parameters={"stack_id": "my-app-stack"}

        ### 3. fetch_service_events
        Service-level diagnostics for ECS services
        - Required: cluster_name, service_name
        - Optional: time_window (Time window in seconds to look back for events (default: 3600)),
                    start_time (Explicit start time for the analysis window (UTC, takes
                    precedence over time_window if provided)),
                    end_time (Explicit end time for the analysis window (UTC, defaults to
                    current time if not provided))
        - Example: action="fetch_service_events",
                   parameters={"cluster_name": "my-cluster",
                               "service_name": "my-service",
                               "time_window": 7200}

        ### 4. fetch_task_failures
        Task-level diagnostics for ECS task failures
        - Required: cluster_name
        - Optional: time_window (Time window in seconds to look back for failures (default: 3600)),
                    start_time (Explicit start time for the analysis window (UTC, takes
                    precedence over time_window if provided)),
                    end_time (Explicit end time for the analysis window (UTC, defaults to
                    current time if not provided))
        - Example: action="fetch_task_failures",
                   parameters={"cluster_name": "my-cluster",
                               "time_window": 3600}

        ### 5. fetch_task_logs
        Application-level diagnostics through CloudWatch logs
        - Required: cluster_name
        - Optional: task_id (Specific task ID to retrieve logs for),
                    time_window (Time window in seconds to look back for logs (default: 3600)),
                    filter_pattern (CloudWatch logs filter pattern),
                    start_time (Explicit start time for the analysis window (UTC, takes
                    precedence over time_window if provided)),
                    end_time (Explicit end time for the analysis window (UTC, defaults to
                    current time if not provided))
        - Example: action="fetch_task_logs",
                   parameters={"cluster_name": "my-cluster",
                               "filter_pattern": "ERROR",
                               "time_window": 1800}

        ### 6. detect_image_pull_failures
        Specialized tool for detecting container image pull failures
        - Required: None (but at least one valid parameter combination must be provided)
        - Valid combinations: cluster_name+service_name, cluster_name+task_id, stack_name,
          family_prefix
        - Optional: cluster_name, service_name, stack_name, family_prefix, task_id
        - Example: action="detect_image_pull_failures",
                   parameters={"cluster_name": "my-cluster", "service_name": "my-service"}

        ### 7. fetch_network_configuration
        Network-level diagnostics for ECS deployments
        - Required: None (all parameters are optional)
        - Optional: vpc_id (Specific VPC ID to analyze), cluster_name (Specific ECS cluster name)
        - Example: action="fetch_network_configuration",
                   parameters={"vpc_id": "vpc-12345678", "cluster_name": "my-cluster"}

        ## Resource Discovery:
        If you don't know the cluster or service names, use `ecs_resource_management` tool first:

        # List all clusters
        ecs_resource_management(api_operation="ListClusters")

        # List services in a cluster
        ecs_resource_management(api_operation="ListServices", api_params={"cluster": "my-cluster"})

        # Get detailed cluster information
        ecs_resource_management(api_operation="DescribeClusters",
                               api_params={"clusters": ["my-cluster"]})

        ## Quick Usage Examples:
        ```
        # Initial assessment and data collection
        action: "get_ecs_troubleshooting_guidance"
        parameters: {"cluster_name": "my-cluster",
                    "symptoms_description": "ALB returning 503 errors"}

        # Infrastructure-level diagnostics for CloudFormation stacks
        action: "fetch_cloudformation_status"
        parameters: {"stack_id": "my-app-stack"}

        # Service-level diagnostics for ECS services
        action: "fetch_service_events"
        parameters: {"cluster_name": "my-cluster",
                    "service_name": "my-service",
                    "time_window": 7200}

        # Task-level diagnostics for ECS task failures
        action: "fetch_task_failures"
        parameters: {"cluster_name": "my-cluster",
                    "time_window": 3600}

        # Application-level diagnostics through CloudWatch logs
        action: "fetch_task_logs"
        parameters: {"cluster_name": "my-cluster",
                    "filter_pattern": "ERROR",
                    "time_window": 1800}

        # Specialized tool for detecting container image pull failures
        action: "detect_image_pull_failures"
        parameters: {"cluster_name": "my-cluster", "service_name": "my-service"}

        # Network-level diagnostics for ECS deployments
        action: "fetch_network_configuration"
        parameters: {"vpc_id": "vpc-12345678", "cluster_name": "my-cluster"}
        ```

        Parameters:
            action: The troubleshooting action to perform (see available actions above)
            parameters: Action-specific parameters (see parameter specifications above)

        Returns:
            Results from the selected troubleshooting action
        """
        # Initialize default parameters if None
        if parameters is None:
            parameters = {}

        return await ecs_troubleshooting_tool(action, parameters)

    # Define prompt groups for bulk registration
    prompt_groups = {
        "General ECS troubleshooting": [
            "troubleshoot ecs",
            "ecs deployment failed",
            "diagnose ecs",
            "fix ecs deployment",
            "help debug ecs",
        ],
        "Task and container issues": [
            "ecs tasks failing",
            "container is failing",
            "service is failing",
        ],
        "Infrastructure issues": [
            "cloudformation stack failed",
            "stack .* is broken",
            "fix .* stack",
            "failed stack .*",
            "stack .* failed",
            ".*-stack.* is broken",
            ".*-stack.* failed",
            "help me fix .*-stack.*",
            "why did my stack fail",
        ],
        "Image pull failures": [
            "image pull failure",
            "container image not found",
            "imagepullbackoff",
            "can't pull image",
            "invalid container image",
        ],
        "Network and connectivity": [
            "network issues",
            "security group issues",
            "connectivity issues",
            "unable to connect",
            "service unreachable",
        ],
        "Load balancer issues": [
            "alb not working",
            "load balancer not working",
            "alb url not working",
            "healthcheck failing",
            "target group",
            "404 not found",
        ],
        "Logs and monitoring": ["check ecs logs", "ecs service events"],
        "Generic deployment issues": [
            "fix my deployment",
            "deployment issues",
            "what's wrong with my stack",
            "deployment is broken",
            "app won't deploy",
        ],
    }

    # Register all prompts with bulk registration
    register_troubleshooting_prompts(mcp, prompt_groups)
