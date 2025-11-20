# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AgentCore Gateway Tool - Manage MCP Gateway lifecycle and operations.

Comprehensive gateway operations including create, configure, list, get, and delete.
"""

from typing import Any, Dict


def manage_agentcore_gateway() -> Dict[str, Any]:
    """Provides comprehensive information on how to deploy and manage MCP Gateways in AgentCore.

    This tool returns detailed documentation about:
    - Gateway creation and configuration requirements
    - Step-by-step CLI deployment workflow
    - Target management for Lambda, OpenAPI, and Smithy models
    - Authentication and authorization setup
    - Common issues and troubleshooting

    Use this tool to understand the complete process of deploying and managing MCP Gateways.
    """
    deployment_guide = """
AGENTCORE GATEWAY DEPLOYMENT GUIDE
===================================

GATEWAY OVERVIEW:
MCP Gateways provide a managed endpoint for Model Context Protocol (MCP) servers, enabling:
- Centralized access to multiple MCP targets (Lambda functions, OpenAPI services, Smithy models)
- Built-in authentication and authorization
- Semantic search capabilities
- Automatic scaling and management

CLI DEPLOYMENT WORKFLOW:

Step 1: Install CLI
    pip install bedrock-agentcore-starter-toolkit

Step 2: Create MCP Gateway
    agentcore gateway create-mcp-gateway

    Available flags:
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --name TEXT                    Name of the gateway (defaults to TestGateway)
    --role-arn TEXT                IAM role ARN to use (creates one if not provided)
    --authorizer-config TEXT       Serialized authorizer config JSON (creates one if not provided)
    --enable_semantic_search       Enable semantic search tool (defaults to True)
    -sem                           Short flag for --enable_semantic_search

    Example:
    agentcore gateway create-mcp-gateway --name MyGateway --region us-east-1

Step 3: Add Gateway Targets
    Create targets to connect your gateway to actual services:

    A. Lambda Target (Default):
    agentcore gateway create-mcp-gateway-target \\
        --gateway-arn arn:aws:bedrock-agentcore:region:account:gateway/gateway-id \\
        --gateway-url https://gateway-url \\
        --role-arn arn:aws:iam::account:role/role-name \\
        --name MyLambdaTarget \\
        --target-type lambda

    B. OpenAPI Schema Target:
    agentcore gateway create-mcp-gateway-target \\
        --gateway-arn arn:aws:bedrock-agentcore:region:account:gateway/gateway-id \\
        --gateway-url https://gateway-url \\
        --role-arn arn:aws:iam::account:role/role-name \\
        --name MyAPITarget \\
        --target-type openApiSchema \\
        --target-payload '{"openApiSchema": {"uri": "https://api.example.com/openapi.json"}}' \\
        --credentials '{"api_key": "your-api-key", "credential_location": "header", "credential_parameter_name": "X-API-Key"}'  # pragma: allowlist secret

    C. Smithy Model Target:
    agentcore gateway create-mcp-gateway-target \\
        --gateway-arn arn:aws:bedrock-agentcore:region:account:gateway/gateway-id \\
        --gateway-url https://gateway-url \\
        --role-arn arn:aws:iam::account:role/role-name \\
        --name MySmithyTarget \\
        --target-type smithyModel

    Available flags for create-mcp-gateway-target:
    --gateway-arn TEXT             ARN of the created gateway (required)
    --gateway-url TEXT             URL of the created gateway (required)
    --role-arn TEXT                IAM role ARN of the created gateway (required)
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --name TEXT                    Name of the target (defaults to TestGatewayTarget)
    --target-type TEXT             Type: 'lambda', 'openApiSchema', 'mcpServer', or 'smithyModel' (defaults to 'lambda')
    --target-payload TEXT          Target specification JSON (required for openApiSchema targets)
    --credentials TEXT             Credentials JSON for target access (API key or OAuth2, for openApiSchema targets)

MANAGEMENT COMMANDS:

List Gateways:
    agentcore gateway list-mcp-gateways

    Available flags:
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --name TEXT                    Filter by gateway name
    --max-results INTEGER          Maximum number of results to return (defaults to 50, max 1000)
    -m INTEGER                     Short flag for --max-results

Get Gateway Details:
    agentcore gateway get-mcp-gateway --name MyGateway
    # OR
    agentcore gateway get-mcp-gateway --id gateway-id
    # OR
    agentcore gateway get-mcp-gateway --arn arn:aws:bedrock-agentcore:region:account:gateway/gateway-id

    Available flags:
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --id TEXT                      Gateway ID
    --name TEXT                    Gateway name (will look up ID)
    --arn TEXT                     Gateway ARN (will extract ID)

List Gateway Targets:
    agentcore gateway list-mcp-gateway-targets --name MyGateway

    Available flags:
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --id TEXT                      Gateway ID
    --name TEXT                    Gateway name (will look up ID)
    --arn TEXT                     Gateway ARN (will extract ID)
    --max-results INTEGER          Maximum number of results to return (defaults to 50, max 1000)
    -m INTEGER                     Short flag for --max-results

Get Target Details:
    agentcore gateway get-mcp-gateway-target --name MyGateway --target-name MyTarget

    Available flags:
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --id TEXT                      Gateway ID
    --name TEXT                    Gateway name (will look up ID)
    --arn TEXT                     Gateway ARN (will extract ID)
    --target-id TEXT               Target ID
    --target-name TEXT             Target name (will look up ID)

CLEANUP COMMANDS:

Delete Gateway Target:
    agentcore gateway delete-mcp-gateway-target --name MyGateway --target-name MyTarget

    Available flags:
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --id TEXT                      Gateway ID
    --name TEXT                    Gateway name (will look up ID)
    --arn TEXT                     Gateway ARN (will extract ID)
    --target-id TEXT               Target ID to delete
    --target-name TEXT             Target name to delete (will look up ID)

Delete Gateway:
    agentcore gateway delete-mcp-gateway --name MyGateway

    Note: Gateway must have zero targets before deletion, unless --force is used

    Available flags:
    --region TEXT                  AWS region to use (defaults to us-west-2)
    --id TEXT                      Gateway ID to delete
    --name TEXT                    Gateway name to delete (will look up ID)
    --arn TEXT                     Gateway ARN to delete (will extract ID)
    --force                        Delete all targets before deleting the gateway

AUTHENTICATION & AUTHORIZATION:

Automatic Setup:
- CLI automatically creates Cognito User Pool and OAuth2 configuration
- Uses client credentials flow for machine-to-machine authentication
- Creates resource server with 'invoke' scope

Manual Configuration:
- Provide --authorizer-config with custom JWT authorizer configuration
- Format: '{"customJWTAuthorizer": {"allowedClients": ["client-id"], "discoveryUrl": "https://..."}}'

CREDENTIAL PROVIDERS FOR OPENAPI TARGETS:

API Key Authentication:
{
    "api_key": "your-api-key",  # pragma: allowlist secret
    "credential_location": "header",  # or "query"
    "credential_parameter_name": "X-API-Key"
}

OAuth2 Authentication (Custom):
{
    "oauth2_provider_config": {
        "customOauth2ProviderConfig": {
            "oauthDiscovery": {
                "discoveryUrl": "https://auth.example.com/.well-known/openid-configuration"
            },
            "clientId": "your-client-id",
            "clientSecret": "your-client-secret"  # pragma: allowlist secret
        }
    },
    "scopes": ["read", "write"]
}

OAuth2 Authentication (Google):
{
    "oauth2_provider_config": {
        "googleOauth2ProviderConfig": {
            "clientId": "your-google-client-id",
            "clientSecret": "your-google-client-secret"  # pragma: allowlist secret
        }
    },
    "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
}

TARGET TYPES:

1. Lambda Target:
   - Automatically creates test Lambda function if no target payload provided
   - Requires Lambda invoke permissions on gateway execution role
   - Supports custom Lambda ARN and tool schema configuration

2. OpenAPI Schema Target:
   - Requires target payload with OpenAPI specification URI
   - Supports API key and OAuth2 authentication
   - Automatically creates credential providers

3. MCP Server Target:
   - Connects to existing MCP servers
   - Enables integration with external MCP-compatible services
   - Requires appropriate authentication configuration

4. Smithy Model Target:
   - Uses pre-configured Smithy models (e.g., DynamoDB)
   - Automatically selects appropriate model for region
   - No additional configuration required

COMMON PATTERNS:

Complete Gateway Setup:
    # 1. Create gateway
    agentcore gateway create-mcp-gateway --name ProductionGateway --region us-east-1

    # 2. Add Lambda target
    agentcore gateway create-mcp-gateway-target \\
        --gateway-arn <gateway-arn> \\
        --gateway-url <gateway-url> \\
        --role-arn <role-arn> \\
        --name LambdaProcessor \\
        --target-type lambda

    # 3. Add API target
    agentcore gateway create-mcp-gateway-target \\
        --gateway-arn <gateway-arn> \\
        --gateway-url <gateway-url> \\
        --role-arn <role-arn> \\
        --name ExternalAPI \\
        --target-type openApiSchema \\
        --target-payload '{"openApiSchema": {"uri": "https://api.example.com/openapi.json"}}' \\
        --credentials '{"api_key": "key123", "credential_location": "header", "credential_parameter_name": "Authorization"}'  # pragma: allowlist secret

Gateway Cleanup:
    # Option 1: Delete targets individually, then gateway
    agentcore gateway list-mcp-gateway-targets --name ProductionGateway
    agentcore gateway delete-mcp-gateway-target --name ProductionGateway --target-name LambdaProcessor
    agentcore gateway delete-mcp-gateway-target --name ProductionGateway --target-name ExternalAPI
    agentcore gateway delete-mcp-gateway --name ProductionGateway

    # Option 2: Force delete gateway and all targets at once
    agentcore gateway delete-mcp-gateway --name ProductionGateway --force

KEY POINTS:
- Gateways provide centralized MCP endpoint management
- Multiple target types supported (Lambda, OpenAPI, Smithy)
- Automatic authentication setup with Cognito
- Semantic search enabled by default
- Region defaults to us-west-2
- Gateway must be empty (no targets) before deletion
- IAM roles and Cognito resources created automatically if not provided
"""

    return {'deployment_guide': deployment_guide}
