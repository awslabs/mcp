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

"""Test cases for the get_tgw_flow_logs tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs import (
    get_tgw_flow_logs,
)
from fastmcp.exceptions import ToolError
from typing import Any, Dict
from unittest.mock import MagicMock, patch


class TestGetTgwFlowLogs:
    """Test cases for get_tgw_flow_logs function."""

    @pytest.fixture
    def flow_logs_response(self):
        """Sample flow logs API response."""
        return {
            'FlowLogs': [
                {
                    'FlowLogId': 'fl-12345678',
                    'ResourceId': 'tgw-12345678',
                    'LogDestinationType': 'cloud-watch-logs',
                    'LogGroupName': '/aws/transitgateway/flowlogs',
                    'FlowLogStatus': 'ACTIVE',
                }
            ]
        }

    @pytest.fixture
    def query_results(self):
        """Sample CloudWatch Logs query results."""
        return {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2024-01-15 10:30:00.000'},
                    {
                        'field': '@message',
                        'value': '5 TransitGateway 123456789012 tgw-12345678 tgw-attach-123 123456789012 123456789012 vpc-src vpc-dst subnet-src subnet-dst eni-src eni-dst az-src az-dst tgw-attach-pair 10.0.1.100 10.0.2.200 443 80 6 10 1024 1642248600 1642248660 OK IPv4 0 0 0 0',
                    },
                ]
            ],
        }

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    @patch('time.sleep')
    async def test_success(self, mock_sleep, mock_get_client, flow_logs_response, query_results):
        """Test successful flow logs retrieval."""
        mock_ec2 = MagicMock()
        mock_logs = MagicMock()
        mock_get_client.side_effect = [mock_ec2, mock_logs]

        mock_ec2.describe_flow_logs.return_value = flow_logs_response
        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        result = await get_tgw_flow_logs('tgw-12345678')

        assert len(result) == 1
        log_entry: Dict[str, Any] = result[0]
        assert log_entry['tgw_id'] == 'tgw-12345678'
        assert log_entry['srcaddr'] == '10.0.1.100'
        assert log_entry['dstaddr'] == '10.0.2.200'
        assert log_entry['srcport'] == '443'
        assert log_entry['dstport'] == '80'
        assert log_entry['log_status'] == 'OK'

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    async def test_no_flow_logs(self, mock_get_client):
        """Test when no flow logs exist."""
        mock_ec2 = MagicMock()
        mock_get_client.return_value = mock_ec2
        mock_ec2.describe_flow_logs.return_value = {'FlowLogs': None}

        with pytest.raises(ToolError, match='There are no flow logs for the Transit Gateway'):
            await get_tgw_flow_logs('tgw-12345678')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    async def test_no_cloudwatch_logs(self, mock_get_client):
        """Test when flow logs not stored in CloudWatch."""
        mock_ec2 = MagicMock()
        mock_get_client.return_value = mock_ec2
        mock_ec2.describe_flow_logs.return_value = {'FlowLogs': [{'LogDestinationType': 's3'}]}

        with pytest.raises(ToolError, match='is not stored in CloudWatch Logs'):
            await get_tgw_flow_logs('tgw-12345678')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    @patch('time.sleep')
    async def test_no_results(self, mock_sleep, mock_get_client, flow_logs_response):
        """Test when query returns no results."""
        mock_ec2 = MagicMock()
        mock_logs = MagicMock()
        mock_get_client.side_effect = [mock_ec2, mock_logs]

        mock_ec2.describe_flow_logs.return_value = flow_logs_response
        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = {'status': 'Complete', 'results': []}

        with pytest.raises(ToolError, match='No flow logs found'):
            await get_tgw_flow_logs('tgw-12345678')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    @patch('time.sleep')
    async def test_query_failed(self, mock_sleep, mock_get_client, flow_logs_response):
        """Test when CloudWatch query fails."""
        mock_ec2 = MagicMock()
        mock_logs = MagicMock()
        mock_get_client.side_effect = [mock_ec2, mock_logs]

        mock_ec2.describe_flow_logs.return_value = flow_logs_response
        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = {'status': 'Failed'}

        with pytest.raises(ToolError, match='There was an error with the query'):
            await get_tgw_flow_logs('tgw-12345678')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    @patch('time.sleep')
    async def test_with_filters(
        self, mock_sleep, mock_get_client, flow_logs_response, query_results
    ):
        """Test with IP and port filters."""
        mock_ec2 = MagicMock()
        mock_logs = MagicMock()
        mock_get_client.side_effect = [mock_ec2, mock_logs]

        mock_ec2.describe_flow_logs.return_value = flow_logs_response
        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await get_tgw_flow_logs(
            'tgw-12345678', srcaddr='10.0.1.100', dstaddr='10.0.2.200', srcport=443, dstport=80
        )

        # Verify query string contains filters
        call_args = mock_logs.start_query.call_args
        query_string = call_args[1]['queryString']
        assert "srcaddr = '10.0.1.100'" in query_string
        assert "dstaddr = '10.0.2.200'" in query_string
        assert 'srcport = 443' in query_string
        assert 'dstport = 80' in query_string

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    @patch('time.sleep')
    async def test_custom_time_range(
        self, mock_sleep, mock_get_client, flow_logs_response, query_results
    ):
        """Test with custom time range."""
        mock_ec2 = MagicMock()
        mock_logs = MagicMock()
        mock_get_client.side_effect = [mock_ec2, mock_logs]

        mock_ec2.describe_flow_logs.return_value = flow_logs_response
        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await get_tgw_flow_logs('tgw-12345678', time_period=30, start_time='2024-01-15T10:00:00Z')

        # Verify time range parameters
        call_args = mock_logs.start_query.call_args
        assert call_args[1]['startTime'] == 1705311000  # 09:30 UTC
        assert call_args[1]['endTime'] == 1705312800  # 10:00 UTC

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    @patch('time.sleep')
    async def test_custom_entry_limit(
        self, mock_sleep, mock_get_client, flow_logs_response, query_results
    ):
        """Test with custom entry limit."""
        mock_ec2 = MagicMock()
        mock_logs = MagicMock()
        mock_get_client.side_effect = [mock_ec2, mock_logs]

        mock_ec2.describe_flow_logs.return_value = flow_logs_response
        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = query_results

        await get_tgw_flow_logs('tgw-12345678', entry_limit='50')

        call_args = mock_logs.start_query.call_args
        assert call_args[1]['limit'] == '50'

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    async def test_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_ec2 = MagicMock()
        mock_get_client.return_value = mock_ec2
        mock_ec2.describe_flow_logs.side_effect = Exception('AWS Error')

        with pytest.raises(ToolError, match='Error getting Transit Gateway flow logs'):
            await get_tgw_flow_logs('tgw-12345678')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    async def test_with_profile(self, mock_get_client, flow_logs_response):
        """Test with custom AWS profile."""
        mock_ec2 = MagicMock()
        mock_get_client.return_value = mock_ec2
        mock_ec2.describe_flow_logs.return_value = {'FlowLogs': None}

        try:
            await get_tgw_flow_logs('tgw-12345678', profile_name='test-profile')
        except ToolError:
            pass  # Expected due to no flow logs

        mock_get_client.assert_called_with('ec2', None, 'test-profile')

    @patch(
        'awslabs.aws_network_mcp_server.tools.transit_gateway.get_transit_gateway_flow_logs.get_aws_client'
    )
    @patch('time.sleep')
    async def test_query_timeout(self, mock_sleep, mock_get_client, flow_logs_response):
        """Test CloudWatch query timeout."""
        mock_ec2 = MagicMock()
        mock_logs = MagicMock()
        mock_get_client.side_effect = [mock_ec2, mock_logs]

        mock_ec2.describe_flow_logs.return_value = flow_logs_response
        mock_logs.start_query.return_value = {'queryId': 'query-123'}
        mock_logs.get_query_results.return_value = {'status': 'Timeout'}

        with pytest.raises(ToolError, match='There was an error with the query'):
            await get_tgw_flow_logs('tgw-12345678')
