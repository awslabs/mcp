"""
CloudWAN MCP BLEU Consensus Framework

This package provides comprehensive BLEU score consensus voting capabilities
for evaluating and ranking solutions from multiple AI agents working on
CloudWAN MCP server implementations.

The framework analyzes code quality, performance, integration, test coverage,
and documentation to provide consensus-based recommendations for optimal
architecture decisions.
"""

from .bleu_framework import (
    BLEUConsensusFramework,
    AgentEvaluationMetrics,
    AgentImplementationAnalysis,
    ConsensusResults,
    run_bleu_consensus_analysis,
)

from .report_generator import (
    BLEUConsensusReportGenerator,
    generate_bleu_consensus_report,
)

__version__ = "1.0.0"
__author__ = "CloudWAN MCP Agent Consensus Team"

__all__ = [
    "BLEUConsensusFramework",
    "AgentEvaluationMetrics",
    "AgentImplementationAnalysis",
    "ConsensusResults",
    "BLEUConsensusReportGenerator",
    "run_bleu_consensus_analysis",
    "generate_bleu_consensus_report",
]
