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

"""Scoring engine for field index recommendations.

Scores candidate fields based on query frequency, equality filter usage,
recency, scan volume, and cardinality. Also defines result models.
"""

import math
from awslabs.cloudwatch_mcp_server.cloudwatch_logs.query_parser import FieldUsage
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
QUERY_HISTORY_DAYS = 30
TOP_N_FOR_CARDINALITY = 10
CARDINALITY_SAMPLE_HOURS = 1
FIELD_EXISTENCE_SAMPLE_HOURS = 1
QUERY_TIMEOUT = 30

# System/default-indexed fields to always exclude
# Source: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-FilterIndex.html
SYSTEM_FIELDS: Set[str] = {
    '@timestamp',
    '@message',
    '@logStream',
    '@log',
    '@ptr',
    '@ingestionTime',
    '@aws.region',
    '@aws.account',
    '@source.log',
    '@data_source_name',
    '@data_source_type',
    '@data_format',
    'traceId',
    'severityText',
    'attributes.session.id',
    # VPC Flow Logs
    'action',
    'logStatus',
    'flowDirection',
    'type',
    # Route53 Resolver Query Logs
    'query_type',
    'transport',
    'rcode',
    # AWS WAF
    'httpRequest.country',
    # CloudTrail
    'eventSource',
    'eventName',
    'awsRegion',
    'userAgent',
    'errorCode',
    'eventType',
    'managementEvent',
    'readOnly',
    'eventCategory',
    'requestId',
}

# Scoring weights (must sum to 1.0)
# Source: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CloudWatchLogs-Field-Indexing.html
W_FREQUENCY = 0.30
W_FILTER_EQUALITY = 0.25
W_RECENCY = 0.15
W_SCAN_VOLUME = 0.15
W_CARDINALITY = 0.15

if not math.isclose(
    W_FREQUENCY + W_FILTER_EQUALITY + W_RECENCY + W_SCAN_VOLUME + W_CARDINALITY, 1.0
):
    raise ValueError('Scoring weights must sum to 1.0')

RECENCY_HALF_LIFE_DAYS = 7


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------
class FieldScoreBreakdown(BaseModel):
    """Score breakdown for a single field."""

    frequency_score: float = Field(..., description='Normalized query frequency score')
    filter_equality_score: float = Field(..., description='Ratio of equality filter usage')
    recency_score: float = Field(..., description='Time-decay weighted recency score')
    scan_volume_score: float = Field(..., description='Normalized log group scan volume score')
    cardinality_score: Optional[float] = Field(
        default=None, description='Normalized cardinality score (only for top candidates)'
    )


class IndexRecommendation(BaseModel):
    """A single field index recommendation."""

    field_name: str = Field(..., description='The field name recommended for indexing')
    score: float = Field(..., description='Overall recommendation score (0-1, higher is better)')
    action: str = Field(..., description='Recommended action: CREATE_INDEX')
    query_count: int = Field(..., description='Number of queries using this field in the period')
    filter_equality_count: int = Field(
        ..., description='Number of queries using this field in equality filters'
    )
    score_breakdown: FieldScoreBreakdown = Field(..., description='Detailed score breakdown')


class AlreadyIndexedField(BaseModel):
    """A field that is already indexed."""

    field_name: str = Field(..., description='The field name')
    query_count: int = Field(..., description='Number of queries using this field')
    source: str = Field(..., description='Index source: ACCOUNT or LOG_GROUP')


class FieldNotFound(BaseModel):
    """A field referenced in queries but not found in log data."""

    field_name: str = Field(..., description='The field name')
    query_count: int = Field(..., description='Number of queries referencing this field')


class IndexRecommenderResult(BaseModel):
    """Result of the index recommender analysis for a single log group."""

    recommendations: List[IndexRecommendation] = Field(
        default_factory=list, description='Fields recommended for indexing, sorted by score'
    )
    already_indexed: List[AlreadyIndexedField] = Field(
        default_factory=list, description='Fields already indexed (no action needed)'
    )
    fields_not_found: List[FieldNotFound] = Field(
        default_factory=list, description='Fields referenced in queries but not in log data'
    )
    queries_analyzed: int = Field(..., description='Total completed queries analyzed')
    unique_queries: int = Field(..., description='Unique query strings analyzed')
    time_range_days: int = Field(..., description='Days of query history covered')
    log_group: str = Field(..., description='Log group name or ARN analyzed')
    warnings: List[str] = Field(default_factory=list, description='Warnings encountered')


class AccountIndexRecommenderResult(BaseModel):
    """Result of the account-level index recommender analysis."""

    log_group_results: List[IndexRecommenderResult] = Field(
        ..., description='Per-log-group recommendations, sorted by highest field score'
    )
    total_log_groups_analyzed: int = Field(
        ..., description='Number of log groups with query history'
    )
    total_queries_analyzed: int = Field(..., description='Total queries analyzed across account')
    time_range_days: int = Field(..., description='Days of query history covered')
    warnings: List[str] = Field(default_factory=list, description='Warnings encountered')


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
def recency_score(epoch_seconds: float, now: float) -> float:
    """Exponential decay score based on age. Returns 0-1."""
    age_days = max(0, (now - epoch_seconds) / 86400.0)
    return math.exp(-0.693 * age_days / RECENCY_HALF_LIFE_DAYS)


def normalize(value: float, max_value: float) -> float:
    """Normalize value to 0-1 range."""
    return min(value / max_value, 1.0) if max_value > 0 else 0.0


def score_fields(
    scorable: Dict[str, FieldUsage],
    now_epoch: float,
    scan_vol_norm: float,
) -> List[tuple]:
    """Score candidate fields. Returns sorted list of (name, score, breakdown, fu)."""
    max_count = max(fu.total_count for fu in scorable.values())
    scored = []
    for name, fu in scorable.items():
        freq = normalize(fu.total_count, max_count)
        eq_ratio = fu.filter_equality_count / fu.total_count if fu.total_count > 0 else 0.0
        rec = recency_score(fu.most_recent_use, now_epoch)
        if fu.filter_equality_count == 0 and fu.non_equality_filter_count > 0:
            eq_ratio *= 0.5
        score = (
            freq * W_FREQUENCY
            + eq_ratio * W_FILTER_EQUALITY
            + rec * W_RECENCY
            + scan_vol_norm * W_SCAN_VOLUME
        )
        breakdown = FieldScoreBreakdown(
            frequency_score=freq,
            filter_equality_score=eq_ratio,
            recency_score=rec,
            scan_volume_score=scan_vol_norm,
        )
        scored.append((name, score, breakdown, fu))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def build_recommendations(
    scored: List[tuple],
    cardinality_map: Optional[Dict[str, float]] = None,
) -> List[IndexRecommendation]:
    """Build final recommendation list, optionally incorporating cardinality scores."""
    if cardinality_map is None:
        cardinality_map = {}
    recommendations = []
    for name, base_score, breakdown, fu in scored:
        card = cardinality_map.get(name)
        if card is not None:
            breakdown.cardinality_score = card
            final = (
                breakdown.frequency_score * W_FREQUENCY
                + breakdown.filter_equality_score * W_FILTER_EQUALITY
                + breakdown.recency_score * W_RECENCY
                + breakdown.scan_volume_score * W_SCAN_VOLUME
                + card * W_CARDINALITY
            )
        else:
            final = base_score
        recommendations.append(
            IndexRecommendation(
                field_name=name,
                score=round(final, 4),
                action='CREATE_INDEX',
                query_count=fu.total_count,
                filter_equality_count=fu.filter_equality_count,
                score_breakdown=breakdown,
            )
        )
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations


def score_fields_lightweight(
    candidates: Dict[str, FieldUsage],
    now_epoch: float,
) -> List[IndexRecommendation]:
    """Lightweight scoring without existence/cardinality (for account-level scan)."""
    max_count = max(fu.total_count for fu in candidates.values())
    recommendations = []
    for name, fu in candidates.items():
        freq = normalize(fu.total_count, max_count)
        eq_ratio = fu.filter_equality_count / fu.total_count if fu.total_count > 0 else 0.0
        rec = recency_score(fu.most_recent_use, now_epoch)
        if fu.filter_equality_count == 0 and fu.non_equality_filter_count > 0:
            eq_ratio *= 0.5
        score = freq * 0.40 + eq_ratio * 0.35 + rec * 0.25
        recommendations.append(
            IndexRecommendation(
                field_name=name,
                score=round(score, 4),
                action='CREATE_INDEX',
                query_count=fu.total_count,
                filter_equality_count=fu.filter_equality_count,
                score_breakdown=FieldScoreBreakdown(
                    frequency_score=freq,
                    filter_equality_score=eq_ratio,
                    recency_score=rec,
                    scan_volume_score=0.0,
                ),
            )
        )
    recommendations.sort(key=lambda r: r.score, reverse=True)
    return recommendations
