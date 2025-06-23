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

"""Tests for the cluster_metrics_tools module."""

import pytest
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools import (
    get_cluster_metrics,
    get_monitoring_level_rank,
    list_available_metrics,
)
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class TestClusterMetricsTools:
    """Tests for the cluster_metrics_tools module."""

    def test_get_monitoring_level_rank(self):
        """Test the get_monitoring_level_rank function."""
        # Test all valid monitoring levels
        assert get_monitoring_level_rank('DEFAULT') == 0
        assert get_monitoring_level_rank('PER_BROKER') == 1
        assert get_monitoring_level_rank('PER_TOPIC_PER_BROKER') == 2
        assert get_monitoring_level_rank('PER_TOPIC_PER_PARTITION') == 3

        # Test invalid monitoring level
        assert get_monitoring_level_rank('INVALID') == -1
        assert get_monitoring_level_rank(None) == -1

    def test_list_available_metrics(self):
        """Test the list_available_metrics function."""
        # Test with valid monitoring level
        metrics = list_available_metrics('DEFAULT')
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

        # Check structure of a metric
        for metric_name, metric_config in metrics.items():
            assert 'monitoring_level' in metric_config
            assert 'default_statistic' in metric_config
            assert 'dimensions' in metric_config
            assert metric_config['monitoring_level'] == 'DEFAULT'

        # Test with invalid monitoring level
        metrics = list_available_metrics('INVALID')
        assert isinstance(metrics, dict)
        assert len(metrics) == 0

        # Test with None monitoring level
        with pytest.raises(ValueError) as excinfo:
            list_available_metrics(None)
        assert 'Monitoring level must be provided' in str(excinfo.value)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    def test_get_cluster_metrics_basic(self, mock_boto3_client, mock_get_cluster_name):
        """Test the get_cluster_metrics function with basic parameters."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT'}
        }

        # Mock the response from get_metric_data
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'GlobalTopicCount',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [10, 12, 15],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        metrics = ['GlobalTopicCount']

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

        # Verify the result
        assert 'MetricDataResults' in result
        assert len(result['MetricDataResults']) == 1
        assert result['MetricDataResults'][0]['Label'] == 'GlobalTopicCount'
        assert len(result['MetricDataResults'][0]['Values']) == 3

        # Verify the calls
        mock_kafka_client.describe_cluster.assert_called_once_with(ClusterArn=cluster_arn)
        mock_get_cluster_name.assert_called_once_with(cluster_arn)
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Verify the parameters passed to get_metric_data
        args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
        assert 'MetricDataQueries' in kwargs
        assert len(kwargs['MetricDataQueries']) == 1
        assert kwargs['MetricDataQueries'][0]['Id'] == 'm0'
        assert (
            kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['MetricName']
            == 'GlobalTopicCount'
        )
        assert kwargs['MetricDataQueries'][0]['MetricStat']['Period'] == period
        assert kwargs['StartTime'] == start_time
        assert kwargs['EndTime'] == end_time

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    def test_get_cluster_metrics_with_broker_metrics(
        self, mock_boto3_client, mock_get_cluster_name
    ):
        """Test the get_cluster_metrics function with broker-level metrics."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'PER_BROKER'}
        }

        # Mock the response from list_nodes
        mock_kafka_client.list_nodes.return_value = {
            'NodeInfoList': [
                {'BrokerNodeInfo': {'BrokerId': 1}},
                {'BrokerNodeInfo': {'BrokerId': 2}},
                {'BrokerNodeInfo': {'BrokerId': 3}},
            ]
        }

        # Mock the response from get_metric_data
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0_1',
                    'Label': 'BytesInPerSec Broker 1',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [1000, 1100, 1200],
                    'StatusCode': 'Complete',
                },
                {
                    'Id': 'm0_2',
                    'Label': 'BytesInPerSec Broker 2',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [1100, 1200, 1300],
                    'StatusCode': 'Complete',
                },
                {
                    'Id': 'm0_3',
                    'Label': 'BytesInPerSec Broker 3',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [1200, 1300, 1400],
                    'StatusCode': 'Complete',
                },
            ]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
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

        # Verify the result
        assert 'MetricDataResults' in result
        assert len(result['MetricDataResults']) == 3

        # Verify the calls
        mock_kafka_client.describe_cluster.assert_called_once_with(ClusterArn=cluster_arn)
        mock_kafka_client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)
        # get_cluster_name is called multiple times for each broker, so we don't check the exact call count
        assert mock_get_cluster_name.call_count > 0
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Verify the parameters passed to get_metric_data
        args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
        assert 'MetricDataQueries' in kwargs
        assert len(kwargs['MetricDataQueries']) == 3

        # Check that each broker has a query
        broker_ids = set()
        for query in kwargs['MetricDataQueries']:
            assert query['MetricStat']['Metric']['MetricName'] == 'BytesInPerSec'
            assert query['MetricStat']['Period'] == period

            # Extract broker ID from the dimensions
            for dimension in query['MetricStat']['Metric']['Dimensions']:
                if dimension['Name'] == 'Broker ID':
                    broker_ids.add(dimension['Value'])

        # Verify that all broker IDs are included
        assert broker_ids == {'1', '2', '3'}

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    def test_get_cluster_metrics_with_metric_dict(self, mock_boto3_client, mock_get_cluster_name):
        """Test the get_cluster_metrics function with a dictionary of metrics and statistics."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT'}
        }

        # Mock the response from get_metric_data
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'GlobalTopicCount',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [10, 12, 15],
                    'StatusCode': 'Complete',
                },
                {
                    'Id': 'm1',
                    'Label': 'GlobalPartitionCount',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [30, 36, 45],
                    'StatusCode': 'Complete',
                },
            ]
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        metrics = {'GlobalTopicCount': 'Average', 'GlobalPartitionCount': 'Sum'}

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

        # Verify the result
        assert 'MetricDataResults' in result
        assert len(result['MetricDataResults']) == 2

        # Verify the calls
        mock_kafka_client.describe_cluster.assert_called_once_with(ClusterArn=cluster_arn)
        # get_cluster_name is called multiple times for each metric, so we don't check the exact call count
        assert mock_get_cluster_name.call_count > 0
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Verify the parameters passed to get_metric_data
        args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
        assert 'MetricDataQueries' in kwargs
        assert len(kwargs['MetricDataQueries']) == 2

        # Check that each metric has the correct statistic
        for query in kwargs['MetricDataQueries']:
            metric_name = query['MetricStat']['Metric']['MetricName']
            assert metric_name in metrics
            assert query['MetricStat']['Stat'] == metrics[metric_name]

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    def test_get_cluster_metrics_with_optional_params(
        self, mock_boto3_client, mock_get_cluster_name
    ):
        """Test the get_cluster_metrics function with optional parameters."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT'}
        }

        # Mock the response from get_metric_data
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'GlobalTopicCount',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [10, 12, 15],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # For pagination, we need to mock the paginator
        mock_paginator = MagicMock()
        mock_paginate = MagicMock()
        mock_build_full_result = MagicMock()
        mock_build_full_result.return_value = mock_cloudwatch_client.get_metric_data.return_value
        mock_paginate.return_value.build_full_result = mock_build_full_result
        mock_paginator.paginate = mock_paginate
        mock_cloudwatch_client.get_paginator.return_value = mock_paginator

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        metrics = ['GlobalTopicCount']
        scan_by = 'TimestampDescending'
        label_options = {'timezone': 'UTC'}
        pagination_config = {'MaxItems': 100, 'PageSize': 10}

        # Call the function
        result = get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            client_manager=mock_client_manager,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
            scan_by=scan_by,
            label_options=label_options,
            pagination_config=pagination_config,
        )

        # Verify the result
        assert 'MetricDataResults' in result
        assert len(result['MetricDataResults']) == 1

        # Verify the calls
        mock_kafka_client.describe_cluster.assert_called_once_with(ClusterArn=cluster_arn)
        assert mock_get_cluster_name.call_count > 0

        # When pagination_config is provided, get_paginator is used instead of get_metric_data
        mock_cloudwatch_client.get_paginator.assert_called_once_with('get_metric_data')

        # Verify the parameters passed to paginate
        args, kwargs = mock_paginator.paginate.call_args
        assert 'MetricDataQueries' in kwargs
        assert kwargs['StartTime'] == start_time
        assert kwargs['EndTime'] == end_time
        assert kwargs['ScanBy'] == scan_by
        assert kwargs['LabelOptions'] == label_options

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    def test_get_cluster_metrics_error_handling(self, mock_boto3_client, mock_get_cluster_name):
        """Test the get_cluster_metrics function's error handling."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster to raise an error
        mock_kafka_client.describe_cluster.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Cluster not found'}},
            'DescribeCluster',
        )

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        metrics = ['GlobalTopicCount']

        # Call the function and expect an error
        with pytest.raises(ClientError) as excinfo:
            get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                client_manager=mock_client_manager,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
            )

        # Verify the error
        assert 'ResourceNotFoundException' in str(excinfo.value)
        assert 'Cluster not found' in str(excinfo.value)

        # Verify the calls
        mock_kafka_client.describe_cluster.assert_called_once_with(ClusterArn=cluster_arn)
        mock_cloudwatch_client.get_metric_data.assert_not_called()

    def test_get_cluster_metrics_missing_client_manager(self):
        """Test the get_cluster_metrics function with a missing client manager."""
        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        metrics = ['GlobalTopicCount']

        # Call the function and expect an error
        with pytest.raises(ValueError) as excinfo:
            get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                client_manager=None,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
            )

        # Verify the error
        assert 'Client manager must be provided' in str(excinfo.value)
