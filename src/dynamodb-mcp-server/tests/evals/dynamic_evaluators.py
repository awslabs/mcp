"""Dynamic DSPy evaluator using evaluation registry for easy dimension management."""

import dspy
import json
from dataclasses import dataclass
from evaluation_registry import EvaluationConfig, registry
from logging_config import get_logger
from pathlib import Path
from typing import Any, Dict, Type


# Initialize logger for this module
logger = get_logger(__name__)


def create_dspy_signature(evaluation_config: EvaluationConfig) -> Type[dspy.Signature]:
    """Dynamically create a DSPy signature class based on evaluation configuration."""
    signature_attrs = {}

    input_fields = evaluation_config.input_fields or {}
    for field_name, field_desc in input_fields.items():
        signature_attrs[field_name] = dspy.InputField(desc=field_desc)

    for dimension in evaluation_config.dimensions:
        score_field_name = f'{dimension.name}_score'
        signature_attrs[score_field_name] = dspy.OutputField(desc=dimension.scoring_rubric)

    for dimension in evaluation_config.dimensions:
        if dimension.justification_prompt:
            justification_field_name = f'{dimension.name}_justification'
            signature_attrs[justification_field_name] = dspy.OutputField(
                desc=dimension.justification_prompt
            )

    signature_attrs['strengths'] = dspy.OutputField(
        desc=f'Key strengths of the {evaluation_config.display_name.lower()}, highlighting what was done exceptionally well'
    )
    signature_attrs['weaknesses'] = dspy.OutputField(
        desc=f'Main weaknesses and areas where the {evaluation_config.display_name.lower()} fell short or could be significantly improved'
    )
    signature_attrs['improvement_recommendations'] = dspy.OutputField(
        desc=f'Specific, actionable recommendations for improving the {evaluation_config.display_name.lower()}, with concrete suggestions for addressing identified weaknesses'
    )

    signature_class_name = f'{evaluation_config.name.title().replace("_", "")}Signature'
    signature_class = type(signature_class_name, (dspy.Signature,), signature_attrs)

    signature_class.__doc__ = f'Generated DSPy signature for {evaluation_config.display_name} with {len(evaluation_config.dimensions)} dimensions.'

    return signature_class


def create_result_dataclass(evaluation_config: EvaluationConfig) -> Type:
    """Dynamically create a result dataclass based on evaluation configuration."""
    class_fields = []

    for dimension in evaluation_config.dimensions:
        class_fields.append((dimension.name, float))

    class_fields.extend(
        [('justifications', Dict[str, str]), ('overall_score', float), ('quality_level', str)]
    )

    dataclass_name = f'{evaluation_config.name.title().replace("_", "")}Result'
    annotations = dict(class_fields)
    result_class = type(dataclass_name, (), {'__annotations__': annotations})
    result_class = dataclass(result_class)

    def to_dict(self):
        """Convert result object to dictionary for JSON serialization."""
        result_dict = {}
        for dimension in evaluation_config.dimensions:
            result_dict[dimension.name] = getattr(self, dimension.name)
        result_dict.update(
            {
                'justifications': self.justifications,
                'overall_score': self.overall_score,
                'quality_level': self.quality_level,
            }
        )
        return result_dict

    setattr(result_class, 'to_dict', to_dict)
    result_class.__doc__ = f'Generated result container for {evaluation_config.display_name} with {len(evaluation_config.dimensions)} dimensions.'

    return result_class


class DynamicEvaluationEngine:
    """Dynamic evaluation engine that adapts to any registered evaluation type."""

    def __init__(self):
        """Initialize the dynamic evaluation engine with empty caches."""
        self._evaluators = {}
        self._result_classes = {}
        self._expert_knowledge_cache = None

    def _get_evaluator(self, evaluation_name: str):
        """Get or create evaluator for the specified evaluation type."""
        if evaluation_name not in self._evaluators:
            evaluation_config = registry.get_evaluation(evaluation_name)
            signature_class = create_dspy_signature(evaluation_config)
            self._evaluators[evaluation_name] = dspy.ChainOfThought(signature_class)

        return self._evaluators[evaluation_name]

    def _get_result_class(self, evaluation_name: str):
        """Get or create result class for the specified evaluation type."""
        if evaluation_name not in self._result_classes:
            evaluation_config = registry.get_evaluation(evaluation_name)
            self._result_classes[evaluation_name] = create_result_dataclass(evaluation_config)

        return self._result_classes[evaluation_name]

    def _load_expert_knowledge(self) -> str:
        """Load DynamoDB expert knowledge (cached)."""
        if self._expert_knowledge_cache is None:
            try:
                prompt_path = (
                    Path(__file__).parent.parent.parent
                    / 'awslabs'
                    / 'dynamodb_mcp_server'
                    / 'prompts'
                    / 'dynamodb_architect.md'
                )
                self._expert_knowledge_cache = prompt_path.read_text(encoding='utf-8')
            except Exception as e:
                logger.warning(f'Warning: Could not load expert knowledge: {e}')
                self._expert_knowledge_cache = 'Expert knowledge not available.'

        return self._expert_knowledge_cache

    def evaluate(self, evaluation_name: str, scenario: Dict[str, Any], content: str, **kwargs):
        """Evaluate content using the specified evaluation type."""
        evaluation_config = registry.get_evaluation(evaluation_name)
        evaluator = self._get_evaluator(evaluation_name)
        result_class = self._get_result_class(evaluation_name)

        # Prepare input arguments
        eval_inputs = {}

        scenario_json = json.dumps(scenario, indent=2)

        input_mappings = {
            'scenario_requirements': scenario_json,
            'guidance_response': content,
            'modeling_requirement_content': content,
            'dynamodb_expert_knowledge': self._load_expert_knowledge(),
            'architect_methodology': self._load_expert_knowledge(),
        }

        # Add inputs based on evaluation configuration
        for field_name in evaluation_config.input_fields.keys():
            if field_name in input_mappings:
                eval_inputs[field_name] = input_mappings[field_name]
            elif field_name in kwargs:
                eval_inputs[field_name] = kwargs[field_name]

        # Run the evaluation
        raw_result = evaluator(**eval_inputs)

        # Process results into structured format
        return self._process_results(evaluation_config, raw_result, result_class)

    def _process_results(self, evaluation_config: EvaluationConfig, raw_result, result_class):
        """Process raw DSPy results into structured result object."""
        # Extract dimension scores
        dimension_scores = {}
        for dimension in evaluation_config.dimensions:
            score_field = f'{dimension.name}_score'
            score_value = getattr(raw_result, score_field, 0.0)
            # Handle DSPy returning various types
            if isinstance(score_value, (int, float)):
                dimension_scores[dimension.name] = float(score_value)
            else:
                # Try to parse if string
                try:
                    dimension_scores[dimension.name] = float(str(score_value).split()[0])
                except (ValueError, IndexError):
                    dimension_scores[dimension.name] = 0.0

        # Calculate overall score using weighted average
        total_weight = sum(dim.weight for dim in evaluation_config.dimensions)
        if total_weight > 0:
            weighted_sum = sum(
                dimension_scores[dim.name] * dim.weight for dim in evaluation_config.dimensions
            )
            overall_score = round(weighted_sum / total_weight, 2)
        else:
            overall_score = 0.0

        # Determine quality level using existing thresholds
        quality_thresholds = {
            'excellent': 8.5,
            'good': 7.0,
            'acceptable': 5.5,
            'needs_improvement': 4.0,
            'poor': 2.0,
        }

        if overall_score >= quality_thresholds['excellent']:
            quality_level = 'excellent'
        elif overall_score >= quality_thresholds['good']:
            quality_level = 'good'
        elif overall_score >= quality_thresholds['acceptable']:
            quality_level = 'acceptable'
        elif overall_score >= quality_thresholds['needs_improvement']:
            quality_level = 'needs_improvement'
        else:
            quality_level = 'poor'

        # Build justifications dictionary
        justifications = {}

        # Add dimension justifications
        for dimension in evaluation_config.dimensions:
            if dimension.justification_prompt:
                justification_field = f'{dimension.name}_justification'
                justifications[dimension.name] = str(getattr(raw_result, justification_field, ''))

        # Add overall assessment fields
        justifications.update(
            {
                'strengths': str(getattr(raw_result, 'strengths', '')),
                'weaknesses': str(getattr(raw_result, 'weaknesses', '')),
                'improvement_recommendations': str(
                    getattr(raw_result, 'improvement_recommendations', '')
                ),
            }
        )

        # Create result object
        result_kwargs = {
            **dimension_scores,
            'justifications': justifications,
            'overall_score': overall_score,
            'quality_level': quality_level,
        }

        return result_class(**result_kwargs)


# Create global instance
dynamic_engine = DynamicEvaluationEngine()

__all__ = [
    'DynamicEvaluationEngine',
    'create_dspy_signature',
    'create_result_dataclass',
    'dynamic_engine',
]
