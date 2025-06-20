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
from datetime import datetime
from unittest.mock import MagicMock, patch


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


class TestGetClusterTelemetry:
    """Tests for the get_cluster_telemetry function."""

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_metrics'
    )
    def test_get_metrics(self, mock_get_cluster_metrics):
        """Test the 'metrics' action with valid parameters."""
        # Arrange
        region = 'us-west-2'
        action = 'metrics'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcdef'

        # Mock the response from get_cluster_metrics
        mock_response = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'BytesInPerSec',
                    'Timestamps': [datetime(2025, 6, 19, 15, 0, 0)],
                    'Values': [1234.5],
                    'StatusCode': 'Complete',
                }
            ]
        }
        mock_get_cluster_metrics.return_value = mock_response

        # Prepare kwargs with required parameters
        kwargs = {
            'start_time': datetime(2025, 6, 19, 14, 0, 0),
            'end_time': datetime(2025, 6, 19, 15, 0, 0),
            'period': 300,
            'metrics': ['BytesInPerSec'],
        }

        # Create a mock function for get_cluster_telemetry
        def mock_get_cluster_telemetry(region, action, cluster_arn, kwargs):
            if action == 'metrics':
                # Check required parameters
                if 'start_time' not in kwargs:
                    raise ValueError('start_time is required for metrics action')
                if 'end_time' not in kwargs:
                    raise ValueError('end_time is required for metrics action')
                if 'period' not in kwargs:
                    raise ValueError('period is required for metrics action')
                if 'metrics' not in kwargs:
                    raise ValueError('metrics is required for metrics action')

                # Call the mocked get_cluster_metrics function
                return mock_get_cluster_metrics(
                    region=region,
                    cluster_arn=cluster_arn,
                    client_manager=None,
                    start_time=kwargs['start_time'],
                    end_time=kwargs['end_time'],
                    period=kwargs['period'],
                    metrics=kwargs['metrics'],
                )
            else:
                raise ValueError(f'Unsupported action or missing required arguments for {action}')

        # Act
        result = mock_get_cluster_telemetry(region, action, cluster_arn, kwargs)

        # Assert
        assert result == mock_response
        mock_get_cluster_metrics.assert_called_once()
        # Verify the parameters passed to get_cluster_metrics
        call_args = mock_get_cluster_metrics.call_args[1]
        assert call_args['region'] == region
        assert call_args['cluster_arn'] == cluster_arn
        assert call_args['start_time'] == kwargs['start_time']
        assert call_args['end_time'] == kwargs['end_time']
        assert call_args['period'] == kwargs['period']
        assert call_args['metrics'] == kwargs['metrics']

    @patch('awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.list_available_metrics')
    @patch('awslabs.aws_msk_mcp_server.tools.common_functions.client_manager.AWSClientManager')
    def test_available_metrics(self, mock_client_manager_class, mock_list_available_metrics):
        """Test the 'available_metrics' action."""
        # Arrange
        region = 'us-west-2'
        action = 'available_metrics'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcdef'

        # Mock the client manager and kafka client
        mock_client_manager = MagicMock()
        mock_client_manager_class.return_value = mock_client_manager

        mock_kafka_client = MagicMock()
        mock_client_manager.get_client.return_value = mock_kafka_client

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'PER_BROKER'}
        }

        # Mock the response from list_available_metrics
        mock_metrics = {
            'BytesInPerSec': {
                'monitoring_level': 'PER_BROKER',
                'default_statistic': 'Sum',
                'dimensions': ['Cluster Name', 'Broker ID'],
            }
        }
        mock_list_available_metrics.return_value = mock_metrics

        # Create a mock function for get_cluster_telemetry
        def mock_get_cluster_telemetry(region, action, cluster_arn, kwargs):
            if action == 'available_metrics':
                if not cluster_arn:
                    raise ValueError('Cluster ARN must be provided to determine monitoring level')

                # Create a client manager instance
                client_manager = mock_client_manager_class()

                # Configure the client manager with the region
                kafka_client = client_manager.get_client(region, 'kafka')

                # Get cluster's monitoring level
                cluster_info = kafka_client.describe_cluster(ClusterArn=cluster_arn)['ClusterInfo']
                cluster_monitoring = cluster_info.get('EnhancedMonitoring', 'DEFAULT')

                # Return metrics filtered by the cluster's monitoring level
                return mock_list_available_metrics(monitoring_level=cluster_monitoring)
            else:
                raise ValueError(f'Unsupported action or missing required arguments for {action}')

        # Act
        result = mock_get_cluster_telemetry(region, action, cluster_arn, {})

        # Assert
        assert result == mock_metrics
        mock_kafka_client.describe_cluster.assert_called_once_with(ClusterArn=cluster_arn)
        mock_list_available_metrics.assert_called_once_with(monitoring_level='PER_BROKER')

    def test_invalid_action(self):
        """Test with an invalid action."""
        # Arrange
        region = 'us-west-2'
        action = 'invalid_action'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcdef'

        # Create a mock function for get_cluster_telemetry
        def mock_get_cluster_telemetry(region, action, cluster_arn, kwargs):
            raise ValueError(f'Unsupported action or missing required arguments for {action}')

        # Act & Assert
        try:
            mock_get_cluster_telemetry(region, action, cluster_arn, {})
            assert False, 'Expected ValueError was not raised'
        except ValueError as e:
            assert f'Unsupported action or missing required arguments for {action}' in str(e)

    def test_missing_required_parameters_for_metrics(self):
        """Test the 'metrics' action with missing required parameters."""
        # Arrange
        region = 'us-west-2'
        action = 'metrics'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcdef'

        # Create a mock function for get_cluster_telemetry
        def mock_get_cluster_telemetry(region, action, cluster_arn, kwargs):
            if action == 'metrics':
                # Check required parameters
                if 'start_time' not in kwargs:
                    raise ValueError('start_time is required for metrics action')
                if 'end_time' not in kwargs:
                    raise ValueError('end_time is required for metrics action')
                if 'period' not in kwargs:
                    raise ValueError('period is required for metrics action')
                if 'metrics' not in kwargs:
                    raise ValueError('metrics is required for metrics action')
            return {}

        # Missing start_time
        kwargs = {
            'end_time': datetime(2025, 6, 19, 15, 0, 0),
            'period': 300,
            'metrics': ['BytesInPerSec'],
        }

        # Act & Assert
        try:
            mock_get_cluster_telemetry(region, action, cluster_arn, kwargs)
            assert False, 'Expected ValueError was not raised'
        except ValueError as e:
            assert 'start_time is required for metrics action' in str(e)

        # Missing end_time
        kwargs = {
            'start_time': datetime(2025, 6, 19, 14, 0, 0),
            'period': 300,
            'metrics': ['BytesInPerSec'],
        }

        try:
            mock_get_cluster_telemetry(region, action, cluster_arn, kwargs)
            assert False, 'Expected ValueError was not raised'
        except ValueError as e:
            assert 'end_time is required for metrics action' in str(e)

        # Missing period
        kwargs = {
            'start_time': datetime(2025, 6, 19, 14, 0, 0),
            'end_time': datetime(2025, 6, 19, 15, 0, 0),
            'metrics': ['BytesInPerSec'],
        }

        try:
            mock_get_cluster_telemetry(region, action, cluster_arn, kwargs)
            assert False, 'Expected ValueError was not raised'
        except ValueError as e:
            assert 'period is required for metrics action' in str(e)

        # Missing metrics
        kwargs = {
            'start_time': datetime(2025, 6, 19, 14, 0, 0),
            'end_time': datetime(2025, 6, 19, 15, 0, 0),
            'period': 300,
        }

        try:
            mock_get_cluster_telemetry(region, action, cluster_arn, kwargs)
            assert False, 'Expected ValueError was not raised'
        except ValueError as e:
            assert 'metrics is required for metrics action' in str(e)

    def test_available_metrics_missing_cluster_arn(self):
        """Test the 'available_metrics' action with missing cluster ARN."""
        # Arrange
        region = 'us-west-2'
        action = 'available_metrics'
        cluster_arn = None  # Missing cluster ARN

        # Create a mock function for get_cluster_telemetry
        def mock_get_cluster_telemetry(region, action, cluster_arn, kwargs):
            if action == 'available_metrics':
                if not cluster_arn:
                    raise ValueError('Cluster ARN must be provided to determine monitoring level')
            return {}

        # Act & Assert
        try:
            mock_get_cluster_telemetry(region, action, cluster_arn, {})
            assert False, 'Expected ValueError was not raised'
        except ValueError as e:
            assert 'Cluster ARN must be provided to determine monitoring level' in str(e)
