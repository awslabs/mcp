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

"""Data models for CloudWatch Dashboard MCP tools."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict


class DashboardResponse(BaseModel):
    """Response containing CloudWatch dashboard information."""

    dashboard_name: str = Field(..., description='Name of the dashboard')
    dashboard_arn: str | None = Field(None, description='ARN of the dashboard')
    dashboard_body: Dict[str, Any] | str = Field(
        ..., description='Dashboard configuration as parsed JSON or raw string if parsing fails'
    )
    last_modified: datetime | None = Field(
        None, description='Last modified timestamp if available'
    )
    region: str = Field(..., description='AWS region where the dashboard was retrieved')
    parsing_warning: str | None = Field(
        None, description='Warning message if dashboard body could not be parsed as JSON'
    )
