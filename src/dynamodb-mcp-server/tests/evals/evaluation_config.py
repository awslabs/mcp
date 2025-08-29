"""Configuration for DynamoDB guidance evaluation system.

This module provides the foundational configuration infrastructure for evaluating
DynamoDB data modeling guidance quality. It defines two complementary evaluation
frameworks:

1. **Data Model Evaluation**: Assesses the technical quality of final DynamoDB
   schema designs including completeness, accuracy, and optimization strategies.

2. **Session Evaluation**: Evaluates the quality of the modeling process itself,
   including requirements gathering, methodology adherence, and documentation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class EvaluationDimension(Enum):
    """Core dimensions for evaluating DynamoDB data model guidance quality.

    These dimensions assess the technical quality of final DynamoDB schema designs,
    focusing on the completeness and correctness of the delivered solution.
    Each dimension is scored 1-10 and contributes equally to the overall model score.

    Dimensions:
        COMPLETENESS: Whether guidance addresses all scenario requirements
            - Entity identification and modeling
            - Relationship mapping
            - Access pattern identification
            - Performance and scale requirements coverage

        TECHNICAL_ACCURACY: Correctness of DynamoDB recommendations
            - Primary key design best practices
            - GSI design and projection optimization
            - Data type selections and TTL usage
            - Sort key design for access patterns

        ACCESS_PATTERN_COVERAGE: Optimization for query patterns
            - Query pattern mapping to table/GSI design
            - Optimization for frequent/critical patterns
            - Edge case and infrequent pattern handling
            - Performance implications addressed

        SCALABILITY_CONSIDERATIONS: Performance and scale planning
            - Hot partition prevention strategies
            - Capacity planning for growth
            - Performance bottleneck identification
            - Auto-scaling and future growth accommodation

        COST_OPTIMIZATION: Cost efficiency strategies
            - On-demand vs provisioned billing analysis
            - GSI cost implications
            - Storage optimization strategies
            - Read/write cost efficiency recommendations
    """

    COMPLETENESS = 'completeness'
    TECHNICAL_ACCURACY = 'technical_accuracy'
    ACCESS_PATTERN_COVERAGE = 'access_pattern_coverage'
    SCALABILITY_CONSIDERATIONS = 'scalability_considerations'
    COST_OPTIMIZATION = 'cost_optimization'


class SessionDimension(Enum):
    """Core dimensions for evaluating DynamoDB modeling session quality.

    These dimensions assess the quality of the modeling process itself, focusing
    on methodology, requirements gathering, and systematic analysis approach.
    Each dimension is scored 1-10 and contributes equally to the overall session score.

    Dimensions:
        REQUIREMENTS_ENGINEERING: Quality of requirements capture and scope definition
            - Business context understanding and documentation
            - Entity identification and relationship modeling
            - Constraint and requirement completeness
            - Scale and performance requirement analysis

        ACCESS_PATTERN_ANALYSIS: Rigor of access pattern identification and analysis
            - Comprehensive pattern identification (read/write)
            - RPS estimates and performance requirements
            - Pattern prioritization by business importance
            - Edge case and secondary pattern consideration

        METHODOLOGY_ADHERENCE: Following structured DynamoDB modeling methodology
            - Systematic approach to design decisions
            - Decision framework application
            - Step-by-step progression through modeling phases
            - Best practice application throughout process

        TECHNICAL_REASONING: Quality of design justifications and trade-off analysis
            - Clear rationale for design choices
            - Trade-off analysis between alternatives
            - Risk assessment and mitigation strategies
            - Optimization consideration explanations

        PROCESS_DOCUMENTATION: Organization and clarity of process documentation
            - Clear structure and logical flow
            - Transparency of decision-making process
            - Traceability from requirements to design
            - Professional quality and completeness
    """

    REQUIREMENTS_ENGINEERING = 'requirements_engineering'
    ACCESS_PATTERN_ANALYSIS = 'access_pattern_analysis'
    METHODOLOGY_ADHERENCE = 'methodology_adherence'
    TECHNICAL_REASONING = 'technical_reasoning'
    PROCESS_DOCUMENTATION = 'process_documentation'


@dataclass
class ScoringCriteria:
    """Standardized scoring criteria framework for evaluation dimensions.

    Provides detailed rubrics for each score level (1-10 scale) to ensure
    consistent evaluation across different assessors and evaluation sessions.
    Each criterion level corresponds to specific quality benchmarks.

    Attributes:
        excellent (str): Criteria for scores 9-10 (exceptional quality)
        good (str): Criteria for scores 7-8 (solid quality with minor gaps)
        fair (str): Criteria for scores 5-6 (adequate with notable limitations)
        poor (str): Criteria for scores 3-4 (significant deficiencies)
        failing (str): Criteria for scores 1-2 (major gaps or errors)
    """

    excellent: str  # 9-10 score criteria - exceptional quality
    good: str  # 7-8 score criteria - solid quality with minor gaps
    fair: str  # 5-6 score criteria - adequate with notable limitations
    poor: str  # 3-4 score criteria - significant deficiencies
    failing: str  # 1-2 score criteria - major gaps or fundamental errors

    def get_score_description(self, score: int) -> str:
        """Map numeric score to corresponding quality description.

        Args:
            score: Numeric score from 1-10

        Returns:
            String description matching the score range

        Score Mapping:
            9-10: excellent (exceptional quality)
            7-8:  good (solid quality with minor gaps)
            5-6:  fair (adequate with notable limitations)
            3-4:  poor (significant deficiencies)
            1-2:  failing (major gaps or fundamental errors)
        """
        if score >= 9:
            return self.excellent
        elif score >= 7:
            return self.good
        elif score >= 5:
            return self.fair
        elif score >= 3:
            return self.poor
        else:
            return self.failing


class EvaluationConfig:
    """Central configuration for DynamoDB guidance evaluation system.

    Provides scoring algorithms, quality thresholds, and evaluation parameters
    for both data model and session evaluations. This class serves as the
    single source of truth for evaluation standards and scoring methodology.
    """

    QUALITY_THRESHOLDS = {
        'excellent': 8.5,  # Exceptional quality - ready for production
        'good': 7.0,  # Solid quality - minor improvements needed
        'acceptable': 5.5,  # Adequate - meets basic requirements
        'needs_improvement': 4.0,  # Deficient - significant gaps present
        'poor': 2.0,  # Major issues - substantial rework required
    }

    @classmethod
    def calculate_datamodel_eval_score(cls, scores: Dict[EvaluationDimension, float]) -> float:
        """Calculate overall data model evaluation score using equal weighting.

        Computes arithmetic mean across all EvaluationDimension scores to
        produce a balanced assessment of technical design quality.

        Args:
            scores: Dictionary mapping each EvaluationDimension to its numeric score (1-10)
                   Must contain all 5 dimensions: COMPLETENESS, TECHNICAL_ACCURACY,
                   ACCESS_PATTERN_COVERAGE, SCALABILITY_CONSIDERATIONS, COST_OPTIMIZATION

        Returns:
            Overall score (1-10) rounded to 2 decimal places
        """
        weighted_sum = (
            scores[EvaluationDimension.COMPLETENESS]
            + scores[EvaluationDimension.TECHNICAL_ACCURACY]
            + scores[EvaluationDimension.ACCESS_PATTERN_COVERAGE]
            + scores[EvaluationDimension.SCALABILITY_CONSIDERATIONS]
            + scores[EvaluationDimension.COST_OPTIMIZATION]
        ) / len(EvaluationDimension)

        return round(weighted_sum, 2)

    @classmethod
    def calculate_session_eval_score(cls, scores: Dict[SessionDimension, float]) -> float:
        """Calculate overall session evaluation score using equal weighting.

        Computes arithmetic mean across all SessionDimension scores to
        produce a balanced assessment of modeling process quality.

        Args:
            scores: Dictionary mapping each SessionDimension to its numeric score (1-10)
                   Must contain all 5 dimensions: REQUIREMENTS_ENGINEERING,
                   ACCESS_PATTERN_ANALYSIS, METHODOLOGY_ADHERENCE,
                   TECHNICAL_REASONING, PROCESS_DOCUMENTATION

        Returns:
            Overall score (1-10) rounded to 2 decimal places
        """
        weighted_sum = (
            scores[SessionDimension.REQUIREMENTS_ENGINEERING]
            + scores[SessionDimension.ACCESS_PATTERN_ANALYSIS]
            + scores[SessionDimension.METHODOLOGY_ADHERENCE]
            + scores[SessionDimension.TECHNICAL_REASONING]
            + scores[SessionDimension.PROCESS_DOCUMENTATION]
        ) / len(SessionDimension)

        return round(weighted_sum, 2)

    @classmethod
    def get_quality_level(cls, score: float) -> str:
        """Map numeric score to categorical quality level.

        Converts continuous numeric scores to discrete quality categories
        using predefined thresholds. Provides human-readable assessment
        levels for reporting and decision-making.

        Args:
            score: Numeric score (typically 1-10 range)

        Returns:
            Quality level string: "excellent", "good", "acceptable",
            "needs_improvement", or "poor"
        """
        if score >= cls.QUALITY_THRESHOLDS['excellent']:
            return 'excellent'
        elif score >= cls.QUALITY_THRESHOLDS['good']:
            return 'good'
        elif score >= cls.QUALITY_THRESHOLDS['acceptable']:
            return 'acceptable'
        elif score >= cls.QUALITY_THRESHOLDS['needs_improvement']:
            return 'needs_improvement'
        else:
            return 'poor'


__all__ = [
    'EvaluationConfig',
    'EvaluationDimension',
    'SessionDimension',
    'ScoringCriteria',
]
