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

"""Tests for create_cluster tool."""

import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_cluster.create_cluster import create_db_cluster


class TestCreateCluster:
    """Test cases for create_db_cluster function."""

    @pytest.mark.asyncio
    async def test_create_cluster_success(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test successful cluster creation."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'MasterUsername': 'admin',
                'Endpoint': 'test-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
                'Port': 3306,
                'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        assert result['message'] == 'DB cluster test-cluster has been created successfully.'
        assert result['formatted_cluster']['cluster_id'] == 'test-cluster'
        assert 'DBCluster' in result

    @pytest.mark.asyncio
    async def test_create_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster creation in readonly mode."""
        result = await create_db_cluster(
            db_cluster_identifier='test-cluster', engine='aurora-mysql', master_username='admin'
        )

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_create_cluster_with_optional_params(
        self, mock_rds_client, mock_rds_context_allowed, mock_asyncio_thread
    ):
        """Test cluster creation with optional parameters."""
        mock_rds_client.create_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'creating',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.mysql_aurora.2.10.2',
                'MasterUsername': 'admin',
                'Endpoint': 'test-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
                'Port': 3306,
                'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
            }
        }

        async def async_return(func, **kwargs):
            return func(**kwargs)

        mock_asyncio_thread.side_effect = async_return

        result = await create_db_cluster(
            db_cluster_identifier='test-cluster',
            engine='aurora-mysql',
            master_username='admin',
            database_name='testdb',
            backup_retention_period=7,
            port=3306,
        )

        assert result['message'] == 'DB cluster test-cluster has been created successfully.'
        mock_asyncio_thread.assert_called_once()
        call_args = mock_asyncio_thread.call_args[1]
        assert call_args['DatabaseName'] == 'testdb'
        assert call_args['BackupRetentionPeriod'] == 7
        assert call_args['Port'] == 3306
