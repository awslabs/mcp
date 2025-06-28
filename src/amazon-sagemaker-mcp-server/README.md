# Amazon SageMaker MCP Server

## Overview

The Amazon SageMaker Model Context Protocol (MCP) Server is an open-source tool that provides AI assistants with comprehensive access to Amazon SageMaker's machine learning capabilities. This server enables seamless integration between AI coding assistants and SageMaker services, allowing developers to build, train, deploy, and manage machine learning models through natural language interactions.


## Prerequisites

- Have an AWS account with [credentials configured](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)
- Appropriate IAM permissions for SageMaker operations

## Installation

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=awslabs.amazon-sagemaker-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXNhZ2VtYWtlci1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119)

You can download the Amazon SageMaker MCP Server from GitHub. To get started using your favorite code assistant with MCP support, like Q Developer, Cursor, or Cline.

Add the following code to your MCP client configuration. The SageMaker MCP server uses the default AWS profile by default. Specify a value in AWS_PROFILE if you want to use a different profile. Similarly, adjust the AWS Region and log level values as needed.

```json
{
  "mcpServers": {
    "awslabs.amazon-sagemaker-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.amazon-sagemaker-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using temporary credentials

```json
{
  "mcpServers": {
    "awslabs.amazon-sagemaker-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.amazon-sagemaker-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
        "AWS_SESSION_TOKEN": "your-session-token",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Configuration Options

### `--allow-write`
Enables write access mode, which allows mutating operations and creation of resources. By default, the server runs in read-only mode, which restricts operations to only perform read actions, preventing any changes to AWS resources.

Write operations include:
- Creating and deleting SageMaker Studio Space apps
- Starting and stopping notebook instances

### `--allow-sensitive-data-access`
Enables access to sensitive data operations, such as:
- Invoking SageMaker endpoints and accessing inference results

## Environment Variables

- `AWS_PROFILE`: AWS profile to use (default: default)
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID`: AWS access key ID (for temporary credentials)
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key (for temporary credentials)
- `AWS_SESSION_TOKEN`: AWS session token (for temporary credentials)
- `FASTMCP_LOG_LEVEL`: Log level (DEBUG, INFO, WARNING, ERROR)

## Available MCP Tools

The SageMaker MCP server provides the following tools organized by category:

### Notebook Instance Management

#### `list_sm_nb_instances`
List SageMaker notebook instances with optional filtering and sorting.

**Parameters:**
- `sort_by` (optional): Sort criteria - Name, CreationTime, Status (default: CreationTime)
- `sort_order` (optional): Sort order - Ascending, Descending (default: Descending)
- `name_contains` (optional): Filter instances by name containing this string
- `status_equals` (optional): Filter instances by status
- `max_results` (optional): Maximum number of results to return (default: 10)

#### `describe_sm_nb_instance`
Get detailed information about a specific SageMaker notebook instance.

**Parameters:**
- `notebook_instance_name` (required): Name of the notebook instance

#### `start_sm_nb_instance`
Start a stopped SageMaker notebook instance.

**Parameters:**
- `notebook_instance_name` (required): Name of the notebook instance

*Requires `--allow-write` flag*

#### `stop_sm_nb_instance`
Stop a running SageMaker notebook instance.

**Parameters:**
- `notebook_instance_name` (required): Name of the notebook instance

*Requires `--allow-write` flag*

### SageMaker Studio Space App Management

#### `list_sm_space_apps`
List SageMaker Space apps with optional filtering and sorting.

**Parameters:**
- `sort_by` (optional): Sort criteria - Name, CreationTime, Status (default: CreationTime)
- `sort_order` (optional): Sort order - Ascending, Descending (default: Descending)
- `domain_id_contains` (optional): Filter apps by Domain Id
- `space_name_contains` (optional): Filter apps by space name
- `max_results` (optional): Maximum number of results to return (default: 10)

#### `create_sm_space_app`
Create a new SageMaker Space app.

**Parameters:**
- `domain_id` (required): Domain ID of the app
- `space_name` (required): Space name of the app
- `app_type` (required): Type of the app (JupyterServer, KernelGateway, or Space)
- `app_name` (required): Name of the app

*Requires `--allow-write` flag*

#### `delete_sm_space_app`
Stop/Delete a SageMaker Space app.

**Parameters:**
- `domain_id` (required): Domain ID of the app
- `space_name` (required): Space name of the app
- `app_type` (required): Type of the app (JupyterServer, KernelGateway, DetailedProfiler, TensorBoard, CodeEditor, JupyterLab, RStudioServerPro, RSessionGateway, Canvas)
- `app_name` (required): Name of the app

*Requires `--allow-write` flag*

### SageMaker Studio Domain Management

#### `list_sm_domains`
List SageMaker Studio domains in your AWS account.

**Parameters:**
- `max_results` (optional): Maximum number of results to return (default: 10)

#### `describe_sm_domain`
Get detailed information about a specific SageMaker Studio domain.

**Parameters:**
- `domain_id` (required): Unique identifier of the domain

### SageMaker Endpoint Management

#### `list_sm_endpoints`
List SageMaker endpoints with optional filtering and sorting.

**Parameters:**
- `sort_by` (optional): Sort criteria - Name, CreationTime, Status (default: CreationTime)
- `sort_order` (optional): Sort order - Ascending, Descending (default: Descending)
- `name_contains` (optional): Filter endpoints by name containing this string
- `status_equals` (optional): Filter endpoints by status
- `max_results` (optional): Maximum number of results to return (default: 10)

#### `describe_sm_endpoint`
Get detailed information about a specific SageMaker endpoint.

**Parameters:**
- `endpoint_name` (required): Name of the endpoint to describe

#### `invoke_sm_endpoint`
Invoke a SageMaker endpoint for real-time inference with input data.

**Parameters:**
- `endpoint_name` (required): Name of the endpoint to invoke
- `body` (required): Input data for the endpoint (JSON string)
- `content_type` (optional): Content type of the input data (default: application/json)
- `accept` (optional): Accept header for the response (default: application/json)

*Requires `--allow-sensitive-data-access` flag*

## Usage Examples

### Managing Notebook Instances

```
Using the SageMaker MCP server, help me:
1. List all my notebook instances
2. Start a specific notebook instance named "my-notebook"
3. Check the status of the notebook instance
4. Stop the notebook instance when finished
```

### Managing Studio Space Apps

```
Using the SageMaker MCP server, help me:
1. List all my Studio Space apps
2. Create a new JupyterLab app in domain "d-123456789" and space "my-space"
3. Monitor the app status
4. Delete the app when finished
```

### Working with Endpoints

```
Using the SageMaker MCP server, help me:
1. List all my SageMaker endpoints
2. Get detailed information about a specific endpoint
3. Invoke the endpoint with sample data for inference
4. Analyze the inference results
```

### Managing Studio Domains

```
Using the SageMaker MCP server, help me:
1. List all my SageMaker Studio domains
2. Get detailed information about a specific domain
3. Understand the domain configuration and settings
```

## IAM Permissions

The SageMaker MCP server requires appropriate IAM permissions to access SageMaker services. Here's a sample IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:ListNotebookInstances",
        "sagemaker:DescribeNotebookInstance",
        "sagemaker:StartNotebookInstance",
        "sagemaker:StopNotebookInstance",
        "sagemaker:ListApps",
        "sagemaker:CreateApp",
        "sagemaker:DeleteApp",
        "sagemaker:ListDomains",
        "sagemaker:DescribeDomain",
        "sagemaker:ListEndpoints",
        "sagemaker:DescribeEndpoint",
        "sagemaker-runtime:InvokeEndpoint"
      ],
      "Resource": "*"
    }
  ]
}
```

## Security Considerations

- The server runs in read-only mode by default to prevent accidental modifications
- Write operations require explicit `--allow-write` flag
- Sensitive data access requires explicit `--allow-sensitive-data-access` flag
- All AWS API calls use the configured AWS credentials and respect IAM permissions
- Endpoint invocations and sensitive data are only accessible with appropriate flags

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Ensure AWS credentials are properly configured
2. **Permission Denied**: Check IAM permissions for SageMaker operations
3. **Region Mismatch**: Ensure AWS_REGION matches your SageMaker resources
4. **Write Operations Blocked**: Ensure `--allow-write` flag is set for mutating operations
5. **Sensitive Data Access Blocked**: Ensure `--allow-sensitive-data-access` flag is set for endpoint invocations

### Debug Mode

Enable debug logging by setting:
```bash
export FASTMCP_LOG_LEVEL=DEBUG
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](../../CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache-2.0 License. See the [LICENSE](../../LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in the [GitHub repository](https://github.com/awslabs/mcp/issues)
- Check the [AWS SageMaker documentation](https://docs.aws.amazon.com/sagemaker/)
- Review the [MCP specification](https://modelcontextprotocol.io/)
