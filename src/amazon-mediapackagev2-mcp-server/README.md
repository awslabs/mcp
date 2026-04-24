# AWS Labs Amazon MediaPackage V2 MCP Server

An AWS Labs Model Context Protocol (MCP) server for AWS Elemental MediaPackage v2. This server provides typed tools for managing MediaPackage v2 channel groups, channels, origin endpoints, and harvest jobs with rich schema intelligence auto-generated from botocore service models.

### Features

- Typed Pydantic models for every API parameter — the AI sees full JSON schema with field names, types, descriptions, and enum constraints
- Hand-written description overrides for field-level gotchas and usage guidance
- Waiter tools for harvest job completion (harvest_job_finished)
- Workflow context tool for understanding end-to-end media service pipelines
- Pagination support with tuned default page sizes

### Pre-Requisites

1. An [AWS account](https://aws.amazon.com/free/) with MediaPackage v2 access
2. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/)
3. Install Python using `uv python install 3.10`
4. AWS credentials configured via `aws configure` or environment variables

### Tools

#### Channel Group Management
- `create_channel_group` — Create a channel group to organize channels and origin endpoints
- `get_channel_group` — Retrieve channel group details
- `list_channel_groups` — List all channel groups in the account/region
- `update_channel_group` — Update channel group description
- `delete_channel_group` — Delete a channel group (channels must be deleted first)

#### Channel Management
- `create_channel` — Create a channel to receive content streams from an encoder
- `get_channel` — Retrieve channel details including ingest endpoints
- `list_channels` — List channels in a channel group
- `update_channel` — Update channel configuration
- `delete_channel` — Delete a channel (origin endpoints must be deleted first)
- `reset_channel_state` — Reset a channel to clear encoder misconfiguration errors
- `get_channel_policy` — Retrieve the IAM policy attached to a channel
- `put_channel_policy` — Attach an IAM policy to a channel
- `delete_channel_policy` — Delete a channel policy

#### Origin Endpoint Management
- `create_origin_endpoint` — Create an origin endpoint for content playback (HLS, DASH, CMAF, MSS)
- `get_origin_endpoint` — Retrieve origin endpoint details and playback URL
- `list_origin_endpoints` — List origin endpoints in a channel
- `update_origin_endpoint` — Update origin endpoint packaging settings
- `delete_origin_endpoint` — Delete an origin endpoint
- `reset_origin_endpoint_state` — Reset an origin endpoint to clear previous content
- `get_origin_endpoint_policy` — Retrieve the IAM policy attached to an origin endpoint
- `put_origin_endpoint_policy` — Attach an IAM policy to an origin endpoint
- `delete_origin_endpoint_policy` — Delete an origin endpoint policy

#### Harvest Job Management
- `create_harvest_job` — Create a harvest job to export live content to S3
- `get_harvest_job` — Retrieve harvest job details
- `list_harvest_jobs` — List harvest jobs for a channel group
- `cancel_harvest_job` — Cancel an in-progress harvest job

#### Waiter Tools
- `wait_for_resource` — Wait for a resource to reach a desired state (harvest_job_finished)

#### Tagging
- `list_tags_for_resource` — List tags on a resource
- `tag_resource` — Add tags to a resource
- `untag_resource` — Remove tags from a resource

#### Additional Tools
- `get_media_workflow_context` — Understand how MediaPackage v2 fits in end-to-end streaming workflows

## Setup

### IAM Configuration

The server requires AWS credentials with MediaPackage v2 permissions. At minimum:
- `mediapackagev2:Get*`, `mediapackagev2:List*` for read-only operations
- `mediapackagev2:Create*`, `mediapackagev2:Update*`, `mediapackagev2:Put*` for write operations
- `mediapackagev2:Delete*` for destructive operations
- `mediapackagev2:TagResource`, `mediapackagev2:UntagResource` for tagging

### Installation

Configure the MCP server in your MCP client configuration (e.g., for Kiro, edit `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.amazon-mediapackagev2-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-mediapackagev2-mcp-server@latest"],
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
cd src/amazon-mediapackagev2-mcp-server
uv venv && uv sync --all-groups
```

Test with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector \
  uv \
  --directory /path/to/src/amazon-mediapackagev2-mcp-server \
  run \
  awslabs.amazon-mediapackagev2-mcp-server
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `AWS_REGION` | AWS region for MediaPackage v2 API calls | `us-east-1` |
| `AWS_PROFILE` | AWS credentials profile name | Default credentials chain |
| `FASTMCP_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `WARNING` |

## Security Considerations

- This server can create, modify, and delete MediaPackage v2 resources
- Destructive operations (delete, cancel) are annotated in tool metadata
- Follow the principle of least privilege when configuring IAM permissions
- Use separate AWS profiles for different environments

## Version

Current MCP server version: 0.0.0
