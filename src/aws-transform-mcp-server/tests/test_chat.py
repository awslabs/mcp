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

"""Tests for chat tools (send_message)."""
# ruff: noqa: D101, D102, D103

import json
import pytest
from unittest.mock import AsyncMock, patch


_SEND_MOD = 'awslabs.aws_transform_mcp_server.tools.chat.send_message'
_COMMON_MOD = 'awslabs.aws_transform_mcp_server.tools.chat._common'


@pytest.fixture
def ctx():
    """Return a mock MCP context."""
    return AsyncMock()


def _parse(result: dict) -> dict:
    """Extract the parsed JSON payload from an MCP result envelope."""
    return json.loads(result['content'][0]['text'])


# ── send_message: Parameter validation ─────────────────────────────────


class TestSendValidation:
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    async def test_text_sends_to_fes(self, _mock_configured, mock_fes, ctx):
        """Text param is forwarded to FES SendMessage."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_fes.return_value = {'message': {'messageId': 'msg-1'}}
        result = await send_message(ctx, workspaceId='ws-1', text='hello', skipPolling=True)
        parsed = _parse(result)
        assert parsed['success'] is True
        call_body = mock_fes.call_args[0][1].model_dump(by_alias=True, exclude_none=True)
        assert call_body['text'] == 'hello'

    async def test_missing_text_fails(self, ctx):
        """Missing text should fail with TypeError since text is a required parameter."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        with pytest.raises(TypeError, match='text'):
            await send_message(ctx, workspaceId='ws-1')  # pyright: ignore[reportCallIssue]


# ── send_message: Skip polling ─────────────────────────────────────────


class TestSkipPolling:
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    async def test_skip_polling(self, _mock_configured, mock_fes, ctx):
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_fes.return_value = {'message': {'messageId': 'msg-1'}}
        result = await send_message(ctx, workspaceId='ws-1', text='hi', skipPolling=True)
        parsed = _parse(result)

        assert parsed['success'] is True
        assert mock_fes.call_count == 1
        assert mock_fes.call_args[0][0] == 'SendMessage'
        assert 'Polling skipped' in parsed['data']['note']


# ── send_message: Polling finds response ───────────────────────────────


class TestPollingFindsResponse:
    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_finds_response_on_second_poll(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-sent'}}
        mock_poll_fes.side_effect = [
            {'messageIds': ['msg-sent', 'msg-resp']},
            {
                'messages': [
                    {
                        'messageId': 'msg-resp',
                        'parentMessageId': 'msg-sent',
                        'messageOrigin': 'SYSTEM',
                        'processingInfo': {'messageType': 'THINKING'},
                        'text': 'thinking...',
                    }
                ]
            },
            {'messageIds': ['msg-sent', 'msg-resp', 'msg-final']},
            {
                'messages': [
                    {
                        'messageId': 'msg-final',
                        'parentMessageId': 'msg-sent',
                        'messageOrigin': 'SYSTEM',
                        'processingInfo': {'messageType': 'FINAL_RESPONSE'},
                        'text': 'Done!',
                        'interactions': [{'type': 'click'}],
                        'createdAt': '2025-01-01T00:00:00Z',
                    }
                ]
            },
        ]

        result = await send_message(ctx, workspaceId='ws-1', text='do something')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['response']['messageId'] == 'msg-final'
        assert parsed['data']['response']['text'] == 'Done!'
        assert parsed['data']['response']['messageType'] == 'FINAL_RESPONSE'
        assert parsed['data']['sentMessage']['messageId'] == 'msg-sent'
        # First iteration has no sleep, second iteration sleeps once
        assert mock_sleep.call_count == 1


# ── send_message: Polling timeout ──────────────────────────────────────


class TestPollingTimeout:
    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_timeout_returns_none_response(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-sent'}}
        mock_poll_fes.return_value = {'messageIds': []}

        result = await send_message(ctx, workspaceId='ws-1', text='ping')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['response'] is None
        assert 'note' in parsed['data']
        assert 'list_resources' in parsed['data']['note']
        # First iteration has no sleep, remaining 29 do
        assert mock_sleep.call_count == 29


# ── send_message: Timeout with THINKING message ──────────────────────


class TestSendTimeoutWithThinking:
    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_timeout_includes_last_thinking_message(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        """When polling times out but a THINKING message was seen, include it."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-sent'}}
        mock_poll_fes.side_effect = [
            {'messageIds': ['msg-sent', 'msg-think']},
            {
                'messages': [
                    {
                        'messageId': 'msg-think',
                        'parentMessageId': 'msg-sent',
                        'messageOrigin': 'SYSTEM',
                        'processingInfo': {'messageType': 'THINKING'},
                        'text': 'Searching AWS docs...',
                    }
                ]
            },
        ] + [{'messageIds': []}] * 29  # remaining 29 polls (1 used + 29 = 30)

        result = await send_message(ctx, workspaceId='ws-1', text='explain ECS')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['response'] is None
        assert 'lastThinkingMessage' in parsed['data']
        assert parsed['data']['lastThinkingMessage']['text'] == 'Searching AWS docs...'
        assert parsed['data']['lastThinkingMessage']['messageType'] == 'THINKING'
        assert parsed['data']['lastThinkingMessage']['messageId'] == 'msg-think'

    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_timeout_no_thinking_message(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        """When polling times out with no THINKING message, lastThinkingMessage is absent."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-sent'}}
        mock_poll_fes.return_value = {'messageIds': []}

        result = await send_message(ctx, workspaceId='ws-1', text='hello')
        parsed = _parse(result)

        assert parsed['success'] is True
        assert parsed['data']['response'] is None
        assert 'lastThinkingMessage' not in parsed['data']

    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_timeout_keeps_latest_thinking(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        """When multiple THINKING messages arrive, keep the latest one."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-sent'}}
        mock_poll_fes.side_effect = [
            {'messageIds': ['msg-think1']},
            {
                'messages': [
                    {
                        'messageId': 'msg-think1',
                        'parentMessageId': 'msg-sent',
                        'messageOrigin': 'SYSTEM',
                        'processingInfo': {'messageType': 'THINKING'},
                        'text': 'First thinking...',
                    }
                ]
            },
            {'messageIds': ['msg-think1', 'msg-think2']},
            {
                'messages': [
                    {
                        'messageId': 'msg-think1',
                        'parentMessageId': 'msg-sent',
                        'messageOrigin': 'SYSTEM',
                        'processingInfo': {'messageType': 'THINKING'},
                        'text': 'First thinking...',
                    },
                    {
                        'messageId': 'msg-think2',
                        'parentMessageId': 'msg-sent',
                        'messageOrigin': 'SYSTEM',
                        'processingInfo': {'messageType': 'THINKING'},
                        'text': 'Still working...',
                    },
                ]
            },
        ] + [{'messageIds': []}] * 28  # remaining 28 polls (2 used + 28 = 30)

        result = await send_message(ctx, workspaceId='ws-1', text='explain EKS')
        parsed = _parse(result)

        assert parsed['data']['lastThinkingMessage']['messageId'] == 'msg-think2'
        assert parsed['data']['lastThinkingMessage']['text'] == 'Still working...'


# ── send_message: jobId forwarding ────────────────────────────────────


class TestSendJobId:
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    async def test_job_id_in_metadata(self, _mock_configured, mock_fes, ctx):
        """JobId should be included in the metadata sent to FES."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_fes.return_value = {'message': {'messageId': 'msg-1'}}
        await send_message(ctx, workspaceId='ws-1', text='hi', jobId='job-1', skipPolling=True)
        call_body = mock_fes.call_args[0][1].model_dump(by_alias=True, exclude_none=True)
        jobs = call_body['metadata']['resourcesOnScreen']['workspace']['jobs']
        assert jobs == [{'jobId': 'job-1', 'focusState': 'ACTIVE'}]

    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    async def test_no_job_id_omits_jobs(self, _mock_configured, mock_fes, ctx):
        """Without jobId, metadata should not have a jobs key."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_fes.return_value = {'message': {'messageId': 'msg-1'}}
        await send_message(ctx, workspaceId='ws-1', text='hi', skipPolling=True)
        call_body = mock_fes.call_args[0][1].model_dump(by_alias=True, exclude_none=True)
        workspace = call_body['metadata']['resourcesOnScreen']['workspace']
        assert 'jobs' not in workspace


# ── send_message: timeout note format ─────────────────────────────────


class TestSendTimeoutNote:
    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_timeout_note_includes_send_message_call(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        """Timeout note should contain list_resources guidance with workspace and job IDs."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-abc'}}
        mock_poll_fes.return_value = {'messageIds': []}

        result = await send_message(ctx, workspaceId='ws-1', text='hi', jobId='job-1')
        parsed = _parse(result)
        note = parsed['data']['note']

        assert 'list_resources' in note
        assert 'workspaceId="ws-1"' in note
        assert 'jobId="job-1"' in note
        assert 'parentMessageId="msg-abc"' in note

    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_timeout_note_omits_job_id_when_absent(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        """Timeout note should not include jobId when it was not provided."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-abc'}}
        mock_poll_fes.return_value = {'messageIds': []}

        result = await send_message(ctx, workspaceId='ws-1', text='hi')
        parsed = _parse(result)
        note = parsed['data']['note']

        assert 'list_resources' in note
        assert 'jobId' not in note


# ── send_message: FES error handling ──────────────────────────────────


class TestSendFesError:
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    async def test_fes_exception_returns_failure(self, _mock_configured, mock_fes, ctx):
        """FES exceptions should be caught and returned as failure results."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_fes.side_effect = Exception('FES is down')
        result = await send_message(ctx, workspaceId='ws-1', text='hi', skipPolling=True)
        parsed = _parse(result)

        assert parsed['success'] is False


# ── send_message: Not configured ───────────────────────────────────────


class TestNotConfigured:
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=False)
    async def test_not_configured(self, _mock_configured, ctx):
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        result = await send_message(ctx, workspaceId='ws-1', text='hello')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'NOT_CONFIGURED'


# ── send_message: ERROR messageType ───────────────────────────────────


class TestSendErrorMessageType:
    @patch(f'{_COMMON_MOD}.asyncio.sleep', new_callable=AsyncMock)
    @patch(f'{_COMMON_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_error_message_returns_assistant_error(
        self, mock_send_fes, _mock_configured, mock_poll_fes, mock_sleep, ctx
    ):
        """ERROR messageType should return error_result with ASSISTANT_ERROR."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_send_fes.return_value = {'message': {'messageId': 'msg-sent'}}
        mock_poll_fes.side_effect = [
            {'messageIds': ['msg-err']},
            {
                'messages': [
                    {
                        'messageId': 'msg-err',
                        'parentMessageId': 'msg-sent',
                        'messageOrigin': 'SYSTEM',
                        'processingInfo': {'messageType': 'ERROR'},
                        'text': 'Something went wrong.',
                    }
                ]
            },
        ]

        result = await send_message(ctx, workspaceId='ws-1', text='hello')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'ASSISTANT_ERROR'
        assert 'Something went wrong' in parsed['error']['message']
        assert 'sentMessageId=msg-sent' in parsed['error']['suggestedAction']
        assert mock_sleep.call_count == 0


# ── send_message: messageId extraction failure ────────────────────────


class TestSendMessageIdExtraction:
    @patch(f'{_SEND_MOD}.call_transform_api', new_callable=AsyncMock)
    @patch(f'{_SEND_MOD}.is_fes_available', return_value=True)
    async def test_missing_message_id_returns_error(self, _mock_configured, mock_fes, ctx):
        """When messageId cannot be extracted, return error_result."""
        from awslabs.aws_transform_mcp_server.tools.chat.send_message import send_message

        mock_fes.return_value = {'unexpected': 'shape'}
        result = await send_message(ctx, workspaceId='ws-1', text='hi')
        parsed = _parse(result)

        assert parsed['success'] is False
        assert parsed['error']['code'] == 'MESSAGE_ID_EXTRACTION_FAILED'
        assert 'list_resources' in parsed['error']['suggestedAction']
