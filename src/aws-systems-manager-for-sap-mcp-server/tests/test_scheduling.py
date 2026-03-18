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

"""Tests for SSM for SAP scheduling tools."""

import json
import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture
def tools():
    """Create an SSMSAPSchedulingTools instance."""
    from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools import (
        SSMSAPSchedulingTools,
    )

    return SSMSAPSchedulingTools()


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    return MagicMock()


def _mock_ensure_role():
    """Return a patch for _ensure_scheduler_role."""
    return patch(
        'awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools._ensure_scheduler_role',
        return_value='arn:aws:iam::123456789012:role/EventBridgeSchedulerSSMSAPRole',
    )


class TestScheduleConfigChecks:
    """Tests for schedule_config_checks tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test scheduling config checks."""
        with _mock_ensure_role():
            mock_scheduler = MagicMock()
            mock_scheduler.create_schedule.return_value = {
                'ScheduleArn': 'arn:aws:scheduler:us-east-1:123:schedule/test'
            }
            mock_get_client.return_value = mock_scheduler

            result = await tools.schedule_config_checks(
                ctx,
                application_id='app-1',
                schedule_expression='rate(7 days)',
                check_ids=['CHECK_01'],
            )

            assert result.status == 'success'
            assert result.schedule_arn is not None
            assert result.application_id == 'app-1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_client_error(self, mock_get_client, tools, ctx):
        """Test scheduling config checks handles ClientError."""
        with _mock_ensure_role():
            mock_scheduler = MagicMock()
            mock_scheduler.create_schedule.side_effect = ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'Invalid expression'}},
                'CreateSchedule',
            )
            mock_get_client.return_value = mock_scheduler

            result = await tools.schedule_config_checks(
                ctx,
                application_id='app-1',
                schedule_expression='invalid',
            )

            assert result.status == 'error'
            assert 'ValidationException' in result.message


class TestScheduleStartApplication:
    """Tests for schedule_start_application tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test scheduling application start."""
        with _mock_ensure_role():
            mock_scheduler = MagicMock()
            mock_scheduler.create_schedule.return_value = {
                'ScheduleArn': 'arn:aws:scheduler:us-east-1:123:schedule/start'
            }
            mock_get_client.return_value = mock_scheduler

            result = await tools.schedule_start_application(
                ctx,
                application_id='app-1',
                schedule_expression='cron(0 8 ? * MON-FRI *)',
                timezone_str='America/New_York',
            )

            assert result.status == 'success'
            call_args = mock_scheduler.create_schedule.call_args[1]
            assert call_args['ScheduleExpressionTimezone'] == 'America/New_York'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_with_start_end_dates(self, mock_get_client, tools, ctx):
        """Test scheduling with start and end dates."""
        with _mock_ensure_role():
            mock_scheduler = MagicMock()
            mock_scheduler.create_schedule.return_value = {'ScheduleArn': 'arn:test'}
            mock_get_client.return_value = mock_scheduler

            result = await tools.schedule_start_application(
                ctx,
                application_id='app-1',
                schedule_expression='rate(1 day)',
                start_date='2026-01-15T00:00:00Z',
                end_date='2026-12-31T23:59:59Z',
            )

            assert result.status == 'success'
            call_args = mock_scheduler.create_schedule.call_args[1]
            assert 'StartDate' in call_args
            assert 'EndDate' in call_args


class TestScheduleStopApplication:
    """Tests for schedule_stop_application tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test scheduling application stop."""
        with _mock_ensure_role():
            mock_scheduler = MagicMock()
            mock_scheduler.create_schedule.return_value = {'ScheduleArn': 'arn:test'}
            mock_get_client.return_value = mock_scheduler

            result = await tools.schedule_stop_application(
                ctx,
                application_id='app-1',
                schedule_expression='cron(0 20 ? * MON-FRI *)',
            )

            assert result.status == 'success'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_with_ec2_shutdown(self, mock_get_client, tools, ctx):
        """Test scheduling stop with EC2 shutdown."""
        with _mock_ensure_role():
            mock_scheduler = MagicMock()
            mock_scheduler.create_schedule.return_value = {'ScheduleArn': 'arn:test'}
            mock_get_client.return_value = mock_scheduler

            result = await tools.schedule_stop_application(
                ctx,
                application_id='app-1',
                schedule_expression='rate(1 day)',
                include_ec2_instance_shutdown=True,
                stop_connected_entity='DBMS',
            )

            assert result.status == 'success'
            call_args = mock_scheduler.create_schedule.call_args[1]
            input_payload = json.loads(call_args['Target']['Input'])
            assert input_payload['IncludeEc2InstanceShutdown'] is True
            assert input_payload['StopConnectedEntity'] == 'DBMS'


class TestListAppSchedules:
    """Tests for list_app_schedules tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test listing schedules for an application."""
        mock_scheduler = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {'Schedules': [{'Name': 'sched-1'}, {'Name': 'sched-2'}]}
        ]
        mock_scheduler.get_paginator.return_value = paginator
        mock_scheduler.get_schedule.side_effect = [
            {
                'Arn': 'arn:sched-1',
                'State': 'ENABLED',
                'ScheduleExpression': 'rate(7 days)',
                'Target': {
                    'Arn': 'arn:aws:scheduler:::aws-sdk:ssmsap:startConfigurationChecks',
                    'Input': json.dumps({'ApplicationId': 'app-1'}),
                },
            },
            {
                'Arn': 'arn:sched-2',
                'State': 'DISABLED',
                'ScheduleExpression': 'rate(1 day)',
                'Target': {
                    'Arn': 'arn:aws:scheduler:::aws-sdk:ssmsap:startApplication',
                    'Input': json.dumps({'ApplicationId': 'app-1'}),
                },
            },
        ]
        mock_get_client.return_value = mock_scheduler

        result = await tools.list_app_schedules(ctx, application_id='app-1')

        assert result.application_id == 'app-1'
        assert result.total_schedules == 2
        assert result.enabled_count == 1
        assert result.disabled_count == 1

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_exclude_disabled(self, mock_get_client, tools, ctx):
        """Test listing schedules excluding disabled ones."""
        mock_scheduler = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {'Schedules': [{'Name': 'sched-1'}]}
        ]
        mock_scheduler.get_paginator.return_value = paginator
        mock_scheduler.get_schedule.return_value = {
            'Arn': 'arn:sched-1',
            'State': 'DISABLED',
            'ScheduleExpression': 'rate(1 day)',
            'Target': {
                'Arn': 'arn:aws:scheduler:::aws-sdk:ssmsap:startApplication',
                'Input': json.dumps({'ApplicationId': 'app-1'}),
            },
        }
        mock_get_client.return_value = mock_scheduler

        result = await tools.list_app_schedules(
            ctx, application_id='app-1', include_disabled=False
        )

        assert result.total_schedules == 0

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_filters_by_application_id(self, mock_get_client, tools, ctx):
        """Test that schedules are filtered by application ID."""
        mock_scheduler = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {'Schedules': [{'Name': 'sched-1'}]}
        ]
        mock_scheduler.get_paginator.return_value = paginator
        mock_scheduler.get_schedule.return_value = {
            'Arn': 'arn:sched-1',
            'State': 'ENABLED',
            'ScheduleExpression': 'rate(1 day)',
            'Target': {
                'Arn': 'arn:aws:scheduler:::aws-sdk:ssmsap:startApplication',
                'Input': json.dumps({'ApplicationId': 'other-app'}),
            },
        }
        mock_get_client.return_value = mock_scheduler

        result = await tools.list_app_schedules(ctx, application_id='app-1')

        assert result.total_schedules == 0

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_error(self, mock_get_client, tools, ctx):
        """Test listing schedules handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.list_app_schedules(ctx, application_id='app-1')

        assert result.application_id == 'app-1'
        assert result.total_schedules == 0


class TestDeleteSchedule:
    """Tests for delete_schedule tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test deleting a schedule."""
        mock_scheduler = MagicMock()
        mock_get_client.return_value = mock_scheduler

        result = await tools.delete_schedule(ctx, schedule_name='sched-1')

        assert result.status == 'success'
        mock_scheduler.delete_schedule.assert_called_once_with(Name='sched-1')

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_not_found(self, mock_get_client, tools, ctx):
        """Test deleting a non-existent schedule."""
        mock_scheduler = MagicMock()
        mock_scheduler.delete_schedule.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'DeleteSchedule',
        )
        mock_get_client.return_value = mock_scheduler

        result = await tools.delete_schedule(ctx, schedule_name='nonexistent')

        assert result.status == 'error'
        assert 'ResourceNotFoundException' in result.message


class TestUpdateScheduleState:
    """Tests for update_schedule_state tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_enable(self, mock_get_client, tools, ctx):
        """Test enabling a schedule."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.return_value = {
            'State': 'DISABLED',
            'ScheduleExpression': 'rate(1 day)',
            'Target': {'Arn': 'arn:test', 'Input': '{}'},
            'FlexibleTimeWindow': {'Mode': 'OFF'},
        }
        mock_get_client.return_value = mock_scheduler

        result = await tools.update_schedule_state(
            ctx, schedule_name='sched-1', enabled=True
        )

        assert result.status == 'success'
        assert result.previous_state == 'DISABLED'
        assert result.new_state == 'ENABLED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_already_in_desired_state(self, mock_get_client, tools, ctx):
        """Test updating when already in desired state."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.return_value = {
            'State': 'ENABLED',
            'ScheduleExpression': 'rate(1 day)',
            'Target': {'Arn': 'arn:test', 'Input': '{}'},
            'FlexibleTimeWindow': {'Mode': 'OFF'},
        }
        mock_get_client.return_value = mock_scheduler

        result = await tools.update_schedule_state(
            ctx, schedule_name='sched-1', enabled=True
        )

        assert result.status == 'no_change'
        mock_scheduler.update_schedule.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_client_error(self, mock_get_client, tools, ctx):
        """Test updating schedule state handles ClientError."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetSchedule',
        )
        mock_get_client.return_value = mock_scheduler

        result = await tools.update_schedule_state(
            ctx, schedule_name='nonexistent', enabled=True
        )

        assert result.status == 'error'


class TestGetScheduleDetails:
    """Tests for get_schedule_details tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test getting schedule details."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.return_value = {
            'Arn': 'arn:sched-1',
            'State': 'ENABLED',
            'ScheduleExpression': 'rate(7 days)',
            'Description': 'Weekly config checks',
            'Target': {
                'Arn': 'arn:aws:scheduler:::aws-sdk:ssmsap:startConfigurationChecks',
                'Input': json.dumps({'ApplicationId': 'app-1'}),
                'RoleArn': 'arn:aws:iam::123:role/test',
            },
        }
        mock_get_client.return_value = mock_scheduler

        result = await tools.get_schedule_details(ctx, schedule_name='sched-1')

        assert result['status'] == 'success'
        assert result['state'] == 'ENABLED'
        assert result['operation_type'] == 'Configuration Checks'
        assert result['input']['ApplicationId'] == 'app-1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_not_found(self, mock_get_client, tools, ctx):
        """Test getting details for non-existent schedule."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetSchedule',
        )
        mock_get_client.return_value = mock_scheduler

        result = await tools.get_schedule_details(ctx, schedule_name='nonexistent')

        assert result['status'] == 'error'
        assert 'not found' in result['message']


class TestEnsureSchedulerRole:
    """Tests for _ensure_scheduler_role helper."""

    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    def test_role_exists(self, mock_get_client):
        """Test when role already exists."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools import (
            _ensure_scheduler_role,
        )

        mock_iam = MagicMock()
        mock_iam.get_role.return_value = {
            'Role': {'Arn': 'arn:aws:iam::123:role/EventBridgeSchedulerSSMSAPRole'}
        }
        mock_get_client.return_value = mock_iam

        result = _ensure_scheduler_role()

        assert 'EventBridgeSchedulerSSMSAPRole' in result

    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    def test_role_created(self, mock_get_client):
        """Test creating the role when it doesn't exist."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools import (
            _ensure_scheduler_role,
        )

        mock_iam = MagicMock()
        mock_iam.get_role.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchEntity', 'Message': 'Not found'}},
            'GetRole',
        )
        mock_iam.create_role.return_value = {
            'Role': {'Arn': 'arn:aws:iam::123:role/EventBridgeSchedulerSSMSAPRole'}
        }
        mock_get_client.return_value = mock_iam

        result = _ensure_scheduler_role()

        assert 'EventBridgeSchedulerSSMSAPRole' in result
        mock_iam.create_role.assert_called_once()
        mock_iam.attach_role_policy.assert_called_once()


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_determine_operation_type(self):
        """Test _determine_operation_type mapping."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools import (
            _determine_operation_type,
        )

        assert _determine_operation_type('arn:aws:scheduler:::aws-sdk:ssmsap:startApplication') == 'Start Application'
        assert _determine_operation_type('arn:aws:scheduler:::aws-sdk:ssmsap:stopApplication') == 'Stop Application'
        assert _determine_operation_type('arn:aws:scheduler:::aws-sdk:ssmsap:startConfigurationChecks') == 'Configuration Checks'
        assert _determine_operation_type('arn:unknown') == 'Unknown'

    def test_generate_schedule_name(self):
        """Test _generate_schedule_name produces valid names."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_scheduling.tools import (
            _generate_schedule_name,
        )

        name = _generate_schedule_name('ssmsap-cc-', 'my-app')
        assert name.startswith('ssmsap-cc-my-app-')
        assert len(name) <= 64
