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

"""AWS Network Firewall (ANFW) tools with comprehensive Infrastructure-as-Code parsing support.

This module provides comprehensive AWS Network Firewall analysis including:
- Live AWS firewall policy analysis
- Terraform configuration parsing and validation
- AWS CDK (TypeScript) configuration parsing and validation
- AWS CloudFormation template parsing and validation (YAML/JSON)
- 5-tuple flow analysis and traffic simulation
- Multi-format rule parsing (Native, Suricata, RulesSourceList)
- CloudWatch log monitoring and analysis
- Policy comparison and what-if analysis
- Security assessment and compliance checking

Supported Infrastructure-as-Code Formats:
- Terraform HCL (.tf files)
- AWS CDK TypeScript (.ts files)
- AWS CloudFormation YAML/JSON (.yml, .yaml, .json files)

Supported Rule Formats:
- Native AWS stateless rules (5-tuple matching)
- Native AWS stateful rules (connection tracking)
- Suricata rule strings (IDS/IPS format)
- RulesSourceList (domain allow/deny lists)
"""

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logger import logger
from ..utils.response_formatter import format_response


class TerraformRule(BaseModel):
    """Represents a firewall rule parsed from Terraform configuration."""

    rule_type: str = Field(..., description="Type of rule (stateless, stateful)")
    action: str = Field(..., description="Rule action (pass, drop, alert)")
    protocol: str | None = Field(None, description="Network protocol")
    source: str | None = Field(None, description="Source address/network")
    destination: str | None = Field(None, description="Destination address/network")
    source_port: str | None = Field(None, description="Source port or range")
    destination_port: str | None = Field(None, description="Destination port or range")
    priority: int | None = Field(None, description="Rule priority")
    message: str | None = Field(None, description="Rule message/description")
    sid: int | None = Field(None, description="Suricata rule ID")


class TerraformFirewallPolicy(BaseModel):
    """Represents a complete firewall policy parsed from Terraform."""

    policy_name: str = Field(..., description="Name of the firewall policy")
    stateless_default_actions: list[str] = Field(default_factory=list)
    stateless_fragment_default_actions: list[str] = Field(default_factory=list)
    stateful_default_actions: list[str] = Field(default_factory=list)
    stateless_rule_groups: list[dict] = Field(default_factory=list)
    stateful_rule_groups: list[dict] = Field(default_factory=list)
    parsed_rules: list[TerraformRule] = Field(default_factory=list)


class CdkRule(BaseModel):
    """Represents a firewall rule parsed from CDK configuration."""

    rule_type: str = Field(..., description="Type of rule (stateless, stateful)")
    rule_format: str = Field(..., description="Rule format (native, suricata)")
    action: str = Field(..., description="Rule action (pass, drop, alert)")
    protocol: str | None = Field(None, description="Network protocol")
    source: str | None = Field(None, description="Source address/network")
    destination: str | None = Field(None, description="Destination address/network")
    source_port: str | None = Field(None, description="Source port or range")
    destination_port: str | None = Field(None, description="Destination port or range")
    priority: int | None = Field(None, description="Rule priority")
    message: str | None = Field(None, description="Rule message/description")
    sid: int | None = Field(None, description="Suricata rule ID")
    rule_group_name: str | None = Field(None, description="CDK rule group name")


class CdkFirewallPolicy(BaseModel):
    """Represents a complete firewall policy parsed from CDK."""

    policy_name: str = Field(..., description="Name of the firewall policy")
    policy_type: str = Field(..., description="Type of policy (egress, eastwest)")
    stateless_default_actions: list[str] = Field(default_factory=list)
    stateless_fragment_default_actions: list[str] = Field(default_factory=list)
    stateful_default_actions: list[str] = Field(default_factory=list)
    stateless_rule_groups: list[dict] = Field(default_factory=list)
    stateful_rule_groups: list[dict] = Field(default_factory=list)
    parsed_rules: list[CdkRule] = Field(default_factory=list)
    logging_configuration: dict = Field(default_factory=dict)


class NetworkFirewallTerraformParser:
    """Parser for AWS Network Firewall Terraform configurations."""

    def __init__(self):
        """Initialize the Terraform parser."""
        self.variable_definitions = {}
        self.local_values = {}

    def parse_terraform_file(self, terraform_content: str) -> TerraformFirewallPolicy:
        """Parse Terraform content and extract Network Firewall policy configuration.

        Args:
            terraform_content: Raw Terraform configuration content

        Returns:
            TerraformFirewallPolicy with parsed configuration
        """
        try:
            # Extract variables and locals
            self._extract_variables_and_locals(terraform_content)

            # Find firewall policy resource
            policy_match = re.search(
                r'resource\s+"aws_networkfirewall_firewall_policy"\s+"([^"]+)"\s*{([^}]*(?:{[^}]*}[^}]*)*)}',
                terraform_content,
                re.MULTILINE | re.DOTALL
            )

            if not policy_match:
                raise ValueError("No aws_networkfirewall_firewall_policy resource found")

            policy_name = policy_match.group(1)
            policy_block = policy_match.group(2)

            # Parse firewall policy block
            policy = self._parse_firewall_policy_block(policy_name, policy_block)

            # Parse rule groups
            stateless_rules = self._parse_stateless_rule_groups(terraform_content)
            stateful_rules = self._parse_stateful_rule_groups(terraform_content)

            policy.parsed_rules.extend(stateless_rules)
            policy.parsed_rules.extend(stateful_rules)

            return policy

        except Exception as e:
            logger.error(f"Error parsing Terraform content: {str(e)}")
            raise

    def _extract_variables_and_locals(self, content: str) -> None:
        """Extract variable and local value definitions."""

        # Extract variables
        var_pattern = r'variable\s+"([^"]+)"\s*{[^}]*default\s*=\s*"([^"]*)"'
        for match in re.finditer(var_pattern, content):
            var_name, default_value = match.groups()
            self.variable_definitions[var_name] = default_value

        # Extract locals
        locals_pattern = r"locals\s*{([^}]*)}"
        locals_match = re.search(locals_pattern, content, re.DOTALL)
        if locals_match:
            locals_block = locals_match.group(1)
            local_assignments = re.findall(r'(\w+)\s*=\s*"([^"]*)"', locals_block)
            for name, value in local_assignments:
                self.local_values[name] = value

    def _parse_firewall_policy_block(self, policy_name: str, policy_block: str) -> TerraformFirewallPolicy:
        """Parse the main firewall policy block."""

        policy = TerraformFirewallPolicy(policy_name=policy_name)

        # Extract firewall_policy sub-block
        fp_match = re.search(r"firewall_policy\s*{([^}]*(?:{[^}]*}[^}]*)*)}", policy_block, re.DOTALL)
        if fp_match:
            fp_content = fp_match.group(1)

            # Parse default actions
            policy.stateless_default_actions = self._extract_list_values(
                fp_content, "stateless_default_actions"
            )
            policy.stateless_fragment_default_actions = self._extract_list_values(
                fp_content, "stateless_fragment_default_actions"
            )
            policy.stateful_default_actions = self._extract_list_values(
                fp_content, "stateful_default_actions"
            )

            # Parse rule group references
            policy.stateless_rule_groups = self._parse_rule_group_references(
                fp_content, "stateless_rule_group_reference"
            )
            policy.stateful_rule_groups = self._parse_rule_group_references(
                fp_content, "stateful_rule_group_reference"
            )

        return policy

    def _extract_list_values(self, content: str, field_name: str) -> list[str]:
        """Extract list values from Terraform configuration."""

        pattern = rf"{field_name}\s*=\s*\[(.*?)\]"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            list_content = match.group(1)
            # Extract quoted strings
            values = re.findall(r'"([^"]*)"', list_content)
            return values

        return []

    def _parse_rule_group_references(self, content: str, block_name: str) -> list[dict]:
        """Parse rule group reference blocks."""

        references = []
        pattern = rf"{block_name}\s*{{([^}}]*)}}"

        for match in re.finditer(pattern, content):
            ref_content = match.group(1)
            ref = {}

            # Extract priority
            priority_match = re.search(r"priority\s*=\s*(\d+)", ref_content)
            if priority_match:
                ref["priority"] = int(priority_match.group(1))

            # Extract resource_arn reference
            arn_match = re.search(r"resource_arn\s*=\s*([^\\n]+)", ref_content)
            if arn_match:
                ref["resource_arn"] = arn_match.group(1).strip()

            references.append(ref)

        return references

    def _parse_stateless_rule_groups(self, content: str) -> list[TerraformRule]:
        """Parse stateless rule groups from Terraform configuration."""

        rules = []

        # Find stateless rule group resources
        pattern = r'resource\s+"aws_networkfirewall_rule_group"\s+"([^"]+)"\s*{([^}]*(?:{[^}]*}[^}]*)*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*(?:{[^}]*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*}[^}]*)*)})'

        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            rule_group_name = match.group(1)
            rule_group_content = match.group(2)

            # Check if it's stateless
            if 'type = "STATELESS"' in rule_group_content:
                stateless_rules = self._parse_stateless_rules_block(rule_group_content, rule_group_name)
                rules.extend(stateless_rules)

        return rules

    def _parse_stateless_rules_block(self, content: str, rule_group_name: str) -> list[TerraformRule]:
        """Parse individual stateless rules."""

        rules = []

        # Find stateless_rule blocks
        rule_pattern = r"stateless_rule\s*{([^}]*(?:{[^}]*}[^}]*)*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*)})"

        for rule_match in re.finditer(rule_pattern, content, re.DOTALL):
            rule_content = rule_match.group(1)

            # Extract priority
            priority_match = re.search(r"priority\s*=\s*(\d+)", rule_content)
            priority = int(priority_match.group(1)) if priority_match else None

            # Extract rule definition
            rule_def_match = re.search(r"rule_definition\s*{([^}]*(?:{[^}]*}[^}]*)*)}", rule_content, re.DOTALL)
            if rule_def_match:
                rule_def_content = rule_def_match.group(1)

                # Extract actions
                actions = self._extract_list_values(rule_def_content, "actions")
                action = actions[0] if actions else "unknown"

                # Extract match attributes
                match_attrs = self._parse_stateless_match_attributes(rule_def_content)

                rule = TerraformRule(
                    rule_type="stateless",
                    action=action.replace("aws:", ""),
                    priority=priority,
                    protocol=match_attrs.get("protocol"),
                    source=match_attrs.get("source"),
                    destination=match_attrs.get("destination"),
                    source_port=match_attrs.get("source_port"),
                    destination_port=match_attrs.get("destination_port"),
                    message=f"Stateless rule from {rule_group_name}"
                )

                rules.append(rule)

        return rules

    def _parse_stateless_match_attributes(self, content: str) -> dict[str, str]:
        """Parse match attributes for stateless rules."""

        attrs = {}

        # Extract protocols (convert from number to name)
        protocol_match = re.search(r"protocols\s*=\s*\[(\d+)\]", content)
        if protocol_match:
            proto_num = int(protocol_match.group(1))
            protocol_map = {6: "TCP", 17: "UDP", 1: "ICMP"}
            attrs["protocol"] = protocol_map.get(proto_num, f"Protocol-{proto_num}")

        # Extract source address
        source_match = re.search(r'source\s*{[^}]*address_definition\s*=\s*"([^"]*)"', content)
        if source_match:
            attrs["source"] = source_match.group(1)

        # Extract destination address
        dest_match = re.search(r'destination\s*{[^}]*address_definition\s*=\s*"([^"]*)"', content)
        if dest_match:
            attrs["destination"] = dest_match.group(1)

        # Extract source port
        src_port_match = re.search(r"source_port\s*{[^}]*from_port\s*=\s*(\d+)[^}]*to_port\s*=\s*(\d+)", content)
        if src_port_match:
            from_port, to_port = src_port_match.groups()
            if from_port == to_port:
                attrs["source_port"] = from_port
            else:
                attrs["source_port"] = f"{from_port}-{to_port}"

        # Extract destination port
        dest_port_match = re.search(r"destination_port\s*{[^}]*from_port\s*=\s*(\d+)[^}]*to_port\s*=\s*(\d+)", content)
        if dest_port_match:
            from_port, to_port = dest_port_match.groups()
            if from_port == to_port:
                attrs["destination_port"] = from_port
            else:
                attrs["destination_port"] = f"{from_port}-{to_port}"

        return attrs

    def _parse_stateful_rule_groups(self, content: str) -> list[TerraformRule]:
        """Parse stateful rule groups from Terraform configuration."""

        rules = []

        # Find stateful rule group resources
        pattern = r'resource\s+"aws_networkfirewall_rule_group"\s+"([^"]+)"\s*{([^}]*(?:{[^}]*}[^}]*)*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*(?:{[^}]*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*}[^}]*)*)})'

        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            rule_group_name = match.group(1)
            rule_group_content = match.group(2)

            # Check if it's stateful
            if 'type = "STATEFUL"' in rule_group_content:
                stateful_rules = self._parse_stateful_rules_block(rule_group_content, rule_group_name)
                rules.extend(stateful_rules)

        return rules

    def _parse_stateful_rules_block(self, content: str, rule_group_name: str) -> list[TerraformRule]:
        """Parse individual stateful rules (Suricata format)."""

        rules = []

        # Find rules_string blocks
        rules_string_pattern = r"rules_string\s*=\s*<<EOF(.*?)EOF"

        for match in re.finditer(rules_string_pattern, content, re.DOTALL):
            rules_text = match.group(1).strip()

            # Parse individual Suricata rules
            for line in rules_text.split("\\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                suricata_rule = self._parse_suricata_rule_line(line, rule_group_name)
                if suricata_rule:
                    rules.append(suricata_rule)

        return rules

    def _parse_suricata_rule_line(self, rule_line: str, rule_group_name: str) -> TerraformRule | None:
        """Parse a single Suricata rule line."""

        # Basic Suricata rule pattern: action protocol src_ip src_port -> dst_ip dst_port (options)
        pattern = r"(\\w+)\\s+(\\w+)\\s+([\\w\\d\\./\\$_]+)\\s+([\\w\\d\\-,]+)\\s*->\\s*([\\w\\d\\./\\$_]+)\\s+([\\w\\d\\-,]+)\\s*\\((.*)\\)"

        match = re.match(pattern, rule_line.strip())
        if not match:
            return None

        action, protocol, src_ip, src_port, dst_ip, dst_port, options = match.groups()

        # Extract message and sid from options
        message = None
        sid = None

        msg_match = re.search(r'msg:"([^"]*)"', options)
        if msg_match:
            message = msg_match.group(1)

        sid_match = re.search(r"sid:(\\d+)", options)
        if sid_match:
            sid = int(sid_match.group(1))

        return TerraformRule(
            rule_type="stateful",
            action=action,
            protocol=protocol.upper(),
            source=src_ip,
            destination=dst_ip,
            source_port=src_port if src_port != "any" else None,
            destination_port=dst_port if dst_port != "any" else None,
            message=message or f"Stateful rule from {rule_group_name}",
            sid=sid
        )


class NetworkFirewallCdkParser:
    """Parser for AWS Network Firewall CDK configurations."""

    def __init__(self):
        """Initialize the CDK parser."""
        pass

    def parse_cdk_file(self, cdk_content: str) -> CdkFirewallPolicy:
        """Parse CDK TypeScript content and extract Network Firewall policy configuration.

        Args:
            cdk_content: Raw CDK TypeScript configuration content

        Returns:
            CdkFirewallPolicy with parsed configuration
        """
        try:
            # Determine policy type by looking for method names
            policy_type = "unknown"
            policy_name = "unknown"

            if "createEgressInspectionFirewallPolicy" in cdk_content:
                policy_type = "egress"
                policy_name = "egress-inspection-policy"
            elif "createInspectionVPCFirewallPolicy" in cdk_content:
                policy_type = "eastwest"
                policy_name = "eastwest-policy"

            # Create policy object
            policy = CdkFirewallPolicy(
                policy_name=policy_name,
                policy_type=policy_type
            )

            # Parse firewall policy configurations
            if policy_type == "egress":
                self._parse_egress_policy(cdk_content, policy)
            elif policy_type == "eastwest":
                self._parse_eastwest_policy(cdk_content, policy)

            # Parse logging configuration
            policy.logging_configuration = self._parse_logging_configuration(cdk_content)

            return policy

        except Exception as e:
            raise ValueError(f"Error parsing CDK content: {str(e)}")

    def _parse_egress_policy(self, content: str, policy: CdkFirewallPolicy) -> None:
        """Parse egress inspection firewall policy from CDK."""

        # Extract stateless/stateful default actions from policy definition
        policy_match = re.search(r"firewallPolicy:\s*{([^}]*(?:{[^}]*}[^}]*)*)}", content, re.DOTALL)
        if policy_match:
            policy_block = policy_match.group(1)

            # Parse default actions
            policy.stateless_default_actions = self._extract_cdk_array_values(
                policy_block, "statelessDefaultActions"
            )
            policy.stateless_fragment_default_actions = self._extract_cdk_array_values(
                policy_block, "statelessFragmentDefaultActions"
            )
            policy.stateful_default_actions = self._extract_cdk_array_values(
                policy_block, "statefulDefaultActions"
            )

        # Parse rule groups
        self._parse_cdk_rule_groups(content, policy)

    def _parse_eastwest_policy(self, content: str, policy: CdkFirewallPolicy) -> None:
        """Parse east-west inspection firewall policy from CDK."""

        # Similar to egress but with different rule groups
        policy_match = re.search(r"firewallPolicy:\s*{([^}]*(?:{[^}]*}[^}]*)*)}", content, re.DOTALL)
        if policy_match:
            policy_block = policy_match.group(1)

            # Parse default actions
            policy.stateless_default_actions = self._extract_cdk_array_values(
                policy_block, "statelessDefaultActions"
            )
            policy.stateless_fragment_default_actions = self._extract_cdk_array_values(
                policy_block, "statelessFragmentDefaultActions"
            )
            policy.stateful_default_actions = self._extract_cdk_array_values(
                policy_block, "statefulDefaultActions"
            )

        # Parse rule groups (east-west has fewer rule groups)
        self._parse_cdk_rule_groups(content, policy)

    def _extract_cdk_array_values(self, content: str, field_name: str) -> list[str]:
        """Extract array values from CDK TypeScript configuration."""

        pattern = rf"{field_name}:\s*\[(.*?)\]"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            array_content = match.group(1)
            # Extract quoted strings
            values = re.findall(r'"([^"]*)"', array_content)
            return values

        return []

    def _parse_cdk_rule_groups(self, content: str, policy: CdkFirewallPolicy) -> None:
        """Parse both stateless and stateful rule groups from CDK."""

        # Parse stateless rule groups (native format)
        stateless_rules = self._parse_cdk_stateless_rules(content)
        policy.parsed_rules.extend(stateless_rules)

        # Parse stateful rule groups (Suricata format)
        stateful_rules = self._parse_cdk_stateful_rules(content)
        policy.parsed_rules.extend(stateful_rules)

    def _parse_cdk_stateless_rules(self, content: str) -> list[CdkRule]:
        """Parse stateless rules in CDK native format."""

        rules = []

        # Find CfnRuleGroup with type STATELESS
        stateless_pattern = r'new nf\.CfnRuleGroup\([^,]+,\s*"([^"]+)",\s*{([^}]*(?:{[^}]*}[^}]*)*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*(?:{[^}]*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*}[^}]*)*)})'

        for match in re.finditer(stateless_pattern, content, re.DOTALL):
            rule_group_name = match.group(1)
            rule_group_content = match.group(2)

            # Check if it's stateless
            if 'type: "STATELESS"' in rule_group_content:
                # Parse stateless rules from the native CDK format
                stateless_rules_content = self._extract_stateless_rules_content(rule_group_content)

                for rule_data in stateless_rules_content:
                    rule = CdkRule(
                        rule_type="stateless",
                        rule_format="native",
                        action=rule_data.get("action", "unknown"),
                        protocol=rule_data.get("protocol"),
                        source=rule_data.get("source"),
                        destination=rule_data.get("destination"),
                        source_port=rule_data.get("source_port"),
                        destination_port=rule_data.get("destination_port"),
                        priority=rule_data.get("priority"),
                        message=f"Stateless rule from {rule_group_name}",
                        rule_group_name=rule_group_name
                    )
                    rules.append(rule)

        return rules

    def _extract_stateless_rules_content(self, content: str) -> list[dict]:
        """Extract stateless rule details from CDK native format."""

        rules = []

        # Look for statelessRules array
        rules_pattern = r"statelessRules:\s*\[([^\]]*(?:\[[^\]]*\][^\]]*)*)\]"
        rules_match = re.search(rules_pattern, content, re.DOTALL)

        if rules_match:
            rules_content = rules_match.group(1)

            # Parse each rule object
            rule_objects = re.finditer(r"{([^}]*(?:{[^}]*}[^}]*)*)}", rules_content)

            for rule_obj in rule_objects:
                rule_text = rule_obj.group(1)

                rule_data = {}

                # Extract priority
                priority_match = re.search(r"priority:\s*(\d+)", rule_text)
                if priority_match:
                    rule_data["priority"] = int(priority_match.group(1))

                # Extract actions
                actions_match = re.search(r'actions:\s*\["([^"]*)"', rule_text)
                if actions_match:
                    rule_data["action"] = actions_match.group(1).replace("aws:", "")

                # Parse match attributes
                match_attrs = self._parse_cdk_match_attributes(rule_text)
                rule_data.update(match_attrs)

                rules.append(rule_data)

        return rules

    def _parse_cdk_match_attributes(self, content: str) -> dict[str, str]:
        """Parse match attributes from CDK stateless rule."""

        attrs = {}

        # Extract protocols
        protocols_match = re.search(r"protocols:\s*\[(\d+)\]", content)
        if protocols_match:
            proto_num = int(protocols_match.group(1))
            protocol_map = {6: "TCP", 17: "UDP", 1: "ICMP"}
            attrs["protocol"] = protocol_map.get(proto_num, f"Protocol-{proto_num}")

        # Extract sources
        sources_match = re.search(r'sources:\s*\[.*?addressDefinition:\s*"([^"]*)"', content)
        if sources_match:
            attrs["source"] = sources_match.group(1)

        # Extract destinations
        destinations_match = re.search(r'destinations:\s*\[.*?addressDefinition:\s*"([^"]*)"', content)
        if destinations_match:
            attrs["destination"] = destinations_match.group(1)

        # Extract source ports
        src_ports_match = re.search(r"sourcePorts:\s*\[.*?fromPort:\s*(\d+),\s*toPort:\s*(\d+)", content)
        if src_ports_match:
            from_port, to_port = src_ports_match.groups()
            if from_port == to_port:
                attrs["source_port"] = from_port
            else:
                attrs["source_port"] = f"{from_port}-{to_port}"

        # Extract destination ports
        dest_ports_match = re.search(r"destinationPorts:\s*\[.*?fromPort:\s*(\d+),\s*toPort:\s*(\d+)", content)
        if dest_ports_match:
            from_port, to_port = dest_ports_match.groups()
            if from_port == to_port:
                attrs["destination_port"] = from_port
            else:
                attrs["destination_port"] = f"{from_port}-{to_port}"

        return attrs

    def _parse_cdk_stateful_rules(self, content: str) -> list[CdkRule]:
        """Parse stateful rules in Suricata format from CDK."""

        rules = []

        # Find CfnRuleGroup with type STATEFUL
        stateful_pattern = r'new nf\.CfnRuleGroup\([^,]+,\s*"([^"]+)",\s*{([^}]*(?:{[^}]*}[^}]*)*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*(?:{[^}]*(?:{[^}]*(?:{[^}]*}[^}]*)*}[^}]*)*}[^}]*)*)})'

        for match in re.finditer(stateful_pattern, content, re.DOTALL):
            rule_group_name = match.group(1)
            rule_group_content = match.group(2)

            # Check if it's stateful
            if 'type: "STATEFUL"' in rule_group_content:
                # Parse Suricata rules from rulesString
                suricata_rules = self._parse_cdk_suricata_rules(rule_group_content, rule_group_name)
                rules.extend(suricata_rules)

        return rules

    def _parse_cdk_suricata_rules(self, content: str, rule_group_name: str) -> list[CdkRule]:
        """Parse Suricata rules from CDK rulesString."""

        rules = []

        # Find rulesString with template literal
        rules_string_pattern = r"rulesString:\s*`([^`]*)`"

        for match in re.finditer(rules_string_pattern, content, re.DOTALL):
            rules_text = match.group(1).strip()

            # Parse individual Suricata rules
            for line in rules_text.split("\\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                suricata_rule = self._parse_cdk_suricata_rule_line(line, rule_group_name)
                if suricata_rule:
                    rules.append(suricata_rule)

        return rules

    def _parse_cdk_suricata_rule_line(self, rule_line: str, rule_group_name: str) -> CdkRule | None:
        """Parse a single Suricata rule line from CDK."""

        # Basic Suricata rule pattern: action protocol src_ip src_port direction dst_ip dst_port (options)
        pattern = r"(\\w+)\\s+(\\w+)\\s+([\\w\\d\\./\\$_]+)\\s+([\\w\\d\\-,]+)\\s*([<>-]+)\\s*([\\w\\d\\./\\$_]+)\\s+([\\w\\d\\-,]+)\\s*\\((.*)\\)"

        match = re.match(pattern, rule_line.strip())
        if not match:
            return None

        action, protocol, src_ip, src_port, direction, dst_ip, dst_port, options = match.groups()

        # Extract message and sid from options
        message = None
        sid = None

        msg_match = re.search(r'msg:\\s*"([^"]*)"', options)
        if msg_match:
            message = msg_match.group(1)

        sid_match = re.search(r"sid:\\s*(\\d+)", options)
        if sid_match:
            sid = int(sid_match.group(1))

        return CdkRule(
            rule_type="stateful",
            rule_format="suricata",
            action=action,
            protocol=protocol.upper(),
            source=src_ip,
            destination=dst_ip,
            source_port=src_port if src_port != "any" else None,
            destination_port=dst_port if dst_port != "any" else None,
            message=message or f"Stateful rule from {rule_group_name}",
            sid=sid,
            rule_group_name=rule_group_name
        )

    def _parse_logging_configuration(self, content: str) -> dict[str, Any]:
        """Parse CloudWatch logging configuration from CDK."""

        logging_config = {
            "flow_logs": False,
            "alert_logs": False,
            "log_groups": []
        }

        # Look for LogGroup creation
        flow_logs_match = re.search(r'new logs\.LogGroup\([^,]+,\s*"([^"]*LogsGroup)"', content)
        if flow_logs_match:
            logging_config["flow_logs"] = True
            logging_config["log_groups"].append("flow")

        alert_logs_match = re.search(r'new logs\.LogGroup\([^,]+,\s*"([^"]*AlertLogsGroup)"', content)
        if alert_logs_match:
            logging_config["alert_logs"] = True
            logging_config["log_groups"].append("alert")

        return logging_config


class CloudFormationRule(BaseModel):
    """Represents a firewall rule parsed from CloudFormation template."""

    rule_type: str = Field(..., description="Type of rule (stateless, stateful)")
    rule_format: str = Field(..., description="Rule format (native, suricata, rules_source_list)")
    action: str = Field(..., description="Rule action (pass, drop, alert)")
    protocol: str | None = Field(None, description="Network protocol")
    source: str | None = Field(None, description="Source address/network")
    destination: str | None = Field(None, description="Destination address/network")
    source_port: str | None = Field(None, description="Source port or range")
    destination_port: str | None = Field(None, description="Destination port or range")
    priority: int | None = Field(None, description="Rule priority")
    message: str | None = Field(None, description="Rule message/description")
    sid: int | None = Field(None, description="Suricata rule ID")
    rule_group_name: str | None = Field(None, description="CloudFormation rule group name")
    target_types: list[str] | None = Field(None, description="Target types for rules source list")
    targets: list[str] | None = Field(None, description="Targets for rules source list")


class CloudFormationFirewallPolicy(BaseModel):
    """Represents a complete firewall policy parsed from CloudFormation."""

    policy_name: str = Field(..., description="Name of the firewall policy")
    template_format_version: str = Field(default="2010-09-09", description="CloudFormation template version")
    description: str | None = Field(None, description="Template description")
    stateless_default_actions: list[str] = Field(default_factory=list)
    stateless_fragment_default_actions: list[str] = Field(default_factory=list)
    stateful_default_actions: list[str] = Field(default_factory=list)
    stateful_engine_options: dict = Field(default_factory=dict)
    stateless_rule_groups: list[dict] = Field(default_factory=list)
    stateful_rule_groups: list[dict] = Field(default_factory=list)
    parsed_rules: list[CloudFormationRule] = Field(default_factory=list)


class NetworkFirewallCloudFormationParser:
    """Parser for AWS Network Firewall CloudFormation templates."""

    def __init__(self):
        """Initialize the CloudFormation parser."""
        pass

    def parse_cloudformation_template(self, cf_content: str) -> CloudFormationFirewallPolicy:
        """Parse CloudFormation YAML/JSON content and extract Network Firewall policy configuration.

        Args:
            cf_content: Raw CloudFormation template content (YAML or JSON)

        Returns:
            CloudFormationFirewallPolicy with parsed configuration
        """
        try:
            import json

            import yaml

            # Try to parse as YAML first, then JSON
            try:
                template = yaml.safe_load(cf_content)
            except yaml.YAMLError:
                try:
                    template = json.loads(cf_content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Unable to parse as YAML or JSON: {str(e)}")

            # Extract template metadata
            template_version = template.get("AWSTemplateFormatVersion", "2010-09-09")
            description = template.get("Description", "")
            resources = template.get("Resources", {})

            # Find firewall policy resource
            firewall_policy_resource = None
            policy_name = "unknown"

            for resource_name, resource_data in resources.items():
                if resource_data.get("Type") == "AWS::NetworkFirewall::FirewallPolicy":
                    firewall_policy_resource = resource_data
                    policy_name = resource_data.get("Properties", {}).get("FirewallPolicyName", resource_name)
                    break

            if not firewall_policy_resource:
                raise ValueError("No AWS::NetworkFirewall::FirewallPolicy resource found")

            # Create policy object
            policy = CloudFormationFirewallPolicy(
                policy_name=policy_name,
                template_format_version=template_version,
                description=description
            )

            # Parse firewall policy properties
            self._parse_firewall_policy_properties(firewall_policy_resource, policy)

            # Parse rule groups
            self._parse_cloudformation_rule_groups(resources, policy)

            return policy

        except Exception as e:
            raise ValueError(f"Error parsing CloudFormation template: {str(e)}")

    def _parse_firewall_policy_properties(self, policy_resource: dict, policy: CloudFormationFirewallPolicy) -> None:
        """Parse firewall policy properties from CloudFormation resource."""

        properties = policy_resource.get("Properties", {})
        firewall_policy = properties.get("FirewallPolicy", {})

        # Parse default actions
        policy.stateless_default_actions = firewall_policy.get("StatelessDefaultActions", [])
        policy.stateless_fragment_default_actions = firewall_policy.get("StatelessFragmentDefaultActions", [])
        policy.stateful_default_actions = firewall_policy.get("StatefulDefaultActions", [])

        # Parse engine options
        policy.stateful_engine_options = firewall_policy.get("StatefulEngineOptions", {})

        # Parse rule group references
        policy.stateless_rule_groups = firewall_policy.get("StatelessRuleGroupReferences", [])
        policy.stateful_rule_groups = firewall_policy.get("StatefulRuleGroupReferences", [])

    def _parse_cloudformation_rule_groups(self, resources: dict, policy: CloudFormationFirewallPolicy) -> None:
        """Parse rule groups from CloudFormation resources."""

        for resource_name, resource_data in resources.items():
            if resource_data.get("Type") == "AWS::NetworkFirewall::RuleGroup":
                rule_group_properties = resource_data.get("Properties", {})
                rule_group_type = rule_group_properties.get("Type", "").upper()
                rule_group_name = rule_group_properties.get("RuleGroupName", resource_name)

                if rule_group_type == "STATELESS":
                    stateless_rules = self._parse_cf_stateless_rules(rule_group_properties, rule_group_name)
                    policy.parsed_rules.extend(stateless_rules)
                elif rule_group_type == "STATEFUL":
                    stateful_rules = self._parse_cf_stateful_rules(rule_group_properties, rule_group_name)
                    policy.parsed_rules.extend(stateful_rules)

    def _parse_cf_stateless_rules(self, rule_group_props: dict, rule_group_name: str) -> list[CloudFormationRule]:
        """Parse stateless rules from CloudFormation rule group."""

        rules = []
        rule_group = rule_group_props.get("RuleGroup", {})
        rules_source = rule_group.get("RulesSource", {})
        stateless_rules_and_actions = rules_source.get("StatelessRulesAndCustomActions", {})
        stateless_rules = stateless_rules_and_actions.get("StatelessRules", [])

        for rule_data in stateless_rules:
            priority = rule_data.get("Priority")
            rule_definition = rule_data.get("RuleDefinition", {})

            # Extract actions
            actions = rule_definition.get("Actions", [])
            action = actions[0].replace("aws:", "") if actions else "unknown"

            # Extract match attributes
            match_attrs = rule_definition.get("MatchAttributes", {})

            # Parse protocols
            protocols = match_attrs.get("Protocols", [])
            protocol = None
            if protocols:
                protocol_map = {6: "TCP", 17: "UDP", 1: "ICMP"}
                protocol = protocol_map.get(protocols[0], f"Protocol-{protocols[0]}")

            # Parse sources and destinations
            sources = match_attrs.get("Sources", [])
            destinations = match_attrs.get("Destinations", [])

            source = sources[0].get("AddressDefinition") if sources else None
            destination = destinations[0].get("AddressDefinition") if destinations else None

            # Parse port ranges
            source_ports = match_attrs.get("SourcePorts", [])
            dest_ports = match_attrs.get("DestinationPorts", [])

            source_port = None
            if source_ports:
                from_port = source_ports[0].get("FromPort")
                to_port = source_ports[0].get("ToPort")
                if from_port == to_port:
                    source_port = str(from_port)
                else:
                    source_port = f"{from_port}-{to_port}"

            destination_port = None
            if dest_ports:
                from_port = dest_ports[0].get("FromPort")
                to_port = dest_ports[0].get("ToPort")
                if from_port == to_port:
                    destination_port = str(from_port)
                else:
                    destination_port = f"{from_port}-{to_port}"

            rule = CloudFormationRule(
                rule_type="stateless",
                rule_format="native",
                action=action,
                protocol=protocol,
                source=source,
                destination=destination,
                source_port=source_port,
                destination_port=destination_port,
                priority=priority,
                message=f"Stateless rule from {rule_group_name}",
                rule_group_name=rule_group_name
            )

            rules.append(rule)

        return rules

    def _parse_cf_stateful_rules(self, rule_group_props: dict, rule_group_name: str) -> list[CloudFormationRule]:
        """Parse stateful rules from CloudFormation rule group."""

        rules = []
        rule_group = rule_group_props.get("RuleGroup", {})
        rules_source = rule_group.get("RulesSource", {})

        # Handle RulesString (Suricata format)
        if "RulesString" in rules_source:
            rules_string = rules_source["RulesString"]
            suricata_rules = self._parse_cf_suricata_rules(rules_string, rule_group_name)
            rules.extend(suricata_rules)

        # Handle RulesSourceList (domain allowlist/denylist)
        if "RulesSourceList" in rules_source:
            rules_source_list = rules_source["RulesSourceList"]
            list_rules = self._parse_cf_rules_source_list(rules_source_list, rule_group_name)
            rules.extend(list_rules)

        # Handle StatefulRules (native CloudFormation format)
        if "StatefulRules" in rules_source:
            stateful_rules = rules_source["StatefulRules"]
            native_rules = self._parse_cf_native_stateful_rules(stateful_rules, rule_group_name)
            rules.extend(native_rules)

        return rules

    def _parse_cf_suricata_rules(self, rules_string: str, rule_group_name: str) -> list[CloudFormationRule]:
        """Parse Suricata rules from CloudFormation RulesString."""

        rules = []

        # Split rules by lines and parse each one
        for line in rules_string.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse Suricata rule format
            suricata_rule = self._parse_cf_suricata_rule_line(line, rule_group_name)
            if suricata_rule:
                rules.append(suricata_rule)

        return rules

    def _parse_cf_suricata_rule_line(self, rule_line: str, rule_group_name: str) -> CloudFormationRule | None:
        """Parse a single Suricata rule line from CloudFormation."""

        # Basic Suricata rule pattern
        pattern = r"(\w+)\s+(\w+)\s+([\w\d\./\$_]+)\s+([\w\d\-,]+)\s*([<>-]+)\s*([\w\d\./\$_]+)\s+([\w\d\-,]+)\s*\((.*)\)"

        match = re.match(pattern, rule_line.strip())
        if not match:
            return None

        action, protocol, src_ip, src_port, direction, dst_ip, dst_port, options = match.groups()

        # Extract message and sid from options
        message = None
        sid = None

        msg_match = re.search(r'msg:\s*"([^"]*)"', options)
        if msg_match:
            message = msg_match.group(1)

        sid_match = re.search(r"sid:\s*(\d+)", options)
        if sid_match:
            sid = int(sid_match.group(1))

        return CloudFormationRule(
            rule_type="stateful",
            rule_format="suricata",
            action=action,
            protocol=protocol.upper(),
            source=src_ip,
            destination=dst_ip,
            source_port=src_port if src_port != "any" else None,
            destination_port=dst_port if dst_port != "any" else None,
            message=message or f"Stateful rule from {rule_group_name}",
            sid=sid,
            rule_group_name=rule_group_name
        )

    def _parse_cf_rules_source_list(self, rules_source_list: dict, rule_group_name: str) -> list[CloudFormationRule]:
        """Parse RulesSourceList (domain allowlist/denylist) from CloudFormation."""

        rules = []

        generated_rules_type = rules_source_list.get("GeneratedRulesType", "ALLOWLIST")
        target_types = rules_source_list.get("TargetTypes", [])
        targets = rules_source_list.get("Targets", [])

        action = "pass" if generated_rules_type == "ALLOWLIST" else "drop"

        for target in targets:
            for target_type in target_types:
                rule = CloudFormationRule(
                    rule_type="stateful",
                    rule_format="rules_source_list",
                    action=action,
                    protocol="ANY" if target_type == "TLS_SNI" else "HTTP",
                    source="$HOME_NET",
                    destination="$EXTERNAL_NET",
                    destination_port="443" if target_type == "TLS_SNI" else "80",
                    message=f"{generated_rules_type} for {target_type}: {target}",
                    rule_group_name=rule_group_name,
                    target_types=target_types,
                    targets=[target]
                )
                rules.append(rule)

        return rules

    def _parse_cf_native_stateful_rules(self, stateful_rules: list[dict], rule_group_name: str) -> list[CloudFormationRule]:
        """Parse native CloudFormation StatefulRules format."""

        rules = []

        for rule_data in stateful_rules:
            action = rule_data.get("Action", "pass")
            header = rule_data.get("Header", {})
            rule_options = rule_data.get("RuleOptions", [])

            # Extract header information
            protocol = header.get("Protocol", "ANY")
            source = header.get("Source", "ANY")
            destination = header.get("Destination", "ANY")
            source_port = header.get("SourcePort", "ANY")
            destination_port = header.get("DestinationPort", "ANY")
            direction = header.get("Direction", "FORWARD")

            # Build message from rule options
            message_parts = []
            for option in rule_options:
                keyword = option.get("Keyword", "")
                settings = option.get("Settings", [])
                if keyword and settings:
                    message_parts.append(f"{keyword}: {', '.join(settings)}")

            message = "; ".join(message_parts) if message_parts else f"Native stateful rule from {rule_group_name}"

            rule = CloudFormationRule(
                rule_type="stateful",
                rule_format="native",
                action=action.lower(),
                protocol=protocol,
                source=source,
                destination=destination,
                source_port=source_port if source_port != "ANY" else None,
                destination_port=destination_port if destination_port != "ANY" else None,
                message=message,
                rule_group_name=rule_group_name
            )

            rules.append(rule)

        return rules


class NetworkFirewallTools:
    """Comprehensive AWS Network Firewall analysis tools with Terraform, CDK, and CloudFormation support."""

    def __init__(self):
        """Initialize Network Firewall tools."""
        self.terraform_parser = NetworkFirewallTerraformParser()
        self.cdk_parser = NetworkFirewallCdkParser()
        self.cloudformation_parser = NetworkFirewallCloudFormationParser()

    def analyze_terraform_policy(
        self,
        terraform_content: str,
        compare_with_aws: str | None = None
    ) -> dict[str, Any]:
        """Analyze Terraform Network Firewall configuration.

        Args:
            terraform_content: Raw Terraform configuration content
            compare_with_aws: Optional AWS firewall name to compare against

        Returns:
            Comprehensive analysis of the Terraform policy
        """
        try:
            # Parse Terraform configuration
            tf_policy = self.terraform_parser.parse_terraform_file(terraform_content)

            # Analyze traffic behavior
            traffic_analysis = self._analyze_terraform_traffic_behavior(tf_policy)

            # Security assessment
            security_assessment = self._assess_terraform_security(tf_policy)

            result = {
                "terraform_analysis": {
                    "policy_name": tf_policy.policy_name,
                    "stateless_config": {
                        "default_actions": tf_policy.stateless_default_actions,
                        "fragment_actions": tf_policy.stateless_fragment_default_actions,
                        "rule_groups": len(tf_policy.stateless_rule_groups)
                    },
                    "stateful_config": {
                        "default_actions": tf_policy.stateful_default_actions,
                        "rule_groups": len(tf_policy.stateful_rule_groups)
                    },
                    "total_rules": len(tf_policy.parsed_rules),
                    "rules_by_type": {
                        "stateless": len([r for r in tf_policy.parsed_rules if r.rule_type == "stateless"]),
                        "stateful": len([r for r in tf_policy.parsed_rules if r.rule_type == "stateful"])
                    }
                },
                "traffic_analysis": traffic_analysis,
                "security_assessment": security_assessment,
                "parsed_rules": [rule.dict() for rule in tf_policy.parsed_rules]
            }

            # Compare with AWS if requested
            if compare_with_aws:
                aws_comparison = self._compare_terraform_with_aws(tf_policy, compare_with_aws)
                result["aws_comparison"] = aws_comparison

            return format_response("success", "Terraform policy analyzed successfully", result)

        except Exception as e:
            logger.error(f"Error analyzing Terraform policy: {str(e)}")
            return format_response("error", f"Failed to analyze Terraform policy: {str(e)}")

    def _analyze_terraform_traffic_behavior(self, policy: TerraformFirewallPolicy) -> dict[str, Any]:
        """Analyze traffic behavior from Terraform policy."""

        analysis = {
            "policy_type": "unknown",
            "allowed_traffic": [],
            "blocked_traffic": [],
            "security_posture": "unknown"
        }

        # Determine overall policy behavior
        if "aws:forward_to_sfe" in policy.stateless_default_actions:
            if "aws:drop_strict" in policy.stateful_default_actions:
                analysis["policy_type"] = "restrictive_with_exceptions"
                analysis["security_posture"] = "default_deny"
            else:
                analysis["policy_type"] = "permissive"
                analysis["security_posture"] = "default_allow"

        # Analyze rules for allowed traffic
        for rule in policy.parsed_rules:
            if rule.action in ["pass", "allow"]:
                traffic_desc = self._describe_traffic_rule(rule)
                analysis["allowed_traffic"].append(traffic_desc)
            elif rule.action in ["drop", "reject", "alert"]:
                traffic_desc = self._describe_traffic_rule(rule)
                analysis["blocked_traffic"].append(traffic_desc)

        return analysis

    def _describe_traffic_rule(self, rule: TerraformRule) -> dict[str, str]:
        """Create human-readable description of a traffic rule."""

        protocol = rule.protocol or "any protocol"
        source = rule.source or "any source"
        destination = rule.destination or "any destination"
        src_port = f":{rule.source_port}" if rule.source_port else ""
        dst_port = f":{rule.destination_port}" if rule.destination_port else ""

        return {
            "description": f"{protocol} from {source}{src_port} to {destination}{dst_port}",
            "action": rule.action,
            "rule_type": rule.rule_type,
            "message": rule.message or "No description"
        }

    def _assess_terraform_security(self, policy: TerraformFirewallPolicy) -> dict[str, Any]:
        """Assess security implications of Terraform policy."""

        assessment = {
            "security_level": "medium",
            "risks": [],
            "recommendations": [],
            "compliance_notes": []
        }

        # Check for overly permissive rules
        for rule in policy.parsed_rules:
            if rule.action in ["pass", "allow"]:
                if rule.destination == "0.0.0.0/0":
                    assessment["risks"].append(
                        "Rule allows traffic to internet (0.0.0.0/0) - potential data exfiltration risk"
                    )
                    assessment["security_level"] = "low"

                if rule.source == "0.0.0.0/0":
                    assessment["risks"].append(
                        "Rule allows traffic from anywhere (0.0.0.0/0) - potential inbound attack risk"
                    )

        # Check for default deny posture
        if "aws:drop_strict" in policy.stateful_default_actions:
            assessment["recommendations"].append(
                "Good: Default deny posture implemented for stateful traffic"
            )
        else:
            assessment["risks"].append(
                "Missing default deny posture - consider aws:drop_strict"
            )
            assessment["security_level"] = "low"

        # Check for logging
        assessment["recommendations"].append(
            "Ensure logging is configured for this firewall policy in deployment"
        )

        return assessment

    def _compare_terraform_with_aws(self, tf_policy: TerraformFirewallPolicy, aws_firewall_name: str) -> dict[str, Any]:
        """Compare Terraform configuration with deployed AWS firewall."""

        try:
            # Get AWS firewall configuration (placeholder - would need actual implementation)
            comparison = {
                "terraform_policy": tf_policy.policy_name,
                "aws_firewall": aws_firewall_name,
                "differences": [],
                "recommendations": []
            }

            # This would need actual AWS API calls to compare
            comparison["note"] = "AWS comparison requires live AWS connectivity"

            return comparison

        except Exception as e:
            return {"error": f"Failed to compare with AWS: {str(e)}"}

    def validate_terraform_syntax(self, terraform_content: str) -> dict[str, Any]:
        """Validate Terraform syntax for Network Firewall resources.

        Args:
            terraform_content: Raw Terraform configuration content

        Returns:
            Validation results and syntax errors
        """
        try:
            validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "resource_count": 0
            }

            # Check for required resources
            if "aws_networkfirewall_firewall_policy" not in terraform_content:
                validation["errors"].append("No aws_networkfirewall_firewall_policy resource found")
                validation["valid"] = False
            else:
                validation["resource_count"] += 1

            # Check for rule groups
            stateless_count = len(re.findall(r'type\s*=\s*"STATELESS"', terraform_content))
            stateful_count = len(re.findall(r'type\s*=\s*"STATEFUL"', terraform_content))

            validation["resource_count"] += stateless_count + stateful_count

            if stateless_count == 0 and stateful_count == 0:
                validation["warnings"].append("No rule groups found - policy will use default behaviors only")

            # Check for common syntax issues
            if terraform_content.count("{") != terraform_content.count("}"):
                validation["errors"].append("Mismatched braces - check syntax")
                validation["valid"] = False

            # Check for variable references
            var_refs = re.findall(r"var\.([\\w_]+)", terraform_content)
            for var_ref in var_refs:
                if f'variable "{var_ref}"' not in terraform_content:
                    validation["warnings"].append(f"Variable '{var_ref}' referenced but not defined")

            return format_response("success", "Terraform validation completed", validation)

        except Exception as e:
            return format_response("error", f"Validation failed: {str(e)}")

    def analyze_cdk_policy(
        self,
        cdk_content: str,
        compare_with_aws: str | None = None
    ) -> dict[str, Any]:
        """Analyze CDK Network Firewall configuration.

        Args:
            cdk_content: Raw CDK TypeScript configuration content
            compare_with_aws: Optional AWS firewall name to compare against

        Returns:
            Comprehensive analysis of the CDK policy
        """
        try:
            # Parse CDK configuration
            cdk_policy = self.cdk_parser.parse_cdk_file(cdk_content)

            # Analyze traffic behavior
            traffic_analysis = self._analyze_cdk_traffic_behavior(cdk_policy)

            # Security assessment
            security_assessment = self._assess_cdk_security(cdk_policy)

            result = {
                "cdk_analysis": {
                    "policy_name": cdk_policy.policy_name,
                    "policy_type": cdk_policy.policy_type,
                    "stateless_config": {
                        "default_actions": cdk_policy.stateless_default_actions,
                        "fragment_actions": cdk_policy.stateless_fragment_default_actions,
                        "rule_groups": len(cdk_policy.stateless_rule_groups)
                    },
                    "stateful_config": {
                        "default_actions": cdk_policy.stateful_default_actions,
                        "rule_groups": len(cdk_policy.stateful_rule_groups)
                    },
                    "total_rules": len(cdk_policy.parsed_rules),
                    "rules_by_type": {
                        "stateless_native": len([r for r in cdk_policy.parsed_rules if r.rule_type == "stateless" and r.rule_format == "native"]),
                        "stateful_suricata": len([r for r in cdk_policy.parsed_rules if r.rule_type == "stateful" and r.rule_format == "suricata"])
                    },
                    "logging_configuration": cdk_policy.logging_configuration
                },
                "traffic_analysis": traffic_analysis,
                "security_assessment": security_assessment,
                "parsed_rules": [rule.dict() for rule in cdk_policy.parsed_rules]
            }

            # Compare with AWS if requested
            if compare_with_aws:
                aws_comparison = self._compare_cdk_with_aws(cdk_policy, compare_with_aws)
                result["aws_comparison"] = aws_comparison

            return format_response("success", "CDK policy analyzed successfully", result)

        except Exception as e:
            return format_response("error", f"Failed to analyze CDK policy: {str(e)}")

    def _analyze_cdk_traffic_behavior(self, policy: CdkFirewallPolicy) -> dict[str, Any]:
        """Analyze traffic behavior from CDK policy."""

        analysis = {
            "policy_type": policy.policy_type,
            "allowed_traffic": [],
            "blocked_traffic": [],
            "security_posture": "unknown"
        }

        # Determine overall policy behavior
        if "aws:forward_to_sfe" in policy.stateless_default_actions:
            if "aws:drop_strict" in policy.stateful_default_actions:
                analysis["security_posture"] = "default_deny"
            else:
                analysis["security_posture"] = "default_allow"

        # Analyze rules for traffic patterns
        for rule in policy.parsed_rules:
            if rule.action in ["pass"]:
                traffic_desc = self._describe_cdk_traffic_rule(rule)
                analysis["allowed_traffic"].append(traffic_desc)
            elif rule.action in ["drop", "alert"]:
                traffic_desc = self._describe_cdk_traffic_rule(rule)
                if rule.action == "drop":
                    analysis["blocked_traffic"].append(traffic_desc)

        return analysis

    def _describe_cdk_traffic_rule(self, rule: CdkRule) -> dict[str, str]:
        """Create human-readable description of a CDK traffic rule."""

        protocol = rule.protocol or "any protocol"
        source = rule.source or "any source"
        destination = rule.destination or "any destination"
        src_port = f":{rule.source_port}" if rule.source_port else ""
        dst_port = f":{rule.destination_port}" if rule.destination_port else ""

        return {
            "description": f"{protocol} from {source}{src_port} to {destination}{dst_port}",
            "action": rule.action,
            "rule_type": rule.rule_type,
            "rule_format": rule.rule_format,
            "rule_group": rule.rule_group_name or "unknown",
            "message": rule.message or "No description"
        }

    def _assess_cdk_security(self, policy: CdkFirewallPolicy) -> dict[str, Any]:
        """Assess security implications of CDK policy."""

        assessment = {
            "security_level": "medium",
            "risks": [],
            "recommendations": [],
            "compliance_notes": []
        }

        # Policy-specific security assessment
        if policy.policy_type == "egress":
            assessment["compliance_notes"].append(
                "Egress inspection policy - good for outbound traffic control"
            )

            # Check for domain allowlisting
            domain_rules = [r for r in policy.parsed_rules if "amazon.com" in (r.message or "")]
            if domain_rules:
                assessment["recommendations"].append(
                    "Domain allowlisting detected - ensure list is comprehensive"
                )

            # Check for SSH blocking
            ssh_rules = [r for r in policy.parsed_rules if r.destination_port == "22"]
            if ssh_rules:
                assessment["recommendations"].append(
                    "SSH traffic controls detected - good security practice"
                )

        elif policy.policy_type == "eastwest":
            assessment["compliance_notes"].append(
                "East-west inspection policy - good for internal network segmentation"
            )

        # Check for logging configuration
        if policy.logging_configuration.get("flow_logs") and policy.logging_configuration.get("alert_logs"):
            assessment["recommendations"].append(
                "Comprehensive logging configured - good for monitoring and compliance"
            )
        else:
            assessment["risks"].append(
                "Incomplete logging configuration - may impact security monitoring"
            )

        # Check for default deny posture
        if "aws:drop_strict" in policy.stateful_default_actions:
            assessment["recommendations"].append(
                "Default deny posture implemented - strong security baseline"
            )

        return assessment

    def _compare_cdk_with_aws(self, cdk_policy: CdkFirewallPolicy, aws_firewall_name: str) -> dict[str, Any]:
        """Compare CDK configuration with deployed AWS firewall."""

        try:
            comparison = {
                "cdk_policy": cdk_policy.policy_name,
                "aws_firewall": aws_firewall_name,
                "differences": [],
                "recommendations": []
            }

            # This would need actual AWS API calls to compare
            comparison["note"] = "AWS comparison requires live AWS connectivity"

            return comparison

        except Exception as e:
            return {"error": f"Failed to compare with AWS: {str(e)}"}

    def validate_cdk_syntax(self, cdk_content: str) -> dict[str, Any]:
        """Validate CDK syntax for Network Firewall resources.

        Args:
            cdk_content: Raw CDK TypeScript configuration content

        Returns:
            Validation results and syntax errors
        """
        try:
            validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "resource_count": 0
            }

            # Check for required methods
            if "createEgressInspectionFirewallPolicy" not in cdk_content and "createInspectionVPCFirewallPolicy" not in cdk_content:
                validation["errors"].append("No firewall policy creation methods found")
                validation["valid"] = False

            # Check for CfnFirewall creation
            if "new nf.CfnFirewall" not in cdk_content:
                validation["warnings"].append("No CfnFirewall resource found - policy may not be attached")
            else:
                validation["resource_count"] += 1

            # Check for rule groups
            stateless_count = len(re.findall(r'type:\s*"STATELESS"', cdk_content))
            stateful_count = len(re.findall(r'type:\s*"STATEFUL"', cdk_content))

            validation["resource_count"] += stateless_count + stateful_count

            if stateless_count == 0 and stateful_count == 0:
                validation["warnings"].append("No rule groups found - policy will use default behaviors only")

            # Check for logging configuration
            if "new logs.LogGroup" in cdk_content:
                validation["recommendations"] = ["Logging configuration detected - good practice"]
            else:
                validation["warnings"].append("No logging configuration found - consider adding CloudWatch logs")

            # Check for TypeScript syntax issues
            if cdk_content.count("{") != cdk_content.count("}"):
                validation["errors"].append("Mismatched braces - check TypeScript syntax")
                validation["valid"] = False

            if cdk_content.count("(") != cdk_content.count(")"):
                validation["errors"].append("Mismatched parentheses - check TypeScript syntax")
                validation["valid"] = False

            return format_response("success", "CDK validation completed", validation)

        except Exception as e:
            return format_response("error", f"Validation failed: {str(e)}")

    def analyze_cloudformation_policy(
        self,
        cf_content: str,
        compare_with_aws: str | None = None
    ) -> dict[str, Any]:
        """Analyze CloudFormation Network Firewall configuration.

        Args:
            cf_content: Raw CloudFormation template content (YAML or JSON)
            compare_with_aws: Optional AWS firewall name to compare against

        Returns:
            Comprehensive analysis of the CloudFormation policy
        """
        try:
            # Parse CloudFormation template
            cf_policy = self.cloudformation_parser.parse_cloudformation_template(cf_content)

            # Analyze traffic behavior
            traffic_analysis = self._analyze_cf_traffic_behavior(cf_policy)

            # Security assessment
            security_assessment = self._assess_cf_security(cf_policy)

            result = {
                "cloudformation_analysis": {
                    "policy_name": cf_policy.policy_name,
                    "template_version": cf_policy.template_format_version,
                    "description": cf_policy.description,
                    "stateless_config": {
                        "default_actions": cf_policy.stateless_default_actions,
                        "fragment_actions": cf_policy.stateless_fragment_default_actions,
                        "rule_groups": len(cf_policy.stateless_rule_groups)
                    },
                    "stateful_config": {
                        "default_actions": cf_policy.stateful_default_actions,
                        "engine_options": cf_policy.stateful_engine_options,
                        "rule_groups": len(cf_policy.stateful_rule_groups)
                    },
                    "total_rules": len(cf_policy.parsed_rules),
                    "rules_by_format": {
                        "native_stateless": len([r for r in cf_policy.parsed_rules if r.rule_type == "stateless" and r.rule_format == "native"]),
                        "native_stateful": len([r for r in cf_policy.parsed_rules if r.rule_type == "stateful" and r.rule_format == "native"]),
                        "suricata": len([r for r in cf_policy.parsed_rules if r.rule_format == "suricata"]),
                        "rules_source_list": len([r for r in cf_policy.parsed_rules if r.rule_format == "rules_source_list"])
                    }
                },
                "traffic_analysis": traffic_analysis,
                "security_assessment": security_assessment,
                "parsed_rules": [rule.dict() for rule in cf_policy.parsed_rules]
            }

            # Compare with AWS if requested
            if compare_with_aws:
                aws_comparison = self._compare_cf_with_aws(cf_policy, compare_with_aws)
                result["aws_comparison"] = aws_comparison

            return format_response("success", "CloudFormation policy analyzed successfully", result)

        except Exception as e:
            return format_response("error", f"Failed to analyze CloudFormation policy: {str(e)}")

    def _analyze_cf_traffic_behavior(self, policy: CloudFormationFirewallPolicy) -> dict[str, Any]:
        """Analyze traffic behavior from CloudFormation policy."""

        analysis = {
            "template_type": "cloudformation",
            "allowed_traffic": [],
            "blocked_traffic": [],
            "security_posture": "unknown",
            "rule_formats": []
        }

        # Determine overall policy behavior
        if "aws:forward_to_sfe" in policy.stateless_default_actions:
            if "aws:drop_strict" in policy.stateful_default_actions:
                analysis["security_posture"] = "default_deny"
            else:
                analysis["security_posture"] = "default_allow"

        # Track rule formats used
        formats_used = set(rule.rule_format for rule in policy.parsed_rules)
        analysis["rule_formats"] = list(formats_used)

        # Analyze rules for traffic patterns
        for rule in policy.parsed_rules:
            if rule.action in ["pass", "allow"]:
                traffic_desc = self._describe_cf_traffic_rule(rule)
                analysis["allowed_traffic"].append(traffic_desc)
            elif rule.action in ["drop", "alert", "reject"]:
                traffic_desc = self._describe_cf_traffic_rule(rule)
                if rule.action in ["drop", "reject"]:
                    analysis["blocked_traffic"].append(traffic_desc)

        return analysis

    def _describe_cf_traffic_rule(self, rule: CloudFormationRule) -> dict[str, str]:
        """Create human-readable description of a CloudFormation traffic rule."""

        protocol = rule.protocol or "any protocol"
        source = rule.source or "any source"
        destination = rule.destination or "any destination"
        src_port = f":{rule.source_port}" if rule.source_port else ""
        dst_port = f":{rule.destination_port}" if rule.destination_port else ""

        description = f"{protocol} from {source}{src_port} to {destination}{dst_port}"

        # Add format-specific information
        if rule.rule_format == "rules_source_list" and rule.targets:
            description += f" (targets: {', '.join(rule.targets)})"

        return {
            "description": description,
            "action": rule.action,
            "rule_type": rule.rule_type,
            "rule_format": rule.rule_format,
            "rule_group": rule.rule_group_name or "unknown",
            "message": rule.message or "No description",
            "priority": rule.priority
        }

    def _assess_cf_security(self, policy: CloudFormationFirewallPolicy) -> dict[str, Any]:
        """Assess security implications of CloudFormation policy."""

        assessment = {
            "security_level": "medium",
            "risks": [],
            "recommendations": [],
            "compliance_notes": [],
            "template_quality": []
        }

        # Template quality assessment
        if policy.description:
            assessment["template_quality"].append("Good: Template includes description")
        else:
            assessment["template_quality"].append("Consider: Add template description for documentation")

        # Engine options assessment
        if policy.stateful_engine_options.get("RuleOrder") == "STRICT_ORDER":
            assessment["recommendations"].append("Good: STRICT_ORDER rule evaluation configured")

        # Rule format diversity assessment
        formats = set(rule.rule_format for rule in policy.parsed_rules)
        if len(formats) > 1:
            assessment["compliance_notes"].append(f"Multiple rule formats used: {', '.join(formats)}")

        # Domain allowlist/denylist assessment
        rules_source_list_rules = [r for r in policy.parsed_rules if r.rule_format == "rules_source_list"]
        if rules_source_list_rules:
            assessment["recommendations"].append(
                f"Domain filtering rules detected: {len(rules_source_list_rules)} rules using RulesSourceList"
            )

        # Suricata rules assessment
        suricata_rules = [r for r in policy.parsed_rules if r.rule_format == "suricata"]
        if suricata_rules:
            assessment["compliance_notes"].append(
                f"Advanced Suricata rules: {len(suricata_rules)} custom detection rules"
            )

        # Check for default deny posture
        if "aws:drop_strict" in policy.stateful_default_actions:
            assessment["recommendations"].append("Good: Default deny posture implemented")
        else:
            assessment["risks"].append("Consider implementing default deny with aws:drop_strict")

        # Check for overly permissive rules
        for rule in policy.parsed_rules:
            if rule.action in ["pass", "allow"]:
                if rule.destination and "0.0.0.0/0" in rule.destination:
                    assessment["risks"].append(
                        f"Permissive rule allows traffic to internet (0.0.0.0/0) in {rule.rule_group_name}"
                    )
                if rule.source and "0.0.0.0/0" in rule.source:
                    assessment["risks"].append(
                        f"Permissive rule allows traffic from anywhere (0.0.0.0/0) in {rule.rule_group_name}"
                    )

        return assessment

    def _compare_cf_with_aws(self, cf_policy: CloudFormationFirewallPolicy, aws_firewall_name: str) -> dict[str, Any]:
        """Compare CloudFormation configuration with deployed AWS firewall."""

        try:
            comparison = {
                "cloudformation_policy": cf_policy.policy_name,
                "aws_firewall": aws_firewall_name,
                "differences": [],
                "recommendations": []
            }

            # This would need actual AWS API calls to compare
            comparison["note"] = "AWS comparison requires live AWS connectivity"

            return comparison

        except Exception as e:
            return {"error": f"Failed to compare with AWS: {str(e)}"}

    def validate_cloudformation_syntax(self, cf_content: str) -> dict[str, Any]:
        """Validate CloudFormation syntax for Network Firewall resources.

        Args:
            cf_content: Raw CloudFormation template content (YAML or JSON)

        Returns:
            Validation results and syntax errors
        """
        try:
            validation = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "resource_count": 0,
                "template_format": "unknown"
            }

            # Try to parse as YAML/JSON
            try:
                import yaml
                template = yaml.safe_load(cf_content)
                validation["template_format"] = "yaml"
            except yaml.YAMLError:
                try:
                    import json
                    template = json.loads(cf_content)
                    validation["template_format"] = "json"
                except json.JSONDecodeError as e:
                    validation["errors"].append(f"Invalid YAML/JSON syntax: {str(e)}")
                    validation["valid"] = False
                    return format_response("success", "CloudFormation validation completed", validation)

            # Check template version
            if "AWSTemplateFormatVersion" not in template:
                validation["warnings"].append("Missing AWSTemplateFormatVersion - consider adding")

            # Check for required sections
            if "Resources" not in template:
                validation["errors"].append("Missing Resources section in CloudFormation template")
                validation["valid"] = False
                return format_response("success", "CloudFormation validation completed", validation)

            resources = template.get("Resources", {})

            # Check for firewall policy
            firewall_policies = [r for r in resources.values() if r.get("Type") == "AWS::NetworkFirewall::FirewallPolicy"]
            if not firewall_policies:
                validation["errors"].append("No AWS::NetworkFirewall::FirewallPolicy resource found")
                validation["valid"] = False
            else:
                validation["resource_count"] += len(firewall_policies)

            # Check for rule groups
            stateless_groups = len([r for r in resources.values()
                                   if r.get("Type") == "AWS::NetworkFirewall::RuleGroup"
                                   and r.get("Properties", {}).get("Type") == "STATELESS"])
            stateful_groups = len([r for r in resources.values()
                                  if r.get("Type") == "AWS::NetworkFirewall::RuleGroup"
                                  and r.get("Properties", {}).get("Type") == "STATEFUL"])

            validation["resource_count"] += stateless_groups + stateful_groups

            if stateless_groups == 0 and stateful_groups == 0:
                validation["warnings"].append("No rule groups found - policy will use default behaviors only")

            # Check for firewall resource
            firewalls = [r for r in resources.values() if r.get("Type") == "AWS::NetworkFirewall::Firewall"]
            if not firewalls:
                validation["warnings"].append("No AWS::NetworkFirewall::Firewall resource found")
            else:
                validation["resource_count"] += len(firewalls)

            return format_response("success", "CloudFormation validation completed", validation)

        except Exception as e:
            return format_response("error", f"Validation failed: {str(e)}")


# Tool function implementations for FastMCP server integration
def analyze_terraform_network_firewall_policy(terraform_content: str, compare_with_aws: str = None) -> str:
    """Analyze Terraform Network Firewall policy configuration.

    Args:
        terraform_content: Complete Terraform configuration content
        compare_with_aws: Optional AWS firewall name for comparison

    Returns:
        JSON string with policy analysis results
    """
    tools = NetworkFirewallTools()
    result = tools.analyze_terraform_policy(terraform_content, compare_with_aws)
    return json.dumps(result, indent=2)


def validate_terraform_firewall_syntax(terraform_content: str) -> str:
    """Validate Terraform Network Firewall configuration syntax.

    Args:
        terraform_content: Complete Terraform configuration content

    Returns:
        JSON string with validation results
    """
    tools = NetworkFirewallTools()
    result = tools.validate_terraform_syntax(terraform_content)
    return json.dumps(result, indent=2)


def analyze_cdk_network_firewall_policy(cdk_content: str, compare_with_aws: str = None) -> str:
    """Analyze CDK Network Firewall policy configuration.

    Args:
        cdk_content: Complete CDK TypeScript configuration content
        compare_with_aws: Optional AWS firewall name for comparison

    Returns:
        JSON string with policy analysis results
    """
    tools = NetworkFirewallTools()
    result = tools.analyze_cdk_policy(cdk_content, compare_with_aws)
    return json.dumps(result, indent=2)


def validate_cdk_firewall_syntax(cdk_content: str) -> str:
    """Validate CDK Network Firewall configuration syntax.

    Args:
        cdk_content: Complete CDK TypeScript configuration content

    Returns:
        JSON string with validation results
    """
    tools = NetworkFirewallTools()
    result = tools.validate_cdk_syntax(cdk_content)
    return json.dumps(result, indent=2)


def simulate_cdk_firewall_traffic(cdk_content: str, test_flows: str) -> str:
    """Simulate traffic flows against CDK firewall configuration.

    Args:
        cdk_content: Complete CDK TypeScript configuration content
        test_flows: JSON array of 5-tuple flows to test

    Returns:
        JSON string with simulation results
    """
    try:
        tools = NetworkFirewallTools()
        cdk_policy = tools.cdk_parser.parse_cdk_file(cdk_content)

        flows = json.loads(test_flows) if isinstance(test_flows, str) else test_flows

        simulation_results = []

        for flow in flows:
            # Simulate flow against parsed rules
            flow_result = {
                "flow": flow,
                "result": "unknown",
                "matching_rules": [],
                "explanation": ""
            }

            # Check each rule against the flow
            for rule in cdk_policy.parsed_rules:
                if tools._flow_matches_cdk_rule(flow, rule):
                    flow_result["matching_rules"].append({
                        "rule_type": rule.rule_type,
                        "rule_format": rule.rule_format,
                        "action": rule.action,
                        "message": rule.message,
                        "rule_group": rule.rule_group_name
                    })

            # Determine final result based on rule evaluation
            if flow_result["matching_rules"]:
                # Use first matching rule (would need proper priority handling)
                first_match = flow_result["matching_rules"][0]
                flow_result["result"] = first_match["action"]
                flow_result["explanation"] = f"Matched rule: {first_match['message']}"
            else:
                # Apply default actions
                if "aws:drop_strict" in cdk_policy.stateful_default_actions:
                    flow_result["result"] = "drop"
                    flow_result["explanation"] = "No matching rules, default drop_strict applied"
                else:
                    flow_result["result"] = "allow"
                    flow_result["explanation"] = "No matching rules, default allow applied"

            simulation_results.append(flow_result)

        return json.dumps({
            "status": "success",
            "message": "CDK traffic simulation completed",
            "data": {
                "policy_name": cdk_policy.policy_name,
                "policy_type": cdk_policy.policy_type,
                "total_flows": len(flows),
                "simulation_results": simulation_results
            }
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"CDK simulation failed: {str(e)}"
        })


def simulate_terraform_firewall_traffic(terraform_content: str, test_flows: str) -> str:
    """Simulate traffic flows against Terraform firewall configuration.

    Args:
        terraform_content: Complete Terraform configuration content
        test_flows: JSON array of 5-tuple flows to test

    Returns:
        JSON string with simulation results
    """
    try:
        tools = NetworkFirewallTools()
        tf_policy = tools.terraform_parser.parse_terraform_file(terraform_content)

        flows = json.loads(test_flows) if isinstance(test_flows, str) else test_flows

        simulation_results = []

        for flow in flows:
            # Simulate flow against parsed rules
            flow_result = {
                "flow": flow,
                "result": "unknown",
                "matching_rules": [],
                "explanation": ""
            }

            # Check each rule against the flow
            for rule in tf_policy.parsed_rules:
                if tools._flow_matches_rule(flow, rule):
                    flow_result["matching_rules"].append({
                        "rule_type": rule.rule_type,
                        "action": rule.action,
                        "message": rule.message,
                        "priority": rule.priority
                    })

            # Determine final result based on rule evaluation
            if flow_result["matching_rules"]:
                # Use first matching rule (would need proper priority handling)
                first_match = flow_result["matching_rules"][0]
                flow_result["result"] = first_match["action"]
                flow_result["explanation"] = f"Matched rule: {first_match['message']}"
            else:
                # Apply default actions
                if "aws:drop_strict" in tf_policy.stateful_default_actions:
                    flow_result["result"] = "drop"
                    flow_result["explanation"] = "No matching rules, default drop_strict applied"
                else:
                    flow_result["result"] = "allow"
                    flow_result["explanation"] = "No matching rules, default allow applied"

            simulation_results.append(flow_result)

        return json.dumps({
            "status": "success",
            "message": "Traffic simulation completed",
            "data": {
                "policy_name": tf_policy.policy_name,
                "total_flows": len(flows),
                "simulation_results": simulation_results
            }
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Simulation failed: {str(e)}"
        })


# Helper method for flow matching (simplified implementation)
def _flow_matches_rule(self, flow: dict, rule: TerraformRule) -> bool:
    """Check if a flow matches a firewall rule (simplified logic)."""

    # This is a simplified implementation - real matching would be more complex
    # and would need to handle CIDR blocks, port ranges, etc.

    if rule.protocol and flow.get("protocol", "").upper() != rule.protocol.upper():
        return False

    if rule.source and rule.source != "any" and not self._ip_matches_pattern(
        flow.get("source_ip", ""), rule.source
    ):
        return False

    if rule.destination and rule.destination != "any" and not self._ip_matches_pattern(
        flow.get("destination_ip", ""), rule.destination
    ):
        return False

    return True


def _ip_matches_pattern(self, ip: str, pattern: str) -> bool:
    """Check if IP matches pattern (simplified - would need proper CIDR handling)."""

    if pattern in ["any", "0.0.0.0/0"]:
        return True

    if "/" in pattern:
        # CIDR block - simplified check
        network = pattern.split("/")[0]
        return ip.startswith(network.rsplit(".", 1)[0])

    return ip == pattern


# Helper method for CDK flow matching
def _flow_matches_cdk_rule(self, flow: dict, rule: CdkRule) -> bool:
    """Check if a flow matches a CDK firewall rule (simplified logic)."""

    # Similar to Terraform but handles CDK-specific rule formats

    if rule.protocol and flow.get("protocol", "").upper() != rule.protocol.upper():
        return False

    if rule.source and rule.source not in ["any", "$EXTERNAL_NET", "$HOME_NET", "$NETWORK"]:
        if not self._ip_matches_pattern(flow.get("source_ip", ""), rule.source):
            return False

    if rule.destination and rule.destination not in ["any", "$EXTERNAL_NET", "$HOME_NET", "$NETWORK"]:
        if not self._ip_matches_pattern(flow.get("destination_ip", ""), rule.destination):
            return False

    # Handle CDK port matching
    if rule.destination_port and rule.destination_port != "any":
        flow_port = str(flow.get("destination_port", ""))
        if flow_port != rule.destination_port:
            return False

    return True


def analyze_cloudformation_network_firewall_policy(cf_content: str, compare_with_aws: str = None) -> str:
    """Analyze CloudFormation Network Firewall policy configuration.

    Args:
        cf_content: Complete CloudFormation template content (YAML or JSON)
        compare_with_aws: Optional AWS firewall name for comparison

    Returns:
        JSON string with policy analysis results
    """
    tools = NetworkFirewallTools()
    result = tools.analyze_cloudformation_policy(cf_content, compare_with_aws)
    return json.dumps(result, indent=2)


def validate_cloudformation_firewall_syntax(cf_content: str) -> str:
    """Validate CloudFormation Network Firewall template syntax.

    Args:
        cf_content: Complete CloudFormation template content (YAML or JSON)

    Returns:
        JSON string with validation results
    """
    tools = NetworkFirewallTools()
    result = tools.validate_cloudformation_syntax(cf_content)
    return json.dumps(result, indent=2)


def simulate_cloudformation_firewall_traffic(cf_content: str, test_flows: str) -> str:
    """Simulate traffic flows against CloudFormation firewall configuration.

    Args:
        cf_content: Complete CloudFormation template content (YAML or JSON)
        test_flows: JSON array of 5-tuple flows to test

    Returns:
        JSON string with simulation results
    """
    try:
        tools = NetworkFirewallTools()
        cf_policy = tools.cloudformation_parser.parse_cloudformation_template(cf_content)

        flows = json.loads(test_flows) if isinstance(test_flows, str) else test_flows

        simulation_results = []

        for flow in flows:
            # Simulate flow against parsed rules
            flow_result = {
                "flow": flow,
                "result": "unknown",
                "matching_rules": [],
                "explanation": ""
            }

            # Check each rule against the flow
            for rule in cf_policy.parsed_rules:
                if tools._flow_matches_cf_rule(flow, rule):
                    flow_result["matching_rules"].append({
                        "rule_type": rule.rule_type,
                        "rule_format": rule.rule_format,
                        "action": rule.action,
                        "message": rule.message,
                        "rule_group": rule.rule_group_name,
                        "priority": rule.priority
                    })

            # Determine final result based on rule evaluation
            if flow_result["matching_rules"]:
                # Sort by priority if available (lower numbers = higher priority)
                matching_rules = sorted(flow_result["matching_rules"],
                                       key=lambda x: x.get("priority", 999))
                first_match = matching_rules[0]
                flow_result["result"] = first_match["action"]
                flow_result["explanation"] = f"Matched rule: {first_match['message']}"
            else:
                # Apply default actions
                if "aws:drop_strict" in cf_policy.stateful_default_actions:
                    flow_result["result"] = "drop"
                    flow_result["explanation"] = "No matching rules, default drop_strict applied"
                else:
                    flow_result["result"] = "allow"
                    flow_result["explanation"] = "No matching rules, default allow applied"

            simulation_results.append(flow_result)

        return json.dumps({
            "status": "success",
            "message": "CloudFormation traffic simulation completed",
            "data": {
                "policy_name": cf_policy.policy_name,
                "template_version": cf_policy.template_format_version,
                "total_flows": len(flows),
                "simulation_results": simulation_results
            }
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"CloudFormation simulation failed: {str(e)}"
        })


# Helper method for CloudFormation flow matching
def _flow_matches_cf_rule(self, flow: dict, rule: CloudFormationRule) -> bool:
    """Check if a flow matches a CloudFormation firewall rule (simplified logic)."""

    # Handle different rule formats
    if rule.rule_format == "rules_source_list":
        # Domain-based rules - simplified matching
        if rule.targets and any(target in flow.get("domain", "") for target in rule.targets):
            return True
        return False

    # Standard 5-tuple matching for native and Suricata formats
    if rule.protocol and rule.protocol != "ANY":
        if flow.get("protocol", "").upper() != rule.protocol.upper():
            return False

    # Source matching
    if rule.source and rule.source not in ["ANY", "any", "$EXTERNAL_NET", "$HOME_NET", "$NETWORK"]:
        if not self._ip_matches_pattern(flow.get("source_ip", ""), rule.source):
            return False

    # Destination matching
    if rule.destination and rule.destination not in ["ANY", "any", "$EXTERNAL_NET", "$HOME_NET", "$NETWORK"]:
        if not self._ip_matches_pattern(flow.get("destination_ip", ""), rule.destination):
            return False

    # Port matching
    if rule.destination_port and rule.destination_port not in ["ANY", "any"]:
        flow_port = str(flow.get("destination_port", ""))
        if "-" in rule.destination_port:
            # Handle port range
            from_port, to_port = rule.destination_port.split("-")
            if not (int(from_port) <= int(flow_port) <= int(to_port)):
                return False
        elif flow_port != rule.destination_port:
            return False

    return True


# Bind helper methods to class
NetworkFirewallTools._flow_matches_rule = _flow_matches_rule
NetworkFirewallTools._flow_matches_cdk_rule = _flow_matches_cdk_rule
NetworkFirewallTools._flow_matches_cf_rule = _flow_matches_cf_rule
NetworkFirewallTools._ip_matches_pattern = _ip_matches_pattern
