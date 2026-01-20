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
from typing import Annotated, Any, Dict, Optional


async def get_eni_details(
    eni_id: Annotated[str, Field(..., description='AWS Interface ID')],
    region: Annotated[
        Optional[str], Field(..., description='AWS Region where the network interface is located')
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get comprehensive AWS Elastic Network Interface (ENI) details for network troubleshooting.

    Use this tool when:
    - Analyzing network connectivity issues for EC2 instances, Lambda functions, or other AWS resources
    - Investigating security group or NACL rule configurations affecting traffic
    - Tracing routing paths from a specific network interface
    - Validating IP address assignments and associations
    - Following up after find_ip_address() to get detailed network configuration

    This tool retrieves:
    - Basic ENI information (ID, type, status, IPs, subnet, VPC, AZ)
    - Security group rules (inbound and outbound) for all attached security groups
    - Network ACL rules (inbound and outbound) for the subnet
    - Route table entries and associations for the subnet

    Common troubleshooting workflow:
    1. Use find_ip_address() to locate the ENI
    2. Call this tool to get security groups, NACLs, and routing
    3. Analyze rules to identify blocked traffic or misconfigurations
    4. Follow routing to next hop (IGW, NAT, TGW, VGW, etc.)

    Args:
        eni_id: ENI identifier (format: eni-xxxxxxxxxxxxxxxxx)
        region: AWS region code (e.g., us-east-1). If not provided, uses default region
        profile_name: AWS CLI profile name. If not provided, uses default credentials

    Returns:
        Dict containing:
        - basic_info: ENI metadata, IPs, subnet, VPC, AZ
        - security_groups: List of security groups with inbound/outbound rules
        - network_acls: List of NACLs with inbound/outbound rules
        - route_tables: List of route tables with routes and associations

    """
    try:
        ec2_client = get_aws_client('ec2', region, profile_name)

        # Get ENI details
        eni_response = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
        eni = eni_response['NetworkInterfaces'][0]

        subnet_id = eni['SubnetId']
        vpc_id = eni['VpcId']

        # Get security groups and rules
        sg_ids = [sg['GroupId'] for sg in eni['Groups']]
        sg_response = ec2_client.describe_security_groups(GroupIds=sg_ids)

        # Get route tables for subnet
        rt_response = ec2_client.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
        )

        # If no explicit association, get main route table
        if not rt_response['RouteTables']:
            rt_response = ec2_client.describe_route_tables(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'association.main', 'Values': ['true']},
                ]
            )

        # Get NACLs for subnet
        nacl_response = ec2_client.describe_network_acls(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id]}]
        )
    except Exception as e:
        raise ToolError(
            f'There was an error getting AWS ENI details. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    # Format output
    result = {
        'basic_info': {
            'id': eni['NetworkInterfaceId'],
            'type': eni['InterfaceType'],
            'status': eni['Status'],
            'private_ip': eni['PrivateIpAddress'],
            'public_ip': eni.get('Association', {}).get('PublicIp'),
            'subnet_id': subnet_id,
            'vpc_id': vpc_id,
            'availability_zone': eni['AvailabilityZone'],
        },
        'security_groups': [],
        'network_acls': [],
        'route_tables': [],
    }

    # Add security group rules
    for sg in sg_response['SecurityGroups']:
        sg_info = {
            'group_id': sg['GroupId'],
            'inbound_rules': sg['IpPermissions'],
            'outbound_rules': sg['IpPermissionsEgress'],
        }
        result['security_groups'].append(sg_info)

    # Add NACL rules
    for nacl in nacl_response['NetworkAcls']:
        nacl_info = {
            'network_acl_id': nacl['NetworkAclId'],
            'inbound_rules': [e for e in nacl['Entries'] if not e['Egress']],
            'outbound_rules': [e for e in nacl['Entries'] if e['Egress']],
        }
        result['network_acls'].append(nacl_info)

    # Add route table
    for rt in rt_response['RouteTables']:
        rt_info = {
            'route_table_id': rt['RouteTableId'],
            'routes': rt['Routes'],
            'associations': rt['Associations'],
        }
        result['route_tables'].append(rt_info)

    return result
