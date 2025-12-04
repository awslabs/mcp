# AWS Bedrock Custom Model Import MCP Server

## Overview

The Bedrock Custom Model Import Model Context Protocol (MCP) Server streamlines the process of importing custom models into Amazon Bedrock. It provides a comprehensive set of tools for managing model import jobs and imported models, enabling developers to efficiently integrate their custom models with Amazon Bedrock's capabilities.

Key benefits of the Bedrock Custom Model Import MCP Server include:

- **AI-powered model management**: Provides rich contextual information to AI coding assistants to ensure your model import operations align with AWS best practices.
- **Comprehensive tooling**: Offers tools for creating, monitoring, and managing model import jobs and imported models.
- **Operational best practices**: Ensures alignment with AWS architectural principles for model import operations and management.

## Features

The set of tools provided by the Bedrock Custom Model Import MCP server can be broken down into two categories:

1. Handle model imports
   - Create new model import jobs
   - List existing model import jobs
   - Get details of specific model import jobs
2. Manage imported models
   - List imported models
   - Get details of specific imported models
   - Delete imported models

## Prerequisites

- Have an AWS account with [credentials configured](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)
- Install uv from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
- Install Python 3.12 or newer using uv python install 3.12 (or a more recent version)
- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Have access to Amazon Bedrock with appropriate permissions

## Installation

|                                                                                                                                                                                                                Cursor                                                                                                                                                                                                                |                                                                                                                                                                                                                                                                            VS Code                                                                                                                                                                                                                                                                            |
| :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-bedrock-custom-model-import-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWJlZHJvY2stY3VzdG9tLW1vZGVsLWltcG9ydC1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20Custom%20Model%20Import%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-bedrock-custom-model-import-mcp-server%40latest%22%2C%22--allow-write%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

You can download the Bedrock Custom Model Import MCP Server from GitHub. To get started using your favorite code assistant with MCP support, like Q Developer, Cursor or Cline.

Add the following code to your MCP client configuration. The server uses the default AWS profile by default. Specify a value in AWS_PROFILE if you want to use a different profile. Similarly, adjust the AWS Region and log level values as needed.

```json
{
  "mcpServers": {
    "awslabs.aws-bedrock-custom-model-import-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-bedrock-custom-model-import-mcp-server@latest",
        "--allow-write"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_IMPORT_S3_BUCKET": "your-model-bucket",
        "BEDROCK_MODEL_IMPORT_ROLE_ARN": "your-role-arn"
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
    "awslabs.aws-bedrock-custom-model-import-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-bedrock-custom-model-import-mcp-server@latest"],
      "env": {
        "AWS_ACCESS_KEY_ID": "your-temporary-access-key", // pragma: allowlist secret
        "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key", // pragma: allowlist secret
        "AWS_SESSION_TOKEN": "your-session-token", // pragma: allowlist secret
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_IMPORT_S3_BUCKET": "your-model-bucket",
        "BEDROCK_MODEL_IMPORT_ROLE_ARN": "your-role-arn"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Environment Variables

The server can be configured through environment variables in the MCP configuration:

### AWS Authentication

- `AWS_PROFILE`: AWS CLI profile to use for credentials
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: Explicit AWS credentials (alternative to AWS_PROFILE)
- `AWS_SESSION_TOKEN`: Session token for temporary credentials (used with `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`)

**Note**: If you intend to authenticate with [Amazon Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html), ensure your IAM policy includes the `iam:PassRole` permission, which is required to import a model.

### Bedrock Model Import Configuration

- `BEDROCK_MODEL_IMPORT_S3_BUCKET` (required): S3 bucket containing model files. If specified, the server will automatically search this bucket for model files based on the model name.
- `BEDROCK_MODEL_IMPORT_ROLE_ARN` (optional): IAM execution role ARN to use for model import jobs. If not specified, the server will assume the role from the credentials.

### Other Configuration

- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARNING, INFO, DEBUG)

## Local development

To make changes to this MCP locally and run it:

1. Clone this repository:

   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/aws-bedrock-custom-model-import-mcp-server
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
   python -m awslabs.aws_bedrock_custom_model_import_mcp_server.server
   ```

5. To use this MCP server with AI clients, add the following to your MCP configuration:

```json
{
  "mcpServers": {
    "awslabs.aws-bedrock-custom-model-import-mcp-server": {
      "command": "mcp/src/aws-bedrock-custom-model-import-mcp-server/bin/awslabs.aws-bedrock-custom-model-import-mcp-server/",
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_IMPORT_S3_BUCKET": "your-model-bucket",
        "BEDROCK_MODEL_IMPORT_ROLE_ARN": "your-role-arn"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Available tools

The server exposes model import capabilities as tools:

### create_model_import_job

Creates a new model import job in Amazon Bedrock.

**Parameters**:

- `jobName` (required)

  - Name of the model import job
  - Maximum length: 50 characters
  - Must be unique within your account

- `importedModelName` (required)

  - Name of the model to import
  - Maximum length: 50 characters
  - Used to identify the model in Bedrock

- `roleArn` (optional)

  - ARN of the IAM role for the import job
  - If not provided, uses BEDROCK_MODEL_IMPORT_ROLE_ARN from environment
  - Role must have necessary permissions for model import

- `modelDataSource` (conditional)

  - Required if BEDROCK_MODEL_IMPORT_S3_BUCKET is not set
  - Contains S3 data source configuration:
    - s3Uri: S3 URI pointing to model data

- `jobTags` (optional)

  - List of tags to apply to the import job
  - Each tag has:
    - key: Tag key (required)
    - value: Tag value (required)

- `importedModelTags` (optional)

  - List of tags to apply to the imported model
  - Same structure as jobTags

- `clientRequestToken` (optional)

  - Idempotency token for the request
  - Helps prevent duplicate job creation

- `vpcConfig` (optional)

  - VPC configuration for network isolation
  - Contains:
    - subnetIds: List of subnet IDs
    - securityGroupIds: List of security group IDs

- `importedModelKmsKeyId` (optional)
  - KMS key ID for encrypting the imported model
  - Must have necessary permissions for Bedrock

### list_model_import_jobs

Lists existing model import jobs in Amazon Bedrock.

**Parameters**:

- `creationTimeAfter` (optional)

  - Filter jobs created after this datetime
  - Format: ISO 8601 datetime string

- `creationTimeBefore` (optional)

  - Filter jobs created before this datetime
  - Format: ISO 8601 datetime string

- `statusEquals` (optional)

  - Filter jobs by status
  - Valid values: InProgress, Completed, Failed

- `nameContains` (optional)

  - Filter jobs by name substring
  - Case-sensitive search

- `sortBy` (optional)

  - Field to sort results by
  - Example: CreationTime

- `sortOrder` (optional)
  - Order of sorted results
  - Valid values: Ascending, Descending

### list_imported_models

Lists models that have been successfully imported into Amazon Bedrock.

**Parameters**:

- `creationTimeBefore` (optional)

  - Filter models created before this datetime
  - Format: ISO 8601 datetime string

- `creationTimeAfter` (optional)

  - Filter models created after this datetime
  - Format: ISO 8601 datetime string

- `nameContains` (optional)

  - Filter models by name substring
  - Case-sensitive search

- `sortBy` (optional)

  - Field to sort results by
  - Example: CreationTime

- `sortOrder` (optional)
  - Order of sorted results
  - Valid values: Ascending, Descending

### get_model_import_job

Gets detailed information about a specific model import job.

**Parameters**:

- `job_identifier` (required)
  - Name or ARN of the job to get details for
  - Must be an existing job name

### get_imported_model

Gets detailed information about a specific imported model.

**Parameters**:

- `model_identifier` (required)
  - Name or ARN of the model to get details for
  - Must be an existing imported model name

### delete_imported_model

Deletes an imported model from Amazon Bedrock.

**Parameters**:

- `model_identifier` (required)
  - Identifier of the model to delete
  - Must be an existing imported model identifier

## Example usage

### Creating a Model Import Job

Example user prompt:

```
I want to import a Llama 3.3 model into Bedrock. Can you help me create a new import job?
```

This prompt would trigger the AI assistant to use the `create_model_import_job` tool with appropriate configuration, automatically searching the configured S3 bucket for the model artifacts.

### Monitoring Import Jobs

Example user prompt:

```
Show me all the model import jobs I have running in Bedrock?
```

This prompt would trigger the AI assistant to use the `list_model_import_jobs` tool to display all jobs and their current status.

## Security features

1. **AWS Authentication**: Uses AWS credentials from the environment for secure authentication
2. **TLS Verification**: Enforces TLS verification for all AWS API calls
3. **Resource Tagging**: Tags all created resources for traceability
4. **Least Privilege**: Uses IAM roles with appropriate permissions for model import operations

## Security considerations

### Production use cases

The Bedrock Custom Model Import MCP Server can be used for production environments with proper security controls in place. For production use cases, consider the following:

- **Read-Only Mode by Default**: The server runs in read-only mode by default, which is safer for production environments. Only explicitly enable write access when necessary.
- **Disable auto-approve**: Require the user to approve each time the AI assistant executes a tool

### Role scoping recommendations

To follow security best practices:

1. **Create dedicated IAM roles** with the principle of least privilege
2. **Use separate roles** for read-only and write operations
3. **Implement resource tagging** to limit actions to resources created by the server
4. **Enable AWS CloudTrail** to audit all API calls made by the server
5. **Regularly review** the permissions granted to the server's IAM role
6. **Use IAM Access Analyzer** to identify unused permissions that can be removed

### Sensitive information handling

**IMPORTANT**: Do not pass secrets or sensitive information via allowed input mechanisms:

- Do not include secrets or credentials in model import configurations
- Do not pass sensitive information directly in the prompt to the model

## Links

- [Homepage](https://awslabs.github.io/mcp/)
- [Documentation](https://awslabs.github.io/mcp/servers/aws-bedrock-custom-model-import-mcp-server/)
- [Source Code](https://github.com/awslabs/mcp.git)
- [Bug Tracker](https://github.com/awslabs/mcp/issues)
- [Changelog](https://github.com/awslabs/mcp/blob/main/src/aws-bedrock-custom-model-import-mcp-server/CHANGELOG.md)

## License

Apache-2.0
