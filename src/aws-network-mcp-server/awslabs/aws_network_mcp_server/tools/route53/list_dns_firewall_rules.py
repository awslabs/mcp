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


async def list_dns_firewall_rules(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the DNS Firewall resources are deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
    rule_group_id: Annotated[
        Optional[str],
        Field(
            ...,
            description='Optional DNS Firewall rule group ID to retrieve individual rules for a specific group.',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List DNS Firewall rule groups with VPC associations. Use when diagnosing blocked DNS queries.

    Use this tool when:
    - Diagnosing DNS queries being blocked or altered by DNS Firewall policies
    - Verifying which DNS Firewall rule groups are associated with specific VPCs
    - Auditing DNS Firewall rule group configurations and priorities
    - Troubleshooting DNS resolution failures caused by firewall rules
    - Reviewing ALLOW, BLOCK, and ALERT actions on DNS domain lists

    Common workflows:
    1. list_dns_firewall_rules() → Identify rule groups → Check VPC associations
    2. list_dns_firewall_rules(rule_group_id=...) → Review individual rules and actions
    3. list_dns_firewall_rules() → Find rule groups → Verify priorities across VPCs

    Returns:
        Dict containing:
        - firewall_rule_groups: List of DNS Firewall rule groups with VPC associations
        - firewall_rules: List of individual rules (only when rule_group_id is provided)
        - count: Total number of rule groups
        - region: AWS region queried
    """
    try:
        client = get_aws_client('route53resolver', region, profile_name)

        # Get all firewall rule groups
        groups_paginator = client.get_paginator('list_firewall_rule_groups')
        all_groups = []
        for page in groups_paginator.paginate():
            all_groups.extend(page.get('FirewallRuleGroups', []))

        # Get ALL VPC associations in one pass and build a lookup by rule group ID
        all_associations = []
        try:
            assoc_paginator = client.get_paginator('list_firewall_rule_group_associations')
            for assoc_page in assoc_paginator.paginate():
                all_associations.extend(assoc_page.get('FirewallRuleGroupAssociations', []))
        except Exception:
            pass

        group_vpc_map: Dict[str, list] = {}
        for assoc in all_associations:
            group_id = assoc.get('FirewallRuleGroupId', '')
            vpc_id = assoc.get('VpcId')
            priority = assoc.get('Priority')
            if vpc_id:
                group_vpc_map.setdefault(group_id, []).append(
                    {
                        'vpc_id': vpc_id,
                        'priority': priority,
                    }
                )

        # Build firewall rule groups with VPC associations
        firewall_rule_groups = []
        for group in all_groups:
            group_id = group.get('Id', '')
            firewall_rule_groups.append(
                {
                    'id': group_id,
                    'name': group.get('Name', ''),
                    'share_status': group.get('ShareStatus', ''),
                    'owner_id': group.get('OwnerId', ''),
                    'vpc_associations': group_vpc_map.get(group_id, []),
                }
            )

        # If rule_group_id is provided, get individual rules for that group
        firewall_rules = None
        if rule_group_id:
            rules_paginator = client.get_paginator('list_firewall_rules')
            raw_rules = []
            for page in rules_paginator.paginate(FirewallRuleGroupId=rule_group_id):
                raw_rules.extend(page.get('FirewallRules', []))

            firewall_rules = []
            for rule in raw_rules:
                firewall_rules.append(
                    {
                        'name': rule.get('Name', ''),
                        'priority': rule.get('Priority'),
                        'action': rule.get('Action', ''),
                        'firewall_domain_list_id': rule.get('FirewallDomainListId', ''),
                        'block_response': rule.get('BlockResponse'),
                    }
                )

        return {
            'firewall_rule_groups': firewall_rule_groups,
            'firewall_rules': firewall_rules,
            'count': len(firewall_rule_groups),
            'region': region,
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error listing DNS Firewall rules. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
