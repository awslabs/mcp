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

"""Tests for the create_vpc_connection module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_vpc.create_vpc_connection import create_vpc_connection
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestCreateVpcConnection:
    """Tests for the create_vpc_connection module."""

    def test_create_vpc_connection_basic(self):
        """Test the create_vpc_connection function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'CREATING',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
        }
        mock_client.create_vpc_connection.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_id = 'vpc-12345678'
        subnet_ids = ['subnet-12345678', 'subnet-23456789', 'subnet-34567890']
        security_groups = ['sg-12345678']
        result = create_vpc_connection(
            cluster_arn, vpc_id, subnet_ids, security_groups, mock_client
        )

        # Assert
        mock_client.create_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn,
            VpcId=vpc_id,
            SubnetIds=subnet_ids,
            SecurityGroups=security_groups,
        )
        assert result == expected_response
        assert (
            result['VpcConnectionArn']
            == 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )
        assert result['VpcConnectionState'] == 'CREATING'
        assert (
            result['ClusterArn']
            == 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )
        assert result['VpcId'] == 'vpc-12345678'

    def test_create_vpc_connection_with_authentication(self):
        """Test the create_vpc_connection function with authentication."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'CREATING',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'Authentication': {'Type': 'IAM'},
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
        }
        mock_client.create_vpc_connection.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_id = 'vpc-12345678'
        subnet_ids = ['subnet-12345678', 'subnet-23456789', 'subnet-34567890']
        security_groups = ['sg-12345678']
        authentication_type = 'IAM'
        result = create_vpc_connection(
            cluster_arn, vpc_id, subnet_ids, security_groups, mock_client, authentication_type
        )

        # Assert
        mock_client.create_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn,
            VpcId=vpc_id,
            SubnetIds=subnet_ids,
            SecurityGroups=security_groups,
            Authentication={'Type': 'IAM'},
        )
        assert result == expected_response
        assert result['Authentication']['Type'] == 'IAM'

    def test_create_vpc_connection_with_client_subnets(self):
        """Test the create_vpc_connection function with client subnets."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'CREATING',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
            'ClientSubnets': ['subnet-45678901', 'subnet-56789012'],
        }
        mock_client.create_vpc_connection.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_id = 'vpc-12345678'
        subnet_ids = ['subnet-12345678', 'subnet-23456789', 'subnet-34567890']
        security_groups = ['sg-12345678']
        client_subnets = ['subnet-45678901', 'subnet-56789012']
        result = create_vpc_connection(
            cluster_arn,
            vpc_id,
            subnet_ids,
            security_groups,
            mock_client,
            client_subnets=client_subnets,
        )

        # Assert
        mock_client.create_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn,
            VpcId=vpc_id,
            SubnetIds=subnet_ids,
            SecurityGroups=security_groups,
            ClientSubnets=client_subnets,
        )
        assert result == expected_response
        assert result['ClientSubnets'] == ['subnet-45678901', 'subnet-56789012']

    def test_create_vpc_connection_with_tags(self):
        """Test the create_vpc_connection function with tags."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'CREATING',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
            'Tags': {'Environment': 'Production', 'Owner': 'DataTeam'},
        }
        mock_client.create_vpc_connection.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_id = 'vpc-12345678'
        subnet_ids = ['subnet-12345678', 'subnet-23456789', 'subnet-34567890']
        security_groups = ['sg-12345678']
        tags = {'Environment': 'Production', 'Owner': 'DataTeam'}
        result = create_vpc_connection(
            cluster_arn, vpc_id, subnet_ids, security_groups, mock_client, tags=tags
        )

        # Assert
        mock_client.create_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn,
            VpcId=vpc_id,
            SubnetIds=subnet_ids,
            SecurityGroups=security_groups,
            Tags=tags,
        )
        assert result == expected_response
        assert result['Tags'] == {'Environment': 'Production', 'Owner': 'DataTeam'}

    def test_create_vpc_connection_with_all_parameters(self):
        """Test the create_vpc_connection function with all parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'CREATING',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'Authentication': {'Type': 'IAM'},
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
            'ClientSubnets': ['subnet-45678901', 'subnet-56789012'],
            'Tags': {'Environment': 'Production', 'Owner': 'DataTeam'},
        }
        mock_client.create_vpc_connection.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_id = 'vpc-12345678'
        subnet_ids = ['subnet-12345678', 'subnet-23456789', 'subnet-34567890']
        security_groups = ['sg-12345678']
        authentication_type = 'IAM'
        client_subnets = ['subnet-45678901', 'subnet-56789012']
        tags = {'Environment': 'Production', 'Owner': 'DataTeam'}
        result = create_vpc_connection(
            cluster_arn,
            vpc_id,
            subnet_ids,
            security_groups,
            mock_client,
            authentication_type,
            client_subnets,
            tags,
        )

        # Assert
        mock_client.create_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn,
            VpcId=vpc_id,
            SubnetIds=subnet_ids,
            SecurityGroups=security_groups,
            Authentication={'Type': 'IAM'},
            ClientSubnets=client_subnets,
            Tags=tags,
        )
        assert result == expected_response
        assert result['Authentication']['Type'] == 'IAM'
        assert result['ClientSubnets'] == ['subnet-45678901', 'subnet-56789012']
        assert result['Tags'] == {'Environment': 'Production', 'Owner': 'DataTeam'}

    def test_create_vpc_connection_error(self):
        """Test the create_vpc_connection function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.create_vpc_connection.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}},
            'CreateVpcConnection',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_id = 'vpc-12345678'
        subnet_ids = ['subnet-12345678', 'subnet-23456789', 'subnet-34567890']
        security_groups = ['sg-12345678']
        with pytest.raises(ClientError) as excinfo:
            create_vpc_connection(cluster_arn, vpc_id, subnet_ids, security_groups, mock_client)

        # Verify the error
        assert 'InternalServerError' in str(excinfo.value)
        assert 'Internal server error' in str(excinfo.value)
        mock_client.create_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn,
            VpcId=vpc_id,
            SubnetIds=subnet_ids,
            SecurityGroups=security_groups,
        )

    def test_create_vpc_connection_missing_client(self):
        """Test the create_vpc_connection function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_id = 'vpc-12345678'
        subnet_ids = ['subnet-12345678', 'subnet-23456789', 'subnet-34567890']
        security_groups = ['sg-12345678']
        with pytest.raises(ValueError) as excinfo:
            create_vpc_connection(cluster_arn, vpc_id, subnet_ids, security_groups, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
