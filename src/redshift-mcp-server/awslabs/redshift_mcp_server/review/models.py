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

"""Pydantic models for the review subpackage."""

from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    """A single finding from signal evaluation."""

    signal_name: str = Field(..., description='Name of the signal that was triggered')
    section: str = Field(..., description='The diagnostic query section this finding belongs to')
    affected_row_count: int = Field(..., description='Number of rows matching the signal criteria')
    recommendation_ids: list[str] = Field(
        ..., description='List of recommendation IDs associated with this finding'
    )


class ReviewRecommendation(BaseModel):
    """A resolved recommendation with full details."""

    id: str = Field(..., description='Unique identifier for the recommendation')
    text: str = Field(..., description='Markdown text of the recommendation')
    triggered_by_signals: list[str] = Field(
        ..., description='Names of signals that triggered this recommendation'
    )


class ReviewResult(BaseModel):
    """Complete result of a review_cluster tool call."""

    signals_evaluated: int = Field(..., description='Total number of signals evaluated')
    findings: list[ReviewFinding] = Field(
        ..., description='List of triggered findings from signal evaluation'
    )
    recommendations: list[ReviewRecommendation] = Field(
        ..., description='Deduplicated recommendations ordered by effort'
    )
    queries_executed: list[str] = Field(
        ..., description='Names of diagnostic queries that were executed'
    )
