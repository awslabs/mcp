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

"""Unit tests for the compute_optimizer_automation tools and operations modules.

These tests verify the MCP tool wrappers and their underlying operation
handlers for the AWS Compute Optimizer Automation API, covering delegation, response
formatting, pagination, and error handling.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools import (
    compute_optimizer_automation_operations as ops,
)
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_automation_tools import (
    VALID_OPERATIONS,
    compute_optimizer_automation_server,
)
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_automation_tools import (
    compute_optimizer_automation as automation_fn,
)
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


STATUS_SUCCESS = 'success'
STATUS_ERROR = 'error'
ACCOUNT_ID = '123456789012'
EVENT_ID = 'event-abc123'
RULE_ARN = f'arn:aws:compute-optimizer-automation::{ACCOUNT_ID}:rule/rule-abc123'
RESOURCE_ARN = f'arn:aws:ec2:us-east-1:{ACCOUNT_ID}:volume/vol-0abc'

TS = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
TS_ISO = '2025-06-01T12:00:00'

SAVINGS = {
    'currency': 'USD',
    'beforeDiscountSavings': 10.5,
    'afterDiscountSavings': 9.0,
    'savingsEstimationMode': 'BeforeDiscount',
}


@pytest.fixture
def mock_ctx():
    """Create a mock MCP context."""
    ctx = MagicMock()
    ctx.info = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


# ===== Server / registration =====


def test_server_initialization():
    """The server is initialized with the expected name."""
    assert compute_optimizer_automation_server.name == 'compute-optimizer-automation-tools'


async def test_tool_registered_with_name():
    """The single dispatch tool is registered on the server under the expected MCP name."""
    tool = await compute_optimizer_automation_server.get_tool('compute-optimizer-automation')
    assert tool is not None
    assert tool.name == 'compute-optimizer-automation'


def test_valid_operations_list():
    """VALID_OPERATIONS covers exactly the 13 supported read operations."""
    assert len(VALID_OPERATIONS) == 13
    assert set(VALID_OPERATIONS) == {
        'get_automation_event',
        'get_automation_rule',
        'get_enrollment_configuration',
        'list_accounts',
        'list_automation_events',
        'list_automation_event_steps',
        'list_automation_event_summaries',
        'list_automation_rules',
        'list_recommended_actions',
        'list_recommended_action_summaries',
        'list_automation_rule_preview',
        'list_automation_rule_preview_summaries',
        'list_tags_for_resource',
    }


# ===== Formatting helpers =====


def test_format_savings():
    """Savings objects are formatted with snake_case keys."""
    result = ops._format_savings(SAVINGS)
    assert result == {
        'currency': 'USD',
        'before_discount_savings': 10.5,
        'after_discount_savings': 9.0,
        'savings_estimation_mode': 'BeforeDiscount',
    }


def test_format_savings_none():
    """A missing savings object formats to None."""
    assert ops._format_savings(None) is None


def test_format_timestamp():
    """Timestamps convert to UTC ISO strings; None passes through."""
    assert ops._format_timestamp(TS) == TS_ISO
    assert ops._format_timestamp(None) is None


def test_format_resource_details_ebs_volume():
    """EBS volume resource details are formatted with snake_case keys."""
    details = {
        'ebsVolume': {
            'configuration': {'type': 'gp3', 'sizeInGib': 100, 'iops': 3000, 'throughput': 125}
        }
    }
    result = ops._format_resource_details(details)
    assert result == {
        'ebs_volume': {
            'configuration': {
                'type': 'gp3',
                'size_in_gib': 100,
                'iops': 3000,
                'throughput': 125,
            }
        }
    }


def test_format_resource_details_unknown_member_preserved():
    """Unknown union members are preserved rather than dropped."""
    details = {'someFutureType': {'foo': 'bar'}}
    assert ops._format_resource_details(details) == details


def test_format_resource_details_none():
    """A missing resource details object formats to None."""
    assert ops._format_resource_details(None) is None


def test_create_client_uses_service_name():
    """The client factory requests the compute-optimizer-automation service."""
    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_automation_operations.create_aws_client'
    ) as mock_create:
        ops.create_compute_optimizer_automation_client('us-west-2')
        mock_create.assert_called_once_with(
            'compute-optimizer-automation', region_name='us-west-2'
        )


def test_format_tags():
    """Tags are formatted into key/value dicts."""
    assert ops._format_tags([{'key': 'env', 'value': 'prod'}]) == [{'key': 'env', 'value': 'prod'}]
    assert ops._format_tags(None) == []


# ===== Operation handlers (with mocked boto3 client) =====


# Each list handler paired with its boto3 method, response list key, and any
# required positional args (beyond ctx/client). Used to exercise the shared
# pagination branches (max_results forwarding + next_token continuation) uniformly.
_LIST_HANDLERS = [
    ('list_accounts', 'list_accounts', 'accounts', ()),
    ('list_automation_events', 'list_automation_events', 'automationEvents', ()),
    (
        'list_automation_event_steps',
        'list_automation_event_steps',
        'automationEventSteps',
        (EVENT_ID,),
    ),
    (
        'list_automation_event_summaries',
        'list_automation_event_summaries',
        'automationEventSummaries',
        (),
    ),
    ('list_automation_rules', 'list_automation_rules', 'automationRules', ()),
    ('list_recommended_actions', 'list_recommended_actions', 'recommendedActions', ()),
    (
        'list_recommended_action_summaries',
        'list_recommended_action_summaries',
        'recommendedActionSummaries',
        (),
    ),
    (
        'list_automation_rule_preview',
        'list_automation_rule_preview',
        'previewResults',
        ('AccountRule', '["UpgradeEbsVolumeType"]'),
    ),
    (
        'list_automation_rule_preview_summaries',
        'list_automation_rule_preview_summaries',
        'previewResultSummaries',
        ('AccountRule', '["UpgradeEbsVolumeType"]'),
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize('op_name,method,list_key,args', _LIST_HANDLERS)
async def test_list_handler_pagination_branches(mock_ctx, op_name, method, list_key, args):
    """Each list handler forwards max_results and stops at max_pages, returning next_token."""
    client = MagicMock()
    getattr(client, method).return_value = {list_key: [], 'nextToken': 'more'}

    result = await getattr(ops, op_name)(mock_ctx, client, *args, max_results=5, max_pages=1)

    _, kwargs = getattr(client, method).call_args
    assert kwargs['maxResults'] == 5
    assert result['data']['next_token'] == 'more'


@pytest.mark.asyncio
@pytest.mark.parametrize('op_name,method,list_key,args', _LIST_HANDLERS)
async def test_list_handler_next_token_continuation(mock_ctx, op_name, method, list_key, args):
    """Each list handler passes a provided next_token into the request."""
    client = MagicMock()
    getattr(client, method).return_value = {list_key: []}

    await getattr(ops, op_name)(mock_ctx, client, *args, next_token='resume-here')

    _, kwargs = getattr(client, method).call_args
    assert kwargs['nextToken'] == 'resume-here'


@pytest.mark.asyncio
class TestGetOperations:
    """Tests for the single-item Get* operations."""

    async def test_get_automation_event(self, mock_ctx):
        """get_automation_event formats the API response."""
        client = MagicMock()
        client.get_automation_event.return_value = {
            'eventId': EVENT_ID,
            'eventType': 'UpgradeEbsVolumeType',
            'eventStatus': 'Complete',
            'accountId': ACCOUNT_ID,
            'createdTimestamp': TS,
            'estimatedMonthlySavings': SAVINGS,
        }

        result = await ops.get_automation_event(mock_ctx, client, EVENT_ID)

        client.get_automation_event.assert_called_once_with(eventId=EVENT_ID)
        assert result['status'] == STATUS_SUCCESS
        event = result['data']['automation_event']
        assert event['event_id'] == EVENT_ID
        assert event['created_timestamp'] == TS_ISO
        assert event['estimated_monthly_savings']['currency'] == 'USD'

    async def test_get_automation_rule_includes_criteria_and_tags(self, mock_ctx):
        """get_automation_rule includes criteria and tags when present."""
        client = MagicMock()
        client.get_automation_rule.return_value = {
            'ruleArn': RULE_ARN,
            'ruleId': 'rule-abc123',
            'name': 'my-rule',
            'ruleType': 'AccountRule',
            'recommendedActionTypes': ['UpgradeEbsVolumeType'],
            'schedule': {
                'scheduleExpression': 'cron(30 12 * * ? *)',
                'scheduleExpressionTimezone': 'UTC',
                'executionWindowInMinutes': 60,
            },
            'organizationConfiguration': {
                'ruleApplyOrder': 'BeforeAccountRules',
                'accountIds': [ACCOUNT_ID],
            },
            'criteria': {'region': [{'comparison': 'StringEquals', 'values': ['us-east-1']}]},
            'tags': [{'key': 'env', 'value': 'prod'}],
            'createdTimestamp': TS,
        }

        result = await ops.get_automation_rule(mock_ctx, client, RULE_ARN)

        client.get_automation_rule.assert_called_once_with(ruleArn=RULE_ARN)
        rule = result['data']['automation_rule']
        assert rule['rule_arn'] == RULE_ARN
        assert rule['schedule']['execution_window_in_minutes'] == 60
        assert rule['organization_configuration']['rule_apply_order'] == 'BeforeAccountRules'
        assert rule['criteria'] == {
            'region': [{'comparison': 'StringEquals', 'values': ['us-east-1']}]
        }
        assert rule['tags'] == [{'key': 'env', 'value': 'prod'}]

    async def test_get_enrollment_configuration(self, mock_ctx):
        """get_enrollment_configuration formats the API response."""
        client = MagicMock()
        client.get_enrollment_configuration.return_value = {
            'status': 'Active',
            'statusReason': 'ok',
            'organizationRuleMode': 'AnyAllowed',
            'lastUpdatedTimestamp': TS,
        }

        result = await ops.get_enrollment_configuration(mock_ctx, client)

        client.get_enrollment_configuration.assert_called_once_with()
        enrollment = result['data']['enrollment_configuration']
        assert enrollment['status'] == 'Active'
        assert enrollment['organization_rule_mode'] == 'AnyAllowed'
        assert enrollment['last_updated_timestamp'] == TS_ISO

    async def test_list_tags_for_resource(self, mock_ctx):
        """list_tags_for_resource formats the tag list."""
        client = MagicMock()
        client.list_tags_for_resource.return_value = {
            'tags': [{'key': 'team', 'value': 'billing'}]
        }

        result = await ops.list_tags_for_resource(mock_ctx, client, RESOURCE_ARN)

        client.list_tags_for_resource.assert_called_once_with(resourceArn=RESOURCE_ARN)
        assert result['data']['tags'] == [{'key': 'team', 'value': 'billing'}]


@pytest.mark.asyncio
class TestListPagination:
    """Tests for pagination behavior in List* operations."""

    async def test_list_accounts_paginates(self, mock_ctx):
        """list_accounts follows nextToken across pages and aggregates results."""
        client = MagicMock()
        client.list_accounts.side_effect = [
            {
                'accounts': [{'accountId': '111', 'status': 'Active'}],
                'nextToken': 'tok1',
            },
            {
                'accounts': [{'accountId': '222', 'status': 'Inactive'}],
            },
        ]

        result = await ops.list_accounts(mock_ctx, client)

        assert client.list_accounts.call_count == 2
        assert result['data']['count'] == 2
        assert 'next_token' not in result['data']
        assert result['data']['accounts'][0]['account_id'] == '111'

    async def test_list_accounts_respects_max_pages(self, mock_ctx):
        """list_accounts stops at max_pages and returns the token to continue."""
        client = MagicMock()
        client.list_accounts.return_value = {
            'accounts': [{'accountId': '111', 'status': 'Active'}],
            'nextToken': 'more',
        }

        result = await ops.list_accounts(mock_ctx, client, max_pages=1)

        assert client.list_accounts.call_count == 1
        assert result['data']['next_token'] == 'more'
        assert result['data']['count'] == 1

    async def test_list_accounts_passes_max_results(self, mock_ctx):
        """list_accounts passes maxResults through to the API."""
        client = MagicMock()
        client.list_accounts.return_value = {'accounts': []}

        await ops.list_accounts(mock_ctx, client, max_results=5)

        _, kwargs = client.list_accounts.call_args
        assert kwargs['maxResults'] == 5


@pytest.mark.asyncio
class TestListEvents:
    """Tests for list_automation_events."""

    async def test_parses_filters_and_time_range(self, mock_ctx):
        """Filters (JSON) and datetime strings are parsed and passed to the API."""
        client = MagicMock()
        client.list_automation_events.return_value = {
            'automationEvents': [
                {
                    'eventId': EVENT_ID,
                    'eventStatus': 'Complete',
                    'estimatedMonthlySavings': SAVINGS,
                }
            ]
        }

        result = await ops.list_automation_events(
            mock_ctx,
            client,
            filters='[{"name": "EventStatus", "values": ["Complete"]}]',
            start_time='2025-01-01',
            end_time='2025-02-01T00:00:00',
        )

        _, kwargs = client.list_automation_events.call_args
        assert kwargs['filters'] == [{'name': 'EventStatus', 'values': ['Complete']}]
        assert kwargs['startTimeInclusive'] == datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert kwargs['endTimeExclusive'] == datetime(2025, 2, 1, tzinfo=timezone.utc)
        assert result['data']['count'] == 1
        event = result['data']['automation_events'][0]
        assert event['event_id'] == EVENT_ID
        assert event['estimated_monthly_savings']['after_discount_savings'] == 9.0

    async def test_invalid_time_raises_value_error(self, mock_ctx):
        """An invalid datetime string raises ValueError."""
        client = MagicMock()
        with pytest.raises(ValueError):
            await ops.list_automation_events(mock_ctx, client, start_time='06/01/2025')


@pytest.mark.asyncio
class TestListRecommendedActions:
    """Tests for recommended action listing and formatting."""

    async def test_formats_current_and_recommended_details(self, mock_ctx):
        """Recommended actions expand the current/recommended EBS details."""
        client = MagicMock()
        client.list_recommended_actions.return_value = {
            'recommendedActions': [
                {
                    'recommendedActionId': 'ra-1',
                    'resourceType': 'EbsVolume',
                    'recommendedActionType': 'UpgradeEbsVolumeType',
                    'currentResourceDetails': {
                        'ebsVolume': {'configuration': {'type': 'gp2', 'sizeInGib': 100}}
                    },
                    'recommendedResourceDetails': {
                        'ebsVolume': {'configuration': {'type': 'gp3', 'sizeInGib': 100}}
                    },
                    'restartNeeded': False,
                    'estimatedMonthlySavings': SAVINGS,
                    'resourceTags': [{'key': 'env', 'value': 'dev'}],
                }
            ]
        }

        result = await ops.list_recommended_actions(mock_ctx, client)

        action = result['data']['recommended_actions'][0]
        assert action['current_resource_details']['ebs_volume']['configuration']['type'] == 'gp2'
        assert (
            action['recommended_resource_details']['ebs_volume']['configuration']['type'] == 'gp3'
        )
        assert action['restart_needed'] is False
        assert action['resource_tags'] == [{'key': 'env', 'value': 'dev'}]

    async def test_summaries_formatting(self, mock_ctx):
        """Recommended action summaries expand the total block."""
        client = MagicMock()
        client.list_recommended_action_summaries.return_value = {
            'recommendedActionSummaries': [
                {
                    'key': 'EbsVolume',
                    'total': {'recommendedActionCount': 3, 'estimatedMonthlySavings': SAVINGS},
                }
            ]
        }

        result = await ops.list_recommended_action_summaries(mock_ctx, client)

        summary = result['data']['recommended_action_summaries'][0]
        assert summary['key'] == 'EbsVolume'
        assert summary['total']['recommended_action_count'] == 3
        assert summary['total']['estimated_monthly_savings']['currency'] == 'USD'

    async def test_actions_forward_filters(self, mock_ctx):
        """list_recommended_actions parses and forwards a JSON filter string."""
        client = MagicMock()
        client.list_recommended_actions.return_value = {'recommendedActions': []}

        await ops.list_recommended_actions(
            mock_ctx, client, filters='[{"name": "ResourceType", "values": ["EbsVolume"]}]'
        )

        _, kwargs = client.list_recommended_actions.call_args
        assert kwargs['filters'] == [{'name': 'ResourceType', 'values': ['EbsVolume']}]

    async def test_action_summaries_forward_filters(self, mock_ctx):
        """list_recommended_action_summaries parses and forwards a JSON filter string."""
        client = MagicMock()
        client.list_recommended_action_summaries.return_value = {'recommendedActionSummaries': []}

        await ops.list_recommended_action_summaries(
            mock_ctx, client, filters='[{"name": "AccountId", "values": ["123456789012"]}]'
        )

        _, kwargs = client.list_recommended_action_summaries.call_args
        assert kwargs['filters'] == [{'name': 'AccountId', 'values': ['123456789012']}]


@pytest.mark.asyncio
class TestListRulePreview:
    """Tests for rule preview operations."""

    async def test_required_and_optional_params_parsed(self, mock_ctx):
        """rule_type, action types, scope, and criteria are parsed and forwarded."""
        client = MagicMock()
        client.list_automation_rule_preview.return_value = {'previewResults': []}

        await ops.list_automation_rule_preview(
            mock_ctx,
            client,
            rule_type='AccountRule',
            recommended_action_types='["UpgradeEbsVolumeType"]',
            organization_scope='{"accountIds": ["123456789012"]}',
            criteria='{"region": [{"comparison": "StringEquals", "values": ["us-east-1"]}]}',
        )

        _, kwargs = client.list_automation_rule_preview.call_args
        assert kwargs['ruleType'] == 'AccountRule'
        assert kwargs['recommendedActionTypes'] == ['UpgradeEbsVolumeType']
        assert kwargs['organizationScope'] == {'accountIds': ['123456789012']}
        assert kwargs['criteria'] == {
            'region': [{'comparison': 'StringEquals', 'values': ['us-east-1']}]
        }

    async def test_preview_summaries(self, mock_ctx):
        """Preview summaries are formatted using the shared summary formatter."""
        client = MagicMock()
        client.list_automation_rule_preview_summaries.return_value = {
            'previewResultSummaries': [
                {'key': 'k1', 'total': {'recommendedActionCount': 2}},
            ]
        }

        result = await ops.list_automation_rule_preview_summaries(
            mock_ctx,
            client,
            rule_type='AccountRule',
            recommended_action_types='["UpgradeEbsVolumeType"]',
        )

        summary = result['data']['preview_result_summaries'][0]
        assert summary['key'] == 'k1'
        assert summary['total']['recommended_action_count'] == 2
        assert summary['total']['estimated_monthly_savings'] is None

    async def test_preview_summaries_forward_scope_and_criteria(self, mock_ctx):
        """Preview summaries parse and forward organization_scope and criteria."""
        client = MagicMock()
        client.list_automation_rule_preview_summaries.return_value = {'previewResultSummaries': []}

        await ops.list_automation_rule_preview_summaries(
            mock_ctx,
            client,
            rule_type='OrganizationRule',
            recommended_action_types='["UpgradeEbsVolumeType"]',
            organization_scope='{"accountIds": ["123456789012"]}',
            criteria='{"region": [{"comparison": "StringEquals", "values": ["us-east-1"]}]}',
        )

        _, kwargs = client.list_automation_rule_preview_summaries.call_args
        assert kwargs['organizationScope'] == {'accountIds': ['123456789012']}
        assert kwargs['criteria'] == {
            'region': [{'comparison': 'StringEquals', 'values': ['us-east-1']}]
        }


@pytest.mark.asyncio
class TestEventSummariesAndSteps:
    """Tests for event summaries and steps formatting."""

    async def test_event_summaries(self, mock_ctx):
        """Event summaries format dimensions, time period, and totals."""
        client = MagicMock()
        client.list_automation_event_summaries.return_value = {
            'automationEventSummaries': [
                {
                    'key': 'Complete',
                    'dimensions': [{'key': 'EventStatus', 'value': 'Complete'}],
                    'timePeriod': {'startTimeInclusive': TS, 'endTimeExclusive': TS},
                    'total': {'automationEventCount': 4, 'estimatedMonthlySavings': SAVINGS},
                }
            ]
        }

        result = await ops.list_automation_event_summaries(mock_ctx, client)

        summary = result['data']['automation_event_summaries'][0]
        assert summary['dimensions'] == [{'key': 'EventStatus', 'value': 'Complete'}]
        assert summary['time_period']['start_time_inclusive'] == TS_ISO
        assert summary['total']['automation_event_count'] == 4

    async def test_event_summaries_forward_filters_and_dates(self, mock_ctx):
        """Summaries forward filters and the string start/end dates to the API."""
        client = MagicMock()
        client.list_automation_event_summaries.return_value = {'automationEventSummaries': []}

        await ops.list_automation_event_summaries(
            mock_ctx,
            client,
            filters='[{"name": "EventType", "values": ["UpgradeEbsVolumeType"]}]',
            start_date='2025-01-01',
            end_date='2025-02-01',
        )

        _, kwargs = client.list_automation_event_summaries.call_args
        assert kwargs['filters'] == [{'name': 'EventType', 'values': ['UpgradeEbsVolumeType']}]
        assert kwargs['startDateInclusive'] == '2025-01-01'
        assert kwargs['endDateExclusive'] == '2025-02-01'

    async def test_event_steps(self, mock_ctx):
        """Event steps require eventId and format each step."""
        client = MagicMock()
        client.list_automation_event_steps.return_value = {
            'automationEventSteps': [
                {
                    'eventId': EVENT_ID,
                    'stepId': 'step-1',
                    'stepType': 'CreateEbsSnapshot',
                    'stepStatus': 'Complete',
                    'startTimestamp': TS,
                }
            ]
        }

        result = await ops.list_automation_event_steps(mock_ctx, client, EVENT_ID)

        _, kwargs = client.list_automation_event_steps.call_args
        assert kwargs['eventId'] == EVENT_ID
        step = result['data']['automation_event_steps'][0]
        assert step['step_type'] == 'CreateEbsSnapshot'
        assert step['start_timestamp'] == TS_ISO


@pytest.mark.asyncio
class TestListRulesAndAccounts:
    """Tests for list_automation_rules and account/summary formatting paths."""

    async def test_list_automation_rules_omits_get_only_fields(self, mock_ctx):
        """List rule responses omit criteria/tags (present only on GetAutomationRule)."""
        client = MagicMock()
        client.list_automation_rules.return_value = {
            'automationRules': [
                {
                    'ruleArn': RULE_ARN,
                    'ruleId': 'rule-abc123',
                    'name': 'my-rule',
                    'ruleType': 'AccountRule',
                    'status': 'Active',
                    'recommendedActionTypes': ['UpgradeEbsVolumeType'],
                }
            ]
        }

        result = await ops.list_automation_rules(mock_ctx, client)

        rule = result['data']['automation_rules'][0]
        assert rule['rule_arn'] == RULE_ARN
        # criteria/tags are only populated by the get operation.
        assert 'criteria' not in rule
        assert 'tags' not in rule
        # Missing optional nested structures format to None.
        assert rule['organization_configuration'] is None
        assert rule['schedule'] is None

    async def test_list_automation_rules_forwards_filters(self, mock_ctx):
        """list_automation_rules parses and forwards a JSON filter string."""
        client = MagicMock()
        client.list_automation_rules.return_value = {'automationRules': []}

        await ops.list_automation_rules(
            mock_ctx, client, filters='[{"name": "Status", "values": ["Active"]}]'
        )

        _, kwargs = client.list_automation_rules.call_args
        assert kwargs['filters'] == [{'name': 'Status', 'values': ['Active']}]


# ===== Dispatch tool (routing, validation, error handling) =====

_TOOLS_MODULE = (
    'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_automation_tools'
)


@pytest.mark.asyncio
class TestDispatchRouting:
    """Tests for operation routing in the single dispatch tool."""

    async def test_routes_to_operation_with_client(self, mock_ctx):
        """The tool creates a client and routes to the matching operation handler."""
        with (
            patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create,
            patch(f'{_TOOLS_MODULE}.get_automation_event', new_callable=AsyncMock) as mock_op,
        ):
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}
            fake_client = MagicMock()
            mock_create.return_value = fake_client

            result = await automation_fn(
                mock_ctx, operation='get_automation_event', event_id=EVENT_ID
            )

            assert result['status'] == STATUS_SUCCESS
            mock_create.assert_called_once_with(None)
            mock_op.assert_awaited_once_with(mock_ctx, fake_client, EVENT_ID)

    async def test_passes_region_through(self, mock_ctx):
        """The region parameter is forwarded to the client factory."""
        with (
            patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create,
            patch(
                f'{_TOOLS_MODULE}.get_enrollment_configuration', new_callable=AsyncMock
            ) as mock_op,
        ):
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}
            mock_create.return_value = MagicMock()

            await automation_fn(
                mock_ctx, operation='get_enrollment_configuration', region='us-west-2'
            )

            mock_create.assert_called_once_with('us-west-2')

    async def test_forwards_rule_preview_params(self, mock_ctx):
        """Rule-preview params are forwarded positionally to the operation."""
        with (
            patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create,
            patch(
                f'{_TOOLS_MODULE}.list_automation_rule_preview', new_callable=AsyncMock
            ) as mock_op,
        ):
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}
            fake_client = MagicMock()
            mock_create.return_value = fake_client

            await automation_fn(
                mock_ctx,
                operation='list_automation_rule_preview',
                rule_type='AccountRule',
                recommended_action_types='["UpgradeEbsVolumeType"]',
            )

            mock_op.assert_awaited_once_with(
                mock_ctx,
                fake_client,
                'AccountRule',
                '["UpgradeEbsVolumeType"]',
                None,
                None,
                None,
                10,
                None,
            )

    @pytest.mark.parametrize(
        'operation,handler,extra_kwargs',
        [
            ('get_automation_event', 'get_automation_event', {'event_id': EVENT_ID}),
            ('get_automation_rule', 'get_automation_rule', {'rule_arn': RULE_ARN}),
            ('get_enrollment_configuration', 'get_enrollment_configuration', {}),
            ('list_accounts', 'list_accounts', {}),
            ('list_automation_events', 'list_automation_events', {}),
            (
                'list_automation_event_steps',
                'list_automation_event_steps',
                {'event_id': EVENT_ID},
            ),
            (
                'list_automation_event_summaries',
                'list_automation_event_summaries',
                {},
            ),
            ('list_automation_rules', 'list_automation_rules', {}),
            ('list_recommended_actions', 'list_recommended_actions', {}),
            (
                'list_recommended_action_summaries',
                'list_recommended_action_summaries',
                {},
            ),
            (
                'list_automation_rule_preview',
                'list_automation_rule_preview',
                {
                    'rule_type': 'AccountRule',
                    'recommended_action_types': '["UpgradeEbsVolumeType"]',
                },
            ),
            (
                'list_automation_rule_preview_summaries',
                'list_automation_rule_preview_summaries',
                {
                    'rule_type': 'AccountRule',
                    'recommended_action_types': '["UpgradeEbsVolumeType"]',
                },
            ),
            ('list_tags_for_resource', 'list_tags_for_resource', {'resource_arn': RESOURCE_ARN}),
        ],
    )
    async def test_every_operation_routes_to_its_handler(
        self, mock_ctx, operation, handler, extra_kwargs
    ):
        """Each supported operation dispatches to the correctly named handler."""
        with (
            patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create,
            patch(f'{_TOOLS_MODULE}.{handler}', new_callable=AsyncMock) as mock_op,
        ):
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}
            mock_create.return_value = MagicMock()

            result = await automation_fn(mock_ctx, operation=operation, **extra_kwargs)

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once()

    async def test_unsupported_operation(self, mock_ctx):
        """An unknown operation returns an error without creating a client."""
        with patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create:
            mock_create.return_value = MagicMock()

            result = await automation_fn(mock_ctx, operation='delete_everything')

            assert result['status'] == STATUS_ERROR
            assert result['data']['provided_operation'] == 'delete_everything'

    async def test_handles_exception(self, mock_ctx):
        """Exceptions are routed through handle_aws_error."""
        with (
            patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create,
            patch(f'{_TOOLS_MODULE}.handle_aws_error', new_callable=AsyncMock) as mock_handle,
        ):
            mock_create.side_effect = RuntimeError('boom')
            mock_handle.return_value = {'status': STATUS_ERROR, 'message': 'boom'}

            result = await automation_fn(
                mock_ctx, operation='get_automation_event', event_id=EVENT_ID
            )

            assert result['status'] == STATUS_ERROR
            mock_handle.assert_awaited_once()


@pytest.mark.asyncio
class TestDispatchValidation:
    """Tests for required-parameter validation in the dispatch tool."""

    async def test_missing_event_id(self, mock_ctx):
        """get_automation_event without event_id errors before creating a client."""
        with patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create:
            result = await automation_fn(mock_ctx, operation='get_automation_event')

            assert result['status'] == STATUS_ERROR
            assert 'event_id' in result['data']['missing_parameters']
            mock_create.assert_not_called()

    async def test_missing_rule_preview_params(self, mock_ctx):
        """Rule preview without required params reports all missing params."""
        with patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create:
            result = await automation_fn(mock_ctx, operation='list_automation_rule_preview')

            assert result['status'] == STATUS_ERROR
            assert set(result['data']['missing_parameters']) == {
                'rule_type',
                'recommended_action_types',
            }
            mock_create.assert_not_called()

    async def test_missing_resource_arn(self, mock_ctx):
        """list_tags_for_resource without resource_arn errors before creating a client."""
        with patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create:
            result = await automation_fn(mock_ctx, operation='list_tags_for_resource')

            assert result['status'] == STATUS_ERROR
            assert 'resource_arn' in result['data']['missing_parameters']
            mock_create.assert_not_called()


@pytest.mark.asyncio
class TestFilterValidation:
    """Tests for the `filters` JSON/name validation in the dispatch tool."""

    async def test_invalid_json_filters(self, mock_ctx):
        """Malformed filters JSON errors with a friendly message, no client created."""
        with patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create:
            result = await automation_fn(
                mock_ctx, operation='list_automation_events', filters='{not json'
            )

            assert result['status'] == STATUS_ERROR
            assert 'Invalid JSON' in result['message']
            mock_create.assert_not_called()

    async def test_filters_not_a_list(self, mock_ctx):
        """A non-array filters value errors before calling AWS."""
        with patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create:
            result = await automation_fn(
                mock_ctx, operation='list_automation_events', filters='{"name": "EventStatus"}'
            )

            assert result['status'] == STATUS_ERROR
            mock_create.assert_not_called()

    async def test_invalid_filter_name(self, mock_ctx):
        """An unknown filter name errors and lists the valid names."""
        with patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create:
            result = await automation_fn(
                mock_ctx,
                operation='list_automation_events',
                filters='[{"name": "Nonsense", "values": ["x"]}]',
            )

            assert result['status'] == STATUS_ERROR
            assert result['data']['invalid_filter_names'] == ['Nonsense']
            assert 'EventStatus' in result['data']['valid_filter_names']
            mock_create.assert_not_called()

    async def test_valid_filter_name_passes(self, mock_ctx):
        """A valid filter name passes validation and reaches the handler."""
        with (
            patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create,
            patch(f'{_TOOLS_MODULE}.list_automation_events', new_callable=AsyncMock) as mock_op,
        ):
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}
            mock_create.return_value = MagicMock()

            result = await automation_fn(
                mock_ctx,
                operation='list_automation_events',
                filters='[{"name": "EventStatus", "values": ["Complete"]}]',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once()

    async def test_validation_skipped_when_model_unavailable(self, mock_ctx):
        """If the boto model can't be loaded, filter validation is skipped (AWS validates)."""
        with (
            patch(f'{_TOOLS_MODULE}.create_compute_optimizer_automation_client') as mock_create,
            patch(f'{_TOOLS_MODULE}.list_automation_events', new_callable=AsyncMock) as mock_op,
            patch(f'{_TOOLS_MODULE}._valid_filter_names_by_operation', return_value={}),
        ):
            mock_op.return_value = {'status': STATUS_SUCCESS, 'data': {}}
            mock_create.return_value = MagicMock()

            # 'Bogus' would normally be rejected, but with no model it passes through.
            result = await automation_fn(
                mock_ctx,
                operation='list_automation_events',
                filters='[{"name": "Bogus", "values": ["x"]}]',
            )

            assert result['status'] == STATUS_SUCCESS
            mock_op.assert_awaited_once()


class TestFilterNamesFromModel:
    """Tests that filter names are derived from the botocore service model."""

    def test_names_match_boto_model(self):
        """The derived names come from the installed botocore model, not a hardcoded list."""
        from awslabs.billing_cost_management_mcp_server.tools import (
            compute_optimizer_automation_tools as mod,
        )

        # Cached accessor is populated from the model at call time.
        mod._valid_filter_names_by_operation.cache_clear()
        mapping = mod._valid_filter_names_by_operation()

        # Events and event-summaries share the AutomationEventFilterName enum.
        assert 'EventStatus' in mapping['list_automation_events']
        assert mapping['list_automation_events'] == mapping['list_automation_event_summaries']

        # Recommended-actions and its summaries share the RecommendedActionFilterName enum.
        assert 'RecommendedActionType' in mapping['list_recommended_actions']
        assert mapping['list_recommended_actions'] == mapping['list_recommended_action_summaries']

        # Operations without a `filters` input are absent from the map.
        assert 'list_accounts' not in mapping
        assert 'get_automation_event' not in mapping

    def test_returns_empty_when_model_load_fails(self):
        """If the botocore model can't be loaded, an empty map is returned (no raise)."""
        from awslabs.billing_cost_management_mcp_server.tools import (
            compute_optimizer_automation_tools as mod,
        )

        mod._valid_filter_names_by_operation.cache_clear()
        with patch('botocore.session.Session.get_service_model', side_effect=RuntimeError('boom')):
            assert mod._valid_filter_names_by_operation() == {}
        mod._valid_filter_names_by_operation.cache_clear()

    def test_skips_ops_without_input_shape_or_enum(self):
        """Ops with no input shape, no filters, or a non-enum filter name are skipped."""
        from awslabs.billing_cost_management_mcp_server.tools import (
            compute_optimizer_automation_tools as mod,
        )

        def _op(input_shape):
            m = MagicMock()
            m.input_shape = input_shape
            return m

        def _filters_member(name_enum):
            name_member = MagicMock()
            name_member.enum = name_enum
            member = MagicMock()
            member.members = {'name': name_member}
            filters = MagicMock()
            filters.type_name = 'list'
            filters.member = member
            return filters

        no_input = _op(None)
        no_filters = _op(MagicMock(members={}))
        no_enum = _op(MagicMock(members={'filters': _filters_member(None)}))

        service_model = MagicMock()
        service_model.operation_names = ['NoInput', 'NoFilters', 'NoEnum']
        service_model.operation_model.side_effect = lambda n: {
            'NoInput': no_input,
            'NoFilters': no_filters,
            'NoEnum': no_enum,
        }[n]

        mod._valid_filter_names_by_operation.cache_clear()
        with patch('botocore.session.Session.get_service_model', return_value=service_model):
            assert mod._valid_filter_names_by_operation() == {}
        mod._valid_filter_names_by_operation.cache_clear()


_OPS_MODULE = (
    'awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_automation_operations'
)


@pytest.mark.asyncio
class TestSqlOffload:
    """List handlers offload large responses to SQL to protect the context window."""

    async def test_small_response_returned_inline(self, mock_ctx):
        """An offload-enabled op still returns inline when below the size threshold."""
        client = MagicMock()
        client.list_recommended_actions.return_value = {
            'recommendedActions': [{'recommendedActionId': 'ra-1', 'resourceType': 'EbsVolume'}]
        }

        result = await ops.list_recommended_actions(mock_ctx, client)

        # Below the threshold the inline list and count survive; no SQL sentinel.
        assert result['data']['recommended_actions'][0]['recommended_action_id'] == 'ra-1'
        assert result['data']['count'] == 1
        assert 'data_stored' not in result['data']

    async def test_large_response_offloaded_to_sql(self, mock_ctx):
        """A response over the size threshold is offloaded and the sentinel surfaces."""
        client = MagicMock()
        # Many tag-heavy actions push the response past the offload threshold.
        actions = [
            {
                'recommendedActionId': f'ra-{i}',
                'resourceType': 'EbsVolume',
                'resourceTags': [{'key': f'k{j}', 'value': 'v' * 200} for j in range(50)],
            }
            for i in range(60)
        ]
        client.list_recommended_actions.return_value = {'recommendedActions': actions}

        result = await ops.list_recommended_actions(mock_ctx, client)

        assert result['status'] == STATUS_SUCCESS
        assert result['data']['data_stored'] is True
        assert result['data']['table_name'].startswith(
            'compute_optimizer_automation_list_recommended_actions'
        )
        # One row per item.
        assert result['data']['row_count'] == 60

    async def test_offload_preserves_next_token(self, mock_ctx):
        """When a large response paginates, the next_token survives the offload."""
        client = MagicMock()
        actions = [
            {
                'recommendedActionId': f'ra-{i}',
                'resourceTags': [{'key': f'k{j}', 'value': 'v' * 200} for j in range(50)],
            }
            for i in range(60)
        ]
        client.list_recommended_actions.return_value = {
            'recommendedActions': actions,
            'nextToken': 'more-pages',
        }

        result = await ops.list_recommended_actions(mock_ctx, client, max_pages=1)

        assert result['data']['data_stored'] is True
        assert result['data']['next_page_token'] == 'more-pages'
        assert result['data']['has_more'] is True

    @pytest.mark.parametrize('op_name,method,list_key,args', _LIST_HANDLERS)
    async def test_every_list_handler_routes_through_gate(
        self, mock_ctx, op_name, method, list_key, args
    ):
        """Every list handler routes through the SQL size gate with its operation name."""
        client = MagicMock()
        getattr(client, method).return_value = {list_key: []}

        with patch(
            f'{_OPS_MODULE}.convert_response_if_needed', new_callable=AsyncMock
        ) as mock_gate:
            mock_gate.side_effect = lambda ctx, data, name, **kw: data

            await getattr(ops, op_name)(mock_ctx, client, *args)

            _, kwargs = mock_gate.call_args
            gate_args = mock_gate.call_args.args
            assert gate_args[2] == f'compute_optimizer_automation_{op_name}'
            assert kwargs['pagination_token_key'] == 'next_token'
