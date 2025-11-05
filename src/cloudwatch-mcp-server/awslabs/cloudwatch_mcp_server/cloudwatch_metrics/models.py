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

"""Data models for CloudWatch Metrics MCP tools."""

from awslabs.cloudwatch_mcp_server.cloudwatch_metrics.constants import (
    DAYS_PER_WEEK,
    HOURS_PER_DAY,
    MINUTES_PER_HOUR,
    SECONDS_PER_MINUTE,
)
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_serializer, model_validator
from typing import Any, ClassVar, Dict, List, Optional, Union


class Trend(str, Enum):
    """Trend direction based on statistical significance."""

    POSITIVE = 'positive'
    NEGATIVE = 'negative'
    NONE = 'none'


# Seasonality rounding threshold constant
SEASONALITY_ROUNDING_THRESHOLD = 0.1


class Seasonality(Enum):
    """Seasonality detection results with period in seconds."""

    NONE = 0
    FIFTEEN_MINUTES = 15 * SECONDS_PER_MINUTE
    ONE_HOUR = MINUTES_PER_HOUR * SECONDS_PER_MINUTE
    SIX_HOURS = 6 * ONE_HOUR
    ONE_DAY = HOURS_PER_DAY * ONE_HOUR
    ONE_WEEK = DAYS_PER_WEEK * ONE_DAY

    @classmethod
    def from_seconds(cls, seconds: Union[float, int]) -> 'Seasonality':
        """Convert seconds to closest seasonality enum."""
        seconds = int(seconds)
        closest = min(cls, key=lambda x: abs(x.value - seconds))
        return (
            closest
            if abs(closest.value - seconds) < closest.value * SEASONALITY_ROUNDING_THRESHOLD
            else cls.NONE
        )


class DecompositionResult(BaseModel):
    """Result of metric data decomposition into seasonal and trend components."""

    seasonality: Seasonality
    trend: Trend


class SortOrder(str, Enum):
    """Sort order for Metrics Insights queries."""

    ASCENDING = 'ASC'
    DESCENDING = 'DESC'


class Dimension(BaseModel):
    """Represents a CloudWatch metric dimension for input parameters."""

    name: str = Field(..., description='The name of the dimension')
    value: str = Field(..., description='The value of the dimension')


class MetricDataPoint(BaseModel):
    """Represents a single CloudWatch metric data point."""

    timestamp: datetime = Field(..., description='The timestamp for the data point')
    value: float = Field(..., description='The value of the metric at this timestamp')


class MetricDataResult(BaseModel):
    """Represents the result of a CloudWatch GetMetricData API call for a single metric."""

    id: str = Field(..., description='The ID of the metric data query')
    label: str = Field(..., description='The label of the metric')
    statusCode: str = Field(..., description='The status code of the query result')
    datapoints: List[MetricDataPoint] = Field(
        default_factory=list, description='The data points for the metric'
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description='Messages related to the metric data query'
    )


class GetMetricDataResponse(BaseModel):
    """Represents the response from the GetMetricData API call."""

    metricDataResults: List[MetricDataResult] = Field(
        default_factory=list, description='The results of the metric data queries'
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description='Messages related to the GetMetricData operation'
    )


class MetricMetadataIndexKey:
    """Key class for indexing metric metadata."""

    def __init__(self, namespace: str, metric_name: str):
        """Initialize MetricKey with namespace and metric name.

        Args:
            namespace: The CloudWatch namespace for the metric.
            metric_name: The name of the metric.
        """
        self.namespace = namespace
        self.metric_name = metric_name

    def __hash__(self) -> int:
        """Generate hash for use as dictionary key."""
        return hash((self.namespace, self.metric_name))

    def __eq__(self, other) -> bool:
        """Check equality for dictionary key comparison."""
        if not isinstance(other, MetricMetadataIndexKey):
            return False
        return self.namespace == other.namespace and self.metric_name == other.metric_name

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"MetricMetadataIndexKey(namespace='{self.namespace}', metric_name='{self.metric_name}')"


class MetricMetadata(BaseModel):
    """Represents the metadata of a CloudWatch metric including description, unit and recommended statistics."""

    description: str = Field(..., description='Description of the metric')
    recommendedStatistics: str = Field(
        ..., description="Recommended statistics for the metric (e.g., 'Average, Maximum')"
    )
    unit: str = Field(..., description='Unit of measurement for the metric')


class AlarmRecommendationThreshold(BaseModel):
    """Represents an alarm threshold configuration."""

    justification: str = Field(default='', description='Justification for the threshold value')


class StaticAlarmThreshold(AlarmRecommendationThreshold):
    """Represents an alarm static threshold configuration."""

    staticValue: float = Field(..., description='The static threshold value')


class AnomalyDetectionAlarmThreshold(AlarmRecommendationThreshold):
    """Represents an anomaly detection alarm threshold configuration."""

    DEFAULT_SENSITIVITY: ClassVar[float] = 2.0

    sensitivity: float = Field(
        default=DEFAULT_SENSITIVITY, description='The sensitivity of the Anomaly Detection bands.'
    )

    @field_validator('sensitivity')
    @classmethod
    def validate_sensitivity(cls, v):
        """Validate sensitivity is within acceptable range."""
        # Extreme sensitivity values result in reduced Anomaly Detection performance
        if not 0 < v <= 100:
            raise ValueError('Sensitivity must be above 0 and less than or equal to 100')
        return v


class AlarmRecommendationDimension(BaseModel):
    """Represents a dimension for alarm recommendations."""

    name: str = Field(..., description='The name of the dimension')
    value: str | None = Field(
        default=None, description='The value of the dimension (if specified)'
    )


class AlarmRecommendation(BaseModel):
    """Represents a CloudWatch alarm recommendation."""

    alarmDescription: str = Field(..., description='Description of what the alarm monitors')
    threshold: AlarmRecommendationThreshold = Field(
        ..., description='Threshold configuration for the alarm'
    )
    period: int = Field(
        ..., description='The period in seconds over which the statistic is applied'
    )
    comparisonOperator: str = Field(
        ...,
        description='The arithmetic operation to use when comparing the statistic and threshold',
    )
    statistic: str = Field(
        ..., description="The statistic to apply to the alarm's associated metric"
    )
    evaluationPeriods: int = Field(
        ..., description='The number of periods over which data is compared to the threshold'
    )
    datapointsToAlarm: int = Field(
        ..., description='The number of datapoints that must be breaching to trigger the alarm'
    )
    treatMissingData: str = Field(..., description='How to treat missing data points')
    dimensions: List[AlarmRecommendationDimension] = Field(
        default_factory=list, description='List of dimensions for the alarm'
    )
    intent: str = Field(..., description='The intent or purpose of the alarm')
    cloudformation_template: Optional[Dict[str, Any]] = Field(
        default=None,
        description='CloudFormation template (only for anomaly detection alarms)',
    )

    @model_serializer
    def serialize_model(self):
        """Serialize alarm recommendation to dict format."""
        data = {
            'alarmDescription': self.alarmDescription,
            'threshold': self.threshold,
            'period': self.period,
            'comparisonOperator': self.comparisonOperator,
            'statistic': self.statistic,
            'evaluationPeriods': self.evaluationPeriods,
            'datapointsToAlarm': self.datapointsToAlarm,
            'treatMissingData': self.treatMissingData,
            'dimensions': self.dimensions,
            'intent': self.intent,
        }
        if self.cloudformation_template is not None:
            data['cloudformation_template'] = self.cloudformation_template
        return data


class MetricData(BaseModel):
    """Represents CloudWatch Metric (time series) data."""

    period_seconds: int = Field(
        ..., description='The aggregation period in seconds of the requested metric data'
    )
    timestamps: List[int] = Field(default_factory=list, description='List of metric timestamps')
    values: List[float] = Field(default_factory=list, description='List of metric values')

    @model_validator(mode='after')
    def validate_metric_data(self):
        """Validate MetricData after initialization."""
        if len(self.timestamps) != len(self.values):
            raise ValueError('Timestamps and values must have the same length')
        if self.period_seconds <= 0:
            raise ValueError('Timeseries must have a period >= 0')
        return self


class AlarmRecommendationResult(BaseModel):
    """Result wrapper for alarm recommendations with a success/failure message to guide the calling LLM."""

    recommendations: List[AlarmRecommendation] = Field(
        default_factory=list,
        description='A list of alarm recommendations that match the provided dimensions.',
    )
    message: str = Field(
        ...,
        description='Message describing the success/failure of generating alarm recommendation.',
    )
