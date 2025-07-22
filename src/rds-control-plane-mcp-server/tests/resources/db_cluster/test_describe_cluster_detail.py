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

"""Tests for describe_cluster_detail resource."""

import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_cluster.describe_cluster_detail import (
    Cluster,
    ClusterMember,
    describe_cluster_detail,
)
from datetime import datetime
from typing import Any


class TestDescribeClusterDetail:
    """Test describe_cluster_detail function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_rds_client):
        """Test successful cluster detail retrieval."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster',
                    'Status': 'available',
                    'Engine': 'aurora-mysql',
                    'EngineVersion': '5.7.12',
                    'Endpoint': 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                    'ReaderEndpoint': 'test-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
                    'MultiAZ': True,
                    'BackupRetentionPeriod': 7,
                    'PreferredBackupWindow': '03:00-04:00',
                    'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                    'ClusterCreateTime': datetime(2024, 1, 1, 12, 0, 0),
                    'DBClusterMembers': [
                        {
                            'DBInstanceIdentifier': 'test-instance-1',
                            'IsClusterWriter': True,
                            'DBClusterParameterGroupStatus': 'in-sync',
                        }
                    ],
                    'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345', 'Status': 'active'}],
                    'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
                }
            ]
        }

        result = await describe_cluster_detail(cluster_id='test-cluster')

        assert result.cluster_id == 'test-cluster'
        assert result.status == 'available'
        assert result.engine == 'aurora-mysql'
        assert result.engine_version == '5.7.12'
        assert result.multi_az is True
        assert result.backup_retention == 7
        assert len(result.members) == 1
        assert result.members[0].instance_id == 'test-instance-1'
        assert result.members[0].is_writer is True
        assert result.tags['Environment'] == 'Production'

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_parameters(self, mock_rds_client):
        """Test API is called with correct parameters."""
        mock_rds_client.describe_db_clusters.return_value = {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster',
                    'Status': 'available',
                    'Engine': 'aurora-mysql',
                    'MultiAZ': False,
                    'BackupRetentionPeriod': 1,
                    'DBClusterMembers': [],
                    'VpcSecurityGroups': [],
                    'TagList': [],
                }
            ]
        }

        await describe_cluster_detail(cluster_id='test-cluster')

        mock_rds_client.describe_db_clusters.assert_called_once_with(
            DBClusterIdentifier='test-cluster'
        )


class TestCluster:
    """Test Cluster model."""

    def test_from_db_cluster_typedef(self):
        """Test model creation from AWS API response."""
        api_response: Any = {
            'DBClusterIdentifier': 'test-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'EngineVersion': '5.7.12',
            'Endpoint': 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
            'MultiAZ': True,
            'BackupRetentionPeriod': 7,
            'DBClusterMembers': [
                {
                    'DBInstanceIdentifier': 'test-instance-1',
                    'IsClusterWriter': True,
                    'DBClusterParameterGroupStatus': 'in-sync',
                }
            ],
            'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345', 'Status': 'active'}],
            'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
        }

        cluster = Cluster.from_DBClusterTypeDef(api_response)

        assert cluster.cluster_id == 'test-cluster'
        assert cluster.status == 'available'
        assert cluster.engine == 'aurora-mysql'
        assert cluster.multi_az is True
        assert cluster.backup_retention == 7
        assert len(cluster.members) == 1
        assert cluster.members[0].instance_id == 'test-instance-1'
        assert cluster.tags['Environment'] == 'Production'
        assert cluster.resource_uri == 'aws-rds://db-cluster/test-cluster'

    def test_handles_missing_fields(self):
        """Test model handles missing API response fields."""
        api_response: Any = {
            'DBClusterIdentifier': 'test-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
        }

        cluster = Cluster.from_DBClusterTypeDef(api_response)

        assert cluster.cluster_id == 'test-cluster'
        assert cluster.engine_version is None
        assert cluster.endpoint is None
        assert cluster.multi_az is False
        assert cluster.backup_retention == 0
        assert len(cluster.members) == 0
        assert len(cluster.vpc_security_groups) == 0
        assert len(cluster.tags) == 0


class TestClusterMember:
    """Test ClusterMember model."""

    def test_model_creation(self):
        """Test cluster member model creation."""
        member = ClusterMember(instance_id='test-instance-1', is_writer=True, status='in-sync')

        assert member.instance_id == 'test-instance-1'
        assert member.is_writer is True
        assert member.status == 'in-sync'
