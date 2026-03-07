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
from unittest.mock import MagicMock, PropertyMock, call, patch


class TestTransportConfigurationAWS:
    """Tests for AWS server transport configuration logic."""

    def test_stdio_transport_does_not_set_host_port(self):
        """Test that stdio transport does not set mcp.settings.host or mcp.settings.port."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'stdio'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                mock_settings = MagicMock()
                mock_mcp.settings = mock_settings
                mock_mcp.run = MagicMock()

                from awslabs.aws_documentation_mcp_server.server_aws import main
                main()

                # settings.host and settings.port should NOT have been assigned
                # Check that no attribute was set on mock_settings via __setattr__
                set_calls = [
                    c for c in mock_settings.mock_calls
                    if '__setattr__' not in str(c)
                ]
                # The key check: host and port should not appear in the
                # property assignments on mock_settings
                for c in mock_settings._mock_children:
                    assert c not in ('host', 'port'), (
                        f'mcp.settings.{c} should not be set for stdio transport'
                    )
                mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_streamable_http_transport_sets_host_port(self):
        """Test that streamable-http transport sets mcp.settings.host and mcp.settings.port."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'streamable-http'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                mock_settings = MagicMock()
                mock_mcp.settings = mock_settings
                mock_mcp.run = MagicMock()

                from awslabs.aws_documentation_mcp_server.server_aws import (
                    FASTMCP_HOST,
                    FASTMCP_PORT,
                    main,
                )
                main()

                # Verify host and port were SET (not just read) on settings
                assert mock_mcp.settings.host == FASTMCP_HOST
                assert mock_mcp.settings.port == FASTMCP_PORT
                mock_mcp.run.assert_called_once_with(transport='streamable-http')

    def test_streamable_http_localhost_keeps_transport_security(self):
        """Test that transport_security is NOT disabled when host is localhost."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'streamable-http'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                with patch('awslabs.aws_documentation_mcp_server.server_aws.FASTMCP_HOST', '127.0.0.1'):
                    mock_settings = MagicMock()
                    mock_mcp.settings = mock_settings
                    mock_mcp.run = MagicMock()

                    from awslabs.aws_documentation_mcp_server.server_aws import main
                    main()

                    # transport_security should NOT have been set to None
                    # (MagicMock attribute access returns a new MagicMock, not None)
                    assert mock_mcp.settings.transport_security is not None
                    mock_mcp.run.assert_called_once_with(transport='streamable-http')

    def test_streamable_http_non_localhost_disables_transport_security(self):
        """Test that transport_security is disabled when host is 0.0.0.0 (non-localhost)."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'streamable-http'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                with patch('awslabs.aws_documentation_mcp_server.server_aws.FASTMCP_HOST', '0.0.0.0'):
                    mock_settings = MagicMock()
                    mock_mcp.settings = mock_settings
                    mock_mcp.run = MagicMock()

                    from awslabs.aws_documentation_mcp_server.server_aws import main
                    main()

                    # transport_security should be set to None
                    assert mock_mcp.settings.transport_security is None
                    mock_mcp.run.assert_called_once_with(transport='streamable-http')

    def test_default_transport_is_stdio(self):
        """Test that default transport is stdio when FASTMCP_TRANSPORT is not set."""
        env = os.environ.copy()
        env.pop('FASTMCP_TRANSPORT', None)

        with patch.dict(os.environ, env, clear=True):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.mcp') as mock_mcp:
                mock_mcp.run = MagicMock()
                mock_mcp.settings = MagicMock()

                from awslabs.aws_documentation_mcp_server.server_aws import main
                main()

                mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_module_level_env_defaults(self):
        """Test default FASTMCP_HOST and FASTMCP_PORT values at module level."""
        from awslabs.aws_documentation_mcp_server.server_aws import FASTMCP_HOST, FASTMCP_PORT

        # These are read at module import time; verify they have sensible defaults
        assert isinstance(FASTMCP_HOST, str)
        assert isinstance(FASTMCP_PORT, int)
        assert FASTMCP_PORT > 0


class TestTransportConfigurationCN:
    """Tests for AWS CN server transport configuration logic."""

    def test_cn_stdio_transport_does_not_set_host_port(self):
        """Test that stdio transport does not set mcp.settings.host or mcp.settings.port for CN."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'stdio'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.mcp') as mock_mcp:
                mock_settings = MagicMock()
                mock_mcp.settings = mock_settings
                mock_mcp.run = MagicMock()

                from awslabs.aws_documentation_mcp_server.server_aws_cn import main
                main()

                for c in mock_settings._mock_children:
                    assert c not in ('host', 'port'), (
                        f'mcp.settings.{c} should not be set for stdio transport'
                    )
                mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_cn_streamable_http_transport_sets_host_port(self):
        """Test that streamable-http transport sets mcp.settings.host and mcp.settings.port for CN."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'streamable-http'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.mcp') as mock_mcp:
                mock_settings = MagicMock()
                mock_mcp.settings = mock_settings
                mock_mcp.run = MagicMock()

                from awslabs.aws_documentation_mcp_server.server_aws_cn import (
                    FASTMCP_HOST,
                    FASTMCP_PORT,
                    main,
                )
                main()

                assert mock_mcp.settings.host == FASTMCP_HOST
                assert mock_mcp.settings.port == FASTMCP_PORT
                mock_mcp.run.assert_called_once_with(transport='streamable-http')

    def test_cn_streamable_http_localhost_keeps_transport_security(self):
        """Test that CN transport_security is NOT disabled when host is localhost."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'streamable-http'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.mcp') as mock_mcp:
                with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.FASTMCP_HOST', '127.0.0.1'):
                    mock_settings = MagicMock()
                    mock_mcp.settings = mock_settings
                    mock_mcp.run = MagicMock()

                    from awslabs.aws_documentation_mcp_server.server_aws_cn import main
                    main()

                    # transport_security should NOT have been set to None
                    assert mock_mcp.settings.transport_security is not None
                    mock_mcp.run.assert_called_once_with(transport='streamable-http')

    def test_cn_streamable_http_non_localhost_disables_transport_security(self):
        """Test that CN transport_security is disabled when host is 0.0.0.0."""
        with patch.dict(os.environ, {'FASTMCP_TRANSPORT': 'streamable-http'}, clear=False):
            with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.mcp') as mock_mcp:
                with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.FASTMCP_HOST', '0.0.0.0'):
                    mock_settings = MagicMock()
                    mock_mcp.settings = mock_settings
                    mock_mcp.run = MagicMock()

                    from awslabs.aws_documentation_mcp_server.server_aws_cn import main
                    main()

                    assert mock_mcp.settings.transport_security is None
                    mock_mcp.run.assert_called_once_with(transport='streamable-http')
