# Authentication for OpenAPI MCP Server

[← Back to main README](README.md)

## Supported Authentication Methods

The OpenAPI MCP Server supports five authentication methods:

| Method | Description | Required Parameters |
|--------|-------------|---------------------|
| **None** | No authentication (default) | None |
| **Bearer** | Token-based authentication | `--auth-token` |
| **Basic** | Username/password authentication | `--auth-username`, `--auth-password` |
| **API Key** | API key authentication | `--auth-api-key`, `--auth-api-key-name`, `--auth-api-key-in` |
| **Cognito** | AWS Cognito User Pool authentication | `--auth-cognito-client-id`, `--auth-cognito-username`, `--auth-cognito-password`, `--auth-cognito-user-pool-id` (optional) |

## Quick Start Examples

### Bearer Authentication

```bash
# Command line
python -m awslabs.openapi_mcp_server.server --auth-type bearer --auth-token "YOUR_TOKEN" --api-url "https://api.example.com"

# Environment variables
export AUTH_TYPE=bearer
export AUTH_TOKEN="YOUR_TOKEN"
python -m awslabs.openapi_mcp_server.server
```

### Basic Authentication

```bash
# Command line
python -m awslabs.openapi_mcp_server.server --auth-type basic --auth-username "user" --auth-password "pass" --api-url "https://api.example.com"

# Environment variables
export AUTH_TYPE=basic
export AUTH_USERNAME="user"
export AUTH_PASSWORD="pass"
python -m awslabs.openapi_mcp_server.server
```

### API Key Authentication

```bash
# Command line
python -m awslabs.openapi_mcp_server.server --auth-type api_key --auth-api-key "your-key" --auth-api-key-name "X-API-Key" --auth-api-key-in "header"

# Environment variables
export AUTH_TYPE=api_key
export AUTH_API_KEY="your-key"
export AUTH_API_KEY_NAME="X-API-Key"
export AUTH_API_KEY_IN="header"  # Options: header, query, cookie
```

### Cognito Authentication

```bash
# Command line
python -m awslabs.openapi_mcp_server.server --auth-type cognito \
  --auth-cognito-client-id "YOUR_CLIENT_ID" \
  --auth-cognito-username "username" \
  --auth-cognito-password "password" \
  --auth-cognito-user-pool-id "OPTIONAL_POOL_ID" \
  --auth-cognito-region "us-east-1" \
  --api-url "https://api.example.com"

# Environment variables
export AUTH_TYPE=cognito
export AUTH_COGNITO_CLIENT_ID="YOUR_CLIENT_ID"
export AUTH_COGNITO_USERNAME="username"
export AUTH_COGNITO_PASSWORD="password" # Can also be set in system environment
export AUTH_COGNITO_USER_POOL_ID="OPTIONAL_POOL_ID"
export AUTH_COGNITO_REGION="us-east-1"
python -m awslabs.openapi_mcp_server.server
```

## Important Notes

- **Bearer Authentication**: Requires a valid token. The server will exit gracefully with an error message if no token is provided.
- **Basic Authentication**: Requires both username and password. The server will exit gracefully with an error message if either is missing.
- **API Key Authentication**: Can be placed in a header (default), query parameter, or cookie.
- **Cognito Authentication**: Requires client ID, username, and password. The password can be stored in the system environment variable `AUTH_COGNITO_PASSWORD` for security. Tokens are automatically refreshed when they expire.
  - **ID Token Usage**: The Cognito authentication provider uses the **ID Token** for authentication. This is consistent with the AWS CLI approach:
    ```bash
    # Get ID Token from Cognito and use it for authentication
    export AUTH_TOKEN=$(aws cognito-idp initiate-auth \
      --auth-flow USER_PASSWORD_AUTH \
      --client-id $AUTH_COGNITO_CLIENT_ID \
      --auth-parameters USERNAME=$AUTH_COGNITO_USERNAME,PASSWORD=$AUTH_COGNITO_PASSWORD \
      --query 'AuthenticationResult.IdToken' \
      --output text)
    ```
    Support for using the Access Token will be added in a future release.
  - **User Pool ID**: Some Cognito configurations require a User Pool ID. If you encounter authentication errors, try providing the User Pool ID using `--auth-cognito-user-pool-id` or `AUTH_COGNITO_USER_POOL_ID`.
  - **Authentication Flows**: The provider automatically tries different authentication flows (USER_PASSWORD_AUTH and ADMIN_USER_PASSWORD_AUTH) based on your Cognito configuration.

## Error Handling

The server implements graceful shutdown with detailed error messages for authentication failures:

1. **Configuration Errors**: If required authentication parameters are missing, the server will exit with a clear error message indicating what's missing.
2. **Authentication Failures**: If authentication fails (e.g., invalid credentials), the server will exit with a detailed error message.
3. **Token Refresh**: If token refresh fails, the server will attempt to re-authenticate with the provided credentials.
4. **Resource Registration**: If there are issues registering tools or resources, the server will exit with an error message.

## Advanced Configuration

### Authentication Caching

The authentication system implements caching to improve performance:

- **Provider Caching**: Authentication provider instances are cached based on their configuration
- **Token Caching**: Authentication tokens and headers are cached with configurable TTL
- **Cache Control**: Cache can be cleared programmatically when needed

### Custom TTL Configuration

You can configure the TTL (Time-To-Live) for authentication tokens:

```bash
# Set token TTL to 1 hour (3600 seconds)
python -m awslabs.openapi_mcp_server.server --auth-type bearer --auth-token "YOUR_TOKEN" --auth-token-ttl 3600
```

## System Architecture

The authentication system follows these design principles:

1. **Template Method Pattern**: Standardized validation and initialization flow
2. **Decorator Pattern**: Conditional execution based on configuration validity
3. **Factory Pattern**: Dynamic provider creation and caching
4. **Error Handling**: Structured error types with detailed information

## Performance Optimizations

The authentication system includes several optimizations:

- **Selective Provider Registration**: Only registers the authentication provider that will be used
- **Provider Instance Reuse**: Reduces memory usage and initialization overhead
- **Authentication Data Caching**: Improves response times for repeated requests
- **Secure Credential Handling**: Hashes sensitive data for cache keys
- **Configurable TTL**: Allows fine-tuning cache duration based on security requirements

## Testing

Test scripts are provided for authentication providers:

```bash
# Test Bearer authentication
python test_bearer_auth.py

# Test Basic authentication
python test_basic_auth.py

# Test API Key authentication
python test_api_key_auth.py

# Test Cognito authentication
python test_cognito_auth.py --client-id "YOUR_CLIENT_ID" --username "username" --password "password" --user-pool-id "OPTIONAL_POOL_ID" --region "us-east-1"

# Run all authentication tests
python -m pytest tests/auth/
```

## Troubleshooting

If you encounter authentication issues:

1. Verify credentials are correct and not expired
2. Enable DEBUG logging: `--log-level DEBUG`
3. Check server logs for authentication-related error messages
4. Ensure the API requires the authentication method you're using
5. Check for detailed error information in the logs, including error type and details

### Cognito Authentication Debugging

The Cognito authentication provider includes detailed debug logging to help troubleshoot authentication issues:

```
DEBUG | awslabs.openapi_mcp_server.auth.cognito_auth:__init__:50 - Cognito auth configuration: Username=username, ClientID=client-id, Password=SET, UserPoolID=NOT SET
```

This log message appears at the DEBUG level during initialization and shows:

- **Username**: The Cognito username being used
- **ClientID**: The Cognito client ID being used
- **Password**: Whether a password is set (shows "SET" or "NOT SET", never the actual password)
- **UserPoolID**: Whether a user pool ID is set (shows the ID or "NOT SET")

To enable these debug logs, run the server with `--log-level DEBUG`:

```bash
python -m awslabs.openapi_mcp_server.server --auth-type cognito --log-level DEBUG [other options]
```

Common Cognito authentication issues:

1. **Missing credentials**: Check that all required parameters are set (client ID, username, password)
2. **Invalid credentials**: Verify the credentials are correct in the AWS Cognito console
3. **Expired token**: The server will automatically attempt to refresh expired tokens
4. **User not confirmed**: Confirm the user in the AWS Cognito console
5. **Missing User Pool ID**: Some Cognito configurations require a User Pool ID
