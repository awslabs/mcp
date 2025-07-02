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

"""Tests for CloudWatch alarm history functionality."""

import json
import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.models import (
    AlarmDetails,
    AlarmHistoryItem,
    AlarmHistoryResponse,
    CompositeAlarmComponentResponse,
    TimeRangeSuggestion,
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
def sample_alarm_history_response():
    """Sample CloudWatch GetAlarmHistory API response."""
    return {
        'AlarmHistoryItems': [
            {
                'AlarmName': 'test-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': datetime(2025, 6, 20, 10, 0, 0),
                'HistoryItemType': 'StateUpdate',
                'HistorySummary': 'Alarm updated from OK to ALARM',
                'HistoryData': json.dumps(
                    {
                        'oldState': {'stateValue': 'OK'},
                        'newState': {'stateValue': 'ALARM', 'stateReason': 'Threshold crossed'},
                    }
                ),
            },
            {
                'AlarmName': 'test-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': datetime(2025, 6, 20, 9, 0, 0),
                'HistoryItemType': 'StateUpdate',
                'HistorySummary': 'Alarm updated from ALARM to OK',
                'HistoryData': json.dumps(
                    {
                        'oldState': {'stateValue': 'ALARM'},
                        'newState': {'stateValue': 'OK', 'stateReason': 'Threshold not crossed'},
                    }
                ),
            },
        ]
    }


@pytest.fixture
def sample_metric_alarm():
    """Sample metric alarm from DescribeAlarms API."""
    return {
        'AlarmName': 'test-alarm',
        'AlarmDescription': 'Test alarm description',
        'StateValue': 'ALARM',
        'MetricName': 'CPUUtilization',
        'Namespace': 'AWS/EC2',
        'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}],
        'Threshold': 80.0,
        'ComparisonOperator': 'GreaterThanThreshold',
        'EvaluationPeriods': 2,
        'Period': 300,
        'Statistic': 'Average',
    }


@pytest.fixture
def sample_composite_alarm():
    """Sample composite alarm from DescribeAlarms API."""
    return {
        'AlarmName': 'composite-alarm',
        'AlarmDescription': 'Composite alarm description',
        'StateValue': 'ALARM',
        'AlarmRule': 'ALARM("alarm1") OR ALARM("alarm2")',
    }


class TestGetAlarmHistory:
    """Test cases for get_alarm_history functionality."""

    @pytest.mark.asyncio
    async def test_get_alarm_history_basic_functionality(
        self, mock_context, sample_alarm_history_response, sample_metric_alarm
    ):
        """Test basic alarm history retrieval functionality."""
        # Mock boto3 session and client
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup paginator mock
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [sample_alarm_history_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [sample_metric_alarm],
                'CompositeAlarms': [],
            }

            # Create CloudWatchAlarmsTools instance
            alarms_tools = CloudWatchAlarmsTools()

            # Call get_alarm_history
            result = await alarms_tools.get_alarm_history(
                ctx=mock_context, alarm_name='test-alarm'
            )

            # Verify result type and basic properties
            assert isinstance(result, AlarmHistoryResponse)
            assert result.alarm_details.alarm_name == 'test-alarm'
            assert result.alarm_details.alarm_type == 'MetricAlarm'
            assert len(result.history_items) == 2

            # Verify API calls
            mock_client.get_paginator.assert_called_once_with('describe_alarm_history')
            mock_client.describe_alarms.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_alarm_history_with_custom_parameters(
        self, mock_context, sample_alarm_history_response, sample_metric_alarm
    ):
        """Test alarm history with custom parameters."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [sample_alarm_history_response]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [sample_metric_alarm],
                'CompositeAlarms': [],
            }

            alarms_tools = CloudWatchAlarmsTools()

            # Call with custom parameters
            result = await alarms_tools.get_alarm_history(
                ctx=mock_context,
                alarm_name='test-alarm',
                start_time='2025-06-20T08:00:00Z',
                end_time='2025-06-20T12:00:00Z',
                history_item_type='StateUpdate',
                max_items=25,
            )

            assert isinstance(result, AlarmHistoryResponse)

            # Verify paginator call parameters
            call_args = mock_paginator.paginate.call_args[1]
            assert call_args['AlarmName'] == 'test-alarm'
            assert call_args['HistoryItemType'] == 'StateUpdate'
            assert call_args['PaginationConfig']['MaxItems'] == 26

    @pytest.mark.asyncio
    async def test_composite_alarm_handling(self, mock_context, sample_composite_alarm):
        """Test composite alarm component handling."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup composite alarm response
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'AlarmHistoryItems': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_alarms.return_value = {
                'MetricAlarms': [],
                'CompositeAlarms': [sample_composite_alarm],
            }

            alarms_tools = CloudWatchAlarmsTools()

            # Call with include_component_alarms=True
            result = await alarms_tools.get_alarm_history(
                ctx=mock_context, alarm_name='composite-alarm', include_component_alarms=True
            )

            assert isinstance(result, CompositeAlarmComponentResponse)
            assert result.composite_alarm_name == 'composite-alarm'
            assert result.alarm_rule == 'ALARM("alarm1") OR ALARM("alarm2")'
            assert 'alarm1' in result.component_alarms
            assert 'alarm2' in result.component_alarms

    def test_transform_history_item_with_state_update(self):
        """Test history item transformation with state update data."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # Sample history item with state update
            history_item = {
                'AlarmName': 'test-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': datetime(2025, 6, 20, 10, 0, 0),
                'HistoryItemType': 'StateUpdate',
                'HistorySummary': 'Alarm updated from OK to ALARM',
                'HistoryData': json.dumps(
                    {
                        'oldState': {'stateValue': 'OK'},
                        'newState': {'stateValue': 'ALARM', 'stateReason': 'Threshold crossed'},
                    }
                ),
            }

            result = alarms_tools._transform_history_item(history_item)

            assert isinstance(result, AlarmHistoryItem)
            assert result.alarm_name == 'test-alarm'
            assert result.old_state == 'OK'
            assert result.new_state == 'ALARM'
            assert result.state_reason == 'Threshold crossed'

    def test_transform_history_item_with_invalid_json(self):
        """Test history item transformation with invalid JSON."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # Sample history item with invalid JSON
            history_item = {
                'AlarmName': 'test-alarm',
                'AlarmType': 'MetricAlarm',
                'Timestamp': datetime(2025, 6, 20, 10, 0, 0),
                'HistoryItemType': 'StateUpdate',
                'HistorySummary': 'Alarm updated',
                'HistoryData': 'invalid json',
            }

            result = alarms_tools._transform_history_item(history_item)

            assert isinstance(result, AlarmHistoryItem)
            assert result.alarm_name == 'test-alarm'
            assert result.old_state is None
            assert result.new_state is None
            assert result.state_reason is None

    def test_generate_time_range_suggestions(self):
        """Test time range suggestion generation."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # Create sample history items with ALARM transitions
            history_items = [
                AlarmHistoryItem(
                    alarm_name='test-alarm',
                    alarm_type='MetricAlarm',
                    timestamp=datetime(2025, 6, 20, 10, 0, 0),
                    history_item_type='StateUpdate',
                    history_summary='Alarm updated',
                    old_state='OK',
                    new_state='ALARM',
                    state_reason='Threshold crossed',
                )
            ]

            # Create alarm details
            alarm_details = AlarmDetails(
                alarm_name='test-alarm',
                alarm_type='MetricAlarm',
                current_state='ALARM',
                period=300,
                evaluation_periods=2,
            )

            suggestions = alarms_tools._generate_time_range_suggestions(
                history_items, alarm_details
            )

            assert len(suggestions) == 1
            assert isinstance(suggestions[0], TimeRangeSuggestion)

            # Verify time range calculation (5 * period * evaluation_periods before, 2 * period after)
            expected_start = datetime(2025, 6, 20, 10, 0, 0) - timedelta(
                seconds=300 * 2 * 5
            )  # 50 minutes before
            expected_end = datetime(2025, 6, 20, 10, 0, 0) + timedelta(
                seconds=300 * 2
            )  # 10 minutes after

            assert suggestions[0].start_time == expected_start
            assert suggestions[0].end_time == expected_end

    def test_generate_time_range_suggestions_with_flapping(self):
        """Test time range suggestions with alarm flapping detection."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # Create multiple ALARM transitions within short time (flapping)
            base_time = datetime(2025, 6, 20, 10, 0, 0)
            history_items = [
                AlarmHistoryItem(
                    alarm_name='test-alarm',
                    alarm_type='MetricAlarm',
                    timestamp=base_time,
                    history_item_type='StateUpdate',
                    history_summary='Alarm updated',
                    old_state='OK',
                    new_state='ALARM',
                    state_reason='Threshold crossed',
                ),
                AlarmHistoryItem(
                    alarm_name='test-alarm',
                    alarm_type='MetricAlarm',
                    timestamp=base_time + timedelta(minutes=10),
                    history_item_type='StateUpdate',
                    history_summary='Alarm updated',
                    old_state='OK',
                    new_state='ALARM',
                    state_reason='Threshold crossed',
                ),
            ]

            alarm_details = AlarmDetails(
                alarm_name='test-alarm',
                alarm_type='MetricAlarm',
                current_state='ALARM',
                period=300,
                evaluation_periods=1,
            )

            suggestions = alarms_tools._generate_time_range_suggestions(
                history_items, alarm_details
            )

            # Should have individual suggestions plus flapping cluster suggestion
            assert len(suggestions) >= 2

            # Check for flapping detection in reasons
            flapping_suggestions = [s for s in suggestions if 'flapping' in s.reason.lower()]
            assert len(flapping_suggestions) >= 1

    def test_parse_alarm_rule(self):
        """Test composite alarm rule parsing."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # Test various alarm rule formats
            test_cases = [
                ('ALARM("alarm1") OR ALARM("alarm2")', ['alarm1', 'alarm2']),
                ('ALARM("single-alarm")', ['single-alarm']),
                (
                    'ALARM("alarm-1") AND ALARM("alarm-2") OR ALARM("alarm-3")',
                    ['alarm-1', 'alarm-2', 'alarm-3'],
                ),
                ('', []),
                ('ALARM(alarm-without-quotes)', ['alarm-without-quotes']),
            ]

            for rule, expected_alarms in test_cases:
                result = alarms_tools._parse_alarm_rule(rule)
                assert set(result) == set(expected_alarms), f'Failed for rule: {rule}'

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_context):
        """Test error handling in get_alarm_history."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup paginator to raise an exception
            mock_paginator = Mock()
            mock_paginator.paginate.side_effect = Exception('Access denied')
            mock_client.get_paginator.return_value = mock_paginator

            alarms_tools = CloudWatchAlarmsTools()

            # Should raise exception since error handling raises
            with pytest.raises(Exception, match='Access denied'):
                await alarms_tools.get_alarm_history(ctx=mock_context, alarm_name='test-alarm')

            # Verify error was logged
            mock_context.error.assert_called_once()

    def test_alarm_tools_registration_includes_history(self):
        """Test that CloudWatchAlarmsTools registers the get_alarm_history tool."""
        mock_mcp = Mock()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            alarms_tools.get_alarm_history = Mock()

            alarms_tools.register(mock_mcp)

            # Verify both tools are registered
            assert mock_mcp.tool.call_count == 2
            tool_calls = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
            assert 'get_active_alarms' in tool_calls
            assert 'get_alarm_history' in tool_calls

    def test_region_handling(self):
        """Test region handling from environment configuration."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Test default region when no environment variable is set
            with patch.dict('os.environ', {}, clear=True):
                CloudWatchAlarmsTools()
                # Should use default us-east-1
                mock_session.assert_called_with(region_name='us-east-1')

            # Test custom region from environment
            with patch.dict('os.environ', {'AWS_REGION': 'eu-west-1'}):
                CloudWatchAlarmsTools()
                # Should use environment region
                mock_session.assert_called_with(region_name='eu-west-1')


class TestAlarmHistoryEdgeCases:
    """Test edge cases for alarm history functionality."""

    def test_empty_history_response(self):
        """Test handling of empty alarm history."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # Test with empty history items
            suggestions = alarms_tools._generate_time_range_suggestions(
                [], AlarmDetails(alarm_name='test', alarm_type='MetricAlarm', current_state='OK')
            )

            assert suggestions == []

    def test_history_item_with_missing_fields(self):
        """Test history item transformation with missing fields."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'):
            alarms_tools = CloudWatchAlarmsTools()

            # History item with minimal fields
            history_item = {
                'AlarmName': 'test-alarm'
                # Missing other fields
            }

            result = alarms_tools._transform_history_item(history_item)

            assert isinstance(result, AlarmHistoryItem)
            assert result.alarm_name == 'test-alarm'
            assert result.alarm_type == ''
            assert result.history_item_type == ''

    def test_alarm_details_not_found(self):
        """Test alarm details retrieval when alarm doesn't exist."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            # Setup empty response (alarm not found)
            mock_client.describe_alarms.return_value = {'MetricAlarms': [], 'CompositeAlarms': []}

            alarms_tools = CloudWatchAlarmsTools()

            # This should be an async call
            import asyncio

            result = asyncio.run(alarms_tools._get_alarm_details(mock_client, 'nonexistent-alarm'))

            assert isinstance(result, AlarmDetails)
            assert result.alarm_name == 'nonexistent-alarm'
            assert result.alarm_type == 'Unknown'
            assert result.current_state == 'Unknown'
            assert 'not found' in result.alarm_description.lower()
