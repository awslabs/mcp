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

from mcp.server.fastmcp import FastMCP

from awslabs.ecs_mcp_server.modules import (
    containerize,
    delete,
    deployment_status,
    infrastructure,
    resource_management,
    troubleshooting,
    security_analysis,
)
from awslabs.ecs_mcp_server.utils.config import get_config
from awslabs.ecs_mcp_server.utils.security import (
    PERMISSION_WRITE,
    secure_tool,
)

# Configure logging
log_level = os.environ.get("FASTMCP_LOG_LEVEL", "INFO")
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_file = os.environ.get("FASTMCP_LOG_FILE")

# Set up basic configuration
logging.basicConfig(
    level=log_level,
    format=log_format,
)

# Add file handler if log file path is specified
if log_file:
    try:
        # Create directory for log file if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Add file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
        logging.info(f"Logging to file: {log_file}")
    except Exception as e:
        logging.error(f"Failed to set up log file {log_file}: {e}")

logger = logging.getLogger("ecs-mcp-server")

# Load configuration
config = get_config()

# Create the MCP server
mcp = FastMCP(
    name="AWS ECS MCP Server",
    instructions="""Use this server to containerize and deploy web applications to AWS ECS.

WORKFLOW:
1. containerize_app:
   - Get guidance on how to containerize your web application
   - Learn best practices for Dockerfile creation
   - Get recommendations for container tools and architecture

2. create_ecs_infrastructure:
   - Create the necessary AWS infrastructure for ECS deployment
   - Set up VPC, subnets, security groups, and IAM roles
   - Configure ECS Cluster, ECS Task Definitions, and ECS Services

3. get_deployment_status:
   - Check the status of your ECS deployment
   - Get the ALB URL to access your application
   - Monitor the health of your ECS Service

4. ecs_security_analysis_tool:
   - List available ECS clusters for user selection
   - Interactive cluster selection with guided analysis options
   - Perform security analysis of a SPECIFIC user-selected cluster
   - Generate detailed security reports for the selected cluster
   - Check compliance against security best practices for one cluster
   - Get filtered security recommendations by severity or category
   - IMPORTANT: Always let the user choose which cluster to analyze
   
   Example prompts customers can use:
   • "Analyze my ECS security"
   • "Check security issues in my cluster"
   • "Show me security vulnerabilities"
   • "Generate a security report"
   • "What clusters do I have?"
   • "Is my ECS secure?"
   • "Fix security problems"
   • "Check compliance"

IMPORTANT:
- Make sure your application has a clear entry point
- Ensure all dependencies are properly defined in requirements.txt, package.json, etc.
- For containerization, your application should listen on a configurable port
- AWS credentials must be properly configured with appropriate permissions
- Set ALLOW_WRITE=true to enable infrastructure creation and deletion
- Set ALLOW_SENSITIVE_DATA=true to enable access to logs and detailed resource information
""",
)

# Apply security wrappers to API functions
# Write operations
infrastructure.create_infrastructure = secure_tool(
    config, PERMISSION_WRITE, "create_ecs_infrastructure"
)(infrastructure.create_infrastructure)
delete.delete_infrastructure = secure_tool(config, PERMISSION_WRITE, "delete_ecs_infrastructure")(
    delete.delete_infrastructure
)

# Register all modules
containerize.register_module(mcp)  # type: ignore[arg-type]
infrastructure.register_module(mcp)  # type: ignore[arg-type]
deployment_status.register_module(mcp)  # type: ignore[arg-type]
resource_management.register_module(mcp)  # type: ignore[arg-type]
troubleshooting.register_module(mcp)  # type: ignore[arg-type]
security_analysis.register_module(mcp)  # type: ignore[arg-type]
delete.register_module(mcp)  # type: ignore[arg-type]


def main() -> None:
    """Main entry point for the ECS MCP Server."""
    try:
        # Start the server
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
