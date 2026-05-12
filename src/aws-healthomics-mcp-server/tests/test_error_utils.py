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

"""Tests for error handling utilities."""

import pytest
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_handle_tool_error():
    """Test handle_tool_error returns error dict and calls ctx.error."""
    mock_ctx = AsyncMock()
    error = ValueError('Test error message')
    operation = 'Test operation'

    result = await handle_tool_error(mock_ctx, error, operation)

    # Verify ctx.error was called
    mock_ctx.error.assert_called_once()
    error_message = mock_ctx.error.call_args[0][0]
    assert operation in error_message
    assert 'Test error message' in error_message

    # Verify error dict is returned
    assert 'error' in result
    assert operation in result['error']
    assert 'Test error message' in result['error']


@pytest.mark.asyncio
async def test_handle_tool_error_with_exception_details():
    """Test handle_tool_error preserves exception details."""
    mock_ctx = AsyncMock()
    error = RuntimeError('Detailed error information')
    operation = 'AWS API call failed'

    result = await handle_tool_error(mock_ctx, error, operation)

    # Verify full error details are preserved
    assert 'error' in result
    assert 'AWS API call failed' in result['error']
    assert 'Detailed error information' in result['error']
    mock_ctx.error.assert_called_once()
