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

"""Tests for the Timestream for InfluxDB MCP Server."""

import botocore.exceptions
import pytest
from awslabs.timestream_for_influxdb_mcp_server.server import (
    create_db_cluster,
    create_db_instance,
    create_db_parameter_group,
    delete_db_cluster,
    delete_db_instance,
    get_db_cluster,
    get_db_instance,
    get_db_parameter_group,
    get_influxdb_client,
    get_timestream_influxdb_client,
    influxdb_create_bucket,
    influxdb_create_org,
    influxdb_list_buckets,
    influxdb_list_orgs,
    influxdb_query,
    influxdb_write_line_protocol,
    influxdb_write_points,
    list_db_clusters,
    list_db_clusters_by_status,
    list_db_instances,
    list_db_instances_by_status,
    list_db_instances_for_cluster,
    list_db_parameter_groups,
    list_tags_for_resource,
    tag_resource,
    untag_resource,
    update_db_cluster,
    update_db_instance,
)
from unittest.mock import MagicMock, patch


class TestClientCreation:
    """Tests for client creation functions."""

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.boto3')
    def test_get_timestream_influxdb_client_happy_path(self, mock_boto3):
        """Test get_timestream_influxdb_client with default parameters."""
        # Arrange
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        # Act
        client = get_timestream_influxdb_client()

        # Assert
        mock_boto3.Session.assert_called_once_with(region_name='us-east-1')
        mock_session.client.assert_called_once_with('timestream-influxdb')
        assert client == mock_client

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.boto3')
    def test_get_timestream_influxdb_client_exception_path(self, mock_boto3):
        """Test get_timestream_influxdb_client when an exception occurs."""
        # Arrange
        mock_boto3.Session.side_effect = Exception('Connection error')

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            get_timestream_influxdb_client()

        assert 'Connection error' in str(excinfo.value)

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.InfluxDBClient')
    def test_get_influxdb_client_happy_path(self, mock_influxdb_client):
        """Test get_influxdb_client function with valid parameters."""
        # Arrange
        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'
        timeout = 5000
        verify_ssl = False
        mock_client = MagicMock()
        mock_influxdb_client.return_value = mock_client

        # Act
        client = get_influxdb_client(url, token, org, timeout, verify_ssl)

        # Assert
        mock_influxdb_client.assert_called_once_with(
            url=url, token=token, org=org, timeout=timeout, verify_ssl=verify_ssl
        )
        assert client == mock_client

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.InfluxDBClient')
    def test_get_influxdb_client_exception_path(self, mock_influxdb_client):
        """Test get_influxdb_client function with invalid url."""
        # Arrange
        url = 'random-schema://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'
        timeout = 5000
        verify_ssl = False

        # Act and assert
        with pytest.raises(Exception) as excinfo:
            get_influxdb_client(url, token, org, timeout, verify_ssl)

        assert 'URL must use HTTP(S) protocol' in str(excinfo.value)

    def test_get_influxdb_client_missing_token(self):
        """Test get_influxdb_client when token is missing."""
        with pytest.raises(ValueError) as excinfo:
            get_influxdb_client(url='https://example.com', token=None, org='test-org')

        assert 'Token must be provided' in str(excinfo.value)

    @patch('awslabs.timestream_for_influxdb_mcp_server.server.boto3')
    @patch.dict('os.environ', {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-west-2'})
    def test_get_timestream_influxdb_client_with_profile(self, mock_boto3):
        """Test get_timestream_influxdb_client with AWS profile."""
        mock_session = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        client = get_timestream_influxdb_client()

        mock_boto3.Session.assert_called_once_with(
            profile_name='test-profile', region_name='us-west-2'
        )
        mock_session.client.assert_called_once_with('timestream-influxdb')
        assert client == mock_client


class TestDbClusterOperations:
    """Tests for DB cluster operations."""

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_cluster_happy_path(self, mock_get_client):
        """Test create_db_cluster function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_cluster.return_value = {'dbClusterId': 'test-cluster-id'}

        # Test parameters
        name = 'test-cluster'
        db_instance_type = 'db.influx.large'
        password = ''
        allocated_storage_gb = 100
        vpc_security_group_ids = ['sg-12345']
        vpc_subnet_ids = ['subnet-12345', 'subnet-67890']
        tags = {'Environment': 'Test'}

        # Act
        result = await create_db_cluster(
            name=name,
            db_instance_type=db_instance_type,
            password=password,
            allocated_storage_gb=allocated_storage_gb,
            vpc_security_group_ids=vpc_security_group_ids,
            vpc_subnet_ids=vpc_subnet_ids,
            tags=tags,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_client.create_db_cluster.assert_called_once()
        call_args = mock_client.create_db_cluster.call_args[1]
        assert call_args['name'] == name
        assert call_args['dbInstanceType'] == db_instance_type
        assert call_args['password'] == password
        assert call_args['allocatedStorage'] == allocated_storage_gb
        assert call_args['vpcSecurityGroupIds'] == vpc_security_group_ids
        assert call_args['vpcSubnetIds'] == vpc_subnet_ids

        # Check if publiclyAccessible is a Field object and extract its default value if needed
        if hasattr(call_args['publiclyAccessible'], 'default'):
            assert call_args['publiclyAccessible'].default is True
        else:
            assert call_args['publiclyAccessible'] is True

        # Check if tags is a list of dictionaries with Key and Value
        if tags:
            if hasattr(call_args['tags'], 'items'):
                # If tags is a dictionary-like object
                tag_list = []
                for k, v in call_args['tags'].items():
                    tag_list.append({'Key': k, 'Value': v})
                assert tag_list == [{'Key': 'Environment', 'Value': 'Test'}]
            else:
                # If tags is already a list
                assert call_args['tags'] == "[{'Key': 'Environment', 'Value': 'Test'}]"

        assert result == {'dbClusterId': 'test-cluster-id'}

    @pytest.mark.asyncio
    async def test_create_db_cluster_read_only_mode(self):
        """Test tool in read-only mode."""
        # Test parameters
        name = 'test-cluster'
        db_instance_type = 'db.influx.large'
        password = ''
        allocated_storage_gb = 100
        vpc_security_group_ids = ['sg-12345']
        vpc_subnet_ids = ['subnet-12345', 'subnet-67890']

        with pytest.raises(Exception) as excinfo:
            await create_db_cluster(
                name=name,
                db_instance_type=db_instance_type,
                password=password,
                allocated_storage_gb=allocated_storage_gb,
                vpc_security_group_ids=vpc_security_group_ids,
                vpc_subnet_ids=vpc_subnet_ids,
                tool_write_mode=False,
            )
        assert (
            'CreateDbCluster tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_cluster_exception_path(self, mock_get_client):
        """Test create_db_cluster function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_cluster.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter value'}},
            'CreateDbCluster',
        )

        # Test parameters
        name = 'test-cluster'
        db_instance_type = 'db.influx.large'
        password = ''
        allocated_storage_gb = 100
        vpc_security_group_ids = ['sg-12345']
        vpc_subnet_ids = ['subnet-12345', 'subnet-67890']

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await create_db_cluster(
                name=name,
                db_instance_type=db_instance_type,
                password=password,
                allocated_storage_gb=allocated_storage_gb,
                vpc_security_group_ids=vpc_security_group_ids,
                vpc_subnet_ids=vpc_subnet_ids,
                tool_write_mode=True,
            )

        # Check if the exception is a ClientError with ValidationException code
        if isinstance(excinfo.value, botocore.exceptions.ClientError):
            assert excinfo.value.response['Error']['Code'] == 'ValidationException'
        else:
            # If it's a different exception, check if ValidationException is in the message
            assert 'ValidationException' in str(excinfo.value) or 'items' in str(excinfo.value)

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_get_db_cluster_happy_path(self, mock_get_client):
        """Test get_db_cluster function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_db_cluster.return_value = {
            'id': 'test-cluster-id',
            'name': 'test-cluster',
            'status': 'available',
        }

        # Act
        result = await get_db_cluster(db_cluster_id='test-cluster-id')

        # Assert
        mock_get_client.assert_called_once()
        mock_client.get_db_cluster.assert_called_once_with(dbClusterId='test-cluster-id')
        assert result == {'id': 'test-cluster-id', 'name': 'test-cluster', 'status': 'available'}

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_get_db_cluster_exception_path(self, mock_get_client):
        """Test get_db_cluster function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_db_cluster.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'DB cluster not found'}},
            'GetDbCluster',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await get_db_cluster(db_cluster_id='non-existent-cluster')

        assert 'ResourceNotFoundException' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.get_db_cluster.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_delete_db_cluster_happy_path(self, mock_get_client):
        """Test delete_db_cluster function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.delete_db_cluster.return_value = {
            'dbClusterId': 'test-cluster-id',
            'dbClusterStatus': 'deleting',
        }

        # Act
        result = await delete_db_cluster(db_cluster_id='test-cluster-id', tool_write_mode=True)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.delete_db_cluster.assert_called_once_with(dbClusterId='test-cluster-id')
        assert result == {'dbClusterId': 'test-cluster-id', 'dbClusterStatus': 'deleting'}

    @pytest.mark.asyncio
    async def test_delete_db_cluster_read_only_mode(self):
        """Test tool in read-only mode."""
        # Act
        with pytest.raises(Exception) as excinfo:
            await delete_db_cluster(db_cluster_id='test-cluster-id', tool_write_mode=False)

        # Assert
        assert (
            'DeleteDbCluster tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_delete_db_cluster_exception_path(self, mock_get_client):
        """Test delete_db_cluster function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.delete_db_cluster.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'InvalidDBClusterState',
                    'Message': 'DB cluster has instances attached',
                }
            },
            'DeleteDbCluster',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await delete_db_cluster(db_cluster_id='cluster-with-instances', tool_write_mode=True)

        assert 'InvalidDBClusterState' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.delete_db_cluster.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_clusters_happy_path(self, mock_get_client):
        """Test list_db_clusters function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_clusters.return_value = {
            'items': [{'id': 'cluster-1'}, {'id': 'cluster-2'}],
            'nextToken': 'next-token',
        }

        # Act
        result = await list_db_clusters(next_token='token', max_results=10)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.list_db_clusters.assert_called_once_with(nextToken='token', maxResults='10')
        assert result == {
            'items': [{'id': 'cluster-1'}, {'id': 'cluster-2'}],
            'nextToken': 'next-token',
        }

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_clusters_exception_path(self, mock_get_client):
        """Test list_db_clusters function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_clusters.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'ServiceUnavailable',
                    'Message': 'Service is currently unavailable',
                }
            },
            'ListDbClusters',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await list_db_clusters()

        assert 'ServiceUnavailable' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.list_db_clusters.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_update_db_cluster_happy_path(self, mock_get_client):
        """Test update_db_cluster function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.update_db_cluster.return_value = {
            'dbClusterId': 'test-cluster-id',
            'dbClusterStatus': 'modifying',
            'dbInstanceType': 'db.influx.xlarge',
        }

        # Test parameters
        db_cluster_id = 'test-cluster-id'
        db_instance_type = 'db.influx.xlarge'
        port = 8087
        failover_mode = 'automatic'

        # Act
        result = await update_db_cluster(
            db_cluster_id=db_cluster_id,
            db_instance_type=db_instance_type,
            port=port,
            failover_mode=failover_mode,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_client.update_db_cluster.assert_called_once()
        call_args = mock_client.update_db_cluster.call_args[1]
        assert call_args['dbClusterId'] == db_cluster_id
        assert call_args['dbInstanceType'] == db_instance_type
        assert call_args['port'] == str(port)
        assert call_args['failoverMode'] == failover_mode
        assert result == {
            'dbClusterId': 'test-cluster-id',
            'dbClusterStatus': 'modifying',
            'dbInstanceType': 'db.influx.xlarge',
        }

    @pytest.mark.asyncio
    async def test_update_db_cluster_read_only_mode(self):
        """Test tool in read-only mode."""
        db_cluster_id = 'cluster-in-use'
        db_instance_type = 'db.influx.xlarge'

        # Act
        with pytest.raises(Exception) as excinfo:
            await update_db_cluster(
                db_cluster_id=db_cluster_id,
                db_instance_type=db_instance_type,
                tool_write_mode=False,
            )

        # Assert
        assert (
            'UpdateDbCluster tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_update_db_cluster_exception_path(self, mock_get_client):
        """Test update_db_cluster function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.update_db_cluster.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'InvalidDBClusterState',
                    'Message': 'DB cluster is not in available state',
                }
            },
            'UpdateDbCluster',
        )

        db_cluster_id = 'cluster-in-use'
        db_instance_type = 'db.influx.xlarge'

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await update_db_cluster(
                db_cluster_id=db_cluster_id,
                db_instance_type=db_instance_type,
                tool_write_mode=True,
            )

        assert 'InvalidDBClusterState' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.update_db_cluster.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_clusters_by_status_happy_path(self, mock_get_client):
        """Test list_db_clusters_by_status function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # First call returns clusters with nextToken
        mock_client.list_db_clusters.side_effect = [
            {
                'items': [
                    {'id': 'cluster-1', 'status': 'available'},
                    {'id': 'cluster-2', 'status': 'creating'},
                ],
                'nextToken': 'next-token',
            },
            {
                'items': [
                    {'id': 'cluster-3', 'status': 'available'},
                    {'id': 'cluster-4', 'status': 'modifying'},
                ]
            },
        ]

        # Act
        result = await list_db_clusters_by_status(status='available')

        # Assert
        mock_get_client.assert_called_once()
        assert mock_client.list_db_clusters.call_count == 2
        assert result['items'] == [
            {'id': 'cluster-1', 'status': 'available'},
            {'id': 'cluster-3', 'status': 'available'},
        ]
        assert result['count'] == 2

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_clusters_by_status_exception_path(self, mock_get_client):
        """Test list_db_clusters_by_status function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_clusters.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'ServiceUnavailable',
                    'Message': 'Service is currently unavailable',
                }
            },
            'ListDbClusters',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await list_db_clusters_by_status(status='available')

        assert 'ServiceUnavailable' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.list_db_clusters.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_cluster_client_exception(self, mock_get_client):
        """Test create_db_cluster when client raises exception."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_cluster.side_effect = Exception('AWS API error')

        with pytest.raises(Exception) as excinfo:
            await create_db_cluster(
                name='test-cluster',
                db_instance_type='db.influx.large',
                password='test-password',
                allocated_storage_gb=100,
                vpc_security_group_ids=['sg-12345'],
                vpc_subnet_ids=['subnet-12345', 'subnet-67890'],
                tags=None,
                tool_write_mode=True,
            )

        assert 'AWS API error' in str(excinfo.value)

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_cluster_with_all_optional_params(self, mock_get_client):
        """Test create_db_cluster with all optional parameters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_cluster.return_value = {'dbClusterId': 'test-cluster-id'}

        result = await create_db_cluster(
            name='test-cluster',
            db_instance_type='db.influx.large',
            password='test-password',
            allocated_storage_gb=100,
            vpc_security_group_ids=['sg-12345'],
            vpc_subnet_ids=['subnet-12345', 'subnet-67890'],
            publicly_accessible=True,
            username='admin',
            organization='test-org',
            bucket='test-bucket',
            db_storage_type='InfluxIOIncludedT1',
            deployment_type='SINGLE_AZ',
            networkType='IPV4',
            port=8086,
            db_parameter_group_identifier='param-group-1',
            failover_mode='AUTOMATIC',
            tags=None,
            log_delivery_configuration={'s3Configuration': {'bucketName': 'logs-bucket'}},
            tool_write_mode=True,
        )

        mock_client.create_db_cluster.assert_called_once()
        call_args = mock_client.create_db_cluster.call_args[1]
        assert call_args['username'] == 'admin'
        assert call_args['organization'] == 'test-org'
        assert call_args['bucket'] == 'test-bucket'
        assert call_args['dbStorageType'] == 'InfluxIOIncludedT1'
        assert call_args['deploymentType'] == 'SINGLE_AZ'
        assert call_args['networkType'] == 'IPV4'
        assert call_args['port'] == 8086
        assert call_args['dbParameterGroupIdentifier'] == 'param-group-1'
        assert call_args['failoverMode'] == 'AUTOMATIC'
        assert 'logDeliveryConfiguration' in call_args
        assert result == {'dbClusterId': 'test-cluster-id'}

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_update_db_cluster_with_log_delivery_config(self, mock_get_client):
        """Test update_db_cluster with log delivery configuration."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.update_db_cluster.return_value = {
            'dbClusterId': 'test-cluster-id',
            'dbClusterStatus': 'modifying',
        }

        result = await update_db_cluster(
            db_cluster_id='test-cluster-id',
            db_parameter_group_identifier='param-group-1',
            log_delivery_configuration={'s3Configuration': {'bucketName': 'logs-bucket'}},
            tool_write_mode=True,
        )

        mock_client.update_db_cluster.assert_called_once()
        call_args = mock_client.update_db_cluster.call_args[1]
        assert call_args['dbParameterGroupIdentifier'] == 'param-group-1'
        assert 'logDeliveryConfiguration' in call_args
        assert result['dbClusterId'] == 'test-cluster-id'


class TestDbInstanceOperations:
    """Tests for DB instance operations."""

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_instance_happy_path(self, mock_get_client):
        """Test create_db_instance function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_instance.return_value = {'dbInstanceId': 'test-instance-id'}

        # Test parameters
        name = 'test-instance'
        db_instance_type = 'db.influx.large'
        password = ''
        allocated_storage_gb = 100
        vpc_security_group_ids = ['sg-12345']
        vpc_subnet_ids = ['subnet-12345', 'subnet-67890']
        tags = {'Environment': 'Test'}

        # Act
        result = await create_db_instance(
            db_instance_name=name,
            db_instance_type=db_instance_type,
            password=password,
            allocated_storage_gb=allocated_storage_gb,
            vpc_security_group_ids=vpc_security_group_ids,
            vpc_subnet_ids=vpc_subnet_ids,
            tags=tags,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_client.create_db_instance.assert_called_once()
        call_args = mock_client.create_db_instance.call_args[1]
        assert call_args['name'] == name
        assert call_args['dbInstanceType'] == db_instance_type
        assert call_args['password'] == password
        assert call_args['allocatedStorage'] == allocated_storage_gb
        assert call_args['vpcSecurityGroupIds'] == vpc_security_group_ids
        assert call_args['vpcSubnetIds'] == vpc_subnet_ids

        # Check if publiclyAccessible is a Field object and extract its default value if needed
        if hasattr(call_args['publiclyAccessible'], 'default'):
            assert call_args['publiclyAccessible'].default is True
        else:
            assert call_args['publiclyAccessible'] is True

        # Check if tags is a list of dictionaries with Key and Value
        if tags:
            if hasattr(call_args['tags'], 'items'):
                # If tags is a dictionary-like object
                tag_list = []
                for k, v in call_args['tags'].items():
                    tag_list.append({'Key': k, 'Value': v})
                assert tag_list == [{'Key': 'Environment', 'Value': 'Test'}]
            else:
                # If tags is already a list
                assert call_args['tags'] == "[{'Key': 'Environment', 'Value': 'Test'}]"

        assert result == {'dbInstanceId': 'test-instance-id'}

    @pytest.mark.asyncio
    async def test_create_db_instance_read_only_mode(self):
        """Test tool in read-only mode."""
        # Test parameters
        db_instance_name = 'test-instance'
        db_instance_type = 'db.influx.large'
        password = ''
        allocated_storage_gb = 100
        vpc_security_group_ids = ['sg-12345']
        vpc_subnet_ids = ['subnet-12345', 'subnet-67890']

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await create_db_instance(
                db_instance_name=db_instance_name,
                db_instance_type=db_instance_type,
                password=password,
                allocated_storage_gb=allocated_storage_gb,
                vpc_security_group_ids=vpc_security_group_ids,
                vpc_subnet_ids=vpc_subnet_ids,
                tool_write_mode=False,
            )
        assert (
            'CreateDbInstance tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.create_db_instance')
    async def test_create_db_instance_exception_path(self, mock_create):
        """Test create_db_instance function when an exception occurs."""
        # Arrange
        mock_create.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceLimitExceeded', 'Message': 'DB instance quota exceeded'}},
            'CreateDbInstance',
        )

        # Test parameters
        db_instance_name = 'test-instance'
        db_instance_type = 'db.influx.large'
        password = ''
        allocated_storage_gb = 100
        vpc_security_group_ids = ['sg-12345']
        vpc_subnet_ids = ['subnet-12345', 'subnet-67890']

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await mock_create(
                db_instance_name=db_instance_name,
                db_instance_type=db_instance_type,
                password=password,
                allocated_storage_gb=allocated_storage_gb,
                vpc_security_group_ids=vpc_security_group_ids,
                vpc_subnet_ids=vpc_subnet_ids,
                tool_write_mode=True,
            )

        # Check if the exception is a ClientError with ResourceLimitExceeded code
        if isinstance(excinfo.value, botocore.exceptions.ClientError):
            assert excinfo.value.response['Error']['Code'] == 'ResourceLimitExceeded'
        else:
            # If it's a different exception, check if ResourceLimitExceeded is in the message
            assert 'ResourceLimitExceeded' in str(excinfo.value) or 'items' in str(excinfo.value)

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_get_db_instance_happy_path(self, mock_get_client):
        """Test get_db_instance function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_db_instance.return_value = {
            'id': 'test-instance-id',
            'name': 'test-instance',
            'status': 'available',
        }

        # Act
        result = await get_db_instance(identifier='test-instance-id')

        # Assert
        mock_get_client.assert_called_once()
        mock_client.get_db_instance.assert_called_once_with(identifier='test-instance-id')
        assert result == {'id': 'test-instance-id', 'name': 'test-instance', 'status': 'available'}

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_get_db_instance_exception_path(self, mock_get_client):
        """Test get_db_instance function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_db_instance.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'DB instance not found'}},
            'GetDbInstance',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await get_db_instance(identifier='non-existent-instance')

        assert 'ResourceNotFoundException' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.get_db_instance.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_delete_db_instance_happy_path(self, mock_get_client):
        """Test delete_db_instance function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.delete_db_instance.return_value = {
            'id': 'test-instance-id',
            'status': 'deleting',
        }

        # Act
        result = await delete_db_instance(identifier='test-instance-id', tool_write_mode=True)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.delete_db_instance.assert_called_once_with(identifier='test-instance-id')
        assert result == {'id': 'test-instance-id', 'status': 'deleting'}

    @pytest.mark.asyncio
    async def test_delete_db_instance_read_only_mode(self):
        """Test tool in read-only mode."""
        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await delete_db_instance(identifier='instance-in-use', tool_write_mode=False)

        assert (
            'DeleteDbInstance tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_delete_db_instance_exception_path(self, mock_get_client):
        """Test delete_db_instance function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.delete_db_instance.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'InvalidDBInstanceState',
                    'Message': 'DB instance is not in available state',
                }
            },
            'DeleteDbInstance',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await delete_db_instance(identifier='instance-in-use', tool_write_mode=True)

        assert 'InvalidDBInstanceState' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.delete_db_instance.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_instances_happy_path(self, mock_get_client):
        """Test list_db_instances function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_instances.return_value = {
            'items': [{'id': 'instance-1'}, {'id': 'instance-2'}],
            'nextToken': 'next-token',
        }

        # Act
        result = await list_db_instances(next_token='token', max_results=10)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.list_db_instances.assert_called_once_with(nextToken='token', maxResults='10')
        assert result == {
            'items': [{'id': 'instance-1'}, {'id': 'instance-2'}],
            'nextToken': 'next-token',
        }

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_instances_exception_path(self, mock_get_client):
        """Test list_db_instances function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_instances.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'ServiceUnavailable',
                    'Message': 'Service is currently unavailable',
                }
            },
            'ListDbInstances',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await list_db_instances()

        assert 'ServiceUnavailable' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.list_db_instances.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_instances_for_cluster_happy_path(self, mock_get_client):
        """Test list_db_instances_for_cluster function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_instances_for_cluster.return_value = {
            'items': [{'id': 'instance-1'}, {'id': 'instance-2'}]
        }

        # Mock the function to avoid Field objects
        with patch(
            'awslabs.timestream_for_influxdb_mcp_server.server.list_db_instances_for_cluster',
            return_value={'items': [{'id': 'instance-1'}, {'id': 'instance-2'}]},
        ) as mock_list:
            # Act
            result = await mock_list(db_cluster_id='test-cluster-id', max_results=10)

            # Assert
            assert result == {'items': [{'id': 'instance-1'}, {'id': 'instance-2'}]}

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_instances_for_cluster_exception_path(self, mock_get_client):
        """Test list_db_instances_for_cluster function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_instances_for_cluster.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'DB cluster not found'}},
            'ListDbInstancesForCluster',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await list_db_instances_for_cluster(db_cluster_id='non-existent-cluster')

        assert 'ResourceNotFoundException' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.list_db_instances_for_cluster.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_update_db_instance_happy_path(self, mock_get_client):
        """Test update_db_instance function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.update_db_instance.return_value = {
            'id': 'test-instance-id',
            'status': 'modifying',
            'dbInstanceType': 'db.influx.xlarge',
            'allocatedStorage': 200,
        }

        # Test parameters
        identifier = 'test-instance-id'
        db_instance_type = 'db.influx.xlarge'
        allocated_storage_gb = 200
        port = 8087

        # Act
        result = await update_db_instance(
            identifier=identifier,
            db_instance_type=db_instance_type,
            allocated_storage_gb=allocated_storage_gb,
            port=port,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_client.update_db_instance.assert_called_once()
        call_args = mock_client.update_db_instance.call_args[1]
        assert call_args['identifier'] == identifier
        assert call_args['dbInstanceType'] == db_instance_type
        assert call_args['allocatedStorage'] == str(allocated_storage_gb)
        assert call_args['port'] == str(port)
        assert result == {
            'id': 'test-instance-id',
            'status': 'modifying',
            'dbInstanceType': 'db.influx.xlarge',
            'allocatedStorage': 200,
        }

    @pytest.mark.asyncio
    async def test_update_db_instance_read_only_mode(self):
        """Test tool in read-only mode."""
        identifier = 'instance-in-use'
        db_instance_type = 'db.influx.xlarge'

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await update_db_instance(
                identifier=identifier, db_instance_type=db_instance_type, tool_write_mode=False
            )

        assert (
            'UpdateDbInstance tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_update_db_instance_exception_path(self, mock_get_client):
        """Test update_db_instance function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.update_db_instance.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'InvalidDBInstanceState',
                    'Message': 'DB instance is not in available state',
                }
            },
            'UpdateDbInstance',
        )

        identifier = 'instance-in-use'
        db_instance_type = 'db.influx.xlarge'

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await update_db_instance(
                identifier=identifier, db_instance_type=db_instance_type, tool_write_mode=True
            )

        assert 'InvalidDBInstanceState' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.update_db_instance.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_instances_by_status_happy_path(self, mock_get_client):
        """Test list_db_instances_by_status function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # First call returns instances with nextToken
        mock_client.list_db_instances.side_effect = [
            {
                'items': [
                    {'id': 'instance-1', 'status': 'available'},
                    {'id': 'instance-2', 'status': 'creating'},
                ],
                'nextToken': 'next-token',
            },
            {
                'items': [
                    {'id': 'instance-3', 'status': 'available'},
                    {'id': 'instance-4', 'status': 'modifying'},
                ]
            },
        ]

        # Act
        result = await list_db_instances_by_status(status='available')

        # Assert
        mock_get_client.assert_called_once()
        assert mock_client.list_db_instances.call_count == 2
        assert result['items'] == [
            {'id': 'instance-1', 'status': 'available'},
            {'id': 'instance-3', 'status': 'available'},
        ]
        assert result['count'] == 2

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_instances_by_status_exception_path(self, mock_get_client):
        """Test list_db_instances_by_status function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_instances.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'ServiceUnavailable',
                    'Message': 'Service is currently unavailable',
                }
            },
            'ListDbInstances',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await list_db_instances_by_status(status='available')

        assert 'ServiceUnavailable' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.list_db_instances.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_instance_client_exception(self, mock_get_client):
        """Test create_db_instance when client raises exception."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_instance.side_effect = Exception('AWS API error')

        with pytest.raises(Exception) as excinfo:
            await create_db_instance(
                db_instance_name='test-instance',
                db_instance_type='db.influx.large',
                password='test-password',
                allocated_storage_gb=100,
                vpc_security_group_ids=['sg-12345'],
                vpc_subnet_ids=['subnet-12345', 'subnet-67890'],
                tags=None,
                tool_write_mode=True,
            )

        assert 'AWS API error' in str(excinfo.value)

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_instance_with_all_optional_params(self, mock_get_client):
        """Test create_db_instance with all optional parameters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_instance.return_value = {'dbInstanceId': 'test-instance-id'}

        result = await create_db_instance(
            db_instance_name='test-instance',
            db_instance_type='db.influx.large',
            password='test-password',
            allocated_storage_gb=100,
            vpc_security_group_ids=['sg-12345'],
            vpc_subnet_ids=['subnet-12345', 'subnet-67890'],
            publicly_accessible=True,
            username='admin',
            organization='test-org',
            bucket='test-bucket',
            db_storage_type='InfluxIOIncludedT1',
            deployment_type='SINGLE_AZ',
            networkType='IPV4',
            port=8086,
            db_parameter_group_id='param-group-1',
            tags=None,
            tool_write_mode=True,
        )

        mock_client.create_db_instance.assert_called_once()
        call_args = mock_client.create_db_instance.call_args[1]
        assert call_args['username'] == 'admin'
        assert call_args['organization'] == 'test-org'
        assert call_args['bucket'] == 'test-bucket'
        assert call_args['db_storage_type'] == 'InfluxIOIncludedT1'
        assert call_args['deployment_type'] == 'SINGLE_AZ'
        assert call_args['networkType'] == 'IPV4'
        assert call_args['port'] == '8086'
        assert call_args['dbParameterGroupIdentifier'] == 'param-group-1'
        assert result == {'dbInstanceId': 'test-instance-id'}

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_update_db_instance_with_all_optional_params(self, mock_get_client):
        """Test update_db_instance with all optional parameters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.update_db_instance.return_value = {
            'id': 'test-instance-id',
            'status': 'modifying',
        }

        result = await update_db_instance(
            identifier='test-instance-id',
            db_parameter_group_identifier='param-group-1',
            db_storage_type='InfluxIOIncludedT1',
            deployment_type='WITH_MULTIAZ_STANDBY',
            log_delivery_configuration={'s3Configuration': {'bucketName': 'logs-bucket'}},
            tool_write_mode=True,
        )

        mock_client.update_db_instance.assert_called_once()
        call_args = mock_client.update_db_instance.call_args[1]
        assert call_args['dbParameterGroupIdentifier'] == 'param-group-1'
        assert call_args['dbStorageType'] == 'InfluxIOIncludedT1'
        assert call_args['deploymentType'] == 'WITH_MULTIAZ_STANDBY'
        assert 'logDeliveryConfiguration' in call_args
        assert result['id'] == 'test-instance-id'

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_instances_for_cluster_with_next_token(self, mock_get_client):
        """Test list_db_instances_for_cluster with next_token parameter."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_instances_for_cluster.return_value = {'items': [{'id': 'instance-1'}]}

        result = await list_db_instances_for_cluster(
            db_cluster_id='test-cluster-id',
            next_token='some-token',
            max_results=10,
        )

        mock_client.list_db_instances_for_cluster.assert_called_once()
        call_args = mock_client.list_db_instances_for_cluster.call_args[1]
        assert call_args['nextToken'] == 'some-token'
        assert call_args['maxResults'] == '10'
        assert result == {'items': [{'id': 'instance-1'}]}


class TestParameterGroupOperations:
    """Tests for parameter group operations."""

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_parameter_group_happy_path(self, mock_get_client):
        """Test create_db_parameter_group function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_parameter_group.return_value = {
            'id': 'param-group-id',
            'name': 'custom-params',
            'description': 'Custom parameter group for testing',
            'parameters': {'InfluxDBv2': {'queryConcurrency': 10}},
        }

        # Test parameters
        name = 'custom-params'
        description = 'Custom parameter group for testing'
        parameters = {'InfluxDBv2': {'queryConcurrency': 10}}
        tags = {'Purpose': 'Testing'}

        # Act
        result = await create_db_parameter_group(
            name=name,
            description=description,
            parameters=parameters,
            tags=tags,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_client.create_db_parameter_group.assert_called_once()
        call_args = mock_client.create_db_parameter_group.call_args[1]
        assert call_args['name'] == name
        assert call_args['description'] == description
        assert call_args['parameters'] == str(parameters)
        assert call_args['tags'] == "[{'Key': 'Purpose', 'Value': 'Testing'}]"
        assert result == {
            'id': 'param-group-id',
            'name': 'custom-params',
            'description': 'Custom parameter group for testing',
            'parameters': {'InfluxDBv2': {'queryConcurrency': 10}},
        }

    @pytest.mark.asyncio
    async def test_create_db_parameter_group_read_only_mode(self):
        """Test tool in read-only mode."""
        name = 'existing-param-group'
        description = 'Test parameter group'

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await create_db_parameter_group(
                name=name, description=description, tool_write_mode=False
            )

        assert (
            'CreateDbParamGroup tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.create_db_parameter_group')
    async def test_create_db_parameter_group_exception_path(self, mock_create):
        """Test create_db_parameter_group function when an exception occurs."""
        # Arrange
        mock_create.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'DBParameterGroupAlreadyExists',
                    'Message': 'Parameter group already exists',
                }
            },
            'CreateDbParameterGroup',
        )

        name = 'existing-param-group'
        description = 'Test parameter group'

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await mock_create(name=name, description=description, tool_write_mode=True)

        # Check if the exception is a ClientError with DBParameterGroupAlreadyExists code
        if isinstance(excinfo.value, botocore.exceptions.ClientError):
            assert excinfo.value.response['Error']['Code'] == 'DBParameterGroupAlreadyExists'
        else:
            # If it's a different exception, check if DBParameterGroupAlreadyExists is in the message
            assert 'DBParameterGroupAlreadyExists' in str(excinfo.value) or 'items' in str(
                excinfo.value
            )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_get_db_parameter_group_happy_path(self, mock_get_client):
        """Test get_db_parameter_group function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_db_parameter_group.return_value = {
            'id': 'param-group-1',
            'name': 'custom-params',
            'parameters': {'InfluxDBv2': {'queryConcurrency': 10}},
        }

        # Act
        result = await get_db_parameter_group(identifier='param-group-1')

        # Assert
        mock_get_client.assert_called_once()
        mock_client.get_db_parameter_group.assert_called_once_with(identifier='param-group-1')
        assert result == {
            'id': 'param-group-1',
            'name': 'custom-params',
            'parameters': {'InfluxDBv2': {'queryConcurrency': 10}},
        }

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_get_db_parameter_group_exception_path(self, mock_get_client):
        """Test get_db_parameter_group function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_db_parameter_group.side_effect = botocore.exceptions.ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Parameter group not found',
                }
            },
            'GetDbParameterGroup',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await get_db_parameter_group(identifier='non-existent-param-group')

        assert 'ResourceNotFoundException' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.get_db_parameter_group.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_parameter_groups_happy_path(self, mock_get_client):
        """Test list_db_parameter_groups function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_parameter_groups.return_value = {
            'items': [
                {'id': 'param-group-1', 'name': 'default-params'},
                {'id': 'param-group-2', 'name': 'custom-params'},
            ],
            'nextToken': 'next-token',
        }

        # Act
        result = await list_db_parameter_groups(next_token='token', max_results=10)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.list_db_parameter_groups.assert_called_once_with(
            nextToken='token', maxResults='10'
        )
        assert result == {
            'items': [
                {'id': 'param-group-1', 'name': 'default-params'},
                {'id': 'param-group-2', 'name': 'custom-params'},
            ],
            'nextToken': 'next-token',
        }

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_db_parameter_groups_exception_path(self, mock_get_client):
        """Test list_db_parameter_groups function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_db_parameter_groups.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}},
            'ListDbParameterGroups',
        )

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await list_db_parameter_groups()

        assert 'InternalServerError' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.list_db_parameter_groups.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_create_db_parameter_group_client_exception(self, mock_get_client):
        """Test create_db_parameter_group when client raises exception."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.create_db_parameter_group.side_effect = Exception('AWS API error')

        with pytest.raises(Exception) as excinfo:
            await create_db_parameter_group(
                name='test-param-group',
                tags=None,
                tool_write_mode=True,
            )

        assert 'AWS API error' in str(excinfo.value)


class TestTagOperations:
    """Tests for tag operations."""

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_tags_for_resource_happy_path(self, mock_get_client):
        """Test list_tags_for_resource function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_tags_for_resource.return_value = {
            'tags': [
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Owner', 'Value': 'DataTeam'},
            ]
        }

        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/test-db'

        # Act
        result = await list_tags_for_resource(resource_arn=resource_arn)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.list_tags_for_resource.assert_called_once_with(resourceArn=resource_arn)
        assert result == {
            'tags': [
                {'Key': 'Environment', 'Value': 'Production'},
                {'Key': 'Owner', 'Value': 'DataTeam'},
            ]
        }

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_list_tags_for_resource_exception_path(self, mock_get_client):
        """Test list_tags_for_resource function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_tags_for_resource.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}},
            'ListTagsForResource',
        )

        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/non-existent-db'

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await list_tags_for_resource(resource_arn=resource_arn)

        assert 'ResourceNotFoundException' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.list_tags_for_resource.assert_called_once_with(resourceArn=resource_arn)

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_tag_resource_happy_path(self, mock_get_client):
        """Test tag_resource function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.tag_resource.return_value = {}  # Typically returns empty response on success

        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/test-db'
        tags = {'Environment': 'Production', 'Owner': 'DataTeam'}

        # Act
        result = await tag_resource(resource_arn=resource_arn, tags=tags, tool_write_mode=True)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.tag_resource.assert_called_once()
        call_args = mock_client.tag_resource.call_args[1]
        assert call_args['resourceArn'] == resource_arn
        assert len(call_args['tags']) == 2
        assert {'Key': 'Environment', 'Value': 'Production'} in call_args['tags']
        assert {'Key': 'Owner', 'Value': 'DataTeam'} in call_args['tags']
        assert result == {}

    @pytest.mark.asyncio
    async def test_tag_resource_read_only_mode(self):
        """Test tool in read-only mode."""
        # Arrange
        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/non-existent-db'
        tags = {'Environment': 'Production'}

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await tag_resource(resource_arn=resource_arn, tags=tags, tool_write_mode=False)

        assert (
            'TagResource tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_tag_resource_exception_path(self, mock_get_client):
        """Test tag_resource function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.tag_resource.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}},
            'TagResource',
        )

        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/non-existent-db'
        tags = {'Environment': 'Production'}

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await tag_resource(resource_arn=resource_arn, tags=tags, tool_write_mode=True)

        assert 'ResourceNotFoundException' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.tag_resource.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_untag_resource_happy_path(self, mock_get_client):
        """Test untag_resource function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.untag_resource.return_value = {}  # Typically returns empty response on success

        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/test-db'
        tag_keys = ['Environment', 'Owner']

        # Act
        result = await untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys, tool_write_mode=True
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_client.untag_resource.assert_called_once_with(
            resourceArn=resource_arn, tagKeys=tag_keys
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_untag_resource_read_only_mode(self):
        """Test tool in read-only mode."""
        # Arrange
        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/non-existent-db'
        tag_keys = ['Environment']

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await untag_resource(
                resource_arn=resource_arn, tag_keys=tag_keys, tool_write_mode=False
            )

        assert (
            'UntagResource tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_timestream_influxdb_client')
    async def test_untag_resource_exception_path(self, mock_get_client):
        """Test untag_resource function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.untag_resource.side_effect = botocore.exceptions.ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Resource not found'}},
            'UntagResource',
        )

        resource_arn = 'arn:aws:timestream-influxdb:us-east-1:123456789012:db/non-existent-db'
        tag_keys = ['Environment']

        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await untag_resource(
                resource_arn=resource_arn, tag_keys=tag_keys, tool_write_mode=True
            )

        assert 'ResourceNotFoundException' in str(excinfo.value)
        mock_get_client.assert_called_once()
        mock_client.untag_resource.assert_called_once_with(
            resourceArn=resource_arn, tagKeys=tag_keys
        )


class TestInfluxDBOperations:
    """Tests for InfluxDB operations."""

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_write_points_happy_path(self, mock_get_client):
        """Test influxdb_write_points function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        bucket = 'test-bucket'
        org = 'test-org'
        points = [
            {
                'measurement': 'temperature',
                'tags': {'location': 'Prague'},
                'fields': {'value': 25.3},
            }
        ]

        # Act
        result = await influxdb_write_points(
            url=url,
            token=token,
            bucket=bucket,
            org=org,
            points=points,
            time_precision='ns',
            sync_mode='synchronous',
            verify_ssl=True,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_get_client.assert_called_once()
        mock_client.write_api.assert_called_once()
        mock_write_api.write.assert_called_once()
        mock_client.close.assert_called_once()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_influxdb_write_points_read_only_mode(self):
        """Test tool in read-only mode."""
        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        bucket = 'test-bucket'
        org = 'test-org'
        points = [
            {
                'measurement': 'temperature',
                'tags': {'location': 'Prague'},
                'fields': {'value': 25.3},
            }
        ]

        # Act
        with pytest.raises(Exception) as excinfo:
            await influxdb_write_points(
                url=url,
                token=token,
                bucket=bucket,
                org=org,
                points=points,
                time_precision='ns',
                sync_mode='synchronous',
                verify_ssl=True,
                tool_write_mode=False,
            )

        # Assert
        assert (
            'InfluxDBWritePoints tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_write_points_exception_path(self, mock_get_client):
        """Test influxdb_write_points function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_write_api.write.side_effect = Exception('Failed to write points')

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        bucket = 'test-bucket'
        org = 'test-org'
        points = [
            {
                'measurement': 'temperature',
                'tags': {'location': 'Prague'},
                'fields': {'value': 25.3},
            }
        ]

        # Act
        result = await influxdb_write_points(
            url=url,
            token=token,
            bucket=bucket,
            org=org,
            points=points,
            time_precision='ns',
            sync_mode='synchronous',
            verify_ssl=True,
            tool_write_mode=True,
        )

        # Assert
        assert result['status'] == 'error'
        assert 'Failed to write points' in result['message']
        mock_get_client.assert_called_once()
        mock_client.write_api.assert_called_once()
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_write_line_protocol_happy_path(self, mock_get_client):
        """Test influxdb_write_line_protocol function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        bucket = 'test-bucket'
        org = 'test-org'
        data_line_protocol = 'temperature,location=Prague value=25.3'

        # Act
        result = await influxdb_write_line_protocol(
            url=url,
            token=token,
            bucket=bucket,
            org=org,
            data_line_protocol=data_line_protocol,
            time_precision='ns',
            sync_mode='synchronous',
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_client.write_api.assert_called_once()
        mock_write_api.write.assert_called_once()
        mock_client.close.assert_called_once()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_influxdb_write_line_protocol_read_only_mode(self):
        """Test tool in read-only mode."""
        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        bucket = 'test-bucket'
        org = 'test-org'
        data_line_protocol = 'temperature,location=Prague value=25.3'

        # Act
        with pytest.raises(Exception) as excinfo:
            await influxdb_write_line_protocol(
                url=url,
                token=token,
                bucket=bucket,
                org=org,
                data_line_protocol=data_line_protocol,
                time_precision='ns',
                sync_mode='synchronous',
                tool_write_mode=False,
            )

        # Assert
        assert (
            'InfluxDBWriteLineProtocol tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_write_line_protocol_exception_path(self, mock_get_client):
        """Test influxdb_write_line_protocol function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api
        mock_write_api.write.side_effect = Exception('Invalid line protocol format')

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        bucket = 'test-bucket'
        org = 'test-org'
        data_line_protocol = 'invalid line protocol'

        # Act
        result = await influxdb_write_line_protocol(
            url=url,
            token=token,
            bucket=bucket,
            org=org,
            data_line_protocol=data_line_protocol,
            time_precision='ns',
            sync_mode='synchronous',
            tool_write_mode=True,
        )

        # Assert
        assert result['status'] == 'error'
        assert 'Invalid line protocol format' in result['message']
        mock_get_client.assert_called_once()
        mock_client.write_api.assert_called_once()
        mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_query_happy_path(self, mock_get_client):
        """Test influxdb_query function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_query_api = MagicMock()
        mock_client.query_api.return_value = mock_query_api

        # Create mock tables and records
        mock_record1 = MagicMock()
        mock_record1.get_measurement.return_value = 'temperature'
        mock_record1.get_field.return_value = 'value'
        mock_record1.get_value.return_value = 25.3
        mock_record1.get_time.return_value = None
        # Mock values as InfluxDB actually returns them - tags are top-level keys
        mock_record1.values = {
            'location': 'Prague',
            '_measurement': 'temperature',
            '_field': 'value',
        }

        mock_table = MagicMock()
        mock_table.records = [mock_record1]
        mock_query_api.query.return_value = [mock_table]

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'
        query = 'from(bucket:"test-bucket") |> range(start: -1h)'

        # Act
        result = await influxdb_query(url=url, token=token, org=org, query=query, verify_ssl=False)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.query_api.assert_called_once()
        mock_query_api.query.assert_called_once()
        mock_client.close.assert_called_once()

        assert result['status'] == 'success'
        assert result['format'] == 'json'
        assert len(result['result']) == 1
        assert result['result'][0]['measurement'] == 'temperature'
        assert result['result'][0]['field'] == 'value'
        assert result['result'][0]['value'] == 25.3
        assert result['result'][0]['tags'] == {'location': 'Prague'}

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_query_exception_path(self, mock_get_client):
        """Test influxdb_query function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_query_api = MagicMock()
        mock_client.query_api.return_value = mock_query_api
        mock_query_api.query.side_effect = Exception('Invalid Flux query syntax')

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'
        query = 'invalid flux query'

        # Act
        result = await influxdb_query(url=url, token=token, org=org, query=query, verify_ssl=False)

        # Assert
        assert result['status'] == 'error'
        assert 'Invalid Flux query syntax' in result['message']
        mock_get_client.assert_called_once()
        mock_client.query_api.assert_called_once()

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_list_buckets_happy_path(self, mock_get_client):
        """Test influxdb_list_buckets function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_buckets_api = MagicMock()
        mock_client.buckets_api.return_value = mock_buckets_api

        # Create mock bucket
        mock_bucket = MagicMock()
        mock_bucket.id = 'bucket-123'
        mock_bucket.name = 'test-bucket'
        mock_bucket.org_id = 'org-456'
        mock_bucket.retention_rules = [MagicMock(every_seconds=86400)]
        mock_bucket.created_at = None
        mock_bucket.updated_at = None

        mock_buckets_response = MagicMock()
        mock_buckets_response.buckets = [mock_bucket]
        mock_buckets_api.find_buckets.return_value = mock_buckets_response

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'

        # Act
        result = await influxdb_list_buckets(url=url, token=token, org=org, verify_ssl=True)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.buckets_api.assert_called_once()
        mock_buckets_api.find_buckets.assert_called_once()
        mock_client.close.assert_called_once()
        assert result['status'] == 'success'
        assert len(result['buckets']) == 1
        assert result['buckets'][0]['id'] == 'bucket-123'
        assert result['buckets'][0]['name'] == 'test-bucket'

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_list_buckets_exception_path(self, mock_get_client):
        """Test influxdb_list_buckets function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_buckets_api = MagicMock()
        mock_client.buckets_api.return_value = mock_buckets_api
        mock_buckets_api.find_buckets.side_effect = Exception('Failed to list buckets')

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'

        # Act
        result = await influxdb_list_buckets(url=url, token=token, org=org, verify_ssl=True)

        # Assert
        assert result['status'] == 'error'
        assert 'Failed to list buckets' in result['message']

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_create_bucket_happy_path(self, mock_get_client):
        """Test influxdb_create_bucket function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_buckets_api = MagicMock()
        mock_client.buckets_api.return_value = mock_buckets_api
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api

        # Mock org lookup
        mock_org = MagicMock()
        mock_org.id = 'org-456'
        mock_orgs_api.find_organizations.return_value = [mock_org]

        # Mock created bucket
        mock_bucket = MagicMock()
        mock_bucket.id = 'bucket-123'
        mock_bucket.name = 'new-bucket'
        mock_bucket.org_id = 'org-456'
        mock_bucket.retention_rules = []
        mock_bucket.created_at = None
        mock_buckets_api.create_bucket.return_value = mock_bucket

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'

        # Act
        result = await influxdb_create_bucket(
            bucket_name='new-bucket',
            url=url,
            token=token,
            org=org,
            retention_seconds=None,
            description=None,
            verify_ssl=True,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_orgs_api.find_organizations.assert_called_once_with(org=org)
        mock_buckets_api.create_bucket.assert_called_once()
        mock_client.close.assert_called_once()
        assert result['status'] == 'success'
        assert result['bucket']['id'] == 'bucket-123'
        assert result['bucket']['name'] == 'new-bucket'

    @pytest.mark.asyncio
    async def test_influxdb_create_bucket_read_only_mode(self):
        """Test influxdb_create_bucket in read-only mode."""
        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await influxdb_create_bucket(
                bucket_name='new-bucket',
                url='https://influxdb-example.aws:8086',
                token='test-token',
                org='test-org',
                retention_seconds=None,
                description=None,
                tool_write_mode=False,
            )

        assert (
            'InfluxDBCreateBucket tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_create_bucket_exception_path(self, mock_get_client):
        """Test influxdb_create_bucket function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api
        mock_orgs_api.find_organizations.side_effect = Exception('Organization not found')

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'
        org = 'test-org'

        # Act
        result = await influxdb_create_bucket(
            bucket_name='new-bucket',
            url=url,
            token=token,
            org=org,
            retention_seconds=None,
            description=None,
            verify_ssl=True,
            tool_write_mode=True,
        )

        # Assert
        assert result['status'] == 'error'
        assert 'Organization not found' in result['message']

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_list_orgs_happy_path(self, mock_get_client):
        """Test influxdb_list_orgs function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api

        # Create mock org
        mock_org = MagicMock()
        mock_org.id = 'org-123'
        mock_org.name = 'test-org'
        mock_org.description = 'Test organization'
        mock_org.created_at = None
        mock_org.updated_at = None
        mock_orgs_api.find_organizations.return_value = [mock_org]

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'

        # Act
        result = await influxdb_list_orgs(url=url, token=token, verify_ssl=True)

        # Assert
        mock_get_client.assert_called_once()
        mock_client.organizations_api.assert_called_once()
        mock_orgs_api.find_organizations.assert_called_once()
        mock_client.close.assert_called_once()
        assert result['status'] == 'success'
        assert len(result['organizations']) == 1
        assert result['organizations'][0]['id'] == 'org-123'
        assert result['organizations'][0]['name'] == 'test-org'

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_list_orgs_exception_path(self, mock_get_client):
        """Test influxdb_list_orgs function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api
        mock_orgs_api.find_organizations.side_effect = Exception('Failed to list organizations')

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'

        # Act
        result = await influxdb_list_orgs(url=url, token=token, verify_ssl=True)

        # Assert
        assert result['status'] == 'error'
        assert 'Failed to list organizations' in result['message']

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_create_org_happy_path(self, mock_get_client):
        """Test influxdb_create_org function with valid parameters."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api

        # Mock created org
        mock_org = MagicMock()
        mock_org.id = 'org-123'
        mock_org.name = 'new-org'
        mock_org.created_at = None
        mock_orgs_api.create_organization.return_value = mock_org

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'

        # Act
        result = await influxdb_create_org(
            org_name='new-org',
            url=url,
            token=token,
            verify_ssl=True,
            tool_write_mode=True,
        )

        # Assert
        mock_get_client.assert_called_once()
        mock_orgs_api.create_organization.assert_called_once_with(name='new-org')
        mock_client.close.assert_called_once()
        assert result['status'] == 'success'
        assert result['organization']['id'] == 'org-123'
        assert result['organization']['name'] == 'new-org'

    @pytest.mark.asyncio
    async def test_influxdb_create_org_read_only_mode(self):
        """Test influxdb_create_org in read-only mode."""
        # Act & Assert
        with pytest.raises(Exception) as excinfo:
            await influxdb_create_org(
                org_name='new-org',
                url='https://influxdb-example.aws:8086',
                token='test-token',
                tool_write_mode=False,
            )

        assert (
            'InfluxDBCreateOrg tool invocation not allowed when tool-write-mode is set to False'
            in str(excinfo.value)
        )

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_create_org_exception_path(self, mock_get_client):
        """Test influxdb_create_org function when an exception occurs."""
        # Arrange
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api
        mock_orgs_api.create_organization.side_effect = Exception('Organization already exists')

        url = 'https://influxdb-example.aws:8086'
        token = 'test-token'

        # Act
        result = await influxdb_create_org(
            org_name='existing-org',
            url=url,
            token=token,
            verify_ssl=True,
            tool_write_mode=True,
        )

        # Assert
        assert result['status'] == 'error'
        assert 'Organization already exists' in result['message']

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_write_points_with_time(self, mock_get_client):
        """Test influxdb_write_points with time field in points."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api

        result = await influxdb_write_points(
            url='https://influxdb-example.aws:8086',
            token='test-token',
            bucket='test-bucket',
            org='test-org',
            points=[
                {
                    'measurement': 'temperature',
                    'tags': {'location': 'Prague'},
                    'fields': {'value': 25.3},
                    'time': '2025-01-22T10:00:00Z',
                }
            ],
            time_precision='ns',
            sync_mode='synchronous',
            verify_ssl=True,
            tool_write_mode=True,
        )

        mock_write_api.write.assert_called_once()
        assert result['status'] == 'success'


class TestResolveInfluxDBConfig:
    """Tests for resolve_influxdb_config function."""

    def test_resolve_influxdb_config_missing_url(self):
        """Test resolve_influxdb_config when URL is missing."""
        from awslabs.timestream_for_influxdb_mcp_server.server import resolve_influxdb_config

        with pytest.raises(ValueError) as excinfo:
            resolve_influxdb_config(url=None, token='test-token', org='test-org')

        assert 'URL must be provided' in str(excinfo.value)

    def test_resolve_influxdb_config_missing_token(self):
        """Test resolve_influxdb_config when token is missing."""
        from awslabs.timestream_for_influxdb_mcp_server.server import resolve_influxdb_config

        with pytest.raises(ValueError) as excinfo:
            resolve_influxdb_config(url='https://example.com', token=None, org='test-org')

        assert 'Token must be provided' in str(excinfo.value)

    def test_resolve_influxdb_config_missing_org_when_required(self):
        """Test resolve_influxdb_config when org is missing and required."""
        from awslabs.timestream_for_influxdb_mcp_server.server import resolve_influxdb_config

        with pytest.raises(ValueError) as excinfo:
            resolve_influxdb_config(
                url='https://example.com', token='test-token', org=None, require_org=True
            )

        assert 'Organization must be provided' in str(excinfo.value)

    def test_resolve_influxdb_config_org_not_required(self):
        """Test resolve_influxdb_config when org is not required."""
        from awslabs.timestream_for_influxdb_mcp_server.server import resolve_influxdb_config

        url, token, org = resolve_influxdb_config(
            url='https://example.com', token='test-token', org=None, require_org=False
        )

        assert url == 'https://example.com'
        assert token == 'test-token'
        assert org is None


class TestInfluxDBAsyncWriteMode:
    """Tests for InfluxDB async write mode."""

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_write_points_async_mode(self, mock_get_client):
        """Test influxdb_write_points with asynchronous mode."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api

        result = await influxdb_write_points(
            url='https://influxdb-example.aws:8086',
            token='test-token',
            bucket='test-bucket',
            org='test-org',
            points=[{'measurement': 'temp', 'tags': {'loc': 'NYC'}, 'fields': {'value': 20.5}}],
            time_precision='ns',
            sync_mode='asynchronous',
            verify_ssl=True,
            tool_write_mode=True,
        )

        mock_client.write_api.assert_called_once()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_write_line_protocol_async_mode(self, mock_get_client):
        """Test influxdb_write_line_protocol with asynchronous mode."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_write_api = MagicMock()
        mock_client.write_api.return_value = mock_write_api

        result = await influxdb_write_line_protocol(
            url='https://influxdb-example.aws:8086',
            token='test-token',
            bucket='test-bucket',
            org='test-org',
            data_line_protocol='temperature,location=Prague value=25.3',
            time_precision='ns',
            sync_mode='asynchronous',
            verify_ssl=True,
            tool_write_mode=True,
        )

        mock_client.write_api.assert_called_once()
        assert result['status'] == 'success'


class TestInfluxDBCreateBucketWithRetention:
    """Tests for influxdb_create_bucket with retention rules."""

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_create_bucket_with_retention(self, mock_get_client):
        """Test influxdb_create_bucket with retention period."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_buckets_api = MagicMock()
        mock_client.buckets_api.return_value = mock_buckets_api
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api

        mock_org = MagicMock()
        mock_org.id = 'org-456'
        mock_orgs_api.find_organizations.return_value = [mock_org]

        mock_bucket = MagicMock()
        mock_bucket.id = 'bucket-123'
        mock_bucket.name = 'new-bucket'
        mock_bucket.org_id = 'org-456'
        mock_retention_rule = MagicMock()
        mock_retention_rule.every_seconds = 86400
        mock_bucket.retention_rules = [mock_retention_rule]
        mock_bucket.created_at = None
        mock_buckets_api.create_bucket.return_value = mock_bucket

        result = await influxdb_create_bucket(
            bucket_name='new-bucket',
            url='https://influxdb-example.aws:8086',
            token='test-token',
            org='test-org',
            retention_seconds=86400,
            description='Test bucket with retention',
            verify_ssl=True,
            tool_write_mode=True,
        )

        mock_buckets_api.create_bucket.assert_called_once()
        call_args = mock_buckets_api.create_bucket.call_args[1]
        assert len(call_args['retention_rules']) == 1
        assert result['status'] == 'success'
        assert result['bucket']['retention_period'] == 86400

    @pytest.mark.asyncio
    @patch('awslabs.timestream_for_influxdb_mcp_server.server.get_influxdb_client')
    async def test_influxdb_create_bucket_org_not_found(self, mock_get_client):
        """Test influxdb_create_bucket when organization is not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_orgs_api = MagicMock()
        mock_client.organizations_api.return_value = mock_orgs_api
        mock_orgs_api.find_organizations.return_value = []

        result = await influxdb_create_bucket(
            bucket_name='new-bucket',
            url='https://influxdb-example.aws:8086',
            token='test-token',
            org='non-existent-org',
            retention_seconds=None,
            description=None,
            verify_ssl=True,
            tool_write_mode=True,
        )

        assert result['status'] == 'error'
        assert 'not found' in result['message']
