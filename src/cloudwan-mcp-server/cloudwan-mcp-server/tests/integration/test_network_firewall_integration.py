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

"""Integration tests for AWS Network Firewall (ANFW) tools."""

import json
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

from awslabs.cloudwan_mcp_server.tools.network_firewall import (
    monitor_anfw_logs,
    analyze_anfw_policy,
    analyze_five_tuple_flow,
    parse_suricata_rules,
    simulate_policy_changes
)


@pytest.mark.integration
class TestANFWToolsIntegration:
    """Integration test suite for all ANFW tools working together."""
    
    @pytest.fixture
    def comprehensive_firewall_setup(self):
        """Comprehensive firewall mock setup with multiple resources."""
        nfw_client = Mock()
        logs_client = Mock()
        
        # Mock multiple firewalls
        firewalls = {
            "production-firewall": {
                "Firewall": {
                    "FirewallName": "production-firewall",
                    "FirewallArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall/production-firewall",
                    "VpcId": "vpc-prod-12345",
                    "SubnetMappings": [
                        {"SubnetId": "subnet-prod-1"}, 
                        {"SubnetId": "subnet-prod-2"}
                    ],
                    "FirewallPolicyArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/production-policy"
                },
                "FirewallStatus": {"Status": "READY"}
            },
            "staging-firewall": {
                "Firewall": {
                    "FirewallName": "staging-firewall",
                    "FirewallArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall/staging-firewall",
                    "VpcId": "vpc-staging-12345",
                    "SubnetMappings": [{"SubnetId": "subnet-staging-1"}],
                    "FirewallPolicyArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/staging-policy"
                },
                "FirewallStatus": {"Status": "READY"}
            }
        }
        
        # Dynamic firewall responses based on name
        def mock_describe_firewall(**kwargs):
            if "FirewallName" in kwargs:
                name = kwargs["FirewallName"]
            else:
                # Extract from ARN
                arn = kwargs["FirewallArn"]
                name = arn.split('/')[-1]
            
            if name in firewalls:
                return firewalls[name]
            else:
                raise ClientError(
                    error_response={'Error': {'Code': 'ResourceNotFoundException', 'Message': f'Firewall {name} not found'}},
                    operation_name='DescribeFirewall'
                )
        
        nfw_client.describe_firewall.side_effect = mock_describe_firewall
        
        # Mock comprehensive policy responses
        policies = {
            "production-policy": {
                "FirewallPolicy": {
                    "StatelessRuleGroups": [
                        {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateless-rulegroup/prod-stateless"}
                    ],
                    "StatefulRuleGroups": [
                        {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/prod-stateful-web"},
                        {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/prod-stateful-security"}
                    ],
                    "StatelessDefaultActions": ["aws:forward_to_sfe"],
                    "StatelessFragmentDefaultActions": ["aws:drop"]
                }
            },
            "staging-policy": {
                "FirewallPolicy": {
                    "StatelessRuleGroups": [],
                    "StatefulRuleGroups": [
                        {"ResourceArn": "arn:aws:network-firewall:us-east-1:123456789012:stateful-rulegroup/staging-stateful"}
                    ],
                    "StatelessDefaultActions": ["aws:pass"],
                    "StatelessFragmentDefaultActions": ["aws:pass"]
                }
            }
        }
        
        def mock_describe_policy(**kwargs):
            policy_arn = kwargs["FirewallPolicyArn"]
            policy_name = policy_arn.split('/')[-1]
            if policy_name in policies:
                return policies[policy_name]
            else:
                raise ClientError(
                    error_response={'Error': {'Code': 'ResourceNotFoundException', 'Message': f'Policy {policy_name} not found'}},
                    operation_name='DescribeFirewallPolicy'
                )
        
        nfw_client.describe_firewall_policy.side_effect = mock_describe_policy
        
        # Mock rule groups with comprehensive Suricata rules
        rule_groups = {
            "prod-stateful-web": {
                "RuleGroup": {
                    "RulesSource": {
                        "RulesString": """alert http any any -> any any (msg:"HTTP GET request"; http.method; content:"GET"; sid:1001; rev:1;)
alert http any any -> any any (msg:"HTTP POST request"; http.method; content:"POST"; sid:1002; rev:1;)
drop tcp any any -> any 22 (msg:"SSH access blocked"; sid:2001; rev:1;)
alert tcp any any -> any 3389 (msg:"RDP access attempt"; sid:2002; rev:1;)"""
                    }
                }
            },
            "prod-stateful-security": {
                "RuleGroup": {
                    "RulesSource": {
                        "RulesString": """alert tls any any -> any any (msg:"TLS certificate validation"; tls.cert_subject; content:"CN="; sid:3001; rev:1;)
drop tcp any any -> any 23 (msg:"Telnet blocked"; sid:3002; rev:1;)
alert dns any any -> any any (msg:"DNS query monitoring"; dns.query; sid:4001; rev:1;)"""
                    }
                }
            },
            "staging-stateful": {
                "RuleGroup": {
                    "RulesSource": {
                        "RulesString": """pass tcp any any -> any 80 (msg:"HTTP traffic allowed in staging"; sid:5001; rev:1;)
pass tcp any any -> any 443 (msg:"HTTPS traffic allowed in staging"; sid:5002; rev:1;)"""
                    }
                }
            }
        }
        
        def mock_describe_rule_group(**kwargs):
            rule_arn = kwargs["RuleGroupArn"]
            rule_name = rule_arn.split('/')[-1]
            if rule_name in rule_groups:
                return rule_groups[rule_name]
            else:
                raise ClientError(
                    error_response={'Error': {'Code': 'ResourceNotFoundException', 'Message': f'Rule group {rule_name} not found'}},
                    operation_name='DescribeRuleGroup'
                )
        
        nfw_client.describe_rule_group.side_effect = mock_describe_rule_group
        
        # Mock logging configuration
        def mock_logging_config(**kwargs):
            firewall_arn = kwargs["FirewallArn"]
            return {
                "LoggingConfiguration": {
                    "LogDestinationConfigs": [
                        {
                            "LogType": "FLOW",
                            "LogDestinationType": "CloudWatchLogs",
                            "LogDestination": {
                                "logGroup": f"/aws/network-firewall/{firewall_arn.split('/')[-1]}"
                            }
                        },
                        {
                            "LogType": "ALERT",
                            "LogDestinationType": "CloudWatchLogs", 
                            "LogDestination": {
                                "logGroup": f"/aws/network-firewall/{firewall_arn.split('/')[-1]}-alerts"
                            }
                        }
                    ]
                }
            }
        
        nfw_client.describe_logging_configuration.side_effect = mock_logging_config
        
        # Mock comprehensive CloudWatch Logs responses
        query_results = {
            "flow": [
                [
                    {"field": "@timestamp", "value": "2023-01-01T12:00:00.000Z"},
                    {"field": "@message", "value": "FLOW srcaddr=10.0.1.100 dstaddr=172.16.2.200 srcport=12345 dstport=80 protocol=6 action=ALLOW"}
                ],
                [
                    {"field": "@timestamp", "value": "2023-01-01T12:01:00.000Z"},
                    {"field": "@message", "value": "FLOW srcaddr=10.0.1.101 dstaddr=172.16.2.200 srcport=12346 dstport=443 protocol=6 action=ALLOW"}
                ],
                [
                    {"field": "@timestamp", "value": "2023-01-01T12:02:00.000Z"}, 
                    {"field": "@message", "value": "FLOW srcaddr=192.168.1.50 dstaddr=10.0.1.200 srcport=54321 dstport=22 protocol=6 action=DENY"}
                ]
            ],
            "alert": [
                [
                    {"field": "@timestamp", "value": "2023-01-01T12:00:30.000Z"},
                    {"field": "@message", "value": "ALERT SSH access blocked from 192.168.1.50 to 10.0.1.200:22"}
                ],
                [
                    {"field": "@timestamp", "value": "2023-01-01T12:01:15.000Z"},
                    {"field": "@message", "value": "ALERT RDP access attempt from 172.16.1.100 to 10.0.2.150:3389"}
                ]
            ]
        }
        
        logs_client.start_query.return_value = {"queryId": "integration-query-123"}
        
        def mock_get_query_results(**kwargs):
            # Simulate query completion after multiple calls
            if not hasattr(mock_get_query_results, 'call_count'):
                mock_get_query_results.call_count = 0
            mock_get_query_results.call_count += 1
            
            # First few calls return Running, then Complete
            if mock_get_query_results.call_count < 3:
                return {"status": "Running"}
            else:
                # Determine log type from query string context
                log_type = "flow"  # Default
                # This would be more sophisticated in real implementation
                return {
                    "status": "Complete",
                    "results": query_results[log_type]
                }
        
        logs_client.get_query_results.side_effect = mock_get_query_results
        
        return nfw_client, logs_client
    
    @pytest.mark.asyncio
    async def test_full_anfw_workflow_production(self, comprehensive_firewall_setup):
        """Test complete ANFW workflow for production environment."""
        nfw_client, logs_client = comprehensive_firewall_setup
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_logs_client', return_value=logs_client):
            
            # Step 1: Analyze firewall policy
            policy_result = await analyze_anfw_policy("production-firewall", include_compliance_check=True)
            policy_data = json.loads(policy_result)
            
            assert policy_data["success"] is True
            assert policy_data["analysis"]["firewall_details"]["name"] == "production-firewall"
            assert policy_data["analysis"]["policy_summary"]["stateful_rule_groups"] == 2
            assert policy_data["analysis"]["policy_summary"]["stateless_rule_groups"] == 1
            
            # Step 2: Parse Suricata rules for L7 analysis
            rules_result = await parse_suricata_rules("production-firewall", analyze_l7_rules=True)
            rules_data = json.loads(rules_result)
            
            assert rules_data["success"] is True
            assert len(rules_data["parsed_rules"]) > 0
            assert "l7_analysis" in rules_data
            assert rules_data["l7_analysis"]["security_analysis"]["total_rules"] > 0
            
            # Step 3: Monitor logs for recent activity
            logs_result = await monitor_anfw_logs("production-firewall", "flow", 120)
            logs_data = json.loads(logs_result)
            
            assert logs_data["success"] is True
            assert "log_entries" in logs_data
            assert "analysis" in logs_data
            
            # Step 4: Test specific 5-tuple flows based on log analysis
            flow_result = await analyze_five_tuple_flow(
                "production-firewall", "10.0.1.100", "172.16.2.200", "TCP", 12345, 80
            )
            flow_data = json.loads(flow_result)
            
            assert flow_data["success"] is True
            assert flow_data["flow_analysis"]["flow_details"]["source_ip"] == "10.0.1.100"
            
            # Step 5: Simulate policy changes based on findings
            simulation_result = await simulate_policy_changes(
                "production-firewall",
                "Block all SSH traffic from external networks",
                ["192.168.1.50:54321->10.0.1.200:22/TCP"]
            )
            simulation_data = json.loads(simulation_result)
            
            assert simulation_data["success"] is True
            assert "simulation_result" in simulation_data
            assert "impact_analysis" in simulation_data["simulation_result"]
    
    @pytest.mark.asyncio
    async def test_anfw_cross_environment_comparison(self, comprehensive_firewall_setup):
        """Test ANFW analysis across production and staging environments."""
        nfw_client, logs_client = comprehensive_firewall_setup
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_logs_client', return_value=logs_client):
            
            # Analyze production firewall
            prod_policy = await analyze_anfw_policy("production-firewall")
            prod_data = json.loads(prod_policy)
            
            # Analyze staging firewall
            staging_policy = await analyze_anfw_policy("staging-firewall")
            staging_data = json.loads(staging_policy)
            
            # Compare configurations
            assert prod_data["success"] is True
            assert staging_data["success"] is True
            
            # Production should have more restrictive default actions
            prod_actions = prod_data["analysis"]["policy_summary"]["stateless_default_actions"]
            staging_actions = staging_data["analysis"]["policy_summary"]["stateless_default_actions"]
            
            assert "aws:forward_to_sfe" in prod_actions  # More secure
            assert "aws:pass" in staging_actions  # More permissive for testing
            
            # Production should have more rule groups
            prod_rules = prod_data["analysis"]["policy_summary"]["stateful_rule_groups"]
            staging_rules = staging_data["analysis"]["policy_summary"]["stateful_rule_groups"]
            
            assert prod_rules > staging_rules
    
    @pytest.mark.asyncio
    async def test_anfw_error_resilience(self, comprehensive_firewall_setup):
        """Test ANFW tools resilience to various error conditions."""
        nfw_client, logs_client = comprehensive_firewall_setup
        
        # Test partial failures - some operations succeed, others fail
        def failing_describe_rule_group(**kwargs):
            rule_arn = kwargs["RuleGroupArn"]
            if "security" in rule_arn:
                # Simulate intermittent failure for security rule group
                raise ClientError(
                    error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                    operation_name='DescribeRuleGroup'
                )
            else:
                # Other rule groups succeed
                return {
                    "RuleGroup": {
                        "RulesSource": {
                            "RulesString": "alert tcp any any -> any 80 (msg:\"HTTP traffic\"; sid:1; rev:1;)"
                        }
                    }
                }
        
        nfw_client.describe_rule_group.side_effect = failing_describe_rule_group
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_logs_client', return_value=logs_client):
            
            # Should handle partial failures gracefully
            result = await parse_suricata_rules("production-firewall")
            data = json.loads(result)
            
            assert data["success"] is True  # Should still succeed
            # Should have some rules (from non-failing rule groups)
            assert len(data["parsed_rules"]) > 0
    
    @pytest.mark.asyncio
    async def test_anfw_performance_under_load(self, comprehensive_firewall_setup):
        """Test ANFW tools performance under concurrent load."""
        nfw_client, logs_client = comprehensive_firewall_setup
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_logs_client', return_value=logs_client):
            
            # Simulate concurrent operations
            tasks = []
            
            # Multiple policy analyses
            for firewall in ["production-firewall", "staging-firewall"]:
                tasks.append(analyze_anfw_policy(firewall))
            
            # Multiple log monitoring requests
            for log_type in ["flow", "alert"]:
                tasks.append(monitor_anfw_logs("production-firewall", log_type, 60))
            
            # Multiple 5-tuple analyses
            test_flows = [
                ("10.0.1.100", "172.16.2.200", "TCP", 12345, 80),
                ("10.0.1.101", "172.16.2.201", "TCP", 12346, 443),
                ("192.168.1.50", "10.0.1.200", "TCP", 54321, 22)
            ]
            
            for src_ip, dst_ip, protocol, src_port, dst_port in test_flows:
                tasks.append(analyze_five_tuple_flow(
                    "production-firewall", src_ip, dst_ip, protocol, src_port, dst_port
                ))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All operations should succeed (no exceptions)
            successful_results = []
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent operation failed: {result}")
                else:
                    data = json.loads(result)
                    assert data["success"] is True
                    successful_results.append(data)
            
            # Should have completed all tasks
            assert len(successful_results) == len(tasks)
    
    @pytest.mark.asyncio
    async def test_anfw_complex_rule_parsing(self, comprehensive_firewall_setup):
        """Test ANFW complex Suricata rule parsing scenarios."""
        nfw_client, logs_client = comprehensive_firewall_setup
        
        # Add complex rule group with advanced Suricata features
        complex_rules = {
            "RuleGroup": {
                "RulesSource": {
                    "RulesString": """# Complex HTTP rules
alert http any any -> any any (msg:"Suspicious User-Agent"; http.user_agent; content:"sqlmap"; nocase; sid:10001; rev:1;)
alert http any any -> any any (msg:"PHP injection attempt"; http.uri; pcre:"/\\.php\\?.*=/"; sid:10002; rev:1;)
drop http any any -> any any (msg:"Known malware C2"; http.host; content:"malicious.example.com"; nocase; sid:10003; rev:1;)

# TLS/SSL inspection
alert tls any any -> any any (msg:"Self-signed certificate"; tls.cert_issuer; content:"CN=localhost"; nocase; sid:20001; rev:1;)
alert tls any any -> any any (msg:"Weak cipher suite"; tls.cert_serial; content:"00"; startswith; sid:20002; rev:1;)

# DNS monitoring
alert dns any any -> any any (msg:"DNS tunneling attempt"; dns.query; content:"|00 10|"; within:50; sid:30001; rev:1;)
alert dns any any -> any any (msg:"DGA domain detected"; dns.query; pcre:"/^[a-z0-9]{20,}\\.com$/"; sid:30002; rev:1;)

# File transfer monitoring
alert ftp any any -> any any (msg:"FTP file upload"; ftp.command; content:"STOR"; nocase; sid:40001; rev:1;)
alert smtp any any -> any any (msg:"Email with attachment"; file.name; content:".exe"; nocase; sid:40002; rev:1;)"""
                }
            }
        }
        
        # Override rule group response for this test
        nfw_client.describe_rule_group.return_value = complex_rules
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await parse_suricata_rules("production-firewall", analyze_l7_rules=True)
            data = json.loads(result)
            
            assert data["success"] is True
            assert len(data["parsed_rules"]) > 0
            
            # Should detect application protocols
            l7_analysis = data["l7_analysis"]
            assert "application_protocols" in l7_analysis
            assert "HTTP" in l7_analysis["application_protocols"]
            assert "TLS/SSL" in l7_analysis["application_protocols"]
            assert "DNS" in l7_analysis["application_protocols"]
            
            # Should have security analysis
            security_analysis = l7_analysis["security_analysis"]
            assert security_analysis["alert_rules"] > 0
            assert security_analysis["drop_rules"] > 0
    
    @pytest.mark.asyncio
    async def test_anfw_integration_with_cloudwan_path_tracing(self, comprehensive_firewall_setup):
        """Test ANFW integration with CloudWAN path tracing."""
        nfw_client, logs_client = comprehensive_firewall_setup
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client), \
             patch('awslabs.cloudwan_mcp_server.tools.network_analysis.NetworkAnalysisTools') as mock_path_tools:
            
            # Configure mock path tracing tools
            mock_path_instance = Mock()
            mock_path_tools.return_value = mock_path_instance
            
            result = await analyze_five_tuple_flow(
                "production-firewall", "10.0.1.100", "172.16.2.200", "TCP", 12345, 80
            )
            data = json.loads(result)
            
            assert data["success"] is True
            assert "path_integration" in data["flow_analysis"]
            assert data["flow_analysis"]["path_integration"]["path_trace_available"] is True


@pytest.mark.integration
@pytest.mark.slow
class TestANFWLongRunningOperations:
    """Integration tests for ANFW long-running operations."""
    
    @pytest.mark.asyncio
    async def test_extended_log_monitoring(self):
        """Test extended log monitoring with large time ranges."""
        # Mock for extended time range monitoring
        logs_client = Mock()
        
        # Simulate large result set
        large_results = []
        for i in range(100):  # 100 log entries
            large_results.append([
                {"field": "@timestamp", "value": f"2023-01-01T12:{i:02d}:00.000Z"},
                {"field": "@message", "value": f"FLOW srcaddr=10.0.1.{i} dstaddr=172.16.2.200 srcport={12000+i} dstport=80 protocol=6 action=ALLOW"}
            ])
        
        logs_client.start_query.return_value = {"queryId": "long-running-query-123"}
        logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": large_results
        }
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_logs_client', return_value=logs_client):
            result = await monitor_anfw_logs("production-firewall", "flow", 1440)  # 24 hours
            data = json.loads(result)
            
            assert data["success"] is True
            assert len(data["log_entries"]) == 100
            assert data["analysis"]["total_entries"] == 100
    
    @pytest.mark.asyncio
    async def test_comprehensive_policy_simulation(self):
        """Test comprehensive policy simulation with many flows."""
        nfw_client = Mock()
        
        # Mock comprehensive firewall setup
        nfw_client.describe_firewall.return_value = {
            "Firewall": {
                "FirewallName": "comprehensive-firewall",
                "FirewallArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall/comprehensive-firewall",
                "FirewallPolicyArn": "arn:aws:network-firewall:us-east-1:123456789012:firewall-policy/comprehensive-policy"
            }
        }
        
        nfw_client.describe_firewall_policy.return_value = {
            "FirewallPolicy": {
                "StatelessRuleGroups": [],
                "StatefulRuleGroups": [],
                "StatelessDefaultActions": ["aws:drop"],
                "StatelessFragmentDefaultActions": ["aws:drop"]
            }
        }
        
        # Generate many test flows
        test_flows = []
        for i in range(50):
            test_flows.append(f"10.0.1.{i}:{12000+i}->172.16.2.200:80/TCP")
            test_flows.append(f"10.0.1.{i}:{13000+i}->172.16.2.200:443/TCP")
        
        with patch('awslabs.cloudwan_mcp_server.tools.network_firewall.firewall_tools.get_network_firewall_client', return_value=nfw_client):
            result = await simulate_policy_changes(
                "comprehensive-firewall",
                "Comprehensive security policy update",
                test_flows
            )
            data = json.loads(result)
            
            assert data["success"] is True
            assert data["simulation_result"]["impact_analysis"]["flows_analyzed"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])