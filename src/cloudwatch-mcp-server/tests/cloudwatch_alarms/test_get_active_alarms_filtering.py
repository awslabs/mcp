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

"""Integration tests for CloudWatch active alarms filtering functionality.

This module contains comprehensive integration tests for the get_active_alarms method
with the new include_autoscaling_alarms parameter. Tests cover various filtering
scenarios, pagination behavior, backward compatibility, and edge cases.

The tests validate that:
- Filtering correctly excludes autoscaling alarms when enabled
- Backward compatibility is maintained when filtering is disabled
- Pagination works correctly with filtering enabled
- Error handling and edge cases are properly managed
- Performance characteristics are maintained
"""

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


# Fixtures are now imported from fixtures.py module


class TestGetActiveAlarmsFiltering:
    """Integration tests for get_active_alarms filtering functionality."""

    @pytest.mark.asyncio
    async def test_include_autoscaling_alarms_true_returns_all_alarms(
        self,
        mock_context,
        autoscaling_metric_alarm,
        non_autoscaling_metric_alarm,
        autoscaling_composite_alarm,
        non_autoscaling_composite_alarm,
    ):
        """Test that include_autoscaling_alarms=True returns all alarms (backward compatibility)."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [autoscaling_metric_alarm, non_autoscaling_metric_alarm],
                    'CompositeAlarms': [
                        autoscaling_composite_alarm,
                        non_autoscaling_composite_alarm,
                    ],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=10, include_autoscaling_alarms=True
            )

            # Verify paginator was called with MaxItems limit (backward compatibility)
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM',
                AlarmTypes=['CompositeAlarm', 'MetricAlarm'],
                PaginationConfig={'MaxItems': 11},
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 2  # Both metric alarms included
            assert len(result.composite_alarms) == 2  # Both composite alarms included

            # Verify all alarm names are present
            metric_names = [alarm.alarm_name for alarm in result.metric_alarms]
            composite_names = [alarm.alarm_name for alarm in result.composite_alarms]

            assert 'autoscaling-cpu-high-alarm' in metric_names
            assert 'application-cpu-high-alarm' in metric_names
            assert 'autoscaling-composite-alarm' in composite_names
            assert 'application-health-composite-alarm' in composite_names

    @pytest.mark.asyncio
    async def test_include_autoscaling_alarms_false_excludes_autoscaling_alarms(
        self,
        mock_context,
        autoscaling_metric_alarm,
        non_autoscaling_metric_alarm,
        autoscaling_composite_alarm,
        non_autoscaling_composite_alarm,
    ):
        """Test that include_autoscaling_alarms=False excludes autoscaling alarms."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [autoscaling_metric_alarm, non_autoscaling_metric_alarm],
                    'CompositeAlarms': [
                        autoscaling_composite_alarm,
                        non_autoscaling_composite_alarm,
                    ],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=10, include_autoscaling_alarms=False
            )

            # Verify paginator was called without MaxItems limit (filtering enabled)
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM', AlarmTypes=['CompositeAlarm', 'MetricAlarm']
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1  # Only non-autoscaling metric alarm
            assert len(result.composite_alarms) == 1  # Only non-autoscaling composite alarm

            # Verify only non-autoscaling alarms are present
            assert result.metric_alarms[0].alarm_name == 'application-cpu-high-alarm'
            assert result.composite_alarms[0].alarm_name == 'application-health-composite-alarm'

    @pytest.mark.asyncio
    async def test_omitting_parameter_uses_default_filtering_behavior(
        self, mock_context, autoscaling_metric_alarm, non_autoscaling_metric_alarm
    ):
        """Test that omitting the parameter uses default filtering behavior (False)."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [autoscaling_metric_alarm, non_autoscaling_metric_alarm],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            # Call without include_autoscaling_alarms parameter
            result = await alarms_tools.get_active_alarms(mock_context, max_items=10)

            # Verify paginator was called without MaxItems limit (filtering enabled by default)
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM', AlarmTypes=['CompositeAlarm', 'MetricAlarm']
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1  # Only non-autoscaling alarm
            assert result.metric_alarms[0].alarm_name == 'application-cpu-high-alarm'

    @pytest.mark.asyncio
    async def test_pagination_continues_until_max_items_non_autoscaling_alarms_collected(
        self, mock_context, autoscaling_metric_alarm, non_autoscaling_metric_alarm
    ):
        """Test pagination continues until max_items non-autoscaling alarms are collected."""
        # Create additional non-autoscaling alarms for pagination test
        additional_non_autoscaling_alarm = {
            'AlarmName': 'additional-app-alarm',
            'AlarmDescription': 'Additional application alarm',
            'StateValue': 'ALARM',
            'StateReason': 'Additional alarm triggered',
            'MetricName': 'MemoryUtilization',
            'Namespace': 'AWS/EC2',
            'Dimensions': [{'Name': 'InstanceId', 'Value': 'i-9876543210fedcba'}],
            'Threshold': 90.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'StateUpdatedTimestamp': datetime.now(),
            'AlarmActions': ['arn:aws:sns:us-east-1:123456789012:app-alerts'],
            'OKActions': [],
            'InsufficientDataActions': [],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            # Simulate multiple pages with mixed alarm types
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [autoscaling_metric_alarm, autoscaling_metric_alarm],
                    'CompositeAlarms': [],
                },
                {'MetricAlarms': [non_autoscaling_metric_alarm], 'CompositeAlarms': []},
                {'MetricAlarms': [additional_non_autoscaling_alarm], 'CompositeAlarms': []},
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=2, include_autoscaling_alarms=False
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 2  # Collected 2 non-autoscaling alarms

            # Verify the correct alarms were collected
            alarm_names = [alarm.alarm_name for alarm in result.metric_alarms]
            assert 'application-cpu-high-alarm' in alarm_names
            assert 'additional-app-alarm' in alarm_names
            assert 'autoscaling-cpu-high-alarm' not in alarm_names

    @pytest.mark.asyncio
    async def test_behavior_when_all_alarms_have_autoscaling_actions(
        self, mock_context, autoscaling_metric_alarm, autoscaling_composite_alarm
    ):
        """Test behavior when all alarms have autoscaling actions."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [autoscaling_metric_alarm, autoscaling_metric_alarm],
                    'CompositeAlarms': [autoscaling_composite_alarm],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=10, include_autoscaling_alarms=False
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 0
            assert len(result.composite_alarms) == 0
            assert 'No non-autoscaling active alarms found' in result.message
            assert 'autoscaling alarms were filtered out' in result.message
            assert 'Set include_autoscaling_alarms=True to see all alarms' in result.message
            assert not result.has_more_results

    @pytest.mark.asyncio
    async def test_has_more_results_accuracy_with_filtering_enabled(
        self, mock_context, autoscaling_metric_alarm, non_autoscaling_metric_alarm
    ):
        """Test has_more_results accuracy with filtering enabled."""
        # Create additional alarms to test has_more_results logic
        additional_alarms = []
        for i in range(5):
            additional_alarms.append(
                {
                    'AlarmName': f'app-alarm-{i}',
                    'AlarmDescription': f'Application alarm {i}',
                    'StateValue': 'ALARM',
                    'StateReason': f'Alarm {i} triggered',
                    'MetricName': 'CPUUtilization',
                    'Namespace': 'AWS/EC2',
                    'Dimensions': [{'Name': 'InstanceId', 'Value': f'i-{i:016x}'}],
                    'Threshold': 80.0,
                    'ComparisonOperator': 'GreaterThanThreshold',
                    'StateUpdatedTimestamp': datetime.now(),
                    'AlarmActions': ['arn:aws:sns:us-east-1:123456789012:app-alerts'],
                    'OKActions': [],
                    'InsufficientDataActions': [],
                }
            )

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        autoscaling_metric_alarm,  # Will be filtered out
                        non_autoscaling_metric_alarm,  # Will be included
                        *additional_alarms,  # All will be included
                    ],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=3,  # Request only 3 alarms
                include_autoscaling_alarms=False,
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 3  # Only 3 returned despite more available
            assert (
                result.has_more_results
            )  # Should be True because we have more non-autoscaling alarms
            assert 'Showing 3 non-autoscaling alarms' in result.message
            assert 'more non-autoscaling alarms available' in result.message

    @pytest.mark.asyncio
    async def test_has_more_results_false_when_no_more_alarms(
        self, mock_context, autoscaling_metric_alarm, non_autoscaling_metric_alarm
    ):
        """Test has_more_results is False when no more alarms are available."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        autoscaling_metric_alarm,  # Will be filtered out
                        non_autoscaling_metric_alarm,  # Will be included
                    ],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=5,  # Request more than available
                include_autoscaling_alarms=False,
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1  # Only 1 non-autoscaling alarm available
            assert not result.has_more_results  # Should be False because no more alarms available

    @pytest.mark.asyncio
    async def test_mixed_actions_alarm_treated_as_autoscaling(
        self, mock_context, mixed_actions_metric_alarm, non_autoscaling_metric_alarm
    ):
        """Test that alarms with mixed autoscaling and non-autoscaling actions are treated as autoscaling."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [mixed_actions_metric_alarm, non_autoscaling_metric_alarm],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=10, include_autoscaling_alarms=False
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1  # Only non-autoscaling alarm included
            assert result.metric_alarms[0].alarm_name == 'application-cpu-high-alarm'
            # Mixed actions alarm should be filtered out

    @pytest.mark.asyncio
    async def test_autoscaling_actions_in_different_fields(self, mock_context):
        """Test detection of autoscaling actions in different action fields."""
        # Alarm with autoscaling action in OKActions
        alarm_ok_actions = {
            'AlarmName': 'ok-actions-alarm',
            'StateValue': 'ALARM',
            'StateReason': 'Test reason',
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Dimensions': [],
            'Threshold': 80.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'StateUpdatedTimestamp': datetime.now(),
            'AlarmActions': [],
            'OKActions': [
                'arn:aws:autoscaling:us-east-1:123456789012:scalingPolicy:policy-id:autoScalingGroupName/my-asg:policyName/scale-down'
            ],
            'InsufficientDataActions': [],
        }

        # Alarm with autoscaling action in InsufficientDataActions
        alarm_insufficient_data_actions = {
            'AlarmName': 'insufficient-data-actions-alarm',
            'StateValue': 'ALARM',
            'StateReason': 'Test reason',
            'MetricName': 'MemoryUtilization',
            'Namespace': 'AWS/EC2',
            'Dimensions': [],
            'Threshold': 90.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'StateUpdatedTimestamp': datetime.now(),
            'AlarmActions': [],
            'OKActions': [],
            'InsufficientDataActions': [
                'arn:aws:autoscaling:us-west-2:987654321098:scalingPolicy:another-policy:autoScalingGroupName/another-asg:policyName/scale-up'
            ],
        }

        # Non-autoscaling alarm for comparison
        non_autoscaling_alarm = {
            'AlarmName': 'non-autoscaling-alarm',
            'StateValue': 'ALARM',
            'StateReason': 'Test reason',
            'MetricName': 'DiskUtilization',
            'Namespace': 'AWS/EC2',
            'Dimensions': [],
            'Threshold': 95.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'StateUpdatedTimestamp': datetime.now(),
            'AlarmActions': ['arn:aws:sns:us-east-1:123456789012:alerts'],
            'OKActions': [],
            'InsufficientDataActions': [],
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'MetricAlarms': [
                        alarm_ok_actions,
                        alarm_insufficient_data_actions,
                        non_autoscaling_alarm,
                    ],
                    'CompositeAlarms': [],
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context, max_items=10, include_autoscaling_alarms=False
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 1  # Only non-autoscaling alarm included
            assert result.metric_alarms[0].alarm_name == 'non-autoscaling-alarm'

    @pytest.mark.asyncio
    async def test_filtering_error_handling_fallback_to_include(self, mock_context):
        """Test that filtering errors result in fallback to including the alarm."""
        problematic_alarm = {
            'AlarmName': 'problematic-alarm',
            'StateValue': 'ALARM',
            'StateReason': 'Test reason',
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Dimensions': [],
            'Threshold': 80.0,
            'ComparisonOperator': 'GreaterThanThreshold',
            'StateUpdatedTimestamp': datetime.now(),
            # Missing action fields to potentially cause issues
        }

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {'MetricAlarms': [problematic_alarm], 'CompositeAlarms': []}
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            # Mock the autoscaling filter's has_autoscaling_actions method to raise an exception
            alarms_tools = CloudWatchAlarmsTools()
            with patch.object(
                alarms_tools.autoscaling_filter, 'has_autoscaling_actions'
            ) as mock_filter:
                mock_filter.side_effect = Exception('Filter error')

                result = await alarms_tools.get_active_alarms(
                    mock_context, max_items=10, include_autoscaling_alarms=False
                )

                # Should still return the alarm despite the filtering error (fallback behavior)
                assert isinstance(result, ActiveAlarmsResponse)
                assert len(result.metric_alarms) == 1  # Alarm should be included due to fallback
                assert result.metric_alarms[0].alarm_name == 'problematic-alarm'

    @pytest.mark.asyncio
    async def test_early_termination_optimization(self, mock_context):
        """Test that pagination stops early when max_items is reached."""
        # Create many alarms to test early termination
        many_alarms = []
        for i in range(10):
            many_alarms.append(
                {
                    'AlarmName': f'app-alarm-{i}',
                    'StateValue': 'ALARM',
                    'StateReason': f'Alarm {i} triggered',
                    'MetricName': 'CPUUtilization',
                    'Namespace': 'AWS/EC2',
                    'Dimensions': [],
                    'Threshold': 80.0,
                    'ComparisonOperator': 'GreaterThanThreshold',
                    'StateUpdatedTimestamp': datetime.now(),
                    'AlarmActions': ['arn:aws:sns:us-east-1:123456789012:alerts'],
                    'OKActions': [],
                    'InsufficientDataActions': [],
                }
            )

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            # Simulate multiple pages
            mock_paginator.paginate.return_value = [
                {'MetricAlarms': many_alarms[:5], 'CompositeAlarms': []},
                {'MetricAlarms': many_alarms[5:], 'CompositeAlarms': []},
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=3,  # Request only 3 alarms
                include_autoscaling_alarms=False,
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 3  # Should stop at max_items
            assert result.has_more_results

    @pytest.mark.asyncio
    async def test_backward_compatibility_response_format(
        self, mock_context, non_autoscaling_metric_alarm
    ):
        """Test that response format remains unchanged for backward compatibility."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {'MetricAlarms': [non_autoscaling_metric_alarm], 'CompositeAlarms': []}
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()
            result = await alarms_tools.get_active_alarms(mock_context, max_items=10)

            # Verify response structure matches ActiveAlarmsResponse
            assert isinstance(result, ActiveAlarmsResponse)
            assert hasattr(result, 'metric_alarms')
            assert hasattr(result, 'composite_alarms')
            assert hasattr(result, 'has_more_results')
            assert hasattr(result, 'message')

            # Verify no new fields were added that could break backward compatibility
            expected_fields = {'metric_alarms', 'composite_alarms', 'has_more_results', 'message'}
            actual_fields = set(ActiveAlarmsResponse.model_fields.keys())
            assert actual_fields == expected_fields

    @pytest.mark.asyncio
    async def test_parameter_validation_and_defaults(self, mock_context):
        """Test parameter validation and default value handling."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'MetricAlarms': [], 'CompositeAlarms': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test with None values (should use defaults)
            result = await alarms_tools.get_active_alarms(
                mock_context,
                max_items=None,  # Should default to 50
                include_autoscaling_alarms=None,  # Should default to False
            )

            assert isinstance(result, ActiveAlarmsResponse)

            # Verify paginator was called without MaxItems (filtering enabled by default)
            mock_paginator.paginate.assert_called_with(
                StateValue='ALARM', AlarmTypes=['CompositeAlarm', 'MetricAlarm']
            )
