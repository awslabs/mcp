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

"""AgentCore MCP Server - Identity Management Module.

Contains API key credential provider creation, management, and runtime utilities.

MCP TOOLS IMPLEMENTED:
• create_credential_provider - Create API key credential providers
• list_credential_providers - List all credential providers
• get_credential_provider - Get specific credential provider details
• update_credential_provider - Update existing credential providers
• delete_credential_provider - Delete credential providers

"""

import time
from .utils import RUNTIME_AVAILABLE, SDK_AVAILABLE
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Literal


# ============================================================================
# IDENTITY MANAGEMENT TOOLS
# ============================================================================


def register_identity_tools(mcp: FastMCP):
    """Register identity and credential provider management tools."""

    @mcp.tool()
    async def manage_credentials(
        action: Literal['create', 'list', 'delete', 'get', 'update'] = Field(
            default='list', description='Credential action'
        ),
        provider_name: str = Field(default='', description='Name of the credential provider'),
        api_key: str = Field(default='', description='API key value (for create/update)'),
        description: str = Field(default='', description='Description of the credential provider'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ):
        """Security: IDENTITY & CREDENTIAL MANAGEMENT.

        Manage API key credential providers for use in agents at runtime.
        These providers allow agents to securely access API keys without hardcoding them.

        Actions:
        - create: Create a new API key credential provider
        - list: List all credential providers
        - delete: Delete a credential provider
        - get: Get details of a specific provider
        - update: Update an existing provider
        """
        if not SDK_AVAILABLE:
            return """X AgentCore SDK Not Available

To use credential provider functionality:
1. Install: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`
2. Configure AWS credentials: `aws configure`
3. Retry credential operations

Alternative: Use AWS Console for credential management"""
        from bedrock_agentcore.services.identity import IdentityClient

        try:
            # Initialize Identity Client
            identity_client = IdentityClient(region=region)

            # Action: create - Create new API key credential provider
            if action == 'create':
                if not provider_name:
                    return """X Error: provider_name is required for create action

Example:
```python
manage_credentials(
    action="create",
    provider_name="openai-api-key", # pragma: allowlist secret
    api_key="sk-...", # pragma: allowlist secret
    description="OpenAI API key for GPT models" # pragma: allowlist secret
)
```"""

                if not api_key:
                    return """X Error: api_key is required for create action

Example:
```python
manage_credentials(
    action="create",
    provider_name="my-api-provider", # pragma: allowlist secret
    api_key="your-actual-api-key-here" # pragma: allowlist secret
)
```"""

                try:
                    # Create the credential provider
                    provider_config = {'name': provider_name, 'apiKey': api_key}

                    if description:
                        provider_config['description'] = description

                    result = identity_client.create_api_key_credential_provider(provider_config)

                    return f"""# OK Credential Provider Created Successfully

## Provider Details:
- Name: `{provider_name}`
- Type: API Key Credential Provider
- Region: `{region}`
- Created: {time.strftime('%Y-%m-%d %H:%M:%S')}
{f'- Description: {description}' if description else ''}
- full result: {result}
## Usage in Agent Code:
```python
from bedrock_agentcore.identity.auth import requires_api_key

@requires_api_key(provider_name="{provider_name}")
async def my_function(*, api_key: str):
    # The API key is automatically injected
    print(f"Using API key: {{api_key[:8]}}...")
    # Use the API key for authentication
    headers = {{"Authorization": f"Bearer {{api_key}}"}}
    # Make your API calls...
```

## Next Steps:
1. List providers: `manage_credentials(action="list")`
2. Use in agents: Import and use the `@requires_api_key` decorator
3. Update if needed: `manage_credentials(action="update", provider_name="{provider_name}")`

Secure: Security: API key is securely stored and encrypted by AWS AgentCore Identity service."""

                except Exception as create_error:
                    return f"""X Failed to Create Credential Provider

Provider Name: `{provider_name}`
Error: {str(create_error)}

Possible Causes:
- Provider name already exists
- Invalid API key format
- Insufficient AWS permissions
- Network connectivity issues

Troubleshooting:
1. Check if provider exists: `manage_credentials(action="list")`
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Ensure unique provider name
4. Check API key format"""

            # Action: list - List all credential providers
            elif action == 'list':
                try:
                    # Get all credential providers

                    api_key_providers = (
                        identity_client.cp_client.list_api_key_credential_providers()
                    )
                    oauth2_providers = identity_client.cp_client.list_oauth2_credential_providers()
                    providers = api_key_providers.get(
                        'credentialProviders', []
                    ) + oauth2_providers.get('credentialProviders', [])

                    if not providers or len(providers) == 0:
                        return f"""# Security: No Credential Providers Found

Region: {region}

## Getting Started:
Create your first credential provider:
```python
manage_credentials(
    action="create",
    provider_name="my-api-key", # pragma: allowlist secret
    api_key="your-api-key-here", # pragma: allowlist secret
    description="My API service credentials" # pragma: allowlist secret
)
```

## Common Use Cases:
- OpenAI API: Store GPT model API keys
- Third-party APIs: Store authentication tokens
- External Services: Store service credentials
- Custom APIs: Store your own API keys

## Benefits:
- Secure: Secure storage with AWS encryption
- Target: Runtime injection via decorators
- Note: No hardcoded keys in agent code
- Reuse: Reusable across multiple agents"""

                    # Format results
                    result_parts = []
                    result_parts.append('# Security: Credential Providers')
                    result_parts.append('')
                    result_parts.append(f'Region: {region}')
                    result_parts.append(f'Total Providers: {len(providers)}')
                    result_parts.append('')

                    # List each provider
                    for i, provider in enumerate(providers, 1):
                        name = provider.get('name', 'Unknown')
                        provider_type = provider.get('type', 'API Key')
                        created_at = provider.get('createdAt', 'Unknown')
                        description = provider.get('description', '')

                        result_parts.append(f'## {i}. {name}')
                        result_parts.append(f'- Type: {provider_type}')
                        result_parts.append(f'- Created: {created_at}')
                        if description:
                            result_parts.append(f'- Description: {description}')
                        result_parts.append(
                            f'- Usage: `@requires_api_key(provider_name="{name}")`'
                        )
                        result_parts.append(
                            f'- Delete: `manage_credentials(action="delete", provider_name="{name}")`'
                        )
                        result_parts.append('')

                    result_parts.append('## Usage Example:')
                    result_parts.append('```python')
                    result_parts.append(
                        'from bedrock_agentcore.identity.auth import requires_api_key'
                    )
                    result_parts.append('')
                    result_parts.append(
                        f'@requires_api_key(provider_name="{providers[0].get("name", "your-provider")}")'
                    )
                    result_parts.append('async def call_external_api(*, api_key: str):')
                    result_parts.append("    headers = {'Authorization': f'Bearer {api_key}'}")
                    result_parts.append('    # Make your API calls...')
                    result_parts.append('```')
                    result_parts.append('')
                    result_parts.append('## Management:')
                    result_parts.append(
                        '- Create new: `manage_credentials(action="create", provider_name="name", api_key="key")`'  # pragma: allowlist secret
                    )
                    result_parts.append(
                        '- Get details: `manage_credentials(action="get", provider_name="name")`'
                    )
                    result_parts.append(
                        '- Update: `manage_credentials(action="update", provider_name="name", api_key="new_key")`'  # pragma: allowlist secret
                    )

                    return '\n'.join(result_parts)

                except Exception as list_error:
                    return f"""X Failed to List Credential Providers

Region: {region}
Error: {str(list_error)}

Possible Causes:
- AWS credentials not configured
- Insufficient permissions for AgentCore Identity service
- Network connectivity issues

Troubleshooting:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify AgentCore permissions
3. Try creating a provider first"""

            # Action: delete - Delete credential provider
            elif action == 'delete':
                if not provider_name:
                    return 'X Error: provider_name is required for delete action'

                try:
                    delete_result = identity_client.cp_client.delete_api_key_credential_provider(
                        credentialProviderName=provider_name
                    )
                except ValueError:
                    delete_result = identity_client.cp_client.delete_oauth2_credential_provider(
                        credentialProviderName=provider_name
                    )

                    return f"""# OK Credential Provider Deleted

## Deleted Provider:
- Name: `{provider_name}`
- Status: Permanently deleted
- Region: `{region}`

## ! Important Notes:
- Deletion is permanent and cannot be undone
- Any agents using this provider will lose access to the API key
- Update agent code to remove references to this provider

## Next Steps:
1. Update agents: Remove `@requires_api_key(provider_name="{provider_name}")` decorators
2. Check remaining: `manage_credentials(action="list")`
3. Create new if needed: `manage_credentials(action="create", ...)`

Provider `{provider_name}` has been completely removed."""

                except Exception as delete_result:
                    return f"""X Failed to Delete Credential Provider

Provider Name: `{provider_name}`
Error: {str(delete_result)}

Possible Causes:
- Provider doesn't exist
- Provider is currently in use by agents
- Insufficient permissions

Check Status: `manage_credentials(action="list")` to see available providers"""

            # Action: get - Get provider details
            elif action == 'get':
                if not provider_name:
                    return 'X Error: provider_name is required for get action'

                try:
                    provider = identity_client.cp_client.get_api_key_credential_provider(
                        credentialProviderName=provider_name
                    )
                except ValueError as get_error:
                    print(str(get_error))
                    provider = identity_client.cp_client.get_oauth2_credential_provider(
                        credentialProviderName=provider_name
                    )

                    return f"""# Security: Credential Provider Details

## Provider Information:
- Name: `{provider.get('name', provider_name)}`
- Type: {provider.get('type', 'API Key')}
- Region: `{region}`
- Created: {provider.get('createdAt', 'Unknown')}
- Status: {provider.get('status', 'Active')}
{f'- Description: {provider.get("description", "")}' if provider.get('description') else ''}

## Usage in Agent Code:
```python
from bedrock_agentcore.identity.auth import requires_api_key

@requires_api_key(provider_name="{provider_name}")
async def my_function(*, api_key: str):
    # API key automatically injected here
    headers = {{"Authorization": f"Bearer {{api_key}}"}}
    # Use for API calls...
```

## Management Options:
- Update: `manage_credentials(action="update", provider_name="{provider_name}", api_key="new_key")` # pragma: allowlist secret
- Delete: `manage_credentials(action="delete", provider_name="{provider_name}")`
- List all: `manage_credentials(action="list")`

Secure: Security: API key value is never displayed for security reasons."""

                except Exception as get_error:
                    return f"""X Failed to Get Credential Provider

Provider Name: `{provider_name}`
Error: {str(get_error)}

Possible Causes:
- Provider doesn't exist
- Insufficient permissions

Check Available: `manage_credentials(action="list")`"""

            # Action: update - Update credential provider
            elif action == 'update':
                if not provider_name:
                    return 'X Error: provider_name is required for update action'
                if not api_key:
                    return 'X Error: api_key is required for update action'

                try:
                    # Update the credential provider
                    update_config = {'name': provider_name, 'apiKey': api_key}

                    if description:
                        update_config['description'] = description

                    try:
                        update_result = (
                            identity_client.cp_client.update_api_key_credential_provider(
                                credentialProviderName=provider_name, **update_config
                            )
                        )
                    except ValueError as update_error:
                        print(update_error)
                        update_result = (
                            identity_client.cp_client.update_oauth2_credential_provider(
                                credentialProviderName=provider_name, **update_config
                            )
                        )

                    return f"""# OK Credential Provider Updated

## Updated Provider:
- Name: `{provider_name}`
- Status: Successfully updated
- Region: `{region}`
- Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
- result: {update_result}
{f'- Description: {description}' if description else ''}

## ! Important Notes:
- New API key is now active
- Old API key is permanently invalidated
- Agents using this provider will automatically use the new key

## Next Steps:
1. Test agents: Ensure they work with the new API key
2. Verify access: Check that API calls succeed
3. Monitor usage: Watch for any authentication errors

Secure: Security: Old API key is securely deleted and new key is encrypted."""

                except Exception as update_error:
                    return f"""X Failed to Update Credential Provider

Provider Name: `{provider_name}`
Error: {str(update_error)}

Possible Causes:
- Provider doesn't exist
- Invalid API key format
- Insufficient permissions

Check Status: `manage_credentials(action="get", provider_name="{provider_name}")`"""

            else:
                return f"""X Unknown Action: {action}

## Available Actions:
- create: Create new credential provider
- list: List all providers
- delete: Delete a provider
- get: Get provider details
- update: Update provider API key

## Example:
```python
manage_credentials(action="create", provider_name="my-key", api_key="secret") # pragma: allowlist secret
```"""

        except ImportError as e:
            return f"""X Required Dependencies Missing

Error: {str(e)}

To use credential provider functionality:
1. Install AgentCore: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`
2. Configure AWS: `aws configure`

Alternative: Use AWS Console for credential management"""

        except Exception as e:
            return f"""X Credential Management Error: {str(e)}

Action: {action}
Provider: {provider_name or 'Not specified'}
Region: {region}

Troubleshooting:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify AgentCore permissions
3. Check provider exists: `manage_credentials(action="list")`"""


## ============================================================================
## OAUTH ACCESS TOKEN GENERATION
## ============================================================================


def register_oauth_tools(mcp: FastMCP):
    """Register OAuth-related tools with the MCP server."""

    @mcp.tool()
    async def get_oauth_access_token(
        method: Literal['ask', 'gateway_client', 'manual_curl'] = Field(
            default='ask', description='Token generation method'
        ),
        gateway_name: str = Field(
            default='', description='Gateway name (for gateway_client method)'
        ),
        client_id: str = Field(default='', description='OAuth client ID (for manual_curl method)'),
        client_secret: str = Field(
            default='', description='OAuth client secret (for manual_curl method)'
        ),
        token_endpoint: str = Field(
            default='', description='OAuth token endpoint URL (for manual_curl method)'
        ),
        scope: str = Field(default='', description='OAuth scope (for manual_curl method)'),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Generate OAuth access tokens for AgentCore gateways using multiple methods.

        Methods:
        - gateway_client: Uses simplified GatewayClient from starter toolkit (recommended)
        - manual_curl: Direct OAuth 2.0 client credentials flow via HTTP
        - ask: Present both options to choose from
        """
        try:
            ## Method: ask - Present options
            if method == 'ask':
                return """## 🔐 OAuth Access Token Generation - Choose Your Method

#### Option 1: Gateway Client (Recommended)
Uses the simplified `GatewayClient` from the bedrock-agentcore-starter-toolkit.

Advantages:
- OK Built-in retry logic and error handling
- OK Automatic DNS propagation handling
- OK Abstracts OAuth complexity
- OK Works with stored gateway configurations

Usage:
```python
get_oauth_access_token(
    method="gateway_client",
    gateway_name="your-gateway-name"
)
```

#### Option 2: Manual cURL (Direct Control)
Direct OAuth 2.0 client credentials flow via HTTP requests.

Advantages:
- Full control over OAuth flow
- No gateway client dependencies
- Good for debugging OAuth issues
- Can be used outside Python environments

Usage:
```python
get_oauth_access_token(
    method="manual_curl",
    client_id="<your-client-id>",
    client_secret="<your-client-secrt>",
    token_endpoint="https://your-domain.auth.region.amazoncognito.com/oauth2/token",
    scope="gateway-name/invoke"
)
```

Quick Setup:
If you have a gateway but need credentials, first get them:
agent_gateway(action="auth", gateway_name="your-gateway-name")

Choose your preferred method and call this tool again with the appropriate parameters."""

            ## Method: gateway_client - Use simplified toolkit approach
            elif method == 'gateway_client':
                if not gateway_name:
                    return 'Error: gateway_name is required for gateway_client method\n'

                try:
                    if not RUNTIME_AVAILABLE:
                        return """Gateway Client Not Available

Issue: bedrock-agentcore-starter-toolkit not installed

To install:
```bash
uv add bedrock-agentcore-starter-toolkit
## or
pip install bedrock-agentcore-starter-toolkit
```

Alternative: Use `method="manual_curl"` with explicit credentials"""

                    ## Use the starter toolkit GatewayClient approach
                    import json

                    ## Load gateway configuration
                    import os
                    from bedrock_agentcore_starter_toolkit.operations.gateway.client import (
                        GatewayClient,
                    )

                    config_dir = os.path.expanduser('~/.agentcore_gateways')
                    config_file = os.path.join(config_dir, f'{gateway_name}.json')

                    if not os.path.exists(config_file):
                        ## Try to get cognito info from gateway setup

                        try:
                            ## Create OAuth if not exists (EZ Auth)
                            from bedrock_agentcore_starter_toolkit.operations.gateway.client import (
                                GatewayClient,
                            )

                            client = GatewayClient()
                            cognito_result = client.create_oauth_authorizer_with_cognito(
                                gateway_name
                            )
                            client_info = cognito_result.get('client_info', {})
                        except Exception as e:
                            return f"""Gateway Configuration Not Found: `{gateway_name}`

Issue: No stored configuration and failed to create OAuth setup
Error: {str(e)}

Solutions:
1. Create gateway first: `agent_gateway(action="setup", gateway_name="{gateway_name}")`
2. Use manual method: Get credentials from AWS Cognito Console
3. List existing gateways: `agent_gateway(action="list")`

Config Directory: `{config_dir}`"""
                    else:
                        ## Load stored configuration
                        with open(config_file, 'r') as f:
                            gateway_config = json.load(f)
                        client_info = gateway_config.get('cognito_client_info', {})

                    if not client_info:
                        return f"""Missing OAuth Configuration: `{gateway_name}`

Issue: Gateway exists but missing OAuth client info

Solutions:
1. Recreate gateway: `agent_gateway(action="setup", gateway_name="{gateway_name}")`
2. Use manual method: Get credentials from AWS Cognito Console
3. Check configuration: `{config_file}`"""

                    ## Get access token using GatewayClient
                    gateway_client = GatewayClient(region_name=region)
                    access_token = gateway_client.get_access_token_for_cognito(client_info)

                    return f"""## OK Access Token Generated (Gateway Client)

#### Gateway: `{gateway_name}`
- Method: Simplified GatewayClient
- Region: {region}
- Token Type: Bearer

#### Target: Access Token:
```
{access_token}
```

#### Tip: Usage Examples:

##### MCP Client Integration:
```python
from mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

## Replace with your actual gateway URL from AWS Console
gateway_url = "https://gateway-id.bedrock-agentcore.{region}.amazonaws.com/mcp"

client = MCPClient(
    lambda: streamablehttp_client(
        gateway_url,
        headers={{"Authorization": "Bearer {access_token}"}}
    )
)

with client:
    tools = client.list_tools_sync()
    print([tool.tool_name for tool in tools])
```

##### Direct HTTP Request:
```bash
curl -H "Authorization: Bearer {access_token}" \\
     https://your-gateway-url/mcp/tools
```

#### ! Important Notes:
- Token expires: Use this tool to generate new tokens when needed
- Store securely: Don't commit tokens to version control
- Gateway URL: Check AWS Console for exact endpoint URL

Success: Ready to connect to gateway with simplified token management!"""

                except Exception as e:
                    return f"""Gateway Client Error: {str(e)}

Gateway: `{gateway_name}`
Method: gateway_client

Possible Causes:
- Gateway configuration missing or invalid
- Network connectivity issues
- AWS credentials expired
- Cognito User Pool or App Client deleted

Solutions:
1. Check gateway exists: `agent_gateway(action="list")`
2. Recreate gateway: `agent_gateway(action="setup", gateway_name="{gateway_name}")`
3. Try manual method: Use explicit OAuth credentials
4. Check AWS Console: Verify Cognito User Pool exists"""

            ## Method: manual_curl - Direct OAuth 2.0 flow
            elif method == 'manual_curl':
                if not all([client_id, client_secret, token_endpoint, scope]):
                    return """Missing Required Parameters for Manual cURL

Required Parameters:
- `client_id`: OAuth client ID from Cognito
- `client_secret`: OAuth client secret from Cognito
- `token_endpoint`: OAuth token endpoint URL
- `scope`: OAuth scope (usually gateway-name/invoke)

Example:
```python
get_oauth_access_token(
    method="manual_curl",
    client_id="<your-client-id>",
    client_secret="<your-client-secrt>",
    token_endpoint="https://agentcore-cf32b91a.auth.us-east-1.amazoncognito.com/oauth2/token",
    scope="clean-dynamodb-gateway/invoke"
)
```

To get credentials:
1. From existing gateway: `agent_gateway(action="auth", gateway_name="your-gateway")`
2. From AWS Console: Cognito → User Pools → App clients"""
                import json
                import subprocess

                try:
                    ## Build curl command for OAuth 2.0 client credentials flow
                    curl_cmd = [
                        'curl',
                        '-X',
                        'POST',
                        token_endpoint,
                        '-H',
                        'Content-Type: application/x-www-form-urlencoded',
                        '-d',
                        f'grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}&scope={scope}',
                        '--silent',
                    ]

                    ## Execute curl command
                    result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)

                    if result.returncode == 0:
                        try:
                            ## Parse JSON response
                            token_data = json.loads(result.stdout)
                            access_token = token_data.get('access_token')
                            token_type = token_data.get('token_type', 'Bearer')
                            expires_in = token_data.get('expires_in', 'Unknown')

                            if not access_token:
                                return f"""No Access Token in Response

Response: {result.stdout}
Token Endpoint: {token_endpoint}

Possible Issues:
- Invalid client credentials
- Incorrect scope
- Token endpoint URL wrong
- Cognito configuration issues"""

                            return f"""## OK Access Token Generated (Manual cURL)

#### OAuth Details:
- Client ID: `{client_id}`
- Scope: `{scope}`
- Token Type: {token_type}
- Expires In: {expires_in} seconds

#### Target: Access Token:
```
{access_token}
```

#### Tip: Usage Examples:

##### cURL Command:
```bash
curl -H "Authorization: Bearer {access_token}" \\
     https://your-gateway-url/mcp/tools
```

##### Python HTTP Client:
```python
import requests

headers = {{"Authorization": "Bearer {access_token}"}}
response = requests.get("https://your-gateway-url/mcp/tools", headers=headers)
print(response.json())
```

##### MCP Client:
```python
from mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

client = MCPClient(
    lambda: streamablehttp_client(
        "https://your-gateway-url/mcp",
        headers={{"Authorization": "Bearer {access_token}"}}
    )
)
```

#### ! Token Management:
- Expires: Token expires in {expires_in} seconds
- Refresh: Use this tool again to get a new token
- Security: Store securely, don't log or commit to version control

#### Update: Automated Refresh Script:
```python
def get_fresh_token():
    return get_oauth_access_token(
        method="manual_curl",
        client_id="{client_id}",
        client_secret="***", ## Your secret
        token_endpoint="{token_endpoint}",
        scope="{scope}"
    )
```

Success: Ready to use with full manual control over OAuth flow!"""

                        except json.JSONDecodeError:
                            return f"""Invalid JSON Response

Raw Response: {result.stdout}
Error Response: {result.stderr}
Token Endpoint: {token_endpoint}

Possible Issues:
- Token endpoint URL is incorrect
- OAuth server returned HTML error page
- Network connectivity issues
- DNS resolution problems"""

                    else:
                        return f"""OAuth Request Failed

cURL Error: {result.stderr}
Exit Code: {result.returncode}
Token Endpoint: {token_endpoint}

Troubleshooting:
1. Check endpoint URL: Verify the token endpoint is correct
2. Test connectivity: `curl {token_endpoint}`
3. Verify credentials: Check client ID and secret in AWS Console
4. Check scope: Ensure scope matches gateway configuration

Command that failed:
```bash
curl -X POST {token_endpoint} \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "grant_type=client_credentials&client_id={client_id}&client_secret=***&scope={scope}"
```"""

                except subprocess.TimeoutExpired:
                    return f"""OAuth Request Timeout

Token Endpoint: {token_endpoint}
Timeout: 30 seconds

Possible Causes:
- Network connectivity issues
- DNS resolution problems
- Token endpoint server issues
- Firewall blocking the request

Troubleshooting:
1. Test basic connectivity: `ping {token_endpoint.split('/')[2]}`
2. Check DNS: `nslookup {token_endpoint.split('/')[2]}`
3. Try from browser: Visit the endpoint URL
4. Check network settings: VPN, proxy, firewall"""

                except Exception as e:
                    return f"""Manual cURL Error: {str(e)}

Token Endpoint: {token_endpoint}
Client ID: {client_id}

Possible Causes:
- curl command not available
- Invalid parameters format
- System/environment issues

Alternative: Try the gateway_client method for automated handling"""

            else:
                return f"""Unknown Method: `{method}`

Available Methods:
- `ask` - Show method options (default)
- `gateway_client` - Use simplified GatewayClient (recommended)
- `manual_curl` - Direct OAuth 2.0 client credentials flow

Example:
```python
get_oauth_access_token(method="gateway_client", gateway_name="my-gateway")
```"""

        except Exception as e:
            return f'OAuth Token Generation Error: {str(e)}'
