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
from awslabs.aws_network_mcp_server.utils.vcp_details import (
    process_igws,
    process_nacls,
    process_nat_gateways,
    process_route_tables,
    process_subnets,
    process_vpc_endpoints,
)
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def get_vpc_network(
    vpc_id: Annotated[
        Optional[str],
        Field(..., description='VPC ID for which to return route table information '),
    ] = None,
    region: Annotated[
        Optional[str], Field(..., description='AWS region where the VPC is located')
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get comprehensive VPC network configuration including routing, subnets, security, and connectivity.

    Use this tool when:
    - Troubleshooting connectivity issues within a VPC
    - Analyzing why traffic cannot reach the internet or specific destinations
    - Understanding the network topology and routing paths
    - Investigating security group or NACL blocking issues
    - Validating VPC endpoint configurations
    - Mapping out subnet associations and route table assignments

    Required parameters:
    - vpc_id: The VPC identifier (e.g., vpc-0123456789abcdef0)
    - region: AWS region where the VPC exists (e.g., us-east-1, eu-west-1)

    Returns comprehensive VPC details:
    - VPC CIDR blocks and basic configuration
    - Route tables with all routes and subnet associations
    - Subnets with CIDR blocks, availability zones, and route table mappings
    - Internet gateways attached to the VPC
    - NAT gateways for private subnet internet access
    - Network ACLs with inbound/outbound rules
    - VPC endpoints for AWS service connectivity

    Common troubleshooting workflows:
    1. Internet connectivity: Check for internet gateway, route to 0.0.0.0/0, and NACL rules
    2. Subnet isolation: Verify route tables and NACL rules between subnets
    3. AWS service access: Confirm VPC endpoints exist for required services
    4. NAT gateway issues: Validate NAT gateway state and routing from private subnets

    Example scenarios:
    - "EC2 instance can't reach internet" → Check IGW attachment, route table 0.0.0.0/0 route, NACL egress
    - "Can't connect between subnets" → Verify route tables allow local routing, check NACL rules
    - "S3 access failing" → Look for S3 VPC endpoint or NAT gateway for internet path

    Note: This tool provides network configuration only. For traffic flow validation, use get_vpc_flow_logs.
    For security group rules on specific instances, use get_eni_details.
    """
    # Get VPC details
    try:
        ec2_client = get_aws_client('ec2', region, profile_name)
        vpc_resp = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        vpc = vpc_resp['Vpcs'][0]
    except Exception as e:
        raise ToolError(
            f'VPC with id {vpc_id} could not be found. Error: {str(e)}. VALIDATE PARAMETERS BEFORE CONTINUING.'
        )

    try:
        rt_resp = ec2_client.describe_route_tables(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        subnet_resp = ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        endpoint_resp = ec2_client.describe_vpc_endpoints(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        igw_resp = ec2_client.describe_internet_gateways(
            Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
        )
        acl_resp = ec2_client.describe_network_acls(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        nat_resp = ec2_client.describe_nat_gateways(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
    except Exception as e:
        raise ToolError(
            f'Failure reading VPC details. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    # Build result structure
    return {
        'vpc': {'id': vpc['VpcId'], 'cidr': vpc['CidrBlock'], 'region': region or 'us-east-1'},
        'route_tables': process_route_tables(rt_resp),
        'subnets': process_subnets(subnet_resp, rt_resp),
        'internet_gateway': process_igws(igw_resp),
        'nat_gateways': process_nat_gateways(nat_resp),
        'network_acls': process_nacls(acl_resp),
        'vpc_endpoints': process_vpc_endpoints(endpoint_resp),
    }
