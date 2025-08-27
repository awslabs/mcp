# Finch MCP Server

A Model Context Protocol (MCP) server for Finch that enables generative AI models to build and push container images through finch cli leveraged MCP tools.

## Features

This MCP server acts as a bridge between MCP clients and Finch, allowing generative AI models to build and push container images to repositories, and create ECR repositories as needed. The server provides a secure way to interact with Finch, ensuring that the Finch VM is properly initialized and running before performing operations.

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

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.finch-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZmluY2gtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLXdlc3QtMiIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Finch%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.finch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%2C%22transportType%22%3A%22stdio%22%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration:

#### Default Mode (Read-only AWS Resources)

By default, the server runs in a mode that prevents the creation of new AWS resources. This is useful for environments where you want to limit resource creation or for users who should only be able to build and push to existing repositories.

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "transportType": "stdio",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.finch-mcp-server@latest",
        "awslabs.finch-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```


In this default mode:
- The `finch_build_container_image` tools will work normally
- The `finch_create_ecr_repo` and `finch_push_image` tool will return an error and will not create or modify AWS resources.

#### AWS Resource Write Mode

The server can also be set to enable AWS resource creation and modification by using the `--enable-aws-resource-write` flag.

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.finch-mcp-server@latest",
        "--enable-aws-resource-write"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "transportType": "stdio",
      "disabled": false,
      "autoApprove": []
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

This tool checks if the specified ECR repository exists using boto3. If the repository doesn't exist, it creates a new one with the given name with immutable tags for enhanced security. The tool requires appropriate AWS credentials configured.

**Note:** The scan on push option is disabled in the mcp tool in favour of intentionally set by the user.

**Note:** When the server is running in readonly mode, this tool will return an error and will not create any AWS resources.

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

# Response if server is in readonly mode:
{
  "status": "error",
  "message": "Server running in read-only mode, unable to perform the action"
}
```

## Best Practices

- **Development and Prototyping Only**: The tools provided by this MCP server are intended for development and prototyping purposes only. They are not meant for production use cases.
- **Security Considerations**: Always review the Dockerfiles and container configurations before building and pushing images.
- **Resource Management**: Regularly clean up unused images and containers to free up disk space.
- **Version Control**: Keep track of image versions and tags to ensure reproducibility.
- **Error Handling**: Implement proper error handling in your applications when using these tools.
- **ECR Registry Scanning Configuration**: The PutImageScanningConfiguration API is being deprecated in favor of specifying image scanning configuration at the registry level. To configure registry-level scanning, use the following AWS CLI command:
  ```bash
  aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules "[{\"scanFrequency\":\"SCAN_ON_PUSH\",\"repositoryFilters\":[{\"filter\":\"*\",\"filterType\":\"WILDCARD\"}]}]"
  ```
  For more information, see [ECR PutRegistryScanningConfiguration documentation](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_PutRegistryScanningConfiguration.html).


## Logging

The Finch MCP server provides comprehensive logging capabilities to help with debugging and monitoring operations.

### Log Destinations

By default, the server logs to two destinations:
1. **stderr** - Standard error output (follows MCP protocol standards)
2. **File** - Persistent log file for detailed debugging

### File Logging

#### Default Log Location

Logs are automatically saved to platform-specific directories:
- **macOS/Linux**: `~/.finch/finch-mcp-server/finch_mcp_server.log`
- **Windows**: `%LOCALAPPDATA%\finch-mcp-server\finch_mcp_server.log`

#### Custom Log File Location

Specify a custom log file path using the `FINCH_MCP_LOG_FILE` environment variable:

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "FINCH_MCP_LOG_FILE": "~/logs/finch-mcp-server.log"
      }
    }
  }
}
```

#### Disable File Logging

To log only to stderr (following strict MCP standards), disable file logging:

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "FINCH_DISABLE_FILE_LOGGING": "true"
      }
    }
  }
}
```

Or use the command line argument in the args array:
```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.finch-mcp-server@latest",
        "--disable-file-logging"
      ]
    }
  }
}
```

### Log Features

#### Automatic Log Rotation
- Log files are automatically rotated when they exceed 10 MB
- Old logs are compressed (gzip) and retained for 7 days
- This prevents disk space issues from large log files

#### Sensitive Data Protection
The logging system automatically redacts sensitive information from log messages:
- AWS access keys and secret keys
- API keys, passwords, and tokens
- JWT tokens and OAuth credentials
- URLs containing embedded credentials

#### Log Format
- **stderr**: `{time} | {level} | {message}`
- **File**: `{time} | {level} | {name}:{function}:{line} | {message}`

The file format includes additional context (function name and line number) for detailed debugging.

### Example Configuration

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FINCH_MCP_LOG_FILE": "~/logs/finch-mcp-server.log"
      }
    }
  }
}
```

## Troubleshooting

- If you encounter permission errors with ECR, verify your AWS credentials and boto3 configuration are properly set up
- For Finch VM issues, try running `finch vm stop` and then `finch vm start` manually
- If the build fails with errors about missing files, check that your context path is correct
- For general Finch issues, consult the [Finch documentation](https://github.com/runfinch/finch)
- **Check the logs**: Enable DEBUG level logging and examine the log files for detailed error information
- **Log file permissions**: If file logging fails, the server will continue with stderr-only logging and show a warning message

## Version

Current MCP server version: 0.1.0
