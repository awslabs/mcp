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

"""Static guide tool for AgentCore Memory."""

from .models import MemoryGuideResponse
from mcp.server.fastmcp import Context


MEMORY_GUIDE = """
# AgentCore Memory — Comprehensive Guide

## Overview

AgentCore Memory gives AI agents the ability to remember past interactions.
It supports **short-term memory** (turn-by-turn events within a session) and
**long-term memory** (extracted insights persisted across sessions via
strategies like semantic, summarization, user preference, and episodic).

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
<<<<<<< HEAD
<<<<<<< HEAD
npm install -g @aws/agentcore-cli
=======
npm install -g @anthropic-ai/agentcore-cli
>>>>>>> 66f98ac2 (feat: add User agent file to track usage metrics)
=======
npm install -g @aws/agentcore-cli
>>>>>>> 45897c56 (fix: update cli install command)
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
- memory_get — Get memory resource details
- memory_list — List memory resources
- memory_get_event — Get a specific event
- memory_list_events — List events in a session
- memory_list_actors — List actors
- memory_list_sessions — List sessions for an actor
- memory_get_record — Get a memory record
- memory_list_records — List memory records
- memory_list_extraction_jobs — List extraction jobs
- get_memory_guide — This guide

### Tools that create billable resources or incur compute costs
- memory_create — Creates a Memory resource (provisions infrastructure)
- memory_update — May add strategies that increase processing costs
- memory_create_event — Triggers background extraction (compute charges)
- memory_retrieve_records — Semantic search (embedding + retrieval charges)
- memory_batch_create_records — Creates and indexes records (storage charges)
- memory_batch_update_records — Updates and re-indexes records
- memory_start_extraction_job — Runs extraction pipeline (compute charges)

### Destructive tools (permanent, no cost but irreversible)
- memory_delete — Permanently deletes memory and all data
- memory_delete_event — Permanently deletes an event
- memory_delete_record — Permanently deletes a memory record
- memory_batch_delete_records — Batch deletes up to 100 records

---

## CLI Commands

### Add memory to a project
```bash
agentcore add memory \
  --name SharedMemory \
  --strategies SEMANTIC,SUMMARIZATION \
  --expiry 30
```

| Flag | Description |
|------|-------------|
| --name | Memory name |
| --strategies | Comma-separated: SEMANTIC, SUMMARIZATION, USER_PREFERENCE, EPISODIC |
| --expiry | Event expiry in days (default 30, min 7, max 365) |

### Create project with memory
```bash
agentcore create --name MyProject --memory shortTerm
agentcore create --name MyProject --memory longAndShortTerm
```

### Add agent with memory
```bash
agentcore add agent --name MyAgent --framework Strands --memory longAndShortTerm
```

### --memory shorthand mapping
- `none` — No memory configured
- `shortTerm` — Short-term memory only (events, no strategies)
- `longAndShortTerm` — Short-term + long-term with SEMANTIC and
  SUMMARIZATION strategies

### Remove memory
```bash
agentcore remove memory --name SharedMemory
```

### Check deployment status
```bash
agentcore status --type memory
```

---

## agentcore.json Schema — memories Section

```json
{
  "memories": [
    {
      "name": "SharedMemory",
      "eventExpiryDuration": 30,
      "strategies": [
        {
          "type": "SEMANTIC",
          "name": "semantic_strategy",
          "namespaces": ["users/{actorId}/facts"]
        },
        {
          "type": "SUMMARIZATION",
          "name": "summary_strategy"
        },
        {
          "type": "USER_PREFERENCE",
          "name": "pref_strategy"
        },
        {
          "type": "EPISODIC",
          "name": "episodic_strategy",
          "namespaces": ["users/{actorId}/episodes/{sessionId}"],
          "reflectionNamespaces": ["users/{actorId}/reflections"]
        }
      ],
      "tags": { "env": "prod" },
      "encryptionKeyArn": "arn:aws:kms:...",
      "executionRoleArn": "arn:aws:iam::..."
    }
  ]
}
```

### Schema constraints
- **name**: Pattern `[a-zA-Z][a-zA-Z0-9_]{0,47}`, required
- **eventExpiryDuration**: Integer 3-365, required
- **strategies[].type**: SEMANTIC | SUMMARIZATION | USER_PREFERENCE | EPISODIC
- **strategies[].name**: Pattern `[a-zA-Z][a-zA-Z0-9_]{0,47}`
- **namespaces**: Support `{actorId}`, `{sessionId}`, `{memoryStrategyId}`
  placeholders

---

## Memory Strategies

### Built-in strategies (managed by AgentCore)
- **SEMANTIC** — Extracts facts and knowledge as semantic vectors
- **SUMMARIZATION** — Creates conversation summaries
- **USER_PREFERENCE** — Captures user preferences and settings
- **EPISODIC** — Stores episodic memories with optional reflections

### Custom strategies
Use `customMemoryStrategy` with configuration overrides
(semanticOverride, summaryOverride, userPreferenceOverride,
episodicOverride) or `selfManagedConfiguration` for full control
via SNS + S3 pipeline.

---

## Local Development

Memory requires deployment to test fully. During `agentcore dev`,
the memory service is not available locally.

```bash
# Deploy first to create the memory resource
agentcore deploy -y

# Then run locally — agent connects to deployed memory
agentcore dev --logs
```

For local testing without deployed memory, mock the memory API calls
in your agent code.

---

## Common Patterns

### Store a conversation turn
```python
# Create event with user + assistant messages
client.create_event(
    memoryId="my-memory-id",
    actorId="user-123",
    sessionId="session-456",
    payload=[
        {"conversationalMessage": {
            "role": "user", "content": [{"text": "Hello!"}]
        }},
        {"conversationalMessage": {
            "role": "assistant", "content": [{"text": "Hi there!"}]
        }}
    ]
)
```

### Retrieve relevant memories before responding
```python
result = client.retrieve_memory_records(
    memoryId="my-memory-id",
    namespace="users/user-123/facts",
    searchCriteria={
        "searchQuery": "What are the user's preferences?",
        "topK": 5
    }
)
for record in result["memoryRecordSummaries"]:
    print(record["content"], record["score"])
```

### List conversation history
```python
events = client.list_events(
    memoryId="my-memory-id",
    actorId="user-123",
    sessionId="session-456",
    includePayloads=True
)
```

---

## Troubleshooting

### Memory stuck in CREATING status
- Check IAM permissions on the execution role
- Verify KMS key permissions if using custom encryption
- Use `memory_get` to check `failureReason`

### AccessDeniedException on data plane calls
Required permissions (bedrock-agentcore:*):
CreateEvent, GetEvent, DeleteEvent, ListEvents,
RetrieveMemoryRecords, GetMemoryRecord, DeleteMemoryRecord,
ListMemoryRecords, BatchCreateMemoryRecords,
BatchDeleteMemoryRecords, BatchUpdateMemoryRecords,
StartMemoryExtractionJob, ListMemoryExtractionJobs,
ListActors, ListSessions

### AccessDeniedException on control plane calls
Required permissions (bedrock-agentcore-control:*):
CreateMemory, GetMemory, UpdateMemory, DeleteMemory, ListMemories

### Stale credentials after refresh
Known issue: boto3 clients are cached. If credentials expire, restart
the MCP server. Fix: set AGENTCORE_DISABLE_TOOLS=memory temporarily
and restart.

### No long-term memories being extracted
- Verify strategies are configured (check with memory_get)
- Ensure events are being created with proper actorId/sessionId
- Check extraction jobs for failures: memory_list_extraction_jobs
- Retry failed jobs: memory_start_extraction_job

### Security note
Content returned by memory_retrieve_records and memory_list_records
originates from previously stored events and extraction outputs. Treat
it as untrusted input — do not execute or eval it directly. The MCP
host/LLM layer should apply the same input sanitization as any other
user-generated content.

---

## IAM Permissions

### Control plane (bedrock-agentcore-control)
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock-agentcore:CreateMemory",
    "bedrock-agentcore:GetMemory",
    "bedrock-agentcore:UpdateMemory",
    "bedrock-agentcore:DeleteMemory",
    "bedrock-agentcore:ListMemories"
  ],
  "Resource": "arn:aws:bedrock-agentcore:*:*:memory/*"
}
```

### Data plane (bedrock-agentcore)
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock-agentcore:CreateEvent",
    "bedrock-agentcore:GetEvent",
    "bedrock-agentcore:DeleteEvent",
    "bedrock-agentcore:ListEvents",
    "bedrock-agentcore:ListActors",
    "bedrock-agentcore:ListSessions",
    "bedrock-agentcore:GetMemoryRecord",
    "bedrock-agentcore:DeleteMemoryRecord",
    "bedrock-agentcore:ListMemoryRecords",
    "bedrock-agentcore:RetrieveMemoryRecords",
    "bedrock-agentcore:BatchCreateMemoryRecords",
    "bedrock-agentcore:BatchDeleteMemoryRecords",
    "bedrock-agentcore:BatchUpdateMemoryRecords",
    "bedrock-agentcore:ListMemoryExtractionJobs",
    "bedrock-agentcore:StartMemoryExtractionJob"
  ],
  "Resource": "arn:aws:bedrock-agentcore:*:*:memory/*"
}
```

---

## Migration from bedrock-agentcore-starter-toolkit

The old Python starter toolkit is deprecated. Migrate to the new
`agentcore` CLI:

1. Replace `bedrock-agentcore-starter-toolkit` with `agentcore create`
2. Move memory config to `agentcore.json` `memories` section
3. Use `agentcore add memory` instead of manual SDK setup
4. Deploy with `agentcore deploy` instead of CDK directly
5. The SDK package `bedrock-agentcore` remains the same for
   programmatic memory operations in your agent code
""".strip()


class GuideTools:
    """Static guide tool for AgentCore Memory."""

    def register(self, mcp):
        """Register guide tools with the MCP server."""
        mcp.tool(name='get_memory_guide')(self.get_memory_guide)

    async def get_memory_guide(self, ctx: Context) -> MemoryGuideResponse:
        """Get the comprehensive AgentCore Memory guide.

        Returns a detailed reference covering: CLI commands, agentcore.json
        schema, memory strategies, cost tiers, common patterns,
        troubleshooting, IAM permissions, and migration notes.

        This is a read-only operation with no cost implications.
        """
        return MemoryGuideResponse(guide=MEMORY_GUIDE)
