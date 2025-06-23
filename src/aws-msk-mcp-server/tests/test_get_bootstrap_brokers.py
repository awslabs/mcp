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

"""Tests for the get_bootstrap_brokers module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.get_bootstrap_brokers import (
    get_bootstrap_brokers,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestGetBootstrapBrokers:
    """Tests for the get_bootstrap_brokers module."""

    def test_get_bootstrap_brokers_basic(self):
        """Test the get_bootstrap_brokers function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'BootstrapBrokerString': 'broker1:9092,broker2:9092,broker3:9092',
            'BootstrapBrokerStringTls': 'broker1:9094,broker2:9094,broker3:9094',
            'BootstrapBrokerStringSaslScram': 'broker1:9096,broker2:9096,broker3:9096',
            'BootstrapBrokerStringSaslIam': 'broker1:9098,broker2:9098,broker3:9098',
        }
        mock_client.get_bootstrap_brokers.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = get_bootstrap_brokers(cluster_arn, mock_client)

        # Assert
        mock_client.get_bootstrap_brokers.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'BootstrapBrokerString' in result
        assert 'BootstrapBrokerStringTls' in result
        assert 'BootstrapBrokerStringSaslScram' in result
        assert 'BootstrapBrokerStringSaslIam' in result

    def test_get_bootstrap_brokers_partial_response(self):
        """Test the get_bootstrap_brokers function with a partial response."""
        # Arrange
        mock_client = MagicMock()
        # Only plaintext and TLS endpoints are available
        expected_response = {
            'BootstrapBrokerString': 'broker1:9092,broker2:9092,broker3:9092',
            'BootstrapBrokerStringTls': 'broker1:9094,broker2:9094,broker3:9094',
        }
        mock_client.get_bootstrap_brokers.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = get_bootstrap_brokers(cluster_arn, mock_client)

        # Assert
        mock_client.get_bootstrap_brokers.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'BootstrapBrokerString' in result
        assert 'BootstrapBrokerStringTls' in result
        assert 'BootstrapBrokerStringSaslScram' not in result
        assert 'BootstrapBrokerStringSaslIam' not in result

    def test_get_bootstrap_brokers_error(self):
        """Test the get_bootstrap_brokers function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_bootstrap_brokers.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'GetBootstrapBrokers',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            get_bootstrap_brokers(cluster_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.get_bootstrap_brokers.assert_called_once_with(ClusterArn=cluster_arn)

    def test_get_bootstrap_brokers_missing_client(self):
        """Test the get_bootstrap_brokers function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            get_bootstrap_brokers(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
