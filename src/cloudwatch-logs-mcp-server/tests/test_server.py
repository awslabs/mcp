# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the cloudwatch-logs MCP Server."""

import awslabs.cloudwatch_logs_mcp_server.server
import boto3
import pytest
import pytest_asyncio
from awslabs.cloudwatch_logs_mcp_server.models import (
    CancelQueryResult,
    LogMetadata,
)
from awslabs.cloudwatch_logs_mcp_server.server import (
    cancel_query_tool,
    describe_log_groups_tool,
    execute_log_insights_query_tool,
    get_query_results_tool,
)
from moto import mock_aws
from unittest.mock import AsyncMock


@pytest_asyncio.fixture
async def ctx():
    """Fixture to provide mock context."""
    return AsyncMock()


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os

    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_REGION'] = 'us-west-2'


@pytest_asyncio.fixture
async def logs_client(aws_credentials):
    """Create mocked logs client."""
    with mock_aws():
        client = boto3.client('logs', region_name='us-west-2')
        awslabs.cloudwatch_logs_mcp_server.server.logs_client = client
        yield client


@pytest.mark.asyncio
class TestDescribeLogGroups:
    """Tests for describe_log_groups_tool."""

    async def test_basic_describe(self, ctx, logs_client):
        """Test basic log group description."""
        # Create a test log group
        logs_client.create_log_group(logGroupName='/aws/test/group1')

        def mock_describe_query_definitions(*args, **kwargs):
            return {
                'queryDefinitions': [
                    {
                        'name': 'test-query',
                        'queryString': 'fields @timestamp, @message | limit 1',
                        'logGroupNames': ['/aws/test/group1'],
                    }
                ]
            }

        logs_client.describe_query_definitions = mock_describe_query_definitions

        # Call the tool
        result = await describe_log_groups_tool(
            ctx,
            account_identifiers=None,
            include_linked_accounts=None,
            log_group_class='STANDARD',
            log_group_name_prefix='/aws',
            max_items=None,
        )

        # Verify results
        assert isinstance(result, LogMetadata)
        assert len(result.log_group_metadata) == 1
        assert result.log_group_metadata[0].logGroupName == '/aws/test/group1'
        assert len(result.saved_queries) == 1

    async def test_max_items_limit(self, ctx, logs_client):
        """Test max items limit."""
        # Create multiple log groups
        for i in range(3):
            logs_client.create_log_group(logGroupName=f'/aws/test/group{i}')

        def mock_describe_query_definitions(*args, **kwargs):
            return {
                'queryDefinitions': [
                    {
                        'name': 'test-query',
                        'queryString': 'SOURCE logGroups(namePrefix: ["different_prefix"]) | filter @message like "ERROR"',
                        'logGroupNames': [],
                    }
                ]
            }

        logs_client.describe_query_definitions = mock_describe_query_definitions

        # Call with max_items=2
        result = await describe_log_groups_tool(
            ctx,
            account_identifiers=None,
            include_linked_accounts=None,
            log_group_class='STANDARD',
            log_group_name_prefix='/aws',
            max_items=2,
        )

        # Verify results
        assert len(result.log_group_metadata) == 2
        assert len(result.saved_queries) == 0

    async def test_saved_query_with_prefix(self, ctx, logs_client):
        """Test basic log group description."""
        # Create a test log group
        logs_client.create_log_group(logGroupName='/aws/test/group1')

        def mock_describe_query_definitions(*args, **kwargs):
            return {
                'queryDefinitions': [
                    {
                        'name': 'test-query',
                        'queryString': 'SOURCE logGroups(namePrefix: ["/aws/test/group", \'other_prefix\']) | filter @message like "ERROR"',
                        'logGroupNames': [],
                    }
                ]
            }

        logs_client.describe_query_definitions = mock_describe_query_definitions

        # Call the tool
        result = await describe_log_groups_tool(
            ctx,
            account_identifiers=None,
            include_linked_accounts=None,
            log_group_class='STANDARD',
            log_group_name_prefix='/aws',
            max_items=None,
        )

        # Verify results
        assert isinstance(result, LogMetadata)
        assert len(result.log_group_metadata) == 1
        assert result.log_group_metadata[0].logGroupName == '/aws/test/group1'
        assert len(result.saved_queries) == 1
        assert result.saved_queries[0].logGroupPrefixes == {'/aws/test/group', 'other_prefix'}


@pytest.mark.asyncio
class TestExecuteLogInsightsQuery:
    """Tests for execute_log_insights_query_tool."""

    async def test_basic_query(self, ctx, logs_client):
        """Test basic log insights query."""
        # Create a log group and add some test logs
        log_group_name = '/aws/test/query1'
        logs_client.create_log_group(logGroupName=log_group_name)

        # Execute query
        start_time = '2020-01-01T00:00:00'
        end_time = '2020-01-01T01:00:00'
        query = 'fields @timestamp, @message | limit 1'

        result = await execute_log_insights_query_tool(
            ctx,
            log_group_names=[log_group_name],
            log_group_identifiers=None,
            start_time=start_time,
            end_time=end_time,
            query_string=query,
            limit=10,
            max_timeout=10,
        )

        # Verify results
        assert 'queryId' in result
        assert result['status'] in {'Complete', 'Running', 'Scheduled'}

    async def test_invalid_time_format(self, ctx, logs_client):
        """Test query with invalid time format."""
        with pytest.raises(Exception):
            await execute_log_insights_query_tool(
                ctx,
                log_group_names=['/aws/test/query1'],
                log_group_identifiers=None,
                start_time='invalid-time',
                end_time='2020-01-01T01:00:00',
                query_string='fields @timestamp',
                limit=10,
                max_timeout=10,
            )

    async def test_missing_log_groups(self, ctx, logs_client):
        """Test query with no log groups specified."""
        with pytest.raises(Exception):
            await execute_log_insights_query_tool(
                ctx,
                log_group_names=None,
                log_group_identifiers=None,
                start_time='2020-01-01T00:00:00',
                end_time='2020-01-01T01:00:00',
                query_string='fields @timestamp',
                limit=10,
                max_timeout=10,
            )

    async def test_query_timeout(self, ctx, logs_client, monkeypatch):
        """Test query timeout behavior."""
        log_group_name = '/aws/test/timeout'
        logs_client.create_log_group(logGroupName=log_group_name)

        # Mock get_query_results to return Running
        original_get_query_results = logs_client.get_query_results

        def custom_get_query_results(*args, **kwargs):
            # You can either modify the original response
            response = original_get_query_results(*args, **kwargs)
            response['status'] = 'Running'
            return response

        logs_client.get_query_results = custom_get_query_results

        result = await execute_log_insights_query_tool(
            ctx,
            log_group_names=[log_group_name],
            log_group_identifiers=None,
            start_time='2020-01-01T00:00:00',
            end_time='2020-01-01T01:00:00',
            query_string='fields @timestamp | stats count(*) by bin(1h)',
            limit=10,
            max_timeout=1,  # Set very short timeout
        )

        assert result['status'] == 'Polling Timeout'
        assert 'queryId' in result


@pytest.mark.asyncio
class TestGetQueryResults:
    """Tests for get_query_results_tool."""

    async def test_get_results(self, ctx, logs_client):
        """Test getting query results."""
        # First start a query
        log_group_name = '/aws/test/query1'
        logs_client.create_log_group(logGroupName=log_group_name)

        start_query_response = await execute_log_insights_query_tool(
            ctx,
            log_group_names=[log_group_name],
            log_group_identifiers=None,
            start_time='2020-01-01T00:00:00',
            end_time='2020-01-01T01:00:00',
            query_string='fields @timestamp | stats count(*) by bin(1h)',
            limit=10,
            max_timeout=1,
        )

        # Get results
        result = await get_query_results_tool(ctx, query_id=start_query_response['queryId'])

        # Verify results
        assert 'status' in result
        assert result['status'] in {'Complete', 'Running', 'Scheduled'}

    async def test_invalid_query_id(self, ctx, logs_client):
        """Test getting results with invalid query ID."""
        with pytest.raises(Exception):
            await get_query_results_tool(ctx, query_id='invalid-id')


@pytest.mark.asyncio
class TestCancelQuery:
    """Tests for cancel_query_tool."""

    async def test_cancel_query(self, ctx, logs_client):
        """Test canceling a query."""
        # First start a query
        log_group_name = '/aws/test/query1'
        logs_client.create_log_group(logGroupName=log_group_name)

        start_query_response = await execute_log_insights_query_tool(
            ctx,
            log_group_names=[log_group_name],
            log_group_identifiers=None,
            start_time='2020-01-01T00:00:00',
            end_time='2020-01-01T01:00:00',
            query_string='fields @timestamp | stats count(*) by bin(1h)',
            limit=10,
            max_timeout=1,
        )

        def mock_stop_query(*args, **kwargs):
            return {'success': True}

        logs_client.stop_query = mock_stop_query

        result = await cancel_query_tool(ctx, query_id=start_query_response['queryId'])
        assert isinstance(result, CancelQueryResult)

    async def test_invalid_query_id(self, ctx, logs_client):
        """Test canceling with invalid query ID."""
        with pytest.raises(Exception):
            await cancel_query_tool(ctx, query_id='invalid-id')
