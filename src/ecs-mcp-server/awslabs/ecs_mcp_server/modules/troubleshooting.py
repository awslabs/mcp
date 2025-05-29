"""
Troubleshooting module for ECS MCP Server.
This module provides tools and prompts for troubleshooting ECS deployments.
"""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from awslabs.ecs_mcp_server.api.ecs_troubleshooting import (
    TROUBLESHOOTING_DOCS,
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
        description=TROUBLESHOOTING_DOCS,  # Dynamically generated documentation string
    )
    async def mcp_ecs_troubleshooting_tool(
        app_name: Optional[str] = None,
        action: TroubleshootingAction = "get_ecs_troubleshooting_guidance",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Initialize default parameters if None
        if parameters is None:
            parameters = {}

        return await ecs_troubleshooting_tool(app_name, action, parameters)

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
