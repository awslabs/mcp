# AWS Transform MCP Server

[![PyPI Downloads](https://static.pepy.tech/personalized-badge/awslabs-aws-transform-mcp-server?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/awslabs-aws-transform-mcp-server) [![PyPI Downloads/month](https://static.pepy.tech/personalized-badge/awslabs-aws-transform-mcp-server?period=month&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads/month)](https://pepy.tech/projects/awslabs-aws-transform-mcp-server)

An MCP server for [AWS Transform](https://aws.amazon.com/transform/) that enables AI assistants to manage transformation workspaces, jobs, connectors, human-in-the-loop (HITL) tasks, artifacts, and chat directly from the IDE.

AWS Transform accelerates migration and modernization of enterprise workloads using specialized AI agents across discovery, planning, and execution. This MCP server exposes the Transform lifecycle through 19 tools, supporting mainframe modernization, VMware migration, .NET modernization, and custom code transformations.

> [!IMPORTANT]
> This server uses stdio transport and runs as a long-lived process spawned by your MCP client.

## Features

1. **Workspace and job management** - Create, start, stop, and delete transformation workspaces and jobs
2. **Human-in-the-loop tasks** - Respond to HITL tasks with full component validation, output schemas, and response templates
3. **Artifact handling** - Upload and download artifacts (JSON, ZIP, PDF, HTML, TXT) up to 500 MB
4. **Connector management** - Create S3 and code source connectors, manage profiles, and accept connectors with IAM role association
5. **Chat** - Send messages to the Transform assistant with automatic response polling
6. **Job status and polling** - Check job status with AI-generated summaries or detailed raw snapshots, with adaptive polling for transitional states
7. **Resource browsing** - List and inspect any resource: workspaces, jobs, connectors, tasks, artifacts, worklogs, plans, agents, collaborators, and users

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
        "AWS_REGION": "us-east-1",
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
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

For macOS/Linux:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

For Windows:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false
    }
  }
}
```

</details>

<details>
<summary>Cursor / VS Code / Cline</summary>

Add to your MCP settings file (`.cursor/mcp.json`, `.vscode/mcp.json`, or Cline MCP config):

For macOS/Linux:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

For Windows:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false
    }
  }
}
```

</details>

### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false
    }
  }
}
```

### Verify

After configuring, restart your MCP client and ask: **"Check my AWS Transform connection status"**. The assistant calls `get_status` and returns the server version and authentication state.

## Authentication

Most tools require **Transform Web API auth** (browser login). One tool (`accept_connector`) additionally requires **AWS credentials**, which are detected automatically from your environment.

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

### AWS Credential Auth (auto-detected)

Required for Control Plane tools such as `accept_connector`.

AWS credentials are detected automatically from your environment — no tool call needed. Set `AWS_PROFILE` in your MCP client config `env` block to select a specific profile. Credentials auto-refresh when temporary tokens expire.

At startup the server probes all supported regions. If multiple regions have active profiles, use `switch_profile` to select which region to use.

To verify your credentials are working, ask your AI assistant: **"Check my AWS Transform connection status"** — `get_status` validates via STS and shows your account ID, ARN, and the resolved TCP endpoint.

> [!IMPORTANT]
> The `accept_connector` tool requires **both** Web API auth and AWS credentials.

## Available Tools

### Configuration

| Tool | Description | Auth |
|------|-------------|------|
| `configure` | Connect via session cookie or SSO/IdC bearer token. | None |
| `get_status` | Check all connection statuses, validate AWS credentials via STS, and show server version. | None |
| `switch_profile` | Switch between available regions when multiple credential-enabled profiles are discovered. | Web API |

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
| `complete_task` | Handle HITL tasks with validation, file upload, and submission. Supports actions: APPROVE, REJECT, SEND_FOR_APPROVAL, SAVE_DRAFT. For TOOL_APPROVAL tasks (agent tool execution requests), only APPROVE and REJECT are valid — artifact upload is skipped automatically. | Web API |
| `upload_artifact` | Upload files (JSON, ZIP, PDF, HTML, TXT) as artifacts. Max 500 MB. | Web API |

### Chat

| Tool | Description | Auth |
|------|-------------|------|
| `send_message` | Send a message to the Transform assistant and poll up to 60s for a reply. On timeout, returns `sentMessageId` for follow-up retrieval. | Web API |

### Job Status and Polling

| Tool | Description | Auth |
|------|-------------|------|
| `get_job_status` | Check the status of a running job. By default asks the Transform assistant for a concise summary. Pass `detailed=true` for the full raw snapshot (worklogs, tasks, messages, plan steps). | Web API |
| `adaptive_poll` | Wait for a specified duration then return a follow-up message. Use when a resource is in a transitional state. Does no API calls — only sleeps. | None |

### Job Instructions

| Tool | Description | Auth |
|------|-------------|------|
| `load_instructions` | MUST be called before working on any job. Scans the artifact store for workflow instructions and downloads them if found. Other job-scoped tools block with `INSTRUCTIONS_REQUIRED` until this is called. | Web API |

### Connectors

| Tool | Description | Auth |
|------|-------------|------|
| `create_connector` | Create an S3 or code source connector in a workspace. | Web API |
| `accept_connector` | Associate an IAM role with a connector. | Web API + AWS credentials |

### Resource Listing and Details

| Tool | Description | Auth |
|------|-------------|------|
| `list_resources` | List any resource type: workspaces, jobs, connectors, tasks, artifacts, messages, worklogs, plan, agents, collaborators, users. Use `category="TOOL_APPROVAL"` and `taskStatus="AWAITING_APPROVAL"` to list pending tool approvals. | Web API |
| `get_resource` | Get details for any resource by ID. Auto-downloads artifacts and enriches HITL tasks with output schemas. | Web API |

### Collaborators

| Tool | Description | Auth |
|------|-------------|------|
| `manage_collaborator` | Add or remove workspace collaborators. | Web API |

## Supported Transformation Types

- **Assessment** - Migration readiness assessment
- **Mainframe Modernization** - IBM z/OS and Fujitsu GS21 to Java (COBOL, JCL, CICS, DB2, VSAM)
- **VMware Migration** - Application discovery, dependency mapping, network conversion, wave planning, server rehosting to EC2
- **.NET Modernization** - .NET Framework to cross-platform .NET for Linux
- **Full-Stack Windows** - End-to-end application (.NET) + SQL Server + deployment modernization
- **Custom Transformation** - Java upgrades, Node.js, Python, API and framework migrations, language translations

## Configuration

### Persisted Configuration

Authentication state is saved to `~/.aws-transform-mcp/config.json` and auto-loaded on restart. This includes auth mode, tokens, tenant URL, and region.

### Environment Variables

Set these in your MCP client config `env` block:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_PROFILE` | No | `default` profile | AWS profile from `~/.aws/credentials` to use for Control Plane tools (e.g., `accept_connector`). If you have multiple AWS profiles, set this to the one with access to your Transform account. If not set, boto3 uses the `[default]` profile, then falls back to environment variables (`AWS_ACCESS_KEY_ID`), then instance metadata. See [boto3 credential chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) for the full resolution order. |
| `AWS_REGION` | No | Profile region, then `us-east-1` | AWS region for Control Plane API calls. If not set, uses the region from your AWS profile (`~/.aws/config`), then falls back to `us-east-1`. |
| `FASTMCP_LOG_LEVEL` | No | `INFO` | Log level for the MCP server (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

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

## VPC Configuration

The server makes outbound HTTPS calls to AWS-managed endpoints. When running on an instance in a VPC without direct internet access, ensure these endpoints are reachable.

> [!IMPORTANT]
> The server does not open any inbound ports. All communication with the MCP client is over stdio. Only outbound TCP 443 is required.

### Required Endpoints

The server connects to the following endpoints. Replace `{region}` with your AWS region (e.g., `us-east-1`).

**Core API:**

| Endpoint | Purpose | PrivateLink Service Name |
|----------|---------|--------------------------|
| `api.transform.{region}.on.aws` | Transform API — jobs, workspaces, artifacts, chat | `com.amazonaws.{region}.api.transform` |
| `transform.{region}.api.aws` | TCP — connectors, profiles, agents | `com.amazonaws.{region}.transform` |

See [AWS Transform and interface VPC endpoints](https://docs.aws.amazon.com/transform/latest/userguide/vpc-interface-endpoints.html) for details on these service names.

**Authentication:**

| Endpoint | Purpose | PrivateLink Service Name |
|----------|---------|--------------------------|
| `oidc.{region}.amazonaws.com` | SSO OIDC token exchange and refresh | None — requires NAT Gateway |
| `sts.{region}.amazonaws.com` | Credential verification, connector ops | `com.amazonaws.{region}.sts` |

**Artifact storage:**

| Endpoint | Purpose | PrivateLink Service Name |
|----------|---------|--------------------------|
| `*.s3.{region}.amazonaws.com` | Pre-signed URL upload and download | `com.amazonaws.{region}.s3` (Gateway) |

The server does not call S3 directly — it uses pre-signed URLs returned by the Transform API. The domain may be virtual-hosted style (`{bucket}.s3.{region}.amazonaws.com`).

**SSO browser login** (only during `configure` with SSO auth):

| Endpoint | Purpose |
|----------|---------|
| `oidc.{region}.amazonaws.com` | OAuth authorize redirect |
| `portal.sso.{region}.amazonaws.com` | SSO portal login |
| `assets.sso-portal.{region}.amazonaws.com` | SSO portal static assets |
| `{directory-id}.awsapps.com` | IAM Identity Center portal |
| `{region}.signin.aws` | SSO sign-in redirect |

These domains are documented in [Accessing the AWS Transform web application from a VPC](https://docs.aws.amazon.com/transform/latest/userguide/vpc-webapp-access.html). AWS credential auth (SigV4) does not require these browser endpoints.

### VPC Endpoints

Create these endpoints for private connectivity without a NAT Gateway. Service names are documented in [AWS Transform and interface VPC endpoints](https://docs.aws.amazon.com/transform/latest/userguide/vpc-interface-endpoints.html).

| Service Name | Purpose | Private DNS |
|--------------|---------|-------------|
| `com.amazonaws.{region}.api.transform` | Transform API | Required |
| `com.amazonaws.{region}.transform` | Control Plane | Optional |
| `com.amazonaws.{region}.sts` | STS | Optional |
| `com.amazonaws.{region}.s3` | S3 (Gateway) | N/A |

> [!IMPORTANT]
> The `com.amazonaws.{region}.api.transform` endpoint requires private DNS enabled. Without it, `api.transform.{region}.on.aws` resolves to a public IP and API calls fail with connection timeouts.

SSO OIDC and SSO Portal do not have PrivateLink support. Use a NAT Gateway or HTTP proxy for these.

### Security Groups

**Instance (private subnet)** — outbound TCP 443 to `0.0.0.0/0` (or scoped to VPC endpoint ENIs and NAT Gateway).

**VPC endpoint ENIs** — inbound TCP 443 from the private subnet CIDR.

### Network Firewall (Controlled Egress)

For strict domain-based filtering, deploy AWS Network Firewall with TLS SNI inspection. The [VPC web application access guide](https://docs.aws.amazon.com/transform/latest/userguide/vpc-webapp-access.html) covers:

- Stateful rule group with the domain allowlist
- Symmetric routing between private, firewall, and public subnets
- Route table configuration for each subnet tier
- Verification commands

Estimated base cost: ~$325/month per AZ (Network Firewall + NAT Gateway + Elastic IP). See [AWS Network Firewall pricing](https://aws.amazon.com/network-firewall/pricing/) for current rates.

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection timeout on Transform API calls | VPC endpoint missing or private DNS disabled | Create `com.amazonaws.{region}.api.transform` with private DNS enabled |
| Connection timeout on TCP calls | No route to TCP endpoint | Create `com.amazonaws.{region}.transform` endpoint or add NAT Gateway route |
| SSO token refresh fails | OIDC endpoint unreachable | Verify NAT Gateway routes to `oidc.{region}.amazonaws.com` |
| Artifact upload/download fails | S3 unreachable | Create S3 Gateway Endpoint and verify route table entry |
| DNS returns public IP for `api.transform.{region}.on.aws` | Private DNS not enabled | Delete and re-create the VPC endpoint with **Enable DNS name** selected |

Verify connectivity from your instance:

```bash
# Should return a private IP address if VPC endpoint is configured
nslookup api.transform.us-east-1.on.aws

# Should return HTTP 403 or similar (confirms network path works)
curl -v --connect-timeout 15 'https://api.transform.us-east-1.on.aws/'

# Should return account info (confirms STS reachability)
aws sts get-caller-identity

# Should list buckets (confirms S3 Gateway Endpoint)
aws s3 ls --region us-east-1
```

## License

This project is licensed under the Apache-2.0 License.
