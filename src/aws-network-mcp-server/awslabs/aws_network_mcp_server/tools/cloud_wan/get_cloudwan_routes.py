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
from datetime import datetime
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def get_cwan_routes(
    core_network_id: Annotated[str, Field(..., description='Cloud WAN Core Network ID.')],
    region: Annotated[str, Field(..., description='AWS region to get routes for.')],
    segment: Annotated[
        Optional[str], Field(..., description='Segment name to get routes for.')
    ] = None,
    network_function_group: Annotated[
        Optional[str], Field(..., description='Network function group name to get routes for.')
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get network routes for a specific segment and region.

    Use this tool when:
    - Troubleshooting routing issues in Cloud WAN segments
    - Verifying route propagation to specific regions
    - Analyzing traffic paths through Network Function Groups (NFGs)
    - Checking if expected routes exist in segment route tables
    - Investigating blackhole or missing routes

    You must provide either segment OR network_function_group (or both).

    Common workflow:
    1. Use get_cloudwan_details() first to discover available segments and NFGs
    2. Call this tool for specific segment/region combinations
    3. Analyze route targets (attachment IDs) and states (active/blackhole)

    Returns route table with destination CIDRs, targets (attachment IDs),
    route types (propagated/static), and states (active/blackhole).
    """
    if not any([segment, network_function_group]):
        raise ToolError('Please provide a segment or network_function_group as parameter.')

    try:
        nm_client = get_aws_client('networkmanager', region_name=region, profile_name=profile_name)
        core_network = nm_client.get_core_network(CoreNetworkId=core_network_id)
    except Exception as e:
        raise ToolError(
            f'There was an error getting AWS Core Network details. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    segments = core_network['CoreNetwork'].get('Segments', [])
    segment_names = [segment['Name'] for segment in segments]
    network_function_groups = core_network['CoreNetwork'].get('NetworkFunctionGroups', [])
    nfg_names = [nfg['Name'] for nfg in network_function_groups]

    if segment:
        if segment not in segment_names:
            raise ToolError(f'Segment {segment} not found in core network {core_network_id}.')
    if network_function_group:
        if network_function_group not in nfg_names:
            raise ToolError(
                f'Network function group {network_function_group} not found in core network {core_network_id}.'
            )

    result = {
        'core_network_id': core_network_id,
        'region': region,
        'timestamp': datetime.now().isoformat(),
        'segment': {},
        'network_function_group': {},
    }
    if segment:
        routes_response = nm_client.get_network_routes(
            GlobalNetworkId=core_network['CoreNetwork']['GlobalNetworkId'],
            RouteTableIdentifier={
                'CoreNetworkSegmentEdge': {
                    'CoreNetworkId': core_network_id,
                    'EdgeLocation': region,
                    'SegmentName': segment,
                }
            },
        )

        if not routes_response.get('NetworkRoutes'):
            result['segment'] = {
                'name': segment,
                'routes': 'No network routes found with the given parameters.',
            }
        else:
            result['segment'] = {
                'name': segment,
                'routes': [
                    {
                        'destination': route.get('DestinationCidrBlock'),
                        'target': route['Destinations'][0].get('CoreNetworkAttachmentId')
                        or route['Destinations'][0].get('ResourceId'),
                        'type': route.get('Type', '').lower(),
                        'state': route.get('State', '').lower(),
                    }
                    for route in routes_response.get('NetworkRoutes', [])
                ],
            }

    if network_function_group:
        routes_response = nm_client.get_network_routes(
            GlobalNetworkId=core_network['CoreNetwork']['GlobalNetworkId'],
            RouteTableIdentifier={
                'CoreNetworkNetworkFunctionGroup': {
                    'CoreNetworkId': core_network_id,
                    'EdgeLocation': region,
                    'NetworkFunctionGroupName': network_function_group,
                }
            },
        )

        if not routes_response.get('NetworkRoutes'):
            result['network_function_group'] = {
                'name': network_function_group,
                'routes': 'No network routes found with the given parameters.',
            }
        else:
            result['network_function_group'] = {
                'name': network_function_group,
                'routes': [
                    {
                        'destination': route.get('DestinationCidrBlock'),
                        'target': route['Destinations'][0].get('CoreNetworkAttachmentId')
                        or route['Destinations'][0].get('ResourceId'),
                        'type': route.get('Type', '').lower(),
                        'state': route.get('State', '').lower(),
                    }
                    for route in routes_response.get('NetworkRoutes', [])
                ],
            }

    return result
