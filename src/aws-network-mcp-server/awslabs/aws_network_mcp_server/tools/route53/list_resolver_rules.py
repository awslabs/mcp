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


async def list_resolver_rules(
    region: Annotated[
        Optional[str],
        Field(..., description='AWS region where the Route 53 Resolver resources are deployed.'),
    ],
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """List Route 53 Resolver rules and endpoints for hybrid DNS troubleshooting.

    Use this tool when:
    - Diagnosing DNS resolution failures in hybrid cloud environments
    - Verifying Resolver forwarding rules and their VPC associations
    - Checking Resolver endpoint status and IP addresses
    - Auditing DNS forwarding configuration across VPCs
    - Troubleshooting on-premises to AWS DNS resolution

    Common workflows:
    1. list_resolver_rules() → Identify forwarding rules → Verify target IPs
    2. list_resolver_rules() → Check endpoint status → Verify IP addresses and subnets
    3. list_resolver_rules() → Find VPC associations → Verify DNS resolution scope

    Returns:
        Dict containing:
        - resolver_rules: List of resolver rules with VPC associations
        - resolver_endpoints: List of resolver endpoints with IP addresses
        - region: AWS region queried
    """
    try:
        client = get_aws_client('route53resolver', region, profile_name)

        # Get all resolver rules
        rules_paginator = client.get_paginator('list_resolver_rules')
        all_rules = []
        for page in rules_paginator.paginate():
            all_rules.extend(page.get('ResolverRules', []))

        # Get ALL VPC associations in one pass and build a lookup by rule ID
        all_associations = []
        try:
            assoc_paginator = client.get_paginator('list_resolver_rule_associations')
            for assoc_page in assoc_paginator.paginate():
                all_associations.extend(assoc_page.get('ResolverRuleAssociations', []))
        except Exception:
            pass

        rule_vpc_map: Dict[str, list] = {}
        for assoc in all_associations:
            rule_id = assoc.get('ResolverRuleId', '')
            vpc_id = assoc.get('VPCId')
            if vpc_id:
                rule_vpc_map.setdefault(rule_id, []).append(vpc_id)

        # Build resolver rules with VPC associations
        resolver_rules = []
        for rule in all_rules:
            rule_id = rule.get('Id', '')

            target_ips = []
            for tip in rule.get('TargetIps', []):
                target_ips.append(
                    {
                        'ip': tip.get('Ip', ''),
                        'port': tip.get('Port', 53),
                    }
                )

            resolver_rules.append(
                {
                    'id': rule_id,
                    'name': rule.get('Name', ''),
                    'domain_name': rule.get('DomainName', ''),
                    'rule_type': rule.get('RuleType', ''),
                    'status': rule.get('Status', ''),
                    'target_ips': target_ips,
                    'vpc_associations': rule_vpc_map.get(rule_id, []),
                }
            )

        # Get all resolver endpoints
        endpoints_paginator = client.get_paginator('list_resolver_endpoints')
        all_endpoints = []
        for page in endpoints_paginator.paginate():
            all_endpoints.extend(page.get('ResolverEndpoints', []))

        resolver_endpoints = []
        for ep in all_endpoints:
            ep_id = ep.get('Id', '')
            ip_addresses = []
            try:
                ip_paginator = client.get_paginator('list_resolver_endpoint_ip_addresses')
                for ip_page in ip_paginator.paginate(ResolverEndpointId=ep_id):
                    for ip_addr in ip_page.get('IpAddresses', []):
                        ip_addresses.append(
                            {
                                'ip': ip_addr.get('Ip', ''),
                                'subnet_id': ip_addr.get('SubnetId', ''),
                            }
                        )
            except Exception:
                pass

            resolver_endpoints.append(
                {
                    'id': ep_id,
                    'name': ep.get('Name', ''),
                    'direction': ep.get('Direction', ''),
                    'vpc_id': ep.get('HostVPCId', ''),
                    'status': ep.get('Status', ''),
                    'ip_addresses': ip_addresses,
                }
            )

        return {
            'resolver_rules': resolver_rules,
            'resolver_endpoints': resolver_endpoints,
            'region': region,
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(
            f'Error listing resolver rules. Error: {str(e)}. '
            f'REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )
