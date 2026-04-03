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

"""Tests for the get_model_import_job tool."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    JobStatus,
    ModelDataSource,
    ModelImportJob,
    S3DataSource,
    VpcConfig,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.get_model_import_job import (
    GetModelImportJob,
)
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import FastMCP
from unittest.mock import AsyncMock, MagicMock


class TestGetModelImportJob:
    """Tests for the GetModelImportJob tool."""

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
        mock.get_model_import_job = AsyncMock()
        return mock

    @pytest.fixture
    def tool(self, mock_mcp, mock_service):
        """Fixture for creating a GetModelImportJob instance."""
        return GetModelImportJob(mock_mcp, mock_service)

    @pytest.fixture
    def mock_context(self):
        """Fixture for mocking MCP Context."""
        mock = MagicMock()
        mock.info = AsyncMock()
        mock.error = AsyncMock()
        return mock

    @pytest.fixture
    def sample_job(self):
        """Fixture for creating a sample ModelImportJob."""
        return ModelImportJob(
            jobArn='arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job',
            jobName='test-job',
            importedModelName='test-model',
            importedModelArn='arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model',
            roleArn='arn:aws:iam::123456789012:role/test-role',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            status=JobStatus.IN_PROGRESS,
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            lastModifiedTime=datetime(2025, 1, 1, 12, 0, 0),
            endTime=None,
            failureMessage=None,
            vpcConfig=None,
            importedModelKmsKeyArn=None,
        )

    def test_initialization(self, mock_mcp, mock_service):
        """Test tool initialization."""
        tool = GetModelImportJob(mock_mcp, mock_service)
        assert tool.model_import_service == mock_service
        assert mock_mcp.tool.call_count == 1

    @pytest.mark.asyncio
    async def test_get_model_import_job_with_context(self, tool, mock_context, sample_job):
        """Test getting a model import job with context."""
        # Setup
        job_identifier = 'test-job'
        tool.model_import_service.get_model_import_job.return_value = sample_job

        # Execute
        result = await tool.get_model_import_job(mock_context, job_identifier)

        # Verify
        tool.model_import_service.get_model_import_job.assert_called_once_with(job_identifier)
        mock_context.info.assert_called_once()
        assert 'Model Import Job: `test-job`' in result
        assert '**Status**: 🔄 `InProgress`' in result
        assert '**Model Name**: `test-model`' in result
        assert '**Role ARN**: `arn:aws:iam::123456789012:role/test-role`' in result

    @pytest.mark.asyncio
    async def test_get_model_import_job_without_context(self, tool, sample_job):
        """Test getting a model import job without context."""
        # Setup
        job_identifier = 'test-job'
        tool.model_import_service.get_model_import_job.return_value = sample_job

        # Execute
        result = await tool.get_model_import_job(None, job_identifier)

        # Verify
        tool.model_import_service.get_model_import_job.assert_called_once_with(job_identifier)
        assert 'Model Import Job: `test-job`' in result
        assert '**Status**: 🔄 `InProgress`' in result
        assert '**Model Name**: `test-model`' in result
        assert '**Role ARN**: `arn:aws:iam::123456789012:role/test-role`' in result

    @pytest.mark.asyncio
    async def test_get_model_import_job_completed(self, tool, mock_context):
        """Test getting a completed model import job."""
        # Setup
        job_identifier = 'test-job'
        job = ModelImportJob(
            jobArn='test-job-arn',
            jobName='test-job',
            importedModelName='test-model',
            importedModelArn='test-model-arn',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            status=JobStatus.COMPLETED,
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            lastModifiedTime=datetime(2025, 1, 1, 13, 0, 0),
            endTime=datetime(2025, 1, 1, 13, 0, 0),
            failureMessage=None,
            vpcConfig=None,
            importedModelKmsKeyArn=None,
        )
        tool.model_import_service.get_model_import_job.return_value = job

        # Execute
        result = await tool.get_model_import_job(mock_context, job_identifier)

        # Verify
        assert '**Status**: ✅ `Completed`' in result
        assert '**Completed**: `2025-01-01 13:00:00`' in result

    @pytest.mark.asyncio
    async def test_get_model_import_job_failed(self, tool, mock_context):
        """Test getting a failed model import job."""
        # Setup
        job_identifier = 'test-job'
        job = ModelImportJob(
            jobArn='test-job-arn',
            jobName='test-job',
            importedModelName='test-model',
            importedModelArn='test-model-arn',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            status=JobStatus.FAILED,
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            lastModifiedTime=datetime(2025, 1, 1, 13, 0, 0),
            endTime=datetime(2025, 1, 1, 13, 0, 0),
            failureMessage='Test failure message',
            vpcConfig=None,
            importedModelKmsKeyArn=None,
        )
        tool.model_import_service.get_model_import_job.return_value = job

        # Execute
        result = await tool.get_model_import_job(mock_context, job_identifier)

        # Verify
        assert '**Status**: ❌ `Failed`' in result
        assert '**Failure Reason**: `Test failure message`' in result
        assert '**Completed**: `2025-01-01 13:00:00`' in result

    @pytest.mark.asyncio
    async def test_get_model_import_job_with_vpc_and_kms(self, tool, mock_context):
        """Test getting a model import job with VPC and KMS configuration."""
        # Setup
        job_identifier = 'test-job'
        job = ModelImportJob(
            jobArn='test-job-arn',
            jobName='test-job',
            importedModelName='test-model',
            importedModelArn='test-model-arn',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            status=JobStatus.IN_PROGRESS,
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            lastModifiedTime=datetime(2025, 1, 1, 12, 0, 0),
            endTime=None,
            failureMessage=None,
            vpcConfig=VpcConfig(
                securityGroupIds=['sg-123', 'sg-456'],
                subnetIds=['subnet-123', 'subnet-456'],
            ),
            importedModelKmsKeyArn='test-kms-key-arn',
        )
        tool.model_import_service.get_model_import_job.return_value = job

        # Execute
        result = await tool.get_model_import_job(mock_context, job_identifier)

        # Verify
        assert '**VPC Config**:' in result
        assert 'Subnet IDs: `subnet-123, subnet-456`' in result
        assert 'Security Groups: `sg-123, sg-456`' in result
        assert '**KMS Key ARN**: `test-kms-key-arn`' in result

    @pytest.mark.asyncio
    async def test_get_model_import_job_not_found(self, tool, mock_context):
        """Test error handling when job is not found."""
        # Setup
        job_identifier = 'test-job'
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Job not found'}}
        tool.model_import_service.get_model_import_job.side_effect = ClientError(
            error_response, 'GetModelImportJob'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.get_model_import_job(mock_context, job_identifier)

        # Verify the error details
        assert 'Error getting model import job' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_import_job_access_denied(self, tool, mock_context):
        """Test error handling when access is denied."""
        # Setup
        job_identifier = 'test-job'
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        tool.model_import_service.get_model_import_job.side_effect = ClientError(
            error_response, 'GetModelImportJob'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.get_model_import_job(mock_context, job_identifier)

        # Verify the error details
        assert 'Error getting model import job' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_model_import_job_other_error(self, tool, mock_context):
        """Test error handling for other errors."""
        # Setup
        job_identifier = 'test-job'
        error_msg = 'Some other error'
        tool.model_import_service.get_model_import_job.side_effect = Exception(error_msg)

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.get_model_import_job(mock_context, job_identifier)

        # Verify the error details
        assert f'Error getting model import job: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()
