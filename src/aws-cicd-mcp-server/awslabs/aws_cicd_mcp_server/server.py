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

"""AWS CI/CD MCP Server implementation."""

import sys
from awslabs.aws_cicd_mcp_server.core.common.config import FASTMCP_LOG_LEVEL
from loguru import logger
from mcp.server.fastmcp import FastMCP

# Configure logging
logger.remove()
logger.add(sys.stderr, level=FASTMCP_LOG_LEVEL)

# Create MCP server
mcp = FastMCP(
    'AWS CI/CD MCP Server for CodePipeline, CodeBuild, and CodeDeploy operations',
    dependencies=[
        'boto3',
        'botocore', 
        'pydantic',
        'loguru',
    ],
)

def _register_tools():
    """Lazy load and register tools to improve startup time."""
    from awslabs.aws_cicd_mcp_server.core.codepipeline import tools as pipeline_tools
    from awslabs.aws_cicd_mcp_server.core.codebuild import tools as build_tools
    from awslabs.aws_cicd_mcp_server.core.codedeploy import tools as deploy_tools
    
    # Register CodePipeline tools
    mcp.tool()(pipeline_tools.list_pipelines)
    mcp.tool()(pipeline_tools.get_pipeline_details)
    mcp.tool()(pipeline_tools.start_pipeline_execution)
    mcp.tool()(pipeline_tools.get_pipeline_execution_history)
    mcp.tool()(pipeline_tools.create_pipeline)
    mcp.tool()(pipeline_tools.update_pipeline)
    mcp.tool()(pipeline_tools.delete_pipeline)

    # Register CodeBuild tools  
    mcp.tool()(build_tools.list_projects)
    mcp.tool()(build_tools.get_project_details)
    mcp.tool()(build_tools.start_build)
    mcp.tool()(build_tools.get_build_logs)
    mcp.tool()(build_tools.create_project)
    mcp.tool()(build_tools.update_project)
    mcp.tool()(build_tools.delete_project)

    # Register CodeDeploy tools
    mcp.tool()(deploy_tools.list_applications)
    mcp.tool()(deploy_tools.get_application_details)
    mcp.tool()(deploy_tools.create_deployment)
    mcp.tool()(deploy_tools.get_deployment_status)
    mcp.tool()(deploy_tools.list_deployment_groups)
    mcp.tool()(deploy_tools.create_application)
    mcp.tool()(deploy_tools.create_deployment_group)
    mcp.tool()(deploy_tools.delete_application)

def main() -> None:
    """Run the MCP server."""
    _register_tools()
    mcp.run()

if __name__ == '__main__':
    main()
