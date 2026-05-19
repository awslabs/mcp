### Related to existing issue?
No existing issue. This is a new MCP server proposal for AWS Transform.

### Summary

An MCP server for AWS Transform that enables AI assistants to manage the full transformation lifecycle — workspaces, jobs, connectors, human-in-the-loop (HITL) tasks, artifacts, and chat — directly from the IDE and CLI.

AWS Transform accelerates migration and modernization of enterprise workloads using specialized AI agents. It supports mainframe modernization, VMware migration to EC2, .NET modernization to cross-platform .NET, full-stack Windows modernization, and custom code transformations (Java, Node.js, Python).

The server exposes **19 tools** across workspace management, job lifecycle, HITL task handling with dynamic output schema validation, artifact upload/download, connector management, resource browsing, agent registry queries, collaborator management, tool approval workflows (via HITL), chat with integrated polling, and job status monitoring. It is built in Python using FastMCP (`mcp[cli]>=1.23.0`) and distributed via PyPI as `awslabs.aws-transform-mcp-server`.

### Use Cases

1. **Seamless IDE-to-Transform bridge for last-mile completion** — Customers need a bridge between AWS Transform and their coding companion. Transform handles heavy lifting (assessment, code analysis, refactoring), but remaining gaps require a coding companion. With the MCP server loaded in Kiro or Claude Code, the AI assistant uses Transform's specialized agents first, then continues with the IDE's native capabilities for remaining errors — all in a single interface.

2. **End-to-end .NET and full-stack Windows modernization from IDE** — A developer with a .NET Framework project open in Kiro can kick off a full modernization without switching to the console. The AI assistant creates a workspace, uploads source code to S3, creates a connector, starts the job, and handles HITL checkpoints — all through natural language.

3. **Autonomous job monitoring with adaptive polling** — The AI assistant monitors long-running transformation jobs using `get_job_status` for concise summaries and `adaptive_poll` for wait-and-retry loops, presenting HITL tasks to the user for confirmation as they arise.

### Architecture

```
┌─────────────┐     stdio      ┌──────────────────┐     HTTPS      ┌─────────────────────┐
│  MCP Client  │◄──────────────►│  ATX MCP Server  │◄──────────────►│  Transform Web API  │
│  (Kiro,      │                │  (Python/FastMCP) │                │  (FES — Cookie,     │
│   Claude,    │                │                  │                │   Bearer, or SigV4) │
│   Cursor)    │                │                  │     HTTPS      ├─────────────────────┤
└─────────────┘                │                  │◄──────────────►│  Transform CP API   │
                                └──────────────────┘                │  (TCP — SigV4)      │
                                         │                          └─────────────────────┘
                                         ▼
                              ~/.aws-transform-mcp/config.json
                              (persisted auth state, file 0600, dir 0700,
                               atomic write via tmpfile + os.replace)
```

**Transport:** stdio only (MCP client spawns server as subprocess). No SSE/WebSocket mode.

**Internal API clients:**
- **FES client** (`fes_client.py`): Uses a vendored botocore C2J service model to create a `boto3.client("elasticgumbyfrontendservice")`. Supports cookie auth (session header injection), bearer token auth (Authorization header), and SigV4 auth (standard credential chain). Includes automatic token refresh with 5-minute buffer.
- **TCP client** (`tcp_client.py`): SigV4-signed RPC-over-HTTP to the Transform Control Plane. Operations include `AssociateConnectorResource`, `GetAgent`, `GetAgentRuntimeConfiguration`, `ListAgents`, etc.

### Tool Registration Pattern

All tools are registered at startup via the `audited_tool` decorator, which wraps each handler with automatic audit logging (redacting sensitive parameters like `sessionCookie`, `bearer_token`, `content`). Auth state is checked at call time — tools return `NOT_CONFIGURED` with a `suggestedAction` if auth is missing.

```python
class WorkspaceHandler:
    def __init__(self, mcp):
        audited_tool(mcp, 'create_workspace', title='Create Workspace', annotations=MUTATE)(
            self.create_workspace
        )
        audited_tool(mcp, 'delete_workspace', title='Delete Workspace', annotations=DELETE_IDEMPOTENT)(
            self.delete_workspace
        )

    async def create_workspace(
        self,
        ctx: Context,
        name: Annotated[str, Field(description='Name for the workspace')],
        description: Annotated[Optional[str], Field(description='Optional description')] = None,
    ) -> dict:
        """Create a new transformation workspace."""
        if not is_fes_available():
            return error_result('NOT_CONFIGURED', ...)
        result = await call_fes('CreateWorkspace', CreateWorkspaceRequest(
            name=name, description=description, idempotencyToken=str(uuid.uuid4()),
        ))
        return success_result(result.get('workspace', result))
```

### Tool Inventory (19 active)

| # | Tool | Category | Description | Auth Required |
|---|------|----------|-------------|---------------|
| 1 | `configure` | Configuration | Authenticate via SSO (OAuth PKCE) or cookie | None |
| 2 | `get_status` | Configuration | Check connection health (FES + SigV4 + TCP) | None |
| 3 | `switch_profile` | Configuration | Switch region/profile (SSO or SigV4) | Active session |
| 4 | `create_workspace` | Workspaces | Create a new transformation workspace | FES (any auth) |
| 5 | `delete_workspace` | Workspaces | Permanently delete a workspace (requires confirm) | FES (any auth) |
| 6 | `create_job` | Jobs | Create + start a job, poll until ready, fetch initial messages | FES (any auth) |
| 7 | `control_job` | Jobs | Start or stop a running job | FES (any auth) |
| 8 | `delete_job` | Jobs | Permanently delete a job (requires confirm) | FES (any auth) |
| 9 | `complete_task` | HITL Tasks | Submit HITL task response (APPROVE/REJECT/SEND_FOR_APPROVAL/SAVE_DRAFT) | FES (any auth) |
| 10 | `upload_artifact` | Artifacts | Upload file or raw content, returns artifactId | FES (any auth) |
| 11 | `send_message` | Chat | Send message to Transform assistant, polls up to 60s for reply | FES (any auth) |
| 12 | `create_connector` | Connectors | Create S3/CODE connector in a workspace | FES (any auth) |
| 13 | `accept_connector` | Connectors | Activate connector by associating IAM role (SigV4 + FES) | FES + AWS credentials |
| 14 | `list_resources` | Resource Access | List workspaces/jobs/connectors/tasks/artifacts/messages/worklogs/plan/agents/collaborators/users | FES (any auth) |
| 15 | `get_resource` | Resource Access | Get single resource: session/workspace/job/connector/task/artifact/asset/messages/plan | FES (any auth) |
| 16 | `load_instructions` | Job Instructions | Load job-specific workflow instructions (required before other job operations) | FES (any auth) |
| 17 | `get_job_status` | Job Status | Concise assistant summary or full raw snapshot (job/tasks/worklogs/messages/plan) | FES (any auth) |
| 18 | `manage_collaborator` | Collaborators | Add/update/remove workspace collaborators (put/remove/leave) | FES (any auth) |
| 19 | `adaptive_poll` | Polling | Sleep N seconds then return follow-up message for polling loops | None |

**Tool approval workflows** are handled via `complete_task` with `category=TOOL_APPROVAL` — the server detects TOOL_APPROVAL tasks and uses a fast path (direct approve/reject without artifact upload).

### Authentication Flow

Three authentication methods (any ONE is sufficient):

1. **AWS Credentials (zero-config, recommended):** Auto-detected at startup. The server probes SigV4 credentials by fanning out `ListWorkspaces` across all 9 supported regions (`us-east-1`, `eu-central-1`, `ap-southeast-2`, `ap-northeast-1`, `eu-west-2`, `ap-northeast-2`, `sa-east-1`, `ap-south-1`, `ca-central-1`) with a 5-second timeout per region. If exactly one region succeeds, it auto-selects. If multiple succeed, stores them for deferred selection via `switch_profile`. Uses boto3's standard credential chain (`AWS_PROFILE`, `~/.aws/credentials`, instance profile).

2. **SSO/IdC (explicit):** User calls `configure` with `authMode: "sso"`, `startUrl`, and `idcRegion`. Server runs OAuth Authorization Code + PKCE flow:
   - Registers a temporary OIDC client via `boto3` sso-oidc (`register_client`)
   - Starts a local HTTP callback server on `127.0.0.1:8079`
   - Opens a browser for login (uses platform-specific `open`/`xdg-open` commands)
   - Exchanges the auth code for tokens
   - Fans out `ListAvailableProfiles` across all 9 regions to discover available profiles
   - Supports MCP elicitation for multi-profile selection (falls back to PROFILE_SELECTION_REQUIRED)
   - Stores bearer + refresh token in `~/.aws-transform-mcp/config.json`

3. **Session Cookie (explicit):** User calls `configure` with `authMode: "cookie"`, `sessionCookie`, and `origin` (tenant URL, format: `https://{id}.transform.{region}.on.aws`). Server validates via `VerifySession` call.

**Token refresh:** Bearer tokens are automatically refreshed when within 5 minutes of expiry (`TOKEN_REFRESH_BUFFER_SECS = 300`).

**Config persistence:** Written atomically via `tempfile.mkstemp()` + `os.replace()`. File permissions: `0600` (owner read/write only). Directory permissions: `0700`.

### HITL Task System

The HITL system is the most complex subsystem:

- **114 output schema definitions** (`hitl_output_schemas.py`, 7799 lines) — auto-generated from the schema registry, each defining a UX component's output shape (display-only flag, merge behavior, JSON Schema)
- **52 component customizations** (`hitl_schemas.py`) — per-component preprocessing, templates, response hints, and validation logic
- **Dynamic schema generation** — at task retrieval time, the server downloads the agent artifact, builds a dynamic JSON Schema from it (based on `uxComponentId`), and enriches the task response with `_outputSchema`, `_responseTemplate`, and `_responseHint`
- **Format and validate pipeline** — `format_and_validate()` preprocesses LLM responses through component-specific formatters before submission
- **Actions:** APPROVE, REJECT, SEND_FOR_APPROVAL (CRITICAL severity only), SAVE_DRAFT
- **TOOL_APPROVAL fast path** — skips artifact upload/download/validation, submits directly

### Behavioral Guardrails

The server enforces several behavioral constraints via its instructions and tool logic:

1. **INSTRUCTIONS_REQUIRED gate** — `load_instructions` must be called before any job operation; tools return `INSTRUCTIONS_REQUIRED` error otherwise (`guidance_nudge.py`)
2. **Destructive action confirmation** — `delete_workspace`, `delete_job`, and `manage_collaborator` (remove/leave) require explicit `confirm=true`
3. **HITL human-confirmation mandate** — `complete_task` docstring explicitly states: "REQUIRES EXPLICIT USER CONFIRMATION. Before calling this tool you MUST present the full task details..."
4. **Audit logging** — every tool invocation is logged with non-sensitive parameters; error responses are logged at WARNING level
5. **File validation** — `validate_read_path()` prevents path traversal on file uploads

### Distribution

Published to PyPI as `awslabs.aws-transform-mcp-server`:
1. Python source built with `hatchling` (`pyproject.toml`)
2. Installed via `uvx awslabs.aws-transform-mcp-server@latest`
3. Entry point: `awslabs.aws-transform-mcp-server` → `awslabs.aws_transform_mcp_server.server:main`
4. Integrates with the monorepo's existing CI, release tooling, and version bumping (`commitizen` for conventional commits)
5. Supports Python 3.10–3.13

### Out of Scope
- Direct database or infrastructure modifications — server interacts with AWS Transform APIs only
- Real-time streaming of job logs or events — server uses server-side blocking via `poll_for_response` for chat (polls ListMessages up to 30 attempts) and `adaptive_poll` for agent-driven wait loops; other resources are fetched on demand
- Windows native support — WSL is supported (browser opening falls back to `xdg-open`)

### Potential Challenges

1. **Triple authentication model** — Requires three independent auth systems: (a) bearer token from SSO OIDC for web app operations, (b) session cookie for web app operations (alternative to bearer), and (c) SigV4 for Control Plane API calls (`accept_connector`, agent registry). The zero-config SigV4 path also supports FES calls, creating a complex auth routing layer.

2. **HITL task schema complexity** — HITL tasks have runtime-defined schemas that vary by component type. The server dynamically generates JSON Schema, response templates, and hints from agent artifacts at task fetch time. 52 component customizations and 114 output schema definitions are maintained in auto-generated code.

3. **Multi-region profile discovery** — Both SSO and SigV4 startup probe fan out concurrent requests across 9 regions with a 5-second timeout per region. Network conditions can make startup slow. Multiple-region responses require deferred selection via elicitation or `switch_profile`.

4. **Polling complexity** — Chat responses, job creation, and status checks all use internal polling loops (up to 60-90 seconds). The `adaptive_poll` tool adds agent-driven polling on top. Long-running operations can hit MCP client timeouts.

### Dependencies and Integrations

| Dependency | Version | Purpose |
|---|---|---|
| `mcp[cli]` | ≥1.23.0 | FastMCP framework, stdio transport |
| `boto3` | ≥1.37.27 | AWS SDK (SSO OIDC, STS, credential chain) |
| `botocore[crt]` | ≥1.37.27 | SigV4 signing, CRT for HTTP/2 |
| `httpx` | ≥0.28.0 | Async HTTP client (S3 uploads/downloads, retry logic) |
| `pydantic` | ≥2.10.6 | Request/response models, Field descriptions for tool schemas |
| `loguru` | ≥0.7.0 | Structured logging to stderr + `~/.aws-transform-mcp/server.log` |

**Internal service dependencies:**
- AWS Transform Web API (FES — `api.transform.{region}.on.aws`)
- AWS Transform Control Plane (TCP — `transform.{region}.api.aws`)
- IAM Identity Center (SSO OIDC for OAuth flow)
- AWS STS (credential validation via `GetCallerIdentity`)
- Amazon S3 (artifact upload/download via presigned URLs)

### Alternative Solutions Considered

1. **Standalone awslabs repo** — Publish as `awslabs/atx-mcp-server` outside the monorepo. Reduces discoverability compared to being listed alongside the other 40+ servers. Would also miss the monorepo's shared CI, release tooling, and PyPI publishing workflow.

2. **Contribute to managed AWS MCP Server** — The 19 tools require deterministic API orchestration with correct sequencing (job lifecycle with polling, connector setup with acceptance flow, HITL validation against 114 dynamic schemas) which does not fit the SOP model.

3. **Separate tools for each resource operation** — Instead of the consolidated `list_resources` (11 resource types) and `get_resource` (9 resource types) pattern, individual tools could be created. The consolidated approach was chosen to stay within MCP client tool limits while providing comprehensive resource access.
