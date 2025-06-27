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

"""Tests for the main function and async_main function."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from awslabs.prometheus_mcp_server.server import main, async_main, _global_config


class TestMain:
    """Tests for the main function and async_main function."""

    @pytest.mark.asyncio
    async def test_async_main_with_url(self):
        """Test that async_main correctly logs when URL is configured."""
        # Set global config with URL
        _global_config["prometheus_url"] = "https://example.com"
        
        with patch("awslabs.prometheus_mcp_server.server.logger") as mock_logger:
            await async_main()
            
            mock_logger.info.assert_any_call("Using configured Prometheus URL: https://example.com")
            mock_logger.info.assert_any_call("Workspace ID will be optional when using tools")
        
        # Reset global config
        _global_config["prometheus_url"] = None

    @pytest.mark.asyncio
    async def test_async_main_without_url(self):
        """Test that async_main correctly logs when URL is not configured."""
        # Ensure global config has no URL
        _global_config["prometheus_url"] = None
        
        with patch("awslabs.prometheus_mcp_server.server.logger") as mock_logger:
            await async_main()
            
            mock_logger.info.assert_called_with(
                'Initializing Prometheus MCP Server - workspace ID will be required for each tool invocation'
            )
        
    def test_main_success(self):
        """Test that main correctly initializes and runs the server."""
        mock_args = MagicMock()
        mock_config = {"region": "us-east-1", "profile": "test-profile", "url": "https://example.com"}
        
        with patch("awslabs.prometheus_mcp_server.server.ConfigManager.parse_arguments", return_value=mock_args), \
             patch("awslabs.prometheus_mcp_server.server.ConfigManager.setup_basic_config", return_value=mock_config), \
             patch("awslabs.prometheus_mcp_server.server.AWSCredentials.validate", return_value=True), \
             patch("awslabs.prometheus_mcp_server.server.asyncio.run"), \
             patch("awslabs.prometheus_mcp_server.server.mcp.run"), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            # Mock _global_config as a regular dictionary
            mock_global_config = {}
            with patch("awslabs.prometheus_mcp_server.server._global_config", mock_global_config):
                main()
                
                # Check that global config was updated
                assert mock_global_config["prometheus_url"] == "https://example.com"
                assert mock_global_config["region"] == "us-east-1"
                assert mock_global_config["profile"] == "test-profile"

    def test_main_credentials_failure(self):
        """Test that main exits when credentials validation fails."""
        mock_args = MagicMock()
        mock_config = {"region": "us-east-1", "profile": "test-profile", "url": "https://example.com"}
        
        with patch("awslabs.prometheus_mcp_server.server.ConfigManager.parse_arguments", return_value=mock_args), \
             patch("awslabs.prometheus_mcp_server.server.ConfigManager.setup_basic_config", return_value=mock_config), \
             patch("awslabs.prometheus_mcp_server.server.AWSCredentials.validate", return_value=False), \
             patch("awslabs.prometheus_mcp_server.server.sys.exit") as mock_exit, \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            main()
            
            mock_exit.assert_called_once_with(1)

    def test_main_server_error(self):
        """Test that main handles server startup errors."""
        mock_args = MagicMock()
        mock_config = {"region": "us-east-1", "profile": "test-profile", "url": "https://example.com"}
        
        with patch("awslabs.prometheus_mcp_server.server.ConfigManager.parse_arguments", return_value=mock_args), \
             patch("awslabs.prometheus_mcp_server.server.ConfigManager.setup_basic_config", return_value=mock_config), \
             patch("awslabs.prometheus_mcp_server.server.AWSCredentials.validate", return_value=True), \
             patch("awslabs.prometheus_mcp_server.server.asyncio.run"), \
             patch("awslabs.prometheus_mcp_server.server.mcp.run", side_effect=Exception("Server error")), \
             patch("awslabs.prometheus_mcp_server.server.sys.exit") as mock_exit, \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            # Mock _global_config as a regular dictionary
            mock_global_config = {}
            with patch("awslabs.prometheus_mcp_server.server._global_config", mock_global_config):
                main()
                
                mock_exit.assert_called_once_with(1)