"""DSPy-powered evaluation engine for DynamoDB data modeling guidance assessment.

This module implements a sophisticated evaluation system using DSPy to provide consistent, structured assessment of DynamoDB modeling guidance quality.
The system combines expert knowledge with LLM-based evaluation to score both technical design
quality and modeling process rigor.

Architecture Overview:
    The evaluation engine uses DSPy signatures to define structured evaluation interfaces,
    ensuring consistent scoring across different LLM backends. Two complementary evaluation
    pathways assess different aspects of DynamoDB modeling excellence:

    1. **Guidance Evaluation**: Assesses final technical design quality
       - Uses DynamoDBGuidanceEvaluator signature
       - Scores completeness, technical accuracy, access patterns, scalability, cost
       - Focuses on WHAT was delivered

    2. **Session Evaluation**: Assesses modeling process quality
       - Uses DynamoDBSessionEvaluator signature
       - Scores requirements engineering, methodology, reasoning, documentation
       - Focuses on HOW the design was derived

DSPy Integration Benefits:
    - Consistent evaluation across different LLM backends
    - Structured input/output with automatic validation
    - Chain-of-thought reasoning for transparent scoring
    - Expert knowledge injection for domain-specific assessment
"""

import dspy
from dataclasses import dataclass
from evaluation_config import EvaluationConfig, EvaluationDimension, SessionDimension
from pathlib import Path
from typing import Any, Dict, Optional


class ScoreDescriptions:
    """Embedded scoring rubrics for DSPy evaluator prompts.

    This class contains detailed scoring criteria that are injected directly into
    DSPy signature prompts to guide LLM evaluation behavior. Each description
    provides specific, measurable criteria for different score levels, ensuring
    consistent evaluation across different models and evaluation sessions.
    """

    COMPLETENESS = (
        'Score 1-10: Evaluate if guidance addresses ALL scenario elements: '
        '(1) All entities identified and defined, '
        '(2) All entity relationships mapped, '
        '(3) All access patterns identified (not optimized), '
        '(4) Performance requirements and constraints covered, '
        '(5) Scale requirements and constraints covered. '
        'Score 9-10: Comprehensive coverage of all elements. '
        'Score 7-8: Most elements covered with minor gaps. '
        'Score 5-6: Core elements but missing important details. '
        'Score 3-4: Significant gaps in key elements. '
        'Score 1-2: Major elements missing. '
        'Return single number 1-10, not 8/10'
    )

    TECHNICAL_ACCURACY = (
        'Score 1-10: Evaluate technical correctness of DynamoDB recommendations: '
        '(1) Primary key design follows best practices, '
        '(2) GSI design is appropriate and efficient including the use of projections where relevant, '
        '(3) Data types and attribute choices are optimal (TTL as number, etc.), '
        '(4) Sort key design enables required access patterns, '
        '(5) Recommendations follow DynamoDB best practices. '
        'Score 9-10: All recommendations technically sound with deep expertise. '
        'Score 7-8: Mostly accurate with only minor technical issues. '
        'Score 5-6: Generally accurate but some questionable recommendations. '
        'Score 3-4: Several technical errors or best practice violations. '
        'Score 1-2: Major technical errors, fundamental DynamoDB misunderstandings. '
        'Return single number 1-10.'
    )

    ACCESS_PATTERN_COVERAGE = (
        'Score 1-10: Evaluate how well access patterns are optimized: '
        '(1) Query patterns mapped to optimal table/GSI design, '
        '(2) Solutions optimize for most frequent/critical patterns, '
        '(3) Edge cases and less frequent patterns considered, '
        '(4) Performance implications of each pattern addressed, '
        '(5) Efficient query strategies recommended. '
        'Score 9-10: Identifies and addresses all critical patterns with optimized solutions. '
        'Score 7-8: Covers most important patterns with effective solutions. '
        'Score 5-6: Addresses core patterns but misses some important ones. '
        'Score 3-4: Limited coverage, solutions may be inefficient. '
        'Score 1-2: Poor understanding of patterns, inadequate solutions. '
        'Return single number 1-10.'
    )

    SCALABILITY_CONSIDERATIONS = (
        'Score 1-10: Evaluate scalability and performance planning: '
        '(1) Hot partition prevention strategies, '
        '(2) Capacity planning for expected growth, '
        '(3) Performance bottleneck identification, '
        '(4) Auto-scaling considerations, '
        '(5) Future growth accommodation in design. '
        'Score 9-10: Comprehensive scalability analysis with proactive solutions for bottlenecks. '
        'Score 7-8: Good scalability awareness with most key considerations addressed. '
        'Score 5-6: Basic scalability considerations with some important aspects covered. '
        'Score 3-4: Limited scalability planning, may have scaling issues. '
        'Score 1-2: No meaningful scalability considerations, designs likely to fail at scale. '
        'Return single number 1-10.'
    )

    COST_OPTIMIZATION = (
        'Score 1-10: Evaluate cost optimization strategies: '
        '(1) On-demand vs provisioned billing analysis, '
        '(2) GSI cost implications considered, '
        '(3) Storage cost optimization strategies, '
        '(4) Read/write cost efficiency recommendations, '
        '(5) Multiple cost-saving techniques suggested. '
        'Score 9-10: Sophisticated cost optimization with multiple strategies. '
        'Score 7-8: Good cost awareness with several optimization techniques. '
        'Score 5-6: Basic cost considerations with some optimization suggestions. '
        'Score 3-4: Limited cost analysis, may lead to unnecessary expenses. '
        'Score 1-2: No cost optimization, designs likely to be expensive. '
        'Return single number 1-10.'
    )


class DynamoDBGuidanceEvaluator(dspy.Signature):
    """DSPy signature for evaluating DynamoDB data model guidance technical quality.

    This signature defines the structured evaluation interface for assessing the
    technical quality of final DynamoDB schema designs and recommendations.
    It focuses on the WHAT (final deliverable quality) rather than the HOW
    (process quality), which is handled by DynamoDBSessionEvaluator.
    """

    # Input context fields - provide complete evaluation context
    scenario_requirements = dspy.InputField(
        desc='Complete scenario requirements including entities, access patterns, scale, and performance needs'
    )
    guidance_response = dspy.InputField(
        desc='The AI-generated DynamoDB guidance response to evaluate'
    )
    dynamodb_expert_knowledge = dspy.InputField(
        desc='Comprehensive DynamoDB expert guidance including best practices, design patterns, technical constraints, and cost optimization strategies to inform evaluation scoring'
    )

    # Core evaluation dimension scores (1-10 scale)
    # Each uses detailed scoring rubric from ScoreDescriptions
    completeness_score = dspy.OutputField(desc=ScoreDescriptions.COMPLETENESS)

    technical_accuracy_score = dspy.OutputField(desc=ScoreDescriptions.TECHNICAL_ACCURACY)

    access_pattern_coverage_score = dspy.OutputField(
        desc=ScoreDescriptions.ACCESS_PATTERN_COVERAGE
    )

    scalability_considerations_score = dspy.OutputField(
        desc=ScoreDescriptions.SCALABILITY_CONSIDERATIONS
    )

    cost_optimization_score = dspy.OutputField(desc=ScoreDescriptions.COST_OPTIMIZATION)

    # Detailed explanations for key scoring dimensions
    # These provide transparency and actionable feedback
    completeness_justification = dspy.OutputField(
        desc='Detailed explanation of completeness score, highlighting what was covered well and what was missed'
    )

    technical_justification = dspy.OutputField(
        desc='Detailed explanation of technical accuracy, noting correct and incorrect recommendations'
    )

    access_pattern_coverage_justification = dspy.OutputField(
        desc='Detailed explanation of access pattern coverage score, analyzing how well patterns were identified, prioritized, and optimized in the design'
    )

    scalability_considerations_justification = dspy.OutputField(
        desc='Detailed explanation of scalability considerations score, evaluating hot partition prevention, capacity planning, and performance bottleneck analysis'
    )

    cost_optimization_justification = dspy.OutputField(
        desc='Detailed explanation of cost optimization score, assessing billing mode choices, GSI costs, storage optimization, and overall cost efficiency strategies'
    )

    # Structured overall assessment broken into actionable categories
    strengths = dspy.OutputField(
        desc='Key strengths of the DynamoDB guidance, highlighting what was done exceptionally well in the design and recommendations'
    )

    weaknesses = dspy.OutputField(
        desc='Main weaknesses and areas where the DynamoDB guidance fell short or could be significantly improved'
    )

    improvement_recommendations = dspy.OutputField(
        desc='Specific, actionable recommendations for improving the DynamoDB guidance, with concrete suggestions for addressing identified weaknesses'
    )


class DynamoDBSessionEvaluator(dspy.Signature):
    """DSPy signature for evaluating DynamoDB modeling session process quality.

    This signature defines the evaluation interface for assessing the quality of
    the DynamoDB modeling process itself, focusing on methodology, requirements
    engineering, and systematic analysis approach. It complements the
    DynamoDBGuidanceEvaluator by focusing on HOW the design was derived rather
    than WHAT the final design contains.
    """

    # Input context fields - provide complete process evaluation context
    scenario_requirements = dspy.InputField(
        desc='Original business requirements and constraints provided by user'
    )
    modeling_session_content = dspy.InputField(
        desc='Complete modeling session output including analysis, methodology, and validation'
    )
    architect_methodology = dspy.InputField(
        desc='DynamoDB architect prompt methodology and best practices for reference'
    )

    # Session-specific evaluation scores (1-10 scale)
    # These focus on process quality rather than design quality
    requirements_engineering_score = dspy.OutputField(
        desc='Score 1-10: Quality of requirements capture, entity modeling, and scope definition. Are business context, scale, and constraints properly documented? Should be just a number between 1-10'
    )

    access_pattern_analysis_score = dspy.OutputField(
        desc='Score 1-10: Rigor of access pattern analysis including completeness, RPS estimates, performance requirements, and prioritization. Should be just a number between 1-10'
    )

    methodology_adherence_score = dspy.OutputField(
        desc='Score 1-10: How well does the session follow the systematic methodology from the architect prompt? Are decision frameworks properly applied? Should be just a number between 1-10'
    )

    technical_reasoning_score = dspy.OutputField(
        desc='Score 1-10: Quality of design justifications, trade-off analysis, risk assessment, and optimization considerations. Should be just a number between 1-10'
    )

    process_documentation_score = dspy.OutputField(
        desc='Score 1-10: Organization, transparency, traceability, and professional quality of process documentation. Should be just a number between 1-10'
    )

    # Detailed qualitative analysis sections
    # These provide actionable feedback for process improvement
    requirements_analysis = dspy.OutputField(
        desc='Detailed assessment of requirements engineering quality, highlighting strengths and gaps'
    )

    access_pattern_analysis_justification = dspy.OutputField(
        desc='Detailed explanation of access pattern analysis score, evaluating the rigor and completeness of pattern identification, RPS estimates, and prioritization methodology'
    )

    methodology_assessment = dspy.OutputField(
        desc='Evaluation of how well the structured methodology was followed, including decision framework usage'
    )

    technical_depth_evaluation = dspy.OutputField(
        desc='Analysis of technical reasoning quality, design justifications, and proactive risk identification'
    )

    process_documentation_justification = dspy.OutputField(
        desc='Detailed explanation of process documentation score, assessing organization, clarity, traceability, and professional quality of the modeling session documentation'
    )

    # Structured session assessment broken into actionable categories
    session_strengths = dspy.OutputField(
        desc='Key strengths of the modeling session process, highlighting what was done exceptionally well in methodology and analysis'
    )

    session_weaknesses = dspy.OutputField(
        desc='Main weaknesses and areas where the modeling session process fell short or could be significantly improved'
    )

    session_improvement_recommendations = dspy.OutputField(
        desc='Specific, actionable recommendations for improving the modeling session process, with concrete suggestions for addressing identified process weaknesses'
    )


@dataclass
class EvaluationResult:
    """Container for DynamoDB data model evaluation results.

    Holds the complete evaluation outcome for technical design quality assessment,
    including individual dimension scores, qualitative justifications, and overall
    quality assessment. This structure enables comprehensive analysis and reporting
    of data model guidance quality.
    """

    completeness: float  # 1-10 requirement coverage score
    technical_accuracy: float  # 1-10 DynamoDB correctness score
    access_pattern_coverage: float  # 1-10 access pattern optimization score
    scalability_considerations: float  # 1-10 scalability planning score
    cost_optimization: float  # 1-10 cost efficiency score

    justifications: Dict[str, str]  # Detailed explanations for key dimensions

    overall_score: float  # Weighted average of all dimensions
    quality_level: str  # Categorical quality assessment


@dataclass
class SessionEvaluationResult:
    """Container for DynamoDB modeling session evaluation results.

    Holds the complete evaluation outcome for modeling process quality assessment,
    including individual process dimension scores, qualitative analysis, and overall
    session quality rating. This structure enables assessment of HOW the modeling
    was conducted rather than WHAT was delivered.
    """

    requirements_engineering: float  # 1-10 requirements capture score
    access_pattern_analysis: float  # 1-10 pattern analysis rigor score
    methodology_adherence: float  # 1-10 systematic methodology score
    technical_reasoning: float  # 1-10 design justification score
    process_documentation: float  # 1-10 documentation quality score
    justifications: Dict[str, str]  # Detailed process quality analysis
    overall_score: float  # Weighted average of all process dimensions
    quality_level: str  # Categorical process quality assessment


class DSPyEvaluationEngine:
    """Main orchestration engine for DynamoDB guidance evaluation using DSPy.

    This class coordinates the complete evaluation workflow, managing both technical
    design quality assessment and modeling process evaluation. It handles expert
    knowledge loading, DSPy evaluator orchestration, result aggregation, and
    provides a clean interface for comprehensive DynamoDB guidance assessment.
    """

    def __init__(self, architect_prompt_path: Optional[str] = None):
        """Initialize DSPy evaluation engine with expert knowledge configuration.

        Sets up DSPy evaluators with chain-of-thought reasoning and configures
        expert knowledge loading with automatic fallback path detection.

        Args:
            architect_prompt_path: Custom path to DynamoDB architect prompt file.
                                 If None, uses default path relative to current directory.
                                 Falls back to relative path if primary path fails.
        """
        # Initialize DSPy evaluators with chain-of-thought reasoning
        # This enables transparent, step-by-step evaluation logic
        self.guidance_evaluator = dspy.ChainOfThought(DynamoDBGuidanceEvaluator)
        self.session_evaluator = dspy.ChainOfThought(DynamoDBSessionEvaluator)

        # Configure expert knowledge path with fallback to relative location
        # Primary path assumes current working directory structure
        if architect_prompt_path is None:
            architect_prompt_path = (
                'src/dynamodb-mcp-server/awslabs/dynamodb_mcp_server/prompts/dynamodb_architect.md'
            )

        self.architect_prompt_path = architect_prompt_path

        # Initialize expert knowledge cache (loaded lazily on first evaluation)
        # This prevents unnecessary file I/O during initialization
        self._expert_knowledge_cache = None

    def _load_expert_knowledge(self) -> str:
        if self._expert_knowledge_cache is None:
            try:
                prompt_path = Path(self.architect_prompt_path)

                if not prompt_path.exists():
                    current_dir = Path(__file__).parent
                    fallback_path = (
                        current_dir
                        / '..'
                        / '..'
                        / 'awslabs'
                        / 'dynamodb_mcp_server'
                        / 'prompts'
                        / 'dynamodb_architect.md'
                    )
                    if fallback_path.exists():
                        prompt_path = fallback_path
                    else:
                        raise FileNotFoundError(
                            f'DynamoDB architect prompt not found at {self.architect_prompt_path} or fallback location'
                        )

                with open(prompt_path, 'r', encoding='utf-8') as file:
                    self._expert_knowledge_cache = file.read()

            except Exception as e:
                fallback_msg = f'Error loading DynamoDB expert knowledge: {str(e)}. Using minimal context for evaluation.'
                print(f'Warning: {fallback_msg}')
                self._expert_knowledge_cache = fallback_msg

        return self._expert_knowledge_cache

    def evaluate_guidance(self, scenario: Dict[str, Any], response: str) -> EvaluationResult:
        """Evaluate guidance response against scenario requirements."""
        expert_knowledge = self._load_expert_knowledge()

        guidance_result = self.guidance_evaluator(
            scenario_requirements=self._build_scenario_summary(scenario),
            guidance_response=response,
            dynamodb_expert_knowledge=expert_knowledge,
        )

        return self._aggregate_evaluation_results(guidance_result)

    def evaluate_session(
        self, scenario: Dict[str, Any], session_content: str
    ) -> SessionEvaluationResult:
        """Evaluate session content against scenario requirements."""
        expert_knowledge = self._load_expert_knowledge()

        # Run session evaluation with expert context
        session_result = self.session_evaluator(
            scenario_requirements=self._build_scenario_summary(scenario),
            modeling_session_content=session_content,
            architect_methodology=expert_knowledge,
        )

        # Aggregate session results
        return self._aggregate_session_evaluation_results(session_result)

    def _build_scenario_summary(self, scenario: Dict[str, Any]) -> str:
        """Build comprehensive scenario summary for evaluation."""
        parts = [
            f'Scenario: {scenario.get("name", "Unknown")}',
            f'Complexity: {scenario.get("complexity", "beginner")}',
            f'Description: {scenario.get("description", "")}',
        ]

        if 'entities_and_relationships' in scenario:
            parts.append(f'Entities: {scenario["entities_and_relationships"]}')

        if 'access_patterns' in scenario:
            parts.append(f'Access Patterns: {scenario["access_patterns"]}')

        if 'performance_and_scale' in scenario:
            parts.append(f'Scale Requirements: {scenario["performance_and_scale"]}')

        return '\n'.join(parts)

    def _aggregate_evaluation_results(self, guidance_result) -> EvaluationResult:
        def safe_float(value, default=0.0):
            try:
                return float(str(value).split()[0]) if value else default
            except (ValueError, IndexError):
                return default

        scores = {
            EvaluationDimension.COMPLETENESS: safe_float(guidance_result.completeness_score),
            EvaluationDimension.TECHNICAL_ACCURACY: safe_float(
                guidance_result.technical_accuracy_score
            ),
            EvaluationDimension.ACCESS_PATTERN_COVERAGE: safe_float(
                guidance_result.access_pattern_coverage_score
            ),
            EvaluationDimension.SCALABILITY_CONSIDERATIONS: safe_float(
                guidance_result.scalability_considerations_score
            ),
            EvaluationDimension.COST_OPTIMIZATION: safe_float(
                guidance_result.cost_optimization_score
            ),
        }

        overall_score = EvaluationConfig.calculate_datamodel_eval_score(scores)
        quality_level = EvaluationConfig.get_quality_level(overall_score)

        return EvaluationResult(
            completeness=scores[EvaluationDimension.COMPLETENESS],
            technical_accuracy=scores[EvaluationDimension.TECHNICAL_ACCURACY],
            access_pattern_coverage=scores[EvaluationDimension.ACCESS_PATTERN_COVERAGE],
            scalability_considerations=scores[EvaluationDimension.SCALABILITY_CONSIDERATIONS],
            cost_optimization=scores[EvaluationDimension.COST_OPTIMIZATION],
            justifications={
                'completeness': str(guidance_result.completeness_justification),
                'technical': str(guidance_result.technical_justification),
                'access_pattern_coverage': str(
                    guidance_result.access_pattern_coverage_justification
                ),
                'scalability_considerations': str(
                    guidance_result.scalability_considerations_justification
                ),
                'cost_optimization': str(guidance_result.cost_optimization_justification),
                'strengths': str(guidance_result.strengths),
                'weaknesses': str(guidance_result.weaknesses),
                'improvement_recommendations': str(guidance_result.improvement_recommendations),
            },
            overall_score=overall_score,
            quality_level=quality_level,
        )

    def _aggregate_session_evaluation_results(self, session_result) -> SessionEvaluationResult:
        def safe_float(value, default=0.0):
            try:
                return float(str(value).split()[0]) if value else default
            except (ValueError, IndexError):
                return default

        scores = {
            SessionDimension.REQUIREMENTS_ENGINEERING: safe_float(
                session_result.requirements_engineering_score
            ),
            SessionDimension.ACCESS_PATTERN_ANALYSIS: safe_float(
                session_result.access_pattern_analysis_score
            ),
            SessionDimension.METHODOLOGY_ADHERENCE: safe_float(
                session_result.methodology_adherence_score
            ),
            SessionDimension.TECHNICAL_REASONING: safe_float(
                session_result.technical_reasoning_score
            ),
            SessionDimension.PROCESS_DOCUMENTATION: safe_float(
                session_result.process_documentation_score
            ),
        }

        overall_score = EvaluationConfig.calculate_session_eval_score(scores)
        quality_level = EvaluationConfig.get_quality_level(overall_score)

        return SessionEvaluationResult(
            requirements_engineering=scores[SessionDimension.REQUIREMENTS_ENGINEERING],
            access_pattern_analysis=scores[SessionDimension.ACCESS_PATTERN_ANALYSIS],
            methodology_adherence=scores[SessionDimension.METHODOLOGY_ADHERENCE],
            technical_reasoning=scores[SessionDimension.TECHNICAL_REASONING],
            process_documentation=scores[SessionDimension.PROCESS_DOCUMENTATION],
            justifications={
                'requirements': str(session_result.requirements_analysis),
                'access_pattern_analysis': str(
                    session_result.access_pattern_analysis_justification
                ),
                'methodology': str(session_result.methodology_assessment),
                'technical_depth': str(session_result.technical_depth_evaluation),
                'process_documentation': str(session_result.process_documentation_justification),
                'session_strengths': str(session_result.session_strengths),
                'session_weaknesses': str(session_result.session_weaknesses),
                'session_improvement_recommendations': str(
                    session_result.session_improvement_recommendations
                ),
            },
            overall_score=overall_score,
            quality_level=quality_level,
        )


__all__ = [
    'DynamoDBGuidanceEvaluator',
    'DynamoDBSessionEvaluator',
    'DSPyEvaluationEngine',
    'EvaluationResult',
    'SessionEvaluationResult',
]
