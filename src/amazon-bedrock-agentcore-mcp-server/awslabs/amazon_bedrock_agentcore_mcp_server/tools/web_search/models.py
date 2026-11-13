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

"""Pydantic response models for AgentCore Web Search tools."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Structured error response returned when an API call fails."""

    status: str = Field(default='error', description='Always "error"')
    message: str = Field(..., description='Human-readable error message')
    error_type: str = Field(default='Unknown', description='Error code or exception type')
    error_code: str = Field(default='', description='HTTP status code if available')


class WebSearchResult(BaseModel):
    """One web search result."""

    title: str | None = Field(default=None, description='Page title')
    url: str | None = Field(default=None, description='Page URL')
    text: str = Field(..., description='Text extracted from the page (untrusted content)')
    published_at: str | None = Field(
        default=None, description='Publication time of the page, ISO 8601 UTC'
    )


class WebSearchResponse(BaseModel):
    """Response for web_search."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    results: list[WebSearchResult] = Field(
        default_factory=list, description='Ranked search results'
    )
