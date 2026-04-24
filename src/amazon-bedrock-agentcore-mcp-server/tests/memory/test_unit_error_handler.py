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

"""Unit tests for Memory error handler."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.error_handler import (
    handle_memory_error,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    ErrorResponse,
)
from botocore.exceptions import ClientError


class TestHandleMemoryError:
    """Tests for handle_memory_error."""

    def test_handles_client_error(self):
        """Extracts code, message, HTTP status from ClientError."""
        error = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad input'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateMemory',
        )
        result = handle_memory_error('CreateMemory', error)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'bad input' in result.message
        assert result.error_type == 'ValidationException'
        assert result.error_code == '400'

    def test_handles_generic_exception(self):
        """Falls back to exception type name for non-ClientError."""
        error = ValueError('something went wrong')
        result = handle_memory_error('SomeOperation', error)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'something went wrong' in result.message
        assert result.error_type == 'ValueError'
        assert result.error_code == ''

    def test_handles_runtime_error(self):
        """Handles RuntimeError with correct type name."""
        error = RuntimeError('connection lost')
        result = handle_memory_error('GetMemory', error)
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'RuntimeError'
        assert 'connection lost' in result.message
