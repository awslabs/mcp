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

"""Unit tests for AWS Network Firewall (ANFW) tools."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

from awslabs.cloudwan_mcp_server.tools.network_firewall import (
    NetworkFirewallTools,
    monitor_anfw_logs,
    analyze_anfw_policy,
    analyze_five_tuple_flow,
    parse_suricata_rules,
    simulate_policy_changes
)


class TestNetworkFirewallTools:
    """Test suite for NetworkFirewallTools class."""
    
    @pytest.fixture
    def firewall_tools(self):
        """Create NetworkFirewallTools instance for testing."""
        return NetworkFirewallTools()
    
    @pytest.fixture
    def mock_firewall_response(self):
        """Mock firewall describe response."""
        return {
            "Firewall": {
                "FirewallName": "test-firewall",
                "FirewallArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall/test-firewall",
                "VpcId": "vpc-12345",
                "SubnetMappings": [{"SubnetId": "subnet-12345"}],
                "FirewallPolicyArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/test-policy"
            },
            "FirewallStatus": {
                "Status": "READY"
            }
        }
    
    @pytest.fixture
    def mock_policy_response(self):
        """Mock firewall policy response."""
        return {
            "FirewallPolicy": {
                "StatelessRuleGroups": [
                    {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateless-rulegroup/test-stateless"}
                ],
                "StatefulRuleGroups": [
                    {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/test-stateful"}
                ],
                "StatelessDefaultActions": ["aws:pass"],
                "StatelessFragmentDefaultActions": ["aws:drop"]
            }
        }
    
    @pytest.fixture
    def mock_rule_group_response(self):
        """Mock rule group response with Suricata rules."""
        return {
            "RuleGroup": {
                "RulesSource": {
                    "RulesString": """alert tcp any any -> any 80 (msg:"HTTP traffic detected"; sid:1; rev:1;)
drop tcp any any -> any 22 (msg:"SSH traffic blocked"; sid:2; rev:1;)
pass udp any 53 -> any any (msg:"DNS traffic allowed"; sid:3; rev:1;)"""
                }
            }
        }
    
    def test_init(self, firewall_tools):
        """Test NetworkFirewallTools initialization."""
        assert firewall_tools is not None
        assert hasattr(firewall_tools, 'config')
    
    def test_validate_firewall_identifier_valid_arn(self, firewall_tools):
        """Test validation of valid firewall ARN."""
        valid_arn = "arn:aws:network-firewall:us-east-1:123456789012:firewall/test-firewall"
        # Should not raise exception
        firewall_tools._validate_firewall_identifier(valid_arn)
    
    def test_validate_firewall_identifier_valid_name(self, firewall_tools):
        """Test validation of valid firewall name."""
        valid_name = "test-firewall-123"
        # Should not raise exception
        firewall_tools._validate_firewall_identifier(valid_name)
    
    def test_validate_firewall_identifier_invalid_arn(self, firewall_tools):
        """Test validation of invalid firewall ARN."""
        invalid_arn = "arn:aws:invalid:format"
        with pytest.raises(ValueError, match="Invalid firewall ARN format"):
            firewall_tools._validate_firewall_identifier(invalid_arn)
    
    def test_validate_firewall_identifier_invalid_name(self, firewall_tools):
        """Test validation of invalid firewall name."""
        invalid_name = "test@firewall!"
        with pytest.raises(ValueError, match="Invalid firewall name format"):
            firewall_tools._validate_firewall_identifier(invalid_name)
    
    def test_validate_ip_address_valid(self, firewall_tools):
        """Test IP address validation with valid IPs."""
        valid_ips = ["10.0.1.1", "192.168.1.100", "2001:db8::1"]
        for ip in valid_ips:
            firewall_tools._validate_ip_address(ip)  # Should not raise
    
    def test_validate_ip_address_invalid(self, firewall_tools):
        """Test IP address validation with invalid IPs."""
        invalid_ips = ["invalid", "256.1.1.1", "10.0.1"]
        for ip in invalid_ips:
            with pytest.raises(ValueError, match="Invalid IP address format"):
                firewall_tools._validate_ip_address(ip)
    
    def test_validate_port_valid(self, firewall_tools):
        """Test port validation with valid ports."""
        valid_ports = [1, 80, 443, 8080, 65535]
        for port in valid_ports:
            firewall_tools._validate_port(port)  # Should not raise
    
    def test_validate_port_invalid(self, firewall_tools):
        """Test port validation with invalid ports."""
        invalid_ports = [0, -1, 65536, 100000]
        for port in invalid_ports:
            with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
                firewall_tools._validate_port(port)
    
    def test_parse_suricata_rule_valid(self, firewall_tools):
        """Test parsing valid Suricata rule."""
        rule = "alert tcp 10.0.0.0/8 any -> any 80 (msg:\"HTTP traffic\"; sid:1;)"
        parsed = firewall_tools._parse_suricata_rule(rule)
        
        assert parsed.action == "alert"
        assert parsed.protocol == "tcp"
        assert parsed.src_ip == "10.0.0.0/8"
        assert parsed.dst_port == "80"
        assert parsed.parsed is True
        assert parsed.raw_rule == rule
    
    def test_parse_suricata_rule_invalid(self, firewall_tools):
        """Test parsing invalid Suricata rule."""
        rule = "invalid rule format"
        parsed = firewall_tools._parse_suricata_rule(rule)
        
        assert parsed.action == "unknown"
        assert parsed.protocol == "any"
        assert parsed.parsed is False
        assert parsed.raw_rule == rule
    
    def test_check_five_tuple_match_protocol(self, firewall_tools):
        """Test 5-tuple matching with protocol check."""
        from awslabs.cloudwan_mcp_server.models.network_models import SuricataRule
        
        rule = SuricataRule(
            action="alert",
            protocol="tcp",
            src_ip="any",
            src_port="any",
            dst_ip="any",
            dst_port="80",
            raw_rule="test rule",
            parsed=True
        )
        
        # Should match TCP traffic to port 80
        assert firewall_tools._check_five_tuple_match(
            rule, "10.0.1.1", "10.0.2.1", "tcp", 12345, 80
        ) is True
        
        # Should not match UDP traffic
        assert firewall_tools._check_five_tuple_match(
            rule, "10.0.1.1", "10.0.2.1", "udp", 12345, 80
        ) is False
    
    def test_ip_matches_pattern_cidr(self, firewall_tools):
        """Test IP matching with CIDR patterns."""
        assert firewall_tools._ip_matches_pattern("10.0.1.100", "10.0.0.0/16") is True
        assert firewall_tools._ip_matches_pattern("192.168.1.100", "10.0.0.0/16") is False
    
    def test_ip_matches_pattern_exact(self, firewall_tools):
        """Test IP matching with exact patterns."""
        assert firewall_tools._ip_matches_pattern("10.0.1.100", "10.0.1.100") is True
        assert firewall_tools._ip_matches_pattern("10.0.1.100", "10.0.1.101") is False
    
    def test_port_matches_pattern_exact(self, firewall_tools):
        """Test port matching with exact patterns."""
        assert firewall_tools._port_matches_pattern(80, "80") is True
        assert firewall_tools._port_matches_pattern(80, "443") is False
    
    def test_port_matches_pattern_range(self, firewall_tools):
        """Test port matching with range patterns."""
        assert firewall_tools._port_matches_pattern(8080, "8000:9000") is True
        assert firewall_tools._port_matches_pattern(7000, "8000:9000") is False


@pytest.mark.asyncio
class TestANFWToolFunctions:
    """Test suite for ANFW tool functions."""
    
    @pytest.fixture
    def mock_firewall_clients(self):
        """Mock firewall and logs clients."""
        nfw_client = Mock()
        logs_client = Mock()
        
        # Mock firewall response
        nfw_client.describe_firewall.return_value = {
            "Firewall": {
                "FirewallName": "test-firewall",
                "FirewallArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall/test-firewall",
                "VpcId": "vpc-12345",
                "SubnetMappings": [{"SubnetId": "subnet-12345"}],
                "FirewallPolicyArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/test-policy"
            },
            "FirewallStatus": {
                "Status": "READY"
            }
        }
        
        # Mock policy response
        nfw_client.describe_firewall_policy.return_value = {
            "FirewallPolicy": {
                "StatelessRuleGroups": [],
                "StatefulRuleGroups": [
                    {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/test-stateful"}
                ],
                "StatelessDefaultActions": ["aws:pass"],
                "StatelessFragmentDefaultActions": ["aws:drop"]
            }
        }
        
        # Mock rule group response
        nfw_client.describe_rule_group.return_value = {
            "RuleGroup": {
                "RulesSource": {
                    "RulesString": "alert tcp any any -> any 80 (msg:\"HTTP traffic detected\"; sid:1; rev:1;)"
                }
            }
        }
        
        # Mock logging configuration
        nfw_client.describe_logging_configuration.return_value = {
            "LoggingConfiguration": {
                "LogDestinationConfigs": [
                    {
                        "LogType": "FLOW",
                        "LogDestinationType": "CloudWatchLogs",
                        "LogDestination": {
                            "logGroup": "/aws/network-firewall/test-firewall"
                        }
                    }
                ]
            }
        }
        
        # Mock CloudWatch Logs responses
        logs_client.start_query.return_value = {"queryId": "test-query-123"}
        logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2023-01-01T12:00:00.000Z"},
                    {"field": "@message", "value": "FLOW srcaddr=10.0.1.100 dstaddr=10.0.2.200 srcport=12345 dstport=80 protocol=6 action=ALLOW"}
                ]
            ]
        }
        
        return nfw_client, logs_client
    
    async def test_monitor_anfw_logs_success(self, mock_firewall_clients):
        """Test successful ANFW log monitoring."""
        nfw_client, logs_client = mock_firewall_clients
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_logs_client', return_value=logs_client):
            
            result = await monitor_anfw_logs("test-firewall", "flow", 60)
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert parsed_result["firewall_name"] == "test-firewall"
            assert "log_entries" in parsed_result
            assert "analysis" in parsed_result
    
    async def test_monitor_anfw_logs_invalid_firewall_name(self):
        """Test log monitoring with invalid firewall name."""
        result = await monitor_anfw_logs("invalid@name!", "flow", 60)
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "Invalid firewall name format" in parsed_result["error"]
    
    async def test_monitor_anfw_logs_invalid_log_type(self):
        """Test log monitoring with invalid log type."""
        result = await monitor_anfw_logs("test-firewall", "invalid", 60)
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "log_type must be 'flow' or 'alert'" in parsed_result["error"]
    
    async def test_monitor_anfw_logs_invalid_time_range(self):
        """Test log monitoring with invalid time range."""
        result = await monitor_anfw_logs("test-firewall", "flow", 2000)  # > 1440 minutes
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "time_range_minutes must be between 1 and 1440" in parsed_result["error"]
    
    async def test_analyze_anfw_policy_success(self, mock_firewall_clients):
        """Test successful ANFW policy analysis."""
        nfw_client, logs_client = mock_firewall_clients
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await analyze_anfw_policy("test-firewall", True)
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert "analysis" in parsed_result
            assert "firewall_details" in parsed_result["analysis"]
            assert "policy_summary" in parsed_result["analysis"]
            assert "security_recommendations" in parsed_result["analysis"]
    
    async def test_analyze_anfw_policy_invalid_identifier(self):
        """Test policy analysis with invalid identifier."""
        result = await analyze_anfw_policy("invalid@name!")
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "Invalid firewall name format" in parsed_result["error"]
    
    async def test_analyze_five_tuple_flow_success(self, mock_firewall_clients):
        """Test successful 5-tuple flow analysis."""
        nfw_client, logs_client = mock_firewall_clients
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await analyze_five_tuple_flow(
                "test-firewall", "10.0.1.100", "10.0.2.200", "TCP", 12345, 80
            )
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert "flow_analysis" in parsed_result
            assert "flow_details" in parsed_result["flow_analysis"]
            assert "policy_evaluation" in parsed_result["flow_analysis"]
    
    async def test_analyze_five_tuple_flow_invalid_ip(self):
        """Test 5-tuple flow analysis with invalid IP."""
        result = await analyze_five_tuple_flow(
            "test-firewall", "invalid-ip", "10.0.2.200", "TCP", 12345, 80
        )
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "Invalid IP address format" in parsed_result["error"]
    
    async def test_analyze_five_tuple_flow_invalid_port(self):
        """Test 5-tuple flow analysis with invalid port."""
        result = await analyze_five_tuple_flow(
            "test-firewall", "10.0.1.100", "10.0.2.200", "TCP", 70000, 80  # Invalid port > 65535
        )
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "Port must be between 1 and 65535" in parsed_result["error"]
    
    async def test_analyze_five_tuple_flow_invalid_protocol(self):
        """Test 5-tuple flow analysis with invalid protocol."""
        result = await analyze_five_tuple_flow(
            "test-firewall", "10.0.1.100", "10.0.2.200", "INVALID", 12345, 80
        )
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "Protocol must be TCP, UDP, or ICMP" in parsed_result["error"]
    
    async def test_parse_suricata_rules_success(self, mock_firewall_clients):
        """Test successful Suricata rule parsing."""
        nfw_client, logs_client = mock_firewall_clients
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await parse_suricata_rules("test-firewall", True)
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert "parsed_rules" in parsed_result
            assert "l7_analysis" in parsed_result
            assert "recommendations" in parsed_result
    
    async def test_parse_suricata_rules_invalid_firewall(self):
        """Test Suricata rule parsing with invalid firewall identifier."""
        result = await parse_suricata_rules("invalid@firewall!")
        parsed_result = json.loads(result)
        
        assert parsed_result["success"] is False
        assert "Invalid firewall name format" in parsed_result["error"]
    
    async def test_simulate_policy_changes_success(self, mock_firewall_clients):
        """Test successful policy change simulation."""
        nfw_client, logs_client = mock_firewall_clients
        
        test_flows = ["10.0.1.100:12345->10.0.2.200:80/TCP"]
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await simulate_policy_changes(
                "test-firewall", "Add deny rule for SSH traffic", test_flows
            )
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert "simulation_result" in parsed_result
            assert "impact_analysis" in parsed_result["simulation_result"]
    
    async def test_simulate_policy_changes_invalid_flow_format(self, mock_firewall_clients):
        """Test policy simulation with invalid flow format."""
        nfw_client, logs_client = mock_firewall_clients
        
        test_flows = ["invalid-flow-format"]
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await simulate_policy_changes(
                "test-firewall", "Test policy change", test_flows
            )
            parsed_result = json.loads(result)
            
            # Should still succeed but with warnings about invalid flows
            assert parsed_result["success"] is True
    
    async def test_simulate_policy_changes_default_flows(self, mock_firewall_clients):
        """Test policy simulation with default test flows."""
        nfw_client, logs_client = mock_firewall_clients
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await simulate_policy_changes(
                "test-firewall", "Test policy change"  # No test_flows provided
            )
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert parsed_result["simulation_result"]["impact_analysis"]["flows_analyzed"] == 4  # Default flows


@pytest.mark.asyncio
class TestANFWErrorHandling:
    """Test suite for ANFW error handling scenarios."""
    
    async def test_monitor_anfw_logs_client_error(self):
        """Test log monitoring with AWS client error."""
        mock_client = Mock()
        mock_client.start_query.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            operation_name='StartQuery'
        )
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_logs_client', return_value=mock_client):
            result = await monitor_anfw_logs("test-firewall", "flow", 60)
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is False
            assert "error_code" in parsed_result
    
    async def test_analyze_anfw_policy_firewall_not_found(self):
        """Test policy analysis with firewall not found."""
        mock_client = Mock()
        mock_client.describe_firewall.side_effect = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Firewall not found'}},
            operation_name='DescribeFirewall'
        )
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=mock_client):
            result = await analyze_anfw_policy("nonexistent-firewall")
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is False
            assert parsed_result["error_code"] == "ResourceNotFoundException"
    
    async def test_parse_suricata_rules_rule_group_not_found(self):
        """Test Suricata parsing with rule group not found."""
        mock_client = Mock()
        
        # Mock successful firewall and policy calls
        mock_client.describe_firewall.return_value = {
            "Firewall": {
                "FirewallName": "test-firewall",
                "FirewallArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall/test-firewall",
                "FirewallPolicyArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/test-policy"
            }
        }
        
        mock_client.describe_firewall_policy.return_value = {
            "FirewallPolicy": {
                "StatefulRuleGroups": [
                    {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/nonexistent"}
                ]
            }
        }
        
        # Mock rule group not found
        mock_client.describe_rule_group.side_effect = ClientError(
            error_response={'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Rule group not found'}},
            operation_name='DescribeRuleGroup'
        )
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=mock_client):
            result = await parse_suricata_rules("test-firewall")
            parsed_result = json.loads(result)
            
            # Should succeed but with empty rules (graceful handling)
            assert parsed_result["success"] is True
            assert len(parsed_result["parsed_rules"]) == 0


@pytest.mark.asyncio 
class TestANFWIntegration:
    """Test suite for ANFW integration scenarios."""
    
    async def test_anfw_cloudwan_integration(self, mock_firewall_clients):
        """Test ANFW integration with CloudWAN compliance analysis."""
        nfw_client, logs_client = mock_firewall_clients
        
        # Mock successful core network tools import
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.core_network.CoreNetworkTools') as mock_core_tools:
            
            result = await analyze_anfw_policy("test-firewall", include_compliance_check=True)
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert "cloudwan_compliance" in parsed_result["analysis"]
    
    async def test_anfw_path_tracing_integration(self, mock_firewall_clients):
        """Test ANFW integration with path tracing functionality."""
        nfw_client, logs_client = mock_firewall_clients
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.network_analysis.NetworkAnalysisTools') as mock_analysis_tools:
            
            result = await analyze_five_tuple_flow(
                "test-firewall", "10.0.1.100", "10.0.2.200", "TCP", 12345, 80
            )
            parsed_result = json.loads(result)
            
            assert parsed_result["success"] is True
            assert "path_integration" in parsed_result["flow_analysis"]


if __name__ == "__main__":
    pytest.main([__file__])