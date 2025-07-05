# AWS Labs OpenAPI MCP Server

This project is a server that dynamically creates Model Context Protocol (MCP) tools and resources from OpenAPI specifications. It allows Large Language Models (LLMs) to interact with APIs through the Model Context Protocol.

## Introduction

This server acts as a bridge between OpenAPI specifications and LLMs, enabling models to understand and interact with API capabilities without requiring manual tool definitions. The server automatically creates structured MCP tools that LLMs can use to understand your API endpoints, parameters, and response formats.

## Features

- **Dynamic Tool Generation**: Automatically creates MCP tools from OpenAPI endpoints
- **Intelligent Route Mapping**: Maps GET operations with query parameters to TOOLS for better LLM usability
- **Dynamic Prompt Generation**: Creates helpful natural language prompts based on API structure
- **Authentication Support**: Works with multiple authentication methods (Basic, Bearer Token, API Key, OAuth 2.0/Cognito)
- **Transport Options**: Supports stdio transport
- **Flexible Configuration**: Configure via environment variables or command line arguments
- **OpenAPI Support**: Works with OpenAPI 3.x specifications in JSON or YAML format
- **AWS Best Practices**: Implements best practices for caching, resilience, and observability
- **Metrics Collection**: Tracks API calls, tool usage, errors, and performance metrics

## Installation

### From PyPI

```bash
pip install "awslabs.openapi-mcp-server"
```

### Optional Dependencies

The package supports several optional dependencies:

```bash
# For YAML OpenAPI specification support
pip install "awslabs.openapi-mcp-server[yaml]"

# For Prometheus metrics support
pip install "awslabs.openapi-mcp-server[prometheus]"

# For testing
pip install "awslabs.openapi-mcp-server[test]"

# For all optional dependencies
pip install "awslabs.openapi-mcp-server[all]"
```

### From Source

```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/openapi-mcp-server
pip install -e .
```

## Basic Usage

```bash
# Start with Petstore API example
awslabs.openapi-mcp-server --api-name petstore --api-url https://petstore3.swagger.io/api/v3 --spec-url https://petstore3.swagger.io/api/v3/openapi.json
```

### Custom API

```bash
# Use a different API
awslabs.openapi-mcp-server --api-name myapi --api-url https://api.example.com --spec-url https://api.example.com/openapi.json
```

### Local OpenAPI Specification

```bash
# Use a local OpenAPI specification file
awslabs.openapi-mcp-server --spec-path ./openapi.json

# Use a YAML OpenAPI specification file (requires pyyaml)
pip install "awslabs.openapi-mcp-server[yaml]"
awslabs.openapi-mcp-server --spec-path ./openapi.yaml
```

## Authentication Configuration

### Bearer Token Authentication

```bash
# Bearer Token Authentication
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type bearer --auth-token YOUR_TOKEN
```

### OAuth 2.0/Cognito Authentication

```bash
# Cognito Authentication with OAuth 2.0 Client Credentials Flow
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type cognito --auth-cognito-client-id YOUR_CLIENT_ID --auth-cognito-client-secret YOUR_CLIENT_SECRET --auth-cognito-domain YOUR_DOMAIN --auth-cognito-region us-east-2 --auth-cognito-scopes "scope1,scope2"
```

For detailed information about all supported authentication methods (Basic Auth, Bearer Token, API Key, and OAuth 2.0/Cognito), configuration options, and examples, see [AUTHENTICATION.md](AUTHENTICATION.md).

## MCP Integration

### Amazon Q CLI Configuration

Add to `~/.aws/amazonq/mcp.json`:

```json
{
  "mcpServers": {
    "petstore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.openapi-mcp-server@latest"],
      "env": {
        "API_NAME": "petstore",
        "API_BASE_URL": "https://petstore3.swagger.io/api/v3",
        "API_SPEC_URL": "https://petstore3.swagger.io/api/v3/openapi.json",
        "LOG_LEVEL": "INFO",
        "ENABLE_OPERATION_PROMPTS": "true"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Cline Integration

The server is available in the [Cline Marketplace](https://docs.cline.bot/mcp/mcp-marketplace) as "OpenAPI Dynamic Tools" for easy installation:

1. Go to Cline Extension of your favorite IDE

2. Access the Marketplace
   - Click the "Extensions" button (square icon) in the top toolbar
   - The MCP marketplace will open, showing available servers by category

3. Browse and Select the Server
   - Browse servers by category
   - Find and click on "OpenAPI Dynamic Tools" to see details about its capabilities

4. Install and Configure
   - Click the install button for "OpenAPI Dynamic Tools"
   - Configure your API details in the setup form:
     ```
     API Name: petstore
     API Base URL: https://petstore3.swagger.io/api/v3
     API Spec URL: https://petstore3.swagger.io/api/v3/openapi.json
     ```
   - If your API requires authentication, enter the necessary credentials
   - The server will be added to your MCP settings automatically

5. Verify Installation
   - Cline will show confirmation when installation is complete
   - Check the server status in Cline's MCP settings UI

6. Using Your New API Tools
   - After successful installation, Cline will automatically integrate the API's capabilities
   - You can now interact with the Petstore API by asking Cline to use its endpoints
   - Example: "Find a pet by ID using the Petstore API" or "List available pets in the Petstore"

For information about integrating with other LLM tools, see the main [MCP README](https://github.com/awslabs/mcp/blob/main/README.md).

## Troubleshooting

### SSL Certificate Issues

When running the server with Cognito authentication through desktop clients like Amazon Q CLI, Claude Desktop, or GitHub Copilot in Visual Studio Code on macOS, you might encounter SSL certificate verification issues. This is because these applications may not use the system's certificate store by default.

To resolve certificate issues, add the following environment variables to your MCP configuration:

```json
{
  "mcpServers": {
    "your-api-server": {
      "env": {
        "SSL_CERT_FILE": "/opt/homebrew/etc/openssl@3/cert.pem",
        "REQUESTS_CA_BUNDLE": "/opt/homebrew/etc/openssl@3/cert.pem"
      }
    }
  }
}
```

The path to the certificate file may vary depending on your macOS setup:

- For Homebrew installations: `/opt/homebrew/etc/openssl@3/cert.pem`
- For older Homebrew installations: `/usr/local/etc/openssl@3/cert.pem`
- You can also use: `/etc/ssl/cert.pem`

## Docker Deployment

The project includes a Dockerfile for containerized deployment:

```bash
# Build the Docker image
docker build -t openapi-mcp-server:latest .

# Run with custom configuration
docker run \
  -e API_NAME=myapi \
  -e API_BASE_URL=https://api.example.com \
  -e API_SPEC_URL=https://api.example.com/openapi.json \
  -e SERVER_TRANSPORT=stdio \
  openapi-mcp-server:latest
```

For detailed information about Docker deployment, AWS service integration, and transport considerations, see the [DEPLOYMENT.md](DEPLOYMENT.md) file.

## Detailed Configuration

The server can be configured using environment variables or command line arguments. Here are some commonly used configuration options:

```bash
# Server configuration
export SERVER_NAME="My API Server"
export LOG_LEVEL="INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# API configuration
export API_NAME="myapi"
export API_BASE_URL="https://api.example.com"
export API_SPEC_URL="https://api.example.com/openapi.json"
```

For a complete reference of all configuration parameters, including mandatory, optional, and conditional parameters for different scenarios, see the [CONFIGURATION.md](CONFIGURATION.md) file.

## Additional Documentation

The OpenAPI MCP Server includes comprehensive documentation to help you get started and make the most of its features:

- [**AUTHENTICATION.md**](AUTHENTICATION.md): Detailed information about authentication methods and configuration
- [**DEPLOYMENT.md**](DEPLOYMENT.md): Guidelines for deploying the server in various environments
- [**AWS_BEST_PRACTICES.md**](AWS_BEST_PRACTICES.md): AWS best practices implemented in the server
- [**OBSERVABILITY.md**](OBSERVABILITY.md): Information about metrics, logging, and monitoring capabilities
- [**CONFIGURATION.md**](CONFIGURATION.md): Complete reference for all configuration parameters
- [**tests/README.md**](tests/README.md): Overview of the test structure and strategy

## Development and Testing

### Local Development

For local development and testing, you can use the `uvx` command with the `--refresh` and `--from` options:

```bash
# Run the server from the local directory with the Petstore API
uvx --refresh --from . awslabs.openapi-mcp-server --api-url https://petstore3.swagger.io/api/v3 --spec-url https://petstore3.swagger.io/api/v3/openapi.json --log-level DEBUG
```

### Running Tests

```bash
# Install test dependencies
pip install "awslabs.openapi-mcp-server[test]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=awslabs
```
