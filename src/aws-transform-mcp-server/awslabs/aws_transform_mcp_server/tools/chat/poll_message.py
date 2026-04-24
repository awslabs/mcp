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

"""poll_message tool — blocks server-side while waiting for an assistant response."""

from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.tools.chat._common import (
    build_metadata,
    build_poll_call,
    build_timeout_data,
    format_response,
    not_configured_error,
    poll_for_response,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Optional


async def poll_message(
    ctx: Context,
    workspaceId: str = Field(..., description='Workspace ID (UUID format)'),
    sentMessageId: str = Field(
        ...,
        description=(
            'The messageId of the sent message to poll for a response to. '
            'Returned by send_message in sentMessage.messageId.'
        ),
    ),
    jobId: Optional[str] = Field(
        None,
        description='Job ID (UUID) to scope the conversation to a specific job',
    ),
) -> dict:
    """Poll for an assistant response to a previously sent message.

    Blocks up to 60s waiting for a FINAL_RESPONSE. Use when send_message
    timed out — its result contains the exact poll_message call to make.
    Also use after send_message with skipPolling=true.

    Do NOT use list_resources + get_resource in a loop — this tool replaces
    that pattern. If 60s elapses, the result includes the exact call to retry.
    """
    if not is_configured():
        return not_configured_error()

    _jobId: Optional[str] = jobId if isinstance(jobId, str) else None

    try:
        metadata = build_metadata(workspaceId, _jobId)

        result = await poll_for_response(
            metadata,
            workspaceId,
            sentMessageId,
            max_attempts=30,
        )

        if result['terminal']:
            resp = format_response(result['terminal'])
            if result['is_error']:
                return error_result(
                    'ASSISTANT_ERROR',
                    resp.get('text') or 'The assistant returned an error.',
                    f'sentMessageId={sentMessageId}, workspaceId={workspaceId}',
                )
            return success_result({'response': resp})

        poll_call = build_poll_call(workspaceId, sentMessageId, _jobId)
        return success_result(build_timeout_data(poll_call, 60, result['last_thinking']))
    except Exception as error:
        return failure_result(error)
