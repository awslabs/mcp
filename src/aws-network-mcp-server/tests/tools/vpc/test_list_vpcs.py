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

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
vpc_list_module = importlib.import_module('awslabs.aws_network_mcp_server.tools.vpc.list_vpcs')


class TestListVpcs:
    """Test cases for list_vpcs function."""

    @pytest.fixture
    def sample_vpcs(self):
        """Sample VPCs fixture."""
        return [
            {
                'VpcId': 'vpc-12345678',
                'State': 'available',
                'CidrBlock': '10.0.0.0/16',
                'IsDefault': False,
                'Tags': [{'Key': 'Name', 'Value': 'test-vpc'}],
            },
            {
                'VpcId': 'vpc-87654321',
                'State': 'available',
                'CidrBlock': '172.16.0.0/16',
                'IsDefault': True,
                'Tags': [],
            },
        ]

    @patch.object(vpc_list_module, 'get_aws_client')
    async def test_list_vpcs_success(self, mock_get_client, sample_vpcs):
        """Test successful VPCs listing."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {'Vpcs': sample_vpcs}

        result = await vpc_list_module.list_vpcs(region='us-east-1')

        assert result == {'vpcs': sample_vpcs, 'region': 'us-east-1', 'total_count': 2}
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_client.describe_vpcs.assert_called_once()

    @patch.object(vpc_list_module, 'get_aws_client')
    async def test_list_vpcs_empty(self, mock_get_client):
        """Test listing when no VPCs exist."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {'Vpcs': []}

        result = await vpc_list_module.list_vpcs(region='us-west-2')

        assert result == {'vpcs': [], 'region': 'us-west-2', 'total_count': 0}

    @patch.object(vpc_list_module, 'get_aws_client')
    async def test_list_vpcs_with_profile(self, mock_get_client, sample_vpcs):
        """Test VPCs listing with specific AWS profile."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {'Vpcs': sample_vpcs}

        await vpc_list_module.list_vpcs(region='eu-central-1', profile_name='test-profile')

        mock_get_client.assert_called_once_with('ec2', 'eu-central-1', 'test-profile')

    @patch.object(vpc_list_module, 'get_aws_client')
    async def test_list_vpcs_missing_vpcs_key(self, mock_get_client):
        """Test handling response without Vpcs key."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpcs.return_value = {}

        result = await vpc_list_module.list_vpcs(region='us-east-1')

        assert result == {'vpcs': [], 'region': 'us-east-1', 'total_count': 0}

    @patch.object(vpc_list_module, 'get_aws_client')
    async def test_list_vpcs_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.describe_vpcs.side_effect = Exception('ServiceUnavailableException')

        with pytest.raises(
            ToolError,
            match='Error listing VPCs. Error: ServiceUnavailableException. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await vpc_list_module.list_vpcs(region='us-east-1')

    @patch.object(vpc_list_module, 'get_aws_client')
    async def test_list_vpcs_client_error(self, mock_get_client):
        """Test client creation error handling."""
        mock_get_client.side_effect = Exception('Invalid credentials')

        with pytest.raises(
            ToolError,
            match='Error listing VPCs. Error: Invalid credentials. REQUIRED TO REMEDIATE BEFORE CONTINUING',
        ):
            await vpc_list_module.list_vpcs(region='us-east-1')
