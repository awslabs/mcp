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

"""Unit tests for the free_tier_usage_tools module.

These tests verify the functionality of AWS Free Tier usage monitoring tools, including:
- Retrieving Free Tier usage information across AWS services
- Tracking usage limits and remaining allowances for eligible services
- Getting usage forecasts and overage alerts for Free Tier resources
- Handling historical usage analysis and trend monitoring
- Error handling for accounts not eligible for Free Tier benefits
"""

import json
import pytest
from awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools import (
    create_free_tier_usage_summary,
    free_tier_usage_server,
    get_free_tier_usage_data,
)
from fastmcp import Context
from fastmcp.tools import FunctionTool
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock(spec=Context)
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


@pytest.fixture
def mock_freetier_client():
    """Create a mock Free Tier boto3 client."""
    mock_client = MagicMock()

    # Mock get_free_tier_usage response
    mock_client.get_free_tier_usage.return_value = {
        'freeTierUsages': [
            {
                'service': 'Amazon EC2',
                'usageType': 'BoxUsage:t2.micro',
                'region': 'us-east-1',
                'limit': {
                    'amount': '750',
                    'unit': 'Hours',
                },
                'usage': {
                    'amount': '250',
                    'unit': 'Hours',
                },
                'remaining': {
                    'amount': '500',
                    'unit': 'Hours',
                },
                'periodStartDate': '2023-01-01',
                'periodEndDate': '2023-02-01',
            },
            {
                'service': 'Amazon S3',
                'usageType': 'TimedStorage-ByteHrs',
                'region': 'us-east-1',
                'limit': {
                    'amount': '5',
                    'unit': 'GB',
                },
                'usage': {
                    'amount': '1',
                    'unit': 'GB',
                },
                'remaining': {
                    'amount': '4',
                    'unit': 'GB',
                },
                'periodStartDate': '2023-01-01',
                'periodEndDate': '2023-02-01',
            },
        ]
    }

    return mock_client


class TestCreateFreeTierUsageSummary:
    """Tests for create_free_tier_usage_summary function."""

    def test_create_free_tier_usage_summary_categories(self):
        """Test create_free_tier_usage_summary categorizes services correctly."""
        # Setup
        free_tier_usages = [
            {
                'service': 'Amazon EC2',
                'usageType': 'BoxUsage:t2.micro',
                'actualUsageAmount': 250,
                'limit': 750,
                'unit': 'Hours',
            },
            {
                'service': 'Amazon S3',
                'usageType': 'TimedStorage-ByteHrs',
                'actualUsageAmount': 4.5,
                'limit': 5,
                'unit': 'GB',
            },
            {
                'service': 'AWS Lambda',
                'usageType': 'Requests',
                'actualUsageAmount': 0,
                'limit': 1000000,
                'unit': 'Requests',
            },
        ]

        # Execute
        result = create_free_tier_usage_summary(free_tier_usages)

        # Assert
        assert 'at_limit_count' in result
        assert 'near_limit_count' in result
        assert 'safe_count' in result

        # Check categorization
        assert result['near_limit_count'] == 1  # S3 at 90% usage
        assert result['safe_count'] == 2  # EC2 and Lambda

    def test_create_free_tier_usage_summary_sorting(self):
        """Test create_free_tier_usage_summary sorts services by usage percentage."""
        # Setup
        free_tier_usages = [
            {
                'service': 'Service A',
                'usageType': 'TypeA',
                'actualUsageAmount': 20,
                'limit': 100,
                'unit': 'Units',
            },
            {
                'service': 'Service C',
                'usageType': 'TypeC',
                'actualUsageAmount': 80,
                'limit': 100,
                'unit': 'Units',
            },
            {
                'service': 'Service B',
                'usageType': 'TypeB',
                'actualUsageAmount': 50,
                'limit': 100,
                'unit': 'Units',
            },
            {
                'service': 'Service D',
                'usageType': 'TypeD',
                'actualUsageAmount': 95,
                'limit': 100,
                'unit': 'Units',
            },
        ]

        # Execute
        result = create_free_tier_usage_summary(free_tier_usages)

        # Assert
        assert 'at_limit_items' in result
        assert 'near_limit_items' in result

        # Check sorting (highest usage first)
        if len(result['near_limit_items']) >= 2:
            assert result['near_limit_items'][0]['service'] == 'Service D'
            assert result['near_limit_items'][1]['service'] == 'Service C'

    def test_create_free_tier_usage_summary_empty_input(self):
        """Test create_free_tier_usage_summary handles empty input."""
        # Setup
        free_tier_usages = []

        # Execute
        result = create_free_tier_usage_summary(free_tier_usages)

        # Assert
        assert 'at_limit_count' in result
        assert 'near_limit_count' in result
        assert 'safe_count' in result
        assert 'unknown_count' in result

        # Check that all counts are zero
        assert result['at_limit_count'] == 0
        assert result['near_limit_count'] == 0
        assert result['safe_count'] == 0
        assert result['unknown_count'] == 0
        assert result['total_services'] == 0

    def test_create_free_tier_usage_summary_edge_cases(self):
        """Test create_free_tier_usage_summary handles edge cases."""
        # Setup
        free_tier_usages = [
            # At exact 50% threshold
            {
                'service': 'Service A',
                'usageType': 'TypeA',
                'actualUsageAmount': 50,
                'limit': 100,
                'unit': 'Units',
            },
            # At exact 80% threshold (boundary for near_limit)
            {
                'service': 'Service B',
                'usageType': 'TypeB',
                'actualUsageAmount': 80,
                'limit': 100,
                'unit': 'Units',
            },
            # 100% usage
            {
                'service': 'Service C',
                'usageType': 'TypeC',
                'actualUsageAmount': 100,
                'limit': 100,
                'unit': 'Units',
            },
            # Missing needed values
            {'service': 'Service D', 'usageType': 'TypeD'},
        ]

        # Execute
        result = create_free_tier_usage_summary(free_tier_usages)

        # Assert
        assert result['safe_count'] == 1  # Service A (50%)
        assert result['near_limit_count'] == 1  # Service B (80%)
        assert result['at_limit_count'] == 1  # Service C (100%)
        assert result['unknown_count'] == 1  # Service D (missing data)


@pytest.mark.asyncio
class TestGetFreeTierUsageData:
    """Tests for get_free_tier_usage_data function."""

    async def test_get_free_tier_usage_data_basic(self, mock_context, mock_freetier_client):
        """Test get_free_tier_usage_data with basic parameters."""
        # Execute
        result = await get_free_tier_usage_data(
            mock_context,
            mock_freetier_client,
            None,  # filter_expr
        )

        # Assert
        mock_freetier_client.get_free_tier_usage.assert_called_once()
        assert result['status'] == 'success'
        assert 'freeTierUsages' in result['data']
        assert len(result['data']['freeTierUsages']) == 2
        assert result['data']['freeTierUsages'][0]['service'] == 'Amazon EC2'


_TOOLS_MODULE = 'awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools'


async def _free_tier_usage_fn():
    """Return the undecorated function behind the registered free-tier-usage tool."""
    tool = await free_tier_usage_server.get_tool('free-tier-usage')
    assert isinstance(tool, FunctionTool)
    return tool.fn


@pytest.mark.asyncio
class TestFreeTierUsage:
    """Tests for the free-tier-usage tool."""

    async def test_free_tier_usage_get_free_tier_usage(self, mock_context):
        """The default operation returns every usage row the API reports."""
        fn = await _free_tier_usage_fn()
        client = MagicMock()
        client.get_free_tier_usage.return_value = {
            'freeTierUsages': [{'service': 'Amazon EC2'}, {'service': 'Amazon S3'}]
        }

        with patch(f'{_TOOLS_MODULE}.create_aws_client', return_value=client):
            result = await fn(mock_context, operation='get_free_tier_usage')

        assert result['status'] == 'success'
        assert [u['service'] for u in result['data']['freeTierUsages']] == [
            'Amazon EC2',
            'Amazon S3',
        ]

    async def test_free_tier_usage_with_all_parameters(self, mock_context):
        """The filter is parsed and sent with a page size sized from max_items."""
        fn = await _free_tier_usage_fn()
        client = MagicMock()
        client.get_free_tier_usage.return_value = {'freeTierUsages': []}
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["Amazon EC2"]}}'

        with patch(f'{_TOOLS_MODULE}.create_aws_client', return_value=client):
            result = await fn(
                mock_context, operation='get_free_tier_usage', filter=filter_json, max_items=10
            )

        assert result['status'] == 'success'
        client.get_free_tier_usage.assert_called_once_with(
            filter={'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon EC2']}}, maxResults=10
        )

    async def test_free_tier_usage_unsupported_operation(self, mock_context):
        """An unknown operation returns an error without calling the API."""
        fn = await _free_tier_usage_fn()
        client = MagicMock()

        with patch(f'{_TOOLS_MODULE}.create_aws_client', return_value=client):
            result = await fn(mock_context, operation='unknown_operation')

        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']
        client.get_free_tier_usage.assert_not_called()

    async def test_free_tier_usage_error_handling(self, mock_context):
        """An exception from the API comes back as an error response."""
        fn = await _free_tier_usage_fn()
        client = MagicMock()
        client.get_free_tier_usage.side_effect = RuntimeError('API error')

        with patch(f'{_TOOLS_MODULE}.create_aws_client', return_value=client):
            result = await fn(mock_context, operation='get_free_tier_usage')

        assert result['status'] == 'error'
        assert 'API error' in result['message']


class TestFreeTierUsageEdgeCases:
    """Additional tests to improve coverage."""

    @pytest.fixture
    def mock_context(self):
        """Mock context for testing."""
        from unittest.mock import AsyncMock

        context = MagicMock()
        context.info = AsyncMock()
        context.error = AsyncMock()
        return context

    async def test_max_items_sizes_the_page_within_api_limits(self, mock_context):
        """max_items below 1 is rejected; otherwise it sizes the page within the API's 1000 limit."""
        mock_client = MagicMock()
        mock_client.get_free_tier_usage.return_value = {'freeTierUsages': []}

        mock_context.warning = AsyncMock()
        result = await get_free_tier_usage_data(mock_context, mock_client, None, max_items=0)
        assert result['status'] == 'error'
        mock_client.get_free_tier_usage.assert_not_called()

        mock_client.reset_mock()
        await get_free_tier_usage_data(mock_context, mock_client, None, max_items=2000)
        mock_client.get_free_tier_usage.assert_called_with(maxResults=1000)

        mock_client.reset_mock()
        await get_free_tier_usage_data(mock_context, mock_client, None)
        mock_client.get_free_tier_usage.assert_called_with(maxResults=1000)

    async def test_filter_parameter_handling(self, mock_context):
        """Test filter parameter processing."""
        from awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools import (
            get_free_tier_usage_data,
        )

        mock_client = MagicMock()
        mock_client.get_free_tier_usage.return_value = {'freeTierUsages': []}

        # Test with filter
        filter_json = '{"dimensions": [{"key": "SERVICE", "values": ["EC2"]}]}'
        await get_free_tier_usage_data(mock_context, mock_client, filter_json, None)

        # Verify filter was parsed and passed
        call_args = mock_client.get_free_tier_usage.call_args[1]
        assert 'filter' in call_args
        assert 'maxResults' in call_args

    async def test_pagination_with_next_token(self, mock_context):
        """Test pagination handling."""
        from awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools import (
            get_free_tier_usage_data,
        )

        mock_client = MagicMock()
        # First call returns nextToken, second call doesn't
        mock_client.get_free_tier_usage.side_effect = [
            {'freeTierUsages': [{'service': 'EC2'}], 'nextToken': 'token1'},
            {'freeTierUsages': [{'service': 'S3'}]},
        ]

        result = await get_free_tier_usage_data(mock_context, mock_client, None)

        # Verify pagination worked
        assert result['status'] == 'success'
        assert len(result['data']['freeTierUsages']) == 2
        assert mock_client.get_free_tier_usage.call_count == 2
        assert result['data']['pagination'] == {
            'complete_dataset': True,
            'has_more': False,
            'next_token': None,
            'items_returned': 2,
        }
        assert 'warning' not in result['data']
        assert result['data']['summary']['total_services'] == 2

    async def test_max_items_stop_marks_summary_partial(self, mock_context):
        """Stopping at max_items returns the token and the partial-data warning."""
        mock_client = MagicMock()
        mock_client.get_free_tier_usage.side_effect = [
            {
                'freeTierUsages': [
                    {'service': 'EC2', 'actualUsageAmount': 750, 'limit': 750},
                    {'service': 'S3', 'actualUsageAmount': 1, 'limit': 5},
                ],
                'nextToken': 'token1',
            },
        ]

        result = await get_free_tier_usage_data(mock_context, mock_client, None, max_items=2)

        data = result['data']
        assert mock_client.get_free_tier_usage.call_count == 1
        assert mock_client.get_free_tier_usage.call_args.kwargs['maxResults'] == 2
        assert list(data)[:2] == ['complete_dataset', 'warning']
        assert 'Partial data' in data['warning']
        assert data['pagination']['next_token'] == 'token1'
        assert data['pagination']['has_more'] is True
        assert data['summary']['at_limit_count'] == 1

    async def test_continuation_sends_token_and_identical_params(self, mock_context):
        """A continuation sends the caller's token and otherwise the same request."""
        filter_json = '{"Dimensions": {"Key": "SERVICE", "Values": ["EC2"]}}'
        first = MagicMock()
        first.get_free_tier_usage.return_value = {
            'freeTierUsages': [{'service': 'EC2'}],
            'nextToken': 'token1',
        }
        resumed = MagicMock()
        resumed.get_free_tier_usage.return_value = {'freeTierUsages': [{'service': 'EC2'}]}

        await get_free_tier_usage_data(mock_context, first, filter_json, max_items=1)
        result = await get_free_tier_usage_data(
            mock_context, resumed, filter_json, max_items=1, next_token='token1'
        )

        first_call = first.get_free_tier_usage.call_args.kwargs
        resumed_call = resumed.get_free_tier_usage.call_args.kwargs
        assert resumed_call['nextToken'] == 'token1'
        assert 'nextToken' not in first_call
        assert {k: v for k, v in resumed_call.items() if k != 'nextToken'} == first_call
        assert result['data']['pagination']['complete_dataset'] is True

    async def test_rejected_token_is_invalid_next_token(self, mock_context):
        """A token the service rejects maps to invalid_next_token."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.get_free_tier_usage.side_effect = ClientError(
            {'Error': {'Code': 'InvalidNextTokenException', 'Message': 'bad'}},
            'GetFreeTierUsage',
        )
        mock_context.warning = AsyncMock()

        result = await get_free_tier_usage_data(
            mock_context, mock_client, None, next_token='stale'
        )

        assert result['status'] == 'error'
        assert result['error_type'] == 'invalid_next_token'


async def test_free_tier_usage_tool_takes_max_items_and_next_token():
    """The tool exposes max_items/next_token and no longer exposes max_results."""
    tool = await free_tier_usage_server.get_tool('free-tier-usage')
    assert tool is not None
    properties = tool.parameters['properties']

    assert 'max_items' in properties
    assert 'next_token' in properties
    assert 'max_results' not in properties
    assert 'max_items' in (tool.description or '')
    assert 'complete_dataset' in (tool.description or '')


async def test_free_tier_usage_tool_forwards_max_items_and_next_token(mock_context):
    """The tool sends the caller's next_token and sizes the page from max_items."""
    tool = await free_tier_usage_server.get_tool('free-tier-usage')
    assert isinstance(tool, FunctionTool)
    mock_client = MagicMock()
    mock_client.get_free_tier_usage.return_value = {
        'freeTierUsages': [{'service': 'EC2'}],
        'nextToken': 'page3',
    }

    with patch(
        'awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools.create_aws_client',
        return_value=mock_client,
    ):
        result = await tool.fn(mock_context, max_items=1, next_token='page2')

    mock_client.get_free_tier_usage.assert_called_once_with(nextToken='page2', maxResults=1)
    assert result['status'] == 'success'
    assert result['data']['pagination']['next_token'] == 'page3'
    assert result['data']['complete_dataset'] is False


def test_free_tier_usage_server_initialization():
    """Test that the free_tier_usage_server is properly initialized."""
    # Verify the server name
    assert free_tier_usage_server.name == 'free-tier-usage-tools'

    # Verify the server instructions
    instructions = free_tier_usage_server.instructions
    assert instructions is not None
    assert (
        'Tools for working with AWS Free Tier Usage API' in instructions if instructions else False
    )


class TestFilterValidation:
    """The tool rejects filters the API would reject or silently match nothing with."""

    @pytest.mark.parametrize(
        'filter_json',
        [
            '{"Dimensions": {"Key": "SERVICE", "Values": ["AWS Lambda"],'
            ' "MatchOptions": ["GREATER_THAN_OR_EQUAL"]}}',
            '{"And": [{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"],'
            ' "MatchOptions": ["EQUALS"]}}, {"Not": {"Dimensions": {"Key": "USAGE_TYPE",'
            ' "Values": ["Requests"], "MatchOptions": ["GREATER_THAN_OR_EQUAL"]}}}]}',
            '{"Not": {"Dimensions": {"Key": "FREE_TIER_TYPE", "Values": ["Always Free"],'
            ' "MatchOptions": ["GREATER_THAN_OR_EQUAL"]}}}',
        ],
    )
    async def test_greater_than_or_equal_off_usage_percentage_is_rejected(
        self, mock_context, filter_json
    ):
        """GTE on a text key matches no row at the API (every row under Not), so the tool rejects it."""
        mock_client = MagicMock()

        result = await get_free_tier_usage_data(mock_context, mock_client, filter_json)

        mock_client.get_free_tier_usage.assert_not_called()
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert 'GREATER_THAN_OR_EQUAL applies only to USAGE_PERCENTAGE' in result['message']
        assert 'it matches no row (and under Not, every row)' in result['message']

    async def test_value_of_21_characters_is_rejected(self, mock_context):
        """21 characters is one over the API's limit."""
        mock_client = MagicMock()
        filter_json = (
            '{"Dimensions": {"Key": "USAGE_TYPE", "Values": ["123456789012345678901"],'
            ' "MatchOptions": ["CONTAINS"]}}'
        )

        result = await get_free_tier_usage_data(mock_context, mock_client, filter_json)

        mock_client.get_free_tier_usage.assert_not_called()
        assert result['error_type'] == 'validation_error'
        assert 'is 21 characters' in result['message']

    async def test_value_over_20_characters_is_rejected_with_hint(self, mock_context):
        """The API caps each value at 20 characters; the tool names the fix."""
        mock_client = MagicMock()
        filter_json = (
            '{"Or": [{"Dimensions": {"Key": "REGION", "Values": ["us-east-1"],'
            ' "MatchOptions": ["EQUALS"]}}, {"Dimensions": {"Key": "SERVICE",'
            ' "Values": ["AmazonSNS", "Amazon Simple Notification Service"],'
            ' "MatchOptions": ["EQUALS"]}}]}'
        )

        result = await get_free_tier_usage_data(mock_context, mock_client, filter_json)

        mock_client.get_free_tier_usage.assert_not_called()
        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert 'Amazon Simple Notification Service' in result['message']
        assert '20' in result['message']
        assert 'CONTAINS' in result['message']
        assert 'AmazonSNS' in result['message']

    @pytest.mark.parametrize(
        'filter_json',
        [
            '{"Dimensions": {"Key": "USAGE_PERCENTAGE", "Values": ["80"],'
            ' "MatchOptions": ["GREATER_THAN_OR_EQUAL"]}}',
            '{"Dimensions": {"Key": "SERVICE", "Values": ["12345678901234567890"],'
            ' "MatchOptions": ["CONTAINS"]}}',
            # Malformed shapes are left for the SDK and the API to report.
            '{"Dimensions": {"Key": "SERVICE", "Values": ["AWS Lambda"],'
            ' "MatchOptions": ["EQUALS", "GREATER_THAN_OR_EQUAL"]}}',
            '{"Dimensions": {"Key": "service", "Values": ["AWS Lambda"],'
            ' "MatchOptions": ["GREATER_THAN_OR_EQUAL"]}}',
            '{"Dimensions": {"Values": ["AWS Lambda"], "MatchOptions": ["GREATER_THAN_OR_EQUAL"]}}',
            '{"Dimensions": {"Key": "SERVICE", "Values": ["AmazonSNS"]}}',
            '{"Dimensions": "SERVICE"}',
            '{"And": {"Dimensions": {}}}',
            '[1, 2]',
        ],
    )
    async def test_other_filters_are_sent_unchanged(self, mock_context, filter_json):
        """A valid filter, or one the tool does not check, reaches the API as given."""
        mock_client = MagicMock()
        mock_client.get_free_tier_usage.return_value = {'freeTierUsages': []}

        result = await get_free_tier_usage_data(mock_context, mock_client, filter_json)

        assert result['status'] == 'success'
        assert mock_client.get_free_tier_usage.call_args.kwargs['filter'] == json.loads(
            filter_json
        )


async def test_description_documents_the_filter_rules():
    """The served description gives the filter shape and every trap the API leaves silent."""
    tool = await free_tier_usage_server.get_tool('free-tier-usage')
    assert tool is not None
    description = ' '.join((tool.description or '').split())

    assert '"MatchOptions": ["EQUALS"]' in description
    assert 'exactly one' in description
    assert 'at least 2' in description
    assert 'at most 20 characters of letters, digits, spaces and - : . _ / , $ ( )' in description
    assert 'AmazonSNS' in description
    assert 'ignores case and spaces' in description
    assert (
        'FREE_TIER_TYPE is one of "Always Free", "12 Months Free" or "Free Trial" '
        '(empty for a row with no type).'
    ) in description
    assert 'Only USAGE_PERCENTAGE takes GREATER_THAN_OR_EQUAL' in description


def _usage_row(service, actual, forecast, limit, region='us-east-1', free_tier_type='Always Free'):
    """Build one GetFreeTierUsage row."""
    return {
        'service': service,
        'usageType': f'{service}-Usage',
        'actualUsageAmount': actual,
        'forecastedUsageAmount': forecast,
        'limit': limit,
        'unit': 'Units',
        'region': region,
        'freeTierType': free_tier_type,
    }


class TestSummaryForecastAndOffer:
    """The summary flags forecast breaches and keeps each row's region and offer type."""

    def test_row_under_limit_with_forecast_at_limit_is_flagged(self):
        """A row at 50% whose month-end forecast reaches the limit is in forecast_exceeds_limit."""
        result = create_free_tier_usage_summary([_usage_row('Service A', 50, 120, 100)])

        assert result['forecast_exceeds_limit_count'] == 1
        item = result['forecast_exceeds_limit_items'][0]
        assert item['service'] == 'Service A'
        assert item['forecast'] == 120
        assert item['forecast_percentage'] == 120.0
        # The actual-usage buckets are unchanged: the row is still counted as safe.
        assert result['safe_count'] == 1

    def test_forecast_equal_to_limit_is_flagged(self):
        """A forecast of exactly the limit counts as reaching it."""
        result = create_free_tier_usage_summary([_usage_row('Service A', 85, 100, 100)])

        assert result['forecast_exceeds_limit_count'] == 1
        assert result['near_limit_count'] == 1

    def test_forecast_under_limit_is_not_flagged(self):
        """A forecast below the limit is not a breach."""
        result = create_free_tier_usage_summary([_usage_row('Service A', 50, 90, 100)])

        assert result['forecast_exceeds_limit_count'] == 0
        assert result['forecast_exceeds_limit_items'] == []

    def test_row_already_at_limit_is_not_repeated(self):
        """A row already at the limit stays in at_limit only."""
        result = create_free_tier_usage_summary([_usage_row('Service A', 62, 71.2, 62)])

        assert result['at_limit_count'] == 1
        assert result['forecast_exceeds_limit_count'] == 0

    def test_missing_forecast_or_limit_is_not_flagged(self):
        """No forecast, or no usable limit, never lands in forecast_exceeds_limit."""
        no_forecast = _usage_row('Service A', 85, None, 100)
        del no_forecast['forecastedUsageAmount']
        zero_limit = _usage_row('Service B', 0, 5, 0)

        result = create_free_tier_usage_summary([no_forecast, zero_limit])

        assert result['forecast_exceeds_limit_count'] == 0
        assert result['unknown_count'] == 1
        item = result['near_limit_items'][0]
        assert item['forecast'] is None
        assert 'forecast_percentage' not in item

    def test_default_zero_forecast_gets_no_percentage(self):
        """A forecast of 0 under a positive actual is the API's default, not a forecast."""
        result = create_free_tier_usage_summary([_usage_row('Service A', 85, 0, 100)])

        item = result['near_limit_items'][0]
        assert item['forecast'] == 0
        assert 'forecast_percentage' not in item
        assert result['forecast_exceeds_limit_count'] == 0

    @pytest.mark.parametrize(
        'actual,forecast,flagged',
        [
            (50, 99.9, True),
            (50, 99.8, False),
            (99.85, 120, True),
            (99.9, 120, False),
        ],
    )
    def test_forecast_threshold_is_99_9_percent(self, actual, forecast, flagged):
        """The forecast and at-limit cut-offs are both 99.9% of the limit."""
        result = create_free_tier_usage_summary([_usage_row('Service A', actual, forecast, 100)])

        assert result['forecast_exceeds_limit_count'] == (1 if flagged else 0)

    def test_forecast_breaches_sort_highest_forecast_first(self):
        """forecast_exceeds_limit_items is sorted by forecast percentage, highest first."""
        result = create_free_tier_usage_summary(
            [
                _usage_row('Service A', 10, 110, 100),
                _usage_row('Service B', 10, 300, 100),
            ]
        )

        assert [i['service'] for i in result['forecast_exceeds_limit_items']] == [
            'Service B',
            'Service A',
        ]

    def test_items_carry_region_and_free_tier_type(self):
        """Rows of one service in two regions stay apart, each with its region and offer type."""
        result = create_free_tier_usage_summary(
            [
                _usage_row('Amazon SNS', 100, 110, 100, region='us-east-1'),
                _usage_row(
                    'Amazon SNS', 100, 100, 100, region='eu-west-1', free_tier_type='Free Trial'
                ),
            ]
        )

        items = sorted(result['at_limit_items'], key=lambda i: i['region'])
        assert [(i['region'], i['free_tier_type']) for i in items] == [
            ('eu-west-1', 'Free Trial'),
            ('us-east-1', 'Always Free'),
        ]
        assert [i['forecast'] for i in items] == [100, 110]

    def test_existing_item_fields_are_kept(self):
        """The fields the summary already returned keep their names and values."""
        result = create_free_tier_usage_summary([_usage_row('Service A', 90, 95, 100)])

        item = result['near_limit_items'][0]
        assert item['service'] == 'Service A'
        assert item['usage_type'] == 'Service A-Usage'
        assert item['actual'] == 90
        assert item['limit'] == 100
        assert item['unit'] == 'Units'
        assert item['percentage'] == 90.0
        assert item['forecast_percentage'] == 95.0


async def test_description_documents_the_summary():
    """The served description names the forecast list and the per-item region and offer type."""
    tool = await free_tier_usage_server.get_tool('free-tier-usage')
    assert tool is not None
    description = ' '.join((tool.description or '').split())

    assert 'forecast_exceeds_limit_items' in description
    assert 'forecastedUsageAmount' in description
    assert 'free_tier_type' in description
    assert 'an empty one says neither' in description
    assert (
        'The forecast is month-to-date usage projected in a straight line to month end, '
        'so early in the month it can greatly overstate.'
    ) in description
    assert 'region' in description
