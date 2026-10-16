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

"""Unit tests for the billing_preferences_operations module."""

import boto3
import pytest
from awslabs.billing_cost_management_mcp_server.tools.billing_preferences_operations import (
    get_billing_preferences,
)
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.billing_preferences_operations.'
    'create_aws_client'
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


def _client():
    """Return a real billing client so the stub validates against the API model."""
    return boto3.Session(
        aws_access_key_id='a', aws_secret_access_key='b', region_name='us-east-1'
    ).client('billing')


def _stub(response, expected_params):
    """Queue one GetBillingPreferences response on an activated stubber.

    Args:
        response: The response body the API should return.
        expected_params: The request parameters the call must send.

    Returns:
        Tuple of (client, stubber).
    """
    client = _client()
    stubber = Stubber(client)
    stubber.activate()
    stubber.add_response(
        'get_billing_preferences',
        response,
        {'maxResults': 50, **expected_params},
    )
    return client, stubber


ACCOUNT_ROW = {
    'feature': 'RI_SHARING',
    'key': 'account/123456789012',
    'value': 'DISABLED',
    'accountId': '123456789012',
    'accountName': 'linked-1',
}
ORG_ROWS = [
    {'feature': 'RI_SHARING', 'key': 'default', 'value': 'ENABLED'},
    {'feature': 'RI_SHARING', 'key': 'open-sharing', 'value': 'ENABLED'},
]


class TestRequestParameters:
    """Caller arguments reach the API under its own lowercase parameter names."""

    @pytest.mark.asyncio
    async def test_bare_string_feature_is_wrapped_into_a_list(self, mock_context):
        """The API takes a list, so a bare feature name is wrapped rather than rejected."""
        client, stubber = _stub(
            {'billingPreferences': list(ORG_ROWS)}, {'features': ['RI_SHARING']}
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='RI_SHARING')

        stubber.assert_no_pending_responses()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_list_feature_is_passed_through(self, mock_context):
        """A list is forwarded unchanged."""
        client, stubber = _stub({'billingPreferences': []}, {'features': ['CREDIT_SHARING']})

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features=['CREDIT_SHARING'])

        stubber.assert_no_pending_responses()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_filters_json_and_paging_params_are_sent(self, mock_context):
        """JSON filters are parsed and paging params use the API's lowercase names."""
        client, stubber = _stub(
            {'billingPreferences': []},
            {
                'features': ['CREDIT_PREFERENCE_OPTIONS'],
                'filters': [{'name': 'PREFERENCE_KEY', 'value': ['credit/4242']}],
                'maxResults': 25,
                'nextToken': 'resume-here',
            },
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(
                mock_context,
                features='CREDIT_PREFERENCE_OPTIONS',
                filters='[{"name": "PREFERENCE_KEY", "value": ["credit/4242"]}]',
                max_results=25,
                next_token='resume-here',
            )

        stubber.assert_no_pending_responses()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_omitted_max_results_sends_no_page_size(self, mock_context):
        """Passing None omits maxResults so the service applies its own default."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response(
            'get_billing_preferences',
            {'billingPreferences': list(ORG_ROWS)},
            {'features': ['RI_SHARING']},
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(
                mock_context, features='RI_SHARING', max_results=None
            )

        stubber.assert_no_pending_responses()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_largest_page_is_requested_by_default(self, mock_context):
        """The default page size is the API maximum, so a list arrives in fewer calls."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response(
            'get_billing_preferences',
            {'billingPreferences': []},
            {'features': ['BILLING_ALERTS'], 'maxResults': 50},
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='BILLING_ALERTS')

        stubber.assert_no_pending_responses()
        assert result['status'] == 'success'


class TestResponsePassthrough:
    """Rows are returned as the API sent them."""

    @pytest.mark.asyncio
    async def test_rows_are_not_rewritten_or_annotated(self, mock_context):
        """Every field is preserved verbatim and nothing is derived on top."""
        client, stubber = _stub(
            {'billingPreferences': [ACCOUNT_ROW]}, {'features': ['RI_SHARING']}
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='RI_SHARING')

        assert result['data']['billing_preferences'] == [ACCOUNT_ROW]

    @pytest.mark.asyncio
    async def test_history_billing_period_is_preserved(self, mock_context):
        """The history rows' billingPeriod object is passed through as-is."""
        row = {
            'feature': 'RI_SHARING_HISTORY',
            'key': '2026-06/default',
            'value': 'ENABLED',
            'billingPeriod': {'year': 2026, 'month': 6},
        }
        client, stubber = _stub(
            {'billingPreferences': [row]}, {'features': ['RI_SHARING_HISTORY']}
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='RI_SHARING_HISTORY')

        assert result['data']['billing_preferences'][0]['billingPeriod'] == {
            'year': 2026,
            'month': 6,
        }

    @pytest.mark.asyncio
    async def test_empty_result_is_a_success_not_an_error(self, mock_context):
        """No rows is a real answer and must not be reported as a failure."""
        client, stubber = _stub({'billingPreferences': []}, {'features': ['RI_SHARING']})

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='RI_SHARING')

        assert result['status'] == 'success'
        assert result['data']['billing_preferences'] == []


class TestPagination:
    """The response is paged manually because the SDK declares no paginator."""

    @pytest.mark.asyncio
    async def test_pages_are_followed_with_the_lowercase_token(self, mock_context):
        """A nextToken in the response drives a second request."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response(
            'get_billing_preferences',
            {'billingPreferences': [ORG_ROWS[0]], 'nextToken': 'page-2'},
            {'features': ['RI_SHARING'], 'maxResults': 50},
        )
        stubber.add_response(
            'get_billing_preferences',
            {'billingPreferences': [ORG_ROWS[1]]},
            {
                'features': ['RI_SHARING'],
                'maxResults': 50,
                'nextToken': 'page-2',
            },
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='RI_SHARING')

        stubber.assert_no_pending_responses()
        assert len(result['data']['billing_preferences']) == 2

    @pytest.mark.asyncio
    async def test_max_pages_stops_early_and_reports_more(self, mock_context):
        """Stopping at the page limit is reported rather than looking complete."""
        client, stubber = _stub(
            {'billingPreferences': [ORG_ROWS[0]], 'nextToken': 'page-2'},
            {'features': ['RI_SHARING']},
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(
                mock_context, features='RI_SHARING', max_pages=1
            )

        stubber.assert_no_pending_responses()
        assert result['data']['pagination']['has_more'] is True

    @pytest.mark.asyncio
    async def test_default_page_cap_bounds_an_unbounded_organization(self, mock_context):
        """A very large result set stops at the default cap and says so.

        The cap keeps one call from filling the agent's context, and the
        pagination block carries has_more plus the resume token so the truncation
        cannot be mistaken for the whole list.
        """
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        # Every page offers another, so only the cap can end the loop.
        for page in range(5):
            params = {'features': ['RI_SHARING'], 'maxResults': 50}
            if page:
                params['nextToken'] = f'page-{page}'
            stubber.add_response(
                'get_billing_preferences',
                {'billingPreferences': [ORG_ROWS[0]], 'nextToken': f'page-{page + 1}'},
                params,
            )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='RI_SHARING')

        stubber.assert_no_pending_responses()
        pagination = result['data']['pagination']
        assert pagination['pages_fetched'] == 5
        assert pagination['has_more'] is True
        assert pagination['next_token'] == 'page-5'


class TestErrorHandling:
    """Failures go through the shared handler and stay distinguishable from no data."""

    @pytest.mark.asyncio
    async def test_access_denied_is_surfaced_as_an_error(self, mock_context):
        """A denial is reported as an error, never as an absence of preferences."""
        error = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'nope'},
                'ResponseMetadata': {'RequestId': 'req-1', 'HTTPStatusCode': 400},
            },
            'GetBillingPreferences',
        )
        client = MagicMock()
        client.get_billing_preferences.side_effect = error

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(mock_context, features='RI_SHARING')

        assert result['status'] == 'error'
        assert result['error_type'] == 'AccessDeniedException'

    @pytest.mark.asyncio
    async def test_service_validation_error_is_not_pre_empted(self, mock_context):
        """Input constraints are left to the service, whose error names the limit.

        Revalidating them here would duplicate the service and risk diverging
        from it: the live feature enum already contains values absent from the
        bundled API model.
        """
        error = ClientError(
            {
                'Error': {
                    'Code': 'ValidationException',
                    'Message': (
                        "1 validation error detected: Value at 'features' failed to "
                        'satisfy constraint: Member must have length less than or equal to 1'
                    ),
                },
                'ResponseMetadata': {'RequestId': 'req-2', 'HTTPStatusCode': 400},
            },
            'GetBillingPreferences',
        )
        client = MagicMock()
        client.get_billing_preferences.side_effect = error

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await get_billing_preferences(
                mock_context, features=['RI_SHARING', 'RI_SHARING_HISTORY']
            )

        # The request reached the API rather than being refused locally, and the
        # service's own message came back intact.
        client.get_billing_preferences.assert_called_once()
        assert result['status'] == 'error'
        assert 'length less than or equal to 1' in result['message']
