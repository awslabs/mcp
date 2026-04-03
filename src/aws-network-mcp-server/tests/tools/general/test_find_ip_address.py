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

"""Test cases for the find_ip_address tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
find_ip_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.general.find_ip_address'
)


class TestFindIpAddress:
    """Test cases for find_ip_address function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        client = MagicMock()
        return client

    @pytest.fixture
    def sample_eni_response(self):
        """Sample ENI response fixture."""
        return {
            'NetworkInterfaceId': 'eni-12345678',
            'VpcId': 'vpc-12345678',
            'SubnetId': 'subnet-12345678',
            'PrivateIpAddress': '10.0.1.100',
            'Groups': [{'GroupId': 'sg-12345678', 'GroupName': 'test-sg'}],
            'Attachment': {'InstanceId': 'i-12345678', 'DeviceIndex': 0},
        }

    @patch.object(find_ip_module, 'get_aws_client')
    async def test_find_private_ip_single_region_success(
        self, mock_get_client, mock_ec2_client, sample_eni_response
    ):
        """Test successful private IP lookup in single region."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.return_value = {
            'NetworkInterfaces': [sample_eni_response]
        }

        result = await find_ip_module.find_ip_address(
            ip_address='10.0.1.100', region='us-east-1', all_regions=False
        )

        assert result == sample_eni_response
        mock_get_client.assert_called_once_with('ec2', 'us-east-1', None)
        mock_ec2_client.describe_network_interfaces.assert_called_once_with(
            Filters=[{'Name': 'private-ip-address', 'Values': ['10.0.1.100']}]
        )

    @patch.object(find_ip_module, 'get_aws_client')
    async def test_find_public_ip_single_region_success(
        self, mock_get_client, mock_ec2_client, sample_eni_response
    ):
        """Test successful public IP lookup in single region."""
        mock_get_client.return_value = mock_ec2_client
        # First call for private IP returns empty, second call for public IP returns result
        mock_ec2_client.describe_network_interfaces.side_effect = [
            {'NetworkInterfaces': []},  # No private IP match
            {'NetworkInterfaces': [sample_eni_response]},  # Public IP match
        ]

        result = await find_ip_module.find_ip_address(
            ip_address='54.123.45.67',
            region='us-west-2',
            all_regions=False,
            profile_name='test-profile',
        )

        assert result == sample_eni_response
        mock_get_client.assert_called_once_with('ec2', 'us-west-2', 'test-profile')
        assert mock_ec2_client.describe_network_interfaces.call_count == 2

    @patch.object(find_ip_module, 'get_aws_client')
    async def test_find_ip_single_region_not_found(self, mock_get_client, mock_ec2_client):
        """Test IP not found in single region."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.return_value = {'NetworkInterfaces': []}

        with pytest.raises(ToolError) as exc_info:
            await find_ip_module.find_ip_address(
                ip_address='10.0.1.200', region='us-east-1', all_regions=False
            )

        assert 'IP address 10.0.1.200 not found in region us-east-1' in str(exc_info.value)
        assert 'VALIDATE PARAMETERS BEFORE CONTINUING' in str(exc_info.value)

    @patch.object(find_ip_module, 'get_aws_client')
    async def test_find_ip_all_regions_success(self, mock_get_client, sample_eni_response):
        """Test successful IP lookup across all regions."""
        mock_clients = {}

        def client_side_effect(service, region, profile):
            if region not in mock_clients:
                mock_clients[region] = MagicMock()
            return mock_clients[region]

        mock_get_client.side_effect = client_side_effect

        # First client returns regions, second client finds the IP in us-west-2
        mock_clients['us-east-1'] = MagicMock()
        mock_clients['us-east-1'].describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'},
                {'RegionName': 'us-west-2'},
                {'RegionName': 'eu-west-1'},
            ]
        }

        # us-east-1: not found, us-west-2: found
        mock_clients['us-east-1'].describe_network_interfaces.return_value = {
            'NetworkInterfaces': []
        }
        mock_clients['us-west-2'] = MagicMock()
        mock_clients['us-west-2'].describe_network_interfaces.return_value = {
            'NetworkInterfaces': [sample_eni_response]
        }

        result = await find_ip_module.find_ip_address(
            ip_address='10.0.1.100',
            region='us-east-1',  # This will be ignored for all_regions=True
            all_regions=True,
        )

        assert result == sample_eni_response

    @patch.object(find_ip_module, 'get_aws_client')
    async def test_find_ip_all_regions_not_found(self, mock_get_client):
        """Test IP not found in any region."""
        mock_clients = {}

        def client_side_effect(service, region, profile):
            if region not in mock_clients:
                mock_clients[region] = MagicMock()
            return mock_clients[region]

        mock_get_client.side_effect = client_side_effect

        mock_clients['us-east-1'] = MagicMock()
        mock_clients['us-east-1'].describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}, {'RegionName': 'us-west-2'}]
        }

        # Both regions return no results
        mock_clients['us-east-1'].describe_network_interfaces.return_value = {
            'NetworkInterfaces': []
        }
        mock_clients['us-west-2'] = MagicMock()
        mock_clients['us-west-2'].describe_network_interfaces.return_value = {
            'NetworkInterfaces': []
        }

        with pytest.raises(ToolError) as exc_info:
            await find_ip_module.find_ip_address(
                ip_address='10.0.1.200', region='us-east-1', all_regions=True
            )

        assert 'IP address was not found in any region' in str(exc_info.value)

    @patch.object(find_ip_module, 'get_aws_client')
    async def test_find_ip_single_region_aws_error(self, mock_get_client, mock_ec2_client):
        """Test handling AWS API errors in single region mode."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.side_effect = Exception(
            'AccessDenied: User not authorized'
        )

        with pytest.raises(ToolError) as exc_info:
            await find_ip_module.find_ip_address(
                ip_address='10.0.1.100', region='us-east-1', all_regions=False
            )

        assert 'Error searching IP address: AccessDenied: User not authorized' in str(
            exc_info.value
        )
        assert 'REQUIRED TO REMEDIATE BEFORE CONTINUING' in str(exc_info.value)

    @patch.object(find_ip_module, 'get_aws_client')
    async def test_find_ip_all_regions_with_error(self, mock_get_client):
        """Test handling errors while searching all regions."""
        mock_clients = {}

        def client_side_effect(service, region, profile):
            if region not in mock_clients:
                mock_clients[region] = MagicMock()
            return mock_clients[region]

        mock_get_client.side_effect = client_side_effect

        mock_clients['us-east-1'] = MagicMock()
        mock_clients['us-east-1'].describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}, {'RegionName': 'us-west-2'}]
        }

        # First region throws error, second region has no results
        mock_clients['us-east-1'].describe_network_interfaces.side_effect = Exception(
            'Network timeout'
        )
        mock_clients['us-west-2'] = MagicMock()
        mock_clients['us-west-2'].describe_network_interfaces.return_value = {
            'NetworkInterfaces': []
        }

        with pytest.raises(ToolError) as exc_info:
            await find_ip_module.find_ip_address(
                ip_address='10.0.1.100', region='us-east-1', all_regions=True
            )

        assert 'Error searching IP address in all regions: Network timeout' in str(exc_info.value)
        assert 'REQUIRED TO REMEDIATE BEFORE CONTINUING' in str(exc_info.value)
