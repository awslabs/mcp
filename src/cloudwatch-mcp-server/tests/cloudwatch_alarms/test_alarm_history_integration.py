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

"""Integration tests for CloudWatch alarm history functionality."""

import json
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.models import (
    AlarmHistoryResponse,
    CompositeAlarmComponentResponse,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools import CloudWatchAlarmsTools
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch


@pytest.fixture
def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def realistic_alarm_history_response():
    """Realistic CloudWatch GetAlarmHistory API response with multiple state changes."""
    base_time = datetime(2025, 6, 20, 10, 0, 0)
    return {
        'AlarmHistoryItems': [
            {
                'AlarmName': 'web-server-cpu-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': base_time,
                'HistoryItemType': 'StateUpdate',
                'HistorySummary': 'Alarm updated from OK to ALARM',
                'HistoryData': json.dumps(
                    {
                        'oldState': {
                            'stateValue': 'OK',
                            'stateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [45.2] was not greater than the threshold (80.0) (minimum 1 datapoint for OK -> ALARM transition).',
                        },
                        'newState': {
                            'stateValue': 'ALARM',
                            'stateReason': 'Threshold Crossed: 2 consecutive datapoints [85.4, 87.1] were greater than the threshold (80.0) (minimum 2 datapoints for ALARM transition).',
                        },
                    }
                ),
            },
            {
                'AlarmName': 'web-server-cpu-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': base_time - timedelta(minutes=15),
                'HistoryItemType': 'StateUpdate',
                'HistorySummary': 'Alarm updated from ALARM to OK',
                'HistoryData': json.dumps(
                    {
                        'oldState': {
                            'stateValue': 'ALARM',
                            'stateReason': 'Threshold Crossed: 2 consecutive datapoints [85.4, 87.1] were greater than the threshold (80.0).',
                        },
                        'newState': {
                            'stateValue': 'OK',
                            'stateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [45.2] was not greater than the threshold (80.0).',
                        },
                    }
                ),
            },
            {
                'AlarmName': 'web-server-cpu-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': base_time - timedelta(minutes=30),
                'HistoryItemType': 'StateUpdate',
                'HistorySummary': 'Alarm updated from OK to ALARM',
                'HistoryData': json.dumps(
                    {
                        'oldState': {
                            'stateValue': 'OK',
                            'stateReason': 'Threshold Crossed: 1 out of the last 1 datapoints [45.2] was not greater than the threshold (80.0).',
                        },
                        'newState': {
                            'stateValue': 'ALARM',
                            'stateReason': 'Threshold Crossed: 2 consecutive datapoints [82.3, 84.7] were greater than the threshold (80.0).',
                        },
                    }
                ),
            },
            {
                'AlarmName': 'web-server-cpu-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': base_time - timedelta(hours=2),
                'HistoryItemType': 'ConfigurationUpdate',
                'HistorySummary': 'Alarm threshold updated from 70.0 to 80.0',
                'HistoryData': json.dumps(
                    {
                        'updatedAlarm': {
                            'threshold': 80.0,
                            'comparisonOperator': 'GreaterThanThreshold',
                        }
                    }
                ),
            },
        ],
        'NextToken': 'next-page-token-123',
    }


@pytest.fixture
def realistic_metric_alarm():
    """Realistic metric alarm configuration."""
    return {
        'AlarmName': 'web-server-cpu-alarm',
        'AlarmDescription': 'Monitors CPU utilization for web server instances',
        'StateValue': 'ALARM',
        'StateReason': 'Threshold Crossed: 2 consecutive datapoints [85.4, 87.1] were greater than the threshold (80.0).',
        'StateUpdatedTimestamp': datetime(2025, 6, 20, 10, 0, 0),
        'MetricName': 'CPUUtilization',
        'Namespace': 'AWS/EC2',
        'Dimensions': [
            {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'},
            {'Name': 'AutoScalingGroupName', 'Value': 'web-server-asg'},
        ],
        'Threshold': 80.0,
        'ComparisonOperator': 'GreaterThanThreshold',
        'EvaluationPeriods': 2,
        'Period': 300,
        'Statistic': 'Average',
        'TreatMissingData': 'notBreaching',
        'ActionsEnabled': True,
        'AlarmActions': ['arn:aws:sns:us-east-1:123456789012:cpu-alarm-topic'],
    }


@pytest.fixture
def realistic_composite_alarm():
    """Realistic composite alarm configuration."""
    return {
        'AlarmName': 'application-health-composite',
        'AlarmDescription': 'Overall application health based on multiple metrics',
        'StateValue': 'ALARM',
        'StateReason': 'ALARM("web-server-cpu-alarm") is in ALARM',
        'StateUpdatedTimestamp': datetime(2025, 6, 20, 10, 0, 0),
        'AlarmRule': '(ALARM("web-server-cpu-alarm") OR ALARM("database-connection-alarm")) AND NOT ALARM("maintenance-mode-alarm")',
        'ActionsEnabled': True,
        'AlarmActions': ['arn:aws:sns:us-east-1:123456789012:critical-alert-topic'],
    }


class TestAlarmHistoryIntegration:
    """Integration tests for alarm history functionality."""

    @pytest.mark.asyncio
    async def test_end_to_end_metric_alarm_history(
        self, mock_context, realistic_alarm_history_response, realistic_metric_alarm
    ):
        """Test complete end-to-end alarm history retrieval for metric alarm."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup realistic API responses - simulate more items than max_items (50)
            # Create a response with 51 items to trigger has_more_results=True
            extended_response = realistic_alarm_history_response.copy()
            # Add extra items to simulate pagination
            for i in range(47):  # Add 47 more items (4 existing + 47 = 51 total)
                extended_response['AlarmHistoryItems'].append(
                    {
                        'AlarmName': 'web-server-cpu-alarm',
                        'AlarmType': 'MetricAlarm',
                        'Timestamp': datetime(2025, 6, 20, 8, 0, 0) - timedelta(minutes=i),
                        'HistoryItemType': 'StateUpdate',
                        'HistorySummary': f'Extra item {i}',
                        'HistoryData': '{}',
                    }
                )

            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [extended_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [realistic_metric_alarm],
                'CompositeAlarms': [],
            }

            alarms_tools = CloudWatchAlarmsTools()

            # Call with realistic parameters
            result = await alarms_tools.get_alarm_history(
                ctx=mock_context,
                alarm_name='web-server-cpu-alarm',
                start_time='2025-06-20T06:00:00Z',
                end_time='2025-06-20T12:00:00Z',
            )

            # Verify comprehensive response
            assert isinstance(result, AlarmHistoryResponse)
            assert result.has_more_results

            # Verify alarm details
            assert result.alarm_details.alarm_name == 'web-server-cpu-alarm'
            assert result.alarm_details.alarm_type == 'MetricAlarm'
            assert result.alarm_details.metric_name == 'CPUUtilization'
            assert result.alarm_details.namespace == 'AWS/EC2'
            assert result.alarm_details.threshold == 80.0
            assert result.alarm_details.period == 300
            assert result.alarm_details.evaluation_periods == 2

            # Verify history items parsing (limited to max_items=50)
            assert len(result.history_items) == 50

            # Check state update items (first few are the original ones)
            state_updates = [
                item for item in result.history_items if item.history_item_type == 'StateUpdate'
            ]
            assert len(state_updates) >= 3  # At least the original 3

            # Verify ALARM transitions (from original items)
            alarm_transitions = [item for item in state_updates if item.new_state == 'ALARM']
            assert len(alarm_transitions) >= 2  # At least the original 2

            # Verify time range suggestions
            assert len(result.time_range_suggestions) >= 2  # At least individual suggestions

            # Check for flapping detection (2 ALARM transitions within 30 minutes)
            flapping_suggestions = [
                s for s in result.time_range_suggestions if 'flapping' in s.reason.lower()
            ]
            assert len(flapping_suggestions) >= 1

            # Verify time range calculation
            for suggestion in result.time_range_suggestions:
                assert isinstance(suggestion.start_time, datetime)
                assert isinstance(suggestion.end_time, datetime)
                assert suggestion.start_time < suggestion.end_time
                assert len(suggestion.reason) > 0

    @pytest.mark.asyncio
    async def test_end_to_end_composite_alarm_with_components(
        self, mock_context, realistic_composite_alarm, realistic_metric_alarm
    ):
        """Test complete composite alarm handling with component expansion."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup composite alarm response
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'AlarmHistoryItems': []}]
            mock_client.get_paginator.return_value = mock_paginator

            # First call returns composite alarm, subsequent calls return component alarms
            describe_calls = [
                {'MetricAlarms': [], 'CompositeAlarms': [realistic_composite_alarm]},
                {  # For web-server-cpu-alarm
                    'MetricAlarms': [realistic_metric_alarm],
                    'CompositeAlarms': [],
                },
                {  # For database-connection-alarm
                    'MetricAlarms': [
                        {
                            'AlarmName': 'database-connection-alarm',
                            'AlarmDescription': 'Database connection monitoring',
                            'StateValue': 'OK',
                            'MetricName': 'DatabaseConnections',
                            'Namespace': 'AWS/RDS',
                            'Threshold': 80.0,
                            'ComparisonOperator': 'GreaterThanThreshold',
                            'EvaluationPeriods': 1,
                            'Period': 300,
                            'Statistic': 'Average',
                        }
                    ],
                    'CompositeAlarms': [],
                },
                {  # For maintenance-mode-alarm
                    'MetricAlarms': [
                        {
                            'AlarmName': 'maintenance-mode-alarm',
                            'AlarmDescription': 'Maintenance mode indicator',
                            'StateValue': 'OK',
                            'MetricName': 'MaintenanceMode',
                            'Namespace': 'Custom/Application',
                            'Threshold': 1.0,
                            'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                            'EvaluationPeriods': 1,
                            'Period': 60,
                            'Statistic': 'Maximum',
                        }
                    ],
                    'CompositeAlarms': [],
                },
            ]

            mock_client.describe_alarms.side_effect = describe_calls

            alarms_tools = CloudWatchAlarmsTools()

            # Call with component expansion
            result = await alarms_tools.get_alarm_history(
                ctx=mock_context,
                alarm_name='application-health-composite',
                include_component_alarms=True,
            )

            # Verify composite alarm response
            assert isinstance(result, CompositeAlarmComponentResponse)
            assert result.composite_alarm_name == 'application-health-composite'

            # Verify alarm rule parsing
            expected_components = [
                'web-server-cpu-alarm',
                'database-connection-alarm',
                'maintenance-mode-alarm',
            ]
            assert set(result.component_alarms) == set(expected_components)

            # Verify component details
            assert result.component_details is not None
            assert len(result.component_details) == 3

            # Check each component
            component_names = [detail.alarm_name for detail in result.component_details]
            assert 'web-server-cpu-alarm' in component_names
            assert 'database-connection-alarm' in component_names
            assert 'maintenance-mode-alarm' in component_names

    @pytest.mark.asyncio
    async def test_pagination_handling(
        self, mock_context, realistic_alarm_history_response, realistic_metric_alarm
    ):
        """Test pagination handling in alarm history."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup paginated response - simulate more items than max_items (50)
            extended_response = realistic_alarm_history_response.copy()
            # Add extra items to simulate pagination
            for i in range(47):  # Add 47 more items (4 existing + 47 = 51 total)
                extended_response['AlarmHistoryItems'].append(
                    {
                        'AlarmName': 'web-server-cpu-alarm',
                        'AlarmType': 'MetricAlarm',
                        'Timestamp': datetime(2025, 6, 20, 8, 0, 0) - timedelta(minutes=i),
                        'HistoryItemType': 'StateUpdate',
                        'HistorySummary': f'Extra item {i}',
                        'HistoryData': '{}',
                    }
                )

            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [extended_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [realistic_metric_alarm],
                'CompositeAlarms': [],
            }

            alarms_tools = CloudWatchAlarmsTools()

            result = await alarms_tools.get_alarm_history(
                ctx=mock_context, alarm_name='web-server-cpu-alarm', max_items=50
            )

            assert isinstance(result, AlarmHistoryResponse)
            assert result.has_more_results
            assert 'more available' in result.message.lower()

    @pytest.mark.asyncio
    async def test_different_history_item_types(self, mock_context, realistic_metric_alarm):
        """Test handling of different history item types."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup response with different item types
            mixed_history_response = {
                'AlarmHistoryItems': [
                    {
                        'AlarmName': 'test-alarm',
                        'AlarmType': 'MetricAlarm',
                        'Timestamp': datetime(2025, 6, 20, 10, 0, 0),
                        'HistoryItemType': 'StateUpdate',
                        'HistorySummary': 'State updated',
                        'HistoryData': json.dumps(
                            {
                                'oldState': {'stateValue': 'OK'},
                                'newState': {
                                    'stateValue': 'ALARM',
                                    'stateReason': 'Threshold crossed',
                                },
                            }
                        ),
                    },
                    {
                        'AlarmName': 'test-alarm',
                        'AlarmType': 'MetricAlarm',
                        'Timestamp': datetime(2025, 6, 20, 9, 0, 0),
                        'HistoryItemType': 'ConfigurationUpdate',
                        'HistorySummary': 'Alarm threshold updated',
                        'HistoryData': json.dumps({'updatedAlarm': {'threshold': 80.0}}),
                    },
                    {
                        'AlarmName': 'test-alarm',
                        'AlarmType': 'MetricAlarm',
                        'Timestamp': datetime(2025, 6, 20, 8, 0, 0),
                        'HistoryItemType': 'Action',
                        'HistorySummary': 'SNS notification sent',
                        'HistoryData': json.dumps(
                            {
                                'actionExecuted': {
                                    'actionArn': 'arn:aws:sns:us-east-1:123456789012:alarm-topic'
                                }
                            }
                        ),
                    },
                ]
            }

            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [mixed_history_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [realistic_metric_alarm],
                'CompositeAlarms': [],
            }

            alarms_tools = CloudWatchAlarmsTools()

            # Test with different history item types
            for item_type in ['StateUpdate', 'ConfigurationUpdate', 'Action']:
                result = await alarms_tools.get_alarm_history(
                    ctx=mock_context, alarm_name='test-alarm', history_item_type=item_type
                )

                assert isinstance(result, AlarmHistoryResponse)
                # Verify paginator was called with correct item type
                call_args = mock_paginator.paginate.call_args[1]
                assert call_args['HistoryItemType'] == item_type

    @pytest.mark.asyncio
    async def test_error_scenarios_integration(self, mock_context):
        """Test various error scenarios in integration context."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test alarm not found
            mock_paginator = Mock()
            mock_paginator.paginate.side_effect = Exception('ResourceNotFound')
            mock_client.get_paginator.return_value = mock_paginator

            # Should raise exception since error handling raises
            with pytest.raises(Exception, match='ResourceNotFound'):
                await alarms_tools.get_alarm_history(
                    ctx=mock_context, alarm_name='nonexistent-alarm'
                )

            # Verify error was logged
            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_time_range_edge_cases(self, mock_context, realistic_metric_alarm):
        """Test edge cases in time range handling."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'AlarmHistoryItems': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [realistic_metric_alarm],
                'CompositeAlarms': [],
            }

            alarms_tools = CloudWatchAlarmsTools()

            # Test with various time formats
            time_formats = [
                ('2025-06-20T08:00:00Z', '2025-06-20T12:00:00Z'),
                ('2025-06-20T08:00:00+00:00', '2025-06-20T12:00:00+00:00'),
                ('2025-06-20T08:00:00-05:00', '2025-06-20T12:00:00-05:00'),
            ]

            for start_time, end_time in time_formats:
                result = await alarms_tools.get_alarm_history(
                    ctx=mock_context,
                    alarm_name='test-alarm',
                    start_time=start_time,
                    end_time=end_time,
                )

                assert isinstance(result, AlarmHistoryResponse)

                # Verify paginator call parameters
                call_args = mock_paginator.paginate.call_args[1]
                assert 'StartDate' in call_args
                assert 'EndDate' in call_args

    @pytest.mark.asyncio
    async def test_environment_region_behavior(
        self, mock_context, realistic_alarm_history_response, realistic_metric_alarm
    ):
        """Test region behavior from environment configuration."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [realistic_alarm_history_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [realistic_metric_alarm],
                'CompositeAlarms': [],
            }

            # Test different regions via environment
            regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']

            for region in regions:
                with patch.dict('os.environ', {'AWS_REGION': region}):
                    alarms_tools = CloudWatchAlarmsTools()

                    result = await alarms_tools.get_alarm_history(
                        ctx=mock_context, alarm_name='test-alarm'
                    )

                    assert isinstance(result, AlarmHistoryResponse)

                    # Verify region-specific client creation
                    mock_session.assert_called()

    def test_complex_alarm_rule_parsing(self):
        """Test parsing of complex composite alarm rules."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # Test complex real-world alarm rules
            complex_rules = [
                (
                    '(ALARM("web-server-cpu-alarm") OR ALARM("web-server-memory-alarm")) AND NOT ALARM("maintenance-mode")',
                    ['web-server-cpu-alarm', 'web-server-memory-alarm', 'maintenance-mode'],
                ),
                (
                    'ALARM("primary-db-alarm") AND (ALARM("replica-1-alarm") OR ALARM("replica-2-alarm"))',
                    ['primary-db-alarm', 'replica-1-alarm', 'replica-2-alarm'],
                ),
                (
                    '((ALARM("app-server-1") OR ALARM("app-server-2")) AND ALARM("load-balancer")) OR ALARM("critical-service")',
                    ['app-server-1', 'app-server-2', 'load-balancer', 'critical-service'],
                ),
            ]

            for rule, expected_alarms in complex_rules:
                result = alarms_tools._parse_alarm_rule(rule)
                assert set(result) == set(expected_alarms), f'Failed for complex rule: {rule}'

    @pytest.mark.asyncio
    async def test_performance_with_large_history(self, mock_context, realistic_metric_alarm):
        """Test performance considerations with large alarm history."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Create large history response (simulating busy alarm)
            base_time = datetime(2025, 6, 20, 10, 0, 0)
            large_history = {'AlarmHistoryItems': []}

            # Generate 100 history items (alternating states)
            for i in range(100):
                timestamp = base_time - timedelta(minutes=i * 5)
                old_state = 'ALARM' if i % 2 == 0 else 'OK'
                new_state = 'OK' if i % 2 == 0 else 'ALARM'

                large_history['AlarmHistoryItems'].append(
                    {
                        'AlarmName': 'busy-alarm',
                        'AlarmType': 'MetricAlarm',
                        'Timestamp': timestamp,
                        'HistoryItemType': 'StateUpdate',
                        'HistorySummary': f'Alarm updated from {old_state} to {new_state}',
                        'HistoryData': json.dumps(
                            {
                                'oldState': {'stateValue': old_state},
                                'newState': {
                                    'stateValue': new_state,
                                    'stateReason': 'Threshold crossed',
                                },
                            }
                        ),
                    }
                )

            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [large_history]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [realistic_metric_alarm],
                'CompositeAlarms': [],
            }

            alarms_tools = CloudWatchAlarmsTools()

            result = await alarms_tools.get_alarm_history(
                ctx=mock_context, alarm_name='busy-alarm', max_items=100
            )

            assert isinstance(result, AlarmHistoryResponse)
            assert len(result.history_items) == 100

            # Should detect significant flapping
            flapping_suggestions = [
                s for s in result.time_range_suggestions if 'flapping' in s.reason.lower()
            ]
            assert len(flapping_suggestions) > 0

            # Verify performance - should complete without timeout
            # (This is implicit - if the test completes, performance is acceptable)

    @pytest.mark.asyncio
    async def test_default_time_range_behavior(self, mock_context, realistic_metric_alarm):
        """Test behavior when no start and end times are provided with mocked datetime."""
        fixed_now = datetime(2025, 6, 20, 15, 30, 0)
        expected_start = fixed_now - timedelta(hours=24)

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.datetime'
            ) as mock_datetime:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client

                # Mock datetime.now() to return fixed time
                mock_datetime.now.return_value = fixed_now
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

                mock_paginator = Mock()
                mock_paginator.paginate.return_value = [{'AlarmHistoryItems': []}]
                mock_client.get_paginator.return_value = mock_paginator
                mock_client.describe_alarms.return_value = {
                    'MetricAlarms': [realistic_metric_alarm],
                    'CompositeAlarms': [],
                }

                alarms_tools = CloudWatchAlarmsTools()

                result = await alarms_tools.get_alarm_history(
                    ctx=mock_context, alarm_name='test-alarm'
                )

                assert isinstance(result, AlarmHistoryResponse)

                # Verify paginator was called with default 24-hour range
                call_args = mock_paginator.paginate.call_args[1]
                assert 'StartDate' in call_args
                assert 'EndDate' in call_args
                assert call_args['EndDate'] == fixed_now
                assert call_args['StartDate'] == expected_start
