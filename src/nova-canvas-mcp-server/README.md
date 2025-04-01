# Nova Canvas MCP Server

MCP server for generating images using Amazon Nova Canvas

## Features

- **Text-based image generation**: Create images from text prompts with `generate_image`
  - Customizable dimensions (320-4096px), quality options, and negative prompting
  - Supports multiple image generation (1-5) in single request
  - Adjustable parameters like cfg_scale (1.1-10.0) and seeded generation

- **Color-guided image generation**: Generate images with specific color palettes using `generate_image_with_colors`
  - Define up to 10 hex color values to influence the image style and mood
  - Same customization options as text-based generation

- **Workspace integration**: Images saved to user-specified workspace directories with automatic folder creation

- **AWS authentication**: Uses AWS profiles for secure access to Amazon Nova Canvas services

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.13`
3. Set up AWS credentials with access to Amazon Bedrock and Nova Canvas
   - You need an AWS account with Amazon Bedrock and Amazon Nova Canvas enabled
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to use Amazon Bedrock and Nova Canvas

## Installation

Here are some ways you can work with MCP across AWS, and we'll be adding support to more products including Amazon Q Developer CLI soon: (e.g. for Amazon Q DeveloperCLI MCP, `~/.aws/amazonq/mcp.json`):

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

### AWS Authentication

The MCP server uses the AWS profile specified in the `AWS_PROFILE` environment variable. If not provided, it defaults to the "default" profile in your AWS configuration file.

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1"
}
```

Make sure the AWS profile has permissions to access Amazon Bedrock and Amazon Nova Canvas. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for using the Amazon Bedrock model APIs.
