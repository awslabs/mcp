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

import importlib
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import Mock, patch


# Get the actual module - prevents function/module resolution issues
vpc_details_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.vpc.get_vpc_network_details'
)


@pytest.fixture
def mock_ec2_responses():
    """Mock EC2 API responses."""
    return {
        'describe_vpcs': {
            'Vpcs': [{'VpcId': 'vpc-12345678', 'CidrBlock': '10.0.0.0/16', 'State': 'available'}]
        },
        'describe_route_tables': {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-12345678',
                    'Associations': [{'Main': True}],
                    'Routes': [
                        {
                            'DestinationCidrBlock': '0.0.0.0/0',
                            'GatewayId': 'igw-12345678',
                            'State': 'active',
                            'Origin': 'CreateRoute',
                        }
                    ],
                }
            ]
        },
        'describe_subnets': {
            'Subnets': [
                {
                    'SubnetId': 'subnet-12345678',
                    'CidrBlock': '10.0.1.0/24',
                    'AvailabilityZone': 'us-east-1a',
                }
            ]
        },
        'describe_vpc_endpoints': {'VpcEndpoints': []},
        'describe_internet_gateways': {
            'InternetGateways': [
                {'InternetGatewayId': 'igw-12345678', 'Attachments': [{'State': 'available'}]}
            ]
        },
        'describe_network_acls': {
            'NetworkAcls': [
                {
                    'NetworkAclId': 'acl-12345678',
                    'Associations': [],
                    'Entries': [
                        {
                            'RuleNumber': 100,
                            'Protocol': '6',
                            'RuleAction': 'allow',
                            'CidrBlock': '0.0.0.0/0',
                        }
                    ],
                }
            ]
        },
        'describe_nat_gateways': {'NatGateways': []},
    }


@patch.object(vpc_details_module, 'get_aws_client')
@pytest.mark.asyncio
async def test_get_vpc_network_details_success(
    mock_get_client, mock_aws_credentials, mock_ec2_responses
):
    """Test successful VPC network details retrieval."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    mock_client.describe_vpcs.return_value = mock_ec2_responses['describe_vpcs']
    mock_client.describe_route_tables.return_value = mock_ec2_responses['describe_route_tables']
    mock_client.describe_subnets.return_value = mock_ec2_responses['describe_subnets']
    mock_client.describe_vpc_endpoints.return_value = mock_ec2_responses['describe_vpc_endpoints']
    mock_client.describe_internet_gateways.return_value = mock_ec2_responses[
        'describe_internet_gateways'
    ]
    mock_client.describe_network_acls.return_value = mock_ec2_responses['describe_network_acls']
    mock_client.describe_nat_gateways.return_value = mock_ec2_responses['describe_nat_gateways']

    result = await vpc_details_module.get_vpc_network(vpc_id='vpc-12345678', region='us-east-1')

    assert result['vpc']['id'] == 'vpc-12345678'
    assert result['vpc']['cidr'] == '10.0.0.0/16'
    assert result['vpc']['region'] == 'us-east-1'
    assert len(result['route_tables']) == 1
    assert len(result['subnets']) == 1
    assert result['internet_gateway'].id == 'igw-12345678'


@patch.object(vpc_details_module, 'get_aws_client')
@pytest.mark.asyncio
async def test_get_vpc_network_details_vpc_not_found(mock_get_client, mock_aws_credentials):
    """Test VPC not found error."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    mock_client.describe_vpcs.side_effect = Exception('VPC not found')

    with pytest.raises(ToolError, match='VPC with id vpc-invalid could not be found'):
        await vpc_details_module.get_vpc_network(vpc_id='vpc-invalid', region='us-east-1')


@patch.object(vpc_details_module, 'get_aws_client')
@pytest.mark.asyncio
async def test_get_vpc_network_details_api_failure(
    mock_get_client, mock_aws_credentials, mock_ec2_responses
):
    """Test API failure during resource retrieval."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    mock_client.describe_vpcs.return_value = mock_ec2_responses['describe_vpcs']
    mock_client.describe_route_tables.side_effect = Exception('API Error')

    with pytest.raises(ToolError, match='Failure reading VPC details'):
        await vpc_details_module.get_vpc_network(vpc_id='vpc-12345678', region='us-east-1')


@patch.object(vpc_details_module, 'get_aws_client')
@pytest.mark.asyncio
async def test_get_vpc_network_details_with_profile(
    mock_get_client, mock_aws_credentials, mock_ec2_responses
):
    """Test VPC details retrieval with custom profile."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    mock_client.describe_vpcs.return_value = mock_ec2_responses['describe_vpcs']
    mock_client.describe_route_tables.return_value = mock_ec2_responses['describe_route_tables']
    mock_client.describe_subnets.return_value = mock_ec2_responses['describe_subnets']
    mock_client.describe_vpc_endpoints.return_value = mock_ec2_responses['describe_vpc_endpoints']
    mock_client.describe_internet_gateways.return_value = mock_ec2_responses[
        'describe_internet_gateways'
    ]
    mock_client.describe_network_acls.return_value = mock_ec2_responses['describe_network_acls']
    mock_client.describe_nat_gateways.return_value = mock_ec2_responses['describe_nat_gateways']

    await vpc_details_module.get_vpc_network(
        vpc_id='vpc-12345678', region='us-west-2', profile_name='test-profile'
    )


@patch.object(vpc_details_module, 'get_aws_client')
@pytest.mark.asyncio
async def test_get_vpc_network_details_default_region(
    mock_get_client, mock_aws_credentials, mock_ec2_responses
):
    """Test default region handling."""
    mock_client = Mock()
    mock_get_client.return_value = mock_client
    mock_client.describe_vpcs.return_value = mock_ec2_responses['describe_vpcs']
    mock_client.describe_route_tables.return_value = mock_ec2_responses['describe_route_tables']
    mock_client.describe_subnets.return_value = mock_ec2_responses['describe_subnets']
    mock_client.describe_vpc_endpoints.return_value = mock_ec2_responses['describe_vpc_endpoints']
    mock_client.describe_internet_gateways.return_value = mock_ec2_responses[
        'describe_internet_gateways'
    ]
    mock_client.describe_network_acls.return_value = mock_ec2_responses['describe_network_acls']
    mock_client.describe_nat_gateways.return_value = mock_ec2_responses['describe_nat_gateways']

    result = await vpc_details_module.get_vpc_network(vpc_id='vpc-12345678')

    assert result['vpc']['region'] == 'us-east-1'


@patch.object(vpc_details_module, 'get_aws_client')
@pytest.mark.asyncio
async def test_get_vpc_network_details_complex_resources(mock_get_client, mock_aws_credentials):
    """Test with complex resource configurations."""
    complex_responses = {
        'describe_vpcs': {
            'Vpcs': [{'VpcId': 'vpc-12345678', 'CidrBlock': '10.0.0.0/16', 'State': 'available'}]
        },
        'describe_route_tables': {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-12345678',
                    'Associations': [{'SubnetId': 'subnet-12345678'}],
                    'Routes': [
                        {
                            'DestinationCidrBlock': '0.0.0.0/0',
                            'NatGatewayId': 'nat-12345678',
                            'State': 'active',
                            'Origin': 'CreateRoute',
                        }
                    ],
                }
            ]
        },
        'describe_subnets': {
            'Subnets': [
                {
                    'SubnetId': 'subnet-12345678',
                    'CidrBlock': '10.0.1.0/24',
                    'AvailabilityZone': 'us-east-1a',
                }
            ]
        },
        'describe_vpc_endpoints': {
            'VpcEndpoints': [
                {
                    'VpcEndpointId': 'vpce-12345678',
                    'VpcEndpointType': 'Interface',
                    'State': 'available',
                    'ServiceName': 'com.amazonaws.us-east-1.s3',
                    'SubnetIds': ['subnet-12345678'],
                    'PolicyDocument': '{}',
                    'Tags': [],
                }
            ]
        },
        'describe_internet_gateways': {'InternetGateways': []},
        'describe_network_acls': {
            'NetworkAcls': [
                {
                    'NetworkAclId': 'acl-12345678',
                    'Associations': [{'SubnetId': 'subnet-12345678'}],
                    'Entries': [
                        {
                            'RuleNumber': 100,
                            'Protocol': '6',
                            'RuleAction': 'allow',
                            'CidrBlock': '0.0.0.0/0',
                            'PortRange': {'From': 80, 'To': 80},
                        }
                    ],
                }
            ]
        },
        'describe_nat_gateways': {
            'NatGateways': [
                {
                    'NatGatewayId': 'nat-12345678',
                    'State': 'available',
                    'SubnetId': 'subnet-12345678',
                    'NatGatewayAddresses': [{'PrivateIp': '10.0.1.100', 'PublicIp': '1.2.3.4'}],
                }
            ]
        },
    }

    mock_client = Mock()
    mock_get_client.return_value = mock_client
    for method, response in complex_responses.items():
        getattr(mock_client, method).return_value = response

    result = await vpc_details_module.get_vpc_network(vpc_id='vpc-12345678', region='us-east-1')

    assert len(result['vpc_endpoints']) == 1
    assert result['vpc_endpoints'][0].service_name == 'com.amazonaws.us-east-1.s3'
    assert len(result['nat_gateways']) == 1
    assert result['nat_gateways'][0].id == 'nat-12345678'
    assert result['network_acls'][0].rules[0].port_range == '80-80'
