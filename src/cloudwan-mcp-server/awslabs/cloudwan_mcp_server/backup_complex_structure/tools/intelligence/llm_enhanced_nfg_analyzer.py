"""
LLM-Enhanced Network Function Groups (NFG) Policy Analysis Tool.

This module provides enhanced NFG policy analysis that integrates LLM-powered
validation for deeper insights into NFG configurations, routing logic,
security implications, and operational efficiency.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

from ...aws.client_manager import AWSClientManager
from ...config import CloudWANConfig
from ...llm.config import LLMConfig, LLMProvider
from ...llm.manager import LLMManager, LLMValidationError
from ...llm.validators import NFGPolicyValidator
from ..base import (
    BaseMCPTool,
    ToolError,
    handle_errors,
)
from .nfg_policy_explainer import (
    NFGPolicyExplainerTool, 
    NFGAnalysisContext
)

logger = logging.getLogger(__name__)


class LLMEnhancedNFGPolicyAnalyzer(NFGPolicyExplainerTool):
    """Enhanced NFG policy analyzer with LLM integration."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        
        # Initialize LLM components
        self.llm_config = LLMConfig.from_dict(config.llm.model_dump())
        self.llm_manager = LLMManager(self.llm_config)
        self.nfg_validator = NFGPolicyValidator(self.llm_manager)
        
        self.logger = logging.getLogger(f"{__name__}.LLMEnhancedNFGPolicyAnalyzer")
        
        # Log LLM configuration
        if self.llm_config.provider != LLMProvider.NONE:
            self.logger.info(f"LLM validation enabled with provider: {self.llm_config.provider.value}")
        else:
            self.logger.info("LLM validation disabled - using heuristic analysis only")
    
    async def analyze_nfg_policies(
        self,
        context: NFGAnalysisContext
    ) -> Dict[str, Any]:
        """Enhanced NFG policy analysis with LLM validation."""
        
        try:
            # Perform base analysis
            base_result = await super().analyze_nfg_policies(context)
            
            # Enhance with LLM validation if enabled
            if self.llm_config.validation_enabled:
                enhanced_result = await self._enhance_with_llm_validation(base_result, context)
                return enhanced_result
            else:
                self.logger.info("LLM validation disabled - returning base analysis")
                return base_result
                
        except Exception as e:
            self.logger.error(f"Enhanced NFG policy analysis failed: {e}")
            raise ToolError(f"LLM-enhanced NFG policy analysis failed: {e}")
    
    async def _enhance_with_llm_validation(
        self,
        base_result: Dict[str, Any],
        context: NFGAnalysisContext
    ) -> Dict[str, Any]:
        """Enhance base analysis results with LLM validation."""
        
        self.logger.info("Enhancing NFG analysis with LLM validation")
        
        # Extract NFG data from base result
        nfgs_data = base_result.get('network_function_groups', [])
        
        # Prepare context for LLM validation
        validation_context = {
            'network_function_groups': [
                {
                    'name': nfg.get('name', 'unnamed'),
                    'description': nfg.get('description', ''),
                    'require_attachment_acceptance': nfg.get('require_attachment_acceptance', False),
                    'edge_locations': nfg.get('edge_locations', []),
                    'send_to_targets': nfg.get('send_to_targets', []),
                    'send_via_targets': nfg.get('send_via_targets', []),
                    'routing_complexity': self._calculate_routing_complexity(nfg)
                } for nfg in nfgs_data
            ],
            'policy_overview': base_result.get('policy_overview', {}),
            'routing_analysis': base_result.get('routing_analysis', {}),
            'performance_metrics': base_result.get('performance_metrics', {}),
            'operational_insights': base_result.get('operational_insights', {})
        }
        
        try:
            # Get LLM validation results
            llm_result = await self.nfg_validator.validate(validation_context)
            
            # Integrate LLM insights into base result
            enhanced_result = await self._integrate_llm_insights(base_result, llm_result)
            
            return enhanced_result
            
        except LLMValidationError as e:
            self.logger.error(f"LLM validation failed: {e}")
            if self.llm_config.fallback_to_heuristics:
                self.logger.info("Falling back to base analysis due to LLM validation failure")
                base_result['llm_validation_status'] = "failed_fallback_used"
                base_result['llm_validation_error'] = str(e)
                return base_result
            else:
                raise ToolError(f"LLM validation failed and fallback disabled: {e}")
    
    def _calculate_routing_complexity(self, nfg: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate routing complexity metrics for an NFG."""
        
        send_to_count = len(nfg.get('send_to_targets', []))
        send_via_count = len(nfg.get('send_via_targets', []))
        edge_location_count = len(nfg.get('edge_locations', []))
        
        # Calculate complexity score
        complexity_score = (
            send_to_count * 0.2 +
            send_via_count * 0.4 +  # send-via is more complex
            (0.3 if send_to_count > 0 and send_via_count > 0 else 0) +  # mixed config penalty
            edge_location_count * 0.1
        )
        
        complexity_level = (
            'high' if complexity_score > 2.0 else
            'medium' if complexity_score > 1.0 else
            'low'
        )
        
        return {
            'send_to_targets': send_to_count,
            'send_via_targets': send_via_count,
            'edge_locations': edge_location_count,
            'complexity_score': complexity_score,
            'complexity_level': complexity_level,
            'has_mixed_configuration': send_to_count > 0 and send_via_count > 0,
            'multi_location': edge_location_count > 1
        }
    
    async def _integrate_llm_insights(
        self,
        base_result: Dict[str, Any],
        llm_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Integrate LLM validation insights into base analysis result."""
        
        # Extract LLM validation results
        llm_validation = llm_result.get('validation_result', {})
        
        # Create enhanced result with LLM insights
        enhanced_result = base_result.copy()
        enhanced_result['analysis_type'] = 'llm_enhanced'
        enhanced_result['llm_validation_status'] = 'success'
        enhanced_result['llm_validation_provider'] = llm_result.get('provider', 'unknown')
        
        # Add LLM-specific analysis
        if 'validation_status' in llm_validation:
            enhanced_result['llm_nfg_analysis'] = {
                'validation_status': llm_validation['validation_status'],
                'risk_level': llm_validation.get('risk_level', 'unknown'),
                'security_score': llm_validation.get('security_score', 0.0),
                'findings': llm_validation.get('findings', []),
                'recommendations': llm_validation.get('recommendations', []),
                'compliance_status': llm_validation.get('compliance_status', {})
            }
        
        # Integrate NFG-specific analysis from LLM
        if 'nfg_analysis' in llm_result:
            enhanced_result['enhanced_nfg_insights'] = llm_result['nfg_analysis']
        
        # Enhance operational insights with LLM recommendations
        llm_recommendations = llm_validation.get('recommendations', [])
        if llm_recommendations:
            enhanced_insights = enhanced_result.get('operational_insights', {})
            enhanced_insights['llm_recommendations'] = {
                'routing_optimization': [],
                'security_improvements': [],
                'performance_enhancements': [],
                'operational_best_practices': []
            }
            
            # Categorize LLM recommendations
            for recommendation in llm_recommendations:
                rec_lower = recommendation.lower()
                if any(keyword in rec_lower for keyword in ['route', 'routing', 'path']):
                    enhanced_insights['llm_recommendations']['routing_optimization'].append(recommendation)
                elif any(keyword in rec_lower for keyword in ['security', 'access', 'acceptance']):
                    enhanced_insights['llm_recommendations']['security_improvements'].append(recommendation)
                elif any(keyword in rec_lower for keyword in ['performance', 'latency', 'throughput']):
                    enhanced_insights['llm_recommendations']['performance_enhancements'].append(recommendation)
                else:
                    enhanced_insights['llm_recommendations']['operational_best_practices'].append(recommendation)
            
            enhanced_result['operational_insights'] = enhanced_insights
        
        # Integrate LLM findings into policy gaps
        llm_findings = llm_validation.get('findings', [])
        critical_findings = [
            f.get('message', '') for f in llm_findings 
            if f.get('severity') in ['high', 'critical']
        ]
        if critical_findings:
            enhanced_gaps = enhanced_result.get('policy_gaps', [])
            enhanced_gaps.extend([f"LLM Analysis: {finding}" for finding in critical_findings])
            enhanced_result['policy_gaps'] = enhanced_gaps
        
        # Enhance routing analysis with LLM insights
        if 'routing_analysis' in enhanced_result and 'nfg_analysis' in llm_result:
            llm_routing = llm_result['nfg_analysis'].get('routing_patterns', {})
            enhanced_result['routing_analysis']['llm_insights'] = {
                'pattern_analysis': llm_routing,
                'optimization_opportunities': self._identify_optimization_opportunities(llm_routing),
                'risk_assessment': self._assess_routing_risks(llm_routing)
            }
        
        self.logger.info(f"Successfully integrated LLM insights from {llm_result.get('provider')}")
        
        return enhanced_result
    
    def _identify_optimization_opportunities(self, routing_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify optimization opportunities from LLM routing analysis."""
        
        opportunities = []
        
        # Service chaining optimization
        if routing_patterns.get('service_chaining', 0) > 2:
            opportunities.append({
                'type': 'service_chaining',
                'priority': 'high',
                'description': 'Multiple service chaining detected - consider consolidation to reduce latency',
                'impact': 'performance'
            })
        
        # Geographic distribution optimization
        if routing_patterns.get('single_location_nfgs', 0) > routing_patterns.get('multi_location_nfgs', 0):
            opportunities.append({
                'type': 'geographic_distribution',
                'priority': 'medium',
                'description': 'Consider distributing NFGs across multiple edge locations for resilience',
                'impact': 'availability'
            })
        
        # Hub-spoke optimization
        if routing_patterns.get('hub_spoke', 0) > 3:
            opportunities.append({
                'type': 'hub_spoke_optimization',
                'priority': 'medium', 
                'description': 'Hub-spoke pattern detected - evaluate for potential bottlenecks',
                'impact': 'performance'
            })
        
        return opportunities
    
    def _assess_routing_risks(self, routing_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess routing risks from LLM analysis."""
        
        risks = []
        
        # Single point of failure risk
        single_location_count = routing_patterns.get('single_location_nfgs', 0)
        if single_location_count > 0:
            risks.append({
                'type': 'single_point_of_failure',
                'severity': 'high' if single_location_count > 2 else 'medium',
                'description': f'{single_location_count} NFGs deployed in single locations',
                'mitigation': 'Deploy NFGs across multiple edge locations for redundancy'
            })
        
        # Complex service chaining risk
        service_chaining_count = routing_patterns.get('service_chaining', 0)
        if service_chaining_count > 3:
            risks.append({
                'type': 'complex_service_chaining',
                'severity': 'medium',
                'description': 'Complex service chaining may impact performance and troubleshooting',
                'mitigation': 'Simplify service chains and implement comprehensive monitoring'
            })
        
        return risks
    
    async def get_llm_health_status(self) -> Dict[str, Any]:
        """Get LLM integration health status."""
        
        health_status = await self.llm_manager.health_check()
        cache_stats = self.llm_manager.get_cache_stats()
        
        return {
            'llm_health': health_status,
            'cache_statistics': cache_stats,
            'configuration': {
                'provider': self.llm_config.provider.value,
                'validation_enabled': self.llm_config.validation_enabled,
                'fallback_enabled': self.llm_config.fallback_to_heuristics,
                'nfg_validation_enabled': self.llm_config.nfg_validation_enabled
            }
        }


class LLMEnhancedNFGPolicyAnalysisTool(BaseMCPTool):
    """LLM-Enhanced Premium Tier NFG Policy Analysis Tool."""
    
    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        super().__init__(aws_manager, config)
        self.enhanced_nfg_analyzer = LLMEnhancedNFGPolicyAnalyzer(aws_manager, config)
        self._load_time = 0.0
        self._start_time = time.time()
        
        # Record load time
        self._load_time = time.time() - self._start_time
        logger.info(f"LLMEnhancedNFGPolicyAnalysisTool initialized in {self._load_time:.3f}s")
    
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
                    "description": "Specific segment names to focus on (optional)",
                    "default": []
                },
                "analysis_depth": {
                    "type": "string",
                    "enum": ["basic", "detailed", "comprehensive", "llm_enhanced"],
                    "description": "Depth of NFG analysis (llm_enhanced provides AI-powered validation)",
                    "default": "llm_enhanced"
                },
                "include_routing_analysis": {
                    "type": "boolean",
                    "description": "Include detailed routing logic analysis",
                    "default": True
                },
                "include_security_analysis": {
                    "type": "boolean",
                    "description": "Include security posture assessment",
                    "default": True
                },
                "include_performance_analysis": {
                    "type": "boolean",
                    "description": "Include performance optimization analysis",
                    "default": True
                },
                "llm_validation": {
                    "type": "boolean",
                    "description": "Enable LLM-powered validation (overrides config)",
                    "default": True
                }
            },
            "required": []
        }
    
    @handle_errors
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute LLM-enhanced comprehensive NFG policy analysis."""
        
        # Extract and validate parameters
        regions = kwargs.get('regions', ['us-east-1'])
        core_network_ids = kwargs.get('core_network_ids', [])
        segment_names = kwargs.get('segment_names', [])
        analysis_depth = kwargs.get('analysis_depth', 'llm_enhanced')
        include_routing_analysis = kwargs.get('include_routing_analysis', True)
        include_security_analysis = kwargs.get('include_security_analysis', True)
        include_performance_analysis = kwargs.get('include_performance_analysis', True)
        llm_validation = kwargs.get('llm_validation', True)
        
        # Override LLM validation setting if specified
        if not llm_validation:
            self.enhanced_nfg_analyzer.llm_config.validation_enabled = False
        
        # Create analysis context
        context = NFGAnalysisContext(
            analysis_id=str(uuid.uuid4()),
            regions=regions,
            core_network_ids=core_network_ids if core_network_ids else None,
            segment_names=segment_names if segment_names else None,
            analysis_depth=analysis_depth,
            start_time=datetime.now()
        )
        
        # Perform enhanced NFG analysis
        try:
            analysis_result = await self.enhanced_nfg_analyzer.analyze_nfg_policies(context)
            
            # Get LLM health status
            llm_health = await self.enhanced_nfg_analyzer.get_llm_health_status()
            
            # Format results for MCP
            result = {
                "analysis_id": analysis_result.get('analysis_id', context.analysis_id),
                "analysis_type": "llm_enhanced_nfg_policy",
                "nfg_summary": {
                    "total_nfgs": len(analysis_result.get('network_function_groups', [])),
                    "send_to_nfgs": len([nfg for nfg in analysis_result.get('network_function_groups', []) 
                                       if nfg.get('send_to_targets')]),
                    "send_via_nfgs": len([nfg for nfg in analysis_result.get('network_function_groups', []) 
                                        if nfg.get('send_via_targets')]),
                    "multi_location_nfgs": len([nfg for nfg in analysis_result.get('network_function_groups', []) 
                                              if len(nfg.get('edge_locations', [])) > 1])
                },
                "policy_overview": analysis_result.get('policy_overview', {}),
                "network_function_groups": analysis_result.get('network_function_groups', []),
                "routing_analysis": analysis_result.get('routing_analysis', {}),
                "llm_enhanced_analysis": analysis_result.get('llm_nfg_analysis', {}),
                "enhanced_nfg_insights": analysis_result.get('enhanced_nfg_insights', {}),
                "operational_insights": analysis_result.get('operational_insights', {}),
                "performance_metrics": analysis_result.get('performance_metrics', {}),
                "policy_gaps": analysis_result.get('policy_gaps', []),
                "llm_validation_status": analysis_result.get('llm_validation_status', 'not_attempted'),
                "llm_provider": analysis_result.get('llm_validation_provider', 'none'),
                "regions_analyzed": analysis_result.get('regions_analyzed', regions),
                "analysis_timestamp": datetime.now().isoformat(),
                "llm_health_status": llm_health,
                "tool_performance": {
                    "load_time_seconds": self._load_time,
                    "execution_time_seconds": (datetime.now() - context.start_time).total_seconds()
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM-enhanced NFG policy analysis failed: {e}")
            raise ToolError(f"Enhanced NFG policy analysis failed: {e}")
    
    def get_load_time(self) -> float:
        """Get tool load time in seconds."""
        return self._load_time
    
    @property
    def tool_name(self) -> str:
        """Tool name for MCP registration."""
        return "analyze_nfg_policies_enhanced"
    
    @property  
    def description(self) -> str:
        """Tool description for MCP registration."""
        return "LLM-Enhanced analysis of CloudWAN Network Function Groups (NFG) policies with AI-powered validation, routing analysis, and optimization recommendations"