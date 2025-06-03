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
Containerize module for ECS MCP Server.
This module provides tools and prompts for containerizing web applications.
"""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.containerize import containerize_app


def register_module(mcp: FastMCP) -> None:
    """Register containerize module tools and prompts with the MCP server."""

    @mcp.tool(name="containerize_app", annotations=None)
    async def mcp_containerize_app(
        app_path: str = Field(
            ...,
            description="Absolute file path to the web application directory",
        ),
        port: int = Field(
            ...,
            description="Port the application listens on",
        ),
    ) -> Dict[str, Any]:
        """
        Start here if a user wants to run their application locally or deploy an app to the cloud.
        Provides guidance for containerizing a web application.

        This tool provides guidance on how to build Docker images for web applications,
        including recommendations for base images, build tools, and architecture choices.

        USAGE INSTRUCTIONS:
        1. Run this tool to get guidance on how to configure your application for ECS.
        2. Follow the steps generated from the tool.
        3. Proceed to create_ecs_infrastructure tool.

        The guidance includes:
        - Example Dockerfile content
        - Example docker-compose.yml content
        - Build commands for different container tools
        - Architecture recommendations
        - Troubleshooting tips

        Parameters:
            app_path: Path to the web application directory
            port: Port the application listens on

        Returns:
            Dictionary containing containerization guidance
        """
        return await containerize_app(app_path, port)

    # Prompt patterns for containerization
    @mcp.prompt("dockerize")
    def dockerize_prompt():
        """User wants to containerize an application"""
        return ["containerize_app"]

    @mcp.prompt("containerize")
    def containerize_prompt():
        """User wants to containerize an application"""
        return ["containerize_app"]

    @mcp.prompt("docker container")
    def docker_container_prompt():
        """User wants to create a Docker container"""
        return ["containerize_app"]

    @mcp.prompt("put in container")
    def put_in_container_prompt():
        """User wants to containerize an application"""
        return ["containerize_app"]

    # Combined prompts
    @mcp.prompt("containerize and deploy")
    def containerize_and_deploy_prompt():
        """User wants to containerize and deploy an application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("docker and deploy")
    def docker_and_deploy_prompt():
        """User wants to containerize and deploy an application"""
        return ["containerize_app", "create_ecs_infrastructure"]
