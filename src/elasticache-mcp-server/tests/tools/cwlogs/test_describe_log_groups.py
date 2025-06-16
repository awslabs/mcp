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

"""Tests for describe_log_groups tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.cwlogs.describe_log_groups import describe_log_groups
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_log_groups_basic():
    """Test basic describe_log_groups functionality with no parameters."""
    # Mock successful response
    mock_client = MagicMock()
    mock_client.describe_log_groups.return_value = {
        'logGroups': [
            {
                'logGroupName': 'test-group-1',
                'creationTime': 1234567890,
                'metricFilterCount': 0,
                'arn': 'arn:aws:logs:region:account:log-group:test-group-1',
                'storedBytes': 1234,
            }
        ]
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call the function
        result = await describe_log_groups()

        # Verify the client was called correctly
        mock_client.describe_log_groups.assert_called_once_with()

        # Verify the response
        assert 'logGroups' in result
        assert len(result['logGroups']) == 1
        assert result['logGroups'][0]['logGroupName'] == 'test-group-1'


@pytest.mark.asyncio
async def test_describe_log_groups_with_all_params():
    """Test describe_log_groups with all optional parameters."""
    # Mock successful response
    mock_client = MagicMock()
    mock_client.describe_log_groups.return_value = {
        'logGroups': [
            {
                'logGroupName': 'test-group-1',
                'creationTime': 1234567890,
                'metricFilterCount': 0,
                'arn': 'arn:aws:logs:region:account:log-group:test-group-1',
                'storedBytes': 1234,
            }
        ],
        'nextToken': 'next-token-value',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call with all parameters
        result = await describe_log_groups(
            account_identifiers=['123456789012'],
            log_group_name_prefix='/aws/lambda',
            log_group_name_pattern='*lambda*',
            include_linked_accounts=True,
            log_group_class='STANDARD',
            log_group_identifiers=['group-1', 'group-2'],
        )

        # Verify all parameters were passed correctly
        mock_client.describe_log_groups.assert_called_once_with(
            accountIdentifiers=['123456789012'],
            logGroupNamePrefix='/aws/lambda',
            logGroupNamePattern='*lambda*',
            includeLinkedAccounts=True,
            logGroupClass='STANDARD',
            logGroupIdentifiers=['group-1', 'group-2'],
        )

        # Verify the response
        assert 'logGroups' in result
        assert len(result['logGroups']) == 1
        assert 'nextToken' in result
        assert result['nextToken'] == 'next-token-value'


@pytest.mark.asyncio
async def test_describe_log_groups_with_pagination():
    """Test describe_log_groups with pagination token."""
    # Mock successful response
    mock_client = MagicMock()
    mock_client.describe_log_groups.return_value = {
        'logGroups': [
            {
                'logGroupName': 'test-group-1',
                'creationTime': 1234567890,
                'metricFilterCount': 0,
                'arn': 'arn:aws:logs:region:account:log-group:test-group-1',
                'storedBytes': 1234,
            }
        ],
        'nextToken': 'next-page-token',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call the function
        result = await describe_log_groups(log_group_name_prefix='/aws')

        # Verify the client was called correctly
        mock_client.describe_log_groups.assert_called_once_with(logGroupNamePrefix='/aws')

        # Verify the response includes pagination token
        assert 'logGroups' in result
        assert 'nextToken' in result
        assert result['nextToken'] == 'next-page-token'


@pytest.mark.asyncio
async def test_describe_log_groups_error():
    """Test describe_log_groups error handling."""
    # Mock error response
    mock_client = MagicMock()
    mock_client.describe_log_groups.side_effect = ClientError(
        {
            'Error': {
                'Code': 'InvalidParameterException',
                'Message': 'Invalid parameter: logGroupNamePattern',
            }
        },
        'DescribeLogGroups',
    )

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Call the function and verify error is handled
        result = await describe_log_groups(log_group_name_pattern='invalid*pattern')

        # Verify error response
        assert 'error' in result
        assert 'Invalid parameter: logGroupNamePattern' in result['error']


@pytest.mark.asyncio
async def test_describe_log_groups_with_max_items():
    """Test describe_log_groups with max_items parameter."""
    # Mock client with multiple pages of results
    mock_client = MagicMock()
    mock_client.describe_log_groups.side_effect = [
        {
            'logGroups': [
                {'logGroupName': f'group-{i}', 'creationTime': 1234567890}
                for i in range(1, 4)  # 3 items
            ],
            'nextToken': 'token1',
        },
        {
            'logGroups': [
                {'logGroupName': f'group-{i}', 'creationTime': 1234567890}
                for i in range(4, 7)  # 3 more items
            ],
            'nextToken': 'token2',
        },
    ]

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test with max_items less than first page
        result = await describe_log_groups(max_items=2)
        assert len(result['logGroups']) == 2
        assert result['nextToken'] == 'token1'
        assert result['logGroups'][0]['logGroupName'] == 'group-1'
        assert result['logGroups'][1]['logGroupName'] == 'group-2'

        # Reset mock
        mock_client.describe_log_groups.reset_mock()
        mock_client.describe_log_groups.side_effect = [
            {
                'logGroups': [
                    {'logGroupName': f'group-{i}', 'creationTime': 1234567890} for i in range(1, 4)
                ],
                'nextToken': 'token1',
            },
            {
                'logGroups': [
                    {'logGroupName': f'group-{i}', 'creationTime': 1234567890} for i in range(4, 7)
                ],
                'nextToken': 'token2',
            },
        ]

        # Test with max_items spanning multiple pages
        result = await describe_log_groups(max_items=4)
        assert len(result['logGroups']) == 4
        assert result['nextToken'] == 'token2'
        assert result['logGroups'][0]['logGroupName'] == 'group-1'
        assert result['logGroups'][3]['logGroupName'] == 'group-4'


@pytest.mark.asyncio
async def test_describe_log_groups_with_page_size():
    """Test describe_log_groups with page_size parameter."""
    mock_client = MagicMock()
    mock_client.describe_log_groups.return_value = {
        'logGroups': [
            {'logGroupName': f'group-{i}', 'creationTime': 1234567890} for i in range(1, 4)
        ],
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test with page_size
        result = await describe_log_groups(page_size=2)

        # Verify page_size was passed correctly
        mock_client.describe_log_groups.assert_called_once_with(limit=2)

        assert 'logGroups' in result
        assert len(result['logGroups']) == 3


@pytest.mark.asyncio
async def test_describe_log_groups_max_items_with_remainder():
    """Test describe_log_groups with max_items that leaves a remainder."""
    mock_client = MagicMock()
    mock_client.describe_log_groups.side_effect = [
        {
            'logGroups': [
                {'logGroupName': f'group-{i}', 'creationTime': 1234567890}
                for i in range(1, 6)  # 5 items
            ],
            'nextToken': 'token1',
        },
    ]

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.CloudWatchLogsConnectionManager.get_connection',
        return_value=mock_client,
    ):
        # Test with max_items=3 when page returns 5 items
        result = await describe_log_groups(max_items=3)

        assert len(result['logGroups']) == 3
        assert result['nextToken'] == 'token1'
        assert result['logGroups'][0]['logGroupName'] == 'group-1'
        assert result['logGroups'][2]['logGroupName'] == 'group-3'
