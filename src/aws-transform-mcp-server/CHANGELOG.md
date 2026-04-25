# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-24

### Added

- First release of AWS Transform MCP Server
- `configure` tool. Connect to AWS Transform using a browser session cookie or SSO/IdC bearer token
- `configure_sigv4` tool. Configure AWS IAM credentials for the Transform Control Plane (TCP) API
- `get_status` tool. Check the status of all configured connections (FES and SigV4)
- `create_workspace` tool. Create a new transformation workspace
- `delete_workspace` tool. Delete a workspace with explicit confirmation
- `create_job` tool. Create and start a transformation job in a workspace
- `control_job` tool. Start or stop an existing job
- `delete_job` tool. Delete a job with explicit confirmation
- `load_instructions` tool. Load job-specific workflow instructions before working on a job
- `send_message` tool. Send a chat message to a transformation agent
- `poll_message` tool. Wait for a response from the transformation agent with server-side blocking
- `complete_task` tool. Submit a human-in-the-loop (HITL) task response with schema validation
- `upload_artifact` tool. Upload a file artifact to a job
- `list_resources` tool. Browse collections of workspaces, jobs, connectors, tasks, artifacts, messages, worklogs, plans, agents, profiles, and collaborators
- `get_resource` tool. Fetch a single resource with full details including HITL task enrichment
- `create_connector` tool. Create an S3 or code source connector in a workspace
- `create_profile` tool. Create an ATX profile via the Transform Control Plane
- `accept_connector` tool. Associate an IAM role with a connector (requires both FES and SigV4 auth)
- `get_agent` tool. Fetch agent details from the agent registry
- `get_agent_runtime_configuration` tool. Fetch agent runtime configuration
- `manage_collaborator` tool. Add or remove workspace collaborators
- `list_tool_approvals` tool. List pending tool approval tasks for a job
- `approve_tool_approval` tool. Approve an agent tool execution request
- `deny_tool_approval` tool. Deny an agent tool execution request
- `get_approval_status` tool. Check the status of a tool approval task
