"""
Model comparison service for Bedrock Advisor.

This module provides advanced model comparison functionality, including
detailed side-by-side comparisons, feature differentials, and cost analysis
to help users make informed decisions when choosing between models.
"""

from typing import Any, Dict, List, Optional, cast

from typing_extensions import TypedDict

from ..models.bedrock import BedrockModel
from ..utils.logging import get_logger
from .recommendation import RecommendationEngine

logger = get_logger(__name__)


class ComparisonResult(TypedDict):
    """Type definition for model comparison result."""

    model_id: str
    model_name: str
    provider: str
    score: float
    reasoning: List[str]
    pros: List[str]
    cons: List[str]
    feature_scores: Dict[str, float]


class ComparisonService:
    """
    Service for comparing Bedrock models across multiple dimensions.

    This service provides comprehensive model comparison functionality,
    including scoring, feature analysis, cost comparison, and performance
    benchmarking to help users make informed decisions when choosing
    between different foundation models.
    """

    def __init__(self):
        """Initialize the comparison service."""
        self.recommendation_engine = RecommendationEngine()

    def compare_models(
        self,
        models: List[BedrockModel],
        criteria: Dict[str, Any],
        include_detailed_analysis: bool = True,
    ) -> Dict[str, Any]:
        """
        Compare multiple models based on specified criteria.

        This method performs a comprehensive comparison of the provided models
        across multiple dimensions, including capabilities, performance, cost,
        and availability. It generates detailed comparison results with scores,
        reasoning, and feature-by-feature analysis.

        Args:
            models: List of models to compare
            criteria: Comparison criteria (same format as recommend_model)
            include_detailed_analysis: Whether to include detailed scoring breakdown

        Returns:
            Dict containing comparison results, comparison table, winner, and summary
        """
        if len(models) < 2:
            raise ValueError("At least two models must be provided for comparison")

        # Score each model
        scored_models = self._score_models(models, criteria)

        # Generate comparison table
        comparison_table = self._generate_comparison_table(models)

        # Generate feature comparison
        feature_comparison = (
            self._generate_feature_comparison(models)
            if include_detailed_analysis
            else None
        )

        # Generate cost comparison
        cost_comparison = (
            self._generate_cost_comparison(models)
            if include_detailed_analysis
            else None
        )

        # Generate performance comparison
        performance_comparison = (
            self._generate_performance_comparison(models)
            if include_detailed_analysis
            else None
        )

        # Generate winner and summary
        winner = scored_models[0]["model_id"] if scored_models else None
        summary = {
            "winner": winner,
            "winner_name": scored_models[0]["model_name"] if scored_models else None,
            "winner_score": scored_models[0]["score"] if scored_models else None,
            "models_compared": len(models),
            "comparison_criteria": criteria.get("use_case", {}).get(
                "primary", "general performance"
            ),
        }

        # Generate key differentiators
        key_differentiators = (
            self._identify_key_differentiators(models, scored_models)
            if include_detailed_analysis
            else None
        )

        # Generate usage scenario comparison
        usage_scenario_comparison = (
            self.generate_usage_scenario_comparison(models)
            if include_detailed_analysis
            else None
        )

        # Generate recommendation summary
        recommendation_summary = (
            self.generate_recommendation_summary(models)
            if include_detailed_analysis
            else None
        )

        result = {
            "comparison_results": scored_models,
            "comparison_table": comparison_table,
            "winner": winner,
            "summary": summary,
        }

        # Add detailed analysis if requested
        if include_detailed_analysis:
            result["detailed_analysis"] = {
                "feature_comparison": feature_comparison,
                "cost_comparison": cost_comparison,
                "performance_comparison": performance_comparison,
                "key_differentiators": key_differentiators,
                "usage_scenario_comparison": usage_scenario_comparison,
                "recommendation_summary": recommendation_summary,
            }

        return result

    def _score_models(
        self, models: List[BedrockModel], criteria: Dict[str, Any]
    ) -> List[ComparisonResult]:
        """
        Score each model based on the provided criteria.

        Args:
            models: List of models to score
            criteria: Scoring criteria

        Returns:
            List of scored models with detailed results
        """
        scored_models: List[ComparisonResult] = []

        for model in models:
            # Get overall score and reasoning
            score, reasoning, pros, cons = self.recommendation_engine._score_model(
                model, criteria, self.recommendation_engine.default_weights
            )

            # Get detailed feature scores
            feature_scores = self._calculate_feature_scores(model, criteria)

            scored_models.append(
                cast(
                    ComparisonResult,
                    {
                        "model_id": model.model_id,
                        "model_name": model.model_name,
                        "provider": model.provider_name,
                        "score": score,
                        "reasoning": reasoning,
                        "pros": pros,
                        "cons": cons,
                        "feature_scores": feature_scores,
                    },
                )
            )

        # Sort by score
        scored_models.sort(key=lambda x: x["score"], reverse=True)

        return scored_models

    def _calculate_feature_scores(
        self, model: BedrockModel, criteria: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate detailed scores for individual features.

        Args:
            model: Model to score
            criteria: Scoring criteria

        Returns:
            Dictionary of feature scores
        """
        feature_scores = {}

        # Calculate capability score
        capability_score, _, _, _ = (
            self.recommendation_engine._calculate_capability_match(model, criteria)
        )
        feature_scores["capability"] = capability_score

        # Calculate performance score
        performance_score, _, _, _ = (
            self.recommendation_engine._calculate_performance_score(model, criteria)
        )
        feature_scores["performance"] = performance_score

        # Calculate cost score
        cost_score, _, _, _ = self.recommendation_engine._calculate_cost_score(
            model, criteria
        )
        feature_scores["cost"] = cost_score

        # Calculate availability score
        availability_score, _, _, _ = (
            self.recommendation_engine._calculate_availability_score(model, criteria)
        )
        feature_scores["availability"] = availability_score

        # Calculate reliability score
        reliability_score, _, _, _ = (
            self.recommendation_engine._calculate_reliability_score(model)
        )
        feature_scores["reliability"] = reliability_score

        return feature_scores

    def _generate_comparison_table(
        self, models: List[BedrockModel]
    ) -> List[Dict[str, Any]]:
        """
        Generate a structured comparison table for the models.

        Args:
            models: List of models to compare

        Returns:
            List of model information dictionaries for tabular comparison
        """
        comparison_table = []

        for model in models:
            model_info = {
                "model_id": model.model_id,
                "model_name": model.model_name,
                "provider": model.provider_name,
                "context_length": model.context_length,
                "max_tokens": model.max_tokens,
                "streaming_supported": model.response_streaming_supported,
                "multimodal": model.capabilities.multimodal,
                "function_calling": model.capabilities.function_calling,
                "regions": len(model.availability.regions),
                "status": model.availability.status.value,
            }

            # Add pricing if available
            if model.pricing:
                model_info["input_price"] = (
                    f"${model.pricing.input_token_price:.6f} per 1K tokens"
                )
                model_info["output_price"] = (
                    f"${model.pricing.output_token_price:.6f} per 1K tokens"
                )

                # Add cost for common scenarios
                model_info["cost_1M_tokens"] = (
                    f"${(model.pricing.input_token_price + model.pricing.output_token_price) * 1000:.2f}"
                )

            # Add performance metrics
            if model.performance:
                model_info["latency_ms"] = model.performance.latency_ms
                model_info["throughput"] = (
                    model.performance.throughput_tokens_per_second
                )
                model_info["accuracy"] = model.performance.accuracy_score

            # Add capability details
            model_info["capabilities"] = {
                "text_generation": model.capabilities.text_generation,
                "code_generation": model.capabilities.code_generation,
                "summarization": model.capabilities.summarization,
                "question_answering": model.capabilities.question_answering,
                "translation": model.capabilities.translation,
                "classification": model.capabilities.classification,
                "embedding": model.capabilities.embedding,
                "multimodal": model.capabilities.multimodal,
                "function_calling": model.capabilities.function_calling,
                "reasoning": model.capabilities.reasoning,
                "mathematics": model.capabilities.mathematics,
                "creative": model.capabilities.creative,
            }

            comparison_table.append(model_info)

        return comparison_table

    def _generate_feature_comparison(
        self, models: List[BedrockModel]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate a feature-by-feature comparison of the models.

        Args:
            models: List of models to compare

        Returns:
            Dictionary with feature categories and comparisons
        """
        # Define feature categories
        categories = {
            "capabilities": [
                "text_generation",
                "code_generation",
                "summarization",
                "question_answering",
                "translation",
                "classification",
                "embedding",
                "multimodal",
                "function_calling",
                "reasoning",
                "mathematics",
                "creative",
            ],
            "performance": [
                "latency_ms",
                "throughput_tokens_per_second",
                "accuracy_score",
            ],
            "technical": [
                "context_length",
                "max_tokens",
                "response_streaming_supported",
            ],
            "pricing": ["input_token_price", "output_token_price"],
        }

        result = {}

        # Generate comparison for each category
        for category, features in categories.items():
            feature_list = []

            for feature in features:
                feature_values = []

                for model in models:
                    # Get feature value based on category
                    if category == "capabilities":
                        value = getattr(model.capabilities, feature, None)
                    elif category == "performance":
                        value = (
                            getattr(model.performance, feature, None)
                            if model.performance
                            else None
                        )
                    elif category == "pricing":
                        value = (
                            getattr(model.pricing, feature, None)
                            if model.pricing
                            else None
                        )
                    elif category == "technical":
                        value = getattr(model, feature, None)
                    else:
                        value = None

                    feature_values.append(
                        {
                            "model_id": model.model_id,
                            "model_name": model.model_name,
                            "value": value,
                        }
                    )

                feature_list.append(
                    {
                        "feature": feature,
                        "values": feature_values,
                        "best_model": self._determine_best_model_for_feature(
                            feature, feature_values
                        ),
                    }
                )

            result[category] = feature_list

        return result

    def _determine_best_model_for_feature(
        self, feature: str, feature_values: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Determine which model is best for a specific feature.

        Args:
            feature: Feature name
            feature_values: List of feature values for each model

        Returns:
            Model ID of the best model for this feature, or None if no clear winner
        """
        # Skip if any value is None
        if any(item["value"] is None for item in feature_values):
            return None

        # For boolean features, if only one model has it, that's the best
        if all(isinstance(item["value"], bool) for item in feature_values):
            true_values = [item for item in feature_values if item["value"] is True]
            if len(true_values) == 1:
                return true_values[0]["model_id"]
            elif len(true_values) == len(feature_values):
                return None  # All models have this feature
            elif len(true_values) == 0:
                return None  # No model has this feature

        # For numeric features, determine best based on feature type
        if all(isinstance(item["value"], (int, float)) for item in feature_values):
            # Lower is better for latency and price
            if "latency" in feature or "price" in feature:
                best_item = min(feature_values, key=lambda x: x["value"])
                return best_item["model_id"]

            # Higher is better for throughput, accuracy, context length, etc.
            else:
                best_item = max(feature_values, key=lambda x: x["value"])
                return best_item["model_id"]

        # No clear winner
        return None

    def _generate_cost_comparison(self, models: List[BedrockModel]) -> Dict[str, Any]:
        """
        Generate a detailed cost comparison for the models.

        Args:
            models: List of models to compare

        Returns:
            Dictionary with cost comparison data
        """
        # Define common usage scenarios
        scenarios = [
            {"name": "Small request", "input_tokens": 1000, "output_tokens": 500},
            {"name": "Medium request", "input_tokens": 5000, "output_tokens": 1000},
            {"name": "Large request", "input_tokens": 20000, "output_tokens": 2000},
            {
                "name": "Monthly (100 req/day)",
                "input_tokens": 300000,  # 1000 * 100 * 30
                "output_tokens": 150000,  # 500 * 100 * 30
            },
        ]

        # Calculate costs for each model and scenario
        cost_comparison = {"scenarios": scenarios, "model_costs": []}

        for model in models:
            if not model.pricing:
                continue

            model_costs = {
                "model_id": model.model_id,
                "model_name": model.model_name,
                "input_price": model.pricing.input_token_price,
                "output_price": model.pricing.output_token_price,
                "scenario_costs": [],
            }

            for scenario in scenarios:
                input_cost = (
                    scenario["input_tokens"] / 1000
                ) * model.pricing.input_token_price
                output_cost = (
                    scenario["output_tokens"] / 1000
                ) * model.pricing.output_token_price
                total_cost = input_cost + output_cost

                model_costs["scenario_costs"].append(
                    {
                        "scenario": scenario["name"],
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost,
                    }
                )

            cost_comparison["model_costs"].append(model_costs)

        # Determine most cost-effective model for each scenario
        for i, scenario in enumerate(scenarios):
            costs = [
                (model["model_id"], model["scenario_costs"][i]["total_cost"])
                for model in cost_comparison["model_costs"]
            ]

            if costs:
                most_cost_effective = min(costs, key=lambda x: x[1])
                cost_comparison["scenarios"][i]["most_cost_effective_model"] = (
                    most_cost_effective[0]
                )

        return cost_comparison

    def _generate_performance_comparison(
        self, models: List[BedrockModel]
    ) -> Dict[str, Any]:
        """
        Generate a detailed performance comparison for the models.

        Args:
            models: List of models to compare

        Returns:
            Dictionary with performance comparison data
        """
        performance_metrics = [
            "latency_ms",
            "throughput_tokens_per_second",
            "accuracy_score",
        ]

        performance_comparison = {"metrics": [], "best_overall_performance": None}

        # Calculate performance scores for each metric
        for metric in performance_metrics:
            metric_values = []

            for model in models:
                if not model.performance:
                    continue

                value = getattr(model.performance, metric, None)
                if value is not None:
                    metric_values.append(
                        {
                            "model_id": model.model_id,
                            "model_name": model.model_name,
                            "value": value,
                        }
                    )

            # Determine best model for this metric
            best_model = None
            if metric_values:
                if metric == "latency_ms":
                    best_model = min(metric_values, key=lambda x: x["value"])[
                        "model_id"
                    ]
                else:
                    best_model = max(metric_values, key=lambda x: x["value"])[
                        "model_id"
                    ]

            performance_comparison["metrics"].append(
                {"metric": metric, "values": metric_values, "best_model": best_model}
            )

        # Calculate overall performance score
        performance_scores = {}
        for model in models:
            if not model.performance:
                continue

            # Normalize and combine scores (lower latency is better, higher throughput and accuracy are better)
            latency_score = (
                1.0 - min(1.0, model.performance.latency_ms / 3000)
                if model.performance.latency_ms
                else 0
            )
            throughput_score = (
                min(1.0, model.performance.throughput_tokens_per_second / 150)
                if model.performance.throughput_tokens_per_second
                else 0
            )
            accuracy_score = (
                model.performance.accuracy_score
                if model.performance.accuracy_score
                else 0
            )

            # Weighted combination
            overall_score = (
                (latency_score * 0.3)
                + (throughput_score * 0.3)
                + (accuracy_score * 0.4)
            )
            performance_scores[model.model_id] = overall_score

        # Determine best overall performance
        if performance_scores:
            best_model_id = max(performance_scores.items(), key=lambda x: x[1])[0]
            best_model = next((m for m in models if m.model_id == best_model_id), None)

            if best_model:
                performance_comparison["best_overall_performance"] = {
                    "model_id": best_model.model_id,
                    "model_name": best_model.model_name,
                    "score": performance_scores[best_model_id],
                }

        return performance_comparison

    def _identify_key_differentiators(
        self, models: List[BedrockModel], scored_models: List[ComparisonResult]
    ) -> Dict[str, Any]:
        """
        Identify key differentiating factors between models.

        Args:
            models: List of models to compare
            scored_models: List of scored model results

        Returns:
            Dictionary containing key differentiators organized by category
        """
        # Initialize differentiators by category
        differentiators = {
            "capability_differentiators": [],
            "performance_differentiators": [],
            "cost_differentiators": [],
            "technical_differentiators": [],
            "summary": {},
        }

        # Compare top model with others
        if len(scored_models) < 2:
            return differentiators

        top_model = scored_models[0]
        other_models = scored_models[1:]

        # Find the model objects
        top_model_obj = next(
            (m for m in models if m.model_id == top_model["model_id"]), None
        )
        if not top_model_obj:
            return differentiators

        # Check for significant differences in feature scores
        for feature, score in top_model["feature_scores"].items():
            for other_model in other_models:
                other_score = other_model["feature_scores"].get(feature, 0)

                # If there's a significant difference (>0.2)
                if abs(score - other_score) > 0.2:
                    differentiator = {
                        "feature": feature,
                        "top_model": {
                            "model_id": top_model["model_id"],
                            "model_name": top_model["model_name"],
                            "score": score,
                        },
                        "compared_model": {
                            "model_id": other_model["model_id"],
                            "model_name": other_model["model_name"],
                            "score": other_score,
                        },
                        "difference": score - other_score,
                        "significance": "high"
                        if abs(score - other_score) > 0.4
                        else "medium",
                    }

                    # Add explanation based on feature
                    if feature == "capability":
                        if score > other_score:
                            differentiator["explanation"] = (
                                f"{top_model['model_name']} has more comprehensive capabilities for the specified use case"
                            )
                        else:
                            differentiator["explanation"] = (
                                f"{other_model['model_name']} has more comprehensive capabilities for the specified use case"
                            )
                        differentiators["capability_differentiators"].append(
                            differentiator
                        )
                    elif feature == "performance":
                        if score > other_score:
                            differentiator["explanation"] = (
                                f"{top_model['model_name']} offers better performance characteristics (latency, throughput)"
                            )
                        else:
                            differentiator["explanation"] = (
                                f"{other_model['model_name']} offers better performance characteristics (latency, throughput)"
                            )
                        differentiators["performance_differentiators"].append(
                            differentiator
                        )
                    elif feature == "cost":
                        if score > other_score:
                            differentiator["explanation"] = (
                                f"{top_model['model_name']} is more cost-effective for the specified usage pattern"
                            )
                        else:
                            differentiator["explanation"] = (
                                f"{other_model['model_name']} is more cost-effective for the specified usage pattern"
                            )
                        differentiators["cost_differentiators"].append(differentiator)
                    elif feature == "availability":
                        if score > other_score:
                            differentiator["explanation"] = (
                                f"{top_model['model_name']} has better regional availability"
                            )
                        else:
                            differentiator["explanation"] = (
                                f"{other_model['model_name']} has better regional availability"
                            )
                        differentiators["technical_differentiators"].append(
                            differentiator
                        )
                    else:
                        differentiators["technical_differentiators"].append(
                            differentiator
                        )

        return differentiators

    def generate_usage_scenario_comparison(
        self, models: List[BedrockModel]
    ) -> Dict[str, Any]:
        """
        Generate comparison of models across different usage scenarios.

        Args:
            models: List of models to compare

        Returns:
            Dictionary with usage scenario comparison data
        """
        # Define common usage scenarios
        scenarios = [
            {
                "name": "Text generation",
                "description": "General text generation tasks",
                "key_capabilities": ["text_generation", "creative"],
                "key_metrics": ["accuracy_score"],
            },
            {
                "name": "Code generation",
                "description": "Writing and completing code",
                "key_capabilities": ["code_generation", "reasoning"],
                "key_metrics": ["accuracy_score"],
            },
            {
                "name": "Question answering",
                "description": "Answering questions accurately",
                "key_capabilities": ["question_answering", "reasoning"],
                "key_metrics": ["accuracy_score"],
            },
            {
                "name": "High throughput",
                "description": "Processing many requests quickly",
                "key_capabilities": [],
                "key_metrics": ["throughput_tokens_per_second", "latency_ms"],
            },
            {
                "name": "Cost-sensitive",
                "description": "Minimizing token costs",
                "key_capabilities": [],
                "key_metrics": ["input_token_price", "output_token_price"],
            },
        ]

        # Score each model for each scenario
        scenario_results = []

        for scenario in scenarios:
            model_scores = []

            for model in models:
                score = 0.0
                reasons = []

                # Score based on capabilities
                for capability in scenario["key_capabilities"]:
                    if hasattr(model.capabilities, capability) and getattr(
                        model.capabilities, capability
                    ):
                        score += 1.0
                        reasons.append(f"Supports {capability}")

                # Score based on metrics
                for metric in scenario["key_metrics"]:
                    if (
                        metric == "latency_ms"
                        and model.performance
                        and model.performance.latency_ms
                    ):
                        # Lower latency is better
                        normalized_score = 1.0 - min(
                            1.0, model.performance.latency_ms / 3000
                        )
                        score += normalized_score
                        reasons.append(f"Latency: {model.performance.latency_ms}ms")
                    elif (
                        metric == "throughput_tokens_per_second"
                        and model.performance
                        and model.performance.throughput_tokens_per_second
                    ):
                        # Higher throughput is better
                        normalized_score = min(
                            1.0, model.performance.throughput_tokens_per_second / 150
                        )
                        score += normalized_score
                        reasons.append(
                            f"Throughput: {model.performance.throughput_tokens_per_second} tokens/sec"
                        )
                    elif (
                        metric == "accuracy_score"
                        and model.performance
                        and model.performance.accuracy_score
                    ):
                        # Higher accuracy is better
                        score += model.performance.accuracy_score
                        reasons.append(
                            f"Accuracy: {model.performance.accuracy_score:.2f}"
                        )
                    elif (
                        metric in ["input_token_price", "output_token_price"]
                        and model.pricing
                    ):
                        # Lower price is better
                        price = getattr(model.pricing, metric)
                        if price:
                            normalized_score = 1.0 - min(
                                1.0, price / 0.01
                            )  # Normalize against $0.01 per 1K tokens
                            score += normalized_score
                            reasons.append(f"{metric}: ${price:.6f} per 1K tokens")

                # Normalize score based on number of factors
                total_factors = len(scenario["key_capabilities"]) + len(
                    scenario["key_metrics"]
                )
                if total_factors > 0:
                    score = score / total_factors

                model_scores.append(
                    {
                        "model_id": model.model_id,
                        "model_name": model.model_name,
                        "score": score,
                        "reasons": reasons,
                    }
                )

            # Sort models by score for this scenario
            model_scores.sort(key=lambda x: x["score"], reverse=True)

            # Determine best model for this scenario
            best_model = model_scores[0] if model_scores else None

            scenario_results.append(
                {
                    "scenario": scenario["name"],
                    "description": scenario["description"],
                    "model_scores": model_scores,
                    "best_model": best_model["model_id"] if best_model else None,
                    "best_model_name": best_model["model_name"] if best_model else None,
                }
            )

        return {"scenarios": scenario_results}

    def generate_recommendation_summary(
        self, models: List[BedrockModel]
    ) -> Dict[str, Any]:
        """
        Generate a summary of recommendations for different use cases.

        Args:
            models: List of models to compare

        Returns:
            Dictionary with recommendation summary data
        """
        # Define common use cases
        use_cases = [
            "text-generation",
            "code-generation",
            "question-answering",
            "summarization",
            "translation",
            "classification",
        ]

        # Generate recommendations for each use case
        recommendations = []

        for use_case in use_cases:
            # Create criteria for this use case
            criteria = {"use_case": {"primary": use_case}}

            # Score models for this use case
            scored_models = self._score_models(models, criteria)

            # Get top recommendation
            top_model = scored_models[0] if scored_models else None

            if top_model:
                recommendations.append(
                    {
                        "use_case": use_case,
                        "recommended_model": top_model["model_id"],
                        "recommended_model_name": top_model["model_name"],
                        "score": top_model["score"],
                        "reasoning": top_model["reasoning"][:2]
                        if len(top_model["reasoning"]) > 2
                        else top_model["reasoning"],
                    }
                )

        return {"use_case_recommendations": recommendations}
