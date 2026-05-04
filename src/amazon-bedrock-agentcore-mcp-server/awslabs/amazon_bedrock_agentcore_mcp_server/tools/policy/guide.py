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

"""Static guide tool for AgentCore Policy."""

from .models import PolicyGuideResponse
from mcp.server.fastmcp import Context


POLICY_GUIDE = """
# AgentCore Policy — Comprehensive Guide

## Overview

AgentCore Policy provides Cedar-based authorization for agent tool
invocations. It has three primary concepts:

- **Policy Engine** — Top-level container that holds a set of Cedar
  policies. Attached to a Gateway to enforce access control on tools
  exposed through that gateway.
- **Policy** — A Cedar policy statement defining who (principals) can
  perform what (actions) on which resources, under which conditions.
  Cedar uses a default-deny model; `forbid` statements override
  `permit` statements.
- **Policy Generation** — AI-powered translation of natural-language
  policy intent into Cedar syntax. Produces candidate assets you
  review and promote into real policies.

---

## Prerequisites

### For MCP tools (this sub-package)
- AWS credentials configured (AWS_PROFILE, AWS_ACCESS_KEY_ID, or IAM role)
- AWS_REGION environment variable (defaults to us-east-1)
- No additional installation — tools use boto3 bundled with the MCP server

### For CLI commands referenced in this guide
The `agentcore` CLI is a separate tool for project scaffolding,
deployment, and management. Install it before using any `agentcore`
commands:

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
- policy_engine_get — Get policy engine details
- policy_engine_list — List policy engines
- policy_get — Get policy details (use to poll async status)
- policy_list — List policies in an engine
- policy_generation_get — Get generation details (use to poll async status)
- policy_generation_list — List generations in an engine
- policy_generation_list_assets — List generated policy assets
- get_policy_guide — This guide

### Tools that create billable resources or incur compute costs
- policy_engine_create — Provisions a policy engine (infrastructure charges)
- policy_create — Invokes validation pipeline and provisions a policy
- policy_update — Re-invokes validation pipeline
- policy_generation_start — AI-powered generation (foundation model
  invocation; typically the most expensive Policy operation per call)

### Destructive tools (permanent, irreversible)
- policy_engine_delete — Permanently deletes the policy engine
  (requires zero associated policies first)
- policy_delete — Permanently deletes a policy

---

## CLI Commands

Policy engines and policies are declared in `agentcore.json` under the
top-level `policyEngines` array and created during `agentcore deploy`.
The CLI does not currently provide dedicated `agentcore add policy-engine`
or `agentcore add policy` subcommands — edit `agentcore.json` directly
and redeploy.

### Attach a policy engine to a Gateway

```bash
agentcore add gateway \
  --name MyGateway \
  --runtimes MyAgent \
  --policy-engine MyPolicyEngine \
  --policy-engine-mode LOG_ONLY
```

| Flag                          | Description                                |
| ----------------------------- | ------------------------------------------ |
| `--policy-engine <n>`         | Policy engine name (must exist in config)  |
| `--policy-engine-mode <mode>` | `LOG_ONLY` or `ENFORCE`                    |

### Check policy deployment status

```bash
# All policy engines
agentcore status --type policy-engine

# All policies
agentcore status --type policy

# JSON output
agentcore status --type policy-engine --json
```

### Deploy policy engine and policies

After editing `agentcore.json`, run:

```bash
agentcore deploy -y
```

Async status transitions (CREATING → ACTIVE, UPDATING → ACTIVE,
DELETING → deleted) can be polled via the MCP tools `policy_engine_get`
and `policy_get`, or via `agentcore status`.

---

## agentcore.json Schema — policyEngines Section

```json
{
  "policyEngines": [
    {
      "name": "MyPolicyEngine",
      "description": "Authorization for production tools",
      "encryptionKeyArn": "arn:aws:kms:us-east-1:123:key/abc",
      "tags": { "env": "prod" },
      "policies": [
        {
          "name": "AdminFullAccess",
          "description": "Admins can invoke all tools",
          "statement": "permit(principal in Group::\\"Admins\\", action, resource);",
          "validationMode": "FAIL_ON_ANY_FINDINGS"
        },
        {
          "name": "RestrictWeatherToBusinessHours",
          "description": "Weather tool allowed 9am-5pm only",
          "sourceFile": "policies/business-hours.cedar"
        }
      ]
    }
  ]
}
```

### Schema constraints

- **policyEngines[].name**: Pattern `[A-Za-z][A-Za-z0-9_]*`, 1-48 chars,
  required. Immutable after creation.
- **policyEngines[].description**: 1-4096 chars, optional.
- **policyEngines[].encryptionKeyArn**: KMS key ARN for encryption at
  rest, optional.
- **policyEngines[].tags**: Map of tag key → tag value, optional
  (max 50 tags).
- **policyEngines[].policies[].name**: Pattern
  `[A-Za-z][A-Za-z0-9_]*`, 1-48 chars, required. Immutable.
- **policyEngines[].policies[].statement**: Cedar policy text
  (35-10000 chars when sent to the API). Required unless `sourceFile`
  is used.
- **policyEngines[].policies[].sourceFile**: Path to a `.cedar` file
  relative to the project root. CLI-only convenience; the file
  contents are read at deploy time and passed as `statement`.
- **policyEngines[].policies[].validationMode**:
  `FAIL_ON_ANY_FINDINGS` (default) or `IGNORE_ALL_FINDINGS`.

### Attaching a policy engine to a gateway

The gateway config carries a `policyEngineConfiguration` block:

```json
{
  "gateways": [
    {
      "name": "MyGateway",
      "policyEngineConfiguration": {
        "policyEngineName": "MyPolicyEngine",
        "mode": "ENFORCE"
      }
    }
  ]
}
```

- **mode**: `LOG_ONLY` evaluates policies and logs decisions but does
  not block. `ENFORCE` actively allows or denies based on policy
  evaluation. Always deploy first in `LOG_ONLY`, inspect the logs,
  then switch to `ENFORCE`.

---

## Common Patterns

### Create a policy engine and a policy via MCP tools

```python
# 1. Create the engine
await policy_engine_create(
    name="ProdAuth",
    description="Production authorization rules",
)
# Poll: await policy_engine_get(policy_engine_id="ProdAuth-abcdefghij")
# Wait for status == "ACTIVE"

# 2. Create a Cedar policy inside it
await policy_create(
    policy_engine_id="ProdAuth-abcdefghij",
    name="AdminAccess",
    definition={
        "cedar": {
            "statement": (
                'permit(principal in Group::"Admins", '
                'action, resource);'
            )
        }
    },
    validation_mode="FAIL_ON_ANY_FINDINGS",
)
# Poll: await policy_get(policy_engine_id=..., policy_id=...)
```

### Generate a policy from natural language

```python
# 1. Start generation
gen = await policy_generation_start(
    policy_engine_id="ProdAuth-abcdefghij",
    name="BusinessHoursGen",
    content={
        "rawText": (
            "Allow Admins to invoke any tool. Allow Users to "
            "invoke the weather tool only between 9am and 5pm UTC."
        )
    },
    resource={
        "arn": (
            "arn:aws:bedrock-agentcore:us-east-1:123456789012:"
            "gateway/my-gateway-abc123"
        )
    },
)
# Poll: await policy_generation_get(...)
# Wait for status == "GENERATED"

# 2. Review the generated assets
assets = await policy_generation_list_assets(
    policy_engine_id="ProdAuth-abcdefghij",
    policy_generation_id="BusinessHoursGen-abcdefghij",
)
# Inspect each asset's "findings" — only promote those with "VALID".

# 3. Promote a valid asset into a real policy
await policy_create(
    policy_engine_id="ProdAuth-abcdefghij",
    name="BusinessHoursPolicy",
    definition={
        "policyGeneration": {
            "policyGenerationId": "BusinessHoursGen-abcdefghij",
            "policyGenerationAssetId": "asset-abcdefghij",
        }
    },
)
```

### Update only the description of an engine or policy

```python
# Update description
await policy_engine_update(
    policy_engine_id="ProdAuth-abcdefghij",
    description={"optionalValue": "Updated description"},
)

# Clear description
await policy_engine_update(
    policy_engine_id="ProdAuth-abcdefghij",
    description={"optionalValue": None},
)

# Leave description unchanged — simply omit the parameter entirely.
```

### Delete order

Engines cannot be deleted while they hold policies. The correct order is:

```python
# 1. List and delete all policies in the engine
policies = await policy_list(policy_engine_id="ProdAuth-abcdefghij")
for p in policies.policies:
    await policy_delete(
        policy_engine_id="ProdAuth-abcdefghij",
        policy_id=p["policyId"],
    )
    # Poll policy_get until deletion completes

# 2. Then delete the engine
await policy_engine_delete(policy_engine_id="ProdAuth-abcdefghij")
```

---

## Validation Modes and Findings

When a policy is created or updated, Cedar validates it against the
schema derived from the associated Gateway's tools. Each finding has
a type:

| Finding Type       | Meaning                                               |
| ------------------ | ----------------------------------------------------- |
| `VALID`            | Policy is ready to use                                |
| `INVALID`          | Policy has validation errors that must be fixed      |
| `NOT_TRANSLATABLE` | Input couldn't be converted to a policy (generation) |
| `ALLOW_ALL`        | Policy would allow all actions (security risk)       |
| `ALLOW_NONE`       | Policy would allow no actions (unusable)             |
| `DENY_ALL`         | Policy would deny all actions (over-restrictive)     |
| `DENY_NONE`        | Policy would deny no actions (ineffective)           |

`FAIL_ON_ANY_FINDINGS` (default) rejects the create/update if any
finding is present. `IGNORE_ALL_FINDINGS` creates the policy
regardless — use sparingly and only after manual review.

---

## Troubleshooting

### Policy engine stuck in CREATING
- Check the engine's `statusReasons` via `policy_engine_get`
- Verify KMS key permissions if `encryptionKeyArn` was provided
- Check AWS CloudTrail for the CreatePolicyEngine call

### Policy stuck in CREATE_FAILED
- Call `policy_get` and inspect `statusReasons` for validation
  findings
- If the policy depends on a Gateway's tool schema, the Gateway must
  be fully deployed first
- Try `validation_mode="IGNORE_ALL_FINDINGS"` only after confirming
  the findings are acceptable

### AccessDeniedException
Required control-plane permissions on `bedrock-agentcore-control:*`:
CreatePolicyEngine, GetPolicyEngine, UpdatePolicyEngine,
DeletePolicyEngine, ListPolicyEngines, CreatePolicy, GetPolicy,
UpdatePolicy, DeletePolicy, ListPolicies, StartPolicyGeneration,
GetPolicyGeneration, ListPolicyGenerations,
ListPolicyGenerationAssets. See IAM Permissions below.

### ConflictException on create
A policy engine or policy with that name already exists in the
account/engine. Names are immutable and unique — choose a different
name or delete the existing resource.

### Policy engine cannot be deleted
Engines must have zero associated policies before deletion. Use
`policy_list` to enumerate, `policy_delete` each, poll `policy_get`
until each is gone, then `policy_engine_delete`.

### StartPolicyGeneration returns ValidationException
- The `resource.arn` must be a Gateway ARN the caller has visibility to
- The natural-language content must be 1-2000 chars

### Stale credentials after refresh
Known issue: boto3 clients are cached. If credentials expire, restart
the MCP server. Workaround: set `AGENTCORE_DISABLE_TOOLS=policy`
temporarily and restart.

### Generated assets disappearing
Policy generation assets auto-delete after 7 days. Promote valuable
assets into real policies with `policy_create` before the expiration
window closes.

---

## IAM Permissions

All Policy APIs are control plane (`bedrock-agentcore-control`).

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock-agentcore:CreatePolicyEngine",
    "bedrock-agentcore:GetPolicyEngine",
    "bedrock-agentcore:UpdatePolicyEngine",
    "bedrock-agentcore:DeletePolicyEngine",
    "bedrock-agentcore:ListPolicyEngines",
    "bedrock-agentcore:CreatePolicy",
    "bedrock-agentcore:GetPolicy",
    "bedrock-agentcore:UpdatePolicy",
    "bedrock-agentcore:DeletePolicy",
    "bedrock-agentcore:ListPolicies",
    "bedrock-agentcore:StartPolicyGeneration",
    "bedrock-agentcore:GetPolicyGeneration",
    "bedrock-agentcore:ListPolicyGenerations",
    "bedrock-agentcore:ListPolicyGenerationAssets"
  ],
  "Resource": "arn:aws:bedrock-agentcore:*:*:policy-engine/*"
}
```

If `encryptionKeyArn` is provided on `policy_engine_create`, also grant
`kms:Encrypt`, `kms:Decrypt`, `kms:GenerateDataKey`, and
`kms:DescribeKey` on that key.

---

## Migration from bedrock-agentcore-starter-toolkit

The old Python starter toolkit is deprecated. Migrate to the new
`agentcore` CLI and `agentcore.json`:

1. Replace any direct SDK setup of policy engines / policies with a
   `policyEngines` section in `agentcore.json`.
2. Reference the engine from a gateway via `policyEngineConfiguration`
   instead of passing it programmatically.
3. Deploy with `agentcore deploy` instead of invoking
   `CreatePolicyEngine` / `CreatePolicy` directly from your agent code.
4. Use the MCP tools in this server (`policy_*`) for interactive
   inspection and one-off operations — but keep declarative config in
   `agentcore.json` for reproducibility.
5. Generated policies (from `policy_generation_start`) remain
   ephemeral (7-day TTL) — promote valid assets into the
   `policyEngines[].policies[]` config if you want them persisted
   across deploys.
""".strip()


class GuideTools:
    """Static guide tool for AgentCore Policy."""

    def register(self, mcp):
        """Register guide tools with the MCP server."""
        mcp.tool(name='get_policy_guide')(self.get_policy_guide)

    async def get_policy_guide(self, ctx: Context) -> PolicyGuideResponse:
        """Get the comprehensive AgentCore Policy guide.

        Returns a detailed reference covering: CLI commands,
        agentcore.json schema, Cedar policy concepts, policy generation
        workflow, cost tiers, common patterns, troubleshooting, IAM
        permissions, and migration notes.

        This is a read-only operation with no cost implications.
        """
        return PolicyGuideResponse(guide=POLICY_GUIDE)
