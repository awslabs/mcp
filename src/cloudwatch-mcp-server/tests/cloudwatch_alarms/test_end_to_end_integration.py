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

"""End-to-end integration tests for CloudWatch autoscaling alarm filtering functionality."""

import pytest
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.models import ActiveAlarmsResponse
from awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools import CloudWatchAlarmsTools

# Import shared fixtures
from tests.cloudwatch_alarms.fixtures import (
    AlarmFixtures,
    PaginationFixtures,
)
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
def realistic_cloudwatch_api_responses():
    """Create realistic CloudWatch API responses using shared fixtures for consistency."""
    # Use shared fixtures to create realistic multi-page responses
    return PaginationFixtures.create_multi_page_response_for_filtering() + [
        # Add additional page with more diverse alarm types
        {
            'MetricAlarms': [
                # Create additional application alarms with different names
                {
                    **AlarmFixtures.create_metric_alarm_without_autoscaling_actions(),
                    'AlarmName': 'api-gateway-5xx-errors',
                    'AlarmDescription': 'API Gateway 5XX error rate is high',
                    'MetricName': '5XXError',
                    'Namespace': 'AWS/ApiGateway',
                    'Dimensions': [{'Name': 'ApiName', 'Value': 'production-api'}],
                },
                {
                    **AlarmFixtures.create_metric_alarm_without_autoscaling_actions(),
                    'AlarmName': 'lambda-function-errors',
                    'AlarmDescription': 'Lambda function error rate is high',
                    'MetricName': 'Errors',
                    'Namespace': 'AWS/Lambda',
                    'Dimensions': [{'Name': 'FunctionName', 'Value': 'data-processor'}],
                },
            ],
            'CompositeAlarms': [],
        }
    ]


class TestEndToEndIntegration:
    """End-to-end integration tests for CloudWatch autoscaling alarm filtering."""

    @pytest.mark.asyncio
    async def test_complete_workflow_with_filtering_enabled(
        self, mock_context, realistic_cloudwatch_api_responses
    ):
        """Test complete end-to-end workflow with filtering enabled - validates all requirements."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = realistic_cloudwatch_api_responses
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test with filtering enabled (default behavior)
            result = await alarms_tools.get_active_alarms(
                ctx=mock_context,
                max_items=5,  # Request 5 alarms to test pagination behavior
                region='us-east-1',
                include_autoscaling_alarms=False,  # Explicit filtering
            )

            # Validate Requirements 1.1, 1.2, 1.3, 1.4: Parameter handling and filtering behavior
            assert isinstance(result, ActiveAlarmsResponse)

            # Verify paginator was called without MaxItems (filtering enabled)
            # When filtering is enabled, omit MaxItems to allow processing all pages
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM', AlarmTypes=['CompositeAlarm', 'MetricAlarm']
            )

            # Validate Requirements 2.1, 2.2, 2.3: Pagination preserves max_items limit
            total_returned = len(result.metric_alarms) + len(result.composite_alarms)
            assert total_returned == 5  # Should return exactly max_items non-autoscaling alarms

            # Validate Requirements 3.1-3.6: Autoscaling alarm detection accuracy
            # Verify only non-autoscaling alarms are included (using actual shared fixture names)
            returned_metric_names = {alarm.alarm_name for alarm in result.metric_alarms}
            returned_composite_names = {alarm.alarm_name for alarm in result.composite_alarms}

            # Should NOT contain autoscaling alarms (from shared fixtures)
            autoscaling_alarms = {
                'autoscaling-cpu-high-alarm',  # Has autoscaling actions in AlarmActions
                'mixed-actions-cpu-alarm',  # Has mixed actions including autoscaling
                'autoscaling-composite-alarm',  # Composite alarm with autoscaling actions
            }
            assert returned_metric_names.isdisjoint(autoscaling_alarms)
            assert returned_composite_names.isdisjoint(autoscaling_alarms)

            # Should contain only non-autoscaling alarms (from shared fixtures)
            expected_non_autoscaling_alarms = {
                'application-cpu-high-alarm',  # Pure application alarm
                'empty-actions-alarm',  # Alarm with empty actions
                'additional-app-alarm-1',  # Additional application alarm
                'additional-app-alarm-2',  # Additional application alarm
                'api-gateway-5xx-errors',  # Custom application alarm
                'lambda-function-errors',  # Custom application alarm
            }
            expected_non_autoscaling_composite = {
                'application-health-composite-alarm'  # Application composite alarm
            }

            # Verify returned alarms are from the expected non-autoscaling set
            assert returned_metric_names.issubset(expected_non_autoscaling_alarms)
            assert returned_composite_names.issubset(expected_non_autoscaling_composite)

            # Response messaging and has_more_results
            assert result.has_more_results  # Should be True since we limited to 5 items
            assert result.message is not None
            assert 'non-autoscaling alarms' in result.message.lower()
            assert 'filtered out' in result.message.lower()

            # Backward compatibility
            # Response structure should match ActiveAlarmsResponse
            assert hasattr(result, 'metric_alarms')
            assert hasattr(result, 'composite_alarms')
            assert hasattr(result, 'has_more_results')
            assert hasattr(result, 'message')

    @pytest.mark.asyncio
    async def test_complete_workflow_with_filtering_disabled(
        self, mock_context, single_page_mixed_response
    ):
        """Test complete workflow when autoscaling alarm filtering is disabled."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = single_page_mixed_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test with filtering disabled (backward compatibility)
            result = await alarms_tools.get_active_alarms(
                ctx=mock_context,
                max_items=10,
                region='us-east-1',
                include_autoscaling_alarms=True,  # Disable filtering
            )

            # Backward compatibility
            assert isinstance(result, ActiveAlarmsResponse)

            # Verify paginator was called with MaxItems (backward compatibility)
            # When filtering is disabled, use MaxItems for optimal performance
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM',
                AlarmTypes=['CompositeAlarm', 'MetricAlarm'],
                PaginationConfig={'MaxItems': 11},  # max_items + 1
            )

            # Should include ALL alarms (both autoscaling and non-autoscaling)
            total_returned = len(result.metric_alarms) + len(result.composite_alarms)
            assert total_returned == 5  # All alarms from single_page_mixed_response

            # Verify both autoscaling and non-autoscaling alarms are included
            returned_metric_names = {alarm.alarm_name for alarm in result.metric_alarms}
            returned_composite_names = {alarm.alarm_name for alarm in result.composite_alarms}

            # Should include autoscaling alarms (from shared fixtures)
            assert 'autoscaling-cpu-high-alarm' in returned_metric_names
            assert 'mixed-actions-cpu-alarm' in returned_metric_names
            assert 'autoscaling-composite-alarm' in returned_composite_names

            # Should also include non-autoscaling alarms
            assert 'application-cpu-high-alarm' in returned_metric_names
            assert 'application-health-composite-alarm' in returned_composite_names

    @pytest.mark.asyncio
    async def test_complete_workflow_with_default_parameter_behavior(
        self, mock_context, single_page_mixed_response
    ):
        """Test complete workflow with default parameter behavior (filtering enabled)."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = single_page_mixed_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test with omitted include_autoscaling_alarms parameter (should default to False)
            result = await alarms_tools.get_active_alarms(
                ctx=mock_context,
                max_items=5,
                region='us-east-1',
                # include_autoscaling_alarms parameter omitted - should default to False
            )

            # Default behavior should filter autoscaling alarms
            assert isinstance(result, ActiveAlarmsResponse)

            # Verify paginator was called without MaxItems (filtering enabled by default)
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM', AlarmTypes=['CompositeAlarm', 'MetricAlarm']
            )

            # Should exclude autoscaling alarms by default
            returned_metric_names = {alarm.alarm_name for alarm in result.metric_alarms}
            returned_composite_names = {alarm.alarm_name for alarm in result.composite_alarms}

            # Should NOT contain autoscaling alarms (from shared fixtures)
            autoscaling_alarms = {
                'autoscaling-cpu-high-alarm',
                'mixed-actions-cpu-alarm',  # Mixed actions are treated as autoscaling
                'autoscaling-composite-alarm',
            }
            assert returned_metric_names.isdisjoint(autoscaling_alarms)
            assert returned_composite_names.isdisjoint(autoscaling_alarms)

    @pytest.mark.asyncio
    async def test_realistic_pagination_behavior_with_large_dataset(
        self, mock_context, large_dataset_response
    ):
        """Test realistic pagination behavior with large dataset and filtering."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = large_dataset_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Request 8 non-autoscaling alarms (should require processing multiple pages)
            result = await alarms_tools.get_active_alarms(
                ctx=mock_context, max_items=8, region='us-east-1', include_autoscaling_alarms=False
            )

            # Validate Pagination continues until max_items collected
            assert isinstance(result, ActiveAlarmsResponse)
            assert (
                len(result.metric_alarms) == 8
            )  # Should collect exactly 8 non-autoscaling alarms

            # Validate has_more_results accuracy
            assert (
                result.has_more_results
            )  # Should be True since there are more application alarms available

            # Verify all returned alarms are non-autoscaling
            for alarm in result.metric_alarms:
                assert 'application-alarm' in alarm.alarm_name
                assert 'autoscaling-alarm' not in alarm.alarm_name

            # Validate messaging
            assert result.message is not None
            assert 'non-autoscaling alarms' in result.message.lower()
            assert 'filtered out' in result.message.lower()

    @pytest.mark.asyncio
    async def test_edge_case_all_alarms_are_autoscaling(self, mock_context):
        """Test edge case where all alarms are autoscaling-related."""
        all_autoscaling_response = PaginationFixtures.create_single_page_response_all_autoscaling()

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = all_autoscaling_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            result = await alarms_tools.get_active_alarms(
                ctx=mock_context,
                max_items=10,
                region='us-east-1',
                include_autoscaling_alarms=False,
            )

            assert isinstance(result, ActiveAlarmsResponse)
            assert len(result.metric_alarms) == 0
            assert len(result.composite_alarms) == 0
            assert not result.has_more_results
            assert result.message is not None
            assert 'No non-autoscaling active alarms found' in result.message
            assert 'autoscaling alarms were filtered out' in result.message
            assert 'Set include_autoscaling_alarms=True to see all alarms' in result.message

    @pytest.mark.asyncio
    async def test_error_handling_and_fallback_behavior(
        self, mock_context, non_autoscaling_metric_alarm, malformed_actions_alarm
    ):
        """Test error handling and fallback behavior with malformed alarm data."""
        # Create response with normal alarm and problematic alarm data
        problematic_response = [
            {
                'MetricAlarms': [
                    non_autoscaling_metric_alarm,  # Normal alarm
                    malformed_actions_alarm,  # Problematic alarm with malformed actions
                ],
                'CompositeAlarms': [],
            }
        ]

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = problematic_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Mock the autoscaling filter to raise an exception for the problematic alarm
            original_has_autoscaling_actions = (
                alarms_tools.autoscaling_filter.has_autoscaling_actions
            )

            def mock_has_autoscaling_actions(alarm_data):
                if alarm_data.get('AlarmName') == 'malformed-actions-alarm':
                    raise Exception('Filtering error for problematic alarm')
                return original_has_autoscaling_actions(alarm_data)

            with patch.object(
                alarms_tools.autoscaling_filter,
                'has_autoscaling_actions',
                side_effect=mock_has_autoscaling_actions,
            ):
                result = await alarms_tools.get_active_alarms(
                    ctx=mock_context,
                    max_items=10,
                    region='us-east-1',
                    include_autoscaling_alarms=False,
                )

                assert isinstance(result, ActiveAlarmsResponse)
                assert (
                    len(result.metric_alarms) == 2
                )  # Both alarms should be included (fallback behavior)

                # Verify both alarms are present
                alarm_names = {alarm.alarm_name for alarm in result.metric_alarms}
                assert 'application-cpu-high-alarm' in alarm_names  # Normal alarm
                assert (
                    'malformed-actions-alarm' in alarm_names
                )  # Should be included due to fallback

    @pytest.mark.asyncio
    async def test_parameter_validation_and_type_handling(self, mock_context, empty_response):
        """Test parameter validation and type handling for various input types."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = empty_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            # Test with None values (should use defaults)
            result = await alarms_tools.get_active_alarms(
                ctx=mock_context,
                max_items=None,  # Should default to 50
                region='us-east-1',
                include_autoscaling_alarms=None,  # Should default to False
            )

            assert isinstance(result, ActiveAlarmsResponse)

            # Verify paginator was called without MaxItems (filtering enabled by default)
            mock_paginator.paginate.assert_called_once_with(
                StateValue='ALARM', AlarmTypes=['CompositeAlarm', 'MetricAlarm']
            )

            # Test with invalid max_items (should raise ValueError)
            with pytest.raises(ValueError, match='max_items must be at least 1'):
                await alarms_tools.get_active_alarms(
                    ctx=mock_context, max_items=0, region='us-east-1'
                )

    @pytest.mark.asyncio
    async def test_comprehensive_autoscaling_action_detection(
        self,
        mock_context,
        autoscaling_metric_alarm,
        non_autoscaling_metric_alarm,
        mixed_actions_metric_alarm,
    ):
        """Test comprehensive autoscaling action detection across various alarm types."""
        # Create comprehensive test response using shared fixtures and additional alarms
        autoscaling_ok_actions_alarm = (
            AlarmFixtures.create_metric_alarm_with_autoscaling_ok_actions()
        )
        autoscaling_insufficient_data_alarm = (
            AlarmFixtures.create_metric_alarm_with_autoscaling_insufficient_data_actions()
        )

        comprehensive_test_response = [
            {
                'MetricAlarms': [
                    autoscaling_metric_alarm,
                    autoscaling_ok_actions_alarm,
                    autoscaling_insufficient_data_alarm,
                    mixed_actions_metric_alarm,
                    non_autoscaling_metric_alarm,
                ],
                'CompositeAlarms': [],
            }
        ]

        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_alarms.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = comprehensive_test_response
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            alarms_tools = CloudWatchAlarmsTools()

            result = await alarms_tools.get_active_alarms(
                ctx=mock_context,
                max_items=10,
                region='us-east-1',
                include_autoscaling_alarms=False,
            )

            # Validate Requirements 3.1-3.6: Comprehensive autoscaling detection
            assert isinstance(result, ActiveAlarmsResponse)
            assert (
                len(result.metric_alarms) == 1
            )  # Only the pure application alarm should be included

            # Verify only the non-autoscaling alarm is returned
            assert result.metric_alarms[0].alarm_name == 'application-cpu-high-alarm'

            # Verify all autoscaling alarms were filtered out
            returned_names = {alarm.alarm_name for alarm in result.metric_alarms}
            autoscaling_alarm_names = {
                'autoscaling-cpu-high-alarm',  # Requirement 3.1: AlarmActions
                'autoscaling-cpu-low-alarm',  # Requirement 3.2: OKActions
                'autoscaling-memory-insufficient-data-alarm',  # Requirement 3.3: InsufficientDataActions
                'mixed-actions-cpu-alarm',  # Requirement 3.5: Mixed actions
            }
            assert returned_names.isdisjoint(autoscaling_alarm_names)

            # Validate messaging indicates filtering occurred
            assert result.message is not None
            assert 'filtered out' in result.message.lower()
            assert (
                '4 autoscaling alarms' in result.message
            )  # Should indicate 4 alarms were filtered
