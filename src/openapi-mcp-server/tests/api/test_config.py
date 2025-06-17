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
"""Tests for the API configuration module."""

import os
from awslabs.openapi_mcp_server.api.config import Config, load_config
from unittest.mock import MagicMock


def test_config_default_values():
    """Test that Config has the expected default values."""
    config = Config()
    assert config.api_name == 'awslabs-openapi-mcp-server'
    assert config.api_base_url == 'https://localhost:8000'
    assert config.auth_type == 'none'
    assert config.host == '127.0.0.1'  # Default host should be localhost for security
    assert config.port == 8000
    assert config.transport == 'stdio'
    assert config.version == '0.1.0'


def test_config_custom_values():
    """Test that Config accepts custom values."""
    config = Config(
        api_name='testapi',
        api_base_url='https://test.api.com',
        api_spec_url='https://test.api.com/openapi.json',
        api_spec_path='/path/to/spec.json',
        auth_type='basic',
        auth_username='user',
        auth_password='pass',
        host='127.0.0.1',
        port=9000,
        transport='sse',
        version='1.0.0',
    )

    assert config.api_name == 'testapi'
    assert config.api_base_url == 'https://test.api.com'
    assert config.api_spec_url == 'https://test.api.com/openapi.json'
    assert config.api_spec_path == '/path/to/spec.json'
    assert config.auth_type == 'basic'
    assert config.auth_username == 'user'
    assert config.auth_password == 'pass'
    assert config.host == '127.0.0.1'
    assert config.port == 9000
    assert config.transport == 'sse'
    assert config.version == '1.0.0'


def test_load_config_from_args():
    """Test loading config from arguments."""
    args = MagicMock()
    args.api_name = 'testapi'
    args.api_url = 'https://test.api.com'
    args.spec_url = 'https://test.api.com/openapi.json'
    args.spec_path = '/path/to/spec.json'
    args.port = 9000
    args.sse = True
    args.host = None  # Host is not set in args
    args.auth_type = 'basic'
    args.auth_username = 'user'
    args.auth_password = 'pass'
    args.auth_token = 'token'
    args.auth_api_key = 'apikey'
    args.auth_api_key_name = 'X-API-Key'
    args.auth_api_key_in = 'header'
    args.debug = True
    args.log_level = 'DEBUG'

    config = load_config(args)

    assert config.api_name == 'testapi'
    assert config.api_base_url == 'https://test.api.com'
    assert config.api_spec_url == 'https://test.api.com/openapi.json'
    assert config.api_spec_path == '/path/to/spec.json'
    assert config.port == 9000
    assert config.transport == 'stdio'  # Updated to match the default in config.py
    assert config.host == '127.0.0.1'  # Default host
    assert config.auth_type == 'basic'
    assert config.auth_username == 'user'
    assert config.auth_password == 'pass'
    assert config.auth_token == 'token'
    assert config.auth_api_key == 'apikey'
    assert config.auth_api_key_name == 'X-API-Key'
    assert config.auth_api_key_in == 'header'


def test_load_config_environment_variables():
    """Test loading config from environment variables."""
    # Save original environment variables to restore later
    original_env = os.environ.copy()

    try:
        # Set environment variables
        os.environ['API_NAME'] = 'env-api'
        os.environ['API_BASE_URL'] = 'https://env-api.com'
        os.environ['API_SPEC_URL'] = 'https://env-api.com/openapi.json'
        os.environ['API_SPEC_PATH'] = '/path/to/env-spec.json'
        os.environ['SERVER_PORT'] = '7777'
        os.environ['SERVER_TRANSPORT'] = 'stdio'
        os.environ['SERVER_HOST'] = '127.0.0.1'
        os.environ['AUTH_TYPE'] = 'bearer'
        os.environ['AUTH_TOKEN'] = 'env-token'
        os.environ['LOG_LEVEL'] = 'DEBUG'

        # Load config
        config = load_config()

        # Assert environment variables are used
        assert config.api_name == 'env-api'
        assert config.api_base_url == 'https://env-api.com'
        assert config.api_spec_url == 'https://env-api.com/openapi.json'
        assert config.api_spec_path == '/path/to/env-spec.json'
        assert config.port == 7777
        assert config.transport == 'stdio'
        assert config.host == '127.0.0.1'
        assert config.auth_type == 'bearer'
        assert config.auth_token == 'env-token'
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_load_config_api_key_auth():
    """Test loading config with API key authentication."""
    # Save original environment variables to restore later
    original_env = os.environ.copy()

    try:
        # Set environment variables
        os.environ['API_NAME'] = 'api-key-api'
        os.environ['API_BASE_URL'] = 'https://api-key-api.com'
        os.environ['AUTH_TYPE'] = 'api_key'
        os.environ['AUTH_API_KEY'] = 'test-api-key'
        os.environ['AUTH_API_KEY_NAME'] = 'X-Test-API-Key'
        os.environ['AUTH_API_KEY_IN'] = 'header'

        # Load config
        config = load_config()

        # Assert environment variables are used
        assert config.api_name == 'api-key-api'
        assert config.api_base_url == 'https://api-key-api.com'
        assert config.auth_type == 'api_key'
        assert config.auth_api_key == 'test-api-key'
        assert config.auth_api_key_name == 'X-Test-API-Key'
        assert config.auth_api_key_in == 'header'
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_load_config_basic_auth():
    """Test loading config with basic authentication."""
    # Save original environment variables to restore later
    original_env = os.environ.copy()

    try:
        # Set environment variables
        os.environ['API_NAME'] = 'basic-auth-api'
        os.environ['API_BASE_URL'] = 'https://basic-auth-api.com'
        os.environ['AUTH_TYPE'] = 'basic'
        os.environ['AUTH_USERNAME'] = 'test-user'
        os.environ['AUTH_PASSWORD'] = 'test-pass'

        # Load config
        config = load_config()

        # Assert environment variables are used
        assert config.api_name == 'basic-auth-api'
        assert config.api_base_url == 'https://basic-auth-api.com'
        assert config.auth_type == 'basic'
        assert config.auth_username == 'test-user'
        assert config.auth_password == 'test-pass'
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_load_config_precedence():
    """Test that arguments take precedence over environment variables."""
    # Save original environment variables to restore later
    original_env = os.environ.copy()

    try:
        # Set environment variables
        os.environ['API_NAME'] = 'env-api'
        os.environ['API_BASE_URL'] = 'https://env-api.com'
        os.environ['SERVER_PORT'] = '7777'

        # Create arguments
        args = MagicMock()
        args.api_name = 'arg-api'
        args.api_url = 'https://arg-api.com'
        args.port = 9999
        args.host = None
        args.spec_url = None
        args.spec_path = None
        args.sse = False
        args.auth_type = None
        args.auth_username = None
        args.auth_password = None
        args.auth_token = None
        args.auth_api_key = None
        args.auth_api_key_name = None
        args.auth_api_key_in = None
        args.debug = False
        args.log_level = None

        # Load config
        config = load_config(args)

        # Assert arguments take precedence
        assert config.api_name == 'arg-api'
        assert config.api_base_url == 'https://arg-api.com'
        assert config.port == 9999
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
