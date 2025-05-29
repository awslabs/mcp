"""
Resource Management module for ECS MCP Server.
This module provides tools and prompts for managing ECS resources.
"""

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.resource_management import ecs_resource_management


def register_module(mcp: FastMCP) -> None:
    """Register resource management module tools and prompts with the MCP server."""

    @mcp.tool(name="ecs_resource_management", annotations=None)
    async def mcp_ecs_resource_management(
        action: str = Field(
            ...,
            description="Action to perform (list, describe)",
        ),
        resource_type: str = Field(
            ...,
            description=(
                "Type of resource (cluster, service, task, task_definition, "
                "container_instance, capacity_provider)"
            ),
        ),
        identifier: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Read-only tool for managing ECS resources.

        This tool provides a consistent interface to list and describe various ECS resources.

        USAGE EXAMPLES:
        - List all clusters: ecs_resource_management("list", "cluster")
        - Describe a cluster: ecs_resource_management("describe", "cluster", "my-cluster")
        - List services in cluster: ecs_resource_management("list", "service",
          filters={"cluster": "my-cluster"})
        - List tasks by status: ecs_resource_management("list", "task",
          filters={"cluster": "my-cluster", "status": "RUNNING"})
        - Describe a task: ecs_resource_management("describe", "task", "task-id",
          filters={"cluster": "my-cluster"})
        - List task definitions: ecs_resource_management("list", "task_definition",
          filters={"family": "nginx"})
        - Describe a task definition: ecs_resource_management("describe", "task_definition",
          "family:revision")

        Parameters:
            action: Action to perform (list, describe)
            resource_type: Type of resource (cluster, service, task, task_definition,
                          container_instance, capacity_provider)
            identifier: Resource identifier (name or ARN) for describe actions (optional)
            filters: Filters for list operations (optional)

        Returns:
            Dictionary containing the requested ECS resources
        """
        return await ecs_resource_management(action, resource_type, identifier, filters)

    # Prompt patterns for resource management
    @mcp.prompt("list ecs resources")
    def list_ecs_resources_prompt():
        """User wants to list ECS resources"""
        return ["ecs_resource_management"]

    @mcp.prompt("show ecs clusters")
    def show_ecs_clusters_prompt():
        """User wants to see ECS clusters"""
        return ["ecs_resource_management"]

    @mcp.prompt("describe ecs service")
    def describe_ecs_service_prompt():
        """User wants to describe an ECS service"""
        return ["ecs_resource_management"]

    @mcp.prompt("view ecs tasks")
    def view_ecs_tasks_prompt():
        """User wants to view ECS tasks"""
        return ["ecs_resource_management"]

    @mcp.prompt("check task definitions")
    def check_task_definitions_prompt():
        """User wants to check ECS task definitions"""
        return ["ecs_resource_management"]

    @mcp.prompt("show running containers")
    def show_running_containers_prompt():
        """User wants to see running containers in ECS"""
        return ["ecs_resource_management"]

    @mcp.prompt("view ecs resources")
    def view_ecs_resources_prompt():
        """User wants to view ECS resources"""
        return ["ecs_resource_management"]

    @mcp.prompt("inspect ecs")
    def inspect_ecs_prompt():
        """User wants to inspect ECS resources"""
        return ["ecs_resource_management"]

    @mcp.prompt("check ecs status")
    def check_ecs_status_prompt():
        """User wants to check ECS status"""
        return ["ecs_resource_management"]
