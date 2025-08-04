"""
LLM-powered validators for CloudWAN network analysis tools.

This module provides specialized validation classes that leverage LLM capabilities
for complex network configuration analysis and security assessment.
"""

import logging
from typing import Any, Dict, List
from abc import ABC, abstractmethod

from .manager import LLMManager, LLMValidationError

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """Base class for LLM-powered validators."""
    
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def validate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform validation using LLM assistance."""
        pass
    
    def _create_validation_prompt(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """Create a structured validation prompt."""
        return f"""
{base_prompt}

Please analyze the provided configuration and return a JSON response with the following structure:
{{
    "validation_status": "valid|invalid|warning",
    "risk_level": "low|medium|high|critical",
    "security_score": 0.0-1.0,
    "findings": [
        {{
            "type": "error|warning|info",
            "category": "security|performance|compliance|configuration",
            "message": "Description of the finding",
            "severity": "low|medium|high|critical",
            "recommendation": "Specific action to take"
        }}
    ],
    "recommendations": [
        "High-level recommendations for improvement"
    ],
    "compliance_status": {{
        "pci_dss": "compliant|non_compliant|partial",
        "nist": "compliant|non_compliant|partial",
        "cis": "compliant|non_compliant|partial"
    }}
}}

Focus on:
1. Security vulnerabilities and misconfigurations
2. Performance optimization opportunities
3. Compliance with security best practices
4. Operational reliability concerns
"""


class FirewallPolicyValidator(BaseValidator):
    """LLM-powered validator for AWS Network Firewall policies."""
    
    async def validate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate firewall policy configuration."""
        
        if not self.llm_manager.config.firewall_validation_enabled:
            return {"validation_skipped": "firewall_validation_disabled"}
        
        prompt = self._create_firewall_validation_prompt()
        
        try:
            result = await self.llm_manager.validate_with_llm(
                validation_type="firewall",
                prompt=prompt,
                context=context,
                structured_output=True
            )
            
            # Post-process result to add firewall-specific analysis
            enhanced_result = await self._enhance_firewall_analysis(result, context)
            
            return enhanced_result
            
        except LLMValidationError as e:
            self.logger.error(f"Firewall validation failed: {e}")
            return {
                "validation_status": "error",
                "error": str(e),
                "fallback_used": self.llm_manager.config.fallback_to_heuristics
            }
    
    def _create_firewall_validation_prompt(self) -> str:
        """Create firewall-specific validation prompt."""
        
        return self._create_validation_prompt(
            """
You are an expert AWS Network Firewall security analyst. Analyze the provided firewall policy configuration for security effectiveness, rule conflicts, and compliance issues.

Pay special attention to:
1. **CRITICAL**: Ensure there are blocking rules (drop/reject) - alert-only policies allow all traffic
2. **Rule Conflicts**: Duplicate rules, contradictory actions, rule shadowing
3. **Suricata Rule Quality**: Pattern specificity, false positive risk, performance impact
4. **Security Gaps**: Missing protocol coverage, overly broad rules, default allow policies
5. **Performance Issues**: Complex PCRE patterns, rule ordering, resource utilization
6. **Compliance**: PCI-DSS, NIST Cybersecurity Framework, CIS Controls alignment

Critical Security Issues to Flag:
- No drop/reject rules (detection-only policy)
- Rules matching 'any any -> any any' without restrictions
- Missing rule documentation (no msg field)
- Conflicting rule priorities
- Unencrypted traffic patterns not blocked
- Known malicious patterns not covered
""",
            {}
        )
    
    async def _enhance_firewall_analysis(
        self,
        llm_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance LLM result with firewall-specific analysis."""
        
        # Extract rule statistics
        rules = context.get('rules', [])
        rule_stats = self._calculate_rule_statistics(rules)
        
        # Add firewall-specific metrics
        llm_result['firewall_analysis'] = {
            'rule_statistics': rule_stats,
            'policy_type': self._determine_policy_type(rules),
            'coverage_analysis': self._analyze_coverage(rules),
            'performance_assessment': self._assess_performance(rules)
        }
        
        return llm_result
    
    def _calculate_rule_statistics(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate detailed rule statistics."""
        
        if not rules:
            return {
                'total_rules': 0,
                'blocking_rules': 0,
                'alert_rules': 0,
                'pass_rules': 0,
                'blocking_percentage': 0.0
            }
        
        action_counts = {'drop': 0, 'reject': 0, 'alert': 0, 'pass': 0}
        
        for rule in rules:
            action = rule.get('action', '').lower()
            if action in action_counts:
                action_counts[action] += 1
        
        total_rules = len(rules)
        blocking_rules = action_counts['drop'] + action_counts['reject']
        
        return {
            'total_rules': total_rules,
            'blocking_rules': blocking_rules,
            'alert_rules': action_counts['alert'],
            'pass_rules': action_counts['pass'],
            'blocking_percentage': (blocking_rules / total_rules) * 100 if total_rules > 0 else 0.0,
            'action_distribution': action_counts
        }
    
    def _determine_policy_type(self, rules: List[Dict[str, Any]]) -> str:
        """Determine the type of firewall policy."""
        
        if not rules:
            return "empty"
        
        blocking_rules = len([r for r in rules if r.get('action') in ['drop', 'reject']])
        total_rules = len(rules)
        
        if blocking_rules == 0:
            return "detection_only"
        elif blocking_rules == total_rules:
            return "blocking_only"
        elif blocking_rules < total_rules * 0.1:
            return "mostly_detection"
        elif blocking_rules > total_rules * 0.9:
            return "mostly_blocking"
        else:
            return "balanced"
    
    def _analyze_coverage(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze protocol and port coverage."""
        
        protocols = set()
        ports = set()
        
        for rule in rules:
            if 'protocol' in rule:
                protocols.add(rule['protocol'])
            if 'dest_port' in rule and rule['dest_port'] != 'any':
                ports.add(rule['dest_port'])
        
        return {
            'protocols_covered': list(protocols),
            'specific_ports': len(ports),
            'has_tcp_coverage': 'tcp' in protocols,
            'has_udp_coverage': 'udp' in protocols,
            'has_icmp_coverage': 'icmp' in protocols
        }
    
    def _assess_performance(self, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess performance characteristics."""
        
        complex_rules = 0
        pcre_rules = 0
        
        for rule in rules:
            patterns = rule.get('patterns', [])
            if any(p.get('pattern_type') == 'pcre' for p in patterns):
                pcre_rules += 1
            if len(patterns) > 3:
                complex_rules += 1
        
        return {
            'complex_rules': complex_rules,
            'pcre_rules': pcre_rules,
            'estimated_performance_impact': 'high' if pcre_rules > 10 else 'medium' if pcre_rules > 0 else 'low'
        }


class CoreNetworkPolicyValidator(BaseValidator):
    """LLM-powered validator for CloudWAN Core Network policies."""
    
    async def validate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Core Network policy configuration."""
        
        if not self.llm_manager.config.core_network_validation_enabled:
            return {"validation_skipped": "core_network_validation_disabled"}
        
        prompt = self._create_core_network_validation_prompt()
        
        try:
            result = await self.llm_manager.validate_with_llm(
                validation_type="core_network",
                prompt=prompt,
                context=context,
                structured_output=True
            )
            
            # Add core network specific analysis
            enhanced_result = await self._enhance_core_network_analysis(result, context)
            
            return enhanced_result
            
        except LLMValidationError as e:
            self.logger.error(f"Core Network validation failed: {e}")
            return {
                "validation_status": "error",
                "error": str(e),
                "fallback_used": self.llm_manager.config.fallback_to_heuristics
            }
    
    def _create_core_network_validation_prompt(self) -> str:
        """Create Core Network policy validation prompt."""
        
        return self._create_validation_prompt(
            """
You are an expert AWS CloudWAN Core Network policy analyst. Analyze the provided Core Network policy document for configuration correctness, routing efficiency, and security best practices.

Pay special attention to:
1. **Policy Structure**: Valid JSON structure, required fields, version compatibility
2. **Segment Configuration**: Segment isolation, route table associations, edge locations
3. **Segment Actions**: Routing logic, priorities, conditions, and actions
4. **Attachment Configuration**: VPC attachments, Site-to-Site VPN, Direct Connect
5. **Security**: Segment isolation, cross-segment access controls, attachment acceptance
6. **Performance**: Route aggregation, path optimization, bandwidth allocation
7. **Compliance**: Network segmentation requirements, traffic isolation policies

Critical Issues to Flag:
- Missing required policy sections
- Circular routing dependencies
- Overly permissive cross-segment rules
- Undefined edge locations
- Missing route tables for segments
- Conflicting segment action priorities
- Insecure attachment acceptance policies
""",
            {}
        )
    
    async def _enhance_core_network_analysis(
        self,
        llm_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance LLM result with Core Network specific analysis."""
        
        policy_doc = context.get('policy_document', {})
        
        llm_result['core_network_analysis'] = {
            'policy_structure': self._analyze_policy_structure(policy_doc),
            'segment_analysis': self._analyze_segments(policy_doc.get('segments', [])),
            'routing_complexity': self._calculate_routing_complexity(policy_doc),
            'attachment_security': self._assess_attachment_security(policy_doc)
        }
        
        return llm_result
    
    def _analyze_policy_structure(self, policy_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Core Network policy document structure."""
        
        required_sections = ['version', 'core-network-configuration', 'segments']
        optional_sections = ['segment-actions', 'attachment-policies', 'network-function-groups']
        
        present_sections = []
        missing_required = []
        
        for section in required_sections:
            if section in policy_doc:
                present_sections.append(section)
            else:
                missing_required.append(section)
        
        for section in optional_sections:
            if section in policy_doc:
                present_sections.append(section)
        
        return {
            'present_sections': present_sections,
            'missing_required': missing_required,
            'has_version': 'version' in policy_doc,
            'version_value': policy_doc.get('version', 'unknown'),
            'structure_valid': len(missing_required) == 0
        }
    
    def _analyze_segments(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze segment configuration."""
        
        segment_names = [s.get('name', 'unnamed') for s in segments]
        edge_locations = set()
        
        for segment in segments:
            segment_edge_locations = segment.get('edge-locations', [])
            edge_locations.update(segment_edge_locations)
        
        return {
            'segment_count': len(segments),
            'segment_names': segment_names,
            'total_edge_locations': len(edge_locations),
            'edge_locations': list(edge_locations),
            'has_isolated_segments': any(s.get('isolate-attachments') for s in segments)
        }
    
    def _calculate_routing_complexity(self, policy_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate routing complexity score."""
        
        segment_actions = policy_doc.get('segment-actions', [])
        nfgs = policy_doc.get('network-function-groups', [])
        
        complexity_factors = {
            'segment_action_count': len(segment_actions),
            'nfg_count': len(nfgs),
            'has_send_via': any('send-via' in sa for sa in segment_actions),
            'has_send_to': any('send-to' in sa for sa in segment_actions),
            'complex_conditions': sum(1 for sa in segment_actions if len(sa.get('conditions', [])) > 2)
        }
        
        # Calculate overall complexity score
        complexity_score = (
            complexity_factors['segment_action_count'] * 0.1 +
            complexity_factors['nfg_count'] * 0.2 +
            (0.3 if complexity_factors['has_send_via'] else 0) +
            (0.2 if complexity_factors['has_send_to'] else 0) +
            complexity_factors['complex_conditions'] * 0.1
        )
        
        complexity_factors['overall_score'] = min(1.0, complexity_score)
        complexity_factors['complexity_level'] = (
            'high' if complexity_score > 0.7 else
            'medium' if complexity_score > 0.4 else
            'low'
        )
        
        return complexity_factors
    
    def _assess_attachment_security(self, policy_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Assess attachment security configuration."""
        
        attachment_policies = policy_doc.get('attachment-policies', [])
        nfgs = policy_doc.get('network-function-groups', [])
        
        return {
            'has_attachment_policies': len(attachment_policies) > 0,
            'attachment_policy_count': len(attachment_policies),
            'requires_acceptance': any(
                nfg.get('require-attachment-acceptance', False) for nfg in nfgs
            ),
            'has_conditional_policies': any(
                'conditions' in ap for ap in attachment_policies
            )
        }


class NFGPolicyValidator(BaseValidator):
    """LLM-powered validator for Network Function Groups."""
    
    async def validate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate NFG configuration."""
        
        if not self.llm_manager.config.nfg_validation_enabled:
            return {"validation_skipped": "nfg_validation_disabled"}
        
        prompt = self._create_nfg_validation_prompt()
        
        try:
            result = await self.llm_manager.validate_with_llm(
                validation_type="nfg",
                prompt=prompt,
                context=context,
                structured_output=True
            )
            
            # Add NFG-specific analysis
            enhanced_result = await self._enhance_nfg_analysis(result, context)
            
            return enhanced_result
            
        except LLMValidationError as e:
            self.logger.error(f"NFG validation failed: {e}")
            return {
                "validation_status": "error",
                "error": str(e),
                "fallback_used": self.llm_manager.config.fallback_to_heuristics
            }
    
    def _create_nfg_validation_prompt(self) -> str:
        """Create NFG validation prompt."""
        
        return self._create_validation_prompt(
            """
You are an expert AWS CloudWAN Network Function Groups (NFG) analyst. Analyze the provided NFG configuration for routing logic, security implications, and operational efficiency.

Pay special attention to:
1. **NFG Configuration**: Edge locations, attachment requirements, service definitions
2. **Traffic Steering**: Send-to vs send-via configurations and their implications
3. **Routing Logic**: Traffic flow patterns, multi-hop routing, loop prevention
4. **Security Impact**: Service insertion points, traffic inspection, bypass risks
5. **Performance**: Latency impact, throughput considerations, geographic distribution
6. **Operational**: Monitoring, troubleshooting, capacity planning implications

Critical Issues to Flag:
- NFGs without proper edge location distribution
- Circular routing through send-via chains
- Missing attachment acceptance controls
- Inadequate service insertion point coverage
- Performance bottlenecks from sequential processing
- Security gaps in traffic steering logic
""",
            {}
        )
    
    async def _enhance_nfg_analysis(
        self,
        llm_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance LLM result with NFG-specific analysis."""
        
        nfgs = context.get('network_function_groups', [])
        
        llm_result['nfg_analysis'] = {
            'nfg_statistics': self._calculate_nfg_statistics(nfgs),
            'routing_patterns': self._analyze_routing_patterns(nfgs),
            'geographic_distribution': self._analyze_geographic_distribution(nfgs),
            'security_posture': self._assess_nfg_security(nfgs)
        }
        
        return llm_result
    
    def _calculate_nfg_statistics(self, nfgs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate NFG statistics."""
        
        total_nfgs = len(nfgs)
        send_to_nfgs = sum(1 for nfg in nfgs if nfg.get('send_to_targets'))
        send_via_nfgs = sum(1 for nfg in nfgs if nfg.get('send_via_targets'))
        
        return {
            'total_nfgs': total_nfgs,
            'send_to_count': send_to_nfgs,
            'send_via_count': send_via_nfgs,
            'mixed_configuration': sum(1 for nfg in nfgs 
                                     if nfg.get('send_to_targets') and nfg.get('send_via_targets'))
        }
    
    def _analyze_routing_patterns(self, nfgs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze NFG routing patterns."""
        
        patterns = {
            'service_chaining': 0,
            'hub_spoke': 0,
            'distributed': 0
        }
        
        for nfg in nfgs:
            send_via_count = len(nfg.get('send_via_targets', []))
            send_to_count = len(nfg.get('send_to_targets', []))
            
            if send_via_count > 1:
                patterns['service_chaining'] += 1
            if send_to_count > 0 and len(nfg.get('edge_locations', [])) == 1:
                patterns['hub_spoke'] += 1
            if len(nfg.get('edge_locations', [])) > 2:
                patterns['distributed'] += 1
        
        return patterns
    
    def _analyze_geographic_distribution(self, nfgs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze geographic distribution of NFGs."""
        
        all_locations = set()
        single_location_nfgs = 0
        
        for nfg in nfgs:
            edge_locations = nfg.get('edge_locations', [])
            all_locations.update(edge_locations)
            
            if len(edge_locations) == 1:
                single_location_nfgs += 1
        
        return {
            'total_edge_locations': len(all_locations),
            'edge_locations': list(all_locations),
            'single_location_nfgs': single_location_nfgs,
            'multi_location_nfgs': len(nfgs) - single_location_nfgs
        }
    
    def _assess_nfg_security(self, nfgs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess NFG security configuration."""
        
        requires_acceptance = sum(1 for nfg in nfgs 
                                if nfg.get('require_attachment_acceptance', False))
        
        return {
            'requires_acceptance_count': requires_acceptance,
            'acceptance_percentage': (requires_acceptance / len(nfgs)) * 100 if nfgs else 0,
            'security_level': 'high' if requires_acceptance == len(nfgs) else 
                             'medium' if requires_acceptance > 0 else 'low'
        }


class ConnectivityValidator(BaseValidator):
    """LLM-powered validator for network connectivity analysis."""
    
    async def validate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate network connectivity configuration."""
        
        if not self.llm_manager.config.connectivity_validation_enabled:
            return {"validation_skipped": "connectivity_validation_disabled"}
        
        prompt = self._create_connectivity_validation_prompt()
        
        try:
            result = await self.llm_manager.validate_with_llm(
                validation_type="connectivity",
                prompt=prompt,
                context=context,
                structured_output=True
            )
            
            # Add connectivity-specific analysis
            enhanced_result = await self._enhance_connectivity_analysis(result, context)
            
            return enhanced_result
            
        except LLMValidationError as e:
            self.logger.error(f"Connectivity validation failed: {e}")
            return {
                "validation_status": "error",
                "error": str(e),
                "fallback_used": self.llm_manager.config.fallback_to_heuristics
            }
    
    def _create_connectivity_validation_prompt(self) -> str:
        """Create connectivity validation prompt."""
        
        return self._create_validation_prompt(
            """
You are an expert AWS network connectivity analyst. Analyze the provided network configuration for end-to-end connectivity, security controls, and potential connectivity issues.

Consider all layers of network controls:
1. **Route Tables**: Routing paths, route priorities, next-hop resolution
2. **Security Groups**: Stateful firewall rules, port/protocol restrictions
3. **Network ACLs**: Stateless filtering, subnet-level controls
4. **CloudWAN Core Network**: Segment isolation, cross-segment routing
5. **Network Function Groups**: Traffic steering, service insertion
6. **AWS Network Firewall**: Deep packet inspection, Suricata rules
7. **VPC Configuration**: Subnets, internet gateways, NAT gateways

Connectivity Analysis Focus:
- End-to-end reachability between source and destination
- Security control effectiveness and potential bypasses
- Performance bottlenecks and latency sources
- Redundancy and failover capabilities
- Compliance with network segmentation requirements

Critical Issues to Flag:
- Missing or incorrect routing entries
- Conflicting security group and NACL rules
- Firewall policies allowing unintended traffic
- Network segmentation violations
- Single points of failure
- Asymmetric routing issues
""",
            {}
        )
    
    async def _enhance_connectivity_analysis(
        self,
        llm_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance LLM result with connectivity-specific analysis."""
        
        llm_result['connectivity_analysis'] = {
            'path_analysis': self._analyze_network_path(context),
            'security_layers': self._analyze_security_layers(context),
            'performance_factors': self._analyze_performance_factors(context),
            'redundancy_assessment': self._assess_redundancy(context)
        }
        
        return llm_result
    
    def _analyze_network_path(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze network path components."""
        
        source = context.get('source', {})
        destination = context.get('destination', {})
        
        return {
            'source_vpc': source.get('vpc_id'),
            'source_subnet': source.get('subnet_id'),
            'destination_vpc': destination.get('vpc_id'),
            'destination_subnet': destination.get('subnet_id'),
            'cross_vpc': source.get('vpc_id') != destination.get('vpc_id'),
            'same_az': source.get('availability_zone') == destination.get('availability_zone')
        }
    
    def _analyze_security_layers(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security control layers."""
        
        return {
            'has_security_groups': bool(context.get('security_groups')),
            'has_network_acls': bool(context.get('network_acls')),
            'has_firewall_rules': bool(context.get('firewall_rules')),
            'has_core_network_policy': bool(context.get('core_network_policy')),
            'security_layers_count': sum([
                bool(context.get('security_groups')),
                bool(context.get('network_acls')),
                bool(context.get('firewall_rules')),
                bool(context.get('core_network_policy'))
            ])
        }
    
    def _analyze_performance_factors(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance impact factors."""
        
        nfgs = context.get('network_function_groups', [])
        firewall_rules = context.get('firewall_rules', [])
        
        return {
            'nfg_hops': len([nfg for nfg in nfgs if nfg.get('send_via_targets')]),
            'firewall_inspection_points': len(firewall_rules),
            'estimated_latency_category': self._estimate_latency_category(context)
        }
    
    def _estimate_latency_category(self, context: Dict[str, Any]) -> str:
        """Estimate latency category based on path complexity."""
        
        complexity_factors = 0
        
        if context.get('network_function_groups'):
            complexity_factors += len(context['network_function_groups'])
        if context.get('firewall_rules'):
            complexity_factors += 1
        if context.get('cross_region', False):
            complexity_factors += 2
        
        if complexity_factors == 0:
            return 'low'
        elif complexity_factors <= 2:
            return 'medium'
        else:
            return 'high'
    
    def _assess_redundancy(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess network redundancy and resilience."""
        
        return {
            'has_multiple_azs': len(set(context.get('availability_zones', []))) > 1,
            'has_backup_routes': len(context.get('route_tables', [])) > 1,
            'single_points_of_failure': self._identify_spofs(context)
        }
    
    def _identify_spofs(self, context: Dict[str, Any]) -> List[str]:
        """Identify potential single points of failure."""
        
        spofs = []
        
        if len(context.get('availability_zones', [])) == 1:
            spofs.append('single_availability_zone')
        
        nfgs = context.get('network_function_groups', [])
        single_location_nfgs = [nfg for nfg in nfgs if len(nfg.get('edge_locations', [])) == 1]
        if single_location_nfgs:
            spofs.append('single_location_nfgs')
        
        if not context.get('backup_routes'):
            spofs.append('no_backup_routes')
        
        return spofs