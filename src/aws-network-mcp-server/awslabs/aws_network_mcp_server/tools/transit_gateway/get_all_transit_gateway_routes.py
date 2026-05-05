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


async def get_all_tgw_routes(
    transit_gateway_id: Annotated[
        str,
        Field(
            ...,
            description='Transit Gateway ID to get the routes for',
        ),
    ],
    global_network_region: Annotated[
        str,
        Field(
            ...,
            description='Region for the Cloud WAN Global Network where the Transit Gateway is registered to.',
        ),
    ],
    tgw_account_profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the account where Transit Gateway is deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    cloudwan_account_profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the account where Cloud WAN is deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get all Transit Gateway route tables and their routes in one call.

    Use this tool when:
    - You need a complete view of all routing in a Transit Gateway
    - Troubleshooting connectivity issues across multiple route tables
    - Comparing routes across different route tables
    - Initial discovery phase to understand TGW routing architecture

    Prerequisites:
    - Transit Gateway MUST be registered to AWS Network Manager (Cloud WAN Global Network)
    - If you receive a registration error, instruct the user to register the TGW first

    Performance considerations:
    - Returns ALL routes from ALL route tables (can be large output)
    - For focused analysis of a single route table, use get_tgw_routes() instead
    - Typical use: Initial discovery, then follow up with get_tgw_routes() for specific tables

    Cross-account support:
    - Transit Gateway and Cloud WAN can be in different accounts
    - Use tgw_account_profile_name for TGW account credentials
    - Use cloudwan_account_profile_name for Network Manager account credentials

    Returns:
        Dict containing:
        - transit_gateway_id: The TGW ID queried
        - transit_gateway_region: AWS region where TGW is deployed
        - global_network_id: Network Manager Global Network ID
        - global_network_region: Region where Global Network is registered
        - route_count: Total number of routes across all tables
        - routes: Dict keyed by route table ID, each containing:
            - name: Route table name from tags
            - state: Route table state (available, etc.)
            - routes: List of route objects with destination, attachment_id, resource_type, type, state
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

        transit_gateway_client = get_aws_client(
            'ec2', transit_gateway_region, tgw_account_profile_name
        )

        tg_rt_resp = transit_gateway_client.describe_transit_gateway_route_tables(
            Filters=[
                {
                    'Name': 'transit-gateway-id',
                    'Values': [transit_gateway_id],
                },
                {
                    'Name': 'state',
                    'Values': ['available'],
                },
            ]
        )
        tg_rts = tg_rt_resp['TransitGatewayRouteTables']

        while tg_rt_resp.get('NextToken', None):
            tg_rt_resp = transit_gateway_client.describe_transit_gateway_route_tables(
                Filters=[
                    {
                        'Name': 'transit-gateway-id',
                        'Values': [transit_gateway_id],
                    },
                    {
                        'Name': 'state',
                        'Values': ['available'],
                    },
                ]
            )
            tg_rts += tg_rt_resp['TransitGatewayRouteTables']

        routes = {}
        for rt in tg_rts:
            rt_id = rt['TransitGatewayRouteTableId']
            tgw_rt_resp = cloudwan_client.get_network_routes(
                GlobalNetworkId=registered_global_net,
                RouteTableIdentifier={
                    'TransitGatewayRouteTableArn': f'arn:aws:ec2:{transit_gateway_region}:{transit_gateway_account_id}:transit-gateway-route-table/{rt_id}'
                },
            )
            routes[rt_id] = {'routes': []}
            for tag in rt['Tags']:
                if tag['Key'] == 'Name':
                    routes[rt_id]['name'] = tag['Value']
                    break
            routes[rt_id]['state'] = rt['State'].lower()

            for route in tgw_rt_resp['NetworkRoutes']:
                routes[rt_id]['routes'].append(
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
            'transit_gateway_region': transit_gateway_region,
            'global_network_id': registered_global_net,
            'global_network_region': global_network_region,
            'route_count': route_count,
            'routes': routes,
        }
    except Exception as e:
        raise ToolError(
            f'There was an error getting Transit Gateway routes. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
