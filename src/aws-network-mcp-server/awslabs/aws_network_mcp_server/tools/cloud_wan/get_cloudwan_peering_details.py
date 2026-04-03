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


async def get_cwan_peering(
    peering_id: Annotated[str, Field(..., description='Cloud WAN Peering ID')],
    core_network_region: Annotated[
        str, Field(..., description='Region where Cloud WAN core network is deployed')
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get comprehensive peering details from both Cloud WAN and Transit Gateway perspectives.

    Use this tool when:
    - Troubleshooting connectivity issues between Cloud WAN and Transit Gateway
    - Validating peering configuration and state
    - Understanding routing between Cloud WAN segments and Transit Gateway route tables
    - Investigating cross-region or cross-account network connectivity
    - Verifying peering attachment associations

    This tool retrieves complete peering information including:
    - Cloud WAN peering configuration (state, edge location, segment)
    - Transit Gateway details (ASN, route table associations)
    - Peering attachment ID and associated route table
    - Segment and edge location information

    RELATED TOOLS:
    - Use list_cloudwan_peerings() first to discover available peerings
    - Use get_tgw_routes() to examine routes in the associated route table
    - Use get_cloudwan_routes() to verify Cloud WAN segment routing

    Returns:
        Dict containing:
        - cloudwan_peering: Full Cloud WAN peering details
        - cloudwan_segment: Segment name where peering is attached
        - cloudwan_edge_location: Edge location of the peering
        - transit_gateway: Transit Gateway configuration details
        - peering_route_table_id: TGW route table associated with peering
        - peering_attachment_id: Attachment ID for the peering connection
    """
    try:
        nm_client = get_aws_client('networkmanager', core_network_region, profile_name)

        # Get Cloud WAN peering details
        peering_response = nm_client.get_transit_gateway_peering(PeeringId=peering_id)
        peering = peering_response['TransitGatewayPeering']

        # Extract TGW ARN and region
        tgw_arn = peering['TransitGatewayArn']
        tgw_region = tgw_arn.split(':')[3]
        tgw_id = tgw_arn.split('/')[-1]

        # Get Transit Gateway details and route tables
        ec2_client = get_aws_client('ec2', tgw_region, profile_name)
        tgw_response = ec2_client.describe_transit_gateways(TransitGatewayIds=[tgw_id])

        # Get peering attachment ID from the peering response
        peering_attachment_id = peering.get('TransitGatewayPeeringAttachmentId')

        # Find the route table associated with the peering attachment
        peering_route_table_id = None
        if peering_attachment_id:
            # Get all route tables and check associations
            route_tables_response = ec2_client.describe_transit_gateway_route_tables(
                Filters=[{'Name': 'transit-gateway-id', 'Values': [tgw_id]}]
            )
            for rt in route_tables_response.get('TransitGatewayRouteTables', []):
                associations_response = ec2_client.get_transit_gateway_route_table_associations(
                    TransitGatewayRouteTableId=rt['TransitGatewayRouteTableId']
                )
                for assoc in associations_response.get('Associations', []):
                    if assoc.get('TransitGatewayAttachmentId') == peering_attachment_id:
                        peering_route_table_id = rt['TransitGatewayRouteTableId']
                        break
                if peering_route_table_id:
                    break

        # Get Cloud WAN segment information from peering response
        segment_info = peering['Peering'].get('SegmentName')
        edge_location = peering['Peering'].get('EdgeLocation')

        return {
            'cloudwan_peering': peering,
            'cloudwan_segment': segment_info,
            'cloudwan_edge_location': edge_location,
            'transit_gateway': tgw_response['TransitGateways'][0]
            if tgw_response['TransitGateways']
            else None,
            'peering_route_table_id': peering_route_table_id,
            'peering_attachment_id': peering_attachment_id,
        }
    except Exception as e:
        raise ToolError(
            f'Error getting Cloud WAN peering details with error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
