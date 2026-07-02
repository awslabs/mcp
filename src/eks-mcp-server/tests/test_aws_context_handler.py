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
"""Tests for the AWS Context Handler."""

import json
import os
import pytest
from awslabs.eks_mcp_server.aws_context_handler import AwsContextHandler, AwsContextData
from awslabs.eks_mcp_server.aws_helper import AwsHelper
from awslabs.eks_mcp_server.k8s_client_cache import K8sClientCache
from mcp.server.fastmcp import FastMCP
from unittest.mock import MagicMock, patch


class TestAwsContextHandler:
    """Tests for the AwsContextHandler class."""

    def setup_method(self):
        """Set up the test environment."""
        # Clear caches before each test
        AwsHelper._client_cache = {}

        # Reset K8sClientCache singleton for clean tests
        K8sClientCache._instance = None

    @pytest.fixture
    def mcp_server(self):
        """Create a mock MCP server."""
        return FastMCP('test-server')

    @pytest.fixture
    def handler(self, mcp_server):
        """Create an AwsContextHandler instance."""
        return AwsContextHandler(mcp_server)

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock MCP context."""
        ctx = MagicMock()
        ctx.request_id = 'test-request-id'
        return ctx

    def test_handler_registers_tools(self, mcp_server, handler):
        """Test that the handler registers the expected tools."""
        # Get registered tools
        tools = mcp_server._tool_manager._tools

        # Verify both tools are registered
        assert 'get_aws_context' in tools
        assert 'set_aws_context' in tools

    @pytest.mark.asyncio
    @patch.dict(os.environ, {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-west-2'}, clear=True)
    async def test_get_aws_context(self, handler, mock_ctx):
        """Test get_aws_context returns current profile and region."""
        result = await handler.get_aws_context(mock_ctx)

        assert result.isError is not True
        assert len(result.content) == 1

        data = json.loads(result.content[0].text)
        assert data['success'] is True
        assert data['profile'] == 'test-profile'
        assert data['region'] == 'us-west-2'

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_get_aws_context_no_values_set(self, handler, mock_ctx):
        """Test get_aws_context when no profile/region is set."""
        result = await handler.get_aws_context(mock_ctx)

        data = json.loads(result.content[0].text)
        assert data['success'] is True
        assert data['profile'] is None
        assert data['region'] is None

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_set_aws_context_sets_values(self, handler, mock_ctx):
        """Test set_aws_context sets profile and region."""
        result = await handler.set_aws_context(
            mock_ctx, profile='new-profile', region='ap-south-1'
        )

        assert result.isError is not True
        data = json.loads(result.content[0].text)
        assert data['success'] is True
        assert data['profile'] == 'new-profile'
        assert data['region'] == 'ap-south-1'
        assert os.environ.get('AWS_PROFILE') == 'new-profile'
        assert os.environ.get('AWS_REGION') == 'ap-south-1'

    @pytest.mark.asyncio
    @patch.dict(os.environ, {'AWS_PROFILE': 'old-profile', 'AWS_REGION': 'old-region'}, clear=True)
    async def test_set_aws_context_clears_values(self, handler, mock_ctx):
        """Test set_aws_context clears values when empty string is passed."""
        result = await handler.set_aws_context(mock_ctx, profile='', region='')

        data = json.loads(result.content[0].text)
        assert data['success'] is True
        assert data['profile'] is None
        assert data['region'] is None
        assert 'AWS_PROFILE' not in os.environ
        assert 'AWS_REGION' not in os.environ

    @pytest.mark.asyncio
    @patch.dict(os.environ, {'AWS_PROFILE': 'existing-profile'}, clear=True)
    async def test_set_aws_context_partial_update(self, handler, mock_ctx):
        """Test set_aws_context only updates specified values."""
        # Only update region
        result = await handler.set_aws_context(mock_ctx, region='eu-west-1')

        data = json.loads(result.content[0].text)
        assert data['success'] is True
        assert data['profile'] == 'existing-profile'
        assert data['region'] == 'eu-west-1'

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_set_aws_context_clears_aws_client_cache(self, handler, mock_ctx):
        """Test that set_aws_context clears the AWS client cache."""
        # Add a mock client to the cache
        AwsHelper._client_cache['eks'] = MagicMock()

        # Set new context
        await handler.set_aws_context(mock_ctx, profile='new-profile')

        # Verify cache was cleared
        assert len(AwsHelper._client_cache) == 0

    @pytest.mark.asyncio
    @patch.dict(os.environ, {'EKS_AUTH_MODE': 'iam'}, clear=True)
    async def test_set_aws_context_clears_k8s_client_cache(self, handler, mock_ctx):
        """Test that set_aws_context clears the Kubernetes client cache."""
        # Initialize the K8sClientCache singleton
        k8s_cache = K8sClientCache()
        k8s_cache._client_cache['test-cluster'] = MagicMock()

        # Set new context
        await handler.set_aws_context(mock_ctx, profile='new-profile')

        # Verify K8s cache was cleared
        assert len(k8s_cache._client_cache) == 0


class TestAwsContextData:
    """Tests for the AwsContextData model."""

    def test_data_model_fields(self):
        """Test that AwsContextData has expected fields."""
        data = AwsContextData(
            success=True,
            profile='test-profile',
            region='us-west-2',
            message='Test message',
        )

        assert data.success is True
        assert data.profile == 'test-profile'
        assert data.region == 'us-west-2'
        assert data.message == 'Test message'

    def test_data_model_nullable_fields(self):
        """Test that profile and region can be None."""
        data = AwsContextData(
            success=True,
            profile=None,
            region=None,
            message='No profile or region set',
        )

        assert data.profile is None
        assert data.region is None
