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


async def get_tgw_routes(
    global_network_region: Annotated[
        str,
        Field(
            ...,
            description='Region for the Cloud WAN Global Network where the Transit Gateway is registered to.',
        ),
    ],
    transit_gateway_id: Annotated[
        str,
        Field(
            ...,
            description='Transit Gateway ID to get the routes',
        ),
    ],
    route_table_id: Annotated[
        str,
        Field(..., description='Transit Gateway Route Table ID for which to get the routes.'),
    ],
    route_state: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter based on active or blackhole routes. Valid values ACTIVE / BLACKHOLE',
        ),
    ] = None,
    route_type: Annotated[
        Optional[str],
        Field(..., description='Filter based on the route type. Valid values PROPAGATED / STATIC'),
    ] = None,
    cloudwan_account_profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the account where Cloud WAN is deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get routes from a specific Transit Gateway route table with optional filtering.

    Use this tool when:
    - Analyzing routing paths through a Transit Gateway
    - Troubleshooting connectivity issues involving Transit Gateway routing
    - Verifying route propagation from VPC or VPN attachments
    - Identifying blackhole routes that may be blocking traffic
    - Comparing static vs propagated routes in a route table

    Prerequisites:
    - Transit Gateway must be registered to a Cloud WAN Global Network
    - Use list_transit_gateways() to discover Transit Gateway IDs
    - Use get_tgw_details() to find route table IDs

    Filters:
    - route_state: Filter by ACTIVE (working routes) or BLACKHOLE (failed routes)
    - route_type: Filter by PROPAGATED (automatic) or STATIC (manual) routes

    Returns:
    - Route destinations (CIDR blocks)
    - Attachment IDs where traffic is forwarded
    - Resource types (VPC, VPN, peering, etc.)
    - Route type and state for each entry
    - Total route count

    Common troubleshooting workflow:
    1. Use get_tgw_details() to list available route tables
    2. Call this tool with specific route_table_id
    3. Check for blackhole routes if connectivity fails
    4. Verify expected routes are present and active
    """
    try:
        cloudwan_client = get_aws_client(
            'networkmanager', global_network_region, cloudwan_account_profile_name
        )

        # Validate that the Transit Gateway is registered to the Cloud WAN Global Network
        global_network_ids = []
        for core_network in cloudwan_client.list_core_networks()['CoreNetworks']:
            if core_network['State'] == 'AVAILABLE':
                global_network_ids.append(core_network['GlobalNetworkId'])
                break

        if global_network_ids == []:
            raise ToolError(
                'No Cloud WAN Global Networks found in this account and region. VALIDATE PARAMETERS BEFORE CONTINUING.'
            )

        registered_global_net = None
        transit_gateway_region = None
        transit_gateway_account_id = None
        for global_net_id in global_network_ids:
            reg_resp = cloudwan_client.get_transit_gateway_registrations(
                GlobalNetworkId=global_net_id,
            )
            for tgw in reg_resp['TransitGatewayRegistrations']:
                if tgw['TransitGatewayArn'].endswith(transit_gateway_id):
                    registered_global_net = global_net_id
                    transit_gateway_region = tgw['TransitGatewayArn'].split(':')[3]
                    transit_gateway_account_id = tgw['TransitGatewayArn'].split(':')[4]
                    break

        if not registered_global_net:
            raise ToolError(
                'Transit Gateway is not registered to Cloud WAN Global Network and route discovery is only possible for registered transit gateway. Request user to check that the transit gateway is registered to Cloud WAN Global Network. REQUIRED TO REMEDIATE BEFORE CONTINUING'
            )

        states = ['ACTIVE', 'BLACKHOLE']
        if route_state:
            if route_state not in states:
                raise ToolError(
                    'Route state value not valid. Only ACTIVE and BLACKHOLE are allowed. VALIDATE PARAMETERS BEFORE CONTINUING.'
                )
            else:
                states = [route_state]
        types = ['PROPAGATED', 'STATIC']
        if route_type:
            if route_type not in types:
                raise ToolError(
                    'Route type value not valid. Only PROPAGATED and STATIC are allowed. VALIDATE PARAMETERS BEFORE CONTINUING.'
                )
            else:
                types = [route_type]

        tgw_rt_resp = cloudwan_client.get_network_routes(
            GlobalNetworkId=registered_global_net,
            RouteTableIdentifier={
                'TransitGatewayRouteTableArn': f'arn:aws:ec2:{transit_gateway_region}:{transit_gateway_account_id}:transit-gateway-route-table/{route_table_id}'
            },
            States=states,
            Types=types,
        )

        routes = {route_table_id: {'routes': []}}
        for route in tgw_rt_resp['NetworkRoutes']:
            routes[route_table_id]['routes'].append(
                {
                    'destination': route.get('DestinationCidrBlock'),
                    'attachment_id': route['Destinations'][0]['TransitGatewayAttachmentId'],
                    'resource_type': route['Destinations'][0]['ResourceType'],
                    'type': route['Type'].lower(),
                    'state': route['State'].lower(),
                }
            )

        route_count = sum(len(routes[rt]['routes']) for rt in routes)

        return {
            'transit_gateway_id': transit_gateway_id,
            'global_network_id': registered_global_net,
            'global_network_region': global_network_region,
            'route_count': route_count,
            'routes': routes,
        }
    except Exception as e:
        raise ToolError(
            f'Error getting Transit Gateway routes. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
