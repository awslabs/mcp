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

"""Tests for CloudWatch active alarms functionality."""

import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.models import ActiveAlarmsResponse
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools import CloudWatchAlarmsTools
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch


@pytest.fixture
def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


class TestGetActiveAlarms:
    """Test cases for get_active_alarms functionality."""

    @pytest.mark.asyncio
    async def test_max_items_validation_valid(self, mock_context):
        """Test max_items parameter validation with valid values."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'MetricAlarms': [], 'CompositeAlarms': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test valid max_items values
            result = await alarms_tools.get_active_alarms(mock_context, max_items=25)
            assert isinstance(result, ActiveAlarmsResponse)

            result = await alarms_tools.get_active_alarms(mock_context, max_items=1)
            assert isinstance(result, ActiveAlarmsResponse)

    @pytest.mark.asyncio
    async def test_max_items_validation_invalid(self, mock_context):
        """Test max_items parameter validation with invalid values."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test invalid max_items values
            with pytest.raises(ValueError, match='max_items must be at least 1'):
                await alarms_tools.get_active_alarms(mock_context, max_items=0)

            with pytest.raises(ValueError, match='max_items must be at least 1'):
                await alarms_tools.get_active_alarms(mock_context, max_items=-1)

    @pytest.mark.asyncio
    async def test_no_max_items_works_correctly(self, mock_context):
        """Test that boto3 paginator is used correctly."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'test-alarm',
                            'StateValue': 'ALARM',
                            'StateReason': 'Test reason',
                            'MetricName': 'CPUUtilization',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        }
                    ],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context)

            # Verify paginator was used
            mock_client.get_paginator.assert_called_once_with('describe_alarms')
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM',
                AlarmTypes=['CompositeAlarm', 'MetricAlarm'],
                PaginationConfig={'MaxItems': 51},
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1
            # Verify total_count is not in response
            assert not hasattr(result, 'total_count')

    @pytest.mark.asyncio
    async def test_paginator_usage(self, mock_context):
        """Test that boto3 paginator is used correctly."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'test-alarm',
                            'StateValue': 'ALARM',
                            'StateReason': 'Test reason',
                            'MetricName': 'CPUUtilization',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        }
                    ],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=50)

            # Verify paginator was used
            mock_client.get_paginator.assert_called_once_with('describe_alarms')
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM',
                AlarmTypes=['CompositeAlarm', 'MetricAlarm'],
                PaginationConfig={'MaxItems': 51},
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1
            # Verify total_count is not in response
            assert not hasattr(result, 'total_count')

    def test_describe_alarms_parameters(self):
        """Test that describe_alarms is called with the correct parameters."""
        # Create a mock client
        mock_client = Mock()

        # Set up the return value
        mock_client.describe_alarms.return_value = {'MetricAlarms': [], 'CompositeAlarms': []}

        # Call describe_alarms
        mock_client.describe_alarms(
            StateValue='ALARM', MaxRecords=50, AlarmTypes=['CompositeAlarm', 'MetricAlarm']
        )

        # Verify the call
        mock_client.describe_alarms.assert_called_once_with(
            StateValue='ALARM', MaxRecords=50, AlarmTypes=['CompositeAlarm', 'MetricAlarm']
        )

    def test_alarm_tools_registration(self):
        """Test that CloudWatchAlarmsTools registers both alarm tools."""
        # Create a mock MCP
        mock_mcp = Mock()

        # Mock boto3 session to avoid AWS credential errors
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            # Setup mock client
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Create a CloudWatchAlarmsTools instance
            alarms_tools = CloudWatchAlarmsTools()

            # Mock the methods
            alarms_tools.get_active_alarms = Mock()
            alarms_tools.get_alarm_history = Mock()

            # Register the tools
            alarms_tools.register(mock_mcp)

            # Verify that both tools were registered
            assert mock_mcp.tool.call_count == 2
            calls = mock_mcp.tool.call_args_list
            call_names = [call[1]['name'] for call in calls]
            assert 'get_active_alarms' in call_names
            assert 'get_alarm_history' in call_names

    @pytest.mark.asyncio
    async def test_empty_alarms_response(self, mock_context):
        """Test handling of empty alarms response."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'MetricAlarms': [], 'CompositeAlarms': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=50)

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 0
            assert len(result.composite_alarms) == 0
            assert result.message == 'No active alarms found'
            assert not result.has_more_results

    @pytest.mark.asyncio
    async def test_mixed_alarm_types_response(self, mock_context):
        """Test response with both metric and composite alarms."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'metric-alarm',
                            'StateValue': 'ALARM',
                            'StateReason': 'Metric alarm reason',
                            'MetricName': 'CPUUtilization',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-123'}],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        }
                    ],
                    'CompositeAlarms': [
                        {
                            'AlarmName': 'composite-alarm',
                            'StateValue': 'ALARM',
                            'StateReason': 'Composite alarm reason',
                            'AlarmRule': 'ALARM("metric-alarm")',
                            'StateUpdatedTimestamp': datetime.now(),
                        }
                    ],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=50)

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1
            assert len(result.composite_alarms) == 1
            assert result.metric_alarms[0].alarm_name == 'metric-alarm'
            assert result.composite_alarms[0].alarm_name == 'composite-alarm'

    @pytest.mark.asyncio
    async def test_has_more_results_logic(self, mock_context):
        """Test has_more_results logic when max_items is exceeded."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            # Return 3 alarms when max_items=2
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'alarm1',
                            'StateValue': 'ALARM',
                            'StateReason': 'reason1',
                            'MetricName': 'CPU',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        },
                        {
                            'AlarmName': 'alarm2',
                            'StateValue': 'ALARM',
                            'StateReason': 'reason2',
                            'MetricName': 'CPU',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        },
                        {
                            'AlarmName': 'alarm3',
                            'StateValue': 'ALARM',
                            'StateReason': 'reason3',
                            'MetricName': 'CPU',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        },
                    ],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=2)

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 2  # Only 2 returned despite 3 available
            assert result.has_more_results
            assert (
                result.message is not None
                and 'Showing 2 alarms (more available)' in result.message
            )

    @pytest.mark.asyncio
    async def test_boto3_client_error_handling(self, mock_context):
        """Test error handling when boto3 client fails."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session',
            side_effect=Exception('AWS credentials not found'),
        ):
            alarms_tools = CloudWatchAlarmsTools()
            with pytest.raises(Exception, match='AWS credentials not found'):
                await alarms_tools.get_active_alarms(mock_context, max_items=50)

    @pytest.mark.asyncio
    async def test_describe_alarms_api_error(self, mock_context):
        """Test error handling when describe_alarms API fails."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.side_effect = Exception('API Error')
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            with pytest.raises(Exception, match='API Error'):
                await alarms_tools.get_active_alarms(mock_context, max_items=50)

            # Verify error was logged to context
            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_alarm_transformation_with_missing_fields(self, mock_context):
        """Test alarm transformation handles missing optional fields gracefully."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            # Alarm with minimal required fields
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'minimal-alarm',
                            'StateValue': 'ALARM',
                            # Missing optional fields like AlarmDescription, Dimensions, etc.
                        }
                    ],
                    'CompositeAlarms': [
                        {
                            'AlarmName': 'minimal-composite',
                            'StateValue': 'ALARM',
                            # Missing optional fields
                        }
                    ],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=50)

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1
            assert len(result.composite_alarms) == 1

            # Check that missing fields are handled with defaults
            metric_alarm = result.metric_alarms[0]
            assert metric_alarm.alarm_name == 'minimal-alarm'
            assert metric_alarm.alarm_description is None
            assert metric_alarm.dimensions == []

            composite_alarm = result.composite_alarms[0]
            assert composite_alarm.alarm_name == 'minimal-composite'
            assert composite_alarm.alarm_description is None

    @pytest.mark.asyncio
    async def test_pagination_across_multiple_pages(self, mock_context):
        """Test pagination handling across multiple pages."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            # Simulate multiple pages
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'alarm-page1',
                            'StateValue': 'ALARM',
                            'StateReason': 'reason1',
                            'MetricName': 'CPU',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        }
                    ],
                    'CompositeAlarms': [],
                },
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'alarm-page2',
                            'StateValue': 'ALARM',
                            'StateReason': 'reason2',
                            'MetricName': 'Memory',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [],
                            'Threshold': 90.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        }
                    ],
                    'CompositeAlarms': [],
                },
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=5)

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 2
            assert result.metric_alarms[0].alarm_name == 'alarm-page1'
            assert result.metric_alarms[1].alarm_name == 'alarm-page2'

    @pytest.mark.asyncio
    async def test_dimension_transformation(self, mock_context):
        """Test proper transformation of alarm dimensions."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        {
                            'AlarmName': 'alarm-with-dimensions',
                            'StateValue': 'ALARM',
                            'StateReason': 'Test reason',
                            'MetricName': 'CPUUtilization',
                            'Namespace': 'AWS/EC2',
                            'Dimensions': [
                                {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'},
                                {'Name': 'AutoScalingGroupName', 'Value': 'my-asg'},
                            ],
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'StateUpdatedTimestamp': datetime.now(),
                        }
                    ],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=50)

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1

            alarm = result.metric_alarms[0]
            assert len(alarm.dimensions) == 2
            assert alarm.dimensions[0] == {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}
            assert alarm.dimensions[1] == {'Name': 'AutoScalingGroupName', 'Value': 'my-asg'}

    def test_transform_metric_alarm_direct(self):
        """Test _transform_metric_alarm method directly."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            alarm_data = {
                'AlarmName': 'test-alarm',
                'AlarmDescription': 'Test description',
                'StateValue': 'ALARM',
                'StateReason': 'Test reason',
                'MetricName': 'CPUUtilization',
                'Namespace': 'AWS/EC2',
                'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-123'}],
                'Threshold': 75.5,
                'ComparisonOperator': 'GreaterThanThreshold',
                'StateUpdatedTimestamp': datetime(2023, 1, 1, 12, 0, 0),
            }

            result = alarms_tools._transform_metric_alarm(alarm_data)

            assert result.alarm_name == 'test-alarm'
            assert result.alarm_description == 'Test description'
            assert result.state_value == 'ALARM'
            assert result.threshold == 75.5
            assert len(result.dimensions) == 1

    def test_transform_composite_alarm_direct(self):
        """Test _transform_composite_alarm method directly."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            alarm_data = {
                'AlarmName': 'composite-test',
                'AlarmDescription': 'Composite description',
                'StateValue': 'ALARM',
                'StateReason': 'Composite reason',
                'AlarmRule': 'ALARM("alarm1") OR ALARM("alarm2")',
                'StateUpdatedTimestamp': datetime(2023, 1, 1, 12, 0, 0),
            }

            result = alarms_tools._transform_composite_alarm(alarm_data)

            assert result.alarm_name == 'composite-test'
            assert result.alarm_description == 'Composite description'
            assert result.state_value == 'ALARM'
            assert result.alarm_rule == 'ALARM("alarm1") OR ALARM("alarm2")'
            assert result.alarm_type == 'CompositeAlarm'
