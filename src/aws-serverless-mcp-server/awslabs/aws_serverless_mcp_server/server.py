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

"""Serverless MCP Server implementation."""

import argparse
import os
import sys
from awslabs.aws_serverless_mcp_server import __version__
from awslabs.aws_serverless_mcp_server.resources import (
    handle_deployment_details,
    handle_deployments_list,
    handle_template_details,
    handle_template_list,
)
from awslabs.aws_serverless_mcp_server.tools.guidance import (
    DeployServerlessAppHelpTool,
    GetIaCGuidanceTool,
    GetLambdaEventSchemasTool,
    GetLambdaGuidanceTool,
    GetServerlessTemplatesTool,
)
from awslabs.aws_serverless_mcp_server.tools.sam import (
    SamBuildTool,
    SamDeployTool,
    SamInitTool,
    SamLocalInvokeTool,
    SamLogsTool,
)
from awslabs.aws_serverless_mcp_server.tools.schemas import (
    DescribeSchemaTool,
    ListRegistriesTool,
    SearchSchemaTool,
)
from awslabs.aws_serverless_mcp_server.tools.webapps import (
    ConfigureDomainTool,
    DeployWebAppTool,
    GetMetricsTool,
    UpdateFrontendTool,
    WebappDeploymentHelpTool,
)
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from awslabs.aws_serverless_mcp_server.utils.const import AWS_REGION, DEPLOYMENT_STATUS_DIR
from loguru import logger
from mcp.server.fastmcp import FastMCP
from typing import Any, Dict


# Initialize boto3 client
schemas_client = get_aws_client('schemas', AWS_REGION)

mcp = FastMCP(
    'awslabs.aws-serverless-mcp-server',
    instructions="""AWS Serverless MCP

    The AWS Serverless Model Context Protocol (MCP) Server is an open-source tool that combines
    AI assistance with serverless expertise to streamline how developers build serverless applications.
    It provides contextual guidance specific to serverless development, helping developers make informed
    decisions about architecture, implementation, and deployment throughout the entire application development
    lifecycle. With AWS Serverless MCP, developers can build reliable, efficient, and production-ready serverless
    applications with confidence.

    ## Features
    1. Serverless Application Lifecycle
    - Intialize, build, and deploy Serverless Application Model (SAM) applications with SAM CLI
    - Test Lambda functions locally and remotely
    2. Web Application Deployment & Management
    - Deploy fullstack, frontend, and backend web applications onto AWS Serverless using Lambda Web Adapter.
    - Update frontend assets and optionally invaliate CloudFront caches
    - Create custom domain names, including certificate and DNS setup.
    3. Observability
    - Retrieve and logs and metrics of serverless resources
    4. Guidance, Templates, and Deployment Help
    - Provides guidance on AWS Lambda use-cases, selecting an IaC framework, and deployment process onto AWS Serverless
    - Provides sample SAM templates for different serverless application types from [Serverless Land](https://serverlessland.com/)
    - Provides schema types for different Lambda event sources and runtimes

    ## Usage Notes
    - By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations and public resource creation.
    - Access to sensitive data (Lambda function and API GW logs) requires the `--allow-sensitive-data-access` flag.

    ## Prerequisites
    1. Have an AWS account
    2. Configure AWS CLI with your credentials and profile. Set AWS_PROFILE environment variable if not using default
    3. Set AWS_REGION environment variable if not using default
    4. Install AWS CLI and SAM CLI
    """,
    dependencies=['pydantic', 'boto3', 'loguru'],
)


# Template resources
@mcp.resource(
    'template://list',
    description="""List of SAM deployment templates that can be used with the deploy_webapp_tool.
                Includes frontend, backend, and fullstack templates. """,
)
def template_list() -> Dict[str, Any]:
    """Retrieves a list of all available deployment templates.

    Returns:
        Dict[str, Any]: A dictionary containing the list of available templates.
    """
    return handle_template_list()


@mcp.resource(
    'template://{template_name}',
    description="""Returns details of a deployment template including compatible frameworks,
                template schema, and example usage of the template""",
)
def template_details(template_name: str) -> Dict[str, Any]:
    """Retrieves detailed information about a specific deployment template.

    Args:
        template_name (str): The name of the template to retrieve details for.

    Returns:
        Dict[str, Any]: A dictionary containing the template details.
    """
    return handle_template_details(template_name)


# Deployment resources
@mcp.resource(
    'deployment://list', description='Lists CloudFormation deployments managed by this MCP server.'
)
async def deployment_list() -> Dict[str, Any]:
    """Asynchronously retrieves a list of all AWS deployments managed by the MCP server.

    Returns:
        Dict[str, Any]: A dictionary containing the list of deployments.
    """
    return await handle_deployments_list()


@mcp.resource(
    'deployment://{project_name}',
    description="""Returns details of a CloudFormation deployment managed by this MCP server, including
                deployment type, status, and stack outputs.""",
)
async def deployment_details(project_name: str) -> Dict[str, Any]:
    """Asynchronously retrieves detailed information about a specific deployment.

    Args:
        project_name (str): The name of the project deployment to retrieve details for.

    Returns:
        Dict[str, Any]: A dictionary containing the deployment details.
    """
    return await handle_deployment_details(project_name)


def main() -> int:
    """Entry point for the AWS Serverless MCP server.

    This function is called when the `awslabs.aws-serverless-mcp-server` command is run.
    It starts the MCP server and handles command-line arguments.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    os.makedirs(DEPLOYMENT_STATUS_DIR, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

    parser = argparse.ArgumentParser(description='AWS Serverless MCP Server')
    parser.add_argument(
        '--allow-write', action='store_true', help='Enables MCP tools that make write operations'
    )
    parser.add_argument(
        '--allow-sensitive-data-access',
        action='store_true',
        help='Returns sensitive data from tools (e.g. logs, environment variables)',
    )

    args = parser.parse_args()

    WebappDeploymentHelpTool(mcp)
    DeployServerlessAppHelpTool(mcp)
    GetIaCGuidanceTool(mcp)
    GetLambdaEventSchemasTool(mcp)
    GetLambdaGuidanceTool(mcp)
    GetServerlessTemplatesTool(mcp)

    SamBuildTool(mcp)
    SamDeployTool(mcp, args.allow_write)
    SamInitTool(mcp)
    SamLocalInvokeTool(mcp)
    SamLogsTool(mcp, args.allow_sensitive_data_access)

    ListRegistriesTool(mcp, schemas_client)
    SearchSchemaTool(mcp, schemas_client)
    DescribeSchemaTool(mcp, schemas_client)

    GetMetricsTool(mcp)
    ConfigureDomainTool(mcp)
    DeployWebAppTool(mcp, args.allow_write)
    UpdateFrontendTool(mcp)

    # Set AWS_EXECUTION_ENV to configure user agent of boto3. Setting it through an environment variable
    # because SAM CLI does not support setting user agents directly
    os.environ['AWS_EXECUTION_ENV'] = f'awslabs/mcp/aws-serverless-mcp-server/{__version__}'

    try:
        mcp.run()
        return 0
    except Exception as e:
        logger.error(f'Error starting AWS Serverless MCP server: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
