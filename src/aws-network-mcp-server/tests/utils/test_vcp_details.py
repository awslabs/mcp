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

"""Test cases for the vcp_details utils module."""

from awslabs.aws_network_mcp_server.utils.vcp_details import (
    NetworkAclRuleDict,
    RouteDict,
    SubnetDict,
    process_igws,
    process_nacls,
    process_nat_gateways,
    process_route_tables,
    process_subnets,
    process_vpc_endpoints,
)


class TestProcessRouteTables:
    """Test process_route_tables function."""

    def test_main_route_table(self):
        """Test processing main route table."""
        data = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-main',
                    'Associations': [{'Main': True}],
                    'Routes': [
                        {
                            'DestinationCidrBlock': '10.0.0.0/16',
                            'GatewayId': 'local',
                            'State': 'active',
                            'Origin': 'CreateRouteTable',
                        }
                    ],
                }
            ]
        }

        result = process_route_tables(data)

        assert len(result) == 1
        assert result[0].type == 'main'
        assert result[0].id == 'rtb-main'
        assert len(result[0].routes) == 1

    def test_custom_route_table_with_subnets(self):
        """Test processing custom route table with subnet associations."""
        data = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-custom',
                    'Associations': [{'SubnetId': 'subnet-123'}],
                    'Routes': [
                        {
                            'DestinationCidrBlock': '0.0.0.0/0',
                            'GatewayId': 'igw-123',
                            'State': 'active',
                            'Origin': 'CreateRoute',
                        }
                    ],
                }
            ]
        }

        result = process_route_tables(data)

        assert result[0].type == 'custom'
        assert result[0].associated_subnets == ['subnet-123']

    def test_route_with_different_targets(self):
        """Test routes with various target types."""
        data = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-test',
                    'Associations': [],
                    'Routes': [
                        {
                            'DestinationCidrBlock': '0.0.0.0/0',
                            'NatGatewayId': 'nat-123',
                            'State': 'active',
                            'Origin': 'CreateRoute',
                        },
                        {
                            'DestinationCidrBlock': '192.168.0.0/16',
                            'TransitGatewayId': 'tgw-123',
                            'State': 'active',
                            'Origin': 'CreateRoute',
                        },
                        {
                            'DestinationIpv6CidrBlock': '::/0',
                            'EgressOnlyInternetGatewayId': 'eigw-123',
                            'State': 'active',
                            'Origin': 'CreateRoute',
                        },
                    ],
                }
            ]
        }

        result = process_route_tables(data)
        routes = result[0].routes

        assert routes[0].target == 'nat-123'
        assert routes[1].target == 'tgw-123'
        assert routes[2].target == 'eigw-123'
        assert routes[2].destination == '::/0'


class TestProcessSubnets:
    """Test process_subnets function."""

    def test_public_subnet(self):
        """Test processing public subnet."""
        subnets_data = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-public',
                    'CidrBlock': '10.0.1.0/24',
                    'AvailabilityZone': 'us-east-1a',
                    'MapPublicIpOnLaunch': True,
                }
            ]
        }

        route_tables_data = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-public',
                    'Associations': [{'SubnetId': 'subnet-public'}],
                    'Routes': [{'GatewayId': 'igw-123'}],
                }
            ]
        }

        result = process_subnets(subnets_data, route_tables_data)

        assert result[0].type == 'public'
        assert result[0].route_table_id == 'rtb-public'

    def test_private_subnet_with_main_route_table(self):
        """Test processing private subnet using main route table."""
        subnets_data = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-private',
                    'CidrBlock': '10.0.2.0/24',
                    'AvailabilityZone': 'us-east-1b',
                }
            ]
        }

        route_tables_data = {
            'RouteTables': [
                {
                    'RouteTableId': 'rtb-main',
                    'Associations': [{'Main': True}],
                    'Routes': [{'GatewayId': 'local'}],
                }
            ]
        }

        result = process_subnets(subnets_data, route_tables_data)

        assert result[0].type == 'private'
        assert result[0].route_table_id == 'rtb-main'

    def test_subnet_without_route_table(self):
        """Test processing subnet without associated route table."""
        subnets_data = {
            'Subnets': [
                {
                    'SubnetId': 'subnet-orphan',
                    'CidrBlock': '10.0.3.0/24',
                    'AvailabilityZone': 'us-east-1c',
                }
            ]
        }

        route_tables_data = {'RouteTables': []}

        result = process_subnets(subnets_data, route_tables_data)

        assert result[0].route_table_id == ''


class TestProcessIgws:
    """Test process_igws function."""

    def test_attached_igw(self):
        """Test processing attached internet gateway."""
        data = {
            'InternetGateways': [
                {
                    'InternetGatewayId': 'igw-123',
                    'Attachments': [{'State': 'available', 'VpcId': 'vpc-123'}],
                }
            ]
        }

        result = process_igws(data)

        assert result.id == 'igw-123'
        assert result.state == 'available'
        assert result.type == 'Internet gateway'

    def test_no_igw(self):
        """Test processing when no internet gateway exists."""
        data = {'InternetGateways': []}

        result = process_igws(data)

        assert result.id == ''
        assert result.state == ''

    def test_igw_without_attachments(self):
        """Test processing IGW without attachments."""
        data = {'InternetGateways': [{'InternetGatewayId': 'igw-detached'}]}

        result = process_igws(data)

        assert result.id == ''
        assert result.state == ''


class TestProcessNatGateways:
    """Test process_nat_gateways function."""

    def test_nat_gateway_processing(self):
        """Test processing NAT gateway."""
        data = {
            'NatGateways': [
                {
                    'NatGatewayId': 'nat-123',
                    'State': 'available',
                    'SubnetId': 'subnet-123',
                    'NatGatewayAddresses': [
                        {'PrivateIp': '10.0.1.5', 'PublicIp': '1.2.3.4'},
                        {'PrivateIp': '10.0.1.6', 'PublicIp': '1.2.3.5'},
                    ],
                }
            ]
        }

        result = process_nat_gateways(data)

        assert len(result) == 1
        assert result[0].id == 'nat-123'
        assert result[0].private_ips == ['10.0.1.5', '10.0.1.6']
        assert result[0].public_ips == ['1.2.3.4', '1.2.3.5']

    def test_empty_nat_gateways(self):
        """Test processing empty NAT gateways list."""
        data = {'NatGateways': []}

        result = process_nat_gateways(data)

        assert result == []


class TestProcessNacls:
    """Test process_nacls function."""

    def test_nacl_processing(self):
        """Test processing network ACLs."""
        data = {
            'NetworkAcls': [
                {
                    'NetworkAclId': 'acl-123',
                    'Associations': [{'SubnetId': 'subnet-123'}],
                    'Entries': [
                        {
                            'RuleNumber': 100,
                            'Protocol': '6',
                            'RuleAction': 'allow',
                            'CidrBlock': '0.0.0.0/0',
                            'PortRange': {'From': 80, 'To': 80},
                        },
                        {
                            'RuleNumber': 200,
                            'Protocol': '-1',
                            'RuleAction': 'deny',
                            'CidrBlock': '192.168.1.0/24',
                        },
                    ],
                }
            ]
        }

        result = process_nacls(data)

        assert len(result) == 1
        assert result[0].id == 'acl-123'
        assert result[0].associations == ['subnet-123']
        assert len(result[0].rules) == 2
        assert result[0].rules[0].port_range == '80-80'
        assert result[0].rules[1].port_range == ''

    def test_empty_nacls(self):
        """Test processing empty NACLs list."""
        data = {'NetworkAcls': []}

        result = process_nacls(data)

        assert result == []


class TestProcessVpcEndpoints:
    """Test process_vpc_endpoints function."""

    def test_interface_endpoint(self):
        """Test processing interface VPC endpoint."""
        data = {
            'VpcEndpoints': [
                {
                    'VpcEndpointId': 'vpce-123',
                    'VpcEndpointType': 'Interface',
                    'State': 'available',
                    'ServiceName': 'com.amazonaws.us-east-1.s3',
                    'SubnetIds': ['subnet-123'],
                    'PolicyDocument': '{"Version":"2012-10-17"}',
                    'Tags': [{'Key': 'Name', 'Value': 'test-endpoint'}],
                }
            ]
        }

        result = process_vpc_endpoints(data)

        assert len(result) == 1
        assert result[0].type == 'Interface'
        assert result[0].policy_document == '{"Version":"2012-10-17"}'

    def test_gateway_load_balancer_endpoint(self):
        """Test processing Gateway Load Balancer endpoint."""
        data = {
            'VpcEndpoints': [
                {
                    'VpcEndpointId': 'vpce-gwlb',
                    'VpcEndpointType': 'GatewayLoadBalancer',
                    'State': 'available',
                    'ServiceName': 'com.amazonaws.vpce.us-east-1.vpce-svc-123',
                    'SubnetIds': ['subnet-456'],
                    'Tags': [],
                }
            ]
        }

        result = process_vpc_endpoints(data)

        assert len(result) == 1
        assert result[0].type == 'GatewayLoadBalancer'
        assert result[0].policy_document is None

    def test_gateway_endpoint_ignored(self):
        """Test that Gateway endpoints are ignored."""
        data = {
            'VpcEndpoints': [
                {
                    'VpcEndpointId': 'vpce-gateway',
                    'VpcEndpointType': 'Gateway',
                    'State': 'available',
                    'ServiceName': 'com.amazonaws.us-east-1.s3',
                }
            ]
        }

        result = process_vpc_endpoints(data)

        assert result == []


class TestDataClasses:
    """Test dataclass instantiation."""

    def test_route_dict(self):
        """Test RouteDict creation."""
        route = RouteDict(
            destination='0.0.0.0/0', target='igw-123', state='active', origin='CreateRoute'
        )
        assert route.destination == '0.0.0.0/0'

    def test_subnet_dict(self):
        """Test SubnetDict creation."""
        subnet = SubnetDict(
            id='subnet-123',
            cidr='10.0.1.0/24',
            az='us-east-1a',
            type='public',
            route_table_id='rtb-123',
        )
        assert subnet.type == 'public'

    def test_network_acl_rule_dict(self):
        """Test NetworkAclRuleDict creation."""
        rule = NetworkAclRuleDict(
            rule_number=100, protocol='6', action='allow', cidr='0.0.0.0/0', port_range='80-80'
        )
        assert rule.action == 'allow'
