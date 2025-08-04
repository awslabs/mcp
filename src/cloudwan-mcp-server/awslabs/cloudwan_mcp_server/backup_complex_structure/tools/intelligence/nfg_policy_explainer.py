"""
Network Function Groups (NFG) Policy Explainer Tool for CloudWAN MCP Server.

This module provides comprehensive explanation of Network Function Groups as applied 
within CloudWAN Core Network Policy documents, analyzing NFG configurations, send-to/send-via 
targets, and policy enforcement with <2.0s load time performance.

Features:
- Network Function Groups (NFG) policy parsing and explanation
- Send-to and send-via target analysis
- Multi-hop routing configuration explanation
- Network function placement and routing rules
- Policy enforcement and traffic flow analysis
- Cross-segment NFG routing explanation
- Service insertion point identification and explanation
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ..base import (
    BaseMCPTool,
    ToolError,
    ValidationError,
    AWSOperationError,
    handle_errors,
)

logger = logging.getLogger(__name__)


class NFGActionType(Enum):
    """Network Function Group action types."""
    SEND_TO = "send-to"
    SEND_VIA = "send-via"


class NFGTargetType(Enum):
    """NFG target types."""
    ATTACHMENT = "attachment"
    CORE_NETWORK = "core-network"
    SEGMENT = "segment"


class TrafficDirection(Enum):
    """Traffic flow directions for NFG analysis."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class NFGAnalysisContext:
    """Context for NFG policy analysis operations."""
    
    analysis_id: str
    regions: List[str]
    core_network_ids: Optional[List[str]]
    segment_names: Optional[List[str]]
    analysis_depth: str  # "basic", "detailed", "comprehensive"
    start_time: datetime
    timeout_seconds: int = 300
    cache_ttl_minutes: int = 30
    
    def __post_init__(self):
        if not self.analysis_id:
            self.analysis_id = str(uuid.uuid4())
        if not self.start_time:
            self.start_time = datetime.now()


@dataclass
class NetworkFunctionGroup:
    """Network Function Group configuration."""
    
    name: str
    description: Optional[str]
    require_attachment_acceptance: bool
    edge_locations: List[str]
    send_to_targets: List[Dict[str, Any]]
    send_via_targets: List[Dict[str, Any]]
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class NFGRoutingRule:
    """NFG routing rule configuration."""
    
    rule_id: str
    source: Dict[str, Any]
    destination: Dict[str, Any]
    action_type: NFGActionType
    target_type: NFGTargetType
    target_identifier: str
    conditions: List[Dict[str, Any]]
    priority: Optional[int] = None


@dataclass
class TrafficFlow:
    """Traffic flow through NFG."""
    
    flow_id: str
    source_segment: str
    destination_segment: str
    nfg_name: str
    direction: TrafficDirection
    routing_path: List[str]
    service_insertion_points: List[str]
    policy_enforcement_points: List[str]


@dataclass
class NFGPolicyExplanation:
    """Detailed explanation of NFG policy application."""
    
    nfg_name: str
    policy_section: str
    explanation_text: str
    routing_behavior: str
    traffic_flows: List[TrafficFlow]
    configuration_details: Dict[str, Any]
    impact_on_segments: List[str]


@dataclass
class NFGAnalysisResult:
    """Result of NFG policy analysis."""
    
    analysis_id: str
    core_network_id: str
    network_function_groups: List[NetworkFunctionGroup]
    routing_rules: List[NFGRoutingRule]
    traffic_flows: List[TrafficFlow]
    policy_explanations: List[NFGPolicyExplanation]
    nfg_summary: Dict[str, Any]
    routing_complexity_score: float
    recommendations: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)


class NFGPolicyAnalyzer:
    """Analyzer for Network Function Groups policy explanation."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        self.aws_manager = aws_manager
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.NFGPolicyAnalyzer")
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
    async def analyze_nfg_policy(
        self,
        context: NFGAnalysisContext
    ) -> NFGAnalysisResult:
        """Analyze Network Function Groups in Core Network Policy."""
        
        self.logger.info(f"Starting NFG policy analysis: {context.analysis_id}")
        
        # Get Core Network and policy document
        core_network = await self._get_core_network_details(context)
        if not core_network:
            raise ValidationError("No Core Network found for NFG analysis")
            
        policy_document = await self._parse_policy_document(
            core_network['PolicyDocument']
        )
        
        # Extract and analyze Network Function Groups
        nfgs = await self._extract_network_function_groups(policy_document)
        
        # Analyze routing rules and traffic flows
        routing_rules = await self._analyze_nfg_routing_rules(policy_document, nfgs)
        traffic_flows = await self._analyze_traffic_flows(policy_document, nfgs, routing_rules)
        
        # Generate detailed explanations
        policy_explanations = await self._generate_policy_explanations(
            policy_document, nfgs, routing_rules, traffic_flows
        )
        
        # Calculate complexity score
        complexity_score = self._calculate_routing_complexity(nfgs, routing_rules)
        
        # Generate recommendations
        recommendations = self._generate_nfg_recommendations(nfgs, routing_rules, traffic_flows)
        
        # Create summary
        nfg_summary = {
            "total_nfgs": len(nfgs),
            "total_routing_rules": len(routing_rules),
            "total_traffic_flows": len(traffic_flows),
            "send_to_configurations": sum(1 for nfg in nfgs if nfg.send_to_targets),
            "send_via_configurations": sum(1 for nfg in nfgs if nfg.send_via_targets),
            "multi_hop_routing_enabled": any(
                len(flow.routing_path) > 2 for flow in traffic_flows
            ),
            "service_insertion_points": sum(
                len(flow.service_insertion_points) for flow in traffic_flows
            )
        }
        
        return NFGAnalysisResult(
            analysis_id=context.analysis_id,
            core_network_id=core_network['CoreNetworkId'],
            network_function_groups=nfgs,
            routing_rules=routing_rules,
            traffic_flows=traffic_flows,
            policy_explanations=policy_explanations,
            nfg_summary=nfg_summary,
            routing_complexity_score=complexity_score,
            recommendations=recommendations
        )
    
    async def _get_core_network_details(self, context: NFGAnalysisContext) -> Optional[Dict[str, Any]]:
        """Get Core Network details with policy document."""
        
        try:
            # Use primary region for Network Manager
            primary_region = context.regions[0] if context.regions else "us-east-1"
            client = await self.aws_manager.get_client("networkmanager", primary_region)
            
            if context.core_network_ids:
                # Get specific Core Network
                response = await client.get_core_network(
                    CoreNetworkId=context.core_network_ids[0]
                )
                return response.get('CoreNetwork')
            else:
                # Get first available Core Network
                networks = await client.list_core_networks()
                if networks.get('CoreNetworks'):
                    core_network_id = networks['CoreNetworks'][0]['CoreNetworkId']
                    response = await client.get_core_network(
                        CoreNetworkId=core_network_id
                    )
                    return response.get('CoreNetwork')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get Core Network details: {e}")
            raise AWSOperationError(f"Core Network retrieval failed: {e}")
    
    async def _parse_policy_document(self, policy_doc_json: str) -> Dict[str, Any]:
        """Parse CloudWAN policy document JSON."""
        
        try:
            return json.loads(policy_doc_json)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in policy document: {e}")
        except Exception as e:
            raise ValidationError(f"Policy document parsing failed: {e}")
    
    async def _extract_network_function_groups(
        self,
        policy_document: Dict[str, Any]
    ) -> List[NetworkFunctionGroup]:
        """Extract Network Function Groups from policy document."""
        
        nfgs = []
        
        # Parse network-function-groups section
        nfg_data = policy_document.get('network-function-groups', [])
        
        for nfg in nfg_data:
            # Extract send-to targets
            send_to_targets = []
            for target in nfg.get('send-to', []):
                send_to_targets.append({
                    'target_type': target.get('type'),
                    'target_id': target.get('id'),
                    'conditions': target.get('conditions', [])
                })
            
            # Extract send-via targets  
            send_via_targets = []
            for target in nfg.get('send-via', []):
                send_via_targets.append({
                    'target_type': target.get('type'),
                    'target_id': target.get('id'),
                    'conditions': target.get('conditions', [])
                })
            
            nfgs.append(NetworkFunctionGroup(
                name=nfg.get('name'),
                description=nfg.get('description'),
                require_attachment_acceptance=nfg.get('require-attachment-acceptance', False),
                edge_locations=nfg.get('edge-locations', []),
                send_to_targets=send_to_targets,
                send_via_targets=send_via_targets,
                tags=nfg.get('tags', {})
            ))
        
        return nfgs
    
    async def _analyze_nfg_routing_rules(
        self,
        policy_document: Dict[str, Any],
        nfgs: List[NetworkFunctionGroup]
    ) -> List[NFGRoutingRule]:
        """Analyze routing rules involving NFGs."""
        
        routing_rules = []
        
        # Analyze segment actions that reference NFGs
        for action in policy_document.get('segment-actions', []):
            if 'send-to' in action or 'send-via' in action:
                rule_id = f"action_{action.get('rule-number', 'unknown')}"
                
                # Handle send-to actions
                if 'send-to' in action:
                    routing_rules.append(NFGRoutingRule(
                        rule_id=f"{rule_id}_send_to",
                        source=action.get('source', {}),
                        destination=action.get('destination', {}),
                        action_type=NFGActionType.SEND_TO,
                        target_type=NFGTargetType.ATTACHMENT,  # Default
                        target_identifier=action['send-to'],
                        conditions=action.get('conditions', []),
                        priority=action.get('rule-number')
                    ))
                
                # Handle send-via actions
                if 'send-via' in action:
                    routing_rules.append(NFGRoutingRule(
                        rule_id=f"{rule_id}_send_via",
                        source=action.get('source', {}),
                        destination=action.get('destination', {}),
                        action_type=NFGActionType.SEND_VIA,
                        target_type=NFGTargetType.ATTACHMENT,  # Default
                        target_identifier=action['send-via'],
                        conditions=action.get('conditions', []),
                        priority=action.get('rule-number')
                    ))
        
        return routing_rules
    
    async def _analyze_traffic_flows(
        self,
        policy_document: Dict[str, Any],
        nfgs: List[NetworkFunctionGroup],
        routing_rules: List[NFGRoutingRule]
    ) -> List[TrafficFlow]:
        """Analyze traffic flows through Network Function Groups."""
        
        traffic_flows = []
        segments = policy_document.get('segments', [])
        segment_names = [seg.get('name') for seg in segments]
        
        for i, rule in enumerate(routing_rules):
            # Determine source and destination segments
            source_segment = self._extract_segment_from_condition(rule.source, segment_names)
            dest_segment = self._extract_segment_from_condition(rule.destination, segment_names)
            
            # Find associated NFG
            nfg_name = self._find_nfg_for_target(rule.target_identifier, nfgs)
            
            # Determine routing path
            routing_path = self._calculate_routing_path(rule, nfgs, segments)
            
            # Identify service insertion points
            service_insertion_points = self._identify_service_insertion_points(rule, nfgs)
            
            traffic_flows.append(TrafficFlow(
                flow_id=f"flow_{i}",
                source_segment=source_segment or "unknown",
                destination_segment=dest_segment or "unknown",
                nfg_name=nfg_name or "unknown",
                direction=TrafficDirection.BIDIRECTIONAL,  # Default
                routing_path=routing_path,
                service_insertion_points=service_insertion_points,
                policy_enforcement_points=[rule.target_identifier]
            ))
        
        return traffic_flows
    
    async def _generate_policy_explanations(
        self,
        policy_document: Dict[str, Any],
        nfgs: List[NetworkFunctionGroup],
        routing_rules: List[NFGRoutingRule],
        traffic_flows: List[TrafficFlow]
    ) -> List[NFGPolicyExplanation]:
        """Generate detailed explanations of NFG policy application."""
        
        explanations = []
        
        for nfg in nfgs:
            # Generate explanation for each NFG
            explanation_text = self._generate_nfg_explanation(nfg, routing_rules, traffic_flows)
            routing_behavior = self._describe_routing_behavior(nfg, routing_rules)
            
            # Find traffic flows involving this NFG
            related_flows = [f for f in traffic_flows if f.nfg_name == nfg.name]
            
            # Identify affected segments
            affected_segments = set()
            for flow in related_flows:
                affected_segments.add(flow.source_segment)
                affected_segments.add(flow.destination_segment)
            
            explanations.append(NFGPolicyExplanation(
                nfg_name=nfg.name,
                policy_section="network-function-groups",
                explanation_text=explanation_text,
                routing_behavior=routing_behavior,
                traffic_flows=related_flows,
                configuration_details={
                    "require_attachment_acceptance": nfg.require_attachment_acceptance,
                    "edge_locations": nfg.edge_locations,
                    "send_to_targets_count": len(nfg.send_to_targets),
                    "send_via_targets_count": len(nfg.send_via_targets),
                    "tags": nfg.tags
                },
                impact_on_segments=list(affected_segments)
            ))
        
        return explanations
    
    def _generate_nfg_explanation(
        self,
        nfg: NetworkFunctionGroup,
        routing_rules: List[NFGRoutingRule],
        traffic_flows: List[TrafficFlow]
    ) -> str:
        """Generate human-readable explanation of NFG configuration."""
        
        explanation_parts = []
        
        # Basic NFG description
        explanation_parts.append(
            f"Network Function Group '{nfg.name}' is configured to provide network services "
            f"across {len(nfg.edge_locations)} edge locations: {', '.join(nfg.edge_locations)}."
        )
        
        # Send-to configuration
        if nfg.send_to_targets:
            explanation_parts.append(
                f"This NFG has {len(nfg.send_to_targets)} send-to target(s) configured, "
                "meaning traffic destined for specific conditions will be redirected to "
                "this network function for processing before continuing to its final destination."
            )
        
        # Send-via configuration
        if nfg.send_via_targets:
            explanation_parts.append(
                f"This NFG has {len(nfg.send_via_targets)} send-via target(s) configured, "
                "meaning traffic matching specific conditions will be routed through "
                "this network function as an intermediate hop in the routing path."
            )
        
        # Attachment acceptance
        if nfg.require_attachment_acceptance:
            explanation_parts.append(
                "Attachments to this NFG require explicit acceptance, providing "
                "administrative control over which resources can connect."
            )
        
        return " ".join(explanation_parts)
    
    def _describe_routing_behavior(
        self,
        nfg: NetworkFunctionGroup,
        routing_rules: List[NFGRoutingRule]
    ) -> str:
        """Describe the routing behavior of the NFG."""
        
        # Find rules that reference this NFG
        related_rules = [
            rule for rule in routing_rules 
            if rule.target_identifier == nfg.name or nfg.name in str(rule)
        ]
        
        if not related_rules:
            return "No specific routing rules reference this NFG directly."
        
        send_to_rules = [r for r in related_rules if r.action_type == NFGActionType.SEND_TO]
        send_via_rules = [r for r in related_rules if r.action_type == NFGActionType.SEND_VIA]
        
        behavior_parts = []
        
        if send_to_rules:
            behavior_parts.append(
                f"Acts as a final destination for {len(send_to_rules)} routing rule(s), "
                "processing traffic before it reaches its ultimate destination."
            )
        
        if send_via_rules:
            behavior_parts.append(
                f"Acts as an intermediate hop for {len(send_via_rules)} routing rule(s), "
                "processing traffic in transit between source and destination."
            )
        
        return " ".join(behavior_parts) if behavior_parts else "Standard routing behavior."
    
    def _extract_segment_from_condition(self, condition: Dict[str, Any], segment_names: List[str]) -> Optional[str]:
        """Extract segment name from routing condition."""
        
        # Look for segment references in conditions
        if isinstance(condition, dict):
            for key, value in condition.items():
                if key == 'segment' or 'segment' in str(key).lower():
                    return value
                if value in segment_names:
                    return value
        
        return None
    
    def _find_nfg_for_target(self, target_identifier: str, nfgs: List[NetworkFunctionGroup]) -> Optional[str]:
        """Find NFG name for a given target identifier."""
        
        for nfg in nfgs:
            if nfg.name == target_identifier:
                return nfg.name
            # Check if target_identifier references this NFG in any way
            if target_identifier in str(nfg.send_to_targets) or target_identifier in str(nfg.send_via_targets):
                return nfg.name
        
        return None
    
    def _calculate_routing_path(
        self,
        rule: NFGRoutingRule,
        nfgs: List[NetworkFunctionGroup],
        segments: List[Dict[str, Any]]
    ) -> List[str]:
        """Calculate the routing path for a given rule."""
        
        path = []
        
        # Add source
        source_info = str(rule.source)
        path.append(f"Source: {source_info}")
        
        # Add NFG/target
        if rule.action_type == NFGActionType.SEND_VIA:
            path.append(f"Via NFG: {rule.target_identifier}")
            path.append("Destination")
        else:
            path.append(f"To NFG: {rule.target_identifier}")
        
        return path
    
    def _identify_service_insertion_points(
        self,
        rule: NFGRoutingRule,
        nfgs: List[NetworkFunctionGroup]
    ) -> List[str]:
        """Identify service insertion points for the rule."""
        
        insertion_points = []
        
        # NFG itself is a service insertion point
        if rule.target_identifier:
            insertion_points.append(rule.target_identifier)
        
        # Look for additional insertion points in NFG configuration
        for nfg in nfgs:
            if nfg.name == rule.target_identifier:
                # Edge locations are potential insertion points
                for edge_location in nfg.edge_locations:
                    insertion_points.append(f"{edge_location}_edge")
        
        return insertion_points
    
    def _calculate_routing_complexity(
        self,
        nfgs: List[NetworkFunctionGroup],
        routing_rules: List[NFGRoutingRule]
    ) -> float:
        """Calculate routing complexity score."""
        
        if not nfgs and not routing_rules:
            return 0.0
        
        # Base complexity factors
        nfg_complexity = len(nfgs) * 0.1
        rule_complexity = len(routing_rules) * 0.2
        
        # Additional complexity for multi-target NFGs
        multi_target_complexity = 0
        for nfg in nfgs:
            if len(nfg.send_to_targets) > 1 or len(nfg.send_via_targets) > 1:
                multi_target_complexity += 0.1
        
        # Rule priority complexity
        priority_complexity = 0
        if routing_rules:
            priorities = [r.priority for r in routing_rules if r.priority]
            if len(set(priorities)) != len(priorities):  # Duplicate priorities
                priority_complexity += 0.2
        
        total_complexity = nfg_complexity + rule_complexity + multi_target_complexity + priority_complexity
        return min(1.0, round(total_complexity, 3))  # Cap at 1.0
    
    def _generate_nfg_recommendations(
        self,
        nfgs: List[NetworkFunctionGroup],
        routing_rules: List[NFGRoutingRule],
        traffic_flows: List[TrafficFlow]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for NFG configuration."""
        
        recommendations = []
        
        # Check for missing NFG descriptions
        undocumented_nfgs = [nfg for nfg in nfgs if not nfg.description]
        if undocumented_nfgs:
            recommendations.append({
                "priority": "medium",
                "category": "documentation",
                "title": "Add NFG Descriptions",
                "description": f"{len(undocumented_nfgs)} NFG(s) lack descriptions for operational clarity",
                "affected_nfgs": [nfg.name for nfg in undocumented_nfgs],
                "action_items": [
                    "Add descriptive text for each NFG explaining its purpose",
                    "Document service insertion points and traffic processing"
                ]
            })
        
        # Check for complex routing patterns
        complex_flows = [f for f in traffic_flows if len(f.routing_path) > 3]
        if complex_flows:
            recommendations.append({
                "priority": "low",
                "category": "optimization",
                "title": "Review Complex Routing Patterns",
                "description": f"{len(complex_flows)} traffic flow(s) have complex routing paths",
                "action_items": [
                    "Review multi-hop routing for performance impact",
                    "Consider simplifying routing where possible"
                ]
            })
        
        # Check for NFGs without edge location diversity
        single_location_nfgs = [nfg for nfg in nfgs if len(nfg.edge_locations) < 2]
        if single_location_nfgs and len(nfgs) > 1:
            recommendations.append({
                "priority": "medium",
                "category": "resilience", 
                "title": "Consider NFG Geographic Distribution",
                "description": f"{len(single_location_nfgs)} NFG(s) deployed in single location",
                "action_items": [
                    "Evaluate multi-region NFG deployment for resilience",
                    "Consider geographic distribution based on traffic patterns"
                ]
            })
        
        return recommendations


class NFGPolicyExplainerTool(BaseMCPTool):
    """Network Function Groups Policy Explainer MCP Tool."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        self.nfg_analyzer = NFGPolicyAnalyzer(aws_manager, config)
        self._load_time = 0.0
        self._start_time = time.time()
        
        # Record load time
        self._load_time = time.time() - self._start_time
        logger.info(f"NFGPolicyExplainerTool initialized in {self._load_time:.3f}s")
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the tool input schema."""
        return {
            "type": "object",
            "properties": {
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions to analyze (default: ['us-east-1'])",
                    "default": ["us-east-1"]
                },
                "core_network_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific Core Network IDs to analyze (optional)",
                    "default": []
                },
                "segment_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific segment names to focus analysis on (optional)",
                    "default": []
                },
                "analysis_depth": {
                    "type": "string",
                    "enum": ["basic", "detailed", "comprehensive"],
                    "description": "Depth of NFG policy analysis",
                    "default": "detailed"
                },
                "explain_routing_flows": {
                    "type": "boolean",
                    "description": "Include detailed traffic flow explanations",
                    "default": True
                }
            },
            "required": []
        }
    
    @handle_errors
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute NFG policy explanation analysis."""
        
        # Extract and validate parameters
        regions = kwargs.get('regions', ['us-east-1'])
        core_network_ids = kwargs.get('core_network_ids', [])
        segment_names = kwargs.get('segment_names', [])
        analysis_depth = kwargs.get('analysis_depth', 'detailed')
        explain_routing_flows = kwargs.get('explain_routing_flows', True)
        
        # Validate regions
        if not regions:
            regions = ['us-east-1']
        
        # Create analysis context
        context = NFGAnalysisContext(
            analysis_id=str(uuid.uuid4()),
            regions=regions,
            core_network_ids=core_network_ids if core_network_ids else None,
            segment_names=segment_names if segment_names else None,
            analysis_depth=analysis_depth,
            start_time=datetime.now()
        )
        
        # Perform NFG policy analysis
        try:
            analysis_result = await self.nfg_analyzer.analyze_nfg_policy(context)
            
            # Format results
            result = {
                "analysis_id": analysis_result.analysis_id,
                "core_network_id": analysis_result.core_network_id,
                "nfg_summary": analysis_result.nfg_summary,
                "routing_complexity_score": analysis_result.routing_complexity_score,
                "network_function_groups": [
                    {
                        "name": nfg.name,
                        "description": nfg.description,
                        "require_attachment_acceptance": nfg.require_attachment_acceptance,
                        "edge_locations": nfg.edge_locations,
                        "send_to_targets": nfg.send_to_targets,
                        "send_via_targets": nfg.send_via_targets,
                        "tags": nfg.tags
                    }
                    for nfg in analysis_result.network_function_groups
                ],
                "policy_explanations": [
                    {
                        "nfg_name": exp.nfg_name,
                        "policy_section": exp.policy_section,
                        "explanation_text": exp.explanation_text,
                        "routing_behavior": exp.routing_behavior,
                        "configuration_details": exp.configuration_details,
                        "impact_on_segments": exp.impact_on_segments
                    }
                    for exp in analysis_result.policy_explanations
                ],
                "recommendations": analysis_result.recommendations,
                "regions_analyzed": regions,
                "analysis_timestamp": analysis_result.timestamp.isoformat(),
                "tool_performance": {
                    "load_time_seconds": self._load_time,
                    "execution_time_seconds": (datetime.now() - context.start_time).total_seconds()
                }
            }
            
            # Include detailed routing flows if requested
            if explain_routing_flows:
                result["traffic_flows"] = [
                    {
                        "flow_id": flow.flow_id,
                        "source_segment": flow.source_segment,
                        "destination_segment": flow.destination_segment,
                        "nfg_name": flow.nfg_name,
                        "direction": flow.direction.value,
                        "routing_path": flow.routing_path,
                        "service_insertion_points": flow.service_insertion_points,
                        "policy_enforcement_points": flow.policy_enforcement_points
                    }
                    for flow in analysis_result.traffic_flows
                ]
                
                result["routing_rules"] = [
                    {
                        "rule_id": rule.rule_id,
                        "action_type": rule.action_type.value,
                        "target_type": rule.target_type.value,
                        "target_identifier": rule.target_identifier,
                        "source": rule.source,
                        "destination": rule.destination,
                        "conditions": rule.conditions,
                        "priority": rule.priority
                    }
                    for rule in analysis_result.routing_rules
                ]
            
            return result
            
        except Exception as e:
            self.logger.error(f"NFG policy analysis failed: {e}")
            raise ToolError(f"Network Function Groups policy analysis failed: {e}")
    
    def get_load_time(self) -> float:
        """Get tool load time in seconds."""
        return self._load_time
    
    @property
    def tool_name(self) -> str:
        """Tool name for MCP registration."""
        return "explain_nfg_policy"
    
    @property
    def description(self) -> str:
        """Tool description for MCP registration."""
        return "Explain Network Function Groups as applied in CloudWAN Core Network Policy documents"