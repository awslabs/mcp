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

"""Tests for tool error result helpers."""

from awslabs.aws_dataprocessing_mcp_server.utils.error_helper import create_error_result
from botocore.exceptions import ClientError


def test_create_error_result_with_client_error():
    """ClientError details are exposed without changing the human-readable text."""
    exception = ClientError(
        {
            'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'},
            'ResponseMetadata': {'HTTPStatusCode': 429, 'RequestId': 'request-123'},
        },
        'StartQueryExecution',
    )

    result = create_error_result(exception, 'Error in operation: original text')

    assert result.is_error is True
    assert result.content[0].text == 'Error in operation: original text'
    assert result.structured_content == {
        'error': {
            'code': 'ThrottlingException',
            'error_type': 'ClientError',
            'message': 'Rate exceeded',
            'http_status': 429,
            'request_id': 'request-123',
        }
    }


def test_create_error_result_with_missing_client_error_metadata():
    """Missing AWS response metadata is represented by null values."""
    exception = ClientError({'Error': {'Code': 'BadRequestException'}}, 'Operation')

    result = create_error_result(exception, str(exception))

    assert result.structured_content == {
        'error': {
            'code': 'BadRequestException',
            'error_type': 'ClientError',
            'message': None,
            'http_status': None,
            'request_id': None,
        }
    }


def test_create_error_result_with_non_aws_exception():
    """Non-AWS exceptions keep the existing text-only error shape."""
    result = create_error_result(ValueError('bad input'), 'Error: bad input')

    assert result.is_error is True
    assert result.content[0].text == 'Error: bad input'
    assert result.structured_content is None
