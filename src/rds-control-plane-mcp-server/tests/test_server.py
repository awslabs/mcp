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

"""Tests for the RDS Control Plane MCP Server resources."""

import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import boto3

from awslabs.rds_control_plane_mcp_server.server import (
    get_cluster_resource,
    get_instance_resource,
    list_clusters_resource,
    list_instances_resource,
)
from awslabs.rds_control_plane_mcp_server.resources import (
    get_cluster_list_resource,
    get_cluster_detail_resource,
    get_instance_list_resource,
    get_instance_detail_resource,
)


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest_asyncio.fixture
async def rds_client(aws_credentials):
    """RDS client fixture with mock database setup."""
    client = MagicMock()
    
    client.describe_db_clusters = MagicMock(return_value={
        'DBClusters': [
            {
                'DBClusterIdentifier': 'test-cluster',
                'Engine': 'aurora-mysql',
                'Status': 'available',
                'Endpoint': 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                'ReaderEndpoint': 'test-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
                'MultiAZ': True,
                'BackupRetentionPeriod': 7,
                'PreferredBackupWindow': '07:00-09:00',
                'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                'DBClusterMembers': [
                    {
                        'DBInstanceIdentifier': 'test-instance-1',
                        'IsClusterWriter': True,
                        'DBClusterParameterGroupStatus': 'in-sync',
                    }
                ],
                'VpcSecurityGroups': [
                    {
                        'VpcSecurityGroupId': 'sg-12345',
                        'Status': 'active',
                    }
                ],
                'TagList': [
                    {
                        'Key': 'Environment',
                        'Value': 'Test',
                    }
                ],
            }
        ]
    })
    
    client.describe_db_instances = MagicMock(return_value={
        'DBInstances': [
            {
                'DBInstanceIdentifier': 'test-instance-1',
                'DBClusterIdentifier': 'test-cluster',
                'Engine': 'aurora-mysql',
                'EngineVersion': '5.7.12',
                'DBInstanceClass': 'db.r5.large',
                'DBInstanceStatus': 'available',
                'AvailabilityZone': 'us-east-1a',
                'MultiAZ': False,
                'PubliclyAccessible': False,
                'StorageType': 'aurora',
                'StorageEncrypted': True,
                'Endpoint': {
                    'Address': 'test-instance-1.abc123.us-east-1.rds.amazonaws.com',
                    'Port': 3306,
                    'HostedZoneId': 'Z2R2ITUGPM61AM',
                },
                'TagList': []
            },
            {
                'DBInstanceIdentifier': 'test-instance-2',
                'Engine': 'mysql',
                'EngineVersion': '8.0.23',
                'DBInstanceClass': 'db.t3.medium',
                'DBInstanceStatus': 'available',
                'AvailabilityZone': 'us-east-1b',
                'MultiAZ': False,
                'PubliclyAccessible': False,
                'StorageType': 'gp2',
                'AllocatedStorage': 20,
                'StorageEncrypted': False,
                'Endpoint': {
                    'Address': 'test-instance-2.def456.us-east-1.rds.amazonaws.com',
                    'Port': 3306,
                    'HostedZoneId': 'Z2R2ITUGPM61AM',
                },
                'TagList': []
            }
        ]
    })
    
    yield client


@pytest.mark.asyncio
async def test_get_cluster_list_resource(rds_client):
    """Test retrieving cluster list resource."""
    with patch('awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread') as mock_to_thread:
        mock_to_thread.return_value = {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster',
                    'Engine': 'aurora-mysql',
                    'Status': 'available',
                    'Endpoint': 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                    'ReaderEndpoint': 'test-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
                    'MultiAZ': True,
                    'BackupRetentionPeriod': 7,
                    'PreferredBackupWindow': '07:00-09:00',
                    'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                    'DBClusterMembers': [
                        {
                            'DBInstanceIdentifier': 'test-instance-1',
                            'IsClusterWriter': True,
                            'DBClusterParameterGroupStatus': 'in-sync',
                        }
                    ],
                    'VpcSecurityGroups': [
                        {
                            'VpcSecurityGroupId': 'sg-12345',
                            'Status': 'active',
                        }
                    ],
                    'TagList': [
                        {
                            'Key': 'Environment',
                            'Value': 'Test',
                        }
                    ],
                }
            ]
        }
        
        result = await get_cluster_list_resource(rds_client)
        
        # Verify result
        result_json = json.loads(result)
        assert result_json['count'] == 1
        assert result_json['clusters'][0]['cluster_id'] == 'test-cluster'
        assert result_json['clusters'][0]['engine'] == 'aurora-mysql'
        assert result_json['resource_uri'] == 'aws-rds://db-cluster'


@pytest.mark.asyncio
async def test_get_cluster_detail_resource(rds_client):
    """Test retrieving cluster detail resource."""
    with patch('awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread') as mock_to_thread:
        mock_to_thread.return_value = {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'test-cluster',
                    'Engine': 'aurora-mysql',
                    'EngineVersion': '5.7.12',
                    'Status': 'available',
                    'Endpoint': 'test-cluster.cluster-abc123.us-east-1.rds.amazonaws.com',
                    'ReaderEndpoint': 'test-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com',
                    'MultiAZ': True,
                    'BackupRetentionPeriod': 7,
                    'PreferredBackupWindow': '07:00-09:00',
                    'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                    'DBClusterMembers': [
                        {
                            'DBInstanceIdentifier': 'test-instance-1',
                            'IsClusterWriter': True,
                            'DBClusterParameterGroupStatus': 'in-sync',
                        }
                    ],
                    'VpcSecurityGroups': [
                        {
                            'VpcSecurityGroupId': 'sg-12345',
                            'Status': 'active',
                        }
                    ],
                    'TagList': [
                        {
                            'Key': 'Environment',
                            'Value': 'Test',
                        }
                    ],
                }
            ]
        }
        
        result = await get_cluster_detail_resource('test-cluster', rds_client)
        
        result_json = json.loads(result)
        assert result_json['cluster_id'] == 'test-cluster'
        assert result_json['engine'] == 'aurora-mysql'
        assert result_json['engine_version'] == '5.7.12'
        assert result_json['status'] == 'available'
        assert result_json['members'][0]['instance_id'] == 'test-instance-1'
        assert result_json['resource_uri'] == 'aws-rds://db-cluster/test-cluster'


@pytest.mark.asyncio
async def test_get_instance_list_resource(rds_client):
    """Test retrieving instance list resource."""
    with patch('awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread') as mock_to_thread:
        mock_to_thread.return_value = {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-instance-1',
                    'DBClusterIdentifier': 'test-cluster',
                    'Engine': 'aurora-mysql',
                    'EngineVersion': '5.7.12',
                    'DBInstanceClass': 'db.r5.large',
                    'DBInstanceStatus': 'available',
                    'AvailabilityZone': 'us-east-1a',
                    'MultiAZ': False,
                    'PubliclyAccessible': False,
                    'StorageType': 'aurora',
                    'StorageEncrypted': True,
                    'Endpoint': {
                        'Address': 'test-instance-1.abc123.us-east-1.rds.amazonaws.com',
                        'Port': 3306,
                        'HostedZoneId': 'Z2R2ITUGPM61AM',
                    },
                    'VpcSecurityGroups': [
                        {
                            'VpcSecurityGroupId': 'sg-12345',
                            'Status': 'active',
                        }
                    ],
                    'TagList': [
                        {
                            'Key': 'Environment',
                            'Value': 'Test',
                        }
                    ],
                },
                {
                    'DBInstanceIdentifier': 'test-instance-2',
                    'Engine': 'mysql',
                    'EngineVersion': '8.0.23',
                    'DBInstanceClass': 'db.t3.medium',
                    'DBInstanceStatus': 'available',
                    'AvailabilityZone': 'us-east-1b',
                    'MultiAZ': False,
                    'PubliclyAccessible': False,
                    'StorageType': 'gp2',
                    'AllocatedStorage': 20,
                    'StorageEncrypted': False,
                    'Endpoint': {
                        'Address': 'test-instance-2.def456.us-east-1.rds.amazonaws.com',
                        'Port': 3306,
                        'HostedZoneId': 'Z2R2ITUGPM61AM',
                    },
                    'VpcSecurityGroups': [
                        {
                            'VpcSecurityGroupId': 'sg-67890',
                            'Status': 'active',
                        }
                    ],
                    'TagList': [
                        {
                            'Key': 'Environment',
                            'Value': 'Development',
                        }
                    ],
                },
            ]
        }
        
        result = await get_instance_list_resource(rds_client)
        
        result_json = json.loads(result)
        assert result_json['count'] == 2
        assert result_json['instances'][0]['instance_id'] == 'test-instance-1'
        assert result_json['instances'][1]['instance_id'] == 'test-instance-2'
        assert result_json['instances'][0]['db_cluster'] == 'test-cluster'
        assert result_json['instances'][1]['db_cluster'] is None
        assert result_json['resource_uri'] == 'aws-rds://db-instance'


@pytest.mark.asyncio
async def test_get_instance_detail_resource(rds_client):
    """Test retrieving instance detail resource."""
    with patch('awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread') as mock_to_thread:
        mock_to_thread.return_value = {
            'DBInstances': [
                {
                    'DBInstanceIdentifier': 'test-instance-1',
                    'DBClusterIdentifier': 'test-cluster',
                    'Engine': 'aurora-mysql',
                    'EngineVersion': '5.7.12',
                    'DBInstanceClass': 'db.r5.large',
                    'DBInstanceStatus': 'available',
                    'AvailabilityZone': 'us-east-1a',
                    'MultiAZ': False,
                    'PubliclyAccessible': False,
                    'StorageType': 'aurora',
                    'StorageEncrypted': True,
                    'Endpoint': {
                        'Address': 'test-instance-1.abc123.us-east-1.rds.amazonaws.com',
                        'Port': 3306,
                        'HostedZoneId': 'Z2R2ITUGPM61AM',
                    },
                    'PreferredBackupWindow': '07:00-09:00',
                    'PreferredMaintenanceWindow': 'sun:05:00-sun:06:00',
                    'VpcSecurityGroups': [
                        {
                            'VpcSecurityGroupId': 'sg-12345',
                            'Status': 'active',
                        }
                    ],
                    'TagList': [
                        {
                            'Key': 'Environment',
                            'Value': 'Test',
                        }
                    ],
                }
            ]
        }
        
        result = await get_instance_detail_resource('test-instance-1', rds_client)
        
        result_json = json.loads(result)
        assert result_json['instance_id'] == 'test-instance-1'
        assert result_json['db_cluster'] == 'test-cluster'
        assert result_json['engine'] == 'aurora-mysql'
        assert result_json['storage']['encrypted'] == True
        assert result_json['endpoint']['address'] == 'test-instance-1.abc123.us-east-1.rds.amazonaws.com'
        assert result_json['endpoint']['port'] == 3306
        assert result_json['resource_uri'] == 'aws-rds://db-instance/test-instance-1'


@pytest.mark.asyncio
async def test_list_clusters_resource():
    """Test the list_clusters_resource function."""
    with patch('awslabs.rds_control_plane_mcp_server.server.get_rds_client') as mock_get_rds_client, \
         patch('awslabs.rds_control_plane_mcp_server.server.get_cluster_list_resource') as mock_get_cluster_list:
        mock_rds_client = MagicMock()
        mock_get_rds_client.return_value = mock_rds_client
        mock_get_cluster_list.return_value = json.dumps({
            'clusters': [{'cluster_id': 'test-cluster'}],
            'count': 1,
            'resource_uri': 'aws-rds://db-cluster'
        })
        
        result = await list_clusters_resource()
        
        mock_get_rds_client.assert_called_once()
        mock_get_cluster_list.assert_called_once_with(mock_rds_client)
        
        result_json = json.loads(result)
        assert result_json['count'] == 1
        assert result_json['clusters'][0]['cluster_id'] == 'test-cluster'


@pytest.mark.asyncio
async def test_get_cluster_resource():
    """Test the get_cluster_resource function."""
    with patch('awslabs.rds_control_plane_mcp_server.server.get_rds_client') as mock_get_rds_client, \
         patch('awslabs.rds_control_plane_mcp_server.server.get_cluster_detail_resource') as mock_get_cluster_detail:
        mock_rds_client = MagicMock()
        mock_get_rds_client.return_value = mock_rds_client
        mock_get_cluster_detail.return_value = json.dumps({
            'cluster_id': 'test-cluster',
            'engine': 'aurora-mysql',
            'status': 'available',
            'resource_uri': 'aws-rds://db-cluster/test-cluster'
        })
        
        result = await get_cluster_resource('test-cluster')
        
        mock_get_rds_client.assert_called_once()
        mock_get_cluster_detail.assert_called_once_with('test-cluster', mock_rds_client)
        
        result_json = json.loads(result)
        assert result_json['cluster_id'] == 'test-cluster'
        assert result_json['resource_uri'] == 'aws-rds://db-cluster/test-cluster'


@pytest.mark.asyncio
async def test_list_instances_resource():
    """Test the list_instances_resource function."""
    with patch('awslabs.rds_control_plane_mcp_server.server.get_rds_client') as mock_get_rds_client, \
         patch('awslabs.rds_control_plane_mcp_server.server.get_instance_list_resource') as mock_get_instance_list:
        mock_rds_client = MagicMock()
        mock_get_rds_client.return_value = mock_rds_client
        mock_get_instance_list.return_value = json.dumps({
            'instances': [
                {'instance_id': 'test-instance-1'},
                {'instance_id': 'test-instance-2'}
            ],
            'count': 2,
            'resource_uri': 'aws-rds://db-instance'
        })
        
        result = await list_instances_resource()
        
        mock_get_rds_client.assert_called_once()
        mock_get_instance_list.assert_called_once_with(mock_rds_client)
        
        result_json = json.loads(result)
        assert result_json['count'] == 2
        assert result_json['instances'][0]['instance_id'] == 'test-instance-1'
        assert result_json['instances'][1]['instance_id'] == 'test-instance-2'


@pytest.mark.asyncio
async def test_get_instance_resource():
    """Test the get_instance_resource function."""
    with patch('awslabs.rds_control_plane_mcp_server.server.get_rds_client') as mock_get_rds_client, \
         patch('awslabs.rds_control_plane_mcp_server.server.get_instance_detail_resource') as mock_get_instance_detail:
        mock_rds_client = MagicMock()
        mock_get_rds_client.return_value = mock_rds_client
        mock_get_instance_detail.return_value = json.dumps({
            'instance_id': 'test-instance-1',
            'db_cluster': 'test-cluster',
            'status': 'available',
            'resource_uri': 'aws-rds://db-instance/test-instance-1'
        })
        
        result = await get_instance_resource('test-instance-1')
        
        mock_get_rds_client.assert_called_once()
        mock_get_instance_detail.assert_called_once_with('test-instance-1', mock_rds_client)
        
        result_json = json.loads(result)
        assert result_json['instance_id'] == 'test-instance-1'
        assert result_json['db_cluster'] == 'test-cluster'
        assert result_json['resource_uri'] == 'aws-rds://db-instance/test-instance-1'


@pytest.mark.asyncio
async def test_error_handling_in_get_cluster_list_resource():
    """Test error handling in get_cluster_list_resource function."""
    mock_rds_client = MagicMock()
    mock_rds_client.describe_db_clusters = MagicMock(side_effect=Exception("Test error"))
    
    with patch('awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread', side_effect=Exception("Test error")):
        result = await get_cluster_list_resource(mock_rds_client)
        
        result_json = json.loads(result)
        assert 'error' in result_json
        assert 'Test error' in result_json['error_message']


@pytest.mark.asyncio
async def test_error_handling_in_get_instance_detail_resource():
    """Test error handling in get_instance_detail_resource function for non-existent instance."""
    with patch('awslabs.rds_control_plane_mcp_server.resources.asyncio.to_thread') as mock_to_thread:
        mock_to_thread.return_value = {'DBInstances': []}
        
        result = await get_instance_detail_resource('non-existent-instance', MagicMock())
        
        result_json = json.loads(result)
        assert 'error' in result_json
        assert 'non-existent-instance' in result_json['error']
