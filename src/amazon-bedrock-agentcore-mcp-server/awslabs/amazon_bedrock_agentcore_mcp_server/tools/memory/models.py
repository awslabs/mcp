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

"""Pydantic response models for AgentCore Memory tools."""

from pydantic import BaseModel, Field
from typing import Any


class ErrorResponse(BaseModel):
    """Structured error response returned when an API call fails."""

    status: str = Field(default='error', description='Always "error"')
    message: str = Field(..., description='Human-readable error message')
    error_type: str = Field(default='Unknown', description='Error code or exception type')
    error_code: str = Field(default='', description='HTTP status code if available')


class MemoryResponse(BaseModel):
    """Response for single-memory operations (create, get, update)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    memory: dict[str, Any] = Field(default_factory=dict, description='Memory resource details')


class DeleteMemoryResponse(BaseModel):
    """Response for delete_memory."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    memory_id: str = Field(default='', description='Deleted memory ID')
    memory_status: str = Field(default='', description='Memory status after deletion')


class ListMemoriesResponse(BaseModel):
    """Response for list_memories."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    memories: list[dict[str, Any]] = Field(
        default_factory=list, description='List of memory summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class EventResponse(BaseModel):
    """Response for single-event operations (create, get)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    event: dict[str, Any] = Field(default_factory=dict, description='Event details')


class DeleteEventResponse(BaseModel):
    """Response for delete_event."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    event_id: str = Field(default='', description='Deleted event ID')


class ListEventsResponse(BaseModel):
    """Response for list_events."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    events: list[dict[str, Any]] = Field(default_factory=list, description='List of events')
    next_token: str | None = Field(default=None, description='Pagination token')


class ListActorsResponse(BaseModel):
    """Response for list_actors."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    actors: list[dict[str, Any]] = Field(
        default_factory=list, description='List of actor summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class ListSessionsResponse(BaseModel):
    """Response for list_sessions."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    sessions: list[dict[str, Any]] = Field(
        default_factory=list, description='List of session summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class MemoryRecordResponse(BaseModel):
    """Response for single memory record operations (get)."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    memory_record: dict[str, Any] = Field(
        default_factory=dict, description='Memory record details'
    )


class DeleteMemoryRecordResponse(BaseModel):
    """Response for delete_memory_record."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    memory_record_id: str = Field(default='', description='Deleted memory record ID')


class ListMemoryRecordsResponse(BaseModel):
    """Response for list_memory_records and retrieve_memory_records."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    memory_records: list[dict[str, Any]] = Field(
        default_factory=list, description='List of memory record summaries'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class BatchRecordsResponse(BaseModel):
    """Response for batch create/update/delete memory records."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    successful_records: list[dict[str, Any]] = Field(
        default_factory=list, description='Successfully processed records'
    )
    failed_records: list[dict[str, Any]] = Field(
        default_factory=list, description='Records that failed processing'
    )


class ExtractionJobResponse(BaseModel):
    """Response for start_memory_extraction_job."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    job_id: str = Field(default='', description='Extraction job ID')


class ListExtractionJobsResponse(BaseModel):
    """Response for list_memory_extraction_jobs."""

    status: str = Field(..., description='Operation status')
    message: str = Field(..., description='Human-readable result')
    jobs: list[dict[str, Any]] = Field(
        default_factory=list, description='List of extraction job metadata'
    )
    next_token: str | None = Field(default=None, description='Pagination token')


class MemoryGuideResponse(BaseModel):
    """Response for get_memory_guide."""

    guide: str = Field(..., description='Comprehensive Memory guide content')
