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

"""Tests for SSM for SAP application tools."""

import pytest
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_consent():
    """Return a patch for request_consent in applications tools."""
    return patch(
        'awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.request_consent',
        new_callable=AsyncMock,
    )


def _hana_app_response():
    """Return a standard HANA app get_application response with empty associations."""
    return {'Application': {'Id': 'app-1', 'Type': 'HANA', 'AssociatedApplicationArns': []}}


@pytest.fixture
def tools():
    """Create an SSMSAPApplicationTools instance."""
    from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools import (
        SSMSAPApplicationTools,
    )

    return SSMSAPApplicationTools()


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    return MagicMock()


class TestListApplications:
    """Tests for list_applications tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_list_applications_success(self, mock_get_client, tools, ctx):
        """Test listing applications returns correct results."""
        mock_client = MagicMock()
        mock_client.list_applications.return_value = {
            'Applications': [
                {'Id': 'app-1', 'Type': 'HANA', 'Arn': 'arn:aws:ssm-sap:us-east-1:123:app/app-1'},
                {'Id': 'app-2', 'Type': 'SAP_ABAP'},
            ]
        }
        mock_get_client.return_value = mock_client

        result = await tools.list_applications(ctx)

        assert len(result.applications) == 2
        assert result.applications[0].id == 'app-1'
        assert result.applications[0].type == 'HANA'
        assert result.applications[1].id == 'app-2'
        assert 'Found 2' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_list_applications_pagination(self, mock_get_client, tools, ctx):
        """Test listing applications handles pagination."""
        mock_client = MagicMock()
        mock_client.list_applications.side_effect = [
            {
                'Applications': [{'Id': 'app-1', 'Type': 'HANA'}],
                'NextToken': 'token1',
            },
            {
                'Applications': [{'Id': 'app-2', 'Type': 'SAP_ABAP'}],
            },
        ]
        mock_get_client.return_value = mock_client

        result = await tools.list_applications(ctx)

        assert len(result.applications) == 2
        assert mock_client.list_applications.call_count == 2

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_list_applications_empty(self, mock_get_client, tools, ctx):
        """Test listing applications when none exist."""
        mock_client = MagicMock()
        mock_client.list_applications.return_value = {'Applications': []}
        mock_get_client.return_value = mock_client

        result = await tools.list_applications(ctx)

        assert len(result.applications) == 0
        assert 'Found 0' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_list_applications_error(self, mock_get_client, tools, ctx):
        """Test listing applications handles errors."""
        mock_get_client.side_effect = Exception('Connection error')

        result = await tools.list_applications(ctx)

        assert 'Error' in result.message


class TestGetApplication:
    """Tests for get_application tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_application_success(self, mock_get_client, tools, ctx):
        """Test getting application details."""
        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Arn': 'arn:aws:ssm-sap:us-east-1:123:app/app-1',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {
            'Components': [{'ComponentId': 'comp-1'}]
        }
        mock_client.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
            }
        }
        mock_get_client.return_value = mock_client

        result = await tools.get_application(ctx, application_id='app-1')

        assert result.id == 'app-1'
        assert result.type == 'HANA'
        assert result.status == 'ACTIVATED'
        assert result.components is not None
        assert len(result.components) == 1

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_application_client_error(self, mock_get_client, tools, ctx):
        """Test getting application handles ClientError."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetApplication',
        )
        mock_get_client.return_value = mock_client

        result = await tools.get_application(ctx, application_id='nonexistent')

        assert result.status == 'ERROR'
        assert 'ResourceNotFoundException' in result.status_message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_application_component_error(self, mock_get_client, tools, ctx):
        """Test getting application handles component listing errors gracefully."""
        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1',
                'Type': 'HANA',
                'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.side_effect = Exception('Component error')
        mock_get_client.return_value = mock_client

        result = await tools.get_application(ctx, application_id='app-1')

        assert result.id == 'app-1'
        assert result.status == 'ACTIVATED'


class TestGetComponent:
    """Tests for get_component tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_component_success(self, mock_get_client, tools, ctx):
        """Test getting component details."""
        mock_client = MagicMock()
        mock_client.get_component.return_value = {
            'Component': {
                'ComponentType': 'HANA',
                'Status': 'ACTIVATED',
                'Sid': 'HDB',
                'Hosts': [
                    {
                        'HostName': 'host1',
                        'HostIp': '10.0.0.1',
                        'HostRole': 'LEADER',
                        'EC2InstanceId': 'i-abc123',
                    }
                ],
            }
        }
        mock_get_client.return_value = mock_client

        result = await tools.get_component(ctx, application_id='app-1', component_id='comp-1')

        assert result.component_type == 'HANA'
        assert result.status == 'ACTIVATED'
        assert result.sid == 'HDB'
        assert len(result.hosts) == 1
        assert result.hosts[0]['hostname'] == 'host1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_component_error(self, mock_get_client, tools, ctx):
        """Test getting component handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.get_component(ctx, application_id='app-1', component_id='comp-1')

        assert result.status == 'ERROR'


class TestGetOperation:
    """Tests for get_operation tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_operation_success(self, mock_get_client, tools, ctx):
        """Test getting operation details."""
        mock_client = MagicMock()
        mock_client.get_operation.return_value = {
            'Operation': {
                'Id': 'op-1',
                'Type': 'START_APPLICATION',
                'Status': 'SUCCESS',
            }
        }
        mock_get_client.return_value = mock_client

        result = await tools.get_operation(ctx, operation_id='op-1')

        assert result.id == 'op-1'
        assert result.status == 'SUCCESS'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_operation_error(self, mock_get_client, tools, ctx):
        """Test getting operation handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.get_operation(ctx, operation_id='op-1')

        assert result.status == 'ERROR'


class TestRegisterApplication:
    """Tests for register_application tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_register_hana_success(self, mock_get_client, tools, ctx):
        """Test registering a HANA application."""
        mock_client = MagicMock()
        mock_client.register_application.return_value = {
            'ApplicationId': 'app-1',
            'ApplicationArn': 'arn:aws:ssm-sap:us-east-1:123:app/app-1',
            'OperationId': 'op-1',
        }
        mock_get_client.return_value = mock_client

        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='HANA',
            sid='HDB',
            sap_instance_number='00',
            instances=['i-abc123'],
        )

        assert result.status == 'success'
        assert result.operation_id == 'op-1'

    @pytest.mark.asyncio
    async def test_register_invalid_type(self, tools, ctx):
        """Test registering with invalid application type."""
        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='INVALID',
            sid='HDB',
            sap_instance_number='00',
            instances=['i-abc123'],
        )

        assert result.status == 'error'
        assert 'HANA' in result.message

    @pytest.mark.asyncio
    async def test_register_abap_without_database_arn(self, tools, ctx):
        """Test registering SAP_ABAP without database_arn fails."""
        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='SAP_ABAP',
            sid='S4H',
            sap_instance_number='00',
            instances=['i-abc123'],
        )

        assert result.status == 'error'
        assert 'database_arn' in result.message

    @pytest.mark.asyncio
    async def test_register_invalid_sid(self, tools, ctx):
        """Test registering with invalid SID length."""
        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='HANA',
            sid='AB',
            sap_instance_number='00',
            instances=['i-abc123'],
        )

        assert result.status == 'error'
        assert 'SID' in result.message

    @pytest.mark.asyncio
    async def test_register_invalid_instance_number(self, tools, ctx):
        """Test registering with invalid instance number."""
        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='HANA',
            sid='HDB',
            sap_instance_number='ABC',
            instances=['i-abc123'],
        )

        assert result.status == 'error'
        assert 'sap_instance_number' in result.message

    @pytest.mark.asyncio
    async def test_register_empty_instances(self, tools, ctx):
        """Test registering with empty instances list."""
        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='HANA',
            sid='HDB',
            sap_instance_number='00',
            instances=[],
        )

        assert result.status == 'error'
        assert 'instance' in result.message.lower()

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_register_client_error(self, mock_get_client, tools, ctx):
        """Test registering handles ClientError."""
        mock_client = MagicMock()
        mock_client.register_application.side_effect = ClientError(
            {'Error': {'Code': 'ConflictException', 'Message': 'Already exists'}},
            'RegisterApplication',
        )
        mock_get_client.return_value = mock_client

        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='HANA',
            sid='HDB',
            sap_instance_number='00',
            instances=['i-abc123'],
        )

        assert result.status == 'error'
        assert 'ConflictException' in result.message


class TestStartStopApplication:
    """Tests for start_application and stop_application tools."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_start_application_success(self, mock_get_client, tools, ctx):
        """Test starting an application."""
        with _mock_consent():
            mock_client = MagicMock()
            mock_client.start_application.return_value = {'OperationId': 'op-start-1'}
            mock_get_client.return_value = mock_client

            result = await tools.start_application(ctx, application_id='app-1')

            assert result.status == 'success'
            assert result.operation_id == 'op-start-1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_start_application_error(self, mock_get_client, tools, ctx):
        """Test starting an application handles errors."""
        with _mock_consent():
            mock_get_client.side_effect = Exception('API error')

            result = await tools.start_application(ctx, application_id='app-1')

            assert result.status == 'error'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_stop_application_success(self, mock_get_client, tools, ctx):
        """Test stopping an application."""
        with _mock_consent():
            mock_client = MagicMock()
            mock_client.get_application.return_value = _hana_app_response()
            mock_client.stop_application.return_value = {'OperationId': 'op-stop-1'}
            mock_get_client.return_value = mock_client

            result = await tools.stop_application(ctx, application_id='app-1')

            assert result.status == 'success'
            assert result.operation_id == 'op-stop-1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_stop_application_with_ec2_shutdown(self, mock_get_client, tools, ctx):
        """Test stopping with EC2 shutdown flag."""
        with _mock_consent():
            mock_client = MagicMock()
            mock_client.get_application.return_value = _hana_app_response()
            mock_client.stop_application.return_value = {'OperationId': 'op-stop-2'}
            mock_get_client.return_value = mock_client

            result = await tools.stop_application(
                ctx, application_id='app-1', include_ec2_instance_shutdown=True
            )

            assert result.status == 'success'
            call_args = mock_client.stop_application.call_args[1]
            assert call_args['IncludeEc2InstanceShutdown'] is True

    @pytest.mark.asyncio
    async def test_stop_application_invalid_connected_entity(self, tools, ctx):
        """Test stopping with invalid connected entity."""
        result = await tools.stop_application(
            ctx, application_id='app-1', stop_connected_entity='INVALID'
        )

        assert result.status == 'error'
        assert 'INVALID' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_stop_application_client_error(self, mock_get_client, tools, ctx):
        """Test stopping handles ClientError."""
        with _mock_consent():
            mock_client = MagicMock()
            mock_client.get_application.return_value = _hana_app_response()
            mock_client.stop_application.side_effect = ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'Invalid state'}},
                'StopApplication',
            )
            mock_get_client.return_value = mock_client

            result = await tools.stop_application(ctx, application_id='app-1')

            assert result.status == 'error'
            assert 'ValidationException' in result.message


class TestRequestConsent:
    """Tests for request_consent function."""

    @pytest.mark.asyncio
    async def test_consent_approved(self):
        """Test request_consent when user approves."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools import (
            request_consent,
        )
        mock_ctx = MagicMock()
        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = True
        mock_ctx.elicit = AsyncMock(return_value=mock_result)

        # Should not raise
        await request_consent('Test op', 'I acknowledge', mock_ctx)

    @pytest.mark.asyncio
    async def test_consent_rejected(self):
        """Test request_consent when user rejects."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools import (
            request_consent,
        )
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools import (
            request_consent,
        )
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools import (
            request_consent,
        )
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
        from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools import (
            request_consent,
        )
        from mcp.shared.exceptions import McpError
        from mcp.types import ErrorData

        mock_ctx = MagicMock()
        mock_ctx.elicit = AsyncMock(
            side_effect=McpError(ErrorData(code=-32000, message='Other error'))
        )

        with pytest.raises(McpError):
            await request_consent('Test op', 'I acknowledge', mock_ctx)


class TestStartApplicationConsent:
    """Tests for start_application consent paths."""

    @pytest.mark.asyncio
    async def test_start_rejected(self, tools, ctx):
        """Test start_application when user rejects consent."""
        with patch(
            'awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.request_consent',
            new_callable=AsyncMock,
            side_effect=ValueError('User rejected the operation.'),
        ):
            result = await tools.start_application(ctx, application_id='app-1')
            assert result.status == 'error'
            assert 'User rejected' in result.message


class TestStopApplicationCascade:
    """Tests for stop_application cascade stop with associated NW apps."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_cascade_stop_with_nw_apps(self, mock_get_client, tools, ctx):
        """Test stop with associated NW apps and cascade enabled."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_client.stop_application.side_effect = [
            {'OperationId': 'op-nw-stop'},
            {'OperationId': 'op-hana-stop'},
        ]
        mock_client.get_operation.return_value = {
            'Operation': {'Status': 'SUCCESS', 'StartTime': '2026-01-01', 'EndTime': '2026-01-01'},
        }
        mock_get_client.return_value = mock_client

        # Mock elicitation for cascade dialog
        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = True
        mock_result.data.stop_associated_apps_first = True
        ctx.elicit = AsyncMock(return_value=mock_result)

        with patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.asyncio.sleep', new_callable=AsyncMock):
            result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'success'
        assert result.associated_app_stop_details is not None
        assert len(result.associated_app_stop_details) == 1
        assert result.associated_app_stop_details[0].application_id == 'nw-1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_cascade_skip(self, mock_get_client, tools, ctx):
        """Test stop with NW apps but user skips cascade."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_client.stop_application.return_value = {'OperationId': 'op-hana-stop'}
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = True
        mock_result.data.stop_associated_apps_first = False
        ctx.elicit = AsyncMock(return_value=mock_result)

        result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'success'
        assert result.associated_app_stop_details is None

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_cascade_user_rejects(self, mock_get_client, tools, ctx):
        """Test stop with NW apps but user rejects."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.action = 'reject'
        mock_result.data.acknowledge = False
        ctx.elicit = AsyncMock(return_value=mock_result)

        result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'error'
        assert 'rejected' in result.message.lower()

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_get_application_fails(self, mock_get_client, tools, ctx):
        """Test stop when get_application fails."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = Exception('Access denied')
        mock_get_client.return_value = mock_client

        result = await tools.stop_application(ctx, application_id='app-1')

        assert result.status == 'error'
        assert 'Failed to retrieve' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_nw_stop_client_error(self, mock_get_client, tools, ctx):
        """Test cascade stop when NW stop raises ClientError."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_client.stop_application.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Cannot stop'}},
            'StopApplication',
        )
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = True
        mock_result.data.stop_associated_apps_first = True
        ctx.elicit = AsyncMock(return_value=mock_result)

        result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'error'
        assert result.associated_app_stop_details is not None

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_no_elicitation_support_with_nw_apps(self, mock_get_client, tools, ctx):
        """Test stop with NW apps when client doesn't support elicitation."""
        from mcp.shared.exceptions import McpError
        from mcp.types import METHOD_NOT_FOUND, ErrorData

        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_get_client.return_value = mock_client

        ctx.elicit = AsyncMock(
            side_effect=McpError(ErrorData(code=METHOD_NOT_FOUND, message='Not supported'))
        )

        result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'error'
        assert 'does not support elicitation' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_nw_stop_operation_error(self, mock_get_client, tools, ctx):
        """Test cascade stop when NW stop operation returns ERROR."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_client.stop_application.return_value = {'OperationId': 'op-nw-stop'}
        mock_client.get_operation.return_value = {
            'Operation': {'Status': 'ERROR', 'StatusMessage': 'Stop failed', 'StartTime': '', 'EndTime': ''},
        }
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = True
        mock_result.data.stop_associated_apps_first = True
        ctx.elicit = AsyncMock(return_value=mock_result)

        with patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.asyncio.sleep', new_callable=AsyncMock):
            result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'error'
        assert 'Failed to stop' in result.message


class TestGetApplicationEdgeCases:
    """Tests for get_application edge cases — individual component errors and generic exceptions."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_individual_get_component_error(self, mock_get_client, tools, ctx):
        """Test get_application when get_component fails for one component (lines 201-202)."""
        mock_client = MagicMock()
        mock_client.get_application.return_value = {
            'Application': {
                'Id': 'app-1', 'Type': 'HANA', 'Status': 'ACTIVATED',
                'DiscoveryStatus': 'SUCCESS',
            }
        }
        mock_client.list_components.return_value = {
            'Components': [{'ComponentId': 'comp-ok'}, {'ComponentId': 'comp-bad'}]
        }
        mock_client.get_component.side_effect = [
            {'Component': {'ComponentType': 'HANA', 'Status': 'ACTIVATED', 'Sid': 'HDB'}},
            Exception('get_component failed for comp-bad'),
        ]
        mock_get_client.return_value = mock_client

        result = await tools.get_application(ctx, application_id='app-1')

        assert result.id == 'app-1'
        assert result.status == 'ACTIVATED'
        assert len(result.components) == 2
        assert result.components[1].get('error') == 'get_component failed for comp-bad'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_generic_exception(self, mock_get_client, tools, ctx):
        """Test get_application generic exception path (lines 229-231)."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = RuntimeError('Unexpected failure')
        mock_get_client.return_value = mock_client

        result = await tools.get_application(ctx, application_id='app-1')

        assert result.status == 'ERROR'
        assert 'Unexpected failure' in result.status_message


class TestRegisterApplicationOptionalParams:
    """Tests for register_application with optional credentials, tags, database_arn."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_with_credentials_and_tags(self, mock_get_client, tools, ctx):
        """Test register_application passes credentials and tags (lines 456, 460)."""
        mock_client = MagicMock()
        mock_client.register_application.return_value = {
            'ApplicationId': 'app-1', 'OperationId': 'op-1',
        }
        mock_get_client.return_value = mock_client

        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='HANA',
            sid='HDB',
            sap_instance_number='00',
            instances=['i-abc123'],
            credentials=[{'CredentialType': 'ADMIN', 'DatabaseName': 'HDB/SYSTEMDB', 'SecretId': 'arn:secret'}],
            tags={'env': 'prod'},
        )

        assert result.status == 'success'
        call_kwargs = mock_client.register_application.call_args[1]
        assert call_kwargs['Credentials'] == [{'CredentialType': 'ADMIN', 'DatabaseName': 'HDB/SYSTEMDB', 'SecretId': 'arn:secret'}]
        assert call_kwargs['Tags'] == {'env': 'prod'}

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_abap_with_database_arn(self, mock_get_client, tools, ctx):
        """Test register_application SAP_ABAP with database_arn (line 458)."""
        mock_client = MagicMock()
        mock_client.register_application.return_value = {
            'ApplicationId': 'nw-1', 'OperationId': 'op-2',
        }
        mock_get_client.return_value = mock_client

        result = await tools.register_application(
            ctx,
            application_id='nw-1',
            application_type='SAP_ABAP',
            sid='S4H',
            sap_instance_number='01',
            instances=['i-def456'],
            database_arn='arn:aws:ssm-sap:us-east-1:123:HANA/hana-db',
        )

        assert result.status == 'success'
        call_kwargs = mock_client.register_application.call_args[1]
        assert call_kwargs['DatabaseArn'] == 'arn:aws:ssm-sap:us-east-1:123:HANA/hana-db'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_register_generic_exception(self, mock_get_client, tools, ctx):
        """Test register_application generic exception (lines 476-478)."""
        mock_client = MagicMock()
        mock_client.register_application.side_effect = RuntimeError('Unexpected')
        mock_get_client.return_value = mock_client

        result = await tools.register_application(
            ctx,
            application_id='app-1',
            application_type='HANA',
            sid='HDB',
            sap_instance_number='00',
            instances=['i-abc123'],
        )

        assert result.status == 'error'
        assert 'Unexpected' in result.message


class TestStartApplicationClientError:
    """Tests for start_application ClientError path."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_start_client_error(self, mock_get_client, tools, ctx):
        """Test start_application ClientError (line 532)."""
        with _mock_consent():
            mock_client = MagicMock()
            mock_client.start_application.side_effect = ClientError(
                {'Error': {'Code': 'ValidationException', 'Message': 'App not in stoppable state'}},
                'StartApplication',
            )
            mock_get_client.return_value = mock_client

            result = await tools.start_application(ctx, application_id='app-1')

            assert result.status == 'error'
            assert 'ValidationException' in result.message


class TestStopApplicationEdgeCases:
    """Tests for stop_application edge cases."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_associated_app_verification_error(self, mock_get_client, tools, ctx):
        """Test stop when verifying associated app raises exception (lines 611-612)."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-bad'],
            }},
            Exception('Cannot verify associated app'),  # get_application for nw-bad fails
        ]
        mock_client.stop_application.return_value = {'OperationId': 'op-stop'}
        mock_get_client.return_value = mock_client

        # Since associated app verification fails, nw_apps list stays empty -> standard consent
        with _mock_consent():
            result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'success'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_associated_arn_without_slash(self, mock_get_client, tools, ctx):
        """Test stop when associated ARN has no slash (line 604)."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['no-slash-arn'],
            }},
        ]
        mock_client.stop_application.return_value = {'OperationId': 'op-stop'}
        mock_get_client.return_value = mock_client

        with _mock_consent():
            result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'success'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_cascade_nw_stop_timeout(self, mock_get_client, tools, ctx):
        """Test cascade stop when NW stop operation times out (lines 735-741)."""
        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_client.stop_application.return_value = {'OperationId': 'op-nw-stop'}
        # get_operation always returns IN_PROGRESS (never completes)
        mock_client.get_operation.return_value = {
            'Operation': {'Status': 'IN_PROGRESS', 'StartTime': '', 'EndTime': ''},
        }
        mock_get_client.return_value = mock_client

        mock_result = MagicMock()
        mock_result.action = 'accept'
        mock_result.data.acknowledge = True
        mock_result.data.stop_associated_apps_first = True
        ctx.elicit = AsyncMock(return_value=mock_result)

        with patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.asyncio.sleep', new_callable=AsyncMock):
            result = await tools.stop_application(ctx, application_id='hana-1')

        assert result.status == 'error'
        assert 'Timed out' in result.message
        assert result.associated_app_stop_details is not None
        assert result.associated_app_stop_details[0].status == 'TIMED_OUT'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_stop_with_connected_entity_dbms(self, mock_get_client, tools, ctx):
        """Test stop_application with stop_connected_entity='DBMS' (line 767)."""
        with _mock_consent():
            mock_client = MagicMock()
            mock_client.get_application.return_value = _hana_app_response()
            mock_client.stop_application.return_value = {'OperationId': 'op-stop-dbms'}
            mock_get_client.return_value = mock_client

            result = await tools.stop_application(
                ctx, application_id='app-1', stop_connected_entity='DBMS'
            )

            assert result.status == 'success'
            call_kwargs = mock_client.stop_application.call_args[1]
            assert call_kwargs['StopConnectedEntity'] == 'DBMS'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_stop_generic_exception_during_final_stop(self, mock_get_client, tools, ctx):
        """Test stop_application generic exception during final stop call (lines 787-789)."""
        with _mock_consent():
            mock_client = MagicMock()
            mock_client.get_application.return_value = _hana_app_response()
            mock_client.stop_application.side_effect = RuntimeError('Unexpected stop error')
            mock_get_client.return_value = mock_client

            result = await tools.stop_application(ctx, application_id='app-1')

            assert result.status == 'error'
            assert 'Unexpected stop error' in result.message

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_cascade_elicitation_other_mcp_error(self, mock_get_client, tools, ctx):
        """Test stop with NW apps when elicitation raises non-METHOD_NOT_FOUND McpError (lines 674, 684-685)."""
        from mcp.shared.exceptions import McpError
        from mcp.types import ErrorData

        mock_client = MagicMock()
        mock_client.get_application.side_effect = [
            {'Application': {
                'Id': 'hana-1', 'Type': 'HANA',
                'AssociatedApplicationArns': ['arn:aws:ssm-sap:us-east-1:123:app/nw-1'],
            }},
            {'Application': {'Id': 'nw-1', 'Type': 'SAP_ABAP'}},
        ]
        mock_get_client.return_value = mock_client

        ctx.elicit = AsyncMock(
            side_effect=McpError(ErrorData(code=-32000, message='Internal error'))
        )

        with pytest.raises(McpError):
            await tools.stop_application(ctx, application_id='hana-1')
