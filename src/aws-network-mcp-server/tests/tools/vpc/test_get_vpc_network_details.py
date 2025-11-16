#!/usr/bin/env python3
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

"""Test cases for the get_vpc_network_details tool."""

import pytest
from unittest.mock import MagicMock, patch
from fastmcp.exceptions import ToolError
from awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details import get_vpc_network_details


class TestGetVpcNetworkDetails:
    """Test cases for get_vpc_network_details function."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Mock EC2 client fixture."""
        return MagicMock()

    @pytest.fixture
    def sample_vpc_data(self):
        """Sample VPC data fixture."""
        return {
            'VpcId': 'vpc-12345678',
            'State': 'available',
            'CidrBlock': '10.0.0.0/16',
            'CidrBlockAssociationSet': [
                {
                    'AssociationId': 'vpc-cidr-assoc-12345678',
                    'CidrBlock': '10.0.0.0/16',
                    'CidrBlockState': {'State': 'associated'}
                }
            ],
            'DhcpOptionsId': 'dopt-12345678',
            'InstanceTenancy': 'default',
            'IsDefault': False
        }

    @pytest.fixture
    def sample_subnets(self):
        """Sample subnets fixture."""
        return [
            {
                'SubnetId': 'subnet-12345678',
                'VpcId': 'vpc-12345678',
                'CidrBlock': '10.0.1.0/24',
                'AvailabilityZone': 'us-east-1a',
                'State': 'available',
                'MapPublicIpOnLaunch': True
            },
            {
                'SubnetId': 'subnet-87654321',
                'VpcId': 'vpc-12345678',
                'CidrBlock': '10.0.2.0/24',
                'AvailabilityZone': 'us-east-1b',
                'State': 'available',
                'MapPublicIpOnLaunch': False
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
                        'State': 'active'
                    },
                    {
                        'DestinationCidrBlock': '0.0.0.0/0',
                        'GatewayId': 'igw-12345678',
                        'State': 'active'
                    }
                ],
                'Associations': [
                    {
                        'RouteTableAssociationId': 'rtbassoc-12345678',
                        'RouteTableId': 'rtb-12345678',
                        'SubnetId': 'subnet-12345678',
                        'Main': False
                    }
                ]
            }
        ]

    @pytest.fixture
    def sample_igws(self):
        """Sample internet gateways fixture."""
        return [
            {
                'InternetGatewayId': 'igw-12345678',
                'State': 'available',
                'Attachments': [
                    {
                        'State': 'available',
                        'VpcId': 'vpc-12345678'
                    }
                ]
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
                        'CidrBlock': '0.0.0.0/0'
                    }
                ]
            }
        ]

    @pytest.fixture
    def sample_vpc_endpoints(self):
        """Sample VPC endpoints fixture."""
        return [
            {
                'VpcEndpointId': 'vpce-12345678',
                'VpcId': 'vpc-12345678',
                'ServiceName': 'com.amazonaws.us-east-1.s3',
                'VpcEndpointType': 'Gateway',
                'State': 'Available'
            }
        ]

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_get_vpc_network_details_success(
        self, mock_get_client, mock_ec2_client, sample_vpc_data,
        sample_subnets, sample_route_tables, sample_igws, sample_nacls, sample_vpc_endpoints
    ):
        """Test successful VPC network details retrieval."""
        mock_get_client.return_value = mock_ec2_client

        # Mock all the AWS API responses
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': [sample_vpc_data]}
        mock_ec2_client.describe_subnets.return_value = {'Subnets': sample_subnets}
        mock_ec2_client.describe_route_tables.return_value = {'RouteTables': sample_route_tables}
        mock_ec2_client.describe_internet_gateways.return_value = {'InternetGateways': sample_igws}
        mock_ec2_client.describe_network_acls.return_value = {'NetworkAcls': sample_nacls}
        mock_ec2_client.describe_vpc_endpoints.return_value = {'VpcEndpoints': sample_vpc_endpoints}

        result = await get_vpc_network_details(
            vpc_id='vpc-12345678',
            region='us-east-1'
        )

        # Verify the complete result structure
        assert 'vpc_details' in result
        assert 'subnets' in result
        assert 'route_tables' in result
        assert 'internet_gateways' in result
        assert 'network_acls' in result
        assert 'vpc_endpoints' in result

        assert result['vpc_details'] == sample_vpc_data
        assert result['subnets'] == sample_subnets
        assert result['route_tables'] == sample_route_tables
        assert result['internet_gateways'] == sample_igws
        assert result['network_acls'] == sample_nacls
        assert result['vpc_endpoints'] == sample_vpc_endpoints

        # Verify all API calls were made with correct parameters
        mock_ec2_client.describe_vpcs.assert_called_once_with(VpcIds=['vpc-12345678'])
        mock_ec2_client.describe_subnets.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': ['vpc-12345678']}]
        )
        mock_ec2_client.describe_route_tables.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': ['vpc-12345678']}]
        )
        mock_ec2_client.describe_internet_gateways.assert_called_once_with(
            Filters=[{'Name': 'attachment.vpc-id', 'Values': ['vpc-12345678']}]
        )
        mock_ec2_client.describe_network_acls.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': ['vpc-12345678']}]
        )
        mock_ec2_client.describe_vpc_endpoints.assert_called_once_with(
            Filters=[{'Name': 'vpc-id', 'Values': ['vpc-12345678']}]
        )

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_get_vpc_network_details_vpc_not_found(self, mock_get_client, mock_ec2_client):
        """Test error handling when VPC is not found."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': []}

        with pytest.raises(ToolError) as exc_info:
            await get_vpc_network_details(
                vpc_id='vpc-nonexistent',
                region='us-east-1'
            )

        assert 'VPC vpc-nonexistent not found' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_get_vpc_network_details_aws_error(self, mock_get_client, mock_ec2_client):
        """Test AWS API error handling."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.side_effect = Exception('InvalidVpc.NotFound')

        with pytest.raises(ToolError) as exc_info:
            await get_vpc_network_details(
                vpc_id='vpc-invalid',
                region='us-east-1'
            )

        assert 'Error getting VPC network details: InvalidVpc.NotFound' in str(exc_info.value)

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_get_vpc_network_details_with_profile(
        self, mock_get_client, mock_ec2_client, sample_vpc_data
    ):
        """Test VPC details retrieval with specific AWS profile."""
        mock_get_client.return_value = mock_ec2_client
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': [sample_vpc_data]}
        mock_ec2_client.describe_subnets.return_value = {'Subnets': []}
        mock_ec2_client.describe_route_tables.return_value = {'RouteTables': []}
        mock_ec2_client.describe_internet_gateways.return_value = {'InternetGateways': []}
        mock_ec2_client.describe_network_acls.return_value = {'NetworkAcls': []}
        mock_ec2_client.describe_vpc_endpoints.return_value = {'VpcEndpoints': []}

        await get_vpc_network_details(
            vpc_id='vpc-12345678',
            region='eu-central-1',
            profile_name='test-profile'
        )

        mock_get_client.assert_called_with('ec2', 'eu-central-1', 'test-profile')

    @patch('awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details.get_aws_client')
    async def test_get_vpc_network_details_partial_failure(
        self, mock_get_client, mock_ec2_client, sample_vpc_data
    ):
        """Test handling when some API calls fail but VPC details succeed."""
        mock_get_client.return_value = mock_ec2_client

        # VPC details succeed, but subnets call fails
        mock_ec2_client.describe_vpcs.return_value = {'Vpcs': [sample_vpc_data]}
        mock_ec2_client.describe_subnets.side_effect = Exception('InternalError')

        with pytest.raises(ToolError) as exc_info:
            await get_vpc_network_details(
                vpc_id='vpc-12345678',
                region='us-east-1'
            )

        assert 'Error getting VPC network details: InternalError' in str(exc_info.value)

    async def test_parameter_validation(self):
        """Test parameter validation for required fields."""
        with pytest.raises(TypeError):
            await get_vpc_network_details()  # Missing required parameters

        with pytest.raises(TypeError):
            await get_vpc_network_details(vpc_id='vpc-test')  # Missing region