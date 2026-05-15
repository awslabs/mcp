# AWS Bedrock AgentCore MCP Server

Model Context Protocol (MCP) server for Amazon Bedrock AgentCore — providing operational API tools that let AI coding agents manage AgentCore resources directly.

## Overview

This MCP server gives AI agents (Claude Code, Kiro, Cursor, VS Code, Codex CLI) direct access to AgentCore platform APIs. Agents can create and manage runtimes, store and retrieve memories, configure identity providers, deploy gateways, and manage policies — all through standard MCP tool calls backed by real boto3 API calls.

**122 tools** across 7 operational primitives + documentation search.

|Primitive           |Tools|What it does                                                                                   |
|--------------------|----:|-----------------------------------------------------------------------------------------------|
|**Runtime**         |14   |Deploy, manage, and invoke agent runtimes and endpoints                                        |
|**Memory**          |21   |Create memory resources, store events, semantic search, batch operations, extraction jobs      |
|**Identity**        |21   |Manage workload identities, API key providers, OAuth2 providers, token vault, resource policies|
|**Gateway**         |15   |Create and manage API gateways, gateway targets, resource policies                             |
|**Policy**          |15   |Create policy engines, manage policies, generate and review policy assets                      |
|**Browser**         |25   |Cloud-based browser automation — navigate, click, type, screenshot, extract data               |
|**Code Interpreter**|9    |Sandboxed code execution, file upload/download, package installation                           |
|**Documentation**   |2    |Search and fetch AgentCore docs                                                                |

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
1. Install Python 3.10+ using `uv python install 3.10`
1. AWS credentials configured (AWS_PROFILE, AWS_ACCESS_KEY_ID, or IAM role)

## Installation

|Kiro                                                                                                                                                                                                                                                                                                         |Cursor                                                                                                                                                                                                                                                                                                                                                                                                     |VS Code                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=bedrock-agentcore-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D)|[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=bedrock-agentcore-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWJlZHJvY2stYWdlbnRjb3JlLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6WyJzZWFyY2hfYWdlbnRjb3JlX2RvY3MiLCJmZXRjaF9hZ2VudGNvcmVfZG9jIl19)|[![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20AgentCore%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%22search_agentcore_docs%22%2C%22fetch_agentcore_doc%22%5D%7D)|

### Configuration

Add to your MCP client configuration (e.g., `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Windows

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uv",
      "args": [
        "tool", "run", "--from",
        "awslabs.amazon-bedrock-agentcore-mcp-server@latest",
        "awslabs.amazon-bedrock-agentcore-mcp-server.exe"
      ],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" }
    }
  }
}
```

## Tool Configuration

All primitive tools are enabled by default. Use environment variables to control which tools are registered:

```bash
# Disable specific primitives
AGENTCORE_DISABLE_TOOLS=browser,code_interpreter

# Or enable only specific primitives
AGENTCORE_ENABLE_TOOLS=memory,runtime,identity
```

When `AGENTCORE_ENABLE_TOOLS` is set, only the listed primitives are registered. Documentation tools (`search_agentcore_docs`, `fetch_agentcore_doc`) are always available.

## Primitives

### Runtime (14 tools)

Manage agent runtimes and endpoints on AgentCore. Create runtimes, deploy endpoint versions, invoke agents, and manage sessions.

Key tools: `create_agent_runtime`, `create_agent_runtime_endpoint`, `invoke_agent_runtime`, `stop_runtime_session`, `get_runtime_guide`

### Memory (21 tools)

Create memory resources, store conversation events, retrieve semantically relevant memories, and manage extraction jobs. Supports both short-term (session events) and long-term (extracted insights) memory.

Key tools: `memory_create`, `memory_create_event`, `memory_retrieve_records`, `memory_batch_create_records`, `get_memory_guide`

> **Note:** The MCP tools call AgentCore Memory APIs directly via boto3. The `agentcore` CLI is not required to use these tools.

### Identity (21 tools)

Manage workload identities, API key credential providers, OAuth2 credential providers, token vault configuration, and resource policies. Data plane operations (token retrieval) are intentionally excluded — they return live credentials that should not flow through LLM context.

Key tools: `identity_create_workload_identity`, `identity_create_api_key_provider`, `identity_create_oauth2_provider`, `identity_get_token_vault`, `get_identity_guide`

### Gateway (15 tools)

Create and manage API gateways that transform existing APIs into agent-callable MCP tools. Manage gateway targets (Lambda, OpenAPI, Smithy, MCP servers) and resource policies. The `InvokeGateway` data plane operation is excluded — it requires agent-runtime JWTs and can return sensitive content.

Key tools: `gateway_create`, `gateway_target_create`, `gateway_target_synchronize`, `gateway_resource_policy_put`, `get_gateway_guide`

### Policy (15 tools)

Create policy engines, manage authorization policies, and generate policy assets. Policy engines enforce fine-grained access control for agent actions.

Key tools: `policy_engine_create`, `policy_create`, `policy_generation_start`, `policy_generation_get`, `get_policy_guide`

### Browser (25 tools)

Cloud-based browser automation powered by AgentCore. Each session runs in an isolated Firecracker microVM — no local browser installation needed.

```
start_browser_session → browser_navigate → browser_snapshot → browser_click → stop_browser_session
```

Tips:

- Use DuckDuckGo or Bing instead of Google (CAPTCHAs block cloud IPs)
- Use `browser_evaluate` with `querySelectorAll` for data extraction
- `timeout_seconds` is an idle timeout, not absolute duration

### Code Interpreter (9 tools)

Sandboxed code execution in isolated environments. Start a session, execute code or shell commands, install packages, and transfer files.

Key tools: `start_code_interpreter_session`, `execute_code`, `execute_command`, `install_packages`, `upload_file`, `download_file`

> **Cost note:** Sessions incur AWS charges. Stop sessions when done.

### Documentation (2 tools)

Search and fetch AgentCore documentation. These tools are always available regardless of `AGENTCORE_DISABLE_TOOLS` settings.

- `search_agentcore_docs` — search with ranked results and snippets
- `fetch_agentcore_doc` — retrieve full document content by URL

## Cost Awareness

Tools that create AWS resources or invoke compute incur charges. Each primitive’s guide tool (`get_memory_guide`, `get_runtime_guide`, etc.) documents cost tiers:

- **Read-only** (no cost): get, list, guide operations
- **Billable** (AWS charges): create, update, invoke, search operations
- **Destructive** (irreversible): delete operations

Billable and destructive tools include `COST WARNING:` or `WARNING:` in their descriptions so agents understand the implications before calling them.

## Security

- All API calls use boto3 with credentials resolved from your environment (AWS_PROFILE, env vars, or IAM role)
- Operations that return credential material (tokens, API keys, secrets) are excluded from MCP tools — credentials should not flow through LLM context
- Retrieved content (memory records, gateway responses) should be treated as untrusted input
- User-agent tracking (`agentcore-mcp-server/{version} {primitive}`) is included in API calls for usage analytics — no telemetry is sent elsewhere

## Architecture

Each primitive is implemented as an independent sub-package under `tools/`:

```
tools/
├── runtime/       # 14 tools — agent runtime management
├── memory/        # 21 tools — memory resources and records
├── identity/      # 21 tools — workload identity and credentials
├── gateway/       # 15 tools — API gateway management
├── policy/        # 15 tools — policy engine management
├── browser/       # 25 tools — cloud browser automation
├── code_interpreter/  # 9 tools — sandboxed code execution
└── docs.py        # 2 tools — documentation search
```

Each sub-package contains: cached boto3 client wrapper, Pydantic response models, structured error handler, domain tool files, and a comprehensive guide tool.
