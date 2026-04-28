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

"""Entry point for the AWS Transform MCP server.

Creates a FastMCP instance with full guidance instructions and registers
all tool handlers.
"""

import argparse
import asyncio
from awslabs.aws_transform_mcp_server.config_store import load_persisted_config
from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Instructions — sent once during MCP initialization.  Contains cross-tool
# workflows, behavioral constraints, and capability hints only.  Individual
# tool behavior belongs in each tool's description, not here.
# ---------------------------------------------------------------------------

INSTRUCTIONS = """AWS Transform MCP Server — manage workspaces, jobs, tasks, connectors, artifacts, and agents.

# Authentication

Two independent auth systems. Configuring one does NOT affect the other.
All tools are always visible — if auth is missing, the tool returns a
structured error with the exact setup step to follow.

- `configure` → browser/SSO auth (FES). Used by most tools.
- `configure_sigv4` → AWS IAM credentials (TCP). Used by accept_connector.
- `accept_connector` requires BOTH.
- `configure`, `configure_sigv4`, and `get_status` work without auth.

# Workflows

## Before working on any job

Call `load_instructions` with workspaceId and jobId first. Other tools return
INSTRUCTIONS_REQUIRED if this is skipped.

## HITL task handling

1. `get_resource(resource="task")` — fetch task details, agent artifact, `_outputSchema`, `_responseTemplate`, `_responseHint`.
2. Present task details and artifact content to the user.
3. Wait for the user's explicit decision — do NOT proceed without it.
4. `complete_task` with the user-confirmed response.

NEVER auto-submit. Never guess response content — use `_outputSchema` and
`_responseTemplate`. For file uploads: `upload_artifact` first, then include
`artifactId`. If `agentArtifactContent` is `{}`, check worklogs — the agent
may still be generating.

# Tool Selection
- **Job status / progress (polling)** → use `get_job_status` for a complete snapshot
  (job metadata, worklogs, HITL tasks, messages, plan) in a single call.
  IMPORTANT: After calling get_job_status, if `_pollingGuidance.isTerminal` is false,
  you MUST automatically call it again in 1 minute. DO NOT ask the user — just poll.
  Keep polling until isTerminal is true or the user says stop.
  If `hasPendingTasks` is true, handle HITL tasks immediately.
- **Job status / progress (interactive)** → use `send_message` scoped to the job
  to ask the Transform assistant about status. The assistant has full job context.
  Also call `list_resources(resource="worklogs")` for recent activity.
  Only fall back to `list_resources` / `get_resource` if you need more information
  the assistant didn't cover or send message has no useful information.
- Browse collections → `list_resources`
- Fetch a single resource with full details → `get_resource`
- Basic job metadata only → `get_resource(resource="job")`
- Workspace-level connectors → `list_resources(resource="connectors")` (FES)
- Create a new connector → `create_connector`
- Associate an IAM role with an existing connector → `accept_connector`
- Check connection health → `get_status`

# Error Recovery

- `NOT_CONFIGURED` → run `configure` (cookie or SSO).
- `SIGV4_NOT_CONFIGURED` → run `configure_sigv4`.
- `INSTRUCTIONS_REQUIRED` → run `load_instructions` for the job.
- Auth errors (401/403) on any tool → run `get_status` to diagnose.
- When uncertain about parameter values, ask the user — do not guess.

# Constraints

- MUST NOT delete workspaces or jobs without explicit user confirmation.
"""


def create_server() -> FastMCP:
    """Create and return a configured FastMCP server instance.

    Separated from main() for testability.
    """
    return FastMCP(
        'awslabs.aws-transform-mcp-server',
        instructions=INSTRUCTIONS,
        dependencies=['boto3', 'botocore', 'pydantic', 'loguru', 'httpx'],
    )


def _register_handlers(mcp: FastMCP) -> None:
    """Import and instantiate all tool handler classes on *mcp*.

    All tools are registered at startup regardless of auth state.
    Auth is checked at call time — tools return NOT_CONFIGURED or
    SIGV4_NOT_CONFIGURED with a suggestedAction if auth is missing.
    """
    from awslabs.aws_transform_mcp_server.tools.approve_hitl import ApproveHitlHandler
    from awslabs.aws_transform_mcp_server.tools.artifact import ArtifactHandler
    from awslabs.aws_transform_mcp_server.tools.chat import ChatHandler
    from awslabs.aws_transform_mcp_server.tools.collaborator import CollaboratorHandler
    from awslabs.aws_transform_mcp_server.tools.configure import ConfigureHandler
    from awslabs.aws_transform_mcp_server.tools.connector import ConnectorHandler
    from awslabs.aws_transform_mcp_server.tools.get_resource import GetResourceHandler
    from awslabs.aws_transform_mcp_server.tools.hitl import HitlHandler
    from awslabs.aws_transform_mcp_server.tools.job import JobHandler
    from awslabs.aws_transform_mcp_server.tools.job_status import JobStatusHandler
    from awslabs.aws_transform_mcp_server.tools.list_resources import ListResourcesHandler
    from awslabs.aws_transform_mcp_server.tools.load_instructions import LoadInstructionsHandler
    from awslabs.aws_transform_mcp_server.tools.sigv4_configure import SigV4ConfigureHandler
    from awslabs.aws_transform_mcp_server.tools.workspace import WorkspaceHandler

    ConfigureHandler(mcp)
    SigV4ConfigureHandler(mcp)
    WorkspaceHandler(mcp)
    JobHandler(mcp)
    HitlHandler(mcp)
    ArtifactHandler(mcp)
    ChatHandler(mcp)
    ConnectorHandler(mcp)
    ListResourcesHandler(mcp)
    GetResourceHandler(mcp)
    CollaboratorHandler(mcp)
    ApproveHitlHandler(mcp)
    LoadInstructionsHandler(mcp)
    JobStatusHandler(mcp)


def main() -> None:
    """Entry point for the AWS Transform MCP server."""
    import os
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'INFO'))

    from pathlib import Path

    log_dir = Path.home() / '.aws-transform-mcp'
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(log_dir / 'server.log', rotation='10 MB', retention='7 days', level='INFO')

    parser = argparse.ArgumentParser(
        description='AWS Transform MCP server — manage workspaces, jobs, connectors, and tasks.',
    )
    parser.parse_args()

    # Restore persisted auth config from ~/.aws-transform-mcp/config.json
    asyncio.run(load_persisted_config())

    mcp = create_server()
    _register_handlers(mcp)
    mcp.run()


if __name__ == '__main__':
    main()
