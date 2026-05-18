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


async def list_route53_profiles(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the Route 53 Profiles are deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    profile_id: Annotated[
        Optional[str],
        Field(
            ...,
            description='Optional Route 53 Profile ID to retrieve attached resources for a specific profile.',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List Route 53 Profiles with VPC associations and attached resources. Use when troubleshooting enterprise multi-VPC DNS management.

    Use this tool when:
    - Troubleshooting enterprise multi-VPC DNS management with Route 53 Profiles
    - Verifying which profiles are associated with specific VPCs
    - Reviewing resources attached to a profile (private hosted zones, resolver rules, DNS Firewall rule groups)
    - Diagnosing DNS configuration inconsistencies across VPCs
    - Auditing profile sharing status across accounts

    Common workflows:
    1. list_route53_profiles() → Identify profiles → Check VPC associations
    2. list_route53_profiles(profile_id=...) → Review attached resources
    3. list_route53_profiles() → Find profiles → Verify DNS config consistency

    Returns:
        Dict containing:
        - profiles: List of Route 53 Profiles with VPC associations
        - profile_resources: List of attached resources (only when profile_id is provided)
        - count: Total number of profiles
        - region: AWS region queried
    """
    try:
        client = get_aws_client('route53profiles', region, profile_name)

        # Get all profiles
        profiles_paginator = client.get_paginator('list_profiles')
        all_profiles = []
        for page in profiles_paginator.paginate():
            all_profiles.extend(page.get('ProfileSummaries', []))

        # Get ALL profile associations in one pass and build a lookup by profile ID
        all_associations = []
        try:
            assoc_paginator = client.get_paginator('list_profile_associations')
            for assoc_page in assoc_paginator.paginate():
                all_associations.extend(assoc_page.get('ProfileAssociations', []))
        except Exception:
            pass

        profile_vpc_map: Dict[str, list] = {}
        for assoc in all_associations:
            pid = assoc.get('ProfileId', '')
            vpc_id = assoc.get('ResourceId')
            if vpc_id:
                profile_vpc_map.setdefault(pid, []).append(vpc_id)

        # Build profiles with VPC associations
        profiles = []
        for prof in all_profiles:
            pid = prof.get('Id', '')
            profiles.append(
                {
                    'id': pid,
                    'name': prof.get('Name', ''),
                    'status': prof.get('Status', ''),
                    'share_status': prof.get('ShareStatus', ''),
                    'vpc_associations': profile_vpc_map.get(pid, []),
                }
            )

        # If profile_id is provided, get attached resources for that profile
        profile_resources = None
        if profile_id:
            res_paginator = client.get_paginator('list_profile_resource_associations')
            raw_resources = []
            for page in res_paginator.paginate(ProfileId=profile_id):
                raw_resources.extend(page.get('ProfileResourceAssociations', []))

            profile_resources = []
            for res in raw_resources:
                profile_resources.append(
                    {
                        'resource_type': res.get('ResourceType', ''),
                        'resource_id': res.get('ResourceArn', ''),
                        'name': res.get('Name', ''),
                        'status': res.get('Status', ''),
                    }
                )

        return {
            'profiles': profiles,
            'profile_resources': profile_resources,
            'count': len(profiles),
            'region': region,
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error listing Route 53 Profiles. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
