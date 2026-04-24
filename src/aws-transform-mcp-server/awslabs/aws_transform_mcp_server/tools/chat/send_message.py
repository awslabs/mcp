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

"""send_message tool — sends a chat message and polls for the response."""

import uuid
from awslabs.aws_transform_mcp_server.config_store import is_configured
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
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


def _extract_sent_msg(send_result: object) -> object:
    """Extract the message dict from a SendMessage FES response."""
    if isinstance(send_result, dict):
        return send_result.get('message', send_result)
    return send_result


async def send_message(
    ctx: Context,
    workspaceId: str = Field(..., description='Workspace ID (UUID format)'),
    text: str = Field(
        ...,
        description='The message to send to the Transform assistant (max 7000 chars)',
    ),
    jobId: Optional[str] = Field(
        None,
        description='Job ID (UUID) to scope the conversation to a specific job',
    ),
    skipPolling: Optional[bool] = Field(
        None,
        description=(
            'Return immediately without waiting for assistant response. '
            'Use when you have other work to do before checking the reply.'
        ),
    ),
) -> dict:
    """Send a chat message to the AWS Transform assistant and poll for a response.

    Polls up to 60s for the assistant's reply. If no response arrives, the
    result includes the exact poll_message call to continue waiting.

    Do NOT use this to check for responses to previously sent messages — use
    poll_message instead.

    Use skipPolling=true to return immediately if you have other work to do
    before checking the reply.
    """
    resolved_text: Optional[str] = text if isinstance(text, str) else None
    if not resolved_text:
        return error_result(
            'VALIDATION_ERROR',
            'Missing required parameter "text". Provide the message to send.',
            'Pass text="your message here".',
        )

    if not is_configured():
        return not_configured_error()

    _jobId: Optional[str] = jobId if isinstance(jobId, str) else None
    _skipPolling: Optional[bool] = skipPolling if isinstance(skipPolling, bool) else None

    nudge = job_needs_check(_jobId)
    if nudge:
        return error_result('INSTRUCTIONS_REQUIRED', nudge)

    try:
        metadata = build_metadata(workspaceId, _jobId)

        body = {
            'text': resolved_text,
            'idempotencyToken': str(uuid.uuid4()),
            'metadata': metadata,
        }

        send_result = await call_fes('SendMessage', body)
        sent_msg = _extract_sent_msg(send_result)
        sent_message_id = sent_msg.get('messageId') if isinstance(sent_msg, dict) else None

        if not sent_message_id:
            return error_result(
                'MESSAGE_ID_EXTRACTION_FAILED',
                'SendMessage succeeded but messageId could not be extracted from the response.',
                'Use list_resources(resource="messages") to check for a reply.',
            )

        poll_call = build_poll_call(workspaceId, sent_message_id, _jobId)

        if _skipPolling:
            return success_result(
                {
                    'sentMessage': sent_msg,
                    'note': f'Polling skipped. Call {poll_call} to check for the reply.',
                }
            )

        result = await poll_for_response(
            metadata,
            workspaceId,
            sent_message_id,
            max_attempts=30,
        )

        if result['terminal']:
            resp = format_response(result['terminal'])
            if result['is_error']:
                return error_result(
                    'ASSISTANT_ERROR',
                    resp.get('text') or 'The assistant returned an error.',
                    f'sentMessageId={sent_message_id}, workspaceId={workspaceId}',
                )
            return success_result(
                {
                    'sentMessage': sent_msg,
                    'response': resp,
                }
            )

        timeout_data = build_timeout_data(poll_call, 60, result['last_thinking'])
        timeout_data['sentMessage'] = sent_msg
        return success_result(timeout_data)
    except Exception as error:
        return failure_result(error)
