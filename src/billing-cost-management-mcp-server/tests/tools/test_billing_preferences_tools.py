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

"""Unit tests for the billing_preferences_tools module."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.billing_preferences_tools import (
    billing_preferences_server,
    get_billing_preferences,
)
from unittest.mock import AsyncMock, MagicMock, patch


GET_BILLING_PREFERENCES_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.billing_preferences_tools.'
    '_get_billing_preferences'
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


def _await_kwargs(mock):
    """Return the keyword arguments of a mock's most recent await."""
    assert mock.await_args is not None
    return mock.await_args.kwargs


async def _registered_tool():
    """Return the registered get-billing-preferences tool, asserting it exists."""
    tool = await billing_preferences_server.get_tool('get-billing-preferences')
    assert tool is not None
    return tool


class TestToolRegistration:
    """The tool is registered and documents what an agent needs to use it."""

    @pytest.mark.asyncio
    async def test_tool_is_registered(self):
        """The get-billing-preferences tool is exposed on the server, named after the API."""
        tool = await _registered_tool()

        assert tool.name == 'get-billing-preferences'

    @pytest.mark.asyncio
    async def test_features_is_declared_required_in_the_schema(self):
        """The API rejects a call without `features`, so the schema must say it is required."""
        tool = await _registered_tool()
        schema = tool.parameters

        assert 'features' in schema.get('required', [])
        assert 'null' not in str(schema['properties']['features'])

    @pytest.mark.asyncio
    async def test_description_states_the_one_feature_limit(self):
        """The one-feature-per-call constraint is the easiest thing to get wrong."""
        tool = await _registered_tool()

        assert 'TAKES EXACTLY ONE VALUE' in (tool.description or '')

    @pytest.mark.asyncio
    async def test_description_distinguishes_org_wide_keys_from_accounts(self):
        """Counting `default` / `open-sharing` as accounts is the other easy mistake."""
        tool = await _registered_tool()

        assert 'ORGANIZATION-WIDE' in (tool.description or '')


class TestWrapper:
    """The decorated tool delegates to the operation handler."""

    @pytest.mark.asyncio
    async def test_every_parameter_is_forwarded(self, mock_context):
        """No parameter is dropped between the tool and the operation."""
        handler = AsyncMock(return_value=SUCCESS)

        with patch(GET_BILLING_PREFERENCES_PATH, new=handler):
            result = await get_billing_preferences(
                mock_context,
                features='RI_SHARING',
                filters='[{"name": "PREFERENCE_KEY", "value": ["credit/4242"]}]',
                max_items=10,
                next_token='token',
            )

        assert result == SUCCESS
        assert _await_kwargs(handler) == {
            'features': 'RI_SHARING',
            'filters': '[{"name": "PREFERENCE_KEY", "value": ["credit/4242"]}]',
            'max_items': 10,
            'next_token': 'token',
        }

    @pytest.mark.asyncio
    async def test_omitted_max_items_fetches_everything(self, mock_context):
        """An omitted max_items reaches the operation as None, which fetches every page."""
        handler = AsyncMock(return_value=SUCCESS)

        with patch(GET_BILLING_PREFERENCES_PATH, new=handler):
            await get_billing_preferences(mock_context, features='RI_SHARING')

        assert _await_kwargs(handler)['max_items'] is None
        assert _await_kwargs(handler)['next_token'] is None

    @pytest.mark.asyncio
    async def test_schema_takes_max_items_not_page_params(self):
        """The tool exposes max_items and next_token, not the removed page parameters."""
        tool = await _registered_tool()

        params = set(tool.parameters['properties'])
        assert {'max_items', 'next_token'} <= params
        assert not {'max_results', 'max_pages'} & params
