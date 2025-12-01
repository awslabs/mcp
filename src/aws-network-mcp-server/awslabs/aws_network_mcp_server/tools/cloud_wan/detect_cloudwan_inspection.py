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


import json
from awslabs.aws_network_mcp_server.utils.aws_common import get_aws_client
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def detect_cwan_inspection(
    core_network_id: Annotated[str, Field(..., description='AWS Cloud WAN Core Network ID')],
    source_segment: Annotated[str, Field(..., description='Source segment name')],
    destination_segment: Annotated[
        str, Field(..., description='AWS Cloud WAN destination segment name')
    ],
    cloudwan_region: Annotated[
        str, Field(..., description='AWS region where the Cloud WAN core network is deployed.')
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Detect Network Function Groups (NFGs) performing inspection in CloudWAN path.

    Use this tool when:
    - Analyzing CloudWAN traffic inspection and security architecture
    - Troubleshooting connectivity issues that may involve NFG-based firewall filtering
    - Validating that Network Function Groups are properly configured for traffic inspection
    - Planning CloudWAN policy changes that could affect firewall traffic flow
    - Auditing security posture of CloudWAN segment-to-segment communication
    - Determining if traffic between specific segments will be inspected by firewalls

    This tool analyzes the live CloudWAN policy document to identify Network Function Groups
    (NFGs) that are configured to inspect traffic flowing between specified source and
    destination segments. It examines segment-actions in the policy to find 'via' or
    'send-via' routing rules that force traffic through inspection NFGs.

    Returns:
        Dict containing inspection NFGs in path, traffic inspection status, and detailed
        analysis of which NFGs will process traffic between the specified segments
    """
    try:
        nm_client = get_aws_client('networkmanager', cloudwan_region, profile_name)
        policy_response = nm_client.get_core_network_policy(
            CoreNetworkId=core_network_id, Alias='LIVE'
        )

        # Safely parse policy document with error handling
        try:
            policy_doc = json.loads(policy_response['CoreNetworkPolicy']['PolicyDocument'])
        except json.JSONDecodeError as e:
            return {
                'error': f'Invalid policy document JSON: {str(e)}',
                'success': False,
                'core_network_id': core_network_id,
            }

        # Validate segments exist
        segment_names = {seg.get('name') for seg in policy_doc.get('segments', [])}
        for segment, name in [(source_segment, 'Source'), (destination_segment, 'Destination')]:
            if segment not in segment_names:
                return {
                    'error': f'{name} segment "{segment}" not found in policy',
                    'success': False,
                }

        nfgs = {nfg.get('name'): nfg for nfg in policy_doc.get('network-function-groups', [])}
        inspection_nfgs = []

        # Check segment actions for NFG routing
        for action in policy_doc.get('segment-actions', []):
            if action.get('segment') != source_segment:
                continue

            # Extract NFG names from via/send-via routing
            nfg_names = []
            for key in ['via', 'send-via']:
                if key in action and 'network-function-groups' in action[key]:
                    nfg_names.extend(action[key]['network-function-groups'])

            if not nfg_names:
                continue

            # Check if action applies to destination
            destinations = action.get('destinations', [])
            when_sent_to_segments = action.get('when-sent-to', {}).get('segments', [])

            if destinations and destination_segment not in destinations:
                if destination_segment not in when_sent_to_segments:
                    continue

            # Build inspection info for each NFG
            for nfg_name in nfg_names:
                nfg_details = nfgs.get(nfg_name, {})
                inspection_nfgs.append(
                    {
                        'nfg_name': nfg_name,
                        'action_type': action.get('action', 'unknown'),
                        'segment': source_segment,
                        'destinations': destinations,
                        'mode': action.get('mode', 'default'),
                        'inspection_required': True,
                        'require_attachment_acceptance': nfg_details.get(
                            'require-attachment-acceptance', False
                        ),
                        'analysis_note': f"Traffic from {source_segment} to {destination_segment} passes through NFG '{nfg_name}' for inspection",
                    }
                )

        count = len(inspection_nfgs)
        return {
            'core_network_id': core_network_id,
            'path': f'{source_segment} -> {destination_segment}',
            'inspection_nfgs_in_path': inspection_nfgs,
            'total_inspection_nfgs': count,
            'traffic_inspected': count > 0,
            'inspection_summary': f'Traffic passes through {count} inspection NFG(s)'
            if count
            else 'No inspection NFGs in path - traffic not inspected',
        }

    except Exception as e:
        raise ToolError(f'Error detecting inspection in path: {str(e)}')
