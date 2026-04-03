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
from awslabs.aws_serverless_mcp_server.tools.esm import (
    EsmDiagnosisTool,
    EsmGuidanceTool,
    EsmRecommendTool,
)
from awslabs.aws_serverless_mcp_server.tools.esm.secure_esm_guidance import SecureEsmGuidanceTool
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

    AUTOMATIC TOOL SELECTION FOR STREAMING DATA SCENARIOS

    When user requests involve creating, setting up, or configuring:
    - Kafka clusters (MSK) with Lambda functions
    - Kinesis streams with Lambda consumers
    - DynamoDB streams with Lambda processing
    - SQS queues with Lambda functions
    - VPCs for streaming data processing
    - Real-time data processing infrastructure
    - Event-driven architectures with streaming

    → AUTOMATICALLY use esm_guidance tool for infrastructure setup
    → Use esm_optimize tool for performance tuning and cost optimization
    → Use esm_kafka_troubleshoot tool for Kafka connectivity issues
    → Generate complete SAM templates with VPC, security groups, IAM roles
    → CRITICAL: Always ask user for explicit confirmation before any deployment
    → Tools are read-only by default - they generate templates but do NOT deploy automatically

    KEYWORDS THAT TRIGGER STREAMING TOOLS:
    - "Kafka cluster", "MSK", "streaming data", "real-time processing"
    - "Kinesis stream", "DynamoDB stream", "SQS queue"
    - "Lambda consumer", "event processing", "message processing"
    - "VPC for streaming", "private subnets", "security groups"
    - "Event Source Mapping", "stream processing", "data pipeline"

    The AWS Serverless Model Context Protocol (MCP) Server is an open-source tool that combines
    AI assistance with serverless expertise to streamline how developers build serverless applications.
    It provides contextual guidance specific to serverless development, helping developers make informed
    decisions about architecture, implementation, and deployment throughout the entire application development
    lifecycle. With AWS Serverless MCP, developers can build reliable, efficient, and production-ready serverless
    applications with confidence.

    ## Features
    1. Serverless Application Lifecycle
    - Initialize, build, and deploy Serverless Application Model (SAM) applications with SAM CLI
    - Test Lambda functions locally and remotely
    2. Web Application Deployment & Management
    - Deploy fullstack, frontend, and backend web applications onto AWS Serverless using Lambda Web Adapter.
    - Update frontend assets and optionally invalidate CloudFront caches
    - Create custom domain names, including certificate and DNS setup.
    3. Observability
    - Retrieve and logs and metrics of serverless resources
    4. Guidance, Templates, and Deployment Help
    - Provides guidance on AWS Lambda use-cases, selecting an IaC framework, and deployment process onto AWS Serverless
    - Provides sample SAM templates for different serverless application types from [Serverless Land](https://serverlessland.com/)
    - Provides schema types for different Lambda event sources and runtimes
    5. Event Source Mapping (ESM) Tools
    - Setup, optimization, and troubleshooting for Lambda event sources
    - Support for Kafka, Kinesis, DynamoDB, and SQS event sources
    - Network configuration and performance optimization guidance

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
    'streaming://infrastructure-setup',
    description="""Streaming Infrastructure Setup: Automatically detects requests for creating Kafka clusters, Kinesis streams, DynamoDB streams, or SQS queues with Lambda functions. Handles VPC setup, security groups, IAM roles, and Event Source Mappings.""",
)
def streaming_infrastructure_setup() -> Dict[str, Any]:
    """Provides automatic detection for streaming infrastructure requests.

    Returns:
        Dict[str, Any]: Detection rules for streaming data processing scenarios.
    """
    return {
        'auto_detection_keywords': [
            'create kafka cluster',
            'create kinesis stream',
            'create dynamodb stream',
            'create sqs queue',
            'kafka with lambda',
            'kinesis with lambda',
            'stream processing',
            'real-time data processing',
            'event-driven architecture',
            'message processing',
            'VPC for streaming',
            'private subnets',
            'security groups for streaming',
            'MSK cluster',
            'lambda consumer',
            'event source mapping',
        ],
        'automatic_tool_selection': {
            'primary_tool': 'esm_guidance',
            'optimization_tool': 'esm_optimize',
            'troubleshooting_tool': 'esm_kafka_troubleshoot',
        },
        'generates': [
            'Complete SAM templates',
            'VPC and networking infrastructure',
            'Security groups and IAM roles',
            'Lambda functions with Event Source Mappings',
            'Deployment and testing scripts',
        ],
    }


@mcp.resource(
    'streaming://natural-language-detection',
    description="""Natural Language Detection: Automatically recognizes requests like 'create a Kafka cluster with Lambda', 'set up real-time data processing', 'build event-driven architecture'. Triggers appropriate streaming infrastructure tools without requiring technical keywords.""",
)
def natural_language_detection() -> Dict[str, Any]:
    """Provides natural language detection for streaming infrastructure requests.

    Returns:
        Dict[str, Any]: Natural language patterns and automatic tool selection.
    """
    return {
        'natural_language_patterns': [
            'create a kafka cluster',
            'set up kafka with lambda',
            'build real-time data processing',
            'create kinesis stream',
            'process dynamodb changes',
            'handle sqs messages',
            'event-driven architecture',
            'streaming data pipeline',
            'message queue processing',
            'VPC for streaming',
            'private subnets for kafka',
            'lambda consumer function',
            'process messages from queue',
        ],
        'automatic_workflow': [
            '1. Detect streaming intent → Auto-select esm_guidance tool',
            '2. Generate complete infrastructure → SAM templates with VPC, security groups, IAM',
            '3. Provide deployment scripts → Ready-to-use deployment and testing scripts',
            '4. Optimize performance → Use esm_optimize for tuning',
            '5. Troubleshoot issues → Use esm_kafka_troubleshoot for problems',
        ],
        'no_keywords_required': 'Tools automatically selected based on user intent, not technical terminology',
    }


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
    ConfigureDomainTool(mcp, args.allow_write)
    DeployWebAppTool(mcp, args.allow_write)
    UpdateFrontendTool(mcp, args.allow_write)

    # ESM tools
    EsmGuidanceTool(mcp, allow_write=args.allow_write)
    EsmDiagnosisTool(mcp, allow_write=args.allow_write)
    EsmRecommendTool(mcp, allow_write=args.allow_write)
    SecureEsmGuidanceTool(mcp, allow_write=args.allow_write)

    # Set AWS_EXECUTION_ENV to configure user agent of boto3. Setting it through an environment variable
    # because SAM CLI does not support setting user agents directly
    os.environ['AWS_EXECUTION_ENV'] = f'awslabs/mcp/aws-serverless-mcp-server/{__version__}'

    mode_info = []
    if not args.allow_write:
        mode_info.append('read-only mode')
    if not args.allow_sensitive_data_access:
        mode_info.append('restricted sensitive data access mode')

    try:
        logger.info(f'Starting AWS Serverless MCP Server in {", ".join(mode_info)}')
        mcp.run()
        return 0
    except Exception as e:
        logger.error(f'Error starting AWS Serverless MCP Server: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
