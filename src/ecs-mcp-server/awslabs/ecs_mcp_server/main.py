#!/usr/bin/env python3
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
AWS ECS MCP Server - Main entry point
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, Tuple

from fastmcp import FastMCP

from awslabs.ecs_mcp_server.modules import (
    aws_knowledge_proxy,
    containerize,
    delete,
    express,
    infrastructure,
    resource_management,
    troubleshooting,
)
from awslabs.ecs_mcp_server.utils.config import get_config
from awslabs.ecs_mcp_server.utils.security import (
    PERMISSION_WRITE,
    secure_tool,
)


def _setup_logging() -> logging.Logger:
    """Configure logging for the server."""
    log_level = os.environ.get("FASTMCP_LOG_LEVEL", "INFO")
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file = os.environ.get("FASTMCP_LOG_FILE")

    logging.basicConfig(level=log_level, format=log_format)

    if log_file:
        try:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(file_handler)
            logging.info(f"Logging to file: {log_file}")
        except Exception as e:
            logging.error(f"Failed to set up log file {log_file}: {e}")

    return logging.getLogger("ecs-mcp-server")


@asynccontextmanager
async def server_lifespan(server):
    """
    Server lifespan context manager for initialization and cleanup.

    Provides safe access to async server methods during startup for
    operations like tool transformations.
    """
    logger = logging.getLogger("ecs-mcp-server")
    logger.info("Server initializing")

    # Safe async operations can be performed here
    await aws_knowledge_proxy.apply_tool_transformations(server)

    logger.info("Server ready")
    yield
    logger.info("Server shutting down")


def _create_ecs_mcp_server() -> Tuple[FastMCP, Dict[str, Any]]:
    """Create and configure the MCP server."""
    config = get_config()

    mcp = FastMCP(
        name="AWS ECS MCP Server",
        lifespan=server_lifespan,
        instructions="""Use this server to containerize and deploy web applications to AWS ECS \
using Express Mode.

        DEPLOYMENT WORKFLOW with EXPRESS MODE:
        1. containerize_app(app_path, port)
        - Creates Dockerfile for your application

        2. build_and_push_image_to_ecr(app_name, app_path)
        - app_name must be unique for each application
        - Creates ECR repository via CloudFormation using app_name
        - Builds Docker image and pushes to ECR
        - Returns full_image_uri to use in deployment

        3. validate_ecs_express_mode_prerequisites(image_uri)
        - Validates IAM roles (checks default names if not provided)
        - Verifies image exists in ECR

        4. Deploy with ecs_resource_management - CreateExpressGatewayService:

        Minimal deployment:
        ecs_resource_management(
            api_operation="CreateExpressGatewayService",
            api_params={
                "primaryContainer": {"image": full_image_uri},
                "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
                "infrastructureRoleArn": (
                    "arn:aws:iam::ACCOUNT:role/ecsInfrastructureRoleForExpressServices"
                )
            }
        )

        Or with more configuration options:
        ecs_resource_management(
            api_operation="CreateExpressGatewayService",
            api_params={
                "serviceName": "my-api",
                "cluster": "production",
                "primaryContainer": {
                    "image": full_image_uri,
                    "containerPort": 8080,
                    "environment": [
                        {"name": "NODE_ENV", "value": "production"}
                    ]
                },
                "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
                "infrastructureRoleArn": (
                    "arn:aws:iam::ACCOUNT:role/ecsInfrastructureRoleForExpressServices"
                ),
                "cpu": "1024",
                "memory": "2048",
                "scalingTarget": {
                    "minTaskCount": 2,
                    "maxTaskCount": 10,
                    "autoScalingMetric": "CPUUtilization",
                    "autoScalingTargetValue": 70
                },
                "healthCheckPath": "/health",
                "tags": [
                    {"key": "Environment", "value": "production"}
                ]
            }
        )

        5. Wait for service to be ready (optional but recommended):
        wait_for_service_ready(
            cluster="my-cluster",
            service_name="my-service"
        )

        6. Check status and get application URL:

        First, describe the service to get its status and URL:
        ecs_resource_management(
            api_operation="DescribeExpressGatewayService",
            api_params={"serviceArn": service_arn}
        )

        IMPORTANT: After the CreateExpressGatewayService or \
DescribeExpressGatewayService commands complete:
        - Present the customer with a summary of the deployed configuration options
        - Extract the application URL from the response and explicitly inform the user: \
"Once the service is up and running, your application will be accessible at: <URL>"

        EXPRESS MODE FEATURES:
        - Auto-provisions Application Load Balancer, target groups, security groups
        - Built-in HTTPS with custom domain (https://service.ecs.region.on.aws)
        - Configurable CPU/memory (256-4096 vCPU units, 512-8192 MB)
        - Auto-scaling with min/max task counts and target metrics
        - Health monitoring with customizable health check paths
        - No CloudFormation templates needed for ECS resources

        LEARN MORE:
        Use the integrated AWS Knowledge MCP tools to access up-to-date documentation:
        - Search: aws_knowledge_aws___search_documentation with "ECS Express Mode"
        - Read docs: aws_knowledge_aws___read_documentation with Express Mode URLs
        - Get recommendations: aws_knowledge_aws___recommend for related topics
        For detailed API parameters, search for "CreateExpressGatewayService API reference"

        IMPORTANT:
        - Set ALLOW_WRITE=true to enable infrastructure creation and deletion
        - Set ALLOW_SENSITIVE_DATA=true to enable access to logs and detailed \
resource information
        - AWS credentials must be properly configured
        - Application should listen on a configurable port
        - Use the integrated Knowledge MCP Tools to search and read up-to-date \
AWS documentation including ECS's newest feature launches
 """,
    )

    # Apply security wrappers to API functions
    # Write operations
    infrastructure.create_infrastructure = secure_tool(
        config, PERMISSION_WRITE, "create_ecs_infrastructure"
    )(infrastructure.create_infrastructure)
    delete.delete_infrastructure = secure_tool(
        config, PERMISSION_WRITE, "delete_ecs_infrastructure"
    )(delete.delete_infrastructure)
    express.build_and_push_image_to_ecr = secure_tool(
        config, PERMISSION_WRITE, "build_and_push_image_to_ecr"
    )(express.build_and_push_image_to_ecr)
    express.delete_app = secure_tool(config, PERMISSION_WRITE, "delete_app")(express.delete_app)

    # Register all modules
    containerize.register_module(mcp)
    express.register_module(mcp)
    resource_management.register_module(mcp)
    troubleshooting.register_module(mcp)

    # Register all proxies
    aws_knowledge_proxy.register_proxy(mcp)

    return mcp, config


def main() -> None:
    """Main entry point for the ECS MCP Server."""
    try:
        # Start the server
        mcp, config = _create_ecs_mcp_server()
        logger = _setup_logging()

        logger.info("Server started")
        logger.info(f"Write operations enabled: {config.get('allow-write', False)}")
        logger.info(f"Sensitive data access enabled: {config.get('allow-sensitive-data', False)}")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
