"""
BLEU Score Consensus Voting Framework for CloudWAN MCP Agent Evaluation

This module implements a comprehensive BLEU (Bilingual Evaluation Understudy) score
consensus voting system to evaluate and rank solutions from multiple AI agents working
on the CloudWAN MCP server implementation.

The framework analyzes code quality, performance, integration, test coverage, and 
documentation across all agent implementations to determine optimal solutions.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import asyncio
from collections import defaultdict

import nltk
from nltk.translate.bleu_score import SmoothingFunction


# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")


@dataclass
class AgentEvaluationMetrics:
    """Comprehensive metrics for evaluating agent implementations."""

    # Code Quality Metrics (30% weight)
    code_readability_score: float = 0.0
    maintainability_score: float = 0.0
    standards_compliance_score: float = 0.0
    architecture_quality_score: float = 0.0

    # Performance Metrics (25% weight)
    efficiency_score: float = 0.0
    scalability_score: float = 0.0
    resource_optimization_score: float = 0.0
    response_time_score: float = 0.0

    # Integration Metrics (20% weight)
    mcp_compatibility_score: float = 0.0
    api_design_score: float = 0.0
    component_integration_score: float = 0.0
    interoperability_score: float = 0.0

    # Test Coverage Metrics (15% weight)
    unit_test_coverage: float = 0.0
    integration_test_coverage: float = 0.0
    edge_case_handling: float = 0.0
    test_quality_score: float = 0.0

    # Documentation Metrics (10% weight)
    code_documentation_score: float = 0.0
    api_documentation_score: float = 0.0
    usage_examples_score: float = 0.0
    documentation_completeness: float = 0.0

    # Calculated Scores
    weighted_score: float = field(init=False)
    category_scores: Dict[str, float] = field(default_factory=dict, init=False)

    def __post_init__(self):
        """Calculate weighted scores after initialization."""
        self.category_scores = {
            "code_quality": (
                self.code_readability_score
                + self.maintainability_score
                + self.standards_compliance_score
                + self.architecture_quality_score
            )
            / 4.0,
            "performance": (
                self.efficiency_score
                + self.scalability_score
                + self.resource_optimization_score
                + self.response_time_score
            )
            / 4.0,
            "integration": (
                self.mcp_compatibility_score
                + self.api_design_score
                + self.component_integration_score
                + self.interoperability_score
            )
            / 4.0,
            "test_coverage": (
                self.unit_test_coverage
                + self.integration_test_coverage
                + self.edge_case_handling
                + self.test_quality_score
            )
            / 4.0,
            "documentation": (
                self.code_documentation_score
                + self.api_documentation_score
                + self.usage_examples_score
                + self.documentation_completeness
            )
            / 4.0,
        }

        # Calculate weighted score using specified weights
        weights = {
            "code_quality": 0.30,
            "performance": 0.25,
            "integration": 0.20,
            "test_coverage": 0.15,
            "documentation": 0.10,
        }

        self.weighted_score = sum(
            self.category_scores[category] * weight for category, weight in weights.items()
        )


@dataclass
class AgentImplementationAnalysis:
    """Analysis results for a single agent's implementation."""

    agent_id: str
    agent_name: str
    agent_role: str

    # File Analysis
    total_files: int = 0
    total_lines_of_code: int = 0
    implementation_files: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    documentation_files: List[str] = field(default_factory=list)

    # Code Analysis
    function_count: int = 0
    class_count: int = 0
    complexity_score: float = 0.0
    duplication_score: float = 0.0

    # Quality Metrics
    metrics: AgentEvaluationMetrics = field(default_factory=AgentEvaluationMetrics)

    # BLEU Scores
    bleu_scores: Dict[str, float] = field(default_factory=dict)

    # Strengths and Weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ConsensusResults:
    """Final consensus results with rankings and recommendations."""

    agent_analyses: List[AgentImplementationAnalysis]
    rankings: List[Tuple[str, float]]  # (agent_name, score)

    # Best Practices Identified
    best_practices: Dict[str, List[str]] = field(default_factory=dict)

    # Integration Recommendations
    optimal_solutions: Dict[str, str] = field(default_factory=dict)
    integration_plan: List[str] = field(default_factory=list)

    # Performance Analysis
    performance_leaders: Dict[str, str] = field(default_factory=dict)
    optimization_opportunities: List[str] = field(default_factory=list)

    # Overall Assessment
    consensus_score: float = 0.0
    consensus_confidence: float = 0.0

    generation_timestamp: datetime = field(default_factory=datetime.now)


class BLEUConsensusFramework:
    """
    Main BLEU consensus framework for evaluating multi-agent implementations.

    This framework analyzes code quality, performance, integration capabilities,
    test coverage, and documentation across all agent implementations to determine
    optimal solutions and provide consensus-based recommendations.
    """

    def __init__(self, project_root: str):
        """Initialize the BLEU consensus framework."""
        self.project_root = Path(project_root)
        self.logger = logging.getLogger(__name__)

        # Agent definitions
        self.agents = {
            "agent1": {
                "name": "Foundation Engine Architect",
                "role": "Multi-region processing & IP resolution capabilities",
                "directories": ["engines/", "aws/"],
                "focus_areas": ["ip_resolution", "multi_region", "client_management"],
            },
            "agent2": {
                "name": "CloudWAN Policy Specialist",
                "role": "Core Networks & segment analysis enhancements",
                "directories": ["engines/", "tools/cloudwan/"],
                "focus_areas": [
                    "policy_analysis",
                    "segment_discovery",
                    "network_function_groups",
                ],
            },
            "agent3": {
                "name": "Transit Gateway Expert",
                "role": "TGW routing & peering analysis optimizations",
                "directories": ["engines/", "tools/core/"],
                "focus_areas": ["tgw_analysis", "peering_discovery", "cross_account"],
            },
            "agent4": {
                "name": "Path Tracing Algorithm Designer",
                "role": "End-to-end path discovery algorithms",
                "directories": ["engines/", "tools/analysis/", "tools/core/"],
                "focus_areas": ["path_tracing", "network_analysis", "graph_algorithms"],
            },
            "agent5": {
                "name": "Integration & Performance Engineer",
                "role": "MCP integration & system optimization",
                "directories": ["performance/", "protocol/", "monitoring/"],
                "focus_areas": [
                    "mcp_integration",
                    "performance_optimization",
                    "monitoring",
                ],
            },
        }

        # Initialize analysis components
        self.smoothing_function = SmoothingFunction().method1

    async def analyze_all_agents(self) -> ConsensusResults:
        """Perform comprehensive analysis of all agent implementations."""
        self.logger.info("Starting comprehensive BLEU consensus analysis")

        agent_analyses = []

        # Analyze each agent in parallel
        analysis_tasks = [
            self._analyze_agent(agent_id, agent_config)
            for agent_id, agent_config in self.agents.items()
        ]

        agent_analyses = await asyncio.gather(*analysis_tasks)

        # Generate consensus results
        consensus_results = await self._generate_consensus(agent_analyses)

        self.logger.info("BLEU consensus analysis completed")
        return consensus_results

    async def _analyze_agent(
        self, agent_id: str, agent_config: Dict
    ) -> AgentImplementationAnalysis:
        """Analyze a single agent's implementation comprehensively."""
        analysis = AgentImplementationAnalysis(
            agent_id=agent_id,
            agent_name=agent_config["name"],
            agent_role=agent_config["role"],
        )

        # Find agent's implementation files
        implementation_files = await self._find_agent_files(agent_config)
        analysis.implementation_files = implementation_files

        # Analyze code structure and quality
        await self._analyze_code_structure(analysis, implementation_files)

        # Calculate evaluation metrics
        await self._calculate_evaluation_metrics(analysis)

        # Calculate BLEU scores
        await self._calculate_bleu_scores(analysis)

        # Identify strengths and weaknesses
        await self._identify_strengths_weaknesses(analysis)

        return analysis

    async def _find_agent_files(self, agent_config: Dict) -> List[str]:
        """Find all files related to an agent's implementation."""
        implementation_files = []
        src_path = self.project_root / "src" / "cloudwan_mcp"

        # Search in agent's focus directories
        for directory in agent_config["directories"]:
            dir_path = src_path / directory
            if dir_path.exists():
                for file_path in dir_path.rglob("*.py"):
                    if file_path.is_file() and not file_path.name.startswith("__"):
                        implementation_files.append(str(file_path.relative_to(self.project_root)))

        # Also search for files matching focus areas
        for focus_area in agent_config["focus_areas"]:
            for file_path in src_path.rglob("*.py"):
                if focus_area.replace("_", "") in file_path.name.lower().replace("_", ""):
                    rel_path = str(file_path.relative_to(self.project_root))
                    if rel_path not in implementation_files:
                        implementation_files.append(rel_path)

        return implementation_files

    async def _analyze_code_structure(
        self, analysis: AgentImplementationAnalysis, files: List[str]
    ):
        """Analyze code structure and complexity for agent files."""
        total_lines = 0
        total_functions = 0
        total_classes = 0
        complexity_scores = []

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Count lines of code (excluding empty lines and comments)
                lines = [line.strip() for line in content.split("\n")]
                code_lines = [line for line in lines if line and not line.startswith("#")]
                total_lines += len(code_lines)

                # Parse AST for structure analysis
                try:
                    tree = ast.parse(content)

                    # Count functions and classes
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            total_functions += 1
                        elif isinstance(node, ast.ClassDef):
                            total_classes += 1

                    # Calculate cyclomatic complexity approximation
                    complexity = self._calculate_complexity(tree)
                    complexity_scores.append(complexity)

                except SyntaxError:
                    self.logger.warning(f"Could not parse {file_path}")

            except Exception as e:
                self.logger.warning(f"Error analyzing {file_path}: {e}")

        analysis.total_lines_of_code = total_lines
        analysis.function_count = total_functions
        analysis.class_count = total_classes
        analysis.complexity_score = (
            sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0.0
        )
        analysis.total_files = len(files)

    def _calculate_complexity(self, tree: ast.AST) -> float:
        """Calculate approximate cyclomatic complexity."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            # Add complexity for control flow statements
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += len(node.handlers)
            elif isinstance(node, (ast.BoolOp, ast.Compare)):
                complexity += 1

        return complexity

    async def _calculate_evaluation_metrics(self, analysis: AgentImplementationAnalysis):
        """Calculate comprehensive evaluation metrics for an agent."""
        metrics = analysis.metrics

        # Code Quality Metrics (30%)
        metrics.code_readability_score = await self._calculate_readability_score(analysis)
        metrics.maintainability_score = await self._calculate_maintainability_score(analysis)
        metrics.standards_compliance_score = await self._calculate_standards_compliance(analysis)
        metrics.architecture_quality_score = await self._calculate_architecture_quality(analysis)

        # Performance Metrics (25%)
        metrics.efficiency_score = await self._calculate_efficiency_score(analysis)
        metrics.scalability_score = await self._calculate_scalability_score(analysis)
        metrics.resource_optimization_score = await self._calculate_resource_optimization(analysis)
        metrics.response_time_score = await self._calculate_response_time_score(analysis)

        # Integration Metrics (20%)
        metrics.mcp_compatibility_score = await self._calculate_mcp_compatibility(analysis)
        metrics.api_design_score = await self._calculate_api_design_score(analysis)
        metrics.component_integration_score = await self._calculate_component_integration(analysis)
        metrics.interoperability_score = await self._calculate_interoperability_score(analysis)

        # Test Coverage Metrics (15%)
        metrics.unit_test_coverage = await self._calculate_test_coverage(analysis, "unit")
        metrics.integration_test_coverage = await self._calculate_test_coverage(
            analysis, "integration"
        )
        metrics.edge_case_handling = await self._calculate_edge_case_handling(analysis)
        metrics.test_quality_score = await self._calculate_test_quality(analysis)

        # Documentation Metrics (10%)
        metrics.code_documentation_score = await self._calculate_code_documentation(analysis)
        metrics.api_documentation_score = await self._calculate_api_documentation(analysis)
        metrics.usage_examples_score = await self._calculate_usage_examples(analysis)
        metrics.documentation_completeness = await self._calculate_documentation_completeness(
            analysis
        )

    async def _calculate_readability_score(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate code readability score based on various factors."""
        score = 8.0  # Base score

        # Penalize high complexity
        if analysis.complexity_score > 10:
            score -= 2.0
        elif analysis.complexity_score > 15:
            score -= 3.0

        # Reward good function/class ratio
        if analysis.total_files > 0:
            avg_functions_per_file = analysis.function_count / analysis.total_files
            if 3 <= avg_functions_per_file <= 8:
                score += 1.0

        # Check for naming conventions and docstrings
        naming_score = await self._check_naming_conventions(analysis.implementation_files)
        score += naming_score

        return min(10.0, max(0.0, score))

    async def _calculate_maintainability_score(
        self, analysis: AgentImplementationAnalysis
    ) -> float:
        """Calculate maintainability score."""
        score = 7.5  # Base score

        # Reward modular design
        if analysis.class_count > 0 and analysis.function_count > 0:
            modularity_ratio = analysis.class_count / analysis.function_count
            if 0.1 <= modularity_ratio <= 0.5:
                score += 1.5

        # Check for error handling patterns
        error_handling_score = await self._check_error_handling(analysis.implementation_files)
        score += error_handling_score

        return min(10.0, max(0.0, score))

    async def _calculate_standards_compliance(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate standards compliance score."""
        score = 8.0  # Base score

        # Check for type hints
        type_hints_score = await self._check_type_hints(analysis.implementation_files)
        score += type_hints_score

        # Check for async/await patterns
        async_patterns_score = await self._check_async_patterns(analysis.implementation_files)
        score += async_patterns_score

        return min(10.0, max(0.0, score))

    async def _calculate_architecture_quality(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate architecture quality score."""
        score = 7.0  # Base score

        # Reward separation of concerns
        if len(analysis.implementation_files) > 1:
            score += 1.0

        # Check for design patterns
        patterns_score = await self._check_design_patterns(analysis.implementation_files)
        score += patterns_score

        return min(10.0, max(0.0, score))

    async def _calculate_efficiency_score(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate efficiency score based on implementation patterns."""
        score = 7.5  # Base score

        # Check for performance patterns
        caching_score = await self._check_caching_patterns(analysis.implementation_files)
        score += caching_score

        # Check for async operations
        async_score = await self._check_async_operations(analysis.implementation_files)
        score += async_score

        return min(10.0, max(0.0, score))

    async def _calculate_scalability_score(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate scalability score."""
        score = 7.0  # Base score

        # Check for concurrent processing patterns
        concurrency_score = await self._check_concurrency_patterns(analysis.implementation_files)
        score += concurrency_score

        return min(10.0, max(0.0, score))

    async def _calculate_resource_optimization(
        self, analysis: AgentImplementationAnalysis
    ) -> float:
        """Calculate resource optimization score."""
        score = 7.5  # Base score

        # Check for resource management patterns
        resource_mgmt_score = await self._check_resource_management(analysis.implementation_files)
        score += resource_mgmt_score

        return min(10.0, max(0.0, score))

    async def _calculate_response_time_score(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate response time optimization score."""
        score = 8.0  # Base score

        # Check for optimization patterns
        optimization_score = await self._check_optimization_patterns(analysis.implementation_files)
        score += optimization_score

        return min(10.0, max(0.0, score))

    async def _calculate_mcp_compatibility(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate MCP compatibility score."""
        score = 6.0  # Base score

        # Check for MCP patterns
        mcp_patterns_score = await self._check_mcp_patterns(analysis.implementation_files)
        score += mcp_patterns_score

        return min(10.0, max(0.0, score))

    async def _calculate_api_design_score(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate API design quality score."""
        score = 7.5  # Base score

        # Check for API design patterns
        api_design_score = await self._check_api_design(analysis.implementation_files)
        score += api_design_score

        return min(10.0, max(0.0, score))

    async def _calculate_component_integration(
        self, analysis: AgentImplementationAnalysis
    ) -> float:
        """Calculate component integration score."""
        score = 7.0  # Base score

        # Check for integration patterns
        integration_score = await self._check_integration_patterns(analysis.implementation_files)
        score += integration_score

        return min(10.0, max(0.0, score))

    async def _calculate_interoperability_score(
        self, analysis: AgentImplementationAnalysis
    ) -> float:
        """Calculate interoperability score."""
        score = 7.5  # Base score

        # Check for interoperability patterns
        interop_score = await self._check_interoperability_patterns(analysis.implementation_files)
        score += interop_score

        return min(10.0, max(0.0, score))

    async def _calculate_test_coverage(
        self, analysis: AgentImplementationAnalysis, test_type: str
    ) -> float:
        """Calculate test coverage score."""
        # Find corresponding test files
        test_files = await self._find_test_files(analysis, test_type)

        if not test_files:
            return 3.0  # Low score for no tests

        # Basic coverage calculation
        coverage_ratio = len(test_files) / max(1, len(analysis.implementation_files))
        base_score = min(8.0, coverage_ratio * 10)

        # Check test quality
        test_quality_bonus = await self._check_test_quality_in_files(test_files)

        return min(10.0, base_score + test_quality_bonus)

    async def _calculate_edge_case_handling(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate edge case handling score."""
        score = 6.0  # Base score

        # Check for edge case patterns
        edge_case_score = await self._check_edge_case_patterns(analysis.implementation_files)
        score += edge_case_score

        return min(10.0, max(0.0, score))

    async def _calculate_test_quality(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate overall test quality score."""
        test_files = await self._find_test_files(analysis, "all")

        if not test_files:
            return 2.0  # Very low score for no tests

        quality_score = await self._check_test_quality_in_files(test_files)
        return min(10.0, max(0.0, 5.0 + quality_score))

    async def _calculate_code_documentation(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate code documentation score."""
        score = 5.0  # Base score

        # Check for docstrings
        docstring_score = await self._check_docstrings(analysis.implementation_files)
        score += docstring_score

        return min(10.0, max(0.0, score))

    async def _calculate_api_documentation(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate API documentation score."""
        score = 6.0  # Base score

        # Check for API documentation patterns
        api_doc_score = await self._check_api_documentation(analysis.implementation_files)
        score += api_doc_score

        return min(10.0, max(0.0, score))

    async def _calculate_usage_examples(self, analysis: AgentImplementationAnalysis) -> float:
        """Calculate usage examples score."""
        examples_path = self.project_root / "examples"
        if examples_path.exists():
            example_files = list(examples_path.glob("*.py"))
            if example_files:
                return 8.5  # Good score for having examples

        return 4.0  # Lower score for no examples

    async def _calculate_documentation_completeness(
        self, analysis: AgentImplementationAnalysis
    ) -> float:
        """Calculate documentation completeness score."""
        score = 6.0  # Base score

        # Check for README and documentation files
        docs_score = await self._check_documentation_files(analysis)
        score += docs_score

        return min(10.0, max(0.0, score))

    # Helper methods for detailed analysis

    async def _check_naming_conventions(self, files: List[str]) -> float:
        """Check naming conventions in files."""
        score = 0.0
        file_count = 0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for snake_case functions and camelCase classes
                snake_case_functions = len(re.findall(r"def [a-z_][a-z0-9_]*\(", content))
                camel_case_classes = len(re.findall(r"class [A-Z][a-zA-Z0-9]*[:\(]", content))

                if snake_case_functions > 0 or camel_case_classes > 0:
                    score += 0.5
                    file_count += 1

            except Exception:
                continue

        return score / max(1, file_count) if file_count > 0 else 0.0

    async def _check_error_handling(self, files: List[str]) -> float:
        """Check error handling patterns in files."""
        score = 0.0
        file_count = 0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for try-except blocks
                try_except_count = content.count("try:")
                logging_count = content.count("logger.") + content.count("logging.")

                if try_except_count > 0:
                    score += 0.5
                if logging_count > 0:
                    score += 0.3

                file_count += 1

            except Exception:
                continue

        return score / max(1, file_count) if file_count > 0 else 0.0

    async def _check_type_hints(self, files: List[str]) -> float:
        """Check for type hints in files."""
        score = 0.0
        file_count = 0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for type hints
                type_hints = len(re.findall(r":\s*[A-Za-z][A-Za-z0-9_\[\],\s]*\s*[=)]", content))
                return_annotations = content.count(" -> ")

                if type_hints > 0 or return_annotations > 0:
                    score += 1.0

                file_count += 1

            except Exception:
                continue

        return score / max(1, file_count) if file_count > 0 else 0.0

    async def _check_async_patterns(self, files: List[str]) -> float:
        """Check for async/await patterns."""
        score = 0.0
        file_count = 0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for async patterns
                async_functions = content.count("async def")
                await_calls = content.count("await ")

                if async_functions > 0 and await_calls > 0:
                    score += 1.0

                file_count += 1

            except Exception:
                continue

        return score / max(1, file_count) if file_count > 0 else 0.0

    async def _check_design_patterns(self, files: List[str]) -> float:
        """Check for design patterns in implementation."""
        score = 0.0
        patterns_found = set()

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for common patterns
                if "@dataclass" in content:
                    patterns_found.add("dataclass")
                if "abc.ABC" in content or "ABC" in content:
                    patterns_found.add("abstract_base_class")
                if "@contextmanager" in content or "async with" in content:
                    patterns_found.add("context_manager")
                if "Factory" in content:
                    patterns_found.add("factory")
                if "Singleton" in content:
                    patterns_found.add("singleton")

            except Exception:
                continue

        return min(2.0, len(patterns_found) * 0.5)

    async def _check_caching_patterns(self, files: List[str]) -> float:
        """Check for caching implementation patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for caching patterns
                if "cache" in content.lower() or "lru_cache" in content:
                    score += 1.0
                if "redis" in content.lower():
                    score += 0.5
                if "ttl" in content.lower():
                    score += 0.3

            except Exception:
                continue

        return min(2.0, score)

    async def _check_async_operations(self, files: List[str]) -> float:
        """Check for proper async operations."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for async operations
                if "asyncio.gather" in content:
                    score += 1.0
                if "async with" in content:
                    score += 0.5
                if "ThreadPoolExecutor" in content:
                    score += 0.5

            except Exception:
                continue

        return min(2.0, score)

    async def _check_concurrency_patterns(self, files: List[str]) -> float:
        """Check for concurrency patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for concurrency patterns
                if "concurrent.futures" in content:
                    score += 1.0
                if "asyncio.Semaphore" in content:
                    score += 0.5
                if "Queue" in content:
                    score += 0.3

            except Exception:
                continue

        return min(2.0, score)

    async def _check_resource_management(self, files: List[str]) -> float:
        """Check for resource management patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for resource management
                if "with " in content:
                    score += 0.5
                if "finally:" in content:
                    score += 0.3
                if ".close()" in content:
                    score += 0.2

            except Exception:
                continue

        return min(1.5, score)

    async def _check_optimization_patterns(self, files: List[str]) -> float:
        """Check for optimization patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for optimization patterns
                if "batch" in content.lower():
                    score += 0.5
                if "pool" in content.lower():
                    score += 0.3
                if "lazy" in content.lower():
                    score += 0.2

            except Exception:
                continue

        return min(1.5, score)

    async def _check_mcp_patterns(self, files: List[str]) -> float:
        """Check for MCP-specific patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for MCP patterns
                if "@server.tool" in content:
                    score += 2.0
                if "mcp" in content.lower():
                    score += 1.0
                if "ToolError" in content:
                    score += 0.5

            except Exception:
                continue

        return min(3.0, score)

    async def _check_api_design(self, files: List[str]) -> float:
        """Check API design quality."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for good API design
                if "def " in content and ":" in content:
                    score += 0.5
                if "class " in content:
                    score += 0.3
                if "return " in content:
                    score += 0.2

            except Exception:
                continue

        return min(2.0, score)

    async def _check_integration_patterns(self, files: List[str]) -> float:
        """Check for integration patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for integration patterns
                if "import" in content:
                    score += 0.5
                if "from " in content:
                    score += 0.3

            except Exception:
                continue

        return min(2.0, score)

    async def _check_interoperability_patterns(self, files: List[str]) -> float:
        """Check for interoperability patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for interoperability
                if "boto3" in content:
                    score += 1.0
                if "json" in content:
                    score += 0.3
                if "dict" in content or "Dict" in content:
                    score += 0.2

            except Exception:
                continue

        return min(2.0, score)

    async def _find_test_files(
        self, analysis: AgentImplementationAnalysis, test_type: str
    ) -> List[str]:
        """Find test files related to an agent."""
        test_files = []
        tests_path = self.project_root / "tests"

        if not tests_path.exists():
            return test_files

        # Search for test files
        search_patterns = []
        for impl_file in analysis.implementation_files:
            file_name = Path(impl_file).stem
            search_patterns.extend(
                [
                    f"test_{file_name}.py",
                    f"test_*{file_name}*.py",
                    f"{file_name}_test.py",
                ]
            )

        for pattern in search_patterns:
            for test_file in tests_path.rglob(pattern):
                if test_type == "all" or test_type in str(test_file):
                    test_files.append(str(test_file.relative_to(self.project_root)))

        return test_files

    async def _check_test_quality_in_files(self, test_files: List[str]) -> float:
        """Check quality of test files."""
        score = 0.0
        file_count = 0

        for file_path in test_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check test quality indicators
                if "def test_" in content:
                    score += 1.0
                if "assert" in content:
                    score += 0.5
                if "mock" in content.lower():
                    score += 0.3
                if "pytest" in content:
                    score += 0.2

                file_count += 1

            except Exception:
                continue

        return score / max(1, file_count) if file_count > 0 else 0.0

    async def _check_edge_case_patterns(self, files: List[str]) -> float:
        """Check for edge case handling patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for edge case handling
                if "if not " in content:
                    score += 0.5
                if "except " in content:
                    score += 0.5
                if "raise " in content:
                    score += 0.3
                if "None" in content:
                    score += 0.2

            except Exception:
                continue

        return min(2.0, score)

    async def _check_docstrings(self, files: List[str]) -> float:
        """Check for docstrings in files."""
        score = 0.0
        file_count = 0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for docstrings
                triple_quotes = content.count('"""') + content.count("'''")
                if triple_quotes >= 2:  # At least one docstring
                    score += 2.0
                elif triple_quotes > 0:
                    score += 1.0

                file_count += 1

            except Exception:
                continue

        return score / max(1, file_count) if file_count > 0 else 0.0

    async def _check_api_documentation(self, files: List[str]) -> float:
        """Check for API documentation patterns."""
        score = 0.0

        for file_path in files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for API documentation
                if "Args:" in content or "Returns:" in content:
                    score += 1.5
                if "Parameters:" in content:
                    score += 1.0
                if "Example:" in content:
                    score += 0.5

            except Exception:
                continue

        return min(3.0, score)

    async def _check_documentation_files(self, analysis: AgentImplementationAnalysis) -> float:
        """Check for documentation files."""
        score = 0.0

        # Check for README files
        readme_files = list(self.project_root.glob("README*"))
        if readme_files:
            score += 1.0

        # Check for docs directory
        docs_path = self.project_root / "docs"
        if docs_path.exists() and any(docs_path.iterdir()):
            score += 1.5

        # Check for CHANGELOG
        changelog_files = list(self.project_root.glob("CHANGELOG*"))
        if changelog_files:
            score += 0.5

        return min(3.0, score)

    async def _calculate_bleu_scores(self, analysis: AgentImplementationAnalysis):
        """Calculate BLEU scores for agent implementation."""
        # This is a simplified BLEU calculation for code analysis
        # In practice, you might want to compare against reference implementations

        bleu_scores = {}

        # Code quality BLEU (compare structure and patterns)
        bleu_scores["code_quality"] = min(10.0, analysis.metrics.category_scores["code_quality"])

        # Performance BLEU (compare optimization patterns)
        bleu_scores["performance"] = min(10.0, analysis.metrics.category_scores["performance"])

        # Integration BLEU (compare integration patterns)
        bleu_scores["integration"] = min(10.0, analysis.metrics.category_scores["integration"])

        # Test coverage BLEU
        bleu_scores["test_coverage"] = min(10.0, analysis.metrics.category_scores["test_coverage"])

        # Documentation BLEU
        bleu_scores["documentation"] = min(10.0, analysis.metrics.category_scores["documentation"])

        # Overall BLEU score
        bleu_scores["overall"] = analysis.metrics.weighted_score

        analysis.bleu_scores = bleu_scores

    async def _identify_strengths_weaknesses(self, analysis: AgentImplementationAnalysis):
        """Identify strengths and weaknesses for an agent."""
        metrics = analysis.metrics

        # Identify strengths
        strengths = []
        if metrics.category_scores["code_quality"] >= 8.0:
            strengths.append("Excellent code quality and maintainability")
        if metrics.category_scores["performance"] >= 8.0:
            strengths.append("Strong performance optimization implementation")
        if metrics.category_scores["integration"] >= 8.0:
            strengths.append("Excellent integration and interoperability")
        if metrics.category_scores["test_coverage"] >= 7.0:
            strengths.append("Good test coverage and quality")
        if metrics.category_scores["documentation"] >= 7.0:
            strengths.append("Well-documented codebase")

        if analysis.complexity_score < 8.0:
            strengths.append("Low complexity, easy to understand")
        if analysis.function_count > 20:
            strengths.append("Comprehensive functionality implementation")

        # Identify weaknesses
        weaknesses = []
        if metrics.category_scores["code_quality"] < 6.0:
            weaknesses.append("Code quality needs improvement")
        if metrics.category_scores["performance"] < 6.0:
            weaknesses.append("Performance optimization opportunities")
        if metrics.category_scores["integration"] < 6.0:
            weaknesses.append("Integration patterns could be enhanced")
        if metrics.category_scores["test_coverage"] < 5.0:
            weaknesses.append("Insufficient test coverage")
        if metrics.category_scores["documentation"] < 5.0:
            weaknesses.append("Documentation needs significant improvement")

        if analysis.complexity_score > 15.0:
            weaknesses.append("High complexity may impact maintainability")

        # Generate recommendations
        recommendations = []
        if metrics.category_scores["test_coverage"] < 7.0:
            recommendations.append("Increase test coverage with unit and integration tests")
        if metrics.category_scores["documentation"] < 7.0:
            recommendations.append("Add comprehensive documentation and API docs")
        if metrics.category_scores["performance"] < 7.0:
            recommendations.append("Implement caching and async optimization patterns")
        if analysis.complexity_score > 10.0:
            recommendations.append("Refactor complex functions to improve maintainability")

        analysis.strengths = strengths
        analysis.weaknesses = weaknesses
        analysis.recommendations = recommendations

    async def _generate_consensus(
        self, agent_analyses: List[AgentImplementationAnalysis]
    ) -> ConsensusResults:
        """Generate final consensus results from all agent analyses."""

        # Create rankings based on weighted scores
        rankings = [
            (analysis.agent_name, analysis.metrics.weighted_score) for analysis in agent_analyses
        ]
        rankings.sort(key=lambda x: x[1], reverse=True)

        # Identify best practices from top-performing agents
        best_practices = defaultdict(list)
        for analysis in agent_analyses:
            if analysis.metrics.weighted_score >= 8.0:
                for strength in analysis.strengths:
                    best_practices[analysis.agent_name].append(strength)

        # Identify optimal solutions for different categories
        optimal_solutions = {}
        categories = [
            "code_quality",
            "performance",
            "integration",
            "test_coverage",
            "documentation",
        ]

        for category in categories:
            best_agent = max(agent_analyses, key=lambda a: a.metrics.category_scores[category])
            optimal_solutions[category] = best_agent.agent_name

        # Generate integration plan
        integration_plan = [
            f"Integrate {optimal_solutions['code_quality']} architecture patterns for code quality",
            f"Adopt {optimal_solutions['performance']} optimization strategies",
            f"Use {optimal_solutions['integration']} integration patterns for MCP compatibility",
            f"Follow {optimal_solutions['test_coverage']} testing methodologies",
            f"Implement {optimal_solutions['documentation']} documentation standards",
        ]

        # Identify performance leaders
        performance_leaders = {
            "efficiency": max(agent_analyses, key=lambda a: a.metrics.efficiency_score).agent_name,
            "scalability": max(
                agent_analyses, key=lambda a: a.metrics.scalability_score
            ).agent_name,
            "resource_optimization": max(
                agent_analyses, key=lambda a: a.metrics.resource_optimization_score
            ).agent_name,
        }

        # Generate optimization opportunities
        optimization_opportunities = []
        avg_scores = defaultdict(list)
        for analysis in agent_analyses:
            for category, score in analysis.metrics.category_scores.items():
                avg_scores[category].append(score)

        for category, scores in avg_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score < 7.0:
                optimization_opportunities.append(
                    f"Improve {category} across all agents (current avg: {avg_score:.1f})"
                )

        # Calculate consensus metrics
        all_scores = [analysis.metrics.weighted_score for analysis in agent_analyses]
        consensus_score = sum(all_scores) / len(all_scores)

        # Calculate consensus confidence (based on score variance)
        score_variance = sum((score - consensus_score) ** 2 for score in all_scores) / len(
            all_scores
        )
        consensus_confidence = max(0.0, min(1.0, 1.0 - (score_variance / 10.0)))

        return ConsensusResults(
            agent_analyses=agent_analyses,
            rankings=rankings,
            best_practices=dict(best_practices),
            optimal_solutions=optimal_solutions,
            integration_plan=integration_plan,
            performance_leaders=performance_leaders,
            optimization_opportunities=optimization_opportunities,
            consensus_score=consensus_score,
            consensus_confidence=consensus_confidence,
        )


# Helper function for easy usage
async def run_bleu_consensus_analysis(project_root: str) -> ConsensusResults:
    """Run the complete BLEU consensus analysis."""
    framework = BLEUConsensusFramework(project_root)
    results = await framework.analyze_all_agents()
    return results
