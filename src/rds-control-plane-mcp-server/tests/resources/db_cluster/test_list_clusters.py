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

"""Tests for list_clusters resource."""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from awslabs.rds_control_plane_mcp_server.resources.db_cluster.list_clusters import list_clusters
from awslabs.rds_control_plane_mcp_server.common.constants import RESOURCE_PREFIX_DB_CLUSTER


@pytest.mark.asyncio
async def test_list_clusters_success():
    """Test successful retrieval of cluster list."""
    create_time = datetime(2023, 1, 1, 12, 0, 0)

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters.return_value = {
        'DBClusters': [
            {
                'DBClusterIdentifier': 'test-cluster-1',
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
                        'DBClusterParameterGroupStatus': 'in-sync'
                    }
                ],
                'VpcSecurityGroups': [
                    {
                        'VpcSecurityGroupId': 'sg-12345',
                        'Status': 'active'
                    }
                ],
                'TagList': [
                    {
                        'Key': 'Environment',
                        'Value': 'Production'
                    }
                ]
            },
            {
                'DBClusterIdentifier': 'test-cluster-2',
                'Status': 'available',
                'Engine': 'aurora-postgresql',
                'EngineVersion': '13.6',
                'Endpoint': 'test-cluster-2.cluster-def456.us-east-1.rds.amazonaws.com',
                'ReaderEndpoint': 'test-cluster-2.cluster-ro-def456.us-east-1.rds.amazonaws.com',
                'MultiAZ': False,
                'ClusterCreateTime': create_time,
                'BackupRetentionPeriod': 14,
                'PreferredBackupWindow': '04:00-05:00',
                'PreferredMaintenanceWindow': 'mon:05:00-mon:06:00',
                'DBClusterMembers': [],
                'VpcSecurityGroups': [],
                'TagList': []
            }
        ]
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_clusters()

        result_dict = json.loads(result)

        assert 'clusters' in result_dict
        assert 'count' in result_dict
        assert 'resource_uri' in result_dict

        assert result_dict['count'] == 2
        assert len(result_dict['clusters']) == 2
        assert result_dict['resource_uri'] == RESOURCE_PREFIX_DB_CLUSTER

        cluster1 = result_dict['clusters'][0]
        assert cluster1['cluster_id'] == 'test-cluster-1'
        assert cluster1['status'] == 'available'
        assert cluster1['engine'] == 'aurora-mysql'
        assert cluster1['engine_version'] == '5.7.12'
        assert cluster1['endpoint'] == 'test-cluster-1.cluster-abc123.us-east-1.rds.amazonaws.com'
        assert cluster1['reader_endpoint'] == 'test-cluster-1.cluster-ro-abc123.us-east-1.rds.amazonaws.com'
        assert cluster1['multi_az'] is True
        assert cluster1['backup_retention'] == 7
        assert len(cluster1['members']) == 1
        assert len(cluster1['vpc_security_groups']) == 1
        assert 'Environment' in cluster1['tags']
        assert cluster1['tags']['Environment'] == 'Production'

        cluster2 = result_dict['clusters'][1]
        assert cluster2['cluster_id'] == 'test-cluster-2'
        assert cluster2['engine'] == 'aurora-postgresql'
        assert cluster2['engine_version'] == '13.6'
        assert cluster2['multi_az'] is False
        assert cluster2['backup_retention'] == 14
        assert len(cluster2['members']) == 0
        assert len(cluster2['vpc_security_groups']) == 0
        assert len(cluster2['tags']) == 0


@pytest.mark.asyncio
async def test_list_clusters_empty():
    """Test list_clusters when no clusters exist."""
    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters.return_value = {
        'DBClusters': []
    }

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_clusters()

        result_dict = json.loads(result)
        assert result_dict['clusters'] == []
        assert result_dict['count'] == 0
        assert result_dict['resource_uri'] == RESOURCE_PREFIX_DB_CLUSTER


@pytest.mark.asyncio
async def test_list_clusters_with_pagination():
    """Test list_clusters with pagination."""
    create_time = datetime(2023, 1, 1, 12, 0, 0)

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters.side_effect = [
        {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster-1',
                    'Status': 'available',
                    'Engine': 'aurora-mysql',
                    'ClusterCreateTime': create_time,
                    'DBClusterMembers': [],
                    'VpcSecurityGroups': [],
                    'TagList': []
                }
            ],
            'Marker': 'next-page'
        },
        {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster-2',
                    'Status': 'available',
                    'Engine': 'aurora-postgresql',
                    'ClusterCreateTime': create_time,
                    'DBClusterMembers': [],
                    'VpcSecurityGroups': [],
                    'TagList': []
                }
            ]
        }
    ]

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_clusters()

        assert mock_rds_client.describe_db_clusters.call_count == 2

        result_dict = json.loads(result)
        assert result_dict['count'] == 2
        assert len(result_dict['clusters']) == 2

        cluster_ids = [c['cluster_id'] for c in result_dict['clusters']]
        assert 'test-cluster-1' in cluster_ids
        assert 'test-cluster-2' in cluster_ids


@pytest.mark.asyncio
async def test_list_clusters_client_error():
    """Test list_clusters when RDS client raises an error."""
    from botocore.exceptions import ClientError

    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters.side_effect = ClientError(
        {
            'Error': {
                'Code': 'InvalidParameterCombination',
                'Message': 'Invalid parameter combination'
            }
        },
        'DescribeDBClusters'
    )

    with patch(
        'awslabs.rds_control_plane_mcp_server.common.connection.RDSConnectionManager.get_connection',
        return_value=mock_rds_client
    ):
        result = await list_clusters()

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'error_code' in result_dict
        assert result_dict['error_code'] == 'InvalidParameterCombination'
        assert 'Invalid parameter combination' in result_dict['error_message']
