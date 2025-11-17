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

import pytest
from awslabs.aws_network_mcp_server.tools.vpc.get_vpc_flow_logs import get_vpc_flow_logs
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestGetVpcFlowLogs:
    """Test cases for get_vpc_flow_logs function."""

    @pytest.fixture
    def mock_logs_client(self):
        """Mock CloudWatch Logs client fixture."""
        return MagicMock()

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_flow_logs.get_aws_client')
    async def test_get_vpc_flow_logs_basic(self, mock_get_client, mock_logs_client):
        """Test basic VPC flow logs retrieval."""
        mock_get_client.return_value = mock_logs_client

        # Mock successful response
        mock_logs_client.describe_log_groups.return_value = {
            'logGroups': [{'logGroupName': 'vpc-flow-logs-group'}]
        }

        result = await get_vpc_flow_logs(vpc_id='vpc-12345678', region='us-east-1')

        # Basic structure check - actual implementation may vary
        assert isinstance(result, dict)
        mock_get_client.assert_called_with('logs', 'us-east-1', None)

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_flow_logs.get_aws_client')
    async def test_get_vpc_flow_logs_aws_error(self, mock_get_client, mock_logs_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_logs_client
        mock_logs_client.describe_log_groups.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError):
            await get_vpc_flow_logs(vpc_id='vpc-12345678', region='us-east-1')
