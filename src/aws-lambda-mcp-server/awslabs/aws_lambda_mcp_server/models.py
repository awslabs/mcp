"""Models for the AWS Lambda MCP Server."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal, Any
from enum import Enum

class SamBuildRequest(BaseModel):
    """Request model for AWS SAM build command."""
    
    project_directory: str = Field(
        ..., description="Absolute path to directory containing the SAM project (defaults to current directory)"
    )
    resource_id: Optional[str] = Field(
        None, description="ID of the resource to build (builds a single resource)"
    )
    template_file: Optional[str] = Field(
        None, description="Path to the template file (defaults to template.yaml)"
    )
    base_dir: Optional[str] = Field(
        None, description="Resolve relative paths to function's source code with respect to this folder"
    )
    build_dir: Optional[str] = Field(
        None, description="Path to a folder where the built artifacts will be stored"
    )
    cache_dir: Optional[str] = Field(
        None, description="Path to a folder where the built artifacts will be cached"
    )
    cached: bool = Field(
        False, description="Use cached build artifacts if available"
    )
    use_container: bool = Field(
        False, description="Use a container to build the function"
    )
    no_use_container: bool = Field(
        False, description="Run build in local machine instead of Docker container"
    )
    container_env_vars: Optional[Dict[str, str]] = Field(
        None, description="Environment variables to pass to the container"
    )
    container_env_var_file: Optional[str] = Field(
        None, description="Path to a JSON file containing container environment variables"
    )
    skip_pull_image: bool = Field(
        False, description="Skip pulling the latest Docker image for the runtime"
    )
    build_method: Optional[str] = Field(
        None, description="Build method to use"
    )
    build_in_source: bool = Field(
        False, description="Build your project directly in the source folder"
    )
    no_build_in_source: bool = Field(
        False, description="Do not build your project directly in the source folder"
    )
    beta_features: bool = Field(
        False, description="Allow beta features"
    )
    no_beta_features: bool = Field(
        False, description="Deny beta features"
    )
    build_image: Optional[str] = Field(
        None, description="URI of the container image to pull for the build"
    )
    debug: bool = Field(
        False, description="Turn on debug logging"
    )

# Prompts models
class GetIaCGuidanceRequest(BaseModel):
    """Request model for getting Infrastructure as Code guidance."""
    
    resource_type: str = Field(
        ..., description="AWS resource type (e.g., Lambda, DynamoDB, S3)"
    )
    use_case: str = Field(
        ..., description="Description of the use case"
    )
    iac_tool: Optional[Literal["CloudFormation", "SAM", "CDK", "Terraform"]] = Field(
        "CloudFormation", description="IaC tool to use"
    )
    include_examples: Optional[bool] = Field(
        True, description="Whether to include examples"
    )
    advanced_options: Optional[bool] = Field(
        False, description="Whether to include advanced options"
    )

class GetLambdaEventSchemasRequest(BaseModel):
    """Request model for getting Lambda event schemas."""
    
    event_source: str = Field(
        ..., description="Event source (e.g., S3, DynamoDB, API Gateway)"
    )
    runtime: str = Field(
        ..., description="Programming language for the schema references (e.g., go, nodejs, python, java)"
    )

class GetLambdaGuidanceRequest(BaseModel):
    """Request model for getting Lambda guidance."""
    
    runtime: str = Field(
        ..., description="Lambda runtime (e.g., nodejs18.x, python3.9)"
    )
    use_case: str = Field(
        ..., description="Description of the use case"
    )
    event_source: Optional[str] = Field(
        None, description="Event source (e.g., S3, DynamoDB, API Gateway)"
    )
    include_examples: Optional[bool] = Field(
        True, description="Whether to include examples"
    )
    advanced_options: Optional[bool] = Field(
        False, description="Whether to include advanced options"
    )

class GetServerlessTemplatesRequest(BaseModel):
    """Request model for getting serverless templates."""
    
    template_type: str = Field(
        ..., description="Template type (e.g., API, ETL, Web)"
    )
    runtime: Optional[str] = Field(
        None, description="Lambda runtime (e.g., nodejs18.x, python3.9)"
    )

class DeployServerlessAppHelpRequest(BaseModel):
    """Request model for getting serverless app deployment help."""
    
    application_type: Literal["event_driven", "backend", "fullstack"] = Field(
        ..., description="Type of application to deploy"
    )

# WebApp models
class BackendConfiguration(BaseModel):
    """Backend configuration for web application deployment."""
    
    built_artifacts_path: str = Field(
        ..., description="Path to pre-built backend artifacts"
    )
    framework: Optional[str] = Field(
        None, description="Backend framework"
    )
    runtime: str = Field(
        ..., description="Lambda runtime (e.g. nodejs22.x, python3.13)"
    )
    startup_script: Optional[str] = Field(
        None, description="Startup script that must be executable in Linux environment"
    )
    entry_point: Optional[str] = Field(
        None, description="Application entry point file (e.g., app.js, app.py)"
    )
    generate_startup_script: Optional[bool] = Field(
        False, description="Whether to automatically generate a startup script"
    )
    architecture: Optional[Literal["x86_64", "arm64"]] = Field(
        "x86_64", description="Lambda architecture"
    )
    memory_size: Optional[int] = Field(
        512, description="Lambda memory size"
    )
    timeout: Optional[int] = Field(
        30, description="Lambda timeout"
    )
    stage: Optional[str] = Field(
        "prod", description="API Gateway stage"
    )
    cors: Optional[bool] = Field(
        True, description="Enable CORS"
    )
    port: int = Field(
        ..., description="Port on which the web application runs"
    )
    environment: Optional[Dict[str, str]] = Field(
        None, description="Environment variables"
    )
    database_configuration: Optional[Dict[str, Any]] = Field(
        None, description="Database configuration for creating DynamoDB tables"
    )

class FrontendConfiguration(BaseModel):
    """Frontend configuration for web application deployment."""
    
    built_assets_path: str = Field(
        ..., description="Path to pre-built frontend assets"
    )
    framework: Optional[str] = Field(
        None, description="Frontend framework"
    )
    index_document: Optional[str] = Field(
        "index.html", description="Index document"
    )
    error_document: Optional[str] = Field(
        None, description="Error document"
    )
    custom_domain: Optional[str] = Field(
        None, description="Custom domain"
    )
    certificate_arn: Optional[str] = Field(
        None, description="ACM certificate ARN"
    )

class DeployWebAppRequest(BaseModel):
    """Request model for deploying a web application."""
    
    deployment_type: Literal["backend", "frontend", "fullstack"] = Field(
        ..., description="Type of deployment"
    )
    project_name: str = Field(
        ..., description="Project name"
    )
    project_root: str = Field(
        ..., description="Absolute path to the project root directory"
    )
    region: Optional[str] = Field(
        "us-east-1", description="AWS region"
    )
    backend_configuration: Optional[BackendConfiguration] = Field(
        None, description="Backend configuration"
    )
    frontend_configuration: Optional[FrontendConfiguration] = Field(
        None, description="Frontend configuration"
    )

class GetLogsRequest(BaseModel):
    """Request model for getting logs from a deployed web application."""
    
    project_name: str = Field(
        ..., description="Project name"
    )
    start_time: Optional[str] = Field(
        None, description="Start time for logs (ISO format)"
    )
    end_time: Optional[str] = Field(
        None, description="End time for logs (ISO format)"
    )
    limit: Optional[int] = Field(
        100, description="Maximum number of log events to return"
    )
    filter_pattern: Optional[str] = Field(
        None, description="Filter pattern for logs"
    )
    log_group_name: Optional[str] = Field(
        None, description="CloudWatch log group name (if not provided, will use default based on project name)"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )

class GetMetricsRequest(BaseModel):
    """Request model for getting metrics from a deployed web application."""
    
    project_name: str = Field(
        ..., description="Project name"
    )
    metric_names: List[str] = Field(
        ..., description="List of metric names to retrieve"
    )
    start_time: Optional[str] = Field(
        None, description="Start time for metrics (ISO format)"
    )
    end_time: Optional[str] = Field(
        None, description="End time for metrics (ISO format)"
    )
    period: Optional[int] = Field(
        60, description="Period for metrics in seconds"
    )
    statistics: Optional[List[str]] = Field(
        ["Average"], description="Statistics to retrieve"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )

class UpdateFrontendRequest(BaseModel):
    """Request model for updating the frontend of a deployed web application."""
    
    project_name: str = Field(
        ..., description="Project name"
    )
    built_assets_path: str = Field(
        ..., description="Path to pre-built frontend assets"
    )
    invalidate_cache: Optional[bool] = Field(
        True, description="Whether to invalidate the CloudFront cache"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )

class ConfigureDomainRequest(BaseModel):
    """Request model for configuring a custom domain for a deployed web application."""
    
    project_name: str = Field(
        ..., description="Project name"
    )
    domain_name: str = Field(
        ..., description="Custom domain name"
    )
    certificate_arn: str = Field(
        ..., description="ACM certificate ARN"
    )
    hosted_zone_id: Optional[str] = Field(
        None, description="Route 53 hosted zone ID"
    )
    create_route53_record: Optional[bool] = Field(
        True, description="Whether to create a Route 53 record"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )

# API Gateway models
class CreateEndpointRequest(BaseModel):
    """Request model for creating an API Gateway endpoint."""
    
    api_name: str = Field(
        ..., description="Name of the API Gateway"
    )
    description: Optional[str] = Field(
        None, description="Description of the API Gateway"
    )
    endpoint_type: Literal["REGIONAL", "EDGE", "PRIVATE"] = Field(
        "REGIONAL", description="Type of API Gateway endpoint"
    )
    function_name: str = Field(
        ..., description="Name of the Lambda function to integrate with"
    )
    path: str = Field(
        ..., description="Path for the API Gateway endpoint"
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "ANY"] = Field(
        ..., description="HTTP method for the API Gateway endpoint"
    )
    stage_name: str = Field(
        "prod", description="Name of the API Gateway stage"
    )
    cors_enabled: bool = Field(
        False, description="Whether to enable CORS for the API Gateway endpoint"
    )
    cors_origin: Optional[str] = Field(
        "*", description="Allowed origin for CORS"
    )
    cors_headers: Optional[List[str]] = Field(
        None, description="Allowed headers for CORS"
    )
    cors_methods: Optional[List[str]] = Field(
        None, description="Allowed methods for CORS"
    )
    cors_credentials: Optional[bool] = Field(
        False, description="Whether to allow credentials for CORS"
    )
    auth_type: Optional[Literal["NONE", "AWS_IAM", "COGNITO_USER_POOLS", "CUSTOM"]] = Field(
        "NONE", description="Type of authorization for the API Gateway endpoint"
    )
    authorizer_id: Optional[str] = Field(
        None, description="ID of the authorizer for the API Gateway endpoint"
    )
    api_key_required: Optional[bool] = Field(
        False, description="Whether to require an API key for the API Gateway endpoint"
    )
    tags: Optional[Dict[str, str]] = Field(
        None, description="Tags to apply to the API Gateway"
    )

# IAM models
class CreateRoleRequest(BaseModel):
    """Request model for creating an IAM role."""
    
    role_name: str = Field(
        ..., description="Name of the IAM role"
    )
    assume_role_policy_document: Dict[str, Any] = Field(
        ..., description="Trust policy document that grants an entity permission to assume the role"
    )
    description: Optional[str] = Field(
        None, description="Description of the role"
    )
    max_session_duration: Optional[int] = Field(
        3600, description="Maximum session duration in seconds (3600-43200)"
    )
    path: Optional[str] = Field(
        "/", description="Path to the role"
    )
    permissions_boundary: Optional[str] = Field(
        None, description="ARN of the policy that is used to set the permissions boundary"
    )
    tags: Optional[Dict[str, str]] = Field(
        None, description="Tags to attach to the role"
    )
    managed_policy_arns: Optional[List[str]] = Field(
        None, description="List of managed policy ARNs to attach to the role"
    )
    inline_policies: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description="Inline policies to embed in the role"
    )

class UpdateRoleRequest(BaseModel):
    """Request model for updating an IAM role."""
    
    role_name: str = Field(
        ..., description="Name of the IAM role to update"
    )
    assume_role_policy_document: Optional[Dict[str, Any]] = Field(
        None, description="Updated trust policy document"
    )
    description: Optional[str] = Field(
        None, description="Updated description of the role"
    )
    max_session_duration: Optional[int] = Field(
        None, description="Updated maximum session duration in seconds (3600-43200)"
    )
    permissions_boundary: Optional[str] = Field(
        None, description="Updated ARN of the policy that is used to set the permissions boundary"
    )
    managed_policy_arns: Optional[List[str]] = Field(
        None, description="Updated list of managed policy ARNs to attach to the role"
    )
    inline_policies: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description="Updated inline policies to embed in the role"
    )

class DeleteRoleRequest(BaseModel):
    """Request model for deleting an IAM role."""
    
    role_name: str = Field(
        ..., description="Name of the IAM role to delete"
    )

# DynamoDB models
class AttributeDefinition(BaseModel):
    """DynamoDB attribute definition."""
    
    name: str = Field(
        ..., description="Attribute name"
    )
    type: Literal["S", "N", "B"] = Field(
        ..., description="Attribute type (S=String, N=Number, B=Binary)"
    )

class KeySchema(BaseModel):
    """DynamoDB key schema."""
    
    name: str = Field(
        ..., description="Attribute name"
    )
    type: Literal["HASH", "RANGE"] = Field(
        ..., description="Key type (HASH=partition key, RANGE=sort key)"
    )

class CreateTableRequest(BaseModel):
    """Request model for creating a DynamoDB table."""
    
    table_name: str = Field(
        ..., description="Name of the DynamoDB table"
    )
    attribute_definitions: List[AttributeDefinition] = Field(
        ..., description="List of attribute definitions"
    )
    key_schema: List[KeySchema] = Field(
        ..., description="List of key schema elements"
    )
    billing_mode: Literal["PROVISIONED", "PAY_PER_REQUEST"] = Field(
        "PAY_PER_REQUEST", description="Billing mode for the table"
    )
    read_capacity_units: Optional[int] = Field(
        None, description="Read capacity units (required for PROVISIONED billing mode)"
    )
    write_capacity_units: Optional[int] = Field(
        None, description="Write capacity units (required for PROVISIONED billing mode)"
    )
    global_secondary_indexes: Optional[List[Dict[str, Any]]] = Field(
        None, description="Global secondary indexes"
    )
    local_secondary_indexes: Optional[List[Dict[str, Any]]] = Field(
        None, description="Local secondary indexes"
    )
    tags: Optional[Dict[str, str]] = Field(
        None, description="Tags to apply to the table"
    )

class UpdateTableRequest(BaseModel):
    """Request model for updating a DynamoDB table."""
    
    table_name: str = Field(
        ..., description="Name of the DynamoDB table to update"
    )
    billing_mode: Optional[Literal["PROVISIONED", "PAY_PER_REQUEST"]] = Field(
        None, description="Updated billing mode for the table"
    )
    read_capacity_units: Optional[int] = Field(
        None, description="Updated read capacity units"
    )
    write_capacity_units: Optional[int] = Field(
        None, description="Updated write capacity units"
    )
    global_secondary_indexes: Optional[List[Dict[str, Any]]] = Field(
        None, description="Updated global secondary indexes"
    )
    stream_specification: Optional[Dict[str, Any]] = Field(
        None, description="Updated stream specification"
    )

class DeleteTableRequest(BaseModel):
    """Request model for deleting a DynamoDB table."""
    
    table_name: str = Field(
        ..., description="Name of the DynamoDB table to delete"
    )

# Lambda function models
class Runtime(str, Enum):
    """Lambda runtime environments."""
    NODEJS18_X = "nodejs18.x"
    NODEJS20_X = "nodejs20.x"
    NODEJS22_X = "nodejs22.x"
    PYTHON39 = "python3.9"
    PYTHON310 = "python3.10"
    PYTHON311 = "python3.11"
    PYTHON312 = "python3.12"
    PYTHON313 = "python3.13"
    JAVA17 = "java17"
    JAVA21 = "java21"
    DOTNET8 = "dotnet8"
    RUBY32 = "ruby3.2"
    GO1_X = "go1.x"

class CreateFunctionRequest(BaseModel):
    """Request model for creating an AWS Lambda function."""
    
    function_name: str = Field(
        ..., description="Name of the Lambda function"
    )
    runtime: Runtime = Field(
        ..., description="Runtime environment for the Lambda function"
    )
    role: str = Field(
        ..., description="ARN of the execution role for the Lambda function"
    )
    handler: str = Field(
        ..., description="Function handler (e.g., index.handler for Node.js)"
    )
    code_path: Optional[str] = Field(
        None, description="Path to the function code (zip file or directory)"
    )
    s3_bucket: Optional[str] = Field(
        None, description="S3 bucket containing the function code"
    )
    s3_key: Optional[str] = Field(
        None, description="S3 key of the function code"
    )
    s3_object_version: Optional[str] = Field(
        None, description="S3 object version of the function code"
    )
    image_uri: Optional[str] = Field(
        None, description="URI of the container image"
    )
    source_kms_key_arn: Optional[str] = Field(
        None, description="ARN of the KMS key used to encrypt the function code"
    )
    description: Optional[str] = Field(
        None, description="Description of the Lambda function"
    )
    timeout: Optional[int] = Field(
        3, description="Function timeout in seconds (1-900)"
    )
    memory_size: Optional[int] = Field(
        128, description="Function memory in MB (128-10240)"
    )
    environment_variables: Optional[Dict[str, str]] = Field(
        None, description="Environment variables for the Lambda function"
    )
    tags: Optional[Dict[str, str]] = Field(
        None, description="Tags to apply to the Lambda function"
    )
    vpc_config: Optional[Dict[str, Any]] = Field(
        None, description="VPC configuration for the Lambda function"
    )
    dead_letter_config: Optional[Dict[str, str]] = Field(
        None, description="Dead letter queue configuration"
    )
    tracing_config: Optional[Dict[str, str]] = Field(
        None, description="X-Ray tracing configuration"
    )
    layers: Optional[List[str]] = Field(
        None, description="List of Lambda layer ARNs"
    )
    architectures: Optional[List[str]] = Field(
        ["x86_64"], description="CPU architectures (x86_64 or arm64)"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )

class UpdateFunctionRequest(BaseModel):
    """Request model for updating an AWS Lambda function."""
    
    function_name: str = Field(
        ..., description="Name of the Lambda function to update"
    )
    role: Optional[str] = Field(
        None, description="ARN of the execution role for the Lambda function"
    )
    handler: Optional[str] = Field(
        None, description="Function handler (e.g., index.handler for Node.js)"
    )
    code_path: Optional[str] = Field(
        None, description="Path to the updated function code (zip file or directory)"
    )
    s3_bucket: Optional[str] = Field(
        None, description="S3 bucket containing the function code"
    )
    s3_key: Optional[str] = Field(
        None, description="S3 key of the function code"
    )
    s3_object_version: Optional[str] = Field(
        None, description="S3 object version of the function code"
    )
    image_uri: Optional[str] = Field(
        None, description="URI of the container image"
    )
    source_kms_key_arn: Optional[str] = Field(
        None, description="ARN of the KMS key used to encrypt the function code"
    )
    description: Optional[str] = Field(
        None, description="Updated description of the Lambda function"
    )
    timeout: Optional[int] = Field(
        None, description="Updated function timeout in seconds (1-900)"
    )
    memory_size: Optional[int] = Field(
        None, description="Updated function memory in MB (128-10240)"
    )
    environment_variables: Optional[Dict[str, str]] = Field(
        None, description="Updated environment variables for the Lambda function"
    )
    vpc_config: Optional[Dict[str, Any]] = Field(
        None, description="Updated VPC configuration for the Lambda function"
    )
    dead_letter_config: Optional[Dict[str, str]] = Field(
        None, description="Updated dead letter queue configuration"
    )
    tracing_config: Optional[Dict[str, str]] = Field(
        None, description="Updated X-Ray tracing configuration"
    )
    layers: Optional[List[str]] = Field(
        None, description="Updated list of Lambda layer ARNs"
    )
    architectures: Optional[List[str]] = Field(
        None, description="Updated CPU architectures (x86_64 or arm64)"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )

class DeleteFunctionRequest(BaseModel):
    """Request model for deleting an AWS Lambda function."""
    
    function_name: str = Field(
        ..., description="Name of the Lambda function to delete"
    )

class InvokeFunctionRequest(BaseModel):
    """Request model for invoking an AWS Lambda function."""
    
    function_name: str = Field(
        ..., description="Name of the Lambda function to invoke"
    )
    payload: Optional[Dict[str, Any]] = Field(
        None, description="JSON payload to pass to the function"
    )
    invocation_type: Optional[str] = Field(
        "RequestResponse", description="Invocation type (RequestResponse, Event, or DryRun)"
    )
    log_type: Optional[str] = Field(
        "None", description="Log type (None or Tail)"
    )

class ListFunctionsRequest(BaseModel):
    """Request model for listing AWS Lambda functions."""
    
    max_items: Optional[int] = Field(
        50, description="Maximum number of functions to return"
    )
    marker: Optional[str] = Field(
        None, description="Pagination token from a previous request"
    )
    function_version: Optional[str] = Field(
        "ALL", description="Function version to list (ALL or $LATEST)"
    )

class PackageCodeRequest(BaseModel):
    """Request model for packaging Lambda function code."""
    
    source_path: str = Field(
        ..., description="Path to the source code directory"
    )
    output_path: str = Field(
        ..., description="Path where the packaged code will be saved"
    )
    include_dependencies: Optional[bool] = Field(
        True, description="Whether to include dependencies in the package"
    )
    exclude_patterns: Optional[List[str]] = Field(
        None, description="Patterns of files/directories to exclude"
    )
    docker_network: Optional[str] = Field(
        None, description="Name or ID of an existing Docker network for Lambda containers"
    )
    exclude: Optional[List[str]] = Field(
        None, description="Resources to exclude from the build"
    )
    manifest: Optional[str] = Field(
        None, description="Path to a custom dependency manifest file (e.g., package.json)"
    )
    mount_symlinks: bool = Field(
        False, description="Mount symlinks in the build container"
    )
    parallel: bool = Field(
        False, description="Build functions and layers in parallel"
    )
    parameter_overrides: Optional[str] = Field(
        None, description="CloudFormation parameter overrides encoded as key-value pairs"
    )
    region: Optional[str] = Field(
        None, description="AWS Region to deploy to (e.g., us-east-1)"
    )
    save_params: bool = Field(
        False, description="Save parameters to the SAM configuration file"
    )
    skip_prepare_infra: bool = Field(
        False, description="Skip preparation stage if no infrastructure changes"
    )
    terraform_project_root_path: Optional[str] = Field(
        None, description="Path to Terraform configuration files"
    )

class SamInitRequest(BaseModel):
    """Request model for AWS SAM init command."""

    project_name: str = Field(
        ..., description="Name of the SAM project to create"
    )
    architecture: str = Field(
        "x86_64", description="Architecture for the Lambda function"
    )
    package_type: str = Field(
        "Zip", description="Package type for the Lambda function"
    )
    runtime: str = Field(
        ..., description="Runtime environment for the Lambda function"
    )
    project_directory: str = Field(
        ..., description="Absolute path to directory where the SAM application will be initialized"
    )
    dependency_manager: str = Field(
        ..., description="Dependency manager for the Lambda function"
    )
    application_template: str = Field(
        "hello-world", description="Template for the SAM application, e.g., hello-world, quick-start, etc."
    )
    application_insights: Optional[bool] = Field(
        False, description="Activate Amazon CloudWatch Application Insights monitoring"
    )
    no_application_insights: Optional[bool] = Field(
        False, description="Deactivate Amazon CloudWatch Application Insights monitoring"
    )
    base_image: Optional[str] = Field(
        None, description="Base image for the application when package type is Image"
    )
    config_env: Optional[str] = Field(
        None, description="Environment name specifying default parameter values in the configuration file"
    )
    config_file: Optional[str] = Field(
        None, description="Path to configuration file containing default parameter values"
    )
    debug: Optional[bool] = Field(
        False, description="Turn on debug logging"
    )
    extra_content: Optional[str] = Field(
        None, description="Override custom parameters in the template's cookiecutter.json"
    )
    location: Optional[str] = Field(
        None, description="Template or application location (Git, HTTP/HTTPS, zip file path)"
    )
    save_params: Optional[bool] = Field(
        False, description="Save parameters to the SAM configuration file"
    )
    tracing: Optional[bool] = Field(
        False, description="Activate AWS X-Ray tracing for Lambda functions"
    )
    no_tracing: Optional[bool] = Field(
        False, description="Deactivate AWS X-Ray tracing for Lambda functions"
    )

class SamDeployRequest(BaseModel):
    """Request model for AWS SAM deploy command."""
    
    application_name: str = Field(
        ..., description="Name of the application to be deployed"
    )
    project_directory: str = Field(
        ..., description="Absolute path to directory containing the SAM project (defaults to current directory)"
    )
    template_file: Optional[str] = Field(
        None, description="Path to the template file (defaults to template.yaml)"
    )
    s3_bucket: Optional[str] = Field(
        None, description="S3 bucket to deploy artifacts to"
    )
    s3_prefix: Optional[str] = Field(
        None, description="S3 prefix for the artifacts"
    )
    region: Optional[str] = Field(
        None, description="AWS region to deploy to"
    )
    profile: Optional[str] = Field(
        None, description="AWS profile to use"
    )
    parameter_overrides: Optional[str] = Field(
        None, description="CloudFormation parameter overrides encoded as key-value pairs"
    )
    capabilities: Optional[List[Literal["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"]]] = Field(
        ["CAPABILITY_IAM"], description="IAM capabilities required for the deployment"
    )
    no_confirm_changeset: bool = Field(
        True, description="Don't prompt for confirmation before deploying the changeset"
    )
    config_file: Optional[str] = Field(
        None, description="Path to the SAM configuration file"
    )
    config_env: Optional[str] = Field(
        None, description="Environment name specifying default parameter values in the configuration file"
    )
    guided_deploy: bool = Field(
        False, description="Whether to use guided deployment"
    )
    no_execute_changeset: bool = Field(
        False, description="Don't execute the changeset (preview only)"
    )
    fail_on_empty_changeset: bool = Field(
        False, description="Fail the deployment if the changeset is empty"
    )
    force_upload: bool = Field(
        False, description="Force upload artifacts even if they exist in the S3 bucket"
    )
    use_json: bool = Field(
        False, description="Use JSON for output"
    )
    metadata: Optional[Dict[str, str]] = Field(
        None, description="Metadata to include with the stack"
    )
    notification_arns: Optional[List[str]] = Field(
        None, description="SNS topic ARNs to notify about stack events"
    )
    tags: Optional[Dict[str, str]] = Field(
        None, description="Tags to apply to the stack"
    )
    resolve_s3: bool = Field(
        False, description="Automatically create an S3 bucket for deployment artifacts"
    )
    disable_rollback: bool = Field(
        False, description="Disable rollback on deployment failure"
    )
    debug: bool = Field(
        False, description="Turn on debug logging"
    )

class SamLocalInvokeRequest(BaseModel):
    """Request model for AWS SAM local invoke command."""
    
    project_directory: str = Field(
        ..., description="Absolute path to directory containing the SAM project"
    )
    function_name: str = Field(
        ..., description="Name of the Lambda function to invoke locally"
    )
    template_file: Optional[str] = Field(
        None, description="Path to the SAM template file (defaults to template.yaml)"
    )
    event_file: Optional[str] = Field(
        None, description="Path to a JSON file containing event data"
    )
    event_data: Optional[str] = Field(
        None, description="JSON string containing event data (alternative to event_file)"
    )
    environment_variables: Optional[Dict[str, str]] = Field(
        None, description="Environment variables to pass to the function"
    )
    debug_port: Optional[int] = Field(
        None, description="Port for debugging"
    )
    docker_network: Optional[str] = Field(
        None, description="Docker network to run the Lambda function in"
    )
    container_env_vars: Optional[Dict[str, str]] = Field(
        None, description="Environment variables to pass to the container"
    )
    parameter: Optional[Dict[str, str]] = Field(
        None, description="Override parameters from the template file"
    )
    log_file: Optional[str] = Field(
        None, description="Path to a file where the function logs will be written"
    )
    layer_cache_basedir: Optional[str] = Field(
        None, description="Directory where the layers will be cached"
    )
    skip_pull_image: bool = Field(
        False, description="Skip pulling the latest Docker image for the runtime"
    )
    debug_args: Optional[str] = Field(
        None, description="Additional arguments to pass to the debugger"
    )
    debugger_path: Optional[str] = Field(
        None, description="Path to the debugger to use"
    )
    warm_containers: Optional[Literal["EAGER", "LAZY"]] = Field(
        None, description="Warm containers strategy"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )
    profile: Optional[str] = Field(
        None, description="AWS profile to use"
    )

class SamLogsRequest(BaseModel):
    """Request model for AWS SAM logs command."""
    
    function_name: str = Field(
        ..., description="Name of the Lambda function to fetch logs for"
    )
    stack_name: Optional[str] = Field(
        None, description="Name of the CloudFormation stack"
    )
    tail: bool = Field(
        False, description="Continuously poll for new logs"
    )
    filter: Optional[str] = Field(
        None, description="Filter logs by pattern"
    )
    start_time: Optional[str] = Field(
        None, description="Fetch logs starting from this time (format: YYYY-MM-DD HH:MM:SS)"
    )
    end_time: Optional[str] = Field(
        None, description="Fetch logs up until this time (format: YYYY-MM-DD HH:MM:SS)"
    )
    output: Optional[Literal["text", "json"]] = Field(
        "text", description="Output format"
    )
    region: Optional[str] = Field(
        None, description="AWS region to use"
    )
    profile: Optional[str] = Field(
        None, description="AWS profile to use"
    )
    include_triggered_logs: bool = Field(
        False, description="Include logs from explicitly triggered Lambda functions"
    )
    cw: bool = Field(
        False, description="Use AWS CloudWatch to fetch logs"
    )
    resources_dir: Optional[str] = Field(
        None, description="Directory containing resources to fetch logs for"
    )
    template_file: Optional[str] = Field(
        None, description="Path to the SAM template file"
    )

class SamPipelineRequest(BaseModel):
    """Request model for AWS SAM pipeline command."""
    
    project_directory: str = Field(
        ..., description="Absolute path to directory containing the SAM project"
    )
    cicd_provider: Literal["gitlab", "github", "jenkins", "gitlab-ci", "bitbucket-pipelines", "azure-pipelines", "codepipeline"] = Field(
        ..., description="CI/CD provider to generate pipeline configuration for"
    )
    bucket: Optional[str] = Field(
        None, description="S3 bucket to store pipeline artifacts"
    )
    bootstrap_ecr: bool = Field(
        False, description="Whether to create an ECR repository for the pipeline"
    )
    bitbucket_repo_uuid: Optional[str] = Field(
        None, description="The UUID of the Bitbucket repository. This option is specific to using Bitbucket OIDC for permissions"
    )
    cloudformation_execution_role: Optional[str] = Field(
        None, description="The ARN of the IAM role to be assumed by AWS CloudFormation while deploying the application's stack"
    )
    confirm_changes: bool = Field(
        False, description="Whether to confirm changes before creating resources"
    )
    config_env: Optional[str] = Field(
        None, description="Environment name specifying default parameter values in the configuration file"
    )
    config_file: Optional[str] = Field(
        None, description="Path to configuration file containing default parameter values"
    )
    create_image_repository: Optional[bool] = Field(
        None, description="Specify whether to create an Amazon ECR image repository if none is provided"
    )
    debug: bool = Field(
        False, description="Turn on debug logging"
    )
    deployment_branch: Optional[str] = Field(
        None, description="Name of the branch that deployments will occur from. This option is specific to using GitHub Actions OIDC for permissions"
    )
    github_org: Optional[str] = Field(
        None, description="The GitHub organization that the repository belongs to. This option is specific to using GitHub Actions OIDC for permissions"
    )
    gitlab_group: Optional[str] = Field(
        None, description="The GitLab group that the repository belongs to. This option is specific to using GitLab OIDC for permissions"
    )
    gitlab_project: Optional[str] = Field(
        None, description="The GitLab project name. This option is specific to using GitLab OIDC for permissions"
    )
    git_provider: Optional[Literal["codecommit", "github", "gitlab"]] = Field(
        None, description="Git provider for the repository"
    )
    image_repository: Optional[str] = Field(
        None, description="The ARN of an Amazon ECR image repository that holds the container images of Lambda functions or layers"
    )
    interactive: Optional[bool] = Field(
        False, description="Enable/disable interactive prompting for bootstrap parameters"
    )
    oidc_client_id: Optional[str] = Field(
        None, description="The client ID configured for use with your OIDC provider"
    )
    oidc_provider: Optional[Literal["github-actions", "gitlab", "bitbucket-pipelines"]] = Field(
        None, description="Name of the CI/CD provider that will be used for OIDC permissions"
    )
    oidc_provider_url: Optional[str] = Field(
        None, description="The URL for the OIDC provider. Value must begin with https://"
    )
    output_dir: Optional[str] = Field(
        None, description="Directory where the generated pipeline configuration files will be written"
    )
    parameter_overrides: Optional[str] = Field(
        None, description="CloudFormation parameter overrides encoded as key-value pairs"
    )
    permissions_provider: Optional[Literal["oidc", "iam"]] = Field(
        None, description="Choose a permissions provider to assume the pipeline execution role. The default value is iam"
    )
    pipeline_execution_role: Optional[str] = Field(
        None, description="The ARN of the IAM role to be assumed by the pipeline user to operate on this stage"
    )
    pipeline_user: Optional[str] = Field(
        None, description="The Amazon Resource Name (ARN) of the IAM user having its access key ID and secret access key shared with the CI/CD system"
    )
    profile: Optional[str] = Field(
        None, description="AWS profile to use"
    )
    region: Optional[str] = Field(
        None, description="AWS Region to deploy to (e.g., us-east-1)"
    )
    save_params: bool = Field(
        False, description="Save parameters to the SAM configuration file"
    )
    stage: str = Field(
        ..., description="Stage name to be used in the pipeline"
    )

class DeploymentHelpRequest(BaseModel):
    """Request model for getting deployment help or status."""
    
    deployment_type: Literal["backend", "frontend", "fullstack"] = Field(
        description="Type of deployment to get help information for")
