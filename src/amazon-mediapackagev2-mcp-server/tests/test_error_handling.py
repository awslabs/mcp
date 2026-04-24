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

from awslabs.amazon_mediapackagev2_mcp_server.errors import (
    handle_client_error,
    handle_general_error,
)
from botocore.exceptions import ClientError


def test_handle_client_error_extracts_code_and_message():
    """Verify handle_client_error extracts error code and message."""
    error = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}, 'ResponseMetadata': {}},
        'GetChannel',
    )
    result = handle_client_error(error)
    assert result['error'] == 'ClientError'
    assert result['code'] == 'NotFoundException'
    assert result['message'] == 'Not found'


def test_handle_client_error_missing_fields():
    """Verify handle_client_error handles missing Code/Message gracefully."""
    error = ClientError(
        {'Error': {}, 'ResponseMetadata': {}},
        'GetChannel',
    )
    result = handle_client_error(error)
    assert result['code'] == 'Unknown'
    assert result['message'] == 'No message provided'


def test_handle_general_error_returns_type_and_message():
    """Verify handle_general_error returns error type and message."""
    error = ValueError('something went wrong')
    result = handle_general_error(error)
    assert result['error'] == 'ValueError'
    assert result['message'] == 'something went wrong'
