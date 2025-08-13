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

"""Tests for the ModelImportService class."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    CreateModelImportJobRequest,
    JobStatus,
    ListModelImportJobsRequest,
    ModelDataSource,
    S3DataSource,
    Tag,
    VpcConfig,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.services import (
    ModelImportService,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import AppConfig
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestModelImportService:
    """Tests for the ModelImportService class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for mocking BedrockModelImportClient."""
        mock = MagicMock()
        mock._find_model_in_s3 = MagicMock()
        mock.create_model_import_job = MagicMock()
        mock.get_model_import_job = MagicMock()
        mock.list_model_import_jobs = MagicMock()
        return mock

    @pytest.fixture
    def mock_config(self) -> AppConfig:
        """Fixture for mocking AppConfig."""
        mock = MagicMock(spec=AppConfig)
        mock.allow_write = True
        mock_aws_config = MagicMock()
        mock_aws_config.region = 'us-east-1'
        mock_aws_config.s3_bucket_name = 'test-bucket'
        mock.aws_config = mock_aws_config
        return mock

    @pytest.fixture
    def service(self, mock_client, mock_config):
        """Fixture for creating a ModelImportService instance with a mocked client."""
        return ModelImportService(mock_client, mock_config)

    def test_initialization(self, mock_client, mock_config):
        """Test service initialization."""
        service = ModelImportService(mock_client, mock_config)
        assert service.client == mock_client

    @pytest.mark.asyncio
    async def test_create_model_import_job_with_s3_bucket_env(self, service, mock_config):
        """Test creating a model import job with S3 bucket from environment."""
        # Setup
        mock_config.aws_config.s3_bucket = 'test-bucket'
        mock_config.aws_config.role_arn = 'test-role-arn'

        service.client._find_model_in_s3.return_value = 's3://test-bucket/models/test-model'
        service.client.create_model_import_job.return_value = {'jobArn': 'test-job-arn'}
        service.client.get_model_import_job.return_value = {
            'jobArn': 'test-job-arn',
            'jobName': 'test-job-20250101-120000',
            'importedModelName': 'test-model-20250101-120000',
            'importedModelArn': 'test-model-arn',
            'roleArn': 'test-role-arn',
            'modelDataSource': {'s3DataSource': {'s3Uri': 's3://test-bucket/models/test-model'}},
            'status': 'InProgress',
            'creationTime': datetime.now(),
            'lastModifiedTime': datetime.now(),
        }

        # Create request
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn=None,  # Should be filled from environment
            modelDataSource=None,  # Should be filled from S3 bucket
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )

        # Execute
        result = await service.create_model_import_job(request)

        # Verify
        service.client._find_model_in_s3.assert_called_once_with('test-bucket', 'test-model')
        assert result.job_arn == 'test-job-arn'
        assert result.imported_model_name == 'test-model-20250101-120000'
        assert result.role_arn == 'test-role-arn'

        # Verify the request was modified correctly
        assert request.role_arn == 'test-role-arn'
        assert request.model_data_source is not None
        assert (
            request.model_data_source.s3_data_source.s3_uri == 's3://test-bucket/models/test-model'
        )

    @patch(
        'awslabs.aws_bedrock_custom_model_import_mcp_server.services.model_import_service.get_iam_role_arn_from_sts',
        new_callable=MagicMock,
    )
    @pytest.mark.asyncio
    async def test_create_model_import_job_with_sts_role(
        self, mock_get_role_arn, service, mock_config
    ):
        """Test creating a model import job with role ARN from STS."""
        # Setup
        mock_config.aws_config.s3_bucket = 'test-bucket'
        mock_config.aws_config.role_arn = None  # No role ARN in config, should use STS

        # Mock STS role ARN
        mock_get_role_arn.return_value = 'sts-role-arn'

        # Mock client methods
        service.client.create_model_import_job.return_value = {'jobArn': 'test-job-arn'}
        service.client.get_model_import_job.return_value = {
            'jobArn': 'test-job-arn',
            'jobName': 'test-job-20250101-120000',
            'importedModelName': 'test-model-20250101-120000',
            'importedModelArn': 'test-model-arn',
            'roleArn': 'sts-role-arn',
            'modelDataSource': {'s3DataSource': {'s3Uri': 's3://test-bucket/models/test-model'}},
            'status': 'InProgress',
            'creationTime': datetime.now(),
            'lastModifiedTime': datetime.now(),
        }

        # Create request
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn=None,
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
        result = await service.create_model_import_job(request)

        # Verify
        mock_get_role_arn.assert_called_once_with()
        assert result.job_arn == 'test-job-arn'
        assert result.role_arn == 'sts-role-arn'

        # Verify the request was modified correctly
        assert request.role_arn == 'sts-role-arn'

    @pytest.mark.asyncio
    async def test_create_model_import_job_with_all_parameters(self, service):
        """Test creating a model import job with all parameters."""
        # Setup
        # Mock client methods
        service.client.create_model_import_job.return_value = {'jobArn': 'test-job-arn'}
        service.client.get_model_import_job.return_value = {
            'jobArn': 'test-job-arn',
            'jobName': 'test-job-20250101-120000',
            'importedModelName': 'test-model-20250101-120000',
            'importedModelArn': 'test-model-arn',
            'roleArn': 'test-role-arn',
            'modelDataSource': {'s3DataSource': {'s3Uri': 's3://test-bucket/models/test-model'}},
            'status': 'InProgress',
            'creationTime': datetime.now(),
            'lastModifiedTime': datetime.now(),
            'vpcConfig': {'securityGroupIds': ['sg-123'], 'subnetIds': ['subnet-123']},
            'importedModelKmsKeyArn': 'kms-key-arn',
        }

        # Create request with all parameters
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            jobTags=[Tag(key='job-key', value='job-value')],
            importedModelTags=[Tag(key='model-key', value='model-value')],
            vpcConfig=VpcConfig(securityGroupIds=['sg-123'], subnetIds=['subnet-123']),
            importedModelKmsKeyId='kms-key-id',
            clientRequestToken='request-token',
        )

        # Execute
        result = await service.create_model_import_job(request)

        # Verify
        assert result.job_arn == 'test-job-arn'
        assert result.imported_model_name == 'test-model-20250101-120000'
        assert result.vpc_config is not None
        assert result.imported_model_kms_key_arn == 'kms-key-arn'

        # Verify create_args were prepared correctly
        create_args = service._prepare_create_job_args(request)
        assert create_args['jobName'] == request.job_name
        assert create_args['importedModelName'] == request.imported_model_name
        assert create_args['roleArn'] == request.role_arn
        # Ensure model_data_source is not None before calling model_dump
        assert request.model_data_source is not None
        assert create_args['modelDataSource'] == request.model_data_source.model_dump(
            by_alias=True
        )

        # Check optional parameters
        if request.job_tags:
            assert create_args['jobTags'] == [tag.model_dump() for tag in request.job_tags]
        if request.imported_model_tags:
            assert create_args['importedModelTags'] == [
                tag.model_dump() for tag in request.imported_model_tags
            ]
        if request.vpc_config:
            assert create_args['vpcConfig'] == request.vpc_config.model_dump()
        if request.imported_model_kms_key_id:
            assert create_args['importedModelKmsKeyId'] == request.imported_model_kms_key_id
        if request.client_request_token:
            assert create_args['clientRequestToken'] == request.client_request_token

    @pytest.mark.asyncio
    async def test_create_model_import_job_missing_model_data_source(self, service, mock_config):
        """Test creating a model import job with missing model data source."""
        # Setup
        mock_config.aws_config.s3_bucket = 'test-bucket'

        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=None,  # Missing model data source
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )

        # Mock client methods
        service.client._find_model_in_s3.return_value = None  # No model found in S3

        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            await service.create_model_import_job(request)

        # Verify the error message
        assert 'Model test-model not found in bucket test-bucket' in str(excinfo.value)

    def test_create_model_import_job_prepare_args_assertion(self, service):
        """Test assertion in _prepare_create_job_args when model_data_source is None."""
        # Setup
        request = CreateModelImportJobRequest(
            jobName='test-job',
            importedModelName='test-model',
            roleArn='test-role-arn',
            modelDataSource=None,  # This will cause the assertion to fail
            jobTags=None,
            importedModelTags=None,
            clientRequestToken=None,
            vpcConfig=None,
            importedModelKmsKeyId=None,
        )

        # Execute and verify
        with pytest.raises(AssertionError) as excinfo:
            service._prepare_create_job_args(request)

        # Verify the assertion message
        assert 'Model data source is required' in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_with_filters(self, service):
        """Test listing model import jobs with filters."""
        # Setup
        request = ListModelImportJobsRequest(
            statusEquals=JobStatus.IN_PROGRESS,
            creationTimeAfter=datetime(2025, 1, 1),
            creationTimeBefore=datetime(2025, 12, 31),
            nameContains='test',
            sortBy='CreationTime',
            sortOrder='Descending',
        )

        # Mock client response
        service.client.list_model_import_jobs.return_value = {
            'modelImportJobSummaries': [
                {
                    'jobArn': 'job-arn-1',
                    'jobName': 'test-job-1',
                    'status': 'InProgress',
                    'creationTime': datetime(2025, 6, 1),
                    'lastModifiedTime': datetime(2025, 6, 1),
                    'importedModelArn': 'model-arn-1',
                    'importedModelName': 'test-model-1',
                },
                {
                    'jobArn': 'job-arn-2',
                    'jobName': 'test-job-2',
                    'status': 'InProgress',
                    'creationTime': datetime(2025, 5, 1),
                    'lastModifiedTime': datetime(2025, 5, 1),
                    'importedModelArn': 'model-arn-2',
                    'importedModelName': 'test-model-2',
                },
            ],
            'nextToken': 'next-token',
        }

        # Execute
        result = await service.list_model_import_jobs(request)

        # Verify
        service.client.list_model_import_jobs.assert_called_once_with(
            statusEquals=JobStatus.IN_PROGRESS,
            creationTimeAfter=datetime(2025, 1, 1),
            creationTimeBefore=datetime(2025, 12, 31),
            nameContains='test',
            sortBy='CreationTime',
            sortOrder='Descending',
        )

        # Verify result
        assert len(result.model_import_job_summaries) == 2
        assert result.model_import_job_summaries[0].job_name == 'test-job-1'
        assert result.model_import_job_summaries[1].job_name == 'test-job-2'
        assert result.next_token == 'next-token'

    @pytest.mark.asyncio
    async def test_list_model_import_jobs_without_filters(self, service):
        """Test listing model import jobs without filters."""
        # Setup
        # Mock client response
        service.client.list_model_import_jobs.return_value = {
            'modelImportJobSummaries': [
                {
                    'jobArn': 'job-arn-1',
                    'jobName': 'test-job-1',
                    'status': 'Completed',
                    'creationTime': datetime(2025, 6, 1),
                    'lastModifiedTime': datetime(2025, 6, 1),
                    'endTime': datetime(2025, 6, 2),
                    'importedModelArn': 'model-arn-1',
                    'importedModelName': 'test-model-1',
                }
            ]
        }

        # Execute
        result = await service.list_model_import_jobs()

        # Verify
        service.client.list_model_import_jobs.assert_called_once_with()

        # Verify result
        assert len(result.model_import_job_summaries) == 1
        assert result.model_import_job_summaries[0].job_name == 'test-job-1'
        assert result.model_import_job_summaries[0].status == 'Completed'
        assert result.model_import_job_summaries[0].end_time == datetime(2025, 6, 2)
        assert result.next_token is None

    @pytest.mark.asyncio
    async def test_get_model_import_job_success(self, service):
        """Test getting a model import job successfully."""
        # Setup
        job_name = 'test-job'

        # Mock client response
        service.client.get_model_import_job.return_value = {
            'jobArn': 'job-arn',
            'jobName': job_name,
            'importedModelName': 'test-model',
            'importedModelArn': 'model-arn',
            'roleArn': 'role-arn',
            'modelDataSource': {'s3DataSource': {'s3Uri': 's3://bucket/model'}},
            'status': 'Completed',
            'creationTime': datetime(2025, 6, 1),
            'lastModifiedTime': datetime(2025, 6, 1),
            'endTime': datetime(2025, 6, 2),
        }

        # Execute
        result = await service.get_model_import_job(job_name)

        # Verify
        service.client.get_model_import_job.assert_called_once_with(job_name)

        # Verify result
        assert result.job_arn == 'job-arn'
        assert result.job_name == job_name
        assert result.imported_model_name == 'test-model'
        assert result.status == 'Completed'
        assert result.end_time == datetime(2025, 6, 2)

    @pytest.mark.asyncio
    async def test_get_model_import_job_other_client_error(self, service):
        """Test getting a model import job with a non-ValidationException ClientError."""
        # Setup
        job_name = 'test-job'

        # Mock client methods
        # Call fails with AccessDeniedException
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        service.client.get_model_import_job.side_effect = ClientError(
            error_response, 'GetModelImportJob'
        )

        # Execute and verify
        with pytest.raises(ClientError) as excinfo:
            await service.get_model_import_job(job_name)

        # Verify the error details
        assert excinfo.value.response['Error']['Code'] == 'AccessDeniedException'
        service.client._find_job_by_approximate_match.assert_not_called()

    def test_append_datetime_suffix(self, service):
        """Test appending datetime suffix to a name."""
        # Setup
        name = 'test-name'

        # Execute
        result = service._append_datetime_suffix(name)

        # Verify
        assert result.startswith(name + '-')
        assert len(result) > len(name) + 1  # Should have added a suffix

        # Verify format (should be something like test-name-20250101-120000)
        parts = result.split('-')
        assert len(parts) >= 4  # name + date + time

        # Last two parts should be date and time
        date_part = parts[-2]
        time_part = parts[-1]

        assert len(date_part) == 8  # YYYYMMDD
        assert len(time_part) == 6  # HHMMSS
