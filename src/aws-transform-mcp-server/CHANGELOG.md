# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Artifact downloads now return a clear, actionable error when the server is
  spawned with the filesystem root (`/`) as its working directory. The
  write-path confinement added for the arbitrary-file-write fix pinned the
  allowed base to the current working directory; when that was `/`, the
  confinement check rejected every path with a confusing "must be within the
  working directory (/)" message. Downloads in this case are now refused with a
  message telling the operator to set the new `AWS_TRANSFORM_MCP_WRITE_DIR`
  environment variable to choose where downloads are written. The
  arbitrary-write protection is unchanged for all other cases.
- Added the `AWS_TRANSFORM_MCP_WRITE_DIR` environment variable to let an
  operator pin the artifact-download base directory explicitly.
- Artifact downloads now create the target directory if it does not already
  exist (within the confined base), instead of failing with `FileNotFoundError`.

## [0.1.0] - 2026-05-07

### Added

- First release of AWS Transform MCP Server with 19 tools
- **Configuration tools:**
  - `configure` — connect via session cookie or SSO/IdC bearer token (OAuth + PKCE)
  - `get_status` — check connection status, validate AWS credentials via STS, show server version
  - `switch_profile` — switch between regions when multiple credential-enabled profiles are discovered
- **Workspace management:**
  - `create_workspace` — create a new transformation workspace
  - `delete_workspace` — delete a workspace with explicit confirmation
- **Job management:**
  - `create_job` — create and start a transformation job
  - `control_job` — start or stop an existing job
  - `delete_job` — delete a job with explicit confirmation
- **Job status and polling:**
  - `get_job_status` — check job status with AI-generated summary or detailed raw snapshot
  - `adaptive_poll` — wait then return a follow-up message for transitional states
- **Chat:**
  - `send_message` — send a message to the Transform assistant and poll up to 60s for a reply
- **HITL task management:**
  - `complete_task` — submit HITL task responses (APPROVE, REJECT, SEND_FOR_APPROVAL, SAVE_DRAFT) with schema validation and file upload
  - `upload_artifact` — upload files (JSON, ZIP, PDF, HTML, TXT) up to 500 MB
- **Job instructions:**
  - `load_instructions` — load job-specific workflow instructions from the artifact store
- **Connectors:**
  - `create_connector` — create an S3 or code source connector in a workspace
  - `accept_connector` — associate an IAM role with a connector (requires both Web API and AWS credentials)
- **Resource browsing:**
  - `list_resources` — browse workspaces, jobs, connectors, tasks, artifacts, messages, worklogs, plan, agents, collaborators, users
  - `get_resource` — fetch a single resource with full details including HITL task output schema enrichment
- **Collaborators:**
  - `manage_collaborator` — add or remove workspace collaborators
- AWS credentials auto-detected from environment (AWS_PROFILE, credential chain) with multi-region discovery at startup
- Persisted authentication state in `~/.aws-transform-mcp/config.json` with auto-load on restart
- VPC configuration documentation with required endpoints, PrivateLink service names, and troubleshooting
