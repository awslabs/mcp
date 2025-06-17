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
"""Tests for the OpenAPI utilities using direct module patching."""

# Import modules we need to mock
import httpx
import json
import pytest
from unittest.mock import MagicMock, mock_open, patch


# Create a no-op cache decorator function for testing
def no_cache_decorator(ttl_seconds=None):
    """No-op cache decorator for testing."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


# We need to ensure validate_openapi_spec always returns True by default
def always_valid_spec(*args, **kwargs):
    """Return True for testing validation."""
    return True


# Patch both cache decorator and validation before importing
with (
    patch('awslabs.openapi_mcp_server.utils.cache_provider.cached', no_cache_decorator),
    patch(
        'awslabs.openapi_mcp_server.utils.openapi_validator.validate_openapi_spec',
        always_valid_spec,
    ),
):
    # Now import the function we want to test
    from awslabs.openapi_mcp_server.utils.openapi import load_openapi_spec


class TestOpenAPIUtils:
    """Tests for OpenAPI utilities."""

    def test_no_args(self):
        """Test that the function raises ValueError when no arguments are provided."""
        with pytest.raises(ValueError, match='Either url or path must be provided'):
            load_openapi_spec()

    @patch('httpx.get')
    def test_url_http_error(self, mock_get):
        """Test HTTP error handling."""
        # Create mock response that raises HTTPError
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPError('HTTP Error')
        mock_get.return_value = mock_response

        # Test the exception is propagated correctly
        with pytest.raises(httpx.HTTPError, match='HTTP Error'):
            load_openapi_spec(url='https://example.com/api.json')

    @patch('httpx.get')
    def test_url_timeout(self, mock_get):
        """Test timeout exception handling."""
        # Setup the mock to raise TimeoutException
        mock_get.side_effect = httpx.TimeoutException('Timeout Error')

        # Test the exception is propagated correctly
        with pytest.raises(httpx.TimeoutException, match='Timeout Error'):
            load_openapi_spec(url='https://example.com/api.json')

    @patch('httpx.get')
    def test_url_invalid_spec(self, mock_get):
        """Test invalid OpenAPI spec validation."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"invalid": "spec"}'  # Return bytes content
        mock_response.json.return_value = {'invalid': 'spec'}
        mock_get.return_value = mock_response

        # Mock the validate_openapi_spec function directly
        with patch(
            'awslabs.openapi_mcp_server.utils.openapi.validate_openapi_spec', return_value=False
        ):
            # Test ValueError is raised for invalid spec
            with pytest.raises(ValueError, match='Invalid OpenAPI specification'):
                load_openapi_spec(url='https://example.com/api.json')

    @patch('pathlib.Path.exists', return_value=False)
    def test_path_not_found(self, mock_exists):
        """Test file not found error."""
        with pytest.raises(FileNotFoundError):
            load_openapi_spec(path='/nonexistent/file.json')

    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data='{"invalid": json')
    @patch('json.loads', side_effect=json.JSONDecodeError('Invalid JSON', '', 0))
    @patch.dict('sys.modules', {'yaml': None})
    def test_path_yaml_import_error(self, mock_json, mock_file, mock_exists):
        """Test YAML import error."""
        with pytest.raises(ImportError, match="Required dependency 'pyyaml' not installed"):
            load_openapi_spec(path='/path/to/file.yaml')

    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data='invalid: yaml')
    @patch('json.loads', side_effect=json.JSONDecodeError('Invalid JSON', '', 0))
    def test_path_yaml_invalid_spec(self, mock_json, mock_file, mock_exists):
        """Test invalid YAML error."""
        # Mock yaml module
        mock_yaml = MagicMock()
        mock_yaml.safe_load.side_effect = Exception('Invalid YAML')

        # Patch the yaml module
        with patch.dict('sys.modules', {'yaml': mock_yaml}):
            with pytest.raises(ValueError):
                load_openapi_spec(path='/path/to/file.yaml')

    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data='{"openapi": "3.0.0"}')
    @patch('json.loads', return_value={'openapi': '3.0.0'})
    def test_path_invalid_validation(self, mock_json, mock_file, mock_exists):
        """Test invalid OpenAPI spec from file."""
        # Override the validation function to return False
        with patch(
            'awslabs.openapi_mcp_server.utils.openapi_validator.validate_openapi_spec',
            return_value=False,
        ):
            with pytest.raises(ValueError, match='Invalid OpenAPI specification'):
                load_openapi_spec(path='/path/to/file.json')
