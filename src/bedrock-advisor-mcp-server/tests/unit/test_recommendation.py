"""
Unit tests for the recommendation engine.

This module tests the recommendation engine's ability to score and recommend
models based on various criteria.
"""

from datetime import datetime

import pytest

from awslabs.bedrock_advisor_mcp_server.models.bedrock import (
    BedrockModel,
    ModelAvailability,
    ModelCapabilities,
    ModelPerformance,
    ModelPricing,
    ModelStatus,
    UseCaseType,
)
from awslabs.bedrock_advisor_mcp_server.services.recommendation import RecommendationEngine


@pytest.fixture
def recommendation_engine():
    """Create a recommendation engine for testing."""
    return RecommendationEngine()


@pytest.fixture
def test_models():
    """Create a set of test models with different characteristics."""
    # Create a date string for testing
    today = datetime.now().strftime('%Y-%m-%d')

    # Model 1: General purpose model with good all-around capabilities
    model1 = BedrockModel(
        model_id="test.general-purpose-v1:0",
        model_name="Test General Purpose",
        provider_name="TestProvider",
        input_modalities=["TEXT"],
        output_modalities=["TEXT"],
        response_streaming_supported=True,
        customizations_supported=[],
        inference_types_supported=["ON_DEMAND"],
        max_tokens=4096,
        context_length=32000,
        pricing=ModelPricing(
            input_token_price=0.001,
            output_token_price=0.002,
            currency="USD",
            unit="per 1K tokens",
            last_updated=today
        ),
        capabilities=ModelCapabilities(
            text_generation=True,
            code_generation=True,
            summarization=True,
            question_answering=True,
            translation=True,
            classification=True,
            embedding=False,
            multimodal=False,
            function_calling=True,
            reasoning=True,
            mathematics=True,
            creative=True
        ),
        performance=ModelPerformance(
            latency_ms=1000,
            throughput_tokens_per_second=100,
            accuracy_score=0.85
        ),
        availability=ModelAvailability(
            regions=["us-east-1", "us-west-2", "eu-west-1"],
            status=ModelStatus.ACTIVE,
            last_checked=today
        )
    )

    # Model 2: Specialized code generation model
    model2 = BedrockModel(
        model_id="test.code-expert-v1:0",
        model_name="Test Code Expert",
        provider_name="TestProvider",
        input_modalities=["TEXT"],
        output_modalities=["TEXT"],
        response_streaming_supported=True,
        customizations_supported=[],
        inference_types_supported=["ON_DEMAND"],
        max_tokens=8192,
        context_length=64000,
        pricing=ModelPricing(
            input_token_price=0.002,
            output_token_price=0.004,
            currency="USD",
            unit="per 1K tokens",
            last_updated=today
        ),
        capabilities=ModelCapabilities(
            text_generation=True,
            code_generation=True,
            summarization=False,
            question_answering=True,
            translation=False,
            classification=False,
            embedding=False,
            multimodal=False,
            function_calling=True,
            reasoning=True,
            mathematics=True,
            creative=False
        ),
        performance=ModelPerformance(
            latency_ms=1500,
            throughput_tokens_per_second=80,
            accuracy_score=0.92
        ),
        availability=ModelAvailability(
            regions=["us-east-1", "us-west-2"],
            status=ModelStatus.ACTIVE,
            last_checked=today
        )
    )

    # Model 3: Fast, low-cost model
    model3 = BedrockModel(
        model_id="test.fast-lite-v1:0",
        model_name="Test Fast Lite",
        provider_name="TestProvider",
        input_modalities=["TEXT"],
        output_modalities=["TEXT"],
        response_streaming_supported=True,
        customizations_supported=[],
        inference_types_supported=["ON_DEMAND"],
        max_tokens=2048,
        context_length=16000,
        pricing=ModelPricing(
            input_token_price=0.0005,
            output_token_price=0.0005,
            currency="USD",
            unit="per 1K tokens",
            last_updated=today
        ),
        capabilities=ModelCapabilities(
            text_generation=True,
            code_generation=False,
            summarization=True,
            question_answering=True,
            translation=True,
            classification=True,
            embedding=False,
            multimodal=False,
            function_calling=False,
            reasoning=True,
            mathematics=False,
            creative=True
        ),
        performance=ModelPerformance(
            latency_ms=500,
            throughput_tokens_per_second=150,
            accuracy_score=0.75
        ),
        availability=ModelAvailability(
            regions=["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
            status=ModelStatus.ACTIVE,
            last_checked=today
        )
    )

    # Model 4: Multimodal model
    model4 = BedrockModel(
        model_id="test.multimodal-v1:0",
        model_name="Test Multimodal",
        provider_name="TestProvider",
        input_modalities=["TEXT", "IMAGE"],
        output_modalities=["TEXT"],
        response_streaming_supported=True,
        customizations_supported=[],
        inference_types_supported=["ON_DEMAND"],
        max_tokens=4096,
        context_length=32000,
        pricing=ModelPricing(
            input_token_price=0.003,
            output_token_price=0.006,
            currency="USD",
            unit="per 1K tokens",
            last_updated=today
        ),
        capabilities=ModelCapabilities(
            text_generation=True,
            code_generation=False,
            summarization=True,
            question_answering=True,
            translation=True,
            classification=True,
            embedding=False,
            multimodal=True,
            function_calling=True,
            reasoning=True,
            mathematics=False,
            creative=True
        ),
        performance=ModelPerformance(
            latency_ms=2000,
            throughput_tokens_per_second=70,
            accuracy_score=0.88
        ),
        availability=ModelAvailability(
            regions=["us-east-1", "us-west-2"],
            status=ModelStatus.ACTIVE,
            last_checked=today
        )
    )

    return [model1, model2, model3, model4]


def test_recommend_models_text_generation(recommendation_engine, test_models):
    """Test model recommendations for text generation use case."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.TEXT_GENERATION
        }
    }

    recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=2
    )

    # Verify we get the expected number of recommendations
    assert len(recommendations) == 2

    # Verify recommendations are sorted by score (highest first)
    assert recommendations[0]["score"] >= recommendations[1]["score"]

    # Verify the model with best text generation capabilities is recommended
    assert recommendations[0]["model"]["model_id"] in [
        "test.general-purpose-v1:0",
        "test.fast-lite-v1:0"
    ]

    # Verify reasoning is provided
    assert len(recommendations[0]["reasoning"]) > 0
    assert len(recommendations[0]["pros"]) > 0


def test_recommend_models_code_generation(recommendation_engine, test_models):
    """Test model recommendations for code generation use case."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.CODE_GENERATION
        }
    }

    recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=2
    )

    # Verify the code-specialized model is recommended first
    assert recommendations[0]["model"]["model_id"] == "test.code-expert-v1:0"

    # Verify reasoning mentions code generation
    code_mentioned = any("code" in reason.lower() for reason in recommendations[0]["reasoning"])
    assert code_mentioned


def test_recommend_models_multimodal(recommendation_engine, test_models):
    """Test model recommendations for multimodal use case."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.MULTIMODAL
        }
    }

    recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=2
    )

    # Verify the multimodal model is recommended first
    assert recommendations[0]["model"]["model_id"] == "test.multimodal-v1:0"


def test_recommend_models_with_performance_requirements(recommendation_engine, test_models):
    """Test model recommendations with performance requirements."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.TEXT_GENERATION
        },
        "performance_requirements": {
            "max_latency_ms": 600,
            "min_throughput_tokens_per_second": 120
        }
    }

    recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=2
    )

    # Verify the fast model is recommended first
    assert recommendations[0]["model"]["model_id"] == "test.fast-lite-v1:0"

    # Verify reasoning mentions performance
    performance_mentioned = any(
        "latency" in reason.lower() or "throughput" in reason.lower()
        for reason in recommendations[0]["reasoning"]
    )
    assert performance_mentioned


def test_recommend_models_with_cost_constraints(recommendation_engine, test_models):
    """Test model recommendations with cost constraints."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.TEXT_GENERATION
        },
        "cost_constraints": {
            "max_cost_per_token": 0.001,
            "budget_priority": "high"
        }
    }

    recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=2
    )

    # Verify the low-cost model is recommended first
    assert recommendations[0]["model"]["model_id"] == "test.fast-lite-v1:0"

    # Verify reasoning mentions cost
    cost_mentioned = any(
        "cost" in reason.lower() or "budget" in reason.lower() or "price" in reason.lower()
        for reason in recommendations[0]["reasoning"]
    )
    assert cost_mentioned


def test_recommend_models_with_region_preference(recommendation_engine, test_models):
    """Test model recommendations with region preference."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.TEXT_GENERATION
        },
        "region_preference": ["ap-southeast-1"]
    }

    recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=4
    )

    # Verify the model available in ap-southeast-1 is recommended first
    assert recommendations[0]["model"]["model_id"] == "test.fast-lite-v1:0"

    # Verify reasoning mentions region
    region_mentioned = any(
        "region" in reason.lower() or "ap-southeast-1" in reason.lower()
        for reason in recommendations[0]["reasoning"]
    )
    assert region_mentioned


def test_recommend_models_with_technical_requirements(recommendation_engine, test_models):
    """Test model recommendations with technical requirements."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.TEXT_GENERATION
        },
        "technical_requirements": {
            "requires_function_calling": True,
            "min_context_length": 40000
        }
    }

    recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=2
    )

    # Verify a model with function calling and sufficient context length is recommended
    assert recommendations[0]["model"]["model_id"] == "test.code-expert-v1:0"

    # Verify reasoning mentions technical requirements
    tech_mentioned = any(
        "function" in reason.lower() or "context" in reason.lower()
        for reason in recommendations[0]["reasoning"]
    )
    assert tech_mentioned


def test_score_model(recommendation_engine, test_models):
    """Test the model scoring function directly."""
    model = test_models[0]  # General purpose model
    criteria = {
        "use_case": {
            "primary": UseCaseType.TEXT_GENERATION
        }
    }

    score, reasoning, pros, cons = recommendation_engine._score_model(
        model, criteria, recommendation_engine.default_weights
    )

    # Verify score is between 0 and 1
    assert 0 <= score <= 1

    # Verify reasoning, pros, and cons are provided
    assert len(reasoning) > 0
    assert len(pros) > 0

    # Test with different criteria
    criteria = {
        "use_case": {
            "primary": UseCaseType.EMBEDDING
        }
    }

    score2, reasoning2, pros2, cons2 = recommendation_engine._score_model(
        model, criteria, recommendation_engine.default_weights
    )

    # Score should be lower for embedding use case since this model doesn't support it
    assert score2 < score


def test_custom_weights(recommendation_engine, test_models):
    """Test recommendations with custom weights."""
    criteria = {
        "use_case": {
            "primary": UseCaseType.TEXT_GENERATION
        }
    }

    # Default weights
    default_recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=4
    )

    # Custom weights prioritizing cost
    custom_weights = {
        "capability_match": 0.2,
        "performance": 0.1,
        "cost": 0.5,  # Higher weight on cost
        "availability": 0.1,
        "reliability": 0.1
    }

    custom_recommendations = recommendation_engine.recommend_models(
        models=test_models,
        criteria=criteria,
        max_recommendations=4,
        custom_weights=custom_weights
    )

    # With cost prioritized, the cheapest model should rank higher
    default_order = [rec["model"]["model_id"] for rec in default_recommendations]
    custom_order = [rec["model"]["model_id"] for rec in custom_recommendations]

    # Find the position of the cheapest model in both rankings
    cheapest_model_id = "test.fast-lite-v1:0"
    default_position = default_order.index(cheapest_model_id)
    custom_position = custom_order.index(cheapest_model_id)

    # The cheapest model should rank higher (lower index) with custom weights
    assert custom_position <= default_position
