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
import re
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


async def _description():
    """Return the registered tool's description with line breaks collapsed to spaces."""
    tool = await _registered_tool()
    return ' '.join((tool.description or '').split())


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
    async def test_description_states_the_filter_rule_for_each_feature(self):
        """Filters are required for one credit feature, optional for the other, rejected elsewhere."""
        tool = await _registered_tool()
        description = ' '.join((tool.description or '').split())

        assert 'accepted for CREDIT_PREFERENCE_OPTIONS alone' not in description
        assert 'CREDIT_PREFERENCE_OPTIONS: REQUIRED' in description
        assert 'CREDIT_LEVEL_SHARING (management account only): optional' in description
        rejecting = 'RI_SHARING, RI_SHARING_HISTORY, CREDIT_SHARING, CREDIT_SHARING_HISTORY, BILLING_ALERTS'
        assert f'{rejecting}: not allowed' in description
        assert 'returns no rows, not an error' in description

    @pytest.mark.asyncio
    async def test_description_distinguishes_org_wide_keys_from_accounts(self):
        """Counting `default` / `open-sharing` as accounts is the other easy mistake."""
        tool = await _registered_tool()

        assert 'ORGANIZATION-WIDE' in (tool.description or '')
        description = await _description()
        assert 'count only `account/` keys' in description
        assert 'DISABLED excludes it from sharing' in description
        assert 'so does every account a history period does not list' in description

    @pytest.mark.asyncio
    async def test_description_names_every_group_sharing_key(self):
        """A cost-category group row must not be read as open sharing or as an account."""
        description = await _description()

        for key in (
            '`open-sharing`',
            '`costcategory-prioritized/',
            '`costcategory-restricted/',
            '`benefitgroup-prioritized/',
            '`benefitgroup-restricted/',
        ):
            assert key in description
        assert 'THREE KINDS OF KEY' not in description
        # Credits never use the benefitgroup- prefix, so it must stay scoped to RI_SHARING.
        assert '(RI_SHARING may say `benefitgroup-prioritized/`)' in description
        assert '(RI_SHARING may say `benefitgroup-restricted/`)' in description

    @pytest.mark.asyncio
    async def test_description_explains_each_mode_on_its_own_bullet(self):
        """Each mode carries its own meaning, so swapping them would fail."""
        description = await _description()

        def bullet(key, meaning):
            # The meaning must follow the key before the next bullet starts.
            return re.search(
                re.escape(f'- `{key}') + r'(?:(?! - `).)*?' + re.escape(meaning), description
            )

        assert bullet(
            'costcategory-prioritized/', 'group first, then the rest of the organization'
        )
        assert bullet(
            'costcategory-restricted/', "only inside the owner's group, never outside it"
        )
        assert bullet('open-sharing`', 'to any sharing account in the organization')
        assert not bullet('costcategory-prioritized/', 'never outside it')
        assert not bullet('costcategory-restricted/', 'then the rest of the organization')

    @pytest.mark.asyncio
    async def test_missing_group_row_rule_keys_on_the_default_row(self):
        """A next_token or partial page can lack the group row, so it must not read as open sharing."""
        description = await _description()

        assert (
            'a complete result fetched without `next_token` (`complete_dataset: true`) that has '
            '`default` but no group row normally means organization-wide sharing'
        ) in description
        assert (
            'Any other result without a group row (partial, or fetched with `next_token`) says nothing'
        ) in description
        assert (
            'A current-state page fetched with `next_token` continues that order and has no `default` row'
            in description
        )
        assert (
            'rows come in this order across pages: `default`, at most one GROUP-SHARING row'
            in description
        )
        assert 'say the mode was inferred from the missing row' in description
        assert 'No group-sharing row means organization-wide sharing' not in description
        assert '`complete_dataset: true`) does a missing group row' not in description

    @pytest.mark.asyncio
    async def test_description_says_the_group_row_value_is_not_the_mode(self):
        """The group row's value is always ENABLED; the key carries the mode."""
        description = await _description()

        assert 'value always ENABLED; the key is the mode' in description
        assert 'CREDIT_SHARING uses the same keys' in description

    @pytest.mark.asyncio
    async def test_description_says_why_a_group_row_can_be_missing(self):
        """The service omits the group row in cases where group sharing may still apply."""
        description = await _description()

        assert (
            'LEAVES OUT the group row when group-sharing reporting is not enabled for the organization, '
            'or when a prioritized or restricted mode has no cost category attached; group sharing '
            'may still apply then'
        ) in description
        assert 'A period can lack its group row for the same reasons' in description

    @pytest.mark.asyncio
    async def test_description_makes_no_unverified_group_membership_claim(self):
        """Group membership of default-value accounts is not verified, so it is not stated."""
        description = await _description()

        assert 'That cost category defines the account groups' in description
        assert 'default value' not in description
        assert 'are in no group' not in description

    @pytest.mark.asyncio
    async def test_description_covers_member_account_callers(self):
        """A member account sees one bare `account` row and cannot see the group mode."""
        description = await _description()

        assert 'From a member account: one row, key `account` and no `accountId`' in description
        assert 'The group mode is not visible there, so do not infer it' in description
        assert 'the *_HISTORY features need the management account' in description

    @pytest.mark.asyncio
    async def test_description_explains_history_group_rows(self):
        """History repeats the group row, always as costcategory-, and may omit it."""
        description = await _description()

        assert '"2025-09/costcategory-prioritized/' in description
        assert 'They always write `costcategory-`' in description
        assert 'as a current `benefitgroup-` key is the same setting' in description
        assert 'list only accounts that differ' in description
        assert 'a missing history group row is not evidence of open sharing' in description
        assert (
            "can start mid-period, without that period's `default` and group rows" in description
        )
        assert '(`accountId` only in history)' in description
        assert 'CREDIT_LEVEL_SHARING can narrow where one credit goes' in description


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
