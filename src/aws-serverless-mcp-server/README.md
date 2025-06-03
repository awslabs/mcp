# AWS Serverless MCP Server

## Overview

The AWS Serverless Model Context Protocol (MCP) Server is an open-source tool that combines AI assistance with serverless expertise to streamline how developers build serverless applications. It provides contextual guidance specific to serverless development, helping developers make informed decisions about architecture, implementation, and deployment throughout the entire application development lifecycle. With AWS Serverless MCP, developers can build reliable, efficient, and production-ready serverless applications with confidence.

Key benefits of the Serverless MCP Server include:
- AI-powered serverless development: Provides rich contextual information to AI coding assistants to ensure your serverless application aligns with AWS best practices.
- Comprehensive tooling: Offers tools for initialization, deployment, monitoring, and troubleshooting of serverless applications.
- Architecture guidance: Helps evaluate design choices and select optimal serverless patterns based on application needs. Offers recommendations on event sources, function boundaries, and service integrations.
- Operational best practices: Ensures alignment with AWS architectural principles. Suggests effective use of AWS services for event processing, data persistence, and service communication, and guides implementation of security controls, performance tuning, and cost optimization.
- Security-first approach: Implements built-in guardrails with read-only defaults and controlled access to sensitive data.

## Features
The set of tools provided by the Serverless MCP server can be broken down into four categories:

1. Serverless Application Lifecycle
    - Initialize, build, and deploy Serverless Application Model (SAM) applications with SAM CLI
    - Test Lambda functions locally and remotely
2. Web Application Deployment & Management
    - Deploy full-stack, frontend, and backend web applications onto AWS Serverless using Lambda Web Adapter
    - Update frontend assets and optionally invaliate CloudFront caches
    - Create custom domain names, including certificate and DNS setup
3. Observability
    - Retrieve and logs and metrics of serverless resources
4. Guidance, Templates, and Deployment Help
    - Provides guidance on AWS Lambda use-cases, selecting an IaC framework, and deployment process onto AWS Serverless
    - Provides sample SAM templates for different serverless application types from [Serverless Land](https://serverlessland.com/)
    - Provides schema types for different Lambda event sources and runtimes
    - Provides schema registry management and discovery for AWS EventBridge events
    - Enables type-safe Lambda function development with complete event schemas

## Prerequisites
- Have an AWS account with [credentials configured](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python 3.10 or newer using uv python install 3.10 (or a more recent version)
- Install [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

## Installation

You can download the AWS Serverless MCP Server from GitHub. To get started using your favorite code assistant with MCP support, like Q Developer, Cursor or Cline.

Add the following code to your MCP client configuration. The Serverless MCP server uses the default AWS profile by default. Specify a value in AWS_PROFILE if you want to use a different profile. Similarly, adjust the AWS Region and log level values as needed.
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-serverless-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1"
        },
      "disabled": false,
      "autoApprove": [],
      "timeout": 60
    }
  }
}
```

### Using temporary credentials
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-serverless-mcp-server@latest"],
        "env": {
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
          "AWS_SESSION_TOKEN": "your-session-token",
          "AWS_REGION": "us-east-1"
        },
        "disabled": false,
        "autoApprove": [],
        "timeout": 60
    }
  }
}
```

## Serverless MCP Server configuration options
### `--allow-write`
Enables write access mode, which allows mutating operations and creation of public resources. By default, the server runs in read-only mode, which restricts operations to only perform read actions, preventing any changes to AWS resources.

Mutating operations:
* sam_deploy: Deploys a SAM application into AWS Cloud using CloudFormation
* deploy_webapp: Generates SAM template and deploys a web application into AWS CloudFormation. Creates public resources, including Route 53 DNS records, and CloudFront distributions


### `--allow-sensitive-data-access`
Enables access to sensitive data such as logs. By default, the server restricts access to sensitive data.

Operations returning sensitive data:
* sam_logs: Returns Lambda function logs and API Gateway logs

## Local development

To make changes to this MCP locally and run it:

1. Clone this repository:
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/aws-serverless-mcp-server
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
   python -m awslabs.aws_serverless_mcp_server.server
   ```

5. To use this MCP server with AI clients, add the following to your MCP configuration:
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp-server": {
        "command": "mcp/src/aws-serverless-mcp-server/bin/awslabs.aws-serverless-mcp-server/",
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1",
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

## Environment variables

By default, the default AWS profile is used. However, the server can be configured through environment variables in the MCP configuration:

- `AWS_PROFILE`: AWS CLI profile to use for credentials
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: Explicit AWS credentials (alternative to AWS_PROFILE)
- `AWS_SESSION_TOKEN`: Session token for temporary credentials (used with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARNING, INFO, DEBUG)

## Available resources

The server provides the following resources:

### Template resources
- `template://list`: List of available deployment templates.
- `template://{template_name}`: Details of a specific deployment template.

### Deployment resources
- `deployment://list`: List of all AWS deployments managed by the MCP server.
- `deployment://{project_name}`: Details about a specific deployment.

## Available tools

The server exposes deployment capabilities as tools:

### sam_init

Initializes a serverless application using AWS SAM (Serverless Application Model) CLI.
This tool creates a new SAM project that consists of:
- An AWS SAM template to define your infrastructure code
- A folder structure that organizes your application
- Configuration for your AWS Lambda functions
You should have AWS SAM CLI installed and configured in your environment.

**Parameters:**
- `project_name` (required): Name of the SAM project to create
- `runtime` (required): Runtime environment for the Lambda function
- `project_directory` (required): Absolute path to directory where the SAM application will be initialized
- `dependency_manager` (required): Dependency manager for the Lambda function
- `architecture` (default: x86_64): Architecture for the Lambda function
- `package_type` (default: Zip): Package type for the Lambda function
- `application_template` (default: hello-world): Template for the SAM application, e.g., hello-world, quick-start, etc.
- `application_insights`: Activate Amazon CloudWatch Application Insights monitoring
- `no_application_insights`: Deactivate Amazon CloudWatch Application Insights monitoring
- `base_image`: Base image for the application when package type is Image
- `config_env`: Environment name specifying default parameter values in the configuration file
- `config_file`: Absolute path to configuration file containing default parameter values
- `debug`: Turn on debug logging
- `extra_content`: Override custom parameters in the template's cookiecutter.json
- `location`: Template or application location (Git, HTTP/HTTPS, zip file path)
- `save_params`: Save parameters to the SAM configuration file
- `tracing`: Activate AWS X-Ray tracing for Lambda functions
- `no_tracing`: Deactivate AWS X-Ray tracing for Lambda functions

### sam_build

Builds a serverless application using AWS SAM (Serverless Application Model) CLI.
This command compiles your Lambda function code, creates deployment artifacts, and prepares your application for deployment.
Before running this tool, the application should already be initialized with 'sam_init' tool.
You should have AWS SAM CLI installed and configured in your environment.

**Parameters:**
- `project_directory` (required): Absolute path to directory containing the SAM project
- `template_file`: Absolute path to the template file (defaults to template.yaml)
- `base_dir`: Resolve relative paths to function's source code with respect to this folder
- `build_dir`: The absolute path to a directory where the built artifacts are stored
- `use_container` (default: false): Use a container to build the function
- `no_use_container` (default: false): Run build in local machine instead of Docker container
- `parallel` (default: true): Build your AWS SAM application in parallel
- `container_env_vars`: Environment variables to pass to the build container
- `container_env_var_file`: Absolute path to a JSON file containing container environment variables
- `build_image`: The URI of the container image that you want to pull for the build
- `debug` (default: false): Turn on debug logging
- `manifest`: Absolute path to a custom dependency manifest file (e.g., package.json) instead of the default
- `parameter_overrides`: CloudFormation parameter overrides encoded as key-value pairs
- `region`: AWS Region to deploy to (e.g., us-east-1)
- `save_params` (default: false): Save parameters to the SAM configuration file
- `profile`: AWS profile to use

### sam_deploy

Deploys a serverless application using AWS SAM (Serverless Application Model) CLI.
This command deploys your application to AWS CloudFormation.
Every time an appplication is deployed, it should be built with 'sam_build' tool before.
You should have AWS SAM CLI installed and configured in your environment.

**Parameters:**
- `application_name` (required): Name of the application to be deployed
- `project_directory` (required): Absolute path to directory containing the SAM project (defaults to current directory)
- `template_file`: Absolute path to the template file (defaults to template.yaml)
- `s3_bucket`: S3 bucket to deploy artifacts to
- `s3_prefix`: S3 prefix for the artifacts
- `region`: AWS region to deploy to
- `profile`: AWS profile to use
- `parameter_overrides`: CloudFormation parameter overrides encoded as key-value pairs
- `capabilities` (default: ["CAPABILITY_IAM"]): IAM capabilities required for the deployment
- `config_file`: Absolute path to the SAM configuration file
- `config_env`: Environment name specifying default parameter values in the configuration file
- `metadata`: Metadata to include with the stack
- `tags`: Tags to apply to the stack
- `resolve_s3` (default: false): Automatically create an S3 bucket for deployment artifacts
- `debug` (default: false): Turn on debug logging

### sam_logs

Fetches CloudWatch logs that are generated by resources in a SAM application. Use this tool
to help debug invocation failures and find root causes.

**Parameters:**
- `resource_name`: Name of the resource to fetch logs for (logical ID in CloudFormation/SAM template)
- `stack_name`: Name of the CloudFormation stack
- `start_time`: Fetch logs starting from this time (format: 5mins ago, tomorrow, or YYYY-MM-DD HH:MM:SS)
- `end_time`: Fetch logs up until this time (format: 5mins ago, tomorrow, or YYYY-MM-DD HH:MM:SS)
- `output` (default: text): Output format (text or json)
- `region`: AWS region to use (e.g., us-east-1)
- `profile`: AWS profile to use
- `cw_log_group`: CloudWatch Logs log groups to fetch logs from
- `config_env`: Environment name specifying default parameter values in the configuration file
- `config_file`: Absolute path to configuration file containing default parameter values
- `save_params` (default: false): Save parameters to the SAM configuration file

### sam_local_invoke

Locally invokes a Lambda function using AWS SAM CLI.
This command runs your Lambda function locally in a Docker container that simulates the AWS Lambda environment.
You can use this tool to test your Lambda functions before deploying them to AWS. Docker must be installed and running in your environment.

**Parameters:**
- `project_directory` (required): Absolute path to directory containing the SAM project
- `resource_name` (required): Name of the Lambda function to invoke locally
- `template_file`: Absolute path to the SAM template file (defaults to template.yaml)
- `event_file`: Absolute path to a JSON file containing event data
- `event_data`: JSON string containing event data (alternative to event_file)
- `environment_variables_file`: Absolute path to a JSON file containing environment variables to pass to the function
- `docker_network`: Docker network to run the Lambda function in
- `container_env_vars`: Environment variables to pass to the container
- `parameter`: Override parameters from the template file
- `log_file`: Absolute path to a file where the function logs will be written
- `layer_cache_basedir`: Directory where the layers will be cached
- `region`: AWS region to use (e.g., us-east-1)
- `profile`: AWS profile to use

### get_iac_guidance

Returns guidance on selecting an infrastructure as code (IaC) platform to deploy Serverless application to AWS.
Choices include AWS SAM, CDK, and CloudFormation. Use this tool to decide which IaC tool to use for your Lambda deployments
based on your specific use case and requirements.

**Parameters:**
- `iac_tool` (default: CloudFormation): IaC tool to use (CloudFormation, SAM, CDK, Terraform)
- `include_examples` (default: true): Whether to include examples

### get_lambda_event_schemas

Returns AWS Lambda event schemas for different event sources (e.g. s3, sns, apigw) and programming languages.  Each Lambda event source defines its own schema and language-specific types, which should be used in
the Lambda function handler to correctly parse the event data. If you cannot find a schema for your event source, you can directly parse
the event data as a JSON object. For EventBridge events,
you must use the list_registries, search_schema, and describe_schema tools to access the schema registry directly, get schema definitions,
and generate code processing logic.

**Parameters:**
- `event_source` (required): Event source (e.g., api-gw, s3, sqs, sns, kinesis, eventbridge, dynamodb)
- `runtime` (required): Programming language for the schema references (e.g., go, nodejs, python, java)

### get_lambda_guidance

Use this tool to determine if AWS Lambda is suitable platform to deploy an application.
Returns a comprehensive guide on when to choose AWS Lambda as a deployment platform.
It includes scenarios when to use and not use Lambda, advantages and disadvantages,
decision criteria, and specific guidance for various use cases.

**Parameters:**
- `use_case` (required): Description of the use case
- `include_examples` (default: true): Whether to include examples

### deploy_webapp

Deploy web applications to AWS Serverless, including Lambda as compute, DynamoDB as databases, API GW, ACM Certificates, and Route 53 DNS records.
This tool uses the Lambda Web Adapter framework so that applications can be written in a standard web framework like Express or Next.js can be easily
deployed to Lambda. You do not need to use integrate the code with any adapter framework when using this tool.

**Parameters:**
- `deployment_type` (required): Type of deployment (backend, frontend, fullstack)
- `project_name` (required): Project name
- `project_root` (required): Absolute path to the project root directory
- `region`: AWS Region to deploy to (e.g., us-east-1)
- `backend_configuration`: Backend configuration
- `frontend_configuration`: Frontend configuration

### configure_domain

Configures a custom domain for a deployed web application on AWS Serverless.
This tool sets up Route 53 DNS records, ACM certificates, and CloudFront custom domain mappings as needed.
Use this tool after deploying your web application to associate it with your own domain name.

**Parameters:**
- `project_name` (required): Project name
- `domain_name` (required): Custom domain name
- `create_certificate` (default: true): Whether to create a ACM certificate
- `create_route53_record` (default: true): Whether to create a Route 53 record
- `region`: AWS region to use (e.g., us-east-1)

### webapp_deployment_help

Get help information about using the deploy_webapp to perform web application deployments.
If deployment_type is provided, returns help information for that deployment type.
Otherwise, returns a list of deployments and general help information.

**Parameters:**
- `deployment_type` (required): Type of deployment to get help information for (backend, frontend, fullstack)

### get_metrics

Retrieves CloudWatch metrics from a deployed web application. Use this tool get metrics
on error rates, latency, concurrency, etc.

**Parameters:**
- `project_name` (required): Project name
- `start_time`: Start time for metrics (ISO format)
- `end_time`: End time for metrics (ISO format)
- `period` (default: 60): Period for metrics in seconds
- `resources` (default: ["lambda", "apiGateway"]): Resources to get metrics for
- `region`: AWS region to use (e.g., us-east-1)
- `stage` (default: "prod"): API Gateway stage

### update_webapp_frontend

Update the frontend assets of a deployed web application.
This tool uploads new frontend assets to S3 and optionally invalidates the CloudFront cache.

**Parameters:**
- `project_name` (required): Project name
- `project_root` (required): Project root
- `built_assets_path` (required): Absolute path to pre-built frontend assets
- `invalidate_cache` (default: true): Whether to invalidate the CloudFront cache
- `region`: AWS region to use (e.g., us-east-1)

### deploy_serverless_app_help

Provides instructions on how to deploy a serverless application to AWS Lambda.
Deploying a Lambda application requires generating IaC templates, building the code, packaging
the code, selecting a deployment tool, and executing the deployment commands. For deploying
web applications specifically, use the deploy_webapp tool.

**Parameters:**
- `application_type` (required): Type of application to deploy (event_driven, backend, fullstack)

### get_serverless_templates

Returns example SAM templates from the Serverless Land GitHub repo. Use this tool to get
examples for building serverless applications with AWS Lambda and best practices of serverless architecture.

**Parameters:**
- `template_type` (required): Template type (e.g., API, ETL, Web)
- `runtime`: Lambda runtime (e.g., nodejs22.x, python3.13)

### Schema Tools

#### list_registries

Lists the registries in your account.

**Parameters:**
- `registry_name_prefix`: Limits results to registries starting with this prefix
- `scope`: Filter by registry scope (LOCAL or AWS)
- `limit`: Maximum number of results to return (1-100)
- `next_token`: Pagination token for subsequent requests

#### search_schema

Search for schemas in a registry using keywords.

**Parameters:**
- `keywords` (required): Keywords to search for (prefix with "aws." for service events)
- `registry_name` (required): Registry to search in (use "aws.events" for AWS service events)
- `limit`: Maximum number of results (1-100)
- `next_token`: Pagination token

#### describe_schema

Retrieve the schema definition for the specified schema version.

**Parameters:**
- `registry_name` (required): Registry containing the schema (use "aws.events" for AWS service events)
- `schema_name` (required): Name of schema to retrieve (e.g., "aws.s3@ObjectCreated" for S3 events)
- `schema_version`: Version number of schema (latest by default)

## Example usage

### Creating a Lambda Function with SAM

Example user prompt:

```
I want to build a simple backend for a todo app using Python and deploy it to the cloud with AWS Serverless. Can you help me create a new project called my-todo-app. It should include basic functionality to add and list todos. Once it's set up, please build and deploy it with all the necessary permissions. I don’t need to review the changeset before deployment.
```

This prompt would trigger the AI assistant to:
1. Initialize a new SAM project using a template.
2. Make modifications to code and infra for a todo app.
3. Build the SAM application
4. Deploy the application with CAPABILITY_IAM permissions

### Deploying a Web Application

Example user prompt:

```
I have a full-stack web app built with Node.js called my-web-app, and I want to deploy it to the cloud using AWS. Everything’s ready — both frontend and backend. Can you set it up and deploy it with AWS Lambda so it's live and works smoothly?
```

This prompt would trigger the AI assistant to use the deploy_webapp to deploy the full stack application with the specified configuration.

### Working with EventBridge Schemas

Example user prompt:

```
I need to create a Lambda function that processes autoscaling events. Can you help me find the right event schema and implement type-safe event handling?
```

This prompt would trigger the AI assistant to:
1. Search for autoscaling event schemas in aws.events registry using search_schema
2. Retrieve complete schema definition using describe_schema
3. Generate type-safe handler code based on schema structure
4. Implement validation for required fields

## Security features
1. **AWS Authentication**: Uses AWS credentials from the environment for secure authentication
2. **TLS Verification**: Enforces TLS verification for all AWS API calls
3. **Resource Tagging**: Tags all created resources for traceability
4. **Least Privilege**: Uses IAM roles with appropriate permissions for CloudFormation templates

## Security considerations

### Production use cases
The AWS Serverless MCP Server can be used for production environments with proper security controls in place. For production use cases, consider the following:

* **Read-Only Mode by Default**: The server runs in read-only mode by default, which is safer for production environments. Only explicitly enable write access when necessary.
* **Disable auto-approve**: Require the user to approve each time the AI assitant executes a tool

### Role scoping recommendations
To follow security best practices:

1. **Create dedicated IAM roles** to be used by the AWS Serverless MCP Server with the principle of least privilege
2. **Use separate roles** for read-only and write operations
3. **Implement resource tagging** to limit actions to resources created by the server
4. **Enable AWS CloudTrail** to audit all API calls made by the server
5. **Regularly review** the permissions granted to the server's IAM role
6. **Use IAM Access Analyzer** to identify unused permissions that can be removed

### Sensitive information handling
**IMPORTANT**: Do not pass secrets or sensitive information via allowed input mechanisms:

- Do not include secrets or credentials in CloudFormation templates
- Do not pass sensitive information directly in the prompt to the model

## Links

- [Homepage](https://awslabs.github.io/mcp/)
- [Documentation](https://awslabs.github.io/mcp/servers/aws-serverless-mcp-server/)
- [Source Code](https://github.com/awslabs/mcp.git)
- [Bug Tracker](https://github.com/awslabs/mcp/issues)
- [Changelog](https://github.com/awslabs/mcp/blob/main/src/aws-serverless-mcp-server/CHANGELOG.md)

## License

Apache-2.0
