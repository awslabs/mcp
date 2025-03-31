# awslabs MCP Nova Canvas Expert

{%include "../src/mcp-nova-canvas-expert/README.md"%}

MCP server for generating images using Amazon Nova Canvas

## Features

- **Text-based image generation** - Create images from text prompts with `generate_image`
  - Customizable dimensions (320-4096px), quality options, and negative prompting
  - Supports multiple image generation (1-5) in single request
  - Adjustable parameters like cfg_scale (1.1-10.0) and seeded generation

- **Color-guided image generation** - Generate images with specific color palettes using `generate_image_with_colors`
  - Define up to 10 hex color values to influence the image style and mood
  - Same customization options as text-based generation

- **Workspace integration** - Images saved to user-specified workspace directories with automatic folder creation

- **AWS authentication** - Uses AWS profiles for secure access to Amazon Nova Canvas services

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.13`
3. Set up AWS credentials with access to Amazon Bedrock and Nova Canvas
   - You need an AWS account with Amazon Bedrock and Amazon Nova Canvas enabled
   - Configure AWS credentials with `aws configure` or environment variables
   - Ensure your IAM role/user has permissions to use Amazon Bedrock and Nova Canvas

## Installation

Install the MCP server:

Add the server to your MCP client config (e.g. for Amazon Q CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "mcp-nova-canvas-expert": {
      "command": "uvx",
      "args": ["awslabs.mcp-nova-canvas-expert@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",  // Optional: specify AWS profile
        "AWS_REGION": "us-east-1"           // Required: region where Bedrock is available
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
  "AWS_PROFILE": "your-aws-profile",  // Specify which AWS profile to use
  "AWS_REGION": "us-east-1"           // Region where Bedrock is available
}
```

Make sure the AWS profile has permissions to access Amazon Bedrock and Amazon Nova Canvas. The MCP server creates a boto3 session using the specified profile to authenticate with AWS services. Your AWS IAM credentials remain on your local machine and are strictly used for using the Amazon Bedrock model APIs.

## Using the Nova Canvas Image Generation Tool

The MCP server provides a tool for generating images using Amazon Nova Canvas:

### generate_image

This tool generates images based on text prompts using Amazon Nova Canvas.

**Parameters:**

- `prompt` (required): Text description of the image to generate
- `filename` (optional): Name for the output file (without extension)
- `width` (optional, default: 512): Width of the generated image
- `height` (optional, default: 512): Height of the generated image
- `quality` (optional, default: "standard"): Quality of the generated image
- `number_of_images` (optional, default: 1): Number of images to generate

**Example usage with Claude:**

```python
response = use_mcp_tool(
    server_name="ai3_novacanvas_expert",
    tool_name="generate_image",
    arguments={
        "prompt": "A futuristic cityscape with flying cars and neon lights",
        "filename": "futuristic_city",
        "width": 1024,
        "height": 768
    }
)
```

The tool returns a dictionary with:

- `status`: "success" or "error"
- `message`: Description of the result
- `paths`: List of paths to the generated images
- `prompt`: The original prompt used for generation
