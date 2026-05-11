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

import time
import uuid as _uuid
from awslabs.aws_transform_mcp_server.config_store import is_fes_available
from awslabs.aws_transform_mcp_server.guidance_nudge import job_needs_check
from awslabs.aws_transform_mcp_server.tool_utils import (
    error_result,
    failure_result,
    success_result,
)
from awslabs.aws_transform_mcp_server.tools.chat._common import (
    build_metadata,
    build_timeout_data,
    format_response,
    not_configured_error,
    poll_for_response,
)
from awslabs.aws_transform_mcp_server.transform_api_client import call_transform_api
from awslabs.aws_transform_mcp_server.transform_api_models import SendMessageRequest
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Optional


async def send_message(
    ctx: Context,
    workspaceId: Annotated[str, Field(description='Workspace ID (UUID format)')],
    text: Annotated[
        str,
        Field(
            description='The message to send to the Transform assistant (max 7000 chars)',
        ),
    ],
    jobId: Annotated[
        Optional[str],
        Field(
            description='Job ID (UUID) to scope the conversation to a specific job',
        ),
    ] = None,
    skipPolling: Annotated[
        Optional[bool],
        Field(
            description=(
                'Return immediately without waiting for assistant response. '
                'Use when you have other work to do before checking the reply.'
            ),
        ),
    ] = None,
) -> dict:
    """Send a chat message to the AWS Transform assistant and poll for a response.

    Polls up to 60s for the assistant's reply. On timeout the result includes
    sentMessageId and guidance on how to check for the reply.
    """
    resolved_text: Optional[str] = text if isinstance(text, str) else None
    if not resolved_text:
        return error_result(
            'VALIDATION_ERROR',
            'Missing required parameter "text". Provide the message to send.',
            'Pass text="your message here".',
        )

    if not is_fes_available():
        return not_configured_error()

    nudge = job_needs_check(jobId)
    if nudge:
        return error_result('INSTRUCTIONS_REQUIRED', nudge)

    try:
        metadata = build_metadata(workspaceId, jobId)
        start_timestamp = time.time()

        send_result = await call_transform_api(
            'SendMessage',
            SendMessageRequest(
                text=resolved_text,
                idempotencyToken=str(_uuid.uuid4()),
                metadata=metadata,
            ),
        )
        sent_msg = (
            send_result.get('message', send_result)
            if isinstance(send_result, dict)
            else send_result
        )
        sent_message_id = sent_msg.get('messageId') if isinstance(sent_msg, dict) else None

        if not sent_message_id:
            return error_result(
                'MESSAGE_ID_EXTRACTION_FAILED',
                'SendMessage succeeded but messageId could not be extracted from the response.',
                'Use list_resources(resource="messages") to check for a reply.',
            )

        if skipPolling:
            return success_result(
                {
                    'sentMessage': sent_msg,
                    'note': 'Polling skipped. Call send_message again to follow up.',
                }
            )

        result = await poll_for_response(
            metadata,
            workspaceId,
            sent_message_id,
            max_attempts=30,
            start_timestamp=start_timestamp,
        )

        if result['terminal']:
            resp = format_response(result['terminal'])
            if result['is_error']:
                return error_result(
                    'ASSISTANT_ERROR',
                    resp.get('text') or 'The assistant returned an error.',
                    f'sentMessageId={sent_message_id}, workspaceId={workspaceId}',
                )
            return success_result({'sentMessage': sent_msg, 'response': resp})

        timeout_data = build_timeout_data(
            60, result['last_thinking'], workspaceId, sent_message_id, jobId
        )
        timeout_data['sentMessage'] = sent_msg
        return success_result(timeout_data)
    except Exception as error:
        return failure_result(error)
