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
"""Tests for HTTP transport configuration."""

import os
import pytest
from unittest.mock import patch
from awslabs.openapi_mcp_server.api.config import Config, load_config


class TestConfigTransport:
    """Test Config HTTP transport settings."""

    def test_default_config_values(self):
        """Test that default config values are correct for HTTP transport."""
        config = Config()
        
        # Test default transport settings
        assert config.transport == 'stdio'
        assert config.mcp_path == '/mcp'
        assert config.stateless_http == True
        assert config.json_response == True
        assert config.fastmcp_log_level == 'INFO'

    @patch.dict(
        os.environ,
        {
            'TRANSPORT': 'streamable-http',
            'MCP_PATH': '/custom-mcp',
            'STATELESS_HTTP': 'false',
            'JSON_RESPONSE': 'false',
            'FASTMCP_LOG_LEVEL': 'DEBUG',
        },
        clear=True,
    )
    def test_env_var_overrides(self):
        """Test that environment variables override default values."""
        config = load_config()
        
        assert config.transport == 'streamable-http'
        assert config.mcp_path == '/custom-mcp'
        assert config.stateless_http == False
        assert config.json_response == False
        assert config.fastmcp_log_level == 'DEBUG'

    @patch.dict(
        os.environ,
        {
            'SERVER_HOST': '0.0.0.0',
            'SERVER_PORT': '9000',
            'TRANSPORT': 'streamable-http',
        },
        clear=True,
    )
    def test_existing_server_env_vars(self):
        """Test that existing SERVER_HOST and SERVER_PORT work with new transport."""
        config = load_config()
        
        assert config.host == '0.0.0.0'
        assert config.port == 9000
        assert config.transport == 'streamable-http'

    @patch.dict(
        os.environ,
        {
            'SERVER_TRANSPORT': 'streamable-http',
            'TRANSPORT': 'stdio',
        },
        clear=True,
    )
    def test_both_transport_env_vars(self):
        """Test that both SERVER_TRANSPORT and TRANSPORT can set transport."""
        # TRANSPORT should take precedence as it's processed later
        config = load_config()
        
        assert config.transport == 'stdio'

    @patch.dict(os.environ, {'STATELESS_HTTP': 'invalid'}, clear=True)
    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        config = load_config()
        
        # Invalid boolean should default to False
        assert config.stateless_http == False

    @patch.dict(os.environ, {'STATELESS_HTTP': 'TRUE'}, clear=True)
    def test_boolean_parsing_case_insensitive(self):
        """Test boolean parsing is case insensitive."""
        config = load_config()
        
        assert config.stateless_http == True

    def test_config_with_args(self):
        """Test config loading with command line arguments."""
        
        class MockArgs:
            def __init__(self):
                self.api_name = 'test-api'
                self.debug = True
                self.host = '0.0.0.0'
                self.port = 9999
                self.transport = 'streamable-http'
                self.mcp_path = '/custom-mcp'
        
        args = MockArgs()
        config = load_config(args)

        assert config.api_name == 'test-api'
        assert config.debug == True
        assert config.mcp_path == '/custom-mcp'
        assert config.transport == 'streamable-http'
        assert config.host == '0.0.0.0'
        assert config.port == 9999

        # HTTP transport settings should keep defaults
        assert config.stateless_http == True
        assert config.json_response == True
        assert config.fastmcp_log_level == 'INFO'
