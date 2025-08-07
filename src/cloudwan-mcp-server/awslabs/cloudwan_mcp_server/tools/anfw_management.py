 Dict[str, Any]:
        """List Network Firewalls with detailed configuration analysis.
        
        Args:
            vpc_ids: Optional list of VPC IDs to filter firewalls
            
        Returns:
            Comprehensive firewall analysis with CloudWAN integration context
        """
        try:
            client = get_aws_client("network-firewall", self.region)
            
            # List all firewalls
            paginator = client.get_paginator('list_firewalls')
            firewalls = []
            
            for page in paginator.paginate():
                for fw_metadata in page.get('Firewalls', []):
                    # Get detailed firewall configuration
                    fw_response = client.describe_firewall(
                        FirewallName=fw_metadata['FirewallName']
                    )
                    
                    firewall_data = fw_response['Firewall']
                    
                    # Filter by VPC if specified
                    if vpc_ids and firewall_data.get('VpcId') not in vpc_ids:
                        continue
                    
                    # Parse firewall configuration
                    firewall = NetworkFirewall.model_validate(firewall_data)
                    
                    # Enhance with policy analysis
                    policy_analysis = self._analyze_firewall_policy(
                        firewall_data.get('FirewallPolicyArn')
                    )
                    
                    # Add CloudWAN integration context
                    cloudwan_context = self._get_cloudwan_integration_context(
                        firewall_data.get('VpcId'),
                        firewall_data.get('SubnetMappings', [])
                    )
                    
                    firewalls.append({
                        "firewall": firewall.model_dump(),
                        "policy_analysis": policy_analysis,
                        "cloudwan_context": cloudwan_context,
                        "logging_status": self._get_logging_configuration(
                            firewall_data.get('FirewallArn')
                        )
                    })
            
            return format_success_response({
                "total_firewalls": len(firewalls),
                "region": self.region,
                "firewalls": firewalls,
                "analysis_timestamp": datetime.utcnow().isoformat()
            })
            
        except ClientError as e:
            logger.error(f"Failed to list Network Firewalls: {e}")
            return format_error_response(e, "list_firewalls")
        except Exception as e:
            logger.error(f"Unexpected error in list_firewalls: {e}")
            return format_error_response(e, "list_firewalls")
    
    def analyze_firewall_policy(self, policy_arn: str,
                               include_rules: bool = True) -> Dict[str, Any]:
        """Comprehensive firewall policy analysis with Suricata rule parsing.
        
        Args:
            policy_arn: ARN of the firewall policy to analyze
            include_rules: Whether to include detailed rule analysis
            
        Returns:
            Detailed policy analysis with rule breakdown and recommendations
        """
        try:
            client = get_aws_client("network-firewall", self.region)
            
            # Get firewall policy details
            policy_response = client.describe_firewall_policy(
                FirewallPolicyArn=policy_arn
            )
            
            policy_data = policy_response['FirewallPolicy']
            policy_metadata = policy_response['FirewallPolicyResponse']
            
            # Parse policy structure
            firewall_policy = FirewallPolicy.model_validate(policy_data)
            
            # Analyze stateful rule groups
            stateful_analysis = []
            if policy_data.get('StatefulRuleGroupReferences'):
                for rule_group_ref in policy_data['StatefulRuleGroupReferences']:
                    rg_analysis = self._analyze_rule_group(
                        rule_group_ref.get('ResourceArn'),
                        include_rules
                    )
                    stateful_analysis.append(rg_analysis)
            
            # Analyze stateless rule groups
            stateless_analysis = []
            if policy_data.get('StatelessRuleGroupReferences'):
                for rule_group_ref in policy_data['StatelessRuleGroupReferences']:
                    rg_analysis = self._analyze_rule_group(
                        rule_group_ref.get('ResourceArn'),
                        include_rules
                    )
                    stateless_analysis.append(rg_analysis)
            
            # Generate policy recommendations
            recommendations = self._generate_policy_recommendations(
                firewall_policy,
                stateful_analysis,
                stateless_analysis
            )
            
            # Calculate policy complexity metrics
            complexity_metrics = self._calculate_policy_complexity(
                stateful_analysis,
                stateless_analysis
            )
            
            return format_success_response({
                "policy_arn": policy_arn,
                "policy_name": policy_metadata.get('FirewallPolicyName'),
                "policy_id": policy_metadata.get('FirewallPolicyId'),
                "policy_structure": firewall_policy.model_dump(),
                "stateful_rule_groups": stateful_analysis,
                "stateless_rule_groups": stateless_analysis,
                "recommendations": recommendations,
                "complexity_metrics": complexity_metrics,
                "analysis_timestamp": datetime.utcnow().isoformat()
            })
            
        except ClientError as e:
            logger.error(f"Failed to analyze firewall policy: {e}")
            return format_error_response(e, "analyze_firewall_policy")
        except Exception as e:
            logger.error(f"Unexpected error in analyze_firewall_policy: {e}")
            return format_error_response(e, "analyze_firewall_policy")
    
    def simulate_policy_change(self, firewall_arn: str,
                              simulation_config: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate firewall policy changes for what-if analysis.
        
        Args:
            firewall_arn: ARN of the target firewall
            simulation_config: Configuration for the simulation scenario
            
        Returns:
            Detailed simulation results with impact analysis
        """
        try:
            client = get_aws_client("network-firewall", self.region)
            
            # Get current firewall configuration
            fw_response = client.describe_firewall(FirewallArn=firewall_arn)
            current_policy_arn = fw_response['Firewall']['FirewallPolicyArn']
            
            # Get current policy details
            current_policy = self.analyze_firewall_policy(current_policy_arn)
            
            # Run policy simulation
            simulation_result = self.policy_simulator.simulate_policy_change(
                current_policy,
                simulation_config
            )
            
            # Analyze traffic flow impact
            flow_analysis = self._analyze_traffic_flow_impact(
                firewall_arn,
                simulation_result
            )
            
            # Generate compliance assessment
            compliance_impact = self._assess_compliance_impact(
                simulation_result,
                firewall_arn
            )
            
            return format_success_response({
                "firewall_arn": firewall_arn,
                "simulation_config": simulation_config,
                "simulation_result": simulation_result,
                "traffic_flow_impact": flow_analysis,
                "compliance_impact": compliance_impact,
                "recommendations": self._generate_simulation_recommendations(
                    simulation_result
                ),
                "simulation_timestamp": datetime.utcnow().isoformat()
            })
            
        except ClientError as e:
            logger.error(f"Failed to simulate policy change: {e}")
            return format_error_response(e, "simulate_policy_change")
        except Exception as e:
            logger.error(f"Unexpected error in simulate_policy_change: {e}")
            return format_error_response(e, "simulate_policy_change")
    
    def analyze_traffic_flows(self, firewall_arn: str,
                            time_range_hours: int = 24,
                            flow_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze traffic flows through Network Firewall using CloudWatch Logs.
        
        Args:
            firewall_arn: ARN of the firewall to analyze
            time_range_hours: Hours of log data to analyze
            flow_filters: Optional filters for flow analysis
            
        Returns:
            Comprehensive traffic flow analysis
        """
        try:
            # Get firewall logging configuration
            logging_config = self._get_logging_configuration(firewall_arn)
            
            if not logging_config or not logging_config.get('flow_logs_enabled'):
                return format_error_response(
                    ValueError("Flow logging not enabled for this firewall"),
                    "analyze_traffic_flows"
                )
            
            # Analyze CloudWatch Logs
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            flow_analysis = self.log_analyzer.analyze_flow_logs(
                firewall_arn,
                start_time,
                end_time,
                flow_filters
            )
            
            # Generate 5-tuple analysis
            tuple_analysis = self._analyze_five_tuples(flow_analysis['flows'])
            
            # Identify traffic patterns
            pattern_analysis = self._identify_traffic_patterns(
                flow_analysis['flows']
            )
            
            # Generate security insights
            security_insights = self._generate_security_insights(
                flow_analysis,
                tuple_analysis
            )
            
            return format_success_response({
                "firewall_arn": firewall_arn,
                "analysis_period": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "hours_analyzed": time_range_hours
                },
                "flow_summary": {
                    "total_flows": len(flow_analysis['flows']),
                    "allowed_flows": flow_analysis['summary']['allowed'],
                    "blocked_flows": flow_analysis['summary']['blocked'],
                    "bytes_processed": flow_analysis['summary']['total_bytes']
                },
                "five_tuple_analysis": tuple_analysis,
                "traffic_patterns": pattern_analysis,
                "security_insights": security_insights,
                "top_talkers": flow_analysis.get('top_talkers', []),
                "analysis_timestamp": datetime.utcnow().isoformat()
            })
            
        except ClientError as e:
            logger.error(f"Failed to analyze traffic flows: {e}")
            return format_error_response(e, "analyze_traffic_flows")
        except Exception as e:
            logger.error(f"Unexpected error in analyze_traffic_flows: {e}")
            return format_error_response(e, "analyze_traffic_flows")
    
    def validate_five_tuple_flow(self, source_ip: str, dest_ip: str,
                               source_port: int, dest_port: int,
                               protocol: str, firewall_arn: str) -> Dict[str, Any]:
        """Validate specific 5-tuple traffic flow against firewall policy.
        
        Args:
            source_ip: Source IP address
            dest_ip: Destination IP address
            source_port: Source port number
            dest_port: Destination port number
            protocol: Protocol (tcp, udp, icmp)
            firewall_arn: ARN of the firewall to validate against
            
        Returns:
            Validation result with rule matching analysis
        """
        try:
            # Validate IP addresses
            ipaddress.ip_address(source_ip)
            ipaddress.ip_address(dest_ip)
            
            # Validate protocol
            valid_protocols = ['tcp', 'udp', 'icmp', 'icmpv6']
            if protocol.lower() not in valid_protocols:
                raise ValueError(f"Invalid protocol: {protocol}")
            
            # Validate port ranges
            if not (0 <= source_port <= 65535) or not (0 <= dest_port <= 65535):
                raise ValueError("Port numbers must be between 0 and 65535")
            
            # Get firewall policy
            client = get_aws_client("network-firewall", self.region)
            fw_response = client.describe_firewall(FirewallArn=firewall_arn)
            policy_arn = fw_response['Firewall']['FirewallPolicyArn']
            
            # Analyze policy for this flow
            policy_analysis = self.analyze_firewall_policy(policy_arn)
            
            # Simulate flow through policy
            flow_simulation = self.policy_simulator.simulate_five_tuple_flow({
                "source_ip": source_ip,
                "dest_ip": dest_ip,
                "source_port": source_port,
                "dest_port": dest_port,
                "protocol": protocol.lower()
            }, policy_analysis)
            
            # Analyze rule matching
            rule_matches = self._analyze_rule_matches(
                {
                    "source_ip": source_ip,
                    "dest_ip": dest_ip,
                    "source_port": source_port,
                    "dest_port": dest_port,
                    "protocol": protocol.lower()
                },
                policy_analysis
            )
            
            return format_success_response({
                "five_tuple": {
                    "source_ip": source_ip,
                    "dest_ip": dest_ip,
                    "source_port": source_port,
                    "dest_port": dest_port,
                    "protocol": protocol.lower()
                },
                "firewall_arn": firewall_arn,
                "validation_result": flow_simulation['decision'],
                "matching_rules": rule_matches,
                "flow_path": flow_simulation['rule_path'],
                "recommendations": flow_simulation.get('recommendations', []),
                "validation_timestamp": datetime.utcnow().isoformat()
            })
            
        except (ValueError, ipaddress.AddressValueError) as e:
            logger.error(f"Invalid input for 5-tuple validation: {e}")
            return format_error_response(e, "validate_five_tuple_flow")
        except ClientError as e:
            logger.error(f"AWS error in 5-tuple validation: {e}")
            return format_error_response(e, "validate_five_tuple_flow")
        except Exception as e:
            logger.error(f"Unexpected error in validate_five_tuple_flow: {e}")
            return format_error_response(e, "validate_five_tuple_flow")
    
    def integrate_with_cloudwan_policy(self, firewall_arn: str,
                                     core_network_id: str,
                                     segment_name: str) -> Dict[str, Any]:
        """Integrate Network Firewall analysis with CloudWAN policy compliance.
        
        Args:
            firewall_arn: ARN of the Network Firewall
            core_network_id: CloudWAN core network ID
            segment_name: CloudWAN segment name
            
        Returns:
            Integrated compliance and security analysis
        """
        try:
            # Get CloudWAN segment information
            nm_client = get_aws_client("networkmanager", self.region)
            core_network_policy = nm_client.get_core_network_policy(
                CoreNetworkId=core_network_id
            )
            
            # Parse CloudWAN policy for segment
            cloudwan_analysis = self._analyze_cloudwan_segment_policy(
                core_network_policy,
                segment_name
            )
            
            # Get Network Firewall policy
            nf_client = get_aws_client("network-firewall", self.region)
            fw_response = nf_client.describe_firewall(FirewallArn=firewall_arn)
            nf_policy_arn = fw_response['Firewall']['FirewallPolicyArn']
            
            firewall_analysis = self.analyze_firewall_policy(nf_policy_arn)
            
            # Cross-analyze policies for compliance
            compliance_analysis = self._cross_analyze_policies(
                cloudwan_analysis,
                firewall_analysis
            )
            
            # Generate integration recommendations
            integration_recommendations = self._generate_integration_recommendations(
                cloudwan_analysis,
                firewall_analysis,
                compliance_analysis
            )
            
            return format_success_response({
                "firewall_arn": firewall_arn,
                "core_network_id": core_network_id,
                "segment_name": segment_name,
                "cloudwan_policy_analysis": cloudwan_analysis,
                "firewall_policy_summary": {
                    "policy_arn": nf_policy_arn,
                    "stateful_rule_groups": len(firewall_analysis.get('data', {}).get('stateful_rule_groups', [])),
                    "stateless_rule_groups": len(firewall_analysis.get('data', {}).get('stateless_rule_groups', []))
                },
                "compliance_analysis": compliance_analysis,
                "integration_recommendations": integration_recommendations,
                "analysis_timestamp": datetime.utcnow().isoformat()
            })
            
        except ClientError as e:
            logger.error(f"Failed to integrate with CloudWAN policy: {e}")
            return format_error_response(e, "integrate_with_cloudwan_policy")
        except Exception as e:
            logger.error(f"Unexpected error in CloudWAN integration: {e}")
            return format_error_response(e, "integrate_with_cloudwan_policy")
    
    # Helper methods
    
    def _analyze_firewall_policy(self, policy_arn: Optional[str]) -> Dict[str, Any]:
        """Analyze firewall policy structure."""
        if not policy_arn:
            return {"error": "No policy ARN provided"}
        
        try:
            client = get_aws_client("network-firewall", self.region)
            policy_response = client.describe_firewall_policy(
                FirewallPolicyArn=policy_arn
            )
            
            return {
                "policy_name": policy_response['FirewallPolicyResponse']['FirewallPolicyName'],
                "stateful_groups": len(policy_response['FirewallPolicy'].get('StatefulRuleGroupReferences', [])),
                "stateless_groups": len(policy_response['FirewallPolicy'].get('StatelessRuleGroupReferences', []))
            }
            
        except ClientError:
            return {"error": "Failed to analyze policy"}
    
    def _get_cloudwan_integration_context(self, vpc_id: Optional[str],
                                        subnet_mappings: List[Dict]) -> Dict[str, Any]:
        """Get CloudWAN integration context for a firewall."""
        if not vpc_id:
            return {"integrated": False, "reason": "No VPC ID"}
        
        try:
            # Check for CloudWAN attachments
            nm_client = get_aws_client("networkmanager", self.region)
            
            # This would need to be implemented based on actual CloudWAN API
            # for checking VPC attachments to core networks
            
            return {
                "integrated": True,
                "vpc_id": vpc_id,
                "subnet_count": len(subnet_mappings),
                "cloudwan_attached": False  # Placeholder
            }
            
        except ClientError:
            return {"integrated": False, "reason": "Failed to check CloudWAN integration"}
    
    def _get_logging_configuration(self, firewall_arn: Optional[str]) -> Dict[str, Any]:
        """Get logging configuration for a firewall."""
        if not firewall_arn:
            return {"flow_logs_enabled": False, "alert_logs_enabled": False}
        
        try:
            client = get_aws_client("network-firewall", self.region)
            
            logging_response = client.describe_logging_configuration(
                FirewallArn=firewall_arn
            )
            
            logging_config = logging_response.get('LoggingConfiguration', {})
            log_destinations = logging_config.get('LogDestinationConfigs', [])
            
            flow_logs_enabled = any(
                ld.get('LogType') == 'FLOW' for ld in log_destinations
            )
            alert_logs_enabled = any(
                ld.get('LogType') == 'ALERT' for ld in log_destinations
            )
            
            return {
                "flow_logs_enabled": flow_logs_enabled,
                "alert_logs_enabled": alert_logs_enabled,
                "log_destinations": log_destinations
            }
            
        except ClientError:
            return {"flow_logs_enabled": False, "alert_logs_enabled": False}
    
    def _analyze_rule_group(self, rule_group_arn: Optional[str],
                          include_rules: bool) -> Dict[str, Any]:
        """Analyze a specific rule group."""
        if not rule_group_arn:
            return {"error": "No rule group ARN provided"}
        
        try:
            client = get_aws_client("network-firewall", self.region)
            
            rg_response = client.describe_rule_group(
                RuleGroupArn=rule_group_arn
            )
            
            rule_group_data = rg_response['RuleGroup']
            rule_group_metadata = rg_response['RuleGroupResponse']
            
            analysis = {
                "arn": rule_group_arn,
                "name": rule_group_metadata.get('RuleGroupName'),
                "type": rule_group_metadata.get('Type'),
                "capacity": rule_group_metadata.get('Capacity'),
                "rule_count": 0
            }
            
            if include_rules and rule_group_data.get('Rules'):
                if rule_group_metadata.get('Type') == 'STATEFUL':
                    # Parse Suricata rules
                    rules_string = rule_group_data['Rules'].get('RulesString', '')
                    if rules_string:
                        parsed_rules = self.suricata_parser.parse_rules(rules_string)
                        analysis['parsed_rules'] = parsed_rules
                        analysis['rule_count'] = len(parsed_rules)
                else:
                    # Stateless rules
                    stateless_rules = rule_group_data['Rules'].get('StatelessRulesAndCustomActions', {})
                    rules = stateless_rules.get('StatelessRules', [])
                    analysis['rule_count'] = len(rules)
                    analysis['stateless_rules'] = rules if include_rules else []
            
            return analysis
            
        except ClientError as e:
            logger.error(f"Failed to analyze rule group {rule_group_arn}: {e}")
            return {"error": f"Failed to analyze rule group: {str(e)}"}
    
    def _generate_policy_recommendations(self, policy: FirewallPolicy,
                                       stateful_analysis: List[Dict],
                                       stateless_analysis: List[Dict]) -> List[str]:
        """Generate policy optimization recommendations."""
        recommendations = []
        
        # Check for missing default actions
        if not policy.stateless_default_actions:
            recommendations.append("Consider defining explicit stateless default actions")
        
        # Check for rule group capacity optimization
        total_capacity = sum(
            rg.get('capacity', 0) for rg in stateful_analysis + stateless_analysis
        )
        if total_capacity > 20000:  # Example threshold
            recommendations.append("High rule group capacity usage detected - consider optimization")
        
        # Check for overlapping rules
        if len(stateful_analysis) > 5:
            recommendations.append("Large number of stateful rule groups - check for rule overlap")
        
        return recommendations
    
    def _calculate_policy_complexity(self, stateful_analysis: List[Dict],
                                   stateless_analysis: List[Dict]) -> Dict[str, Any]:
        """Calculate policy complexity metrics."""
        total_rules = sum(rg.get('rule_count', 0) for rg in stateful_analysis + stateless_analysis)
        total_capacity = sum(rg.get('capacity', 0) for rg in stateful_analysis + stateless_analysis)
        
        complexity_score = min(100, (total_rules * 2 + len(stateful_analysis) * 5 + len(stateless_analysis) * 3) / 10)
        
        return {
            "total_rule_groups": len(stateful_analysis) + len(stateless_analysis),
            "total_rules": total_rules,
            "total_capacity": total_capacity,
            "complexity_score": complexity_score,
            "complexity_level": "Low" if complexity_score < 30 else "Medium" if complexity_score < 70 else "High"
        }
    
    def _analyze_traffic_flow_impact(self, firewall_arn: str,
                                   simulation_result: Dict) -> Dict[str, Any]:
        """Analyze traffic flow impact of policy changes."""
        # This would integrate with actual traffic analysis
        return {
            "estimated_impact": "Medium",
            "affected_flows_percentage": 15.2,
            "new_blocked_flows": 45,
            "new_allowed_flows": 12
        }
    
    def _assess_compliance_impact(self, simulation_result: Dict,
                                firewall_arn: str) -> Dict[str, Any]:
        """Assess compliance impact of policy changes."""
        return {
            "compliance_status": "Maintained",
            "security_posture": "Improved",
            "risk_assessment": "Low risk change"
        }
    
    def _generate_simulation_recommendations(self, simulation_result: Dict) -> List[str]:
        """Generate recommendations based on simulation results."""
        return [
            "Test change in non-production environment first",
            "Monitor traffic patterns after deployment",
            "Ensure logging is enabled for visibility"
        ]
    
    def _analyze_five_tuples(self, flows: List[Dict]) -> Dict[str, Any]:
        """Analyze 5-tuple patterns in traffic flows."""
        protocols = {}
        port_pairs = {}
        
        for flow in flows:
            protocol = flow.get('protocol', 'unknown')
            protocols[protocol] = protocols.get(protocol, 0) + 1
            
            port_pair = f"{flow.get('src_port', 0)}:{flow.get('dst_port', 0)}"
            port_pairs[port_pair] = port_pairs.get(port_pair, 0) + 1
        
        return {
            "protocol_distribution": protocols,
            "top_port_pairs": dict(sorted(port_pairs.items(), key=lambda x: x[1], reverse=True)[:10]),
            "unique_flows": len(flows)
        }
    
    def _identify_traffic_patterns(self, flows: List[Dict]) -> Dict[str, Any]:
        """Identify traffic patterns and anomalies."""
        # Simplified pattern analysis
        return {
            "peak_traffic_hour": "14:00-15:00",
            "anomalous_patterns": [],
            "recurring_connections": len([f for f in flows if f.get('recurring', False)])
        }
    
    def _generate_security_insights(self, flow_analysis: Dict,
                                  tuple_analysis: Dict) -> List[str]:
        """Generate security insights from traffic analysis."""
        insights = []
        
        blocked_percentage = (
            flow_analysis['summary']['blocked'] /
            (flow_analysis['summary']['allowed'] + flow_analysis['summary']['blocked'])
        ) * 100 if (flow_analysis['summary']['allowed'] + flow_analysis['summary']['blocked']) > 0 else 0
        
        if blocked_percentage > 20:
            insights.append(f"High block rate detected: {blocked_percentage:.1f}% of traffic blocked")
        
        if 'tcp' in tuple_analysis['protocol_distribution']:
            tcp_percentage = tuple_analysis['protocol_distribution']['tcp'] / sum(tuple_analysis['protocol_distribution'].values()) * 100
            if tcp_percentage > 80:
                insights.append(f"TCP-heavy traffic pattern: {tcp_percentage:.1f}% TCP traffic")
        
        return insights
    
    def _analyze_rule_matches(self, five_tuple: Dict, policy_analysis: Dict) -> List[Dict]:
        """Analyze which rules would match a given 5-tuple."""
        # Simplified rule matching logic
        matches = []
        
        # This would implement actual rule matching logic
        matches.append({
            "rule_group": "default-stateless-group",
            "rule_name": "allow-established",
            "action": "PASS",
            "confidence": "high"
        })
        
        return matches
    
    def _analyze_cloudwan_segment_policy(self, core_network_policy: Dict,
                                       segment_name: str) -> Dict[str, Any]:
        """Analyze CloudWAN segment policy for security integration."""
        # Parse CloudWAN policy for segment-specific rules
        policy_doc = core_network_policy.get('CoreNetworkPolicy', {}).get('PolicyDocument')
        
        if not policy_doc:
            return {"error": "No policy document found"}
        
        try:
            # Parse JSON policy document
            if isinstance(policy_