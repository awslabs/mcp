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

"""Tests for the describe_replicator module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.replicator.describe_replicator import describe_replicator
from botocore.exceptions import ClientError
from unittest.mock import MagicMock


class TestDescribeReplicator:
    """Tests for the describe_replicator module."""

    def test_describe_replicator_basic(self):
        """Test the describe_replicator function with basic parameters."""
        # Arrange
        mock_client = MagicMock()
        expected_response = {
            'ReplicatorInfo': {
                'ReplicatorArn': 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef',
                'ReplicatorName': 'test-replicator',
                'KafkaClusters': [
                    {
                        'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/source-cluster/abcdef',
                        'Role': 'SOURCE',
                    },
                    {
                        'ClusterArn': 'arn:aws:kafka:us-east-1:123456789012:cluster/target-cluster/abcdef',
                        'Role': 'TARGET',
                    },
                ],
                'ReplicationInfoList': [
                    {
                        'TopicName': 'test-topic',
                        'TopicNamePrefix': 'test-',
                        'TargetCompressionType': 'NONE',
                    }
                ],
                'ServiceExecutionRoleArn': 'arn:aws:iam::123456789012:role/test-role',
                'ReplicatorState': 'ACTIVE',
                'CreationTime': '2025-06-20T10:00:00.000Z',
                'CurrentVersion': '1',
            }
        }
        mock_client.describe_replicator.return_value = expected_response

        # Act
        replicator_arn = 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef'
        result = describe_replicator(replicator_arn, mock_client)

        # Assert
        mock_client.describe_replicator.assert_called_once_with(ReplicatorArn=replicator_arn)
        assert result == expected_response

    def test_describe_replicator_error(self):
        """Test the describe_replicator function when the API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.describe_replicator.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Replicator not found'}},
            'DescribeReplicator',
        )

        # Act & Assert
        replicator_arn = 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef'
        with pytest.raises(ClientError) as excinfo:
            describe_replicator(replicator_arn, mock_client)

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Replicator not found' in str(excinfo.value)
        mock_client.describe_replicator.assert_called_once_with(ReplicatorArn=replicator_arn)

    def test_describe_replicator_missing_client(self):
        """Test the describe_replicator function with a missing client."""
        # Act & Assert
        replicator_arn = 'arn:aws:kafka:us-east-1:123456789012:replicator/test-replicator/abcdef'
        with pytest.raises(ValueError) as excinfo:
            describe_replicator(replicator_arn, None)

        # Verify the error
        assert 'Client must be provided' in str(excinfo.value)
