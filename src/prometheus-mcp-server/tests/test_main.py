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
import os
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from awslabs.prometheus_mcp_server.server import main, async_main


class TestMain:
    """Tests for the main function and async_main function."""

    @pytest.mark.asyncio
    async def test_async_main_with_url(self):
        """Test that async_main correctly logs when URL is configured."""
        # Set environment variable
        os.environ["PROMETHEUS_URL"] = "https://example.com"
        
        with patch("awslabs.prometheus_mcp_server.server.logger") as mock_logger:
            await async_main()
            
            mock_logger.info.assert_any_call("Using Prometheus URL from environment: https://example.com")
            mock_logger.info.assert_any_call("Workspace ID will be optional when using tools")
        
        # Reset environment variable
        del os.environ["PROMETHEUS_URL"]

    @pytest.mark.asyncio
    async def test_async_main_without_url(self):
        """Test that async_main correctly logs when URL is not configured."""
        # Ensure environment has no URL
        if "PROMETHEUS_URL" in os.environ:
            del os.environ["PROMETHEUS_URL"]
        
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
            
            # Save original environment
            original_env = os.environ.copy()
            try:
                main()
                
                # Check that environment variables were set
                assert os.environ["PROMETHEUS_URL"] == "https://example.com"
                assert os.environ["AWS_REGION"] == "us-east-1"
                assert os.environ["AWS_PROFILE"] == "test-profile"
            finally:
                # Restore original environment
                os.environ.clear()
                os.environ.update(original_env)

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
            
            main()
            
            mock_exit.assert_called_once_with(1)