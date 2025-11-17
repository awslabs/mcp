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

"""Test cases for the list_vpcs tool."""

import pytest
from awslabs.aws_network_mcp_server.tools.vpc.list_vpcs import list_vpcs
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


class TestListVpcs:
    """Test cases for list_vpcs function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_vpcs(self):
        """Sample VPCs fixture."""
        return [
            {
                'VpcId': 'vpc-12345678',
                'State': 'available',
                'CidrBlock': '10.0.0.0/16',
                'DhcpOptionsId': 'dopt-12345678',
                'InstanceTenancy': 'default',
                'IsDefault': False,
            },
            {
                'VpcId': 'vpc-87654321',
                'State': 'available',
                'CidrBlock': '172.16.0.0/16',
                'DhcpOptionsId': 'dopt-87654321',
                'InstanceTenancy': 'default',
                'IsDefault': True,
            },
        ]

    @patch('awslabs.aws_network_mcp_server.tools.vpc.list_vpcs.get_aws_client')
    async def test_list_vpcs_success(self, mock_get_client, mock_ec2_client, sample_vpcs):
        """Test successful VPCs listing."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': sample_vpcs}

        result = await list_vpcs(region='us-east-1')

        assert 'vpcs' in result
        assert result['vpcs'] == sample_vpcs
        assert 'total_count' in result
        assert result['total_count'] == 2

        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_ec2_client.describe_vpcs.assert_called_once()

    @patch('awslabs.aws_network_mcp_server.tools.vpc.list_vpcs.get_aws_client')
    async def test_list_vpcs_empty(self, mock_get_client, mock_ec2_client):
        """Test listing when no VPCs exist."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}

        result = await list_vpcs(region='us-west-2')

        assert result['vpcs'] == []
        assert result['total_count'] == 0

    @patch('awslabs.aws_network_mcp_server.tools.vpc.list_vpcs.get_aws_client')
    async def test_list_vpcs_with_profile(self, mock_get_client, mock_ec2_client, sample_vpcs):
        """Test VPCs listing with specific AWS profile."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': sample_vpcs}

        await list_vpcs(region='eu-central-1', profile_name='test-profile')

        mock_get_client.assert_called_once_with('ec2', 'eu-central-1', 'test-profile')

    @patch('awslabs.aws_network_mcp_server.tools.vpc.list_vpcs.get_aws_client')
    async def test_list_vpcs_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.side_effect = Exception('ServiceUnavailableException')

        with pytest.raises(ToolError) as exc_info:
            await list_vpcs(region='us-east-1')

        assert 'Error listing VPCs. Error: ServiceUnavailableException' in str(exc_info.value)

    async def test_parameter_validation(self):
        """Test parameter validation for required fields."""
        with pytest.raises(TypeError):
            await list_vpcs()  # Missing required region parameter
