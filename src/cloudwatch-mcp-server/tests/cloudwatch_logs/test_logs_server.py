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
import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.models import (
    LogsAnalysisResult,
    LogsMetadata,
    LogsQueryCancelResult,
)
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools import CloudWatchLogsTools
from botocore.exceptions import ClientError
from moto import mock_aws
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


@pytest_asyncio.fixture
async def ctx():
    """Fixture to provide mock context."""
    return AsyncMock()


@pytest_asyncio.fixture
async def logs_client():
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
    with patch('awslabs.cloudwatch_mcp_server.aws_common.Session') as mock_session:
        mock_session.return_value.client.return_value = logs_client
        tools = CloudWatchLogsTools()
        yield tools


@pytest.mark.asyncio
class TestDescribeLogGroups:
    """Tests for describe_log_groups tool."""

    async def test_basic_describe(self, ctx, cloudwatch_tools, logs_client):
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

    async def test_max_items_limit(self, ctx, cloudwatch_tools, logs_client):
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

    async def test_saved_query_with_prefix(self, ctx, cloudwatch_tools, logs_client):
        """Test saved query with prefix matching."""
        # Create a test log group
        logs_client.create_log_group(logGroupName='/aws/test/group1')

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

        logs_client.describe_query_definitions = mock_describe_query_definitions

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

    async def test_exception_handling(self, ctx, cloudwatch_tools, logs_client):
        """Test exception handling in describe_log_groups."""
        # Mock an exception in the logs client
        logs_client.describe_log_groups = MagicMock(side_effect=Exception('Test exception'))

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

    async def test_successful_query(self, ctx, cloudwatch_tools, logs_client):
        """Test successful query execution."""
        # Create a test log group
        logs_client.create_log_group(logGroupName='/aws/test/group1')

        # Mock query execution
        logs_client.start_query = MagicMock(return_value={'queryId': 'test-query-id'})
        logs_client.get_query_results = MagicMock(
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

        logs_client.start_query.assert_called_once_with(
            logGroupNames=['/aws/test/group1'],
            startTime=1672531200,
            endTime=1672534800,
            queryString='fields @timestamp, @message | limit 10',
            limit=10,
        )

        # Verify results
        assert result['queryId'] == 'test-query-id'
        assert result['status'] == 'Complete'
        assert len(result['results']) == 1
        assert result['results'][0]['@timestamp'] == '2023-01-01T00:00:00.000Z'
        assert result['results'][0]['@message'] == 'Test log message'

    async def test_query_timeout(self, ctx, cloudwatch_tools, logs_client):
        """Test query timeout handling."""
        # Create a test log group
        logs_client.create_log_group(logGroupName='/aws/test/group1')

        # Mock query execution with running status
        logs_client.start_query = MagicMock(return_value={'queryId': 'test-query-id'})
        logs_client.get_query_results = MagicMock(
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
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            log_group_names=['/aws/test/group1'],
            log_group_identifiers=['/aws/test/group1'],  # Both provided - should fail
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string='fields @timestamp, @message | limit 10',
            limit=10,
            max_timeout=30,
        )

        # Verify error response structure instead of exception
        assert result['status'] == 'Error'
        assert result['results'] == []
        assert 'Error executing CloudWatch Logs Insights query' in result['message']


@pytest.mark.asyncio
class TestGetQueryResults:
    """Tests for get_query_results tool."""

    async def test_get_results(self, ctx, cloudwatch_tools, logs_client):
        """Test getting query results."""
        # Mock query results
        logs_client.get_query_results = MagicMock(
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

    async def test_cancel_query(self, ctx, cloudwatch_tools, logs_client):
        """Test canceling a query."""
        # Mock query cancellation
        logs_client.stop_query = MagicMock(return_value={'success': True})

        # Call the tool
        result = await cloudwatch_tools.cancel_logs_insight_query(ctx, query_id='test-query-id')

        # Verify results
        assert isinstance(result, LogsQueryCancelResult)
        assert result.success is True


@pytest.mark.asyncio
class TestAnalyzeLogGroup:
    """Tests for analyze_log_group tool."""

    async def test_analyze_log_group(self, ctx, cloudwatch_tools, logs_client):
        """Test log group analysis."""
        log_group_arn = 'arn:aws:logs:us-west-2:123456789012:log-group:/aws/test/group1'

        # Mock anomaly detection
        logs_client.get_paginator = MagicMock()

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

        logs_client.get_paginator.side_effect = get_paginator_side_effect

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

    async def test_analyze_log_group_region_parameter(self, ctx, cloudwatch_tools, logs_client):
        """Test that analyze_log_group passes region parameter to execute_log_insights_query calls."""
        log_group_arn = 'arn:aws:logs:eu-west-1:123456789012:log-group:/aws/test/group1'

        # Mock anomaly detection
        logs_client.get_paginator = MagicMock()

        # Mock list_log_anomaly_detectors paginator
        anomaly_paginator = MagicMock()
        anomaly_paginator.paginate.return_value = [{'anomalyDetectors': []}]

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

        logs_client.get_paginator.side_effect = get_paginator_side_effect

        # Mock execute_log_insights_query to capture the region parameter
        executed_queries = []

        async def mock_execute_query(*args, **kwargs):
            executed_queries.append(kwargs)
            return {
                'queryId': 'test-query-id',
                'status': 'Complete',
                'results': [{'@message': 'Test pattern', '@sampleCount': '10'}],
            }

        # Patch the execute_log_insights_query method
        with patch.object(
            cloudwatch_tools, 'execute_log_insights_query', side_effect=mock_execute_query
        ):
            # Call analyze_log_group with specific region
            await cloudwatch_tools.analyze_log_group(
                ctx,
                log_group_arn=log_group_arn,
                start_time='2023-01-01T00:00:00+00:00',
                end_time='2023-01-01T01:00:00+00:00',
                region='eu-west-1',
            )

        # Verify that both execute_log_insights_query calls received the correct region
        assert len(executed_queries) == 2
        assert executed_queries[0]['region'] == 'eu-west-1'
        assert executed_queries[1]['region'] == 'eu-west-1'

        # Verify other parameters are passed correctly
        for query in executed_queries:
            assert query['log_group_identifiers'] == [log_group_arn]
            assert query['start_time'] == '2023-01-01T00:00:00+00:00'
            assert query['end_time'] == '2023-01-01T01:00:00+00:00'


@pytest.mark.asyncio
class TestQueryLanguages:
    """Exercise language-specific request and schema behavior."""

    @pytest.mark.parametrize(
        'query',
        [
            'SELECT `@message` AS message FROM `/aws/lambda/example` LIMIT 10',
            "SELECT `@message` AS message FROM `dataSource(['amazon_vpc.flow'])` LIMIT 10",
        ],
    )
    async def test_sql_query_without_external_selectors(
        self, ctx, cloudwatch_tools, logs_client, query
    ):
        """Pass SQL through and preserve projected fields."""
        logs_client.start_query = MagicMock(return_value={'queryId': 'test-query-id'})
        logs_client.get_query_results = MagicMock(
            return_value={
                'status': 'Complete',
                'results': [
                    [
                        {'field': 'message', 'value': 'example'},
                        {'field': '@ptr', 'value': 'record'},
                    ]
                ],
            }
        )
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string=query,
            query_language='SQL',
        )
        logs_client.start_query.assert_called_once_with(
            queryLanguage='SQL',
            startTime=1672531200,
            endTime=1672534800,
            queryString=query,
        )
        assert result['status'] == 'Complete'
        assert result['results'] == [{'message': 'example', '@ptr': 'record'}]

    @pytest.mark.parametrize(
        ('selectors', 'query', 'limit', 'expected'),
        [
            (
                {'log_group_names': ['/aws/test/group1']},
                'fields `@message`',
                10,
                {'logGroupNames': ['/aws/test/group1'], 'limit': 10},
            ),
            (
                {'log_group_identifiers': ['arn:example']},
                'fields `@message`',
                10,
                {'logGroupIdentifiers': ['arn:example'], 'limit': 10},
            ),
            ({}, 'source = [lg:`/aws/lambda/example`] | fields `@message` | head 10', None, {}),
            ({}, 'source = [ds:`amazon_vpc.flow`] | fields `@message` | head 10', None, {}),
        ],
    )
    async def test_ppl_query_selectors(
        self, ctx, cloudwatch_tools, logs_client, selectors, query, limit, expected
    ):
        """Pass external selectors or inline source through for PPL."""
        logs_client.start_query = MagicMock(return_value={'queryId': 'test-query-id'})
        logs_client.get_query_results = MagicMock(
            return_value={
                'status': 'Complete',
                'results': [[{'field': '@message', 'value': 'example'}]],
            }
        )
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string=query,
            query_language='PPL',
            limit=limit,
            **selectors,
        )
        logs_client.start_query.assert_called_once_with(
            queryLanguage='PPL',
            startTime=1672531200,
            endTime=1672534800,
            queryString=query,
            **expected,
        )
        assert result['status'] == 'Complete'
        assert result['results'] == [{'@message': 'example'}]

    @pytest.mark.parametrize(
        'selectors',
        [
            {'log_group_names': ['/aws/test/group1']},
            {'log_group_identifiers': ['arn:example']},
        ],
    )
    async def test_sql_rejects_external_selectors(
        self, ctx, cloudwatch_tools, logs_client, selectors
    ):
        """Reject external SQL selectors before calling AWS."""
        logs_client.start_query = MagicMock()
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string='SELECT 1',
            query_language='SQL',
            **selectors,
        )
        assert result['queryId'] == ''
        assert result['status'] == 'Error'
        assert result['results'] == []
        assert all(
            part in result['message']
            for part in ('FROM', 'log_group_names', 'log_group_identifiers')
        )
        logs_client.start_query.assert_not_called()

    @pytest.mark.parametrize('language', ['CWLI', 'PPL'])
    async def test_rejects_multiple_external_selectors(
        self, ctx, cloudwatch_tools, logs_client, language
    ):
        """Reject conflicting selectors before calling AWS."""
        logs_client.start_query = MagicMock()
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            log_group_names=['group'],
            log_group_identifiers=['arn:example'],
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string='fields `@message`',
            query_language=language,
        )
        assert result == {
            'queryId': '',
            'status': 'Error',
            'results': [],
            'message': 'Error executing CloudWatch Logs Insights query: Provide at most one of log_group_names or log_group_identifiers',
        }
        logs_client.start_query.assert_not_called()

    @pytest.mark.parametrize(
        ('query', 'selectors'),
        [
            (
                "SOURCE logGroups(namePrefix: ['/aws/lambda/example']) | fields @message | limit 10",
                {},
            ),
            (
                "SOURCE dataSource(['amazon_vpc.flow']) | fields @message | limit 10",
                {'log_group_names': []},
            ),
            (
                "# note\nSOURCE logGroups(namePrefix: ['/example']) | fields @message | limit 10",
                {},
            ),
            ("\n\nSOURCE logGroups(namePrefix: ['/example']) | fields @message | limit 10", {}),
            ("  \nsource logGroups(namePrefix: ['/example']) | fields @message | limit 10", {}),
            (
                'SOURCE logGroupTags([{ "key": "env", "values": ["test"] }]) | fields @message | limit 10',
                {},
            ),
        ],
    )
    async def test_cwli_source_without_external_selectors(
        self, ctx, cloudwatch_tools, logs_client, query, selectors
    ):
        """Send each CWLI source unchanged without external scope."""
        logs_client.start_query = MagicMock(return_value={'queryId': 'test-query-id'})
        logs_client.get_query_results = MagicMock(
            return_value={
                'status': 'Complete',
                'results': [[{'field': '@message', 'value': 'example'}]],
            }
        )
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string=query,
            **selectors,
        )
        logs_client.start_query.assert_called_once_with(
            startTime=1672531200, endTime=1672534800, queryString=query
        )
        assert result['status'] == 'Complete'
        assert result['results'] == [{'@message': 'example'}]

    async def test_missing_inline_scope_returns_aws_error(
        self, ctx, cloudwatch_tools, logs_client
    ):
        """Return the AWS error without polling when scope is missing."""
        logs_client.start_query = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'InvalidParameterException', 'Message': 'Missing source'}},
                'StartQuery',
            )
        )
        logs_client.get_query_results = MagicMock()
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string='fields @message',
            query_language='PPL',
        )
        expected = {
            'queryLanguage': 'PPL',
            'startTime': 1672531200,
            'endTime': 1672534800,
            'queryString': 'fields @message',
        }
        logs_client.start_query.assert_called_once_with(**expected)
        logs_client.get_query_results.assert_not_called()
        assert result['status'] == 'Error'
        assert result['queryId'] == ''
        assert result['results'] == []
        assert 'Missing source' in result['message']

    @pytest.mark.parametrize(
        ('language', 'query'),
        [
            ('CWLI', "SOURCE logGroups(namePrefix: ['/other']) | fields @message | limit 10"),
            ('PPL', 'source = [lg:`/other`] | fields `@message` | head 10'),
        ],
    )
    async def test_external_selector_with_inline_source_is_forwarded(
        self, ctx, cloudwatch_tools, logs_client, language, query
    ):
        """Preserve both scope inputs without retrying."""
        message = 'LogGroupSelection, LogGroupNames, and SubQueries are mutually exclusive'
        code = 'InvalidParameterException'
        if language == 'CWLI':
            code = 'MalformedQueryException'
            message = 'Compile Error - ' + message + '.'
        logs_client.start_query = MagicMock(
            side_effect=ClientError({'Error': {'Code': code, 'Message': message}}, 'StartQuery')
        )
        logs_client.get_query_results = MagicMock()
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            log_group_names=['/selected'],
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string=query,
            query_language=language,
        )
        expected = {
            'logGroupNames': ['/selected'],
            'startTime': 1672531200,
            'endTime': 1672534800,
            'queryString': query,
        }
        if language == 'PPL':
            expected['queryLanguage'] = 'PPL'
        logs_client.start_query.assert_called_once_with(**expected)
        logs_client.get_query_results.assert_not_called()
        assert result['status'] == 'Error'
        assert result['queryId'] == ''
        assert result['results'] == []
        assert message in result['message']
        assert code in result['message']

    @pytest.mark.parametrize(
        'query',
        [
            'fields @message',
            'sourceful | fields @message',
            '# SOURCE logGroups(...)\nfields @message | limit 10',
        ],
    )
    async def test_cwli_missing_scope_rejected_locally(
        self, ctx, cloudwatch_tools, logs_client, query
    ):
        """Reject missing scope before contacting the service."""
        logs_client.start_query = MagicMock()
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string=query,
        )
        logs_client.start_query.assert_not_called()
        assert result['status'] == 'Error'
        assert result['queryId'] == ''
        assert result['results'] == []
        assert (
            'CWLI queries need log_group_names, log_group_identifiers, or a query that starts with SOURCE'
            in result['message']
        )

    async def test_malformed_cwli_source_returns_aws_error(
        self, ctx, cloudwatch_tools, logs_client
    ):
        """Forward malformed SOURCE to the service without retrying."""
        query = 'SOURCE logGroups( | fields @message | limit 10'
        logs_client.start_query = MagicMock(
            side_effect=ClientError(
                {'Error': {'Code': 'MalformedQueryException', 'Message': 'Malformed source'}},
                'StartQuery',
            )
        )
        logs_client.get_query_results = MagicMock()
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string=query,
        )
        logs_client.start_query.assert_called_once_with(
            startTime=1672531200, endTime=1672534800, queryString=query
        )
        logs_client.get_query_results.assert_not_called()
        assert result['status'] == 'Error'
        assert result['queryId'] == ''
        assert result['results'] == []
        assert 'Malformed source' in result['message']

    async def test_cwli_names_with_empty_identifiers(self, ctx, cloudwatch_tools, logs_client):
        """Remove the empty list while preserving the selected log group."""
        logs_client.start_query = MagicMock(return_value={'queryId': 'test-query-id'})
        logs_client.get_query_results = MagicMock(
            return_value={'status': 'Complete', 'results': []}
        )
        result = await cloudwatch_tools.execute_log_insights_query(
            ctx,
            log_group_names=['/selected'],
            log_group_identifiers=[],
            start_time='2023-01-01T00:00:00+00:00',
            end_time='2023-01-01T01:00:00+00:00',
            query_string='fields @message | limit 10',
        )
        logs_client.start_query.assert_called_once_with(
            logGroupNames=['/selected'],
            startTime=1672531200,
            endTime=1672534800,
            queryString='fields @message | limit 10',
        )
        assert result['status'] == 'Complete'

    async def test_query_language_schema_is_optional_enum(self):
        """Expose the supported languages with a backwards-compatible default."""
        from awslabs.cloudwatch_mcp_server.server import mcp

        tools = await mcp.list_tools()
        schema = next(
            tool.input_schema for tool in tools if tool.name == 'execute_log_insights_query'
        )
        language = schema['properties']['query_language']
        assert set(language['enum']) == {'CWLI', 'SQL', 'PPL'}
        assert language['default'] == 'CWLI'
        assert 'query_language' not in schema['required']
