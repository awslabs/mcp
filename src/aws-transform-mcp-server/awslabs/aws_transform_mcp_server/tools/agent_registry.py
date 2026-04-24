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

"""Agent registry tool handlers for AWS Transform MCP server."""

import re
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.config_store import is_sigv4_configured
from awslabs.aws_transform_mcp_server.tcp_client import call_tcp
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Optional


_SIGV4_NOT_CONFIGURED_CODE = 'SIGV4_NOT_CONFIGURED'
_SIGV4_NOT_CONFIGURED_MSG = 'SigV4 credentials not configured.'
_SIGV4_NOT_CONFIGURED_ACTION = 'Call "configure_sigv4" to set up AWS credentials.'

_AGENT_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')
_VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')


class AgentRegistryHandler:
    """Registers agent-registry-related MCP tools."""

    def __init__(self, mcp: Any) -> None:
        """Register agent registry tools on the MCP server."""
        audited_tool(mcp, 'get_agent')(self.get_agent)
        audited_tool(mcp, 'get_agent_runtime_configuration')(self.get_agent_runtime_configuration)

    async def get_agent(
        self,
        ctx: Context,
        agentName: str = Field(..., description='The name of the agent to retrieve'),
    ) -> dict:
        """Retrieve metadata for a specific agent by name via TCP.

        Requires AWS credentials -- call configure_sigv4 first.
        """
        if not is_sigv4_configured():
            return error_result(
                _SIGV4_NOT_CONFIGURED_CODE,
                _SIGV4_NOT_CONFIGURED_MSG,
                _SIGV4_NOT_CONFIGURED_ACTION,
            )

        if not _AGENT_NAME_RE.match(agentName):
            return error_result(
                'VALIDATION_ERROR',
                'agentName must be alphanumeric, underscore, or hyphen.',
            )

        try:
            data = await call_tcp('GetAgent', {'agentName': agentName})
            return success_result(data)
        except Exception as error:
            return failure_result(error)

    async def get_agent_runtime_configuration(
        self,
        ctx: Context,
        agentName: str = Field(..., description='The name of the agent'),
        version: Optional[str] = Field(
            None,
            description='Specific version to retrieve (semver format, e.g. "1.0.0")',
        ),
    ) -> dict:
        """Retrieve the runtime configuration for an agent, optionally at a specific version.

        Requires AWS credentials -- call configure_sigv4 first.
        """
        if not is_sigv4_configured():
            return error_result(
                _SIGV4_NOT_CONFIGURED_CODE,
                _SIGV4_NOT_CONFIGURED_MSG,
                _SIGV4_NOT_CONFIGURED_ACTION,
            )

        if not _AGENT_NAME_RE.match(agentName):
            return error_result(
                'VALIDATION_ERROR',
                'agentName must be alphanumeric, underscore, or hyphen.',
            )

        if version and not _VERSION_RE.match(version):
            return error_result(
                'VALIDATION_ERROR',
                'version must be in semver format (e.g. 1.0.0).',
            )

        try:
            body: dict = {'agentName': agentName}
            if version:
                body['version'] = version

            data = await call_tcp('GetAgentRuntimeConfiguration', body)
            return success_result(data)
        except Exception as error:
            return failure_result(error)
