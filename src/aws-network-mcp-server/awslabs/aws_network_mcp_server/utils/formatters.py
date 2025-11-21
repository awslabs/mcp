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

import re
from typing import Any, Dict


def format_stateless_rule(rule: Dict[str, Any], priority: str) -> Dict[str, Any]:
    """Format Network Firewall stateless rules for better LLM usage."""
    priority_int = int(priority)
    match_attrs = rule.get('MatchAttributes', {})

    source = match_attrs.get('Sources')
    dest = match_attrs.get('Destinations')
    protocol = match_attrs.get('Protocols')

    if source == '0.0.0.0/0':
        source = '0.0.0.0/0 (anywhere)'
    if dest == '0.0.0.0/0':
        dest = '0.0.0.0/0 (anywhere)'

    return {
        'priority': priority_int,
        'action': rule.get('RuleDefinition', {}).get('Actions')[0],
        'protocol': protocol,
        'source': source,
        'destination': dest,
    }


def format_stateful_rule(rule: Dict[str, Any], rule_id: str) -> Dict[str, Any]:
    """Format Network Firewall stateful rule for better LLM consumption."""
    header = rule.get('Header', {})

    return {
        'rule_id': rule_id,
        'type': 'standard',
        'action': rule.get('Action'),
        'protocol': header.get('Protocol'),
        'source': {'network': header.get('Source'), 'port': header.get('SourcePort')},
        'destination': {
            'network': header.get('Destination'),
            'port': header.get('DestinationPort'),
        },
        'direction': header.get('Direction'),
        'rule_options': rule.get('RuleOptions', []),
    }


def format_routes(routes_data: dict[str, Any], core_net_id: str):
    """Format Cloud WAN route details for better LLM consumption."""
    output = {'core_network_id': core_net_id, 'segments': {}}
    for key, routes in routes_data.items():
        segment, region = key.split('/')
        if segment not in output['segments']:
            output['segments'][segment] = {'regions': {}}
        if region not in output['segments'][segment]['regions']:
            output['segments'][segment]['regions'][region] = {'routes': []}

        for route in routes:
            dest = route.get('Destinations', [{}])[0]
            target = dest.get('TransitGatewayAttachmentId') or dest.get('CoreNetworkAttachmentId')
            output['segments'][segment]['regions'][region]['routes'].append(
                {
                    'destination': route['DestinationCidrBlock'],
                    'target': target,
                    'target_type': route.get('Type', 'unknown'),
                    'state': route.get('State', 'unknown'),
                }
            )
    return output


def parse_suricata_rule(rule_string: str) -> Dict[str, Any] | None:
    """Parse a Suricata rule string into structured format."""
    # Basic regex to parse Suricata rule format
    pattern = r'(\w+)\s+(\w+)\s+([^\s]+)\s+([^\s]+)\s+([<>-]+)\s+([^\s]+)\s+([^\s]+)\s+\(([^)]+)\)'
    match = re.match(pattern, rule_string.strip())

    if not match:
        return None

    action, protocol, src_net, src_port, direction, dst_net, dst_port, options_str = match.groups()

    # Parse options as simple key-value pairs
    conditions = {}
    rule_id = None

    # Split options by semicolon
    options = [opt.strip() for opt in options_str.split(';') if opt.strip()]

    for option in options:
        if ':' in option:
            key, value = option.split(':', 1)
            conditions[key.strip()] = value.strip()
            if key.strip() == 'sid':
                rule_id = value.strip()
        else:
            conditions[option] = True

    return {
        'rule_id': rule_id,
        'type': 'suricata',
        'action': action.lower(),
        'protocol': protocol.lower(),
        'source': {'network': src_net, 'port': src_port},
        'destination': {'network': dst_net, 'port': dst_port},
        'direction': direction,
        'conditions': conditions,
        'parsed_rule': rule_string.strip(),
    }
