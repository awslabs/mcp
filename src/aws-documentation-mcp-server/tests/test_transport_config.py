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
"""Tests for transport configuration and environment variable handling."""

import os
import pytest
from unittest.mock import MagicMock, patch


class TestTransportConfiguration:
    """Tests for transport configuration logic."""

    def test_stdio_transport_does_not_set_host_port(self):
        """Test that stdio transport does not set host and port."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'stdio'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                mock_mcp.run = MagicMock()
                mock_mcp.settings = MagicMock()
                
                from awslabs.aws_documentation_mcp_server.server_aws import main
                
                main()
                
                # Verify host and port were not set for stdio transport
                assert not hasattr(mock_mcp.settings, 'host') or mock_mcp.settings.host != '127.0.0.1'
                assert not hasattr(mock_mcp.settings, 'port') or mock_mcp.settings.port != 8000
                mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_streamable_http_transport_sets_host_port(self):
        """Test that streamable-http transport sets host and port."""
        with patch.dict(
            os.environ,
            {
                'FASTMCP_TRANSPORT': 'streamable-http',
                'FASTMCP_HOST': '0.0.0.0',
                'FASTMCP_PORT': '9000',
            },
            clear=False,
        ):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                mock_mcp.run = MagicMock()
                mock_mcp.settings = MagicMock()
                
                # Need to reload the module to pick up new environment variables
                import importlib
                import awslabs.aws_documentation_mcp_server.server_aws as server_module
                importlib.reload(server_module)
                
                server_module.main()
                
                # Verify host and port were set for streamable-http transport
                mock_mcp.settings.host = '0.0.0.0'
                mock_mcp.settings.port = 9000
                mock_mcp.run.assert_called_once_with(transport='streamable-http')

    def test_default_transport_is_stdio(self):
        """Test that default transport is stdio when FASTMCP_TRANSPORT is not set."""
        env_copy = os.environ.copy()
        if 'FASTMCP_TRANSPORT' in env_copy:
            del env_copy['FASTMCP_TRANSPORT']
        
        with patch.dict(os.environ, env_copy, clear=True):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                mock_mcp.run = MagicMock()
                mock_mcp.settings = MagicMock()
                
                from awslabs.aws_documentation_mcp_server.server_aws import main
                
                main()
                
                mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_environment_variables_read_correctly(self):
        """Test that environment variables are read correctly."""
        with patch.dict(
            os.environ,
            {
                'FASTMCP_HOST': '192.168.1.1',
                'FASTMCP_PORT': '7777',
                'FASTMCP_TRANSPORT': 'streamable-http',
            },
            clear=False,
        ):
            # Need to reload the module to pick up new environment variables
            import importlib
            import awslabs.aws_documentation_mcp_server.server_aws as server_module
            importlib.reload(server_module)
            
            # Verify environment variables are read
            assert server_module.FASTMCP_HOST == '192.168.1.1'
            assert server_module.FASTMCP_PORT == 7777

    def test_default_host_port_values(self):
        """Test default host and port values when environment variables are not set."""
        env_copy = os.environ.copy()
        for key in ['FASTMCP_HOST', 'FASTMCP_PORT']:
            if key in env_copy:
                del env_copy[key]
        
        with patch.dict(os.environ, env_copy, clear=True):
            # Need to reload the module to pick up environment changes
            import importlib
            import awslabs.aws_documentation_mcp_server.server_aws as server_module
            importlib.reload(server_module)
            
            # Verify default values
            assert server_module.FASTMCP_HOST == '127.0.0.1'
            assert server_module.FASTMCP_PORT == 8000


class TestTransportConfigurationCN:
    """Tests for AWS CN transport configuration logic."""

    def test_cn_stdio_transport_does_not_set_host_port(self):
        """Test that stdio transport does not set host and port for CN server."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'stdio'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.mcp') as mock_mcp:
                mock_mcp.run = MagicMock()
                mock_mcp.settings = MagicMock()
                
                from awslabs.aws_documentation_mcp_server.server_aws_cn import main
                
                main()
                
                # Verify host and port were not set for stdio transport
                assert not hasattr(mock_mcp.settings, 'host') or mock_mcp.settings.host != '127.0.0.1'
                assert not hasattr(mock_mcp.settings, 'port') or mock_mcp.settings.port != 8000
                mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_cn_streamable_http_transport_sets_host_port(self):
        """Test that streamable-http transport sets host and port for CN server."""
        with patch.dict(
            os.environ,
            {
                'FASTMCP_TRANSPORT': 'streamable-http',
                'FASTMCP_HOST': '0.0.0.0',
                'FASTMCP_PORT': '9000',
            },
            clear=False,
        ):
            with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.mcp') as mock_mcp:
                mock_mcp.run = MagicMock()
                mock_mcp.settings = MagicMock()
                
                # Need to reload the module to pick up new environment variables
                import importlib
                import awslabs.aws_documentation_mcp_server.server_aws_cn as server_module
                importlib.reload(server_module)
                
                server_module.main()
                
                # Verify host and port were set for streamable-http transport
                mock_mcp.settings.host = '0.0.0.0'
                mock_mcp.settings.port = 9000
                mock_mcp.run.assert_called_once_with(transport='streamable-http')
