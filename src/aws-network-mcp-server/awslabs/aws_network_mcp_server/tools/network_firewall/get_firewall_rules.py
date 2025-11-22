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
from awslabs.aws_network_mcp_server.utils.formatters import (
    format_stateful_rule,
    format_stateless_rule,
    parse_suricata_rule,
)
from fastmcp.exceptions import ToolError
from pydantic import Field
from typing import Annotated, Any, Dict, Optional


async def get_firewall_rules(
    firewall_name: Annotated[str, Field(..., description='AWS Network Firewall name')],
    region: Annotated[
        Optional[str], Field(..., description='AWS Region where the network firewall is located')
    ] = None,
    profile_name: Annotated[
        Optional[str],
        Field(
            ...,
            description='AWS CLI Profile Name to access the AWS account where the resources are deployed. By default uses the profile configured in MCP configuration',
        ),
    ] = None,
) -> Dict[str, Any]:
    """Get AWS Network Firewall rules for traffic inspection analysis.

    Retrieves comprehensive firewall rule configuration including both stateless and stateful rules.
    Use this tool to analyze firewall policies, troubleshoot traffic blocking, and verify security rules.

    ## When to Use
    - Investigating why traffic is being blocked or allowed through the firewall
    - Validating firewall rule configuration and priorities
    - Analyzing security posture of Network Firewall deployments
    - Troubleshooting connectivity issues involving AWS Network Firewall
    - Auditing firewall rules for compliance or security reviews

    ## Rule Types Returned
    1. **Stateless Rules**: Fast path rules evaluated by priority (lower = higher priority)
       - Match on basic packet headers (source/dest IP, ports, protocols)
       - Actions: PASS, DROP, FORWARD to stateful engine

    2. **Stateful Rules**: Deep packet inspection rules
       - Suricata format rules for complex pattern matching
       - 5-tuple rules (protocol, source/dest IP/port)
       - Domain list rules for DNS filtering

    ## Workflow Integration
    1. Use detect_tgw_inspection() or detect_cloudwan_inspection() to identify firewalls in path
    2. Call this tool to retrieve and analyze firewall rules
    3. Use get_network_firewall_flow_logs() to verify actual traffic behavior

    Returns:
        Dict containing:
        - firewall_name: Name of the firewall
        - summary: Rule counts by type
        - stateless_rules: List of stateless rules with priorities and actions
        - stateful_rules: List of stateful rules with match criteria and actions
    """
    try:
        anfw_client = get_aws_client('network-firewall', region, profile_name)

        # Get firewall details
        firewall = anfw_client.describe_firewall(FirewallName=firewall_name)
        policy_arn = firewall['Firewall']['FirewallPolicyArn']

        # Get firewall policy
        policy = anfw_client.describe_firewall_policy(FirewallPolicyArn=policy_arn)

        stateless_rules = []
        stateful_rules = []

        # Process stateless rule groups
        for rule_group_ref in policy['FirewallPolicy'].get('StatelessRuleGroupReferences', []):
            rg = anfw_client.describe_rule_group(RuleGroupArn=rule_group_ref['ResourceArn'])
            rules_source = rg['RuleGroup'].get('RulesSource', {})

            if 'StatelessRulesAndCustomActions' in rules_source:
                for rule in rules_source['StatelessRulesAndCustomActions']['StatelessRules']:
                    formatted_rule = format_stateless_rule(rule, rule['Priority'])
                    stateless_rules.append(formatted_rule)

        # Process stateful rule groups
        for rule_group_ref in policy['FirewallPolicy'].get('StatefulRuleGroupReferences', []):
            rg = anfw_client.describe_rule_group(RuleGroupArn=rule_group_ref['ResourceArn'])
            rules_source = rg['RuleGroup'].get('RulesSource', {})
            rule_group_name = rg['RuleGroup'].get('RuleGroupName', 'Unknown')

            # Handle Suricata rules string
            if 'RulesString' in rules_source:
                rules_string = rules_source['RulesString']
                # Split by newlines and parse each rule
                for line in rules_string.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parsed_rule = parse_suricata_rule(line)
                        if parsed_rule:
                            parsed_rule['rule_group_name'] = rule_group_name
                            stateful_rules.append(parsed_rule)

            # Handle individual stateful rules
            if 'StatefulRules' in rules_source:
                for i, rule in enumerate(rules_source['StatefulRules'], 1):
                    formatted_rule = format_stateful_rule(rule, str(i))
                    formatted_rule['rule_group_name'] = rule_group_name
                    stateful_rules.append(formatted_rule)
    except Exception as e:
        raise ToolError(
            f'There was an error getting AWS Network Firewall rules. Error: {e}. REQUIRED TO REMEDIATE BEFORE CONTINUING'
        )

    return {
        'firewall_name': firewall_name,
        'summary': {
            'total_stateless_rules': len(stateless_rules),
            'total_stateful_rules': len(stateful_rules),
        },
        'stateless_rules': stateless_rules,
        'stateful_rules': stateful_rules,
    }
