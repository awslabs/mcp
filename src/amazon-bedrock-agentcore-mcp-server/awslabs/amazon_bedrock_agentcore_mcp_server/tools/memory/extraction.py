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

"""Extraction job tools for AgentCore Memory data plane.

Extraction jobs process previously failed events to produce structured
long-term memory records.
"""

from .error_handler import handle_memory_error
from .models import (
    ErrorResponse,
    ExtractionJobResponse,
    ListExtractionJobsResponse,
)
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Any


class ExtractionTools:
    """Tools for managing memory extraction jobs."""

    def __init__(self, client_factory):
        """Initialize with a callable that returns a boto3 data plane client."""
        self._get_client = client_factory

    def register(self, mcp):
        """Register extraction tools with the MCP server."""
        mcp.tool(name='memory_list_extraction_jobs')(self.memory_list_extraction_jobs)
        mcp.tool(name='memory_start_extraction_job')(self.memory_start_extraction_job)

    async def memory_list_extraction_jobs(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        extraction_filter: Annotated[
            dict[str, str] | None,
            Field(
                description=(
                    'Filter criteria. Object with optional keys: '
                    '"actorId", "sessionId", "status" (e.g. "FAILED"), '
                    '"strategyId".'
                )
            ),
        ] = None,
        max_results: Annotated[
            int | None,
            Field(description='Max results per page (1-50, default 20)'),
        ] = None,
        next_token: Annotated[
            str | None,
            Field(description='Pagination token'),
        ] = None,
    ) -> ListExtractionJobsResponse | ErrorResponse:
        """List memory extraction jobs for an AgentCore Memory resource.

        Returns extraction job metadata including status, actor/session
        IDs, and failure reasons. This is a read-only operation.
        """
        logger.info(f'Listing extraction jobs for memory {memory_id}')

        try:
            client = self._get_client()
            kwargs: dict[str, Any] = {'memoryId': memory_id}
            if extraction_filter is not None:
                kwargs['filter'] = extraction_filter
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token is not None:
                kwargs['nextToken'] = next_token

            response = client.list_memory_extraction_jobs(**kwargs)
            jobs = response.get('jobs', [])

            return ListExtractionJobsResponse(
                status='success',
                message=f'Found {len(jobs)} extraction job(s).',
                jobs=jobs,
                next_token=response.get('nextToken'),
            )
        except Exception as e:
            return handle_memory_error('ListMemoryExtractionJobs', e)

    async def memory_start_extraction_job(
        self,
        ctx: Context,
        memory_id: Annotated[str, Field(description='Memory resource ID')],
        job_id: Annotated[
            str,
            Field(description='Extraction job ID to restart'),
        ],
    ) -> ExtractionJobResponse | ErrorResponse:
        """Start (or restart) a memory extraction job.

        COST WARNING: Extraction jobs consume compute resources to
        process events and produce memory records. This incurs AWS
        charges.

        Typically used to retry previously failed extraction jobs.
        The job processes events and produces structured long-term
        memory records.
        """
        logger.info(f'Starting extraction job {job_id} for memory {memory_id}')

        try:
            client = self._get_client()
            response = client.start_memory_extraction_job(
                memoryId=memory_id,
                extractionJob={'jobId': job_id},
            )

            return ExtractionJobResponse(
                status='success',
                message=f'Extraction job {job_id} started.',
                job_id=response.get('jobId', job_id),
            )
        except Exception as e:
            return handle_memory_error('StartMemoryExtractionJob', e)
