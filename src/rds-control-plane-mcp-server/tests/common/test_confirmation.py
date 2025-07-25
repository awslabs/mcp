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

"""Tests for the confirmation module in the RDS Control Plane MCP Server."""

import pytest
from awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation import (
    _pending_operations,
    require_confirmation,
)
from awslabs.rds_control_plane_mcp_server.common.decorators.readonly_check import (
    readonly_check,
)
from unittest.mock import patch


class TestReadOnlyCheckDecorator:
    """Test the readonly_check decorator."""

    @pytest.mark.asyncio
    @patch('awslabs.rds_control_plane_mcp_server.common.context.RDSContext.readonly_mode')
    async def test_operation_allowed_when_not_readonly(self, mock_readonly_mode):
        """Test operations are allowed when not in readonly mode."""
        mock_readonly_mode.return_value = False

        @readonly_check
        async def create_test():
            return {'result': 'success'}

        result = await create_test()
        assert result == {'result': 'success'}

    @pytest.mark.asyncio
    @patch('awslabs.rds_control_plane_mcp_server.common.context.RDSContext.readonly_mode')
    async def test_operation_blocked_in_readonly_mode(self, mock_readonly_mode):
        """Test operations return error response in readonly mode."""
        mock_readonly_mode.return_value = True

        @readonly_check
        async def create_test():
            return {'result': 'success'}

        result = await create_test()
        assert 'error' in result
        assert 'read-only mode' in result['error']
        assert result['operation'] == 'create_test'


class TestRequireConfirmationDecorator:
    """Test the require_confirmation decorator."""

    def setup_method(self):
        """Clear pending operations before each test."""
        _pending_operations.clear()

    @pytest.mark.asyncio
    async def test_confirmation_required_without_token(self):
        """Test confirmation is required when no token is provided."""

        @require_confirmation('DeleteDBCluster')
        async def delete_cluster(db_cluster_identifier):
            return {'result': 'deleted'}

        result = await delete_cluster(db_cluster_identifier='test-cluster')
        
        assert result['requires_confirmation'] is True
        assert 'warning' in result
        assert 'WARNING' in result['warning']
        assert 'confirmation_token' in result
        assert result['confirmation_token'] is not None

    @pytest.mark.asyncio
    async def test_confirmation_with_valid_token(self):
        """Test operation proceeds with valid confirmation token."""
        # First call without token to get one
        @require_confirmation('DeleteDBCluster')
        async def delete_cluster(db_cluster_identifier, confirmation_token=None):
            return {'result': 'deleted'}

        # Get confirmation token
        result1 = await delete_cluster(db_cluster_identifier='test-cluster')
        token = result1['confirmation_token']
        
        # Use token to confirm
        result2 = await delete_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )
        assert result2 == {'result': 'deleted'}
        assert token not in _pending_operations  # Token should be removed after use

    @pytest.mark.asyncio
    async def test_confirmation_with_invalid_token(self):
        """Test error returned with invalid confirmation token."""

        @require_confirmation('DeleteDBCluster')
        async def delete_cluster(db_cluster_identifier, confirmation_token=None):
            return {'result': 'deleted'}

        result = await delete_cluster(
            db_cluster_identifier='test-cluster', confirmation_token='invalid-token'
        )
        assert 'error' in result
        assert 'Invalid or expired confirmation token' in result['error']

    @pytest.mark.asyncio
    async def test_confirmation_with_mismatched_parameters(self):
        """Test error returned when parameters don't match token."""
        @require_confirmation('DeleteDBCluster')
        async def delete_cluster(db_cluster_identifier, confirmation_token=None):
            return {'result': 'deleted'}

        # Get token for one cluster
        result1 = await delete_cluster(db_cluster_identifier='cluster-1')
        token = result1['confirmation_token']
        
        # Try to use token for different cluster
        result2 = await delete_cluster(
            db_cluster_identifier='cluster-2', confirmation_token=token
        )
        assert 'error' in result2
        assert 'Parameter mismatch' in result2['error']


# These tests have been moved to test_utils.py
