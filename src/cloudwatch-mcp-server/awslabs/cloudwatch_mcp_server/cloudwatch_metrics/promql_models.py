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

"""Data models for CloudWatch PromQL tools."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List


class PromQLInstantResult(BaseModel):
    """Result from a PromQL instant query (/api/v1/query)."""

    resultType: str = Field(..., description='The type of result (vector, scalar, string)')
    result: List[Dict[str, Any]] = Field(
        default_factory=list, description='List of instant vector results'
    )


class PromQLRangeResult(BaseModel):
    """Result from a PromQL range query (/api/v1/query_range)."""

    resultType: str = Field(..., description='The type of result (matrix)')
    result: List[Dict[str, Any]] = Field(
        default_factory=list, description='List of range vector results'
    )


class PromQLSeriesResult(BaseModel):
    """Result from a PromQL series query (/api/v1/series)."""

    series: List[Dict[str, str]] = Field(
        default_factory=list, description='List of label sets matching the series selector'
    )


class PromQLLabelsResult(BaseModel):
    """Result from a PromQL labels query (/api/v1/labels)."""

    labels: List[str] = Field(default_factory=list, description='List of label names')


class PromQLLabelValuesResult(BaseModel):
    """Result from a PromQL label values query (/api/v1/label/{name}/values)."""

    values: List[str] = Field(default_factory=list, description='List of label values')
