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

"""Tests for the aws-msk MCP Server."""

from awslabs.aws_msk_mcp_server.tools.static_tools.cluster_best_practices import (
    get_cluster_best_practices,
)


class TestClusterBestPractices:
    """Tests for the get_cluster_best_practices function."""

    def test_valid_instance_type(self):
        """Test with a valid instance type."""
        # Arrange
        instance_type = 'kafka.m5.large'
        number_of_brokers = 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert result['Number of Brokers'] == f'{number_of_brokers} (provided as input)'
        assert result['vCPU per Broker'] == 2
        assert result['Memory (GB) per Broker'] == '8 (available on the host)'
        assert result['Recommended Partitions per Broker'] == 1000
        assert result['Recommended Max Partitions per Cluster'] == 3000  # 1000 * 3
        assert result['Replication Factor'] == '3 (recommended)'
        assert result['Minimum In-Sync Replicas'] == 2

    def test_express_instance_type(self):
        """Test with an express instance type."""
        # Arrange
        instance_type = 'express.m7g.large'
        number_of_brokers = 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert result['Instance Type'] == f'{instance_type} (provided as input)'
        assert 'express clusters' in result['Replication Factor']
        assert (
            result['Replication Factor']
            == '3 (Note: For express clusters, replication factor should always be 3)'
        )

    def test_invalid_instance_type(self):
        """Test with an invalid instance type."""
        # Arrange
        instance_type = 'invalid.instance.type'
        number_of_brokers = 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert 'Error' in result
        assert f"Instance type '{instance_type}' is not supported or recognized" in result['Error']

    def test_small_broker_count(self):
        """Test with a broker count less than the recommended replication factor."""
        # Arrange
        instance_type = 'kafka.m5.large'
        number_of_brokers = 2  # Less than recommended replication factor of 3

        # Act
        result = get_cluster_best_practices(instance_type, number_of_brokers)

        # Assert
        assert result['Replication Factor'] == '2 (recommended)'
        assert result['Minimum In-Sync Replicas'] == 2
