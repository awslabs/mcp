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
Infrastructure module for ECS MCP Server.
This module provides tools and prompts for creating ECS infrastructure.
"""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from awslabs.ecs_mcp_server.api.infrastructure import create_infrastructure


def register_module(mcp: FastMCP) -> None:
    """Register infrastructure module tools and prompts with the MCP server."""

    @mcp.tool(name="create_ecs_infrastructure")
    async def mcp_create_ecs_infrastructure(
        app_name: str = Field(
            ...,
            description="Name of the application",
        ),
        app_path: str = Field(
            ...,
            description="Absolute file path to the web application directory",
        ),
        force_deploy: bool = Field(
            default=False,
            description=(
                "Set to True ONLY if you have Docker installed and running, and you agree "
                "to let the server build and deploy your image to ECR, as well as deploy "
                "ECS infrastructure for you in CloudFormation. If False, template files "
                "will be generated locally for your review."
            ),
        ),
        deployment_step: Optional[int] = Field(
            default=None,
            description=(
                "Which deployment step to execute (1, 2, or 3) when force_deploy is True. "
                "1: Create CFN files and deploy ECR to CFN, "
                "2: Build and deploy Docker image, "
                "3: Deploy ECS to CFN. "
                "You must specify to use force-deploy and it must be done sequentially "
                "to prevent timeouts."
            ),
        ),
        vpc_id: Optional[str] = Field(
            default=None,
            description="VPC ID for deployment (optional, will use default if not provided)",
        ),
        subnet_ids: Optional[List[str]] = None,
        route_table_ids: Optional[List[str]] = None,
        cpu: Optional[int] = Field(
            default=None,
            description="CPU units for the task (e.g., 256, 512, 1024)",
        ),
        memory: Optional[int] = Field(
            default=None,
            description="Memory (MB) for the task (e.g., 512, 1024, 2048)",
        ),
        desired_count: Optional[int] = Field(
            default=None,
            description="Desired number of tasks",
        ),
        container_port: Optional[int] = Field(
            default=None,
            description="Port the container listens on",
        ),
        health_check_path: Optional[str] = Field(
            default=None,
            description="Path for ALB health checks",
        ),
    ) -> Dict[str, Any]:
        """
        Creates ECS infrastructure using CloudFormation.

        This tool sets up the necessary AWS infrastructure for deploying applications to ECS.
        It creates or uses an existing VPC, sets up security groups, IAM roles, and configures
        the ECS cluster, task definitions, and services. Deployment is asynchronous, poll the
        get_deployment_status tool every 30 seconds after successful invocation of this.

        USAGE INSTRUCTIONS:
        1. Provide a name for your application
        2. Provide the path to your web application directory
        3. Decide whether to use force_deploy:
           - If False (default): Template files will be generated locally for your review
           - If True: Docker image will be built and pushed to ECR, and CloudFormation stacks
             will be deployed
           - ENSURE you get user permission to deploy and inform that this is only for
             non-production applications.
        4. If force_deploy is True, you can optionally specify a deployment_step:
           - Step 1: Create CFN files and deploy ECR to CloudFormation
           - Step 2: Build and deploy Docker image to ECR
           - Step 3: Deploy ECS infrastructure to CloudFormation
           - If no step is specified, all steps will be executed in sequence
        5. Optionally specify VPC and subnet IDs if you want to use existing resources
        6. Configure CPU, memory, and scaling options as needed

        The created infrastructure includes:
        - Security groups
        - IAM roles and policies
        - ECS cluster
        - Task definition template
        - Service configuration
        - Application Load Balancer

        Parameters:
            app_name: Name of the application
            app_path: Path to the web application directory
            force_deploy: Whether to build and deploy the infrastructure or just generate templates
            deployment_step: Which deployment step to execute (1, 2, or 3) when force_deploy is True
            vpc_id: VPC ID for deployment
            subnet_ids: List of subnet IDs for deployment
            route_table_ids: List of route table IDs for S3 Gateway endpoint association
            cpu: CPU units for the task (e.g., 256, 512, 1024)
            memory: Memory (MB) for the task (e.g., 512, 1024, 2048)
            desired_count: Desired number of tasks
            container_port: Port the container listens on
            health_check_path: Path for ALB health checks

        Returns:
            Dictionary containing infrastructure details or template paths
        """
        return await create_infrastructure(
            app_name=app_name,
            app_path=app_path,
            force_deploy=force_deploy,
            deployment_step=deployment_step,
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
            route_table_ids=route_table_ids,
            cpu=cpu,
            memory=memory,
            desired_count=desired_count,
            container_port=container_port,
            health_check_path=health_check_path,
        )

    # Prompt patterns for deployment
    @mcp.prompt("deploy to aws")
    def deploy_to_aws_prompt():
        """User wants to deploy an application to AWS"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("deploy to cloud")
    def deploy_to_cloud_prompt():
        """User wants to deploy an application to the cloud"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("deploy to ecs")
    def deploy_to_ecs_prompt():
        """User wants to deploy an application to AWS ECS"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("ship to cloud")
    def ship_to_cloud_prompt():
        """User wants to deploy an application to the cloud"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("put on the web")
    def put_on_web_prompt():
        """User wants to make an application accessible online"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("host online")
    def host_online_prompt():
        """User wants to host an application online"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("make live")
    def make_live_prompt():
        """User wants to make an application live"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("launch online")
    def launch_online_prompt():
        """User wants to launch an application online"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("get running on the web")
    def get_running_on_web_prompt():
        """User wants to make an application accessible on the web"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("make accessible")
    def make_accessible_prompt():
        """User wants to make an application accessible online"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("ship it")
    def ship_it_prompt():
        """User wants to ship/deploy their application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("deploy flask")
    def deploy_flask_prompt():
        """User wants to deploy a Flask application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("deploy django")
    def deploy_django_prompt():
        """User wants to deploy a Django application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("deploy react")
    def deploy_react_prompt():
        """User wants to deploy a React application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("deploy express")
    def deploy_express_prompt():
        """User wants to deploy an Express.js application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("deploy node")
    def deploy_node_prompt():
        """User wants to deploy a Node.js application"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("push to prod")
    def push_to_prod_prompt():
        """User wants to deploy an application to production"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("get this online")
    def get_this_online_prompt():
        """User wants to make an application accessible online"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("make this public")
    def make_this_public_prompt():
        """User wants to make an application publicly accessible"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("put this on aws")
    def put_this_on_aws_prompt():
        """User wants to deploy an application to AWS"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("can people access this")
    def can_people_access_this_prompt():
        """User wants to make an application accessible to others"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("how do i share this app")
    def how_do_i_share_this_app_prompt():
        """User wants to make an application accessible to others"""
        return ["containerize_app", "create_ecs_infrastructure"]

    @mcp.prompt("make accessible online")
    def make_accessible_online_prompt():
        """User wants to make an application accessible online"""
        return ["containerize_app", "create_ecs_infrastructure"]
