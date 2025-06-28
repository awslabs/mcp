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

"""Tests for workspace configuration functions."""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from botocore.config import Config
from awslabs.prometheus_mcp_server.server import (
    get_prometheus_client,
    get_workspace_details,
    configure_workspace_for_request
)


class TestWorkspaceConfig:
    """Tests for workspace configuration functions."""

    def test_get_prometheus_client(self):
        """Test that get_prometheus_client correctly creates an AMP client."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        
        with patch("awslabs.prometheus_mcp_server.server.boto3.Session", return_value=mock_session):
            # Test with provided region and profile
            client = get_prometheus_client(region_name="us-west-2", profile_name="test-profile")
            assert client == mock_client
            mock_session.client.assert_called_with("amp", config=ANY)
            
            # Test with default region
            with patch.dict(os.environ, {"AWS_REGION": "eu-west-1"}):
                client = get_prometheus_client()
                assert client == mock_client
                mock_session.client.assert_called_with("amp", config=ANY)
                
            # Test with no region provided and no environment variable
            with patch.dict(os.environ, {"AWS_REGION": ""}, clear=True), \
                 patch("awslabs.prometheus_mcp_server.server.DEFAULT_AWS_REGION", "us-east-1"):
                client = get_prometheus_client()
                assert client == mock_client
                # We can't assert on the Session constructor call because it's already been called
                # Just verify that the client was created

    @pytest.mark.asyncio
    async def test_get_workspace_details_success(self):
        """Test that get_workspace_details correctly retrieves workspace details."""
        mock_client = MagicMock()
        mock_client.describe_workspace.return_value = {
            "workspace": {
                "workspaceId": "ws-12345",
                "alias": "test-workspace",
                "status": {"statusCode": "ACTIVE"},
                "prometheusEndpoint": "https://example.com/workspaces/ws-12345"
            }
        }
        
        with patch("awslabs.prometheus_mcp_server.server.get_prometheus_client", return_value=mock_client), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            result = await get_workspace_details(
                workspace_id="ws-12345",
                region="us-east-1",
                profile="test-profile"
            )
            
            assert result == {
                "workspace_id": "ws-12345",
                "alias": "test-workspace",
                "status": "ACTIVE",
                "prometheus_url": "https://example.com/workspaces/ws-12345",
                "region": "us-east-1"
            }
            mock_client.describe_workspace.assert_called_once_with(workspaceId="ws-12345")

    @pytest.mark.asyncio
    async def test_get_workspace_details_no_endpoint(self):
        """Test that get_workspace_details raises ValueError when no prometheusEndpoint is found."""
        mock_client = MagicMock()
        mock_client.describe_workspace.return_value = {
            "workspace": {
                "workspaceId": "ws-12345",
                "alias": "test-workspace",
                "status": {"statusCode": "ACTIVE"}
                # No prometheusEndpoint
            }
        }
        
        with patch("awslabs.prometheus_mcp_server.server.get_prometheus_client", return_value=mock_client), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            with pytest.raises(ValueError, match="No prometheusEndpoint found in workspace response for ws-12345"):
                await get_workspace_details(
                    workspace_id="ws-12345",
                    region="us-east-1",
                    profile="test-profile"
                )

    @pytest.mark.asyncio
    async def test_get_workspace_details_api_error(self):
        """Test that get_workspace_details raises exception when API call fails."""
        mock_client = MagicMock()
        mock_client.describe_workspace.side_effect = Exception("API error")
        
        with patch("awslabs.prometheus_mcp_server.server.get_prometheus_client", return_value=mock_client), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            with pytest.raises(Exception, match="API error"):
                await get_workspace_details(
                    workspace_id="ws-12345",
                    region="us-east-1",
                    profile="test-profile"
                )

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_with_env_url(self, mock_context):
        """Test that configure_workspace_for_request uses environment URL when available."""
        mock_test_connection = AsyncMock(return_value=True)
        
        # Set environment variables
        os.environ["PROMETHEUS_URL"] = "https://env-example.com"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["AWS_PROFILE"] = "env-profile"
        
        with patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            result = await configure_workspace_for_request(
                ctx=mock_context,
                workspace_id=None,  # No workspace_id needed when URL is set in env
                region=None,
                profile=None
            )
            
            assert result == {
                "prometheus_url": "https://env-example.com",
                "region": "us-west-2",
                "profile": "env-profile",
                "workspace_id": None
            }
            mock_test_connection.assert_called_once_with(
                "https://env-example.com", "us-west-2", "env-profile"
            )
        
        # Reset environment variables
        del os.environ["PROMETHEUS_URL"]
        del os.environ["AWS_REGION"]
        del os.environ["AWS_PROFILE"]

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_with_env_url_connection_failure(self, mock_context):
        """Test that configure_workspace_for_request raises RuntimeError when connection to environment URL fails."""
        mock_test_connection = AsyncMock(return_value=False)
        
        # Set environment variables
        os.environ["PROMETHEUS_URL"] = "https://env-example.com"
        os.environ["AWS_REGION"] = "us-west-2"
        os.environ["AWS_PROFILE"] = "env-profile"
        
        with patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            with pytest.raises(RuntimeError, match="Failed to connect to Prometheus with configured URL"):
                await configure_workspace_for_request(
                    ctx=mock_context,
                    workspace_id=None,
                    region=None,
                    profile=None
                )
        
        # Reset environment variables
        del os.environ["PROMETHEUS_URL"]
        del os.environ["AWS_REGION"]
        del os.environ["AWS_PROFILE"]

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_no_env_url_no_workspace_id(self, mock_context):
        """Test that configure_workspace_for_request raises ValueError when no environment URL and no workspace_id."""
        # Ensure environment has no URL
        if "PROMETHEUS_URL" in os.environ:
            del os.environ["PROMETHEUS_URL"]
        
        with patch("awslabs.prometheus_mcp_server.server.logger"):
            with pytest.raises(ValueError, match="Workspace ID is required when no Prometheus URL is configured"):
                await configure_workspace_for_request(
                    ctx=mock_context,
                    workspace_id=None,
                    region=None,
                    profile=None
                )

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_with_workspace_id(self, mock_context):
        """Test that configure_workspace_for_request uses workspace_id when no environment URL is available."""
        mock_get_workspace_details = AsyncMock(return_value={
            "workspace_id": "ws-12345",
            "alias": "test-workspace",
            "status": "ACTIVE",
            "prometheus_url": "https://example.com/workspaces/ws-12345",
            "region": "us-east-1"
        })
        mock_test_connection = AsyncMock(return_value=True)
        
        # Ensure environment has no URL
        if "PROMETHEUS_URL" in os.environ:
            del os.environ["PROMETHEUS_URL"]
        
        with patch("awslabs.prometheus_mcp_server.server.get_workspace_details", mock_get_workspace_details), \
             patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            result = await configure_workspace_for_request(
                ctx=mock_context,
                workspace_id="ws-12345",
                region="us-east-1",
                profile="test-profile"
            )
            
            assert result == {
                "prometheus_url": "https://example.com/workspaces/ws-12345",
                "region": "us-east-1",
                "profile": "test-profile",
                "workspace_id": "ws-12345"
            }
            mock_get_workspace_details.assert_called_once_with("ws-12345", "us-east-1", "test-profile")
            mock_test_connection.assert_called_once_with(
                "https://example.com/workspaces/ws-12345", "us-east-1", "test-profile"
            )

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_with_workspace_id_connection_failure(self, mock_context):
        """Test that configure_workspace_for_request raises RuntimeError when connection with workspace_id fails."""
        mock_get_workspace_details = AsyncMock(return_value={
            "workspace_id": "ws-12345",
            "alias": "test-workspace",
            "status": "ACTIVE",
            "prometheus_url": "https://example.com/workspaces/ws-12345",
            "region": "us-east-1"
        })
        mock_test_connection = AsyncMock(return_value=False)
        
        # Ensure environment has no URL
        if "PROMETHEUS_URL" in os.environ:
            del os.environ["PROMETHEUS_URL"]
        
        with patch("awslabs.prometheus_mcp_server.server.get_workspace_details", mock_get_workspace_details), \
             patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            with pytest.raises(RuntimeError, match="Failed to connect to Prometheus with workspace ID ws-12345"):
                await configure_workspace_for_request(
                    ctx=mock_context,
                    workspace_id="ws-12345",
                    region="us-east-1",
                    profile="test-profile"
                )

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_unusual_workspace_id(self, mock_context):
        """Test that configure_workspace_for_request logs warning for unusual workspace ID."""
        mock_get_workspace_details = AsyncMock(return_value={
            "workspace_id": "unusual-id",
            "alias": "test-workspace",
            "status": "ACTIVE",
            "prometheus_url": "https://example.com/workspaces/unusual-id",
            "region": "us-east-1"
        })
        mock_test_connection = AsyncMock(return_value=True)
        mock_logger = MagicMock()
        
        # Ensure environment has no URL
        if "PROMETHEUS_URL" in os.environ:
            del os.environ["PROMETHEUS_URL"]
        
        with patch("awslabs.prometheus_mcp_server.server.get_workspace_details", mock_get_workspace_details), \
             patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.logger", mock_logger):
            
            result = await configure_workspace_for_request(
                ctx=mock_context,
                workspace_id="unusual-id",
                region="us-east-1",
                profile="test-profile"
            )
            
            assert result == {
                "prometheus_url": "https://example.com/workspaces/unusual-id",
                "region": "us-east-1",
                "profile": "test-profile",
                "workspace_id": "unusual-id"
            }
            mock_logger.warning.assert_called_once_with(
                'Workspace ID "unusual-id" does not start with "ws-", which is unusual'
            )
            
    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_with_url_containing_workspace_id(self, mock_context):
        """Test that configure_workspace_for_request extracts workspace ID from URL."""
        mock_test_connection = AsyncMock(return_value=True)
        mock_extract = MagicMock(return_value="ws-12345")
        
        # Set environment variables with URL containing workspace ID
        os.environ["PROMETHEUS_URL"] = "https://example.com/workspaces/ws-12345"
        os.environ["AWS_REGION"] = "us-west-2"
        
        with patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.extract_workspace_id_from_url", mock_extract), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            result = await configure_workspace_for_request(
                ctx=mock_context,
                workspace_id=None,  # No explicit workspace_id
                region=None,
                profile=None
            )
            
            assert result == {
                "prometheus_url": "https://example.com/workspaces/ws-12345",
                "region": "us-west-2",
                "profile": None,
                "workspace_id": "ws-12345"  # Should be extracted from URL
            }
            mock_extract.assert_called_once_with("https://example.com/workspaces/ws-12345")
        
        # Reset environment variables
        del os.environ["PROMETHEUS_URL"]
        del os.environ["AWS_REGION"]