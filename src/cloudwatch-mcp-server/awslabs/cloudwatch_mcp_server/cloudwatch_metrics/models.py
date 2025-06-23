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

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class Dimension(BaseModel):
    """Represents a CloudWatch metric dimension for input parameters."""

    name: str = Field(..., description="The name of the dimension")
    value: str = Field(..., description="The value of the dimension")


class MetricDataPoint(BaseModel):
    """Represents a single CloudWatch metric data point."""
    
    timestamp: datetime = Field(..., description="The timestamp for the data point")
    value: float = Field(..., description="The value of the metric at this timestamp")


class MetricDataResult(BaseModel):
    """Represents the result of a CloudWatch GetMetricData API call for a single metric."""
    
    id: str = Field(..., description="The ID of the metric data query")
    label: str = Field(..., description="The label of the metric")
    statusCode: str = Field(..., description="The status code of the query result")
    datapoints: List[MetricDataPoint] = Field(default_factory=list, description="The data points for the metric")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Messages related to the metric data query")


class GetMetricDataResponse(BaseModel):
    """Represents the response from the GetMetricData API call."""
    
    metricDataResults: List[MetricDataResult] = Field(default_factory=list, description="The results of the metric data queries")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Messages related to the GetMetricData operation")

class MetricMetadataIndexKey:
    """Key class for indexing metric metadata."""
    
    def __init__(self, namespace: str, metric_name: str):
        self.namespace = namespace
        self.metric_name = metric_name
    
    def __hash__(self) -> int:
        """Generate hash for use as dictionary key."""
        return hash((self.namespace, self.metric_name))
    
    def __eq__(self, other) -> bool:
        """Check equality for dictionary key comparison."""
        if not isinstance(other, MetricMetadataIndexKey):
            return False
        return (
            self.namespace == other.namespace and
            self.metric_name == other.metric_name
        )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"MetricMetadataIndexKey(namespace='{self.namespace}', metric_name='{self.metric_name}')"


class MetricMetadata(BaseModel):
    """Represents the metadata of a CloudWatch metric including description, unit and recommended statistics."""
    
    description: str = Field(..., description="Description of the metric")
    recommendedStatistics: str = Field(..., description="Recommended statistics for the metric (e.g., 'Average, Maximum')")
    unit: str = Field(..., description="Unit of measurement for the metric")

class AlarmRecommendationThreshold(BaseModel):
    """Represents an alarm threshold configuration."""
    
    staticValue: float = Field(..., description="The static threshold value")
    justification: str = Field(..., description="Justification for the threshold value")


class AlarmRecommendationDimension(BaseModel):
    """Represents a dimension for alarm recommendations."""
    
    name: str = Field(..., description="The name of the dimension")
    value: Optional[str] = Field(None, description="The value of the dimension (if specified)")


class AlarmRecommendation(BaseModel):
    """Represents a CloudWatch alarm recommendation."""
    
    alarmDescription: str = Field(..., description="Description of what the alarm monitors")
    threshold: AlarmRecommendationThreshold = Field(..., description="Threshold configuration for the alarm")
    period: int = Field(..., description="The period in seconds over which the statistic is applied")
    comparisonOperator: str = Field(..., description="The arithmetic operation to use when comparing the statistic and threshold")
    statistic: str = Field(..., description="The statistic to apply to the alarm's associated metric")
    evaluationPeriods: int = Field(..., description="The number of periods over which data is compared to the threshold")
    datapointsToAlarm: int = Field(..., description="The number of datapoints that must be breaching to trigger the alarm")
    treatMissingData: str = Field(..., description="How to treat missing data points")
    dimensions: List[AlarmRecommendationDimension] = Field(default_factory=list, description="List of dimensions for the alarm")
    intent: str = Field(..., description="The intent or purpose of the alarm")