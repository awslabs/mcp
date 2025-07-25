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

"""Tests for delete_cluster tool."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_cluster.delete_cluster import (
    delete_db_cluster,
)
from unittest.mock import patch


class TestDeleteCluster:
    """Test cases for delete_db_cluster function."""

    @pytest.mark.asyncio
    async def test_delete_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster deletion in readonly mode."""
        result = await delete_db_cluster(
            db_cluster_identifier='test-cluster', skip_final_snapshot=True
        )

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_delete_cluster_no_confirmation(self, mock_rds_context_allowed):
        """Test cluster deletion without confirmation token."""
        result = await delete_db_cluster(
            db_cluster_identifier='test-cluster', skip_final_snapshot=True
        )

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result
        assert 'WARNING' in result['warning']

    @pytest.mark.asyncio
    async def test_delete_cluster_with_valid_token(
        self, mock_rds_client, mock_rds_context_allowed
    ):
        """Test cluster deletion with valid confirmation token."""
        mock_rds_client.delete_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'deleting',
                'Engine': 'aurora-mysql',
            }
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation._pending_operations',
            {'valid-token': (
                'DeleteDBCluster',
                {'db_cluster_identifier': 'test-cluster', 'skip_final_snapshot': True},
                9999999999,
            )}
        ):
            result = await delete_db_cluster(
                db_cluster_identifier='test-cluster',
                skip_final_snapshot=True,
                confirmation_token='valid-token',
            )

            assert result['message'] == 'DB cluster test-cluster has been deleted successfully.'

    @pytest.mark.asyncio
    async def test_delete_cluster_invalid_token(self, mock_rds_context_allowed):
        """Test cluster deletion with invalid confirmation token."""
        result = await delete_db_cluster(
            db_cluster_identifier='test-cluster',
            skip_final_snapshot=True,
            confirmation_token='invalid-token',
        )

        assert 'error' in result
        assert 'Invalid or expired confirmation token' in result['error']
