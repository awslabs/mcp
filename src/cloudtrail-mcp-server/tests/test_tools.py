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

"""Comprehensive tests for CloudTrail MCP server tools."""

import json
import pytest
from awslabs.cloudtrail_mcp_server.models import EventDataStore, QueryResult, QueryStatus
from awslabs.cloudtrail_mcp_server.tools import CloudTrailTools
from datetime import datetime, timezone
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, Mock, call, patch


class TestCloudTrailToolsInitialization:
    """Test CloudTrail tools initialization and client management."""

    def test_initialization(self):
        """Test CloudTrailTools initialization."""
        tools = CloudTrailTools()
        assert tools is not None

    @patch('boto3.Session')
    def test_get_cloudtrail_client_without_profile(self, mock_session):
        """Test _get_cloudtrail_client without AWS_PROFILE."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client

        tools = CloudTrailTools()

        with patch.dict('os.environ', {}, clear=True):
            client = tools._get_cloudtrail_client('us-west-2')

        assert client == mock_client
        mock_session.assert_called_once_with(region_name='us-west-2')
        mock_session.return_value.client.assert_called_once()

    @patch('boto3.Session')
    def test_get_cloudtrail_client_with_profile(self, mock_session):
        """Test _get_cloudtrail_client with AWS_PROFILE set."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client

        tools = CloudTrailTools()

        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
            client = tools._get_cloudtrail_client('eu-west-1')

        assert client == mock_client
        mock_session.assert_called_once_with(profile_name='test-profile', region_name='eu-west-1')

    @patch('boto3.Session')
    def test_get_cloudtrail_client_error_handling(self, mock_session):
        """Test _get_cloudtrail_client error handling."""
        mock_session.side_effect = Exception('AWS credentials error')

        tools = CloudTrailTools()

        with pytest.raises(Exception, match='AWS credentials error'):
            tools._get_cloudtrail_client('us-east-1')


class TestLookupEvents:
    """Test the lookup_events tool."""

    @pytest.fixture
    def tools(self):
        """Create CloudTrailTools instance."""
        return CloudTrailTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        ctx = AsyncMock(spec=Context)
        return ctx

    @pytest.fixture
    def sample_events(self):
        """Sample CloudTrail events for testing."""
        return [
            {
                'EventId': 'event-1',
                'EventName': 'ConsoleLogin',
                'EventTime': datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                'Username': 'testuser',
                'Resources': [],
                'CloudTrailEvent': json.dumps(
                    {
                        'eventVersion': '1.05',
                        'userIdentity': {'type': 'IAMUser', 'userName': 'testuser'},
                        'eventTime': '2023-01-01T12:00:00Z',
                        'eventSource': 'signin.amazonaws.com',
                        'eventName': 'ConsoleLogin',
                    }
                ),
            },
            {
                'EventId': 'event-2',
                'EventName': 'CreateUser',
                'EventTime': datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc),
                'Username': 'admin',
                'Resources': [{'ResourceType': 'AWS::IAM::User', 'ResourceName': 'newuser'}],
                'CloudTrailEvent': json.dumps(
                    {
                        'eventVersion': '1.05',
                        'userIdentity': {'type': 'IAMUser', 'userName': 'admin'},
                        'eventTime': '2023-01-01T13:00:00Z',
                        'eventSource': 'iam.amazonaws.com',
                        'eventName': 'CreateUser',
                    }
                ),
            },
        ]

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_basic(self, mock_get_client, tools, mock_context, sample_events):
        """Test basic lookup_events functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {
            'Events': sample_events,
            'NextToken': 'next-token-123',
        }

        result = await tools.lookup_events(mock_context)

        assert len(result['events']) == 2
        assert result['next_token'] == 'next-token-123'
        assert result['events'][0]['EventId'] == 'event-1'
        assert result['events'][1]['EventName'] == 'CreateUser'
        assert 'query_params' in result
        assert 'next_token' not in result['query_params']

        # Verify client was called
        mock_client.lookup_events.assert_called_once()
        call_kwargs = mock_client.lookup_events.call_args[1]
        assert 'StartTime' in call_kwargs
        assert 'EndTime' in call_kwargs
        assert call_kwargs['MaxResults'] == 10

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_with_filters(
        self, mock_get_client, tools, mock_context, sample_events
    ):
        """Test lookup_events with attribute filters."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {'Events': [sample_events[0]]}

        result = await tools.lookup_events(
            mock_context, attribute_key='Username', attribute_value='testuser', max_results=5
        )

        assert len(result['events']) == 1
        assert result['events'][0]['Username'] == 'testuser'
        # Note: next_token will be present but None if not in response

        # Verify lookup attributes were set
        call_kwargs = mock_client.lookup_events.call_args[1]
        assert 'LookupAttributes' in call_kwargs
        assert call_kwargs['LookupAttributes'][0]['AttributeKey'] == 'Username'
        assert call_kwargs['LookupAttributes'][0]['AttributeValue'] == 'testuser'
        assert call_kwargs['MaxResults'] == 5

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_with_time_range(
        self, mock_get_client, tools, mock_context, sample_events
    ):
        """Test lookup_events with specific time range."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {'Events': sample_events}

        result = await tools.lookup_events(
            mock_context, start_time='2023-01-01T00:00:00Z', end_time='2023-01-01T23:59:59Z'
        )

        assert len(result['events']) == 2

        # Verify time parameters were set
        call_kwargs = mock_client.lookup_events.call_args[1]
        assert 'StartTime' in call_kwargs
        assert 'EndTime' in call_kwargs

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_different_region(
        self, mock_get_client, tools, mock_context, sample_events
    ):
        """Test lookup_events with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {'Events': sample_events}

        result = await tools.lookup_events(mock_context, region='us-west-2')

        assert len(result['events']) == 2
        assert result['query_params']['region'] == 'us-west-2'

        # Verify client was created with correct region
        mock_get_client.assert_called_with('us-west-2')

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_with_next_token(
        self, mock_get_client, tools, mock_context, sample_events
    ):
        """Test lookup_events with next_token for pagination (requires both start_time and end_time)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {
            'Events': sample_events,
            'NextToken': 'new-next-token-456',
        }

        result = await tools.lookup_events(
            mock_context,
            start_time='2023-01-01T00:00:00Z',
            end_time='2023-01-01T23:59:59Z',
            next_token='previous-next-token-123',
        )

        assert len(result['events']) == 2
        assert result['next_token'] == 'new-next-token-456'
        assert 'next_token' not in result['query_params']

        # Verify next_token was passed to API call
        call_kwargs = mock_client.lookup_events.call_args[1]
        assert 'NextToken' in call_kwargs
        assert call_kwargs['NextToken'] == 'previous-next-token-123'

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_with_next_token_and_filters(
        self, mock_get_client, tools, mock_context, sample_events
    ):
        """Test lookup_events with both next_token and attribute filters."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {
            'Events': [sample_events[0]],
            'NextToken': 'filtered-next-token-789',
        }

        result = await tools.lookup_events(
            mock_context,
            start_time='2023-01-01T00:00:00Z',
            end_time='2023-01-01T23:59:59Z',
            attribute_key='EventName',
            attribute_value='ConsoleLogin',
            next_token='pagination-token-456',
            max_results=25,
        )

        assert len(result['events']) == 1
        assert result['next_token'] == 'filtered-next-token-789'
        assert 'next_token' not in result['query_params']

        # Verify both filters and next_token were passed to API call
        call_kwargs = mock_client.lookup_events.call_args[1]
        assert 'NextToken' in call_kwargs
        assert call_kwargs['NextToken'] == 'pagination-token-456'
        assert 'LookupAttributes' in call_kwargs
        assert call_kwargs['LookupAttributes'][0]['AttributeKey'] == 'EventName'
        assert call_kwargs['LookupAttributes'][0]['AttributeValue'] == 'ConsoleLogin'
        assert call_kwargs['MaxResults'] == 25

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_without_next_token_in_response(
        self, mock_get_client, tools, mock_context, sample_events
    ):
        """Test lookup_events when response doesn't include NextToken (last page)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {
            'Events': sample_events
            # No NextToken in response - indicates last page
        }

        result = await tools.lookup_events(mock_context)

        assert len(result['events']) == 2
        assert result['next_token'] is None  # Should be None when not in response

        # Verify NextToken was not passed to API call when not provided
        call_kwargs = mock_client.lookup_events.call_args[1]
        assert 'NextToken' not in call_kwargs

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_pagination_missing_start_time_error(
        self, mock_get_client, tools, mock_context
    ):
        """Test lookup_events with next_token but missing start_time raises ValueError."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with pytest.raises(
            ValueError, match='Both start_time and end_time are required when using pagination'
        ):
            await tools.lookup_events(
                mock_context, end_time='2023-01-01T23:59:59Z', next_token='pagination-token-123'
            )

        # Verify no API call was made due to validation error
        mock_client.lookup_events.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_pagination_missing_end_time_error(
        self, mock_get_client, tools, mock_context
    ):
        """Test lookup_events with next_token but missing end_time raises ValueError."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with pytest.raises(
            ValueError, match='Both start_time and end_time are required when using pagination'
        ):
            await tools.lookup_events(
                mock_context, start_time='2023-01-01T00:00:00Z', next_token='pagination-token-123'
            )

        # Verify no API call was made due to validation error
        mock_client.lookup_events.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_pagination_missing_both_times_error(
        self, mock_get_client, tools, mock_context
    ):
        """Test lookup_events with next_token but missing both start_time and end_time raises ValueError."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with pytest.raises(
            ValueError, match='Both start_time and end_time are required when using pagination'
        ):
            await tools.lookup_events(mock_context, next_token='pagination-token-123')

        # Verify no API call was made due to validation error
        mock_client.lookup_events.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_pagination_invalid_time_format_error(
        self, mock_get_client, tools, mock_context
    ):
        """Test lookup_events with invalid time format during pagination raises ValueError."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match='Invalid time format for pagination'):
            await tools.lookup_events(
                mock_context,
                start_time='invalid-time-format',
                end_time='2023-01-01T23:59:59Z',
                next_token='pagination-token-123',
            )

        # Verify no API call was made due to validation error
        mock_client.lookup_events.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_error_handling(self, mock_get_client, tools, mock_context):
        """Test lookup_events general AWS API error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.side_effect = Exception('AWS Error')

        with pytest.raises(Exception, match='AWS Error'):
            await tools.lookup_events(mock_context)

        # Verify error was logged to context
        mock_context.error.assert_called_once()


class TestLakeQuery:
    """Test the lake_query tool."""

    @pytest.fixture
    def tools(self):
        """Create CloudTrailTools instance."""
        return CloudTrailTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_query_result(self):
        """Sample query result for testing."""
        return {
            'QueryId': 'query-123',
            'QueryStatus': 'FINISHED',
            'QueryStatistics': {
                'ResultsCount': 2,
                'TotalBytesScanned': 1024,
                'BytesScanned': 1024,
            },
        }

    @pytest.fixture
    def sample_query_data(self):
        """Sample query data rows."""
        return {
            'QueryResultRows': [
                [{'VarCharValue': 'ConsoleLogin'}, {'VarCharValue': '5'}],
                [{'VarCharValue': 'CreateUser'}, {'VarCharValue': '2'}],
            ]
        }

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    @patch.object(CloudTrailTools, 'get_query_results')
    @patch('time.sleep')  # Mock sleep to speed up tests
    async def test_lake_query_basic(
        self,
        mock_sleep,
        mock_get_query_results,
        mock_get_client,
        tools,
        mock_context,
        sample_query_result,
        sample_query_data,
    ):
        """Test basic lake_query functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.start_query.return_value = {'QueryId': 'query-123'}
        mock_client.describe_query.return_value = sample_query_result

        # Mock the get_query_results method to return a QueryResult object
        mock_get_query_results.return_value = QueryResult(
            query_id='query-123',
            query_status='FINISHED',
            query_statistics=sample_query_result.get('QueryStatistics'),
            query_result_rows=sample_query_data.get('QueryResultRows', []),
            next_token=sample_query_data.get('NextToken'),
        )

        sql = 'SELECT eventName, count(*) FROM eds-123 GROUP BY eventName'
        result = await tools.lake_query(mock_context, sql=sql)

        assert isinstance(result, QueryResult)
        assert result.query_id == 'query-123'
        assert result.query_status == 'FINISHED'
        assert result.query_result_rows is not None
        assert result.query_result_rows is not None
        assert len(result.query_result_rows) == 2
        assert result.query_statistics is not None
        assert result.query_statistics['ResultsCount'] == 2

        # Verify calls were made
        mock_client.start_query.assert_called_once_with(QueryStatement=sql)
        mock_client.describe_query.assert_called_with(QueryId='query-123')
        mock_get_query_results.assert_called_once_with(
            ctx=mock_context,
            query_id='query-123',
            max_results=50,
            next_token=None,
            region='us-east-1',
        )

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    @patch.object(CloudTrailTools, 'get_query_results')
    @patch('time.sleep')
    async def test_lake_query_different_region(
        self,
        mock_sleep,
        mock_get_query_results,
        mock_get_client,
        tools,
        mock_context,
        sample_query_result,
        sample_query_data,
    ):
        """Test lake_query with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.start_query.return_value = {'QueryId': 'query-456'}
        mock_client.describe_query.return_value = sample_query_result

        # Mock the get_query_results method to return a QueryResult object
        mock_get_query_results.return_value = QueryResult(
            query_id='query-456',
            query_status='FINISHED',
            query_statistics=sample_query_result.get('QueryStatistics'),
            query_result_rows=sample_query_data.get('QueryResultRows', []),
            next_token=sample_query_data.get('NextToken'),
        )

        sql = 'SELECT * FROM eds-456'
        result = await tools.lake_query(mock_context, sql=sql, region='eu-west-1')

        assert isinstance(result, QueryResult)

        # Verify client was created with correct region
        mock_get_client.assert_called_with('eu-west-1')

        # Verify get_query_results was called with correct region
        mock_get_query_results.assert_called_once_with(
            ctx=mock_context,
            query_id='query-456',
            max_results=50,
            next_token=None,
            region='eu-west-1',
        )

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    @patch('time.sleep')
    async def test_lake_query_running_status(
        self, mock_sleep, mock_get_client, tools, mock_context
    ):
        """Test lake_query when query is still running."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.start_query.return_value = {'QueryId': 'query-789'}
        mock_client.describe_query.return_value = {
            'QueryId': 'query-789',
            'QueryStatus': 'RUNNING',
            'QueryStatistics': {},
        }

        sql = 'SELECT * FROM eds-789'
        result = await tools.lake_query(mock_context, sql=sql)

        assert isinstance(result, QueryResult)
        assert result.query_id == 'query-789'
        assert result.query_status == 'RUNNING'
        assert result.query_result_rows is None

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    @patch('time.sleep')
    async def test_lake_query_failed_status(
        self, mock_sleep, mock_get_client, tools, mock_context
    ):
        """Test lake_query when query fails."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.start_query.return_value = {'QueryId': 'query-fail'}
        mock_client.describe_query.return_value = {
            'QueryId': 'query-fail',
            'QueryStatus': 'FAILED',
            'ErrorMessage': 'SQL syntax error',
            'QueryStatistics': {},
        }

        sql = 'INVALID SQL'
        result = await tools.lake_query(mock_context, sql=sql)

        assert isinstance(result, QueryResult)
        assert result.query_id == 'query-fail'
        assert result.query_status == 'FAILED'
        assert result.error_message == 'SQL syntax error'

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lake_query_wait_for_completion_false(
        self, mock_get_client, tools, mock_context
    ):
        """Test lake_query with wait_for_completion=False."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.start_query.return_value = {'QueryId': 'query-async-123'}
        mock_client.describe_query.return_value = {
            'QueryId': 'query-async-123',
            'QueryStatus': 'RUNNING',
            'QueryStatistics': {},
        }

        sql = 'SELECT * FROM eds-async'
        result = await tools.lake_query(mock_context, sql=sql, wait_for_completion=False)

        assert isinstance(result, QueryResult)
        assert result.query_id == 'query-async-123'
        assert result.query_status == 'RUNNING'
        assert result.query_result_rows is None
        assert result.next_token is None

        # Verify start_query was called but get_query_results was not
        mock_client.start_query.assert_called_once_with(QueryStatement=sql)
        mock_client.describe_query.assert_called_once_with(QueryId='query-async-123')
        mock_client.get_query_results.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lake_query_error_handling(self, mock_get_client, tools, mock_context):
        """Test lake_query error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.start_query.side_effect = Exception('Invalid SQL')

        sql = 'INVALID SQL'

        with pytest.raises(Exception, match='Invalid SQL'):
            await tools.lake_query(mock_context, sql=sql)

        # Verify error was logged to context
        mock_context.error.assert_called_once()


class TestGetQueryStatus:
    """Test the get_query_status tool."""

    @pytest.fixture
    def tools(self):
        """Create CloudTrailTools instance."""
        return CloudTrailTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_query_status(self):
        """Sample query status for testing."""
        return {
            'QueryId': 'query-status-123',
            'QueryStatus': 'FINISHED',
            'QueryStatistics': {
                'ResultsCount': 10,
                'TotalBytesScanned': 2048,
                'BytesScanned': 2048,
                'ExecutionTimeInMillis': 1500,
            },
        }

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_status_basic(
        self, mock_get_client, tools, mock_context, sample_query_status
    ):
        """Test basic get_query_status functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_status(mock_context, query_id='query-status-123')

        assert isinstance(result, QueryStatus)
        assert result.query_id == 'query-status-123'
        assert result.query_status == 'FINISHED'
        assert result.query_statistics is not None
        assert result.query_statistics['ResultsCount'] == 10
        assert result.query_statistics['ExecutionTimeInMillis'] == 1500
        assert result.error_message is None

        mock_client.describe_query.assert_called_once_with(QueryId='query-status-123')

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_status_failed(self, mock_get_client, tools, mock_context):
        """Test get_query_status for failed query."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.describe_query.return_value = {
            'QueryId': 'query-failed-456',
            'QueryStatus': 'FAILED',
            'ErrorMessage': 'SQL syntax error',
            'QueryStatistics': {},
        }

        result = await tools.get_query_status(mock_context, query_id='query-failed-456')

        assert isinstance(result, QueryStatus)
        assert result.query_id == 'query-failed-456'
        assert result.query_status == 'FAILED'
        assert result.error_message == 'SQL syntax error'

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_status_different_region(
        self, mock_get_client, tools, mock_context, sample_query_status
    ):
        """Test get_query_status with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_status(
            mock_context, query_id='query-region-789', region='ap-southeast-1'
        )

        assert isinstance(result, QueryStatus)
        assert result.query_id == 'query-region-789'  # From input

        # Verify client was created with correct region
        mock_get_client.assert_called_with('ap-southeast-1')

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_status_error_handling(self, mock_get_client, tools, mock_context):
        """Test get_query_status error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.describe_query.side_effect = Exception('Query not found')

        with pytest.raises(Exception, match='Query not found'):
            await tools.get_query_status(mock_context, query_id='nonexistent-query')

        # Verify error was logged to context
        mock_context.error.assert_called_once()


class TestGetQueryResults:
    """Test the get_query_results tool."""

    @pytest.fixture
    def tools(self):
        """Create CloudTrailTools instance."""
        return CloudTrailTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_query_results(self):
        """Sample query results for testing."""
        return {
            'QueryResultRows': [
                [{'VarCharValue': 'ConsoleLogin'}, {'VarCharValue': '15'}],
                [{'VarCharValue': 'CreateUser'}, {'VarCharValue': '8'}],
                [{'VarCharValue': 'DeleteUser'}, {'VarCharValue': '3'}],
            ],
            'NextToken': 'pagination-token-abc123',
        }

    @pytest.fixture
    def sample_query_status(self):
        """Sample query status for testing."""
        return {
            'QueryId': 'query-results-123',
            'QueryStatus': 'FINISHED',
            'QueryStatistics': {
                'ResultsCount': 100,
                'TotalBytesScanned': 4096,
                'ExecutionTimeInMillis': 2500,
            },
        }

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_basic(
        self, mock_get_client, tools, mock_context, sample_query_results, sample_query_status
    ):
        """Test basic get_query_results functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = sample_query_results
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_results(mock_context, query_id='query-results-123')

        assert isinstance(result, QueryResult)
        assert result.query_id == 'query-results-123'
        assert result.query_status == 'FINISHED'
        assert result.query_result_rows is not None
        assert len(result.query_result_rows or []) == 3
        assert result.next_token == 'pagination-token-abc123'
        assert result.query_statistics is not None
        assert result.query_statistics['ResultsCount'] == 100

        # Verify calls were made
        mock_client.get_query_results.assert_called_once_with(
            QueryId='query-results-123', MaxQueryResults=50
        )
        mock_client.describe_query.assert_called_once_with(QueryId='query-results-123')

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_with_max_results(
        self, mock_get_client, tools, mock_context, sample_query_results, sample_query_status
    ):
        """Test get_query_results with custom max_results."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = sample_query_results
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_results(
            mock_context, query_id='query-results-123', max_results=50
        )

        assert isinstance(result, QueryResult)
        assert len(result.query_result_rows or []) == 3

        # Verify max_results was passed correctly
        mock_client.get_query_results.assert_called_once_with(
            QueryId='query-results-123', MaxQueryResults=50
        )

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_with_next_token(
        self, mock_get_client, tools, mock_context, sample_query_results, sample_query_status
    ):
        """Test get_query_results with next_token for pagination."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = {
            'QueryResultRows': [
                [{'VarCharValue': 'ModifyUser'}, {'VarCharValue': '5'}],
            ],
            'NextToken': 'next-page-token-def456',
        }
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_results(
            mock_context, query_id='query-results-123', next_token='previous-token-xyz'
        )

        assert isinstance(result, QueryResult)
        assert len(result.query_result_rows or []) == 1
        assert result.next_token == 'next-page-token-def456'

        # Verify next_token was passed correctly
        mock_client.get_query_results.assert_called_once_with(
            QueryId='query-results-123', MaxQueryResults=50, NextToken='previous-token-xyz'
        )

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_last_page(
        self, mock_get_client, tools, mock_context, sample_query_status
    ):
        """Test get_query_results on last page (no next_token in response)."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = {
            'QueryResultRows': [
                [{'VarCharValue': 'LastEvent'}, {'VarCharValue': '1'}],
            ]
            # No NextToken in response - indicates last page
        }
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_results(mock_context, query_id='query-results-123')

        assert isinstance(result, QueryResult)
        assert len(result.query_result_rows or []) == 1
        assert result.next_token is None  # Should be None on last page

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_empty_results(
        self, mock_get_client, tools, mock_context, sample_query_status
    ):
        """Test get_query_results with empty results."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = {'QueryResultRows': []}
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_results(mock_context, query_id='query-results-123')

        assert isinstance(result, QueryResult)
        assert len(result.query_result_rows or []) == 0
        assert result.next_token is None

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_different_region(
        self, mock_get_client, tools, mock_context, sample_query_results, sample_query_status
    ):
        """Test get_query_results with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = sample_query_results
        mock_client.describe_query.return_value = sample_query_status

        result = await tools.get_query_results(
            mock_context, query_id='query-results-123', region='eu-west-1'
        )

        assert isinstance(result, QueryResult)
        assert result.query_result_rows is not None
        assert len(result.query_result_rows) == 3

        # Verify client was created with correct region
        mock_get_client.assert_called_with('eu-west-1')

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_max_results_boundary(
        self, mock_get_client, tools, mock_context, sample_query_results, sample_query_status
    ):
        """Test get_query_results max_results boundary conditions."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = sample_query_results
        mock_client.describe_query.return_value = sample_query_status

        # Test various max_results values
        test_cases = [
            (None, 50),  # Default
            (1, 1),  # Minimum
            (50, 50),  # Maximum
            (0, 1),  # Below minimum should be adjusted
            (100, 50),  # Above maximum should be adjusted
        ]

        for input_val, expected_val in test_cases:
            await tools.get_query_results(
                mock_context, query_id='query-results-123', max_results=input_val
            )
            call_kwargs = mock_client.get_query_results.call_args[1]
            assert call_kwargs['MaxQueryResults'] == expected_val

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_failed_query(
        self, mock_get_client, tools, mock_context, sample_query_results
    ):
        """Test get_query_results with failed query status."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = sample_query_results
        mock_client.describe_query.return_value = {
            'QueryId': 'query-failed-123',
            'QueryStatus': 'FAILED',
            'ErrorMessage': 'Query execution failed',
            'QueryStatistics': {},
        }

        result = await tools.get_query_results(mock_context, query_id='query-failed-123')

        assert isinstance(result, QueryResult)
        assert result.query_id == 'query-failed-123'
        assert result.query_status == 'FAILED'
        assert result.error_message == 'Query execution failed'
        assert result.query_result_rows is not None
        assert len(result.query_result_rows) == 3  # Still returns results if available

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_error_handling(self, mock_get_client, tools, mock_context):
        """Test get_query_results error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.side_effect = Exception('Query results not available')

        with pytest.raises(Exception, match='Query results not available'):
            await tools.get_query_results(mock_context, query_id='nonexistent-query')

        # Verify error was logged to context
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_get_query_results_describe_query_error(
        self, mock_get_client, tools, mock_context, sample_query_results
    ):
        """Test get_query_results when describe_query fails."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.get_query_results.return_value = sample_query_results
        mock_client.describe_query.side_effect = Exception('Query status not available')

        with pytest.raises(Exception, match='Query status not available'):
            await tools.get_query_results(mock_context, query_id='query-results-123')

        # Verify error was logged to context
        mock_context.error.assert_called_once()


class TestListEventDataStores:
    """Test the list_event_data_stores tool."""

    @pytest.fixture
    def tools(self):
        """Create CloudTrailTools instance."""
        return CloudTrailTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def sample_event_data_stores(self):
        """Sample Event Data Stores for testing."""
        return {
            'EventDataStores': [
                {
                    'EventDataStoreArn': 'arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/eds-123',
                    'Name': 'MyEventDataStore',
                    'MultiRegionEnabled': True,
                    'OrganizationEnabled': False,
                    'Status': 'ENABLED',
                    'CreatedTimestamp': datetime(2023, 1, 1, tzinfo=timezone.utc),
                    'UpdatedTimestamp': datetime(2023, 1, 15, tzinfo=timezone.utc),
                },
                {
                    'EventDataStoreArn': 'arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/eds-456',
                    'Name': 'AnotherEventDataStore',
                    'MultiRegionEnabled': False,
                    'OrganizationEnabled': True,
                    'Status': 'ENABLED',
                    'CreatedTimestamp': datetime(2023, 2, 1, tzinfo=timezone.utc),
                    'UpdatedTimestamp': datetime(2023, 2, 10, tzinfo=timezone.utc),
                },
            ]
        }

    @pytest.fixture
    def sample_event_data_store_details(self):
        """Sample Event Data Store details for testing."""
        return {
            'AdvancedEventSelectors': [
                {
                    'Name': 'Log all management events',
                    'FieldSelectors': [{'Field': 'eventCategory', 'Equals': ['Management']}],
                }
            ],
            'MultiRegionEnabled': True,
            'OrganizationEnabled': False,
        }

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_list_event_data_stores_basic(
        self, mock_get_client, tools, mock_context, sample_event_data_stores
    ):
        """Test basic list_event_data_stores functionality."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_event_data_stores.return_value = sample_event_data_stores
        mock_client.get_event_data_store.return_value = {
            'AdvancedEventSelectors': [],
            'MultiRegionEnabled': True,
            'OrganizationEnabled': False,
        }

        result = await tools.list_event_data_stores(mock_context)

        assert len(result) == 2
        assert result[0]['name'] == 'MyEventDataStore'
        assert result[1]['multi_region_enabled'] is True

        mock_client.list_event_data_stores.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_list_event_data_stores_with_details(
        self,
        mock_get_client,
        tools,
        mock_context,
        sample_event_data_stores,
        sample_event_data_store_details,
    ):
        """Test list_event_data_stores with detailed information."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_event_data_stores.return_value = sample_event_data_stores
        mock_client.get_event_data_store.return_value = sample_event_data_store_details

        result = await tools.list_event_data_stores(mock_context, include_details=True)

        assert len(result) == 2

        # Verify get_event_data_store was called for each EDS
        assert mock_client.get_event_data_store.call_count == 2

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_list_event_data_stores_without_details(
        self, mock_get_client, tools, mock_context, sample_event_data_stores
    ):
        """Test list_event_data_stores without detailed information."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_event_data_stores.return_value = sample_event_data_stores

        result = await tools.list_event_data_stores(mock_context, include_details=False)

        assert len(result) == 2

        # Verify get_event_data_store was not called
        mock_client.get_event_data_store.assert_not_called()

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_list_event_data_stores_different_region(
        self, mock_get_client, tools, mock_context, sample_event_data_stores
    ):
        """Test list_event_data_stores with different AWS region."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_event_data_stores.return_value = sample_event_data_stores
        mock_client.get_event_data_store.return_value = {}

        result = await tools.list_event_data_stores(mock_context, region='us-west-2')

        assert len(result) == 2

        # Verify client was created with correct region
        mock_get_client.assert_called_with('us-west-2')

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_list_event_data_stores_empty_result(self, mock_get_client, tools, mock_context):
        """Test list_event_data_stores with no Event Data Stores."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_event_data_stores.return_value = {'EventDataStores': []}

        result = await tools.list_event_data_stores(mock_context)

        assert len(result) == 0

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_list_event_data_stores_detail_error_handling(
        self, mock_get_client, tools, mock_context, sample_event_data_stores
    ):
        """Test list_event_data_stores when detail retrieval fails."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_event_data_stores.return_value = sample_event_data_stores
        mock_client.get_event_data_store.side_effect = Exception('Access denied for details')

        # Should not raise exception, but log warning
        result = await tools.list_event_data_stores(mock_context, include_details=True)

        assert len(result) == 2
        # Should still return basic info even if details fail

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_list_event_data_stores_error_handling(
        self, mock_get_client, tools, mock_context
    ):
        """Test list_event_data_stores error handling."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.list_event_data_stores.side_effect = Exception('Access denied')

        with pytest.raises(Exception, match='Access denied'):
            await tools.list_event_data_stores(mock_context)

        # Verify error was logged to context
        mock_context.error.assert_called_once()


class TestToolRegistration:
    """Test tool registration functionality."""

    def test_register_tools(self):
        """Test that all tools are registered with MCP server."""
        mock_mcp = Mock()
        mock_tool_decorator = Mock()
        mock_mcp.tool.return_value = mock_tool_decorator

        tools = CloudTrailTools()
        tools.register(mock_mcp)

        # Verify all tools were registered
        expected_calls = [
            call(name='lookup_events'),
            call(name='lake_query'),
            call(name='get_query_status'),
            call(name='get_query_results'),
            call(name='list_event_data_stores'),
        ]

        assert mock_mcp.tool.call_count == 5
        mock_mcp.tool.assert_has_calls(expected_calls, any_order=True)

        # Verify decorators were applied
        assert mock_tool_decorator.call_count == 5


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def tools(self):
        """Create CloudTrailTools instance."""
        return CloudTrailTools()

    @pytest.fixture
    def mock_context(self):
        """Create mock Context."""
        return AsyncMock(spec=Context)

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_with_all_attributes(self, mock_get_client, tools, mock_context):
        """Test lookup_events with all possible attribute keys."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {'Events': []}

        attribute_keys = [
            'EventId',
            'EventName',
            'ReadOnly',
            'Username',
            'ResourceType',
            'ResourceName',
            'EventSource',
            'AccessKeyId',
        ]

        for attr_key in attribute_keys:
            await tools.lookup_events(
                mock_context, attribute_key=attr_key, attribute_value='test-value'
            )

            # Verify correct attribute was used
            call_kwargs = mock_client.lookup_events.call_args[1]
            assert call_kwargs['LookupAttributes'][0]['AttributeKey'] == attr_key

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_lookup_events_max_results_boundary(self, mock_get_client, tools, mock_context):
        """Test lookup_events max_results boundary conditions."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.lookup_events.return_value = {'Events': []}

        # Test various max_results values
        test_cases = [
            (None, 10),  # Default
            (1, 1),  # Minimum
            (50, 50),  # Maximum
            (0, 1),  # Below minimum should be adjusted
            (100, 50),  # Above maximum should be adjusted
        ]

        for input_val, expected_val in test_cases:
            await tools.lookup_events(mock_context, max_results=input_val)
            call_kwargs = mock_client.lookup_events.call_args[1]
            assert call_kwargs['MaxResults'] == expected_val

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    @patch('time.sleep')
    async def test_lake_query_timeout_scenario(
        self, mock_sleep, mock_get_client, tools, mock_context
    ):
        """Test lake_query when query times out."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.start_query.return_value = {'QueryId': 'query-timeout'}

        # Mock describe_query to always return RUNNING status
        mock_client.describe_query.return_value = {
            'QueryId': 'query-timeout',
            'QueryStatus': 'RUNNING',
            'QueryStatistics': {},
        }

        sql = 'SELECT * FROM eds-timeout'
        result = await tools.lake_query(mock_context, sql=sql)

        assert isinstance(result, QueryResult)
        assert result.query_id == 'query-timeout'
        assert result.query_status == 'RUNNING'

        # Verify polling occurred multiple times
        assert mock_client.describe_query.call_count > 1

    @pytest.mark.asyncio
    @patch.object(CloudTrailTools, '_get_cloudtrail_client')
    async def test_query_status_with_delivery_info(self, mock_get_client, tools, mock_context):
        """Test get_query_status with delivery information."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.describe_query.return_value = {
            'QueryId': 'query-delivery',
            'QueryStatus': 'FINISHED',
            'QueryStatistics': {'ResultsCount': 100},
            'DeliveryS3Uri': 's3://bucket/results/',
            'DeliveryStatus': 'SUCCESS',
        }

        result = await tools.get_query_status(mock_context, query_id='query-delivery')

        assert isinstance(result, QueryStatus)
        assert result.delivery_s3_uri == 's3://bucket/results/'
        assert result.delivery_status == 'SUCCESS'


class TestModels:
    """Test Pydantic models."""

    def test_query_result_model(self):
        """Test QueryResult model creation and validation."""
        result = QueryResult(
            query_id='test-query',
            query_status='FINISHED',
            query_result_rows=[],
            query_statistics={'ResultsCount': 0},
        )

        assert result.query_id == 'test-query'
        assert result.query_status == 'FINISHED'
        assert result.query_result_rows == []
        assert result.query_statistics is not None
        assert result.query_statistics['ResultsCount'] == 0
        assert result.next_token is None
        assert result.error_message is None

        # Test that None values are excluded from serialization
        result_dict = result.model_dump()
        assert 'next_token' not in result_dict
        assert 'error_message' not in result_dict

    def test_query_status_model(self):
        """Test QueryStatus model creation and validation."""
        status = QueryStatus(
            query_id='status-query',
            query_status='RUNNING',
            query_statistics={'ExecutionTimeInMillis': 5000},
            error_message=None,
            delivery_s3_uri='s3://bucket/path/',
            delivery_status='IN_PROGRESS',
        )

        assert status.query_id == 'status-query'
        assert status.query_status == 'RUNNING'
        assert status.query_statistics is not None
        assert status.query_statistics['ExecutionTimeInMillis'] == 5000
        assert status.error_message is None
        assert status.delivery_s3_uri == 's3://bucket/path/'
        assert status.delivery_status == 'IN_PROGRESS'

    def test_event_data_store_model_with_aliases(self):
        """Test EventDataStore model with AWS API aliases."""
        # Test with AWS API field names (PascalCase)
        data = {
            'EventDataStoreArn': 'arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/test',
            'Name': 'TestEDS',
            'Status': 'ENABLED',
            'MultiRegionEnabled': True,
            'OrganizationEnabled': False,
            'RetentionPeriod': 90,
            'CreatedTimestamp': datetime.now(timezone.utc),
            'UpdatedTimestamp': datetime.now(timezone.utc),
        }

        eds = EventDataStore.model_validate(data)

        assert eds.event_data_store_arn == data['EventDataStoreArn']
        assert eds.name == data['Name']
        assert eds.status == data['Status']
        assert eds.multi_region_enabled == data['MultiRegionEnabled']
        assert eds.organization_enabled == data['OrganizationEnabled']
        assert eds.retention_period == data['RetentionPeriod']

    def test_event_data_store_model_with_snake_case(self):
        """Test EventDataStore model with snake_case field names."""
        data = {
            'event_data_store_arn': 'arn:aws:cloudtrail:us-east-1:123456789012:eventdatastore/test',
            'name': 'TestEDS',
            'status': 'ENABLED',
            'multi_region_enabled': True,
            'organization_enabled': False,
        }

        eds = EventDataStore.model_validate(data)

        assert eds.event_data_store_arn == data['event_data_store_arn']
        assert eds.name == data['name']
        assert eds.status == data['status']
        assert eds.multi_region_enabled == data['multi_region_enabled']
        assert eds.organization_enabled == data['organization_enabled']


if __name__ == '__main__':
    pytest.main([__file__])
