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

"""Tests for CloudWatch Contributor Insights tools."""

import pytest
from awslabs.cloudwatch_mcp_server.contributor_insights.models import (
    DescribeInsightRulesResponse,
    GetInsightRuleReportResponse,
    ListManagedInsightRulesResponse,
    ModifyInsightRulesResponse,
    PutInsightRuleResponse,
)
from awslabs.cloudwatch_mcp_server.contributor_insights.tools import ContributorInsightsTools
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch


@pytest.fixture
def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


class TestDescribeInsightRules:
    """Test cases for describe_insight_rules."""

    @pytest.mark.asyncio
    async def test_returns_rules(self, mock_context):
        """Test successful retrieval of insight rules."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'InsightRules': [
                        {
                            'Name': 'test-rule-1',
                            'State': 'ENABLED',
                            'Schema': '1',
                            'Definition': '{"Schema":{"Name":"CloudWatchLogRule"}}',
                            'ManagedRule': False,
                        },
                        {
                            'Name': 'test-rule-2',
                            'State': 'DISABLED',
                            'Schema': '1',
                            'Definition': '{}',
                            'ManagedRule': True,
                        },
                    ]
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.describe_insight_rules(mock_context)

            assert isinstance(result, DescribeInsightRulesResponse)
            assert len(result.insight_rules) == 2
            assert result.insight_rules[0].name == 'test-rule-1'
            assert result.insight_rules[0].state == 'ENABLED'
            assert result.insight_rules[1].managed_rule is True
            assert result.has_more_results is False

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_context):
        """Test when no rules exist."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'InsightRules': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.describe_insight_rules(mock_context)

            assert isinstance(result, DescribeInsightRulesResponse)
            assert len(result.insight_rules) == 0
            assert result.message == 'No Contributor Insights rules found'

    @pytest.mark.asyncio
    async def test_name_prefix_filter(self, mock_context):
        """Test filtering by name prefix."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'InsightRules': [
                        {
                            'Name': 'ddb-rule-1',
                            'State': 'ENABLED',
                            'Schema': '1',
                            'Definition': '{}',
                        },
                        {
                            'Name': 'other-rule',
                            'State': 'ENABLED',
                            'Schema': '1',
                            'Definition': '{}',
                        },
                    ]
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.describe_insight_rules(mock_context, name_prefix='ddb-')

            assert len(result.insight_rules) == 1
            assert result.insight_rules[0].name == 'ddb-rule-1'

    @pytest.mark.asyncio
    async def test_name_prefix_paginates_all_pages(self, mock_context):
        """Test that prefix filter paginates through all pages to find matches."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            # Matching rules only on page 2
            mock_paginator.paginate.return_value = [
                {
                    'InsightRules': [
                        {'Name': 'other-1', 'State': 'ENABLED', 'Schema': '1', 'Definition': '{}'},
                        {'Name': 'other-2', 'State': 'ENABLED', 'Schema': '1', 'Definition': '{}'},
                    ]
                },
                {
                    'InsightRules': [
                        {
                            'Name': 'ddb-rule-1',
                            'State': 'ENABLED',
                            'Schema': '1',
                            'Definition': '{}',
                        },
                        {
                            'Name': 'ddb-rule-2',
                            'State': 'DISABLED',
                            'Schema': '1',
                            'Definition': '{}',
                        },
                    ]
                },
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.describe_insight_rules(mock_context, name_prefix='ddb-')

            assert len(result.insight_rules) == 2
            assert result.insight_rules[0].name == 'ddb-rule-1'
            assert result.insight_rules[1].name == 'ddb-rule-2'
            # No MaxItems cap applied when prefix is specified
            mock_paginator.paginate.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_context):
        """Test error handling."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_session.return_value.client.side_effect = Exception('Access denied')

            tools = ContributorInsightsTools()
            with pytest.raises(Exception, match='Access denied'):
                await tools.describe_insight_rules(mock_context)

            mock_context.error.assert_called_once()


class TestGetInsightRuleReport:
    """Test cases for get_insight_rule_report."""

    @pytest.mark.asyncio
    async def test_returns_report(self, mock_context):
        """Test successful retrieval of a rule report."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.get_insight_rule_report.return_value = {
                'KeyLabels': ['PartitionKey'],
                'AggregationStatistic': 'Sum',
                'AggregateValue': 1500.0,
                'ApproximateUniqueCount': 42,
                'Contributors': [
                    {
                        'Keys': ['pk-123'],
                        'ApproximateAggregateValue': 500.0,
                        'Datapoints': [
                            {
                                'Timestamp': datetime(2024, 1, 1, tzinfo=timezone.utc),
                                'ApproximateValue': 250.0,
                            }
                        ],
                    }
                ],
                'MetricDatapoints': [
                    {
                        'Timestamp': datetime(2024, 1, 1, tzinfo=timezone.utc),
                        'UniqueContributors': 10.0,
                        'Sum': 1500.0,
                    }
                ],
            }
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.get_insight_rule_report(mock_context, rule_name='my-rule')

            assert isinstance(result, GetInsightRuleReportResponse)
            assert result.key_labels == ['PartitionKey']
            assert result.aggregation_statistic == 'Sum'
            assert result.aggregate_value == 1500.0
            assert result.approximate_unique_count == 42
            assert len(result.contributors) == 1
            assert result.contributors[0].keys == ['pk-123']
            assert len(result.metric_datapoints) == 1
            assert result.metric_datapoints[0].unique_contributors == 10.0

    @pytest.mark.asyncio
    async def test_empty_report(self, mock_context):
        """Test report with no contributors."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.get_insight_rule_report.return_value = {
                'KeyLabels': [],
                'AggregationStatistic': 'Sum',
                'AggregateValue': 0.0,
                'ApproximateUniqueCount': 0,
                'Contributors': [],
                'MetricDatapoints': [],
            }
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.get_insight_rule_report(mock_context, rule_name='empty-rule')

            assert isinstance(result, GetInsightRuleReportResponse)
            assert len(result.contributors) == 0
            assert len(result.metric_datapoints) == 0

    @pytest.mark.asyncio
    async def test_custom_parameters(self, mock_context):
        """Test that custom parameters are passed correctly."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.get_insight_rule_report.return_value = {
                'KeyLabels': [],
                'AggregationStatistic': 'Maximum',
                'Contributors': [],
                'MetricDatapoints': [],
            }
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            await tools.get_insight_rule_report(
                mock_context,
                rule_name='my-rule',
                period=60,
                max_contributor_count=25,
                metrics=['Maximum', 'SampleCount'],
                order_by='Maximum',
                start_time='2024-01-01T00:00:00Z',
                end_time='2024-01-01T01:00:00Z',
            )

            call_kwargs = mock_client.get_insight_rule_report.call_args[1]
            assert call_kwargs['RuleName'] == 'my-rule'
            assert call_kwargs['Period'] == 60
            assert call_kwargs['MaxContributorCount'] == 25
            assert call_kwargs['Metrics'] == ['Maximum', 'SampleCount']
            assert call_kwargs['OrderBy'] == 'Maximum'

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_context):
        """Test error handling for rule report."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.get_insight_rule_report.side_effect = Exception('Rule not found')
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            with pytest.raises(Exception, match='Rule not found'):
                await tools.get_insight_rule_report(mock_context, rule_name='nonexistent')

            mock_context.error.assert_called_once()


class TestListManagedInsightRules:
    """Test cases for list_managed_insight_rules."""

    @pytest.mark.asyncio
    async def test_returns_managed_rules(self, mock_context):
        """Test successful retrieval of managed rules."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'ManagedRules': [
                        {
                            'TemplateName': 'DynamoDBContributorInsights',
                            'ResourceARN': 'arn:aws:dynamodb:us-east-1:123456789012:table/Orders',
                            'RuleState': {
                                'RuleName': 'DynamoDBContributorInsights-Orders',
                                'State': 'ENABLED',
                            },
                        }
                    ]
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.list_managed_insight_rules(
                mock_context,
                resource_arn='arn:aws:dynamodb:us-east-1:123456789012:table/Orders',
            )

            assert isinstance(result, ListManagedInsightRulesResponse)
            assert len(result.managed_rules) == 1
            assert result.managed_rules[0].template_name == 'DynamoDBContributorInsights'
            assert result.managed_rules[0].rule_state == 'ENABLED'

    @pytest.mark.asyncio
    async def test_empty_managed_rules(self, mock_context):
        """Test when no managed rules exist for a resource."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'ManagedRules': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.list_managed_insight_rules(
                mock_context, resource_arn='arn:aws:dynamodb:us-east-1:123456789012:table/Empty'
            )

            assert len(result.managed_rules) == 0
            assert result.message is not None
            assert 'No managed insight rules found' in result.message


class TestPutInsightRule:
    """Test cases for put_insight_rule."""

    @pytest.mark.asyncio
    async def test_creates_rule(self, mock_context):
        """Test successful rule creation."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.put_insight_rule.return_value = {}
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.put_insight_rule(
                mock_context,
                rule_name='my-new-rule',
                rule_definition='{"Schema":{"Name":"CloudWatchLogRule","Version":1}}',
            )

            assert isinstance(result, PutInsightRuleResponse)
            assert result.success is True
            assert result.rule_name == 'my-new-rule'
            mock_client.put_insight_rule.assert_called_once_with(
                RuleName='my-new-rule',
                RuleDefinition='{"Schema":{"Name":"CloudWatchLogRule","Version":1}}',
                RuleState='ENABLED',
            )

    @pytest.mark.asyncio
    async def test_creates_rule_disabled(self, mock_context):
        """Test rule creation with DISABLED state."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.put_insight_rule.return_value = {}
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            await tools.put_insight_rule(
                mock_context,
                rule_name='disabled-rule',
                rule_definition='{}',
                rule_state='DISABLED',
            )

            mock_client.put_insight_rule.assert_called_once_with(
                RuleName='disabled-rule',
                RuleDefinition='{}',
                RuleState='DISABLED',
            )

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_context):
        """Test error handling for put_insight_rule."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.put_insight_rule.side_effect = Exception('Invalid rule definition')
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            with pytest.raises(Exception, match='Invalid rule definition'):
                await tools.put_insight_rule(mock_context, rule_name='bad', rule_definition='{}')


class TestEnableInsightRules:
    """Test cases for enable_insight_rules."""

    @pytest.mark.asyncio
    async def test_enables_rules(self, mock_context):
        """Test successful rule enabling."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.enable_insight_rules.return_value = {'Failures': []}
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.enable_insight_rules(
                mock_context, rule_names=['rule-1', 'rule-2']
            )

            assert isinstance(result, ModifyInsightRulesResponse)
            assert len(result.failures) == 0
            assert result.message is not None
            assert 'Enabled 2/2 rules' in result.message

    @pytest.mark.asyncio
    async def test_partial_failure(self, mock_context):
        """Test enabling with partial failures."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.enable_insight_rules.return_value = {
                'Failures': [
                    {
                        'FailureResource': 'managed-rule',
                        'ExceptionType': 'InvalidParameterValue',
                        'FailureCode': '400',
                        'FailureDescription': 'Cannot modify managed rule',
                    }
                ]
            }
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.enable_insight_rules(
                mock_context, rule_names=['rule-1', 'managed-rule']
            )

            assert len(result.failures) == 1
            assert result.failures[0].failure_resource == 'managed-rule'
            assert result.message is not None
            assert '1 failed' in result.message


class TestDisableInsightRules:
    """Test cases for disable_insight_rules."""

    @pytest.mark.asyncio
    async def test_disables_rules(self, mock_context):
        """Test successful rule disabling."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.disable_insight_rules.return_value = {'Failures': []}
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.disable_insight_rules(mock_context, rule_names=['rule-1'])

            assert isinstance(result, ModifyInsightRulesResponse)
            assert len(result.failures) == 0
            assert result.message is not None
            assert 'Disabled 1/1 rules' in result.message

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_context):
        """Test error handling for disable."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.disable_insight_rules.side_effect = Exception('Access denied')
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            with pytest.raises(Exception, match='Access denied'):
                await tools.disable_insight_rules(mock_context, rule_names=['rule-1'])

            mock_context.error.assert_called_once()


class TestValidation:
    """Validation test cases."""

    @pytest.mark.asyncio
    async def test_max_items_validation(self, mock_context):
        """Test max_items < 1 raises ValueError."""
        tools = ContributorInsightsTools()
        with pytest.raises(ValueError, match='max_items must be at least 1'):
            await tools.describe_insight_rules(mock_context, max_items=0)

    @pytest.mark.asyncio
    async def test_invalid_rule_state(self, mock_context):
        """Test invalid rule_state raises ValueError."""
        tools = ContributorInsightsTools()
        with pytest.raises(ValueError, match="rule_state must be 'ENABLED' or 'DISABLED'"):
            await tools.put_insight_rule(
                mock_context, rule_name='test', rule_definition='{}', rule_state='INVALID'
            )

    @pytest.mark.asyncio
    async def test_enable_empty_list(self, mock_context):
        """Test enable with empty list raises ValueError."""
        tools = ContributorInsightsTools()
        with pytest.raises(ValueError, match='rule_names must not be empty'):
            await tools.enable_insight_rules(mock_context, rule_names=[])

    @pytest.mark.asyncio
    async def test_disable_empty_list(self, mock_context):
        """Test disable with empty list raises ValueError."""
        tools = ContributorInsightsTools()
        with pytest.raises(ValueError, match='rule_names must not be empty'):
            await tools.disable_insight_rules(mock_context, rule_names=[])


class TestRegistration:
    """Test tool registration."""

    def test_register_tools(self):
        """Test that all 6 tools are registered."""
        mock_mcp = Mock()
        mock_mcp.tool.return_value = lambda f: f
        tools = ContributorInsightsTools()
        tools.register(mock_mcp)
        assert mock_mcp.tool.call_count == 6


class TestDescribeInsightRulesEdgeCases:
    """Edge case tests for describe_insight_rules."""

    @pytest.mark.asyncio
    async def test_max_items_none_defaults_to_50(self, mock_context):
        """Test max_items=None defaults to 50."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'InsightRules': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.describe_insight_rules(mock_context, max_items=None)
            assert isinstance(result, DescribeInsightRulesResponse)

    @pytest.mark.asyncio
    async def test_has_more_when_exceeds_max(self, mock_context):
        """Test has_more flag when results exceed max_items."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'InsightRules': [
                        {
                            'Name': f'rule-{i}',
                            'State': 'ENABLED',
                            'Schema': '1',
                            'Definition': '{}',
                        }
                        for i in range(5)
                    ]
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.describe_insight_rules(mock_context, max_items=2)

            assert len(result.insight_rules) == 2
            assert result.has_more_results is True
            assert result.message is not None
            assert 'more available' in result.message


class TestGetInsightRuleReportEdgeCases:
    """Edge case tests for get_insight_rule_report."""

    @pytest.mark.asyncio
    async def test_period_none_defaults(self, mock_context):
        """Test period=None defaults to 300."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.get_insight_rule_report.return_value = {
                'KeyLabels': [],
                'AggregationStatistic': 'Sum',
                'Contributors': [],
                'MetricDatapoints': [],
            }
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            await tools.get_insight_rule_report(
                mock_context, rule_name='test', period=None, max_contributor_count=None
            )

            call_kwargs = mock_client.get_insight_rule_report.call_args[1]
            assert call_kwargs['Period'] == 300
            assert call_kwargs['MaxContributorCount'] == 10


class TestListManagedInsightRulesEdgeCases:
    """Edge case tests for list_managed_insight_rules."""

    @pytest.mark.asyncio
    async def test_max_items_none_defaults(self, mock_context):
        """Test max_items=None defaults to 50."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'ManagedRules': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.list_managed_insight_rules(
                mock_context, resource_arn='arn:aws:dynamodb:us-east-1:123:table/T', max_items=None
            )
            assert isinstance(result, ListManagedInsightRulesResponse)

    @pytest.mark.asyncio
    async def test_has_more_when_exceeds_max(self, mock_context):
        """Test has_more flag when results exceed max_items."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [
                {
                    'ManagedRules': [
                        {
                            'TemplateName': f'tmpl-{i}',
                            'ResourceARN': 'arn:x',
                            'RuleState': {'State': 'ENABLED'},
                        }
                        for i in range(5)
                    ]
                }
            ]
            mock_client.get_paginator.return_value = mock_paginator
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.list_managed_insight_rules(
                mock_context, resource_arn='arn:aws:dynamodb:us-east-1:123:table/T', max_items=2
            )

            assert len(result.managed_rules) == 2
            assert result.has_more_results is True
            assert result.message is not None
            assert 'more available' in result.message

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_context):
        """Test error handling for list_managed_insight_rules."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_session.return_value.client.side_effect = Exception('Not found')

            tools = ContributorInsightsTools()
            with pytest.raises(Exception, match='Not found'):
                await tools.list_managed_insight_rules(
                    mock_context, resource_arn='arn:aws:dynamodb:us-east-1:123:table/X'
                )
            mock_context.error.assert_called_once()


class TestPutInsightRuleEdgeCases:
    """Edge case tests for put_insight_rule."""

    @pytest.mark.asyncio
    async def test_rule_state_none_defaults_to_enabled(self, mock_context):
        """Test rule_state=None defaults to ENABLED."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.put_insight_rule.return_value = {}
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            await tools.put_insight_rule(
                mock_context, rule_name='test', rule_definition='{}', rule_state=None
            )

            mock_client.put_insight_rule.assert_called_once_with(
                RuleName='test', RuleDefinition='{}', RuleState='ENABLED'
            )


class TestDisableInsightRulesEdgeCases:
    """Edge case tests for disable_insight_rules."""

    @pytest.mark.asyncio
    async def test_partial_failure(self, mock_context):
        """Test disabling with partial failures."""
        with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
            mock_client = Mock()
            mock_client.disable_insight_rules.return_value = {
                'Failures': [
                    {
                        'FailureResource': 'rule-x',
                        'ExceptionType': 'InvalidParameter',
                        'FailureCode': '400',
                        'FailureDescription': 'Cannot disable',
                    }
                ]
            }
            mock_session.return_value.client.return_value = mock_client

            tools = ContributorInsightsTools()
            result = await tools.disable_insight_rules(
                mock_context, rule_names=['rule-1', 'rule-x']
            )

            assert len(result.failures) == 1
            assert result.message is not None
            assert '1 failed' in result.message
