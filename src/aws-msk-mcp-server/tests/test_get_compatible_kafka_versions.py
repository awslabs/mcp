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

"""Tests for the get_compatible_kafka_versions module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.read_cluster.get_compatible_kafka_versions import (
    get_compatible_kafka_versions,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestGetCompatibleKafkaVersions:
    """Tests for the get_compatible_kafka_versions module."""

    def test_get_compatible_kafka_versions_basic(self):
        """Test the get_compatible_kafka_versions function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'CompatibleKafkaVersions': [
                {'SourceVersion': '2.8.1', 'TargetVersions': ['3.3.1', '3.4.0']}
            ]
        }
        mock_client.get_compatible_kafka_versions.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = get_compatible_kafka_versions(cluster_arn, mock_client)

        # Assert
        mock_client.get_compatible_kafka_versions.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'CompatibleKafkaVersions' in result
        assert len(result['CompatibleKafkaVersions']) == 1
        assert result['CompatibleKafkaVersions'][0]['SourceVersion'] == '2.8.1'
        assert '3.3.1' in result['CompatibleKafkaVersions'][0]['TargetVersions']
        assert '3.4.0' in result['CompatibleKafkaVersions'][0]['TargetVersions']

    def test_get_compatible_kafka_versions_multiple_sources(self):
        """Test the get_compatible_kafka_versions function with multiple source versions."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'CompatibleKafkaVersions': [
                {'SourceVersion': '2.8.1', 'TargetVersions': ['3.3.1', '3.4.0']},
                {'SourceVersion': '3.3.1', 'TargetVersions': ['3.4.0', '3.5.0']},
            ]
        }
        mock_client.get_compatible_kafka_versions.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = get_compatible_kafka_versions(cluster_arn, mock_client)

        # Assert
        mock_client.get_compatible_kafka_versions.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'CompatibleKafkaVersions' in result
        assert len(result['CompatibleKafkaVersions']) == 2
        assert result['CompatibleKafkaVersions'][0]['SourceVersion'] == '2.8.1'
        assert result['CompatibleKafkaVersions'][1]['SourceVersion'] == '3.3.1'
        assert '3.5.0' in result['CompatibleKafkaVersions'][1]['TargetVersions']

    def test_get_compatible_kafka_versions_empty_response(self):
        """Test the get_compatible_kafka_versions function with an empty response."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {'CompatibleKafkaVersions': []}
        mock_client.get_compatible_kafka_versions.return_value = expected_response

        # Act
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        result = get_compatible_kafka_versions(cluster_arn, mock_client)

        # Assert
        mock_client.get_compatible_kafka_versions.assert_called_once_with(ClusterArn=cluster_arn)
        assert result == expected_response
        assert 'CompatibleKafkaVersions' in result
        assert len(result['CompatibleKafkaVersions']) == 0

    def test_get_compatible_kafka_versions_error(self):
        """Test the get_compatible_kafka_versions function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.get_compatible_kafka_versions.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'GetCompatibleKafkaVersions',
        )

        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ClientError) as excinfo:
            get_compatible_kafka_versions(cluster_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)
        mock_client.get_compatible_kafka_versions.assert_called_once_with(ClusterArn=cluster_arn)

    def test_get_compatible_kafka_versions_missing_client(self):
        """Test the get_compatible_kafka_versions function with a missing client."""
        # Act & Assert
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        with pytest.raises(ValueError) as excinfo:
            get_compatible_kafka_versions(cluster_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
