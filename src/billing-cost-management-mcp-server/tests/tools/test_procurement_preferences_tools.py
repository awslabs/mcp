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
        'Status': 'ACTIVE',
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
    async def test_pagination_across_pages(self, mock_context, sample_preference):
        """Multiple pages are aggregated and pagination metadata is accurate."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.side_effect = [
            {'ProcurementPortalPreferences': [sample_preference], 'NextToken': 'page-2'},
            {'ProcurementPortalPreferences': [sample_preference]},
        ]

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        assert result['status'] == 'success'
        assert mock_client.list_procurement_portal_preferences.call_count == 2
        assert result['data']['pagination']['total_results'] == 2
        assert result['data']['pagination']['has_more'] is False

    @pytest.mark.asyncio
    async def test_max_results_and_next_token_forwarded(self, mock_context, sample_preference):
        """max_results and next_token are forwarded to the request."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': [sample_preference]
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(
                mock_context, max_results=5, next_token='resume-here'
            )

        assert result['status'] == 'success'
        call = mock_client.list_procurement_portal_preferences.call_args.kwargs
        assert call['MaxResults'] == 5
        assert call['NextToken'] == 'resume-here'

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_context):
        """An empty result set returns success with zero total_results."""
        mock_client = MagicMock()
        mock_client.list_procurement_portal_preferences.return_value = {
            'ProcurementPortalPreferences': []
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_procurement_portal_preferences(mock_context)

        assert result['status'] == 'success'
        assert result['data']['procurement_portal_preferences'] == []
        assert result['data']['pagination']['total_results'] == 0

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
        assert result['data']['procurement_portal_preferences'][0]['Status'] == 'ACTIVE'

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
        assert result['data']['procurement_portal_preference']['Status'] == 'ACTIVE'

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
