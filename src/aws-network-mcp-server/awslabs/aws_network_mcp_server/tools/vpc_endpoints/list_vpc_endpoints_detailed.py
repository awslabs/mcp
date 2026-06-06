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

from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


async def list_vpc_endpoints_detailed(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region to list VPC endpoints in.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    vpc_id: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter endpoints by VPC ID. If not provided, returns endpoints across all VPCs.',
        ),
    ] = None,
    service_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter endpoints by AWS service name (e.g., com.amazonaws.us-east-1.s3).',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List VPC endpoints with detailed type-specific information across VPCs.

    For basic VPC endpoint info within a single VPC, use get_vpc_network_details().
    This tool provides detailed endpoint-specific information across VPCs, including
    security group IDs, private DNS status, DNS entries, network interface IDs,
    route table IDs, and creation timestamps for all endpoint types (Interface,
    Gateway, GatewayLoadBalancer).

    Use this tool when:
    - Listing all VPC endpoints across multiple VPCs in a region
    - Filtering endpoints by service name to find PrivateLink connections
    - Checking private DNS configuration and DNS entries for interface endpoints
    - Reviewing security group associations on interface endpoints
    - Auditing gateway endpoint route table associations

    Common workflows:
    1. list_vpc_endpoints_detailed() → check_endpoint_connectivity() for specific endpoint
    2. list_vpc_endpoints_detailed(service_name=...) → Identify all endpoints for a service
    3. list_vpc_endpoints_detailed(vpc_id=...) → Deep dive into a VPC's endpoint config

    Returns:
        Dict containing:
        - vpc_endpoints: List of endpoint dicts with type-specific fields
        - count: Total number of endpoints returned
        - region: AWS region queried
    """
    try:
        client = get_aws_client('ec2', region, profile_name)

        filters: List[Dict[str, Any]] = []
        if vpc_id:
            filters.append({'Name': 'vpc-id', 'Values': [vpc_id]})
        if service_name:
            filters.append({'Name': 'service-name', 'Values': [service_name]})

        paginator = client.get_paginator('describe_vpc_endpoints')
        paginate_params: Dict[str, Any] = {}
        if filters:
            paginate_params['Filters'] = filters

        endpoints = []
        for page in paginator.paginate(**paginate_params):
            for ep in page.get('VpcEndpoints', []):
                endpoint_type = ep.get('VpcEndpointType', '')
                endpoint_dict: Dict[str, Any] = {
                    'id': ep.get('VpcEndpointId', ''),
                    'service_name': ep.get('ServiceName', ''),
                    'type': endpoint_type,
                    'vpc_id': ep.get('VpcId', ''),
                    'state': ep.get('State', ''),
                    'creation_timestamp': str(ep.get('CreationTimestamp', '')),
                    'policy_document': ep.get('PolicyDocument'),
                    'tags': ep.get('Tags', []),
                }

                if endpoint_type == 'Gateway':
                    endpoint_dict['route_table_ids'] = ep.get('RouteTableIds', [])
                    endpoint_dict['subnet_ids'] = None
                    endpoint_dict['security_group_ids'] = None
                    endpoint_dict['private_dns_enabled'] = None
                    endpoint_dict['dns_entries'] = None
                    endpoint_dict['network_interface_ids'] = None
                elif endpoint_type == 'Interface':
                    endpoint_dict['route_table_ids'] = None
                    endpoint_dict['subnet_ids'] = ep.get('SubnetIds', [])
                    endpoint_dict['security_group_ids'] = [
                        g.get('GroupId', '') for g in ep.get('Groups', [])
                    ]
                    endpoint_dict['private_dns_enabled'] = ep.get('PrivateDnsEnabled', False)
                    endpoint_dict['dns_entries'] = [
                        {
                            'dns_name': d.get('DnsName', ''),
                            'hosted_zone_id': d.get('HostedZoneId', ''),
                        }
                        for d in ep.get('DnsEntries', [])
                    ]
                    endpoint_dict['network_interface_ids'] = ep.get('NetworkInterfaceIds', [])
                elif endpoint_type == 'GatewayLoadBalancer':
                    endpoint_dict['route_table_ids'] = None
                    endpoint_dict['subnet_ids'] = ep.get('SubnetIds', [])
                    endpoint_dict['security_group_ids'] = None
                    endpoint_dict['private_dns_enabled'] = None
                    endpoint_dict['dns_entries'] = None
                    endpoint_dict['network_interface_ids'] = ep.get('NetworkInterfaceIds', [])

                endpoints.append(endpoint_dict)

        return {
            'vpc_endpoints': endpoints,
            'count': len(endpoints),
            'region': region,
        }
    except Exception as e:
        raise ToolError(
            f'Error listing VPC endpoints. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
