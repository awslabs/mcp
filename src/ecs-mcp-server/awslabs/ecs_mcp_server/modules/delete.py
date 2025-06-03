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
Delete module for ECS MCP Server.
This module provides tools and prompts for deleting ECS infrastructure.
"""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.delete import delete_infrastructure


def register_module(mcp: FastMCP) -> None:
    """Register delete module tools and prompts with the MCP server."""

    @mcp.tool(name="delete_ecs_infrastructure")
    async def mcp_delete_ecs_infrastructure(
        app_name: str = Field(
            ...,
            description="Name of the application",
        ),
        ecr_template_path: str = Field(
            ...,
            description="Path to the ECR CloudFormation template file",
        ),
        ecs_template_path: str = Field(
            ...,
            description="Path to the ECS CloudFormation template file",
        ),
    ) -> Dict[str, Any]:
        """
        Deletes ECS infrastructure created by the ECS MCP Server.

        WARNING: This tool is not intended for production usage and is best suited for
        tearing down prototyped work done with the ECS MCP Server.

        This tool attempts to identify and delete CloudFormation stacks based on the
        provided app name and template files. It will scan the user's CloudFormation stacks,
        using the app name as a heuristic, and identify if the templates match the files
        provided in the input. It will only attempt to delete stacks if they are found and
        match the provided templates.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. Provide paths to the ECR and ECS CloudFormation template files
           - Templates will be compared to ensure they match the deployed stacks
        3. The tool will attempt to delete the stacks in the correct order (ECS first, then ECR)

        IMPORTANT:
        - This is a best-effort deletion
        - If a stack is in a transitional state (e.g., CREATE_IN_PROGRESS), it will be skipped
        - You may need to manually delete resources if the deletion fails

        Parameters:
            app_name: Name of the application
            ecr_template_path: Path to the ECR CloudFormation template file
            ecs_template_path: Path to the ECS CloudFormation template file

        Returns:
            Dictionary containing deletion results and guidance
        """
        return await delete_infrastructure(
            app_name=app_name,
            ecr_template_path=ecr_template_path,
            ecs_template_path=ecs_template_path,
        )

    # Prompt patterns for deletion
    @mcp.prompt("delete infrastructure")
    def delete_infrastructure_prompt():
        """User wants to delete an application infrastructure"""
        return ["delete_ecs_infrastructure"]

    @mcp.prompt("tear down")
    def tear_down_prompt():
        """User wants to tear down infrastructure"""
        return ["delete_ecs_infrastructure"]

    @mcp.prompt("remove deployment")
    def remove_deployment_prompt():
        """User wants to remove a deployment"""
        return ["delete_ecs_infrastructure"]

    @mcp.prompt("clean up resources")
    def clean_up_resources_prompt():
        """User wants to clean up resources"""
        return ["delete_ecs_infrastructure"]
