"""
Data-Only NFG Policy Analyzer for CloudWAN MCP Server.

This module provides pure data extraction for Network Function Groups (NFG) 
policy analysis without any LLM validation or interpretive insights. It returns 
factual AWS data only, allowing users to consume the data as they wish.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List
from dataclasses import dataclass

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ..base import (
    BaseMCPTool,
    ToolError,
    ValidationError,
    AWSOperationError,
    handle_errors,
    validate_regions,
)

logger = logging.getLogger(__name__)


@dataclass
class NFGDataAnalysisContext:
    """Context for NFG data analysis operations."""
    
    analysis_id: str
    core_network_id: str
    regions: List[str]
    start_time: datetime
    include_rule_details: bool = True
    include_routing_analysis: bool = True
    
    def __post_init__(self):
        if not self.analysis_id:
            self.analysis_id = str(uuid.uuid4())
        if not self.start_time:
            self.start_time = datetime.now()


class NFGDataAnalyzer:
    """
    Data-only analyzer for Network Function Groups policies.
    
    Extracts pure data from CloudWAN Core Network policies and provides
    structured analysis of NFGs without interpretive insights or LLM validation.
    """
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        self.aws_manager = aws_manager
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.NFGDataAnalyzer")
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def analyze_nfg_policy(
        self,
        context: NFGDataAnalysisContext
    ) -> Dict[str, Any]:
        """
        Extract pure NFG policy data without interpretive analysis.
        
        Args:
            context: Analysis context with core network specifications
            
        Returns:
            Structured NFG data without LLM enhancements
        """
        self.logger.info(f"Starting NFG data extraction: {context.analysis_id}")
        
        try:
            # Extract core network policy data
            policy_data = await self._extract_core_network_policy(
                context.core_network_id,
                context.regions
            )
            
            if not policy_data:
                raise ToolError(f"No policy data found for core network: {context.core_network_id}")
            
            # Extract NFG configurations
            nfg_data = await self._extract_nfg_configurations(policy_data, context)
            
            # Extract routing rules
            routing_data = await self._extract_routing_rules(policy_data, context)
            
            # Calculate heuristic metrics
            complexity_metrics = self._calculate_complexity_metrics(nfg_data, routing_data)
            
            # Generate data-driven insights
            data_insights = self._generate_data_insights(nfg_data, routing_data, complexity_metrics)
            
            return {
                'analysis_id': context.analysis_id,
                'analysis_type': 'data_only_nfg_policy',
                'analysis_timestamp': datetime.now().isoformat(),
                'core_network_id': context.core_network_id,
                'regions_analyzed': context.regions,
                
                # Pure policy data
                'policy_structure': {
                    'policy_version': policy_data.get('policy_version'),
                    'policy_document_version': policy_data.get('document', {}).get('version', 'unknown'),
                    'core_network_configuration': policy_data.get('core_network_configuration', {}),
                    'edge_locations': policy_data.get('document', {}).get('core-network-configuration', {}).get('edge-locations', [])
                },
                
                # NFG data
                'network_function_groups': nfg_data,
                'nfg_summary': {
                    'total_nfgs': len(nfg_data),
                    'send_to_nfgs': len([nfg for nfg in nfg_data if nfg.get('send_to_targets')]),
                    'send_via_nfgs': len([nfg for nfg in nfg_data if nfg.get('send_via_targets')]),
                    'multi_location_nfgs': len([nfg for nfg in nfg_data if len(nfg.get('edge_locations', [])) > 1]),
                    'attachment_acceptance_required': len([nfg for nfg in nfg_data if nfg.get('require_attachment_acceptance', False)])
                },
                
                # Routing data
                'routing_analysis': routing_data,
                
                # Complexity metrics (mathematical only)
                'complexity_metrics': complexity_metrics,
                
                # Data-driven insights
                'data_insights': data_insights,
                
                # Operational metadata
                'operational_data': {
                    'data_extraction_duration_seconds': (datetime.now() - context.start_time).total_seconds(),
                    'policy_size_bytes': len(json.dumps(policy_data.get('document', {}), default=str)),
                    'aws_api_calls_made': self._count_api_calls_made(),
                    'cache_utilization': len(self._cache) > 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"NFG data extraction failed: {e}")
            raise ToolError(f"NFG policy data extraction failed: {e}")
    
    async def _extract_core_network_policy(
        self,
        core_network_id: str,
        regions: List[str]
    ) -> Dict[str, Any]:
        """Extract Core Network policy document."""
        try:
            # Use first region for Network Manager API (global service)
            client = await self.aws_manager.get_client('networkmanager', regions[0])
            
            # Get core network details
            core_network_response = await client.get_core_network(
                CoreNetworkId=core_network_id
            )
            core_network = core_network_response.get('CoreNetwork', {})
            
            # Get current policy
            policy_version_id = core_network.get('PolicyVersionId')
            if not policy_version_id:
                return {}
            
            policy_response = await client.get_core_network_policy(
                CoreNetworkId=core_network_id,
                PolicyVersionId=policy_version_id
            )
            
            policy_document_str = policy_response.get('CoreNetworkPolicy', {}).get('PolicyDocument', '{}')
            policy_document = json.loads(policy_document_str) if isinstance(policy_document_str, str) else policy_document_str
            
            return {
                'core_network_id': core_network_id,
                'policy_version': policy_version_id,
                'document': policy_document,
                'core_network_configuration': core_network,
                'policy_metadata': policy_response.get('CoreNetworkPolicy', {})
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract core network policy: {e}")
            raise AWSOperationError(f"Policy extraction failed: {e}")
    
    async def _extract_nfg_configurations(
        self,
        policy_data: Dict[str, Any],
        context: NFGDataAnalysisContext
    ) -> List[Dict[str, Any]]:
        """Extract Network Function Groups configurations from policy."""
        nfg_configurations = []
        
        try:
            policy_doc = policy_data.get('document', {})
            network_function_groups = policy_doc.get('network-function-groups', [])
            
            for nfg in network_function_groups:
                nfg_config = {
                    'name': nfg.get('name', ''),
                    'description': nfg.get('description', ''),
                    'require_attachment_acceptance': nfg.get('require-attachment-acceptance', False),
                    'tags': nfg.get('tags', {}),
                    'edge_locations': []
                }
                
                # Extract edge locations
                if 'edge-locations' in nfg:
                    for edge_location in nfg['edge-locations']:
                        if isinstance(edge_location, str):
                            nfg_config['edge_locations'].append(edge_location)
                        elif isinstance(edge_location, dict):
                            nfg_config['edge_locations'].append(edge_location.get('location', ''))
                
                # Extract send-to targets
                nfg_config['send_to_targets'] = []
                if 'send-to' in nfg:
                    for target in nfg['send-to']:
                        target_config = {
                            'target_type': self._identify_target_type(target),
                            'target_value': target,
                            'is_segment': self._is_segment_target(target, policy_doc),
                            'is_nfg': self._is_nfg_target(target, network_function_groups)
                        }
                        nfg_config['send_to_targets'].append(target_config)
                
                # Extract send-via targets
                nfg_config['send_via_targets'] = []
                if 'send-via' in nfg:
                    for target in nfg['send-via']:
                        target_config = {
                            'target_type': self._identify_target_type(target),
                            'target_value': target,
                            'is_segment': self._is_segment_target(target, policy_doc),
                            'is_nfg': self._is_nfg_target(target, network_function_groups)
                        }
                        nfg_config['send_via_targets'].append(target_config)
                
                # Add operational metadata
                nfg_config['operational_metadata'] = {
                    'has_description': bool(nfg_config['description']),
                    'has_tags': len(nfg_config['tags']) > 0,
                    'target_count': len(nfg_config['send_to_targets']) + len(nfg_config['send_via_targets']),
                    'edge_location_count': len(nfg_config['edge_locations']),
                    'configuration_complexity': self._calculate_nfg_complexity(nfg_config)
                }
                
                nfg_configurations.append(nfg_config)
                
        except Exception as e:
            self.logger.error(f"Failed to extract NFG configurations: {e}")
        
        return nfg_configurations
    
    async def _extract_routing_rules(
        self,
        policy_data: Dict[str, Any],
        context: NFGDataAnalysisContext
    ) -> Dict[str, Any]:
        """Extract routing rules and segment actions from policy."""
        try:
            policy_doc = policy_data.get('document', {})
            
            # Extract segments
            segments = policy_doc.get('segments', [])
            segment_list = []
            for segment in segments:
                segment_config = {
                    'name': segment.get('name', ''),
                    'description': segment.get('description', ''),
                    'edge_locations': segment.get('edge-locations', []),
                    'isolate_attachments': segment.get('isolate-attachments', False),
                    'allow_filter': segment.get('allow-filter', []),
                    'deny_filter': segment.get('deny-filter', []),
                    'require_attachment_acceptance': segment.get('require-attachment-acceptance', False),
                    'tags': segment.get('tags', {})
                }
                segment_list.append(segment_config)
            
            # Extract segment actions
            segment_actions = policy_doc.get('segment-actions', [])
            action_list = []
            for action in segment_actions:
                action_config = {
                    'action': action.get('action', ''),
                    'segment': action.get('segment', ''),
                    'destinations': action.get('destinations', []),
                    'destination_type': 'segments' if action.get('destinations') else 'none',
                    'via': action.get('via', []),
                    'via_type': self._identify_via_type(action.get('via', []), policy_doc)
                }
                action_list.append(action_config)
            
            # Analyze traffic flows
            traffic_flows = self._analyze_traffic_flows(segment_list, action_list)
            
            return {
                'segments': segment_list,
                'segment_actions': action_list,
                'traffic_flows': traffic_flows,
                'routing_summary': {
                    'total_segments': len(segment_list),
                    'total_actions': len(segment_actions),
                    'isolated_segments': len([s for s in segment_list if s.get('isolate_attachments', False)]),
                    'filtered_segments': len([s for s in segment_list if s.get('allow_filter') or s.get('deny_filter')]),
                    'cross_segment_actions': len([a for a in action_list if a.get('destinations')])
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract routing rules: {e}")
            return {}
    
    def _calculate_complexity_metrics(
        self,
        nfg_data: List[Dict[str, Any]],
        routing_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate mathematical complexity metrics."""
        
        # NFG complexity
        nfg_complexity = 0.0
        if nfg_data:
            total_targets = sum(nfg.get('operational_metadata', {}).get('target_count', 0) for nfg in nfg_data)
            total_locations = sum(nfg.get('operational_metadata', {}).get('edge_location_count', 0) for nfg in nfg_data)
            nfg_complexity = (total_targets + total_locations) / len(nfg_data)
        
        # Routing complexity
        routing_summary = routing_data.get('routing_summary', {})
        routing_complexity = 0.0
        if routing_summary.get('total_segments', 0) > 0:
            routing_complexity = routing_summary.get('total_actions', 0) / routing_summary.get('total_segments', 1)
        
        # Overall complexity
        overall_complexity = (nfg_complexity + routing_complexity) / 2
        
        return {
            'nfg_complexity_score': round(nfg_complexity, 2),
            'routing_complexity_score': round(routing_complexity, 2),
            'overall_complexity_score': round(overall_complexity, 2),
            'complexity_factors': {
                'nfg_count': len(nfg_data),
                'segment_count': routing_summary.get('total_segments', 0),
                'action_count': routing_summary.get('total_actions', 0),
                'cross_segment_actions': routing_summary.get('cross_segment_actions', 0)
            },
            'complexity_category': self._categorize_complexity(overall_complexity)
        }
    
    def _generate_data_insights(
        self,
        nfg_data: List[Dict[str, Any]],
        routing_data: Dict[str, Any],
        complexity_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate data-driven insights without subjective assessments."""
        
        insights = {
            'data_patterns': [],
            'configuration_gaps': [],
            'structural_observations': [],
            'quantitative_analysis': {}
        }
        
        # NFG documentation patterns
        undocumented_nfgs = [nfg['name'] for nfg in nfg_data 
                           if not nfg.get('operational_metadata', {}).get('has_description', False)]
        if undocumented_nfgs:
            insights['data_patterns'].append({
                'pattern': 'missing_descriptions',
                'count': len(undocumented_nfgs),
                'affected_nfgs': undocumented_nfgs[:5],  # Show first 5
                'data_basis': 'nfg.description field empty or missing'
            })
        
        # Edge location distribution
        location_distribution = {}
        for nfg in nfg_data:
            for location in nfg.get('edge_locations', []):
                location_distribution[location] = location_distribution.get(location, 0) + 1
        
        if location_distribution:
            insights['structural_observations'].append({
                'observation': 'edge_location_distribution',
                'data': location_distribution,
                'most_used_location': max(location_distribution, key=location_distribution.get),
                'location_count': len(location_distribution)
            })
        
        # Routing patterns
        routing_summary = routing_data.get('routing_summary', {})
        if routing_summary.get('isolated_segments', 0) > 0:
            insights['structural_observations'].append({
                'observation': 'segment_isolation',
                'isolated_count': routing_summary['isolated_segments'],
                'total_segments': routing_summary['total_segments'],
                'isolation_percentage': round((routing_summary['isolated_segments'] / routing_summary['total_segments']) * 100, 1)
            })
        
        # Target type analysis
        target_types = {'segment': 0, 'nfg': 0, 'other': 0}
        for nfg in nfg_data:
            for target in nfg.get('send_to_targets', []) + nfg.get('send_via_targets', []):
                target_type = target.get('target_type', 'other')
                if target.get('is_segment'):
                    target_types['segment'] += 1
                elif target.get('is_nfg'):
                    target_types['nfg'] += 1
                else:
                    target_types['other'] += 1
        
        insights['quantitative_analysis'] = {
            'target_type_distribution': target_types,
            'average_targets_per_nfg': round(sum(target_types.values()) / max(1, len(nfg_data)), 2),
            'complexity_metrics': complexity_metrics
        }
        
        return insights
    
    # Helper methods
    def _identify_target_type(self, target: str) -> str:
        """Identify the type of a target (segment, NFG, etc.)."""
        if isinstance(target, str):
            if target.startswith('$'):
                return 'variable_reference'
            elif '.' in target:
                return 'qualified_name'
            else:
                return 'simple_name'
        return 'unknown'
    
    def _is_segment_target(self, target: str, policy_doc: Dict[str, Any]) -> bool:
        """Check if target references a segment."""
        segments = policy_doc.get('segments', [])
        segment_names = [seg.get('name', '') for seg in segments]
        return target in segment_names
    
    def _is_nfg_target(self, target: str, nfgs: List[Dict[str, Any]]) -> bool:
        """Check if target references an NFG."""
        nfg_names = [nfg.get('name', '') for nfg in nfgs]
        return target in nfg_names
    
    def _identify_via_type(self, via_list: List[str], policy_doc: Dict[str, Any]) -> str:
        """Identify the type of via targets."""
        if not via_list:
            return 'none'
        
        nfg_names = [nfg.get('name', '') for nfg in policy_doc.get('network-function-groups', [])]
        if any(via in nfg_names for via in via_list):
            return 'nfg'
        return 'other'
    
    def _calculate_nfg_complexity(self, nfg_config: Dict[str, Any]) -> float:
        """Calculate complexity score for a single NFG."""
        score = 0.0
        score += len(nfg_config.get('send_to_targets', []))
        score += len(nfg_config.get('send_via_targets', []))
        score += len(nfg_config.get('edge_locations', [])) * 0.5
        return score
    
    def _analyze_traffic_flows(
        self,
        segments: List[Dict[str, Any]],
        actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze traffic flows based on segments and actions."""
        flows = []
        
        for action in actions:
            flow = {
                'source_segment': action.get('segment', ''),
                'action_type': action.get('action', ''),
                'destinations': action.get('destinations', []),
                'via_nfgs': action.get('via', []),
                'flow_type': 'direct' if not action.get('via') else 'via_nfg'
            }
            flows.append(flow)
        
        return flows
    
    def _categorize_complexity(self, complexity_score: float) -> str:
        """Categorize complexity score into levels."""
        if complexity_score < 1.0:
            return 'simple'
        elif complexity_score < 3.0:
            return 'moderate'
        elif complexity_score < 5.0:
            return 'complex'
        else:
            return 'highly_complex'
    
    def _count_api_calls_made(self) -> int:
        """Count approximate API calls made during analysis."""
        # This would track actual API calls in a real implementation
        return 3  # Placeholder: get_core_network, get_core_network_policy, describe_attachments


class NFGDataAnalyzerTool(BaseMCPTool):
    """Data-Only NFG Policy Analyzer MCP Tool."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        self.nfg_analyzer = NFGDataAnalyzer(aws_manager, config)
        self._load_time = 0.0
        self._start_time = time.time()
        
        # Record load time
        self._load_time = time.time() - self._start_time
        logger.info(f"NFGDataAnalyzerTool initialized in {self._load_time:.3f}s")
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the tool input schema."""
        return {
            "type": "object",
            "properties": {
                "core_network_id": {
                    "type": "string",
                    "description": "CloudWAN Core Network ID to analyze",
                    "pattern": r"^core-network-[0-9a-f]{17}$"
                },
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "AWS regions for analysis (default: ['us-east-1'])",
                    "default": ["us-east-1"]
                },
                "include_rule_details": {
                    "type": "boolean",
                    "description": "Include detailed routing rule analysis",
                    "default": True
                },
                "include_routing_analysis": {
                    "type": "boolean",
                    "description": "Include traffic flow and routing analysis",
                    "default": True
                },
                "include_complexity_metrics": {
                    "type": "boolean",
                    "description": "Include mathematical complexity scoring",
                    "default": True
                }
            },
            "required": ["core_network_id"]
        }
    
    @handle_errors
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute data-only NFG policy analysis."""
        
        # Extract and validate parameters
        core_network_id = kwargs.get('core_network_id')
        regions = kwargs.get('regions', ['us-east-1'])
        include_rule_details = kwargs.get('include_rule_details', True)
        include_routing_analysis = kwargs.get('include_routing_analysis', True)
        include_complexity_metrics = kwargs.get('include_complexity_metrics', True)
        
        if not core_network_id:
            raise ValidationError("core_network_id is required")
        
        validate_regions(regions, self.config)
        
        # Create analysis context
        context = NFGDataAnalysisContext(
            analysis_id=str(uuid.uuid4()),
            core_network_id=core_network_id,
            regions=regions,
            start_time=datetime.now(),
            include_rule_details=include_rule_details,
            include_routing_analysis=include_routing_analysis
        )
        
        # Perform data-only NFG analysis
        try:
            analysis_result = await self.nfg_analyzer.analyze_nfg_policy(context)
            
            # Filter results based on user preferences
            if not include_rule_details:
                analysis_result.pop('routing_analysis', None)
            
            if not include_routing_analysis:
                analysis_result['data_insights'].pop('structural_observations', None)
            
            if not include_complexity_metrics:
                analysis_result.pop('complexity_metrics', None)
            
            # Add tool metadata
            analysis_result['tool_metadata'] = {
                'tool_type': 'data_only_nfg_analyzer',
                'llm_enhanced': False,
                'data_extraction_only': True,
                'load_time_seconds': self._load_time,
                'execution_time_seconds': (datetime.now() - context.start_time).total_seconds()
            }
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"NFG data analysis failed: {e}")
            raise ToolError(f"NFG policy data extraction failed: {e}")
    
    @property
    def tool_name(self) -> str:
        """Tool name for MCP registration."""
        return "analyze_nfg_policy_data_only"
    
    @property  
    def description(self) -> str:
        """Tool description for MCP registration."""
        return "Extract pure NFG policy data from CloudWAN Core Network without LLM validation or interpretive analysis"
    
    def get_load_time(self) -> float:
        """Get tool load time in seconds."""
        return self._load_time