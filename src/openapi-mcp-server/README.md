# AWS Labs OpenAPI MCP Server

This project is a server that dynamically creates Model Context Protocol (MCP) tools and resources from OpenAPI specifications. It allows Large Language Models (LLMs) to interact with APIs through the Model Context Protocol.

## Features

- **Dynamic Tool Generation**: Automatically creates MCP tools from OpenAPI endpoints
- **Intelligent Route Mapping**: Maps GET operations with query parameters to TOOLS instead of RESOURCES
  - Makes API operations with query parameters easier for LLMs to understand and use
  - Improves usability of search and filtering endpoints
  - Configurable via the route_patch module
- **Dynamic Prompt Generation**: Creates helpful prompts based on API structure
  - **Operation-Specific Prompts**: Generates natural language prompts for each API operation
  - **API Documentation Prompts**: Creates comprehensive API documentation prompts
  - **Prompt Optimization**: Implements token efficiency strategies to reduce costs and enhance clarity
    - Follows MCP-compliant structure with name, description, arguments, and metadata
    - Achieves 70-75% reduction in token usage while maintaining functionality
    - Uses concise descriptions with essential information for better developer experience
- **Transport Options**: Supports stdio transport
- **Flexible Configuration**: Configure via environment variables or command line arguments
- **OpenAPI Support**: Works with OpenAPI 3.x specifications in JSON or YAML format
- **OpenAPI Specification Validation**: Validates specifications without failing startup if issues detected, logging warnings instead to work with specs having minor issues or non-standard extensions
- **Authentication Support**: Supports multiple authentication methods (Basic, Bearer Token, API Key, Cognito)
- **AWS Best Practices**: Implements AWS best practices for caching, resilience, and observability
- **Comprehensive Testing**: Includes extensive unit and integration tests with high code coverage
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

### Using MCP Configuration

Here are some ways you can work with MCP across AWS (e.g. for Amazon Q Developer CLI MCP, `~/.aws/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.openapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.openapi-mcp-server@latest"],
      "env": {
        "API_NAME": "your-api-name",
        "API_BASE_URL": "https://api.example.com",
          "API_SPEC_URL": "https://api.example.com/openapi.json",
          "LOG_LEVEL": "ERROR",
          "ENABLE_PROMETHEUS": "false",
          "ENABLE_OPERATION_PROMPTS": "true",
          "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "5.0",
          "UVICORN_GRACEFUL_SHUTDOWN": "true"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Usage

### Basic Usage

```bash
# Start with Petstore API example
awslabs.openapi-mcp-server --api-name petstore --api-url https://petstore3.swagger.io/api/v3 --spec-url https://petstore3.swagger.io/api/v3/openapi.json
```

### Custom API

```bash
# Use a different API
awslabs.openapi-mcp-server --api-name myapi --api-url https://api.example.com --spec-url https://api.example.com/openapi.json
```

### Authenticated API

```bash
# Basic Authentication
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type basic --auth-username YOUR_USERNAME --auth-password YOUR_PASSWORD # pragma: allowlist secret

# Bearer Token Authentication
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type bearer --auth-token YOUR_TOKEN # pragma: allowlist secret

# API Key Authentication (in header)
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type api_key --auth-api-key YOUR_API_KEY --auth-api-key-name X-API-Key --auth-api-key-in header # pragma: allowlist secret
```

For detailed information about authentication methods, configuration options, and examples, see [AUTHENTICATION.md](AUTHENTICATION.md).

### Local OpenAPI Specification

```bash
# Use a local OpenAPI specification file
awslabs.openapi-mcp-server --spec-path ./openapi.json
```

### YAML OpenAPI Specification

```bash
# Use a YAML OpenAPI specification file (requires pyyaml)
pip install "awslabs.openapi-mcp-server[yaml]"
awslabs.openapi-mcp-server --spec-path ./openapi.yaml
```

### Local Development and Testing

For local development and testing, you can use the `uvx` command with the `--refresh` and `--from` options:

```bash
# Run the server from the local directory with the Petstore API
uvx --refresh --from . awslabs.openapi-mcp-server --api-url https://petstore3.swagger.io/api/v3 --spec-url https://petstore3.swagger.io/api/v3/openapi.json --log-level DEBUG
```

**Command Options Explained:**

- `uvx` - The uv package manager's execution tool for running Python packages
- `--refresh` - Refreshes the package cache to ensure the latest version is used (important during development)
- `--from .` - Uses the package from the current directory instead of installing from PyPI
- `awslabs.openapi-mcp-server` - The package name to run
- `--api-url` - The base URL of the API
- `--spec-url` - The URL of the OpenAPI specification
- `--log-level DEBUG` - Sets the logging level to DEBUG for more detailed logs (useful for development)
**When to Use These Options:**

- Use `--refresh` when you've made changes to your code and want to ensure the latest version is used
- Use `--log-level DEBUG` when you need detailed logs for troubleshooting or development

**Note:** The Petstore API is a standard OpenAPI schema endpoint that can be used for simple testing without any API authentication configuration. It's perfect for testing your MCP server implementation without setting up your own API.

## Configuration

### Environment Variables

```bash
# Server configuration
export SERVER_NAME="My API Server"
export SERVER_DEBUG=true
export SERVER_MESSAGE_TIMEOUT=60
export SERVER_HOST="0.0.0.0"
export SERVER_PORT=8000
export SERVER_TRANSPORT="stdio"  # Option: stdio
export LOG_LEVEL="INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Metrics and monitoring configuration
export ENABLE_PROMETHEUS="false"  # Enable/disable Prometheus metrics (default: false)
export PROMETHEUS_PORT=9090  # Port for Prometheus metrics server
export ENABLE_OPERATION_PROMPTS="true"  # Enable/disable operation-specific prompts (default: true)

# Graceful shutdown configuration
export UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=5.0  # Timeout for graceful shutdown in seconds
export UVICORN_GRACEFUL_SHUTDOWN=true  # Enable/disable graceful shutdown

# API configuration
export API_NAME="myapi"
export API_BASE_URL="https://api.example.com"
export API_SPEC_URL="https://api.example.com/openapi.json"
export API_SPEC_PATH="/path/to/local/openapi.json"  # Optional: local file path

# Authentication configuration
export AUTH_TYPE="none"  # Options: none, basic, bearer, api_key
export AUTH_USERNAME="PLACEHOLDER_USERNAME"  # For basic authentication # pragma: allowlist secret
export AUTH_PASSWORD="PLACEHOLDER_PASSWORD"  # For basic authentication # pragma: allowlist secret
export AUTH_TOKEN="PLACEHOLDER_TOKEN"  # For bearer token authentication # pragma: allowlist secret
export AUTH_API_KEY="PLACEHOLDER_API_KEY"  # For API key authentication # pragma: allowlist secret
export AUTH_API_KEY_NAME="X-API-Key"  # Name of the API key (default: api_key)
export AUTH_API_KEY_IN="header"  # Where to place the API key (options: header, query, cookie)
```

## Documentation

The OpenAPI MCP Server includes comprehensive documentation to help you get started and make the most of its features:

- [**AUTHENTICATION.md**](AUTHENTICATION.md): Detailed information about authentication methods, configuration options, and troubleshooting
- [**DEPLOYMENT.md**](DEPLOYMENT.md): Guidelines for deploying the server in various environments, including Docker and AWS
- [**AWS_BEST_PRACTICES.md**](AWS_BEST_PRACTICES.md): AWS best practices implemented in the server for resilience, caching, and efficiency
- [**OBSERVABILITY.md**](OBSERVABILITY.md): Information about metrics, logging, and monitoring capabilities
- [**tests/README.md**](tests/README.md): Overview of the test structure and strategy

## AWS Best Practices

The OpenAPI MCP Server implements AWS best practices for building resilient, observable, and efficient cloud applications. These include:

- **Caching**: Robust caching system with multiple backend options
- **Resilience**: Patterns to handle transient failures and ensure high availability
- **Observability**: Comprehensive monitoring, metrics, and logging features

For detailed information about these features, including implementation details and configuration options, see [AWS_BEST_PRACTICES.md](AWS_BEST_PRACTICES.md).

## Docker Deployment

The project includes a Dockerfile for containerized deployment. To build and run:

```bash
# Build the Docker image
docker build -t openapi-mcp-server:latest .

# Run with default settings
docker run -p 8000:8000 openapi-mcp-server:latest

# Run with custom configuration
docker run -p 8000:8000 \
  -e API_NAME=myapi \
  -e API_BASE_URL=https://api.example.com \
  -e API_SPEC_URL=https://api.example.com/openapi.json \
  -e SERVER_TRANSPORT=stdio \
  -e ENABLE_PROMETHEUS=false \
  -e ENABLE_OPERATION_PROMPTS=true \
  -e UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=5.0 \
  -e UVICORN_GRACEFUL_SHUTDOWN=true \
  openapi-mcp-server:latest
```

For detailed information about Docker deployment, AWS service integration, and transport considerations, see the [DEPLOYMENT.md](DEPLOYMENT.md) file.

## Testing

The project includes a comprehensive test suite covering unit tests, integration tests, and API functionality tests.

### Running Tests

```bash
# Install test dependencies
pip install "awslabs.openapi-mcp-server[test]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=awslabs

# Run specific test modules
pytest tests/api/
pytest tests/utils/
```

The test suite covers:

1. **API Configuration**: Tests for API configuration handling and validation
2. **API Discovery**: Tests for API endpoint discovery and tool generation
3. **Caching**: Tests for the caching system and providers
4. **HTTP Client**: Tests for the HTTP client with resilience features
5. **Metrics**: Tests for metrics collection and reporting
6. **OpenAPI Validation**: Tests for OpenAPI specification validation

For more information about the test structure and strategy, see the [tests/README.md](tests/README.md) file.

## Instructions

This server acts as a bridge between OpenAPI specifications and LLMs, allowing models to have a better understanding of available API capabilities without requiring manual tool definitions. The server creates structured MCP tools that LLMs can use to understand and interact with your API endpoints, parameters, and response formats.

### Key Features

1. **Dynamic Tool Generation**: Automatically creates MCP tools from your API endpoints
2. **Operation-Specific Prompts**: Generates natural language prompts for each API operation
3. **API Documentation**: Creates comprehensive documentation prompts for the entire API
4. **Authentication Support**: Works with Basic Auth, Bearer Token, API Key, and Cognito authentication

### Getting Started

1. Point the server to your API by providing:
   - API name
   - API base URL
   - OpenAPI specification URL or local file path
2. Set up appropriate authentication if your API requires it
3. Configure the stdio transport option

### Monitoring and Metrics

The server includes built-in monitoring capabilities:
- Prometheus metrics (disabled by default)
- Detailed logging of API calls and tool usage
- Performance tracking for API operations
## Testing with Amazon Q

To test the OpenAPI MCP Server with Amazon Q, you need to configure Amazon Q to use your MCP server. Here's how:

1. **Configure Amazon Q MCP Integration**

   Create or edit the MCP configuration file:

   ```bash
   mkdir -p ~/.aws/amazonq
   nano ~/.aws/amazonq/mcp.json
   ```

   Add the following configuration:

   ```json
   {
     "mcpServers": {
       "awslabs.openapi-mcp-server": {
         "command": "python",
         "args": ["-m", "awslabs.openapi_mcp_server"],
         "cwd": "/path/to/your/openapi-mcp-server",
         "env": {
           "API_NAME": "petstore",
           "API_BASE_URL": "https://petstore3.swagger.io/api/v3",
           "API_SPEC_URL": "https://petstore3.swagger.io/api/v3/openapi.json",
           "LOG_LEVEL": "INFO",
           "ENABLE_PROMETHEUS": "false",
           "ENABLE_OPERATION_PROMPTS": "true",
           "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "5.0",
           "UVICORN_GRACEFUL_SHUTDOWN": "true",
           "PYTHONPATH": "/path/to/your/openapi-mcp-server"
         },
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

2. **Start Amazon Q CLI**

   Launch the Amazon Q CLI:

   ```bash
   q chat
   ```

3. **Test the Operation Prompts**

   Once connected, you can test the operation prompts by asking Amazon Q to help you with specific API operations:

   ```
   I need to find a pet by ID using the Petstore API
   ```

   Amazon Q should respond with guidance using the natural language prompt.
