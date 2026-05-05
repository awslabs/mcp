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

"""Tests for the create_model_import_job tool."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    CreateModelImportJobRequest,
    JobStatus,
    ModelDataSource,
    ModelImportJob,
    S3DataSource,
    VpcConfig,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.create_model_import_job import (
    CreateModelImportJob,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import AppConfig
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from unittest.mock import AsyncMock, MagicMock


class TestCreateModelImportJob:
    """Tests for the CreateModelImportJob tool."""

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
        mock.create_model_import_job = AsyncMock()
        return mock

    @pytest.fixture
    def tool(self, mock_mcp, mock_service):
        """Fixture for creating a CreateModelImportJob instance."""
        return CreateModelImportJob(mock_mcp, mock_service)

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
        tool = CreateModelImportJob(mock_mcp, mock_service)
        assert tool.model_import_service == mock_service
        assert mock_mcp.tool.call_count == 1

    @pytest.mark.asyncio
    async def test_create_model_import_job_with_context(self, tool, mock_context, sample_job):
        """Test creating a model import job with context."""
        # Setup
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )
        tool.model_import_service.create_model_import_job.return_value = sample_job

        # Execute
        result = await tool.create_model_import_job(mock_context, request)

        # Verify
        tool.model_import_service.create_model_import_job.assert_called_once_with(request)
        mock_context.info.assert_called_once()
        assert 'Model Import Job: `test-job`' in result
        assert '**Status**: `InProgress`' in result
        assert '**Model Name**: `test-model`' in result
        assert '**Role ARN**: `arn:aws:iam::123456789012:role/test-role`' in result

    @pytest.mark.asyncio
    async def test_create_model_import_job_without_context(self, tool, sample_job):
        """Test creating a model import job without context."""
        # Setup
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )
        tool.model_import_service.create_model_import_job.return_value = sample_job

        # Execute
        result = await tool.create_model_import_job(None, request)

        # Verify
        tool.model_import_service.create_model_import_job.assert_called_once_with(request)
        assert 'Model Import Job: `test-job`' in result
        assert '**Status**: `InProgress`' in result
        assert '**Model Name**: `test-model`' in result
        assert '**Role ARN**: `arn:aws:iam::123456789012:role/test-role`' in result

    @pytest.mark.asyncio
    async def test_create_model_import_job_with_vpc_and_kms(self, tool, mock_context):
        """Test creating a model import job with VPC and KMS configuration."""
        # Setup
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
                securityGroupIds=['sg-123'],
                subnetIds=['subnet-123'],
            ),
            importedModelKmsKeyArn='test-kms-key-arn',
        )
        tool.model_import_service.create_model_import_job.return_value = job

        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=VpcConfig(
                securityGroupIds=['sg-123'],
                subnetIds=['subnet-123'],
            ),
            importedModelKmsKeyId='test-kms-key-id',
        )

        # Execute
        result = await tool.create_model_import_job(mock_context, request)

        # Verify
        tool.model_import_service.create_model_import_job.assert_called_once_with(request)
        assert '**VPC Config**: Enabled' in result
        assert '**KMS Key ARN**: `test-kms-key-arn`' in result

    @pytest.mark.asyncio
    async def test_create_model_import_job_completed(self, tool, mock_context):
        """Test creating a model import job that completes."""
        # Setup
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
        tool.model_import_service.create_model_import_job.return_value = job

        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )

        # Execute
        result = await tool.create_model_import_job(mock_context, request)

        # Verify
        tool.model_import_service.create_model_import_job.assert_called_once_with(request)
        assert '**Status**: `Completed`' in result
        assert '**Completed**: `2025-01-01 13:00:00`' in result

    @pytest.mark.asyncio
    async def test_create_model_import_job_error(self, tool, mock_context):
        """Test error handling when creating a model import job."""
        # Setup
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )
        error_msg = 'Test error'
        tool.model_import_service.create_model_import_job.side_effect = Exception(error_msg)

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.create_model_import_job(mock_context, request)

        # Verify the error details
        assert f'Error creating model import job: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_model_import_job_allow_write_enabled(
        self, mock_mcp, mock_service, mock_context
    ):
        """Test creating a model import job with allow_write enabled."""
        # Setup - allow_write is True
        mock_service.config = MagicMock(spec=AppConfig)
        mock_service.config.allow_write = True

        # Create a sample job
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
            vpcConfig=None,
            importedModelKmsKeyArn=None,
        )
        mock_service.create_model_import_job.return_value = job

        tool = CreateModelImportJob(mock_mcp, mock_service)

        # Create request
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )

        # Execute
        result = await tool.create_model_import_job(mock_context, request)

        # Verify
        mock_service.create_model_import_job.assert_called_once_with(request)
        mock_context.info.assert_called_once()
        assert 'Model Import Job: `test-job`' in result

    @pytest.mark.asyncio
    async def test_create_model_import_job_allow_write_disabled(
        self, mock_mcp, mock_service, mock_context
    ):
        """Test creating a model import job with allow_write disabled."""
        # Setup - allow_write is False
        mock_service.config = MagicMock(spec=AppConfig)
        mock_service.config.allow_write = False

        # We need to patch the service's create_model_import_job method to raise ToolError
        # but we don't want the tool's create_model_import_job method to catch and re-raise it
        error_msg = 'Creating model import job requires --allow-write flag'
        mock_service.create_model_import_job.side_effect = ToolError(error_msg)

        tool = CreateModelImportJob(mock_mcp, mock_service)

        # Create request
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.create_model_import_job(mock_context, request)

        # Verify the error details
        assert f'Error creating model import job: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()
