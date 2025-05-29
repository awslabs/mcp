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

"""Models for the AWS Serverless MCP Server."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


# SAM Models
class SamInitRequest(BaseModel):
    """Request model for AWS SAM init command."""

    project_name: str = Field(..., description='Name of the SAM project to create')
    architecture: str = Field('x86_64', description='Architecture for the Lambda function')
    package_type: str = Field('Zip', description='Package type for the Lambda function')
    runtime: str = Field(..., description='Runtime environment for the Lambda function')
    project_directory: str = Field(
        ..., description='Absolute path to directory where the SAM application will be initialized'
    )
    dependency_manager: str = Field(..., description='Dependency manager for the Lambda function')
    application_template: str = Field(
        'hello-world',
        description="""Template for the SAM application, e.g., hello-world, quick-start, etc.
            This parameter is required if location is not specified.""",
    )
    application_insights: Optional[bool] = Field(
        False, description='Activate Amazon CloudWatch Application Insights monitoring'
    )
    no_application_insights: Optional[bool] = Field(
        False, description='Deactivate Amazon CloudWatch Application Insights monitoring'
    )
    base_image: Optional[str] = Field(
        None, description='Base image for the application when package type is Image'
    )
    config_env: Optional[str] = Field(
        None,
        description='Environment name specifying default parameter values in the configuration file',
    )
    config_file: Optional[str] = Field(
        None, description='Absolute path to configuration file containing default parameter values'
    )
    debug: Optional[bool] = Field(False, description='Turn on debug logging')
    extra_content: Optional[str] = Field(
        None, description="Override custom parameters in the template's cookiecutter.json"
    )
    location: Optional[str] = Field(
        None,
        description="""Template or application location (Git, HTTP/HTTPS, zip file path).
            This parameter is required if app_template is not specified.""",
    )
    save_params: Optional[bool] = Field(
        False, description='Save parameters to the SAM configuration file'
    )
    tracing: Optional[bool] = Field(
        False, description='Activate AWS X-Ray tracing for Lambda functions'
    )
    no_tracing: Optional[bool] = Field(
        False, description='Deactivate AWS X-Ray tracing for Lambda functions'
    )


class SamDeployRequest(BaseModel):
    """Request model for AWS SAM deploy command."""

    application_name: str = Field(..., description='Name of the application to be deployed')
    project_directory: str = Field(
        ...,
        description='Absolute path to directory containing the SAM project (defaults to current directory)',
    )
    template_file: Optional[str] = Field(
        None, description='Absolute path to the template file (defaults to template.yaml)'
    )
    s3_bucket: Optional[str] = Field(None, description='S3 bucket to deploy artifacts to')
    s3_prefix: Optional[str] = Field(None, description='S3 prefix for the artifacts')
    region: Optional[str] = Field(None, description='AWS region to deploy to')
    profile: Optional[str] = Field(None, description='AWS profile to use')
    parameter_overrides: Optional[str] = Field(
        None, description='CloudFormation parameter overrides encoded as key-value pairs'
    )
    capabilities: Optional[
        List[Literal['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND']]
    ] = Field(['CAPABILITY_IAM'], description='IAM capabilities required for the deployment')
    config_file: Optional[str] = Field(
        None, description='Absolute path to the SAM configuration file'
    )
    config_env: Optional[str] = Field(
        None,
        description='Environment name specifying default parameter values in the configuration file',
    )
    metadata: Optional[Dict[str, str]] = Field(
        None, description='Metadata to include with the stack'
    )
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the stack')
    resolve_s3: bool = Field(
        False, description='Automatically create an S3 bucket for deployment artifacts'
    )
    debug: bool = Field(False, description='Turn on debug logging')


class SamLocalInvokeRequest(BaseModel):
    """Request model for AWS SAM local invoke command."""

    project_directory: str = Field(
        ..., description='Absolute path to directory containing the SAM project'
    )
    resource_name: str = Field(..., description='Name of the Lambda function to invoke locally')
    template_file: Optional[str] = Field(
        None, description='Absolute path to the SAM template file (defaults to template.yaml)'
    )
    event_file: Optional[str] = Field(
        None, description='Absolute path to a JSON file containing event data'
    )
    event_data: Optional[str] = Field(
        None, description='JSON string containing event data (alternative to event_file)'
    )
    environment_variables_file: Optional[str] = Field(
        None,
        description='Absolute path to a JSON file containing environment variables to pass to the function',
    )
    docker_network: Optional[str] = Field(
        None, description='Docker network to run the Lambda function in'
    )
    container_env_vars: Optional[Dict[str, str]] = Field(
        None, description='Environment variables to pass to the container'
    )
    parameter: Optional[Dict[str, str]] = Field(
        None, description='Override parameters from the template file'
    )
    log_file: Optional[str] = Field(
        None, description='Absolute path to a file where the function logs will be written'
    )
    layer_cache_basedir: Optional[str] = Field(
        None, description='Directory where the layers will be cached'
    )
    region: Optional[str] = Field(None, description='AWS region to use (e.g., us-east-1)')
    profile: Optional[str] = Field(None, description='AWS profile to use')


class SamLogsRequest(BaseModel):
    """Request model for AWS SAM logs command."""

    resource_name: Optional[str] = Field(
        None,
        description="""Name of the resource to fetch logs for.
            This is be the logical ID of the function resource in the AWS CloudFormation/AWS SAM template.
            Multiple names can be provided by repeating the parameter again. If you don't specify this option,
            AWS SAM fetches logs for all resources in the stack that you specify. You must specify stack_name when
            specifying resource_name.""",
    )
    stack_name: Optional[str] = Field(None, description='Name of the CloudFormation stack')
    start_time: Optional[str] = Field(
        None,
        description='Fetch logs starting from this time (format: 5mins ago, tomorrow, or YYYY-MM-DD HH:MM:SS)',
    )
    end_time: Optional[str] = Field(
        None,
        description='Fetch logs up until this time (format: 5mins ago, tomorrow, or YYYY-MM-DD HH:MM:SS)',
    )
    output: Optional[Literal['text', 'json']] = Field('text', description='Output format')
    region: Optional[str] = Field(None, description='AWS region to use (e.g., us-east-1)')
    profile: Optional[str] = Field(None, description='AWS profile to use')
    cw_log_group: Optional[List[str]] = Field(
        None,
        description="""Use AWS CloudWatch to fetch logs. Includes logs from the CloudWatch Logs log groups that you specify
            If you specify this option along with name, AWS SAM includes logs from the specified log groups in addition to logs
            from the named resources.""",
    )
    config_env: Optional[str] = Field(
        None,
        description='Environment name specifying default parameter values in the configuration file',
    )
    config_file: Optional[str] = Field(
        None, description='Absolute path to configuration file containing default parameter values'
    )
    save_params: bool = Field(False, description='Save parameters to the SAM configuration file')


class SamPipelineRequest(BaseModel):
    """Request model for AWS SAM pipeline command."""

    project_directory: str = Field(
        ..., description='Absolute path to directory containing the SAM project'
    )
    cicd_provider: Literal[
        'gitlab',
        'github',
        'jenkins',
        'gitlab-ci',
        'bitbucket-pipelines',
        'azure-pipelines',
        'codepipeline',
    ] = Field(..., description='CI/CD provider to generate pipeline configuration for')
    bucket: Optional[str] = Field(None, description='S3 bucket to store pipeline artifacts')
    bootstrap_ecr: bool = Field(
        False, description='Whether to create an ECR repository for the pipeline'
    )
    bitbucket_repo_uuid: Optional[str] = Field(
        None,
        description='The UUID of the Bitbucket repository. This option is specific to using Bitbucket OIDC for permissions',
    )
    cloudformation_execution_role: Optional[str] = Field(
        None,
        description="The ARN of the IAM role to be assumed by AWS CloudFormation while deploying the application's stack",
    )
    confirm_changes: bool = Field(
        False, description='Whether to confirm changes before creating resources'
    )
    config_env: Optional[str] = Field(
        None,
        description='Environment name specifying default parameter values in the configuration file',
    )
    config_file: Optional[str] = Field(
        None, description='Absolute path to configuration file containing default parameter values'
    )
    create_image_repository: Optional[bool] = Field(
        None,
        description='Specify whether to create an Amazon ECR image repository if none is provided',
    )
    debug: bool = Field(False, description='Turn on debug logging')
    deployment_branch: Optional[str] = Field(
        None,
        description='Name of the branch that deployments will occur from. This option is specific to using GitHub Actions OIDC for permissions',
    )
    github_org: Optional[str] = Field(
        None,
        description='The GitHub organization that the repository belongs to. This option is specific to using GitHub Actions OIDC for permissions',
    )
    gitlab_group: Optional[str] = Field(
        None,
        description='The GitLab group that the repository belongs to. This option is specific to using GitLab OIDC for permissions',
    )
    gitlab_project: Optional[str] = Field(
        None,
        description='The GitLab project name. This option is specific to using GitLab OIDC for permissions',
    )
    git_provider: Optional[Literal['codecommit', 'github', 'gitlab']] = Field(
        None, description='Git provider for the repository'
    )
    image_repository: Optional[str] = Field(
        None,
        description='The ARN of an Amazon ECR image repository that holds the container images of Lambda functions or layers',
    )
    oidc_client_id: Optional[str] = Field(
        None, description='The client ID configured for use with your OIDC provider'
    )
    oidc_provider: Optional[Literal['github-actions', 'gitlab', 'bitbucket-pipelines']] = Field(
        None, description='Name of the CI/CD provider that will be used for OIDC permissions'
    )
    oidc_provider_url: Optional[str] = Field(
        None, description='The URL for the OIDC provider. Value must begin with https://'
    )
    output_dir: Optional[str] = Field(
        None,
        description='Directory where the generated pipeline configuration files will be written',
    )
    parameter_overrides: Optional[str] = Field(
        None, description='CloudFormation parameter overrides encoded as key-value pairs'
    )
    permissions_provider: Optional[Literal['oidc', 'iam']] = Field(
        None,
        description='Choose a permissions provider to assume the pipeline execution role. The default value is iam',
    )
    pipeline_execution_role: Optional[str] = Field(
        None,
        description='The ARN of the IAM role to be assumed by the pipeline user to operate on this stage',
    )
    pipeline_user: Optional[str] = Field(
        None,
        description='The Amazon Resource Name (ARN) of the IAM user having its access key ID and secret access key shared with the CI/CD system',
    )
    profile: Optional[str] = Field(None, description='AWS profile to use')
    region: Optional[str] = Field(None, description='AWS Region to deploy to (e.g., us-east-1)')
    save_params: bool = Field(False, description='Save parameters to the SAM configuration file')
    stage: str = Field(..., description='Stage name to be used in the pipeline')


class SamBuildRequest(BaseModel):
    """Request model for AWS SAM build command."""

    project_directory: str = Field(
        ...,
        description='Absolute path to directory containing the SAM project (defaults to current directory)',
    )
    template_file: Optional[str] = Field(
        None, description='Absolute path to the template file (defaults to template.yaml)'
    )
    base_dir: Optional[str] = Field(
        None,
        description="""Resolve relative paths to function's source code with respect to this folder.
            Use this option if you want to change how relative paths to source code folders are resolved.
            By default, relative paths are resolved with respect to the AWS SAM template's location.""",
    )
    build_dir: Optional[str] = Field(
        None,
        description="""The absolute path to a directory where the built artifacts are stored.
            This directory and all of its content are removed with this option.""",
    )
    use_container: bool = Field(
        False,
        description='Use a container to build the function. Use this option if your function requires a specific runtime environment'
        'or dependencies that are not available on the local machine. Docker must be installed.',
    )
    no_use_container: bool = Field(
        False,
        description="""Run build in local machine instead of Docker container.
         You can specify this option multiple times. Each instance of this option takes a key-value pair,
         where the key is the resource and environment variable, and the value is the environment variable's value.
         For example: --container-env-var Function1.GITHUB_TOKEN=TOKEN1 --container-env-var Function2.GITHUB_TOKEN=TOKEN2.""",
    )
    container_env_vars: Optional[Dict[str, str]] = Field(
        None, description='Environment variables to pass to the build container.'
    )
    container_env_var_file: Optional[str] = Field(
        None,
        description="""Absolute path to a JSON file containing container environment variables.
            For more information about container environment variable files, see Container environment variable file.""",
    )
    build_image: Optional[str] = Field(
        None,
        description="""The URI of the container image that you want to pull for the build. By default, AWS SAM pulls the
            container image from Amazon ECR Public. Use this option to pull the image from another location.""",
    )
    debug: bool = Field(False, description='Turn on debug logging')
    manifest: Optional[str] = Field(
        None,
        description="""Absolute path to a custom dependency manifest file (e.g., package.json) instead of the default.
         For example: 'ParameterKey=KeyPairName, ParameterValue=MyKey ParameterKey=InstanceType, ParameterValue=t1.micro.""",
    )
    parameter_overrides: Optional[str] = Field(
        None,
        description="""CloudFormation parameter overrides encoded as key-value pairs.
        For example: 'ParameterKey=KeyPairName, ParameterValue=MyKey ParameterKey=InstanceType, ParameterValue=t1.micro'.""",
    )
    region: Optional[str] = Field(None, description='AWS Region to deploy to (e.g., us-east-1)')
    save_params: bool = Field(False, description='Save parameters to the SAM configuration file')
    profile: Optional[str] = Field(None, description='AWS profile to use')


# Guidance and References models
class GetIaCGuidanceRequest(BaseModel):
    """Request model for getting Infrastructure as Code guidance."""

    iac_tool: Optional[Literal['CloudFormation', 'SAM', 'CDK', 'Terraform']] = Field(
        'CloudFormation', description='IaC tool to use'
    )
    include_examples: Optional[bool] = Field(True, description='Whether to include examples')


class GetLambdaEventSchemasRequest(BaseModel):
    """Request model for getting Lambda event schemas."""

    event_source: str = Field(
        ...,
        description='Event source (e.g., api-gw, s3, sqs, sns, kinesis, eventbridge, dynamodb)',
    )
    runtime: str = Field(
        ...,
        description='Programming language for the schema references (e.g., go, nodejs, python, java)',
    )


class GetLambdaGuidanceRequest(BaseModel):
    """Request model for getting Lambda guidance."""

    use_case: str = Field(..., description='Description of the use case')
    include_examples: Optional[bool] = Field(True, description='Whether to include examples')


class GetServerlessTemplatesRequest(BaseModel):
    """Request model for getting serverless templates."""

    template_type: str = Field(..., description='Template type (e.g., API, ETL, Web)')
    runtime: Optional[str] = Field(
        None, description='Lambda runtime (e.g., nodejs22.x, python3.13)'
    )


class DeployServerlessAppHelpRequest(BaseModel):
    """Request model for getting serverless app deployment help."""

    application_type: Literal['event_driven', 'backend', 'fullstack'] = Field(
        ..., description='Type of application to deploy'
    )


# Serverless WebApp models
class BackendConfiguration(BaseModel):
    """Backend configuration for web application deployment."""

    built_artifacts_path: str = Field(
        ..., description='Absolute path to pre-built backend artifacts'
    )
    framework: Optional[str] = Field(None, description='Backend framework')
    runtime: str = Field(..., description='Lambda runtime (e.g. nodejs22.x, python3.13)')
    startup_script: Optional[str] = Field(
        None,
        description='Startup script that must be executable in Linux environment. Relative to the built_artifacts_path directory.',
    )
    entry_point: Optional[str] = Field(
        None, description='Application entry point file (e.g., app.js, app.py)'
    )
    generate_startup_script: Optional[bool] = Field(
        False, description='Whether to automatically generate a startup script'
    )
    architecture: Optional[Literal['x86_64', 'arm64']] = Field(
        'x86_64', description='Lambda architecture'
    )
    memory_size: Optional[int] = Field(512, description='Lambda memory size')
    timeout: Optional[int] = Field(30, description='Lambda timeout')
    stage: Optional[str] = Field('prod', description='API Gateway stage')
    cors: Optional[bool] = Field(True, description='Enable CORS')
    port: int = Field(..., description='Port on which the web application runs')
    environment: Optional[Dict[str, str]] = Field(None, description='Environment variables')
    database_configuration: Optional[Dict[str, Any]] = Field(
        None, description='Database configuration for creating DynamoDB tables'
    )


class FrontendConfiguration(BaseModel):
    """Frontend configuration for web application deployment."""

    built_assets_path: str = Field(..., description='Absolute path to pre-built frontend assets')
    framework: Optional[str] = Field(None, description='Frontend framework')
    index_document: Optional[str] = Field('index.html', description='Index document')
    error_document: Optional[str] = Field(None, description='Error document')
    custom_domain: Optional[str] = Field(None, description='Custom domain')
    certificate_arn: Optional[str] = Field(None, description='ACM certificate ARN')


class DeployWebAppRequest(BaseModel):
    """Request model for deploying a web application."""

    deployment_type: Literal['backend', 'frontend', 'fullstack'] = Field(
        ..., description='Type of deployment'
    )
    project_name: str = Field(..., description='Project name')
    project_root: str = Field(..., description='Absolute path to the project root directory')
    region: Optional[str] = Field(None, description='AWS Region to deploy to (e.g., us-east-1)')
    backend_configuration: Optional[BackendConfiguration] = Field(
        None, description='Backend configuration'
    )
    frontend_configuration: Optional[FrontendConfiguration] = Field(
        None, description='Frontend configuration'
    )


class GetMetricsRequest(BaseModel):
    """Request model for getting metrics from a deployed web application."""

    project_name: str = Field(..., description='Project name')
    start_time: Optional[str] = Field(None, description='Start time for metrics (ISO format)')
    end_time: Optional[str] = Field(None, description='End time for metrics (ISO format)')
    period: Optional[int] = Field(60, description='Period for metrics in seconds')
    resources: Optional[List[Literal['lambda', 'apiGateway', 'cloudfront']]] = Field(
        ['lambda', 'apiGateway'], description='Resources to get metrics for'
    )
    region: Optional[str] = Field(None, description='AWS region to use (e.g., us-east-1)')
    stage: Optional[str] = Field('prod', description='API Gateway stage')


class UpdateFrontendRequest(BaseModel):
    """Request model for updating the frontend of a deployed web application."""

    project_name: str = Field(..., description='Project name')
    project_root: str = Field(..., description='Project root')
    built_assets_path: str = Field(..., description='Absolute path to pre-built frontend assets')
    invalidate_cache: Optional[bool] = Field(
        True, description='Whether to invalidate the CloudFront cache'
    )
    region: Optional[str] = Field(None, description='AWS region to use (e.g., us-east-1)')


class ConfigureDomainRequest(BaseModel):
    """Request model for configuring a custom domain for a deployed web application."""

    project_name: str = Field(..., description='Project name')
    domain_name: str = Field(..., description='Custom domain name')
    create_certificate: Optional[bool] = Field(
        True, description='Whether to create a ACM certificate'
    )
    create_route53_record: Optional[bool] = Field(
        True, description='Whether to create a Route 53 record'
    )
    region: Optional[str] = Field(None, description='AWS region to use (e.g., us-east-1)')


class WebappDeploymentHelpRequest(BaseModel):
    """Request model for getting deployment help or status."""

    deployment_type: Literal['backend', 'frontend', 'fullstack'] = Field(
        description='Type of deployment to get help information for'
    )
