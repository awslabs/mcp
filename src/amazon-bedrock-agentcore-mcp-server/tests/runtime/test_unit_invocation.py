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

"""Tests for invocation.py — invoke and stop session."""

import io
import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.invocation import (
    InvocationTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.models import (
    ErrorResponse,
    InvokeRuntimeResponse,
    StopSessionResponse,
)
from botocore.exceptions import ClientError


def _client_error(code='ValidationException', message='bad request', status=400):
    """Create a ClientError for testing."""
    return ClientError(
        {
            'Error': {'Code': code, 'Message': message},
            'ResponseMetadata': {'HTTPStatusCode': status},
        },
        'TestOp',
    )


class TestInvokeAgentRuntime:
    """Tests for invoke_agent_runtime."""

    @pytest.mark.asyncio
    async def test_success_json_response(self, mock_ctx, data_factory, mock_data_client):
        """JSON response body is read and returned."""
        mock_data_client.invoke_agent_runtime.return_value = {
            'runtimeSessionId': 'sess-123',
            'contentType': 'application/json',
            'response': io.BytesIO(b'{"result":"hello"}'),
        }
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{"prompt":"hi"}',
            runtime_session_id='sess-123',
        )
        assert isinstance(result, InvokeRuntimeResponse)
        assert result.runtime_session_id == 'sess-123'
        assert 'hello' in result.response_body

    @pytest.mark.asyncio
    async def test_success_streaming_bytes(self, mock_ctx, data_factory, mock_data_client):
        """Streaming byte chunks are concatenated."""
        mock_data_client.invoke_agent_runtime.return_value = {
            'runtimeSessionId': 'sess-456',
            'contentType': 'text/event-stream',
            'response': [b'chunk1', b'chunk2'],
        }
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{"prompt":"stream"}',
        )
        assert isinstance(result, InvokeRuntimeResponse)
        assert result.response_body == 'chunk1chunk2'

    @pytest.mark.asyncio
    async def test_success_streaming_strings(self, mock_ctx, data_factory, mock_data_client):
        """Streaming non-bytes chunks are converted via str()."""
        mock_data_client.invoke_agent_runtime.return_value = {
            'runtimeSessionId': 'sess-789',
            'contentType': 'text/event-stream',
            'response': ['text1', 'text2'],
        }
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{}',
        )
        assert isinstance(result, InvokeRuntimeResponse)
        assert result.response_body == 'text1text2'

    @pytest.mark.asyncio
    async def test_no_response_key(self, mock_ctx, data_factory, mock_data_client):
        """Response without 'response' key returns empty body."""
        mock_data_client.invoke_agent_runtime.return_value = {
            'runtimeSessionId': 'sess-000',
        }
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{}',
        )
        assert isinstance(result, InvokeRuntimeResponse)
        assert result.response_body == ''

    @pytest.mark.asyncio
    async def test_access_denied(self, mock_ctx, data_factory, mock_data_client):
        """AccessDeniedException is returned as ErrorResponse."""
        mock_data_client.invoke_agent_runtime.side_effect = _client_error(
            'AccessDeniedException',
            'Forbidden',
            403,
        )
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{}',
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'AccessDeniedException'

    @pytest.mark.asyncio
    async def test_generic_exception(self, mock_ctx, data_factory, mock_data_client):
        """Non-ClientError exception is returned as ErrorResponse."""
        mock_data_client.invoke_agent_runtime.side_effect = RuntimeError('boom')
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{}',
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'RuntimeError'

    @pytest.mark.asyncio
    async def test_default_qualifier(self, mock_ctx, data_factory, mock_data_client):
        """Qualifier defaults to DEFAULT."""
        mock_data_client.invoke_agent_runtime.return_value = {
            'response': io.BytesIO(b'ok'),
        }
        tools = InvocationTools(data_factory)
        await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{}',
        )
        call_kwargs = mock_data_client.invoke_agent_runtime.call_args[1]
        assert call_kwargs['qualifier'] == 'DEFAULT'

    @pytest.mark.asyncio
    async def test_payload_encoding(self, mock_ctx, data_factory, mock_data_client):
        """Payload string is encoded to bytes."""
        mock_data_client.invoke_agent_runtime.return_value = {
            'response': io.BytesIO(b'ok'),
        }
        tools = InvocationTools(data_factory)
        await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{"prompt":"hello"}',
        )
        call_kwargs = mock_data_client.invoke_agent_runtime.call_args[1]
        assert call_kwargs['payload'] == b'{"prompt":"hello"}'

    @pytest.mark.asyncio
    async def test_session_id_omitted(self, mock_ctx, data_factory, mock_data_client):
        """Omitting session_id does not include it in kwargs."""
        mock_data_client.invoke_agent_runtime.return_value = {
            'response': io.BytesIO(b'ok'),
        }
        tools = InvocationTools(data_factory)
        await tools.invoke_agent_runtime(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            payload='{}',
        )
        call_kwargs = mock_data_client.invoke_agent_runtime.call_args[1]
        assert 'runtimeSessionId' not in call_kwargs


class TestStopRuntimeSession:
    """Tests for stop_runtime_session."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, data_factory, mock_data_client):
        """Successful stop returns session ID in message."""
        mock_data_client.stop_runtime_session.return_value = {
            'runtimeSessionId': 'sess-123',
        }
        tools = InvocationTools(data_factory)
        result = await tools.stop_runtime_session(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            runtime_session_id='sess-123',
        )
        assert isinstance(result, StopSessionResponse)
        assert 'sess-123' in result.message

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, data_factory, mock_data_client):
        """ResourceNotFoundException is returned as ErrorResponse."""
        mock_data_client.stop_runtime_session.side_effect = _client_error(
            'ResourceNotFoundException',
            'Session not found',
            404,
        )
        tools = InvocationTools(data_factory)
        result = await tools.stop_runtime_session(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            runtime_session_id='gone',
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_code == '404'

    @pytest.mark.asyncio
    async def test_passes_qualifier(self, mock_ctx, data_factory, mock_data_client):
        """Custom qualifier is forwarded to the API."""
        mock_data_client.stop_runtime_session.return_value = {}
        tools = InvocationTools(data_factory)
        await tools.stop_runtime_session(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            runtime_session_id='sess-1',
            qualifier='staging',
        )
        call_kwargs = mock_data_client.stop_runtime_session.call_args[1]
        assert call_kwargs['qualifier'] == 'staging'

    @pytest.mark.asyncio
    async def test_generic_exception(self, mock_ctx, data_factory, mock_data_client):
        """Non-ClientError exception is returned as ErrorResponse."""
        mock_data_client.stop_runtime_session.side_effect = ValueError('bad')
        tools = InvocationTools(data_factory)
        result = await tools.stop_runtime_session(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            runtime_session_id='sess-1',
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ValueError'
