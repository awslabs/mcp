# AWS Labs OpenAPI MCP Server

This project is a server that dynamically creates Machine Conversation Protocol (MCP) tools and resources from OpenAPI specifications. It allows Large Language Models (LLMs) to interact with APIs through the Machine Conversation Protocol.

## Features

- **Dynamic Tool Generation**: Automatically creates MCP tools from OpenAPI endpoints
- **Dynamic Prompt Generation**: Creates helpful prompts based on API structure
- **Multiple Transport Options**: Supports SSE and stdio transports
- **Flexible Configuration**: Configure via environment variables or command line arguments
- **OpenAPI Support**: Works with OpenAPI 3.x specifications in JSON or YAML format
- **Authentication Support**: Supports multiple authentication methods (Basic, Bearer Token, API Key)

## Installation

### From PyPI

```bash
pip install "awslabs.openapi-mcp-server"
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
        "LOG_LEVEL": "ERROR"
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
# Start with default settings (Petstore API)
awslabs.openapi-mcp-server
```

### Custom API

```bash
# Use a different API
awslabs.openapi-mcp-server --api-name myapi --api-url https://api.example.com --spec-url https://api.example.com/openapi.json
```

### Authenticated API

```bash
# Basic Authentication
awslabs.openapi-mcp-server --api-name myapi --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type basic --auth-username YOUR_USERNAME --auth-password YOUR_PASSWORD # pragma: allowlist secret

# Bearer Token Authentication
awslabs.openapi-mcp-server --api-name myapi --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type bearer --auth-token YOUR_TOKEN # pragma: allowlist secret

# API Key Authentication (in header)
awslabs.openapi-mcp-server --api-name myapi --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type api_key --auth-api-key YOUR_API_KEY --auth-api-key-name X-API-Key --auth-api-key-in header # pragma: allowlist secret
```

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

## Configuration

### Environment Variables

```bash
# Server configuration
export SERVER_NAME="My API Server"
export SERVER_DEBUG=true
export SERVER_MESSAGE_TIMEOUT=60
export SERVER_HOST="0.0.0.0"
export SERVER_PORT=8000
export SERVER_TRANSPORT="sse"  # Options: sse, stdio
export LOG_LEVEL="INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

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

## Testing

### Functional Testing with Petstore API

The project includes a comprehensive functional test for verifying integration with the Swagger Petstore API. This test analyzes the Petstore API structure, lists all available tools and resources, and verifies server startup.

To run the functional test:

```bash
# Run the Petstore API functional test
./run_petstore_test.sh

# For verbose output
./run_petstore_test.sh --verbose

# To use a custom port
./run_petstore_test.sh --port 9000

# Keep the generated test script
./run_petstore_test.sh --keep-script
```

The functional test performs the following:

1. **API Structure Analysis**: Analyzes the OpenAPI specification and provides a detailed breakdown of:
   - All API endpoints grouped by category (pet, store, user)
   - Expected MCP tools to be created from operations
   - Potential MCP resources (GET endpoints without parameters)

2. **Detailed Tool Listing**: Lists all tools that would be created by category, including:
   - Tool name (operationId)
   - HTTP method and path
   - Description summary

3. **Server Startup Test**: Verifies that the server can start successfully with the Petstore API configuration

Example output:

```
📊 ANALYZING PETSTORE API ENDPOINTS...
============================================================
Fetching Petstore OpenAPI spec from https://petstore3.swagger.io/api/v3/openapi.json

📌 Found 13 unique API paths
📌 Found 19 operations that will be converted to MCP tools
📌 Found 3 potential resources (GET endpoints)

🔧 TOOLS BY CATEGORY:
============================================================

[PET] - 9 tools:
  • addPet                   - POST /pet - Add a new pet to the store
  • deletePet                - DELETE /pet/{petId} - Deletes a pet
  • findPetsByStatus         - GET /pet/findByStatus - Finds Pets by status
  • findPetsByTags           - GET /pet/findByTags - Finds Pets by tags
  • getPetById               - GET /pet/{petId} - Find pet by ID
  • updatePet                - PUT /pet - Update an existing pet
  • updatePetWithForm        - POST /pet/{petId} - Updates a pet in the store with form data
  • uploadFile               - POST /pet/{petId}/uploadImage - uploads an image

[STORE] - 4 tools:
  • deleteOrder              - DELETE /store/order/{orderId} - Delete purchase order by ID
  • getInventory             - GET /store/inventory - Returns pet inventories by status
  • getOrderById             - GET /store/order/{orderId} - Find purchase order by ID
  • placeOrder               - POST /store/order - Place an order for a pet

[USER] - 6 tools:
  • createUser               - POST /user - Create user
  • createUsersWithArray     - POST /user/createWithArray - Creates list of users with given input array
  • createUsersWithList      - POST /user/createWithList - Creates list of users with given input array
  • deleteUser               - DELETE /user/{username} - Delete user
  • getUserByName            - GET /user/{username} - Get user by user name
  • loginUser                - GET /user/login - Logs user into the system
  • logoutUser               - GET /user/logout - Logs out current logged in user session
  • updateUser               - PUT /user/{username} - Updated user

📚 POTENTIAL RESOURCES:
============================================================
  • getInventory             - /store/inventory
  • loginUser                - /user/login
  • logoutUser               - /user/logout
```

The test also provides a final summary report:

```
🔍 PETSTORE API FUNCTIONAL TEST REPORT
============================================================
✅ Server startup: SUCCESS
📊 API paths: 13
📊 Total tools (operations): 19
📊 Potential resources: 3
⚠️ Errors encountered: 0
⏱️ Test duration: 5.03 seconds
============================================================
```

## Instructions

This server acts as a bridge between OpenAPI specifications and LLMs, allowing models to have a better understanding of available API capabilities without requiring manual tool definitions. The server creates structured MCP tools that LLMs can use to understand and interact with your API endpoints, parameters, and response formats. Point the server to your API by providing: API name, API base URL and Auth Details, OpenAPI specification URL or local file path. Set up appropriate authentication if your API requires it (Basic, Bearer Token, or API Key). Choose between SSE or stdio transport options based on your needs.
