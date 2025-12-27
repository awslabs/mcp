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

"""Tests for response formatting functions."""

import json
from awslabs.healthimaging_mcp_server.server import create_error_response, create_success_response


def test_create_error_response():
    """Test error response format."""
    response = create_error_response('Test error', 'validation_error')

    assert len(response) == 1
    content = response[0]
    assert content.type == 'text'

    data = json.loads(content.text)
    assert data['error'] is True
    assert data['type'] == 'validation_error'
    assert data['message'] == 'Test error'


def test_create_error_response_default_type():
    """Test error response with default error type."""
    response = create_error_response('Default error')

    data = json.loads(response[0].text)
    assert data['type'] == 'error'


def test_create_success_response():
    """Test success response format."""
    test_data = {'key': 'value', 'number': 42}
    response = create_success_response(test_data)

    assert len(response) == 1
    content = response[0]
    assert content.type == 'text'

    data = json.loads(content.text)
    assert data == test_data


def test_create_success_response_with_datetime():
    """Test success response handles datetime serialization."""
    from datetime import datetime

    test_data = {'timestamp': datetime(2023, 1, 1, 12, 0, 0)}
    response = create_success_response(test_data)

    data = json.loads(response[0].text)
    assert '2023-01-01T12:00:00' in data['timestamp']
