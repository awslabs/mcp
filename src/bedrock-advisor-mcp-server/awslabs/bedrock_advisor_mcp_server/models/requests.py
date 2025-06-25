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

"""Request and response models for MCP tool interactions.

This module defines the Pydantic models used for validating and structuring
requests to the various MCP tools provided by the Bedrock Model Selector.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .bedrock import UseCaseType


class UseCase(BaseModel):
    """Use case specification for model recommendations."""

    primary: UseCaseType = Field(description="Primary use case for the model")
    secondary: Optional[List[UseCaseType]] = Field(
        None, description="Secondary use cases (optional)"
    )
    domain: Optional[str] = Field(
        None, description="Domain context (e.g., healthcare, finance)", max_length=100
    )
    complexity: Optional[str] = Field(
        None, description="Task complexity level", pattern="^(simple|moderate|complex)$"
    )


class PerformanceRequirements(BaseModel):
    """Performance requirements for model selection."""

    max_latency_ms: Optional[int] = Field(
        None, description="Maximum acceptable latency in milliseconds", gt=0, le=30000
    )
    min_throughput_tokens_per_second: Optional[int] = Field(
        None,
        description="Minimum required throughput in tokens per second",
        gt=0,
        le=10000,
    )
    accuracy_priority: Optional[str] = Field(
        None, description="Importance of accuracy", pattern="^(low|medium|high)$"
    )


class CostConstraints(BaseModel):
    """Cost constraints for model selection."""

    max_cost_per_request: Optional[float] = Field(
        None, description="Maximum cost per request in USD", gt=0.0, le=100.0
    )
    max_cost_per_token: Optional[float] = Field(
        None, description="Maximum cost per token in USD", gt=0.0, le=1.0
    )
    budget_priority: Optional[str] = Field(
        None,
        description="Importance of cost optimization",
        pattern="^(low|medium|high)$",
    )


class TechnicalRequirements(BaseModel):
    """Technical requirements for model selection."""

    min_context_length: Optional[int] = Field(
        None, description="Minimum required context length", gt=0, le=2000000
    )
    max_context_length: Optional[int] = Field(
        None, description="Maximum acceptable context length", gt=0, le=2000000
    )
    requires_streaming: Optional[bool] = Field(
        None, description="Whether streaming responses are required"
    )
    requires_customization: Optional[bool] = Field(
        None, description="Whether model customization is required"
    )
    requires_function_calling: Optional[bool] = Field(
        None, description="Whether function calling support is required"
    )
    requires_multimodal: Optional[bool] = Field(
        None, description="Whether multimodal capabilities are required"
    )

    @validator("max_context_length")
    def validate_context_length_range(cls, v, values):
        """Ensure max_context_length >= min_context_length."""
        if v is not None and "min_context_length" in values:
            min_length = values["min_context_length"]
            if min_length is not None and v < min_length:
                raise ValueError("max_context_length must be >= min_context_length")
        return v


class ModelRecommendationCriteria(BaseModel):
    """Complete criteria for model recommendations."""

    use_case: UseCase = Field(description="Use case specification")
    performance_requirements: Optional[PerformanceRequirements] = Field(
        None, description="Performance requirements"
    )
    cost_constraints: Optional[CostConstraints] = Field(
        None, description="Cost constraints"
    )
    technical_requirements: Optional[TechnicalRequirements] = Field(
        None, description="Technical requirements"
    )
    region_preference: Optional[List[str]] = Field(
        None, description="Preferred AWS regions", max_items=20
    )

    @validator("region_preference", each_item=True)
    def validate_region_format(cls, v):
        """Validate AWS region format."""
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v


class RecommendModelRequest(BaseModel):
    """Request for model recommendations."""

    use_case: UseCase = Field(description="Use case specification")
    performance_requirements: Optional[PerformanceRequirements] = Field(
        None, description="Performance requirements"
    )
    cost_constraints: Optional[CostConstraints] = Field(
        None, description="Cost constraints"
    )
    technical_requirements: Optional[TechnicalRequirements] = Field(
        None, description="Technical requirements"
    )
    region_preference: Optional[List[str]] = Field(
        None, description="Preferred AWS regions"
    )
    max_recommendations: int = Field(
        default=3,
        description="Maximum number of recommendations to return",
        ge=1,
        le=10,
    )


class CompareModelsRequest(BaseModel):
    """Request for model comparison."""

    model_ids: List[str] = Field(
        description="List of model IDs to compare", min_items=2, max_items=5
    )
    criteria: Optional[ModelRecommendationCriteria] = Field(
        None, description="Comparison criteria"
    )
    include_detailed_analysis: bool = Field(
        default=True, description="Include detailed scoring breakdown"
    )

    @validator("model_ids", each_item=True)
    def validate_model_id(cls, v):
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()


class GetModelInfoRequest(BaseModel):
    """Request for detailed model information."""

    model_id: str = Field(description="Model ID to get information for")
    include_availability: bool = Field(
        default=True, description="Include availability information"
    )
    include_pricing: bool = Field(
        default=True, description="Include pricing information"
    )
    include_performance: bool = Field(
        default=True, description="Include performance metrics"
    )

    @validator("model_id")
    def validate_model_id(cls, v):
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()


class CheckAvailabilityRequest(BaseModel):
    """Request for checking model availability."""

    model_ids: Optional[List[str]] = Field(
        None, description="Specific model IDs to check (optional)", max_items=50
    )
    regions: Optional[List[str]] = Field(
        None, description="Specific regions to check (optional)", max_items=20
    )
    include_deprecated: bool = Field(
        default=False, description="Include deprecated models"
    )

    @validator("model_ids", each_item=True)
    def validate_model_id(cls, v):
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()

    @validator("regions", each_item=True)
    def validate_region_format(cls, v):
        """Validate AWS region format."""
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v


class EstimateCostRequest(BaseModel):
    """Request for cost estimation."""

    model_id: str = Field(description="Model ID for cost estimation")
    usage: Dict[str, Any] = Field(description="Usage pattern specification")
    region: str = Field(default="us-east-1", description="AWS region for pricing")

    @validator("model_id")
    def validate_model_id(cls, v):
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()

    @validator("region")
    def validate_region_format(cls, v):
        """Validate AWS region format."""
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v

    @validator("usage")
    def validate_usage_structure(cls, v):
        """Validate usage dictionary structure."""
        required_fields = [
            "expected_requests_per_month",
            "average_input_tokens",
            "average_output_tokens",
        ]

        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required usage field: {field}")

            if not isinstance(v[field], (int, float)) or v[field] <= 0:
                raise ValueError(f"Usage field {field} must be a positive number")

        # Validate optional peak_requests_per_second
        if "peak_requests_per_second" in v:
            if (
                not isinstance(v["peak_requests_per_second"], (int, float))
                or v["peak_requests_per_second"] <= 0
            ):
                raise ValueError("peak_requests_per_second must be a positive number")

        return v


class ModelAvailabilityRequest(BaseModel):
    """Request for checking model availability across regions."""

    model_id: str = Field(description="Model ID to check availability for")
    regions: Optional[List[str]] = Field(
        None,
        description="Specific regions to check (optional, defaults to all Bedrock regions)",
        max_items=20,
    )

    @validator("model_id")
    def validate_model_id(cls, v):
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()

    @validator("regions", each_item=True)
    def validate_region_format(cls, v):
        """Validate AWS region format."""
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v


class RegionAvailabilityRequest(BaseModel):
    """Request for checking model availability in a specific region."""

    region: str = Field(description="AWS region to check availability in")
    model_ids: Optional[List[str]] = Field(
        None,
        description="Specific model IDs to check (optional, defaults to all models)",
        max_items=50,
    )

    @validator("region")
    def validate_region_format(cls, v):
        """Validate AWS region format."""
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v

    @validator("model_ids", each_item=True)
    def validate_model_id(cls, v):
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()


class RefreshModelsRequest(BaseModel):
    """Request for refreshing model data."""

    force_refresh: bool = Field(
        default=False, description="Force refresh even if cache is valid"
    )


class CostEstimationRequest(BaseModel):
    """Request for cost estimation."""

    model_id: str = Field(description="Model ID for cost estimation")
    usage: Dict[str, Any] = Field(description="Usage pattern specification")
    region: str = Field(default="us-east-1", description="AWS region for pricing")

    @validator("model_id")
    def validate_model_id(cls, v):
        """Validate model ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Model ID cannot be empty")
        return v.strip()

    @validator("region")
    def validate_region_format(cls, v):
        """Validate AWS region format."""
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v

    @validator("usage")
    def validate_usage_structure(cls, v):
        """Validate usage dictionary structure."""
        required_fields = [
            "expected_requests_per_month",
            "average_input_tokens",
            "average_output_tokens",
        ]

        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required usage field: {field}")

            if not isinstance(v[field], (int, float)) or v[field] <= 0:
                raise ValueError(f"Usage field {field} must be a positive number")

        # Validate optional peak_requests_per_second
        if "peak_requests_per_second" in v:
            if (
                not isinstance(v["peak_requests_per_second"], (int, float))
                or v["peak_requests_per_second"] <= 0
            ):
                raise ValueError("peak_requests_per_second must be a positive number")

        return v


class ListModelsRequest(BaseModel):
    """Request for listing models with filtering."""

    provider: Optional[str] = Field(None, description="Filter by provider name")
    region: Optional[str] = Field(None, description="Filter by AWS region")
    capabilities: Optional[Dict[str, Any]] = Field(
        None, description="Filter by model capabilities"
    )

    @validator("region")
    def validate_region_format(cls, v):
        """Validate AWS region format."""
        if v is None:
            return v
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", v):
            raise ValueError(f"Invalid AWS region format: {v}")
        return v
