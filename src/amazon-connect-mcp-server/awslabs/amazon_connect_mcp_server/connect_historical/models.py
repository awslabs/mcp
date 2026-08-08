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

"""Data models for Amazon Connect historical metric tools."""

from pydantic import BaseModel, Field
from typing import Dict, List


class HistoricalMetricValue(BaseModel):
    """A single historical metric value."""

    name: str = Field(..., description='The name of the metric (e.g., CONTACTS_HANDLED)')
    value: float | None = Field(default=None, description='The computed value of the metric')


class HistoricalMetricResult(BaseModel):
    """A grouped set of historical metric values for a dimension.

    When a report spans more than 24 hours, the requested range is split into
    24-hour intervals and each interval produces its own result rows. The
    ``interval_start`` and ``interval_end`` fields identify which interval a row
    belongs to so that per-interval values are never conflated.
    """

    dimensions: Dict[str, str] = Field(
        default_factory=dict,
        description='The dimensions for this result (e.g., queue, channel, agent)',
    )
    interval_start: str | None = Field(
        default=None,
        description='ISO 8601 start of the 24-hour interval this result row covers',
    )
    interval_end: str | None = Field(
        default=None,
        description='ISO 8601 end of the 24-hour interval this result row covers',
    )
    metrics: List[HistoricalMetricValue] = Field(
        default_factory=list, description='The metric values for this dimension'
    )


class HistoricalMetricDataResponse(BaseModel):
    """Response containing historical metric data from Amazon Connect."""

    resource_arn: str = Field(..., description='The Connect instance ARN the metrics belong to')
    start_time: str = Field(..., description='ISO 8601 start of the reporting interval')
    end_time: str = Field(..., description='ISO 8601 end of the reporting interval')
    interval_count: int = Field(
        default=1,
        description='Number of 24-hour intervals the requested range was split into',
    )
    results: List[HistoricalMetricResult] = Field(
        default_factory=list,
        description='The grouped historical metric results, one set per interval per dimension',
    )
    has_more_results: bool = Field(
        default=False, description='Whether more results are available than were returned'
    )
    message: str | None = Field(None, description='Informational message about the results')
