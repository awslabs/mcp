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


async def get_path_trace_methodology():
    """Comprehensive AWS network path tracing guide for LLM consumption.

    Returns structured guidance for analyzing network connectivity between
    AWS resources across VPC, Transit Gateway, Cloud WAN, and hybrid networks.

    THIS IS MANDATORY STEP BEFORE DOING PATH TRACE IN AWS
    """
    return {
        'methodology': {
            'overview': 'AWS network path tracing follows a systematic approach analyzing each network layer from source to destination',
            'mandatory_sequence': [
                '1. DISCOVER: Identify source and destination network interfaces',
                '2. ROUTE: Trace routing decisions at each hop',
                '3. SECURE: Analyze security controls (SGs, NACLs, firewalls)',
                '4. VERIFY: Confirm end-to-end reachability',
                '5. DIAGNOSE: Identify specific failure points and remediation',
            ],
            'critical_requirements': [
                'NEVER skip steps in the sequence',
                'Handle ALL tool errors before proceeding',
                'Verify each step completes successfully',
                'Document failures and retry with different approaches or validate from user',
            ],
        },
        'step_by_step_process': {
            'step_1_discovery': {
                'objective': 'Locate network interfaces for source and destination',
                'mandatory_tools': ['find_ip_address', 'get_eni_details'],
                'key_information': [
                    'ENI ID, VPC ID, Subnet ID, AZ',
                    'Private/Public IP addresses',
                    'Security Group IDs',
                    'Route table associations',
                ],
                'error_handling': {
                    'ip_not_found': {
                        'action': 'Try find_ip_address with all_regions=true',
                        'fallback': 'Check if IP is external/on-premises',
                    },
                    'multiple_enis': {
                        'action': 'Analyze ALL paths - load balancer or multi-homed instance',
                        'requirement': 'Document each path separately',
                    },
                    'access_denied': {
                        'action': 'Request different AWS profile or region',
                        'requirement': 'Cannot proceed without ENI details',
                    },
                },
                'validation_criteria': [
                    'Both source and destination ENIs identified',
                    'VPC and subnet information retrieved',
                    'Security group IDs collected',
                ],
            },
            'step_2_routing_analysis': {
                'objective': 'Trace packet routing decisions hop by hop',
                'routing_scenarios': {
                    'same_vpc': {
                        'mandatory_tools': ['get_vpc_network_details'],
                        'analysis': 'Check route tables for both subnets, verify local routing',
                        'validation': 'Confirm local VPC CIDR routes exist',
                    },
                    'cross_vpc_tgw': {
                        'mandatory_tools': [
                            'get_transit_gateway_details',
                            'get_transit_gateway_routes',
                            'get_all_transit_gateway_routes',
                        ],
                        'analysis': 'Check TGW route table associations and propagations',
                        'validation': 'Verify routes exist in both directions',
                    },
                    'cross_vpc_cloudwan': {
                        'mandatory_tools': [
                            'get_cloudwan_details',
                            'get_cloudwan_routes',
                            'get_cloudwan_attachment_details',
                        ],
                        'analysis': 'Check segment routing and policy-based forwarding',
                        'validation': 'Confirm attachments in correct segments',
                    },
                    'via_peering': {
                        'mandatory_tools': ['get_vpc_network_details'],
                        'analysis': 'Verify peering connection and route table entries',
                        'validation': 'Check peering status and route propagation',
                    },
                    'internet_gateway': {
                        'mandatory_tools': ['get_vpc_network_details'],
                        'analysis': 'Verify IGW attachment and 0.0.0.0/0 routes',
                        'validation': 'Confirm public subnet configuration',
                    },
                    'nat_gateway': {
                        'mandatory_tools': ['get_vpc_network_details'],
                        'analysis': 'Check NAT Gateway health and route table entries',
                        'validation': 'Verify outbound-only connectivity',
                    },
                },
                'error_handling': {
                    'route_not_found': {
                        'action': 'Check for more specific routes or default routes',
                        'requirement': 'Document exact missing route',
                    },
                    'conflicting_routes': {
                        'action': 'Apply longest prefix match rule',
                        'requirement': 'Document which route wins and why',
                    },
                    'tgw_not_registered': {
                        'action': 'Cannot get TGW routes without Network Manager registration',
                        'requirement': 'Guide user to register TGW first',
                    },
                },
            },
            'step_3_security_analysis': {
                'objective': 'Verify security controls allow required traffic',
                'security_layers': {
                    'security_groups': {
                        'behavior': 'Stateful - return traffic automatically allowed',
                        'direction': 'Check source outbound AND destination inbound rules',
                        'rule_evaluation': 'First matching ALLOW rule permits traffic',
                        'mandatory_checks': [
                            'Source ENI outbound rules',
                            'Destination ENI inbound rules',
                            'Referenced security group rules',
                            'Protocol/port combinations',
                        ],
                        'common_issues': [
                            'Missing protocol/port combinations',
                            'Incorrect source/destination CIDR blocks',
                            'Referenced security groups not properly configured',
                        ],
                    },
                    'network_acls': {
                        'behavior': 'Stateless - both directions must be explicitly allowed',
                        'rule_evaluation': 'Lowest numbered rule wins',
                        'direction': 'Check outbound at source subnet AND inbound at destination subnet',
                        'default_behavior': 'Default NACL allows all traffic, custom NACLs deny by default',
                        'mandatory_checks': [
                            'Source subnet outbound NACL rules',
                            'Destination subnet inbound NACL rules',
                            'Ephemeral port ranges for return traffic',
                            'Rule numbering and precedence',
                        ],
                    },
                    'network_firewall': {
                        'mandatory_tools': [
                            'get_firewall_rules',
                            'get_network_firewall_flow_logs',
                        ],
                        'detection_tools': ['detect_tgw_inspection', 'detect_cloudwan_inspection'],
                        'rule_types': {
                            'stateless': 'Evaluated first, fast path for simple allow/deny',
                            'stateful': 'Deep packet inspection, can block based on application layer',
                        },
                        'analysis_requirements': [
                            'Check if firewall is in traffic path',
                            'Analyze both stateless and stateful rules',
                            'Verify rule order and precedence',
                        ],
                    },
                },
                'error_handling': {
                    'sg_rule_conflicts': {
                        'action': 'Document which rule takes precedence',
                        'requirement': 'Explain allow vs deny behavior',
                    },
                    'nacl_asymmetric': {
                        'action': 'Check both inbound and outbound rules',
                        'requirement': 'Verify ephemeral port ranges',
                    },
                    'firewall_not_found': {
                        'action': 'Use detection tools to confirm no inspection',
                        'requirement': 'Document inspection status',
                    },
                },
            },
            'step_4_verification': {
                'objective': 'Confirm end-to-end connectivity and identify failures',
                'verification_methods': {
                    'flow_logs': {
                        'vpc_flows': {
                            'tool': 'get_vpc_flow_logs',
                            'purpose': 'Shows accept/reject at ENI level',
                            'filters': ['srcaddr', 'dstaddr', 'srcport', 'dstport', 'action'],
                        },
                        'tgw_flows': {
                            'tool': 'get_transit_gateway_flow_logs',
                            'purpose': 'Shows inter-VPC traffic',
                            'filters': ['srcaddr', 'dstaddr', 'tgw_attachment_id'],
                        },
                        'firewall_flows': {
                            'tool': 'get_network_firewall_flow_logs',
                            'purpose': 'Shows firewall decisions',
                            'filters': ['srcaddr', 'dstaddr', 'srcport', 'dstport'],
                        },
                    },
                    'cloudwan_logs': {
                        'tool': 'get_cloudwan_logs',
                        'purpose': 'Shows topology and routing changes',
                        'filters': ['event_type', 'time_period'],
                    },
                },
                'error_handling': {
                    'no_flow_logs': {
                        'action': 'Enable flow logs first, then wait for data',
                        'requirement': 'Cannot verify without flow log data',
                    },
                    'flow_logs_show_reject': {
                        'action': 'Identify rejecting component from flow log fields',
                        'requirement': 'Map rejection to specific security control',
                    },
                    'intermittent_failures': {
                        'action': 'Check for asymmetric routing or load balancing',
                        'requirement': 'Analyze multiple flow log entries',
                    },
                },
                'common_patterns': {
                    'connection_timeout': 'Usually routing or security group issue',
                    'connection_refused': 'Service not listening, check application layer',
                    'intermittent_failures': 'Check for asymmetric routing or NAT issues',
                },
            },
            'step_5_diagnosis': {
                'objective': 'Identify specific failure points and provide remediation',
                'failure_analysis': {
                    'routing_failures': {
                        'symptoms': ['No route to destination', 'Traffic going wrong direction'],
                        'tools': ['get_vpc_network_details', 'get_transit_gateway_routes'],
                        'remediation': 'Add missing routes or fix route priorities',
                    },
                    'security_failures': {
                        'symptoms': ['Flow logs show REJECT', 'Connection timeout'],
                        'tools': ['get_eni_details', 'get_vpc_network_details'],
                        'remediation': 'Modify security group or NACL rules',
                    },
                    'firewall_failures': {
                        'symptoms': ['Traffic blocked at firewall', 'Unexpected drops'],
                        'tools': ['get_firewall_rules', 'get_network_firewall_flow_logs'],
                        'remediation': 'Update firewall rules or policies',
                    },
                },
                'mandatory_output': {
                    'connectivity_verdict': 'PASS/FAIL with confidence level and reasoning',
                    'working_protocols': 'List specific protocols/ports that will succeed',
                    'blocked_traffic': 'List what fails and the exact blocking component',
                    'remediation_steps': 'Specific configuration changes with exact commands',
                    'verification_commands': 'How to test the fix after implementation',
                },
            },
        },
        'service_specific_guidance': {
            'cloud_wan': {
                'key_concepts': [
                    'Segments isolate traffic domains',
                    'Network Function Groups provide service insertion',
                    'Policy-based routing overrides traditional routing',
                    'Attachments determine segment membership',
                ],
                'mandatory_tools': [
                    'get_cloudwan_details',
                    'get_cloudwan_routes',
                    'get_cloudwan_attachment_details',
                    'detect_cloudwan_inspection',
                ],
                'troubleshooting_sequence': [
                    '1. Verify attachment is in correct segment',
                    '2. Check segment routing policy',
                    '3. Analyze route tables for specific region/segment',
                    '4. Review policy changes in logs',
                    '5. Check for Network Function Group inspection',
                ],
                'error_handling': {
                    'attachment_wrong_segment': 'Use get_cloudwan_attachment_details to verify',
                    'policy_conflicts': 'Check policy document in get_cloudwan_details',
                    'nfg_blocking': 'Use detect_cloudwan_inspection to identify',
                },
            },
            'transit_gateway': {
                'key_concepts': [
                    'Route table associations determine which routes an attachment can use',
                    'Route propagations determine which routes are learned',
                    'Default route table behavior vs custom route tables',
                    'Cross-region peering for inter-region connectivity',
                ],
                'mandatory_tools': [
                    'get_transit_gateway_details',
                    'get_transit_gateway_routes',
                    'get_all_transit_gateway_routes',
                    'detect_tgw_inspection',
                ],
                'troubleshooting_sequence': [
                    '1. Check route table associations for source/destination attachments',
                    '2. Verify route propagation settings',
                    '3. Analyze specific routes with filters',
                    '4. Check for route conflicts or missing routes',
                    '5. Verify firewall inspection if present',
                ],
                'error_handling': {
                    'tgw_not_registered': 'Guide user to register with Network Manager',
                    'route_conflicts': 'Apply longest prefix match rule',
                    'missing_associations': 'Check attachment route table associations',
                },
            },
            'vpc_networking': {
                'subnet_types': {
                    'public': 'Has route to Internet Gateway (0.0.0.0/0 -> igw-xxx)',
                    'private': 'No direct internet route, may use NAT Gateway',
                    'isolated': 'No internet connectivity at all',
                },
                'mandatory_tools': ['get_vpc_network_details', 'get_eni_details'],
                'nat_gateway': {
                    'purpose': 'Provides outbound internet for private subnets',
                    'limitations': 'No inbound connectivity, SNAT port exhaustion possible',
                    'troubleshooting': 'Check route tables and NAT Gateway health',
                },
                'error_handling': {
                    'no_internet_access': 'Check for IGW attachment and routes',
                    'nat_issues': 'Verify NAT Gateway health and route tables',
                    'subnet_isolation': 'Confirm intended isolation vs misconfiguration',
                },
            },
        },
        'common_failure_patterns': {
            'asymmetric_routing': {
                'description': 'Forward and return paths differ, breaks stateful connections',
                'detection': 'Flow logs show traffic in one direction only',
                'resolution': 'Ensure symmetric routing or use connection tracking',
                'tools': ['get_vpc_flow_logs', 'get_transit_gateway_flow_logs'],
            },
            'ephemeral_ports': {
                'description': 'Return traffic blocked due to dynamic port ranges',
                'detection': 'Outbound works but return traffic fails',
                'resolution': 'Allow ephemeral port ranges (32768-65535) in security groups',
                'tools': ['get_eni_details', 'get_vpc_network_details'],
            },
            'firewall_inspection': {
                'description': 'Traffic blocked by network firewalls in path',
                'detection': 'Use inspection detection tools',
                'resolution': 'Update firewall rules or bypass inspection',
                'tools': [
                    'detect_tgw_inspection',
                    'detect_cloudwan_inspection',
                    'get_firewall_rules',
                ],
            },
        },
        'critical_best_practices': [
            'MANDATORY: Always call get_path_trace_methodology before beginning analysis',
            'MANDATORY: Follow the 5-step sequence without skipping any steps',
            'MANDATORY: Handle all tool errors before proceeding to next step',
            'MANDATORY: Validate each step completes successfully before continuing',
            'Use find_ip_address to locate network interfaces from IP addresses',
            'Check routing before security - no point analyzing security if routing fails',
            'Analyze both directions of traffic flow, especially for stateless protocols',
            'Consider intermediate hops like NAT Gateways and Network Firewalls',
            'Use inspection detection tools to identify firewalls in path',
            'Use flow logs to confirm actual traffic patterns vs theoretical analysis',
            'Provide specific remediation steps with exact commands, not generic advice',
            'Test connectivity after implementing fixes to confirm resolution',
            'Document confidence level in all verdicts with supporting evidence',
        ],
    }
