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


async def get_all_cwan_routes(
    cloudwan_region: Annotated[
        str, Field(..., description='AWS region where the Cloud WAN is deployed.')
    ],
    core_network_id: Annotated[str, Field(..., description='Cloud WAN Core Network ID.')],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get comprehensive Cloud WAN routing tables across all segments and regions.

    Use this tool when:
    - Analyzing complete Cloud WAN routing architecture across all segments
    - Troubleshooting connectivity issues requiring full routing visibility
    - Validating routing configuration after policy changes
    - Comparing routes across multiple segments and regions simultaneously
    - Auditing routing state for documentation or compliance

    When NOT to use:
    - For targeted route lookups in a specific segment/region (use get_cloudwan_routes instead)
    - When output size is a concern and you only need subset of routes
    - For initial exploration (start with get_cloudwan_details first)

    This tool retrieves routing information for every segment in every Cloud WAN edge location,
    providing a complete view of the network's routing state. Output can be extensive for
    large deployments with many segments and routes.

    Returns:
        dict: Complete routing tables organized by region and segment, including:
            - core_network_id: The Cloud WAN core network identifier
            - regions: Dict keyed by edge location containing:
                - segments: Dict keyed by segment name containing:
                    - routes: List of route entries with destination, target, type, and state

    Example workflow:
    1. Call get_cloudwan_details() to understand network structure
    2. Use this tool for comprehensive routing analysis
    3. Use get_cloudwan_routes() for focused segment-specific queries
    """
    cloudwan_client = get_aws_client('networkmanager', cloudwan_region, profile_name)

    try:
        core_network = cloudwan_client.get_core_network(CoreNetworkId=core_network_id)

        segments = core_network['CoreNetwork'].get('Segments', [])
        edges = core_network['CoreNetwork'].get('Edges', [])

        result = {'core_network_id': core_network_id, 'regions': {}}
    except Exception as e:
        raise ToolError(f'Error getting Cloud WAN routes. VALIDATE parameters. Error: {str(e)}')

    for edge in edges:
        edge_location = edge['EdgeLocation']
        result['regions'][edge_location] = {'segments': {}}

        for segment in segments:
            segment_name = segment['Name']

            try:
                routes_response = cloudwan_client.get_network_routes(
                    GlobalNetworkId=core_network['CoreNetwork']['GlobalNetworkId'],
                    RouteTableIdentifier={
                        'CoreNetworkSegmentEdge': {
                            'CoreNetworkId': core_network_id,
                            'EdgeLocation': edge_location,
                            'SegmentName': segment_name,
                        }
                    },
                )

                routes = []
                for route in routes_response.get('NetworkRoutes', []):
                    target = None
                    if route.get('Destinations'):
                        dest = route['Destinations'][0]
                        target = dest.get('CoreNetworkAttachmentId') or dest.get('ResourceId')

                    routes.append(
                        {
                            'destination': route.get('DestinationCidrBlock'),
                            'target': target,
                            'type': route.get('Type', '').lower(),
                            'state': route.get('State', '').lower(),
                        }
                    )

                result['regions'][edge_location]['segments'][segment_name] = {'routes': routes}

            except Exception:
                result['regions'][edge_location]['segments'][segment_name] = {'routes': []}

    return result
