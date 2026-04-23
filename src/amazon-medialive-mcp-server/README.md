# AWS Labs Amazon MediaLive MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS Elemental MediaLive. This server provides typed tools for managing MediaLive channels, inputs, multiplexes, and related resources with rich schema intelligence auto-generated from botocore service models.

### Features

- Typed Pydantic models for every API parameter — the AI sees full JSON schema with field names, types, descriptions, and enum constraints
- Hand-written description overrides for field-level gotchas and usage guidance
- Cross-reference validation (e.g., VideoDescriptionName must match VideoDescriptions)
- Waiter tools for channel state transitions (channel_created, channel_running, channel_stopped, channel_deleted)
- Workflow context tool for understanding end-to-end media service pipelines
- Pagination support with tuned default page sizes

### Pre-Requisites

1. An [AWS account](https://aws.amazon.com/free/) with MediaLive access
2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
3. Install Python using `uv python install 3.10`
4. AWS credentials configured via `aws configure` or environment variables

### Tools

#### Channel Management
- `create_channel` — Create a MediaLive channel with full encoder settings
- `describe_channel` — Get channel details including state and configuration
- `list_channels` — List channels in the account/region
- `update_channel` — Update channel configuration
- `start_channel` — Start a channel (transitions to RUNNING)
- `stop_channel` — Stop a channel (transitions to IDLE)
- `delete_channel` — Delete a channel (must be IDLE)

#### Input Management
- `create_input` — Create an input (RTMP push, HLS pull, MediaConnect, etc.)
- `describe_input` — Get input details
- `list_inputs` — List inputs in the account/region
- `update_input` — Update input configuration
- `delete_input` — Delete an input

#### Multiplex Management
- `create_multiplex` — Create a multiplex
- `describe_multiplex` — Get multiplex details
- `list_multiplexes` — List multiplexes
- `start_multiplex` / `stop_multiplex` — Control multiplex lifecycle
- `delete_multiplex` — Delete a multiplex

#### Waiter Tools
- `wait_for_resource` — Wait for a resource to reach a desired state (channel_created, channel_running, channel_stopped, channel_deleted, input_attached, input_detached, input_deleted, multiplex_created, multiplex_running, multiplex_stopped, multiplex_deleted)

#### Additional Tools
- `batch_update_schedule` — Manage channel schedule actions
- `describe_schedule` — View scheduled actions
- Input security groups, multiplex programs, offerings, reservations, tags, thumbnails
- `get_media_workflow_context` — Understand how MediaLive fits in end-to-end streaming workflows

## Setup

### IAM Configuration

The server requires AWS credentials with MediaLive permissions. At minimum:
- `medialive:Describe*`, `medialive:List*` for read-only operations
- `medialive:Create*`, `medialive:Update*`, `medialive:Start*`, `medialive:Stop*` for write operations
- `medialive:Delete*` for destructive operations
- `iam:PassRole` for channel creation (to pass the MediaLive execution role)

### Installation

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.amazon-medialive-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-medialive-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Local Development

```bash
cd src/amazon-medialive-mcp-server
uv venv && uv sync --all-groups
```

Test with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector \
  uv \
  --directory /path/to/src/amazon-medialive-mcp-server \
  run \
  awslabs.amazon-medialive-mcp-server
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `AWS_REGION` | AWS region for MediaLive API calls | `us-east-1` |
| `AWS_PROFILE` | AWS credentials profile name | Default credentials chain |
| `FASTMCP_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `WARNING` |

## Security Considerations

- This server can create, modify, start, stop, and delete MediaLive resources
- Destructive operations (delete) are annotated in tool metadata
- Follow the principle of least privilege when configuring IAM permissions
- Use separate AWS profiles for different environments

## Version

Current MCP server version: 0.1.0
