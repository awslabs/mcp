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

"""Tests for error_handler.py — ClientError and generic exception handling."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.runtime.error_handler import (
    handle_runtime_error,
)
from botocore.exceptions import ClientError


class TestHandleRuntimeError:
    """Tests for handle_runtime_error."""

    def test_client_error_extracts_fields(self):
        """ClientError response extracts code, message, and HTTP status."""
        error = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'Bad name'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateAgentRuntime',
        )
        result = handle_runtime_error('CreateAgentRuntime', error)
        assert result.status == 'error'
        assert result.error_type == 'ValidationException'
        assert 'Bad name' in result.message
        assert result.error_code == '400'

    def test_client_error_missing_fields(self):
        """ClientError with minimal response still returns ErrorResponse."""
        error = ClientError(
            {'Error': {}, 'ResponseMetadata': {}},
            'GetAgentRuntime',
        )
        result = handle_runtime_error('GetAgentRuntime', error)
        assert result.status == 'error'
        assert result.error_type == 'Unknown'
        assert result.error_code == ''

    def test_generic_exception(self):
        """Non-ClientError exception uses exception class name."""
        error = RuntimeError('Something broke')
        result = handle_runtime_error('InvokeAgentRuntime', error)
        assert result.status == 'error'
        assert result.error_type == 'RuntimeError'
        assert 'Something broke' in result.message
        assert result.error_code == ''

    def test_value_error(self):
        """ValueError is handled as a generic exception."""
        error = ValueError('invalid param')
        result = handle_runtime_error('StopSession', error)
        assert result.error_type == 'ValueError'
        assert 'invalid param' in result.message
