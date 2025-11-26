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

"""Test cases for the get_network_firewall_flow_logs tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
nfw_flow_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.network_firewall.get_network_firewall_flow_logs'
)


class TestGetNetworkFirewallFlowLogs:
    """Test cases for get_network_firewall_flow_logs function."""

    @pytest.fixture
    def mock_fw_client(self):
        """Mock Network Firewall client fixture."""
        return MagicMock()

    @pytest.fixture
    def mock_logs_client(self):
        """Mock CloudWatch Logs client fixture."""
        return MagicMock()

    @pytest.fixture
    def logging_config_response(self):
        """Sample logging configuration response."""
        return {
            'LoggingConfiguration': {
                'LogDestinationConfigs': [
                    {
                        'LogType': 'FLOW',
                        'LogDestinationType': 'CloudWatchLogs',
                        'LogDestination': {'logGroup': 'firewall-flow-logs'},
                    }
                ]
            }
        }

    @pytest.fixture
    def query_results_response(self):
        """Sample query results response."""
        return {
            'status': 'Complete',
            'results': [
                [
                    {'field': '@timestamp', 'value': '2024-01-15T10:30:00.000Z'},
                    {'field': '@message', 'value': 'flow log entry 1'},
                ]
            ],
        }

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_basic_flow_logs_retrieval(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
        query_results_response,
    ):
        """Test basic network firewall flow logs retrieval."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        result = await nfw_flow_module.get_firewall_flow_logs(
            firewall_name='test-firewall', region='us-east-1'
        )

        assert len(result) == 1
        assert result[0] == 'flow log entry 1'
        mock_fw_client.describe_logging_configuration.assert_called_once()

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_no_flow_logging_configured(
        self, mock_get_client, mock_get_account_id, mock_fw_client
    ):
        """Test error when no flow logging is configured."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.return_value = mock_fw_client
        mock_fw_client.describe_logging_configuration.return_value = {
            'LoggingConfiguration': {'LogDestinationConfigs': []}
        }

        with pytest.raises(
            ToolError,
            match='flow log for the AWS Network Firewall.*are not stored in CloudWatch Logs',
        ):
            await nfw_flow_module.get_firewall_flow_logs(
                firewall_name='test-firewall', region='us-east-1'
            )

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_flow_logs_not_in_cloudwatch(
        self, mock_get_client, mock_get_account_id, mock_fw_client
    ):
        """Test error when flow logs are not stored in CloudWatch."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.return_value = mock_fw_client
        mock_fw_client.describe_logging_configuration.return_value = {
            'LoggingConfiguration': {
                'LogDestinationConfigs': [
                    {
                        'LogType': 'FLOW',
                        'LogDestinationType': 'S3',
                        'LogDestination': {'bucketName': 'firewall-logs'},
                    }
                ]
            }
        }

        with pytest.raises(
            ToolError,
            match='flow log for the AWS Network Firewall.*are not stored in CloudWatch Logs',
        ):
            await nfw_flow_module.get_firewall_flow_logs(
                firewall_name='test-firewall', region='us-east-1'
            )

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_all_filters(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
        query_results_response,
    ):
        """Test all filter parameters."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await nfw_flow_module.get_firewall_flow_logs(
            firewall_name='test-firewall',
            region='us-east-1',
            srcaddr='10.0.1.5',
            dstaddr='10.0.2.10',
            srcport=443,
            dstport=80,
            entry_limit='50',
            time_period=30,
        )

        # Verify query string contains all filters
        call_args = mock_logs_client.start_query.call_args
        query_string = call_args[1]['queryString']
        assert "srcaddr = '10.0.1.5'" in query_string
        assert "dstaddr = '10.0.2.10'" in query_string
        assert 'srcport = 443' in query_string
        assert 'dstport = 80' in query_string

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_custom_time_range(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
        query_results_response,
    ):
        """Test custom time range with start_time."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await nfw_flow_module.get_firewall_flow_logs(
            firewall_name='test-firewall',
            region='us-east-1',
            start_time='2024-01-15T10:00:00Z',
            time_period=30,
        )

        call_args = mock_logs_client.start_query.call_args
        # Verify time range is calculated correctly
        assert call_args[1]['startTime'] is not None
        assert call_args[1]['endTime'] is not None

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_query_timeout(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
    ):
        """Test query timeout handling."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = {'status': 'Timeout'}

        with pytest.raises(ToolError, match='There was an error with the query'):
            await nfw_flow_module.get_firewall_flow_logs(
                firewall_name='test-firewall', region='us-east-1'
            )

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_query_failed(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
    ):
        """Test query failed handling."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = {'status': 'Failed'}

        with pytest.raises(ToolError, match='There was an error with the query'):
            await nfw_flow_module.get_firewall_flow_logs(
                firewall_name='test-firewall', region='us-east-1'
            )

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_no_results_found(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
    ):
        """Test when no flow log results are found."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = {'status': 'Complete', 'results': []}

        with pytest.raises(ToolError, match='No flow logs found'):
            await nfw_flow_module.get_firewall_flow_logs(
                firewall_name='test-firewall', region='us-east-1'
            )

    @patch('time.sleep')  # Patch time.sleep directly at source
    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_query_running_then_complete(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_sleep,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
        query_results_response,
    ):
        """Test query that is running then completes."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.side_effect = [
            {'status': 'Running'},
            query_results_response,
        ]

        result = await nfw_flow_module.get_firewall_flow_logs(
            firewall_name='test-firewall', region='us-east-1'
        )

        assert len(result) == 1
        mock_sleep.assert_called_once_with(1)

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_aws_api_error(self, mock_get_client, mock_get_account_id, mock_fw_client):
        """Test AWS API error handling."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.return_value = mock_fw_client
        mock_fw_client.describe_logging_configuration.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error getting AWS Network Firewall flow logs'):
            await nfw_flow_module.get_firewall_flow_logs(
                firewall_name='test-firewall', region='us-east-1'
            )

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_default_parameters(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
        query_results_response,
    ):
        """Test default parameter values."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await nfw_flow_module.get_firewall_flow_logs(firewall_name='test-firewall')

        # Verify default limit and time period
        call_args = mock_logs_client.start_query.call_args
        assert call_args[1]['limit'] == 100  # default entry_limit
        # Default region should be us-east-1 when not specified

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_multiple_log_destinations(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        query_results_response,
    ):
        """Test handling multiple log destinations with correct FLOW type selection."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = {
            'LoggingConfiguration': {
                'LogDestinationConfigs': [
                    {
                        'LogType': 'ALERT',
                        'LogDestinationType': 'CloudWatchLogs',
                        'LogDestination': {'logGroup': 'firewall-alert-logs'},
                    },
                    {
                        'LogType': 'FLOW',
                        'LogDestinationType': 'CloudWatchLogs',
                        'LogDestination': {'logGroup': 'firewall-flow-logs'},
                    },
                ]
            }
        }
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await nfw_flow_module.get_firewall_flow_logs(
            firewall_name='test-firewall', region='us-east-1'
        )

        # Verify correct log group is used
        call_args = mock_logs_client.start_query.call_args
        assert call_args[1]['logGroupName'] == 'firewall-flow-logs'

    @patch.object(nfw_flow_module, 'get_account_id')
    @patch.object(nfw_flow_module, 'get_aws_client')
    async def test_ipv6_addresses(
        self,
        mock_get_client,
        mock_get_account_id,
        mock_fw_client,
        mock_logs_client,
        logging_config_response,
        query_results_response,
    ):
        """Test IPv6 address filtering."""
        mock_get_account_id.return_value = '123456789012'
        mock_get_client.side_effect = [mock_fw_client, mock_logs_client]
        mock_fw_client.describe_logging_configuration.return_value = logging_config_response
        mock_logs_client.start_query.return_value = {'queryId': 'query-123'}
        mock_logs_client.get_query_results.return_value = query_results_response

        await nfw_flow_module.get_firewall_flow_logs(
            firewall_name='test-firewall',
            region='us-east-1',
            srcaddr='2001:db8::1',
            dstaddr='2001:db8::2',
        )

        # Verify IPv6 addresses are properly included in query
        call_args = mock_logs_client.start_query.call_args
        query_string = call_args[1]['queryString']
        assert "srcaddr = '2001:db8::1'" in query_string
        assert "dstaddr = '2001:db8::2'" in query_string
