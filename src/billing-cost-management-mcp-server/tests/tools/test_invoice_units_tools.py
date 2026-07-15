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

"""Unit tests for the invoice_units_operations and invoice_units_tools modules."""

import pytest
from awslabs.billing_cost_management_mcp_server.tools.invoice_units_operations import (
    batch_get_invoice_profile,
    get_invoice_unit,
    list_invoice_units,
)
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.invoice_units_operations.create_aws_client'
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
def sample_unit():
    """Return a sample InvoiceUnit as the AWS API would return it."""
    return {
        'InvoiceUnitArn': 'arn:aws:invoicing::123456789012:invoice-unit/abc123',
        'InvoiceReceiver': '123456789012',
        'Name': 'Engineering',
        'Description': 'Engineering business unit',
        'TaxInheritanceDisabled': False,
        'Rule': {'LinkedAccounts': ['123456789012', '210987654321']},
        'LastModified': datetime(2026, 5, 1, tzinfo=timezone.utc),
    }


class TestListInvoiceUnits:
    """list_invoice_units filter construction, pagination, and normalization."""

    @pytest.mark.asyncio
    async def test_no_filters_success(self, mock_context, sample_unit):
        """A bare list call succeeds and sends no Filters."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.return_value = {'InvoiceUnits': [sample_unit]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(mock_context)

        assert result['status'] == 'success'
        assert 'Filters' not in mock_client.list_invoice_units.call_args.kwargs

    @pytest.mark.asyncio
    async def test_filters_are_flattened(self, mock_context, sample_unit):
        """Flattened filter params build the nested Filters structure."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.return_value = {'InvoiceUnits': [sample_unit]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(
                mock_context,
                names=['Engineering'],
                invoice_receivers=['123456789012'],
                accounts=['210987654321'],
                bill_source_accounts=['111122223333'],
            )

        assert result['status'] == 'success'
        filters = mock_client.list_invoice_units.call_args.kwargs['Filters']
        assert filters['Names'] == ['Engineering']
        assert filters['InvoiceReceivers'] == ['123456789012']
        assert filters['Accounts'] == ['210987654321']
        assert filters['BillSourceAccounts'] == ['111122223333']

    @pytest.mark.asyncio
    async def test_as_of_uses_epoch_seconds(self, mock_context, sample_unit):
        """as_of is converted to epoch seconds for the AsOf request field."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.return_value = {'InvoiceUnits': [sample_unit]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(mock_context, as_of='2026-05-01')

        assert result['status'] == 'success'
        assert mock_client.list_invoice_units.call_args.kwargs['AsOf'] == int(
            datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp()
        )

    @pytest.mark.asyncio
    async def test_invalid_as_of_returns_error(self, mock_context):
        """A malformed as_of returns a format error without calling the API."""
        result = await list_invoice_units(mock_context, as_of='not-a-date')

        assert result['status'] == 'error'
        assert 'YYYY-MM-DD' in result['data']['message']

    @pytest.mark.asyncio
    async def test_last_modified_normalized_to_iso(self, mock_context, sample_unit):
        """The LastModified datetime is normalized to an ISO 8601 string."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.return_value = {'InvoiceUnits': [sample_unit]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(mock_context)

        unit = result['data']['invoice_units'][0]
        assert unit['LastModified'] == '2026-05-01T00:00:00'

    @pytest.mark.asyncio
    async def test_pagination_across_pages(self, mock_context, sample_unit):
        """Multiple pages are aggregated and pagination metadata is accurate."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.side_effect = [
            {'InvoiceUnits': [sample_unit], 'NextToken': 'page-2'},
            {'InvoiceUnits': [sample_unit]},
        ]

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(mock_context)

        assert result['status'] == 'success'
        assert mock_client.list_invoice_units.call_count == 2
        assert result['data']['pagination']['total_results'] == 2
        assert result['data']['pagination']['has_more'] is False

    @pytest.mark.asyncio
    async def test_max_results_and_next_token_forwarded(self, mock_context, sample_unit):
        """max_results and next_token are forwarded to the request."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.return_value = {'InvoiceUnits': [sample_unit]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(
                mock_context, max_results=10, next_token='resume-here'
            )

        assert result['status'] == 'success'
        call = mock_client.list_invoice_units.call_args.kwargs
        assert call['MaxResults'] == 10
        assert call['NextToken'] == 'resume-here'

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_context):
        """An empty result set returns success with zero total_results."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.return_value = {'InvoiceUnits': []}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(mock_context)

        assert result['status'] == 'success'
        assert result['data']['invoice_units'] == []
        assert result['data']['pagination']['total_results'] == 0

    @pytest.mark.asyncio
    async def test_api_client_error(self, mock_context):
        """A ClientError from the API returns an error status."""
        mock_client = MagicMock()
        mock_client.list_invoice_units.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListInvoiceUnits',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await list_invoice_units(mock_context)

        assert result['status'] == 'error'


class TestGetInvoiceUnit:
    """get_invoice_unit validation and normalization."""

    @pytest.mark.asyncio
    async def test_missing_arn_returns_error(self, mock_context):
        """An empty invoice_unit_arn returns an error without calling the API."""
        result = await get_invoice_unit(mock_context, invoice_unit_arn='')

        assert result['status'] == 'error'
        assert 'invoice_unit_arn is required' in result['data']['message']

    @pytest.mark.asyncio
    async def test_success_strips_metadata_and_normalizes(self, mock_context, sample_unit):
        """A successful call strips ResponseMetadata and normalizes timestamps."""
        mock_client = MagicMock()
        response = dict(sample_unit)
        response['ResponseMetadata'] = {'RequestId': 'abc'}
        mock_client.get_invoice_unit.return_value = response

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await get_invoice_unit(
                mock_context, invoice_unit_arn=sample_unit['InvoiceUnitArn']
            )

        assert result['status'] == 'success'
        unit = result['data']['invoice_unit']
        assert 'ResponseMetadata' not in unit
        assert unit['LastModified'] == '2026-05-01T00:00:00'

    @pytest.mark.asyncio
    async def test_as_of_forwarded(self, mock_context, sample_unit):
        """as_of is converted to epoch seconds and forwarded."""
        mock_client = MagicMock()
        mock_client.get_invoice_unit.return_value = dict(sample_unit)

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await get_invoice_unit(
                mock_context, invoice_unit_arn=sample_unit['InvoiceUnitArn'], as_of='2026-05-01'
            )

        assert result['status'] == 'success'
        assert mock_client.get_invoice_unit.call_args.kwargs['AsOf'] == int(
            datetime(2026, 5, 1, tzinfo=timezone.utc).timestamp()
        )

    @pytest.mark.asyncio
    async def test_invalid_as_of_returns_error(self, mock_context, sample_unit):
        """A malformed as_of returns a format error."""
        result = await get_invoice_unit(
            mock_context, invoice_unit_arn=sample_unit['InvoiceUnitArn'], as_of='bad'
        )

        assert result['status'] == 'error'
        assert 'YYYY-MM-DD' in result['data']['message']

    @pytest.mark.asyncio
    async def test_api_client_error(self, mock_context):
        """A ClientError from the API returns an error status."""
        mock_client = MagicMock()
        mock_client.get_invoice_unit.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetInvoiceUnit',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await get_invoice_unit(mock_context, invoice_unit_arn='arn:bad')

        assert result['status'] == 'error'


class TestBatchGetInvoiceProfile:
    """batch_get_invoice_profile validation and passthrough."""

    @pytest.mark.asyncio
    async def test_empty_account_ids_returns_error(self, mock_context):
        """An empty account_ids list returns an error without calling the API."""
        result = await batch_get_invoice_profile(mock_context, account_ids=[])

        assert result['status'] == 'error'
        assert 'non-empty' in result['data']['message']

    @pytest.mark.asyncio
    async def test_success_returns_profiles(self, mock_context):
        """A successful call returns the normalized profiles list."""
        mock_client = MagicMock()
        mock_client.batch_get_invoice_profile.return_value = {
            'Profiles': [
                {
                    'AccountId': '123456789012',
                    'ReceiverName': 'Example Corp',
                    'ReceiverEmail': 'ap@example.com',
                    'Issuer': 'Amazon Web Services, Inc.',
                    'TaxRegistrationNumber': 'US123',
                }
            ],
            'ResponseMetadata': {'RequestId': 'abc'},
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await batch_get_invoice_profile(mock_context, account_ids=['123456789012'])

        assert result['status'] == 'success'
        assert result['data']['profiles'][0]['AccountId'] == '123456789012'
        assert mock_client.batch_get_invoice_profile.call_args.kwargs['AccountIds'] == [
            '123456789012'
        ]

    @pytest.mark.asyncio
    async def test_api_client_error(self, mock_context):
        """A ClientError from the API returns an error status."""
        mock_client = MagicMock()
        mock_client.batch_get_invoice_profile.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Bad account'}},
            'BatchGetInvoiceProfile',
        )

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await batch_get_invoice_profile(mock_context, account_ids=['x'])

        assert result['status'] == 'error'


class TestInvoiceUnitsServer:
    """FastMCP sub-server registration."""

    def test_server_name(self):
        """The invoice-units sub-server is created with the expected name."""
        from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
            invoice_units_server,
        )

        assert invoice_units_server.name == 'invoice-units-tools'


class TestInvoiceUnitsRouting:
    """Operation routing for the top-level ``invoice-units`` tool."""

    @pytest.mark.asyncio
    async def test_routes_list_invoice_units(self, mock_context, sample_unit):
        """operation=list_invoice_units dispatches to the handler."""
        from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
            _invoice_units,
        )

        mock_client = MagicMock()
        mock_client.list_invoice_units.return_value = {'InvoiceUnits': [sample_unit]}

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await _invoice_units(mock_context, 'list_invoice_units')

        assert result['status'] == 'success'
        assert result['data']['invoice_units'][0]['Name'] == 'Engineering'

    @pytest.mark.asyncio
    async def test_routes_get_invoice_unit(self, mock_context, sample_unit):
        """operation=get_invoice_unit dispatches to the handler."""
        from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
            _invoice_units,
        )

        mock_client = MagicMock()
        mock_client.get_invoice_unit.return_value = dict(sample_unit)

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await _invoice_units(
                mock_context,
                'get_invoice_unit',
                invoice_unit_arn=sample_unit['InvoiceUnitArn'],
            )

        assert result['status'] == 'success'
        assert result['data']['invoice_unit']['Name'] == 'Engineering'

    @pytest.mark.asyncio
    async def test_routes_batch_get_invoice_profile(self, mock_context):
        """operation=batch_get_invoice_profile dispatches to the handler."""
        from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
            _invoice_units,
        )

        mock_client = MagicMock()
        mock_client.batch_get_invoice_profile.return_value = {
            'Profiles': [{'AccountId': '123456789012', 'ReceiverName': 'Example Corp'}]
        }

        with patch(CREATE_CLIENT_PATH) as mock_create:
            mock_create.return_value = mock_client
            result = await _invoice_units(
                mock_context, 'batch_get_invoice_profile', account_ids=['123456789012']
            )

        assert result['status'] == 'success'
        assert result['data']['profiles'][0]['AccountId'] == '123456789012'

    @pytest.mark.asyncio
    async def test_get_invoice_unit_missing_arn_routes_error(self, mock_context):
        """Routing get_invoice_unit without an ARN returns a standardized error."""
        from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
            _invoice_units,
        )

        result = await _invoice_units(mock_context, 'get_invoice_unit')

        assert result['status'] == 'error'
        assert 'invoice_unit_arn is required' in result['data']['message']

    @pytest.mark.asyncio
    async def test_batch_get_invoice_profile_missing_ids_routes_error(self, mock_context):
        """Routing batch_get_invoice_profile without account_ids returns an error."""
        from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
            _invoice_units,
        )

        result = await _invoice_units(mock_context, 'batch_get_invoice_profile')

        assert result['status'] == 'error'
        assert 'account_ids is required' in result['data']['message']

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_error(self, mock_context):
        """An unsupported operation returns a standardized error."""
        from awslabs.billing_cost_management_mcp_server.tools.invoice_units_tools import (
            _invoice_units,
        )

        result = await _invoice_units(mock_context, 'not_a_real_operation')

        assert result['status'] == 'error'
        assert 'not_a_real_operation' in result['data']['message']
