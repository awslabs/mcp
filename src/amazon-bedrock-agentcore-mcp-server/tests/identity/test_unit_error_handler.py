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

"""Unit tests for Identity error handler and response-shaping helper."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.error_handler import (
    handle_identity_error,
    strip_response_metadata,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.identity.models import (
    ErrorResponse,
)
from botocore.exceptions import ClientError


class TestHandleIdentityError:
    """Tests for handle_identity_error."""

    def test_handles_client_error(self):
        """Extracts code, message, and HTTP status from ClientError."""
        error = ClientError(
            {
                'Error': {'Code': 'ValidationException', 'Message': 'bad input'},
                'ResponseMetadata': {'HTTPStatusCode': 400},
            },
            'CreateWorkloadIdentity',
        )
        result = handle_identity_error('CreateWorkloadIdentity', error)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'bad input' in result.message
        assert result.error_type == 'ValidationException'
        assert result.error_code == '400'

    def test_handles_generic_exception(self):
        """Falls back to exception type name for non-ClientError."""
        error = ValueError('something went wrong')
        result = handle_identity_error('SomeOperation', error)
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
        assert 'something went wrong' in result.message
        assert result.error_type == 'ValueError'
        assert result.error_code == ''

    def test_handles_runtime_error(self):
        """Handles RuntimeError with the correct type name."""
        error = RuntimeError('connection lost')
        result = handle_identity_error('GetWorkloadIdentity', error)
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'RuntimeError'
        assert 'connection lost' in result.message

    def test_handles_missing_http_status(self):
        """Falls back to empty error_code when HTTPStatusCode is absent."""
        error = ClientError(
            {
                'Error': {'Code': 'UnknownError', 'Message': 'oops'},
                'ResponseMetadata': {},
            },
            'GetWorkloadIdentity',
        )
        result = handle_identity_error('GetWorkloadIdentity', error)
        assert isinstance(result, ErrorResponse)
        assert result.error_type == 'UnknownError'
        assert result.error_code == ''


class TestStripResponseMetadata:
    """Tests for strip_response_metadata."""

    def test_removes_response_metadata_key(self):
        """ResponseMetadata is stripped from the returned dict."""
        response = {
            'name': 'my-workload',
            'workloadIdentityArn': 'arn:aws:...:workload-identity/my-workload',
            'ResponseMetadata': {'HTTPStatusCode': 200, 'RequestId': 'abc'},
        }
        stripped = strip_response_metadata(response)
        assert 'ResponseMetadata' not in stripped
        assert stripped['name'] == 'my-workload'
        assert 'workloadIdentityArn' in stripped

    def test_no_response_metadata_is_noop(self):
        """Returns a copy unchanged if no ResponseMetadata is present."""
        response = {'name': 'my-workload'}
        stripped = strip_response_metadata(response)
        assert stripped == {'name': 'my-workload'}

    def test_returns_copy_not_mutated_original(self):
        """Does not mutate the original dict."""
        response = {'a': 1, 'ResponseMetadata': {'x': 'y'}}
        strip_response_metadata(response)
        assert 'ResponseMetadata' in response
