"""
Standalone LLM-based Firewall Policy Advisor.

This module provides LLM-enhanced firewall policy analysis that consumes
pure data from the core MCP firewall tools and adds interpretive insights.
"""

import logging
from typing import Any, Dict, List
from dataclasses import dataclass

from ..llm.config import LLMConfig, LLMProvider
from ..llm.manager import LLMManager, LLMValidationError
from ..llm.validators import FirewallPolicyValidator


@dataclass
class FirewallAdvisorContext:
    """Context for firewall policy advisory analysis."""
    
    firewall_data: Dict[str, Any]  # Pure data from MCP tool
    analysis_scope: str = "comprehensive"
    focus_areas: List[str] = None
    
    def __post_init__(self):
        if self.focus_areas is None:
            self.focus_areas = ["security", "performance", "compliance"]


class FirewallPolicyAdvisor:
    """
    Standalone LLM-powered firewall policy advisor.
    
    Consumes factual firewall policy data from MCP tools and provides
    enhanced insights, recommendations, and risk assessments using LLM analysis.
    """
    
    def __init__(self, llm_config: LLMConfig):
        """Initialize the firewall policy advisor."""
        self.llm_config = llm_config
        self.llm_manager = LLMManager(llm_config)
        self.firewall_validator = FirewallPolicyValidator(self.llm_manager)
        
        self.logger = logging.getLogger(f"{__name__}.FirewallPolicyAdvisor")
        
        if llm_config.provider != LLMProvider.NONE:
            self.logger.info(f"Firewall Policy Advisor initialized with LLM provider: {llm_config.provider.value}")
        else:
            self.logger.warning("Firewall Policy Advisor initialized without LLM provider")
    
    async def analyze_firewall_policy(
        self,
        context: FirewallAdvisorContext
    ) -> Dict[str, Any]:
        """
        Provide LLM-enhanced firewall policy analysis.
        
        Args:
            context: Analysis context with pure firewall data
            
        Returns:
            LLM-enhanced analysis with insights and recommendations
        """
        try:
            if self.llm_config.provider == LLMProvider.NONE:
                return self._provide_fallback_analysis(context)
            
            # Extract pure data for LLM analysis
            firewall_data = context.firewall_data
            
            # Prepare LLM analysis context
            llm_context = {
                'firewall_policies': firewall_data.get('firewall_policies', []),
                'rule_analyses': firewall_data.get('rule_analyses', []),
                'security_posture_score': firewall_data.get('security_posture_score', 0.0),
                'performance_analysis': firewall_data.get('performance_analysis', {}),
                'conflict_matrix': firewall_data.get('conflict_matrix', []),
                'coverage_analysis': firewall_data.get('coverage_analysis', {}),
                'analysis_scope': context.analysis_scope,
                'focus_areas': context.focus_areas
            }
            
            # Get LLM insights
            llm_result = await self.firewall_validator.validate(llm_context)
            
            # Structure enhanced analysis
            enhanced_analysis = {
                'advisor_analysis': {
                    'analysis_type': 'llm_enhanced_firewall_policy',
                    'llm_provider': self.llm_config.provider.value,
                    'analysis_timestamp': llm_result.get('timestamp'),
                    'confidence_score': llm_result.get('confidence_score', 0.0)
                },
                'security_insights': {
                    'risk_assessment': llm_result.get('security_assessment', {}),
                    'threat_correlation': llm_result.get('threat_patterns', []),
                    'security_gaps': llm_result.get('security_gaps', []),
                    'attack_surface_analysis': llm_result.get('attack_surface', {})
                },
                'policy_recommendations': {
                    'optimization_suggestions': llm_result.get('optimizations', []),
                    'rule_improvements': llm_result.get('rule_improvements', []),
                    'best_practices': llm_result.get('best_practices', []),
                    'priority_actions': llm_result.get('priority_actions', [])
                },
                'compliance_analysis': {
                    'framework_assessment': llm_result.get('compliance_status', {}),
                    'compliance_gaps': llm_result.get('compliance_gaps', []),
                    'remediation_roadmap': llm_result.get('remediation_steps', [])
                },
                'performance_insights': {
                    'optimization_opportunities': llm_result.get('performance_optimizations', []),
                    'resource_efficiency': llm_result.get('resource_analysis', {}),
                    'scaling_recommendations': llm_result.get('scaling_guidance', [])
                }
            }
            
            return enhanced_analysis
            
        except LLMValidationError as e:
            self.logger.error(f"LLM validation failed: {e}")
            return self._provide_fallback_analysis(context)
        except Exception as e:
            self.logger.error(f"Firewall policy analysis failed: {e}")
            raise
    
    def _provide_fallback_analysis(
        self,
        context: FirewallAdvisorContext
    ) -> Dict[str, Any]:
        """
        Provide fallback analysis when LLM is unavailable.
        
        Args:
            context: Analysis context
            
        Returns:
            Basic analysis without LLM enhancement
        """
        firewall_data = context.firewall_data
        
        return {
            'advisor_analysis': {
                'analysis_type': 'fallback_firewall_analysis',
                'llm_provider': 'none',
                'analysis_timestamp': None,
                'confidence_score': 0.0
            },
            'security_insights': {
                'message': 'LLM security analysis unavailable - using data-only approach',
                'data_driven_score': firewall_data.get('security_posture_score', 0.0)
            },
            'policy_recommendations': {
                'message': 'LLM recommendations unavailable - review raw data for insights'
            },
            'compliance_analysis': {
                'message': 'LLM compliance analysis unavailable'
            },
            'performance_insights': {
                'message': 'LLM performance insights unavailable',
                'basic_metrics': firewall_data.get('performance_analysis', {})
            }
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the firewall policy advisor."""
        health_status = await self.llm_manager.health_check()
        cache_stats = self.llm_manager.get_cache_stats()
        
        return {
            'advisor_health': health_status,
            'cache_statistics': cache_stats,
            'configuration': {
                'provider': self.llm_config.provider.value,
                'validation_enabled': self.llm_config.validation_enabled,
                'fallback_enabled': self.llm_config.fallback_to_heuristics
            }
        }