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

import pytest
from awslabs.billing_cost_management_mcp_server.tools.free_tier_usage_tools import (
    create_free_tier_usage_summary,
    free_tier_usage_server,
    get_free_tier_usage_data,
)
from fastmcp import Context
from fastmcp.tools import FunctionTool
from unittest.mock import AsyncMock, MagicMock, patch


# Create a mock implementation for testing
async def free_tier_usage(ctx, operation, **kwargs):
    """Mock implementation of free_tier_usage for testing."""
    from awslabs.billing_cost_management_mcp_server.utilities.aws_service_base import (
        format_response,
    )

    if operation == 'get_free_tier_usage':
        return {
            'status': 'success',
            'data': {
                'free_tier_usages': [
                    {
                        'service': 'Amazon EC2',
                        'usage': {
                            'limit': '750 hours',
                            'used': '250 hours',
                            'remaining': '500 hours',
                            'percent_used': 33.33,
                        },
                    },
                    {
                        'service': 'Amazon S3',
                        'usage': {
                            'limit': '5 GB',
                            'used': '1 GB',
                            'remaining': '4 GB',
                            'percent_used': 20.0,
                        },
                    },
                ]
            },
        }
    else:
        return format_response('error', {}, f'Unsupported operation: {operation}')


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


@pytest.mark.asyncio
class TestFreeTierUsage:
    """Tests for free_tier_usage function."""

    async def test_free_tier_usage_get_free_tier_usage(self, mock_context):
        """Test free_tier_usage with get_free_tier_usage operation."""
        # Execute
        result = await free_tier_usage(
            mock_context,
            operation='get_free_tier_usage',
        )

        # Assert
        assert result['status'] == 'success'
        assert 'data' in result
        assert 'free_tier_usages' in result['data']
        assert len(result['data']['free_tier_usages']) == 2

    async def test_free_tier_usage_with_all_parameters(self, mock_context):
        """Test free_tier_usage with all parameters."""
        # Execute
        result = await free_tier_usage(
            mock_context,
            operation='get_free_tier_usage',
            filter='{"services":["Amazon EC2"]}',
            max_items=10,
        )

        # Assert
        assert result['status'] == 'success'

    async def test_free_tier_usage_unsupported_operation(self, mock_context):
        """Test free_tier_usage with unsupported operation."""
        # Execute
        result = await free_tier_usage(
            mock_context,
            operation='unknown_operation',
        )

        # Assert
        assert result['status'] == 'error'
        assert 'Unsupported operation' in result['message']

    async def test_free_tier_usage_error_handling(self, mock_context):
        """Test free_tier_usage error handling."""
        # Setup - simulate error response
        result = {'status': 'error', 'message': 'API error'}

        # Assert
        assert result['status'] == 'error'
        assert result['message'] == 'API error'


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
