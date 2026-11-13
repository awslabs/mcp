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

"""Unit tests for the web search error handler."""

from awslabs.amazon_bedrock_agentcore_mcp_server.tools.web_search.error_handler import (
    handle_web_search_error,
)
from botocore.exceptions import ClientError


def _client_error(code, message, status, **extra):
    response = {
        'Error': {'Code': code, 'Message': message},
        'ResponseMetadata': {'HTTPStatusCode': status},
        **extra,
    }
    return ClientError(response, 'InvokeWebSearch')


class TestHandleWebSearchError:
    """Tests for handle_web_search_error."""

    def test_validation_error_includes_reason_and_fields(self):
        """ValidationException messages carry the reason and the invalid fields."""
        error = _client_error(
            'ValidationException',
            'Invalid input',
            400,
            reason='FieldValidationFailed',
            fieldList=[{'name': 'searchQuery', 'message': 'too long'}],
        )

        result = handle_web_search_error('InvokeWebSearch', error)

        assert result.error_type == 'ValidationException'
        assert result.error_code == '400'
        assert 'reason: FieldValidationFailed' in result.message
        assert 'fields: searchQuery' in result.message

    def test_validation_error_without_details(self):
        """A ValidationException with no reason or fields keeps the plain message."""
        result = handle_web_search_error(
            'InvokeWebSearch', _client_error('ValidationException', 'Invalid input', 400)
        )

        assert result.message == 'InvokeWebSearch failed: Invalid input'

    def test_access_denied_names_the_permission(self):
        """AccessDeniedException messages name the required IAM action."""
        result = handle_web_search_error(
            'InvokeWebSearch', _client_error('AccessDeniedException', 'Denied', 403)
        )

        assert result.error_type == 'AccessDeniedException'
        assert 'bedrock-agentcore:InvokeWebSearch' in result.message

    def test_other_client_error(self):
        """Other ClientErrors keep their code, message and status."""
        result = handle_web_search_error(
            'InvokeWebSearch', _client_error('InternalServerException', 'Oops', 500)
        )

        assert result.error_type == 'InternalServerException'
        assert result.error_code == '500'
        assert result.message == 'InvokeWebSearch failed: Oops'

    def test_non_client_error(self):
        """A non-ClientError exception reports its type."""
        result = handle_web_search_error('InvokeWebSearch', RuntimeError('boom'))

        assert result.error_type == 'RuntimeError'
        assert result.message == 'InvokeWebSearch failed: boom'
