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
from awslabs.rds_control_plane_mcp_server.common.confirmation import (
    _pending_operations,
    add_pending_operation,
    readonly_check,
    require_confirmation,
)
from awslabs.rds_control_plane_mcp_server.common.exceptions import (
    ConfirmationRequiredException,
    ReadOnlyModeException,
)
from unittest.mock import patch


class TestReadOnlyCheckDecorator:
    """Test the readonly_check decorator."""

    @pytest.mark.asyncio
    @patch('awslabs.rds_control_plane_mcp_server.common.confirmation.RDSContext.readonly_mode')
    async def test_read_operation_allowed_in_readonly_mode(self, mock_readonly_mode):
        """Test read operations are allowed in readonly mode."""
        mock_readonly_mode.return_value = True

        @readonly_check
        async def describe_test():
            return {'result': 'success'}

        result = await describe_test()
        assert result == {'result': 'success'}

    @pytest.mark.asyncio
    @patch('awslabs.rds_control_plane_mcp_server.common.confirmation.RDSContext.readonly_mode')
    async def test_write_operation_blocked_in_readonly_mode(self, mock_readonly_mode):
        """Test write operations are blocked in readonly mode."""
        mock_readonly_mode.return_value = True

        @readonly_check
        async def create_test():
            return {'result': 'success'}

        with pytest.raises(ReadOnlyModeException) as exc_info:
            await create_test()
        assert exc_info.value.operation == 'create_test'

    @pytest.mark.asyncio
    @patch('awslabs.rds_control_plane_mcp_server.common.confirmation.RDSContext.readonly_mode')
    async def test_write_operation_allowed_when_not_readonly(self, mock_readonly_mode):
        """Test write operations are allowed when not in readonly mode."""
        mock_readonly_mode.return_value = False

        @readonly_check
        async def create_test():
            return {'result': 'success'}

        result = await create_test()
        assert result == {'result': 'success'}


class TestRequireConfirmationDecorator:
    """Test the require_confirmation decorator."""

    @pytest.mark.asyncio
    async def test_confirmation_required_without_token(self):
        """Test confirmation is required when no token is provided."""

        @require_confirmation('delete_db_cluster')
        async def delete_cluster(db_cluster_identifier):
            return {'result': 'deleted'}

        with pytest.raises(ConfirmationRequiredException) as exc_info:
            await delete_cluster(db_cluster_identifier='test-cluster')

        assert exc_info.value.operation == 'delete_db_cluster'
        assert exc_info.value.confirmation_token is not None

    @pytest.mark.asyncio
    async def test_confirmation_with_valid_token(self):
        """Test operation proceeds with valid confirmation token."""
        # Add a pending operation
        token = add_pending_operation(
            'delete_db_cluster', {'db_cluster_identifier': 'test-cluster'}
        )

        @require_confirmation('delete_db_cluster')
        async def delete_cluster(db_cluster_identifier, confirmation_token=None):
            return {'result': 'deleted'}

        result = await delete_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )
        assert result == {'result': 'deleted'}
        assert token not in _pending_operations  # Token should be removed after use

    @pytest.mark.asyncio
    async def test_confirmation_with_invalid_token(self):
        """Test error returned with invalid confirmation token."""

        @require_confirmation('delete_db_cluster')
        async def delete_cluster(db_cluster_identifier, confirmation_token=None):
            return {'result': 'deleted'}

        result = await delete_cluster(
            db_cluster_identifier='test-cluster', confirmation_token='invalid-token'
        )
        assert 'error' in result
        assert 'Invalid or expired confirmation token' in result['error']

    @pytest.mark.asyncio
    async def test_confirmation_with_mismatched_operation(self):
        """Test error returned when operation type doesn't match token."""
        # Add a pending operation for a different operation type
        token = add_pending_operation(
            'modify_db_cluster', {'db_cluster_identifier': 'test-cluster'}
        )

        @require_confirmation('delete_db_cluster')
        async def delete_cluster(db_cluster_identifier, confirmation_token=None):
            return {'result': 'deleted'}

        result = await delete_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )
        assert 'error' in result
        assert 'Invalid operation type' in result['error']

    @pytest.mark.asyncio
    async def test_confirmation_with_mismatched_parameters(self):
        """Test error returned when parameters don't match token."""
        # Add a pending operation with different parameters
        token = add_pending_operation(
            'delete_db_cluster', {'db_cluster_identifier': 'other-cluster'}
        )

        @require_confirmation('delete_db_cluster')
        async def delete_cluster(db_cluster_identifier, confirmation_token=None):
            return {'result': 'deleted'}

        result = await delete_cluster(
            db_cluster_identifier='test-cluster', confirmation_token=token
        )
        assert 'error' in result
        assert 'Parameter mismatch' in result['error']


# These tests have been moved to test_utils.py
