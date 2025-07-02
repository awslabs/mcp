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
"""Tests for the CloudWatch Logs functionality in the MCP Server."""

import boto3
import os
import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.models import (
    LogsAnalysisResult,
    LogsMetadata,
    LogsQueryCancelResult,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools import CloudWatchLogsTools
from moto import mock_aws
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


@pytest_asyncio.fixture
async def ctx():
    """Fixture to provide mock context."""
    return AsyncMock()


@pytest_asyncio.fixture
async def aws_credentials():
    """Set up AWS credentials for testing."""
    os.environ['AWS_REGION'] = 'us-west-2'


@pytest_asyncio.fixture
async def logs_client(aws_credentials):
    """Create mocked logs client."""
    with mock_aws():
        client: Any = boto3.client('logs', region_name='us-west-2')

        # Mock start_query to handle logGroupIdentifier as moto only supports logGroupNames
        original_start_query = client.start_query

        def mock_start_query(**kwargs):
            # Map logGroupIdentifier to logGroupName if present
            if 'logGroupIdentifiers' in kwargs:
                kwargs['logGroupNames'] = [
                    ident.split(':log-group:')[1].split(':')[0]
                    for ident in kwargs['logGroupIdentifiers']
                ]
            return original_start_query(**kwargs)

        client.start_query = mock_start_query
        yield client


@pytest_asyncio.fixture
async def cloudwatch_tools(logs_client):
    """Create CloudWatchLogsTools instance with mocked client."""
    with patch(
        'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
    ) as mock_session:
        mock_session.return_value.client.return_value = logs_client
        tools = CloudWatchLogsTools()
        yield tools


@pytest.mark.asyncio
class TestDescribeLogGroups:
    """Tests for describe_log_groups tool."""

    async def test_basic_describe(self, ctx, cloudwatch_tools):
        """Test basic log group description."""
        # Create a test log group
        cloudwatch_tools.logs_client.create_log_group(logGroupName='/aws/test/group1')

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

        cloudwatch_tools.logs_client.describe_query_definitions = mock_describe_query_definitions

        # Call the tool
        result = await cloudwatch_tools.describe_log_groups(
            ctx,
            account_identifiers=None,
            include_linked_accounts=None,
            log_group_class='STANDARD',
            log_group_name_prefix='/aws',
            max_items=None,
        )

        # Verify results
        assert isinstance(result, LogsMetadata)
        assert len(result.log_group_metadata) == 1
        assert result.log_group_metadata[0].logGroupName == '/aws/test/group1'
        assert len(result.saved_queries) == 1

    async def test_max_items_limit(self, ctx, cloudwatch_tools):
        """Test max items limit."""
        # Create multiple log groups
        for i in range(3):
            cloudwatch_tools.logs_client.create_log_group(logGroupName=f'/aws/test/group{i}')

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

        cloudwatch_tools.logs_client.describe_query_definitions = mock_describe_query_definitions

        # Call with max_items=2
        result = await cloudwatch_tools.describe_log_groups(
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

    async def test_saved_query_with_prefix(self, ctx, cloudwatch_tools):
        """Test saved query with prefix matching."""
        # Create a test log group
        cloudwatch_tools.logs_client.create_log_group(logGroupName='/aws/test/group1')

        def mock_describe_query_definitions(*args, **kwargs):
            return {
                'queryDefinitions': [
                    {
                        'name': 'test-query-with-prefix',
                        'queryString': 'SOURCE logGroups(namePrefix: ["/aws"]) | filter @message like "ERROR"',
                        'logGroupNames': [],
                    }
                ]
            }

        cloudwatch_tools.logs_client.describe_query_definitions = mock_describe_query_definitions

        # Call the tool
        result = await cloudwatch_tools.describe_log_groups(
            ctx,
            account_identifiers=None,
            include_linked_accounts=None,
            log_group_class='STANDARD',
            log_group_name_prefix='/aws',
            max_items=None,
        )

        # Verify results
        assert isinstance(result, LogsMetadata)
        assert len(result.log_group_metadata) == 1
        assert len(result.saved_queries) == 1

    async def test_exception_handling(self, ctx, cloudwatch_tools):
        """Test exception handling in describe_log_groups."""
        # Mock an exception in the logs client
        cloudwatch_tools.logs_client.describe_log_groups = MagicMock(
            side_effect=Exception('Test exception')
        )

        with pytest.raises(Exception):
            await cloudwatch_tools.describe_log_groups(
                ctx,
                account_identifiers=None,
                include_linked_accounts=None,
                log_group_class='STANDARD',
                log_group_name_prefix='/aws',
                max_items=None,
            )


@pytest.mark.asyncio
class TestExecuteLogInsightsQuery:
    """Tests for execute_log_insights_query tool."""

    async def test_successful_query(self, ctx, cloudwatch_tools):
        """Test successful query execution."""
        # Create a test log group
        cloudwatch_tools.logs_client.create_log_group(logGroupName='/aws/test/group1')

        # Mock query execution
        cloudwatch_tools.logs_client.start_query = MagicMock(
            return_value={'queryId': 'test-query-id'}
        )
        cloudwatch_tools.logs_client.get_query_results = MagicMock(
            return_value={
                'status': 'Complete',
                'results': [
                    [
                        {'field': '@timestamp', 'value': '2023-01-01T00:00:00.000Z'},
                        {'field': '@message', 'value': 'Test log message'},
                    ]
                ],
                'statistics': {'recordsMatched': 1, 'recordsScanned': 100},
            }
        )

        # Call the tool
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            log_group_names=['/aws/test/group1'],
            log_group_identifiers=None,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string='fields @timestamp, @message | limit 10',
            limit=10,
            max_timeout=30,
        )

        # Verify results
        assert result['queryId'] == 'test-query-id'
        assert result['status'] == 'Complete'
        assert len(result['results']) == 1
        assert result['results'][0]['@timestamp'] == '2023-01-01T00:00:00.000Z'
        assert result['results'][0]['@message'] == 'Test log message'

    async def test_query_timeout(self, ctx, cloudwatch_tools):
        """Test query timeout handling."""
        # Create a test log group
        cloudwatch_tools.logs_client.create_log_group(logGroupName='/aws/test/group1')

        # Mock query execution with running status
        cloudwatch_tools.logs_client.start_query = MagicMock(
            return_value={'queryId': 'test-query-id'}
        )
        cloudwatch_tools.logs_client.get_query_results = MagicMock(
            return_value={'status': 'Running', 'results': []}
        )

        # Call the tool with short timeout
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            log_group_names=['/aws/test/group1'],
            log_group_identifiers=None,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string='fields @timestamp, @message | limit 10',
            limit=10,
            max_timeout=1,  # Short timeout
        )

        # Verify timeout handling
        assert result['queryId'] == 'test-query-id'
        assert result['status'] == 'Polling Timeout'
        assert 'message' in result

    async def test_invalid_parameters(self, ctx, cloudwatch_tools):
        """Test invalid parameter handling."""
        with pytest.raises(Exception):
            await cloudwatch_tools.execute_log_insights_query(
                ctx,
                log_group_names=['/aws/test/group1'],
                log_group_identifiers=['/aws/test/group1'],  # Both provided - should fail
                start_time='2023-01-01T00:00:00+00:00',
                end_time='2023-01-01T01:00:00+00:00',
                query_string='fields @timestamp, @message | limit 10',
                limit=10,
                max_timeout=30,
            )


@pytest.mark.asyncio
class TestGetQueryResults:
    """Tests for get_query_results tool."""

    async def test_get_results(self, ctx, cloudwatch_tools):
        """Test getting query results."""
        # Mock query results
        cloudwatch_tools.logs_client.get_query_results = MagicMock(
            return_value={
                'status': 'Complete',
                'results': [
                    [
                        {'field': '@timestamp', 'value': '2023-01-01T00:00:00.000Z'},
                        {'field': '@message', 'value': 'Test log message'},
                    ]
                ],
                'statistics': {'recordsMatched': 1, 'recordsScanned': 100},
            }
        )

        # Call the tool
        result = await cloudwatch_tools.get_logs_insight_query_results(
            ctx, query_id='test-query-id'
        )

        # Verify results
        assert result['queryId'] == 'test-query-id'
        assert result['status'] == 'Complete'
        assert len(result['results']) == 1
        assert result['results'][0]['@timestamp'] == '2023-01-01T00:00:00.000Z'


@pytest.mark.asyncio
class TestCancelQuery:
    """Tests for cancel_query tool."""

    async def test_cancel_query(self, ctx, cloudwatch_tools):
        """Test canceling a query."""
        # Mock query cancellation
        cloudwatch_tools.logs_client.stop_query = MagicMock(return_value={'success': True})

        # Call the tool
        result = await cloudwatch_tools.cancel_logs_insight_query(ctx, query_id='test-query-id')

        # Verify results
        assert isinstance(result, LogsQueryCancelResult)
        assert result.success is True


@pytest.mark.asyncio
class TestAnalyzeLogGroup:
    """Tests for analyze_log_group tool."""

    async def test_analyze_log_group(self, ctx, cloudwatch_tools):
        """Test log group analysis."""
        log_group_arn = 'arn:aws:logs:us-west-2:123456789012:log-group:/aws/test/group1'

        # Mock anomaly detection
        cloudwatch_tools.logs_client.get_paginator = MagicMock()

        # Mock list_log_anomaly_detectors paginator
        anomaly_paginator = MagicMock()
        anomaly_paginator.paginate.return_value = [
            {
                'anomalyDetectors': [
                    {
                        'anomalyDetectorArn': 'arn:aws:logs:us-west-2:123456789012:anomaly-detector:test-detector',
                        'detectorName': 'test-detector',
                        'anomalyDetectorStatus': 'ACTIVE',
                    }
                ]
            }
        ]

        # Mock list_anomalies paginator
        anomalies_paginator = MagicMock()
        anomalies_paginator.paginate.return_value = [{'anomalies': []}]

        def get_paginator_side_effect(operation_name):
            if operation_name == 'list_log_anomaly_detectors':
                return anomaly_paginator
            elif operation_name == 'list_anomalies':
                return anomalies_paginator
            else:
                return MagicMock()

        cloudwatch_tools.logs_client.get_paginator.side_effect = get_paginator_side_effect

        # Mock the execute_log_insights_query calls for pattern analysis
        async def mock_execute_query(*args, **kwargs):
            return {
                'queryId': 'test-query-id',
                'status': 'Complete',
                'results': [{'@message': 'Test pattern', '@sampleCount': '10'}],
            }

        # Patch the execute_log_insights_query method
        with patch.object(
            cloudwatch_tools, 'execute_log_insights_query', side_effect=mock_execute_query
        ):
            # Call the tool
            result = await cloudwatch_tools.analyze_log_group(
                ctx,
                log_group_arn=log_group_arn,
                start_time='2023-01-01T00:00:00+00:00',
                end_time='2023-01-01T01:00:00+00:00',
            )

        # Verify results
        assert isinstance(result, LogsAnalysisResult)
        assert len(result.log_anomaly_results.anomaly_detectors) == 1
        assert result.log_anomaly_results.anomaly_detectors[0].detectorName == 'test-detector'
        assert 'results' in result.top_patterns
        assert 'results' in result.top_patterns_containing_errors
