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

"""Test cases for the get_eni_details tool."""

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
eni_details_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.general.get_eni_details'
)


class TestGetEniDetails:
    """Test cases for get_eni_details function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_eni_data(self):
        """Sample ENI data fixture."""
        return {
            'NetworkInterfaceId': 'eni-12345678',
            'VpcId': 'vpc-12345678',
            'SubnetId': 'subnet-12345678',
            'PrivateIpAddress': '10.0.1.100',
            'InterfaceType': 'interface',
            'Status': 'in-use',
            'AvailabilityZone': 'us-east-1a',
            'Groups': [{'GroupId': 'sg-12345678', 'GroupName': 'test-sg'}],
            'Association': {'PublicIp': '54.123.45.67'},
        }

    @pytest.fixture
    def sample_security_groups(self):
        """Sample security groups fixture."""
        return [
            {
                'GroupId': 'sg-12345678',
                'GroupName': 'test-sg',
                'IpPermissions': [
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 80,
                        'ToPort': 80,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                    }
                ],
                'IpPermissionsEgress': [
                    {'IpProtocol': '-1', 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ],
            }
        ]

    @pytest.fixture
    def sample_nacls(self):
        """Sample Network ACLs fixture."""
        return [
            {
                'NetworkAclId': 'acl-12345678',
                'VpcId': 'vpc-12345678',
                'IsDefault': True,
                'Entries': [
                    {
                        'RuleNumber': 100,
                        'Protocol': '6',
                        'RuleAction': 'allow',
                        'CidrBlock': '0.0.0.0/0',
                        'PortRange': {'From': 80, 'To': 80},
                        'Egress': False,
                    },
                    {
                        'RuleNumber': 100,
                        'Protocol': '6',
                        'RuleAction': 'allow',
                        'CidrBlock': '0.0.0.0/0',
                        'PortRange': {'From': 80, 'To': 80},
                        'Egress': True,
                    },
                ],
            }
        ]

    @pytest.fixture
    def sample_route_tables(self):
        """Sample route tables fixture."""
        return [
            {
                'RouteTableId': 'rtb-12345678',
                'VpcId': 'vpc-12345678',
                'Routes': [
                    {
                        'DestinationCidrBlock': '10.0.0.0/16',
                        'GatewayId': 'local',
                        'State': 'active',
                    },
                    {
                        'DestinationCidrBlock': '0.0.0.0/0',
                        'GatewayId': 'igw-12345678',
                        'State': 'active',
                    },
                ],
                'Associations': [
                    {
                        'RouteTableAssociationId': 'rtbassoc-12345678',
                        'RouteTableId': 'rtb-12345678',
                        'SubnetId': 'subnet-12345678',
                        'Main': False,
                    }
                ],
            }
        ]

    @patch.object(eni_details_module, 'get_aws_client')
    async def test_get_eni_details_success(
        self,
        mock_get_client,
        mock_ec2_client,
        sample_eni_data,
        sample_security_groups,
        sample_nacls,
        sample_route_tables,
    ):
        """Test successful ENI details retrieval."""
        mock_get_client.return_value = mock_ec2_client

        # Mock all the AWS API responses
        mock_ec2_client.describe_network_interfaces.return_value = {
            'NetworkInterfaces': [sample_eni_data]
        }
        mock_ec2_client.describe_security_groups.return_value = {
            'SecurityGroups': sample_security_groups
        }
        mock_ec2_client.describe_network_acls.return_value = {'NetworkAcls': sample_nacls}
        mock_ec2_client.describe_route_tables.return_value = {'RouteTables': sample_route_tables}

        result = await eni_details_module.get_eni_details(
            eni_id='eni-12345678', region='us-east-1'
        )

        # Verify the result structure
        assert 'basic_info' in result
        assert 'security_groups' in result
        assert 'network_acls' in result
        assert 'route_tables' in result

        # Check basic_info structure
        basic_info = result['basic_info']
        assert basic_info['id'] == 'eni-12345678'
        assert basic_info['subnet_id'] == 'subnet-12345678'
        assert basic_info['vpc_id'] == 'vpc-12345678'
        assert basic_info['private_ip'] == '10.0.1.100'
        assert basic_info['public_ip'] == '54.123.45.67'

        # Verify API calls were made
        mock_ec2_client.describe_network_interfaces.assert_called_once_with(
            NetworkInterfaceIds=['eni-12345678']
        )
        mock_ec2_client.describe_security_groups.assert_called_once_with(GroupIds=['sg-12345678'])

    @patch.object(eni_details_module, 'get_aws_client')
    async def test_get_eni_details_not_found(self, mock_get_client, mock_ec2_client):
        """Test ENI not found error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.return_value = {'NetworkInterfaces': []}

        with pytest.raises(ToolError) as exc_info:
            await eni_details_module.get_eni_details(eni_id='eni-nonexistent', region='us-east-1')

        assert 'There was an error getting AWS ENI details' in str(exc_info.value)

    @patch.object(eni_details_module, 'get_aws_client')
    async def test_get_eni_details_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.side_effect = Exception(
            'InvalidNetworkInterfaceID.NotFound'
        )

        with pytest.raises(ToolError) as exc_info:
            await eni_details_module.get_eni_details(eni_id='eni-invalid', region='us-east-1')

        assert 'There was an error getting AWS ENI details' in str(exc_info.value)

    @patch.object(eni_details_module, 'get_aws_client')
    async def test_get_eni_details_with_profile(
        self, mock_get_client, mock_ec2_client, sample_eni_data
    ):
        """Test ENI details retrieval with specific profile."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.return_value = {
            'NetworkInterfaces': [sample_eni_data]
        }
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        mock_ec2_client.describe_network_acls.return_value = {'NetworkAcls': []}
        mock_ec2_client.describe_route_tables.return_value = {'RouteTables': []}

        await eni_details_module.get_eni_details(
            eni_id='eni-12345678', region='us-west-2', profile_name='test-profile'
        )

        mock_get_client.assert_called_with('ec2', 'us-west-2', 'test-profile')

    @patch.object(eni_details_module, 'get_aws_client')
    async def test_get_eni_details_no_route_table_association(
        self, mock_get_client, mock_ec2_client, sample_eni_data
    ):
        """Test ENI with no explicit route table association uses main route table."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_network_interfaces.return_value = {
            'NetworkInterfaces': [sample_eni_data]
        }
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        mock_ec2_client.describe_network_acls.return_value = {'NetworkAcls': []}

        # First call returns empty (no explicit association)
        # Second call returns main route table
        mock_ec2_client.describe_route_tables.side_effect = [
            {'RouteTables': []},
            {'RouteTables': [{'RouteTableId': 'rtb-main', 'Routes': [], 'Associations': []}]},
        ]

        result = await eni_details_module.get_eni_details(
            eni_id='eni-12345678', region='us-east-1'
        )

        # Verify main route table lookup was called
        assert mock_ec2_client.describe_route_tables.call_count == 2
        assert len(result['route_tables']) == 1
        assert result['route_tables'][0]['route_table_id'] == 'rtb-main'

    @patch.object(eni_details_module, 'get_aws_client')
    async def test_get_eni_details_no_public_ip(
        self, mock_get_client, mock_ec2_client, sample_eni_data
    ):
        """Test ENI without public IP association."""
        mock_get_client.return_value = mock_ec2_client

        # Remove Association key to simulate no public IP
        eni_data = sample_eni_data.copy()
        del eni_data['Association']

        mock_ec2_client.describe_network_interfaces.return_value = {
            'NetworkInterfaces': [eni_data]
        }
        mock_ec2_client.describe_security_groups.return_value = {'SecurityGroups': []}
        mock_ec2_client.describe_network_acls.return_value = {'NetworkAcls': []}
        mock_ec2_client.describe_route_tables.return_value = {'RouteTables': []}

        result = await eni_details_module.get_eni_details(
            eni_id='eni-12345678', region='us-east-1'
        )

        assert result['basic_info']['public_ip'] is None

    @patch.object(eni_details_module, 'get_aws_client')
    async def test_get_eni_details_multiple_security_groups(
        self, mock_get_client, mock_ec2_client, sample_eni_data
    ):
        """Test ENI with multiple security groups."""
        mock_get_client.return_value = mock_ec2_client

        # Add multiple security groups
        eni_data = sample_eni_data.copy()
        eni_data['Groups'] = [
            {'GroupId': 'sg-12345678', 'GroupName': 'test-sg1'},
            {'GroupId': 'sg-87654321', 'GroupName': 'test-sg2'},
        ]

        mock_ec2_client.describe_network_interfaces.return_value = {
            'NetworkInterfaces': [eni_data]
        }
        mock_ec2_client.describe_security_groups.return_value = {
            'SecurityGroups': [
                {'GroupId': 'sg-12345678', 'IpPermissions': [], 'IpPermissionsEgress': []},
                {'GroupId': 'sg-87654321', 'IpPermissions': [], 'IpPermissionsEgress': []},
            ]
        }
        mock_ec2_client.describe_network_acls.return_value = {'NetworkAcls': []}
        mock_ec2_client.describe_route_tables.return_value = {'RouteTables': []}

        result = await eni_details_module.get_eni_details(
            eni_id='eni-12345678', region='us-east-1'
        )

        # Verify both security groups are called
        mock_ec2_client.describe_security_groups.assert_called_once_with(
            GroupIds=['sg-12345678', 'sg-87654321']
        )
        assert len(result['security_groups']) == 2
