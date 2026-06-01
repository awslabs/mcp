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

"""Unit tests for Memory extraction job tools."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.extraction import (
    ExtractionTools,
)
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.memory.models import (
    ErrorResponse,
    ExtractionJobResponse,
    ListExtractionJobsResponse,
)
from botocore.exceptions import ClientError


class TestMemoryListExtractionJobs:
    """Tests for memory_list_extraction_jobs."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns list of extraction jobs."""
        mock_boto3_client.list_memory_extraction_jobs.return_value = {
            'jobs': [
                {'jobID': 'j1', 'status': 'COMPLETED', 'strategyId': 's1'},
                {'jobID': 'j2', 'status': 'FAILED', 'failureReason': 'to'},
            ],
            'nextToken': None,
        }
        tools = ExtractionTools(client_factory)
        result = await tools.memory_list_extraction_jobs(
            ctx=mock_ctx,
            memory_id='m',
        )
        assert isinstance(result, ListExtractionJobsResponse)
        assert result.status == 'success'
        assert len(result.jobs) == 2

    @pytest.mark.asyncio
    async def test_with_all_params(self, mock_ctx, client_factory, mock_boto3_client):
        """Passes filter, pagination, and next_token to API."""
        mock_boto3_client.list_memory_extraction_jobs.return_value = {'jobs': []}
        tools = ExtractionTools(client_factory)
        await tools.memory_list_extraction_jobs(
            ctx=mock_ctx,
            memory_id='m',
            extraction_filter={'status': 'FAILED', 'actorId': 'u1'},
            max_results=5,
            next_token='tok',
        )
        kw = mock_boto3_client.list_memory_extraction_jobs.call_args.kwargs
        assert kw['filter'] == {'status': 'FAILED', 'actorId': 'u1'}
        assert kw['maxResults'] == 5
        assert kw['nextToken'] == 'tok'

    @pytest.mark.asyncio
    async def test_client_error(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse on AccessDeniedException."""
        mock_boto3_client.list_memory_extraction_jobs.side_effect = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 403},
            },
            'ListMemoryExtractionJobs',
        )
        tools = ExtractionTools(client_factory)
        result = await tools.memory_list_extraction_jobs(
            ctx=mock_ctx,
            memory_id='m',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'


class TestMemoryStartExtractionJob:
    """Tests for memory_start_extraction_job."""

    @pytest.mark.asyncio
    async def test_success(self, mock_ctx, client_factory, mock_boto3_client):
        """Starts extraction job and returns job ID."""
        mock_boto3_client.start_memory_extraction_job.return_value = {'jobId': 'j1'}
        tools = ExtractionTools(client_factory)
        result = await tools.memory_start_extraction_job(
            ctx=mock_ctx,
            memory_id='m',
            job_id='j1',
        )
        assert isinstance(result, ExtractionJobResponse)
        assert result.status == 'success'
        assert result.job_id == 'j1'
        mock_boto3_client.start_memory_extraction_job.assert_called_once_with(
            memoryId='m', extractionJob={'jobId': 'j1'}
        )

    @pytest.mark.asyncio
    async def test_not_found(self, mock_ctx, client_factory, mock_boto3_client):
        """Returns ErrorResponse when job not found."""
        mock_boto3_client.start_memory_extraction_job.side_effect = ClientError(
            {
                'Error': {'Code': 'ResourceNotFoundException', 'Message': 'x'},
                'ResponseMetadata': {'HTTPStatusCode': 404},
            },
            'StartMemoryExtractionJob',
        )
        tools = ExtractionTools(client_factory)
        result = await tools.memory_start_extraction_job(
            ctx=mock_ctx,
            memory_id='m',
            job_id='bad',
        )
        assert isinstance(result, ErrorResponse)
        assert result.status == 'error'
