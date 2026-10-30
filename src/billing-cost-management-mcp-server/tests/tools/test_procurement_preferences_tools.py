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

"""Unit tests for the procurement_preferences_operations and _tools modules."""

import pytest
import re
from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_operations import (
    get_procurement_portal_preference,
    list_procurement_portal_preferences,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.'
    'procurement_preferences_operations.create_aws_client'
)


@pytest.fixture
def mock_context():
    """Create a mock MCP context with async logging methods."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


@pytest.fixture
def sample_preference():
    """Return a sample ProcurementPortalPreference as the AWS API would return it."""
    return {
        'ProcurementPortalPreferenceArn': (
            'arn:aws:invoicing::123456789012:procurement-portal-preference/abc123'
        ),
        'EinvoiceDeliveryEnabled': True,
        'EinvoiceDeliveryPreferenceStatus': 'ACTIVE',
        # Sensitive: must never be propagated to the agent/LLM (dropped by the tool).
        'ProcurementPortalSharedSecret': 'super-secret-shared-value',  # pragma: allowlist secret
        'EinvoiceDeliveryPreference': {
            'EinvoiceDeliveryActivationDate': datetime(2026, 3, 1, tzinfo=timezone.utc),
        },
        'CreateDate': datetime(2026, 1, 1, tzinfo=timezone.utc),
        'LastUpdateDate': datetime(2026, 2, 1, tzinfo=timezone.utc),
    }


class TestListProcurementPortalPreferences:
    """list_procurement_portal_preferences pagination and normalization."""

    @pytest.mark.asyncio
    async def test_success_and_timestamp_normalization(self, mock_context, sample_preference):
        """A successful call normalizes CreateDate/LastUpdateDate to ISO 8601."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': [sample_preference]
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        assert result['status'] == 'success'
        pref = result['data']['procurement_portal_preferences'][0]
        assert pref['CreateDate'] == '2026-01-01T00:00:00'
        assert pref['LastUpdateDate'] == '2026-02-01T00:00:00'

    @pytest.mark.asyncio
    async def test_shared_secret_dropped(self, mock_context, sample_preference):
        """ProcurementPortalSharedSecret is dropped from every listed item."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': [sample_preference, dict(sample_preference)]
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        assert result['status'] == 'success'
        prefs = result['data']['procurement_portal_preferences']
        assert prefs, 'expected at least one preference'
        for pref in prefs:
            assert 'ProcurementPortalSharedSecret' not in pref
        # Non-sensitive fields are preserved.
        assert prefs[0]['EinvoiceDeliveryPreferenceStatus'] == 'ACTIVE'

    @pytest.mark.asyncio
    async def test_shared_secret_dropped_on_every_page(self, mock_context, sample_preference):
        """Items from later pages are redacted too, not just the first page."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.side_effect = [
            {'ProcurementPortalPreferences': [dict(sample_preference)], 'NextToken': 'page-2'},
            {'ProcurementPortalPreferences': [dict(sample_preference)]},
        ]

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        prefs = result['data']['procurement_portal_preferences']
        assert len(prefs) == 2
        assert all('ProcurementPortalSharedSecret' not in pref for pref in prefs)

    @pytest.mark.asyncio
    async def test_no_max_items_fetches_every_page(self, mock_context, sample_preference):
        """Without max_items every page is fetched at the largest page size."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.side_effect = [
            {'ProcurementPortalPreferences': [sample_preference], 'NextToken': 'page-2'},
            {'ProcurementPortalPreferences': [sample_preference], 'NextToken': 'page-3'},
            {'ProcurementPortalPreferences': [sample_preference]},
        ]

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        assert result['status'] == 'success'
        calls = mock_client.list_procurement_portal_preferences.call_args_list
        assert len(calls) == 3
        assert all(call.kwargs['MaxResults'] == 100 for call in calls)
        assert [call.kwargs.get('NextToken') for call in calls] == [None, 'page-2', 'page-3']
        assert len(result['data']['procurement_portal_preferences']) == 3
        assert result['data']['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 3,
        }
        assert 'warning' not in result['data']

    @pytest.mark.asyncio
    async def test_max_items_stops_before_exceeding(self, mock_context, sample_preference):
        """max_items sizes the page and stops once reached, returning the service token."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': [sample_preference, sample_preference],
            'NextToken': 'always-more',
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context, max_items=2)

        assert mock_client.list_procurement_portal_preferences.call_count == 1
        assert mock_client.list_procurement_portal_preferences.call_args.kwargs['MaxResults'] == 2
        data = result['data']
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['complete_dataset'] is False
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 'always-more',
            'items_returned': 2,
        }

    @pytest.mark.asyncio
    async def test_continuation_sends_token_and_identical_params(
        self, mock_context, sample_preference
    ):
        """A continuation sends the caller's token and otherwise the same request."""
        first = MagicMock()
        first.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': [sample_preference],
            'NextToken': 'page-2',
        }
        resumed = MagicMock()
        resumed.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': [sample_preference]
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = first
            await list_procurement_portal_preferences(mock_context, max_items=1)
            mock_create.return_value = resumed
            result = await list_procurement_portal_preferences(
                mock_context, max_items=1, next_token='page-2'
            )

        first_call = first.list_procurement_portal_preferences.call_args.kwargs
        resumed_call = resumed.list_procurement_portal_preferences.call_args.kwargs
        assert resumed_call['NextToken'] == 'page-2'
        assert 'NextToken' not in first_call
        assert {k: v for k, v in resumed_call.items() if k != 'NextToken'} == first_call
        assert result['data']['pagination']['complete_dataset'] is True

    @pytest.mark.asyncio
    async def test_rejected_token_is_invalid_next_token(self, mock_context):
        """A token the service rejects maps to invalid_next_token."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad'}},
            'ListProcurementPortalPreferences',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context, next_token='stale')

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_context):
        """An empty result set returns success with zero items_returned."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': []
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        assert result['status'] == 'success'
        assert result['data']['procurement_portal_preferences'] == []
        assert result['data']['pagination']['items_returned'] == 0
        assert result['data']['pagination']['complete_dataset'] is True

    @pytest.mark.asyncio
    async def test_api_client_error(self, mock_context):
        """A ClientError from the API returns an error status."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListProcurementPortalPreferences',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        assert result['status'] == 'error'


class TestGetProcurementPortalPreference:
    """get_procurement_portal_preference validation and nested normalization."""

    @pytest.mark.asyncio
    async def test_missing_arn_returns_error(self, mock_context):
        """An empty ARN returns an error without calling the API."""
        result = await get_procurement_portal_preference(
            mock_context, procurement_portal_preference_arn=''
        )

        assert result['status'] == 'error'
        assert 'procurement_portal_preference_arn is required' in result['data']['message']

    @pytest.mark.asyncio
    async def test_success_strips_metadata_and_normalizes_nested(
        self, mock_context, sample_preference
    ):
        """The nested EinvoiceDeliveryActivationDate is normalized to ISO 8601."""
        mock_client = MagicMock()
        mock_client.get_procurement_portal_preference.return_value = {
            'ProcurementPortalPreference': sample_preference,
            'ResponseMetadata': {'RequestId': 'abc'},
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await get_procurement_portal_preference(
                mock_context,
                procurement_portal_preference_arn=sample_preference[
                    'ProcurementPortalPreferenceArn'
                ],
            )

        assert result['status'] == 'success'
        pref = result['data']['procurement_portal_preference']
        assert pref['CreateDate'] == '2026-01-01T00:00:00'
        assert (
            pref['EinvoiceDeliveryPreference']['EinvoiceDeliveryActivationDate']
            == '2026-03-01T00:00:00'
        )

    @pytest.mark.asyncio
    async def test_shared_secret_dropped(self, mock_context, sample_preference):
        """ProcurementPortalSharedSecret is dropped from the retrieved preference."""
        mock_client = MagicMock()
        mock_client.get_procurement_portal_preference.return_value = {
            'ProcurementPortalPreference': sample_preference,
            'ResponseMetadata': {'RequestId': 'abc'},
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await get_procurement_portal_preference(
                mock_context,
                procurement_portal_preference_arn=sample_preference[
                    'ProcurementPortalPreferenceArn'
                ],
            )

        assert result['status'] == 'success'
        pref = result['data']['procurement_portal_preference']
        assert 'ProcurementPortalSharedSecret' not in pref
        assert pref['EinvoiceDeliveryPreferenceStatus'] == 'ACTIVE'

    @pytest.mark.asyncio
    async def test_api_client_error(self, mock_context):
        """A ClientError from the API returns an error status."""
        mock_client = MagicMock()
        mock_client.get_procurement_portal_preference.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetProcurementPortalPreference',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await get_procurement_portal_preference(
                mock_context, procurement_portal_preference_arn='arn:bad'
            )

        assert result['status'] == 'error'


class TestDropSensitiveFields:
    """Direct tests for the recursive secret-dropping helper."""

    def test_drops_top_level_and_nested_and_lists(self):
        """The secret key is removed at any depth and in list items."""
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_operations import (
            drop_sensitive_fields,
        )

        data = {
            'ProcurementPortalSharedSecret': 'top',  # pragma: allowlist secret
            'Status': 'ACTIVE',
            'nested': {
                'ProcurementPortalSharedSecret': 'deep',  # pragma: allowlist secret
                'keep': 1,
            },
            'items': [
                {'ProcurementPortalSharedSecret': 'a'},
                {'ProcurementPortalSharedSecret': 'b', 'keep': 2},
            ],
        }

        result = drop_sensitive_fields(data)

        assert 'ProcurementPortalSharedSecret' not in result
        assert 'ProcurementPortalSharedSecret' not in result['nested']
        assert result['nested']['keep'] == 1
        assert all('ProcurementPortalSharedSecret' not in item for item in result['items'])
        assert result['items'][1]['keep'] == 2
        assert result['Status'] == 'ACTIVE'

    def test_noop_when_absent(self):
        """Structures without the secret are returned unchanged."""
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_operations import (
            drop_sensitive_fields,
        )

        data = {'Status': 'ACTIVE', 'items': [{'keep': 1}]}
        assert drop_sensitive_fields(data) == {'Status': 'ACTIVE', 'items': [{'keep': 1}]}


class TestProcurementPreferencesServer:
    """FastMCP sub-server registration."""

    def test_server_name(self):
        """The procurement-preferences sub-server has the expected name."""
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_tools import (
            procurement_preferences_server,
        )

        assert procurement_preferences_server.name == 'procurement-preferences-tools'


class TestProcurementPreferencesRouting:
    """Operation routing for the top-level ``procurement-preferences`` tool."""

    @pytest.mark.asyncio
    async def test_routes_list(self, mock_context, sample_preference):
        """operation=list_procurement_portal_preferences dispatches to the handler."""
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_tools import (
            _procurement_preferences,
        )

        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': [sample_preference]
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await _procurement_preferences(
                mock_context, 'list_procurement_portal_preferences'
            )

        assert result['status'] == 'success'
        assert (
            result['data']['procurement_portal_preferences'][0]['EinvoiceDeliveryPreferenceStatus']
            == 'ACTIVE'
        )

    @pytest.mark.asyncio
    async def test_routes_get(self, mock_context, sample_preference):
        """operation=get_procurement_portal_preference dispatches to the handler."""
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_tools import (
            _procurement_preferences,
        )

        mock_client = MagicMock()
        mock_client.get_procurement_portal_preference.return_value = {
            'ProcurementPortalPreference': sample_preference
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await _procurement_preferences(
                mock_context,
                'get_procurement_portal_preference',
                procurement_portal_preference_arn=sample_preference[
                    'ProcurementPortalPreferenceArn'
                ],
            )

        assert result['status'] == 'success'
        assert (
            result['data']['procurement_portal_preference']['EinvoiceDeliveryPreferenceStatus']
            == 'ACTIVE'
        )

    @pytest.mark.asyncio
    async def test_get_missing_arn_routes_error(self, mock_context):
        """Routing get_procurement_portal_preference without an ARN returns an error."""
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_tools import (
            _procurement_preferences,
        )

        result = await _procurement_preferences(mock_context, 'get_procurement_portal_preference')

        assert result['status'] == 'error'
        assert 'procurement_portal_preference_arn is required' in result['data']['message']

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self, mock_context):
        """An unsupported operation returns a standardized error."""
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_tools import (
            _procurement_preferences,
        )

        result = await _procurement_preferences(mock_context, 'not_a_real_operation')

        assert result['status'] == 'error'
        assert 'not_a_real_operation' in result['data']['message']


class TestProcurementPreferencesDescription:
    """The served description matches the API shapes and keeps the secret out of reach."""

    @staticmethod
    async def _description():
        from awslabs.billing_cost_management_mcp_server.tools.procurement_preferences_tools import (
            procurement_preferences_server,
        )

        tool = await procurement_preferences_server.get_tool('procurement-preferences')
        assert tool is not None
        return ' '.join((tool.description or '').split())

    @pytest.mark.asyncio
    async def test_list_returns_names_only_summary_members(self):
        """List Returns names ProcurementPortalPreferenceSummary members, not Get-only fields."""
        import botocore.session

        model = botocore.session.get_session().get_service_model('invoicing')
        summary = set(model.shape_for('ProcurementPortalPreferenceSummary').members)
        # In the public API reference; older botocore releases do not model it yet.
        summary.add('MarketplacePunchOutEnabled')

        desc = await self._description()
        block = desc.split('1) list_procurement_portal_preferences', 1)[1]
        block = block.split('2) get_procurement_portal_preference', 1)[0]
        returns = block.split('Returns:', 1)[1].split('The summary does NOT include', 1)[0]
        named = set(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', returns))

        assert named, 'expected the list Returns text to name fields'
        assert named <= summary, named - summary
        assert 'EinvoiceDeliveryEnabled' in named
        assert 'PurchaseOrderRetrievalEnabled' in named
        assert 'each have their own Enabled flag and status' in returns
        assert 'The summary does NOT include EinvoiceDeliveryPreference' in block

    @pytest.mark.asyncio
    async def test_get_marks_delivery_preference_optional(self):
        """Get says EinvoiceDeliveryPreference can be absent."""
        desc = await self._description()
        block = desc.split('2) get_procurement_portal_preference', 1)[1].split('NOTE:', 1)[0]

        assert 'EinvoiceDeliveryPreference can be absent' in block

    @pytest.mark.asyncio
    async def test_secret_is_redacted_with_no_retrieval_path(self):
        """The description says the secret is redacted and names no other way to get it."""
        note = (await self._description()).split('NOTE:', 1)[1].split('EXAMPLES', 1)[0]

        assert '`ProcurementPortalSharedSecret` is redacted' in note
        for banned in ('SDK', 'CLI', 'boto', 'accessible via'):
            assert banned not in note, banned
