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
