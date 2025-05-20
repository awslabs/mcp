"""awslabs aws-lambda MCP Server implementation."""

import argparse
import boto3
import logging
import os
import sys
from mcp.server.fastmcp import Context, FastMCP
from typing import Dict, Any

from awslabs.aws_lambda_mcp_server.resources.template_details import handle_template_details
from awslabs.aws_lambda_mcp_server.resources.deployment_details import handle_deployment_details
from awslabs.aws_lambda_mcp_server.resources.deployment_list import handle_deployments_list
from awslabs.aws_lambda_mcp_server.resources.template_list import handle_template_list

# Import all implementation modules
from awslabs.aws_lambda_mcp_server.impl.tools.sam import (
    sam_build, sam_init, sam_deploy, sam_local_invoke
)
from awslabs.aws_lambda_mcp_server.impl.tools.awslambda.create_function import create_function
from awslabs.aws_lambda_mcp_server.impl.tools.awslambda.update_function import update_function
from awslabs.aws_lambda_mcp_server.impl.tools.webapps.deploy_web_app import deploy_web_app
from awslabs.aws_lambda_mcp_server.impl.tools.webapps.configure_domain import configure_domain
from awslabs.aws_lambda_mcp_server.impl.tools.webapps.get_logs import get_logs
from awslabs.aws_lambda_mcp_server.impl.tools.webapps.get_metrics import get_metrics
from awslabs.aws_lambda_mcp_server.impl.tools.webapps.update_frontend import update_frontend
from awslabs.aws_lambda_mcp_server.impl.tools.webapps.deployment_help import deployment_help as get_deployment_help
from awslabs.aws_lambda_mcp_server.impl.tools.prompts.get_iac_guidance import get_iac_guidance
from awslabs.aws_lambda_mcp_server.impl.tools.prompts.get_lambda_event_schemas import get_lambda_event_schemas
from awslabs.aws_lambda_mcp_server.impl.tools.prompts.get_lambda_guidance import get_lambda_guidance
from awslabs.aws_lambda_mcp_server.impl.tools.prompts.get_serverless_templates import get_serverless_templates
from awslabs.aws_lambda_mcp_server.impl.tools.prompts.deploy_serverless_app_help import deploy_serverless_app_help, ApplicationType

# Import all model classes
from awslabs.aws_lambda_mcp_server.models import (
    DeployServerlessAppHelpRequest, SamBuildRequest, SamInitRequest, SamDeployRequest,
    CreateFunctionRequest, UpdateFunctionRequest, GetIaCGuidanceRequest, GetLambdaEventSchemasRequest, GetLambdaGuidanceRequest,
    GetServerlessTemplatesRequest, DeployWebAppRequest, ConfigureDomainRequest, GetLogsRequest, GetMetricsRequest, UpdateFrontendRequest,
    SamLocalInvokeRequest, DeploymentHelpRequest
)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWS_PROFILE = os.environ.get('AWS_PROFILE', 'default')
logger.info(f'AWS_PROFILE: {AWS_PROFILE}')

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
logger.info(f'AWS_REGION: {AWS_REGION}')

# Initialize AWS clients
session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
lambda_client = session.client('lambda')

mcp = FastMCP(
    'awslabs.aws-lambda-mcp-server',
    instructions="""Use AWS Lambda functions to improve your answers.
    These Lambda functions give you additional capabilities and access to AWS services and resources in an AWS account.""",
    dependencies=['pydantic', 'boto3'],
)

# Template resources
@mcp.resource("template://list")
def template_list() -> Dict[str, Any]:
    """List of available deployment templates."""
    return handle_template_list()

# Template resources
@mcp.resource("template://{template_name}")
def template_details(template_name: str) -> Dict[str, Any]:
    """List of available deployment templates."""
    return handle_template_details(template_name)

# Deployment resources
@mcp.resource("deployment://list")
async def deployment_list() -> Dict[str, Any]:
    """List of all AWS deployments managed by the MCP server."""
    return await handle_deployments_list()

@mcp.resource("deployment://{project_name}")
async def deployment_details(project_name: str) -> Dict[str, Any]:
    """Get details about a specific deployment."""
    return await handle_deployment_details(project_name)

@mcp.tool(description="""
    Builds a serverless application using AWS SAM (Serverless Application Model) CLI.
    This command compiles your Lambda functions, creates deployment artifacts, and prepares your application for deployment.
    Before running this tool, the application should already be initialized with 'sam_init' tool.
    You should have AWS SAM CLI installed and configured in your environment.
    """)
async def sam_build_tool(
    ctx: Context,
    request: SamBuildRequest
) -> str:

    await ctx.info(f"Building SAM project in {request.project_directory}")
    await sam_build(request)
    return f"SAM build completed successfully for project in {request.project_directory}"

@mcp.tool(description= """
    Initializes a serverless application using AWS SAM (Serverless Application Model) CLI.
    This command creates a new SAM project with the specified configuration.
    You should have AWS SAM CLI installed and configured in your environment.
    """)
async def sam_init_tool(
    ctx: Context,
    request: SamInitRequest
) -> str:
    await ctx.info(f"Initializing SAM project '{request.project_name}' in {request.project_directory}")
    await sam_init(request)
    return f"SAM initialization completed successfully for project '{request.project_name}' in {request.project_directory}"

@mcp.tool(description="""
    Deploys a serverless application using AWS SAM (Serverless Application Model) CLI.
    This command deploys your application to AWS CloudFormation.
    Before running this tool, the application should already be built with 'sam_build' tool.
    You should have AWS SAM CLI installed and configured in your environment.
    """)
async def sam_deploy_tool(
    ctx: Context,
    request: SamDeployRequest
) -> str:
    
    await ctx.info(f"Deploying SAM application '{request.application_name}' from {request.project_directory}")
    await sam_deploy(request)
    return f"SAM deployment completed successfully for application '{request.application_name}'"

@mcp.tool(description= """
    Creates a new AWS Lambda function.
    This tool can be used to deploy serverless functions to AWS Lambda, supporting both .zip file archives and container images as deployment packages.
    You can specify function configuration including memory, timeout, environment variables, VPC access, and more.
    """)
async def create_function_tool(
    ctx: Context,
    request: CreateFunctionRequest
) -> Dict[str, Any]:
    await ctx.info(f"Creating Lambda function: {request.function_name}")
    response = await create_function(request)
    return response

@mcp.tool(description="""
    Returns guidance on selecting an infrastructure as code (IaC) platform to deploy Serverless application to AWS.
    Choices include AWS SAM, CDK, and CloudFormation. Use this tool to decide which IaC tool to use for your Lambda deployments
    based on your specific use case and requirements.
    """)
async def get_iac_guidance_tool(
    ctx: Context,
    request: GetIaCGuidanceRequest
) -> Dict[str, Any]:
    await ctx.info(f"Getting IaC guidance for {request.iac_tool if request.iac_tool else 'all tools'}")
    response = await get_iac_guidance(request)
    return response

@mcp.tool(description="""
    Returns AWS Lambda event schemas for different event sources (e.g. s3, sns, apigw) and programming languages. Each Lambda event source
    defines its own schema and language-specific types, which should be used in the Lambda function handler to correctly parse the event data.
    If you cannot find a schema for your event source, you can directly parse the event data as a JSON object.
    """)
async def get_lambda_event_schemas_tool(
    ctx: Context,
    request: GetLambdaEventSchemasRequest
) -> Dict[str, Any]:
    
    await ctx.info(f"Getting Lambda event schemas for {request.event_source} in {request.runtime}")
    response = await get_lambda_event_schemas(request)
    return response

@mcp.tool(description="""
    Use this tool to determine if AWS Lambda is suitable platform to deploy an application.
    Returns a comprehensive guide on when to choose AWS Lambda as a deployment platform.
    It includes scenarios when to use and not use Lambda, advantages and disadvantages,
    decision criteria, and specific guidance for various use cases.
    """)
async def get_lambda_guidance_tool(
    ctx: Context,
    request: GetLambdaGuidanceRequest
) -> Dict[str, Any]:
    
    await ctx.info(f"Getting Lambda guidance for {request.use_case if request.use_case else 'general use'}")
    response = await get_lambda_guidance(request)
    return response

@mcp.tool(description="""
    Deploy web applications to AWS, including database resources like DynamoDB tables. This tool uses the Lambda Web Adapter framework
    so that applications can be written in a standard web framework like Express or Next.js can be easily deployed to Lambda. You do not need to use
    setup the code with any other adapter framework when using this tool.
    """)
async def deploy_web_app_tool(
    ctx: Context,
    request: DeployWebAppRequest
) -> Dict[str, Any]:
    await ctx.info(f"Deploying web application '{request.project_name}' from {request.project_root}")
    response = await deploy_web_app(request)
    return response

@mcp.tool(description="""
    Configure a custom domain for a deployed web application.
    This tool updates a CloudFront distribution to use a custom domain and optionally creates a Route 53 record.
    """)
async def configure_domain_tool(
    ctx: Context,
    request: ConfigureDomainRequest
) -> Dict[str, Any]:
    
    await ctx.info(f"Configuring custom domain {request.domain_name} for project {request.project_name}")
    response = await configure_domain(request)
    return response

@mcp.tool(description="""
    Get help information about deployments or deployment status.
    If project_name is provided, returns the status of the deployment.
    If deployment_type is provided, returns help information for that deployment type.
    If neither is provided, returns a list of deployments and general help information.
    """)
async def deployment_help_tool(
    ctx: Context,
    request: DeploymentHelpRequest
) -> Dict[str, Any]:
    await ctx.info(f"Getting deployment help for {request.deployment_type}")
    response = await get_deployment_help(request)
    return response

@mcp.tool(description="""
    Get logs from a deployed web application.
    This tool retrieves CloudWatch logs for a deployed Lambda function.
    """)
async def get_logs_tool(
    ctx: Context,
    request: GetLogsRequest
) -> Dict[str, Any]:
    
    await ctx.info(f"Getting logs for project {request.project_name}")
    response = await get_logs(request)
    return response

@mcp.tool(description= """
    Get metrics from a deployed web application.
    This tool retrieves CloudWatch metrics for a deployed application.
    """)
async def get_metrics_tool(
    ctx: Context,
    request: GetMetricsRequest
) -> Dict[str, Any]:
    await ctx.info(f"Getting metrics for project {request.project_name}")
    response = await get_metrics(request)
    return response

@mcp.tool(description="""
    Update the frontend of a deployed web application.
    This tool uploads new frontend assets to S3 and optionally invalidates the CloudFront cache.
    """)
async def update_frontend_tool(
    ctx: Context,
    request: UpdateFrontendRequest
) -> Dict[str, Any]:
    await ctx.info(f"Updating frontend for project {request.project_name}")
    response = await update_frontend(request)
    return response

@mcp.tool(description= """
    Provides instructions on how to deploy a serverless application to AWS Lambda.
    Deploying a Lambda application requires generating IaC templates, building the code, packaging
    the code, selecting a deployment tool, and executing the deployment commands. For deploying
    web applications specifically, use the deploy_webapp tool.
    """)
async def deploy_serverless_app_help_tool(
    ctx: Context,
    request: DeployServerlessAppHelpRequest
) -> Dict[str, Any]:
    # Map the string literal to the enum value
    app_type_map = {
        "event_driven": ApplicationType.EVENT_DRIVEN,
        "backend": ApplicationType.BACKEND,
        "fullstack": ApplicationType.FULLSTACK
    }
    
    await ctx.info(f"Getting deployment help for {request.application_type} application")
    response = await deploy_serverless_app_help(app_type_map[request.application_type])
    return response

@mcp.tool(description="""
    Returns example SAM templates from the Serverless Land GitHub repo. Use this tool to get
    examples for building serverless applications with AWS Lambda and best practices of serverless architecture.
    """)
async def get_serverless_templates_tool(
    ctx: Context,
    request: GetServerlessTemplatesRequest
) -> Dict[str, Any]:
    await ctx.info(f"Getting serverless templates for {request.template_type if request.template_type else 'all types'} and {request.runtime if request.runtime else 'all runtimes'}")
    response = await get_serverless_templates(request)
    return response

@mcp.tool(description="""
    Locally invokes a Lambda function using AWS SAM CLI.
    This tool allows you to test your function locally before deploying it to AWS Lambda.
    """)
async def sam_local_invoke_tool(
    ctx: Context,
    request: SamLocalInvokeRequest
) -> Dict[str, Any]:
    await ctx.info(f"Locally invoking Lambda function '{request.function_name}' in {request.project_directory}")
    response = await sam_local_invoke(request)
    return response

@mcp.tool(description="""
    Updates an existing AWS Lambda function.
    This tool can be used to modify the configuration and code of an existing Lambda function.
    You can update the function's code, configuration, environment variables, and more.
    """)
async def update_function_tool(
    ctx: Context,
    request: UpdateFunctionRequest
) -> Dict[str, Any]:
    await ctx.info(f"Updating Lambda function: {request.function_name}")
    response = await update_function(request)
    return response


def main() -> int:
    """Entry point for the AWS Lambda MCP server.
    
    This function is called when the `awslabs.aws-lambda-mcp-server` command is run.
    It starts the MCP server and handles command-line arguments.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(description="AWS Lambda MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        mcp.run()
        return 0
    except Exception as e:
        logger.error(f"Error starting MCP server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
