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

"""Static guide tool for AgentCore Identity."""

from .models import IdentityGuideResponse
from mcp.server.fastmcp import Context


IDENTITY_GUIDE = """
# AgentCore Identity — Comprehensive Guide

## Overview

AgentCore Identity is an identity and credential-management service for AI
agents and automated workloads. It provides:

- **Workload identities** — centralized directory of agent/workload identities
- **Credential providers** — stored API keys and OAuth2 client credentials
- **Token vault** — encrypted store backed by AWS Secrets Manager, with
  optional customer-managed KMS keys
- **OAuth2 flow support** — M2M (client credentials) and 3LO (user
  federation/authorization code) via stored providers
- **Resource-based policies** — IAM-style policies on Agent Runtime,
  Endpoint, and Gateway resources
- **Sigv4 inbound auth** — AWS-signed tokens for agent-to-service auth

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

Note: The MCP tools in this server call the AgentCore APIs directly via
boto3. You do NOT need the CLI installed to use the MCP tools. The CLI
is only needed if you want to use the project scaffolding and
`agentcore add credential` flows described in the "CLI Commands"
section below.

---

## Data Plane Tools Are Intentionally NOT Exposed

The Identity service has a data plane (`bedrock-agentcore`) with APIs that
return live credential material:

- `GetWorkloadAccessToken` / `ForJWT` / `ForUserId` — workload access tokens
- `GetResourceOauth2Token` — live OAuth2 access tokens
- `GetResourceApiKey` — stored API key values
- `CompleteResourceTokenAuth` — completes 3LO flow

These operations are **not exposed as MCP tools** because calling them
would pump live tokens and secrets into LLM conversation context. They
are designed to be used inside agent-runtime code via the
`bedrock-agentcore` SDK's decorators:

```python
from bedrock_agentcore.identity.auth import (
    requires_access_token,
    requires_api_key,
    requires_iam_access_token,
)

@requires_access_token(
    provider_name='my-google-provider',
    auth_flow='USER_FEDERATION',
    scopes=['https://www.googleapis.com/auth/calendar.readonly'],
)
async def read_calendar(*, access_token: str):
    # access_token is injected at runtime, never touches LLM context
    ...
```

This MCP sub-package focuses on **management and configuration**
operations: CRUD on workload identities, credential providers, token
vault, and resource policies.

---

## Tool Cost Tiers

### Read-only tools (no cost)
- identity_get_workload_identity, identity_list_workload_identities
- identity_get_api_key_provider, identity_list_api_key_providers
- identity_get_oauth2_provider, identity_list_oauth2_providers
- identity_get_token_vault
- identity_get_resource_policy
- get_identity_guide

### Tools that create/modify resources or incur charges
- identity_create_workload_identity — creates a workload identity
- identity_update_workload_identity — updates allowed callback URLs
- identity_create_api_key_provider — creates a Secrets Manager secret (charges)
- identity_update_api_key_provider — rotates the stored secret
- identity_create_oauth2_provider — creates a Secrets Manager secret (charges)
- identity_update_oauth2_provider — rotates the stored client secret
- identity_set_token_vault_cmk — switches to a CMK (adds KMS charges)
- identity_put_resource_policy — modifies access controls on a resource

### Destructive tools (permanent, irreversible)
- identity_delete_workload_identity
- identity_delete_api_key_provider — removes credential + backing secret
- identity_delete_oauth2_provider — removes credential + backing secret
- identity_delete_resource_policy — removes ALL resource-policy access

---

## Security: Secrets in LLM Context — Use the CLI for Production

The `create` and `update` tools for credential providers accept the
actual secret value (`api_key` or `clientSecret`) as a parameter. When
an AI assistant calls these tools, the secret value flows through LLM
conversation context and may be persisted in chat history, model
training signals, or observability tools.

For production credentials, strongly prefer the CLI:

```bash
# API key credential
agentcore add credential \
  --name OpenAI \
  --api-key sk-...

# OAuth credential
agentcore add credential \
  --name MyOAuthProvider \
  --type oauth \
  --discovery-url https://idp.example.com/.well-known/openid-configuration \
  --client-id my-client-id \
  --client-secret my-client-secret \
  --scopes read,write
```

The CLI reads the secret from the shell invocation directly and never
routes it through an LLM. The MCP create/update tools remain useful
for:
- Test credentials with known non-production values
- Automation from a controlled context (not driven by a chat LLM)
- Scripted flows where the key is fetched from a secure source and
  passed deterministically

---

## CLI Commands

### Add an API key credential
```bash
agentcore add credential --name OpenAI --api-key sk-...
```

### Add an OAuth credential
```bash
agentcore add credential \
  --name MyOAuthProvider \
  --type oauth \
  --discovery-url https://idp.example.com/.well-known/openid-configuration \
  --client-id my-client-id \
  --client-secret my-client-secret \
  --scopes read,write
```

| Flag                       | Description                      |
|---------------------------|----------------------------------|
| --name                    | Credential name                  |
| --type                    | api-key (default) or oauth       |
| --api-key                 | API key value (api-key type)     |
| --discovery-url           | OAuth discovery URL (oauth type) |
| --client-id               | OAuth client ID (oauth type)     |
| --client-secret           | OAuth client secret (oauth type) |
| --scopes                  | OAuth scopes, comma-separated    |
| --json                    | JSON output                      |

### Remove a credential
```bash
agentcore remove credential --name OpenAI
```

### Use an existing credential on a gateway target
```bash
agentcore add gateway-target \
  --name MyAPI \
  --type open-api-schema \
  --schema-path ./schema.json \
  --outbound-auth oauth \
  --credential-name MyOAuthProvider \
  --gateway MyGateway
```

---

## agentcore.json Schema — credentials Section

```json
{
  "credentials": [
    {
      "authorizerType": "ApiKeyCredentialProvider",
      "name": "OpenAI"
    },
    {
      "authorizerType": "OAuthCredentialProvider",
      "name": "MyOAuthProvider",
      "discoveryUrl": "https://idp.example.com/.well-known/openid-configuration",
      "scopes": ["read", "write"],
      "vendor": "CustomOauth2",
      "usage": "outbound"
    }
  ]
}
```

### Schema constraints
- **name**: 1-128 chars. Pattern: `[a-zA-Z0-9\\-_]+`. Required.
- **authorizerType**: `ApiKeyCredentialProvider` | `OAuthCredentialProvider`
- **discoveryUrl** (OAuth only): Full OIDC discovery URL
- **scopes** (OAuth only): Array of scope strings
- **vendor** (OAuth only): Defaults to `CustomOauth2`. Other values include
  `GoogleOauth2`, `GithubOauth2`, `SlackOauth2`, `SalesforceOauth2`,
  `MicrosoftOauth2`, `AtlassianOauth2`, `LinkedinOauth2`, `XOauth2`,
  `OktaOauth2`, `Auth0Oauth2`, `CognitoOauth2`, and several others.
- **usage**: `inbound` | `outbound`

Note: the schema intentionally does not persist `api-key`, `client-id`, or
`client-secret` values — those are held only in the token vault's backing
Secrets Manager and accessed via the credential's name.

---

## OAuth2 Provider Config Shapes

When calling `identity_create_oauth2_provider`, the
`oauth2_provider_config_input` parameter is a union — specify exactly
one inner key:

### Standard vendor (Google, GitHub, Slack, Salesforce, Atlassian, LinkedIn)
```json
{
  "googleOauth2ProviderConfig": {
    "clientId": "123-abc.apps.googleusercontent.com",
    "clientSecret": "<your-client-secret>"
  }
}
```

### Microsoft (supports tenantId)
```json
{
  "microsoftOauth2ProviderConfig": {
    "clientId": "...",
    "clientSecret": "...",
    "tenantId": "common"
  }
}
```

### Custom (requires oauthDiscovery)
```json
{
  "customOauth2ProviderConfig": {
    "clientId": "...",
    "clientSecret": "...",
    "oauthDiscovery": {
      "discoveryUrl": "https://idp.example.com/.well-known/openid-configuration"
    }
  }
}
```

Or with explicit metadata instead of discovery:
```json
{
  "customOauth2ProviderConfig": {
    "clientId": "...",
    "clientSecret": "...",
    "oauthDiscovery": {
      "authorizationServerMetadata": {
        "issuer": "https://idp.example.com",
        "authorizationEndpoint": "https://idp.example.com/authorize",
        "tokenEndpoint": "https://idp.example.com/token",
        "responseTypes": ["code"],
        "tokenEndpointAuthMethods": ["client_secret_post"]
      }
    }
  }
}
```

### Included providers (built-in with optional tenant overrides)
```json
{
  "includedOauth2ProviderConfig": {
    "clientId": "...",
    "clientSecret": "...",
    "issuer": "https://custom-tenant.example.com",
    "authorizationEndpoint": "https://custom-tenant.example.com/authorize",
    "tokenEndpoint": "https://custom-tenant.example.com/token"
  }
}
```

---

## Common Patterns

### Create a workload identity for an agent
```python
identity_create_workload_identity(
    name='my-agent-prod',
    allowed_resource_oauth2_return_urls=[
        'https://agentcore.example.com/oauth2/callback'
    ],
    tags={'env': 'prod', 'owner': 'team-a'},
)
```

### Wire up a GitHub OAuth provider
```python
identity_create_oauth2_provider(
    name='github-provider',
    credential_provider_vendor='GithubOauth2',
    oauth2_provider_config_input={
        'githubOauth2ProviderConfig': {
            'clientId': 'Iv1.abc...',
            'clientSecret': '',
        }
    },
)
# Response includes callbackUrl — register this with GitHub's OAuth app.
```

### Switch the token vault to a customer-managed key
```python
identity_set_token_vault_cmk(
    kms_configuration={
        'keyType': 'CustomerManagedKey',
        'kmsKeyArn': 'arn:aws:kms:us-east-1:123:key/abcd-1234-...',
    },
)
```

### Grant another account's role to invoke an Agent Runtime
```python
identity_put_resource_policy(
    resource_arn='arn:aws:bedrock-agentcore:us-east-1:123:runtime/my-runtime',
    policy_document={
        'Version': '2012-10-17',
        'Statement': [{
            'Sid': 'AllowPartnerInvoke',
            'Effect': 'Allow',
            'Principal': {'AWS': 'arn:aws:iam::456:role/partner-runner'},
            'Action': 'bedrock-agentcore:InvokeAgentRuntime',
            'Resource': '*',
        }],
    },
)
```

### Retrieve credentials at runtime (SDK, not MCP)
```python
from bedrock_agentcore.identity.auth import requires_access_token

@requires_access_token(
    provider_name='github-provider',
    auth_flow='USER_FEDERATION',
    scopes=['repo'],
)
async def list_repos(*, access_token: str):
    import httpx
    resp = httpx.get(
        'https://api.github.com/user/repos',
        headers={'Authorization': f'Bearer {access_token}'},
    )
    return resp.json()
```

---

## Troubleshooting

### AccessDeniedException on control plane calls
Verify the calling IAM principal has the required
`bedrock-agentcore:*` actions for the operation (see IAM Permissions
section below). If using resource policies, verify they do not
explicitly deny the principal.

### ResourceNotFoundException on GetWorkloadIdentity / GetApiKeyCredentialProvider
- Names are case-sensitive and region-scoped
- Confirm you're calling the same region where the resource was created
- Use the corresponding List operation to enumerate existing names

### ConflictException on Create*
- A resource with the same name already exists in the region
- Use the Update tool to modify, or choose a different name

### ValidationException on Create/Update with OAuth2 config
- Only one inner key may be set in oauth2_provider_config_input
- The inner key's vendor name must match credentialProviderVendor
  (e.g. `googleOauth2ProviderConfig` pairs with `GoogleOauth2`)
- CustomOauth2 requires oauthDiscovery (either discoveryUrl or
  authorizationServerMetadata)

### CustomerManagedKey on token vault fails with KMS errors
- The KMS key policy must allow AgentCore to use the key. Required
  actions: kms:Decrypt, kms:Encrypt, kms:GenerateDataKey, kms:DescribeKey
- The key must be in the same region as the token vault
- Multi-region keys are supported; single-region keys are not

### Resource policy not taking effect
- Policies are evaluated alongside identity-based IAM; both must allow
- Check for explicit Deny statements elsewhere in the policy chain
- After Put, allow a few seconds for policy propagation

### Stale credentials after refresh
boto3 clients are cached per-region in this sub-package. If the
underlying AWS credentials refresh (e.g. after an SSO session rotation)
and clients continue using stale creds, restart the MCP server. As a
quick workaround you can set `AGENTCORE_DISABLE_TOOLS=identity` and
restart to force a clean state.

---

## IAM Permissions

Required for the control plane operations exposed by this sub-package.
Verify current action names against the AWS Bedrock AgentCore IAM
documentation — AWS occasionally adjusts service-level action prefixes.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "IdentityWorkloadIdentities",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateWorkloadIdentity",
        "bedrock-agentcore:GetWorkloadIdentity",
        "bedrock-agentcore:UpdateWorkloadIdentity",
        "bedrock-agentcore:DeleteWorkloadIdentity",
        "bedrock-agentcore:ListWorkloadIdentities"
      ],
      "Resource": "arn:aws:bedrock-agentcore:*:*:workload-identity/*"
    },
    {
      "Sid": "IdentityApiKeyProviders",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateApiKeyCredentialProvider",
        "bedrock-agentcore:GetApiKeyCredentialProvider",
        "bedrock-agentcore:UpdateApiKeyCredentialProvider",
        "bedrock-agentcore:DeleteApiKeyCredentialProvider",
        "bedrock-agentcore:ListApiKeyCredentialProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IdentityOauth2Providers",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateOauth2CredentialProvider",
        "bedrock-agentcore:GetOauth2CredentialProvider",
        "bedrock-agentcore:UpdateOauth2CredentialProvider",
        "bedrock-agentcore:DeleteOauth2CredentialProvider",
        "bedrock-agentcore:ListOauth2CredentialProviders"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IdentityTokenVault",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetTokenVault",
        "bedrock-agentcore:SetTokenVaultCMK"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IdentityResourcePolicy",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:PutResourcePolicy",
        "bedrock-agentcore:GetResourcePolicy",
        "bedrock-agentcore:DeleteResourcePolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

When using a CustomerManagedKey for the token vault, the KMS key policy
must additionally grant the AgentCore service principal:
- kms:Decrypt
- kms:Encrypt
- kms:GenerateDataKey
- kms:DescribeKey

---

## Migration from bedrock-agentcore-starter-toolkit

The old Python starter toolkit is deprecated. Migrate to the new
`agentcore` CLI:

1. Replace manual `IdentityClient` setup with `agentcore add credential`
2. Move credential references into `agentcore.json` `credentials` section
3. Use `agentcore add gateway-target ... --credential-name <n>` to
   wire stored credentials to gateway targets
4. Deploy with `agentcore deploy` instead of CDK-based scripts
5. The `bedrock-agentcore` SDK package itself remains the runtime
   library — continue using `@requires_access_token`,
   `@requires_api_key`, and `@requires_iam_access_token` decorators in
   agent code

Notable behavior differences:
- Token vault CMK configuration is now a first-class CLI/MCP operation
- Resource policies on Agent Runtime/Endpoint/Gateway are managed via
  the control plane APIs (no CDK escape hatch required)
- Callback URLs on workload identities are explicit via
  `allowedResourceOauth2ReturnUrls`, not inferred from deploy-time state
""".strip()


class GuideTools:
    """Static guide tool for AgentCore Identity."""

    def register(self, mcp):
        """Register guide tools with the MCP server."""
        mcp.tool(name='get_identity_guide')(self.get_identity_guide)

    async def get_identity_guide(self, ctx: Context) -> IdentityGuideResponse:
        """Get the comprehensive AgentCore Identity guide.

        Returns a detailed reference covering: prerequisites, cost tiers,
        data-plane exclusion rationale, CLI commands, agentcore.json
        schema, OAuth2 provider config shapes, common patterns,
        troubleshooting, IAM permissions, and migration notes.

        This is a read-only operation with no cost implications.
        """
        return IdentityGuideResponse(status='success', guide=IDENTITY_GUIDE)
