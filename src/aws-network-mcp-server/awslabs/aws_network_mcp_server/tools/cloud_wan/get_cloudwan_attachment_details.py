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


async def get_cwan_attachment(
    attachment_id: Annotated[str, Field(..., description='AWS Cloud WAN attachment ID')],
    core_network_region: Annotated[
        str, Field(..., description='AWS region where the Cloud WAN is deployed')
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get detailed information for a specific Cloud WAN attachment based on its type.

    This method handles all Cloud WAN attachment types:
    - VPC attachments (includes subnet ARNs and VPC options)
    - Connect attachments (includes protocol options and transport attachment ID)
    - Direct Connect Gateway attachments (includes Direct Connect Gateway ARN)
    - Site-to-Site VPN attachments (includes VPN connection ARN)
    - Transit Gateway Route Table attachments (includes peering ID and route table ARN)

    Use cases:
    - Use this tool when you want to verify attachment details.
    - Validate that Cloud WAN attachment policy is working correctly.

    Returns comprehensive attachment details specific to each attachment type.
    """
    nm_client = get_aws_client('networkmanager', core_network_region, profile_name)

    response = nm_client.get_vpc_attachment(AttachmentId=attachment_id)
    if 'VpcAttachment' in response:
        attachment_data = response['VpcAttachment']
        return {
            'attachment_type': 'VPC',
            'attachment': attachment_data['Attachment'],
            'vpc_specific': {
                'subnet_arns': attachment_data.get('SubnetArns'),
                'options': attachment_data.get('Options'),
            },
        }

    response = nm_client.get_connect_attachment(AttachmentId=attachment_id)
    if 'ConnectAttachment' in response:
        attachment_data = response['ConnectAttachment']
        return {
            'attachment_type': 'CONNECT',
            'attachment': attachment_data['Attachment'],
            'connect_specific': {
                'transport_attachment_id': attachment_data.get('TransportAttachmentId'),
                'options': attachment_data.get('Options'),
            },
        }

    response = nm_client.get_direct_connect_gateway_attachment(AttachmentId=attachment_id)
    if 'DirectConnectGatewayAttachment' in response:
        attachment_data = response['DirectConnectGatewayAttachment']
        return {
            'attachment_type': 'DIRECT_CONNECT_GATEWAY',
            'attachment': attachment_data['Attachment'],
            'direct_connect_specific': {
                'direct_connect_gateway_arn': attachment_data.get('DirectConnectGatewayArn'),
            },
        }

    response = nm_client.get_site_to_site_vpn_attachment(AttachmentId=attachment_id)
    if 'SiteToSiteVpnAttachment' in response:
        attachment_data = response['SiteToSiteVpnAttachment']
        return {
            'attachment_type': 'SITE_TO_SITE_VPN',
            'attachment': attachment_data['Attachment'],
            'vpn_specific': {
                'vpn_connection_arn': attachment_data.get('VpnConnectionArn'),
            },
        }

    response = nm_client.get_transit_gateway_route_table_attachment(AttachmentId=attachment_id)
    if 'TransitGatewayRouteTableAttachment' in response:
        attachment_data = response['TransitGatewayRouteTableAttachment']
        return {
            'attachment_type': 'TRANSIT_GATEWAY_ROUTE_TABLE',
            'attachment': attachment_data['Attachment'],
            'transit_gateway_specific': {
                'peering_id': attachment_data.get('PeeringId'),
                'transit_gateway_route_table_arn': attachment_data.get(
                    'TransitGatewayRouteTableArn'
                ),
            },
        }

    raise ToolError(f'Attachment {attachment_id} not found or unsupported attachment type')
