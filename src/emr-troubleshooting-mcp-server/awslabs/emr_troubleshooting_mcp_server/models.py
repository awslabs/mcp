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

"""Data models for EMR Troubleshooting MCP server."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class EMRIssue(BaseModel):
    """Represents a known EMR issue."""

    id: str = Field(..., description='Unique identifier for the issue')
    summary: str = Field(..., description='Brief summary of the issue')
    description: str = Field(..., description='Detailed description of the issue')
    keywords: List[str] = Field(..., description='Keywords to match in log files')
    knowledge_center_links: List[str] = Field(
        default_factory=list,
        description=('Links to AWS Knowledge Center articles related to this issue'),
    )


class EMRRecommendation(BaseModel):
    """Recommendation for an EMR issue."""

    issue_id: str = Field(..., description='ID of the related issue')
    summary: str = Field(..., description='Brief summary of the recommendation')
    description: str = Field(..., description='Detailed description of the recommendation')
    knowledge_center_links: List[str] = Field(
        default_factory=list, description='Links to AWS Knowledge Center articles with more info'
    )


class MatchedIssue(BaseModel):
    """Represents an issue matched in the log content."""

    issue: EMRIssue = Field(..., description='The matched issue')
    matched_patterns: List[str] = Field(..., description='Patterns that were matched in the logs')
    confidence: float = Field(default=0.9, description='Confidence score for the match')


class EMRLogAnalysisResponse(BaseModel):
    """Response from analyzing EMR logs."""

    matched_issues: List[MatchedIssue] = Field(
        default_factory=list, description='Issues matched in the log content'
    )
    summary: str = Field(..., description='Summary of the analysis results')
    total_matches: int = Field(..., description='Total number of matched issues')


class EMRIssueOccurrence(BaseModel):
    """Occurrence of an EMR issue in logs with detailed statistics."""

    issue_id: str = Field(..., description='Unique identifier for the issue')
    issue_summary: str = Field(..., description='Brief summary of the issue')
    issue_description: str = Field(..., description='Detailed description and resolution steps')
    component: str = Field(..., description='EMR component (Spark, YARN, HBase, etc.)')
    matched_keyword: str = Field(..., description='Keyword pattern that matched')
    occurrence_count: int = Field(..., description='Number of times this issue occurred')
    sample_data: List[str] = Field(
        default_factory=list, description='Sample log lines that matched this issue'
    )
    knowledge_center_links: List[str] = Field(
        default_factory=list, description='AWS Knowledge Center links for additional help'
    )
    first_occurrence: Optional[str] = Field(None, description='Timestamp of first occurrence')
    last_occurrence: Optional[str] = Field(None, description='Timestamp of last occurrence')


class EMRClusterAnalysisResponse(BaseModel):
    """Response for EMR cluster log analysis using Athena."""

    status: Literal['SUCCEEDED', 'FAILED', 'IN_PROGRESS'] = Field(
        ..., description='Status of the analysis'
    )
    source_type: Literal['cluster', 'uploaded'] = Field(
        ..., description='Type of log source analyzed'
    )
    source_id: str = Field(..., description='Cluster ID or session ID')
    issues_found: int = Field(..., description='Number of unique issues found')
    total_occurrences: int = Field(
        default=0, description='Total number of issue occurrences across all logs'
    )
    results: List[EMRIssueOccurrence] = Field(
        default_factory=list, description='Detailed analysis results with occurrence statistics'
    )
    execution_time_ms: Optional[int] = Field(
        None, description='Analysis execution time in milliseconds'
    )
    error: Optional[str] = Field(None, description='Error message if analysis failed')
