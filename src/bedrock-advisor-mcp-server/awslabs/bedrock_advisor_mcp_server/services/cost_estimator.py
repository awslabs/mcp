"""
Cost estimation service for Bedrock models.

This module provides comprehensive cost estimation functionality for
Bedrock foundation models, including usage-based calculations, optimization
recommendations, and cost comparison across different usage patterns.
"""

from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict

from ..models.bedrock import BedrockModel
from ..utils.logging import get_logger

logger = get_logger(__name__)


class UsagePattern(TypedDict):
    """Type definition for usage pattern."""

    name: str
    requests_per_month: int
    avg_input_tokens: int
    avg_output_tokens: int
    peak_requests_per_second: Optional[int]


class CostBreakdown(TypedDict):
    """Type definition for cost breakdown."""

    input_cost_per_request: float
    output_cost_per_request: float
    total_cost_per_request: float
    monthly_input_cost: float
    monthly_output_cost: float
    monthly_total_cost: float


class Optimization(TypedDict):
    """Type definition for optimization recommendation."""

    type: str
    description: str
    potential_savings: str
    implementation_complexity: str


class CostEstimator:
    """
    Service for estimating costs of using Bedrock foundation models.

    This service provides comprehensive cost estimation functionality,
    including detailed breakdowns, optimization recommendations, and
    cost projections for different usage patterns and scenarios.
    """

    def __init__(self):
        """Initialize the cost estimator."""
        # Define common usage patterns for comparison
        self.common_patterns = [
            {
                "name": "Low volume",
                "requests_per_month": 1000,  # ~33 per day
                "avg_input_tokens": 1000,
                "avg_output_tokens": 500,
            },
            {
                "name": "Medium volume",
                "requests_per_month": 10000,  # ~333 per day
                "avg_input_tokens": 2000,
                "avg_output_tokens": 1000,
            },
            {
                "name": "High volume",
                "requests_per_month": 100000,  # ~3333 per day
                "avg_input_tokens": 3000,
                "avg_output_tokens": 1500,
            },
            {
                "name": "Enterprise volume",
                "requests_per_month": 1000000,  # ~33333 per day
                "avg_input_tokens": 4000,
                "avg_output_tokens": 2000,
            },
        ]

    def estimate_cost(
        self,
        model: BedrockModel,
        usage: Dict[str, Any],
        include_optimizations: bool = True,
        include_projections: bool = True,
    ) -> Dict[str, Any]:
        """
        Estimate costs for using a specific model based on usage patterns.

        This method calculates detailed cost estimates for the specified model
        based on the provided usage parameters. It includes breakdowns of input
        and output costs, monthly projections, and optimization recommendations.

        Args:
            model: The Bedrock model to estimate costs for
            usage: Usage parameters including request volume and token counts
            include_optimizations: Whether to include optimization recommendations
            include_projections: Whether to include cost projections for different scenarios

        Returns:
            Dict containing cost estimates, breakdowns, and recommendations
        """
        if not model.pricing:
            return {
                "model_id": model.model_id,
                "model_name": model.model_name,
                "error": "No pricing information available for this model",
                "estimated_cost": None,
            }

        # Extract usage parameters
        requests_per_month = usage.get("expected_requests_per_month", 0)
        avg_input_tokens = usage.get("average_input_tokens", 0)
        avg_output_tokens = usage.get("average_output_tokens", 0)
        peak_requests_per_second = usage.get("peak_requests_per_second")

        # Calculate costs
        cost_breakdown = self._calculate_cost_breakdown(
            model, requests_per_month, avg_input_tokens, avg_output_tokens
        )

        # Generate result
        result = {
            "model_id": model.model_id,
            "model_name": model.model_name,
            "pricing": {
                "input_token_price": f"${model.pricing.input_token_price:.6f} per 1K tokens",
                "output_token_price": f"${model.pricing.output_token_price:.6f} per 1K tokens",
                "currency": model.pricing.currency,
                "last_updated": model.pricing.last_updated,
            },
            "usage": {
                "requests_per_month": requests_per_month,
                "input_tokens_per_request": avg_input_tokens,
                "output_tokens_per_request": avg_output_tokens,
                "total_input_tokens": requests_per_month * avg_input_tokens,
                "total_output_tokens": requests_per_month * avg_output_tokens,
            },
            "cost_breakdown": cost_breakdown,
            "estimated_cost": {
                "per_request": f"${cost_breakdown['total_cost_per_request']:.4f}",
                "per_month": f"${cost_breakdown['monthly_total_cost']:.2f}",
            },
        }

        # Add peak throughput analysis if provided
        if peak_requests_per_second:
            result["throughput_analysis"] = self._analyze_throughput(
                model, peak_requests_per_second, avg_input_tokens, avg_output_tokens
            )

        # Add optimization recommendations if requested
        if include_optimizations:
            result["optimizations"] = self._generate_optimizations(
                model,
                requests_per_month,
                avg_input_tokens,
                avg_output_tokens,
                cost_breakdown,
            )

        # Add cost projections if requested
        if include_projections:
            result["projections"] = self._generate_projections(
                model, avg_input_tokens, avg_output_tokens
            )

        # Add cost comparison with other models
        result["cost_efficiency"] = self._evaluate_cost_efficiency(model)

        return result

    def _calculate_cost_breakdown(
        self,
        model: BedrockModel,
        requests_per_month: int,
        avg_input_tokens: int,
        avg_output_tokens: int,
    ) -> CostBreakdown:
        """
        Calculate detailed cost breakdown.

        Args:
            model: The Bedrock model
            requests_per_month: Number of requests per month
            avg_input_tokens: Average input tokens per request
            avg_output_tokens: Average output tokens per request

        Returns:
            CostBreakdown with detailed cost information
        """
        if not model.pricing:
            return {
                "input_cost_per_request": 0,
                "output_cost_per_request": 0,
                "total_cost_per_request": 0,
                "monthly_input_cost": 0,
                "monthly_output_cost": 0,
                "monthly_total_cost": 0,
            }

        # Calculate per-request costs
        input_cost_per_request = (
            avg_input_tokens / 1000
        ) * model.pricing.input_token_price
        output_cost_per_request = (
            avg_output_tokens / 1000
        ) * model.pricing.output_token_price
        total_cost_per_request = input_cost_per_request + output_cost_per_request

        # Calculate monthly costs
        monthly_input_cost = input_cost_per_request * requests_per_month
        monthly_output_cost = output_cost_per_request * requests_per_month
        monthly_total_cost = total_cost_per_request * requests_per_month

        return {
            "input_cost_per_request": input_cost_per_request,
            "output_cost_per_request": output_cost_per_request,
            "total_cost_per_request": total_cost_per_request,
            "monthly_input_cost": monthly_input_cost,
            "monthly_output_cost": monthly_output_cost,
            "monthly_total_cost": monthly_total_cost,
        }

    def _analyze_throughput(
        self,
        model: BedrockModel,
        peak_requests_per_second: int,
        avg_input_tokens: int,
        avg_output_tokens: int,
    ) -> Dict[str, Any]:
        """
        Analyze throughput requirements and provide recommendations.

        Args:
            model: The Bedrock model
            peak_requests_per_second: Peak requests per second
            avg_input_tokens: Average input tokens per request
            avg_output_tokens: Average output tokens per request

        Returns:
            Dict with throughput analysis and recommendations
        """
        # Estimate token throughput requirements
        input_tokens_per_second = peak_requests_per_second * avg_input_tokens
        output_tokens_per_second = peak_requests_per_second * avg_output_tokens
        total_tokens_per_second = input_tokens_per_second + output_tokens_per_second

        # Estimate model throughput capacity (if available)
        model_throughput = (
            model.performance.throughput_tokens_per_second
            if model.performance
            else None
        )

        analysis = {
            "peak_requests_per_second": peak_requests_per_second,
            "input_tokens_per_second": input_tokens_per_second,
            "output_tokens_per_second": output_tokens_per_second,
            "total_tokens_per_second": total_tokens_per_second,
        }

        # Add capacity analysis if model throughput is available
        if model_throughput:
            capacity_percentage = (total_tokens_per_second / model_throughput) * 100
            analysis["model_throughput_capacity"] = model_throughput
            analysis["capacity_utilization_percentage"] = capacity_percentage

            # Add recommendations based on capacity
            if capacity_percentage > 80:
                analysis["throughput_recommendation"] = {
                    "message": "High throughput requirements detected",
                    "suggestions": [
                        "Consider implementing request queuing",
                        "Implement client-side rate limiting",
                        "Explore provisioned throughput options if available",
                    ],
                }
            elif capacity_percentage > 50:
                analysis["throughput_recommendation"] = {
                    "message": "Moderate throughput requirements",
                    "suggestions": [
                        "Monitor throughput during peak usage periods",
                        "Implement basic rate limiting as a precaution",
                    ],
                }
            else:
                analysis["throughput_recommendation"] = {
                    "message": "Low throughput requirements",
                    "suggestions": [
                        "Current throughput requirements are well within model capacity"
                    ],
                }

        return analysis

    def _generate_optimizations(
        self,
        model: BedrockModel,
        requests_per_month: int,
        avg_input_tokens: int,
        avg_output_tokens: int,
        cost_breakdown: CostBreakdown,
    ) -> List[Optimization]:
        """
        Generate cost optimization recommendations.

        Args:
            model: The Bedrock model
            requests_per_month: Number of requests per month
            avg_input_tokens: Average input tokens per request
            avg_output_tokens: Average output tokens per request
            cost_breakdown: Cost breakdown information

        Returns:
            List of optimization recommendations
        """
        optimizations = []

        # Check if input tokens can be reduced
        if avg_input_tokens > 1000:
            # Calculate potential savings with 20% reduction
            input_reduction = 0.2
            potential_savings = (
                (avg_input_tokens * input_reduction / 1000)
                * model.pricing.input_token_price
                * requests_per_month
            )

            optimizations.append(
                {
                    "type": "input_reduction",
                    "description": "Reduce input token usage by optimizing prompts",
                    "potential_savings": f"${potential_savings:.2f} per month (assuming {input_reduction * 100}% reduction)",
                    "implementation_complexity": "Medium",
                }
            )

            # Add specific techniques for input reduction
            optimizations.append(
                {
                    "type": "input_reduction_techniques",
                    "description": "Specific techniques for reducing input tokens",
                    "potential_savings": "Varies based on implementation",
                    "implementation_complexity": "Medium",
                    "techniques": [
                        "Use more concise prompts by removing unnecessary context",
                        "Implement prompt compression techniques",
                        "Use embeddings to retrieve only relevant context",
                        "Implement chunking for large documents",
                    ],
                }
            )

        # Check if caching can be implemented
        if requests_per_month > 1000:
            # Calculate potential savings with 30% cache hit rate
            cache_hit_rate = 0.3
            potential_savings = cost_breakdown["monthly_total_cost"] * cache_hit_rate

            optimizations.append(
                {
                    "type": "caching",
                    "description": "Implement response caching for common queries",
                    "potential_savings": f"${potential_savings:.2f} per month (assuming {cache_hit_rate * 100}% cache hit rate)",
                    "implementation_complexity": "Medium",
                }
            )

            # Add specific techniques for caching
            optimizations.append(
                {
                    "type": "caching_techniques",
                    "description": "Specific techniques for implementing caching",
                    "potential_savings": "Varies based on implementation",
                    "implementation_complexity": "Medium to High",
                    "techniques": [
                        "Implement semantic caching based on embedding similarity",
                        "Use deterministic prompts for better cache hit rates",
                        "Consider time-based cache invalidation for dynamic content",
                        "Use distributed caching for high-volume applications",
                    ],
                }
            )

        # Check if batching can be implemented
        if requests_per_month > 10000:
            optimizations.append(
                {
                    "type": "batching",
                    "description": "Implement request batching to reduce overhead",
                    "potential_savings": "Improved throughput and reduced latency",
                    "implementation_complexity": "High",
                }
            )

        # Check if a different model might be more cost-effective
        if (
            model.pricing.input_token_price > 0.001
            or model.pricing.output_token_price > 0.002
        ):
            optimizations.append(
                {
                    "type": "model_alternative",
                    "description": "Consider using a smaller, more cost-effective model for non-critical tasks",
                    "potential_savings": "Up to 50% cost reduction for suitable workloads",
                    "implementation_complexity": "Medium",
                    "suggested_alternatives": [
                        "For text generation: Consider Claude Instant or Titan Text Express",
                        "For embeddings: Consider Titan Embeddings",
                        "For code: Consider CodeLlama or Mistral Code",
                    ],
                }
            )

        # Add RAG optimization if applicable
        if avg_input_tokens > 5000:
            optimizations.append(
                {
                    "type": "rag_optimization",
                    "description": "Optimize RAG implementation to reduce token usage",
                    "potential_savings": "15-30% reduction in input token usage",
                    "implementation_complexity": "High",
                    "techniques": [
                        "Implement better chunk selection algorithms",
                        "Use hybrid search (sparse + dense vectors)",
                        "Implement re-ranking of retrieved chunks",
                        "Use query-focused summarization of retrieved content",
                    ],
                }
            )

        return optimizations

    def _generate_projections(
        self, model: BedrockModel, avg_input_tokens: int, avg_output_tokens: int
    ) -> Dict[str, Any]:
        """
        Generate cost projections for different usage patterns.

        Args:
            model: The Bedrock model
            avg_input_tokens: Average input tokens per request
            avg_output_tokens: Average output tokens per request

        Returns:
            Dict with cost projections for different scenarios
        """
        if not model.pricing:
            return {"error": "No pricing information available"}

        projections = {
            "usage_patterns": [],
            "scaling_factors": {
                "2x": "Doubling current usage",
                "5x": "5x increase in usage",
                "10x": "10x increase in usage",
            },
        }

        # Generate projections for common patterns
        for pattern in self.common_patterns:
            cost_breakdown = self._calculate_cost_breakdown(
                model,
                pattern["requests_per_month"],
                avg_input_tokens,
                avg_output_tokens,
            )

            projections["usage_patterns"].append(
                {
                    "name": pattern["name"],
                    "requests_per_month": pattern["requests_per_month"],
                    "monthly_cost": cost_breakdown["monthly_total_cost"],
                    "formatted_cost": f"${cost_breakdown['monthly_total_cost']:.2f}",
                }
            )

        return projections

    def _evaluate_cost_efficiency(self, model: BedrockModel) -> Dict[str, Any]:
        """
        Evaluate the cost efficiency of the model compared to alternatives.

        Args:
            model: The Bedrock model

        Returns:
            Dict with cost efficiency evaluation
        """
        if not model.pricing:
            return {"error": "No pricing information available"}

        # Define benchmark models for comparison
        benchmarks = [
            {"name": "Claude 3.5 Sonnet", "input_price": 0.003, "output_price": 0.015},
            {
                "name": "Claude 3.5 Haiku",
                "input_price": 0.00025,
                "output_price": 0.00125,
            },
            {
                "name": "Titan Text Express",
                "input_price": 0.0002,
                "output_price": 0.0006,
            },
        ]

        # Calculate average token price
        avg_price = (
            model.pricing.input_token_price + model.pricing.output_token_price
        ) / 2

        # Compare with benchmarks
        comparisons = []
        for benchmark in benchmarks:
            benchmark_avg = (benchmark["input_price"] + benchmark["output_price"]) / 2
            price_ratio = avg_price / benchmark_avg

            comparisons.append(
                {
                    "benchmark_model": benchmark["name"],
                    "price_ratio": price_ratio,
                    "comparison": (
                        f"{price_ratio:.2f}x "
                        + ("more expensive than" if price_ratio > 1 else "cheaper than")
                    ),
                }
            )

        # Determine overall cost efficiency
        if avg_price < 0.001:
            efficiency = "Very High"
        elif avg_price < 0.005:
            efficiency = "High"
        elif avg_price < 0.01:
            efficiency = "Medium"
        else:
            efficiency = "Low"

        return {
            "average_token_price": avg_price,
            "cost_efficiency_rating": efficiency,
            "benchmark_comparisons": comparisons,
        }

    def compare_costs(
        self, models: List[BedrockModel], usage: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare costs across multiple models for the same usage pattern.

        This method calculates and compares costs for multiple models based on
        the same usage parameters, helping users identify the most cost-effective
        option for their specific needs.

        Args:
            models: List of models to compare
            usage: Usage parameters including request volume and token counts

        Returns:
            Dict with cost comparison results
        """
        # Extract usage parameters
        requests_per_month = usage.get("expected_requests_per_month", 0)
        avg_input_tokens = usage.get("average_input_tokens", 0)
        avg_output_tokens = usage.get("average_output_tokens", 0)

        # Calculate costs for each model
        model_costs = []
        for model in models:
            if not model.pricing:
                continue

            cost_breakdown = self._calculate_cost_breakdown(
                model, requests_per_month, avg_input_tokens, avg_output_tokens
            )

            model_costs.append(
                {
                    "model_id": model.model_id,
                    "model_name": model.model_name,
                    "provider": model.provider_name,
                    "input_price": model.pricing.input_token_price,
                    "output_price": model.pricing.output_token_price,
                    "cost_per_request": cost_breakdown["total_cost_per_request"],
                    "monthly_cost": cost_breakdown["monthly_total_cost"],
                    "formatted_monthly_cost": f"${cost_breakdown['monthly_total_cost']:.2f}",
                }
            )

        # Sort by monthly cost
        model_costs.sort(key=lambda x: x["monthly_cost"])

        # Determine most cost-effective model
        most_cost_effective = model_costs[0] if model_costs else None

        # Calculate potential savings compared to most expensive option
        if len(model_costs) > 1:
            most_expensive = model_costs[-1]
            potential_savings = (
                most_expensive["monthly_cost"] - most_cost_effective["monthly_cost"]
            )
            savings_percentage = (
                potential_savings / most_expensive["monthly_cost"]
            ) * 100
        else:
            potential_savings = 0
            savings_percentage = 0

        return {
            "usage": {
                "requests_per_month": requests_per_month,
                "avg_input_tokens": avg_input_tokens,
                "avg_output_tokens": avg_output_tokens,
            },
            "model_costs": model_costs,
            "most_cost_effective": most_cost_effective,
            "potential_savings": {
                "amount": potential_savings,
                "formatted": f"${potential_savings:.2f}",
                "percentage": f"{savings_percentage:.1f}%",
            },
        }
