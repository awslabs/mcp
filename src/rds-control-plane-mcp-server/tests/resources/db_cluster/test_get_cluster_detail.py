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

"""Tests for get_cluster_detail resource."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_cluster.get_cluster_detail import (
    get_cluster_detail,
)
from datetime import datetime
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_get_cluster_detail_success():
    """Test successful retrieval of cluster details."""
    cluster_id = 'test-cluster-1'
    create_time = datetime(2023, 1, 1, 12, 0, 0)

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters.return_value = {
        'DBClusters': [
            {
                'DBClusterIdentifier': cluster_id,
                'Status': 'available',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.12',
                'Endpoint': 'test-cluster-1.cluster-abc123.us-east-1.rds.amazonaws.com',
                'ReaderEndpoint': 'test-cluster-1.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
                'MultiAZ': True,
                'ClusterCreateTime': create_time,
                'BackupRetentionPeriod': 7,
                'PreferredBackupWindow': '03:00-04:00',
                'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                'DBClusterMembers': [
                    {
                        'DBInstanceIdentifier': 'test-instance-1',
                        'IsClusterWriter': True,
                        'DBClusterParameterGroupStatus': 'in-sync',
                    },
                    {
                        'DBInstanceIdentifier': 'test-instance-2',
                        'IsClusterWriter': False,
                        'DBClusterParameterGroupStatus': 'in-sync',
                    },
                ],
                'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-12345', 'Status': 'active'}],
                'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
            }
        ]
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client,
    ):
        result = await get_cluster_detail(cluster_id)

        mock_rds_client.describe_db_clusters.assert_called_once_with(
            DBClusterIdentifier=cluster_id
        )

        result_dict = json.loads(result)

        assert result_dict['cluster_id'] == cluster_id
        assert result_dict['status'] == 'available'
        assert result_dict['engine'] == 'aurora-mysql'
        assert result_dict['engine_version'] == '5.7.12'
        assert result_dict['resource_uri'] == 'aws-rds://db-cluster/' + cluster_id

        assert (
            result_dict['endpoint'] == 'test-cluster-1.cluster-abc123.us-east-1.rds.amazonaws.com'
        )
        assert (
            result_dict['reader_endpoint']
            == 'test-cluster-1.cluster-ro-abc123.us-east-1.rds.amazonaws.com'
        )

        assert result_dict['multi_az'] is True
        assert result_dict['backup_retention'] == 7
        assert result_dict['preferred_backup_window'] == '03:00-04:00'
        assert result_dict['preferred_maintenance_window'] == 'sun:05:00-sun:06:00'

        assert len(result_dict['members']) == 2
        writer = next(m for m in result_dict['members'] if m['is_writer'])
        reader = next(m for m in result_dict['members'] if not m['is_writer'])
        assert writer['instance_id'] == 'test-instance-1'
        assert reader['instance_id'] == 'test-instance-2'
        assert writer['status'] == 'in-sync'
        assert reader['status'] == 'in-sync'

        assert len(result_dict['vpc_security_groups']) == 1
        assert result_dict['vpc_security_groups'][0]['id'] == 'sg-12345'
        assert result_dict['vpc_security_groups'][0]['status'] == 'active'

        assert 'Environment' in result_dict['tags']
        assert result_dict['tags']['Environment'] == 'Production'


@pytest.mark.asyncio
async def test_get_cluster_detail_not_found():
    """Test get_cluster_detail when cluster is not found."""
    cluster_id = 'non-existent-cluster'

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters.return_value = {'DBClusters': []}

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client,
    ):
        result = await get_cluster_detail(cluster_id)

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert f'Cluster {cluster_id} not found' == result_dict['error']


@pytest.mark.asyncio
async def test_get_cluster_detail_client_error():
    """Test get_cluster_detail when RDS client raises an error."""
    from botocore.exceptions import ClientError

    cluster_id = 'test-error'

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters.side_effect = ClientError(
        {
            'Error': {
                'Code': 'DBClusterNotFoundFault',
                'Message': f'DBCluster {cluster_id} not found',
            }
        },
        'DescribeDBClusters',
    )

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client,
    ):
        result = await get_cluster_detail(cluster_id)

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'error_code' in result_dict
        assert result_dict['error_code'] == 'DBClusterNotFoundFault'
        assert f'DBCluster {cluster_id} not found' in result_dict['error_message']
