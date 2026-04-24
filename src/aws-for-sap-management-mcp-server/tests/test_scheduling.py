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
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def tools():
    """Create an SSMSAPSchedulingTools instance."""
    from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
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
        'awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools._ensure_scheduler_role',
        return_value='arn:aws:iam::123456789012:role/EventBridgeSchedulerSSMSAPRole',
    )


def _mock_consent():
    """Return a patch for request_consent in scheduling tools."""
    return patch(
        'awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.request_consent',
        new_callable=AsyncMock,
    )


class TestScheduleConfigChecks:
    """Tests for schedule_config_checks tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test scheduling config checks."""
        with _mock_ensure_role(), _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_client_error(self, mock_get_client, tools, ctx):
        """Test scheduling config checks handles ClientError."""
        with _mock_ensure_role(), _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test scheduling application start."""
        with _mock_ensure_role(), _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_with_start_end_dates(self, mock_get_client, tools, ctx):
        """Test scheduling with start and end dates."""
        with _mock_ensure_role(), _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test scheduling application stop."""
        with _mock_ensure_role(), _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_with_ec2_shutdown(self, mock_get_client, tools, ctx):
        """Test scheduling stop with EC2 shutdown."""
        with _mock_ensure_role(), _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_exclude_disabled(self, mock_get_client, tools, ctx):
        """Test listing schedules excluding disabled ones."""
        mock_scheduler = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [{'Schedules': [{'Name': 'sched-1'}]}]
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_filters_by_application_id(self, mock_get_client, tools, ctx):
        """Test that schedules are filtered by application ID."""
        mock_scheduler = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [{'Schedules': [{'Name': 'sched-1'}]}]
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_error(self, mock_get_client, tools, ctx):
        """Test listing schedules handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.list_app_schedules(ctx, application_id='app-1')

        assert result.application_id == 'app-1'
        assert result.total_schedules == 0


class TestDeleteSchedule:
    """Tests for delete_schedule tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test deleting a schedule."""
        with _mock_consent():
            mock_scheduler = MagicMock()
            mock_get_client.return_value = mock_scheduler

            result = await tools.delete_schedule(ctx, schedule_name='sched-1')

            assert result.status == 'success'
            mock_scheduler.delete_schedule.assert_called_once_with(Name='sched-1')

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_not_found(self, mock_get_client, tools, ctx):
        """Test deleting a non-existent schedule."""
        with _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_enable(self, mock_get_client, tools, ctx):
        """Test enabling a schedule."""
        with _mock_consent():
            mock_scheduler = MagicMock()
            mock_scheduler.get_schedule.return_value = {
                'State': 'DISABLED',
                'ScheduleExpression': 'rate(1 day)',
                'Target': {'Arn': 'arn:test', 'Input': '{}'},
                'FlexibleTimeWindow': {'Mode': 'OFF'},
            }
            mock_get_client.return_value = mock_scheduler

            result = await tools.update_schedule_state(ctx, schedule_name='sched-1', enabled=True)

            assert result.status == 'success'
            assert result.previous_state == 'DISABLED'
            assert result.new_state == 'ENABLED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_already_in_desired_state(self, mock_get_client, tools, ctx):
        """Test updating when already in desired state."""
        with _mock_consent():
            mock_scheduler = MagicMock()
            mock_scheduler.get_schedule.return_value = {
                'State': 'ENABLED',
                'ScheduleExpression': 'rate(1 day)',
                'Target': {'Arn': 'arn:test', 'Input': '{}'},
                'FlexibleTimeWindow': {'Mode': 'OFF'},
            }
            mock_get_client.return_value = mock_scheduler

            result = await tools.update_schedule_state(ctx, schedule_name='sched-1', enabled=True)

            assert result.status == 'no_change'
            mock_scheduler.update_schedule.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_client_error(self, mock_get_client, tools, ctx):
        """Test updating schedule state handles ClientError."""
        with _mock_consent():
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
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
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
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

    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    def test_role_exists(self, mock_get_client):
        """Test when role already exists."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
            _ensure_scheduler_role,
        )

        mock_iam = MagicMock()
        mock_iam.get_role.return_value = {
            'Role': {'Arn': 'arn:aws:iam::123:role/EventBridgeSchedulerSSMSAPRole'}
        }
        mock_get_client.return_value = mock_iam

        result = _ensure_scheduler_role()

        assert 'EventBridgeSchedulerSSMSAPRole' in result

    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    def test_role_created(self, mock_get_client):
        """Test creating the role when it doesn't exist."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
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
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
            _determine_operation_type,
        )

        assert (
            _determine_operation_type('arn:aws:scheduler:::aws-sdk:ssmsap:startApplication')
            == 'Start Application'
        )
        assert (
            _determine_operation_type('arn:aws:scheduler:::aws-sdk:ssmsap:stopApplication')
            == 'Stop Application'
        )
        assert (
            _determine_operation_type(
                'arn:aws:scheduler:::aws-sdk:ssmsap:startConfigurationChecks'
            )
            == 'Configuration Checks'
        )
        assert _determine_operation_type('arn:unknown') == 'Unknown'

    def test_generate_schedule_name(self):
        """Test _generate_schedule_name produces valid names."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
            _generate_schedule_name,
        )

        name = _generate_schedule_name('ssmsap-cc-', 'my-app')
        assert name.startswith('ssmsap-cc-my-app-')
        assert len(name) <= 64


class TestSchedulingRequestConsent:
    """Tests for request_consent in scheduling tools."""

    @pytest.mark.asyncio
    async def test_consent_approved(self):
        """Test request_consent when user approves."""
        from awslabs.aws_for_sap_management_mcp_server.common import request_consent

        mock_ctx = MagicMock()
        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = True
        mock_ctx.elicit = AsyncMock(return_value=mock_result)

        await request_consent('Test op', 'I acknowledge', mock_ctx)

    @pytest.mark.asyncio
    async def test_consent_rejected(self):
        """Test request_consent when user rejects."""
        from awslabs.aws_for_sap_management_mcp_server.common import request_consent

        mock_ctx = MagicMock()
        mock_result = MagicMock()
        mock_result.action = 'reject'
        mock_result.data.acknowledge = False
        mock_ctx.elicit = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match='User rejected'):
            await request_consent('Test op', 'I acknowledge', mock_ctx)

    @pytest.mark.asyncio
    async def test_consent_unchecked(self):
        """Test request_consent when user accepts but doesn't check acknowledge."""
        from awslabs.aws_for_sap_management_mcp_server.common import request_consent

        mock_ctx = MagicMock()
        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = False
        mock_ctx.elicit = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match='User rejected'):
            await request_consent('Test op', 'I acknowledge', mock_ctx)

    @pytest.mark.asyncio
    async def test_consent_no_elicitation_support(self):
        """Test request_consent when client doesn't support elicitation."""
        from awslabs.aws_for_sap_management_mcp_server.common import request_consent
        from mcp.shared.exceptions import McpError
        from mcp.types import METHOD_NOT_FOUND, ErrorData

        mock_ctx = MagicMock()
        mock_ctx.elicit = AsyncMock(
            side_effect=McpError(ErrorData(code=METHOD_NOT_FOUND, message='Not supported'))
        )

        with pytest.raises(ValueError, match='does not support elicitation'):
            await request_consent('Test op', 'I acknowledge', mock_ctx)

    @pytest.mark.asyncio
    async def test_consent_other_mcp_error(self):
        """Test request_consent re-raises non-METHOD_NOT_FOUND McpError."""
        from awslabs.aws_for_sap_management_mcp_server.common import request_consent
        from mcp.shared.exceptions import McpError
        from mcp.types import ErrorData

        mock_ctx = MagicMock()
        mock_ctx.elicit = AsyncMock(
            side_effect=McpError(ErrorData(code=-32000, message='Other error'))
        )

        with pytest.raises(McpError):
            await request_consent('Test op', 'I acknowledge', mock_ctx)


class TestSchedulingRejectionPaths:
    """Tests for rejection paths in scheduling tools."""

    @pytest.mark.asyncio
    async def test_schedule_config_checks_rejected(self, tools, ctx):
        """Test schedule_config_checks when user rejects."""
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.request_consent',
            new_callable=AsyncMock,
            side_effect=ValueError('User rejected the operation.'),
        ):
            result = await tools.schedule_config_checks(
                ctx,
                application_id='app-1',
                schedule_expression='rate(7 days)',
            )
            assert result.status == 'error'
            assert 'User rejected' in result.message

    @pytest.mark.asyncio
    async def test_schedule_start_rejected(self, tools, ctx):
        """Test schedule_start_application when user rejects."""
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.request_consent',
            new_callable=AsyncMock,
            side_effect=ValueError('User rejected the operation.'),
        ):
            result = await tools.schedule_start_application(
                ctx,
                application_id='app-1',
                schedule_expression='rate(1 day)',
            )
            assert result.status == 'error'
            assert 'User rejected' in result.message

    @pytest.mark.asyncio
    async def test_schedule_stop_rejected(self, tools, ctx):
        """Test schedule_stop_application when user rejects."""
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.request_consent',
            new_callable=AsyncMock,
            side_effect=ValueError('User rejected the operation.'),
        ):
            result = await tools.schedule_stop_application(
                ctx,
                application_id='app-1',
                schedule_expression='rate(1 day)',
            )
            assert result.status == 'error'
            assert 'User rejected' in result.message

    @pytest.mark.asyncio
    async def test_delete_schedule_rejected(self, tools, ctx):
        """Test delete_schedule when user rejects."""
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.request_consent',
            new_callable=AsyncMock,
            side_effect=ValueError('User rejected the operation.'),
        ):
            result = await tools.delete_schedule(ctx, schedule_name='sched-1')
            assert result.status == 'error'
            assert 'User rejected' in result.message

    @pytest.mark.asyncio
    async def test_update_schedule_state_rejected(self, tools, ctx):
        """Test update_schedule_state when user rejects."""
        with patch(
            'awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.request_consent',
            new_callable=AsyncMock,
            side_effect=ValueError('User rejected the operation.'),
        ):
            result = await tools.update_schedule_state(
                ctx,
                schedule_name='sched-1',
                enabled=True,
            )
            assert result.status == 'error'
            assert 'User rejected' in result.message


class TestEnsureSchedulerRoleEdgeCases:
    """Tests for _ensure_scheduler_role edge cases."""

    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    def test_role_check_other_client_error(self, mock_get_client):
        """Test when get_role fails with non-NoSuchEntity error."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
            _ensure_scheduler_role,
        )

        mock_iam = MagicMock()
        mock_iam.get_role.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'No access'}},
            'GetRole',
        )
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}

        def client_router(service, **kwargs):
            if service == 'sts':
                return mock_sts
            return mock_iam

        mock_get_client.side_effect = client_router

        result = _ensure_scheduler_role()
        assert 'EventBridgeSchedulerSSMSAPRole' in result

    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    def test_role_create_already_exists(self, mock_get_client):
        """Test when create_role fails with EntityAlreadyExists."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
            _ensure_scheduler_role,
        )

        mock_iam = MagicMock()
        mock_iam.get_role.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchEntity', 'Message': 'Not found'}},
            'GetRole',
        )
        mock_iam.create_role.side_effect = ClientError(
            {'Error': {'Code': 'EntityAlreadyExists', 'Message': 'Already exists'}},
            'CreateRole',
        )
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}

        def client_router(service, **kwargs):
            if service == 'sts':
                return mock_sts
            return mock_iam

        mock_get_client.side_effect = client_router

        result = _ensure_scheduler_role()
        assert 'EventBridgeSchedulerSSMSAPRole' in result

    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    def test_iam_client_creation_fails(self, mock_get_client):
        """Test when IAM client creation fails."""
        from awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools import (
            _ensure_scheduler_role,
        )

        mock_get_client.side_effect = Exception('Cannot create IAM client')

        with pytest.raises(Exception, match='Cannot create IAM client'):
            _ensure_scheduler_role()


class TestCreateScheduleEdgeCases:
    """Tests for _create_schedule edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_unknown_operation(self, mock_get_client, tools, ctx):
        """Test _create_schedule with unknown operation."""
        result = await tools._create_schedule(
            operation='unknown_op',
            application_id='app-1',
            schedule_expression='rate(1 day)',
            schedule_name='test-sched',
            description='Test',
        )
        assert result.status == 'error'
        assert 'Unknown operation' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_generic_exception(self, mock_get_client, tools, ctx):
        """Test _create_schedule with generic exception."""
        with _mock_ensure_role():
            mock_get_client.side_effect = Exception('Connection timeout')
            result = await tools._create_schedule(
                operation='start_application',
                application_id='app-1',
                schedule_expression='rate(1 day)',
                schedule_name='test-sched',
                description='Test',
            )
            assert result.status == 'error'
            assert 'Connection timeout' in result.message


class TestUpdateScheduleDisable:
    """Tests for update_schedule_state disable path."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_disable(self, mock_get_client, tools, ctx):
        """Test disabling a schedule."""
        with _mock_consent():
            mock_scheduler = MagicMock()
            mock_scheduler.get_schedule.return_value = {
                'State': 'ENABLED',
                'ScheduleExpression': 'rate(1 day)',
                'Target': {'Arn': 'arn:test', 'Input': '{}'},
                'FlexibleTimeWindow': {'Mode': 'OFF'},
            }
            mock_get_client.return_value = mock_scheduler

            result = await tools.update_schedule_state(ctx, schedule_name='sched-1', enabled=False)

            assert result.status == 'success'
            assert result.previous_state == 'ENABLED'
            assert result.new_state == 'DISABLED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_generic_exception(self, mock_get_client, tools, ctx):
        """Test update_schedule_state with generic exception."""
        with _mock_consent():
            mock_get_client.side_effect = Exception('Connection error')

            result = await tools.update_schedule_state(ctx, schedule_name='sched-1', enabled=True)

            assert result.status == 'error'
            assert 'Connection error' in result.message


class TestDeleteScheduleGenericError:
    """Tests for delete_schedule generic error path."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_generic_exception(self, mock_get_client, tools, ctx):
        """Test delete_schedule with generic exception."""
        with _mock_consent():
            mock_get_client.side_effect = Exception('Connection error')

            result = await tools.delete_schedule(ctx, schedule_name='sched-1')

            assert result.status == 'error'
            assert 'Connection error' in result.message


class TestGetScheduleDetailsEdgeCases:
    """Tests for get_schedule_details edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_generic_exception(self, mock_get_client, tools, ctx):
        """Test get_schedule_details with generic exception."""
        mock_get_client.side_effect = Exception('Connection error')

        result = await tools.get_schedule_details(ctx, schedule_name='sched-1')

        assert result['status'] == 'error'
        assert 'Connection error' in result['message']

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_other_client_error(self, mock_get_client, tools, ctx):
        """Test get_schedule_details with non-ResourceNotFound ClientError."""
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'No access'}},
            'GetSchedule',
        )
        mock_get_client.return_value = mock_scheduler

        result = await tools.get_schedule_details(ctx, schedule_name='sched-1')

        assert result['status'] == 'error'
        assert 'AccessDenied' in result['message']


class TestListAppSchedulesEdgeCases:
    """Tests for list_app_schedules edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_for_sap_management_mcp_server.ssm_sap_scheduling.tools.get_aws_client')
    async def test_invalid_json_input(self, mock_get_client, tools, ctx):
        """Test list_app_schedules when schedule has invalid JSON input."""
        mock_scheduler = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [{'Schedules': [{'Name': 'sched-1'}]}]
        mock_scheduler.get_paginator.return_value = paginator
        mock_scheduler.get_schedule.return_value = {
            'Arn': 'arn:sched-1',
            'State': 'ENABLED',
            'ScheduleExpression': 'rate(1 day)',
            'Target': {
                'Arn': 'arn:aws:scheduler:::aws-sdk:ssmsap:startApplication',
                'Input': 'not-valid-json',
            },
        }
        mock_get_client.return_value = mock_scheduler

        result = await tools.list_app_schedules(ctx, application_id='app-1')

        assert result.total_schedules == 0
