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

"""Unit tests for the cluster_metrics_tools module in logs_and_telemetry."""

import unittest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools import (
    get_cluster_metrics,
    get_monitoring_level_rank,
    list_available_metrics,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


class TestClusterMetricsTools(unittest.TestCase):
    """Tests for the cluster_metrics_tools module in logs_and_telemetry."""

    def test_get_monitoring_level_rank(self):
        """Test the get_monitoring_level_rank function."""
        # Test the rank of each monitoring level
        self.assertEqual(get_monitoring_level_rank('DEFAULT'), 0)
        self.assertEqual(get_monitoring_level_rank('PER_BROKER'), 1)
        self.assertEqual(get_monitoring_level_rank('PER_TOPIC_PER_BROKER'), 2)
        self.assertEqual(get_monitoring_level_rank('PER_TOPIC_PER_PARTITION'), 3)

        # Test with an invalid monitoring level
        self.assertEqual(get_monitoring_level_rank('INVALID_LEVEL'), -1)

    def test_list_available_metrics_provisioned(self):
        """Test the list_available_metrics function for provisioned clusters."""
        # Test listing available metrics for a provisioned cluster with DEFAULT monitoring level
        result = list_available_metrics(monitoring_level='DEFAULT', serverless=False)

        # Check that the result is a dictionary
        self.assertIsInstance(result, dict)

        # Check that the result contains metrics
        self.assertGreater(len(result), 0)

        # Check that all metrics have the correct monitoring level
        for metric_name, config in result.items():
            self.assertEqual(config['monitoring_level'], 'DEFAULT')

    def test_list_available_metrics_serverless(self):
        """Test the list_available_metrics function for serverless clusters."""
        # Test listing available metrics for a serverless cluster with DEFAULT monitoring level
        result = list_available_metrics(monitoring_level='DEFAULT', serverless=True)

        # Check that the result is a dictionary
        self.assertIsInstance(result, dict)

        # Check that the result contains metrics
        self.assertGreater(len(result), 0)

        # Check that all metrics have the correct monitoring level
        for metric_name, config in result.items():
            self.assertEqual(config['monitoring_level'], 'DEFAULT')

    def test_list_available_metrics_no_monitoring_level(self):
        """Test the list_available_metrics function with no monitoring level."""
        # Test that ValueError is raised when no monitoring level is provided
        with self.assertRaises(ValueError):
            list_available_metrics(monitoring_level=None, serverless=False)

        with self.assertRaises(ValueError):
            list_available_metrics(monitoring_level=None, serverless=True)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_list_metrics(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with a list of metrics."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        mock_kafka_client.list_nodes.return_value = {
            'NodeInfoList': [
                {'BrokerNodeInfo': {'BrokerId': '1'}},
                {'BrokerNodeInfo': {'BrokerId': '2'}},
            ]
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0_1',
                    'Label': 'BytesInPerSec',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [1.2],
                    'StatusCode': 'Complete',
                },
                {
                    'Id': 'm0_2',
                    'Label': 'BytesInPerSec',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [2.4],
                    'StatusCode': 'Complete',
                },
                {
                    'Id': 'm1',
                    'Label': 'GlobalTopicCount',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [10],
                    'StatusCode': 'Complete',
                },
            ]
        }

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['BytesInPerSec', 'GlobalTopicCount']

        # Call the function
        result = get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
            client_manager=mock_client_manager,
        )

        # Verify kafka client was called to get cluster info
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify kafka client was called to get broker IDs for BytesInPerSec
        mock_kafka_client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify cloudwatch client was called to get metric data
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Check the parameters passed to get_metric_data
        call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
        self.assertEqual(call_args['StartTime'], start_time)
        self.assertEqual(call_args['EndTime'], end_time)

        # Check that the metric queries were constructed correctly
        metric_queries = call_args['MetricDataQueries']
        self.assertEqual(
            len(metric_queries), 3
        )  # 2 for BytesInPerSec (one per broker) + 1 for GlobalTopicCount

        # Check that the result contains the expected metrics
        self.assertEqual(len(result['MetricDataResults']), 3)

        # Verify the result
        self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_dict_metrics(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with a dictionary of metrics."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        mock_kafka_client.list_nodes.return_value = {
            'NodeInfoList': [{'BrokerNodeInfo': {'BrokerId': '1'}}]
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0_1',
                    'Label': 'BytesInPerSec',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [1.2],
                    'StatusCode': 'Complete',
                },
                {
                    'Id': 'm1',
                    'Label': 'GlobalTopicCount',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [10],
                    'StatusCode': 'Complete',
                },
            ]
        }

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = {'BytesInPerSec': 'Sum', 'GlobalTopicCount': 'Average'}

        # Call the function
        result = get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
            client_manager=mock_client_manager,
        )

        # Verify kafka client was called to get cluster info
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify kafka client was called to get broker IDs for BytesInPerSec
        mock_kafka_client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify cloudwatch client was called to get metric data
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Check the parameters passed to get_metric_data
        call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
        self.assertEqual(call_args['StartTime'], start_time)
        self.assertEqual(call_args['EndTime'], end_time)

        # Check that the metric queries were constructed correctly
        metric_queries = call_args['MetricDataQueries']
        self.assertEqual(
            len(metric_queries), 2
        )  # 1 for BytesInPerSec (one broker) + 1 for GlobalTopicCount

        # Check that the statistics were set correctly
        bytes_in_query = next(
            q for q in metric_queries if 'BytesInPerSec' in q['MetricStat']['Metric']['MetricName']
        )
        self.assertEqual(bytes_in_query['MetricStat']['Stat'], 'Sum')

        global_topic_query = next(
            q
            for q in metric_queries
            if 'GlobalTopicCount' in q['MetricStat']['Metric']['MetricName']
        )
        self.assertEqual(global_topic_query['MetricStat']['Stat'], 'Average')

        # Verify the result
        self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_serverless(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function for a serverless cluster."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

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
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
            client_manager=mock_client_manager,
        )

        # Verify kafka client was called to get cluster info
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify kafka client was NOT called to get broker IDs for serverless cluster
        mock_kafka_client.list_nodes.assert_not_called()

        # Verify cloudwatch client was called to get metric data
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Check the parameters passed to get_metric_data
        call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
        self.assertEqual(call_args['StartTime'], start_time)
        self.assertEqual(call_args['EndTime'], end_time)

        # Check that the metric queries were constructed correctly
        metric_queries = call_args['MetricDataQueries']
        self.assertEqual(len(metric_queries), 1)  # 1 for BytesInPerSec

        # Verify the result
        self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_with_optional_params(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with optional parameters."""
        # Setup
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()
        mock_cloudwatch_client = MagicMock()
        mock_paginator = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            elif service_name == 'cloudwatch':
                return mock_cloudwatch_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Set up mock return values
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        mock_cloudwatch_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value.build_full_result.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'GlobalTopicCount',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [10],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['GlobalTopicCount']
        scan_by = 'TimestampDescending'
        label_options = {'timezone': 'UTC'}
        pagination_config = {'PageSize': 500}

        # Call the function
        result = get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
            client_manager=mock_client_manager,
            scan_by=scan_by,
            label_options=label_options,
            pagination_config=pagination_config,
        )

        # Verify kafka client was called to get cluster info
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify cloudwatch client was called to get paginator
        mock_cloudwatch_client.get_paginator.assert_called_once_with('get_metric_data')

        # Verify paginator was called with correct parameters
        paginate_call_args = mock_paginator.paginate.call_args[1]
        self.assertEqual(paginate_call_args['StartTime'], start_time)
        self.assertEqual(paginate_call_args['EndTime'], end_time)
        self.assertEqual(paginate_call_args['ScanBy'], scan_by)
        self.assertEqual(paginate_call_args['LabelOptions'], label_options)
        self.assertEqual(paginate_call_args['PaginationConfig'], pagination_config)

        # Verify the result
        self.assertEqual(
            result, mock_paginator.paginate.return_value.build_full_result.return_value
        )

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_no_client_manager(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with no client manager."""
        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['GlobalTopicCount']

        # Call the function with no client manager
        with self.assertRaises(ValueError) as context:
            get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                client_manager=None,
            )
        self.assertEqual(
            str(context.exception),
            'Client manager must be provided. This function should only be called from get_cluster_telemetry.',
        )

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_client_error(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with a client error."""
        # Setup
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Set up mock to raise ClientError
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to perform: kafka:DescribeCluster',
            }
        }
        mock_kafka_client.describe_cluster_v2.side_effect = ClientError(
            error_response, 'DescribeCluster'
        )

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['GlobalTopicCount']

        # Call the function with a client error
        with self.assertRaises(ClientError) as context:
            get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                client_manager=mock_client_manager,
            )
        self.assertEqual(context.exception.response['Error']['Code'], 'AccessDeniedException')

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_unknown_metric(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with an unknown metric."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'UnknownMetric',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [1.2],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['UnknownMetric']  # This metric is not in the configuration

        # Call the function
        result = get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
            client_manager=mock_client_manager,
        )

        # Verify kafka client was called to get cluster info
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify cloudwatch client was called to get metric data
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Check the parameters passed to get_metric_data
        call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
        metric_queries = call_args['MetricDataQueries']

        # Check that the metric query was constructed with default configuration
        self.assertEqual(len(metric_queries), 1)
        self.assertEqual(metric_queries[0]['MetricStat']['Metric']['MetricName'], 'UnknownMetric')
        self.assertEqual(metric_queries[0]['MetricStat']['Stat'], 'Average')  # Default statistic

        # Verify the result
        self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_unsupported_dimension(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with an unsupported dimension."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'CustomMetric',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [1.2],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the metric_config to include an unsupported dimension
        with patch(
            'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_metric_config'
        ) as mock_get_metric_config:
            mock_get_metric_config.return_value = {
                'monitoring_level': 'DEFAULT',
                'dimensions': ['Cluster Name', 'UnsupportedDimension'],
                'default_statistic': 'Average',
            }

            # Test data
            region = 'us-west-2'
            cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
            start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
            period = 300
            metrics = ['CustomMetric']

            # Call the function
            result = get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                client_manager=mock_client_manager,
            )

            # Verify kafka client was called to get cluster info
            mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

            # Verify cloudwatch client was called to get metric data
            mock_cloudwatch_client.get_metric_data.assert_called_once()

            # Check the parameters passed to get_metric_data
            call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
            metric_queries = call_args['MetricDataQueries']

            # Check that the metric query was constructed with only the supported dimension
            self.assertEqual(len(metric_queries), 1)
            dimensions = metric_queries[0]['MetricStat']['Metric']['Dimensions']
            self.assertEqual(len(dimensions), 1)
            self.assertEqual(dimensions[0]['Name'], 'Cluster Name')
            self.assertEqual(dimensions[0]['Value'], 'test-cluster')

            # Verify the result
            self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_no_dimensions(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with no dimensions."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'EmptyDimensionsMetric',
                    'Timestamps': ['2024-01-01T00:00:00Z'],
                    'Values': [1.2],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the metric_config to include empty dimensions
        with patch(
            'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_metric_config'
        ) as mock_get_metric_config:
            mock_get_metric_config.return_value = {
                'monitoring_level': 'DEFAULT',
                'dimensions': [],  # Empty dimensions
                'default_statistic': 'Average',
            }

            # Test data
            region = 'us-west-2'
            cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
            start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
            period = 300
            metrics = ['EmptyDimensionsMetric']

            # Call the function
            result = get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                client_manager=mock_client_manager,
            )

            # Verify kafka client was called to get cluster info
            mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

            # Verify cloudwatch client was called to get metric data
            mock_cloudwatch_client.get_metric_data.assert_called_once()

            # Check the parameters passed to get_metric_data
            call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
            metric_queries = call_args['MetricDataQueries']

            # Check that the metric query was constructed with the fallback cluster name dimension
            self.assertEqual(len(metric_queries), 1)
            dimensions = metric_queries[0]['MetricStat']['Metric']['Dimensions']
            self.assertEqual(len(dimensions), 1)
            self.assertEqual(dimensions[0]['Name'], 'Cluster Name')
            self.assertEqual(dimensions[0]['Value'], 'test-cluster')

            # Verify the result
            self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_general_exception(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with a general exception."""
        # Setup
        mock_client_manager = MagicMock()
        mock_kafka_client = MagicMock()

        # Configure get_client to return different clients based on service name
        def get_client_side_effect(region, service_name):
            if service_name == 'kafka':
                return mock_kafka_client
            return MagicMock()

        mock_client_manager.get_client.side_effect = get_client_side_effect

        # Set up mock to raise a general exception
        mock_kafka_client.describe_cluster_v2.side_effect = Exception('Unexpected error')

        # Test data
        region = 'us-west-2'
        cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
        start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        period = 300
        metrics = ['GlobalTopicCount']

        # Call the function with a general exception
        with self.assertRaises(Exception) as context:
            get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                client_manager=mock_client_manager,
            )
        self.assertEqual(str(context.exception), 'Unexpected error')

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_unsupported_monitoring_level(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with an unsupported monitoring level."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'EnhancedMonitoring': 'DEFAULT',  # DEFAULT monitoring level
                'ClusterType': 'PROVISIONED',
            }
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': []  # Empty results since the metric will be skipped
        }

        # Mock the metric_config to require a higher monitoring level
        with patch(
            'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_metric_config'
        ) as mock_get_metric_config:
            mock_get_metric_config.return_value = {
                'monitoring_level': 'PER_TOPIC_PER_BROKER',  # Requires higher monitoring level
                'dimensions': ['Cluster Name'],
                'default_statistic': 'Average',
            }

            # Test data
            region = 'us-west-2'
            cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
            start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
            period = 300
            metrics = ['AdvancedMetric']  # This metric requires higher monitoring level

            # Call the function
            result = get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                client_manager=mock_client_manager,
            )

            # Verify kafka client was called to get cluster info
            mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

            # Verify cloudwatch client was called to get metric data
            mock_cloudwatch_client.get_metric_data.assert_called_once()

            # Check the parameters passed to get_metric_data
            call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
            metric_queries = call_args['MetricDataQueries']

            # Check that no metric queries were constructed since the metric was skipped
            self.assertEqual(len(metric_queries), 0)

            # Verify the result
            self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    def test_get_cluster_metrics_serverless_unsupported_metric(self, mock_get_cluster_name):
        """Test the get_cluster_metrics function with an unsupported metric for serverless clusters."""
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
        mock_get_cluster_name.return_value = 'test-cluster'

        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {
                'EnhancedMonitoring': 'DEFAULT',
                'ClusterType': 'SERVERLESS',  # Serverless cluster
            }
        }

        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': []  # Empty results since the metric will be skipped
        }

        # Mock the metric_config and SERVERLESS_METRICS
        with (
            patch(
                'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_metric_config'
            ) as mock_get_metric_config,
            patch(
                'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.SERVERLESS_METRICS',
                new={},
            ),
        ):
            mock_get_metric_config.return_value = {
                'monitoring_level': 'DEFAULT',
                'dimensions': ['Cluster Name'],
                'default_statistic': 'Average',
            }

            # Test data
            region = 'us-west-2'
            cluster_arn = 'arn:aws:kafka:us-west-2:123456789012:cluster/test-cluster/abcd1234'
            start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2024, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
            period = 300
            metrics = ['UnsupportedServerlessMetric']  # This metric is not in SERVERLESS_METRICS

            # Call the function
            result = get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                client_manager=mock_client_manager,
            )

            # Verify kafka client was called to get cluster info
            mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)

            # Verify cloudwatch client was called to get metric data
            mock_cloudwatch_client.get_metric_data.assert_called_once()

            # Check the parameters passed to get_metric_data
            call_args = mock_cloudwatch_client.get_metric_data.call_args[1]
            metric_queries = call_args['MetricDataQueries']

            # Check that no metric queries were constructed since the metric was skipped
            self.assertEqual(len(metric_queries), 0)

            # Verify the result
            self.assertEqual(result, mock_cloudwatch_client.get_metric_data.return_value)


if __name__ == '__main__':
    unittest.main()
