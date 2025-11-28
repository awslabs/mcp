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

from pydantic.dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional


@dataclass
class RouteDict:
    """VPC Route Table entry."""

    destination: str
    target: str
    state: str
    origin: str


@dataclass
class RouteTableDict:
    """VPC Route Table dataclass."""

    id: str
    type: Literal['main', 'custom']
    associated_subnets: List[str]
    routes: List[RouteDict]


@dataclass
class SubnetDict:
    """VPC Subnet dataclass."""

    id: str
    cidr: str
    az: str
    type: Literal['public', 'private']
    route_table_id: str


@dataclass
class VpcDict:
    """VPC dataclass."""

    id: str
    cidr: str
    region: str


@dataclass
class InternetGatewayDict:
    """Internet Gateway dataclass."""

    id: str
    type: str
    state: str


@dataclass
class NatGatewayDict:
    """NAT Gateway dataclass."""

    id: str
    type: str
    state: str
    subnet_id: str
    private_ips: List[str]
    public_ips: List[str]


@dataclass
class NetworkAclRuleDict:
    """VPC Network ACL entry dataclass."""

    rule_number: int
    protocol: str
    action: Literal['allow', 'deny']
    cidr: str
    port_range: str


@dataclass
class NetworkAclDict:
    """VPC Network ACL dataclass."""

    id: str
    associations: List[str]
    rules: List[NetworkAclRuleDict]


@dataclass
class VpcEndpointDict:
    """VPC Endpoint dataclass."""

    id: str
    type: str
    state: str
    service_name: str
    subnet_ids: List[str]
    policy_document: Optional[str] = None
    tags: Optional[List[Dict[str, str]]] = None


@dataclass
class VpcNetworkDetailsDict:
    """VPC Network details dataclass."""

    vpc: VpcDict
    route_tables: List[RouteTableDict]
    subnets: List[SubnetDict]
    internet_gateway: InternetGatewayDict
    nat_gateways: List[NatGatewayDict]
    network_acls: List[NetworkAclDict]
    vpc_endpoints: List[VpcEndpointDict]


def process_route_tables(route_tables: Dict[str, Any]) -> List[RouteTableDict]:
    """Format VPC Network details for better LLM usage."""
    result = []
    # Process route tables
    for rt in route_tables['RouteTables']:
        is_main = any(assoc.get('Main', False) for assoc in rt.get('Associations', []))
        associated_subnets = [
            assoc['SubnetId'] for assoc in rt.get('Associations', []) if 'SubnetId' in assoc
        ]

        routes: List[RouteDict] = []
        for route in rt['Routes']:
            target = (
                route.get('GatewayId')
                or route.get('NatGatewayId')
                or route.get('TransitGatewayId')
                or route.get('VpcPeeringConnectionId')
                or route.get('NetworkInterfaceId')
                or route.get('EgressOnlyInternetGatewayId')
                or 'local'
            )
            routes.append(
                RouteDict(
                    **{
                        'destination': route.get('DestinationCidrBlock')
                        or route.get('DestinationIpv6CidrBlock', ''),
                        'target': target,
                        'state': route.get('State', ''),
                        'origin': route.get('Origin', ''),
                    }
                )
            )

        result.append(
            RouteTableDict(
                **{
                    'id': rt['RouteTableId'],
                    'type': 'main' if is_main else 'custom',
                    'associated_subnets': associated_subnets,
                    'routes': routes,
                }
            )
        )
    return result


def process_subnets(subnets: Dict[str, Any], route_tables: Dict[str, Any]) -> List[SubnetDict]:
    """Format VPC Subnet details for better LLM usage."""
    result = []
    # Process subnets
    for subnet in subnets['Subnets']:
        # Find associated route table
        subnet_to_rt = {}
        main_rt_id = {}
        for rt in route_tables['RouteTables']:
            for assoc in rt.get('Associations', []):
                if 'SubnetId' in assoc:
                    subnet_to_rt[assoc['SubnetId']] = rt['RouteTableId']
                elif assoc.get('Main'):
                    main_rt_id = rt['RouteTableId']

        rt_id = subnet_to_rt.get(subnet['SubnetId'], main_rt_id)

        # Determine if public or private
        subnet_type = 'private'
        if rt_id:
            for rt in route_tables['RouteTables']:
                if rt['RouteTableId'] == rt_id:
                    for route in rt['Routes']:
                        if route.get('GatewayId', '').startswith('igw-'):
                            subnet_type = 'public'
                            break

        result.append(
            SubnetDict(
                **{
                    'id': subnet['SubnetId'],
                    'cidr': subnet['CidrBlock'],
                    'az': subnet['AvailabilityZone'],
                    'type': subnet_type,
                    'route_table_id': rt_id if rt_id else '',
                }
            )
        )
    return result


def process_igws(igws: Dict[str, Any]) -> InternetGatewayDict:
    """Format VPC Internet Gateway details for better LLM usage."""
    internet_gateways = igws.get('InternetGateways', [])

    if internet_gateways and internet_gateways[0].get('Attachments'):
        igw = internet_gateways[0]
        return InternetGatewayDict(
            **{
                'id': igw['InternetGatewayId'],
                'type': 'Internet gateway',
                'state': igw['Attachments'][0]['State'],
            }
        )

    return InternetGatewayDict(
        **{
            'id': '',
            'type': 'Internet gateway',
            'state': '',
        }
    )


def process_nat_gateways(nat_gateways: Dict[str, Any]) -> List[NatGatewayDict]:
    """Format VPC NAT gateway details for better LLM usage."""
    result = []
    for nat in nat_gateways['NatGateways']:
        gw = NatGatewayDict(
            **{
                'id': nat['NatGatewayId'],
                'type': 'NAT Gateway',
                'state': nat['State'],
                'subnet_id': nat['SubnetId'],
                'private_ips': [],
                'public_ips': [],
            }
        )

        for address in nat['NatGatewayAddresses']:
            gw.private_ips.append(address['PrivateIp'])
            gw.public_ips.append(address['PublicIp'])

        result.append(gw)

    return result


def process_nacls(nacls: Dict[str, Any]) -> List[NetworkAclDict]:
    """Format VPC Network Access List details for better LLM usage."""
    result: List[NetworkAclDict] = []
    # Process network ACLs
    for acl in nacls['NetworkAcls']:
        associations = []
        for assoc in acl.get('Associations', []):
            associations.append(assoc['SubnetId'])

        rules = []
        for entry in acl['Entries']:
            port_range = ''
            if entry.get('PortRange'):
                port_range = f'{entry["PortRange"]["From"]}-{entry["PortRange"]["To"]}'

            rules.append(
                NetworkAclRuleDict(
                    **{
                        'rule_number': entry['RuleNumber'],
                        'protocol': entry['Protocol'],
                        'action': 'allow' if entry['RuleAction'] == 'allow' else 'deny',
                        'cidr': entry.get('CidrBlock', ''),
                        'port_range': port_range,
                    }
                )
            )

        result.append(
            NetworkAclDict(
                **{'id': acl['NetworkAclId'], 'associations': associations, 'rules': rules}
            )
        )
    return result


def process_vpc_endpoints(endpoints: Dict[str, Any]) -> List[VpcEndpointDict]:
    """Format VPC Endpoint details for better LLM usage."""
    result: List[VpcEndpointDict] = []
    for endpoint in endpoints['VpcEndpoints']:
        if endpoint['VpcEndpointType'] == 'Interface':
            result.append(
                VpcEndpointDict(
                    **{
                        'id': endpoint['VpcEndpointId'],
                        'type': endpoint['VpcEndpointType'],
                        'state': endpoint['State'],
                        'service_name': endpoint['ServiceName'],
                        'subnet_ids': endpoint['SubnetIds'],
                        'policy_document': endpoint['PolicyDocument'],
                        'tags': endpoint['Tags'],
                    }
                )
            )
        elif endpoint['VpcEndpointType'] == 'GatewayLoadBalancer':
            result.append(
                VpcEndpointDict(
                    **{
                        'id': endpoint['VpcEndpointId'],
                        'type': endpoint['VpcEndpointType'],
                        'state': endpoint['State'],
                        'service_name': endpoint['ServiceName'],
                        'subnet_ids': endpoint['SubnetIds'],
                        'tags': endpoint['Tags'],
                    }
                )
            )
    return result
