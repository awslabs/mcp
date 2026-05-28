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


VALID_ZONE_TYPES = ('public', 'private')


async def list_hosted_zones(
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    zone_type: Annotated[
        Optional[str],
        Field(
            ...,
            description='Filter by zone type: "public" or "private". Returns all zones if not specified.',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List all Route 53 hosted zones with type and record counts.

    Use this tool when:
    - Discovering DNS zones in an AWS account
    - Identifying public vs private hosted zones
    - Finding private zones and their VPC associations
    - Starting DNS troubleshooting to identify available hosted zones
    - Auditing DNS zone inventory

    Common workflows:
    1. List zones → Identify target zone → query_dns_records() for record details
    2. List zones → Find private zones → Verify VPC associations for DNS resolution
    3. List zones → check_health_checks() for health check status

    Returns:
        Dict containing:
        - hosted_zones: List of hosted zone objects with ID, name, record count, type, VPC associations
        - count: Number of hosted zones found
    """
    if zone_type is not None and zone_type not in VALID_ZONE_TYPES:
        raise ToolError(
            f'Error listing hosted zones. Error: Invalid zone_type "{zone_type}". '
            f'Must be one of: {", ".join(VALID_ZONE_TYPES)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    try:
        client = get_aws_client('route53', None, profile_name)
        paginator = client.get_paginator('list_hosted_zones')
        zones = []
        for page in paginator.paginate():
            zones.extend(page.get('HostedZones', []))

        if zone_type is not None:
            is_private = zone_type == 'private'
            zones = [
                z for z in zones if z.get('Config', {}).get('PrivateZone', False) == is_private
            ]

        hosted_zones = []
        for zone in zones:
            zone_id = zone.get('Id', '')
            is_private = zone.get('Config', {}).get('PrivateZone', False)
            zone_info = {
                'id': zone_id,
                'name': zone.get('Name', ''),
                'record_count': zone.get('ResourceRecordSetCount', 0),
                'is_private': is_private,
                'comment': zone.get('Config', {}).get('Comment'),
                'vpcs': None,
            }

            if is_private:
                try:
                    detail = client.get_hosted_zone(Id=zone_id)
                    vpcs = detail.get('VPCs', [])
                    zone_info['vpcs'] = [
                        {'vpc_id': v.get('VPCId', ''), 'vpc_region': v.get('VPCRegion', '')}
                        for v in vpcs
                    ]
                except Exception:
                    zone_info['vpcs'] = []

            hosted_zones.append(zone_info)

        return {
            'hosted_zones': hosted_zones,
            'count': len(hosted_zones),
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error listing hosted zones. Error: {str(e)}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
