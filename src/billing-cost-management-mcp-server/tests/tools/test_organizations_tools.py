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

"""Unit tests for the organizations_tools module."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.organizations_tools import (
    describe_organization_account,
    list_organization_accounts,
    organizations_server,
)
from unittest.mock import AsyncMock, MagicMock, patch


LIST_ACCOUNTS_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.organizations_tools._list_accounts'
)
DESCRIBE_ACCOUNT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.organizations_tools._describe_account'
)
SUCCESS = {'status': 'success', 'data': {}}


@pytest.fixture
def mock_context():
    """Create a mock MCP context with async logging methods."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


async def _registered_tool(name):
    """Return the named registered tool, asserting it exists."""
    tool = await organizations_server.get_tool(name)
    assert tool is not None
    return tool


def _await_kwargs(mock):
    """Return the keyword arguments of a mock's most recent await."""
    assert mock.await_args is not None
    return mock.await_args.kwargs


class TestToolRegistration:
    """Both tools are registered and document what an agent needs to use them."""

    @pytest.mark.asyncio
    async def test_both_tools_are_registered(self):
        """The two Organizations tools are exposed on the server, named after the APIs."""
        list_tool = await _registered_tool('list-organization-accounts')
        describe_tool = await _registered_tool('describe-organization-account')

        assert list_tool.name == 'list-organization-accounts'
        assert describe_tool.name == 'describe-organization-account'

    @pytest.mark.asyncio
    async def test_account_id_is_declared_required_for_describe(self):
        """DescribeAccount rejects a call without an ID, so the schema must say it is required."""
        tool = await _registered_tool('describe-organization-account')
        schema = tool.parameters

        assert 'account_id' in schema.get('required', [])

    @pytest.mark.asyncio
    async def test_description_warns_invited_join_is_not_creation(self):
        """Conflating an INVITED account's join time with its creation is the easy mistake."""
        tool = await _registered_tool('list-organization-accounts')

        assert 'INVITED' in (tool.description or '')


class TestWrappers:
    """The decorated tools delegate to their operation handlers."""

    @pytest.mark.asyncio
    async def test_list_forwards_every_parameter(self, mock_context):
        """No parameter is dropped between the list tool and the operation."""
        handler = AsyncMock(return_value=SUCCESS)

        with patch(LIST_ACCOUNTS_PATH, new=handler):
            result = await list_organization_accounts(
                mock_context, max_results=10, next_token='token', max_pages=2
            )

        assert result == SUCCESS
        assert _await_kwargs(handler) == {
            'max_results': 10,
            'next_token': 'token',
            'max_pages': 2,
        }

    @pytest.mark.asyncio
    async def test_list_paging_defaults_are_applied(self, mock_context):
        """The bounded paging defaults reach the operation when the caller omits them."""
        handler = AsyncMock(return_value=SUCCESS)

        with patch(LIST_ACCOUNTS_PATH, new=handler):
            await list_organization_accounts(mock_context)

        assert _await_kwargs(handler)['max_results'] == 20
        assert _await_kwargs(handler)['max_pages'] == 10

    @pytest.mark.asyncio
    async def test_describe_forwards_account_id(self, mock_context):
        """The account_id reaches the operation handler."""
        handler = AsyncMock(return_value=SUCCESS)

        with patch(DESCRIBE_ACCOUNT_PATH, new=handler):
            result = await describe_organization_account(mock_context, account_id='123456789012')

        assert result == SUCCESS
        assert _await_kwargs(handler) == {'account_id': '123456789012'}
