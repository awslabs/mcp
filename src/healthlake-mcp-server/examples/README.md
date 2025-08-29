# MCP Configuration Examples

This directory contains example MCP client configuration files for the AWS HealthLake MCP Server.

## mcp_config.json

The `mcp_config.json` file contains a basic configuration for getting started:

### Standard Configuration
- **Method**: uvx (recommended)
- **Mode**: Full access (all operations available)
- **Authentication**: AWS profile

## Usage

Copy this configuration to your MCP client configuration file:

### Amazon Q Developer CLI
- **macOS**: `~/.aws/amazonq/mcp.json`
- **Linux**: `~/.config/amazon-q/mcp.json`
- **Windows**: `%APPDATA%\Amazon Q\mcp.json`

### Other MCP Clients
Refer to your MCP client's documentation for the correct configuration file location.

## Customization

Update the following values for your environment:
- `AWS_REGION`: Your preferred AWS region (e.g., "us-west-2", "eu-west-1")
- `AWS_PROFILE`: Your AWS profile name
- `MCP_LOG_LEVEL`: Desired log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Additional Configurations

For additional configurations (read-only mode, Docker, etc.), see the main README.md file which contains comprehensive examples for all use cases.
