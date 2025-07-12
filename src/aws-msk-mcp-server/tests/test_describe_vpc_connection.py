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

"""Tests for the describe_vpc_connection module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_vpc.describe_vpc_connection import (
    describe_vpc_connection,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeVpcConnection:
    """Tests for the describe_vpc_connection module."""

    def test_describe_vpc_connection_basic(self):
        """Test the describe_vpc_connection function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        vpc_connection_arn = (
            'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )
        expected_response = {
            'VpcConnectionArn': vpc_connection_arn,
            'VpcConnectionState': 'ACTIVE',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
            'Authentication': {'Sasl': {'Scram': {'Enabled': True}}},
            'CreationTime': '2025-06-20T10:00:00.000Z',
            'VpcId': 'vpc-12345678',
            'SubnetIds': ['subnet-1', 'subnet-2', 'subnet-3'],
            'SecurityGroups': ['sg-1'],
            'ClientSubnets': ['subnet-4', 'subnet-5', 'subnet-6'],
            'Tags': {'Environment': 'Test'},
        }
        mock_client.describe_vpc_connection.return_value = expected_response

        # Act
        result = describe_vpc_connection(vpc_connection_arn, mock_client)

        # Assert
        mock_client.describe_vpc_connection.assert_called_once_with(
            VpcConnectionArn=vpc_connection_arn
        )
        assert result == expected_response
        assert result['VpcConnectionArn'] == vpc_connection_arn
        assert result['VpcConnectionState'] == 'ACTIVE'
        assert (
            result['ClusterArn']
            == 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )
        assert 'Authentication' in result
        assert 'VpcId' in result
        assert 'SubnetIds' in result
        assert 'SecurityGroups' in result
        assert 'ClientSubnets' in result
        assert 'Tags' in result

    def test_describe_vpc_connection_error(self):
        """Test the describe_vpc_connection function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        vpc_connection_arn = (
            'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )
        mock_client.describe_vpc_connection.side_effect = ClientError(
            {'Error': {'Code': 'NotFoundException', 'Message': 'VPC connection not found'}},
            'DescribeVpcConnection',
        )

        # Act & Assert
        with pytest.raises(ClientError) as excinfo:
            describe_vpc_connection(vpc_connection_arn, mock_client)

        # Verify the error
        assert 'NotFoundException' in str(excinfo.value)
        assert 'VPC connection not found' in str(excinfo.value)
        mock_client.describe_vpc_connection.assert_called_once_with(
            VpcConnectionArn=vpc_connection_arn
        )

    def test_describe_vpc_connection_missing_client(self):
        """Test the describe_vpc_connection function with a missing client."""
        # Arrange
        vpc_connection_arn = (
            'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            describe_vpc_connection(vpc_connection_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
