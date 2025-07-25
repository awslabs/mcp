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

"""Tests for modify_cluster tool."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_cluster.modify_cluster import (
    modify_db_cluster,
)


class TestModifyCluster:
    """Test cases for modify_db_cluster function."""

    @pytest.mark.asyncio
    async def test_modify_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster modification in readonly mode."""
        result = await modify_db_cluster(db_cluster_identifier='test-cluster')

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_modify_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster modification."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'modifying',
                'Engine': 'aurora-mysql',
                'BackupRetentionPeriod': 7,
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            backup_retention_period=7,
        )

        assert result['message'] == 'DB cluster test-cluster has been modified successfully.'
        assert 'formatted_cluster' in result

    @pytest.mark.asyncio
    async def test_modify_cluster_with_all_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with all parameters."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'modifying',
                'Engine': 'aurora-mysql',
                'BackupRetentionPeriod': 14,
                'Port': 3307,
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(
            db_cluster_identifier='test-cluster',
            apply_immediately=True,
            backup_retention_period=14,
            vpc_security_group_ids=['sg-12345678'],
            port=3307,
        )

        assert result['message'] == 'DB cluster test-cluster has been modified successfully.'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['ApplyImmediately'] is True
        assert call_args['BackupRetentionPeriod'] == 14
        assert call_args['VpcSecurityGroupIds'] == ['sg-12345678']
        assert call_args['Port'] == 3307

    @pytest.mark.asyncio
    async def test_modify_cluster_minimal_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster modification with minimal parameters."""
        mock_rds_client.modify_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'modifying',
                'Engine': 'aurora-mysql',
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await modify_db_cluster(db_cluster_identifier='test-cluster')

        assert result['message'] == 'DB cluster test-cluster has been modified successfully.'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DBClusterIdentifier'] == 'test-cluster'
