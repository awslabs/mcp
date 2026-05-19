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

"""adaptive_poll tool — sleeps then returns a follow-up message for agent polling loops."""

import asyncio
from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.tool_utils import READ_ONLY, success_result
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any, Dict


MAX_SLEEP_SECONDS = 3000


class AdaptivePollHandler:
    """Registers the adaptive_poll tool."""

    def __init__(self, mcp: Any) -> None:
        """Register the adaptive_poll tool on the given MCP server."""
        audited_tool(
            mcp,
            'adaptive_poll',
            title='Adaptive Poll',
            annotations=READ_ONLY,
            description=(
                'Waits for the specified duration then returns a follow-up message. '
                'Use this when a resource (job, task, message) is in a transitional state '
                'and you need to re-check after a delay.\n\n'
                'Terminal job states (no polling needed): COMPLETED, FAILED, STOPPED.\n'
                'Terminal HITL task states: CANCELLED, CLOSED, CLOSED_PENDING_NEXT_TASK, DELIVERED.\n'
                'Any other status is transitional — use this tool to wait and re-check.\n\n'
                'IMPORTANT: Always ask the user for approval before calling this tool. '
                'The tool does no API calls — it only sleeps and echoes back your follow-up message.'
            ),
        )(self.adaptive_poll)

    async def adaptive_poll(
        self,
        ctx: Context,
        seconds: Annotated[
            int,
            Field(
                description='Number of seconds to wait before returning (1–300).',
                ge=1,
                le=MAX_SLEEP_SECONDS,
            ),
        ],
        follow_up: Annotated[
            str,
            Field(
                description=(
                    'Message returned after the wait completes. Include the tool call '
                    'and parameters the agent should execute next to re-check status.'
                ),
            ),
        ],
    ) -> Dict[str, Any]:
        """Sleep for *seconds* then return *follow_up* as the result."""
        clamped = max(1, min(seconds, MAX_SLEEP_SECONDS))
        await asyncio.sleep(clamped)
        return success_result(
            {
                'waited': clamped,
                'follow_up': follow_up,
            }
        )
