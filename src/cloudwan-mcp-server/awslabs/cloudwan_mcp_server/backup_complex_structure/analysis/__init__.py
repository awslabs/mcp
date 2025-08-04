"""
Standalone LLM Analysis Modules for CloudWAN MCP Server.

This module provides optional LLM-powered analysis capabilities that can be used
independently of the core MCP tools. The MCP server provides factual data only,
while these modules offer enhanced interpretive analysis for users who need it.

Architecture:
- Core MCP tools extract and return factual AWS data
- These analysis modules consume that data and provide LLM-enhanced insights
- Users can choose data-only or data + LLM analysis approaches

Modules:
- firewall_policy_advisor: LLM-based firewall policy recommendations
- threat_intelligence: LLM threat pattern recognition and correlation
- compliance_advisor: LLM compliance framework guidance
- security_risk_evaluator: LLM security risk assessments
- connectivity_advisor: LLM connectivity troubleshooting insights
- policy_optimization_advisor: LLM CloudWAN policy optimization
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..aws.client_manager import AWSClientManager
    from ..config import CloudWANConfig

__all__ = [
    'FirewallPolicyAdvisor',
    'ThreatIntelligenceAnalyzer', 
    'ComplianceAdvisor',
    'SecurityRiskEvaluator',
    'ConnectivityAdvisor',
    'PolicyOptimizationAdvisor'
]

# Version info for LLM analysis modules
__version__ = "1.0.0"
__description__ = "Standalone LLM analysis modules for CloudWAN MCP"