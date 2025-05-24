# Finch MCP Server

A Model Context Protocol (MCP) server for Finch that enables generative AI models to build and push container images through finch cli leveraged MCP tools.

## Features

This MCP server acts as a bridge between MCP clients and Finch, allowing generative AI models to build and push container images. The server provides a secure way to interact with Finch, ensuring that the Finch VM is properly initialized and running before performing operations.

## Key Capabilities

- Build container images using Finch
- Push container images to repositories, including Amazon ECR
- Check if ECR repositories exist and create them if needed
- Automatic management of the Finch VM on macos and windows (initialization, starting, etc.)
- Automatic configuration of ECR credential helpers when needed (only modifies finch.yaml as config.json is automatically handled)

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Install [Finch](https://github.com/runfinch/finch) on your system
4. For ECR operations, AWS credentials with permissions to push to ECR repositories and create/describe ECR repositories

## Setup

### Installation

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "disabled": false,
      "timeout": 1000,
      "command": "uv",
      "args": [
        "--directory",
        "<ABSOLUTE PATH>",
        "run",
        "server.py"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "transportType": "stdio"
    }
  }
}
```

## Available Tools

### `finch_build_container_image`

Build a container image using Finch.

The tool builds a Docker image using the specified Dockerfile and context directory. It supports a range of build options including tags, platforms, and more.

Arguments:
- `dockerfile_path` (str): Absolute path to the Dockerfile
- `context_path` (str): Absolute path to the build context directory
- `tags` (List[str], optional): List of tags to apply to the image (e.g., ["myimage:latest", "myimage:v1"])
- `platforms` (List[str], optional): List of target platforms (e.g., ["linux/amd64", "linux/arm64"])
- `target` (str, optional): Target build stage to build
- `no_cache` (bool, optional): Whether to disable cache. Defaults to False.
- `pull` (bool, optional): Whether to always pull base images. Defaults to False.
- `build_contexts` (List[str], optional): List of additional build contexts
- `outputs` (str, optional): Output destination
- `cache_from` (List[str], optional): List of external cache sources
- `quiet` (bool, optional): Whether to suppress build output. Defaults to False.
- `progress` (str, optional): Type of progress output. Defaults to "auto".

### `finch_push_image`

Push a container image to a repository using Finch, replacing the tag with the image hash.

If the image URL is an ECR repository, it verifies that ECR login credential helper is configured. This tool gets the image hash, creates a new tag using the hash, and pushes the image with the hash tag to the repository.

The workflow is:
1. Get the image hash using `finch image inspect`
2. Create a new tag for the image using the short form of the hash (first 12 characters)
3. Push the hash-tagged image to the repository

Arguments:
- `image` (str): The full image name to push, including the repository URL and tag. For ECR repositories, it must follow the format: `<aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>`

Example:
```
# Original image: myrepo/myimage:latest
# After processing: myrepo/myimage:1a2b3c4d5e6f (where 1a2b3c4d5e6f is the short hash)
```

### `finch_create_ecr_repo`

Check if an ECR repository exists and create it if it doesn't.

This tool checks if the specified ECR repository exists using boto3. If the repository doesn't exist, it creates a new one with the given name with scan on push enabled and immutable tags for enhanced security. The tool requires appropriate AWS credentials configured.

Arguments:
- `app_name` (str): The name of the application/repository to check or create in ECR
- `region` (str, optional): AWS region for the ECR repository. If not provided, uses the default region from AWS configuration

Example:
```
# Check if 'my-app' repository exists in us-west-2 region, create it if it doesn't
{
  "app_name": "my-app",
  "region": "us-west-2"
}

# Response if repository already exists:
{
  "status": "success",
  "message": "ECR repository 'my-app' already exists.",
}

# Response if repository was created:
{
  "status": "success",
  "message": "Successfully created ECR repository 'my-app'.",
}
```

## Best Practices

- **Development and Prototyping Only**: The tools provided by this MCP server are intended for development and prototyping purposes only. They are not meant for production use cases.
- **Security Considerations**: Always review the Dockerfiles and container configurations before building and pushing images.
- **Resource Management**: Regularly clean up unused images and containers to free up disk space.
- **Version Control**: Keep track of image versions and tags to ensure reproducibility.
- **Error Handling**: Implement proper error handling in your applications when using these tools.


## Troubleshooting

- If you encounter permission errors with ECR, verify your AWS credentials and boto3 configuration are properly set up
- For Finch VM issues, try running `finch vm stop` and then `finch vm start` manually
- If the build fails with errors about missing files, check that your context path is correct
- For general Finch issues, consult the [Finch documentation](https://github.com/runfinch/finch)

## Version

Current MCP server version: 0.1.0
