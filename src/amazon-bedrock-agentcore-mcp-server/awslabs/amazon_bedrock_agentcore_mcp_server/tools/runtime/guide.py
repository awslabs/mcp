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

"""Static reference guide for AgentCore Runtime."""

from .models import GuideResponse
from mcp.server.fastmcp import Context


RUNTIME_GUIDE = r"""
# Amazon Bedrock AgentCore Runtime — Quick Reference

## What is AgentCore Runtime?

A serverless hosting environment for AI agents and tools. Each user
session runs in an isolated microVM with dedicated CPU, memory, and
filesystem. Supports HTTP, MCP, A2A, and AGUI protocols.

---

## CLI Commands (agentcore CLI — npm package @aws/agentcore)

### Project lifecycle

```bash
agentcore create --name MyAgent --defaults   # scaffold project
agentcore dev                                 # local dev server on :8080
agentcore dev "Hello"                         # invoke local agent
agentcore deploy                              # deploy to AWS via CDK
agentcore deploy --plan                       # preview without deploying
agentcore invoke "Tell me a joke"             # invoke deployed agent
agentcore invoke --stream "Hello"             # stream response
agentcore invoke --session-id my-sess "Hi"    # maintain session
agentcore status                              # check deployment status
agentcore logs                                # stream CloudWatch logs
agentcore traces list                         # list recent traces
```

### Resource management

```bash
agentcore add agent --name X --framework Strands --model-provider Bedrock
agentcore add memory --name M --strategies SEMANTIC
agentcore add gateway --name G
agentcore add gateway-target --name T --type mcp-server --endpoint URL --gateway G
agentcore remove agent --name X
agentcore remove all                          # remove all, then deploy to tear down
```

### Build types

- **CodeZip** (default): Python code zipped and uploaded to S3.
  Max 250MB zipped / 750MB unzipped.
- **Container**: Docker image pushed to ECR. Must be ARM64.

---

## agentcore.json — Runtime Configuration

The `agents` array in `agentcore/agentcore.json` configures each agent:

```jsonc
{
  "agents": [{
    "name": "MyAgent",
    "language": "Python",
    "framework": "Strands",
    "type": "create",
    "codeLocation": "app/MyAgent",
    "entrypoint": "main.py",
    "build": "CodeZip",
    "modelProvider": "Bedrock",
    "protocol": "HTTP",            // HTTP | MCP | A2A
    "networkMode": "PUBLIC",       // PUBLIC | VPC
    "memory": "none"               // none | shortTerm | longAndShortTerm
  }]
}
```

---

## Protocol Contracts

| Protocol | Port  | Path           | Message Format  |
|----------|-------|----------------|-----------------|
| HTTP     | 8080  | /invocations   | JSON / SSE      |
| MCP      | 8000  | /mcp           | JSON-RPC        |
| A2A      | 9000  | /              | JSON-RPC 2.0    |
| AGUI     | 8080  | /invocations   | SSE events      |

All protocols require ARM64 containers on host 0.0.0.0.
All require a `/ping` GET endpoint returning `{"status": "Healthy"}`.

---

## Session Lifecycle

- **Created** on first invoke with a `runtimeSessionId` (33+ chars).
- **Active**: processing a request or background task.
- **Idle**: waiting; auto-terminates after `idleRuntimeSessionTimeout`
  (default 900s / 15 min).
- **Terminated**: microVM destroyed, memory sanitized. Same session ID
  creates a new environment.
- **Max lifetime**: 28800s (8 hours).
- Use `stop_runtime_session` to terminate early and save costs.

---

## Cost Tiers for MCP Tools

### Per-use billable (creates/uses microVM sessions)
- `invoke_agent_runtime` — sends request to agent, charges for
  compute time while session is active

### One-time setup (creates infrastructure)
- `create_agent_runtime` — provisions runtime definition
- `create_agent_runtime_endpoint` — creates endpoint config

### Cost-saving (terminates resources)
- `stop_runtime_session` — terminates microVM early, prevents
  idle-timeout charges
- `delete_agent_runtime` — removes all infrastructure
- `delete_agent_runtime_endpoint` — removes endpoint

### Read-only (no cost)
- `get_agent_runtime`, `list_agent_runtimes`,
  `list_agent_runtime_versions`
- `get_agent_runtime_endpoint`, `list_agent_runtime_endpoints`
- `get_runtime_guide`

---

## IAM Permissions

### Caller permissions (to manage runtimes)
```
bedrock-agentcore:CreateAgentRuntime
bedrock-agentcore:GetAgentRuntime
bedrock-agentcore:UpdateAgentRuntime
bedrock-agentcore:DeleteAgentRuntime
bedrock-agentcore:ListAgentRuntimes
bedrock-agentcore:CreateAgentRuntimeEndpoint
bedrock-agentcore:GetAgentRuntimeEndpoint
bedrock-agentcore:UpdateAgentRuntimeEndpoint
bedrock-agentcore:DeleteAgentRuntimeEndpoint
bedrock-agentcore:ListAgentRuntimeEndpoints
bedrock-agentcore:InvokeAgentRuntime
bedrock-agentcore:StopRuntimeSession
```

### Execution role (for the agent itself)
Must trust `bedrock-agentcore.amazonaws.com` and include:
- ECR image access (if container deploy)
- CloudWatch Logs (create log group/stream, put events)
- X-Ray (put trace segments)
- Bedrock model invocation (if using Bedrock models)

### Managed policy
`BedrockAgentCoreFullAccess` — broad permissions for development.
Use least-privilege custom policies in production.

---

## Versioning & Endpoints

- `CreateAgentRuntime` creates Version 1 + DEFAULT endpoint.
- Each `UpdateAgentRuntime` creates a new immutable version.
- DEFAULT endpoint auto-updates to latest version.
- Custom endpoints pin to a specific version until explicitly updated.
- States: CREATING → READY (or CREATE_FAILED) → UPDATING → READY.

---

## Common Patterns

### Multi-turn conversation
```python
# Reuse the same session ID across invocations
session_id = str(uuid.uuid4())
for prompt in prompts:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt}).encode()
    )
```

### Blue-green deployment
```python
# 1. Update runtime (creates new version)
client.update_agent_runtime(agentRuntimeId=id, ...)
# 2. Test on DEFAULT endpoint
# 3. Update production endpoint to new version
client.update_agent_runtime_endpoint(
    agentRuntimeId=id,
    endpointName='production',
    agentRuntimeVersion='3'
)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 504 Gateway Timeout | Agent /invocations took too long. Check logs. |
| AccessDeniedException | Missing IAM permissions or wrong role. |
| CREATE_FAILED | Check failureReason via GetAgentRuntime. |
| "exec format error" | Container not built for ARM64. |
| Session terminated early | Increase idleRuntimeSessionTimeout. |
| "Unknown service" in boto3 | Upgrade boto3: pip install --upgrade boto3 |
| Long-running tool interrupted | Ensure async tasks report HealthyBusy via /ping. |

---

## Migration from Deprecated Starter Toolkit

The old `bedrock-agentcore-starter-toolkit` (Python pip package) and its
YAML config file are **deprecated**. Do not use the old pip-based
toolkit for new projects.

The replacement is `@aws/agentcore` (npm package):

| What changed | New CLI equivalent |
|---|---|
| Project scaffolding | `agentcore create` |
| Deploying to AWS | `agentcore deploy` |
| Tearing down resources | `agentcore remove all` then `agentcore deploy` |
| Config file | `agentcore/agentcore.json` (replaces the old YAML) |
| Build system | CDK-based (replaces CodeBuild) |

Install: `npm install -g @aws/agentcore`
""".strip()


class GuideTools:
    """Static reference guide for AgentCore Runtime."""

    def register(self, mcp) -> None:
        """Register the guide tool with the MCP server."""
        mcp.tool(name='get_runtime_guide')(self.get_runtime_guide)

    async def get_runtime_guide(self, ctx: Context) -> GuideResponse:
        """Get a comprehensive reference guide for AgentCore Runtime.

        Covers CLI commands, agentcore.json schema, protocol contracts,
        session lifecycle, IAM permissions, cost tiers, common patterns,
        troubleshooting, and migration notes.

        Read-only, no cost implications.
        """
        return GuideResponse(guide=RUNTIME_GUIDE)
