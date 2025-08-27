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

"""Tests for the list_model_import_jobs tool."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    JobStatus,
    ListModelImportJobsRequest,
    ListModelImportJobsResponse,
    ModelImportJobSummary,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.list_model_import_jobs import (
    ListModelImportJobs,
)
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import FastMCP
from unittest.mock import AsyncMock, MagicMock


class TestListModelImportJobs:
    """Tests for the ListModelImportJobs tool."""

    @pytest.fixture
    def mock_mcp(self):
        """Fixture for mocking FastMCP."""
        mock = MagicMock(spec=FastMCP)
        mock.tool = MagicMock(return_value=MagicMock())
        return mock

    @pytest.fixture
    def mock_service(self):
        """Fixture for mocking ModelImportService."""
        mock = MagicMock()
        mock.list_model_import_jobs = AsyncMock()
        return mock

    @pytest.fixture
    def tool(self, mock_mcp, mock_service):
        """Fixture for creating a ListModelImportJobs instance."""
        return ListModelImportJobs(mock_mcp, mock_service)

    @pytest.fixture
    def mock_context(self):
        """Fixture for mocking MCP Context."""
        mock = MagicMock()
        mock.info = AsyncMock()
        mock.error = AsyncMock()
        return mock

    @pytest.fixture
    def sample_response(self):
        """Fixture for creating a sample ListModelImportJobsResponse."""
        return ListModelImportJobsResponse(
            modelImportJobSummaries=[
                ModelImportJobSummary(
                    jobArn='arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job-1',
                    jobName='test-job-1',
                    status=JobStatus.IN_PROGRESS,
                    creationTime=datetime(2025, 1, 1, 12, 0, 0),
                    lastModifiedTime=datetime(2025, 1, 1, 12, 0, 0),
                    endTime=None,
                    importedModelArn='arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model-1',
                    importedModelName='test-model-1',
                ),
                ModelImportJobSummary(
                    jobArn='arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job-2',
                    jobName='test-job-2',
                    status=JobStatus.COMPLETED,
                    creationTime=datetime(2025, 1, 2, 12, 0, 0),
                    lastModifiedTime=datetime(2025, 1, 2, 13, 0, 0),
                    endTime=datetime(2025, 1, 2, 13, 0, 0),
                    importedModelArn='arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model-2',
                    importedModelName='test-model-2',
                ),
                ModelImportJobSummary(
                    jobArn='arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job-3',
                    jobName='test-job-3',
                    status=JobStatus.FAILED,
                    creationTime=datetime(2025, 1, 3, 12, 0, 0),
                    lastModifiedTime=datetime(2025, 1, 3, 13, 0, 0),
                    endTime=datetime(2025, 1, 3, 13, 0, 0),
                    importedModelArn=None,
                    importedModelName=None,
                ),
            ],
            nextToken='next-token',
        )

    def test_initialization(self, mock_mcp, mock_service):
        """Test tool initialization."""
        tool = ListModelImportJobs(mock_mcp, mock_service)
        assert tool.model_import_service == mock_service
        assert mock_mcp.tool.call_count == 1

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_with_context(self, tool, mock_context, sample_response):
        """Test listing model import jobs with context."""
        # Setup
        tool.model_import_service.list_model_import_jobs.return_value = sample_response

        # Execute
        result = await tool.list_model_import_jobs(mock_context)

        # Verify
        tool.model_import_service.list_model_import_jobs.assert_called_once_with(None)
        mock_context.info.assert_called_once()
        assert 'Model Import Jobs' in result
        assert '| Job Name | Status | Created | Last Modified | Model Name | ARN |' in result
        assert '| `test-job-1` | 🔄 `InProgress`' in result
        assert '| `test-job-2` | ✅ `Completed`' in result
        assert '| `test-job-3` | ❌ `Failed`' in result

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_without_context(self, tool, sample_response):
        """Test listing model import jobs without context."""
        # Setup
        tool.model_import_service.list_model_import_jobs.return_value = sample_response

        # Execute
        result = await tool.list_model_import_jobs(None)

        # Verify
        tool.model_import_service.list_model_import_jobs.assert_called_once_with(None)
        assert 'Model Import Jobs' in result
        assert '| Job Name | Status | Created | Last Modified | Model Name | ARN |' in result
        assert '| `test-job-1` | 🔄 `InProgress`' in result
        assert '| `test-job-2` | ✅ `Completed`' in result
        assert '| `test-job-3` | ❌ `Failed`' in result

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_with_filters(self, tool, mock_context, sample_response):
        """Test listing model import jobs with filters."""
        # Setup
        request = ListModelImportJobsRequest(
            statusEquals=JobStatus.IN_PROGRESS,
            nameContains='test',
            creationTimeAfter=datetime(2025, 1, 1),
            creationTimeBefore=datetime(2025, 12, 31),
            sortBy='CreationTime',
            sortOrder='Descending',
        )
        tool.model_import_service.list_model_import_jobs.return_value = sample_response

        # Execute
        result = await tool.list_model_import_jobs(mock_context, request)

        # Verify
        tool.model_import_service.list_model_import_jobs.assert_called_once_with(request)
        assert 'Model Import Jobs' in result
        assert '| Job Name | Status | Created | Last Modified | Model Name | ARN |' in result
        assert '| `test-job-1` | 🔄 `InProgress`' in result

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_no_results(self, tool, mock_context):
        """Test listing model import jobs with no results."""
        # Setup
        response = ListModelImportJobsResponse(modelImportJobSummaries=[], nextToken=None)
        tool.model_import_service.list_model_import_jobs.return_value = response

        # Execute
        result = await tool.list_model_import_jobs(mock_context)

        # Verify
        tool.model_import_service.list_model_import_jobs.assert_called_once_with(None)
        assert 'Model Import Jobs' in result
        assert 'No model import jobs found.' in result

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_access_denied(self, tool, mock_context):
        """Test error handling when access is denied."""
        # Setup
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        tool.model_import_service.list_model_import_jobs.side_effect = ClientError(
            error_response, 'ListModelImportJobs'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.list_model_import_jobs(mock_context)

        # Verify the error details
        assert 'Error listing model import jobs' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_other_error(self, tool, mock_context):
        """Test error handling for other errors."""
        # Setup
        error_msg = 'Some other error'
        tool.model_import_service.list_model_import_jobs.side_effect = Exception(error_msg)

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.list_model_import_jobs(mock_context)

        # Verify the error details
        assert f'Error listing model import jobs: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()
