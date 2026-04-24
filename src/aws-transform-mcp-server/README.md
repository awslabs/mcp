# AWS Transform MCP Server

An MCP server for [AWS Transform](https://aws.amazon.com/transform/) that enables AI assistants to manage transformation workspaces, jobs, connectors, human-in-the-loop (HITL) tasks, artifacts, and chat directly from the IDE.

AWS Transform accelerates migration and modernization of enterprise workloads using specialized AI agents across discovery, planning, and execution. This MCP server exposes the Transform lifecycle through 25 tools, supporting mainframe modernization, VMware migration, .NET modernization, and custom code transformations.

> [!IMPORTANT]
> This server uses stdio transport and runs as a long-lived process spawned by your MCP client.

## Features

1. **Workspace and job management** - Create, start, stop, and delete transformation workspaces and jobs
2. **Human-in-the-loop tasks** - Respond to HITL tasks with full component validation, output schemas, and response templates
3. **Artifact handling** - Upload and download artifacts (JSON, ZIP, PDF, HTML, TXT) up to 500 MB
4. **Connector management** - Create S3 and code source connectors, manage profiles, and accept connectors with IAM role association
5. **Chat** - Send messages to the Transform assistant and poll for responses
6. **Agent registry** - Query agent metadata and runtime configuration
7. **Resource browsing** - List and inspect any resource: workspaces, jobs, connectors, tasks, artifacts, worklogs, plans, and job types

## Prerequisites

1. [Python](https://www.python.org/) 3.10 or later
2. An [AWS Transform](https://aws.amazon.com/transform/) account with access to a tenant

## Installation

### Quick Start

```bash
uvx awslabs.aws-transform-mcp-server@latest
```

### Configure your MCP client

<details>
<summary>Claude Code</summary>

```bash
claude mcp add awslabs.aws-transform-mcp-server -- uvx awslabs.aws-transform-mcp-server@latest
```

</details>

<details>
<summary>Kiro</summary>

Add to `~/.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

</details>

<details>
<summary>Claude Desktop</summary>

Edit the config file for your OS:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows (WSL):** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

</details>

<details>
<summary>Cursor / VS Code / Cline</summary>

Add to your MCP settings file (`.cursor/mcp.json`, `.vscode/mcp.json`, or Cline MCP config):

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

</details>

### Verify

After configuring, restart your MCP client and ask: **"Check my AWS Transform connection status"**. The assistant calls `get_status` and returns the server version and authentication state.

## Authentication

Most tools require **Transform Web API auth**. Some advanced tools additionally require **SigV4 auth** (Control Plane). Configure through your AI assistant after adding the server.

### Web API Auth (required)

Choose one of the following:

#### SSO / IAM Identity Center (recommended)

Ask your AI assistant: **"Configure AWS Transform with SSO"**

The tool prompts for your IdC start URL (e.g., `https://d-xxx.awsapps.com/start`), opens a browser window for login, and saves credentials to `~/.aws-transform-mcp/config.json`. Tokens auto-load on restart.

#### Session Cookie

1. Log into the [AWS Transform Console](https://aws.amazon.com/transform/)
2. Open DevTools (F12) > **Application** > **Cookies**
3. Copy the session cookie value
4. Ask your AI assistant: **"Configure AWS Transform with cookie auth"** and provide the cookie and your tenant URL

### SigV4 Auth (optional)

Required for Control Plane tools: `accept_connector`, `create_profile`, `get_agent`, `get_agent_runtime_configuration`.

Ask your AI assistant: **"Configure SigV4 for AWS Transform"** and provide your AWS account ID.

> [!IMPORTANT]
> The `accept_connector` tool requires **both** Web API auth and SigV4 auth configured.

## Available Tools

### Configuration

| Tool | Description | Auth |
|------|-------------|------|
| `configure` | Connect via session cookie or SSO/IdC bearer token. | None |
| `configure_sigv4` | Configure AWS credentials for the Transform Control Plane. | None |
| `get_status` | Check all connection statuses and server version. | None |

### Workspace Management

| Tool | Description | Auth |
|------|-------------|------|
| `create_workspace` | Create a new transformation workspace. | Web API |
| `delete_workspace` | Permanently delete a workspace. Requires `confirm: true`. | Web API |

### Job Management

| Tool | Description | Auth |
|------|-------------|------|
| `create_job` | Create and immediately start a transformation job. Use `list_resources(resource="agents")` to discover available agents. | Web API |
| `control_job` | Start or stop an existing job. | Web API |
| `delete_job` | Permanently delete a job. Requires `confirm: true`. | Web API |

### HITL Task Management

| Tool | Description | Auth |
|------|-------------|------|
| `complete_task` | Handle HITL tasks with validation, file upload, and submission. Supports actions: APPROVE, REJECT, SEND_FOR_APPROVAL, SAVE_DRAFT. | Web API |
| `upload_artifact` | Upload files (JSON, ZIP, PDF, HTML, TXT) as artifacts. Max 500 MB. | Web API |

### Chat

| Tool | Description | Auth |
|------|-------------|------|
| `send_message` | Send a message to the Transform assistant. | Web API |
| `poll_message` | Wait for a response from the Transform assistant with server-side blocking. | Web API |

### Job Instructions

| Tool | Description | Auth |
|------|-------------|------|
| `load_instructions` | MUST be called before working on any job. Scans the artifact store for workflow instructions and downloads them if found. Other job-scoped tools block with `INSTRUCTIONS_REQUIRED` until this is called. | Web API |

### Connectors and Profiles

| Tool | Description | Auth |
|------|-------------|------|
| `create_connector` | Create an S3 or code source connector in a workspace. | Web API |
| `create_profile` | Create a profile with SSO or external IdP identity. | SigV4 |
| `accept_connector` | Associate an IAM role with a connector. | Web API + SigV4 |

### Agent Registry

| Tool | Description | Auth |
|------|-------------|------|
| `get_agent` | Get agent metadata by name. | SigV4 |
| `get_agent_runtime_configuration` | Get agent runtime config, optionally at a specific version. | SigV4 |

### Resource Listing and Details

| Tool | Description | Auth |
|------|-------------|------|
| `list_resources` | List any resource type: workspaces, jobs, connectors, tasks, artifacts, messages, worklogs, plan, agents, account_connectors, profiles, collaborators. | Web API (SigV4 for account_connectors, profiles) |
| `get_resource` | Get details for any resource by ID. Auto-downloads artifacts and enriches HITL tasks with output schemas. | Web API |

### Collaborators

| Tool | Description | Auth |
|------|-------------|------|
| `manage_collaborator` | Add or remove workspace collaborators. | Web API |

### Tool Approvals

| Tool | Description | Auth |
|------|-------------|------|
| `list_tool_approvals` | List pending tool approval tasks for a job. | Web API |
| `approve_tool_approval` | Approve an agent tool execution request. | Web API |
| `deny_tool_approval` | Deny an agent tool execution request. | Web API |
| `get_approval_status` | Check the status of a tool approval task. | Web API |

## Supported Transformation Types

- **Assessment** - Migration readiness assessment
- **Mainframe Modernization** - IBM z/OS and Fujitsu GS21 to Java (COBOL, JCL, CICS, DB2, VSAM)
- **VMware Migration** - Application discovery, dependency mapping, network conversion, wave planning, server rehosting to EC2
- **.NET Modernization** - .NET Framework to cross-platform .NET for Linux
- **Full-Stack Windows** - End-to-end application (.NET) + SQL Server + deployment modernization
- **Custom Transformation** - Java upgrades, Node.js, Python, API and framework migrations, language translations

## Configuration

### Stage Endpoints

| Stage | Regions | Tenant URL Format |
|-------|---------|-------------------|
| Prod | All standard AWS regions | `https://<tenant-id>.transform.<region>.on.aws` |

### Persisted Configuration

Authentication state is saved to `~/.aws-transform-mcp/config.json` and auto-loaded on restart. This includes auth mode, tokens, tenant URL, stage, and region.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FASTMCP_LOG_LEVEL` | Log level for the MCP server | `INFO` |
| `AWS_REGION` | AWS region for SigV4 credential resolution | boto3 default |
| `AWS_PROFILE` | AWS profile for SigV4 credential resolution | boto3 default |

## HITL Task Response System

When you fetch a task via `get_resource` with `resource="task"`, the response includes:

- **`_outputSchema`** - JSON Schema with field descriptions, types, enums, and required fields
- **`_responseTemplate`** - A concrete example response matching the schema
- **`_responseHint`** - Human-readable guidance for constructing the response

For components with runtime-defined fields (AutoForm, DynamicHITLRenderEngine), the server builds a dynamic schema from the agent artifact so field names are always accurate.

> [!IMPORTANT]
> Never auto-submit HITL task responses without explicit user review. Always present task details and the agent artifact to the user, then wait for their decision before calling `complete_task`.

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `AccessDeniedException: INVALID_SESSION` | Session cookie expired | Re-copy from DevTools > Application > Cookies |
| Server not starting | Missing Python 3.10+, missing dependencies | Verify `python --version` >= 3.10; re-run `uvx awslabs.aws-transform-mcp-server@latest` |
| Empty results | Auth not configured or wrong IDs | Run `get_status` to verify auth; confirm workspace/job IDs |
| SSO token expired | Bearer token lifetime exceeded | Re-run `configure` with SSO to refresh |

## Limitations

- **Cookie auth sessions expire** - No auto-refresh. Re-copy from browser periodically.
- **SSO tokens expire** - Re-run SSO configuration when tools return auth errors.
- **Windows is not directly supported** - Use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

## Security

### Architecture

This MCP server runs as a **local process** on the user's machine, communicating with the MCP client over **stdio** (stdin/stdout). It does not expose any network listeners, HTTP servers, or open ports. All outbound communication uses HTTPS to AWS-managed Transform API endpoints.

### Authentication and Credential Storage

The server supports three authentication modes, all using the caller's own credentials:

- **Session cookie** — user's browser session cookie for the Transform web API
- **SSO / OAuth bearer token** — obtained via IAM Identity Center with PKCE, auto-refreshed before expiry
- **SigV4** — standard AWS credential chain for Transform Control Plane APIs

Configuration including tokens is persisted to `~/.aws-transform-mcp/config.json`, written atomically (tmpfile + rename) with `0o600` permissions in a `0o700` directory. SigV4 credentials are resolved through the standard AWS credential chain (`boto3`).

### Encryption in Transit

All outbound HTTP calls use **HTTPS** exclusively. API endpoints are derived with hardcoded `https://` prefixes — there is no code path that constructs or accepts `http://` URLs. TLS certificate verification is enabled by default via `httpx` and `certifi`.

### Credential Exfiltration Prevention

The server blocks reads and writes to sensitive files and directories to prevent credential exfiltration via tool misuse:

- **Blocked filenames:** `.env`, `.netrc`, `.pgpass`, SSH keys (`id_rsa`, `id_ed25519`, etc.), `credentials`, `authorized_keys`, and others
- **Blocked directories:** `~/.aws`, `~/.ssh`, `~/.gnupg`, `~/.docker`, `~/.aws-transform-mcp`
- **Path traversal prevention:** all file paths are resolved and validated against directory boundaries
- **Extension allowlisting:** only approved file extensions can be downloaded

### Audit Logging

All tool invocations are logged with sanitized arguments. Sensitive parameters (`secret`, `password`, `credential`, `token`, `cookie`, `content`, `clientSecretArn`, `startUrl`) are automatically excluded from log output. Audit logging is fault-tolerant — failures in the logging path never block tool execution.

### File Download Safety

Artifact downloads enforce:
- Path traversal checks (resolved path must not escape target directory)
- Blocked filename checks
- Extension allowlisting (json, pdf, html, txt, csv, md, zip, gz, tar, yaml, xml, and others)

## License

This project is licensed under the Apache-2.0 License.
