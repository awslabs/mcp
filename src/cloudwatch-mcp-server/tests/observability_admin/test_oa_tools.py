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

"""Tests for Observability Admin tools."""

import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.observability_admin.tools import ObservabilityAdminTools
from unittest.mock import AsyncMock, Mock, patch


@pytest_asyncio.fixture
async def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest_asyncio.fixture
async def oa_tools():
    """Create ObservabilityAdminTools instance."""
    return ObservabilityAdminTools()


class TestRegistration:
    """Test tool registration."""

    def test_all_tools_registered(self):
        """Test test_all_tools_registered."""
        tools = ObservabilityAdminTools()
        mock_mcp = Mock()
        tools.register(mock_mcp)

        assert mock_mcp.tool.call_count == 12
        tool_names = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
        expected = [
            'get_telemetry_evaluation_status',
            'start_telemetry_evaluation',
            'stop_telemetry_evaluation',
            'get_telemetry_evaluation_status_for_organization',
            'start_telemetry_evaluation_for_organization',
            'stop_telemetry_evaluation_for_organization',
            'list_resource_telemetry',
            'list_telemetry_rules',
            'get_telemetry_rule',
            'list_resource_telemetry_for_organization',
            'list_telemetry_rules_for_organization',
            'get_telemetry_rule_for_organization',
        ]
        for name in expected:
            assert name in tool_names


@pytest.mark.asyncio
class TestGetTelemetryEvaluationStatus:
    """Tests for get_telemetry_evaluation_status."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.get_telemetry_evaluation_status.return_value = {
            'Status': 'RUNNING',
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.get_telemetry_evaluation_status(mock_context)

        assert result.status == 'RUNNING'
        assert result.failure_reason is None

    async def test_with_failure(self, mock_context, oa_tools):
        """Test test_with_failure."""
        mock_client = Mock()
        mock_client.get_telemetry_evaluation_status.return_value = {
            'Status': 'FAILED_START',
            'FailureReason': 'Insufficient permissions',
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.get_telemetry_evaluation_status(mock_context)

        assert result.status == 'FAILED_START'
        assert result.failure_reason == 'Insufficient permissions'

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_telemetry_evaluation_status.side_effect = Exception('API Error')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='API Error'):
                await oa_tools.get_telemetry_evaluation_status(mock_context)
        mock_context.error.assert_called_once()

    async def test_region_parameter(self, mock_context, oa_tools):
        """Test test_region_parameter."""
        mock_client = Mock()
        mock_client.get_telemetry_evaluation_status.return_value = {'Status': 'RUNNING'}
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ) as mock_get_client:
            await oa_tools.get_telemetry_evaluation_status(
                mock_context, region='eu-west-1', profile_name='test-profile'
            )
        mock_get_client.assert_called_once_with('observabilityadmin', 'eu-west-1', 'test-profile')


@pytest.mark.asyncio
class TestStartTelemetryEvaluation:
    """Tests for start_telemetry_evaluation."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.start_telemetry_evaluation.return_value = {}
        mock_client.get_telemetry_evaluation_status.return_value = {'Status': 'STARTING'}
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.start_telemetry_evaluation(mock_context)

        assert result.status == 'STARTING'
        mock_client.start_telemetry_evaluation.assert_called_once()

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.start_telemetry_evaluation.side_effect = Exception('Access denied')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Access denied'):
                await oa_tools.start_telemetry_evaluation(mock_context)
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestGetTelemetryEvaluationStatusForOrganization:
    """Tests for get_telemetry_evaluation_status_for_organization."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.get_telemetry_evaluation_status_for_organization.return_value = {
            'Status': 'RUNNING',
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.get_telemetry_evaluation_status_for_organization(mock_context)

        assert result.status == 'RUNNING'

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_telemetry_evaluation_status_for_organization.side_effect = Exception(
            'Not a management account'
        )
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Not a management account'):
                await oa_tools.get_telemetry_evaluation_status_for_organization(mock_context)
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestStartTelemetryEvaluationForOrganization:
    """Tests for start_telemetry_evaluation_for_organization."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.start_telemetry_evaluation_for_organization.return_value = {}
        mock_client.get_telemetry_evaluation_status_for_organization.return_value = {
            'Status': 'STARTING',
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.start_telemetry_evaluation_for_organization(mock_context)

        assert result.status == 'STARTING'
        mock_client.start_telemetry_evaluation_for_organization.assert_called_once()

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.start_telemetry_evaluation_for_organization.side_effect = Exception(
            'Org error'
        )
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Org error'):
                await oa_tools.start_telemetry_evaluation_for_organization(mock_context)
        mock_context.error.assert_called_once()


def _make_paginator(response_key, items):
    """Helper to create a mock paginator."""
    mock_paginator = Mock()
    mock_paginator.paginate.return_value = [{response_key: items}]
    return mock_paginator


@pytest.mark.asyncio
class TestListResourceTelemetry:
    """Tests for list_resource_telemetry."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        items = [
            {
                'AccountIdentifier': '123456789012',
                'ResourceType': 'AWS::EC2::Instance',
                'ResourceIdentifier': 'i-abc123',
                'TelemetryConfigurationState': {'Logs': 'Enabled', 'Metrics': 'Disabled'},
                'ResourceTags': {'Name': 'test'},
                'LastUpdateTimeStamp': 1700000000,
                'TelemetrySourceType': 'CLOUDWATCH_AGENT',
            }
        ]
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryConfigurations', items)
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_resource_telemetry(mock_context)

        assert len(result.telemetry_configurations) == 1
        assert result.telemetry_configurations[0].resource_identifier == 'i-abc123'
        assert result.telemetry_configurations[0].telemetry_source_type == 'CLOUDWATCH_AGENT'
        assert result.has_more_results is False

    async def test_empty_results(self, mock_context, oa_tools):
        """Test test_empty_results."""
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryConfigurations', [])
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_resource_telemetry(mock_context)

        assert len(result.telemetry_configurations) == 0
        assert (
            result.message
            == 'No resource telemetry configurations found. Ensure telemetry evaluation is running.'
        )

    async def test_has_more_results(self, mock_context, oa_tools):
        """Test test_has_more_results."""
        # Create max_items + 1 items to trigger has_more
        items = [
            {
                'AccountIdentifier': '123456789012',
                'ResourceType': 'AWS::EC2::Instance',
                'ResourceIdentifier': f'i-{i:06d}',
                'TelemetryConfigurationState': {'Logs': 'Enabled'},
                'ResourceTags': {},
            }
            for i in range(3)
        ]
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryConfigurations', items)
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_resource_telemetry(mock_context, max_items=2)

        assert len(result.telemetry_configurations) == 2
        assert result.has_more_results is True

    async def test_with_filters(self, mock_context, oa_tools):
        """Test test_with_filters."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{'TelemetryConfigurations': []}]
        mock_client.get_paginator.return_value = mock_paginator
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            await oa_tools.list_resource_telemetry(
                mock_context,
                resource_types=['AWS::EC2::Instance'],
                resource_identifier_prefix='i-abc',
                telemetry_configuration_state={'Logs': 'Disabled'},
                resource_tags={'Env': 'prod'},
            )

        call_kwargs = mock_paginator.paginate.call_args
        assert call_kwargs[1]['ResourceTypes'] == ['AWS::EC2::Instance']
        assert call_kwargs[1]['ResourceIdentifierPrefix'] == 'i-abc'
        assert call_kwargs[1]['TelemetryConfigurationState'] == {'Logs': 'Disabled'}
        assert call_kwargs[1]['ResourceTags'] == {'Env': 'prod'}

    async def test_none_max_items_defaults(self, mock_context, oa_tools):
        """Test test_none_max_items_defaults."""
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryConfigurations', [])
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_resource_telemetry(mock_context, max_items=None)

        assert result is not None  # Should not crash

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_paginator.side_effect = Exception('Throttling')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Throttling'):
                await oa_tools.list_resource_telemetry(mock_context)
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestListTelemetryRules:
    """Tests for list_telemetry_rules."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        items = [
            {
                'RuleName': 'vpc-flow-rule',
                'RuleArn': 'arn:aws:observabilityadmin:us-east-1:123456789012:rule/vpc-flow-rule',
                'ResourceType': 'AWS::EC2::VPC',
                'TelemetryType': 'Logs',
                'TelemetrySourceTypes': ['VPC_FLOW_LOGS'],
                'CreatedTimeStamp': 1700000000,
                'LastUpdateTimeStamp': 1700001000,
            }
        ]
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryRuleSummaries', items)
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_telemetry_rules(mock_context)

        assert len(result.telemetry_rule_summaries) == 1
        assert result.telemetry_rule_summaries[0].rule_name == 'vpc-flow-rule'
        assert result.telemetry_rule_summaries[0].telemetry_source_types == ['VPC_FLOW_LOGS']

    async def test_empty_results(self, mock_context, oa_tools):
        """Test test_empty_results."""
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryRuleSummaries', [])
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_telemetry_rules(mock_context)

        assert result.message == 'No telemetry rules found'

    async def test_with_prefix_filter(self, mock_context, oa_tools):
        """Test test_with_prefix_filter."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{'TelemetryRuleSummaries': []}]
        mock_client.get_paginator.return_value = mock_paginator
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            await oa_tools.list_telemetry_rules(mock_context, rule_name_prefix='vpc-')

        call_kwargs = mock_paginator.paginate.call_args
        assert call_kwargs[1]['RuleNamePrefix'] == 'vpc-'

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_paginator.side_effect = Exception('Service unavailable')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Service unavailable'):
                await oa_tools.list_telemetry_rules(mock_context)
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestGetTelemetryRule:
    """Tests for get_telemetry_rule."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.get_telemetry_rule.return_value = {
            'RuleName': 'vpc-flow-rule',
            'RuleArn': 'arn:aws:observabilityadmin:us-east-1:123456789012:rule/vpc-flow-rule',
            'CreatedTimeStamp': 1700000000,
            'LastUpdateTimeStamp': 1700001000,
            'TelemetryRule': {
                'ResourceType': 'AWS::EC2::VPC',
                'TelemetryType': 'Logs',
                'TelemetrySourceTypes': ['VPC_FLOW_LOGS'],
                'DestinationConfiguration': {
                    'DestinationType': 'cloud-watch-logs',
                    'DestinationPattern': '/aws/vpc-flow-logs/<resourceId>',
                    'RetentionInDays': 30,
                    'VPCFlowLogParameters': {'TrafficType': 'ALL'},
                },
                'Scope': 'ACCOUNT',
                'SelectionCriteria': 'ALL',
            },
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.get_telemetry_rule(
                mock_context, rule_identifier='vpc-flow-rule'
            )

        assert result.rule_name == 'vpc-flow-rule'
        assert result.telemetry_rule is not None
        assert result.telemetry_rule.resource_type == 'AWS::EC2::VPC'
        assert (
            result.telemetry_rule.destination_configuration.destination_type == 'cloud-watch-logs'
        )
        assert result.telemetry_rule.destination_configuration.retention_in_days == 30
        assert result.telemetry_rule.destination_configuration.vpc_flow_log_parameters == {
            'TrafficType': 'ALL'
        }
        assert result.telemetry_rule.scope == 'ACCOUNT'

    async def test_without_destination_config(self, mock_context, oa_tools):
        """Test test_without_destination_config."""
        mock_client = Mock()
        mock_client.get_telemetry_rule.return_value = {
            'RuleName': 'simple-rule',
            'RuleArn': 'arn:test',
            'TelemetryRule': {
                'ResourceType': 'AWS::Lambda::Function',
                'TelemetryType': 'Traces',
            },
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.get_telemetry_rule(mock_context, rule_identifier='simple-rule')

        assert result.telemetry_rule.destination_configuration is None

    async def test_without_telemetry_rule(self, mock_context, oa_tools):
        """Test test_without_telemetry_rule."""
        mock_client = Mock()
        mock_client.get_telemetry_rule.return_value = {
            'RuleName': 'empty-rule',
            'RuleArn': 'arn:test',
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.get_telemetry_rule(mock_context, rule_identifier='empty-rule')

        assert result.telemetry_rule is None

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_telemetry_rule.side_effect = Exception('Rule not found')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Rule not found'):
                await oa_tools.get_telemetry_rule(mock_context, rule_identifier='nonexistent')
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestListResourceTelemetryForOrganization:
    """Tests for list_resource_telemetry_for_organization."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        items = [
            {
                'AccountIdentifier': '111111111111',
                'ResourceType': 'AWS::Lambda::Function',
                'ResourceIdentifier': 'my-function',
                'TelemetryConfigurationState': {'Traces': 'Enabled'},
                'ResourceTags': {},
                'TelemetrySourceType': 'XRAY',
            }
        ]
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryConfigurations', items)
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_resource_telemetry_for_organization(mock_context)

        assert len(result.telemetry_configurations) == 1
        assert result.telemetry_configurations[0].account_identifier == '111111111111'

    async def test_with_account_filter(self, mock_context, oa_tools):
        """Test test_with_account_filter."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{'TelemetryConfigurations': []}]
        mock_client.get_paginator.return_value = mock_paginator
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            await oa_tools.list_resource_telemetry_for_organization(
                mock_context,
                account_identifiers=['111111111111', '222222222222'],
                resource_types=['AWS::EC2::Instance'],
            )

        call_kwargs = mock_paginator.paginate.call_args
        assert call_kwargs[1]['AccountIdentifiers'] == ['111111111111', '222222222222']
        assert call_kwargs[1]['ResourceTypes'] == ['AWS::EC2::Instance']

    async def test_empty_results(self, mock_context, oa_tools):
        """Test test_empty_results."""
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryConfigurations', [])
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_resource_telemetry_for_organization(mock_context)

        assert result.message == 'No resource telemetry configurations found for the organization.'

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_paginator.side_effect = Exception('Not authorized')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Not authorized'):
                await oa_tools.list_resource_telemetry_for_organization(mock_context)
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestListTelemetryRulesForOrganization:
    """Tests for list_telemetry_rules_for_organization."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        items = [
            {
                'RuleName': 'org-vpc-rule',
                'RuleArn': 'arn:test',
                'ResourceType': 'AWS::EC2::VPC',
                'TelemetryType': 'Logs',
                'TelemetrySourceTypes': ['VPC_FLOW_LOGS'],
            }
        ]
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryRuleSummaries', items)
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_telemetry_rules_for_organization(mock_context)

        assert len(result.telemetry_rule_summaries) == 1
        assert result.telemetry_rule_summaries[0].rule_name == 'org-vpc-rule'

    async def test_with_org_filters(self, mock_context, oa_tools):
        """Test test_with_org_filters."""
        mock_client = Mock()
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [{'TelemetryRuleSummaries': []}]
        mock_client.get_paginator.return_value = mock_paginator
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            await oa_tools.list_telemetry_rules_for_organization(
                mock_context,
                rule_name_prefix='vpc-',
                source_account_ids=['111111111111'],
                source_organization_unit_ids=['ou-xxxx-12345678'],
            )

        call_kwargs = mock_paginator.paginate.call_args
        assert call_kwargs[1]['RuleNamePrefix'] == 'vpc-'
        assert call_kwargs[1]['SourceAccountIds'] == ['111111111111']
        assert call_kwargs[1]['SourceOrganizationUnitIds'] == ['ou-xxxx-12345678']

    async def test_empty_results(self, mock_context, oa_tools):
        """Test test_empty_results."""
        mock_client = Mock()
        mock_client.get_paginator.return_value = _make_paginator('TelemetryRuleSummaries', [])
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.list_telemetry_rules_for_organization(mock_context)

        assert result.message == 'No organization telemetry rules found'

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_paginator.side_effect = Exception('Org access denied')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Org access denied'):
                await oa_tools.list_telemetry_rules_for_organization(mock_context)
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestGetTelemetryRuleForOrganization:
    """Tests for get_telemetry_rule_for_organization."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.get_telemetry_rule_for_organization.return_value = {
            'RuleName': 'org-rule',
            'RuleArn': 'arn:test',
            'TelemetryRule': {
                'ResourceType': 'AWS::EKS::Cluster',
                'TelemetryType': 'Logs',
                'TelemetrySourceTypes': ['EKS_AUDIT_LOGS'],
                'DestinationConfiguration': {
                    'DestinationType': 'cloud-watch-logs',
                    'DestinationPattern': '/aws/eks/<resourceId>',
                },
                'Scope': 'ORGANIZATION',
            },
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.get_telemetry_rule_for_organization(
                mock_context, rule_identifier='org-rule'
            )

        assert result.rule_name == 'org-rule'
        assert result.telemetry_rule.resource_type == 'AWS::EKS::Cluster'
        assert result.telemetry_rule.scope == 'ORGANIZATION'
        mock_client.get_telemetry_rule_for_organization.assert_called_once_with(
            RuleIdentifier='org-rule'
        )

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.get_telemetry_rule_for_organization.side_effect = Exception('Rule not found')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Rule not found'):
                await oa_tools.get_telemetry_rule_for_organization(
                    mock_context, rule_identifier='nonexistent'
                )
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestStopTelemetryEvaluation:
    """Tests for stop_telemetry_evaluation."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.stop_telemetry_evaluation.return_value = {}
        mock_client.get_telemetry_evaluation_status.return_value = {'Status': 'STOPPING'}
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.stop_telemetry_evaluation(mock_context)

        assert result.status == 'STOPPING'
        mock_client.stop_telemetry_evaluation.assert_called_once()

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.stop_telemetry_evaluation.side_effect = Exception('Cannot stop')
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Cannot stop'):
                await oa_tools.stop_telemetry_evaluation(mock_context)
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
class TestStopTelemetryEvaluationForOrganization:
    """Tests for stop_telemetry_evaluation_for_organization."""

    async def test_success(self, mock_context, oa_tools):
        """Test test_success."""
        mock_client = Mock()
        mock_client.stop_telemetry_evaluation_for_organization.return_value = {}
        mock_client.get_telemetry_evaluation_status_for_organization.return_value = {
            'Status': 'STOPPING',
        }
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            result = await oa_tools.stop_telemetry_evaluation_for_organization(mock_context)

        assert result.status == 'STOPPING'
        mock_client.stop_telemetry_evaluation_for_organization.assert_called_once()

    async def test_api_error(self, mock_context, oa_tools):
        """Test test_api_error."""
        mock_client = Mock()
        mock_client.stop_telemetry_evaluation_for_organization.side_effect = Exception(
            'Org stop error'
        )
        with patch(
            'awslabs.cloudwatch_mcp_server.observability_admin.tools.get_aws_client',
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match='Org stop error'):
                await oa_tools.stop_telemetry_evaluation_for_organization(mock_context)
        mock_context.error.assert_called_once()
