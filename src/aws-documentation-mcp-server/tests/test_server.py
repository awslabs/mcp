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
"""Tests for the AWS Documentation MCP Server main module."""

import os
import pytest
from unittest.mock import patch


class TestServer:
    """Tests for the main server module."""

    def test_partition_aws(self):
        """Test main function with AWS partition."""
        with patch.dict(os.environ, {'AWS_DOCUMENTATION_PARTITION': 'aws'}):
            with patch('awslabs.aws_documentation_mcp_server.server_aws.main') as mock_main:
                from awslabs.aws_documentation_mcp_server.server import main

                main()
                mock_main.assert_called_once()

    def test_partition_aws_cn(self):
        """Test main function with AWS China partition."""
        with patch.dict(os.environ, {'AWS_DOCUMENTATION_PARTITION': 'aws-cn'}):
            with patch('awslabs.aws_documentation_mcp_server.server_aws_cn.main') as mock_main:
                import awslabs.aws_documentation_mcp_server.server

                # Need to reload the module to pick up the environment variable change
                import importlib
                from awslabs.aws_documentation_mcp_server.server import main

                importlib.reload(awslabs.aws_documentation_mcp_server.server)
                main()
                mock_main.assert_called_once()

    def test_partition_default(self):
        """Test main function with default partition (aws)."""
        with patch.dict(os.environ, {}, clear=True):  # Clear environment variables
            with patch('awslabs.aws_documentation_mcp_server.server_aws.main') as mock_main:
                import awslabs.aws_documentation_mcp_server.server

                # Need to reload the module to pick up the environment variable change
                import importlib
                from awslabs.aws_documentation_mcp_server.server import main

                importlib.reload(awslabs.aws_documentation_mcp_server.server)
                main()
                mock_main.assert_called_once()

    def test_partition_invalid(self):
        """Test main function with invalid partition."""
        with patch.dict(os.environ, {'AWS_DOCUMENTATION_PARTITION': 'invalid'}):
            with pytest.raises(ValueError) as excinfo:
                import awslabs.aws_documentation_mcp_server.server

                # Need to reload the module to pick up the environment variable change
                import importlib
                from awslabs.aws_documentation_mcp_server.server import main

                importlib.reload(awslabs.aws_documentation_mcp_server.server)
                main()
            assert 'Unsupported AWS documentation partition: invalid' in str(excinfo.value)

    def test_logging_setup(self):
        """Test that logging is set up correctly."""
        with patch('loguru.logger.remove') as mock_remove:
            with patch('loguru.logger.add') as mock_add:
                with patch.dict(os.environ, {'FASTMCP_LOG_LEVEL': 'DEBUG'}):
                    # Need to reload the module to pick up the environment variable change
                    import awslabs.aws_documentation_mcp_server.server
                    import importlib

                    importlib.reload(awslabs.aws_documentation_mcp_server.server)

                    mock_remove.assert_called_once()
                    mock_add.assert_called_once()
                    # Check that the log level was set correctly
                    args, kwargs = mock_add.call_args
                    assert kwargs.get('level') == 'DEBUG'

    def test_logging_default_level(self):
        """Test that logging uses default level when not specified."""
        with patch('loguru.logger.remove') as mock_remove:
            with patch('loguru.logger.add') as mock_add:
                with patch.dict(os.environ, {}, clear=True):  # Clear environment variables
                    # Need to reload the module to pick up the environment variable change
                    import awslabs.aws_documentation_mcp_server.server
                    import importlib

                    importlib.reload(awslabs.aws_documentation_mcp_server.server)

                    mock_remove.assert_called_once()
                    mock_add.assert_called_once()
                    # Check that the default log level was used
                    args, kwargs = mock_add.call_args
                    assert kwargs.get('level') == 'WARNING'
