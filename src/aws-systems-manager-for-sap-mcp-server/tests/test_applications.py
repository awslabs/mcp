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
from unittest.mock import MagicMock, patch


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
        mock_get_client.side_effect = Exception('API error')

        result = await tools.start_application(ctx, application_id='app-1')

        assert result.status == 'error'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_stop_application_success(self, mock_get_client, tools, ctx):
        """Test stopping an application."""
        mock_client = MagicMock()
        mock_client.stop_application.return_value = {'OperationId': 'op-stop-1'}
        mock_get_client.return_value = mock_client

        result = await tools.stop_application(ctx, application_id='app-1')

        assert result.status == 'success'
        assert result.operation_id == 'op-stop-1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_applications.tools.get_aws_client')
    async def test_stop_application_with_ec2_shutdown(self, mock_get_client, tools, ctx):
        """Test stopping with EC2 shutdown flag."""
        mock_client = MagicMock()
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
        mock_client = MagicMock()
        mock_client.stop_application.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid state'}},
            'StopApplication',
        )
        mock_get_client.return_value = mock_client

        result = await tools.stop_application(ctx, application_id='app-1')

        assert result.status == 'error'
        assert 'ValidationException' in result.message
