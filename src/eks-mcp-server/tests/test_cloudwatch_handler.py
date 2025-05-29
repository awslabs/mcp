# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
# ruff: noqa: D101, D102, D103
"""Tests for the CloudWatchHandler class."""

import datetime
import pytest
from awslabs.eks_mcp_server.cloudwatch_handler import CloudWatchHandler
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = MagicMock(spec=Context)
    ctx.request_id = 'test-request-id'
    return ctx


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    return MagicMock()


class TestCloudWatchHandler:
    """Tests for the CloudWatchHandler class."""

    def test_init(self, mock_mcp):
        """Test initialization of CloudWatchHandler."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Verify that the handler has the correct attributes
        assert handler.mcp == mock_mcp
        assert handler.allow_sensitive_data_access is False

        # Verify that both tools are registered
        assert mock_mcp.tool.call_count == 2

        # Get all call args
        call_args_list = mock_mcp.tool.call_args_list

        # Verify that get_cloudwatch_logs was registered
        assert call_args_list[0][1]['name'] == 'get_cloudwatch_logs'

        # Verify that get_cloudwatch_metrics was registered
        assert call_args_list[1][1]['name'] == 'get_cloudwatch_metrics'

    def test_resolve_time_range_defaults(self):
        """Test resolve_time_range with default values."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(MagicMock())

        # Mock datetime.now to return a fixed time
        fixed_now = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            # Test with default values
            start_dt, end_dt = handler.resolve_time_range()

            # Verify end_dt is now
            assert end_dt == fixed_now

            # Verify start_dt is 15 minutes before now
            assert start_dt == fixed_now - datetime.timedelta(minutes=15)

    def test_resolve_time_range_custom_minutes(self):
        """Test resolve_time_range with custom minutes."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(MagicMock())

        # Mock datetime.now to return a fixed time
        fixed_now = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            # Test with custom minutes
            start_dt, end_dt = handler.resolve_time_range(minutes=30)

            # Verify end_dt is now
            assert end_dt == fixed_now

            # Verify start_dt is 30 minutes before now
            assert start_dt == fixed_now - datetime.timedelta(minutes=30)

    def test_resolve_time_range_string_times(self):
        """Test resolve_time_range with string times."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(MagicMock())

        # Test with string times
        start_time = '2025-01-01T10:00:00'
        end_time = '2025-01-01T11:00:00'

        start_dt, end_dt = handler.resolve_time_range(start_time, end_time)

        # Verify times are parsed correctly
        assert start_dt == datetime.datetime(2025, 1, 1, 10, 0, 0)
        assert end_dt == datetime.datetime(2025, 1, 1, 11, 0, 0)

    def test_resolve_time_range_datetime_objects(self):
        """Test resolve_time_range with datetime objects."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(MagicMock())

        # Test with datetime objects
        start_time = datetime.datetime(2025, 1, 1, 10, 0, 0)
        end_time = datetime.datetime(2025, 1, 1, 11, 0, 0)

        start_dt, end_dt = handler.resolve_time_range(start_time, end_time)

        # Verify times are passed through correctly
        assert start_dt == start_time
        assert end_dt == end_time

    def test_resolve_time_range_mixed_types(self):
        """Test resolve_time_range with mixed types."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(MagicMock())

        # Test with mixed types
        start_time = '2025-01-01T10:00:00'
        end_time = datetime.datetime(2025, 1, 1, 11, 0, 0)

        start_dt, end_dt = handler.resolve_time_range(start_time, end_time)

        # Verify times are handled correctly
        assert start_dt == datetime.datetime(2025, 1, 1, 10, 0, 0)
        assert end_dt == end_time

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_success(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with successful retrieval."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock the AWS client
        mock_logs_client = MagicMock()
        mock_logs_client.start_query.return_value = {'queryId': 'test-query-id'}
        mock_logs_client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2025-01-01 12:00:00.000'},
                    {'field': '@message', 'value': 'Test log message 1 for test-pod'},
                    {'field': 'kubernetes.pod_name', 'value': 'test-pod'},
                ],
                [
                    {'field': '@timestamp', 'value': '2025-01-01 12:01:00.000'},
                    {'field': '@message', 'value': 'Test log message 2 for test-pod'},
                    {'field': 'kubernetes.pod_name', 'value': 'test-pod'},
                ],
            ],
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_logs_client,
            ) as mock_create_client:
                # Call the get_cloudwatch_logs method
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    log_type='application',
                    limit=100,
                )

                # Verify that AwsHelper.create_boto3_client was called with the correct service name
                # Check that create_boto3_client was called with 'logs'
                assert mock_create_client.call_count == 1
                args, kwargs = mock_create_client.call_args
                assert args[0] == 'logs'

                # Verify that start_query was called with the correct parameters
                mock_logs_client.start_query.assert_called_once()
                args, kwargs = mock_logs_client.start_query.call_args
                assert kwargs['logGroupName'] == '/aws/containerinsights/test-cluster/application'
                assert kwargs['startTime'] == int(start_dt.timestamp())
                assert kwargs['endTime'] == int(end_dt.timestamp())
                assert "@message like 'test-pod'" in kwargs['queryString']
                assert 'limit 100' in kwargs['queryString']

                # Verify that get_query_results was called with the correct query ID
                mock_logs_client.get_query_results.assert_called_with(queryId='test-query-id')

                # Verify the result
                assert not result.isError
                assert isinstance(result.content[0], TextContent)
                assert 'Successfully retrieved' in result.content[0].text
                assert result.resource_type == 'pod'
                assert result.resource_name == 'test-pod'
                assert result.cluster_name == 'test-cluster'
                assert result.log_type == 'application'
                assert result.log_group == '/aws/containerinsights/test-cluster/application'
                assert len(result.log_entries) == 2
                assert result.log_entries[0]['timestamp'] == '2025-01-01 12:00:00.000'
                assert result.log_entries[0]['message'] == 'Test log message 1 for test-pod'
                assert result.log_entries[1]['timestamp'] == '2025-01-01 12:01:00.000'
                assert result.log_entries[1]['message'] == 'Test log message 2 for test-pod'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_with_custom_parameters(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with custom filter parameters."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock the AWS client
        mock_logs_client = MagicMock()
        mock_logs_client.start_query.return_value = {'queryId': 'test-query-id'}
        mock_logs_client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2025-01-01 12:00:00.000'},
                    {'field': '@message', 'value': 'ERROR: Test log message 1 for test-pod'},
                    {'field': 'level', 'value': 'ERROR'},
                ],
            ],
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_logs_client,
            ):
                # Call the get_cloudwatch_logs method with custom parameters
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    log_type='application',
                    filter_pattern="filter level = 'ERROR'",
                    fields='@timestamp, @message, level',
                    limit=50,
                )

                # Verify that start_query was called with the correct parameters
                mock_logs_client.start_query.assert_called_once()
                args, kwargs = mock_logs_client.start_query.call_args
                assert kwargs['logGroupName'] == '/aws/containerinsights/test-cluster/application'
                assert "@message like 'test-pod'" in kwargs['queryString']
                assert "filter level = 'ERROR'" in kwargs['queryString']
                assert '@timestamp, @message, level' in kwargs['queryString']
                assert 'limit 50' in kwargs['queryString']

                # Verify the result
                assert not result.isError
                assert len(result.log_entries) == 1
                assert result.log_entries[0]['timestamp'] == '2025-01-01 12:00:00.000'
                assert result.log_entries[0]['message'] == 'ERROR: Test log message 1 for test-pod'
                assert result.log_entries[0]['level'] == 'ERROR'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_control_plane(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with control-plane log type."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock the AWS client
        mock_logs_client = MagicMock()
        mock_logs_client.start_query.return_value = {'queryId': 'test-query-id'}
        mock_logs_client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [],
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_logs_client,
            ):
                # Call the get_cloudwatch_logs method with control-plane log type
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='pod',
                    resource_name='kube-apiserver',
                    cluster_name='test-cluster',
                    log_type='control-plane',
                )

                # Verify that start_query was called with the correct log group
                mock_logs_client.start_query.assert_called_once()
                args, kwargs = mock_logs_client.start_query.call_args
                assert kwargs['logGroupName'] == '/aws/eks/test-cluster/cluster'

                # Verify the result
                assert not result.isError
                assert result.log_type == 'control-plane'
                assert result.log_group == '/aws/eks/test-cluster/cluster'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_custom_log_group(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with custom log group."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock the AWS client
        mock_logs_client = MagicMock()
        mock_logs_client.start_query.return_value = {'queryId': 'test-query-id'}
        mock_logs_client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [],
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_logs_client,
            ):
                # Call the get_cloudwatch_logs method with custom log group
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='container',
                    resource_name='my-sidecar',
                    cluster_name='test-cluster',
                    log_type='/custom/log/group',
                )

                # Verify that start_query was called with the correct log group
                mock_logs_client.start_query.assert_called_once()
                args, kwargs = mock_logs_client.start_query.call_args
                assert kwargs['logGroupName'] == '/custom/log/group'

                # Verify the result
                assert not result.isError
                assert result.log_type == '/custom/log/group'
                assert result.log_group == '/custom/log/group'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_sensitive_data_access_disabled(
        self, mock_context, mock_mcp
    ):
        """Test get_cloudwatch_logs with sensitive data access disabled."""
        # Initialize the CloudWatch handler with sensitive data access disabled
        handler = CloudWatchHandler(mock_mcp, allow_sensitive_data_access=False)

        # Call the get_cloudwatch_logs method
        result = await handler.get_cloudwatch_logs(
            mock_context,
            resource_type='pod',
            resource_name='test-pod',
            cluster_name='test-cluster',
            log_type='application',
        )

        # Verify the result
        assert result.isError
        assert isinstance(result.content[0], TextContent)
        assert (
            'Access to CloudWatch logs requires --allow-sensitive-data-access flag'
            in result.content[0].text
        )
        assert result.resource_type == 'pod'
        assert result.resource_name == 'test-pod'
        assert result.cluster_name == 'test-cluster'
        assert len(result.log_entries) == 0

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_error(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with an error."""
        # Initialize the CloudWatch handler with sensitive data access enabled
        handler = CloudWatchHandler(mock_mcp, allow_sensitive_data_access=True)

        # Mock the AWS client to raise an exception
        mock_logs_client = MagicMock()
        mock_logs_client.start_query.side_effect = Exception('Test error')

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_logs_client,
            ):
                # Call the get_cloudwatch_logs method
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    log_type='application',
                )

                # Verify the result
                assert result.isError
                assert isinstance(result.content[0], TextContent)
                assert 'Failed to get logs' in result.content[0].text
                assert 'Test error' in result.content[0].text
                assert result.resource_type == 'pod'
                assert result.resource_name == 'test-pod'
                assert result.cluster_name == 'test-cluster'
                assert len(result.log_entries) == 0

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_success(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with successful retrieval."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'cpu_usage_total',
                    'Timestamps': [
                        datetime.datetime(2025, 1, 1, 11, 58, 0),
                        datetime.datetime(2025, 1, 1, 11, 59, 0),
                        datetime.datetime(2025, 1, 1, 12, 0, 0),
                    ],
                    'Values': [10.5, 11.2, 9.8],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ) as mock_create_client:
                # Call the get_cloudwatch_metrics method
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    metric_name='cpu_usage_total',
                    namespace='ContainerInsights',
                    k8s_namespace='default',
                    limit=100,
                )

                # Verify that AwsHelper.create_boto3_client was called with the correct service name
                # Check that create_boto3_client was called with 'cloudwatch'
                assert mock_create_client.call_count == 1
                args, kwargs = mock_create_client.call_args
                assert args[0] == 'cloudwatch'

                # Verify that get_metric_data was called with the correct parameters
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                assert kwargs['StartTime'] == start_dt
                assert kwargs['EndTime'] == end_dt
                assert kwargs['MaxDatapoints'] == 100
                assert len(kwargs['MetricDataQueries']) == 1
                assert kwargs['MetricDataQueries'][0]['Id'] == 'm1'
                assert (
                    kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Namespace']
                    == 'ContainerInsights'
                )
                assert (
                    kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['MetricName']
                    == 'cpu_usage_total'
                )

                # Check dimensions are present
                dimensions = kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Dimensions']
                cluster_name_dim = {'Name': 'ClusterName', 'Value': 'test-cluster'}
                pod_name_dim = {'Name': 'PodName', 'Value': 'test-pod'}
                namespace_dim = {'Name': 'Namespace', 'Value': 'default'}
                assert cluster_name_dim in dimensions
                assert pod_name_dim in dimensions
                assert namespace_dim in dimensions

                assert kwargs['MetricDataQueries'][0]['MetricStat']['Period'] == 60
                assert kwargs['MetricDataQueries'][0]['MetricStat']['Stat'] == 'Average'

                # Verify the result
                assert not result.isError
                assert isinstance(result.content[0], TextContent)
                assert 'Successfully retrieved' in result.content[0].text
                assert result.resource_type == 'pod'
                assert result.resource_name == 'test-pod'
                assert result.cluster_name == 'test-cluster'
                assert result.metric_name == 'cpu_usage_total'
                assert result.namespace == 'ContainerInsights'
                assert len(result.data_points) == 3
                assert result.data_points[0]['timestamp'] == '2025-01-01T11:58:00'
                assert result.data_points[0]['value'] == 10.5
                assert result.data_points[1]['timestamp'] == '2025-01-01T11:59:00'
                assert result.data_points[1]['value'] == 11.2
                assert result.data_points[2]['timestamp'] == '2025-01-01T12:00:00'
                assert result.data_points[2]['value'] == 9.8

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_with_custom_parameters(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with custom parameters."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'memory_utilization',
                    'Timestamps': [
                        datetime.datetime(2025, 1, 1, 11, 58, 0),
                    ],
                    'Values': [75.5],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method with custom parameters
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    metric_name='memory_utilization',
                    namespace='ContainerInsights',
                    k8s_namespace='default',
                    period=300,
                    stat='Maximum',
                    custom_dimensions={
                        'ClusterName': 'test-cluster',
                        'Namespace': 'default',
                        'PodName': 'test-pod',
                    },
                    limit=50,
                )

                # Verify that get_metric_data was called with the correct parameters
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                assert kwargs['MaxDatapoints'] == 50
                assert kwargs['MetricDataQueries'][0]['MetricStat']['Period'] == 300
                assert kwargs['MetricDataQueries'][0]['MetricStat']['Stat'] == 'Maximum'

                # Verify custom dimensions
                dimensions = kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Dimensions']
                cluster_name_dim = {'Name': 'ClusterName', 'Value': 'test-cluster'}
                namespace_dim = {'Name': 'Namespace', 'Value': 'default'}
                pod_name_dim = {'Name': 'PodName', 'Value': 'test-pod'}
                assert cluster_name_dim in dimensions
                assert namespace_dim in dimensions
                assert pod_name_dim in dimensions

                # Verify the result
                assert not result.isError
                assert result.metric_name == 'memory_utilization'
                assert len(result.data_points) == 1
                assert result.data_points[0]['timestamp'] == '2025-01-01T11:58:00'
                assert result.data_points[0]['value'] == 75.5

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_node(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with node resource type."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'memory_utilization',
                    'Timestamps': [],
                    'Values': [],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method with node resource type
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='node',
                    resource_name='ip-10-2-3-45',
                    cluster_name='test-cluster',
                    metric_name='memory_utilization',
                    namespace='ContainerInsights',
                    k8s_namespace='kube-system',
                )

                # Verify that get_metric_data was called with the correct dimensions
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                dimensions = kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Dimensions']
                cluster_name_dim = {'Name': 'ClusterName', 'Value': 'test-cluster'}
                node_name_dim = {'Name': 'NodeName', 'Value': 'ip-10-2-3-45'}
                namespace_dim = {'Name': 'Namespace', 'Value': 'kube-system'}
                assert cluster_name_dim in dimensions
                assert node_name_dim in dimensions
                assert namespace_dim in dimensions

                # Verify the result
                assert not result.isError
                assert result.resource_type == 'node'
                assert result.resource_name == 'ip-10-2-3-45'
                assert result.metric_name == 'memory_utilization'
                assert len(result.data_points) == 0

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_container(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with container resource type."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'container_cpu_utilization',
                    'Timestamps': [],
                    'Values': [],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method with container resource type
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='container',
                    resource_name='my-sidecar',
                    cluster_name='test-cluster',
                    metric_name='container_cpu_utilization',
                    namespace='ContainerInsights',
                    k8s_namespace='default',
                )

                # Verify that get_metric_data was called with the correct dimensions
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                dimensions = kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Dimensions']
                cluster_name_dim = {'Name': 'ClusterName', 'Value': 'test-cluster'}
                container_name_dim = {'Name': 'ContainerName', 'Value': 'my-sidecar'}
                namespace_dim = {'Name': 'Namespace', 'Value': 'default'}
                assert cluster_name_dim in dimensions
                assert container_name_dim in dimensions
                assert namespace_dim in dimensions

                # Verify the result
                assert not result.isError
                assert result.resource_type == 'container'
                assert result.resource_name == 'my-sidecar'
                assert result.metric_name == 'container_cpu_utilization'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_cluster(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with cluster resource type."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'node_cpu_utilization',
                    'Timestamps': [],
                    'Values': [],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method with cluster resource type
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='cluster',
                    resource_name='test-cluster',
                    cluster_name='test-cluster',
                    metric_name='node_cpu_utilization',
                    namespace='ContainerInsights',
                    k8s_namespace='default',
                )

                # Verify that get_metric_data was called with the correct dimensions
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                dimensions = kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Dimensions']
                cluster_name_dim = {'Name': 'ClusterName', 'Value': 'test-cluster'}
                namespace_dim = {'Name': 'Namespace', 'Value': 'default'}
                assert cluster_name_dim in dimensions
                assert namespace_dim in dimensions
                assert len(dimensions) == 2  # ClusterName and Namespace dimensions

                # Verify the result
                assert not result.isError
                assert result.resource_type == 'cluster'
                assert result.resource_name == 'test-cluster'
                assert result.metric_name == 'node_cpu_utilization'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_custom_namespace(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with custom namespace."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'custom_metric',
                    'Timestamps': [],
                    'Values': [],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method with custom namespace
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    metric_name='custom_metric',
                    namespace='CustomNamespace',
                    k8s_namespace='default',
                )

                # Verify that get_metric_data was called with the correct namespace
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                assert (
                    kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Namespace']
                    == 'CustomNamespace'
                )

                # Verify the result
                assert not result.isError
                assert result.namespace == 'CustomNamespace'
                assert result.metric_name == 'custom_metric'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_custom_k8s_namespace(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with custom Kubernetes namespace."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'pod_cpu_utilization',
                    'Timestamps': [
                        datetime.datetime(2025, 1, 1, 12, 0, 0),
                    ],
                    'Values': [15.5],
                    'StatusCode': 'Complete',
                }
            ]
        }

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method with custom k8s_namespace
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    metric_name='pod_cpu_utilization',
                    namespace='ContainerInsights',
                    k8s_namespace='custom-namespace',
                )

                # Verify that get_metric_data was called with the correct dimensions
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                dimensions = kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Dimensions']
                namespace_dim = {'Name': 'Namespace', 'Value': 'custom-namespace'}
                assert namespace_dim in dimensions

                # Verify the result
                assert not result.isError
                assert len(result.data_points) == 1
                assert result.data_points[0]['value'] == 15.5

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_error(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with an error."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client to raise an exception
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.side_effect = Exception('Test error')

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    metric_name='cpu_usage_total',
                    namespace='ContainerInsights',
                    k8s_namespace='default',
                )

                # Verify the result
                assert result.isError
                assert isinstance(result.content[0], TextContent)
                assert 'Failed to get metrics' in result.content[0].text
                assert 'Test error' in result.content[0].text
                assert result.resource_type == 'pod'
                assert result.resource_name == 'test-pod'
                assert result.cluster_name == 'test-cluster'
                assert result.metric_name == 'cpu_usage_total'
                assert len(result.data_points) == 0
