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

"""Pydantic result models for the PromQL (CloudWatch Metrics V2) tools.

Mirror the Prometheus HTTP API response shapes. The ``result`` payloads stay as
plain dicts because native-histogram values and label sets vary; the models give
the MCP tools stable, typed envelopes.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List


class PromQLInstantResult(BaseModel):
    """Result of an instant query (``/query``)."""

    result_type: str = Field(description="Prometheus resultType, e.g. 'vector' or 'matrix'.")
    result: List[Dict[str, Any]] = Field(
        default_factory=list, description='Series with metric labels and value(s).'
    )


class PromQLRangeResult(BaseModel):
    """Result of a range query (``/query_range``)."""

    result_type: str = Field(
        description="Prometheus resultType, typically 'matrix' for range queries."
    )
    result: List[Dict[str, Any]] = Field(
        default_factory=list, description='Series with metric labels and values[].'
    )


class PromQLSeriesResult(BaseModel):
    """Result of a series lookup (``/series``)."""

    series: List[Dict[str, str]] = Field(
        default_factory=list, description='Matching series as label-set dicts.'
    )


class PromQLLabelsResult(BaseModel):
    """Result of a labels lookup (``/labels``)."""

    labels: List[str] = Field(default_factory=list, description='Sorted label names.')


class PromQLLabelValuesResult(BaseModel):
    """Result of a label-values lookup (``/label/<name>/values``)."""

    values: List[str] = Field(default_factory=list, description='Sorted label values.')
