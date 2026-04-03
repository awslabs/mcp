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
from awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.metric_config import (
    METRICS,
    SERVERLESS_METRICS,
    get_metric_config,
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

    def test_list_available_metrics_serverless(self):
        """Test the list_available_metrics function with serverless=True."""
        # Test with valid monitoring level for serverless
        metrics = list_available_metrics('DEFAULT', serverless=True)
        assert isinstance(metrics, dict)
        assert len(metrics) > 0

        # Check that we're getting serverless metrics
        for metric_name, metric_config in metrics.items():
            assert metric_name in SERVERLESS_METRICS
            assert 'monitoring_level' in metric_config
            assert 'default_statistic' in metric_config
            assert 'dimensions' in metric_config
            assert metric_config['monitoring_level'] == 'DEFAULT'

        # Verify that we get different metrics for serverless vs provisioned
        serverless_metrics = list_available_metrics('DEFAULT', serverless=True)
        provisioned_metrics = list_available_metrics('DEFAULT', serverless=False)
        assert serverless_metrics != provisioned_metrics

        # Test with invalid monitoring level
        metrics = list_available_metrics('INVALID', serverless=True)
        assert isinstance(metrics, dict)
        assert len(metrics) == 0

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
        mock_kafka_client.describe_cluster_v2.return_value = {
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
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
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
        mock_kafka_client.describe_cluster_v2.return_value = {
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
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
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
        mock_kafka_client.describe_cluster_v2.return_value = {
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
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
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
        mock_kafka_client.describe_cluster_v2.return_value = {
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
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
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
        mock_kafka_client.describe_cluster_v2.side_effect = ClientError(
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
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
        mock_cloudwatch_client.get_metric_data.assert_not_called()

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    def test_get_cluster_metrics_serverless(self, mock_boto3_client, mock_get_cluster_name):
        """Test the get_cluster_metrics function with a serverless cluster."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster for a serverless cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'SERVERLESS'}
        }

        # Mock the response from get_metric_data
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'BytesInPerSec',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [1000, 1100, 1200],
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
        metrics = ['BytesInPerSec']  # A metric available for serverless clusters

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
        assert result['MetricDataResults'][0]['Label'] == 'BytesInPerSec'

        # Verify the calls
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
        mock_get_cluster_name.assert_called_with(cluster_arn)
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Verify the parameters passed to get_metric_data
        args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
        assert 'MetricDataQueries' in kwargs
        assert len(kwargs['MetricDataQueries']) == 1
        assert (
            kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['MetricName'] == 'BytesInPerSec'
        )

        # Verify that list_nodes is not called for serverless clusters
        mock_kafka_client.list_nodes.assert_not_called()

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.logger')
    def test_get_cluster_metrics_serverless_with_unsupported_metric(
        self, mock_logger, mock_boto3_client, mock_get_cluster_name
    ):
        """Test the get_cluster_metrics function with a serverless cluster and an unsupported metric."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster for a serverless cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'SERVERLESS'}
        }

        # Mock the response from get_metric_data (empty since metric should be skipped)
        mock_cloudwatch_client.get_metric_data.return_value = {'MetricDataResults': []}

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        # Use a metric that's only available for PROVISIONED clusters
        metrics = ['GlobalTopicCount']  # This metric is not in SERVERLESS_METRICS

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

        # Verify the result (should be empty since metric was skipped)
        assert 'MetricDataResults' in result
        assert len(result['MetricDataResults']) == 0

        # Verify that list_nodes is not called for serverless clusters
        mock_kafka_client.list_nodes.assert_not_called()

        # Verify that get_metric_data is still called (with empty queries)
        mock_cloudwatch_client.get_metric_data.assert_called_once()
        args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
        assert 'MetricDataQueries' in kwargs
        assert len(kwargs['MetricDataQueries']) == 1

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.logger')
    def test_get_cluster_metrics_provisioned_monitoring_level_check(
        self, mock_logger, mock_boto3_client, mock_get_cluster_name
    ):
        """Test the monitoring level check for PROVISIONED clusters in get_cluster_metrics."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster for a provisioned cluster with DEFAULT monitoring
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT', 'ClusterType': 'PROVISIONED'}
        }

        # Mock the response from get_metric_data (empty since metric should be skipped)
        mock_cloudwatch_client.get_metric_data.return_value = {'MetricDataResults': []}

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes

        # Use a metric that requires PER_BROKER monitoring level
        # This should be skipped since the cluster only has DEFAULT monitoring
        metrics = ['BytesInPerSec']  # Assuming this requires PER_BROKER monitoring

        # Patch get_metric_config to return a monitoring level higher than DEFAULT
        with patch(
            'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_metric_config',
            return_value={
                'monitoring_level': 'PER_BROKER',  # Higher than DEFAULT
                'default_statistic': 'Average',
                'dimensions': ['Cluster Name', 'Broker ID'],
            },
        ):
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

            # Verify the result (should be empty since metric was skipped)
            assert 'MetricDataResults' in result
            assert len(result['MetricDataResults']) == 0

            # Verify that the warning was logged about the unsupported monitoring level
            mock_logger.warning.assert_any_call(
                'Metric BytesInPerSec requires PER_BROKER monitoring '
                'but cluster is configured for DEFAULT. Skipping metric.'
            )

            # Verify that list_nodes is not called since metric was skipped
            mock_kafka_client.list_nodes.assert_not_called()

            # Verify that get_metric_data is still called (with empty queries)
            mock_cloudwatch_client.get_metric_data.assert_called_once()
            args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
            assert 'MetricDataQueries' in kwargs
            assert len(kwargs['MetricDataQueries']) == 0

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

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.logger')
    def test_get_cluster_metrics_invalid_metric_name(
        self, mock_logger, mock_boto3_client, mock_get_cluster_name
    ):
        """Test the get_cluster_metrics function with an invalid metric name."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'DEFAULT'}
        }

        # Mock the response from get_metric_data
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm0',
                    'Label': 'InvalidMetricName',
                    'Timestamps': [datetime.now() - timedelta(minutes=i * 5) for i in range(3)],
                    'Values': [0, 0, 0],
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
        metrics = ['InvalidMetricName']  # An invalid metric name that doesn't exist

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

        # Verify that a warning was logged about the invalid metric name
        mock_logger.warning.assert_any_call(
            'No configuration found for metric InvalidMetricName, using default configuration'
        )

        # Verify that the function still returns a result with the default configuration
        assert 'MetricDataResults' in result
        assert len(result['MetricDataResults']) == 1
        assert result['MetricDataResults'][0]['Label'] == 'InvalidMetricName'

        # Verify the calls
        mock_kafka_client.describe_cluster_v2.assert_called_once_with(ClusterArn=cluster_arn)
        mock_cloudwatch_client.get_metric_data.assert_called_once()

        # Verify the parameters passed to get_metric_data
        args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
        assert 'MetricDataQueries' in kwargs
        assert len(kwargs['MetricDataQueries']) == 1
        assert (
            kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['MetricName']
            == 'InvalidMetricName'
        )
        assert (
            kwargs['MetricDataQueries'][0]['MetricStat']['Stat'] == 'Average'
        )  # Default statistic

    def test_metric_config_serverless(self):
        """Test the metric_config module's serverless support."""
        # Test that SERVERLESS_METRICS exists and has the expected structure
        assert SERVERLESS_METRICS is not None
        assert isinstance(SERVERLESS_METRICS, dict)
        assert len(SERVERLESS_METRICS) > 0

        # Check structure of a serverless metric
        for metric_name, metric_config in SERVERLESS_METRICS.items():
            assert 'monitoring_level' in metric_config
            assert 'default_statistic' in metric_config
            assert 'dimensions' in metric_config
            assert 'description' in metric_config

        # Test get_metric_config with serverless=True
        metric_name = list(SERVERLESS_METRICS.keys())[0]  # Get first serverless metric
        config = get_metric_config(metric_name, serverless=True)
        assert config == SERVERLESS_METRICS[metric_name]

        # Test get_metric_config with serverless=False for a metric that exists in both
        if metric_name in METRICS:
            config = get_metric_config(metric_name, serverless=False)
            assert config == METRICS[metric_name]
            assert config != SERVERLESS_METRICS[metric_name]

        # Test get_metric_config with an invalid metric name
        with pytest.raises(KeyError):
            get_metric_config('InvalidMetricName', serverless=True)

    @patch(
        'awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.get_cluster_name'
    )
    @patch('boto3.client')
    @patch('awslabs.aws_msk_mcp_server.tools.logs_and_telemetry.cluster_metrics_tools.logger')
    def test_broker_id_extraction_and_dimension_handling(
        self, mock_logger, mock_boto3_client, mock_get_cluster_name
    ):
        """Test the broker ID extraction and dimension handling in get_cluster_metrics."""
        # Set up mocks
        mock_cloudwatch_client = MagicMock()
        mock_kafka_client = MagicMock()
        mock_client_manager = MagicMock()
        mock_client_manager.get_client.side_effect = lambda region, service: {
            'cloudwatch': mock_cloudwatch_client,
            'kafka': mock_kafka_client,
        }[service]

        # Mock the response from describe_cluster
        mock_kafka_client.describe_cluster_v2.return_value = {
            'ClusterInfo': {'EnhancedMonitoring': 'PER_BROKER'}
        }

        # Mock the response from list_nodes with non-sequential broker IDs to test conversion
        mock_kafka_client.list_nodes.return_value = {
            'NodeInfoList': [
                {'BrokerNodeInfo': {'BrokerId': 1}},
                {'BrokerNodeInfo': {'BrokerId': 3}},  # Non-sequential ID
                {'BrokerNodeInfo': {'BrokerId': 5}},  # Non-sequential ID
            ]
        }

        # Mock the response from get_metric_data
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': []  # Empty results for simplicity
        }

        # Mock the get_cluster_name function
        mock_get_cluster_name.return_value = 'test-cluster'

        # Set up parameters
        region = 'us-east-1'
        cluster_arn = 'arn:aws:kafka:us-east-1:123456789012:cluster/test-cluster/abcdef'
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        period = 300  # 5 minutes
        metrics = ['BytesInPerSec']  # A broker-level metric

        # Call the function
        get_cluster_metrics(
            region=region,
            cluster_arn=cluster_arn,
            client_manager=mock_client_manager,
            start_time=start_time,
            end_time=end_time,
            period=period,
            metrics=metrics,
        )

        # Verify that list_nodes was called to get broker IDs
        mock_kafka_client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

        # Verify that the logger was called with the nodes response and extracted broker IDs
        mock_logger.info.assert_any_call(
            f'Got nodes response: {mock_kafka_client.list_nodes.return_value}'
        )
        mock_logger.info.assert_any_call("Extracted broker IDs: ['1', '3', '5']")

        # Verify the parameters passed to get_metric_data
        args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
        assert 'MetricDataQueries' in kwargs

        # There should be 3 queries, one for each broker
        assert len(kwargs['MetricDataQueries']) == 3

        # Check that each broker has the correct dimensions
        broker_ids_in_queries = set()
        for query in kwargs['MetricDataQueries']:
            broker_id = None
            cluster_name = None

            # Extract broker ID and cluster name from dimensions
            for dimension in query['MetricStat']['Metric']['Dimensions']:
                if dimension['Name'] == 'Broker ID':
                    broker_id = dimension['Value']
                    broker_ids_in_queries.add(broker_id)
                elif dimension['Name'] == 'Cluster Name':
                    cluster_name = dimension['Value']

            # Verify that both dimensions are present
            assert broker_id is not None, 'Broker ID dimension is missing'
            assert cluster_name == 'test-cluster', 'Cluster Name dimension is incorrect'

        # Verify that all broker IDs are included in the queries
        assert broker_ids_in_queries == {'1', '3', '5'}
