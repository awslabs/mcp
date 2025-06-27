# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Core data models for Amazon Bedrock model information and selection.

This module defines the fundamental data structures used throughout the
Bedrock Model Selector MCP server for representing model information,
capabilities, performance metrics, and recommendations.
"""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class UseCaseType(str, Enum):
    """Enumeration of supported use case types."""

    TEXT_GENERATION = "text-generation"
    CODE_GENERATION = "code-generation"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "question-answering"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    CREATIVE_WRITING = "creative-writing"
    REASONING = "reasoning"
    MATHEMATICS = "mathematics"
    MULTIMODAL = "multimodal"


class ModelStatus(str, Enum):
    """Model availability status."""

    ACTIVE = "ACTIVE"
    LEGACY = "LEGACY"
    DEPRECATED = "DEPRECATED"


class ModelCapabilities(BaseModel):
    """Model capability matrix defining what each model can do."""

    text_generation: bool = Field(description="Can generate human-like text content")
    code_generation: bool = Field(description="Can generate and understand code")
    summarization: bool = Field(description="Can summarize long text content")
    question_answering: bool = Field(
        description="Can answer questions based on context"
    )
    translation: bool = Field(description="Can translate between languages")
    classification: bool = Field(description="Can classify text into categories")
    embedding: bool = Field(description="Can generate text embeddings")
    multimodal: bool = Field(description="Can process text and images")
    function_calling: bool = Field(description="Supports function/tool calling")
    reasoning: bool = Field(description="Can perform logical reasoning")
    mathematics: bool = Field(description="Can solve mathematical problems")
    creative: bool = Field(description="Can perform creative writing tasks")


class ModelPerformance(BaseModel):
    """Model performance characteristics and benchmarks."""

    latency_ms: int = Field(
        description="Average response latency in milliseconds", gt=0
    )
    throughput_tokens_per_second: int = Field(
        description="Maximum tokens processed per second", gt=0
    )
    accuracy_score: Optional[float] = Field(
        None, description="Overall accuracy score (0.0-1.0)", ge=0.0, le=1.0
    )
    benchmark_scores: Optional[Dict[str, float]] = Field(
        None, description="Benchmark test scores (e.g., MMLU, HumanEval)"
    )


class ModelPricing(BaseModel):
    """Model pricing information."""

    input_token_price: float = Field(
        description="Price per 1K input tokens in USD", ge=0.0
    )
    output_token_price: float = Field(
        description="Price per 1K output tokens in USD", ge=0.0
    )
    currency: str = Field(default="USD", description="Currency for pricing")
    unit: str = Field(default="per 1K tokens", description="Pricing unit description")
    last_updated: str = Field(description="Last price update date (ISO format)")


class ModelAvailability(BaseModel):
    """Model availability across AWS regions."""

    regions: List[str] = Field(
        description="List of AWS regions where model is available"
    )
    status: ModelStatus = Field(description="Current model status")
    last_checked: str = Field(description="Last availability check date (ISO format)")


class BedrockModel(BaseModel):
    """Complete Bedrock model definition with all metadata."""

    model_id: str = Field(description="Unique model identifier")
    model_name: str = Field(description="Human-readable model name")
    provider_name: str = Field(description="Model provider (e.g., Anthropic, Amazon)")
    model_arn: Optional[str] = Field(None, description="AWS ARN for the model")
    input_modalities: List[str] = Field(
        description="Supported input types (TEXT, IMAGE, etc.)"
    )
    output_modalities: List[str] = Field(
        description="Supported output types (TEXT, EMBEDDING, etc.)"
    )
    response_streaming_supported: bool = Field(
        description="Whether model supports streaming responses"
    )
    customizations_supported: List[str] = Field(
        description="Supported customization types (FINE_TUNING, etc.)"
    )
    inference_types_supported: List[str] = Field(
        description="Supported inference types (ON_DEMAND, PROVISIONED)"
    )
    max_tokens: Optional[int] = Field(
        None, description="Maximum output tokens per request", gt=0
    )
    context_length: Optional[int] = Field(
        None, description="Maximum context window size", gt=0
    )
    pricing: Optional[ModelPricing] = Field(None, description="Pricing information")
    capabilities: ModelCapabilities = Field(description="Model capabilities matrix")
    performance: ModelPerformance = Field(description="Performance characteristics")
    availability: ModelAvailability = Field(
        description="Regional availability information"
    )

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()


class CostEstimate(BaseModel):
    """Cost estimation for model usage."""

    cost_per_request: float = Field(
        description="Estimated cost per request in USD", ge=0.0
    )
    cost_per_1k_tokens: float = Field(
        description="Average cost per 1K tokens in USD", ge=0.0
    )
    monthly_cost_estimate: float = Field(
        description="Estimated monthly cost in USD", ge=0.0
    )
    assumptions: List[str] = Field(
        description="List of assumptions used in cost calculation"
    )


class ModelUsageEstimate(BaseModel):
    """Usage pattern estimate for cost calculations."""

    expected_requests_per_month: int = Field(
        description="Expected number of requests per month", gt=0
    )
    average_input_tokens: int = Field(
        description="Average input tokens per request", gt=0
    )
    average_output_tokens: int = Field(
        description="Average output tokens per request", gt=0
    )
    peak_requests_per_second: Optional[int] = Field(
        None, description="Peak requests per second", gt=0
    )


class ModelRecommendation(BaseModel):
    """Model recommendation with scoring and analysis."""

    model: BedrockModel = Field(description="The recommended model")
    score: float = Field(description="Recommendation score (0.0-1.0)", ge=0.0, le=1.0)
    reasoning: List[str] = Field(
        description="Explanation of why this model was recommended"
    )
    pros: List[str] = Field(description="Advantages of this model for the use case")
    cons: List[str] = Field(description="Potential limitations or drawbacks")
    estimated_cost: CostEstimate = Field(description="Cost estimate for typical usage")


class ModelComparison(BaseModel):
    """Comparison results between multiple models."""

    models: List[BedrockModel] = Field(description="Models being compared")
    comparison_results: List[Dict[str, Union[str, float, int, List[str]]]] = Field(
        description="Detailed comparison results"
    )
    winner: str = Field(description="Model ID of the top recommendation")
    summary: Dict[str, Union[str, int, float]] = Field(
        description="Summary of comparison results"
    )


class RegionAvailability(BaseModel):
    """Model availability information for a specific region."""

    region: str = Field(description="AWS region identifier")
    available_models: List[str] = Field(
        description="List of model IDs available in this region"
    )
    total_models: int = Field(description="Total number of available models", ge=0)
    last_checked: str = Field(description="Last check timestamp (ISO format)")
