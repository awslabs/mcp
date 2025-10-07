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

"""Tests for CloudWatch Logs error handling and edge cases."""

import pytest
import pytest_asyncio
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools import CloudWatchLogsTools
from unittest.mock import AsyncMock, Mock, patch


@pytest_asyncio.fixture
async def mock_context():
    """Create mock MCP context."""
    context = Mock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    return context


class TestParameterValidation:
    """Test parameter validation and edge cases."""

    def test_validate_log_group_parameters_both_provided(self):
        """Test validation when both parameters are provided - should raise error."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            with pytest.raises(ValueError) as exc_info:
                tools._validate_log_group_parameters(['group1'], ['arn1'])

            assert (
                'Exactly one of log_group_names or log_group_identifiers must be provided'
                in str(exc_info.value)
            )

    def test_validate_log_group_parameters_neither_provided(self):
        """Test validation when neither parameter is provided - should raise error."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            with pytest.raises(ValueError) as exc_info:
                tools._validate_log_group_parameters(None, None)

            assert (
                'Exactly one of log_group_names or log_group_identifiers must be provided'
                in str(exc_info.value)
            )

    def test_validate_log_group_parameters_valid_cases(self):
        """Test validation with valid parameter combinations."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            # Should not raise - only log_group_names provided
            tools._validate_log_group_parameters(['group1'], None)

            # Should not raise - only log_group_identifiers provided
            tools._validate_log_group_parameters(None, ['arn1'])

    def test_convert_time_to_timestamp(self):
        """Test time string to timestamp conversion."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            # Test valid ISO 8601 time
            timestamp = tools._convert_time_to_timestamp('2023-01-01T00:00:00+00:00')
            assert isinstance(timestamp, int)
            assert timestamp > 0

    def test_build_logs_query_params(self):
        """Test building logs query parameters."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            params = tools._build_logs_query_params(
                log_group_names=['group1'],
                log_group_identifiers=None,
                start_time='2023-01-01T00:00:00+00:00',
                end_time='2023-01-01T01:00:00+00:00',
                query_string='fields @message',
                limit=100,
            )

            assert 'startTime' in params
            assert 'endTime' in params
            assert params['queryString'] == 'fields @message'
            assert params['logGroupNames'] == ['group1']
            assert params['logGroupIdentifiers'] is None
            assert params['limit'] == 100

    def test_process_query_results(self):
        """Test processing query results."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            raw_response = {
                'queryId': 'test-query-id',
                'status': 'Complete',
                'statistics': {'recordsMatched': 10},
                'results': [
                    [
                        {'field': '@timestamp', 'value': '2023-01-01T00:00:00Z'},
                        {'field': '@message', 'value': 'Test message'},
                    ]
                ],
            }

            processed = tools._process_query_results(raw_response, 'custom-query-id')

            assert processed['queryId'] == 'custom-query-id'
            assert processed['status'] == 'Complete'
            assert len(processed['results']) == 1
            assert processed['results'][0]['@timestamp'] == '2023-01-01T00:00:00Z'
            assert processed['results'][0]['@message'] == 'Test message'


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_describe_log_groups_api_error(self, mock_context):
        """Test describe_log_groups with API error - covers lines 367-371."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_paginator.side_effect = Exception('API Error')
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            with pytest.raises(Exception) as exc_info:
                await tools.describe_log_groups(mock_context)

            assert 'API Error' in str(exc_info.value)
            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_log_group_api_error(self, mock_context):
        """Test analyze_log_group with API error - covers lines 374-376, 379, 382."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_paginator.side_effect = Exception('Anomaly API Error')
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            with pytest.raises(Exception) as exc_info:
                await tools.analyze_log_group(
                    mock_context,
                    log_group_arn='arn:aws:logs:us-east-1:123456789012:log-group:test-group',
                    start_time='2023-01-01T00:00:00+00:00',
                    end_time='2023-01-01T01:00:00+00:00',
                )

            assert 'Anomaly API Error' in str(exc_info.value)
            # The analyze_log_group method calls other methods that also log errors,
            # so we expect multiple error calls
            assert mock_context.error.call_count >= 1

    @pytest.mark.asyncio
    async def test_execute_log_insights_query_api_error(self, mock_context):
        """Test execute_log_insights_query with API error - covers lines 455-458."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.start_query.side_effect = Exception('Query API Error')
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            result = await tools.execute_log_insights_query(
                mock_context,
                log_group_names=['test-group'],
                log_group_identifiers=None,
                start_time='2023-01-01T00:00:00+00:00',
                end_time='2023-01-01T01:00:00+00:00',
                query_string='fields @message',
                limit=10,
                max_timeout=30,
            )

            # Verify error response structure instead of exception
            assert result['status'] == 'Error'
            assert result['results'] == []
            assert 'Query API Error' in result['message']
            assert result['queryId'] == ''
            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_logs_insight_query_results_api_error(self, mock_context):
        """Test get_logs_insight_query_results with API error - covers lines 579-582."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_query_results.side_effect = Exception('Query Results API Error')
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            result = await tools.get_logs_insight_query_results(
                mock_context, query_id='test-query-id'
            )

            # Verify error response structure instead of exception
            assert result['status'] == 'Error'
            assert result['results'] == []
            assert 'Query Results API Error' in result['message']
            assert result['queryId'] == 'test-query-id'
            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_logs_insight_query_api_error(self, mock_context):
        """Test cancel_logs_insight_query with API error - covers lines 604-607."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.stop_query.side_effect = Exception('Cancel Query API Error')
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            with pytest.raises(Exception) as exc_info:
                await tools.cancel_logs_insight_query(mock_context, query_id='test-query-id')

            assert 'Cancel Query API Error' in str(exc_info.value)
            mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_for_query_completion_timeout(self, mock_context):
        """Test polling timeout scenario."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            # Always return 'Running' status to trigger timeout
            mock_client.get_query_results.return_value = {'status': 'Running', 'results': []}
            mock_session.return_value.client.return_value = mock_client
            tools = CloudWatchLogsTools()
            # Use very short timeout to trigger timeout quickly
            result = await tools._poll_for_query_completion(
                mock_client, 'test-query-id', 1, mock_context
            )
            assert result['queryId'] == 'test-query-id'
            assert result['status'] == 'Polling Timeout'
            assert 'message' in result
            mock_context.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_for_query_completion_failed_status(self, mock_context):
        """Test polling with failed query status."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_query_results.return_value = {
                'queryId': 'test-query-id',
                'status': 'Failed',
                'results': [],
            }
            mock_session.return_value.client.return_value = mock_client
            tools = CloudWatchLogsTools()
            result = await tools._poll_for_query_completion(
                mock_client, 'test-query-id', 30, mock_context
            )
            assert result['queryId'] == 'test-query-id'
            assert result['status'] == 'Failed'

    @pytest.mark.asyncio
    async def test_poll_for_query_completion_cancelled_status(self, mock_context):
        """Test polling with cancelled query status."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_query_results.return_value = {
                'queryId': 'test-query-id',
                'status': 'Cancelled',
                'results': [],
            }
            mock_session.return_value.client.return_value = mock_client
            tools = CloudWatchLogsTools()
            result = await tools._poll_for_query_completion(
                mock_client, 'test-query-id', 30, mock_context
            )
            assert result['queryId'] == 'test-query-id'
            assert result['status'] == 'Cancelled'

    @pytest.mark.asyncio
    async def test_poll_for_query_completion_unexpected_status(self, mock_context):
        """Test polling with unexpected query status."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_query_results.return_value = {
                'queryId': 'test-query-id',
                'status': 'UnknownStatus',  # Unexpected status
                'results': [],
            }
            mock_session.return_value.client.return_value = mock_client
            tools = CloudWatchLogsTools()
            result = await tools._poll_for_query_completion(
                mock_client, 'test-query-id', 30, mock_context
            )
            assert result['queryId'] == 'test-query-id'
            assert result['status'] == 'UnknownStatus'
            assert result['results'] == []

    @pytest.mark.asyncio
    async def test_poll_for_query_completion_polling_exception(self, mock_context):
        """Test polling with exception during get_query_results."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_query_results.side_effect = Exception('Network timeout during polling')
            mock_session.return_value.client.return_value = mock_client
            tools = CloudWatchLogsTools()

            result = await tools._poll_for_query_completion(
                mock_client, 'test-query-id', 30, mock_context
            )

            # Verify error response structure
            assert result['queryId'] == 'test-query-id'
            assert result['status'] == 'Error'
            assert 'Network timeout during polling' in result['message']
            assert result['results'] == []

            # Verify context error was called
            mock_context.error.assert_called_once()
            error_call_args = mock_context.error.call_args[0][0]
            assert 'Error during query polling' in error_call_args
            assert 'Network timeout during polling' in error_call_args


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_process_query_results_missing_fields(self):
        """Test processing query results with missing optional fields."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            # Response with minimal fields
            raw_response = {
                'status': 'Complete',
                # Missing queryId, results
            }

            processed = tools._process_query_results(raw_response, 'fallback-id')

            assert processed['queryId'] == 'fallback-id'
            assert processed['status'] == 'Complete'
            assert processed['results'] == []

    def test_aws_profile_initialization(self):
        """Test initialization with AWS_PROFILE environment variable."""
        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client

                tools = CloudWatchLogsTools()
                # Actually call a method that creates the client
                tools._get_logs_client('us-east-1')

                # Verify session was created with profile
                mock_session.assert_called_with(
                    profile_name='test-profile', region_name='us-east-1'
                )

    @pytest.mark.asyncio
    async def test_boto3_client_error_handling(self, mock_context):
        """Test error handling when boto3 client creation fails."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_session.side_effect = Exception('AWS credentials not found')

            tools = CloudWatchLogsTools()
            with pytest.raises(Exception, match='AWS credentials not found'):
                await tools.describe_log_groups(mock_context)

    def test_tools_registration(self):
        """Test that all tools are properly registered."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            mock_mcp = Mock()
            tools.register(mock_mcp)

            # Verify all tools are registered
            assert mock_mcp.tool.call_count == 5
            tool_calls = [call[1]['name'] for call in mock_mcp.tool.call_args_list]
            expected_tools = [
                'describe_log_groups',
                'analyze_log_group',
                'execute_log_insights_query',
                'get_logs_insight_query_results',
                'cancel_logs_insight_query',
            ]
            for tool in expected_tools:
                assert tool in tool_calls

    def test_build_logs_query_params_with_none_values(self):
        """Test building query params with None values."""
        with patch('awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'):
            tools = CloudWatchLogsTools()

            params = tools._build_logs_query_params(
                log_group_names=None,
                log_group_identifiers=['arn:test'],
                start_time='2023-01-01T00:00:00+00:00',
                end_time='2023-01-01T01:00:00+00:00',
                query_string='fields @message',
                limit=None,
            )

            assert params['logGroupNames'] is None
            assert params['logGroupIdentifiers'] == ['arn:test']
            assert params['limit'] is None


class TestRegionHandling:
    """Test region parameter handling across tools."""

    def test_get_logs_client_region_parameter(self):
        """Test that _get_logs_client creates client with correct region."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()
            result = tools._get_logs_client('ap-northeast-1')

            # Verify session was created with correct region
            mock_session.assert_called_with(region_name='ap-northeast-1')
            mock_session.return_value.client.assert_called_with(
                'logs', config=mock_session.return_value.client.call_args[1]['config']
            )
            assert result == mock_client

    def test_get_logs_client_with_aws_profile(self):
        """Test _get_logs_client with AWS_PROFILE environment variable."""
        with patch.dict('os.environ', {'AWS_PROFILE': 'test-profile'}):
            with patch(
                'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
            ) as mock_session:
                mock_client = Mock()
                mock_session.return_value.client.return_value = mock_client

                tools = CloudWatchLogsTools()
                result = tools._get_logs_client('ca-central-1')

                # Verify session was created with profile and region
                mock_session.assert_called_with(
                    profile_name='test-profile', region_name='ca-central-1'
                )
                assert result == mock_client

    @pytest.mark.asyncio
    async def test_execute_log_insights_query_region_parameter(self, mock_context):
        """Test that execute_log_insights_query uses correct region for client creation."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.start_query.return_value = {'queryId': 'test-query-id'}
            mock_client.get_query_results.return_value = {
                'status': 'Complete',
                'results': [],
                'statistics': {},
            }
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            # Mock _get_logs_client to capture the region parameter
            with patch.object(
                tools, '_get_logs_client', return_value=mock_client
            ) as mock_get_client:
                await tools.execute_log_insights_query(
                    mock_context,
                    log_group_names=['test-group'],
                    log_group_identifiers=None,
                    start_time='2023-01-01T00:00:00+00:00',
                    end_time='2023-01-01T01:00:00+00:00',
                    query_string='fields @message',
                    region='ap-southeast-2',
                )

                # Verify _get_logs_client was called with correct region
                mock_get_client.assert_called_once_with('ap-southeast-2')

    @pytest.mark.asyncio
    async def test_get_logs_insight_query_results_region_parameter(self, mock_context):
        """Test that get_logs_insight_query_results uses correct region for client creation."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.get_query_results.return_value = {
                'status': 'Complete',
                'results': [],
                'statistics': {},
            }
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            # Mock _get_logs_client to capture the region parameter
            with patch.object(
                tools, '_get_logs_client', return_value=mock_client
            ) as mock_get_client:
                await tools.get_logs_insight_query_results(
                    mock_context, query_id='test-query-id', region='eu-central-1'
                )

                # Verify _get_logs_client was called with correct region
                mock_get_client.assert_called_once_with('eu-central-1')

    @pytest.mark.asyncio
    async def test_cancel_logs_insight_query_region_parameter(self, mock_context):
        """Test that cancel_logs_insight_query uses correct region for client creation."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_client.stop_query.return_value = {'success': True}
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            # Mock _get_logs_client to capture the region parameter
            with patch.object(
                tools, '_get_logs_client', return_value=mock_client
            ) as mock_get_client:
                await tools.cancel_logs_insight_query(
                    mock_context, query_id='test-query-id', region='sa-east-1'
                )

                # Verify _get_logs_client was called with correct region
                mock_get_client.assert_called_once_with('sa-east-1')

    @pytest.mark.asyncio
    async def test_describe_log_groups_region_parameter(self, mock_context):
        """Test that describe_log_groups uses correct region for client creation."""
        with patch(
            'awslabs.cloudwatch_mcp_server.cloudwatch_logs.tools.boto3.Session'
        ) as mock_session:
            mock_client = Mock()
            mock_paginator = Mock()
            mock_paginator.paginate.return_value = [{'logGroups': []}]
            mock_client.get_paginator.return_value = mock_paginator
            mock_client.describe_query_definitions.return_value = {'queryDefinitions': []}
            mock_session.return_value.client.return_value = mock_client

            tools = CloudWatchLogsTools()

            # Mock _get_logs_client to capture the region parameter
            with patch.object(
                tools, '_get_logs_client', return_value=mock_client
            ) as mock_get_client:
                await tools.describe_log_groups(mock_context, region='us-west-1')

                # Verify _get_logs_client was called with correct region
                mock_get_client.assert_called_once_with('us-west-1')
