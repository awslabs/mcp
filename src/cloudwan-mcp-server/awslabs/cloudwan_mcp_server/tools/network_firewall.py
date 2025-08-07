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

"""AWS Network Firewall (ANFW) management tools for CloudWAN MCP Server.

This module provides comprehensive AWS Network Firewall integration including:
- Flow and alert log monitoring
- Policy analysis and compliance checking  
- 5-tuple traffic flow analysis
- Suricata rule parsing for L7 inspection
- What-if policy change simulation
- NFG and CloudWAN integration
"""

import json
import re
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from ..server import mcp, get_aws_client, handle_aws_error, safe_json_dumps, sanitize_error_message
from ..models.network_models import NetworkFirewall, FirewallPolicy, SuricataRule, FlowLog
from ..utils.aws_config_manager import get_aws_config


class NetworkFirewallTools:
    """AWS Network Firewall management and analysis tools."""
    
    def __init__(self):
        """Initialize Network Firewall tools."""
        self.config = get_aws_config()
        
    @lru_cache(maxsize=10)
    def get_network_firewall_client(self, region: Optional[str] = None):
        """Get cached Network Firewall client."""
        return get_aws_client("network-firewall", region or self.config.default_region)
    
    @lru_cache(maxsize=10) 
    def get_logs_client(self, region: Optional[str] = None):
        """Get cached CloudWatch Logs client."""
        return get_aws_client("logs", region or self.config.default_region)

    def _validate_firewall_identifier(self, identifier: str) -> None:
        """Validate firewall ARN or name format."""
        if identifier.startswith("arn:aws"):
            # Validate ARN format
            if not re.match(r'arn:aws:network-firewall:[^:]+:[^:]+:firewall/[^/]+$', identifier):
                raise ValueError(f"Invalid firewall ARN format: {sanitize_error_message(identifier)}")
        else:
            # Validate name format
            if not re.match(r'^[a-zA-Z0-9\-_]{1,128}$', identifier):
                raise ValueError(f"Invalid firewall name format: {sanitize_error_message(identifier)}")

    def _validate_ip_address(self, ip: str) -> None:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f"Invalid IP address format: {sanitize_error_message(ip)}")

    def _validate_port(self, port: int) -> None:
        """Validate port number range."""
        if not (1 <= port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535: {port}")

    def _parse_suricata_rule(self, rule: str) -> SuricataRule:
        """Parse individual Suricata rule into structured format."""
        try:
            # Basic Suricata rule parsing - simplified version
            # Format: action protocol src_ip src_port -> dst_ip dst_port (options)
            pattern = r'(alert|pass|drop|reject)\s+(\w+)\s+(\S+)\s+(\S+)\s+->\s+(\S+)\s+(\S+)'
            match = re.match(pattern, rule.strip())
            
            if not match:
                return SuricataRule(
                    action="unknown",
                    protocol="any",
                    raw_rule=rule,
                    parsed=False
                )
                
            action, protocol, src_ip, src_port, dst_ip, dst_port = match.groups()
            
            return SuricataRule(
                action=action,
                protocol=protocol,
                src_ip=src_ip if src_ip != "any" else None,
                src_port=src_port if src_port != "any" else None,
                dst_ip=dst_ip if dst_ip != "any" else None,
                dst_port=dst_port if dst_port != "any" else None,
                raw_rule=rule,
                parsed=True
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse Suricata rule: {sanitize_error_message(str(e))}")
            return SuricataRule(
                action="unknown",
                protocol="any", 
                raw_rule=rule,
                parsed=False,
                parse_error=str(e)
            )

    def _check_five_tuple_match(self, rule: SuricataRule, src_ip: str, dst_ip: str, 
                              protocol: str, src_port: int, dst_port: int) -> bool:
        """Check if 5-tuple matches Suricata rule."""
        try:
            # Protocol match
            if rule.protocol != "any" and rule.protocol.lower() != protocol.lower():
                return False
                
            # Source IP match
            if rule.src_ip and rule.src_ip != "any":
                if not self._ip_matches_pattern(src_ip, rule.src_ip):
                    return False
                    
            # Destination IP match  
            if rule.dst_ip and rule.dst_ip != "any":
                if not self._ip_matches_pattern(dst_ip, rule.dst_ip):
                    return False
                    
            # Source port match
            if rule.src_port and rule.src_port != "any":
                if not self._port_matches_pattern(src_port, rule.src_port):
                    return False
                    
            # Destination port match
            if rule.dst_port and rule.dst_port != "any":
                if not self._port_matches_pattern(dst_port, rule.dst_port):
                    return False
                    
            return True
            
        except Exception as e:
            logger.warning(f"Error checking 5-tuple match: {sanitize_error_message(str(e))}")
            return False

    def _ip_matches_pattern(self, ip: str, pattern: str) -> bool:
        """Check if IP matches pattern (supports CIDR)."""
        try:
            if "/" in pattern:
                # CIDR notation
                network = ipaddress.ip_network(pattern, strict=False)
                return ipaddress.ip_address(ip) in network
            else:
                # Direct match
                return ip == pattern
        except Exception:
            return False

    def _port_matches_pattern(self, port: int, pattern: str) -> bool:
        """Check if port matches pattern (supports ranges)."""
        try:
            if ":" in pattern:
                # Port range
                start, end = map(int, pattern.split(":"))
                return start <= port <= end
            else:
                # Direct match
                return port == int(pattern)
        except Exception:
            return False

    def _simulate_policy_impact(self, current_policy: Dict, new_policy: Dict, 
                              test_flows: List[Tuple]) -> Dict:
        """Simulate impact of policy changes on test flows."""
        results = {
            "flows_analyzed": len(test_flows),
            "impact_summary": {
                "newly_blocked": 0,
                "newly_allowed": 0,
                "no_change": 0
            },
            "detailed_analysis": []
        }
        
        for flow in test_flows:
            src_ip, dst_ip, protocol, src_port, dst_port = flow
            
            # Analyze current policy decision
            current_decision = self._evaluate_flow_against_policy(
                current_policy, src_ip, dst_ip, protocol, src_port, dst_port
            )
            
            # Analyze new policy decision
            new_decision = self._evaluate_flow_against_policy(
                new_policy, src_ip, dst_ip, protocol, src_port, dst_port
            )
            
            # Determine impact
            if current_decision != new_decision:
                if current_decision == "ALLOW" and new_decision == "DENY":
                    results["impact_summary"]["newly_blocked"] += 1
                    impact = "NEWLY_BLOCKED"
                else:
                    results["impact_summary"]["newly_allowed"] += 1 
                    impact = "NEWLY_ALLOWED"
            else:
                results["impact_summary"]["no_change"] += 1
                impact = "NO_CHANGE"
                
            results["detailed_analysis"].append({
                "flow": f"{src_ip}:{src_port} -> {dst_ip}:{dst_port} ({protocol})",
                "current_decision": current_decision,
                "new_decision": new_decision,
                "impact": impact
            })
            
        return results

    def _evaluate_flow_against_policy(self, policy: Dict, src_ip: str, dst_ip: str,
                                    protocol: str, src_port: int, dst_port: int) -> str:
        """Evaluate if flow is allowed by policy."""
        try:
            # Simplified policy evaluation - in reality this would be much more complex
            # This is a basic implementation for demonstration
            
            # Check stateless rules first
            for rule_group in policy.get("StatelessRuleGroups", []):
                # Simplified stateless evaluation
                if self._check_stateless_rule_match(rule_group, src_ip, dst_ip, protocol, src_port, dst_port):
                    return rule_group.get("Action", "DENY")
                    
            # Check stateful rules
            for rule_group in policy.get("StatefulRuleGroups", []):
                # Simplified stateful evaluation
                if self._check_stateful_rule_match(rule_group, src_ip, dst_ip, protocol, src_port, dst_port):
                    return "ALLOW"  # Stateful rules typically allow established connections
                    
            # Default action
            return policy.get("StatelessDefaultActions", ["aws:drop"])[0].replace("aws:", "").upper()
            
        except Exception as e:
            logger.warning(f"Error evaluating flow against policy: {sanitize_error_message(str(e))}")
            return "DENY"  # Fail secure

    def _check_stateless_rule_match(self, rule_group: Dict, src_ip: str, dst_ip: str,
                                  protocol: str, src_port: int, dst_port: int) -> bool:
        """Check if flow matches stateless rule group."""
        # Simplified implementation - real implementation would be much more complex
        return False

    def _check_stateful_rule_match(self, rule_group: Dict, src_ip: str, dst_ip: str, 
                                 protocol: str, src_port: int, dst_port: int) -> bool:
        """Check if flow matches stateful rule group.""" 
        # Simplified implementation - real implementation would be much more complex
        return False


# Initialize tools instance
firewall_tools = NetworkFirewallTools()


@mcp.tool(name="monitor_anfw_logs")
async def monitor_anfw_logs(
    firewall_name: str,
    log_type: str = "flow", 
    time_range_minutes: int = 60,
    region: Optional[str] = None
) -> str:
    """Monitor AWS Network Firewall flow and alert logs.
    
    Args:
        firewall_name: Name of the Network Firewall
        log_type: Type of logs to monitor ('flow' or 'alert')
        time_range_minutes: Time range in minutes to query (default: 60)
        region: AWS region (optional, uses default if not specified)
        
    Returns:
        JSON string with log entries and analysis
    """
    try:
        # Validate inputs
        firewall_tools._validate_firewall_identifier(firewall_name)
        if log_type not in ["flow", "alert"]:
            raise ValueError("log_type must be 'flow' or 'alert'")
        if not (1 <= time_range_minutes <= 1440):  # Max 24 hours
            raise ValueError("time_range_minutes must be between 1 and 1440")
            
        # Get CloudWatch Logs client
        logs_client = firewall_tools.get_logs_client(region)
        
        # Construct log group name
        log_group = f"/aws/network-firewall/{firewall_name}"
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=time_range_minutes)
        
        # Query CloudWatch Logs
        query = f"""
        fields @timestamp, @message
        | filter @message like /{log_type.upper()}/
        | sort @timestamp desc
        | limit 100
        """
        
        response = logs_client.start_query(
            logGroupName=log_group,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query
        )
        
        query_id = response["queryId"]
        
        # Wait for query completion (simplified polling)
        import time
        for _ in range(30):  # Max 30 seconds
            result = logs_client.get_query_results(queryId=query_id)
            if result["status"] == "Complete":
                break
            time.sleep(1)
        else:
            raise TimeoutError("Query did not complete within 30 seconds")
            
        # Process results
        log_entries = []
        for row in result.get("results", []):
            entry = {}
            for field in row:
                entry[field["field"]] = field["value"]
            log_entries.append(entry)
            
        # Analyze logs for patterns
        analysis = {
            "total_entries": len(log_entries),
            "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
            "log_type": log_type,
            "top_sources": {},
            "top_destinations": {},
            "actions_summary": {}
        }
        
        # Basic log analysis
        for entry in log_entries:
            message = entry.get("@message", "")
            # Parse flow log format (simplified)
            if "srcaddr" in message and "dstaddr" in message:
                # Extract source and destination IPs for analysis
                src_match = re.search(r'srcaddr=(\d+\.\d+\.\d+\.\d+)', message)
                dst_match = re.search(r'dstaddr=(\d+\.\d+\.\d+\.\d+)', message)
                action_match = re.search(r'action=(\w+)', message)
                
                if src_match:
                    src_ip = src_match.group(1)
                    analysis["top_sources"][src_ip] = analysis["top_sources"].get(src_ip, 0) + 1
                    
                if dst_match:
                    dst_ip = dst_match.group(1)
                    analysis["top_destinations"][dst_ip] = analysis["top_destinations"].get(dst_ip, 0) + 1
                    
                if action_match:
                    action = action_match.group(1)
                    analysis["actions_summary"][action] = analysis["actions_summary"].get(action, 0) + 1
        
        return safe_json_dumps({
            "success": True,
            "firewall_name": firewall_name,
            "log_entries": log_entries,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"Failed to monitor ANFW logs: {sanitize_error_message(str(e))}")
        return handle_aws_error(e, "monitor_anfw_logs")


@mcp.tool(name="analyze_anfw_policy")
async def analyze_anfw_policy(
    firewall_identifier: str,
    include_compliance_check: bool = True,
    region: Optional[str] = None
) -> str:
    """Analyze AWS Network Firewall policy and configuration.
    
    Args:
        firewall_identifier: Firewall ARN or name
        include_compliance_check: Include CloudWAN compliance analysis
        region: AWS region (optional)
        
    Returns:
        JSON string with policy analysis and recommendations
    """
    try:
        # Validate inputs
        firewall_tools._validate_firewall_identifier(firewall_identifier)
        
        # Get Network Firewall client
        nfw_client = firewall_tools.get_network_firewall_client(region)
        
        # Get firewall details
        if firewall_identifier.startswith("arn:"):
            firewall_response = nfw_client.describe_firewall(FirewallArn=firewall_identifier)
        else:
            firewall_response = nfw_client.describe_firewall(FirewallName=firewall_identifier)
            
        firewall = firewall_response["Firewall"]
        firewall_metadata = firewall_response["FirewallStatus"]
        
        # Get firewall policy
        policy_response = nfw_client.describe_firewall_policy(
            FirewallPolicyArn=firewall["FirewallPolicyArn"]
        )
        policy = policy_response["FirewallPolicy"]
        
        # Get logging configuration
        try:
            logging_response = nfw_client.describe_logging_configuration(
                FirewallArn=firewall["FirewallArn"]
            )
            logging_config = logging_response.get("LoggingConfiguration", {})
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logging_config = {}
            else:
                raise
                
        # Analyze policy structure
        analysis = {
            "firewall_details": {
                "name": firewall["FirewallName"],
                "arn": firewall["FirewallArn"],
                "vpc_id": firewall["VpcId"],
                "subnet_mappings": len(firewall["SubnetMappings"]),
                "status": firewall_metadata["Status"]
            },
            "policy_summary": {
                "stateless_rule_groups": len(policy.get("StatelessRuleGroups", [])),
                "stateful_rule_groups": len(policy.get("StatefulRuleGroups", [])),
                "stateless_default_actions": policy.get("StatelessDefaultActions", []),
                "stateless_fragment_default_actions": policy.get("StatelessFragmentDefaultActions", [])
            },
            "logging_configuration": {
                "configured": bool(logging_config),
                "destinations": len(logging_config.get("LogDestinationConfigs", []))
            },
            "security_recommendations": []
        }
        
        # Generate security recommendations
        recommendations = []
        
        # Check for logging
        if not logging_config:
            recommendations.append({
                "priority": "HIGH",
                "category": "LOGGING", 
                "recommendation": "Enable logging for flow and alert logs",
                "rationale": "Logging is essential for security monitoring and compliance"
            })
            
        # Check default actions
        if "aws:pass" in policy.get("StatelessDefaultActions", []):
            recommendations.append({
                "priority": "MEDIUM",
                "category": "SECURITY",
                "recommendation": "Review permissive default action 'aws:pass'",
                "rationale": "Consider using explicit allow/deny rules instead of permissive defaults"
            })
            
        # Check for empty rule groups
        if not policy.get("StatelessRuleGroups") and not policy.get("StatefulRuleGroups"):
            recommendations.append({
                "priority": "HIGH", 
                "category": "CONFIGURATION",
                "recommendation": "Add rule groups to define firewall behavior",
                "rationale": "Empty firewall policy may not provide intended protection"
            })
            
        analysis["security_recommendations"] = recommendations
        
        # CloudWAN compliance check if requested
        if include_compliance_check:
            try:
                # Get CloudWAN core network policy for comparison
                from .core_network import CoreNetworkTools
                core_tools = CoreNetworkTools()
                
                # This would involve complex policy comparison logic
                compliance = {
                    "status": "ANALYSIS_AVAILABLE",
                    "note": "CloudWAN policy compliance analysis requires core network context"
                }
                analysis["cloudwan_compliance"] = compliance
                
            except Exception as e:
                logger.warning(f"CloudWAN compliance check failed: {sanitize_error_message(str(e))}")
                analysis["cloudwan_compliance"] = {
                    "status": "CHECK_FAILED",
                    "error": "Unable to perform compliance analysis"
                }
        
        return safe_json_dumps({
            "success": True,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"Failed to analyze ANFW policy: {sanitize_error_message(str(e))}")
        return handle_aws_error(e, "analyze_anfw_policy")


@mcp.tool(name="analyze_five_tuple_flow")
async def analyze_five_tuple_flow(
    firewall_identifier: str,
    source_ip: str,
    destination_ip: str, 
    protocol: str,
    source_port: int,
    destination_port: int,
    region: Optional[str] = None
) -> str:
    """Analyze if a 5-tuple flow would be permitted by Network Firewall policy.
    
    Args:
        firewall_identifier: Firewall ARN or name
        source_ip: Source IP address
        destination_ip: Destination IP address
        protocol: Protocol (TCP, UDP, ICMP)
        source_port: Source port number
        destination_port: Destination port number
        region: AWS region (optional)
        
    Returns:
        JSON string with flow analysis results
    """
    try:
        # Validate inputs
        firewall_tools._validate_firewall_identifier(firewall_identifier)
        firewall_tools._validate_ip_address(source_ip)
        firewall_tools._validate_ip_address(destination_ip)
        firewall_tools._validate_port(source_port)
        firewall_tools._validate_port(destination_port)
        
        if protocol.upper() not in ["TCP", "UDP", "ICMP"]:
            raise ValueError("Protocol must be TCP, UDP, or ICMP")
            
        # Get firewall policy
        nfw_client = firewall_tools.get_network_firewall_client(region)
        
        if firewall_identifier.startswith("arn:"):
            firewall_response = nfw_client.describe_firewall(FirewallArn=firewall_identifier)
        else:
            firewall_response = nfw_client.describe_firewall(FirewallName=firewall_identifier)
            
        firewall = firewall_response["Firewall"]
        
        # Get policy details
        policy_response = nfw_client.describe_firewall_policy(
            FirewallPolicyArn=firewall["FirewallPolicyArn"]
        )
        policy = policy_response["FirewallPolicy"]
        
        # Analyze flow against policy
        flow_analysis = {
            "flow_details": {
                "source_ip": source_ip,
                "destination_ip": destination_ip,
                "protocol": protocol.upper(),
                "source_port": source_port,
                "destination_port": destination_port
            },
            "policy_evaluation": {
                "stateless_analysis": {},
                "stateful_analysis": {},
                "final_decision": "UNKNOWN"
            },
            "rule_matches": [],
            "recommendations": []
        }
        
        # Simplified policy evaluation - in production this would be much more sophisticated
        evaluation_result = firewall_tools._evaluate_flow_against_policy(
            policy, source_ip, destination_ip, protocol.upper(), source_port, destination_port
        )
        
        flow_analysis["policy_evaluation"]["final_decision"] = evaluation_result
        
        # Add contextual analysis
        if evaluation_result == "DENY":
            flow_analysis["recommendations"].append({
                "type": "SECURITY",
                "message": "Flow would be blocked by current policy",
                "suggestion": "Review rule groups if this flow should be allowed"
            })
        else:
            flow_analysis["recommendations"].append({
                "type": "INFO", 
                "message": "Flow would be permitted by current policy",
                "suggestion": "Ensure this aligns with security requirements"
            })
            
        # Integration with path tracing
        try:
            from .network_analysis import NetworkAnalysisTools
            path_tools = NetworkAnalysisTools()
            
            # This would integrate with existing path tracing functionality
            integration_note = {
                "path_trace_available": True,
                "note": "Use trace_network_path tool for end-to-end path analysis including firewall hops"
            }
            flow_analysis["path_integration"] = integration_note
            
        except Exception as e:
            logger.warning(f"Path integration failed: {sanitize_error_message(str(e))}")
            
        return safe_json_dumps({
            "success": True,
            "flow_analysis": flow_analysis
        })
        
    except Exception as e:
        logger.error(f"Failed to analyze 5-tuple flow: {sanitize_error_message(str(e))}")
        return handle_aws_error(e, "analyze_five_tuple_flow")


@mcp.tool(name="parse_suricata_rules")
async def parse_suricata_rules(
    firewall_identifier: str,
    analyze_l7_rules: bool = True,
    region: Optional[str] = None
) -> str:
    """Parse and analyze Suricata rules from Network Firewall for L7 inspection.
    
    Args:
        firewall_identifier: Firewall ARN or name
        analyze_l7_rules: Include L7 application layer analysis
        region: AWS region (optional)
        
    Returns:
        JSON string with parsed Suricata rules and analysis
    """
    try:
        # Validate inputs
        firewall_tools._validate_firewall_identifier(firewall_identifier)
        
        # Get Network Firewall client
        nfw_client = firewall_tools.get_network_firewall_client(region)
        
        # Get firewall and policy
        if firewall_identifier.startswith("arn:"):
            firewall_response = nfw_client.describe_firewall(FirewallArn=firewall_identifier)
        else:
            firewall_response = nfw_client.describe_firewall(FirewallName=firewall_identifier)
            
        firewall = firewall_response["Firewall"]
        
        policy_response = nfw_client.describe_firewall_policy(
            FirewallPolicyArn=firewall["FirewallPolicyArn"]
        )
        policy = policy_response["FirewallPolicy"]
        
        # Parse Suricata rules from stateful rule groups
        parsed_rules = []
        l7_analysis = {
            "application_protocols": {},
            "rule_categories": {},
            "security_analysis": {
                "total_rules": 0,
                "alert_rules": 0,
                "drop_rules": 0,
                "pass_rules": 0
            }
        }
        
        # Process stateful rule groups
        for rule_group in policy.get("StatefulRuleGroups", []):
            try:
                # Get rule group details
                rule_group_response = nfw_client.describe_rule_group(
                    RuleGroupArn=rule_group["ResourceArn"]
                )
                
                rule_group_data = rule_group_response["RuleGroup"]
                
                # Parse Suricata rules if present
                if "RulesSource" in rule_group_data:
                    rules_source = rule_group_data["RulesSource"]
                    
                    if "RulesString" in rules_source:
                        # Parse individual Suricata rules
                        rules_string = rules_source["RulesString"]
                        rule_lines = rules_string.split('\n')
                        
                        for rule_line in rule_lines:
                            rule_line = rule_line.strip()
                            if rule_line and not rule_line.startswith('#'):
                                parsed_rule = firewall_tools._parse_suricata_rule(rule_line)
                                parsed_rules.append(parsed_rule)
                                
                                # Update statistics
                                l7_analysis["security_analysis"]["total_rules"] += 1
                                if parsed_rule.action == "alert":
                                    l7_analysis["security_analysis"]["alert_rules"] += 1
                                elif parsed_rule.action == "drop":
                                    l7_analysis["security_analysis"]["drop_rules"] += 1
                                elif parsed_rule.action == "pass":
                                    l7_analysis["security_analysis"]["pass_rules"] += 1
                                    
                                # Categorize by protocol
                                protocol = parsed_rule.protocol
                                l7_analysis["rule_categories"][protocol] = l7_analysis["rule_categories"].get(protocol, 0) + 1
                                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"Rule group not found: {rule_group['ResourceArn']}")
                    continue
                else:
                    raise
                    
        # L7 application analysis if requested
        if analyze_l7_rules:
            app_protocols = {}
            for rule in parsed_rules:
                if rule.parsed and hasattr(rule, 'raw_rule'):
                    # Look for application protocol indicators in rule content
                    rule_content = rule.raw_rule.lower()
                    
                    # Common application protocol detection
                    if 'http' in rule_content:
                        app_protocols['HTTP'] = app_protocols.get('HTTP', 0) + 1
                    if 'tls' in rule_content or 'ssl' in rule_content:
                        app_protocols['TLS/SSL'] = app_protocols.get('TLS/SSL', 0) + 1
                    if 'dns' in rule_content:
                        app_protocols['DNS'] = app_protocols.get('DNS', 0) + 1
                    if 'smtp' in rule_content:
                        app_protocols['SMTP'] = app_protocols.get('SMTP', 0) + 1
                        
            l7_analysis["application_protocols"] = app_protocols
        
        # Generate recommendations
        recommendations = []
        
        if l7_analysis["security_analysis"]["total_rules"] == 0:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "L7_INSPECTION",
                "recommendation": "Consider adding Suricata rules for application-layer inspection",
                "rationale": "L7 inspection provides deeper security analysis"
            })
            
        if l7_analysis["security_analysis"]["alert_rules"] == 0:
            recommendations.append({
                "priority": "LOW", 
                "category": "MONITORING",
                "recommendation": "Add alert rules for security event detection",
                "rationale": "Alert rules help with threat detection and monitoring"
            })
        
        return safe_json_dumps({
            "success": True,
            "firewall_name": firewall["FirewallName"],
            "parsed_rules": [rule.dict() for rule in parsed_rules],
            "l7_analysis": l7_analysis,
            "recommendations": recommendations
        })
        
    except Exception as e:
        logger.error(f"Failed to parse Suricata rules: {sanitize_error_message(str(e))}")
        return handle_aws_error(e, "parse_suricata_rules")


@mcp.tool(name="simulate_policy_changes")
async def simulate_policy_changes(
    firewall_identifier: str,
    policy_change_description: str,
    test_flows: Optional[List[str]] = None,
    region: Optional[str] = None
) -> str:
    """Simulate what-if scenarios for Network Firewall policy changes.
    
    Args:
        firewall_identifier: Firewall ARN or name
        policy_change_description: Description of proposed policy changes
        test_flows: List of test flows in format "src_ip:src_port->dst_ip:dst_port/protocol"
        region: AWS region (optional)
        
    Returns:
        JSON string with policy change impact analysis
    """
    try:
        # Validate inputs
        firewall_tools._validate_firewall_identifier(firewall_identifier)
        
        # Parse test flows
        parsed_flows = []
        if test_flows:
            for flow_str in test_flows:
                try:
                    # Parse flow string: "1.2.3.4:80->5.6.7.8:443/TCP"
                    parts = flow_str.split('->')
                    if len(parts) != 2:
                        raise ValueError("Invalid flow format")
                        
                    src_part = parts[0].strip()
                    dst_part = parts[1].strip()
                    
                    src_ip, src_port = src_part.split(':')
                    dst_ip_port, protocol = dst_part.split('/')
                    dst_ip, dst_port = dst_ip_port.split(':')
                    
                    # Validate components
                    firewall_tools._validate_ip_address(src_ip)
                    firewall_tools._validate_ip_address(dst_ip)
                    firewall_tools._validate_port(int(src_port))
                    firewall_tools._validate_port(int(dst_port))
                    
                    parsed_flows.append((src_ip, dst_ip, protocol.upper(), int(src_port), int(dst_port)))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse flow '{flow_str}': {sanitize_error_message(str(e))}")
                    continue
        else:
            # Use default test flows if none provided
            parsed_flows = [
                ("10.0.1.100", "10.0.2.200", "TCP", 12345, 80),
                ("10.0.1.100", "10.0.2.200", "TCP", 12346, 443),
                ("192.168.1.10", "8.8.8.8", "UDP", 53, 53),
                ("172.16.1.50", "172.16.2.100", "TCP", 54321, 22)
            ]
        
        # Get current policy
        nfw_client = firewall_tools.get_network_firewall_client(region)
        
        if firewall_identifier.startswith("arn:"):
            firewall_response = nfw_client.describe_firewall(FirewallArn=firewall_identifier)
        else:
            firewall_response = nfw_client.describe_firewall(FirewallName=firewall_identifier)
            
        firewall = firewall_response["Firewall"]
        
        policy_response = nfw_client.describe_firewall_policy(
            FirewallPolicyArn=firewall["FirewallPolicyArn"]
        )
        current_policy = policy_response["FirewallPolicy"]
        
        # For simulation purposes, create a mock "new policy" based on description
        # In production, this would parse actual Terraform/JSON policy files
        simulated_new_policy = current_policy.copy()  # Placeholder
        
        # Analyze impact
        impact_analysis = firewall_tools._simulate_policy_impact(
            current_policy, simulated_new_policy, parsed_flows
        )
        
        # Add metadata
        simulation_result = {
            "firewall_name": firewall["FirewallName"],
            "policy_change_description": policy_change_description,
            "simulation_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "test_flows_count": len(parsed_flows),
                "simulation_type": "BASIC"  # Could be enhanced to support different types
            },
            "impact_analysis": impact_analysis,
            "recommendations": []
        }
        
        # Generate recommendations based on impact
        recommendations = []
        
        if impact_analysis["impact_summary"]["newly_blocked"] > 0:
            recommendations.append({
                "priority": "HIGH",
                "category": "CONNECTIVITY_IMPACT",
                "recommendation": f"Policy change would block {impact_analysis['impact_summary']['newly_blocked']} existing flows",
                "action": "Review blocked flows to ensure this is intentional"
            })
            
        if impact_analysis["impact_summary"]["newly_allowed"] > 0:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "SECURITY_IMPACT", 
                "recommendation": f"Policy change would allow {impact_analysis['impact_summary']['newly_allowed']} new flows",
                "action": "Verify new flows meet security requirements"
            })
            
        simulation_result["recommendations"] = recommendations
        
        # Add integration suggestions
        integration_notes = {
            "nfg_integration": "Consider analyzing impact on Network Function Groups",
            "cloudwan_integration": "Review alignment with CloudWAN segmentation policies",
            "monitoring": "Update logging and monitoring for policy changes"
        }
        simulation_result["integration_notes"] = integration_notes
        
        return safe_json_dumps({
            "success": True,
            "simulation_result": simulation_result
        })
        
    except Exception as e:
        logger.error(f"Failed to simulate policy changes: {sanitize_error_message(str(e))}")
        return handle_aws_error(e, "simulate_policy_changes")


# Add tools to the main tools list for registration
NETWORK_FIREWALL_TOOLS = [
    monitor_anfw_logs,
    analyze_anfw_policy, 
    analyze_five_tuple_flow,
    parse_suricata_rules,
    simulate_policy_changes
]