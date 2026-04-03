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

"""Test cases for the get_cloudwan_logs tool."""

import importlib
import json
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
logs_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_logs'
)


class TestGetCloudwanLogs:
    """Test cases for get_cloudwan_logs function."""

    @pytest.fixture
    def sample_log_event(self):
        """Sample CloudWatch log event."""
        return {
            'time': '2024-01-15T10:30:00Z',
            'detail-type': 'Network Manager Topology Change',
            'detail': {
                'changeType': 'ATTACHMENT_CREATED',
                'changeDescription': 'VPC attachment created',
                'edgeLocation': 'us-east-1',
                'segmentName': 'production',
                'attachmentArn': 'arn:aws:networkmanager::123456789012:attachment/attachment-123',
                'coreNetworkArn': 'arn:aws:networkmanager::123456789012:core-network/core-123',
            },
        }

    @pytest.fixture
    def query_results(self, sample_log_event):
        """Sample CloudWatch Logs query results."""
        return {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2024-01-15 10:30:00.000'},
                    {'field': '@message', 'value': json.dumps(sample_log_event)},
                ]
            ],
        }

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_success(self, mock_sleep, mock_get_client, query_results):
        """Test successful log retrieval."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        result = await logs_module.get_cwan_logs()

        assert 'summary' in result
        assert 'events_by_location' in result
        assert result['summary']['total_events'] == 1
        assert result['summary']['by_change_type']['ATTACHMENT_CREATED'] == 1
        assert result['summary']['by_edge_location']['us-east-1'] == 1
        assert 'us-east-1' in result['events_by_location']

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_topology_change_filter(self, mock_sleep, mock_get_client, query_results):
        """Test filtering by topology change event type."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await logs_module.get_cwan_logs(event_type='Network Manager Topology Change')

        call_args = mock_logs.start_query.call_args
        query_string = call_args[1]['queryString']
        assert 'Network Manager Topology Change' in query_string

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_routing_update_filter(self, mock_sleep, mock_get_client, query_results):
        """Test filtering by routing update event type."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await logs_module.get_cwan_logs(event_type='Network Manager Routing Update')

        call_args = mock_logs.start_query.call_args
        query_string = call_args[1]['queryString']
        assert 'Network Manager Routing Update' in query_string

    @patch.object(logs_module, 'get_aws_client')
    async def test_invalid_event_type(self, mock_get_client):
        """Test error handling for invalid event type."""
        with pytest.raises(ToolError, match='Event type invalid is not supported'):
            await logs_module.get_cwan_logs(event_type='invalid')

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_no_results(self, mock_sleep, mock_get_client):
        """Test when query returns no results."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = {'status': 'Complete', 'results': []}

        with pytest.raises(ToolError, match='No flow logs found'):
            await logs_module.get_cwan_logs()

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_query_failed(self, mock_sleep, mock_get_client):
        """Test when CloudWatch query fails."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = {'status': 'Failed'}

        with pytest.raises(ToolError, match='There was an error with the query'):
            await logs_module.get_cwan_logs()

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_query_timeout(self, mock_sleep, mock_get_client):
        """Test when CloudWatch query times out."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = {'status': 'Timeout'}

        with pytest.raises(ToolError, match='There was an error with the query'):
            await logs_module.get_cwan_logs()

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_custom_time_period(self, mock_sleep, mock_get_client, query_results):
        """Test with custom time period."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await logs_module.get_cwan_logs(time_period=60)

        call_args = mock_logs.start_query.call_args
        # Verify time range is 60 minutes
        start_time = call_args[1]['startTime']
        end_time = call_args[1]['endTime']
        assert end_time - start_time == 3600  # 60 minutes in seconds

    @patch.object(logs_module, 'get_aws_client')
    async def test_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs
        mock_logs.start_query.side_effect = Exception('Access denied')

        with pytest.raises(ToolError, match='There was an error getting AWS Cloud WAN logs'):
            await logs_module.get_cwan_logs()

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_multiple_events_grouping(self, mock_sleep, mock_get_client):
        """Test grouping of multiple events by edge location."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        events = [
            {
                'time': '2024-01-15T10:30:00Z',
                'detail': {
                    'changeType': 'ATTACHMENT_CREATED',
                    'edgeLocation': 'us-east-1',
                    'segmentName': 'prod',
                },
            },
            {
                'time': '2024-01-15T10:31:00Z',
                'detail': {
                    'changeType': 'ROUTE_UPDATED',
                    'edgeLocation': 'us-west-2',
                    'segmentName': 'dev',
                },
            },
        ]

        query_results = {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2024-01-15 10:30:00.000'},
                    {'field': '@message', 'value': json.dumps(events[0])},
                ],
                [
                    {'field': '@timestamp', 'value': '2024-01-15 10:31:00.000'},
                    {'field': '@message', 'value': json.dumps(events[1])},
                ],
            ],
        }

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        result = await logs_module.get_cwan_logs()

        assert result['summary']['total_events'] == 2
        assert result['summary']['by_change_type']['ATTACHMENT_CREATED'] == 1
        assert result['summary']['by_change_type']['ROUTE_UPDATED'] == 1
        assert result['summary']['by_edge_location']['us-east-1'] == 1
        assert result['summary']['by_edge_location']['us-west-2'] == 1
        assert len(result['events_by_location']) == 2

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_uses_us_west_2_region(self, mock_sleep, mock_get_client, query_results):
        """Test that the function uses us-west-2 region for logs."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await logs_module.get_cwan_logs(profile_name='test-profile')

        mock_get_client.assert_called_once_with('logs', 'us-west-2', 'test-profile')

    @patch.object(logs_module, 'get_aws_client')
    @patch('time.sleep')
    async def test_correct_log_group(self, mock_sleep, mock_get_client, query_results):
        """Test that the function uses correct log group name."""
        mock_logs = MagicMock()
        mock_get_client.return_value = mock_logs

        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await logs_module.get_cwan_logs()

        call_args = mock_logs.start_query.call_args
        assert call_args[1]['logGroupName'] == '/aws/events/networkmanagerloggroup'
        assert call_args[1]['limit'] == 10
