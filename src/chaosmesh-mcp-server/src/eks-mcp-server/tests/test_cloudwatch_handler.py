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
    async def test_get_cloudwatch_logs_cluster_resource_type(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with cluster resource type."""
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
                    {'field': '@message', 'value': 'Test cluster log message'},
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
                # Call the get_cloudwatch_logs method with cluster resource type
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='cluster',
                    cluster_name='test-cluster',
                    log_type='control-plane',
                    resource_name='test-cluster',
                )

                # Verify that start_query was called with the correct parameters
                mock_logs_client.start_query.assert_called_once()
                args, kwargs = mock_logs_client.start_query.call_args
                assert kwargs['logGroupName'] == '/aws/eks/test-cluster/cluster'

                # Verify that the query does NOT include a filter for resource_name
                # This is the key test for our change
                assert "@message like 'test-cluster'" not in kwargs['queryString']

                # Verify the result
                assert not result.isError
                assert result.resource_type == 'cluster'
                assert result.resource_name == 'test-cluster'
                assert result.log_type == 'control-plane'
                assert len(result.log_entries) == 1
                assert result.log_entries[0]['message'] == 'Test cluster log message'

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
    async def test_get_cloudwatch_logs_without_resource_name(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs without providing resource_name."""
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
                    {
                        'field': '@message',
                        'value': 'Test log message without resource name filter',
                    },
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
                # Call the get_cloudwatch_logs method without resource_name
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='pod',
                    cluster_name='test-cluster',
                    log_type='application',
                    resource_name=None,
                )

                # Verify that start_query was called with the correct parameters
                mock_logs_client.start_query.assert_called_once()
                args, kwargs = mock_logs_client.start_query.call_args
                assert kwargs['logGroupName'] == '/aws/containerinsights/test-cluster/application'

                # Verify that the query does NOT include a filter for resource_name
                assert '@message like' not in kwargs['queryString']

                # Verify the result
                assert not result.isError
                assert result.resource_type == 'pod'
                assert result.resource_name is None
                assert result.cluster_name == 'test-cluster'
                assert result.log_type == 'application'
                assert len(result.log_entries) == 1
                assert (
                    result.log_entries[0]['message']
                    == 'Test log message without resource name filter'
                )

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
                    cluster_name='test-cluster',
                    metric_name='cpu_usage_total',
                    namespace='ContainerInsights',
                    dimensions={
                        'ClusterName': 'test-cluster',
                        'PodName': 'test-pod',
                        'Namespace': 'default',
                    },
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
                assert result.metric_name == 'cpu_usage_total'
                assert result.namespace == 'ContainerInsights'
                assert result.cluster_name == 'test-cluster'
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
                    cluster_name='test-cluster',
                    metric_name='memory_utilization',
                    namespace='ContainerInsights',
                    dimensions={
                        'ClusterName': 'test-cluster',
                        'Namespace': 'default',
                        'PodName': 'test-pod',
                    },
                    period=300,
                    stat='Maximum',
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
                assert result.cluster_name == 'test-cluster'
                assert len(result.data_points) == 1
                assert result.data_points[0]['timestamp'] == '2025-01-01T11:58:00'
                assert result.data_points[0]['value'] == 75.5

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_cluster_name_mismatch(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with ClusterName dimension not matching cluster_name parameter."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()

        # Mock the resolve_time_range method
        start_dt = datetime.datetime(2025, 1, 1, 11, 45, 0)
        end_dt = datetime.datetime(2025, 1, 1, 12, 0, 0)
        with patch.object(handler, 'resolve_time_range', return_value=(start_dt, end_dt)):
            # Mock the AwsHelper.create_boto3_client method
            with patch(
                'awslabs.eks_mcp_server.cloudwatch_handler.AwsHelper.create_boto3_client',
                return_value=mock_cloudwatch_client,
            ):
                # Call the get_cloudwatch_metrics method with mismatched cluster names
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    cluster_name='test-cluster',
                    metric_name='cpu_usage_total',
                    namespace='ContainerInsights',
                    dimensions={
                        'ClusterName': 'different-cluster',  # This doesn't match the cluster_name parameter
                        'PodName': 'test-pod',
                        'Namespace': 'default',
                    },
                )

                # Verify that get_metric_data was NOT called since validation should fail
                mock_cloudwatch_client.get_metric_data.assert_not_called()

                # Verify the error result
                assert result.isError
                assert isinstance(result.content[0], TextContent)
                assert 'does not match ClusterName dimension' in result.content[0].text
                assert 'test-cluster' in result.content[0].text
                assert 'different-cluster' in result.content[0].text
                assert result.metric_name == 'cpu_usage_total'
                assert result.namespace == 'ContainerInsights'
                assert result.cluster_name == 'test-cluster'
                assert len(result.data_points) == 0

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_empty_results(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with empty results."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the AWS client with empty results
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'cpu_usage_total',
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
                # Call the get_cloudwatch_metrics method
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    cluster_name='test-cluster',
                    metric_name='cpu_usage_total',
                    namespace='ContainerInsights',
                    dimensions={'ClusterName': 'test-cluster'},
                )

                # Verify the result
                assert not result.isError
                assert isinstance(result.content[0], TextContent)
                assert 'Successfully retrieved 0 metric data points' in result.content[0].text
                assert result.metric_name == 'cpu_usage_total'
                assert result.namespace == 'ContainerInsights'
                assert result.cluster_name == 'test-cluster'
                assert len(result.data_points) == 0

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
                    cluster_name='test-cluster',
                    metric_name='cpu_usage_total',
                    namespace='ContainerInsights',
                    dimensions={'ClusterName': 'test-cluster'},
                )

                # Verify the result
                assert result.isError
                assert isinstance(result.content[0], TextContent)
                assert 'Failed to get metrics' in result.content[0].text
                assert 'Test error' in result.content[0].text
                assert result.metric_name == 'cpu_usage_total'
                assert result.namespace == 'ContainerInsights'
                assert result.cluster_name == 'test-cluster'
                assert len(result.data_points) == 0

    @pytest.mark.asyncio
    async def test_get_cloudwatch_metrics_with_field_objects(self, mock_context, mock_mcp):
        """Test get_cloudwatch_metrics with Field objects as parameters."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Create Field objects for period and stat
        period_field = MagicMock()
        period_field.default = 120
        stat_field = MagicMock()
        stat_field.default = 'Sum'

        # Mock the AWS client
        mock_cloudwatch_client = MagicMock()
        mock_cloudwatch_client.get_metric_data.return_value = {
            'MetricDataResults': [
                {
                    'Id': 'm1',
                    'Label': 'network_rx_bytes',
                    'Timestamps': [datetime.datetime(2025, 1, 1, 12, 0, 0)],
                    'Values': [1024],
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
                # Call the get_cloudwatch_metrics method with Field objects
                result = await handler.get_cloudwatch_metrics(
                    mock_context,
                    cluster_name='test-cluster',
                    metric_name='network_rx_bytes',
                    namespace='ContainerInsights',
                    dimensions={'ClusterName': 'test-cluster'},
                    period=period_field,
                    stat=stat_field,
                )

                # Verify that get_metric_data was called with the correct parameters
                mock_cloudwatch_client.get_metric_data.assert_called_once()
                args, kwargs = mock_cloudwatch_client.get_metric_data.call_args
                assert kwargs['MetricDataQueries'][0]['MetricStat']['Period'] == 120
                assert kwargs['MetricDataQueries'][0]['MetricStat']['Stat'] == 'Sum'

                # Verify the result
                assert not result.isError
                assert result.metric_name == 'network_rx_bytes'
                assert result.cluster_name == 'test-cluster'
                assert len(result.data_points) == 1
                assert result.data_points[0]['value'] == 1024

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_with_json_message(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with JSON message."""
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
                    {
                        'field': '@message',
                        'value': '{"level":"info","message":"Pod started","pod":"test-pod","namespace":"default"}',
                    },
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
                # Call the get_cloudwatch_logs method
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    log_type='application',
                )

                # Verify the result
                assert not result.isError
                assert len(result.log_entries) == 1
                assert result.log_entries[0]['timestamp'] == '2025-01-01 12:00:00.000'
                assert isinstance(result.log_entries[0]['message'], dict)
                assert result.log_entries[0]['message']['level'] == 'info'
                assert result.log_entries[0]['message']['message'] == 'Pod started'
                assert result.log_entries[0]['message']['pod'] == 'test-pod'
                assert result.log_entries[0]['message']['namespace'] == 'default'

    @pytest.mark.asyncio
    async def test_get_cloudwatch_logs_with_nested_json_message(self, mock_context, mock_mcp):
        """Test get_cloudwatch_logs with nested JSON message."""
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
                    {
                        'field': '@message',
                        'value': '{"level":"info","message":"Pod event","details":{"pod":"test-pod","status":{"phase":"Running","conditions":[{"type":"Ready","status":"True"}]}}}',
                    },
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
                # Call the get_cloudwatch_logs method
                result = await handler.get_cloudwatch_logs(
                    mock_context,
                    resource_type='pod',
                    resource_name='test-pod',
                    cluster_name='test-cluster',
                    log_type='application',
                )

                # Verify the result
                assert not result.isError
                assert len(result.log_entries) == 1
                assert result.log_entries[0]['timestamp'] == '2025-01-01 12:00:00.000'
                assert isinstance(result.log_entries[0]['message'], dict)
                assert result.log_entries[0]['message']['level'] == 'info'
                assert result.log_entries[0]['message']['message'] == 'Pod event'
                assert isinstance(result.log_entries[0]['message']['details'], dict)
                assert result.log_entries[0]['message']['details']['pod'] == 'test-pod'
                assert isinstance(result.log_entries[0]['message']['details']['status'], dict)
                assert result.log_entries[0]['message']['details']['status']['phase'] == 'Running'
                assert isinstance(
                    result.log_entries[0]['message']['details']['status']['conditions'], list
                )
                assert (
                    result.log_entries[0]['message']['details']['status']['conditions'][0]['type']
                    == 'Ready'
                )
                assert (
                    result.log_entries[0]['message']['details']['status']['conditions'][0][
                        'status'
                    ]
                    == 'True'
                )

    def test_build_log_entry(self, mock_mcp):
        """Test _build_log_entry method."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Test with simple log entry
        result = [
            {'field': '@timestamp', 'value': '2025-01-01 12:00:00.000'},
            {'field': '@message', 'value': 'Simple log message'},
            {'field': 'level', 'value': 'INFO'},
        ]

        entry = handler._build_log_entry(result)
        assert entry['timestamp'] == '2025-01-01 12:00:00.000'
        assert entry['message'] == 'Simple log message'
        assert entry['level'] == 'INFO'

        # Test with JSON log message
        result = [
            {'field': '@timestamp', 'value': '2025-01-01 12:00:00.000'},
            {
                'field': '@message',
                'value': '{"level":"error","message":"Error occurred","code":500}',
            },
        ]

        entry = handler._build_log_entry(result)
        assert entry['timestamp'] == '2025-01-01 12:00:00.000'
        assert isinstance(entry['message'], dict)
        assert entry['message']['level'] == 'error'
        assert entry['message']['message'] == 'Error occurred'
        assert entry['message']['code'] == 500

        # Test with invalid JSON log message
        result = [
            {'field': '@timestamp', 'value': '2025-01-01 12:00:00.000'},
            {'field': '@message', 'value': '{invalid json}'},
        ]

        entry = handler._build_log_entry(result)
        assert entry['timestamp'] == '2025-01-01 12:00:00.000'
        assert entry['message'] == '{invalid json}'

    def test_format_nested_json(self, mock_mcp):
        """Test _format_nested_json method."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Test with dictionary
        obj = {'key1': 'value1', 'key2': {'nested_key': 'nested_value'}}
        result = dict(handler._format_nested_json(obj))
        assert result['key1'] == 'value1'
        assert isinstance(result['key2'], dict)
        assert result['key2']['nested_key'] == 'nested_value'

        # Test with list
        obj = [1, 2, {'key': 'value'}]
        result = handler._format_nested_json(obj)
        assert result[0] == 1
        assert result[1] == 2
        assert isinstance(result[2], dict)
        assert result[2]['key'] == 'value'

        # Test with nested JSON string
        obj = {'key': '{"nested_key": "nested_value"}'}
        result = dict(handler._format_nested_json(obj))
        assert isinstance(result['key'], dict)
        assert result['key']['nested_key'] == 'nested_value'

        # Test with invalid JSON string
        obj = {'key': '{invalid json}'}
        result = dict(handler._format_nested_json(obj))
        assert result['key'] == '{invalid json}'

    def test_poll_query_results_complete(self, mock_context, mock_mcp):
        """Test _poll_query_results with Complete status."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the logs client
        mock_logs_client = MagicMock()
        mock_logs_client.get_query_results.return_value = {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2025-01-01 12:00:00.000'},
                    {'field': '@message', 'value': 'Test log message'},
                ]
            ],
        }

        # Call the _poll_query_results method
        result = handler._poll_query_results(
            mock_context, mock_logs_client, 'test-query-id', 'pod', 'test-pod'
        )

        # Verify that get_query_results was called with the correct query ID
        mock_logs_client.get_query_results.assert_called_with(queryId='test-query-id')

        # Verify the result
        assert result['status'] == 'Complete'
        assert len(result['results']) == 1
        assert result['results'][0][0]['field'] == '@timestamp'
        assert result['results'][0][0]['value'] == '2025-01-01 12:00:00.000'
        assert result['results'][0][1]['field'] == '@message'
        assert result['results'][0][1]['value'] == 'Test log message'

    def test_poll_query_results_failed(self, mock_context, mock_mcp):
        """Test _poll_query_results with Failed status."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the logs client
        mock_logs_client = MagicMock()
        mock_logs_client.get_query_results.return_value = {
            'status': 'Failed',
        }

        # Call the _poll_query_results method and expect an exception
        with pytest.raises(Exception) as excinfo:
            handler._poll_query_results(
                mock_context, mock_logs_client, 'test-query-id', 'pod', 'test-pod'
            )

        # Verify the exception message
        assert 'CloudWatch Logs query failed for pod test-pod' in str(excinfo.value)

    def test_poll_query_results_cancelled(self, mock_context, mock_mcp):
        """Test _poll_query_results with Cancelled status."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the logs client
        mock_logs_client = MagicMock()
        mock_logs_client.get_query_results.return_value = {
            'status': 'Cancelled',
        }

        # Call the _poll_query_results method and expect an exception
        with pytest.raises(Exception) as excinfo:
            handler._poll_query_results(
                mock_context, mock_logs_client, 'test-query-id', 'pod', 'test-pod'
            )

        # Verify the exception message
        assert 'CloudWatch Logs query was cancelled for pod test-pod' in str(excinfo.value)

    def test_poll_query_results_timeout(self, mock_context, mock_mcp):
        """Test _poll_query_results with timeout."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the logs client
        mock_logs_client = MagicMock()
        mock_logs_client.get_query_results.return_value = {
            'status': 'Running',
        }

        # Call the _poll_query_results method with a small max_attempts value and expect a timeout
        with pytest.raises(TimeoutError) as excinfo:
            handler._poll_query_results(
                mock_context, mock_logs_client, 'test-query-id', 'pod', 'test-pod', max_attempts=2
            )

        # Verify the exception message
        assert 'CloudWatch Logs query timed out after 2 attempts for pod test-pod' in str(
            excinfo.value
        )

    def test_poll_query_results_exponential_backoff(self, mock_context, mock_mcp):
        """Test _poll_query_results with exponential backoff."""
        # Initialize the CloudWatch handler
        handler = CloudWatchHandler(mock_mcp)

        # Mock the logs client
        mock_logs_client = MagicMock()

        # First call returns Running, second call returns Complete
        mock_logs_client.get_query_results.side_effect = [
            {'status': 'Running'},
            {'status': 'Complete', 'results': []},
        ]

        # Mock time.sleep to track calls
        with patch('time.sleep') as mock_sleep:
            # Call the _poll_query_results method
            handler._poll_query_results(
                mock_context, mock_logs_client, 'test-query-id', 'pod', 'test-pod', initial_delay=1
            )

            # Verify that time.sleep was called with the correct delay
            mock_sleep.assert_called_once_with(1)  # Initial delay

        # Verify that get_query_results was called twice
        assert mock_logs_client.get_query_results.call_count == 2
