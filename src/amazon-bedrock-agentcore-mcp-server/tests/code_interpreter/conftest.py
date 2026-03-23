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

"""Shared test fixtures for Code Interpreter tool tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_ctx():
    """Create a mock MCP Context for tool functions."""
    ctx = MagicMock()
    ctx.error = AsyncMock()
    return ctx


@pytest.fixture
def mock_code_interpreter():
    """Create a mock CodeInterpreter client."""
    client = MagicMock()
    client.session_id = 'test-session-123'
    client.identifier = 'aws.codeinterpreter.v1'
    return client


def make_stream_response(
    stdout: str = '',
    stderr: str = '',
    exit_code: int = 0,
    is_error: bool = False,
    content_text: str = '',
) -> dict:
    """Build a mock invoke_code_interpreter EventStream response.

    Mirrors the real API shape:
    { "stream": [ { "result": { "content": [...], "structuredContent": {...}, "isError": bool } } ] }
    """
    content_blocks = []
    if content_text:
        content_blocks.append({'type': 'text', 'text': content_text})
    return {
        'stream': [
            {
                'result': {
                    'content': content_blocks,
                    'structuredContent': {
                        'stdout': stdout,
                        'stderr': stderr,
                        'exitCode': exit_code,
                    },
                    'isError': is_error,
                },
            },
        ],
    }


@pytest.fixture
def sample_execution_result():
    """Sample SDK response for successful code execution."""
    return make_stream_response(stdout='Hello, World!\n')


@pytest.fixture
def sample_execution_error():
    """Sample SDK response for failed code execution."""
    return make_stream_response(
        stderr="NameError: name 'x' is not defined",
        exit_code=1,
        is_error=True,
    )


@pytest.fixture
def sample_session_response():
    """Sample SDK response for session operations."""
    return {
        'sessionId': 'test-session-123',
        'status': 'READY',
        'name': 'test-session',
        'createdAt': '2026-03-01T00:00:00Z',
    }


@pytest.fixture
def sample_list_sessions_response():
    """Sample SDK response for list sessions (API returns 'items', not 'sessions')."""
    return {
        'items': [
            {'sessionId': 'session-1', 'status': 'READY', 'name': 'first'},
            {'sessionId': 'session-2', 'status': 'TERMINATED', 'name': 'second'},
        ],
        'nextToken': None,
    }
