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

"""Tests for the reject_client_vpc_connection module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.mutate_vpc.reject_client_vpc_connection import (
    reject_client_vpc_connection,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestRejectClientVpcConnection:
    """Tests for the reject_client_vpc_connection module."""

    def test_reject_client_vpc_connection_basic(self):
        """Test the reject_client_vpc_connection function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'VpcConnectionArn': 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef',
            'VpcConnectionState': 'REJECTED',
            'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef',
        }
        mock_client.reject_client_vpc_connection.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_connection_arn = (
            'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )
        result = reject_client_vpc_connection(cluster_arn, vpc_connection_arn, mock_client)

        # Assert
        mock_client.reject_client_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn, VpcConnectionArn=vpc_connection_arn
        )
        assert result == expected_response
        assert (
            result['VpcConnectionArn']
            == 'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )
        assert result['VpcConnectionState'] == 'REJECTED'
        assert (
            result['ClusterArn']
            == 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        )

    def test_reject_client_vpc_connection_error(self):
        """Test the reject_client_vpc_connection function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.reject_client_vpc_connection.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'VPC connection not found',
                }
            },
            'RejectClientVpcConnection',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_connection_arn = (
            'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )
        with pytest.raises(ClientError) as excinfo:
            reject_client_vpc_connection(cluster_arn, vpc_connection_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'VPC connection not found' in str(excinfo.value)
        mock_client.reject_client_vpc_connection.assert_called_once_with(
            ClusterArn=cluster_arn, VpcConnectionArn=vpc_connection_arn
        )

    def test_reject_client_vpc_connection_missing_client(self):
        """Test the reject_client_vpc_connection function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        vpc_connection_arn = (
            'arn:aws:kafka:us-east-1:123456789012:vpc-connection/test-cluster/abcdef'
        )
        with pytest.raises(ValueError) as excinfo:
            reject_client_vpc_connection(cluster_arn, vpc_connection_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
