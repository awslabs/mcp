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

"""Tests for SSM for SAP configuration check tools."""

import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.fixture
def tools():
    """Create an SSMSAPConfigCheckTools instance."""
    from awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools import (
        SSMSAPConfigCheckTools,
    )

    return SSMSAPConfigCheckTools()


@pytest.fixture
def ctx():
    """Create a mock MCP context."""
    return MagicMock()


class TestListConfigCheckDefinitions:
    """Tests for list_config_check_definitions tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test listing config check definitions."""
        mock_client = MagicMock()
        mock_client.list_configuration_check_definitions.return_value = {
            'ConfigurationChecks': [
                {'Id': 'CHECK_01', 'Name': 'HA Check', 'Description': 'High availability check'},
                {'Id': 'CHECK_02', 'Name': 'Backup Check'},
            ]
        }
        mock_get_client.return_value = mock_client

        result = await tools.list_config_check_definitions(ctx)

        assert len(result) == 2
        assert result[0].id == 'CHECK_01'
        assert result[0].name == 'HA Check'
        assert result[1].id == 'CHECK_02'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_error(self, mock_get_client, tools, ctx):
        """Test listing config check definitions handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.list_config_check_definitions(ctx)

        assert len(result) == 1
        assert result[0].id == 'ERROR'


class TestStartConfigChecks:
    """Tests for start_config_checks tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test starting config checks."""
        mock_client = MagicMock()
        mock_client.start_configuration_checks.return_value = {
            'ConfigurationCheckOperations': [{'OperationId': 'op-1'}]
        }
        mock_get_client.return_value = mock_client

        result = await tools.start_config_checks(
            ctx, application_id='app-1', check_ids=['CHECK_01']
        )

        assert result.status == 'success'
        assert result.operations is not None

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_client_error(self, mock_get_client, tools, ctx):
        """Test starting config checks handles ClientError."""
        mock_client = MagicMock()
        mock_client.start_configuration_checks.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid check ID'}},
            'StartConfigurationChecks',
        )
        mock_get_client.return_value = mock_client

        result = await tools.start_config_checks(
            ctx, application_id='app-1', check_ids=['INVALID']
        )

        assert result.status == 'error'
        assert 'ValidationException' in result.message


class TestGetConfigCheckSummary:
    """Tests for get_config_check_summary tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test getting config check summary."""
        mock_client = MagicMock()
        mock_client.list_configuration_check_operations.return_value = {
            'ConfigurationCheckOperations': [
                {
                    'ConfigurationCheckId': 'CHECK_01',
                    'OperationId': 'op-1',
                    'Status': 'COMPLETED',
                    'Result': 'PASS',
                },
                {
                    'ConfigurationCheckId': 'CHECK_02',
                    'OperationId': 'op-2',
                    'Status': 'COMPLETED',
                    'Result': 'FAIL',
                },
            ]
        }
        mock_get_client.return_value = mock_client

        result = await tools.get_config_check_summary(ctx, application_id='app-1')

        assert result.application_id == 'app-1'
        assert result.total_checks == 2
        assert result.by_status.get('COMPLETED') == 2
        assert result.by_result.get('PASS') == 1
        assert result.by_result.get('FAIL') == 1
        assert len(result.checks) == 2

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_error(self, mock_get_client, tools, ctx):
        """Test getting config check summary handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.get_config_check_summary(ctx, application_id='app-1')

        assert result.application_id == 'app-1'
        assert len(result.checks) == 1
        assert result.checks[0].check_id == 'ERROR'


class TestGetConfigCheckOperation:
    """Tests for get_config_check_operation tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test getting config check operation details."""
        mock_client = MagicMock()
        mock_client.get_configuration_check_operation.return_value = {
            'ConfigurationCheckOperation': {
                'OperationId': 'op-1',
                'Status': 'COMPLETED',
                'Result': 'PASS',
            }
        }
        mock_get_client.return_value = mock_client

        result = await tools.get_config_check_operation(ctx, operation_id='op-1')

        assert result['Status'] == 'COMPLETED'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_error(self, mock_get_client, tools, ctx):
        """Test getting config check operation handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.get_config_check_operation(ctx, operation_id='op-1')

        assert 'error' in result


class TestListSubCheckResults:
    """Tests for list_sub_check_results tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test listing sub-check results."""
        mock_client = MagicMock()
        mock_client.list_sub_check_results.return_value = {
            'SubCheckResults': [
                {'Id': 'sc-1', 'Name': 'Sub Check 1', 'Result': 'PASS'},
                {'Id': 'sc-2', 'Name': 'Sub Check 2', 'Result': 'FAIL', 'Description': 'Failed'},
            ]
        }
        mock_get_client.return_value = mock_client

        result = await tools.list_sub_check_results(ctx, operation_id='op-1')

        assert len(result) == 2
        assert result[0].id == 'sc-1'
        assert result[0].result == 'PASS'
        assert result[1].description == 'Failed'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_error(self, mock_get_client, tools, ctx):
        """Test listing sub-check results handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.list_sub_check_results(ctx, operation_id='op-1')

        assert len(result) == 1
        assert result[0].id == 'ERROR'


class TestListSubCheckRuleResults:
    """Tests for list_sub_check_rule_results tool."""

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_success(self, mock_get_client, tools, ctx):
        """Test listing sub-check rule results."""
        mock_client = MagicMock()
        mock_client.list_sub_check_rule_results.return_value = {
            'RuleResults': [
                {'RuleId': 'rule-1', 'Result': 'PASS'},
            ]
        }
        mock_get_client.return_value = mock_client

        result = await tools.list_sub_check_rule_results(ctx, subcheck_result_id='sc-1')

        assert len(result) == 1
        assert result[0]['RuleId'] == 'rule-1'

    @pytest.mark.asyncio
    @patch('awslabs.aws_systems_manager_for_sap_mcp_server.ssm_sap_config_checks.tools.get_aws_client')
    async def test_error(self, mock_get_client, tools, ctx):
        """Test listing sub-check rule results handles errors."""
        mock_get_client.side_effect = Exception('API error')

        result = await tools.list_sub_check_rule_results(ctx, subcheck_result_id='sc-1')

        assert len(result) == 1
        assert 'error' in result[0]
