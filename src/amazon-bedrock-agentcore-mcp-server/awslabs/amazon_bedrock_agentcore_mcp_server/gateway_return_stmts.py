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
"""AgentCore MCP Server - Gateway long return statements.

Adding longer return statements and errors here
"""

return_sdk_not_available = """X AgentCore SDK Not Available

To use gateway functionality:
1. Install: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`
2. Configure AWS credentials: `aws configure`
3. Retry gateway operations

Alternative: Use AWS Console for gateway management"""

# --------------------------------------------------------------------------------------

return_no_gateways_found = """# Gateway: No Gateways Found

Region: {region}

## Getting Started:
Create your first gateway:
```python
agent_gateway(action="setup", gateway_name="my-gateway", smithy_model="dynamodb")
```

## Available Smithy Models:
Use `agent_gateway(action="discover")` to see all AWS services available for gateway integration.

## AWS Console:
[Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
"""

# --------------------------------------------------------------------------------------

return_list_gateway_error = """X Gateway List Error: {error_message}

Region: {region}

Possible Causes:
- AWS credentials not configured
- Insufficient permissions
- AgentCore service not available in region

Troubleshooting:
1. Check credentials: `aws sts get-caller-identity`
2. Verify region: AgentCore available in us-east-1, us-west-2
3. Check permissions: bedrock-agentcore-control:ListGateways"""

# --------------------------------------------------------------------------------------

return_gateway_deletion_error = """X Gateway Deletion Failed - Targets Still Exist

Gateway: `{gateway_name}` ({gateway_id})
Issue: {remaining_targets_count} targets could not be deleted after {max_deletion_attempts} attempts with throttling protection

## Deletion Steps Attempted:
{deletion_steps_formatted}

## Remaining Targets:
{remaining_targets_formatted}

## This indicates a persistent AWS issue. Try:
1. Wait 10-15 minutes for AWS to fully process deletions
2. Use AWS Console to manually delete targets
3. Contact AWS Support if targets cannot be deleted manually

AWS Console: [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)"""

# --------------------------------------------------------------------------------------

return_gateway_deletion_error_2 = """X Gateway Deletion Failed

Gateway: `{gateway_name}` ({gateway_id})
Region: {region}

## Deletion Steps Attempted:
{deletion_steps_formatted}

Final Error: {delete_error_message}

Possible Causes:
- AWS service temporary issues
- Network connectivity problems
- Insufficient permissions for gateway deletion
- Targets may still be processing deletion

Troubleshooting:
1. Wait 10-15 minutes and retry: AWS may need more time to process target deletions
2. Check AWS Console: [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
3. Verify permissions: Ensure your AWS role has `bedrock-agentcore-control:DeleteGateway` permission
4. Retry deletion: `agent_gateway(action="delete", gateway_name="{gateway_name}")`

If problem persists, this may be an AWS service issue."""

# --------------------------------------------------------------------------------------

return_gateway_deleted_ok = """# OK Gateway Deleted Successfully

## Deleted Gateway:
- Name: `{gateway_name}`
- ID: `{gateway_id}`
- Status: Deleted
- Region: {region}

## Deletion Steps:
{deletion_steps_formatted}

## ! Important Notes:
- Deletion is permanent and cannot be undone
- All gateway targets have been automatically deleted
- Any agents using this gateway will lose access to tools
- Cognito resources may still exist - check Cognito console if cleanup needed
- IAM roles may still exist - check IAM console if cleanup needed

## Next Steps:
- Update any agents that were using this gateway
- Remove gateway references from agent code
- Create new gateway if needed: `agent_gateway(action="setup", gateway_name="new_name")`

## AWS Console Links:
- [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
- [Cognito Console](https://console.aws.amazon.com/cognito/v2/home?region={region})
- [IAM Console](https://console.aws.amazon.com/iam/home?region={region}#/roles)

Gateway `{gateway_name}` has been completely removed from your AWS account."""

# --------------------------------------------------------------------------------------
return_gateway_delete_overall_error = """X Gateway Deletion Error: {error_message}

Gateway: `{gateway_name}`
Region: {region}

Possible Causes:
- Gateway doesn't exist or was already deleted
- AWS credentials not configured
- Network connectivity issues
- Insufficient permissions

Check Status: `agent_gateway(action="list")` to see available gateways"""


# --------------------------------------------------------------------------------------

return_smithy_gateway_creation_ok = """# Gateway: Gateway Setup Complete!

## Setup Steps:
{setup_steps_formatted}

## Gateway Information:
- Name: `{gateway_name}`
- Region: `{region}`
- Semantic Search: {semantic_search_status}
{smithy_model_line}
{openapi_spec_line}

## Next Steps:

### 1. Get Access Token:
```python
get_oauth_access_token(method="gateway_client", gateway_name="{gateway_name}")
```

### 2. Test Gateway:
```python
agent_gateway(action="test", gateway_name="{gateway_name}")
```

### 3. List Available Tools:
```python
agent_gateway(action="list_tools", gateway_name="{gateway_name}")
```

## AWS Console:
- [Gateway Management](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/gateways)
- [Cognito OAuth](https://console.aws.amazon.com/cognito/v2/home?region={region})

Your gateway is ready for MCP client connections! Success!"""

# --------------------------------------------------------------------------------------

return_gateway_testing = """# Test: Gateway MCP Testing

## Gateway: `{gateway_name}`

## Testing Steps:

### 1. Get Access Token:
```python
get_oauth_access_token(method="gateway_client", gateway_name="{gateway_name}")
```

### 2. List Available Tools:
```python
agent_gateway(action="list_tools", gateway_name="{gateway_name}")
```

### 3. Search Tools (if semantic search enabled):
```python
agent_gateway(action="search_tools", gateway_name="{gateway_name}", query="database operations")
```

### 4. Invoke Specific Tool:
```python
agent_gateway(
    action="invoke_tool",
    gateway_name="{gateway_name}",
    tool_name="DescribeTable",
    tool_arguments={{"TableName": "MyTable"}}
)
```

## MCP Client Example:
```python
from mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# Get gateway URL from AWS Console
gateway_url = "https://gateway-id.bedrock-agentcore.{region}.amazonaws.com/mcp"

# Get access token first
access_token = "YOUR_ACCESS_TOKEN"

client = MCPClient(
    lambda: streamablehttp_client(
        gateway_url,
        headers={{"Authorization": f"Bearer {{access_token}}"}}
    )
)

with client:
    # List tools
    tools = client.list_tools_sync()
    print([tool.tool_name for tool in tools])

    # Invoke tool
    result = client.call_tool_sync("DescribeTable", {{"TableName": "MyTable"}})
    print(result)
```

## Manual Testing:
```bash
# Get gateway endpoint from AWS Console first
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
     https://gateway-id.bedrock-agentcore.{region}.amazonaws.com/mcp/tools
```

Complete these steps to fully test your gateway's MCP functionality."""


# --------------------------------------------------------------------------------------

return_gateway_list = """# Tools: Gateway Tools List

## Gateway: `{gateway_name}`
Total Tools: {tools_count}
Gateway URL: `{gateway_url}`

## Available Tools:
{tools_list_formatted}

## Tool Names Only:
```
{tool_names}
```

## Usage Example:
```python
# Invoke a tool
agent_gateway(
    action="invoke_tool",
    gateway_name="{gateway_name}",
    tool_name="ListTables",  # Example DynamoDB tool
    tool_arguments={{}}
)
```

OK Gateway is ready for MCP tool invocation!"""

# --------------------------------------------------------------------------------------

return_gateway_search_results = """# Search: Gateway Semantic Search Results

## Gateway: `{gateway_name}`
Search Query: `{query}`
Matches Found: {matches_found}
Search Method: Built-in semantic search (x_amz_bedrock_agentcore_search)

## Matching Tools:
{matching_tools_formatted}

## Usage Example:
```python
# Invoke a matching tool
agent_gateway(
    action="invoke_tool",
    gateway_name="{gateway_name}",
    tool_name="TOOL_NAME_FROM_RESULTS",
    tool_arguments={{"key": "value"}}
)
```

Note: This uses the gateway's built-in semantic search for highly accurate, context-aware results"""

# --------------------------------------------------------------------------------------

return_gateway_tool_invoke_ok = """# Tool: Tool Invocation Result

## Gateway: `{gateway_name}`
Tool: `{tool_name}`
Arguments: `{args}`

## Result:
```json
{result_formatted}
```

## Status: OK Success

## Next Steps:
- Try other tools: `agent_gateway(action="list_tools", gateway_name="{gateway_name}")`
- Search tools: `agent_gateway(action="search_tools", gateway_name="{gateway_name}", query="your_query")`"""

# --------------------------------------------------------------------------------------

return_gateway_not_implemented = """# WIP: Action '{action}' Implementation

This action is available but requires additional implementation.

## Currently Available Actions:
- setup: Complete gateway setup with Cognito + targets
- list: List all existing gateways
- delete: Delete gateway and all targets (enhanced with retry logic)
- discover: Show available AWS Smithy models
- test: Show testing instructions
- list_tools: List gateway tools via MCP protocol OK
- search_tools: Semantic search for tools OK
- invoke_tool: Invoke specific tools OK

## Coming Soon:
- create: Create gateway only
- targets: Manage individual targets
- cognito: Manage OAuth settings
- auth: Get authentication info

For now, use `action="setup"` for complete gateway creation or `action="list"` to manage existing gateways."""

# --------------------------------------------------------------------------------------

return_gateway_operation_error = """X Gateway Operation Error: {error_message}

Action: {action}
Gateway: {gateway_name_formatted}
Region: {region}

Troubleshooting:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify permissions for bedrock-agentcore-control
3. Check gateway exists: `agent_gateway(action="list")`
4. Try individual actions for debugging"""
