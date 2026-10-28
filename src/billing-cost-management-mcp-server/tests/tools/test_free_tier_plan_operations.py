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

"""Tests for the free-tier-usage plan operations (account plan state and activities)."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools import (
    free_tier_usage_server,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from fastmcp import Context
from fastmcp.tools import FunctionTool
from unittest.mock import AsyncMock, MagicMock, patch


CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools.create_aws_client'
)


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


async def _tool() -> FunctionTool:
    tool = await free_tier_usage_server.get_tool('free-tier-usage')
    assert isinstance(tool, FunctionTool)
    return tool


def _client_error(code: str, message: str, operation: str) -> ClientError:
    return ClientError({'Error': {'Code': code, 'Message': message}}, operation)


async def _call(mock_context, client, **kwargs):
    tool = await _tool()
    with patch(CLIENT_PATH, return_value=client):
        return await tool.fn(mock_context, **kwargs)


class TestGetAccountPlanState:
    """get_account_plan_state wraps GetAccountPlanState."""

    async def test_returns_plan_state(self, mock_context):
        """A plan record is returned with its fields and an ISO expiration date."""
        client = MagicMock()
        client.get_account_plan_state.return_value = {
            'accountId': '111122223333',
            'accountPlanType': 'FREE',
            'accountPlanStatus': 'ACTIVE',
            'accountPlanRemainingCredits': {'amount': 87.5, 'unit': 'USD'},
            'accountPlanExpirationDate': datetime(2026, 1, 15, tzinfo=timezone.utc),
            'ResponseMetadata': {'RequestId': 'r1'},
        }

        result = await _call(mock_context, client, operation='get_account_plan_state')

        client.get_account_plan_state.assert_called_once_with()
        assert result['status'] == 'success'
        assert result['data'] == {
            'plan_record_found': True,
            'accountId': '111122223333',
            'accountPlanType': 'FREE',
            'accountPlanStatus': 'ACTIVE',
            'accountPlanRemainingCredits': {'amount': 87.5, 'unit': 'USD'},
            'accountPlanExpirationDate': '2026-01-15T00:00:00',
        }

    async def test_missing_plan_record_means_not_on_free_plan(self, mock_context):
        """ResourceNotFoundException is a definite answer: no plan record, not on the Free plan."""
        client = MagicMock()
        client.get_account_plan_state.side_effect = _client_error(
            'ResourceNotFoundException',
            'Missing data for account: 111122223333',
            'GetAccountPlanState',
        )

        result = await _call(mock_context, client, operation='get_account_plan_state')

        assert result['status'] == 'success'
        assert result['data'] == {'plan_record_found': False}
        assert 'not on the Free plan' in result['message']
        assert 'July 15, 2025' in result['message']
        assert 'get_free_tier_usage' in result['message']
        # The account ID in the AWS message is not echoed back.
        assert '111122223333' not in str(result)

    async def test_other_errors_use_the_shared_handler(self, mock_context):
        """Any other failure (for example AccessDenied) stays an error."""
        client = MagicMock()
        client.get_account_plan_state.side_effect = _client_error(
            'AccessDeniedException', 'not authorized', 'GetAccountPlanState'
        )

        result = await _call(mock_context, client, operation='get_account_plan_state')

        assert result['status'] == 'error'
        assert result['error_type'] == 'AccessDeniedException'

    async def test_rejects_filter(self, mock_context):
        """The filter argument applies only to get_free_tier_usage, so it is refused."""
        client = MagicMock()

        result = await _call(
            mock_context,
            client,
            operation='get_account_plan_state',
            filter='{"Dimensions": {"Key": "SERVICE", "Values": ["x"], "MatchOptions": ["EQUALS"]}}',
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        client.get_account_plan_state.assert_not_called()

    async def test_missing_optional_fields_are_omitted(self, mock_context):
        """A record without credits or expiration returns only the fields it has."""
        client = MagicMock()
        client.get_account_plan_state.return_value = {
            'accountId': '111122223333',
            'accountPlanType': 'PAID',
            'accountPlanStatus': 'ACTIVE',
        }

        result = await _call(mock_context, client, operation='get_account_plan_state')

        assert result['data'] == {
            'plan_record_found': True,
            'accountId': '111122223333',
            'accountPlanType': 'PAID',
            'accountPlanStatus': 'ACTIVE',
        }

    @pytest.mark.parametrize(
        'extra', [{'max_items': 5}, {'next_token': 'tok'}, {'next_token': ''}]
    )
    async def test_rejects_paging_arguments(self, mock_context, extra):
        """get_account_plan_state does not page, so max_items and next_token are refused."""
        client = MagicMock()

        result = await _call(mock_context, client, operation='get_account_plan_state', **extra)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert next(iter(extra)) in result['message']
        client.get_account_plan_state.assert_not_called()


class TestListAccountActivities:
    """list_account_activities wraps ListAccountActivities with max_items/next_token paging."""

    async def test_returns_every_page(self, mock_context):
        """Without max_items every page is fetched, at most 100 items per page."""
        client = MagicMock()
        activity = {
            'activityId': 'a' * 32,
            'title': 'Set up a cost budget',
            'reward': {'credit': {'amount': 20.0, 'unit': 'USD'}},
            'status': 'COMPLETED',
        }
        client.list_account_activities.side_effect = [
            {'activities': [activity], 'nextToken': 't2'},
            {'activities': [dict(activity, status='NOT_STARTED')]},
        ]

        result = await _call(mock_context, client, operation='list_account_activities')

        assert client.list_account_activities.call_args_list[0].kwargs == {'maxResults': 100}
        assert client.list_account_activities.call_args_list[1].kwargs == {
            'maxResults': 100,
            'nextToken': 't2',
        }
        assert result['status'] == 'success'
        assert [a['status'] for a in result['data']['activities']] == ['COMPLETED', 'NOT_STARTED']
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_empty_list(self, mock_context):
        """An account with no activities gets an empty, complete list."""
        client = MagicMock()
        client.list_account_activities.return_value = {'activities': []}

        result = await _call(mock_context, client, operation='list_account_activities')

        assert result['status'] == 'success'
        assert result['data']['activities'] == []
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_max_items_and_next_token(self, mock_context):
        """max_items sizes the page and next_token continues a previous call."""
        client = MagicMock()
        client.list_account_activities.return_value = {
            'activities': [{'activityId': 'b' * 32, 'status': 'IN_PROGRESS'}],
            'nextToken': 't3',
        }

        result = await _call(
            mock_context,
            client,
            operation='list_account_activities',
            max_items=1,
            next_token='t2',
        )

        client.list_account_activities.assert_called_once_with(maxResults=1, nextToken='t2')
        assert result['data']['complete_dataset'] is False
        assert result['data']['pagination']['next_token'] == 't3'

    async def test_rejected_token_is_invalid_next_token(self, mock_context):
        """The service reports a bad caller token as ValidationException naming the token."""
        client = MagicMock()
        client.list_account_activities.side_effect = _client_error(
            'ValidationException', 'Invalid nextToken', 'ListAccountActivities'
        )

        result = await _call(
            mock_context, client, operation='list_account_activities', next_token='stale'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    async def test_max_items_zero_is_rejected(self, mock_context):
        """max_items below 1 is a validation error and no request is sent."""
        client = MagicMock()

        result = await _call(
            mock_context, client, operation='list_account_activities', max_items=0
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        client.list_account_activities.assert_not_called()

    async def test_validation_error_not_about_the_token_stays_an_error(self, mock_context):
        """A ValidationException whose message does not name the token is a plain error."""
        client = MagicMock()
        client.list_account_activities.side_effect = _client_error(
            'ValidationException', 'Invalid languageCode', 'ListAccountActivities'
        )

        result = await _call(
            mock_context, client, operation='list_account_activities', next_token='t2'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'ValidationException'

    async def test_later_page_failure_returns_partial_result(self, mock_context):
        """A failure after the first page keeps the activities already read, marked partial."""
        client = MagicMock()
        client.list_account_activities.side_effect = [
            {'activities': [{'activityId': 'c' * 32, 'status': 'COMPLETED'}], 'nextToken': 't2'},
            _client_error('ThrottlingException', 'Rate exceeded', 'ListAccountActivities'),
        ]

        result = await _call(mock_context, client, operation='list_account_activities')

        assert result['status'] == 'success'
        assert len(result['data']['activities']) == 1
        assert result['data']['complete_dataset'] is False
        assert result['data']['warning']
        assert result['data']['pagination']['next_token'] == 't2'

    async def test_rejects_filter(self, mock_context):
        """The filter argument applies only to get_free_tier_usage."""
        client = MagicMock()

        result = await _call(
            mock_context, client, operation='list_account_activities', filter='{"Not": {}}'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        client.list_account_activities.assert_not_called()


async def test_unsupported_operation_lists_every_operation(mock_context):
    """The error for an unknown operation names all three operations."""
    result = await _call(mock_context, MagicMock(), operation='upgrade_account_plan')

    assert result['status'] == 'error'
    assert result['error_type'] == 'validation_error'
    for name in ('get_free_tier_usage', 'get_account_plan_state', 'list_account_activities'):
        assert name in result['message']


async def test_description_documents_plan_operations():
    """The served description names both operations and the no-plan-record answer."""
    tool = await _tool()
    description = tool.description or ''

    assert 'get_account_plan_state' in description
    assert 'list_account_activities' in description
    assert 'plan_record_found' in description
    assert 'not on the Free plan' in description
    assert 'read-only' in description
    assert 'placeholders until it starts' in description


def test_no_write_operation_is_reachable():
    """The module never calls the plan-changing API."""
    import inspect
    from awslabs.billing_cost_management_mcp_server.tools import free_tier_usage_tools

    source = inspect.getsource(free_tier_usage_tools)
    assert 'upgrade_account_plan' not in source
    assert 'UpgradeAccountPlan' not in source
