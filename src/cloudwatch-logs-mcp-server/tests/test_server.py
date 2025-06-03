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
import importlib
import os
import pytest
import pytest_asyncio
import sys
from awslabs.cloudwatch_logs_mcp_server.models import (
    CancelQueryResult,
    LogAnalysisResult,
    LogMetadata,
)
from awslabs.cloudwatch_logs_mcp_server.server import (
    analyze_log_group_tool,
    cancel_query_tool,
    describe_log_groups_tool,
    execute_log_insights_query_tool,
    get_query_results_tool,
)
from moto import mock_aws
from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch


@pytest_asyncio.fixture
async def ctx():
    """Fixture to provide mock context."""
    return AsyncMock()


@pytest_asyncio.fixture
async def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
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

        # Patch into the server code
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

    async def test_describe_log_groups_exception_handling(self, ctx, logs_client):
        """Test exception handling in describe_log_groups_tool."""

        def mock_get_paginator(*args, **kwargs):
            raise Exception('Test exception in describe_log_groups')

        logs_client.get_paginator = mock_get_paginator

        with pytest.raises(Exception, match='Test exception in describe_log_groups'):
            await describe_log_groups_tool(
                ctx,
                account_identifiers=None,
                include_linked_accounts=None,
                log_group_class='STANDARD',
                log_group_name_prefix='/aws',
                max_items=None,
            )

        # Verify that ctx.error was called with the expected message
        ctx.error.assert_called_once_with(
            'Error in describing log groups: Test exception in describe_log_groups'
        )


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


@pytest.mark.asyncio
class TestAnalyzeLogGroup:
    """Tests for analyze_log_group_tool."""

    async def test_basic_analysis(self, ctx, logs_client):
        """Test basic log group analysis."""
        # Create a test log group
        log_group_name = '/aws/test/analysis'
        logs_client.create_log_group(logGroupName=log_group_name)
        log_group_arn = f'arn:aws:logs:us-west-2:123456789012:log-group:{log_group_name}'

        # Mock anomaly detector response, not supported by moto
        def mock_describe_anomaly_detectors(*args, **kwargs):
            return {
                'anomalyDetectors': [
                    {
                        'anomalyDetectorArn': f'{log_group_arn}:detector:test',
                        'detectorName': 'test-detector',
                        'anomalyDetectorStatus': 'ACTIVE',
                    }
                ]
            }

        # Mock anomalies response, not supported by moto
        def mock_describe_log_anomalies(*args, **kwargs):
            return {
                'anomalies': [
                    {
                        'anomalyDetectorArn': f'{log_group_arn}:detector:test',
                        'logGroupArnList': [log_group_arn],
                        'firstSeen': 1622505600000,
                        'lastSeen': 1622509200000,
                        'description': 'Test anomaly description',
                        'priority': 'HIGH',
                        'patternRegex': '.*error.*',
                        'patternString': 'error pattern',
                        'logSamples': [
                            {'timestamp': 1622505600000, 'message': 'Test error message'}
                        ],
                        'histogram': {'1622505600': 50, '1622509200': 50},
                    },
                    {
                        'anomalyDetectorArn': f'{log_group_arn}:detector:test',
                        'logGroupArnList': ['differentLogGroup'],
                        'firstSeen': 1622505600000,
                        'lastSeen': 1622509200000,
                        'description': 'Anomaly that should not be included',
                        'priority': 'HIGH',
                        'patternRegex': '.*error.*',
                        'patternString': 'error pattern',
                        'logSamples': [
                            {'timestamp': 1622505600000, 'message': 'Test error message'}
                        ],
                        'histogram': {'1622505600': 50, '1622509200': 50},
                    },
                ]
            }

        # Mock the methods
        logs_client.get_paginator = lambda operation_name: type(
            'Paginator',
            (),
            {
                'paginate': lambda **kwargs: [
                    mock_describe_anomaly_detectors()
                    if operation_name == 'list_log_anomaly_detectors'
                    else mock_describe_log_anomalies()
                ]
            },
        )

        original_get_query_results = logs_client.get_query_results

        def mock_get_query_results(**kwargs):
            # Map logGroupIdentifier to logGroupName if present
            result = original_get_query_results(**kwargs)
            result['results'] = [
                [
                    {'field': '@pattern', 'value': 'test_pattern'},
                    {'field': '@visualization', 'value': 'test_visualization'},
                    {'field': '@tokens', 'value': 'test_tokens'},
                    {'field': '@logSamples', 'value': '[{"logSample1": {}}, {"logSample2": {}}]'},
                ]
            ]
            return result

        logs_client.get_query_results = mock_get_query_results

        # Execute analysis
        result = await analyze_log_group_tool(
            ctx,
            log_group_arn=log_group_arn,
            start_time='2021-01-01T00:00:00+00:00',
            end_time='2022-01-01T01:00:00+00:00',
        )

        # Verify results
        assert isinstance(result, LogAnalysisResult)
        assert len(result.log_anomaly_results.anomaly_detectors) == 1
        assert len(result.log_anomaly_results.anomalies) == 1
        assert result.log_anomaly_results.anomaly_detectors[0].detectorName == 'test-detector'
        assert result.log_anomaly_results.anomaly_detectors[0].anomalyDetectorStatus == 'ACTIVE'
        assert result.log_anomaly_results.anomalies[0].priority == 'HIGH'
        assert result.log_anomaly_results.anomalies[0].patternString == 'error pattern'
        assert isinstance(result.top_patterns, dict)
        assert len(result.top_patterns['results'][0]['@logSamples']) == 1
        assert isinstance(result.top_patterns_containing_errors, dict)

    async def test_no_anomaly_detectors(self, ctx, logs_client):
        """Test analysis when no anomaly detectors exist."""
        log_group_name = '/aws/test/no-detectors'
        logs_client.create_log_group(logGroupName=log_group_name)
        log_group_arn = f'arn:aws:logs:us-west-2:123456789012:log-group:{log_group_name}'

        # Mock empty detector response
        def mock_describe_anomaly_detectors(*args, **kwargs):
            return {'anomalyDetectors': []}

        logs_client.get_paginator = lambda operation_name: type(
            'Paginator',
            (),
            {'paginate': lambda **kwargs: [mock_describe_anomaly_detectors()]},
        )

        result = await analyze_log_group_tool(
            ctx,
            log_group_arn=log_group_arn,
            start_time='2020-01-01T00:00:00+00:00',
            end_time='2020-01-01T01:00:00+00:00',
        )

        assert isinstance(result, LogAnalysisResult)
        assert len(result.log_anomaly_results.anomaly_detectors) == 0
        assert len(result.log_anomaly_results.anomalies) == 0
        assert isinstance(result.top_patterns, dict)
        assert isinstance(result.top_patterns_containing_errors, dict)

    async def test_invalid_time_format(self, ctx, logs_client):
        """Test analysis with invalid time format."""
        log_group_arn = 'arn:aws:logs:us-west-2:123456789012:log-group:/aws/test/invalid'

        with pytest.raises(Exception):
            await analyze_log_group_tool(
                ctx,
                log_group_arn=log_group_arn,
                start_time='invalid-time',
                end_time='2020-01-01T01:00:00+00:00',
            )


class TestAWSProfileInitialization:
    """Tests for AWS profile handling in server initialization."""

    def test_logs_client_with_aws_profile(self, monkeypatch):
        """Test logs client initialization when AWS_PROFILE is set."""
        # Mock environment variables
        monkeypatch.setenv('AWS_PROFILE', 'test-profile')
        monkeypatch.setenv('AWS_REGION', 'us-west-2')

        # Mock boto3.Session to capture the arguments
        mock_session_class = MagicMock()
        mock_session_instance = MagicMock()
        mock_logs_client = MagicMock()

        mock_session_class.return_value = mock_session_instance
        mock_session_instance.client.return_value = mock_logs_client

        with patch('boto3.Session', mock_session_class):
            if 'awslabs.cloudwatch_logs_mcp_server.server' in sys.modules:
                del sys.modules['awslabs.cloudwatch_logs_mcp_server.server']

            # Re-import the module to trigger the initialization with mocked boto3.Session
            importlib.import_module('awslabs.cloudwatch_logs_mcp_server.server')

            mock_session_class.assert_called_with(
                profile_name='test-profile', region_name='us-west-2'
            )
            mock_session_instance.client.assert_called_with('logs', config=ANY)

    def test_logs_client_without_aws_profile(self, monkeypatch):
        """Test logs client initialization when AWS_PROFILE is not set."""
        monkeypatch.delenv('AWS_PROFILE', raising=False)
        monkeypatch.setenv('AWS_REGION', 'us-east-1')

        mock_session_class = MagicMock()
        mock_session_instance = MagicMock()
        mock_logs_client = MagicMock()

        mock_session_class.return_value = mock_session_instance
        mock_session_instance.client.return_value = mock_logs_client

        with patch('boto3.Session', mock_session_class):
            if 'awslabs.cloudwatch_logs_mcp_server.server' in sys.modules:
                del sys.modules['awslabs.cloudwatch_logs_mcp_server.server']
            importlib.import_module('awslabs.cloudwatch_logs_mcp_server.server')

            mock_session_class.assert_called_with(region_name='us-east-1')

            # Verify client method was called with 'logs'
            mock_session_instance.client.assert_called_with('logs', config=ANY)

    def test_logs_client_initialization_exception(self, monkeypatch):
        """Test that initialization exception is properly raised and logged."""
        monkeypatch.setenv('AWS_PROFILE', 'invalid-profile')
        monkeypatch.setenv('AWS_REGION', 'us-west-2')

        mock_session_class = MagicMock()
        mock_session_class.side_effect = Exception('Invalid profile configuration')

        with patch('boto3.Session', mock_session_class):
            if 'awslabs.cloudwatch_logs_mcp_server.server' in sys.modules:
                del sys.modules['awslabs.cloudwatch_logs_mcp_server.server']

            # Verify that importing the module raises the exception
            with pytest.raises(Exception, match='Invalid profile configuration'):
                importlib.import_module('awslabs.cloudwatch_logs_mcp_server.server')
