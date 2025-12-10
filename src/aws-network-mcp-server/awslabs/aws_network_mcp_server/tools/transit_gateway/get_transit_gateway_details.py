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


async def get_tgw(
    transit_gateway_id: Annotated[
        str, Field(..., description='Transit Gateway ID for which to get the details.')
    ],
    region: Annotated[
        str, Field(..., description='AWS region where the Transit Gateway is deployed into')
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get basic configuration and operational details of an AWS Transit Gateway.

    Use this tool when:
    - Starting Transit Gateway troubleshooting to understand its configuration
    - Verifying Transit Gateway state and availability
    - Checking ASN configuration for BGP peering scenarios
    - Understanding route table association/propagation behavior
    - Validating Transit Gateway ownership and account placement

    Common troubleshooting scenarios:
    - "Why isn't my Transit Gateway routing traffic?" - Check state and route table settings
    - "What ASN is configured for BGP?" - Returns amazon_side_asn
    - "Is this Transit Gateway using default route tables?" - Check association/propagation settings

    WORKFLOW CONTEXT:
    This is typically the first step when troubleshooting Transit Gateway issues.
    After getting basic details, use:
    - get_tgw_routes() to examine routing tables
    - list_tgw_peerings() to check connectivity to other networks
    - detect_tgw_inspection() to identify firewall inspection points
    - get_tgw_flow_logs() to analyze actual traffic patterns

    Returns:
        Dict containing:
        - transit_gateway_id: The Transit Gateway identifier
        - transit_gateway_arn: The ARN of the Transit Gateway
        - state: Current state (available, pending, deleting, deleted, modifying)
        - owner_id: AWS account ID that owns the Transit Gateway
        - description: User-provided description
        - creation_time: When the Transit Gateway was created (ISO format)
        - amazon_side_asn: BGP ASN for the Transit Gateway side
        - default_route_table_association: Whether attachments auto-associate to default route table
        - default_route_table_propagation: Whether attachments auto-propagate routes to default table
        - association_default_route_table_id: ID of the default association route table
        - propagation_default_route_table_id: ID of the default propagation route table
        - auto_accept_shared_attachments: Whether shared attachments are automatically accepted
        - dns_support: Whether DNS resolution is enabled between VPCs
        - vpn_ecmp_support: Whether Equal Cost Multipath is enabled for VPN connections
        - multicast_support: Whether multicast is enabled on the Transit Gateway
        - security_group_referencing_support: Whether cross-VPC security group references are enabled
        - transit_gateway_cidr_blocks: List of CIDR blocks assigned to the Transit Gateway
        - tags: Key-value pairs of resource tags
    """
    try:
        ec2_client = get_aws_client('ec2', region, profile_name)

        response = ec2_client.describe_transit_gateways(TransitGatewayIds=[transit_gateway_id])

        if not response['TransitGateways']:
            raise ToolError(
                'Transit Gateway was not found with the given details. VALIDATE PARAMETERS BEFORE CONTINUING.'
            )

        tgw = response['TransitGateways'][0]

        options = tgw['Options']

        return {
            'transit_gateway_id': tgw['TransitGatewayId'],
            'transit_gateway_arn': tgw.get('TransitGatewayArn', ''),
            'state': tgw['State'],
            'owner_id': tgw['OwnerId'],
            'description': tgw.get('Description', ''),
            'creation_time': tgw['CreationTime'].isoformat(),
            'amazon_side_asn': options['AmazonSideAsn'],
            'default_route_table_association': options['DefaultRouteTableAssociation'],
            'default_route_table_propagation': options['DefaultRouteTablePropagation'],
            'association_default_route_table_id': options.get(
                'AssociationDefaultRouteTableId', ''
            ),
            'propagation_default_route_table_id': options.get(
                'PropagationDefaultRouteTableId', ''
            ),
            'auto_accept_shared_attachments': options.get(
                'AutoAcceptSharedAttachments', 'disable'
            ),
            'dns_support': options.get('DnsSupport', 'enable'),
            'vpn_ecmp_support': options.get('VpnEcmpSupport', 'enable'),
            'multicast_support': options.get('MulticastSupport', 'disable'),
            'security_group_referencing_support': options.get(
                'SecurityGroupReferencingSupport', 'disable'
            ),
            'transit_gateway_cidr_blocks': options.get('TransitGatewayCidrBlocks', []),
            'tags': {tag['Key']: tag['Value'] for tag in tgw.get('Tags', [])},
        }
    except Exception as e:
        raise ToolError(
            f'There was an error getting AWS Transit Gateway details. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
