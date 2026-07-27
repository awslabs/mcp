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

"""Static guide tool for AgentCore Gateway."""

from .models import GatewayGuideResponse
from mcp.server.fastmcp import Context


GATEWAY_GUIDE = """
# AgentCore Gateway — Comprehensive Guide

## Overview

AgentCore Gateway is a managed MCP (Model Context Protocol) server that
exposes backend tools — AWS Lambda functions, REST APIs via API Gateway,
OpenAPI- or Smithy-described services, and remote MCP servers — as a
single unified MCP endpoint that agents can discover and invoke. Gateway
handles inbound authentication (JWT, IAM, or none), outbound
authentication (IAM, OAuth, API key), protocol translation, semantic
tool search, and request/response interception.

---

## Prerequisites

### For MCP tools (this sub-package)
- AWS credentials configured (AWS_PROFILE, AWS_ACCESS_KEY_ID, or IAM role)
- AWS_REGION environment variable (defaults to us-east-1)
- No additional installation — tools use boto3 bundled with the MCP server

### For CLI commands referenced in this guide
The `agentcore` CLI is a separate tool for project scaffolding, deployment,
and management. Install it before using any `agentcore` commands:

```bash
npm install -g @aws/agentcore-cli
```

For installation details, supported platforms, and authentication setup,
see: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-cli.html

Note: The MCP tools in this server call the AgentCore APIs directly via
boto3. You do NOT need the CLI installed to use the MCP tools. The CLI
is only needed if you want to use the project scaffolding and deployment
commands described in the "CLI Commands" section below.

---

## Tool Cost Tiers

### Read-only tools (no cost)
- gateway_get — Get gateway details
- gateway_list — List gateways
- gateway_target_get — Get target details
- gateway_target_list — List targets for a gateway
- gateway_resource_policy_get — Get resource policy
- get_gateway_guide — This guide

### Tools that create billable resources or incur compute costs
- gateway_create — Provisions gateway infrastructure (AWS charges)
- gateway_update — Interceptor changes add Lambda invocation costs
- gateway_target_create — For mcpServer targets, implicit synchronization
  runs on creation and incurs compute costs
- gateway_target_update — For mcpServer targets, triggers implicit
  synchronization
- gateway_target_synchronize — Re-indexes tool catalog (compute charges)
- gateway_resource_policy_put — Misconfigured policies can expose the
  gateway; review before applying

### Destructive tools (permanent, no cost but irreversible)
- gateway_delete — Permanently deletes gateway and workload identity
- gateway_target_delete — Permanently removes target and its tools
- gateway_resource_policy_delete — Removes resource-based permissions

---

## Excluded Operations and Security Notes

### Data plane (intentionally not exposed)
Gateway's data plane is the InvokeGateway operation — `tools/list` and
`tools/call` calls over HTTPS with a JWT bearer token. These are not
exposed as MCP tools because:

- Invoking a gateway requires an agent-runtime access token obtained from
  AgentCore Identity; that token is designed for an agent runtime
  (using SDK decorators like `@requires_access_token`), not for
  interactive management tooling.
- Tool invocation responses can be arbitrary and large, and may contain
  sensitive data from backend targets.
- For interactive testing, use the MCP Inspector
  (https://modelcontextprotocol.io/) pointed at your gateway URL with
  the Authorization header set to your bearer token. See "Debug your
  gateway" below.

### Credential material (not accepted as input)
Gateway target creation accepts `credentialProviderConfigurations` that
reference provider ARNs — it does NOT accept API keys or client secrets
as parameters. Create the credential provider separately:

- **CLI:** `agentcore add credential --name MyOAuth --type oauth ...`
  The CLI prompts interactively for secrets so they never enter LLM
  context.
- **Identity MCP tools:** Use the `identity` sub-package tools
  (api_key_provider / oauth2_provider) from this same MCP server.
- **SDK:** `boto3.client('bedrock-agentcore-control')
  .create_api_key_credential_provider(...)` or
  `.create_oauth2_credential_provider(...)`.

Take the returned `providerArn` and reference it in
`credential_provider_configurations` when calling `gateway_target_create`.

### Tag tools
Standalone TagResource / UntagResource / ListTagsForResource tools are not
exposed. Pass `tags` directly to `gateway_create` at creation time.

---

## CLI Commands

### Add a gateway to a project
```bash
# No authorization (development/testing)
agentcore add gateway --name MyGateway

# CUSTOM_JWT authorization (production)
agentcore add gateway \\
  --name MyGateway \\
  --authorizer-type CUSTOM_JWT \\
  --discovery-url https://idp.example.com/.well-known/openid-configuration \\
  --allowed-audience my-api \\
  --allowed-clients my-client-id \\
  --client-id agent-client-id \\
  --client-secret agent-client-secret
```

Relevant flags: --name, --description, --authorizer-type (NONE |
AWS_IAM | CUSTOM_JWT), --discovery-url, --allowed-audience,
--allowed-clients, --allowed-scopes, --custom-claims, --client-id,
--client-secret, --no-semantic-search, --exception-level (NONE |
DEBUG), --policy-engine, --policy-engine-mode (LOG_ONLY | ENFORCE).

### Add a gateway target
Five target types are supported: `mcp-server`, `api-gateway`,
`open-api-schema`, `smithy-model`, and `lambda-function-arn`.

```bash
# MCP Server endpoint
agentcore add gateway-target \\
  --name WeatherTools \\
  --type mcp-server \\
  --endpoint https://mcp.example.com/mcp \\
  --gateway MyGateway

# Lambda Function ARN
agentcore add gateway-target \\
  --name MyLambdaTools \\
  --type lambda-function-arn \\
  --lambda-arn arn:aws:lambda:us-east-1:123:function:my-func \\
  --tool-schema-file tools.json \\
  --gateway MyGateway

# OpenAPI with OAuth (uses named credential created via add credential)
agentcore add gateway-target \\
  --name PetStoreAPI \\
  --type open-api-schema \\
  --schema specs/petstore.json \\
  --gateway MyGateway \\
  --outbound-auth oauth \\
  --credential-name MyOAuth
```

### Create a named credential
```bash
# API key credential
agentcore add credential --name OpenAI --api-key sk-...

# OAuth credential
agentcore add credential \\
  --name MyOAuth \\
  --type oauth \\
  --client-id ... --client-secret ... \\
  --discovery-url ...
```

### Deploy and status
```bash
agentcore deploy -y
agentcore status --type gateway
```

---

## agentcore.json Schema — agentCoreGateways Section

```json
{
  "agentCoreGateways": [
    {
      "name": "MyGateway",
      "description": "Gateway for agent tools",
      "targets": [
        {
          "name": "WeatherTools",
          "targetType": "mcpServer",
          "endpoint": "https://mcp.example.com/mcp"
        },
        {
          "name": "MyLambdaTools",
          "targetType": "lambdaFunctionArn",
          "lambdaArn": "arn:aws:lambda:us-east-1:123:function:f",
          "toolDefinitions": [
            {
              "name": "get_weather",
              "description": "Get weather for a location",
              "inputSchema": {
                "type": "object",
                "properties": {
                  "location": {"type": "string"}
                },
                "required": ["location"]
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### Schema constraints
- **name** (gateway): Pattern `^[0-9a-zA-Z](?:[0-9a-zA-Z-]*[0-9a-zA-Z])?$`,
  max 100 chars
- **targetType**: lambda | mcpServer | openApiSchema | smithyModel |
  apiGateway | lambdaFunctionArn
- **toolDefinitions[].name**: 1-128 chars
- Tool names exposed through MCP are prefixed with the target name:
  `${target_name}___${tool_name}` (three underscores)

---

## Target Types

| Type | Field | Use Case |
|------|-------|----------|
| `lambda` | Lambda ARN + inline tool schema | Lambda as tool provider |
| `mcpServer` | HTTPS endpoint | Remote MCP server |
| `apiGateway` | REST API ID + stage + tool filters | API Gateway REST API |
| `openApiSchema` | Inline or S3 OpenAPI spec | Schema-defined HTTP endpoint |
| `smithyModel` | Inline or S3 Smithy model | AWS service or Smithy API |

### Outbound authorization support by target type
| Target | IAM role | OAuth CC | OAuth AC | API Key | None |
|--------|----------|----------|----------|---------|------|
| apiGateway | Yes | No | No | Yes | No |
| lambda | Yes | No | No | No | No |
| mcpServer | No | Yes | No | No | Yes |
| openApiSchema | No | Yes | Yes | Yes | No |
| smithyModel | Yes | Yes | Yes | No | No |

OAuth CC = Client Credentials (2LO); OAuth AC = Authorization Code (3LO).

---

## Common Patterns

### Create a gateway with CUSTOM_JWT and semantic search
```python
gateway = client.create_gateway(
    name="my-gateway",
    roleArn="arn:aws:iam::123:role/gateway-service-role",
    protocolType="MCP",
    authorizerType="CUSTOM_JWT",
    authorizerConfiguration={
        "customJWTAuthorizer": {
            "discoveryUrl": "https://idp.example.com/.well-known/openid-configuration",
            "allowedClients": ["agent-client"]
        }
    },
    protocolConfiguration={"mcp": {"searchType": "SEMANTIC"}},
)
```

### Add a Lambda target with inline tool schema
```python
client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="WeatherTools",
    targetConfiguration={
        "mcp": {
            "lambda": {
                "lambdaArn": "arn:aws:lambda:us-east-1:123:function:weather",
                "toolSchema": {
                    "inlinePayload": [{
                        "name": "get_weather",
                        "description": "Get weather for a location",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"location": {"type": "string"}},
                            "required": ["location"]
                        }
                    }]
                }
            }
        }
    },
    credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
)
```

### Add an MCP server target with OAuth
```python
# First, create the OAuth credential provider separately
# via Identity MCP tools or `agentcore add credential`.
# Then reference the returned providerArn:
client.create_gateway_target(
    gatewayIdentifier=gateway_id,
    name="SecureTools",
    targetConfiguration={
        "mcp": {"mcpServer": {"endpoint": "https://api.example.com/mcp"}}
    },
    credentialProviderConfigurations=[{
        "credentialProviderType": "OAUTH",
        "credentialProvider": {
            "oauthCredentialProvider": {
                "providerArn": "arn:aws:bedrock-agentcore:...:credentialprovider/...",
                "scopes": ["tools:read"]
            }
        }
    }],
)
```

### Re-synchronize tools after upstream MCP server changes
```python
client.synchronize_gateway_targets(
    gatewayIdentifier=gateway_id,
    targetIdList=[target_id],
)
# Poll with get_gateway_target to track SYNCHRONIZING -> READY
```

---

## Debug Your Gateway

### Enable detailed error messages
Set `exceptionLevel` to `"DEBUG"` on `gateway_create` or `gateway_update`
to return detailed errors from Lambda, authorizer, or target validation.
Omit the field (or update without it) to return generic errors in
production.

### MCP Inspector
The MCP Inspector is a developer tool for testing MCP servers
interactively. Point it at your gateway URL with your JWT access token
in the Authorization header to list tools, call tools, and inspect
responses. This is the recommended interactive testing surface — it is
why this sub-package does not expose data-plane tools.

### CloudWatch Logs & CloudTrail
Management events (Create/Get/Update/Delete Gateway and Target) are
logged to CloudTrail by default. Invocation events (InvokeGateway) are
data events and must be explicitly enabled via advanced event selectors
on a trail. Live logs: `aws logs tail /aws/bedrock-agentcore/gateways/<ID>
--follow`.

---

## Troubleshooting

### Gateway stuck in CREATING status
- Check IAM trust policy on the service role — it must trust
  `bedrock-agentcore.amazonaws.com`.
- Verify KMS key permissions if using a customer-managed key.
- Use `gateway_get` and inspect `statusReasons`.

### Target stuck in SYNCHRONIZING / SYNCHRONIZE_UNSUCCESSFUL
- For mcpServer targets: the upstream MCP server must support MCP
  versions 2025-06-18 or 2025-03-26.
- Tool schemas must not contain $ref, $defs, $anchor, $dynamicRef, or
  $dynamicAnchor — schemas must be self-contained.
- Check `statusReasons` on the target for specific failure detail.

### ValidationException on UpdateGateway
UpdateGateway requires all originally-set fields to be passed. Fetch
current values with `gateway_get` first, then pass through unchanged
fields alongside your changes.

### AccessDeniedException on target invocation (not management)
- Verify the gateway service role has permissions to invoke the target
  (e.g., `lambda:InvokeFunction` on the Lambda ARN).
- For OAuth/API_KEY outbound auth, verify the role also has
  `bedrock-agentcore:GetWorkloadAccessToken` and either
  `GetResourceOauth2Token` or `GetResourceApiKey`, plus
  `secretsmanager:GetSecretValue` on the provider's secret ARN.

### Stale credentials after AWS SSO refresh
boto3 clients are cached per region. If credentials expire, restart the
MCP server. Fix: set `AGENTCORE_DISABLE_TOOLS=gateway` temporarily and
restart.

---

## IAM Permissions

### For users / agents managing gateways via this MCP server
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock-agentcore:CreateGateway",
      "bedrock-agentcore:GetGateway",
      "bedrock-agentcore:UpdateGateway",
      "bedrock-agentcore:DeleteGateway",
      "bedrock-agentcore:ListGateways",
      "bedrock-agentcore:CreateGatewayTarget",
      "bedrock-agentcore:GetGatewayTarget",
      "bedrock-agentcore:UpdateGatewayTarget",
      "bedrock-agentcore:DeleteGatewayTarget",
      "bedrock-agentcore:ListGatewayTargets",
      "bedrock-agentcore:SynchronizeGatewayTargets",
      "bedrock-agentcore:PutResourcePolicy",
      "bedrock-agentcore:GetResourcePolicy",
      "bedrock-agentcore:DeleteResourcePolicy",
      "bedrock-agentcore:*WorkloadIdentity",
      "bedrock-agentcore:*CredentialProvider",
      "iam:PassRole"
    ],
    "Resource": "arn:aws:bedrock-agentcore:*:*:*gateway*"
  }]
}
```

### For the gateway service role (assumed by the gateway)
Trust policy must trust `bedrock-agentcore.amazonaws.com`.
Permissions depend on targets:
- Lambda targets: `lambda:InvokeFunction` on target ARNs
- API Gateway targets: `execute-api:Invoke` on target APIs
- OAuth/API key outbound: `bedrock-agentcore:GetWorkloadAccessToken`,
  `GetResourceOauth2Token` or `GetResourceApiKey`,
  `secretsmanager:GetSecretValue`
- S3-hosted schemas: `s3:GetObject` on schema bucket/key
- Semantic search: `bedrock-agentcore:SynchronizeGatewayTargets` on
  the gateway itself

---

## Migration from bedrock-agentcore-starter-toolkit

The old Python starter toolkit (`bedrock_agentcore_starter_toolkit`) is
deprecated. Migrate to the new `agentcore` CLI:

1. Replace `bedrock-agentcore-starter-toolkit gateway create-mcp-gateway`
   with `agentcore add gateway`.
2. Replace `create-mcp-gateway-target` with `agentcore add gateway-target`.
3. Move gateway configuration into the `agentCoreGateways` section of
   `agentcore.json`.
4. Use `agentcore add credential` to create credential providers before
   adding OAuth/API-key targets — do not pass secrets inline.
5. Use `agentcore deploy` instead of the toolkit's `setup_gateway()`
   helper. The CDK scaffolding the toolkit produced is replaced by the
   CLI's built-in deploy workflow.
6. For programmatic access from agent code at runtime, continue using
   boto3 (`bedrock-agentcore-control` for management, `bedrock-agentcore`
   for InvokeGateway) or MCP client libraries — the SDK surface is
   unchanged.
""".strip()


class GuideTools:
    """Static guide tool for AgentCore Gateway."""

    def register(self, mcp):
        """Register guide tools with the MCP server."""
        mcp.tool(name='get_gateway_guide')(self.get_gateway_guide)

    async def get_gateway_guide(self, ctx: Context) -> GatewayGuideResponse:
        """Get the comprehensive AgentCore Gateway guide.

        Returns a detailed reference covering: prerequisites, tool cost
        tiers, excluded operations and security notes, CLI commands,
        agentcore.json schema, target types, common patterns, debugging,
        troubleshooting, IAM permissions, and migration notes.

        This is a read-only operation with no cost implications.
        """
        return GatewayGuideResponse(guide=GATEWAY_GUIDE)
