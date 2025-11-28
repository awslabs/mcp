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

"""Test cases for the get_vpc_flow_logs tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
vpc_flow_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.vpc.get_vpc_flow_logs'
)


class TestGetVpcFlowLogs:
    """Test cases for get_vpc_flow_logs function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def mock_logs_client(self):
        """Mock CloudWatch Logs client fixture."""
        return MagicMock()

    @pytest.fixture
    def flow_logs_response(self):
        """Sample flow logs response."""
        return {
            'FlowLogs': [
                {'LogDestinationType': 'cloud-watch-logs', 'LogGroupName': 'vpc-flow-logs'}
            ]
        }

    @pytest.fixture
    def query_results_response(self):
        """Sample query results response."""
        return {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2024-01-15T10:30:00.000Z'},
                    {
                        'field': '@message',
                        'value': '2 123456789 eni-12345 10.0.1.5 10.0.2.10 443 80 6 10 1024 1642248600 1642248660 ACCEPT OK',
                    },
                ]
            ],
        }

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_basic_flow_logs_retrieval(
        self,
        mock_get_client,
        mock_ec2_client,
        mock_logs_client,
        flow_logs_response,
        query_results_response,
    ):
        """Test basic VPC flow logs retrieval."""
        mock_get_client.side_effect = [mock_ec2_client, mock_logs_client]
        mock_ec2_client.describe_flow_logs.return_value = flow_logs_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        result = await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345', region='us-east-1')

        assert len(result) == 1
        assert result[0]['version'] == '2'
        assert result[0]['interface_id'] == 'eni-12345'
        assert result[0]['srcaddr'] == '10.0.1.5'
        assert result[0]['action'] == 'ACCEPT'

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_no_flow_logs_configured(self, mock_get_client, mock_ec2_client):
        """Test error when no flow logs are configured."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_flow_logs.return_value = {'FlowLogs': None}

        with pytest.raises(ToolError, match='There are no flow logs for the VPC'):
            await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345', region='us-east-1')

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_flow_logs_not_in_cloudwatch(self, mock_get_client, mock_ec2_client):
        """Test error when flow logs are not stored in CloudWatch."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_flow_logs.return_value = {
            'FlowLogs': [{'LogDestinationType': 's3'}]
        }

        with pytest.raises(ToolError, match='is not stored in CloudWatch Logs'):
            await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345', region='us-east-1')

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_all_filters(
        self,
        mock_get_client,
        mock_ec2_client,
        mock_logs_client,
        flow_logs_response,
        query_results_response,
    ):
        """Test all filter parameters."""
        mock_get_client.side_effect = [mock_ec2_client, mock_logs_client]
        mock_ec2_client.describe_flow_logs.return_value = flow_logs_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await vpc_flow_module.get_vpc_flow_logs(
            vpc_id='vpc-12345',
            region='us-east-1',
            action='ACCEPT',
            srcaddr='10.0.1.5',
            dstaddr='10.0.2.10',
            srcport=443,
            dstport=80,
            interface_id='eni-12345',
            entry_limit='50',
            time_period=30,
        )

        # Verify query string contains all filters
        call_args = mock_logs_client.start_query.call_args
        query_string = call_args[1]['queryString']
        assert "action = 'ACCEPT'" in query_string
        assert "srcaddr = '10.0.1.5'" in query_string
        assert "dstaddr = '10.0.2.10'" in query_string
        assert 'srcport = 443' in query_string
        assert "dstport = '80'" in query_string
        assert "interface_id = 'eni-12345'" in query_string

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_custom_time_range(
        self,
        mock_get_client,
        mock_ec2_client,
        mock_logs_client,
        flow_logs_response,
        query_results_response,
    ):
        """Test custom time range with start_time."""
        mock_get_client.side_effect = [mock_ec2_client, mock_logs_client]
        mock_ec2_client.describe_flow_logs.return_value = flow_logs_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await vpc_flow_module.get_vpc_flow_logs(
            vpc_id='vpc-12345',
            region='us-east-1',
            start_time='2024-01-15T10:00:00Z',
            time_period=30,
        )

        call_args = mock_logs_client.start_query.call_args
        # Verify time range is calculated correctly
        assert call_args[1]['startTime'] is not None
        assert call_args[1]['endTime'] is not None

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_query_timeout(
        self, mock_get_client, mock_ec2_client, mock_logs_client, flow_logs_response
    ):
        """Test query timeout handling."""
        mock_get_client.side_effect = [mock_ec2_client, mock_logs_client]
        mock_ec2_client.describe_flow_logs.return_value = flow_logs_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = {'status': 'Timeout'}

        with pytest.raises(ToolError, match='There was an error with the query'):
            await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345', region='us-east-1')

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_no_results_found(
        self, mock_get_client, mock_ec2_client, mock_logs_client, flow_logs_response
    ):
        """Test when no flow log results are found."""
        mock_get_client.side_effect = [mock_ec2_client, mock_logs_client]
        mock_ec2_client.describe_flow_logs.return_value = flow_logs_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = {'status': 'Complete', 'results': []}

        with pytest.raises(ToolError, match='No flow logs found'):
            await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345', region='us-east-1')

    @patch.object(vpc_flow_module, 'get_aws_client')
    @patch('time.sleep')  # Patch time.sleep directly at source
    async def test_query_running_then_complete(
        self,
        mock_sleep,
        mock_get_client,
        mock_ec2_client,
        mock_logs_client,
        flow_logs_response,
        query_results_response,
    ):
        """Test query that is running then completes."""
        mock_get_client.side_effect = [mock_ec2_client, mock_logs_client]
        mock_ec2_client.describe_flow_logs.return_value = flow_logs_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.side_effect = [
            {'status': 'Running'},
            query_results_response,
        ]

        result = await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345', region='us-east-1')

        assert len(result) == 1
        mock_sleep.assert_called_once_with(1)

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_aws_api_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_flow_logs.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error getting VPC flow logs'):
            await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345', region='us-east-1')

    @patch.object(vpc_flow_module, 'get_aws_client')
    async def test_default_parameters(
        self,
        mock_get_client,
        mock_ec2_client,
        mock_logs_client,
        flow_logs_response,
        query_results_response,
    ):
        """Test default parameter values."""
        mock_get_client.side_effect = [mock_ec2_client, mock_logs_client]
        mock_ec2_client.describe_flow_logs.return_value = flow_logs_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await vpc_flow_module.get_vpc_flow_logs(vpc_id='vpc-12345')

        # Verify default limit and time period
        call_args = mock_logs_client.start_query.call_args
        assert call_args[1]['limit'] == 100  # default entry_limit
        # Time period default is 60 minutes, verified by time range calculation
