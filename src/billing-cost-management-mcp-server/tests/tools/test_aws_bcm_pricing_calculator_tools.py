"""Tests for BCM Pricing Calculator Tools.

This module contains comprehensive tests for all methods in the BCM Pricing Calculator Tools,
ensuring complete code coverage and proper error handling.
"""

import pytest
import time
from awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools import (
    PREFERENCES_NOT_CONFIGURED_ERROR,
    bcm_pricing_calc_core,
    bcm_pricing_calculator_server,
    format_usage_item_response,
    format_workload_estimate_response,
    get_preferences,
    get_workload_estimate,
    list_workload_estimate_usage,
    list_workload_estimates,
)
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta, timezone
from fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_bcm_pricing_calculator_client():
    """Create a mock BCM Pricing Calculator boto3 client."""
    mock_client = MagicMock()

    # Set up mock responses for different operations
    mock_client.get_preferences.return_value = {
        'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
        'memberAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
        'standaloneAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
    }

    mock_client.list_workload_estimates.return_value = {
        'items': [
            {
                'id': 'estimate-123',
                'name': 'Test Workload Estimate',
                'status': 'VALID',
                'rateType': 'BEFORE_DISCOUNTS',
                'createdAt': datetime(2023, 1, 1, 12, 0, 0),
                'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
                'rateTimestamp': datetime(2023, 1, 1, 0, 0, 0),
                'totalCost': 1500.50,
                'costCurrency': 'USD',
            },
            {
                'id': 'estimate-456',
                'name': 'Another Estimate',
                'status': 'UPDATING',
                'rateType': 'AFTER_DISCOUNTS',
                'createdAt': datetime(2023, 2, 1, 10, 0, 0),
                'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
                'rateTimestamp': datetime(2023, 2, 1, 0, 0, 0),
                'totalCost': 2000.75,
                'costCurrency': 'USD',
            },
        ],
        'nextToken': None,
    }

    mock_client.get_workload_estimate.return_value = {
        'id': 'estimate-123',
        'name': 'Test Workload Estimate',
        'status': 'VALID',
        'rateType': 'BEFORE_DISCOUNTS',
        'createdAt': datetime(2023, 1, 1, 12, 0, 0),
        'expiresAt': datetime(2023, 12, 31, 23, 59, 59),
        'rateTimestamp': datetime(2023, 1, 1, 0, 0, 0),
        'totalCost': 1500.50,
        'costCurrency': 'USD',
    }

    mock_client.list_workload_estimate_usage.return_value = {
        'items': [
            {
                'id': 'usage-123',
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'group': 'EC2-Instance',
                'status': 'VALID',
                'currency': 'USD',
                'quantity': {
                    'amount': 744.0,
                    'unit': 'Hrs',
                },
                'cost': 50.25,
                'historicalUsage': {
                    'serviceCode': 'AmazonEC2',
                    'usageType': 'BoxUsage:t3.medium',
                    'operation': 'RunInstances',
                    'location': 'US East (N. Virginia)',
                    'usageAccountId': '123456789012',
                    'billInterval': {
                        'start': datetime(2023, 1, 1),
                        'end': datetime(2023, 1, 31),
                    },
                },
            },
        ],
        'nextToken': None,
    }

    return mock_client


@pytest.mark.asyncio
class TestGetPreferences:
    """Tests for get_preferences function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_success_management_account(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with account_types when management account preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
        }

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        mock_create_client.assert_called_once_with(
            'bcm-pricing-calculator', region_name='us-east-1'
        )
        mock_bcm_pricing_calculator_client.get_preferences.assert_called_once()
        assert 'account_types' in result
        assert 'management account' in result['account_types']
        mock_context.info.assert_called()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_success_member_account(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with account_types when member account preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {
            'memberAccountRateTypeSelections': ['AFTER_DISCOUNTS']
        }

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'member account' in result['account_types']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_success_standalone_account(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with account_types when standalone account preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS']
        }

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'standalone account' in result['account_types']

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_not_configured(
        self, mock_create_client, mock_context, mock_bcm_pricing_calculator_client
    ):
        """Test get_preferences returns dict with error when no preferences are configured."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_bcm_pricing_calculator_client.get_preferences.return_value = {}

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'error' in result
        assert 'BCM Pricing Calculator preferences are not configured' in result['error']
        mock_context.error.assert_called()

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_get_preferences_exception(
        self, mock_handle_error, mock_create_client, mock_context
    ):
        """Test get_preferences handles exceptions properly."""
        # Setup
        error = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'GetPreferences'
        )
        mock_create_client.side_effect = error
        mock_handle_error.return_value = {
            'status': 'error',
            'error_type': 'AccessDenied',
            'message': 'Access denied',
        }

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'get_preferences', 'BCM Pricing Calculator'
        )
        assert 'error' in result
        assert (
            'Failed to check BCM Pricing Calculator preferences: Access denied' in result['error']
        )
        # The AWS classification is kept, not collapsed into "not configured"
        assert result['error_type'] == 'AccessDenied'
        mock_context.error.assert_called()


@pytest.mark.asyncio
class TestListWorkloadEstimates:
    """Tests for list_workload_estimates function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_success(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates returns formatted estimates."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': 'management account'}

        # Execute
        result = await list_workload_estimates(mock_context, max_items=50)

        # Assert
        mock_create_client.assert_called_once_with('bcm-pricing-calculator')
        mock_get_preferences.assert_called_once()
        mock_bcm_pricing_calculator_client.list_workload_estimates.assert_called_once()

        assert result['status'] == 'success'
        assert 'workload_estimates' in result['data']
        assert len(result['data']['workload_estimates']) == 2
        assert result['data']['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 2,
        }
        assert 'total_count' not in result['data']
        assert 'has_more_results' not in result['data']

        # Check first estimate details
        first_estimate = result['data']['workload_estimates'][0]
        assert first_estimate['id'] == 'estimate-123'
        assert first_estimate['name'] == 'Test Workload Estimate'
        assert first_estimate['status'] == 'VALID'
        assert first_estimate['status_indicator'] == 'Valid'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_with_filters(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates with various filters."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': 'management account'}

        # Execute
        result = await list_workload_estimates(
            mock_context,
            created_after='2023-01-01T00:00:00Z',
            created_before='2023-12-31T23:59:59Z',
            expires_after='2023-06-01T00:00:00Z',
            expires_before='2024-01-01T00:00:00Z',
            status_filter='VALID',
            name_filter='Test',
            name_match_option='CONTAINS',
            max_items=25,
        )

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert call_kwargs['maxResults'] == 25
        assert 'createdAtFilter' in call_kwargs
        assert 'expiresAtFilter' in call_kwargs
        assert 'filters' in call_kwargs
        assert len(call_kwargs['filters']) == 2  # status and name filters

        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_list_workload_estimates_preferences_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimates when preferences are not configured."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured'
        }

        # Execute
        result = await list_workload_estimates(mock_context)

        # Assert
        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_list_workload_estimates_preferences_access_denied(
        self, mock_get_preferences, mock_context
    ):
        """An AWS error from the preferences check keeps its error_type."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'Failed to check BCM Pricing Calculator preferences: Access denied',
            'error_type': 'AccessDenied',
        }

        # Execute
        result = await list_workload_estimates(mock_context)

        # Assert
        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'
        assert result['error_type'] == 'AccessDenied'
        assert result['operation'] == 'get_preferences'
        assert result['service'] == 'BCM Pricing Calculator'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_list_workload_estimates_exception(
        self, mock_handle_error, mock_create_client, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimates handles exceptions properly."""
        # Setup
        error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid parameter'}},
            'ListWorkloadEstimates',
        )
        mock_get_preferences.return_value = {'account_types': 'management account'}
        mock_create_client.return_value.list_workload_estimates.side_effect = error
        mock_handle_error.return_value = {'status': 'error', 'message': 'Invalid parameter'}

        # Execute
        result = await list_workload_estimates(mock_context)

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'list_workload_estimates', 'BCM Pricing Calculator'
        )
        assert result['status'] == 'error'


class TestDateFilterOrder:
    """An after bound later than its before bound is rejected locally, before any AWS call.

    The service rejects it too, but with a message that names the bounds the wrong way round.
    """

    @staticmethod
    async def _list(client, **kwargs):
        """Run list_workload_estimates against a client mock with preferences configured."""
        with (
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
                return_value=client,
            ) as create_client,
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences',
                new=AsyncMock(return_value={'account_types': ['management account']}),
            ) as get_prefs,
        ):
            ctx = MagicMock()
            ctx.info = AsyncMock()
            ctx.warning = AsyncMock()
            ctx.error = AsyncMock()
            result = await list_workload_estimates(ctx, **kwargs)
            return result, get_prefs, create_client

    @pytest.mark.asyncio
    @pytest.mark.parametrize('prefix', ['created', 'expires'])
    @pytest.mark.parametrize(
        'after,before',
        [
            ('2026-02-01T00:00:00Z', '2026-01-01T00:00:00Z'),
            ('2026-01-01T00:00:01', '2026-01-01T00:00:00'),
            # Mixed offsets compare as instants: 01:00+00:00 is later than 00:30Z.
            ('2026-01-01T01:00:00+00:00', '2026-01-01T00:30:00Z'),
            # A value without an offset is UTC, as botocore sends it.
            ('2026-01-01T12:00:00', '2026-01-01T11:00:00Z'),
            ('2026-01-01T06:00:00+05:00', '2026-01-01T00:00:00'),
        ],
    )
    async def test_after_later_than_before_is_rejected(self, prefix, after, before):
        """The error names both parameters in the right order, with no AWS call."""
        client = MagicMock()

        result, get_prefs, create_client = await self._list(
            client, **{f'{prefix}_after': after, f'{prefix}_before': before}
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == f'{prefix}_after'
        assert result['data']['value'] == after
        expected = f'{prefix}_after ({after}) is later than {prefix}_before ({before})'
        assert expected in result['message']
        assert 'beforeTimestamp' not in result['message']
        get_prefs.assert_not_called()
        create_client.assert_not_called()
        client.list_workload_estimates.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize('prefix', ['created', 'expires'])
    @pytest.mark.parametrize(
        'after,before',
        [
            ('2026-01-01T00:00:00Z', '2026-02-01T00:00:00Z'),
            # Equal bounds are accepted by the service.
            ('2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
            ('2026-01-01T05:00:00+05:00', '2026-01-01T00:00:00'),
            ('2026-01-01T00:30:00Z', '2026-01-01T01:00:00+00:00'),
        ],
    )
    async def test_ordered_or_equal_bounds_are_sent(self, prefix, after, before):
        """Ordered or equal bounds are sent as UTC instants in the matching filter."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(
            client, **{f'{prefix}_after': after, f'{prefix}_before': before}
        )

        assert result['status'] == 'success'
        sent = client.list_workload_estimates.call_args.kwargs[f'{prefix}AtFilter']
        assert sent['afterTimestamp'] <= sent['beforeTimestamp']
        assert sent['afterTimestamp'].utcoffset() == timedelta(0)
        assert sent['beforeTimestamp'].utcoffset() == timedelta(0)

    @pytest.fixture
    def non_utc_local_time(self, monkeypatch):
        """Run with a non-UTC local zone, so a naive value read as local time would show."""
        if not hasattr(time, 'tzset'):
            pytest.skip('time.tzset is not available on this platform')
        monkeypatch.setenv('TZ', 'America/New_York')
        time.tzset()
        yield
        monkeypatch.undo()
        time.tzset()

    @pytest.mark.asyncio
    @pytest.mark.usefixtures('non_utc_local_time')
    async def test_value_without_offset_is_sent_as_utc(self):
        """A naive value is sent as the same UTC instant botocore would have sent."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        await self._list(client, created_after='2026-01-01T12:00:00')

        sent = client.list_workload_estimates.call_args.kwargs['createdAtFilter']
        assert sent == {'afterTimestamp': datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures('non_utc_local_time')
    async def test_naive_and_utc_bounds_compare_as_utc_off_a_utc_host(self):
        """Naive 12:00 is UTC noon, earlier than 13:00Z, even where local time is not UTC."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(
            client, created_after='2026-01-01T12:00:00', created_before='2026-01-01T13:00:00Z'
        )

        assert result['status'] == 'success'
        sent = client.list_workload_estimates.call_args.kwargs['createdAtFilter']
        assert sent['afterTimestamp'] == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'parameter', ['created_after', 'created_before', 'expires_after', 'expires_before']
    )
    async def test_unparseable_date_is_rejected_before_any_call(self, parameter):
        """A value that is not ISO 8601 returns a validation_error naming it, with no AWS call."""
        client = MagicMock()

        result, get_prefs, create_client = await self._list(client, **{parameter: 'last week'})

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data'] == {'invalid_parameter': parameter, 'value': 'last week'}
        assert f'Invalid {parameter}: last week' in result['message']
        assert 'ISO 8601' in result['message']
        assert '(UTC when no offset is given)' in result['message']
        get_prefs.assert_not_called()
        create_client.assert_not_called()
        client.list_workload_estimates.assert_not_called()

    @pytest.mark.asyncio
    async def test_out_of_range_date_is_rejected_before_any_call(self):
        """A date its offset moves outside the datetime range is a validation_error naming it."""
        client = MagicMock()

        result, get_prefs, create_client = await self._list(
            client, created_before='0001-01-01T00:00:00+05:00'
        )

        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == 'created_before'
        get_prefs.assert_not_called()
        create_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_each_pair_is_checked_independently(self):
        """created_after may be later than expires_before; only bounds of one pair are compared."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(
            client,
            created_after='2026-06-01T00:00:00Z',
            expires_before='2026-01-01T00:00:00Z',
        )

        assert result['status'] == 'success'
        kwargs = client.list_workload_estimates.call_args.kwargs
        assert set(kwargs['createdAtFilter']) == {'afterTimestamp'}
        assert set(kwargs['expiresAtFilter']) == {'beforeTimestamp'}

    @pytest.mark.asyncio
    async def test_core_returns_the_same_rejection(self, mock_context):
        """The tool entry point returns the validation_error without calling the service."""
        with (
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
            ) as create_client,
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
            ) as get_prefs,
        ):
            result = await bcm_pricing_calc_core(
                mock_context,
                operation='list_workload_estimates',
                expires_after='2026-03-01T00:00:00Z',
                expires_before='2026-02-01T00:00:00Z',
            )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == 'expires_after'
        get_prefs.assert_not_called()
        create_client.return_value.list_workload_estimates.assert_not_called()

    @pytest.mark.asyncio
    async def test_served_arg_docs_state_the_order(self):
        """The served schema says each after bound must not be later than its before bound."""
        tool = await bcm_pricing_calculator_server.get_tool('bcm-pricing-calc')
        assert tool is not None
        properties = tool.parameters['properties']

        for prefix in ('created', 'expires'):
            description = properties[f'{prefix}_after']['description']
            assert f'Must not be later than {prefix}_before' in description


@pytest.mark.asyncio
class TestGetWorkloadEstimate:
    """Tests for get_workload_estimate function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_workload_estimate_success(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test get_workload_estimate returns formatted estimate."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': 'management account'}

        # Execute
        result = await get_workload_estimate(mock_context, identifier='estimate-123')

        # Assert
        mock_create_client.assert_called_once_with('bcm-pricing-calculator')
        mock_get_preferences.assert_called_once()
        mock_bcm_pricing_calculator_client.get_workload_estimate.assert_called_once_with(
            identifier='estimate-123'
        )

        assert result['status'] == 'success'
        assert 'workload_estimate' in result['data']
        assert result['data']['identifier'] == 'estimate-123'

        estimate = result['data']['workload_estimate']
        assert estimate['id'] == 'estimate-123'
        assert estimate['name'] == 'Test Workload Estimate'
        assert estimate['status'] == 'VALID'

    async def test_get_workload_estimate_missing_identifier(self, mock_context):
        """Test get_workload_estimate returns error when identifier is missing."""
        # Execute
        result = await get_workload_estimate(mock_context, identifier=None)

        # Assert
        assert result['status'] == 'error'
        assert 'Identifier is required' in result['data']['error']
        assert result['message'] == result['data']['error']
        assert result['data']['error_code'] == 'MISSING_PARAMETER'
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'get_workload_estimate'
        assert result['service'] == 'BCM Pricing Calculator'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_get_workload_estimate_preferences_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test get_workload_estimate when preferences are not configured."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured'
        }

        # Execute
        result = await get_workload_estimate(mock_context, identifier='estimate-123')

        # Assert
        assert result['status'] == 'error'
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'


@pytest.mark.asyncio
class TestListWorkloadEstimateUsage:
    """Tests for list_workload_estimate_usage function."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimate_usage_success(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimate_usage returns formatted usage items."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute
        result = await list_workload_estimate_usage(
            mock_context,
            workload_estimate_id='estimate-123',
            service_code_filter='AmazonEC2',
            max_items=50,
        )

        # Assert
        mock_create_client.assert_called_once_with('bcm-pricing-calculator')
        mock_get_preferences.assert_called_once()
        mock_bcm_pricing_calculator_client.list_workload_estimate_usage.assert_called_once()

        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimate_usage.call_args[1]
        assert call_kwargs['workloadEstimateId'] == 'estimate-123'
        assert call_kwargs['maxResults'] == 50
        assert 'filters' in call_kwargs
        assert len(call_kwargs['filters']) == 1  # service_code_filter

        assert result['status'] == 'success'
        assert 'usage_items' in result['data']
        assert len(result['data']['usage_items']) == 1
        assert result['data']['workload_estimate_id'] == 'estimate-123'

        # Check usage item details
        usage_item = result['data']['usage_items'][0]
        assert usage_item['id'] == 'usage-123'
        assert usage_item['service_code'] == 'AmazonEC2'
        assert usage_item['usage_type'] == 'BoxUsage:t3.medium'

    async def test_list_workload_estimate_usage_missing_id(self, mock_context):
        """Test list_workload_estimate_usage returns error when workload_estimate_id is missing."""
        # Execute
        result = await list_workload_estimate_usage(mock_context, workload_estimate_id=None)

        # Assert
        assert result['status'] == 'error'
        assert 'workload_estimate_id is required' in result['data']['error']
        assert result['message'] == result['data']['error']
        assert result['data']['error_code'] == 'MISSING_PARAMETER'
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'list_workload_estimate_usage'
        assert result['service'] == 'BCM Pricing Calculator'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimate_usage_with_all_filters(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimate_usage with all possible filters."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute
        result = await list_workload_estimate_usage(
            mock_context,
            workload_estimate_id='estimate-123',
            usage_account_id_filter='123456789012',
            service_code_filter='AmazonEC2',
            usage_type_filter='BoxUsage',
            operation_filter='RunInstances',
            location_filter='us-east-1',
            usage_group_filter='EC2-Instance',
            max_items=100,
        )

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimate_usage.call_args[1]
        assert len(call_kwargs['filters']) == 6  # All filters applied
        assert result['status'] == 'success'


class TestFormatWorkloadEstimateResponse:
    """Tests for format_workload_estimate_response function."""

    def test_format_workload_estimate_response_basic(self):
        """Test format_workload_estimate_response with basic fields."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'rateType': 'BEFORE_DISCOUNTS',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['id'] == 'estimate-123'
        assert result['name'] == 'Test Estimate'
        assert result['status'] == 'VALID'
        assert result['rate_type'] == 'BEFORE_DISCOUNTS'
        assert result['status_indicator'] == 'Valid'

    def test_format_workload_estimate_response_with_timestamps(self):
        """Test format_workload_estimate_response with timestamp fields."""
        # Setup
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        expires_at = datetime(2023, 12, 31, 23, 59, 59)
        rate_timestamp = datetime(2023, 1, 1, 0, 0, 0)

        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'UPDATING',
            'createdAt': created_at,
            'expiresAt': expires_at,
            'rateTimestamp': rate_timestamp,
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'created_at' in result
        assert result['created_at']['timestamp'] == created_at.isoformat()
        assert result['created_at']['formatted'] == '2023-01-01 12:00:00 UTC'

        assert 'expires_at' in result
        assert result['expires_at']['timestamp'] == expires_at.isoformat()

        assert 'rate_timestamp' in result
        assert result['rate_timestamp']['timestamp'] == rate_timestamp.isoformat()

        assert result['status_indicator'] == 'Updating'

    def test_format_workload_estimate_response_with_cost(self):
        """Test format_workload_estimate_response with cost information."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'totalCost': 1500.50,
            'costCurrency': 'USD',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'cost' in result
        assert result['cost']['amount'] == 1500.50
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] == 'USD 1,500.50'

    def test_format_workload_estimate_response_with_failure_message(self):
        """Test format_workload_estimate_response with failure message."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'INVALID',
            'failureMessage': 'Invalid configuration detected',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['failure_message'] == 'Invalid configuration detected'
        assert result['status_indicator'] == 'Invalid'

    def test_format_workload_estimate_response_action_needed_status(self):
        """Test format_workload_estimate_response with ACTION_NEEDED status."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'ACTION_NEEDED',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['status_indicator'] == 'Action Needed'

    def test_format_workload_estimate_response_unknown_status(self):
        """Test format_workload_estimate_response with unknown status."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'UNKNOWN_STATUS',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['status_indicator'] == '❓ UNKNOWN_STATUS'


class TestFormatUsageItemResponse:
    """Tests for format_usage_item_response function."""

    def test_format_usage_item_response_basic(self):
        """Test format_usage_item_response with basic fields."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'usageType': 'BoxUsage:t3.medium',
            'operation': 'RunInstances',
            'location': 'US East (N. Virginia)',
            'usageAccountId': '123456789012',
            'group': 'EC2-Instance',
            'status': 'VALID',
            'currency': 'USD',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'
        assert result['usage_type'] == 'BoxUsage:t3.medium'
        assert result['operation'] == 'RunInstances'
        assert result['location'] == 'US East (N. Virginia)'
        assert result['usage_account_id'] == '123456789012'
        assert result['group'] == 'EC2-Instance'
        assert result['status'] == 'VALID'
        assert result['currency'] == 'USD'
        assert result['status_indicator'] == 'Valid'

    def test_format_usage_item_response_with_quantity(self):
        """Test format_usage_item_response with quantity information."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'quantity': {
                'amount': 744.0,
                'unit': 'Hrs',
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'quantity' in result
        assert result['quantity']['amount'] == 744.0
        assert result['quantity']['unit'] == 'Hrs'
        assert result['quantity']['formatted'] == '744.00 Hrs'

    def test_format_usage_item_response_with_cost(self):
        """Test format_usage_item_response with cost information."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'cost': 50.25,
            'currency': 'USD',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'cost' in result
        assert result['cost']['amount'] == 50.25
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] == 'USD 50.25'

    def test_format_usage_item_response_with_historical_usage(self):
        """Test format_usage_item_response with historical usage information."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'billInterval': {
                    'start': datetime(2023, 1, 1),
                    'end': datetime(2023, 1, 31),
                },
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'historical_usage' in result
        historical = result['historical_usage']
        assert historical['service_code'] == 'AmazonEC2'
        assert historical['usage_type'] == 'BoxUsage:t3.medium'
        assert historical['operation'] == 'RunInstances'
        assert historical['location'] == 'US East (N. Virginia)'
        assert historical['usage_account_id'] == '123456789012'
        assert 'bill_interval' in historical
        assert historical['bill_interval']['start'] == '2023-01-01T00:00:00'
        assert historical['bill_interval']['end'] == '2023-01-31T00:00:00'

    def test_format_usage_item_response_quantity_none_amount(self):
        """Test format_usage_item_response with None quantity amount."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'quantity': {
                'amount': None,
                'unit': 'Hrs',
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'quantity' in result
        assert result['quantity']['amount'] is None
        assert result['quantity']['unit'] == 'Hrs'
        assert result['quantity']['formatted'] is None

    def test_format_usage_item_response_stale_status(self):
        """Test format_usage_item_response with STALE status."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'STALE',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['status_indicator'] == 'Stale'

    def test_format_usage_item_response_invalid_status(self):
        """Test format_usage_item_response with INVALID status."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'INVALID',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['status_indicator'] == 'Invalid'

    def test_format_usage_item_response_unknown_status(self):
        """Test format_usage_item_response with unknown status."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'UNKNOWN_STATUS',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['status_indicator'] == '❓ UNKNOWN_STATUS'


def test_bcm_pricing_calculator_server_initialization():
    """Test that the bcm_pricing_calculator_server is properly initialized."""
    # Verify the server name
    assert bcm_pricing_calculator_server.name == 'bcm-pricing-calc-tools'

    # Verify the server instructions
    instructions = bcm_pricing_calculator_server.instructions
    assert instructions is not None
    assert 'BCM Pricing Calculator tools' in instructions


class TestAdditionalFormattingCases:
    """Tests for additional formatting edge cases to achieve complete coverage."""

    def test_format_usage_item_response_no_quantity(self):
        """Test format_usage_item_response with no quantity field."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'VALID',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'quantity' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'
        assert result['status'] == 'VALID'

    def test_format_usage_item_response_no_cost(self):
        """Test format_usage_item_response with no cost field."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'status': 'VALID',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'cost' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'

    def test_format_usage_item_response_no_status(self):
        """Test format_usage_item_response with no status field."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'status_indicator' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'

    def test_format_usage_item_response_default_currency(self):
        """Test format_usage_item_response uses default USD currency."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            # No currency field provided
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert result['currency'] == 'USD'

    def test_format_usage_item_response_historical_usage_no_bill_interval_start_end(self):
        """Test format_usage_item_response with historical usage but no start/end in bill interval."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                'billInterval': {
                    'start': None,
                    'end': None,
                },
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'historical_usage' in result
        historical = result['historical_usage']
        assert 'bill_interval' in historical
        assert historical['bill_interval']['start'] is None
        assert historical['bill_interval']['end'] is None

    def test_format_workload_estimate_response_no_status(self):
        """Test format_workload_estimate_response with no status field."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'rateType': 'BEFORE_DISCOUNTS',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'status_indicator' not in result
        assert result['id'] == 'estimate-123'
        assert result['name'] == 'Test Estimate'

    def test_format_workload_estimate_response_no_failure_message(self):
        """Test format_workload_estimate_response with no failure message."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'failure_message' not in result
        assert result['id'] == 'estimate-123'
        assert result['status'] == 'VALID'


@pytest.mark.asyncio
class TestMissingCoverageBranches:
    """Tests specifically targeting lines 100-148 that are missing coverage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_management_account_only(self, mock_create_client, mock_context):
        """Test get_preferences with only management account preferences (covers lines ~100-110)."""
        # Setup - only management account preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': [
                'BEFORE_DISCOUNTS',
                'AFTER_DISCOUNTS_AND_COMMITMENTS',
            ]
            # No member or standalone account selections
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'management account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the specific log message for management account
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any('management account' in call for call in info_calls)

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_member_account_only(self, mock_create_client, mock_context):
        """Test get_preferences with only member account preferences (covers lines ~100-110)."""
        # Setup - only member account preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'memberAccountRateTypeSelections': ['BEFORE_DISCOUNTS']
            # No management or standalone account selections
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'member account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the specific log message for member account
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any('member account' in call for call in info_calls)

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_standalone_account_only(self, mock_create_client, mock_context):
        """Test get_preferences with only standalone account preferences (covers lines ~100-110)."""
        # Setup - only standalone account preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS']
            # No management or member account selections
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'standalone account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the specific log message for standalone account
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        assert any('standalone account' in call for call in info_calls)

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_get_preferences_multiple_account_types(self, mock_create_client, mock_context):
        """Test get_preferences with multiple account type preferences (covers lines ~100-110)."""
        # Setup - multiple account type preferences
        mock_client = MagicMock()
        mock_client.get_preferences.return_value = {
            'managementAccountRateTypeSelections': ['BEFORE_DISCOUNTS'],
            'memberAccountRateTypeSelections': ['AFTER_DISCOUNTS'],
            'standaloneAccountRateTypeSelections': ['AFTER_DISCOUNTS_AND_COMMITMENTS'],
        }
        mock_create_client.return_value = mock_client

        # Execute
        result = await get_preferences(mock_context)

        # Assert
        assert 'account_types' in result
        assert 'management account' in result['account_types']
        assert 'member account' in result['account_types']
        assert 'standalone account' in result['account_types']
        mock_context.info.assert_called()
        # Verify the log message contains all account types
        info_calls = [call.args[0] for call in mock_context.info.call_args_list]
        combined_message = ' '.join(info_calls)
        assert 'management account' in combined_message
        assert 'member account' in combined_message
        assert 'standalone account' in combined_message

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_created_after_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for created_after only (covers lines ~120-130)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only created_after
        result = await list_workload_estimates(mock_context, created_after='2023-01-01T00:00:00Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'createdAtFilter' in call_kwargs
        created_filter = call_kwargs['createdAtFilter']
        assert 'afterTimestamp' in created_filter
        assert 'beforeTimestamp' not in created_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_created_before_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for created_before only (covers lines ~120-130)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only created_before
        result = await list_workload_estimates(mock_context, created_before='2023-12-31T23:59:59Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'createdAtFilter' in call_kwargs
        created_filter = call_kwargs['createdAtFilter']
        assert 'beforeTimestamp' in created_filter
        assert 'afterTimestamp' not in created_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_expires_after_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for expires_after only (covers lines ~130-140)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only expires_after
        result = await list_workload_estimates(mock_context, expires_after='2023-06-01T00:00:00Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'expiresAtFilter' in call_kwargs
        expires_filter = call_kwargs['expiresAtFilter']
        assert 'afterTimestamp' in expires_filter
        assert 'beforeTimestamp' not in expires_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_datetime_parsing_expires_before_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates datetime parsing for expires_before only (covers lines ~130-140)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only expires_before
        result = await list_workload_estimates(mock_context, expires_before='2024-01-01T00:00:00Z')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'expiresAtFilter' in call_kwargs
        expires_filter = call_kwargs['expiresAtFilter']
        assert 'beforeTimestamp' in expires_filter
        assert 'afterTimestamp' not in expires_filter
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_filter_building_status_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates filter building for status only (covers lines ~140-148)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only status filter
        result = await list_workload_estimates(mock_context, status_filter='VALID')

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'filters' in call_kwargs
        filters = call_kwargs['filters']
        assert len(filters) == 1
        assert filters[0]['name'] == 'STATUS'
        assert filters[0]['values'] == ['VALID']
        assert filters[0]['matchOption'] == 'EQUALS'
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_filter_building_name_only(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates filter building for name only (covers lines ~140-148)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with only name filter
        result = await list_workload_estimates(
            mock_context, name_filter='Test', name_match_option='STARTS_WITH'
        )

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        assert 'filters' in call_kwargs
        filters = call_kwargs['filters']
        assert len(filters) == 1
        assert filters[0]['name'] == 'NAME'
        assert filters[0]['values'] == ['Test']
        assert filters[0]['matchOption'] == 'STARTS_WITH'
        assert result['status'] == 'success'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_list_workload_estimates_no_filters_applied(
        self,
        mock_create_client,
        mock_get_preferences,
        mock_context,
        mock_bcm_pricing_calculator_client,
    ):
        """Test list_workload_estimates with no filters (covers the filters conditional logic)."""
        # Setup
        mock_create_client.return_value = mock_bcm_pricing_calculator_client
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute with no filters
        result = await list_workload_estimates(mock_context)

        # Assert
        call_kwargs = mock_bcm_pricing_calculator_client.list_workload_estimates.call_args[1]
        # Should not have filters key when no filters are applied
        assert 'filters' not in call_kwargs or not call_kwargs.get('filters')
        assert result['status'] == 'success'


@pytest.mark.asyncio
class TestAdditionalConditionalBranches:
    """Tests for additional conditional branches to achieve complete coverage."""


@pytest.mark.asyncio
class TestListWorkloadEstimateUsagePreferencesNotConfigured:
    """Test for line 476 - preferences not configured in list_workload_estimate_usage."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_list_workload_estimate_usage_preferences_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimate_usage when preferences are not configured (line 476)."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured - no rate type selections found'
        }

        # Execute
        result = await list_workload_estimate_usage(
            mock_context, workload_estimate_id='estimate-123'
        )

        # Assert
        assert result['status'] == 'error'
        assert (
            result['data']['error']
            == 'BCM Pricing Calculator preferences are not configured - no rate type selections found'
        )
        assert result['data']['error_code'] == 'PREFERENCES_NOT_CONFIGURED'


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @staticmethod
    async def _call(handler, client, **kwargs):
        """Run a list handler against a client mock with preferences configured."""
        with (
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences',
                new=AsyncMock(return_value={'account_types': ['management account']}),
            ),
        ):
            ctx = MagicMock()
            ctx.info = AsyncMock()
            ctx.warning = AsyncMock()
            ctx.error = AsyncMock()
            return await handler(ctx, **kwargs)

    @pytest.mark.asyncio
    async def test_list_workload_estimates_fetches_every_page(self):
        """Without max_items every page is fetched at the largest page size."""
        client = MagicMock()
        client.list_workload_estimates.side_effect = [
            {'items': [{'id': 'e1'}], 'nextToken': 'p2'},
            {'items': [{'id': 'e2'}], 'nextToken': 'p3'},
            {'items': [{'id': 'e3'}]},
        ]

        result = await self._call(list_workload_estimates, client, status_filter='VALID')

        calls = client.list_workload_estimates.call_args_list
        assert [call.kwargs.get('nextToken') for call in calls] == [None, 'p2', 'p3']
        assert all(call.kwargs['maxResults'] == 25 for call in calls)
        data = result['data']
        assert [e['id'] for e in data['workload_estimates']] == ['e1', 'e2', 'e3']
        assert data['pagination']['complete_dataset'] is True
        assert data['pagination']['items_returned'] == 3
        assert 'warning' not in data

    @pytest.mark.asyncio
    async def test_list_workload_estimates_max_items_stops(self):
        """max_items sizes the page and stops once reached, returning the service token."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {
            'items': [{'id': 'e1'}, {'id': 'e2'}],
            'nextToken': 'p2',
        }

        result = await self._call(list_workload_estimates, client, max_items=2)

        assert client.list_workload_estimates.call_count == 1
        assert client.list_workload_estimates.call_args.kwargs['maxResults'] == 2
        data = result['data']
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert data['pagination'] == {
            'complete_dataset': False,
            'has_more': True,
            'next_token': 'p2',
            'items_returned': 2,
        }

    @pytest.mark.asyncio
    async def test_list_workload_estimates_continuation_identical_params(self):
        """A continuation sends the caller's token and otherwise the same request."""
        client = MagicMock()
        client.list_workload_estimates.side_effect = [
            {'items': [{'id': 'e1'}], 'nextToken': 'p2'},
            {'items': [{'id': 'e2'}]},
        ]
        kwargs = {'name_filter': 'Test', 'created_after': '2023-01-01T00:00:00Z', 'max_items': 1}

        await self._call(list_workload_estimates, client, **kwargs)
        result = await self._call(list_workload_estimates, client, next_token='p2', **kwargs)

        first, resumed = (c.kwargs for c in client.list_workload_estimates.call_args_list)
        assert resumed == {**first, 'nextToken': 'p2'}
        assert result['data']['pagination']['complete_dataset'] is True

    @pytest.mark.asyncio
    async def test_list_workload_estimate_usage_fetches_every_page(self):
        """Without max_items every usage page is fetched at the largest page size."""
        client = MagicMock()
        client.list_workload_estimate_usage.side_effect = [
            {'items': [{'id': 'u1'}], 'nextToken': 'p2'},
            {'items': [{'id': 'u2'}]},
        ]

        result = await self._call(
            list_workload_estimate_usage, client, workload_estimate_id='estimate-123'
        )

        calls = client.list_workload_estimate_usage.call_args_list
        assert [call.kwargs for call in calls] == [
            {'workloadEstimateId': 'estimate-123', 'maxResults': 300},
            {'workloadEstimateId': 'estimate-123', 'maxResults': 300, 'nextToken': 'p2'},
        ]
        data = result['data']
        assert [u['id'] for u in data['usage_items']] == ['u1', 'u2']
        assert data['workload_estimate_id'] == 'estimate-123'
        assert data['pagination']['complete_dataset'] is True
        assert 'total_count' not in data

    @pytest.mark.asyncio
    async def test_list_workload_estimate_usage_max_items_stops(self):
        """max_items stops the usage walk and returns the service token."""
        client = MagicMock()
        client.list_workload_estimate_usage.return_value = {
            'items': [{'id': 'u1'}],
            'nextToken': 'usage-next-token',
        }

        result = await self._call(
            list_workload_estimate_usage,
            client,
            workload_estimate_id='estimate-123',
            max_items=1,
        )

        assert client.list_workload_estimate_usage.call_args.kwargs['maxResults'] == 1
        data = result['data']
        assert data['complete_dataset'] is False
        assert data['pagination']['next_token'] == 'usage-next-token'
        assert data['pagination']['has_more'] is True

    @pytest.mark.asyncio
    async def test_list_workload_estimate_usage_continuation_identical_params(self):
        """A usage continuation sends the caller's token and otherwise the same request."""
        client = MagicMock()
        client.list_workload_estimate_usage.side_effect = [
            {'items': [{'id': 'u1'}], 'nextToken': 'p2'},
            {'items': [{'id': 'u2'}]},
        ]
        kwargs = {
            'workload_estimate_id': 'estimate-123',
            'service_code_filter': 'AmazonEC2',
            'max_items': 1,
        }

        await self._call(list_workload_estimate_usage, client, **kwargs)
        await self._call(list_workload_estimate_usage, client, next_token='p2', **kwargs)

        first, resumed = (c.kwargs for c in client.list_workload_estimate_usage.call_args_list)
        assert resumed == {**first, 'nextToken': 'p2'}

    @pytest.mark.asyncio
    async def test_rejected_token_is_invalid_next_token(self):
        """A token the service rejects maps to invalid_next_token."""
        client = MagicMock()
        client.list_workload_estimates.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad'}},
            'ListWorkloadEstimates',
        )

        result = await self._call(list_workload_estimates, client, next_token='stale')

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'

    def test_format_workload_estimate_response_with_string_timestamps(self):
        """Test format_workload_estimate_response with string timestamps."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'createdAt': '2023-01-01T12:00:00Z',
            'expiresAt': '2023-12-31T23:59:59Z',
            'rateTimestamp': '2023-01-01T00:00:00Z',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert result['created_at']['timestamp'] == '2023-01-01T12:00:00Z'
        assert result['created_at']['formatted'] == '2023-01-01T12:00:00Z'
        assert result['expires_at']['timestamp'] == '2023-12-31T23:59:59Z'
        assert result['rate_timestamp']['timestamp'] == '2023-01-01T00:00:00Z'

    def test_format_workload_estimate_response_none_cost(self):
        """Test format_workload_estimate_response with None total cost."""
        # Setup
        estimate = {
            'id': 'estimate-123',
            'name': 'Test Estimate',
            'status': 'VALID',
            'totalCost': None,
            'costCurrency': 'USD',
        }

        # Execute
        result = format_workload_estimate_response(estimate)

        # Assert
        assert 'cost' in result
        assert result['cost']['amount'] is None
        assert result['cost']['currency'] == 'USD'
        assert result['cost']['formatted'] is None

    def test_format_usage_item_response_no_historical_bill_interval(self):
        """Test format_usage_item_response with historical usage but no bill interval."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {
                'serviceCode': 'AmazonEC2',
                'usageType': 'BoxUsage:t3.medium',
                'operation': 'RunInstances',
                'location': 'US East (N. Virginia)',
                'usageAccountId': '123456789012',
                # No billInterval
            },
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        assert 'historical_usage' in result
        historical = result['historical_usage']
        assert 'bill_interval' not in historical

    def test_format_usage_item_response_empty_historical_usage(self):
        """Test format_usage_item_response with empty historical usage."""
        # Setup
        usage_item = {
            'id': 'usage-123',
            'serviceCode': 'AmazonEC2',
            'historicalUsage': {},
        }

        # Execute
        result = format_usage_item_response(usage_item)

        # Assert
        # Empty historicalUsage dict should not add historical_usage to result
        assert 'historical_usage' not in result
        assert result['id'] == 'usage-123'
        assert result['service_code'] == 'AmazonEC2'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_get_workload_estimate_exception(
        self, mock_handle_error, mock_create_client, mock_get_preferences, mock_context
    ):
        """Test get_workload_estimate handles exceptions properly."""
        # Setup
        error = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Estimate not found'}},
            'GetWorkloadEstimate',
        )
        mock_get_preferences.return_value = {'account_types': ['management account']}
        mock_create_client.return_value.get_workload_estimate.side_effect = error
        mock_handle_error.return_value = {'status': 'error', 'message': 'Estimate not found'}

        # Execute
        result = await get_workload_estimate(mock_context, identifier='nonexistent-estimate')

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'get_workload_estimate', 'BCM Pricing Calculator'
        )
        assert result['status'] == 'error'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_list_workload_estimate_usage_exception(
        self, mock_handle_error, mock_create_client, mock_get_preferences, mock_context
    ):
        """Test list_workload_estimate_usage handles exceptions properly."""
        # Setup
        error = BotoCoreError()
        mock_get_preferences.return_value = {'account_types': ['management account']}
        mock_create_client.return_value.list_workload_estimate_usage.side_effect = error
        mock_handle_error.return_value = {'status': 'error', 'message': 'Connection error'}

        # Execute
        result = await list_workload_estimate_usage(
            mock_context, workload_estimate_id='estimate-123'
        )

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context, error, 'list_workload_estimate_usage', 'BCM Pricing Calculator'
        )
        assert result['status'] == 'error'


@pytest.mark.parametrize(
    'status,expected_indicator',
    [
        ('VALID', 'Valid'),
        ('UPDATING', 'Updating'),
        ('INVALID', 'Invalid'),
        ('ACTION_NEEDED', 'Action Needed'),
        ('UNKNOWN', '❓ UNKNOWN'),
    ],
)
def test_format_workload_estimate_response_status_indicators(status, expected_indicator):
    """Test format_workload_estimate_response status indicators."""
    # Setup
    estimate = {
        'id': 'estimate-123',
        'name': 'Test Estimate',
        'status': status,
    }

    # Execute
    result = format_workload_estimate_response(estimate)

    # Assert
    assert result['status_indicator'] == expected_indicator


@pytest.mark.parametrize(
    'status,expected_indicator',
    [
        ('VALID', 'Valid'),
        ('INVALID', 'Invalid'),
        ('STALE', 'Stale'),
        ('UNKNOWN', '❓ UNKNOWN'),
    ],
)
def test_format_usage_item_response_status_indicators(status, expected_indicator):
    """Test format_usage_item_response status indicators."""
    # Setup
    usage_item = {
        'id': 'usage-123',
        'serviceCode': 'AmazonEC2',
        'status': status,
    }

    # Execute
    result = format_usage_item_response(usage_item)

    # Assert
    assert result['status_indicator'] == expected_indicator


@pytest.mark.asyncio
class TestBcmPricingCalcCoreFunction:
    """Tests for the core bcm_pricing_calc_core function (lines 101-149)."""

    async def test_bcm_pricing_calc_core_invalid_operation(self, mock_context):
        """Test bcm_pricing_calc_core with invalid operation (covers lines 106-113)."""
        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='invalid_operation')

        # Assert
        assert result['status'] == 'error'
        assert 'Invalid operation' in result['message']
        assert 'invalid_parameter' in result['data']
        # The message lists the operations the tool actually accepts
        assert (
            'get_workload_estimate, list_workload_estimates, list_workload_estimate_usage, '
            'get_preferences' in result['message']
        )
        assert result['error_type'] == 'validation_error'
        assert result['operation'] == 'invalid_operation'
        assert result['service'] == 'BCM Pricing Calculator'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: invalid_operation'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_workload_estimate'
    )
    async def test_bcm_pricing_calc_core_get_workload_estimate_operation(
        self, mock_get_workload_estimate, mock_context
    ):
        """Test bcm_pricing_calc_core with get_workload_estimate operation (covers lines 115-117)."""
        # Setup
        mock_get_workload_estimate.return_value = {
            'status': 'success',
            'data': {'workload_estimate': {}},
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context, operation='get_workload_estimate', identifier='estimate-123'
        )

        # Assert
        mock_get_workload_estimate.assert_called_once_with(mock_context, 'estimate-123')
        assert result['status'] == 'success'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: get_workload_estimate'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.list_workload_estimates'
    )
    async def test_bcm_pricing_calc_core_list_workload_estimates_operation(
        self, mock_list_workload_estimates, mock_context
    ):
        """Test bcm_pricing_calc_core with list_workload_estimates operation (covers lines 118-121)."""
        # Setup
        mock_list_workload_estimates.return_value = {
            'status': 'success',
            'data': {'workload_estimates': []},
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context,
            operation='list_workload_estimates',
            created_after='2023-01-01T00:00:00Z',
            created_before='2023-12-31T23:59:59Z',
            expires_after='2023-06-01T00:00:00Z',
            expires_before='2024-01-01T00:00:00Z',
            status_filter='VALID',
            name_filter='Test',
            name_match_option='CONTAINS',
            next_token='token123',
            max_items=50,
        )

        # Assert
        mock_list_workload_estimates.assert_called_once_with(
            mock_context,
            '2023-01-01T00:00:00Z',
            '2023-12-31T23:59:59Z',
            '2023-06-01T00:00:00Z',
            '2024-01-01T00:00:00Z',
            'VALID',
            'Test',
            'CONTAINS',
            'token123',
            50,
        )
        assert result['status'] == 'success'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: list_workload_estimates'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.list_workload_estimate_usage'
    )
    async def test_bcm_pricing_calc_core_list_workload_estimate_usage_operation(
        self, mock_list_usage, mock_context
    ):
        """Test bcm_pricing_calc_core with list_workload_estimate_usage operation (covers lines 122-125)."""
        # Setup
        mock_list_usage.return_value = {'status': 'success', 'data': {'usage_items': []}}

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context,
            operation='list_workload_estimate_usage',
            identifier='estimate-123',
            usage_account_id_filter='123456789012',
            service_code_filter='AmazonEC2',
            usage_type_filter='BoxUsage',
            operation_filter='RunInstances',
            location_filter='us-east-1',
            usage_group_filter='EC2-Instance',
            next_token='usage-token',
            max_items=100,
        )

        # Assert
        mock_list_usage.assert_called_once_with(
            mock_context,
            'estimate-123',
            '123456789012',
            'AmazonEC2',
            'BoxUsage',
            'RunInstances',
            'us-east-1',
            'EC2-Instance',
            'usage-token',
            100,
        )
        assert result['status'] == 'success'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: list_workload_estimate_usage'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_bcm_pricing_calc_core_get_preferences_operation_success(
        self, mock_get_preferences, mock_context
    ):
        """Test bcm_pricing_calc_core with get_preferences operation - success case (covers lines 126-133)."""
        # Setup
        mock_get_preferences.return_value = {'account_types': ['management account']}

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='get_preferences')

        # Assert
        mock_get_preferences.assert_called_once_with(mock_context)
        assert result['status'] == 'success'
        assert result['data']['message'] == 'Preferences are properly configured'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: get_preferences'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences'
    )
    async def test_bcm_pricing_calc_core_get_preferences_operation_not_configured(
        self, mock_get_preferences, mock_context
    ):
        """Test bcm_pricing_calc_core with get_preferences operation - not configured case (covers lines 127-131)."""
        # Setup
        mock_get_preferences.return_value = {
            'error': 'BCM Pricing Calculator preferences are not configured. Please configure preferences before using this service.'
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='get_preferences')

        # Assert
        mock_get_preferences.assert_called_once_with(mock_context)
        assert result['status'] == 'error'
        assert result['data']['error'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['message'] == PREFERENCES_NOT_CONFIGURED_ERROR
        assert result['error_type'] == 'PREFERENCES_NOT_CONFIGURED'
        assert result['operation'] == 'get_preferences'
        assert result['service'] == 'BCM Pricing Calculator'
        mock_context.info.assert_called_with(
            'Received BCM Pricing Calculator operation: get_preferences'
        )

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_workload_estimate'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_bcm_pricing_calc_core_exception_handling(
        self, mock_handle_error, mock_get_workload_estimate, mock_context
    ):
        """Test bcm_pricing_calc_core exception handling (covers lines 137-149)."""
        # Setup
        test_error = Exception('Test error')
        mock_get_workload_estimate.side_effect = test_error
        mock_handle_error.return_value = {
            'status': 'error',
            'error_type': 'ValidationException',
            'message': 'Test error message',
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(
            mock_context, operation='get_workload_estimate', identifier='estimate-123'
        )

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context,
            test_error,
            'get_workload_estimate',
            'BCM Pricing Calculator',
        )
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in error_call_args
        )
        assert 'Test error message' in error_call_args

        assert result['status'] == 'error'
        assert result['data']['error'] == 'Test error message'
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in result['message']
        )
        assert result['error_type'] == 'ValidationException'
        assert result['operation'] == 'get_workload_estimate'
        assert result['service'] == 'BCM Pricing Calculator'

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.list_workload_estimates'
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.handle_aws_error'
    )
    async def test_bcm_pricing_calc_core_exception_handling_no_error_in_response(
        self, mock_handle_error, mock_list_estimates, mock_context
    ):
        """Test bcm_pricing_calc_core exception handling when error response has no error field (covers lines 137-149)."""
        # Setup
        test_error = Exception('Direct error message')
        mock_list_estimates.side_effect = test_error
        mock_handle_error.return_value = {
            'status': 'error',  # No message field
        }

        # Execute - call the core function directly
        result = await bcm_pricing_calc_core(mock_context, operation='list_workload_estimates')

        # Assert
        mock_handle_error.assert_called_once_with(
            mock_context,
            test_error,
            'list_workload_estimates',
            'BCM Pricing Calculator',
        )
        mock_context.error.assert_called_once()
        error_call_args = mock_context.error.call_args[0][0]
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in error_call_args
        )
        assert 'Direct error message' in error_call_args

        assert result['status'] == 'error'
        assert result['data']['error'] == 'Direct error message'
        assert (
            'Failed to process AWS Billing and Cost Management Pricing Calculator request'
            in result['message']
        )


class TestNameMatchOptionValidation:
    """name_match_option must be EQUALS, STARTS_WITH or CONTAINS; the service rejects any other casing."""

    @staticmethod
    async def _list(client, **kwargs):
        """Run list_workload_estimates against a client mock with preferences configured."""
        with (
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
                return_value=client,
            ) as create_client,
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences',
                new=AsyncMock(return_value={'account_types': ['management account']}),
            ) as get_prefs,
        ):
            ctx = MagicMock()
            ctx.info = AsyncMock()
            ctx.error = AsyncMock()
            result = await list_workload_estimates(ctx, **kwargs)
            return result, create_client, get_prefs

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'given,sent',
        [
            ('CONTAINS', 'CONTAINS'),
            ('contains', 'CONTAINS'),
            ('Equals', 'EQUALS'),
            (' starts_with ', 'STARTS_WITH'),
        ],
    )
    async def test_match_option_is_upper_cased(self, given, sent):
        """Any casing of a valid option is sent upper-cased; the name value is sent unchanged."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(client, name_filter='Demo', name_match_option=given)

        assert result['status'] == 'success'
        filters = client.list_workload_estimates.call_args.kwargs['filters']
        assert filters == [{'name': 'NAME', 'values': ['Demo'], 'matchOption': sent}]

    @pytest.mark.asyncio
    @pytest.mark.parametrize('given', ['LIKE', 'starts with', 'EXACT', '   ', None])
    async def test_unknown_match_option_is_rejected_before_any_call(self, given):
        """A value outside the enum returns validation_error listing the valid values, with no AWS call."""
        client = MagicMock()

        result, create_client, get_prefs = await self._list(
            client, name_filter='Demo', name_match_option=given
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == 'name_match_option'
        assert result['data']['value'] == given
        for option in ('EQUALS', 'STARTS_WITH', 'CONTAINS'):
            assert option in result['message']
        create_client.assert_not_called()
        get_prefs.assert_not_called()

    @pytest.mark.asyncio
    async def test_match_option_is_ignored_without_name_filter(self):
        """name_match_option applies only to name_filter, so it is not checked or sent alone."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(client, name_match_option='LIKE')

        assert result['status'] == 'success'
        assert 'filters' not in client.list_workload_estimates.call_args.kwargs

    @pytest.mark.asyncio
    async def test_empty_name_filter_sends_no_filter(self):
        """An empty name_filter is not sent, so its match option is not checked."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(client, name_filter='', name_match_option='LIKE')

        assert result['status'] == 'success'
        assert 'filters' not in client.list_workload_estimates.call_args.kwargs

    @pytest.mark.asyncio
    async def test_tool_entry_point_rejects_unknown_match_option(self):
        """The validation also applies through bcm_pricing_calc_core, the tool's entry point."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
        ) as create_client:
            ctx = MagicMock()
            ctx.info = AsyncMock()
            ctx.error = AsyncMock()
            result = await bcm_pricing_calc_core(
                ctx,
                operation='list_workload_estimates',
                name_filter='Demo',
                name_match_option='LIKE',
            )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == 'name_match_option'
        create_client.assert_not_called()


class TestFilterArgDocs:
    """The served arg docs state how each filter is matched, since a mismatch returns no rows, not an error."""

    @staticmethod
    async def _docs():
        tool = await bcm_pricing_calculator_server.get_tool('bcm-pricing-calc')
        assert tool is not None
        properties = tool.parameters['properties']
        return {name: ' '.join(spec['description'].split()) for name, spec in properties.items()}

    @pytest.mark.asyncio
    async def test_name_filter_docs_state_case_rules(self):
        """name_filter is case-sensitive; name_match_option lists its values and takes any case."""
        docs = await self._docs()
        assert 'always case-sensitive' in docs['name_filter']
        assert 'EQUALS, STARTS_WITH or CONTAINS' in docs['name_match_option']
        assert 'any case' in docs['name_match_option']
        # The option's case rule must not read as a rule about the name match.
        assert 'case-insensitive' not in docs['name_match_option']

    @pytest.mark.asyncio
    @pytest.mark.parametrize('param', ['usage_type_filter', 'operation_filter'])
    async def test_substring_filters_are_documented(self, param):
        """usage_type_filter and operation_filter are sent as case-sensitive CONTAINS."""
        doc = (await self._docs())[param]
        assert 'CONTAINS' in doc
        assert 'case-sensitive' in doc

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'param',
        [
            'usage_account_id_filter',
            'service_code_filter',
            'location_filter',
            'usage_group_filter',
        ],
    )
    async def test_exact_filters_are_documented(self, param):
        """The other usage filters are sent as EQUALS; the text-valued ones say case-sensitive."""
        doc = (await self._docs())[param]
        assert 'EQUALS' in doc
        # Account IDs are 12 digits, so case does not apply to them.
        if param != 'usage_account_id_filter':
            assert 'case-sensitive' in doc

    @pytest.mark.asyncio
    async def test_operation_filter_warns_about_variants(self):
        """CONTAINS on RunInstances also matches the platform variants such as RunInstances:0002."""
        assert 'RunInstances:0002' in (await self._docs())['operation_filter']

    @pytest.mark.asyncio
    async def test_location_filter_documents_the_location_values(self):
        """Local Zone codes, empty global usage, no AZs, and names that match nothing."""
        doc = ' '.join((await self._docs())['location_filter'].split())
        assert 'usually a region code such as us-east-1' in doc
        assert 'Local Zone or Wavelength Zone code (e.g. us-east-1-lim-1)' in doc
        assert "A region code does not match its Local Zones' lines." in doc
        assert 'empty location, which this tool cannot select' in doc
        assert 'an empty location_filter means no filter' in doc
        assert 'Availability Zone (us-east-1a)' in doc
        assert 'US East (N. Virginia)' in doc
        assert 'Filter usage lines by region code' not in doc
        assert 'location/region' not in doc

    @pytest.mark.asyncio
    async def test_empty_location_filter_sends_no_location_filter(self):
        """An empty location_filter is no filter, so empty-location lines cannot be selected."""
        client = MagicMock()
        client.list_workload_estimate_usage.return_value = {'items': []}
        with (
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences',
                new=AsyncMock(return_value={'account_types': ['management account']}),
            ),
        ):
            ctx = MagicMock()
            ctx.info = AsyncMock()
            await list_workload_estimate_usage(
                ctx, workload_estimate_id='estimate-1', location_filter=''
            )
        assert 'filters' not in client.list_workload_estimate_usage.call_args.kwargs


class TestBcmPricingCalcToolSchema:
    """Tests that the registered bcm-pricing-calc tool exposes per-argument descriptions.

    Regression guard for the defect where the decorated wrapper carried only a one-line
    docstring while the ``Args:`` block lived on the undecorated ``bcm_pricing_calc_core``
    delegate, so FastMCP surfaced no per-parameter descriptions to the model.
    """

    @pytest.mark.asyncio
    async def test_every_tool_param_has_schema_description(self):
        """Every bcm-pricing-calc parameter (excluding ctx) must resolve a description."""
        tool = await bcm_pricing_calculator_server.get_tool('bcm-pricing-calc')
        assert tool is not None, 'bcm-pricing-calc tool should be registered'
        properties = tool.parameters.get('properties', {})

        # ctx is injected by FastMCP and is not part of the exposed input schema.
        assert 'ctx' not in properties

        assert properties, 'Expected the tool to expose input parameters'

        missing = [
            name for name, spec in properties.items() if not spec.get('description', '').strip()
        ]
        assert not missing, f'Tool params missing schema descriptions: {missing}'

    @pytest.mark.asyncio
    async def test_paging_parameters_follow_the_max_items_contract(self):
        """The tool takes max_items/next_token; max_results and max_pages are gone."""
        tool = await bcm_pricing_calculator_server.get_tool('bcm-pricing-calc')
        assert tool is not None
        properties = tool.parameters.get('properties', {})
        description = tool.description or ''

        assert 'max_items' in properties
        assert 'next_token' in properties
        assert 'max_results' not in properties
        assert 'max_pages' not in properties
        assert 'complete_dataset' in description
        assert 'max_results' not in description


class TestNonTransientBotocoreRetryStrategy:
    """The guidance derived from the full error survives the tool's own repackaging."""

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_preferences_expired_sso_token_is_do_not_retry(self, mock_create_client):
        """get_preferences' failure keeps handle_aws_error's do_not_retry."""
        from botocore.exceptions import SSOTokenLoadError

        mock_create_client.side_effect = SSOTokenLoadError(error_msg='token expired')

        result = await bcm_pricing_calc_core(AsyncMock(), 'get_preferences')

        assert result['status'] == 'error'
        assert result['error_type'] == 'aws_connection_error'
        assert result['retry_strategy'] == 'do_not_retry'
        assert result['hint'].startswith('AWS credentials or client configuration')

    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
    )
    async def test_preferences_unmapped_5xx_stays_retryable(self, mock_create_client):
        """An unmapped code with a 5xx status is transient after get_preferences repackages it."""
        mock_create_client.side_effect = ClientError(
            {
                'Error': {'Code': 'SomeServiceFault', 'Message': 'oops'},
                'ResponseMetadata': {'HTTPStatusCode': 503},
            },
            'GetPreferences',
        )

        result = await bcm_pricing_calc_core(AsyncMock(), 'get_preferences')

        assert result['error_type'] == 'SomeServiceFault'
        assert result['retry_strategy'] == 'retry_same_request'

    @pytest.mark.parametrize(
        'error, expected',
        [
            (
                ClientError(
                    {
                        'Error': {'Code': 'SomeServiceFault', 'Message': 'oops'},
                        'ResponseMetadata': {'HTTPStatusCode': 503},
                    },
                    'GetWorkloadEstimate',
                ),
                'retry_same_request',
            ),
            (BotoCoreError(), 'do_not_retry'),
        ],
        ids=['unmapped-5xx', 'non-transient-botocore'],
    )
    @patch(
        'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_workload_estimate'
    )
    async def test_core_repackaging_keeps_guidance(self, mock_get_estimate, error, expected):
        """An error reaching bcm_pricing_calc_core's own handler keeps its derived guidance."""
        mock_get_estimate.side_effect = error

        result = await bcm_pricing_calc_core(
            AsyncMock(), 'get_workload_estimate', identifier='estimate-1'
        )

        assert result['status'] == 'error'
        assert result['retry_strategy'] == expected


class TestStatusFilterValidation:
    """status_filter is matched exactly by the service, so it is normalized and validated locally."""

    @staticmethod
    async def _list(client, **kwargs):
        """Run list_workload_estimates against a client mock with preferences configured."""
        with (
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
                return_value=client,
            ) as create_client,
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences',
                new=AsyncMock(return_value={'account_types': ['management account']}),
            ) as get_prefs,
        ):
            ctx = MagicMock()
            ctx.info = AsyncMock()
            ctx.warning = AsyncMock()
            ctx.error = AsyncMock()
            result = await list_workload_estimates(ctx, **kwargs)
            return result, create_client, get_prefs

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'given,sent',
        [
            ('VALID', 'VALID'),
            ('valid', 'VALID'),
            ('Action_Needed', 'ACTION_NEEDED'),
            (' updating ', 'UPDATING'),
            ('invalid', 'INVALID'),
        ],
    )
    async def test_status_filter_is_upper_cased(self, given, sent):
        """Any casing of a valid status is sent upper-cased, since the service match is case-sensitive."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(client, status_filter=given)

        assert result['status'] == 'success'
        filters = client.list_workload_estimates.call_args.kwargs['filters']
        assert filters == [{'name': 'STATUS', 'values': [sent], 'matchOption': 'EQUALS'}]

    @pytest.mark.asyncio
    @pytest.mark.parametrize('given', ['COMPLETE', 'VALIDATED', 'ACTION NEEDED', '   '])
    async def test_unknown_status_is_rejected_before_any_call(self, given):
        """A value outside the enum returns validation_error listing the valid values, with no AWS call."""
        client = MagicMock()

        result, create_client, get_prefs = await self._list(client, status_filter=given)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data']['invalid_parameter'] == 'status_filter'
        assert result['data']['value'] == given
        for status in ('UPDATING', 'VALID', 'INVALID', 'ACTION_NEEDED'):
            assert status in result['message']
        create_client.assert_not_called()
        get_prefs.assert_not_called()
        client.list_workload_estimates.assert_not_called()

    @pytest.mark.asyncio
    async def test_core_routes_rejection_for_list_operation(self, mock_context):
        """The tool entry point returns the same validation_error for a bad status_filter."""
        with patch(
            'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client'
        ) as create_client:
            result = await bcm_pricing_calc_core(
                mock_context, operation='list_workload_estimates', status_filter='COMPLETE'
            )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        create_client.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'given,sent',
        [
            (['VALID'], ['VALID']),
            (['valid', ' Invalid '], ['VALID', 'INVALID']),
            (['VALID', 'valid', 'ACTION_NEEDED'], ['VALID', 'ACTION_NEEDED']),
        ],
    )
    async def test_status_list_is_sent_as_one_or_filter(self, given, sent):
        """A list of statuses is normalized and sent as one STATUS filter, which the API ORs."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(client, status_filter=given)

        assert result['status'] == 'success'
        filters = client.list_workload_estimates.call_args.kwargs['filters']
        assert filters == [{'name': 'STATUS', 'values': sent, 'matchOption': 'EQUALS'}]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'given,invalid',
        [
            (['VALID', 'COMPLETE'], ['COMPLETE']),
            (['done', 'VALID', '  '], ['done', '  ']),
            (['VALID', 7], [7]),
        ],
    )
    async def test_status_list_with_unknown_values_is_rejected(self, given, invalid):
        """Every unknown entry is named in one validation_error, with no AWS call."""
        client = MagicMock()

        result, create_client, get_prefs = await self._list(client, status_filter=given)

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert result['data'] == {'invalid_parameter': 'status_filter', 'value': invalid}
        for status in ('UPDATING', 'VALID', 'INVALID', 'ACTION_NEEDED'):
            assert status in result['message']
        for entry in invalid:
            assert repr(entry) in result['message']
        create_client.assert_not_called()
        get_prefs.assert_not_called()
        client.list_workload_estimates.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'given,sent',
        [
            ('["valid", "INVALID"]', ['VALID', 'INVALID']),
            (' ["ACTION_NEEDED"] ', ['ACTION_NEEDED']),
        ],
    )
    async def test_json_array_string_is_read_as_a_list(self, given, sent):
        """A list sent as a JSON array string is handled like the list itself."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(client, status_filter=given)

        assert result['status'] == 'success'
        filters = client.list_workload_estimates.call_args.kwargs['filters']
        assert filters == [{'name': 'STATUS', 'values': sent, 'matchOption': 'EQUALS'}]

    @pytest.mark.asyncio
    @pytest.mark.parametrize('given', ['[VALID', '["VALID"'])
    async def test_malformed_json_array_string_is_rejected_as_given(self, given):
        """A string that only looks like a JSON array is checked as one status and refused."""
        client = MagicMock()

        result, create_client, _ = await self._list(client, status_filter=given)

        assert result['error_type'] == 'validation_error'
        assert result['data'] == {'invalid_parameter': 'status_filter', 'value': given}
        assert f'Invalid status_filter: {given}.' in result['message']
        create_client.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize('given', ['', None])
    async def test_empty_string_or_none_sends_no_status_filter(self, given):
        """An empty string or None still means no status filter."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}

        result, _, _ = await self._list(client, status_filter=given)

        assert result['status'] == 'success'
        assert 'filters' not in client.list_workload_estimates.call_args.kwargs

    @pytest.mark.asyncio
    async def test_empty_status_list_is_rejected(self):
        """An empty list is refused locally; the service answers it with an internal-error message."""
        client = MagicMock()

        result, create_client, _ = await self._list(client, status_filter=[])

        assert result['error_type'] == 'validation_error'
        assert result['data'] == {'invalid_parameter': 'status_filter', 'value': []}
        assert 'at least one status' in result['message']
        create_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_core_passes_a_status_list_through(self, mock_context):
        """The tool entry point accepts a list and sends every status in one filter."""
        client = MagicMock()
        client.list_workload_estimates.return_value = {'items': []}
        with (
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.create_aws_client',
                return_value=client,
            ),
            patch(
                'awslabs.billing_cost_management_mcp_server.tools.bcm_pricing_calculator_tools.get_preferences',
                new=AsyncMock(return_value={'account_types': ['management account']}),
            ),
        ):
            result = await bcm_pricing_calc_core(
                mock_context,
                operation='list_workload_estimates',
                status_filter=['valid', 'INVALID'],
            )

        assert result['status'] == 'success'
        assert client.list_workload_estimates.call_args.kwargs['filters'] == [
            {'name': 'STATUS', 'values': ['VALID', 'INVALID'], 'matchOption': 'EQUALS'}
        ]

    @pytest.mark.asyncio
    async def test_schema_accepts_a_string_or_a_list(self):
        """The served schema takes one status or a list, and the description says a list is ORed."""
        tool = await bcm_pricing_calculator_server.get_tool('bcm-pricing-calc')
        assert tool is not None
        prop = tool.parameters['properties']['status_filter']
        types = {t.get('type') for t in prop['anyOf']}
        assert {'string', 'array', 'null'} <= types
        array = next(t for t in prop['anyOf'] if t.get('type') == 'array')
        assert array['items'] == {'type': 'string'}
        text = ' '.join(prop['description'].split())
        assert 'or a list of them' in text
        assert 'matches any of them' in text

    @pytest.mark.asyncio
    async def test_schema_lists_status_values(self):
        """The served status_filter description lists the accepted values."""
        tool = await bcm_pricing_calculator_server.get_tool('bcm-pricing-calc')
        assert tool is not None
        text = ' '.join(tool.parameters['properties']['status_filter']['description'].split())
        assert 'UPDATING, VALID, INVALID, ACTION_NEEDED' in text
