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
# ruff: noqa: D101, D102, D103
"""Tests for the EKS Cluster Handler."""

import pytest
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.eks_cluster_handler import EksClusterHandler
from awslabs.eks_mcp_server.models import ListClustersResponse
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, patch


class TestEksClusterHandler:
    """Tests for the EksClusterHandler class."""

    def test_init(self):
        """Test that the handler is initialized correctly and registers its tools."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Initialize the EKS cluster handler with the mock MCP server
        handler = EksClusterHandler(mock_mcp)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp

        # Verify that tools are registered
        mock_mcp.tool.assert_called_once_with(name='list_clusters')

    @pytest.mark.asyncio
    @patch.object(AwsHelper, 'create_boto3_client')
    async def test_list_clusters_success(self, mock_create_client):
        """Test successful listing of EKS clusters."""
        # Mock the EKS client
        mock_eks_client = MagicMock()
        mock_eks_client.list_clusters.return_value = {
            'clusters': ['cluster1', 'cluster2', 'cluster3']
        }
        mock_create_client.return_value = mock_eks_client

        # Create a mock MCP server and handler
        mock_mcp = MagicMock()
        handler = EksClusterHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call list_clusters
        response = await handler.list_clusters(mock_ctx)

        # Verify the response
        assert isinstance(response, ListClustersResponse)
        assert response.isError is False
        assert response.clusters == ['cluster1', 'cluster2', 'cluster3']
        assert response.count == 3
        assert len(response.content) == 1
        assert isinstance(response.content[0], TextContent)
        assert 'Successfully listed 3 EKS clusters' in response.content[0].text

        # Verify that the EKS client was called correctly
        mock_create_client.assert_called_once_with('eks')
        mock_eks_client.list_clusters.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(AwsHelper, 'create_boto3_client')
    async def test_list_clusters_empty(self, mock_create_client):
        """Test listing EKS clusters when no clusters exist."""
        # Mock the EKS client
        mock_eks_client = MagicMock()
        mock_eks_client.list_clusters.return_value = {'clusters': []}
        mock_create_client.return_value = mock_eks_client

        # Create a mock MCP server and handler
        mock_mcp = MagicMock()
        handler = EksClusterHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call list_clusters
        response = await handler.list_clusters(mock_ctx)

        # Verify the response
        assert isinstance(response, ListClustersResponse)
        assert response.isError is False
        assert response.clusters == []
        assert response.count == 0
        assert len(response.content) == 1
        assert isinstance(response.content[0], TextContent)
        assert 'Successfully listed 0 EKS clusters' in response.content[0].text

    @pytest.mark.asyncio
    @patch.object(AwsHelper, 'create_boto3_client')
    async def test_list_clusters_failure(self, mock_create_client):
        """Test failure when listing EKS clusters."""
        # Mock the EKS client to raise an exception
        mock_eks_client = MagicMock()
        mock_eks_client.list_clusters.side_effect = Exception('AWS API Error')
        mock_create_client.return_value = mock_eks_client

        # Create a mock MCP server and handler
        mock_mcp = MagicMock()
        handler = EksClusterHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call list_clusters
        response = await handler.list_clusters(mock_ctx)

        # Verify the response
        assert isinstance(response, ListClustersResponse)
        assert response.isError is True
        assert response.clusters == []
        assert response.count == 0
        assert len(response.content) == 1
        assert isinstance(response.content[0], TextContent)
        assert 'Failed to list EKS clusters: AWS API Error' in response.content[0].text

    @pytest.mark.asyncio
    @patch.object(AwsHelper, 'create_boto3_client')
    async def test_list_clusters_with_all_parameters(self, mock_create_client):
        """Test listing EKS clusters with all parameters combined."""
        # Mock the EKS client
        mock_eks_client = MagicMock()
        mock_eks_client.list_clusters.return_value = {
            'clusters': ['cluster1'],
            'nextToken': 'next_page_token',
        }
        mock_create_client.return_value = mock_eks_client

        # Create a mock MCP server and handler
        mock_mcp = MagicMock()
        handler = EksClusterHandler(mock_mcp)

        # Create a mock context
        mock_ctx = MagicMock(spec=Context)

        # Call list_clusters with all parameters
        response = await handler.list_clusters(
            mock_ctx, max_results=10, next_token='current_token', include=['all']
        )

        # Verify the response
        assert isinstance(response, ListClustersResponse)
        assert response.isError is False
        assert response.clusters == ['cluster1']
        assert response.next_token == 'next_page_token'

        # Verify that the EKS client was called with all correct parameters
        mock_eks_client.list_clusters.assert_called_once_with(
            maxResults=10, nextToken='current_token', include=['all']
        )
