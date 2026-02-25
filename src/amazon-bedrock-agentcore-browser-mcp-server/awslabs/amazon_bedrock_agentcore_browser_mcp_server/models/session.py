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

"""Pydantic models for browser session responses."""

from pydantic import BaseModel, Field


class BrowserSessionResponse(BaseModel):
    """Response from starting or getting a browser session."""

    session_id: str = Field(..., description='Unique session identifier')
    status: str = Field(
        ..., description='Session status (e.g., INITIALIZING, READY, ACTIVE, TERMINATED)'
    )
    browser_identifier: str = Field(..., description='Browser resource identifier')
    automation_stream_url: str | None = Field(
        None, description='WebSocket URL for browser automation via CDP'
    )
    live_view_url: str | None = Field(None, description='URL for live browser view stream')
    viewport_width: int | None = Field(None, description='Browser viewport width in pixels')
    viewport_height: int | None = Field(None, description='Browser viewport height in pixels')
    created_at: str | None = Field(None, description='ISO 8601 creation timestamp')
    message: str | None = Field(None, description='Informational message')


class BrowserSessionSummary(BaseModel):
    """Summary of a browser session for list responses."""

    session_id: str = Field(..., description='Unique session identifier')
    status: str = Field(..., description='Session status')
    created_at: str | None = Field(None, description='ISO 8601 creation timestamp')


class SessionListResponse(BaseModel):
    """Response containing a list of browser sessions."""

    sessions: list[BrowserSessionSummary] = Field(
        default_factory=list, description='List of browser session summaries'
    )
    has_more: bool = Field(default=False, description='Whether more sessions are available')
    message: str | None = Field(None, description='Informational message')
