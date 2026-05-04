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

"""Unit tests for Gateway error handler."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.error_handler import (
    handle_gateway_error,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.gateway.models import (
    ErrorResponse,
)
from botocore.exceptions import ClientError


class TestHandleGatewayError:
    """Tests for handle_gateway_error."""

    def test_handles_client_error(self):
        """Extracts code, message, HTTP status from ClientError."""
        error = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad input'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateGateway',
        )
        result = handle_gateway_error('CreateGateway', error)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'bad input' in result.message
        assert result.error_type == 'ValidationException'
        assert result.error_code == '400'

    def test_handles_conflict_error(self):
        """Extracts 409 conflict errors correctly."""
        error = ClientError(
            {
                'Error': {
                    'Code': 'ConflictException',
                    'Message': 'gateway has targets',
                },
                'ResponseMetadata': {'HTTPStatusCode': 409},
            },
            'DeleteGateway',
        )
        result = handle_gateway_error('DeleteGateway', error)
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'ConflictException'
        assert result.error_code == '409'

    def test_handles_generic_exception(self):
        """Falls back to exception type name for non-ClientError."""
        error = ValueError('something went wrong')
        result = handle_gateway_error('SomeOperation', error)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'something went wrong' in result.message
        assert result.error_type == 'ValueError'
        assert result.error_code == ''

    def test_handles_runtime_error(self):
        """Handles RuntimeError with correct type name."""
        error = RuntimeError('connection lost')
        result = handle_gateway_error('GetGateway', error)
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'RuntimeError'
        assert 'connection lost' in result.message
