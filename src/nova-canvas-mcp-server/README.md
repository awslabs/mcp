# Amazon Nova Canvas MCP Server

[![smithery badge](https://smithery.ai/badge/@awslabs/nova-canvas-mcp-server)](https://smithery.ai/server/@awslabs/nova-canvas-mcp-server)

MCP server for generating images using Amazon Nova Canvas

## Features

### Text-based image generation

- Create images from text prompts with `generate_image`
- Customizable dimensions (320-4096px), quality options, and negative prompting
- Supports multiple image generation (1-5) in single request
- Adjustable parameters like cfg_scale (1.1-10.0) and seeded generation

### Color-guided image generation

- Generate images with specific color palettes using `generate_image_with_colors`
- Define up to 10 hex color values to influence the image style and mood
- Same customization options as text-based generation

### Workspace integration

- Images saved to user-specified workspace directories with automatic folder creation

### AWS authentication

- Uses AWS profiles for secure access to Amazon Nova Canvas services

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Set up AWS credentials with access to Amazon Bedrock and Nova Canvas
   - You need an AWS account with Amazon Bedrock and Amazon Nova Canvas enabled
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to use Amazon Bedrock and Nova Canvas

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.nova-canvas-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubm92YS1jYW52YXMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Nova%20Canvas%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.nova-canvas-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration (e.g., for Amazon Q Developer CLI, edit `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.nova-canvas-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.nova-canvas-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
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
    "awslabs.nova-canvas-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.nova-canvas-mcp-server@latest",
        "awslabs.nova-canvas-mcp-server.exe"
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


or docker after a successful `docker build -t awslabs/nova-canvas-mcp-server .`:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.nova-canvas-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "AWS_REGION=us-east-1",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/nova-canvas-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

NOTE: Your credentials will need to be kept refreshed from your host

### Installing via Smithery

To install Amazon Nova Canvas MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@awslabs/nova-canvas-mcp-server):

```bash
npx -y @smithery/cli install @awslabs/nova-canvas-mcp-server --client claude
```

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1"
}
```

Make sure the AWS profile has permissions to access Amazon Bedrock and Amazon Nova Canvas. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for using the Amazon Bedrock model APIs.
