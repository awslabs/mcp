#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""Serverless MCP Server implementation."""

import argparse
import os
import sys

# Import all model classes
from awslabs.aws_serverless_mcp_server.models import (
    BackendConfiguration,
    ConfigureDomainRequest,
    DeployServerlessAppHelpRequest,
    DeployWebAppRequest,
    FrontendConfiguration,
    GetIaCGuidanceRequest,
    GetLambdaEventSchemasRequest,
    GetLambdaGuidanceRequest,
    GetMetricsRequest,
    GetServerlessTemplatesRequest,
    SamBuildRequest,
    SamDeployRequest,
    SamInitRequest,
    SamLocalInvokeRequest,
    SamLogsRequest,
    UpdateFrontendRequest,
    WebappDeploymentHelpRequest,
)
from awslabs.aws_serverless_mcp_server.resources.deployment_details import (
    handle_deployment_details,
)
from awslabs.aws_serverless_mcp_server.resources.deployment_list import handle_deployments_list
from awslabs.aws_serverless_mcp_server.resources.template_details import handle_template_details
from awslabs.aws_serverless_mcp_server.resources.template_list import handle_template_list
from awslabs.aws_serverless_mcp_server.tools.guidance.deploy_serverless_app_help import (
    ApplicationType,
    deploy_serverless_app_help,
)
from awslabs.aws_serverless_mcp_server.tools.guidance.get_iac_guidance import get_iac_guidance
from awslabs.aws_serverless_mcp_server.tools.guidance.get_lambda_event_schemas import (
    get_lambda_event_schemas,
)
from awslabs.aws_serverless_mcp_server.tools.guidance.get_lambda_guidance import (
    get_lambda_guidance,
)
from awslabs.aws_serverless_mcp_server.tools.guidance.get_serverless_templates import (
    get_serverless_templates,
)

# Import all implementation modules
from awslabs.aws_serverless_mcp_server.tools.sam import (
    handle_sam_build,
    handle_sam_deploy,
    handle_sam_init,
    handle_sam_local_invoke,
    handle_sam_logs,
)
from awslabs.aws_serverless_mcp_server.tools.schemas.describe_schema import describe_schema_impl
from awslabs.aws_serverless_mcp_server.tools.schemas.list_registries import list_registries_impl
from awslabs.aws_serverless_mcp_server.tools.schemas.search_schema import search_schema_impl
from awslabs.aws_serverless_mcp_server.tools.webapps.configure_domain import configure_domain
from awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp import deploy_webapp
from awslabs.aws_serverless_mcp_server.tools.webapps.get_metrics import get_metrics
from awslabs.aws_serverless_mcp_server.tools.webapps.update_webapp_frontend import (
    update_webapp_frontend,
)
from awslabs.aws_serverless_mcp_server.tools.webapps.webapp_deployment_help import (
    webapp_deployment_help,
)
from awslabs.aws_serverless_mcp_server.utils.aws_client_helper import get_aws_client
from awslabs.aws_serverless_mcp_server.utils.const import AWS_REGION, DEPLOYMENT_STATUS_DIR
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal, Optional


# Initialize boto3 client
schemas_client = get_aws_client('schemas', AWS_REGION)


allow_sensitive_data_access = False
allow_write = False

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


# SAM Tools
@mcp.tool(
    description="""
    Builds a serverless application using AWS SAM (Serverless Application Model) CLI.
    This command compiles your Lambda function code, creates deployment artifacts, and prepares your application for deployment.
    Before running this tool, the application should already be initialized with 'sam_init' tool.
    You should have AWS SAM CLI installed and configured in your environment.
    """
)
async def sam_build_tool(
    ctx: Context,
    project_directory: str = Field(
        description='Absolute path to directory containing the SAM project (defaults to current directory)'
    ),
    template_file: Optional[str] = Field(
        default=None, description='Absolute path to the template file (defaults to template.yaml)'
    ),
    base_dir: Optional[str] = Field(
        default=None,
        description="Resolve relative paths to function's source code with respect to this folder.\n            Use this option if you want to change how relative paths to source code folders are resolved.\n            By default, relative paths are resolved with respect to the AWS SAM template's location.",
    ),
    build_dir: Optional[str] = Field(
        default=None,
        description='The absolute path to a directory where the built artifacts are stored.\n            This directory and all of its content are removed with this option.',
    ),
    use_container: bool = Field(
        default=False,
        description='Use a container to build the function. Use this option if your function requires a specific runtime environmentor dependencies that are not available on the local machine. Docker must be installed.',
    ),
    no_use_container: bool = Field(
        default=False,
        description="Run build in local machine instead of Docker container.\n         You can specify this option multiple times. Each instance of this option takes a key-value pair,\n         where the key is the resource and environment variable, and the value is the environment variable's value.\n         For example: --container-env-var Function1.GITHUB_TOKEN=TOKEN1 --container-env-var Function2.GITHUB_TOKEN=TOKEN2.",
    ),
    container_env_vars: Optional[Dict[str, str]] = Field(
        default=None, description='Environment variables to pass to the build container.'
    ),
    container_env_var_file: Optional[str] = Field(
        default=None,
        description='Absolute path to a JSON file containing container environment variables.\n            For more information about container environment variable files, see Container environment variable file.',
    ),
    build_image: Optional[str] = Field(
        default=None,
        description='The URI of the container image that you want to pull for the build. By default, AWS SAM pulls the\n            container image from Amazon ECR Public. Use this option to pull the image from another location.',
    ),
    debug: bool = Field(default=False, description='Turn on debug logging'),
    manifest: Optional[str] = Field(
        default=None,
        description="Absolute path to a custom dependency manifest file (e.g., package.json) instead of the default.\n         For example: 'ParameterKey=KeyPairName, ParameterValue=MyKey ParameterKey=InstanceType, ParameterValue=t1.micro.",
    ),
    parameter_overrides: Optional[str] = Field(
        default=None,
        description="CloudFormation parameter overrides encoded as key-value pairs.\n        For example: 'ParameterKey=KeyPairName, ParameterValue=MyKey ParameterKey=InstanceType, ParameterValue=t1.micro'.",
    ),
    region: Optional[str] = Field(
        default=None, description='AWS Region to deploy to (e.g., us-east-1)'
    ),
    save_params: bool = Field(
        default=False, description='Save parameters to the SAM configuration file'
    ),
    profile: Optional[str] = Field(default=None, description='AWS profile to use'),
) -> dict[str, Any]:
    """Asynchronously builds an AWS SAM project using the provided context and build request.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        project_directory (str): Absolute path to directory containing the SAM project.
        template_file (Optional[str], optional): Absolute path to the template file. Defaults to None.
        base_dir (Optional[str], optional): Resolve relative paths to function's source code with respect to this folder. Defaults to None.
        build_dir (Optional[str], optional): The absolute path to a directory where the built artifacts are stored. Defaults to None.
        use_container (bool, optional): Use a container to build the function. Defaults to False.
        no_use_container (bool, optional): Run build in local machine instead of Docker container. Defaults to False.
        container_env_vars (Optional[Dict[str, str]], optional): Environment variables to pass to the build container. Defaults to None.
        container_env_var_file (Optional[str], optional): Absolute path to a JSON file containing container environment variables. Defaults to None.
        build_image (Optional[str], optional): The URI of the container image that you want to pull for the build. Defaults to None.
        debug (bool, optional): Turn on debug logging. Defaults to False.
        manifest (Optional[str], optional): Absolute path to a custom dependency manifest file. Defaults to None.
        parameter_overrides (Optional[str], optional): CloudFormation parameter overrides encoded as key-value pairs. Defaults to None.
        region (Optional[str], optional): AWS Region to deploy to. Defaults to None.
        save_params (bool, optional): Save parameters to the SAM configuration file. Defaults to False.
        profile (Optional[str], optional): AWS profile to use. Defaults to None.

    Returns:
        str: The output or result of the SAM build process.
    """
    # Create the SamBuildRequest object from the individual parameters
    request = SamBuildRequest(
        project_directory=project_directory,
        template_file=template_file,
        base_dir=base_dir,
        build_dir=build_dir,
        use_container=use_container,
        no_use_container=no_use_container,
        container_env_vars=container_env_vars,
        container_env_var_file=container_env_var_file,
        build_image=build_image,
        debug=debug,
        manifest=manifest,
        parameter_overrides=parameter_overrides,
        region=region,
        save_params=save_params,
        profile=profile,
    )

    await ctx.info(f'Building SAM project in {request.project_directory}')
    return await handle_sam_build(request)


@mcp.tool(
    description="""
    Initializes a serverless application using AWS SAM (Serverless Application Model) CLI.
    This tool creates a new SAM project that consists of:
    - An AWS SAM template to define your infrastructure code
    - A folder structure that organizes your application
    - Configuration for your AWS Lambda functions
    You should have AWS SAM CLI installed and configured in your environment.
    """
)
async def sam_init_tool(
    ctx: Context,
    project_name: str = Field(description='Name of the SAM project to create'),
    runtime: str = Field(description='Runtime environment for the Lambda function'),
    project_directory: str = Field(
        description='Absolute path to directory where the SAM application will be initialized'
    ),
    dependency_manager: str = Field(description='Dependency manager for the Lambda function'),
    architecture: str = Field(
        default='x86_64', description='Architecture for the Lambda function'
    ),
    package_type: str = Field(default='Zip', description='Package type for the Lambda function'),
    application_template: str = Field(
        default='hello-world',
        description='Template for the SAM application, e.g., hello-world, quick-start, etc.\n            This parameter is required if location is not specified.',
    ),
    application_insights: Optional[bool] = Field(
        default=False, description='Activate Amazon CloudWatch Application Insights monitoring'
    ),
    no_application_insights: Optional[bool] = Field(
        default=False, description='Deactivate Amazon CloudWatch Application Insights monitoring'
    ),
    base_image: Optional[str] = Field(
        default=None, description='Base image for the application when package type is Image'
    ),
    config_env: Optional[str] = Field(
        default=None,
        description='Environment name specifying default parameter values in the configuration file',
    ),
    config_file: Optional[str] = Field(
        default=None,
        description='Absolute path to configuration file containing default parameter values',
    ),
    debug: Optional[bool] = Field(default=False, description='Turn on debug logging'),
    extra_content: Optional[str] = Field(
        default=None, description="Override custom parameters in the template's cookiecutter.json"
    ),
    location: Optional[str] = Field(
        default=None,
        description='Template or application location (Git, HTTP/HTTPS, zip file path).\n            This parameter is required if app_template is not specified.',
    ),
    save_params: Optional[bool] = Field(
        default=False, description='Save parameters to the SAM configuration file'
    ),
    tracing: Optional[bool] = Field(
        default=False, description='Activate AWS X-Ray tracing for Lambda functions'
    ),
    no_tracing: Optional[bool] = Field(
        default=False, description='Deactivate AWS X-Ray tracing for Lambda functions'
    ),
) -> dict[str, Any]:
    """Asynchronously initializes a new AWS SAM project with the provided configuration.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        project_name (str): Name of the SAM project to create.
        runtime (str): Runtime environment for the Lambda function.
        project_directory (str): Absolute path to directory where the SAM application will be initialized.
        dependency_manager (str): Dependency manager for the Lambda function.
        architecture (str, optional): Architecture for the Lambda function. Defaults to "x86_64".
        package_type (str, optional): Package type for the Lambda function. Defaults to "Zip".
        application_template (str, optional): Template for the SAM application. Defaults to "hello-world".
        application_insights (Optional[bool], optional): Activate Amazon CloudWatch Application Insights monitoring. Defaults to False.
        no_application_insights (Optional[bool], optional): Deactivate Amazon CloudWatch Application Insights monitoring. Defaults to False.
        base_image (Optional[str], optional): Base image for the application when package type is Image. Defaults to None.
        config_env (Optional[str], optional): Environment name specifying default parameter values. Defaults to None.
        config_file (Optional[str], optional): Absolute path to configuration file. Defaults to None.
        debug (Optional[bool], optional): Turn on debug logging. Defaults to False.
        extra_content (Optional[str], optional): Override custom parameters in the template's cookiecutter.json. Defaults to None.
        location (Optional[str], optional): Template or application location. Defaults to None.
        save_params (Optional[bool], optional): Save parameters to the SAM configuration file. Defaults to False.
        tracing (Optional[bool], optional): Activate AWS X-Ray tracing for Lambda functions. Defaults to False.
        no_tracing (Optional[bool], optional): Deactivate AWS X-Ray tracing for Lambda functions. Defaults to False.

    Returns:
        str: The output or result of the SAM initialization process.
    """
    # Create the SamInitRequest object from the individual parameters
    request = SamInitRequest(
        project_name=project_name,
        runtime=runtime,
        project_directory=project_directory,
        dependency_manager=dependency_manager,
        architecture=architecture,
        package_type=package_type,
        application_template=application_template,
        application_insights=application_insights,
        no_application_insights=no_application_insights,
        base_image=base_image,
        config_env=config_env,
        config_file=config_file,
        debug=debug,
        extra_content=extra_content,
        location=location,
        save_params=save_params,
        tracing=tracing,
        no_tracing=no_tracing,
    )

    await ctx.info(
        f"Initializing SAM project '{request.project_name}' in {request.project_directory}"
    )
    return await handle_sam_init(request)


@mcp.tool(
    description="""
    Deploys a serverless application using AWS SAM (Serverless Application Model) CLI.
    This command deploys your application to AWS CloudFormation.
    Every time an appplication is deployed, it should be built with 'sam_build' tool before.
    You should have AWS SAM CLI installed and configured in your environment.
    """
)
async def sam_deploy_tool(
    ctx: Context,
    application_name: str = Field(description='Name of the application to be deployed'),
    project_directory: str = Field(
        description='Absolute path to directory containing the SAM project (defaults to current directory)'
    ),
    template_file: Optional[str] = Field(
        default=None, description='Absolute path to the template file (defaults to template.yaml)'
    ),
    s3_bucket: Optional[str] = Field(default=None, description='S3 bucket to deploy artifacts to'),
    s3_prefix: Optional[str] = Field(default=None, description='S3 prefix for the artifacts'),
    region: Optional[str] = Field(default=None, description='AWS region to deploy to'),
    profile: Optional[str] = Field(default=None, description='AWS profile to use'),
    parameter_overrides: Optional[str] = Field(
        default=None, description='CloudFormation parameter overrides encoded as key-value pairs'
    ),
    capabilities: Optional[
        List[Literal['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']]
    ] = Field(
        default=['CAPABILITY_IAM'], description='IAM capabilities required for the deployment'
    ),
    config_file: Optional[str] = Field(
        default=None, description='Absolute path to the SAM configuration file'
    ),
    config_env: Optional[str] = Field(
        default=None,
        description='Environment name specifying default parameter values in the configuration file',
    ),
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description='Metadata to include with the stack'
    ),
    tags: Optional[Dict[str, str]] = Field(default=None, description='Tags to apply to the stack'),
    resolve_s3: bool = Field(
        default=False, description='Automatically create an S3 bucket for deployment artifacts'
    ),
    debug: bool = Field(default=False, description='Turn on debug logging'),
) -> Dict[str, Any]:
    """Asynchronously deploys an AWS SAM project to AWS CloudFormation.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        application_name (str): Name of the application to be deployed.
        project_directory (str): Absolute path to directory containing the SAM project.
        template_file (Optional[str], optional): Absolute path to the template file. Defaults to None.
        s3_bucket (Optional[str], optional): S3 bucket to deploy artifacts to. Defaults to None.
        s3_prefix (Optional[str], optional): S3 prefix for the artifacts. Defaults to None.
        region (Optional[str], optional): AWS region to deploy to. Defaults to None.
        profile (Optional[str], optional): AWS profile to use. Defaults to None.
        parameter_overrides (Optional[str], optional): CloudFormation parameter overrides. Defaults to None.
        capabilities (Optional[List[str]], optional): IAM capabilities required for the deployment. Defaults to ["CAPABILITY_IAM"].
        config_file (Optional[str], optional): Absolute path to the SAM configuration file. Defaults to None.
        config_env (Optional[str], optional): Environment name specifying default parameter values. Defaults to None.
        metadata (Optional[Dict[str, str]], optional): Metadata to include with the stack. Defaults to None.
        tags (Optional[Dict[str, str]], optional): Tags to apply to the stack. Defaults to None.
        resolve_s3 (bool, optional): Automatically create an S3 bucket for deployment artifacts. Defaults to False.
        debug (bool, optional): Turn on debug logging. Defaults to False.

    Returns:
        str: The output or result of the SAM deployment process.
    """
    if not allow_write:
        return {
            'success': False,
            'error': 'Write operations are not allowed. Set --allow-write flag to true to enable write operations.',
        }

    # Create the SamDeployRequest object from the individual parameters
    request = SamDeployRequest(
        application_name=application_name,
        project_directory=project_directory,
        template_file=template_file,
        s3_bucket=s3_bucket,
        s3_prefix=s3_prefix,
        region=region,
        profile=profile,
        parameter_overrides=parameter_overrides,
        capabilities=capabilities,
        config_file=config_file,
        config_env=config_env,
        metadata=metadata,
        tags=tags,
        resolve_s3=resolve_s3,
        debug=debug,
    )

    await ctx.info(
        f"Deploying SAM application '{request.application_name}' from {request.project_directory}"
    )
    return await handle_sam_deploy(request)


@mcp.tool(
    description="""
        Fetches CloudWatch logs that are generated by resources in a SAM application. Use this tool
        to help debug invocation failures and find root causes."""
)
async def sam_logs_tool(
    ctx: Context,
    resource_name: Optional[str] = Field(
        default=None,
        description="Name of the resource to fetch logs for.\n            This is be the logical ID of the function resource in the AWS CloudFormation/AWS SAM template.\n            Multiple names can be provided by repeating the parameter again. If you don't specify this option,\n            AWS SAM fetches logs for all resources in the stack that you specify. You must specify stack_name when\n            specifying resource_name.",
    ),
    stack_name: Optional[str] = Field(
        default=None, description='Name of the CloudFormation stack'
    ),
    start_time: Optional[str] = Field(
        default=None,
        description='Fetch logs starting from this time (format: 5mins ago, tomorrow, or YYYY-MM-DD HH:MM:SS)',
    ),
    end_time: Optional[str] = Field(
        default=None,
        description='Fetch logs up until this time (format: 5mins ago, tomorrow, or YYYY-MM-DD HH:MM:SS)',
    ),
    output: Optional[Literal['text', 'json']] = Field(default='text', description='Output format'),
    region: Optional[str] = Field(default=None, description='AWS region to use (e.g., us-east-1)'),
    profile: Optional[str] = Field(default=None, description='AWS profile to use'),
    cw_log_group: Optional[List[str]] = Field(
        default=None,
        description='Use AWS CloudWatch to fetch logs. Includes logs from the CloudWatch Logs log groups that you specify\n            If you specify this option along with name, AWS SAM includes logs from the specified log groups in addition to logs\n            from the named resources.',
    ),
    config_env: Optional[str] = Field(
        default=None,
        description='Environment name specifying default parameter values in the configuration file',
    ),
    config_file: Optional[str] = Field(
        default=None,
        description='Absolute path to configuration file containing default parameter values',
    ),
    save_params: bool = Field(
        default=False, description='Save parameters to the SAM configuration file'
    ),
) -> Dict[str, Any]:
    """Asynchronously fetches CloudWatch logs for resources in a SAM application.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        resource_name (Optional[str], optional): Name of the resource to fetch logs for. Defaults to None.
        stack_name (Optional[str], optional): Name of the CloudFormation stack. Defaults to None.
        start_time (Optional[str], optional): Fetch logs starting from this time. Defaults to None.
        end_time (Optional[str], optional): Fetch logs up until this time. Defaults to None.
        output (Optional[str], optional): Output format. Defaults to "text".
        region (Optional[str], optional): AWS region to use. Defaults to None.
        profile (Optional[str], optional): AWS profile to use. Defaults to None.
        cw_log_group (Optional[List[str]], optional): Use AWS CloudWatch to fetch logs. Defaults to None.
        config_env (Optional[str], optional): Environment name specifying default parameter values. Defaults to None.
        config_file (Optional[str], optional): Absolute path to configuration file. Defaults to None.
        save_params (bool, optional): Save parameters to the SAM configuration file. Defaults to False.

    Returns:
        Dict[str, Any]: A dictionary containing the logs and related information.
    """
    if not allow_sensitive_data_access:
        return {
            'success': False,
            'error': 'Sensitive data access is not allowed. Set --allow-sensitive-data flag to true to access logs.',
        }

    # Create the SamLogsRequest object from the individual parameters
    request = SamLogsRequest(
        resource_name=resource_name,
        stack_name=stack_name,
        start_time=start_time,
        end_time=end_time,
        output=output,
        region=region,
        profile=profile,
        cw_log_group=cw_log_group,
        config_env=config_env,
        config_file=config_file,
        save_params=save_params,
    )

    await ctx.info(f"Fetching logs for resource '{request.resource_name}'")
    response = await handle_sam_logs(request)
    return response


@mcp.tool(
    description="""
    Locally invokes a Lambda function using AWS SAM CLI.
    This command runs your Lambda function locally in a Docker container that simulates the AWS Lambda environment.
    You can use this tool to test your Lambda functions before deploying them to AWS. Docker must be installed and running in your environment.
    """
)
async def sam_local_invoke_tool(
    ctx: Context,
    project_directory: str = Field(
        description='Absolute path to directory containing the SAM project'
    ),
    resource_name: str = Field(description='Name of the Lambda function to invoke locally'),
    template_file: Optional[str] = Field(
        default=None,
        description='Absolute path to the SAM template file (defaults to template.yaml)',
    ),
    event_file: Optional[str] = Field(
        default=None, description='Absolute path to a JSON file containing event data'
    ),
    event_data: Optional[str] = Field(
        default=None, description='JSON string containing event data (alternative to event_file)'
    ),
    environment_variables_file: Optional[str] = Field(
        default=None,
        description='Absolute path to a JSON file containing environment variables to pass to the function',
    ),
    docker_network: Optional[str] = Field(
        default=None, description='Docker network to run the Lambda function in'
    ),
    container_env_vars: Optional[Dict[str, str]] = Field(
        default=None, description='Environment variables to pass to the container'
    ),
    parameter: Optional[Dict[str, str]] = Field(
        default=None, description='Override parameters from the template file'
    ),
    log_file: Optional[str] = Field(
        default=None, description='Absolute path to a file where the function logs will be written'
    ),
    layer_cache_basedir: Optional[str] = Field(
        default=None, description='Directory where the layers will be cached'
    ),
    region: Optional[str] = Field(default=None, description='AWS region to use (e.g., us-east-1)'),
    profile: Optional[str] = Field(default=None, description='AWS profile to use'),
) -> Dict[str, Any]:
    """Asynchronously invokes an AWS SAM local resource for testing purposes.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        project_directory (str): Absolute path to directory containing the SAM project.
        resource_name (str): Name of the Lambda function to invoke locally.
        template_file (Optional[str], optional): Absolute path to the SAM template file. Defaults to None.
        event_file (Optional[str], optional): Absolute path to a JSON file containing event data. Defaults to None.
        event_data (Optional[str], optional): JSON string containing event data. Defaults to None.
        environment_variables_file (Optional[str], optional): Absolute path to a JSON file containing environment variables. Defaults to None.
        docker_network (Optional[str], optional): Docker network to run the Lambda function in. Defaults to None.
        container_env_vars (Optional[Dict[str, str]], optional): Environment variables to pass to the container. Defaults to None.
        parameter (Optional[Dict[str, str]], optional): Override parameters from the template file. Defaults to None.
        log_file (Optional[str], optional): Absolute path to a file where the function logs will be written. Defaults to None.
        layer_cache_basedir (Optional[str], optional): Directory where the layers will be cached. Defaults to None.
        region (Optional[str], optional): AWS region to use. Defaults to None.
        profile (Optional[str], optional): AWS profile to use. Defaults to None.

    Returns:
        Dict[str, Any]: The response from the local invocation of the specified SAM resource.
    """
    # Create the SamLocalInvokeRequest object from the individual parameters
    request = SamLocalInvokeRequest(
        project_directory=project_directory,
        resource_name=resource_name,
        template_file=template_file,
        event_file=event_file,
        event_data=event_data,
        environment_variables_file=environment_variables_file,
        docker_network=docker_network,
        container_env_vars=container_env_vars,
        parameter=parameter,
        log_file=log_file,
        layer_cache_basedir=layer_cache_basedir,
        region=region,
        profile=profile,
    )

    await ctx.info(
        f"Locally invoking resource '{request.resource_name}' in {request.project_directory}"
    )
    response = await handle_sam_local_invoke(request)
    return response


# Guidance Tools
@mcp.tool(
    description="""
    Use this tool to determine if AWS Lambda is suitable platform to deploy an application.
    Returns a comprehensive guide on when to choose AWS Lambda as a deployment platform.
    It includes scenarios when to use and not use Lambda, advantages and disadvantages,
    decision criteria, and specific guidance for various use cases.
    """
)
async def get_lambda_guidance_tool(
    ctx: Context,
    use_case: str = Field(description='Description of the use case'),
    include_examples: Optional[bool] = Field(
        default=True, description='Whether to include examples'
    ),
) -> Dict[str, Any]:
    """Asynchronously retrieves Lambda guidance based on the provided use case request.

    Args:
        ctx (Context): The context object, used for logging and request context.
        use_case (str): Description of the use case.
        include_examples (Optional[bool], optional): Whether to include examples. Defaults to True.

    Returns:
        Dict[str, Any]: A dictionary containing the Lambda guidance response.
    """
    # Create the GetLambdaGuidanceRequest object from the individual parameters
    request = GetLambdaGuidanceRequest(use_case=use_case, include_examples=include_examples)

    await ctx.info(f'Getting Lambda guidance for {request.use_case}')
    response = await get_lambda_guidance(request)
    return response


@mcp.tool(
    description="""
    Returns guidance on selecting an infrastructure as code (IaC) platform to deploy Serverless application to AWS.
    Choices include AWS SAM, CDK, and CloudFormation. Use this tool to decide which IaC tool to use for your Lambda deployments
    based on your specific use case and requirements.
    """
)
async def get_iac_guidance_tool(
    ctx: Context,
    iac_tool: Optional[Literal['CloudFormation', 'SAM', 'CDK', 'Terraform']] = Field(
        default='CloudFormation', description='IaC tool to use'
    ),
    include_examples: Optional[bool] = Field(
        default=True, description='Whether to include examples'
    ),
) -> Dict[str, Any]:
    """Asynchronously retrieves guidance on selecting an Infrastructure as Code (IaC) platform.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        iac_tool (Optional[str], optional): IaC tool to use. Defaults to "CloudFormation".
        include_examples (Optional[bool], optional): Whether to include examples. Defaults to True.

    Returns:
        Dict[str, Any]: A dictionary containing the IaC guidance information.
    """
    # Create the GetIaCGuidanceRequest object from the individual parameters
    request = GetIaCGuidanceRequest(iac_tool=iac_tool, include_examples=include_examples)

    await ctx.info(
        f'Getting IaC guidance for {request.iac_tool if request.iac_tool else "all tools"}'
    )
    response = await get_iac_guidance(request)
    return response


@mcp.tool(
    description="""
    Returns AWS Lambda event schemas for different event sources (e.g. s3, sns, apigw) and programming languages.  Each Lambda event source defines its own schema and language-specific types, which should be used in
    the Lambda function handler to correctly parse the event data. If you cannot find a schema for your event source, you can directly parse
    the event data as a JSON object. For EventBridge events,
    you must use the list_registries, search_schema, and describe_schema tools to access the schema registry directly, get schema definitions,
    and generate code processing logic.
    """
)
async def get_lambda_event_schemas_tool(
    ctx: Context,
    event_source: str = Field(
        description='Event source (e.g., api-gw, s3, sqs, sns, kinesis, eventbridge, dynamodb)'
    ),
    runtime: str = Field(
        description='Programming language for the schema references (e.g., go, nodejs, python, java)'
    ),
) -> Dict[str, Any]:
    """Asynchronously retrieves AWS Lambda event schemas for different event sources and programming languages.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        event_source (str): Event source (e.g., api-gw, s3, sqs, sns, kinesis, eventbridge, dynamodb).
        runtime (str): Programming language for the schema references (e.g., go, nodejs, python, java).

    Returns:
        Dict[str, Any]: A dictionary containing the Lambda event schemas.
    """
    # Create the GetLambdaEventSchemasRequest object from the individual parameters
    request = GetLambdaEventSchemasRequest(event_source=event_source, runtime=runtime)

    await ctx.info(f'Getting Lambda event schemas for {request.event_source} in {request.runtime}')
    response = await get_lambda_event_schemas(request)
    return response


@mcp.tool(
    description="""
    Deploy web applications to AWS Serverless, including Lambda as compute, DynamoDB as databases, API GW, ACM Certificates, and Route 53 DNS records.
    This tool uses the Lambda Web Adapter framework so that applications can be written in a standard web framework like Express or Next.js can be easily
    deployed to Lambda. You do not need to use integrate the code with any adapter framework when using this tool.
    """
)
async def deploy_webapp_tool(
    ctx: Context,
    deployment_type: Literal['backend', 'frontend', 'fullstack'] = Field(
        description='Type of deployment'
    ),
    project_name: str = Field(description='Project name'),
    project_root: str = Field(description='Absolute path to the project root directory'),
    region: Optional[str] = Field(
        default=None, description='AWS Region to deploy to (e.g., us-east-1)'
    ),
    backend_configuration: Optional[BackendConfiguration] = Field(
        default=None, description='Backend configuration'
    ),
    frontend_configuration: Optional[FrontendConfiguration] = Field(
        default=None, description='Frontend configuration'
    ),
) -> Dict[str, Any]:
    """Asynchronously deploys a web application to AWS Serverless infrastructure.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        deployment_type (str): Type of deployment (backend, frontend, or fullstack).
        project_name (str): Project name.
        project_root (str): Absolute path to the project root directory.
        region (Optional[str], optional): AWS Region to deploy to. Defaults to None.
        backend_configuration (Optional[Dict[str, Any]], optional): Backend configuration. Defaults to None.
        frontend_configuration (Optional[Dict[str, Any]], optional): Frontend configuration. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the deployment results and information.
    """
    if not allow_write:
        return {
            'success': False,
            'error': 'Write operations are not allowed. Set --allow-write flag to true to enable write operations.',
        }

    # Create the DeployWebAppRequest object from the individual parameters
    request = DeployWebAppRequest(
        deployment_type=deployment_type,
        project_name=project_name,
        project_root=project_root,
        region=region,
        backend_configuration=backend_configuration,
        frontend_configuration=frontend_configuration,
    )

    await ctx.info(
        f"Deploying web application '{request.project_name}' from {request.project_root}"
    )
    response = await deploy_webapp(request)
    return response


@mcp.tool(
    description="""
    Get help information about using the deploy_webapp_tool to perform web application deployments.
    If deployment_type is provided, returns help information for that deployment type.
    Otherwise, returns a list of deployments and general help information.
    """
)
async def webapp_deployment_help_tool(
    ctx: Context,
    deployment_type: Literal['backend', 'frontend', 'fullstack'] = Field(
        description='Type of deployment to get help information for'
    ),
) -> Dict[str, Any]:
    """Asynchronously retrieves help information about web application deployments.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        deployment_type (str): Type of deployment to get help information for.

    Returns:
        Dict[str, Any]: A dictionary containing the deployment help information.
    """
    # Create the WebappDeploymentHelpRequest object from the individual parameters
    request = WebappDeploymentHelpRequest(deployment_type=deployment_type)

    await ctx.info(f'Getting deployment help for {request.deployment_type}')
    response = await webapp_deployment_help(request)
    return response


@mcp.tool(
    description="""
    Retrieves CloudWatch metrics from a deployed web application. Use this tool get metrics
    on error rates, latency, concurrency, etc.
    """
)
async def get_metrics_tool(
    ctx: Context,
    project_name: str = Field(description='Project name'),
    start_time: Optional[str] = Field(
        default=None, description='Start time for metrics (ISO format)'
    ),
    end_time: Optional[str] = Field(default=None, description='End time for metrics (ISO format)'),
    period: Optional[int] = Field(default=60, description='Period for metrics in seconds'),
    resources: Optional[List[Literal['lambda', 'apiGateway', 'cloudfront']]] = Field(
        default=['lambda', 'apiGateway'], description='Resources to get metrics for'
    ),
    region: Optional[str] = Field(default=None, description='AWS region to use (e.g., us-east-1)'),
    stage: Optional[str] = Field(default='prod', description='API Gateway stage'),
) -> Dict[str, Any]:
    """Asynchronously retrieves CloudWatch metrics for a deployed web application.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        project_name (str): Project name.
        start_time (Optional[str], optional): Start time for metrics (ISO format). Defaults to None.
        end_time (Optional[str], optional): End time for metrics (ISO format). Defaults to None.
        period (Optional[int], optional): Period for metrics in seconds. Defaults to 60.
        resources (Optional[List[str]], optional): Resources to get metrics for. Defaults to ["lambda", "apiGateway"].
        region (Optional[str], optional): AWS region to use. Defaults to None.
        stage (Optional[str], optional): API Gateway stage. Defaults to "prod".

    Returns:
        Dict[str, Any]: A dictionary containing the metrics data.
    """
    # Create the GetMetricsRequest object from the individual parameters
    request = GetMetricsRequest(
        project_name=project_name,
        start_time=start_time,
        end_time=end_time,
        period=period,
        resources=resources,
        region=region,
        stage=stage,
    )

    await ctx.info(f'Getting metrics for project {request.project_name}')
    response = await get_metrics(request)
    return response


@mcp.tool(
    description="""
    Update the frontend assets of a deployed web application.
    This tool uploads new frontend assets to S3 and optionally invalidates the CloudFront cache.
    """
)
async def update_webapp_frontend_tool(
    ctx: Context,
    project_name: str = Field(description='Project name'),
    project_root: str = Field(description='Project root'),
    built_assets_path: str = Field(description='Absolute path to pre-built frontend assets'),
    invalidate_cache: Optional[bool] = Field(
        default=True, description='Whether to invalidate the CloudFront cache'
    ),
    region: Optional[str] = Field(default=None, description='AWS region to use (e.g., us-east-1)'),
) -> Dict[str, Any]:
    """Asynchronously updates the frontend assets of a deployed web application.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        project_name (str): Project name.
        project_root (str): Project root.
        built_assets_path (str): Absolute path to pre-built frontend assets.
        invalidate_cache (Optional[bool], optional): Whether to invalidate the CloudFront cache. Defaults to True.
        region (Optional[str], optional): AWS region to use. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the update results.
    """
    # Create the UpdateFrontendRequest object from the individual parameters
    request = UpdateFrontendRequest(
        project_name=project_name,
        project_root=project_root,
        built_assets_path=built_assets_path,
        invalidate_cache=invalidate_cache,
        region=region,
    )

    await ctx.info(f'Updating frontend for project {request.project_name}')
    response = await update_webapp_frontend(request)
    return response


@mcp.tool(
    description="""
    Configures a custom domain for a deployed web application on AWS Serverless.
    This tool sets up Route 53 DNS records, ACM certificates, and CloudFront custom domain mappings as needed.
    Use this tool after deploying your web application to associate it with your own domain name.
    """
)
async def configure_domain_tool(
    ctx: Context,
    project_name: str = Field(description='Project name'),
    domain_name: str = Field(description='Custom domain name'),
    create_certificate: Optional[bool] = Field(
        default=True, description='Whether to create a ACM certificate'
    ),
    create_route53_record: Optional[bool] = Field(
        default=True, description='Whether to create a Route 53 record'
    ),
    region: Optional[str] = Field(default=None, description='AWS region to use (e.g., us-east-1)'),
) -> Dict[str, Any]:
    """Asynchronously configures a custom domain for a deployed web application.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        project_name (str): Project name.
        domain_name (str): Custom domain name.
        create_certificate (Optional[bool], optional): Whether to create a ACM certificate. Defaults to True.
        create_route53_record (Optional[bool], optional): Whether to create a Route 53 record. Defaults to True.
        region (Optional[str], optional): AWS region to use. Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the domain configuration results.
    """
    # Create the ConfigureDomainRequest object from the individual parameters
    request = ConfigureDomainRequest(
        project_name=project_name,
        domain_name=domain_name,
        create_certificate=create_certificate,
        create_route53_record=create_route53_record,
        region=region,
    )

    return await configure_domain(request)


@mcp.tool(
    description="""
    Provides instructions on how to deploy a serverless application to AWS Lambda.
    Deploying a Lambda application requires generating IaC templates, building the code, packaging
    the code, selecting a deployment tool, and executing the deployment commands. For deploying
    web applications specifically, use the deploy_webapp tool.
    """
)
async def deploy_serverless_app_help_tool(
    ctx: Context,
    application_type: Literal['event_driven', 'backend', 'fullstack'] = Field(
        description='Type of application to deploy'
    ),
) -> Dict[str, Any]:
    """Asynchronously provides instructions on how to deploy a serverless application to AWS Lambda.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        application_type (str): Type of application to deploy.

    Returns:
        Dict[str, Any]: A dictionary containing the deployment help information.
    """
    # Create the DeployServerlessAppHelpRequest object from the individual parameters
    request = DeployServerlessAppHelpRequest(application_type=application_type)

    # Map the string literal to the enum value
    app_type_map = {
        'event_driven': ApplicationType.EVENT_DRIVEN,
        'backend': ApplicationType.BACKEND,
        'fullstack': ApplicationType.FULLSTACK,
    }

    await ctx.info(f'Getting deployment help for {request.application_type} application')
    response = await deploy_serverless_app_help(app_type_map[request.application_type])
    return response


@mcp.tool(
    description="""
    Returns example SAM templates from the Serverless Land GitHub repo. Use this tool to get
    examples for building serverless applications with AWS Lambda and best practices of serverless architecture.
    """
)
async def get_serverless_templates_tool(
    ctx: Context,
    template_type: str = Field(description='Template type (e.g., API, ETL, Web)'),
    runtime: Optional[str] = Field(
        default=None, description='Lambda runtime (e.g., nodejs22.x, python3.13)'
    ),
) -> Dict[str, Any]:
    """Asynchronously retrieves example SAM templates from the Serverless Land GitHub repository.

    Args:
        ctx (Context): The execution context, used for logging and other contextual operations.
        template_type (str): Template type (e.g., API, ETL, Web).
        runtime (Optional[str], optional): Lambda runtime (e.g., nodejs22.x, python3.13). Defaults to None.

    Returns:
        Dict[str, Any]: A dictionary containing the serverless templates.
    """
    # Create the GetServerlessTemplatesRequest object from the individual parameters
    request = GetServerlessTemplatesRequest(template_type=template_type, runtime=runtime)

    await ctx.info(
        f'Getting serverless templates for {request.template_type if request.template_type else "all types"} and {request.runtime if request.runtime else "all runtimes"}'
    )
    response = await get_serverless_templates(request)
    return response


@mcp.tool()
async def list_registries(
    ctx: Context,
    registry_name_prefix: Optional[str] = Field(
        default=None,
        description='Specifying this limits the results to only those registry names that start with the specified prefix. For EventBridge events, use aws.events registry directly instead of searching.',
    ),
    scope: Optional[str] = Field(
        default=None,
        description="""Can be set to Local or AWS to limit responses to your custom registries, or the ones provided by AWS.
        LOCAL: The registry is created in your account.
        AWS: The registry is created by AWS.

        For EventBridge events, use aws.events registry which is an AWS-managed registry containing all AWS service event schemas.""",
    ),
    limit: Optional[int] = Field(
        default=None,
        description='Maximum number of results to return. If you specify 0, the operation returns up to 10 results.',
        ge=0,
        le=100,
    ),
    next_token: Optional[str] = Field(
        default=None, description='Next token returned by the previous operation.'
    ),
) -> Dict:
    """Lists the registries in your account.

    REQUIREMENTS:
    - For AWS service events, you MUST use the aws.events registry directly
    - For custom schemas, you MAY use LOCAL scope to manage your own registries
    - When searching AWS service events, you SHOULD use the AWS scope

    USAGE PATTERNS:
    1. Finding AWS Service Event Schemas:
    - Use aws.events registry directly instead of searching
    - Filter by AWS scope to see only AWS-provided schemas

    2. Managing Custom Schemas:
    - Use LOCAL scope to view your custom registries
    - Apply registry_name_prefix to find specific registry groups
    """
    return await list_registries_impl(
        schemas_client,
        registry_name_prefix=registry_name_prefix,
        scope=scope,
        limit=limit,
        next_token=next_token,
    )


@mcp.tool()
async def search_schema(
    ctx: Context,
    keywords: str = Field(
        description='Keywords to search for. Prefix service names with "aws." for better results (e.g., "aws.s3" for S3 events, "aws.ec2" for EC2 events).'
    ),
    registry_name: str = Field(
        description='For AWS service events, use "aws.events" to search the EventBridge schema registry.'
    ),
    limit: Optional[int] = Field(
        default=None,
        description='Maximum number of results to return. If you specify 0, the operation returns up to 10 results.',
        ge=0,
        le=100,
    ),
    next_token: Optional[str] = Field(
        default=None, description='Next token returned by the previous operation.'
    ),
) -> Dict:
    """Search for schemas in a registry using keywords.

    REQUIREMENTS:
    - You MUST use this tool to find schemas for AWS service events
    - You MUST search in the "aws.events" registry for AWS service events
    - You MUST use this tool when implementing Lambda functions that consume events from EventBridge
    - You SHOULD prefix search keywords with "aws." for optimal results (e.g., "aws.s3", "aws.ec2")
    - You MAY filter results using additional keywords for specific event types

    USE CASES:

    1. Lambda Function Development with EventBridge:
    - CRITICAL: Required for Lambda functions consuming events from EventBridge
    - Search for event schemas your function needs to process
    - Example: "aws.s3" for S3 events, "aws.dynamodb" for DynamoDB streams
    - Use results with describe_schema to get complete event structure

    2. EventBridge Rule Creation:
    - Find schemas to create properly structured event patterns
    - Example: "aws.ec2" for EC2 instance state changes
    - Ensure exact field names and types in rule patterns

    IMPLEMENTATION FLOW:
    1. Search aws.events registry for service schemas
    2. Note relevant schema names from results
    3. Use describe_schema to get complete definitions
    4. Implement handlers using exact schema structure
    """
    return await search_schema_impl(
        schemas_client,
        keywords=keywords,
        registry_name=registry_name,
        limit=limit,
        next_token=next_token,
    )


@mcp.tool()
async def describe_schema(
    ctx: Context,
    registry_name: str = Field(
        description='For AWS service events, use "aws.events" to access the EventBridge schema registry.'
    ),
    schema_name: str = Field(
        description='The name of the schema to retrieve (e.g., "aws.s3@ObjectCreated" for S3 events).'
    ),
    schema_version: Optional[str] = Field(
        default=None,
        description='Version number of the schema. For AWS service events, use latest version (default) to ensure up-to-date event handling.',
    ),
) -> Dict:
    """Retrieve the schema definition for the specified schema version.

    REQUIREMENTS:
    - You MUST use this tool to get complete schema definitions before implementing handlers
    - You MUST use this tool when implementing Lambda functions that consume events from EventBridge
    - You MUST use the returned schema structure for type-safe event handling
    - You SHOULD use the latest schema version unless specifically required otherwise
    - You MUST validate all required fields defined in the schema

    USE CASES:

    1. Lambda Function Handlers with EventBridge:
    You MUST:
    - CRITICAL: Required for Lambda functions consuming events from EventBridge
    - Implement handlers using the exact event structure
    - Validate all required fields defined in schema
    - Handle optional fields appropriately
    - Ensure type safety for EventBridge-sourced events

    You SHOULD:
    - Generate strongly typed code based on schema
    - Implement error handling for missing fields
    - Document any assumptions about structure

    2. EventBridge Rules:
    You MUST:
    - Create patterns that exactly match schema
    - Use correct field names and value types
    - Include all required fields in patterns

    You SHOULD:
    - Test patterns against sample events
    - Document pattern matching logic
    - Consider schema versions in design

    The schema content provides complete event structure with all fields and types, ensuring correct event handling.
    """
    return await describe_schema_impl(
        schemas_client,
        registry_name=registry_name,
        schema_name=schema_name,
        schema_version=schema_version,
    )


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

    global allow_sensitive_data_access
    global allow_write
    allow_sensitive_data_access = True if args.allow_sensitive_data_access else False
    allow_write = True if args.allow_write else False

    try:
        mcp.run()
        return 0
    except Exception as e:
        logger.error(f'Error starting AWS Serverless MCP server: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
