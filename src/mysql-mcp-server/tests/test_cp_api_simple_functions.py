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

"""Tests for internal_get_cluster_properties and internal_get_instance_properties."""

import pytest
from awslabs.mysql_mcp_server.connection.cp_api_connection import (
    internal_create_rds_client,
    internal_get_cluster_properties,
    internal_get_instance_properties,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


class TestInternalGetClusterProperties:
    """Tests for internal_get_cluster_properties."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_returns_cluster_properties(self, mock_create_client):
        """Should return cluster properties for a valid cluster."""
        mock_client = MagicMock()
        mock_client.describe_db_clusters.return_value = {
            'DBClusters': [
                {
                    'DBClusterIdentifier': 'my-cluster',
                    'Status': 'available',
                    'Engine': 'aurora-mysql',
                    'Endpoint': 'my-cluster.cluster-xyz.us-east-1.rds.amazonaws.com',
                    'Port': 3306,
                    'MasterUsername': 'admin',
                    'HttpEndpointEnabled': True,
                    'MasterUserSecret': {'SecretArn': 'arn:secret'},
                    'DBClusterArn': 'arn:aws:rds:us-east-1:123:cluster:my-cluster',
                }
            ]
        }
        mock_create_client.return_value = mock_client

        result = internal_get_cluster_properties('my-cluster', 'us-east-1')

        assert result['DBClusterIdentifier'] == 'my-cluster'
        assert result['Status'] == 'available'
        assert result['Engine'] == 'aurora-mysql'
        assert result['HttpEndpointEnabled'] is True

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_cluster_not_found_raises(self, mock_create_client):
        """Should raise ValueError when cluster is not found."""
        mock_client = MagicMock()
        mock_client.describe_db_clusters.return_value = {'DBClusters': []}
        mock_create_client.return_value = mock_client

        with pytest.raises(ValueError, match='not found'):
            internal_get_cluster_properties('nonexistent', 'us-east-1')

    def test_empty_cluster_identifier_raises(self):
        """Should raise ValueError for empty cluster_identifier."""
        with pytest.raises(ValueError, match='cluster_identifier and region are required'):
            internal_get_cluster_properties('', 'us-east-1')

    def test_empty_region_raises(self):
        """Should raise ValueError for empty region."""
        with pytest.raises(ValueError, match='cluster_identifier and region are required'):
            internal_get_cluster_properties('my-cluster', '')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_client_error_propagates(self, mock_create_client):
        """Should propagate ClientError from AWS."""
        mock_client = MagicMock()
        mock_client.describe_db_clusters.side_effect = ClientError(
            {'Error': {'Code': 'DBClusterNotFoundFault', 'Message': 'not found'}},
            'DescribeDBClusters',
        )
        mock_create_client.return_value = mock_client

        with pytest.raises(ClientError):
            internal_get_cluster_properties('my-cluster', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_unexpected_error_propagates(self, mock_create_client):
        """Should propagate unexpected errors."""
        mock_client = MagicMock()
        mock_client.describe_db_clusters.side_effect = RuntimeError('unexpected')
        mock_create_client.return_value = mock_client

        with pytest.raises(RuntimeError, match='unexpected'):
            internal_get_cluster_properties('my-cluster', 'us-east-1')


class TestInternalGetInstanceProperties:
    """Tests for internal_get_instance_properties."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_returns_instance_properties(self, mock_create_client):
        """Should return instance properties for a matching endpoint."""
        mock_client = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'my-instance',
                        'Endpoint': {
                            'Address': 'my-instance.xyz.us-east-1.rds.amazonaws.com',
                            'Port': 3306,
                        },
                        'MasterUsername': 'admin',
                        'MasterUserSecret': {'SecretArn': 'arn:secret'},
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = paginator
        mock_create_client.return_value = mock_client

        result = internal_get_instance_properties(
            'my-instance.xyz.us-east-1.rds.amazonaws.com', 'us-east-1'
        )

        assert result['DBInstanceIdentifier'] == 'my-instance'
        assert result['MasterUsername'] == 'admin'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_instance_not_found_raises(self, mock_create_client):
        """Should raise ValueError when no instance matches the endpoint."""
        mock_client = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'other-instance',
                        'Endpoint': {
                            'Address': 'other.xyz.us-east-1.rds.amazonaws.com',
                            'Port': 3306,
                        },
                    }
                ]
            }
        ]
        mock_client.get_paginator.return_value = paginator
        mock_create_client.return_value = mock_client

        with pytest.raises(ValueError, match='error fetching instance'):
            internal_get_instance_properties(
                'nonexistent.xyz.us-east-1.rds.amazonaws.com', 'us-east-1'
            )

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_client_error_propagates(self, mock_create_client):
        """Should propagate ClientError from AWS."""
        mock_client = MagicMock()
        paginator = MagicMock()
        paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'denied'}},
            'DescribeDBInstances',
        )
        mock_client.get_paginator.return_value = paginator
        mock_create_client.return_value = mock_client

        with pytest.raises(ClientError):
            internal_get_instance_properties('ep.rds.amazonaws.com', 'us-east-1')

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_multiple_pages(self, mock_create_client):
        """Should search across multiple pages."""
        mock_client = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'instance-1',
                        'Endpoint': {'Address': 'ep1.rds.amazonaws.com', 'Port': 3306},
                    }
                ]
            },
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'instance-2',
                        'Endpoint': {'Address': 'ep2.rds.amazonaws.com', 'Port': 3306},
                        'MasterUsername': 'admin',
                    }
                ]
            },
        ]
        mock_client.get_paginator.return_value = paginator
        mock_create_client.return_value = mock_client

        result = internal_get_instance_properties('ep2.rds.amazonaws.com', 'us-east-1')
        assert result['DBInstanceIdentifier'] == 'instance-2'

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_empty_pages(self, mock_create_client):
        """Should handle empty pages gracefully."""
        mock_client = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [{'DBInstances': []}]
        mock_client.get_paginator.return_value = paginator
        mock_create_client.return_value = mock_client

        with pytest.raises(ValueError, match='error fetching instance'):
            internal_get_instance_properties('ep.rds.amazonaws.com', 'us-east-1')


class TestInternalCreateRdsClient:
    """Tests for internal_create_rds_client."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.boto3.client')
    def test_creates_rds_client(self, mock_boto_client):
        """Should create an RDS client with the correct region."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        result = internal_create_rds_client('us-west-2')

        mock_boto_client.assert_called_once()
        call_args = mock_boto_client.call_args
        assert call_args[0][0] == 'rds'
        assert call_args[1]['region_name'] == 'us-west-2'
        assert result is mock_client


class TestInternalGetInstancePropertiesGenericException:
    """Cover the generic-Exception branch alongside the ClientError test."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_generic_exception_reraises(self, mock_create_client):
        """Non-ClientError exceptions are logged with type name and re-raised."""
        mock_client = MagicMock()
        paginator = MagicMock()
        paginator.paginate.side_effect = RuntimeError('connection reset')
        mock_client.get_paginator.return_value = paginator
        mock_create_client.return_value = mock_client

        with pytest.raises(RuntimeError, match='connection reset'):
            internal_get_instance_properties('ep.rds.amazonaws.com', 'us-east-1')


class TestInternalCreateAuroraClusterErrors:
    """Tests for internal_create_aurora_cluster's ClientError and generic-Exception branches."""

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_client_error_reraises(self, mock_create_client):
        """ClientError from create_db_cluster is logged and re-raised."""
        from awslabs.mysql_mcp_server.connection.cp_api_connection import (
            internal_create_aurora_cluster,
        )

        mock_client = MagicMock()
        mock_client.create_db_cluster.side_effect = ClientError(
            {'Error': {'Code': 'DBClusterAlreadyExistsFault', 'Message': 'exists'}},
            'CreateDBCluster',
        )
        mock_create_client.return_value = mock_client

        with pytest.raises(ClientError):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='my-cluster',
                engine_version='8.0',
                database_name='app',
            )

    @patch('awslabs.mysql_mcp_server.connection.cp_api_connection.internal_create_rds_client')
    def test_generic_exception_reraises(self, mock_create_client):
        """A non-AWS exception is also logged with the type name and re-raised."""
        from awslabs.mysql_mcp_server.connection.cp_api_connection import (
            internal_create_aurora_cluster,
        )

        mock_client = MagicMock()
        mock_client.create_db_cluster.side_effect = RuntimeError('out of memory')
        mock_create_client.return_value = mock_client

        with pytest.raises(RuntimeError, match='out of memory'):
            internal_create_aurora_cluster(
                region='us-east-1',
                cluster_identifier='my-cluster',
                engine_version='8.0',
                database_name='app',
            )
