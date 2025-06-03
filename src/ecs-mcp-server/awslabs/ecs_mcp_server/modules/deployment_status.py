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
Deployment Status module for ECS MCP Server.
This module provides tools to check the status of ECS deployments.
"""

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.status import get_deployment_status


def register_module(mcp: FastMCP) -> None:
    """Register deployment status module tools and prompts with the MCP server."""

    @mcp.tool(name="get_deployment_status", annotations=None)
    async def mcp_get_deployment_status(
        app_name: str = Field(
            ...,
            description="Name of the application",
        ),
        cluster_name: Optional[str] = Field(
            default=None,
            description="Name of the ECS cluster",
        ),
        stack_name: Optional[str] = Field(
            default=None,
            description=(
                "Name of the CloudFormation stack "
                "(optional, defaults to {app_name}-ecs-infrastructure)"
            ),
        ),
        service_name: Optional[str] = Field(
            default=None,
            description="Name of the ECS service (optional, defaults to {app_name}-service)",
        ),
    ) -> Dict[str, Any]:
        """
        Gets the status of an ECS deployment and returns the ALB URL.

        This tool checks the status of your ECS deployment and provides information
        about the service, tasks, and the Application Load Balancer URL for accessing
        your application.

        USAGE INSTRUCTIONS:
        1. Provide the name of your application
        2. Optionally specify the cluster name if different from the application name
        3. Optionally specify the stack name if different from the default naming convention
        4. Optionally specify the service name if different from the default naming pattern
        5. The tool will return the deployment status and access URL once the deployment
           is complete.

        Poll this tool every 30 seconds till the status is active.

        The status information includes:
        - Service status (active, draining, etc.)
        - Running task count
        - Desired task count
        - Application Load Balancer URL
        - Recent deployment events
        - Health check status
        - Custom domain and HTTPS setup guidance (when deployment is complete)

        Parameters:
            app_name: Name of the application
            cluster_name: Name of the ECS cluster (optional, defaults to app_name)
            stack_name: Name of the CloudFormation stack
                       (optional, defaults to {app_name}-ecs-infrastructure)
            service_name: Name of the ECS service (optional, defaults to {app_name}-service)

        Returns:
            Dictionary containing deployment status and ALB URL
        """
        return await get_deployment_status(app_name, cluster_name, stack_name, service_name)
