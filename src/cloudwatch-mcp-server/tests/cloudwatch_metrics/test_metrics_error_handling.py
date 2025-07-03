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

"""Tests for CloudWatch Metrics error handling and edge cases."""

import json
import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.models import (
    AlarmRecommendation,
    Dimension,
    GetMetricDataResponse,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools import CloudWatchMetricsTools
from datetime import datetime
from unittest.mock import AsyncMock, Mock, mock_open, patch


@pytest_asyncio.fixture
async def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


class TestMetadataLoadingErrors:
    """Test error handling in metadata loading."""

    def test_metadata_file_not_found(self):
        """Test handling when metadata file doesn't exist - covers lines 82-83."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            with patch('pathlib.Path.exists', return_value=False):
                with patch(
                    'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.logger'
                ) as mock_logger:
                    tools = CloudWatchMetricsTools()

                    # Should handle missing file gracefully
                    assert tools.metric_metadata_index == {}
                    mock_logger.warning.assert_called()

    def test_metadata_file_read_error(self):
        """Test handling when metadata file can't be read - covers lines 101, 109-111."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', side_effect=IOError('File read error')):
                    with patch(
                        'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.logger'
                    ) as mock_logger:
                        tools = CloudWatchMetricsTools()

                        # Should handle file read error gracefully
                        assert tools.metric_metadata_index == {}
                        mock_logger.error.assert_called()

    def test_metadata_json_parse_error(self):
        """Test handling when metadata JSON is invalid - covers lines 101, 109-111."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', mock_open(read_data='invalid json')):
                    with patch(
                        'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.logger'
                    ) as mock_logger:
                        tools = CloudWatchMetricsTools()

                        # Should handle JSON parse error gracefully
                        assert tools.metric_metadata_index == {}
                        mock_logger.error.assert_called()

    def test_metadata_entry_processing_error(self):
        """Test handling when individual metadata entries are malformed - covers lines 52, 59-61, 116-118."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            with patch('pathlib.Path.exists', return_value=True):
                # Mock metadata with malformed entries
                malformed_metadata = [
                    {
                        'metricId': {'namespace': 'AWS/EC2', 'metricName': 'CPUUtilization'}
                    },  # Valid
                    {'metricId': {'namespace': 'AWS/EC2'}},  # Missing metricName
                    {'metricId': {'metricName': 'NetworkIn'}},  # Missing namespace
                    {'metricId': {}},  # Missing both
                    {},  # Missing metricId entirely
                    {
                        'metricId': {'namespace': 'AWS/S3', 'metricName': 'BucketSizeBytes'}
                    },  # Valid
                ]

                with patch('builtins.open', mock_open(read_data=json.dumps(malformed_metadata))):
                    with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.logger'):
                        tools = CloudWatchMetricsTools()

                        # Should only index valid entries (entries with both namespace and metricName)
                        # The current implementation skips invalid entries but doesn't log warnings
                        assert len(tools.metric_metadata_index) == 2  # Only 2 valid entries

                        # The current implementation doesn't log warnings for invalid entries
                        # so we don't expect any logger calls

    def test_metadata_entry_key_error(self):
        """Test handling when metadata entry access causes KeyError."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            with patch('pathlib.Path.exists', return_value=True):
                # Mock metadata that will cause KeyError when accessing
                metadata_with_error = [
                    {'metricId': {'namespace': 'AWS/EC2', 'metricName': 'CPUUtilization'}},
                ]

                with patch('builtins.open', mock_open(read_data=json.dumps(metadata_with_error))):
                    with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.logger'):
                        # Mock the json.loads to cause an exception during processing
                        with patch(
                            'json.loads',
                            side_effect=[metadata_with_error, Exception('Processing error')],
                        ):
                            tools = CloudWatchMetricsTools()

                            # Should handle entry processing error gracefully
                            # Since we're mocking the actual processing, it should work normally
                            assert isinstance(tools, CloudWatchMetricsTools)


class TestParameterValidation:
    """Test parameter validation and edge cases."""

    @pytest.mark.asyncio
    async def test_get_metric_data_group_by_dimension_not_in_schema(self, mock_context):
        """Test error when group_by_dimension is not in schema_dimension_keys."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            with pytest.raises(ValueError) as exc_info:
                await tools.get_metric_data(
                    mock_context,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    start_time='2023-01-01T00:00:00Z',
                    end_time='2023-01-01T01:00:00Z',
                    statistic='AVG',
                    schema_dimension_keys=['InstanceType'],
                    group_by_dimension='InstanceId',  # Not in schema_dimension_keys
                )

            assert (
                "group_by_dimension 'InstanceId' must be included in schema_dimension_keys"
                in str(exc_info.value)
            )

    @pytest.mark.asyncio
    async def test_get_metric_data_sort_order_without_order_by_statistic(self, mock_context):
        """Test error when sort_order is specified without order_by_statistic."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            with pytest.raises(ValueError) as exc_info:
                await tools.get_metric_data(
                    mock_context,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    start_time='2023-01-01T00:00:00Z',
                    end_time='2023-01-01T01:00:00Z',
                    statistic='AVG',
                    schema_dimension_keys=['InstanceId'],
                    group_by_dimension='InstanceId',
                    sort_order='DESC',  # Without order_by_statistic
                )

            assert 'If sort_order is specified, order_by_statistic must also be specified' in str(
                exc_info.value
            )

    def test_invalid_metrics_insights_statistic(self):
        """Test validation of invalid Metrics Insights statistic."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            with pytest.raises(ValueError) as exc_info:
                tools._validate_metrics_insights_statistic('INVALID')

            assert 'Invalid statistic for Metrics Insights: INVALID' in str(exc_info.value)

    def test_map_to_metrics_insights_statistic_invalid(self):
        """Test mapping invalid statistic for Metrics Insights."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            with pytest.raises(ValueError):
                tools._map_to_metrics_insights_statistic('INVALID_STAT')


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_get_metric_data_api_error(self, mock_context):
        """Test get_metric_data with API error - covers line 370."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_metric_data.side_effect = Exception('API Error')
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchMetricsTools()

            with pytest.raises(Exception) as exc_info:
                await tools.get_metric_data(
                    mock_context,
                    namespace='AWS/EC2',
                    metric_name='CPUUtilization',
                    start_time='2023-01-01T00:00:00Z',
                    end_time='2023-01-01T01:00:00Z',
                    statistic='AVG',
                )

            assert 'API Error' in str(exc_info.value)
            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_metric_metadata_api_error(self, mock_context):
        """Test get_metric_metadata with general error - covers lines 537, 566."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Mock _lookup_metadata to raise exception
            with patch.object(
                tools, '_lookup_metadata', side_effect=Exception('Metadata lookup error')
            ):
                with pytest.raises(Exception) as exc_info:
                    await tools.get_metric_metadata(
                        mock_context, namespace='AWS/EC2', metric_name='CPUUtilization'
                    )

                assert 'Metadata lookup error' in str(exc_info.value)
                mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommended_metric_alarms_api_error(self, mock_context):
        """Test get_recommended_metric_alarms with general error - covers lines 636-639."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Mock _lookup_metadata to raise exception
            with patch.object(
                tools, '_lookup_metadata', side_effect=Exception('Metadata lookup error')
            ):
                with pytest.raises(Exception) as exc_info:
                    await tools.get_recommended_metric_alarms(
                        mock_context,
                        namespace='AWS/EC2',
                        metric_name='CPUUtilization',
                        dimensions=[],
                    )

                assert 'Metadata lookup error' in str(exc_info.value)
                mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommended_metric_alarms_parse_error(self, mock_context):
        """Test get_recommended_metric_alarms with parse error - covers lines 715-717."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Mock metadata with malformed alarm recommendations
            malformed_metadata = {
                'alarmRecommendations': [
                    {
                        'alarmDescription': 'Valid alarm',
                        'threshold': {'staticValue': 80.0},
                        'period': 300,
                        'statistic': 'Average',
                    },
                    {
                        # Missing required fields - will cause parse error
                        'alarmDescription': 'Invalid alarm'
                    },
                ]
            }

            with patch.object(tools, '_lookup_metadata', return_value=malformed_metadata):
                # Mock the _parse_alarm_recommendation method to raise an exception
                with patch.object(
                    tools,
                    '_parse_alarm_recommendation',
                    side_effect=[Mock(), Exception('Parse error')],
                ):
                    with patch(
                        'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.logger'
                    ) as mock_logger:
                        result = await tools.get_recommended_metric_alarms(
                            mock_context,
                            namespace='AWS/EC2',
                            metric_name='CPUUtilization',
                            dimensions=[],
                        )

                        # Should return only valid recommendations and log warning for invalid ones
                        assert isinstance(result, list)
                        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_parse_alarm_recommendation_missing_fields(self, mock_context):
        """Test _parse_alarm_recommendation with missing fields - covers lines 724-727, 745, 751, 755, 757, 761."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Test with minimal alarm data
            minimal_alarm_data = {}

            result = tools._parse_alarm_recommendation(minimal_alarm_data)

            # Should handle missing fields gracefully with defaults
            assert isinstance(result, AlarmRecommendation)
            assert result.alarmDescription == ''
            assert result.threshold.staticValue == 0.0
            assert result.threshold.justification == ''
            assert result.period == 300
            assert result.comparisonOperator == ''
            assert result.statistic == ''
            assert result.evaluationPeriods == 1
            assert result.datapointsToAlarm == 1
            assert result.treatMissingData == 'missing'
            assert result.dimensions == []
            assert result.intent == ''

    def test_alarm_matches_dimensions_edge_cases(self):
        """Test _alarm_matches_dimensions edge cases."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Test with empty alarm dimensions - should match any provided dimensions
            result = tools._alarm_matches_dimensions({}, {'InstanceId': 'i-123'})
            assert result is True

            # Test with alarm dimension missing name
            alarm_data = {
                'dimensions': [
                    {'value': 'some-value'}  # Missing 'name'
                ]
            }
            result = tools._alarm_matches_dimensions(alarm_data, {'InstanceId': 'i-123'})
            assert result is True  # Should skip dimensions without name

            # Test with alarm dimension having specific value requirement not met
            alarm_data = {'dimensions': [{'name': 'InstanceType', 'value': 't2.micro'}]}
            result = tools._alarm_matches_dimensions(alarm_data, {'InstanceType': 't2.small'})
            assert result is False

            # Test with alarm dimension having no specific value requirement
            alarm_data = {
                'dimensions': [
                    {'name': 'InstanceId'}  # No 'value' specified
                ]
            }
            result = tools._alarm_matches_dimensions(alarm_data, {'InstanceId': 'i-123'})
            assert result is True

            # Test with missing required dimension
            alarm_data = {'dimensions': [{'name': 'InstanceId'}]}
            result = tools._alarm_matches_dimensions(alarm_data, {'InstanceType': 't2.micro'})
            assert result is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_boto3_client_error_handling(self):
        """Test error handling when boto3 client creation fails."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'
        ) as mock_session:
            mock_session.side_effect = Exception('AWS credentials not found')

            with pytest.raises(Exception, match='AWS credentials not found'):
                CloudWatchMetricsTools()

    def test_aws_profile_initialization(self):
        """Test initialization with AWS_PROFILE environment variable."""
        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile', 'AWS_REGION': 'us-west-2'}):
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client

                CloudWatchMetricsTools()

                # Verify session was created with profile
                mock_session.assert_called_with(
                    profile_name='test-profile', region_name='us-west-2'
                )

    def test_default_region_usage(self):
        """Test that default region is used when not specified."""
        with patch.dict('os.environ', {}, clear=True):
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client

                CloudWatchMetricsTools()

                # Should use default us-east-1
                mock_session.assert_called_with(region_name='us-east-1')

    def test_tools_registration(self):
        """Test that all tools are properly registered."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            mock_mcp = Mock()
            tools.register(mock_mcp)

            # Verify all tools are registered
            assert mock_mcp.tool.call_count == 3
            tool_calls = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
            expected_tools = [
                'get_metric_data',
                'get_metric_metadata',
                'get_recommended_metric_alarms',
            ]
            for tool in expected_tools:
                assert tool in tool_calls

    def test_process_metric_data_response_edge_cases(self):
        """Test _process_metric_data_response with edge cases."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Test with empty response
            response = {'MetricDataResults': []}
            result = tools._process_metric_data_response(response)
            assert isinstance(result, GetMetricDataResponse)
            assert result.metricDataResults == []
            assert result.messages == []

            # Test with missing optional fields
            response = {
                'MetricDataResults': [
                    {
                        'Id': 'm1',
                        # Missing Label, StatusCode, Timestamps, Values, Messages
                    }
                ]
            }
            result = tools._process_metric_data_response(response)
            assert len(result.metricDataResults) == 1
            assert result.metricDataResults[0].id == 'm1'
            assert result.metricDataResults[0].label == ''
            assert result.metricDataResults[0].statusCode == 'Complete'
            assert result.metricDataResults[0].datapoints == []
            assert result.metricDataResults[0].messages == []

    def test_build_where_clause_edge_cases(self):
        """Test _build_where_clause with edge cases."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Test with empty dimensions
            result = tools._build_where_clause([])
            assert result is None

            # Test with single dimension
            dimensions = [Dimension(name='InstanceId', value='i-123')]
            result = tools._build_where_clause(dimensions)
            assert result == 'WHERE "InstanceId"=\'i-123\''

            # Test with multiple dimensions
            dimensions = [
                Dimension(name='InstanceId', value='i-123'),
                Dimension(name='InstanceType', value='t2.micro'),
            ]
            result = tools._build_where_clause(dimensions)
            assert result == 'WHERE "InstanceId"=\'i-123\' AND "InstanceType"=\'t2.micro\''

    def test_build_schema_string_edge_cases(self):
        """Test _build_schema_string with edge cases."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Test with no dimension keys
            result = tools._build_schema_string('AWS/EC2', [])
            assert result == '"AWS/EC2"'

            # Test with single dimension key
            result = tools._build_schema_string('AWS/EC2', ['InstanceId'])
            assert result == '"AWS/EC2", "InstanceId"'

            # Test with multiple dimension keys
            result = tools._build_schema_string('AWS/EC2', ['InstanceId', 'InstanceType'])
            assert result == '"AWS/EC2", "InstanceId", "InstanceType"'

    def test_statistic_mappings(self):
        """Test statistic mapping functions."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Test CloudWatch statistic mapping
            assert tools._map_to_cloudwatch_statistic('AVG') == 'Average'
            assert tools._map_to_cloudwatch_statistic('SUM') == 'Sum'
            assert tools._map_to_cloudwatch_statistic('MAX') == 'Maximum'
            assert tools._map_to_cloudwatch_statistic('MIN') == 'Minimum'
            assert tools._map_to_cloudwatch_statistic('COUNT') == 'SampleCount'
            assert tools._map_to_cloudwatch_statistic('Average') == 'Average'  # Pass-through

            # Test Metrics Insights statistic mapping
            assert tools._map_to_metrics_insights_statistic('Average') == 'AVG'
            assert tools._map_to_metrics_insights_statistic('Sum') == 'SUM'
            assert tools._map_to_metrics_insights_statistic('Maximum') == 'MAX'
            assert tools._map_to_metrics_insights_statistic('Minimum') == 'MIN'
            assert tools._map_to_metrics_insights_statistic('SampleCount') == 'COUNT'
            assert tools._map_to_metrics_insights_statistic('AVG') == 'AVG'  # Pass-through

    def test_period_calculation_edge_cases(self):
        """Test period calculation with edge cases."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_metrics.tools.boto3.Session'):
            tools = CloudWatchMetricsTools()

            # Test with very short time window
            start_time = datetime(2023, 1, 1, 0, 0, 0)
            end_time = datetime(2023, 1, 1, 0, 1, 0)  # 1 minute

            result_start, result_end, period = tools._prepare_time_parameters(
                start_time, end_time, 60
            )

            # Should use minimum period of 60 seconds
            assert period == 60

            # Test with time window that doesn't divide evenly
            start_time = datetime(2023, 1, 1, 0, 0, 0)
            end_time = datetime(2023, 1, 1, 0, 7, 0)  # 7 minutes = 420 seconds

            result_start, result_end, period = tools._prepare_time_parameters(
                start_time,
                end_time,
                6,  # 420 / 6 = 70, should round up to 120
            )

            # Should round up to nearest multiple of 60
            assert period == 120
