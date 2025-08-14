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
"""Pydantic models for cell-based architecture concepts."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CellArchitectureQuery(BaseModel):
    """Query model for cell-based architecture concepts following whitepaper structure."""
    
    concept: str = Field(
        ..., 
        description="The cell-based architecture concept to query"
    )
    detail_level: Literal["beginner", "intermediate", "expert"] = Field(
        default="intermediate",
        description="Experience level: beginner (new to cell-based architecture), intermediate (some experience), expert (advanced implementation)"
    )
    whitepaper_section: Optional[Literal[
        "introduction", "shared_responsibility", "what_is_cell_based", "why_use_cell_based", 
        "when_to_use", "control_data_plane", "cell_design", "cell_partition", "cell_routing", 
        "cell_sizing", "cell_placement", "cell_migration", "cell_deployment", 
        "cell_observability", "best_practices", "faq"
    ]] = Field(
        default=None,
        description="Specific whitepaper section to focus the response on"
    )


class ImplementationStage(BaseModel):
    """Model for implementation stage guidance."""
    
    stage: Literal["planning", "design", "implementation", "monitoring"] = Field(
        ...,
        description="Implementation stage following whitepaper methodology"
    )
    aws_services: List[str] = Field(
        default_factory=list,
        description="AWS services to consider for this stage"
    )
    experience_level: Literal["beginner", "intermediate", "expert"] = Field(
        default="intermediate",
        description="User experience level for tailored guidance"
    )


class CellDesignAnalysis(BaseModel):
    """Model for cell design analysis results."""
    
    strengths: List[str] = Field(
        default_factory=list,
        description="Identified strengths in the cell design"
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Identified weaknesses or areas for improvement"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Specific recommendations for improvement"
    )
    compliance_score: float = Field(
        ge=0.0, 
        le=1.0,
        description="Compliance score against cell-based architecture principles (0.0 to 1.0)"
    )
    whitepaper_references: List[str] = Field(
        default_factory=list,
        description="Relevant whitepaper sections for the analysis"
    )