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
"""Test script for API name extraction from OpenAPI spec."""

import json
import os
import pytest
import tempfile
from awslabs.openapi_mcp_server.api.config import load_config
from awslabs.openapi_mcp_server.utils.openapi import extract_api_name_from_spec, load_openapi_spec


@pytest.fixture
def openapi_spec():
    """Create a temporary OpenAPI spec for testing."""
    spec = {
        'openapi': '3.0.0',
        'info': {
            'title': 'Hotels API',
            'version': '1.0.0',
            'description': 'API for hotel bookings',
        },
        'paths': {},
    }
    return spec


@pytest.fixture
def temp_spec_file(openapi_spec):
    """Create a temporary file with the OpenAPI spec."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as tmp:
        json.dump(openapi_spec, tmp)
        tmp_path = tmp.name

    yield tmp_path

    # Clean up after the test
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


def test_extract_api_name_from_spec(openapi_spec):
    """Test extracting API name directly from spec dictionary."""
    api_name = extract_api_name_from_spec(openapi_spec)
    assert api_name == 'Hotels API'


def test_extract_api_name_from_loaded_spec(temp_spec_file):
    """Test extracting API name from a loaded spec file."""
    loaded_spec = load_openapi_spec(path=temp_spec_file)
    api_name = extract_api_name_from_spec(loaded_spec)
    assert api_name == 'Hotels API'


def test_config_with_extracted_api_name(temp_spec_file):
    """Test that the API name is correctly extracted and used in config."""

    # Create a mock args object
    class MockArgs:
        """Mock command line arguments for testing."""

        def __init__(self):
            self.api_name = None
            self.api_url = 'https://example.com/api'
            self.spec_path = temp_spec_file
            self.spec_url = None
            self.auth_type = 'none'
            self.sse = False
            self.port = None
            self.debug = False
            self.log_level = 'INFO'
            self.auth_username = None
            self.auth_password = None
            self.auth_token = None
            self.auth_api_key = None
            self.auth_api_key_name = None
            self.auth_api_key_in = None
            self.auth_cognito_client_id = None
            self.auth_cognito_username = None
            self.auth_cognito_password = None
            self.auth_cognito_user_pool_id = None
            self.auth_cognito_region = None

    # Save original environment
    original_env = os.environ.copy()

    try:
        # Make sure API_NAME is not set in the environment
        if 'API_NAME' in os.environ:
            del os.environ['API_NAME']

        # Load configuration
        args = MockArgs()
        config = load_config(args)

        # Simulate the early API name extraction
        if not args.api_name and not os.environ.get('API_NAME') and args.spec_path:
            openapi_spec = load_openapi_spec(path=args.spec_path)
            api_name = extract_api_name_from_spec(openapi_spec)
            if api_name:
                config.api_name = api_name

        assert config.api_name == 'Hotels API'

    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_extract_api_name_with_invalid_spec():
    """Test extracting API name from an invalid spec."""
    from unittest.mock import patch

    # Test with None - should trigger warning log
    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
        result = extract_api_name_from_spec(None)
        assert result is None
        mock_logger.warning.assert_called_once_with('Invalid OpenAPI spec format')

    # Test with non-dict - should trigger warning log
    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
        result = extract_api_name_from_spec('not a dict')
        assert result is None
        mock_logger.warning.assert_called_once_with('Invalid OpenAPI spec format')

    # Test with empty dict - should trigger warning log (empty dict is falsy)
    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
        result = extract_api_name_from_spec({})
        assert result is None
        mock_logger.warning.assert_called_once_with('Invalid OpenAPI spec format')

    # Test with dict missing info - should trigger debug log
    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
        result = extract_api_name_from_spec({'openapi': '3.0.0'})
        assert result is None
        mock_logger.debug.assert_called_once_with('No API name found in OpenAPI spec')

    # Test with dict having info but missing title - should trigger debug log
    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
        result = extract_api_name_from_spec({'info': {}})
        assert result is None
        mock_logger.debug.assert_called_once_with('No API name found in OpenAPI spec')


def test_extract_api_name_logging_coverage():
    """Additional test to ensure logging paths are covered."""
    from unittest.mock import patch

    # Test warning path with empty spec
    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
        result = extract_api_name_from_spec('')
        assert result is None
        mock_logger.warning.assert_called_once()

    # Test debug path with spec that has no title
    with patch('awslabs.openapi_mcp_server.utils.openapi.logger') as mock_logger:
        result = extract_api_name_from_spec({'info': {'version': '1.0.0'}})
        assert result is None
        mock_logger.debug.assert_called_once()
