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

"""Unit tests for the get_cluster_metrics function in cluster_metrics_tools.py."""

import unittest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools import (
    get_cluster_metrics,
)
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


class TestGetClusterMetrics(unittest.TestCase):
    """Tests for the get_cluster_metrics function in cluster_metrics_tools.py."""

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_monitoring_level_rank'
    )
    def test_get_cluster_metrics_provisioned(self, mock_get_monitoring_level_rank):
        """Test the get_cluster_metrics function with a provisioned cluster."""
        # Setup
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()
        mock_cloudwatch_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            elif service_name == 'cloudwatch':
                return mock_cloudwatch_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Set up mock return values
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'BytesInPerSec',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [1.2],
                    'StatusCode': 'Complete',
                }
            ]
        }

        mock_get_monitoring_level_rank.return_value = 0  # DEFAULT

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['BytesInPerSec']

        # Call the function
        result = get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            client_manager=mock_client_manager,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
        )

        # Verify kafka client was called to get cluster info
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify cloudwatch client was called to get metric data
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Verify the result
        self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_monitoring_level_rank'
    )
    def test_get_cluster_metrics_serverless(self, mock_get_monitoring_level_rank):
        """Test the get_cluster_metrics function with a serverless cluster."""
        # Setup
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()
        mock_cloudwatch_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            elif service_name == 'cloudwatch':
                return mock_cloudwatch_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Set up mock return values
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'SERVERLESS'}
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'BytesInPerSec',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [1.2],
                    'StatusCode': 'Complete',
                }
            ]
        }

        mock_get_monitoring_level_rank.return_value = 0  # DEFAULT

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['BytesInPerSec']

        # Call the function
        result = get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            client_manager=mock_client_manager,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
        )

        # Verify kafka client was called to get cluster info
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify cloudwatch client was called to get metric data
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Verify the result
        self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    def test_get_cluster_metrics_missing_client_manager(self):
        """Test the get_cluster_metrics function with missing client manager."""
        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['BytesInPerSec']

        # Call the function and expect an error
        with self.assertRaises(ValueError) as context:
            get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                client_manager=None,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
            )

        self.assertEqual(
            str(context.exception),
            'Client manager must be provided. This function should only be called from get_cluster_telemetry.',
        )


if __name__ == '__main__':
    unittest.main()
