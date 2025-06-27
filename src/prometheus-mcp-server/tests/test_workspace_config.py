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
    configure_workspace_for_request,
    _global_config
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
    async def test_configure_workspace_for_request_with_global_url(self, mock_context):
        """Test that configure_workspace_for_request uses global URL when available."""
        mock_test_connection = AsyncMock(return_value=True)
        
        # Set global config with URL
        _global_config["prometheus_url"] = "https://global-example.com"
        _global_config["region"] = "us-west-2"
        _global_config["profile"] = "global-profile"
        
        with patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            result = await configure_workspace_for_request(
                ctx=mock_context,
                workspace_id=None,  # No workspace_id needed when global URL is set
                region=None,
                profile=None
            )
            
            assert result == {
                "prometheus_url": "https://global-example.com",
                "region": "us-west-2",
                "profile": "global-profile",
                "workspace_id": None
            }
            mock_test_connection.assert_called_once_with(
                "https://global-example.com", "us-west-2", "global-profile"
            )
        
        # Reset global config
        _global_config["prometheus_url"] = None
        _global_config["region"] = None
        _global_config["profile"] = None

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_with_global_url_connection_failure(self, mock_context):
        """Test that configure_workspace_for_request raises RuntimeError when connection to global URL fails."""
        mock_test_connection = AsyncMock(return_value=False)
        
        # Set global config with URL
        _global_config["prometheus_url"] = "https://global-example.com"
        _global_config["region"] = "us-west-2"
        _global_config["profile"] = "global-profile"
        
        with patch("awslabs.prometheus_mcp_server.server.PrometheusConnection.test_connection", mock_test_connection), \
             patch("awslabs.prometheus_mcp_server.server.logger"):
            
            with pytest.raises(RuntimeError, match="Failed to connect to Prometheus with configured URL"):
                await configure_workspace_for_request(
                    ctx=mock_context,
                    workspace_id=None,
                    region=None,
                    profile=None
                )
        
        # Reset global config
        _global_config["prometheus_url"] = None
        _global_config["region"] = None
        _global_config["profile"] = None

    @pytest.mark.asyncio
    async def test_configure_workspace_for_request_no_global_url_no_workspace_id(self, mock_context):
        """Test that configure_workspace_for_request raises ValueError when no global URL and no workspace_id."""
        # Ensure global config has no URL
        _global_config["prometheus_url"] = None
        
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
        """Test that configure_workspace_for_request uses workspace_id when no global URL is available."""
        mock_get_workspace_details = AsyncMock(return_value={
            "workspace_id": "ws-12345",
            "alias": "test-workspace",
            "status": "ACTIVE",
            "prometheus_url": "https://example.com/workspaces/ws-12345",
            "region": "us-east-1"
        })
        mock_test_connection = AsyncMock(return_value=True)
        
        # Ensure global config has no URL
        _global_config["prometheus_url"] = None
        
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
        
        # Ensure global config has no URL
        _global_config["prometheus_url"] = None
        
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
        
        # Ensure global config has no URL
        _global_config["prometheus_url"] = None
        
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