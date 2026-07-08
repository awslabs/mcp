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

"""Unit tests for the invoicing_operations and invoicing_tools modules."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.invoicing_operations import (
    list_invoice_summaries,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.invoicing_operations.create_aws_client'
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
def sample_summary():
    """Return a sample InvoiceSummary as the AWS API would return it."""
    return {
        'AccountId': '123456789012',
        'InvoiceId': 'INV-001',
        'InvoiceType': 'INVOICE',
        'IssuedDate': datetime(2026, 5, 1, tzinfo=timezone.utc),
        'DueDate': datetime(2026, 6, 15, tzinfo=timezone.utc),
        'BillingPeriod': {'Month': 5, 'Year': 2026},
        'Entity': {'InvoicingEntity': 'Amazon Web Services, Inc.'},
        'BaseCurrencyAmount': {
            'TotalAmount': '1500.00',
            'TotalAmountBeforeTax': '1400.00',
            'CurrencyCode': 'USD',
        },
    }


def _client_factory(mock_client, mock_sts):
    """Build a create_aws_client side_effect returning per-service mocks."""

    def _factory(service_name, **kwargs):
        return mock_sts if service_name == 'sts' else mock_client

    return _factory


class TestListInvoiceSummariesSelector:
    """Selector resolution and account auto-detection."""

    @pytest.mark.asyncio
    async def test_billing_period_auto_detects_account(self, mock_context, sample_summary):
        """A billing_period query auto-detects the account via STS."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {'Account': '123456789012'}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(mock_context, billing_period='2026-05')

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Selector'] == {'ResourceType': 'ACCOUNT_ID', 'Value': '123456789012'}
        assert call['Filter']['BillingPeriod'] == {'Month': 5, 'Year': 2026}
        mock_sts.get_caller_identity.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_account_id_skips_sts(self, mock_context, sample_summary):
        """An explicit account_id is used directly without an STS call."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(
                mock_context, account_id='999888777666', billing_period='2026-05'
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Selector']['Value'] == '999888777666'
        mock_sts.get_caller_identity.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoice_id_selector(self, mock_context, sample_summary):
        """An invoice_id builds an INVOICE_ID selector and skips STS."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}
        mock_sts = MagicMock()

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.side_effect = _client_factory(mock_client, mock_sts)
            result = await list_invoice_summaries(mock_context, invoice_id='INV-001')

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Selector'] == {'ResourceType': 'INVOICE_ID', 'Value': 'INV-001'}
        mock_sts.get_caller_identity.assert_not_called()

    @pytest.mark.asyncio
    async def test_account_and_invoice_both_provided(self, mock_context):
        """Providing both account_id and invoice_id returns an error."""
        result = await list_invoice_summaries(
            mock_context, account_id='123456789012', invoice_id='INV-001'
        )

        assert result['status'] == 'error'
        assert 'not both' in result['data']['message']

    @pytest.mark.asyncio
    async def test_sts_exception_returns_error(self, mock_context):
        """When account_id is omitted and STS get_caller_identity raises, status is error."""
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {'Error': {'Code': 'ExpiredTokenException', 'Message': 'Token expired'}},
            'GetCallerIdentity',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_sts
            result = await list_invoice_summaries(mock_context, billing_period='2026-05')

        assert result['status'] == 'error'


class TestListInvoiceSummariesFilter:
    """Filter construction and validation."""

    @pytest.mark.asyncio
    async def test_time_interval_uses_epoch_seconds(self, mock_context, sample_summary):
        """A start/end range builds a TimeInterval with epoch-second values."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                start_date='2026-01-01',
                end_date='2026-06-30',
            )

        assert result['status'] == 'success'
        interval = mock_client.list_invoice_summaries.call_args.kwargs['Filter']['TimeInterval']
        assert interval['StartDate'] == int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
        assert interval['EndDate'] == int(datetime(2026, 6, 30, tzinfo=timezone.utc).timestamp())

    @pytest.mark.asyncio
    async def test_invoicing_entity_filter(self, mock_context, sample_summary):
        """The invoicing_entity value is passed through to the Filter."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                billing_period='2026-05',
                invoicing_entity='Amazon Web Services, Inc.',
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_summaries.call_args.kwargs
        assert call['Filter']['InvoicingEntity'] == 'Amazon Web Services, Inc.'

    @pytest.mark.asyncio
    async def test_billing_period_and_dates_mutually_exclusive(self, mock_context):
        """billing_period together with a date range returns an error."""
        result = await list_invoice_summaries(
            mock_context,
            account_id='123456789012',
            billing_period='2026-05',
            start_date='2026-01-01',
            end_date='2026-06-30',
        )

        assert result['status'] == 'error'
        assert 'mutually' in result['data']['message'].lower()

    @pytest.mark.asyncio
    async def test_start_date_without_end_date(self, mock_context):
        """start_date without end_date returns an error."""
        result = await list_invoice_summaries(
            mock_context, account_id='123456789012', start_date='2026-01-01'
        )

        assert result['status'] == 'error'
        assert 'together' in result['data']['message'].lower()

    @pytest.mark.asyncio
    async def test_invalid_billing_period_format(self, mock_context):
        """A malformed billing_period returns a YYYY-MM error."""
        result = await list_invoice_summaries(mock_context, billing_period='2026')

        assert result['status'] == 'error'
        assert 'YYYY-MM' in result['data']['message']

    @pytest.mark.asyncio
    async def test_invalid_billing_period_month(self, mock_context):
        """An out-of-range month returns an error."""
        result = await list_invoice_summaries(mock_context, billing_period='2026-13')

        assert result['status'] == 'error'
        assert 'month' in result['data']['message'].lower()

    @pytest.mark.asyncio
    async def test_invalid_date_format(self, mock_context):
        """A malformed start_date returns a format error."""
        result = await list_invoice_summaries(
            mock_context,
            account_id='123456789012',
            start_date='not-a-date',
            end_date='2026-06-30',
        )

        assert result['status'] == 'error'
        assert 'YYYY-MM-DD' in result['data']['message']


class TestListInvoiceSummariesResponse:
    """Response normalization, pagination, and error handling."""

    @pytest.mark.asyncio
    async def test_timestamps_normalized_to_iso(self, mock_context, sample_summary):
        """Epoch/datetime timestamp fields are converted to ISO 8601 strings."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05'
            )

        summary = result['data']['invoice_summaries'][0]
        assert summary['IssuedDate'] == '2026-05-01T00:00:00'
        assert summary['DueDate'] == '2026-06-15T00:00:00'

    @pytest.mark.asyncio
    async def test_epoch_int_timestamps_normalized_to_iso(self, mock_context):
        """Epoch INTEGER seconds for IssuedDate/DueDate are normalized to ISO 8601 strings."""
        # 1746144000 == 2025-05-02T00:00:00 UTC
        # 1748822400 == 2025-06-02T00:00:00 UTC
        epoch_summary = {
            'AccountId': '123456789012',
            'InvoiceId': 'INV-EPOCH',
            'InvoiceType': 'INVOICE',
            'IssuedDate': 1746144000,
            'DueDate': 1748822400,
            'BillingPeriod': {'Month': 5, 'Year': 2025},
            'Entity': {'InvoicingEntity': 'Amazon Web Services, Inc.'},
            'BaseCurrencyAmount': {
                'TotalAmount': '500.00',
                'TotalAmountBeforeTax': '450.00',
                'CurrencyCode': 'USD',
            },
        }
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [epoch_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2025-05'
            )

        assert result['status'] == 'success'
        summary = result['data']['invoice_summaries'][0]
        assert summary['IssuedDate'] == '2025-05-02T00:00:00'
        assert summary['DueDate'] == '2025-06-02T00:00:00'

    @pytest.mark.asyncio
    async def test_pagination_across_pages(self, mock_context, sample_summary):
        """Multiple pages are aggregated and pagination metadata is accurate."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.side_effect = [
            {'InvoiceSummaries': [sample_summary], 'NextToken': 'page-2'},
            {'InvoiceSummaries': [sample_summary]},
        ]

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05'
            )

        assert result['status'] == 'success'
        assert mock_client.list_invoice_summaries.call_count == 2
        pagination = result['data']['pagination']
        assert pagination['total_results'] == 2
        assert pagination['has_more'] is False

    @pytest.mark.asyncio
    async def test_max_pages_limit(self, mock_context, sample_summary):
        """max_pages caps the number of pages fetched and reports has_more."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {
            'InvoiceSummaries': [sample_summary],
            'NextToken': 'always-more',
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05', max_pages=2
            )

        assert result['status'] == 'success'
        assert mock_client.list_invoice_summaries.call_count == 2
        assert result['data']['pagination']['has_more'] is True
        assert result['data']['pagination']['next_token'] == 'always-more'

    @pytest.mark.asyncio
    async def test_initial_next_token_forwarded(self, mock_context, sample_summary):
        """A caller-supplied next_token is forwarded on the first API call."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context,
                account_id='123456789012',
                billing_period='2026-05',
                next_token='resume-here',
            )

        assert result['status'] == 'success'
        assert mock_client.list_invoice_summaries.call_args.kwargs['NextToken'] == 'resume-here'

    @pytest.mark.asyncio
    async def test_max_results_forwarded(self, mock_context, sample_summary):
        """max_results is forwarded as the MaxResults request parameter."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05', max_results=25
            )

        assert result['status'] == 'success'
        assert mock_client.list_invoice_summaries.call_args.kwargs['MaxResults'] == 25

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_context):
        """An empty result set returns success with zero total_results."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': []}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05'
            )

        assert result['status'] == 'success'
        assert result['data']['invoice_summaries'] == []
        assert result['data']['pagination']['total_results'] == 0

    @pytest.mark.asyncio
    async def test_api_client_error(self, mock_context):
        """A ClientError from the API is handled and returns an error status."""
        mock_client = MagicMock()
        mock_client.list_invoice_summaries.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListInvoiceSummaries',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_summaries(
                mock_context, account_id='123456789012', billing_period='2026-05'
            )

        assert result['status'] == 'error'


class TestInvoicingServer:
    """FastMCP sub-server registration."""

    def test_server_name(self):
        """The invoicing sub-server is created with the expected name."""
        from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import (
            invoicing_server,
        )

        assert invoicing_server.name == 'invoicing-tools'


class TestInvoicingRouting:
    """Operation routing for the top-level ``invoicing`` tool."""

    @pytest.mark.asyncio
    async def test_routes_list_invoice_summaries(self, mock_context, sample_summary):
        """operation=list_invoice_summaries dispatches to the handler."""
        from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import _invoicing

        mock_client = MagicMock()
        mock_client.list_invoice_summaries.return_value = {'InvoiceSummaries': [sample_summary]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await _invoicing(
                mock_context,
                'list_invoice_summaries',
                account_id='123456789012',
                billing_period='2026-05',
            )

        assert result['status'] == 'success'
        assert result['data']['invoice_summaries'][0]['InvoiceId'] == 'INV-001'

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self, mock_context):
        """An unsupported operation returns a standardized error."""
        from awslabs.billing_cost_management_mcp_server.tools.invoicing_tools import _invoicing

        result = await _invoicing(mock_context, 'not_a_real_operation')

        assert result['status'] == 'error'
        assert 'not_a_real_operation' in result['data']['message']
