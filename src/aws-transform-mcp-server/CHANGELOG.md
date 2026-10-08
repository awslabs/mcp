# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Asia Pacific (Singapore) `ap-southeast-1` is now included in region discovery,
  so accounts whose only AWS Transform profile lives there are found by the
  startup credential probe and by SSO profile discovery.

- Added the `download_artifact` tool, which streams a job or user artifact, or a
  connector asset, through the `GetArtifact` event-stream operation so no
  pre-signed S3 URL is returned to the client. The file is saved only after the
  terminal `streamFinishedEvent` arrives; a stream that ends without it is
  reported as `STREAM_INCOMPLETE` and nothing is written. Without `outputPath`
  the file is written to the allowed write base (`AWS_TRANSFORM_MCP_WRITE_DIR`
  or the server working directory); an `outputPath` that ends in `/`, has no
  file extension, or names an existing directory saves inside it under the
  file's own name, as `get_resource`'s `savePath` does. The bytes are never
  returned inline; the result carries the path, byte count, and SHA-256.
  Workspace-scope downloads are not supported.

### Removed

- Removed the `ListPlanUpdates` call from the `plan` resource in `get_resource`
  and `list_resources`. The call hard-coded `planVersion='1'`, which the service
  rejects with a `ValidationException` for any job whose latest plan version is
  not exactly 1 — every job that has no plan yet (version 0) and every re-planned
  job (version 2 and up). The service exposes no way for a client to read the
  current plan version, and the server only ever requested a full snapshot
  (`timestamp=0`), which `ListJobPlanSteps` already provides without a version
  parameter. `get_resource(plan)` now auto-paginates `ListJobPlanSteps` (a
  filtered page can be empty yet carry a `nextToken`, so single-page reads could
  truncate large plans); `list_resources(plan)` keeps manual pagination via
  `stepsNextToken`. The `planUpdates`/`updatesNextToken` output fields and the
  `updatesNextToken` parameter are gone; a job with no plan yet returns
  `NOT_FOUND` instead of a validation error.

- Trimmed the vendored `elasticgumbyfrontendservice` service model to the
  operations available through this server (and pruned their now-unused shapes):
  the plan operations `CreatePlan`, `UpdatePlan`, `GetPlan`, and `ListPlans`; the
  dashboard operations `CreateDashboard` and `GetDashboard`;
  `ListIamRoleAssignments`; the `SendMessageStreaming` streaming operation; and
  the internal test operations `TestReleaseTraitPreProd` and
  `TestReleaseTraitProd`.
- Removed the legacy `jobType` parameter from the `create_job` tool and the
  `CreateJobRequest` model. AWS Transform no longer honors `jobType` on
  `CreateJob`; callers must use `orchestratorAgent` instead. The
  `orchestratorAgent` description no longer suggests retrying with it after a
  `jobType` failure.

### Fixed

- `create_connector` now returns a reachable `verificationLink` in AWS
  GovCloud. The link was built against the commercial console
  (`console.aws.amazon.com`), which does not serve the `aws-us-gov` partition,
  so the URL users were told to open to finish connector setup was broken. The
  console host is now chosen from the region.
- AWS GovCloud (`us-gov-west-1`) can now authenticate. Both discovery fan-outs
  (the startup credential probe and the SSO `ListAvailableProfiles` sweep) ran
  over a hardcoded list of nine commercial regions, so a GovCloud caller found
  no profile in any region and every tool reported `NOT_CONFIGURED` or
  `NO_PROFILES` even though the account was fine. The region list is now chosen
  from the caller's partition — the resolved AWS region for credential auth,
  the Identity Center region for SSO — so neither partition probes the other.
- `configure(authMode="cookie")` now accepts a GovCloud application URL. The
  origin parser's region group matched only two-word region ids, so
  `us-gov-west-1` was rejected with `INVALID_APPLICATION_URL`.
- Artifact uploads and downloads now use transfer-specific HTTP timeouts instead
  of HTTPX's five-second default, preventing large pre-signed S3 transfers from
  failing while data is still being sent or received.
- `load_instructions` now discovers instruction documents stored inside
  artifact-store folders. Customer uploads (the `upload_artifact` tool and the
  AWS Transform web console) are stored under the store's `User Uploads/`
  folder, and the unprefixed `ListArtifacts` discovery listing does not descend
  into folders, so uploaded instruction documents were never found regardless
  of file name. Discovery now re-scans each folder the root listing reports
  (plus the canonical `User Uploads/` prefix as a fallback) and matches the
  instruction label against the path basename. A folder whose scan fails is
  skipped rather than failing the call.
- `upload_artifact` re-arms the one-shot instructions check when the uploaded
  file matches an instruction label, so a document uploaded mid-session is
  picked up by the next `load_instructions` call.
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
