# AWS Bedrock Data Automation MCP Server

A Model Context Protocol (MCP) server for Amazon Bedrock Data Automation that enables AI assistants to analyze documents, images, videos, and audio files using Amazon Bedrock Data Automation projects.

## Features

- **Project Management**: List and get details about Bedrock Data Automation projects
- **Asset Analysis**: Extract insights from unstructured content using Bedrock Data Automation
- **Support for Multiple Content Types**: Process documents, images, videos, and audio files
- **Integration with Amazon S3**: Seamlessly upload and download assets and results

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to Amazon Bedrock Data Automation
   - You need an AWS account with Amazon Bedrock Data Automation enabled
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to use Amazon Bedrock Data Automation
4. Create an AWS S3 Bucket
   - Example AWS CLI command to create the bucket
   - ```bash
      aws s3 create-bucket <bucket-name>
      ```

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.aws-bedrock-data-automation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-bedrock-data-automation-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "AWS_BUCKET_NAME": "your-s3-bucket-name",
        "BASE_DIR": "/path/to/base/directory",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

or docker after a successful `docker build -t awslabs/aws-bedrock-data-automation-mcp-server .`:

```json
{
  "mcpServers": {
    "awslabs.aws-bedrock-data-automation-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_PROFILE",
        "--env",
        "AWS_REGION",
        "--env",
        "AWS_BUCKET_NAME",
        "--env",
        "BASE_DIR",
        "--env",
        "FASTMCP_LOG_LEVEL",
        "awslabs/aws-bedrock-data-automation-mcp-server:latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "AWS_BUCKET_NAME": "your-s3-bucket-name",
        "BASE_DIR": "/path/to/base/directory",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Environment Variables

- `AWS_PROFILE`: AWS CLI profile to use for credentials
- `AWS_REGION`: AWS region to use (default: us-east-1)
- `AWS_BUCKET_NAME`: S3 bucket name for storing assets and results
- `BASE_DIR`: Base directory for file operations (optional)
- `FASTMCP_LOG_LEVEL`: Logging level (ERROR, WARNING, INFO, DEBUG)

## AWS Authentication

The server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the default credential provider chain.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1"
}
```

Make sure the AWS profile has permissions to access Amazon Bedrock Data Automation services. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Amazon Bedrock Data Automation services is currently available in the following regions: us-east-1 and us-west-2.

## Tools

### getprojects

Get a list of data automation projects.

```python
getprojects() -> list
```

Returns a list of available Bedrock Data Automation projects.

### getprojectdetails

Get details of a specific data automation project.

```python
getprojectdetails(projectArn: str) -> dict
```

Returns detailed information about a specific Bedrock Data Automation project.

### analyzeasset

Analyze an asset using a data automation project.

```python
analyzeasset(assetPath: str, projectArn: Optional[str] = None) -> dict
```

Extracts insights from unstructured content (documents, images, videos, audio) using Amazon Bedrock Data Automation.

- `assetPath`: Path to the asset file to analyze
- `projectArn`: ARN of the Bedrock Data Automation project to use (optional, uses default public project if not provided)

## Example Usage

```python
# List available projects
projects = await getprojects()

# Get details of a specific project
project_details = await getprojectdetails(projectArn="arn:aws:bedrock:us-east-1:123456789012:data-automation-project/my-project")

# Analyze a document
results = await analyzeasset(assetPath="/path/to/document.pdf")

# Analyze an image with a specific project
results = await analyzeasset(
    assetPath="/path/to/image.jpg",
    projectArn="arn:aws:bedrock:us-east-1:123456789012:data-automation-project/my-project"
)
```

## Security Considerations

- Use AWS IAM roles with appropriate permissions
- Store credentials securely
- Use temporary credentials when possible
- Ensure S3 bucket permissions are properly configured

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.
