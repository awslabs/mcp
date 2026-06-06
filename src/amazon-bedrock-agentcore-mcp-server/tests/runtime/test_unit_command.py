# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for invoke_agent_runtime_command and the EventStream parser."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.invocation import (
    InvocationTools,
    _parse_command_event_stream,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.models import (
    ErrorResponse,
    InvokeCommandResponse,
)
from botocore.exceptions import ClientError


def _client_error(code='ValidationException', message='bad', status=400):
    return ClientError(
        {
            'Error': {'Code': code, 'Message': message},
            'ResponseMetadata': {'HTTPStatusCode': status},
        },
        'TestOp',
    )


class TestParseCommandEventStream:
    """EventStream parsing for InvokeAgentRuntimeCommand."""

    def test_none_stream(self):
        """None stream returns empty defaults without error."""
        out = _parse_command_event_stream(None)
        assert out['stdout'] == ''
        assert out['stderr'] == ''
        assert out['exit_code'] is None
        assert out['error'] is None

    def test_normal_flow(self):
        """stdout/stderr deltas concatenate; contentStop yields exitCode and status."""
        events = [
            {'chunk': {'contentStart': {}}},
            {'chunk': {'contentDelta': {'stdout': 'hello\n'}}},
            {'chunk': {'contentDelta': {'stdout': 'world\n'}}},
            {'chunk': {'contentDelta': {'stderr': 'oops\n'}}},
            {'chunk': {'contentStop': {'exitCode': 0, 'status': 'COMPLETED'}}},
        ]
        out = _parse_command_event_stream(iter(events))
        assert out['stdout'] == 'hello\nworld\n'
        assert out['stderr'] == 'oops\n'
        assert out['exit_code'] == 0
        assert out['command_status'] == 'COMPLETED'
        assert out['error'] is None

    def test_stream_typed_exception(self):
        """Typed exception member in stream is captured and stops parsing."""
        events = [
            {'chunk': {'contentDelta': {'stdout': 'partial\n'}}},
            {'validationException': {'message': 'bad timeout', 'httpStatusCode': 400}},
            {'chunk': {'contentDelta': {'stdout': 'after-error'}}},
        ]
        out = _parse_command_event_stream(iter(events))
        assert out['error'] is not None
        assert out['error']['type'] == 'validationException'
        assert out['stdout'] == 'partial\n'

    def test_byte_payload(self):
        """Byte stdout chunks are decoded to str."""
        events = [{'chunk': {'contentDelta': {'stdout': b'bin\n'}}}]
        out = _parse_command_event_stream(iter(events))
        assert out['stdout'] == 'bin\n'

    def test_non_utf8_payload(self):
        """Non-UTF8 bytes are replaced rather than crashing."""
        events = [{'chunk': {'contentDelta': {'stdout': b'\x80\x81'}}}]
        out = _parse_command_event_stream(iter(events))
        assert '�' in out['stdout']


class TestInvokeAgentRuntimeCommand:
    """Tests for the HTTP command tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, data_factory, mock_data_client):
        """Happy path: response fields populate InvokeCommandResponse and request kwargs match."""
        mock_data_client.invoke_agent_runtime_command.return_value = {
            'runtimeSessionId': 'sess-1',
            'contentType': 'application/vnd.amazon.eventstream',
            'statusCode': 200,
            'stream': iter(
                [
                    {'chunk': {'contentDelta': {'stdout': 'hi\n'}}},
                    {'chunk': {'contentStop': {'exitCode': 0, 'status': 'COMPLETED'}}},
                ]
            ),
        }
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime_command(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            command='echo hi',
            timeout=5,
            runtime_session_id='sess-1',
        )
        assert isinstance(result, InvokeCommandResponse)
        assert result.runtime_session_id == 'sess-1'
        assert result.stdout == 'hi\n'
        assert result.exit_code == 0
        assert result.command_status == 'COMPLETED'

        kwargs = mock_data_client.invoke_agent_runtime_command.call_args.kwargs
        assert kwargs['agentRuntimeArn'] == 'arn:test'
        assert kwargs['qualifier'] == 'DEFAULT'
        assert kwargs['body'] == {'command': 'echo hi', 'timeout': 5}
        assert kwargs['runtimeSessionId'] == 'sess-1'

    @pytest.mark.asyncio
    async def test_timeout_forwarded_in_body(self, mock_ctx, data_factory, mock_data_client):
        """Timeout parameter is forwarded into the request body."""
        mock_data_client.invoke_agent_runtime_command.return_value = {
            'runtimeSessionId': 'sess',
            'stream': iter([]),
        }
        tools = InvocationTools(data_factory)
        await tools.invoke_agent_runtime_command(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            command='sleep 1',
            timeout=120,
        )
        kwargs = mock_data_client.invoke_agent_runtime_command.call_args.kwargs
        assert kwargs['body'] == {'command': 'sleep 1', 'timeout': 120}

    @pytest.mark.asyncio
    async def test_propagates_non_200_status_code(
        self, mock_ctx, data_factory, mock_data_client
    ):
        """Non-200 statusCode from response envelope surfaces on http_status_code."""
        mock_data_client.invoke_agent_runtime_command.return_value = {
            'runtimeSessionId': 'sess',
            'statusCode': 207,
            'stream': iter(
                [{'chunk': {'contentStop': {'exitCode': 1, 'status': 'FAILED'}}}]
            ),
        }
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime_command(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            command='false',
        )
        assert isinstance(result, InvokeCommandResponse)
        assert result.http_status_code == 207
        assert result.exit_code == 1
        assert result.command_status == 'FAILED'

    @pytest.mark.asyncio
    async def test_omits_session_when_none(self, mock_ctx, data_factory, mock_data_client):
        """runtime_session_id=None is omitted from kwargs to let the server auto-generate."""
        mock_data_client.invoke_agent_runtime_command.return_value = {
            'runtimeSessionId': 'auto',
            'stream': iter([]),
        }
        tools = InvocationTools(data_factory)
        await tools.invoke_agent_runtime_command(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            command='echo hi',
        )
        kwargs = mock_data_client.invoke_agent_runtime_command.call_args.kwargs
        assert 'runtimeSessionId' not in kwargs

    @pytest.mark.asyncio
    async def test_typed_exception_in_stream(self, mock_ctx, data_factory, mock_data_client):
        """Typed exception in stream becomes an ErrorResponse."""
        mock_data_client.invoke_agent_runtime_command.return_value = {
            'runtimeSessionId': 'sess',
            'stream': iter(
                [
                    {'validationException': {'message': 'bad', 'httpStatusCode': 400}},
                ]
            ),
        }
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime_command(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            command='',
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'validationException'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, data_factory, mock_data_client):
        """boto3 ClientError is caught and returned as ErrorResponse."""
        mock_data_client.invoke_agent_runtime_command.side_effect = _client_error(
            'AccessDeniedException', 'Forbidden', 403
        )
        tools = InvocationTools(data_factory)
        result = await tools.invoke_agent_runtime_command(
            ctx=mock_ctx,
            agent_runtime_arn='arn:test',
            command='ls',
        )
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'AccessDeniedException'
