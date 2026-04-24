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

"""Shared constants and helpers for chat tools."""

import asyncio
from awslabs.aws_transform_mcp_server.fes_client import call_fes
from awslabs.aws_transform_mcp_server.tool_utils import error_result
from typing import Any, Dict, Optional, TypedDict


NOT_CONFIGURED_CODE = 'NOT_CONFIGURED'
NOT_CONFIGURED_MSG = 'Not connected to AWS Transform.'
NOT_CONFIGURED_ACTION = 'Call configure with authMode "cookie" or "sso".'

POLL_INTERVAL_SECS = 2


class PollResult(TypedDict):
    """Result from poll_for_response."""

    terminal: Optional[Dict]
    is_error: bool
    last_thinking: Optional[Dict]


def not_configured_error() -> Dict[str, Any]:
    """Return a standard not-configured error result."""
    return error_result(NOT_CONFIGURED_CODE, NOT_CONFIGURED_MSG, NOT_CONFIGURED_ACTION)


def build_metadata(workspaceId: str, jobId: Optional[str] = None) -> dict:
    """Build the resourcesOnScreen metadata dict for chat API calls."""
    return {
        'resourcesOnScreen': {
            'workspace': {
                'workspaceId': workspaceId,
                **({'jobs': [{'jobId': jobId, 'focusState': 'ACTIVE'}]} if jobId else {}),
            },
        },
    }


async def poll_for_response(
    metadata: dict,
    workspaceId: str,
    sent_message_id: str,
    max_attempts: int,
) -> PollResult:
    """Poll ListMessages + BatchGetMessage for a terminal response.

    Returns a PollResult with:
    - terminal: the FINAL_RESPONSE or ERROR message dict, or None if timed out
    - is_error: True if terminal is an ERROR message
    - last_thinking: the latest THINKING message seen during polling (only set on timeout)

    Only these messageType values are handled: FINAL_RESPONSE (terminal success),
    ERROR (terminal failure), THINKING (intermediate). Other types are ignored.
    """
    last_thinking: Optional[Dict] = None

    for attempt in range(max_attempts):
        if attempt > 0:
            await asyncio.sleep(POLL_INTERVAL_SECS)

        list_result = await call_fes(
            'ListMessages',
            {
                'metadata': metadata,
                'maxResults': 10,
            },
        )
        message_ids = list_result.get('messageIds', []) if isinstance(list_result, dict) else []
        if not message_ids:
            continue

        batch_result = await call_fes(
            'BatchGetMessage',
            {
                'messageIds': message_ids,
                'workspaceId': workspaceId,
            },
        )
        messages = batch_result.get('messages', []) if isinstance(batch_result, dict) else []

        responses = [
            m
            for m in messages
            if isinstance(m, dict)
            and m.get('parentMessageId') == sent_message_id
            and m.get('messageOrigin') == 'SYSTEM'
        ]

        for m in responses:
            pi = m.get('processingInfo')
            if not isinstance(pi, dict):
                continue
            msg_type = pi.get('messageType')
            if msg_type == 'FINAL_RESPONSE':
                return PollResult(terminal=m, is_error=False, last_thinking=None)
            if msg_type == 'ERROR':
                return PollResult(terminal=m, is_error=True, last_thinking=None)
            if msg_type == 'THINKING':
                last_thinking = m

    return PollResult(terminal=None, is_error=False, last_thinking=last_thinking)


def format_response(msg: dict) -> dict:
    """Extract the standard response fields from a terminal message."""
    return {
        'messageId': msg.get('messageId'),
        'text': msg.get('text'),
        'messageType': msg.get('processingInfo', {}).get('messageType'),
        'interactions': msg.get('interactions'),
        'createdAt': msg.get('createdAt'),
    }


def build_poll_call(
    workspaceId: str,
    sentMessageId: str,
    jobId: Optional[str] = None,
) -> str:
    """Build the exact poll_message(...) call string for timeout notes."""
    call = f'poll_message(workspaceId="{workspaceId}", sentMessageId="{sentMessageId}"'
    if jobId:
        call += f', jobId="{jobId}"'
    return call + ')'


def build_timeout_data(
    poll_call: str,
    timeout_secs: int,
    last_thinking: Optional[Dict],
) -> dict:
    """Build the standard timeout response dict with retry guidance."""
    data: dict = {
        'response': None,
        'note': (
            f'No final response within {timeout_secs}s. Call {poll_call} to keep '
            f'waiting. Stop after 3 retries (~3 min total) if no response.'
        ),
    }
    if last_thinking:
        data['lastThinkingMessage'] = {
            'messageId': last_thinking.get('messageId'),
            'text': last_thinking.get('text'),
            'messageType': last_thinking.get('processingInfo', {}).get('messageType'),
        }
    return data
