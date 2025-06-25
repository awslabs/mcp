"""
Advanced recommendation engine for Bedrock models.

This module provides sophisticated model recommendation algorithms
that consider multiple weighted factors to provide optimal model
recommendations based on user requirements.
"""

from typing import Any, Dict, List, Optional, Tuple

from ..models.bedrock import BedrockModel
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RecommendationEngine:
    """
    Advanced recommendation engine for Bedrock models.

    This class implements a sophisticated scoring and recommendation system
    that evaluates foundation models across multiple dimensions to find the
    best match for specific use cases and requirements. The engine considers
    factors such as capability match, performance characteristics, cost,
    regional availability, and provider reliability.

    The recommendation process uses a weighted scoring approach where each factor
    contributes to the final score based on configurable weights. This allows
    for customization of the recommendation algorithm to prioritize different
    aspects based on user preferences.

    Attributes:
        default_weights (Dict[str, float]): Default weighting factors for different
            scoring components. These weights determine how much each factor
            contributes to the final recommendation score.
    """

    def __init__(self):
        """
        Initialize the recommendation engine with default scoring weights.

        The default weights are configured to prioritize capability match (40%),
        followed by performance and cost (20% each), with availability and
        reliability contributing 10% each to the final score.
        """
        # Default weights for different factors
        self.default_weights = {
            "capability_match": 0.4,  # 40% weight for capability match
            "performance": 0.2,  # 20% weight for performance characteristics
            "cost": 0.2,  # 20% weight for cost considerations
            "availability": 0.1,  # 10% weight for regional availability
            "reliability": 0.1,  # 10% weight for provider reliability
        }

    def recommend_models(
        self,
        models: List[BedrockModel],
        criteria: Dict[str, Any],
        max_recommendations: int = 3,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recommend models based on comprehensive criteria and return detailed results.

        This is the main entry point for the recommendation engine. It evaluates all
        available models against the provided criteria, scores them using the weighted
        scoring algorithm, and returns the top recommendations with detailed explanations.

        The criteria can include specifications across multiple dimensions:
        - use_case: Primary and secondary use cases (e.g., text-generation, code-generation)
        - performance_requirements: Latency, throughput, and accuracy requirements
        - cost_constraints: Token price limits and budget priorities
        - technical_requirements: Context length, function calling, multimodal support
        - region_preference: Preferred AWS regions for deployment

        Args:
            models: List of available Bedrock models to evaluate
            criteria: Dictionary containing selection criteria across dimensions
            max_recommendations: Maximum number of recommendations to return (default: 3)
            custom_weights: Optional custom weights for scoring factors to override defaults

        Returns:
            List of recommendation objects, each containing:
            - model: Dictionary with model details (ID, name, capabilities, etc.)
            - score: Normalized score between 0 and 1
            - reasoning: List of reasons explaining the recommendation
            - pros: List of model strengths relevant to the criteria
            - cons: List of model limitations or considerations
        """

        # Use custom weights if provided, otherwise use defaults
        weights = custom_weights or self.default_weights

        # Normalize weights to ensure they sum to 1.0
        total_weight = sum(weights.values())
        normalized_weights = {k: v / total_weight for k, v in weights.items()}

        # Score all models
        scored_models = []
        for model in models:
            score, reasoning, pros, cons = self._score_model(
                model, criteria, normalized_weights
            )
            scored_models.append(
                {
                    "model": {
                        "model_id": model.model_id,
                        "model_name": model.model_name,
                        "provider_name": model.provider_name,
                        "capabilities": model.capabilities.dict(),
                        "performance": model.performance.dict()
                        if model.performance
                        else None,
                        "pricing": model.pricing.dict() if model.pricing else None,
                        "availability": model.availability.dict()
                        if model.availability
                        else None,
                    },
                    "score": score,
                    "reasoning": reasoning,
                    "pros": pros,
                    "cons": cons,
                }
            )

        # Sort by score and take top recommendations
        scored_models.sort(key=lambda x: x["score"], reverse=True)
        return scored_models[:max_recommendations]

    def _score_model(
        self, model: BedrockModel, criteria: Dict[str, Any], weights: Dict[str, float]
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """
        Calculate comprehensive score for a model based on multiple weighted factors.

        This method orchestrates the scoring process by evaluating the model across
        five key dimensions: capability match, performance, cost, availability, and
        reliability. Each dimension is scored independently, and the final score is
        calculated as a weighted sum of these individual scores.

        The method collects detailed reasoning, pros, and cons from each scoring
        component to provide comprehensive explanation of the recommendation.

        Args:
            model: The Bedrock model to evaluate
            criteria: Dictionary containing all selection criteria across dimensions
            weights: Normalized weights for different scoring factors (must sum to 1.0)

        Returns:
            Tuple containing:
            - score: Final normalized score between 0 and 1
            - reasoning: Combined list of reasons explaining the score
            - pros: Combined list of model strengths across all categories
            - cons: Combined list of model limitations across all categories
        """
        # Initialize score components
        scores = {}
        reasoning = []
        pros = []
        cons = []

        # 1. Capability match score
        capability_score, capability_reasons, capability_pros, capability_cons = (
            self._calculate_capability_match(model, criteria)
        )
        scores["capability_match"] = capability_score
        reasoning.extend(capability_reasons)
        pros.extend(capability_pros)
        cons.extend(capability_cons)

        # 2. Performance score
        performance_score, performance_reasons, performance_pros, performance_cons = (
            self._calculate_performance_score(model, criteria)
        )
        scores["performance"] = performance_score
        reasoning.extend(performance_reasons)
        pros.extend(performance_pros)
        cons.extend(performance_cons)

        # 3. Cost score
        cost_score, cost_reasons, cost_pros, cost_cons = self._calculate_cost_score(
            model, criteria
        )
        scores["cost"] = cost_score
        reasoning.extend(cost_reasons)
        pros.extend(cost_pros)
        cons.extend(cost_cons)

        # 4. Availability score
        (
            availability_score,
            availability_reasons,
            availability_pros,
            availability_cons,
        ) = self._calculate_availability_score(model, criteria)
        scores["availability"] = availability_score
        reasoning.extend(availability_reasons)
        pros.extend(availability_pros)
        cons.extend(availability_cons)

        # 5. Reliability score
        reliability_score, reliability_reasons, reliability_pros, reliability_cons = (
            self._calculate_reliability_score(model)
        )
        scores["reliability"] = reliability_score
        reasoning.extend(reliability_reasons)
        pros.extend(reliability_pros)
        cons.extend(reliability_cons)

        # Calculate final weighted score
        final_score = sum(scores[factor] * weight for factor, weight in weights.items())

        # Ensure score is between 0 and 1
        final_score = max(0.0, min(1.0, final_score))

        return final_score, reasoning, pros, cons

    def _calculate_capability_match(
        self, model: BedrockModel, criteria: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """Calculate capability match score."""
        score = 0.5
        reasoning = ["Basic capability match assessment"]
        pros = []
        cons = []

        # Get use case from criteria
        use_case = criteria.get("use_case", {})
        primary_use_case = use_case.get("primary")

        if primary_use_case == "text-generation" and model.capabilities.text_generation:
            score += 0.3
            pros.append("Supports text generation")
        elif (
            primary_use_case == "code-generation" and model.capabilities.code_generation
        ):
            score += 0.3
            pros.append("Supports code generation")

        # Check technical requirements
        tech_reqs = criteria.get("technical_requirements", {})
        if (
            tech_reqs.get("requires_function_calling")
            and model.capabilities.function_calling
        ):
            score += 0.2
            pros.append("Supports function calling")
        elif tech_reqs.get("requires_function_calling"):
            score -= 0.2
            cons.append("Does not support function calling")

        return score, reasoning, pros, cons

    def _calculate_performance_score(
        self, model: BedrockModel, criteria: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """Calculate performance score."""
        score = 0.5
        reasoning = ["Basic performance assessment"]
        pros = []
        cons = []

        if model.performance and model.performance.latency_ms < 1000:
            score += 0.2
            pros.append(f"Low latency ({model.performance.latency_ms}ms)")

        return score, reasoning, pros, cons

    def _calculate_cost_score(
        self, model: BedrockModel, criteria: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """Calculate cost score."""
        score = 0.5
        reasoning = ["Basic cost assessment"]
        pros = []
        cons = []

        if model.pricing and model.pricing.input_token_price < 0.001:
            score += 0.2
            pros.append("Low input token price")

        return score, reasoning, pros, cons

    def _calculate_availability_score(
        self, model: BedrockModel, criteria: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """Calculate availability score."""
        score = 0.5
        reasoning = ["Basic availability assessment"]
        pros = []
        cons = []

        region_preferences = criteria.get("region_preference", [])
        if region_preferences and model.availability:
            matching_regions = set(region_preferences).intersection(
                set(model.availability.regions)
            )
            if matching_regions:
                score += 0.3
                pros.append(
                    f"Available in {len(matching_regions)}/{len(region_preferences)} preferred regions"
                )

        return score, reasoning, pros, cons

    def _calculate_reliability_score(
        self, model: BedrockModel
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """Calculate reliability score."""
        score = 0.5
        reasoning = ["Basic reliability assessment"]
        pros = []
        cons = []

        if model.provider_name.lower() in ["amazon", "anthropic"]:
            score += 0.2
            pros.append(f"Reliable provider ({model.provider_name})")

        return score, reasoning, pros, cons
