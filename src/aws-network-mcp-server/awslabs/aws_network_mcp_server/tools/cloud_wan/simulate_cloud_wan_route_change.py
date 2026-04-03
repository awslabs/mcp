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

import copy
from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from awslabs.aws_network_mcp_server.utils.formatters import format_routes
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional


async def simulate_cwan_route_change(
    changes: Annotated[
        List[Dict[str, str]],
        Field(
            ...,
            description="List of attachemnt IDs and segments to move the routes to. Format is {'attachment_id': 'xxxx', 'segment': 'yyyyy'}",
        ),
    ],
    region: Annotated[
        str, Field(..., description='AWS region for which the route simulation should be done')
    ],
    cloudwan_region: Annotated[
        str, Field(..., description='AWS region where the Cloud WAN is located')
    ],
    core_network_id: Annotated[str, Field(..., description='AWS Cloud WAN core network ID')],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Simulate Cloud WAN network changes for a single region. Provide list of attachment IDs and the segments where to put them.

    This script will get the active route tables from Cloud WAN for single region and then simulate how the route tables would look like when attachemnt routes are changed.

    RELATED TOOLS:
        - Use get_cloudwan_details() first to understand current state
        - Use get_cloud_wan_routes() to see current routing
        - Use find_cloudwan_vpc_attachment() to identify attachment segments

    SIMULATION WORKFLOW:
        1. Get current state with get_cloudwan_details()
        2. Run simulation with this tool
        3. Compare 'before' and 'after' route tables

    Provide only the attachment id to simulate a scenario where the attachment is completely removed.

    example input for changes attribute to simulate moving an attachment from segment to another
    [
        {
            "attachment_id": "attachment-1234567890abcdefg",
            "segment": "segmentA"
        }
    ]

    Example input for changes attribute to simulate removing attachment completely.
    [
        {
            "attachment_id": "attachment-1234567890abcdefg",
        }
    ]

    Returns:
        List of dict: Original Cloud WAN route tables
        List of dict: Modified Cloud WAN route tables
    """
    try:
        nm_client = get_aws_client('networkmanager', cloudwan_region, profile_name)

        core_network = nm_client.get_core_network(CoreNetworkId=core_network_id)['CoreNetwork']
        global_network_id = core_network['GlobalNetworkId']
    except Exception as e:
        raise ToolError(
            f'There was an error when trying to get the core network details. Error: {str(e)}.'
        )

    all_routes = {}
    routes_to_change = []

    for segment in core_network['Segments']:
        if region not in segment['EdgeLocations']:
            continue

        routes = nm_client.get_network_routes(
            GlobalNetworkId=global_network_id,
            RouteTableIdentifier={
                'CoreNetworkSegmentEdge': {
                    'CoreNetworkId': core_network_id,
                    'SegmentName': segment['Name'],
                    'EdgeLocation': region,
                }
            },
        )['NetworkRoutes']

        key = f'{segment["Name"]}/{region}'
        all_routes[key] = routes
        for route in routes:
            dest = route.get('Destinations', [{}])[0]
            attachment = dest.get('TransitGatewayAttachmentId') or dest.get(
                'CoreNetworkAttachmentId'
            )
            for change in changes:
                if attachment == change['attachment_id']:
                    routes_to_change.append(
                        {
                            'route': route,
                            'segment': segment['Name'],
                            'new_segment': change.get('segment'),
                        }
                    )
                    break

    modified_routes = copy.deepcopy(all_routes)
    changes = []
    segment_changes = {}

    for item in routes_to_change:
        route = item['route']
        old_segment = item['segment']
        new_segment = item['new_segment']
        destination_cidr = route['DestinationCidrBlock']
        dest = route.get('Destinations', [{}])[0]
        attachment = dest.get('TransitGatewayAttachmentId') or dest.get('CoreNetworkAttachmentId')

        old_key = f'{old_segment}/{region}'
        modified_routes[old_key] = [
            r for r in modified_routes[old_key] if r['DestinationCidrBlock'] != destination_cidr
        ]

        if new_segment:
            new_key = f'{new_segment}/{region}'
            if new_key not in modified_routes:
                modified_routes[new_key] = []
            modified_routes[new_key].append(route)

            changes.append(
                {
                    'action': 'moved',
                    'destination': destination_cidr,
                    'attachment': attachment,
                    'from': old_segment,
                    'to': new_segment,
                }
            )

            if new_segment not in segment_changes:
                segment_changes[new_segment] = {'removed': 0, 'added': 0}
            segment_changes[new_segment]['added'] += 1
        else:
            changes.append(
                {
                    'action': 'removed',
                    'destination': destination_cidr,
                    'attachment': attachment,
                    'from': old_segment,
                }
            )

        if old_segment not in segment_changes:
            segment_changes[old_segment] = {'removed': 0, 'added': 0}
        segment_changes[old_segment]['removed'] += 1

    return {
        'summary': {
            'total_routes_moved': len(routes_to_change),
            'region': region,
            'segment_changes': segment_changes,
        },
        'changes': changes,
        'route_tables': {
            'before': format_routes(all_routes, core_network_id),
            'after': format_routes(modified_routes, core_network_id),
        },
    }
