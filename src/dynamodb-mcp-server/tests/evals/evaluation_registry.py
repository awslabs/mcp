"""Dynamic evaluation registry for DynamoDB evaluation dimensions and types."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DimensionConfig:
    """Configuration for a single evaluation dimension."""

    name: str
    display_name: str
    description: str
    scoring_rubric: str
    weight: float = 1.0
    justification_prompt: Optional[str] = None


@dataclass
class EvaluationConfig:
    """Configuration for a complete evaluation type."""

    name: str
    display_name: str
    description: str
    dimensions: List[DimensionConfig]
    input_fields: Dict[str, str] = None


class EvaluationRegistry:
    """Central registry for evaluation configurations."""

    def __init__(self):
        """Initialize the evaluation registry and set up default evaluations."""
        self._evaluations: Dict[str, EvaluationConfig] = {}
        self._setup_default_evaluations()

    def _setup_default_evaluations(self):
        """Setup the default DynamoDB evaluations to maintain backward compatibility."""
        # Data Model Evaluation dimensions
        model_dimensions = [
            DimensionConfig(
                name='completeness',
                display_name='Completeness',
                description='Coverage of all scenario requirements',
                scoring_rubric=(
                    'Score 1-10: Evaluate if guidance addresses ALL scenario elements: '
                    '(1) All entities identified and defined, '
                    '(2) All entity relationships mapped, '
                    '(3) All access patterns identified, '
                    '(4) Performance requirements covered, '
                    '(5) Scale requirements covered. '
                    'Score 9-10: Comprehensive coverage. Score 7-8: Most elements with minor gaps. '
                    'Score 5-6: Core elements but missing details. Score 3-4: Significant gaps. '
                    'Score 1-2: Major elements missing. Return single number 1-10.'
                ),
                justification_prompt='Explain completeness score, highlighting what was covered well and what was missed',
            ),
            DimensionConfig(
                name='technical_accuracy',
                display_name='Technical Accuracy',
                description='Correctness of DynamoDB recommendations',
                scoring_rubric=(
                    'Score 1-10: Evaluate technical correctness: '
                    '(1) Primary key design best practices, '
                    '(2) GSI design efficiency and projections, '
                    '(3) Data types and attributes optimal, '
                    '(4) Sort key enables access patterns, '
                    '(5) Follows DynamoDB best practices. '
                    'Score 9-10: Technically sound with expertise. Score 7-8: Mostly accurate, minor issues. '
                    'Score 5-6: Generally accurate, some questionable recommendations. '
                    'Score 3-4: Several errors or violations. Score 1-2: Major errors, misunderstandings. '
                    'Return single number 1-10.'
                ),
                justification_prompt='Explain technical accuracy, noting correct and incorrect recommendations',
            ),
            DimensionConfig(
                name='access_pattern_coverage',
                display_name='Access Pattern Coverage',
                description='Optimization for query patterns',
                scoring_rubric=(
                    'Score 1-10: Evaluate access pattern optimization: '
                    '(1) Patterns mapped to optimal design, '
                    '(2) Optimizes for frequent/critical patterns, '
                    '(3) Edge cases considered, '
                    '(4) Performance implications addressed, '
                    '(5) Efficient strategies recommended. '
                    'Score 9-10: All critical patterns optimized. Score 7-8: Most important patterns effective. '
                    'Score 5-6: Core patterns, misses some important ones. Score 3-4: Limited coverage, inefficient. '
                    'Score 1-2: Poor understanding, inadequate solutions. Return single number 1-10.'
                ),
                justification_prompt='Explain access pattern coverage, analyzing pattern identification and optimization',
            ),
            DimensionConfig(
                name='scalability_considerations',
                display_name='Scalability Considerations',
                description='Performance and scale planning',
                scoring_rubric=(
                    'Score 1-10: Evaluate scalability planning: '
                    '(1) Hot partition prevention, '
                    '(2) Capacity planning for growth, '
                    '(3) Performance bottleneck identification, '
                    '(4) Auto-scaling considerations, '
                    '(5) Future growth accommodation. '
                    'Score 9-10: Comprehensive scalability with proactive solutions. '
                    'Score 7-8: Good awareness, most considerations addressed. '
                    'Score 5-6: Basic considerations, some aspects covered. '
                    'Score 3-4: Limited planning, may have scaling issues. '
                    'Score 1-2: No meaningful considerations, likely to fail at scale. Return single number 1-10.'
                ),
                justification_prompt='Explain scalability score, evaluating prevention strategies and capacity planning',
            ),
            DimensionConfig(
                name='cost_optimization',
                display_name='Cost Optimization',
                description='Cost efficiency strategies',
                scoring_rubric=(
                    'Score 1-10: Evaluate cost optimization: '
                    '(1) On-demand vs provisioned analysis, '
                    '(2) GSI cost implications considered, '
                    '(3) Storage cost optimization, '
                    '(4) Read/write cost efficiency, '
                    '(5) Multiple cost-saving techniques. '
                    'Score 9-10: Sophisticated optimization, multiple strategies. '
                    'Score 7-8: Good awareness, several techniques. '
                    'Score 5-6: Basic considerations, some suggestions. '
                    'Score 3-4: Limited analysis, unnecessary expenses. '
                    'Score 1-2: No optimization, likely expensive. Return single number 1-10.'
                ),
                justification_prompt='Explain cost optimization score, assessing billing choices and efficiency strategies',
            ),
        ]

        #  Requirement Evaluation dimensions
        requirement_dimensions = [
            DimensionConfig(
                name='requirements_engineering',
                display_name='Requirements Engineering',
                description='Quality of requirements capture and scope definition',
                scoring_rubric=(
                    'Score 1-10: Quality of requirements capture, entity modeling, and scope definition. '
                    'Are business context, scale, and constraints properly documented? '
                    'Return single number 1-10.'
                ),
                justification_prompt='Assess requirements engineering quality, highlighting strengths and gaps',
            ),
            DimensionConfig(
                name='access_pattern_analysis',
                display_name='Access Pattern Analysis',
                description='Rigor of access pattern identification and analysis',
                scoring_rubric=(
                    'Score 1-10: Rigor of access pattern analysis including completeness, '
                    'RPS estimates, performance requirements, and prioritization. '
                    'Return single number 1-10.'
                ),
                justification_prompt='Explain access pattern analysis rigor and completeness',
            ),
            DimensionConfig(
                name='methodology_adherence',
                display_name='Methodology Adherence',
                description='Following structured DynamoDB modeling methodology',
                scoring_rubric=(
                    'Score 1-10: How well does the requirement follow systematic methodology? '
                    'Are decision frameworks properly applied? Return single number 1-10.'
                ),
                justification_prompt='Evaluate methodology adherence and decision framework usage',
            ),
            DimensionConfig(
                name='technical_reasoning',
                display_name='Technical Reasoning',
                description='Quality of design justifications and trade-off analysis',
                scoring_rubric=(
                    'Score 1-10: Quality of design justifications, trade-off analysis, '
                    'risk assessment, and optimization considerations. Return single number 1-10.'
                ),
                justification_prompt='Analyze technical reasoning quality and design justifications',
            ),
            DimensionConfig(
                name='process_documentation',
                display_name='Process Documentation',
                description='Organization and clarity of process documentation',
                scoring_rubric=(
                    'Score 1-10: Organization, transparency, traceability, and professional '
                    'quality of process documentation. Return single number 1-10.'
                ),
                justification_prompt='Explain process documentation quality and organization',
            ),
        ]

        # Register default evaluations
        self.register_evaluation(
            EvaluationConfig(
                name='model_evaluation',
                display_name='Data Model Evaluation',
                description='Assesses technical quality of final DynamoDB schema designs',
                dimensions=model_dimensions,
                input_fields={
                    'scenario_requirements': 'Complete scenario requirements including entities, access patterns, scale, and performance needs in JSON format',
                    'guidance_response': 'The AI-generated DynamoDB guidance response to evaluate',
                    'dynamodb_expert_knowledge': 'Comprehensive DynamoDB expert guidance for reference',
                },
            )
        )

        self.register_evaluation(
            EvaluationConfig(
                name='requirement_evaluation',
                display_name='Requirement Evaluation',
                description='Evaluates quality of the modeling process and methodology',
                dimensions=requirement_dimensions,
                input_fields={
                    'scenario_requirements': 'Original business requirements and constraints provided by user in JSON format',
                    'modeling_requirement_content': 'Complete modeling requirement output including analysis and methodology',
                    'architect_methodology': 'DynamoDB architect prompt methodology and best practices for reference',
                },
            )
        )

    def register_evaluation(self, evaluation_config: EvaluationConfig):
        """Register a new evaluation type."""
        self._evaluations[evaluation_config.name] = evaluation_config

    def get_evaluation(self, name: str) -> EvaluationConfig:
        """Get evaluation configuration by name."""
        if name not in self._evaluations:
            raise ValueError(f"Evaluation type '{name}' not found")
        return self._evaluations[name]

    def list_evaluations(self) -> List[str]:
        """List all registered evaluation type names."""
        return list(self._evaluations.keys())


# Global registry instance
registry = EvaluationRegistry()

# Export the registry for advanced usage
__all__ = [
    'DimensionConfig',
    'EvaluationConfig',
    'EvaluationRegistry',
    'registry',
]
