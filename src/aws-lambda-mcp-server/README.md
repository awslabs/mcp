# AWS Lambda MCP Server

A Model Context Protocol (MCP) server that provides tools and resources for deploying and managing applications on AWS Lambda.

## Overview

This MCP server enables AI assistants to deploy, update, invoke, and manage AWS Lambda functions and related serverless resources. It provides a set of tools and resources that can be used to interact with AWS Serverless services.

## Prerequisites
- Python 3.10 or higher
- AWS SAM CLI
- AWS CLI
- AWS credentials configured

## Installation

To use this MCP server with AI clients, add the following to your MCP configuration:
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp": {
      "command": "uvx",
      "args": [
        "awslabs.aws_lambda_mcp_server@latest"
      ],
      "disabled": false
    }
  }
}
```

## Local Development

To make changes to this MCP locally and run it:

1. Clone this repository:
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/aws-lambda-mcp-server
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Configure AWS credentials:
   - Ensure you have AWS credentials configured in `~/.aws/credentials` or set the appropriate environment variables.
   - You can also set the AWS_PROFILE and AWS_REGION environment variables.

4. Run the server:
   ```bash
   python -m awslabs.aws_lambda_mcp_server.server
   ```

5. To use this MCP server with AI clients, add the following to your MCP configuration:
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp": {
      "command": "python",
      "args": [
        "-m", "awslabs.aws_lambda_mcp_server.server"
      ],
      "disabled": false
    }
  }
}
```

## Configuration

The server can be configured through environment variables:

- `AWS_REGION`: AWS region to use
- `AWS_PROFILE`: AWS credentials profile to use

## Available Tools

Exposes deployment capabilities as tools:

### sam_build_tool

Builds a serverless application using AWS SAM (Serverless Application Model) CLI.

**Parameters:**
- `project_directory` (required): Absolute path to directory containing the SAM project
- `resource_id`: ID of the resource to build (builds a single resource)
- `template_file`: Path to the template file (defaults to template.yaml)
- `base_dir`: Resolve relative paths to function's source code with respect to this folder
- `build_dir`: Path to a folder where the built artifacts will be stored
- `cache_dir`: Path to a folder where the built artifacts will be cached
- `cached`: Use cached build artifacts if available
- `use_container`: Use a container to build the function
- `no_use_container`: Run build in local machine instead of Docker container
- `container_env_vars`: Environment variables to pass to the container
- `container_env_var_file`: Path to a JSON file containing container environment variables
- `skip_pull_image`: Skip pulling the latest Docker image for the runtime
- `build_method`: Build method to use
- `build_in_source`: Build your project directly in the source folder
- `no_build_in_source`: Do not build your project directly in the source folder
- `beta_features`: Allow beta features
- `no_beta_features`: Deny beta features
- `build_image`: URI of the container image to pull for the build
- `debug`: Turn on debug logging

### sam_init_tool

Initializes a serverless application using AWS SAM (Serverless Application Model) CLI.

**Parameters:**
- `project_name` (required): Name of the SAM project to create
- `runtime` (required): Runtime environment for the Lambda function
- `project_directory` (required): Absolute path to directory where the SAM application will be initialized
- `dependency_manager` (required): Dependency manager for the Lambda function
- `architecture`: Architecture for the Lambda function
- `package_type`: Package type for the Lambda function
- `application_template`: Template for the SAM application, e.g., hello-world, quick-start, etc.
- `application_insights`: Activate Amazon CloudWatch Application Insights monitoring
- `no_application_insights`: Deactivate Amazon CloudWatch Application Insights monitoring
- `base_image`: Base image for the application when package type is Image
- `config_env`: Environment name specifying default parameter values in the configuration file
- `config_file`: Path to configuration file containing default parameter values
- `debug`: Turn on debug logging
- `extra_content`: Override custom parameters in the template's cookiecutter.json
- `location`: Template or application location (Git, HTTP/HTTPS, zip file path)
- `save_params`: Save parameters to the SAM configuration file
- `tracing`: Activate AWS X-Ray tracing for Lambda functions
- `no_tracing`: Deactivate AWS X-Ray tracing for Lambda functions

### sam_deploy_tool

Deploys a serverless application using AWS SAM (Serverless Application Model) CLI.

**Parameters:**
- `application_name` (required): Name of the application to be deployed
- `project_directory` (required): Absolute path to directory containing the SAM project
- `template_file`: Path to the template file (defaults to template.yaml)
- `s3_bucket`: S3 bucket to deploy artifacts to
- `s3_prefix`: S3 prefix for the artifacts
- `region`: AWS region to deploy to
- `profile`: AWS profile to use
- `parameter_overrides`: CloudFormation parameter overrides encoded as key-value pairs
- `capabilities`: IAM capabilities required for the deployment
- `no_confirm_changeset`: Don't prompt for confirmation before deploying the changeset
- `config_file`: Path to the SAM configuration file
- `config_env`: Environment name specifying default parameter values in the configuration file
- `guided_deploy`: Whether to use guided deployment
- `no_execute_changeset`: Don't execute the changeset (preview only)
- `fail_on_empty_changeset`: Fail the deployment if the changeset is empty
- `force_upload`: Force upload artifacts even if they exist in the S3 bucket
- `use_json`: Use JSON for output
- `metadata`: Metadata to include with the stack
- `notification_arns`: SNS topic ARNs to notify about stack events
- `tags`: Tags to apply to the stack
- `resolve_s3`: Automatically create an S3 bucket for deployment artifacts
- `disable_rollback`: Disable rollback on deployment failure
- `debug`: Turn on debug logging

### create_function_tool

Creates a new AWS Lambda function.

**Parameters:**
- `function_name` (required): Name of the Lambda function
- `runtime` (required): Runtime environment for the Lambda function
- `role` (required): ARN of the execution role for the Lambda function
- `handler` (required): Function handler (e.g., index.handler for Node.js)
- `code_path`: Path to the function code (zip file or directory)
- `s3_bucket`: S3 bucket containing the function code
- `s3_key`: S3 key of the function code
- `s3_object_version`: S3 object version of the function code
- `image_uri`: URI of the container image
- `source_kms_key_arn`: ARN of the KMS key used to encrypt the function code
- `description`: Description of the Lambda function
- `timeout`: Function timeout in seconds (1-900)
- `memory_size`: Function memory in MB (128-10240)
- `environment_variables`: Environment variables for the Lambda function
- `tags`: Tags to apply to the Lambda function
- `vpc_config`: VPC configuration for the Lambda function
- `dead_letter_config`: Dead letter queue configuration
- `tracing_config`: X-Ray tracing configuration
- `layers`: List of Lambda layer ARNs
- `architectures`: CPU architectures (x86_64 or arm64)
- `region`: AWS region to use

### update_function_tool

Updates an existing AWS Lambda function.

**Parameters:**
- `function_name` (required): Name of the Lambda function to update
- `role`: ARN of the execution role for the Lambda function
- `handler`: Function handler (e.g., index.handler for Node.js)
- `code_path`: Path to the updated function code (zip file or directory)
- `s3_bucket`: S3 bucket containing the function code
- `s3_key`: S3 key of the function code
- `s3_object_version`: S3 object version of the function code
- `image_uri`: URI of the container image
- `source_kms_key_arn`: ARN of the KMS key used to encrypt the function code
- `description`: Updated description of the Lambda function
- `timeout`: Updated function timeout in seconds (1-900)
- `memory_size`: Updated function memory in MB (128-10240)
- `environment_variables`: Updated environment variables for the Lambda function
- `vpc_config`: Updated VPC configuration for the Lambda function
- `dead_letter_config`: Updated dead letter queue configuration
- `tracing_config`: Updated X-Ray tracing configuration
- `layers`: Updated list of Lambda layer ARNs
- `architectures`: Updated CPU architectures (x86_64 or arm64)
- `region`: AWS region to use

### get_iac_guidance_tool

Returns guidance on selecting an infrastructure as code (IaC) platform to deploy Serverless application to AWS.

**Parameters:**
- `resource_type` (required): AWS resource type (e.g., Lambda, DynamoDB, S3)
- `use_case` (required): Description of the use case
- `iac_tool`: IaC tool to use (CloudFormation, SAM, CDK, Terraform)
- `include_examples`: Whether to include examples
- `advanced_options`: Whether to include advanced options

### get_lambda_event_schemas_tool

Returns AWS Lambda event schemas for different event sources and programming languages.

**Parameters:**
- `event_source` (required): Event source (e.g., S3, DynamoDB, API Gateway)
- `runtime` (required): Programming language for the schema references (e.g., go, nodejs, python, java)

### get_lambda_guidance_tool

Returns guidance on when to choose AWS Lambda as a deployment platform.

**Parameters:**
- `runtime` (required): Lambda runtime (e.g., nodejs18.x, python3.9)
- `use_case` (required): Description of the use case
- `event_source`: Event source (e.g., S3, DynamoDB, API Gateway)
- `include_examples`: Whether to include examples
- `advanced_options`: Whether to include advanced options

### deploy_web_app_tool

Deploy web applications to AWS, including database resources like DynamoDB tables.

**Parameters:**
- `deployment_type` (required): Type of deployment (backend, frontend, fullstack)
- `project_name` (required): Project name
- `project_root` (required): Absolute path to the project root directory
- `region`: AWS region
- `backend_configuration`: Backend configuration
- `frontend_configuration`: Frontend configuration

### configure_domain_tool

Configure a custom domain for a deployed web application.

**Parameters:**
- `project_name` (required): Project name
- `domain_name` (required): Custom domain name
- `certificate_arn` (required): ACM certificate ARN
- `hosted_zone_id`: Route 53 hosted zone ID
- `create_route53_record`: Whether to create a Route 53 record
- `region`: AWS region to use

### deployment_help_tool

Get help information about deployments or deployment status.

**Parameters:**
- `project_name`: Project name
- `deployment_type`: Type of deployment (backend, frontend, fullstack)

### get_logs_tool

Get logs from a deployed web application.

**Parameters:**
- `project_name` (required): Project name
- `start_time`: Start time for logs (ISO format)
- `end_time`: End time for logs (ISO format)
- `limit`: Maximum number of log events to return
- `filter_pattern`: Filter pattern for logs
- `log_group_name`: CloudWatch log group name
- `region`: AWS region to use

### get_metrics_tool

Get metrics from a deployed web application.

**Parameters:**
- `project_name` (required): Project name
- `metric_names` (required): List of metric names to retrieve
- `start_time`: Start time for metrics (ISO format)
- `end_time`: End time for metrics (ISO format)
- `period`: Period for metrics in seconds
- `statistics`: Statistics to retrieve
- `region`: AWS region to use

### update_frontend_tool

Update the frontend of a deployed web application.

**Parameters:**
- `project_name` (required): Project name
- `built_assets_path` (required): Path to pre-built frontend assets
- `invalidate_cache`: Whether to invalidate the CloudFront cache
- `region`: AWS region to use

### deploy_serverless_app_help_tool

Provides instructions on how to deploy a serverless application to AWS Lambda.

**Parameters:**
- `application_type` (required): Type of application to deploy (event_driven, backend, fullstack)

### get_serverless_templates_tool

Returns example SAM templates from the Serverless Land GitHub repo.

**Parameters:**
- `template_type` (required): Template type (e.g., API, ETL, Web)
- `runtime`: Lambda runtime (e.g., nodejs18.x, python3.9)
- `include_examples`: Whether to include examples

### sam_local_invoke_tool

Locally invokes a Lambda function using AWS SAM CLI.

**Parameters:**
- `project_directory` (required): Absolute path to directory containing the SAM project
- `function_name` (required): Name of the Lambda function to invoke locally
- `template_file`: Path to the SAM template file (defaults to template.yaml)
- `event_file`: Path to a JSON file containing event data
- `event_data`: JSON string containing event data (alternative to event_file)
- `environment_variables`: Environment variables to pass to the function
- `debug_port`: Port for debugging
- `docker_network`: Docker network to run the Lambda function in
- `container_env_vars`: Environment variables to pass to the container
- `parameter`: Override parameters from the template file
- `log_file`: Path to a file where the function logs will be written
- `layer_cache_basedir`: Directory where the layers will be cached
- `skip_pull_image`: Skip pulling the latest Docker image for the runtime
- `debug_args`: Additional arguments to pass to the debugger
- `debugger_path`: Path to the debugger to use
- `warm_containers`: Warm containers strategy
- `region`: AWS region to use
- `profile`: AWS profile to use

## Example Usage

### Creating a Lambda Function

```python
from awslabs.aws_lambda_mcp_server.models import CreateFunctionRequest

request = CreateFunctionRequest(
    function_name="my-function",
    runtime="python3.9",
    role="arn:aws:iam::123456789012:role/lambda-role",
    handler="index.handler",
    code_path="/path/to/function/code",
    timeout=10,
    memory_size=256,
    environment_variables={
        "STAGE": "dev",
        "API_URL": "https://api.example.com"
    }
)

# Using the MCP client
result = await mcp_client.use_tool("aws-serverless-mcp", "create_function_tool", {"request": request.dict()})
```

### Initializing a SAM Project

```python
from awslabs.aws_lambda_mcp_server.models import SamInitRequest

request = SamInitRequest(
    project_name="my-sam-app",
    runtime="python3.9",
    project_directory="/path/to/project",
    dependency_manager="pip",
    application_template="hello-world"
)

# Using the MCP client
result = await mcp_client.use_tool("aws-serverless-mcp", "sam_init_tool", {"request": request.dict()})
```

### Deploying a SAM Application

```python
from awslabs.aws_lambda_mcp_server.models import SamDeployRequest

request = SamDeployRequest(
    application_name="my-sam-app",
    project_directory="/path/to/project",
    capabilities=["CAPABILITY_IAM"],
    no_confirm_changeset=True
)

# Using the MCP client
result = await mcp_client.use_tool("aws-serverless-mcp", "sam_deploy_tool", {"request": request.dict()})
```

### Deploying a Web Application

```python
from awslabs.aws_lambda_mcp_server.models import DeployWebAppRequest, BackendConfiguration

request = DeployWebAppRequest(
    deployment_type="backend",
    project_name="my-web-app",
    project_root="/path/to/project",
    backend_configuration=BackendConfiguration(
        built_artifacts_path="/path/to/artifacts",
        runtime="nodejs18.x",
        port=3000,
        memory_size=512,
        timeout=30
    )
)

# Using the MCP client
result = await mcp_client.use_tool("aws-serverless-mcp", "deploy_web_app_tool", {"request": request.dict()})
```

## License

Apache-2.0
