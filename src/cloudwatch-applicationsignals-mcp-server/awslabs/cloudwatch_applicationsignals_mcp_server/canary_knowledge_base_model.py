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

"""Pydantic data models for Synthetics knowledge base entries, failure context, and match results."""

from __future__ import annotations

from datetime import date
from pydantic import BaseModel, field_validator
from typing import Optional, Union


class ErrorPattern(BaseModel):
    """A single error matching rule."""

    regex: Optional[str] = None
    text_contains: Optional[str] = None
    error_type: Optional[str] = None


class SolutionStep(BaseModel):
    """A single solution step within a recommendation."""

    step: str
    description: Optional[str] = None
    command: Optional[str] = None
    expected_outcome: Optional[str] = None


class Recommendation(BaseModel):
    """A single recommendation within a KB entry."""

    priority: str
    confidence: Union[int, float, str]
    title: Optional[str] = None
    problem: Optional[str] = None
    solution: list[SolutionStep]
    estimated_time: Optional[str] = None


class DocumentationLink(BaseModel):
    """A documentation link with title and URL."""

    title: str
    url: str


class KBEntry(BaseModel):
    """A validated knowledge base entry parsed from JSON."""

    model_config = {'extra': 'ignore'}

    id: str
    title: str
    category: str
    severity: str
    error_patterns: list[ErrorPattern]
    symptoms: list[str]
    root_cause: str
    recommendations: list[Recommendation]
    runtime_versions: list[str] = []
    documentation_links: list[DocumentationLink] = []
    tags: list[str] = []
    deprecated: bool = False
    deprecation_date: Optional[date] = None

    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity is one of the allowed values."""
        allowed = {'critical', 'high', 'medium', 'low'}
        if v.lower() not in allowed:
            raise ValueError(f'severity must be one of {allowed}')
        return v.lower()


class FailureContext(BaseModel):
    """Data collected from canary failure analysis, passed to the recommendation engine."""

    error_messages: list[str] = []
    state_reasons: list[str] = []
    runtime_version: str = ''
    log_patterns: list[str] = []
    resource_metrics: dict[str, float] = {}
    environment_indicators: list[str] = []


class MatchResult(BaseModel):
    """A scored knowledge base match."""

    entry: KBEntry
    confidence_score: float
    error_pattern_score: float
    symptom_score: float
    runtime_version_score: float
    environment_score: float
