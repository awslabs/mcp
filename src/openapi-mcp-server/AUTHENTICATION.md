# Authentication for OpenAPI MCP Server

[← Back to main README](README.md)

## Mandatory Arguments

**IMPORTANT**: Regardless of the authentication method used, the following arguments are always required:

- `--api-url`: The base URL of the API (e.g., `https://api.example.com`)
- One of the following:
  - `--spec-url`: The URL to the OpenAPI specification (e.g., `https://api.example.com/openapi.json`)
  - `--spec-path`: Path to a local OpenAPI specification file (e.g., `./openapi.json`)

These arguments must be provided even when using environment variables for authentication settings.

## Supported Authentication Methods

The OpenAPI MCP Server supports five authentication methods:

| Method | Description | Required Parameters (CLI) | Environment Variables |
|--------|-------------|---------------------|----------------------|
| **None** | No authentication (default) | None | None |
| **Bearer** | Token-based authentication | `--auth-token` | `AUTH_TOKEN` |
| **Basic** | Username/password authentication | `--auth-username`, `--auth-password` | `AUTH_USERNAME`, `AUTH_PASSWORD` |
| **API Key** | API key authentication | `--auth-api-key`, `--auth-api-key-name`, `--auth-api-key-in` | `AUTH_API_KEY`, `AUTH_API_KEY_NAME`, `AUTH_API_KEY_IN` |
| **Cognito** | AWS Cognito User Pool authentication | See below for details | See below for details |

### Cognito Authentication Methods

Cognito authentication supports two different flows:

| Flow | Description | Required Parameters (CLI) | Environment Variables |
|------|-------------|---------------------|----------------------|
| **Password Flow** | Username/password authentication | `--auth-cognito-client-id`, `--auth-cognito-username`, `--auth-cognito-password`, `--auth-cognito-user-pool-id` (optional) | `AUTH_COGNITO_CLIENT_ID`, `AUTH_COGNITO_USERNAME`, `AUTH_COGNITO_PASSWORD`, `AUTH_COGNITO_USER_POOL_ID` (optional) |
| **Client Credentials Flow** | OAuth 2.0 client credentials flow for service-to-service authentication | `--auth-cognito-client-id`, `--auth-cognito-client-secret`, `--auth-cognito-domain`, `--auth-cognito-scopes` (optional) | `AUTH_COGNITO_CLIENT_ID`, `AUTH_COGNITO_CLIENT_SECRET`, `AUTH_COGNITO_DOMAIN`, `AUTH_COGNITO_SCOPES` (optional) |

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
python -m awslabs.openapi_mcp_server.server
```

### Cognito Authentication - Password Flow

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

### Cognito Authentication - OAuth 2.0 Client Credentials Flow

```bash
# Command line
python -m awslabs.openapi_mcp_server.server --auth-type cognito \
  --auth-cognito-client-id "YOUR_CLIENT_ID" \
  --auth-cognito-client-secret "YOUR_CLIENT_SECRET" \
  --auth-cognito-domain "your-domain-prefix" \
  --auth-cognito-region "us-east-2" \
  --auth-cognito-scopes "scope1 scope2" \
  --api-url "https://api.example.com"

# Environment variables
export AUTH_TYPE=cognito
export AUTH_COGNITO_CLIENT_ID="YOUR_CLIENT_ID"
export AUTH_COGNITO_CLIENT_SECRET="YOUR_CLIENT_SECRET"
export AUTH_COGNITO_DOMAIN="your-domain-prefix"
export AUTH_COGNITO_REGION="us-east-2"
export AUTH_COGNITO_SCOPES="scope1 scope2"  # Optional, space-separated list of scopes
python -m awslabs.openapi_mcp_server.server
```

## Important Notes

- **Bearer Authentication**: Requires a valid token. The server will exit gracefully with an error message if no token is provided.
- **Basic Authentication**: Requires both username and password. The server will exit gracefully with an error message if either is missing.
- **API Key Authentication**: Can be placed in a header (default), query parameter, or cookie.
- **Cognito Authentication - Password Flow**: Requires client ID, username, and password. The password can be stored in the system environment variable `AUTH_COGNITO_PASSWORD` for security. Tokens are automatically refreshed when they expire.
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
- **Cognito Authentication - OAuth 2.0 Client Credentials Flow**: Requires client ID, client secret, and domain. The client credentials flow is used for service-to-service authentication and does not require a user.
  - **Domain**: The domain is required for client credentials flow. It's the domain prefix of your Cognito user pool (e.g., if your domain is `https://my-domain.auth.us-east-2.amazoncognito.com`, the domain prefix is `my-domain`).
  - **Scopes**: Scopes are optional. If not provided, the server will use the default scopes configured for the client in Cognito. If provided, they should be a comma-separated list of scopes (e.g., `scope1,scope2`). The server will internally convert these to space-separated format as required by the OAuth 2.0 specification.
  - **Token Type**: The client credentials flow uses the **Access Token** for authentication, not the ID Token.

## OAuth 2.0 and OpenID Connect Support

The OpenAPI MCP Server supports OAuth 2.0 and OpenID Connect through the Cognito authentication provider with client credentials flow. This allows for secure service-to-service authentication without requiring a user.

### OAuth 2.0 Client Credentials Flow

The client credentials flow is designed for service-to-service authentication where a client application needs to access resources on its own behalf, not on behalf of a user. This flow is ideal for server-side applications that need to authenticate to APIs.

#### How It Works

1. The client application authenticates to the authorization server (Cognito) using its client ID and client secret.
2. If the credentials are valid, the authorization server returns an access token.
3. The client application uses the access token to authenticate to the API.
4. The access token is automatically refreshed when it expires.

#### Configuration

To use the client credentials flow, you need to provide:

- **Client ID**: The ID of the client application registered with Cognito.
- **Client Secret**: The secret key of the client application.
- **Domain**: The domain prefix of your Cognito user pool.
- **Region**: The AWS region where your Cognito user pool is located.
- **Scopes** (optional): The scopes to request for the access token.

#### Example

```bash
export AUTH_TYPE=cognito
export AUTH_COGNITO_CLIENT_ID="your-client-id"
export AUTH_COGNITO_CLIENT_SECRET="your-client-secret"
export AUTH_COGNITO_DOMAIN="your-domain-prefix"
export AUTH_COGNITO_REGION="us-east-2"
export AUTH_COGNITO_SCOPES="scope1 scope2"  # Optional
python -m awslabs.openapi_mcp_server.server
```

### OpenID Connect Support

OpenID Connect is built on top of OAuth 2.0 and adds identity functionality. The client credentials flow in OpenID Connect works the same way as in OAuth 2.0, but with additional identity-related scopes and tokens.

To use OpenID Connect features, include OpenID Connect scopes in your scope list:

```bash
export AUTH_COGNITO_SCOPES="api:read,api:write"
```

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

You can configure the cache TTL (Time-To-Live) for authentication data:

```bash
# Set authentication cache TTL to 1 hour (3600 seconds)
python -m awslabs.openapi_mcp_server.server --auth-type bearer --auth-token "YOUR_TOKEN" --auth-token-ttl 3600
```

Note: This setting controls how long the server caches authentication headers locally before regenerating them. It does not affect the actual expiration time of the token itself, which is determined by the authentication server that issued the token.

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

## Verifying Authentication

To verify your authentication configuration is working correctly:

1. Start the server with debug logging enabled:
   ```bash
   python -m awslabs.openapi_mcp_server.server --auth-type your_auth_type [your auth options] --log-level DEBUG
   ```

2. Check the logs for successful authentication messages

3. Make a simple request through your LLM tool to verify API connectivity:
   - For Amazon Q CLI: "Can you list the available endpoints in my API?"
   - For Cline: "Make a simple request to my API to verify authentication is working"

If you encounter authentication errors, see the Troubleshooting section below.

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

For client credentials flow:

```
DEBUG | awslabs.openapi_mcp_server.auth.cognito_auth:__init__:50 - Cognito auth configuration: ClientID=client-id, Client Secret=SET, Domain=domain-prefix, Region=us-east-2
```

To enable these debug logs, run the server with `--log-level DEBUG`:

```bash
python -m awslabs.openapi_mcp_server.server --auth-type cognito --log-level DEBUG [other options]
```

Common Cognito authentication issues:

1. **Missing credentials**: Check that all required parameters are set (client ID, username/password or client secret)
2. **Invalid credentials**: Verify the credentials are correct in the AWS Cognito console
3. **Expired token**: The server will automatically attempt to refresh expired tokens
4. **User not confirmed**: Confirm the user in the AWS Cognito console
5. **Missing User Pool ID**: Some Cognito configurations require a User Pool ID
6. **Invalid domain**: For client credentials flow, ensure the domain prefix is correct
7. **Invalid scopes**: For client credentials flow, ensure the requested scopes are allowed for the client
## AWS Documentation References

### Bearer Token Authentication
- [Understanding JSON Web Tokens (JWTs)](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-with-identity-providers.html)
- [Using the ID token](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-with-identity-providers.html#amazon-cognito-user-pools-using-the-id-token)

### Cognito Authentication - Password Flow
- [User Pool Authentication Flow](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-authentication-flow.html)
- [Using the AWS CLI with Cognito User Pools](https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/index.html)
- [Initiating Auth with the AWS CLI](https://docs.aws.amazon.com/cli/latest/reference/cognito-idp/initiate-auth.html)

### Cognito Authentication - OAuth 2.0 Client Credentials Flow
- [Token Endpoint](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html)
- [Using the Client Credentials Grant](https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html#client-credentials)
- [Setting up a User Pool App Client](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-client-apps.html)
- [Resource Server and Scopes](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-define-resource-servers.html)
