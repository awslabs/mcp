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

"""Tests for the BedrockModelImportClient class."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.client import (
    BedrockModelImportClient,
)
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, call, patch


class TestBedrockModelImportClient:
    """Tests for the BedrockModelImportClient class."""

    @pytest.fixture
    def mock_aws_client(self):
        """Fixture for mocking AWS client helper."""
        with patch(
            'awslabs.aws_bedrock_custom_model_import_mcp_server.client.get_aws_client'
        ) as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_aws_client):
        """Fixture for creating a BedrockModelImportClient instance with mocked AWS clients."""
        mock_bedrock = MagicMock()
        mock_s3 = MagicMock()
        mock_aws_client.side_effect = [mock_bedrock, mock_s3]

        client = BedrockModelImportClient(region_name='us-west-2')

        # Reset the mock to clear the calls from initialization
        mock_aws_client.reset_mock()

        return client

    def test_initialization(self, mock_aws_client):
        """Test client initialization."""
        # Create client
        client = BedrockModelImportClient(region_name='us-west-2')

        # Verify AWS clients were created with correct parameters
        mock_aws_client.assert_has_calls(
            [
                call('bedrock', region_name='us-west-2', profile_name=None),
                call('s3', region_name='us-west-2', profile_name=None),
            ]
        )

        # Verify client attributes
        assert client.region_name == 'us-west-2'
        assert client.bedrock_client == mock_aws_client.return_value
        assert client.s3_client == mock_aws_client.return_value

    async def test_create_model_import_job_success(self, client: BedrockModelImportClient):
        """Test successful creation of a model import job."""
        # Setup
        create_args = {
            'jobName': 'test-job',
            'importedModelName': 'test-model',
            'modelDataSource': {'s3DataSource': {'s3Uri': 's3://bucket/model'}},
            'roleArn': 'arn:aws:iam::123456789012:role/test-role',
        }
        expected_response = {
            'jobArn': 'arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job'
        }
        client.bedrock_client.create_model_import_job = MagicMock(return_value=expected_response)

        # Execute
        response = client.create_model_import_job(create_args)

        # Verify
        client.bedrock_client.create_model_import_job.assert_called_once_with(**create_args)
        assert response == expected_response

    async def test_create_model_import_job_failure(self, client: BedrockModelImportClient):
        """Test failure when creating a model import job."""
        # Setup
        create_args = {'jobName': 'test-job'}
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid request'}}
        client.bedrock_client.create_model_import_job = MagicMock(
            side_effect=ClientError(error_response, 'CreateModelImportJob')
        )

        # Execute and verify
        with pytest.raises(ClientError) as excinfo:
            client.create_model_import_job(create_args)

        # Verify the error details
        assert excinfo.value.response['Error']['Code'] == 'ValidationException'
        client.bedrock_client.create_model_import_job.assert_called_once_with(**create_args)

    async def test_get_model_import_job_success(self, client: BedrockModelImportClient):
        """Test successful retrieval of a model import job."""
        # Setup
        job_name = 'test-job'
        expected_response = {
            'jobArn': 'arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job',
            'jobName': job_name,
            'status': 'InProgress',
        }
        client.bedrock_client.get_model_import_job = MagicMock(return_value=expected_response)

        # Execute
        response = client.get_model_import_job(job_name)

        # Verify
        client.bedrock_client.get_model_import_job.assert_called_once_with(jobIdentifier=job_name)
        assert response == expected_response

    async def test_get_model_import_job_with_approximate_match(
        self, client: BedrockModelImportClient
    ):
        """Test retrieval of a model import job with approximate matching."""
        # Setup
        job_name = 'test-job'
        matched_job_name = 'test-job-20250101-120000'

        # Mock list_model_import_jobs for nameContains
        client.bedrock_client.list_model_import_jobs = MagicMock(
            return_value={
                'modelImportJobSummaries': [
                    {'jobName': matched_job_name, 'status': 'InProgress'},
                ]
            }
        )

        # First get_model_import_job call fails, second succeeds
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Job not found'}}
        client.bedrock_client.get_model_import_job = MagicMock(
            side_effect=[
                ClientError(error_response, 'GetModelImportJob'),
                {
                    'jobArn': f'arn:aws:bedrock:us-west-2:123456789012:model-import-job/{matched_job_name}',
                    'jobName': matched_job_name,
                    'status': 'InProgress',
                },
            ]
        )

        # Execute
        response = client.get_model_import_job(job_name)

        # Verify
        client.bedrock_client.list_model_import_jobs.assert_called_with(nameContains=job_name)
        client.bedrock_client.get_model_import_job.assert_has_calls(
            [call(jobIdentifier=job_name), call(jobIdentifier=matched_job_name)]
        )
        assert response['jobName'] == matched_job_name

    async def test_get_model_import_job_approximate_match_failure(
        self, client: BedrockModelImportClient
    ):
        """Test failure when approximate matching also fails."""
        # Setup
        job_name = 'test-job'

        # First get_model_import_job call fails
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Job not found'}}
        client.bedrock_client.get_model_import_job = MagicMock(
            side_effect=ClientError(error_response, 'GetModelImportJob')
        )

        # nameContains returns no results
        client.bedrock_client.list_model_import_jobs = MagicMock(
            return_value={'modelImportJobSummaries': []}
        )

        # Paginator for approximate matching also returns no results
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [{'modelImportJobSummaries': []}]
        client.bedrock_client.get_paginator.return_value = paginator_mock

        # Execute and verify
        with pytest.raises(ValueError) as excinfo:
            client.get_model_import_job(job_name)

        # Verify the error message
        assert f'Could not find a job matching the name or ARN: {job_name}' in str(excinfo.value)
        client.bedrock_client.list_model_import_jobs.assert_called_with(nameContains=job_name)

    async def test_list_model_import_jobs(self, client: BedrockModelImportClient):
        """Test listing model import jobs."""
        # Setup
        expected_response = {
            'modelImportJobSummaries': [
                {'jobName': 'job1', 'status': 'Completed'},
                {'jobName': 'job2', 'status': 'InProgress'},
            ],
            'nextToken': 'token123',
        }
        client.bedrock_client.list_model_import_jobs = MagicMock(return_value=expected_response)

        # Execute
        response = client.list_model_import_jobs(statusEquals='InProgress')

        # Verify
        client.bedrock_client.list_model_import_jobs.assert_called_once_with(
            statusEquals='InProgress'
        )
        assert response == expected_response

    async def test_get_imported_model_success(self, client: BedrockModelImportClient):
        """Test successful retrieval of an imported model."""
        # Setup
        model_name = 'test-model'
        expected_response = {
            'modelArn': 'arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model',
            'modelName': model_name,
        }
        client.bedrock_client.get_imported_model = MagicMock(return_value=expected_response)

        # Execute
        response = client.get_imported_model(model_name)

        # Verify
        client.bedrock_client.get_imported_model.assert_called_once_with(
            modelIdentifier=model_name
        )
        assert response == expected_response

    async def test_get_imported_model_with_approximate_match(
        self, client: BedrockModelImportClient
    ):
        """Test retrieval of an imported model with approximate matching."""
        # Setup
        model_name = 'test-model'
        matched_model_name = 'test-model-20250101-120000'

        # Mock list_imported_models for nameContains
        client.bedrock_client.list_imported_models = MagicMock(
            return_value={
                'modelSummaries': [
                    {'modelName': matched_model_name, 'status': 'InProgress'},
                ]
            }
        )

        # First get_imported_model call fails, second succeeds
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Model not found'}}
        client.bedrock_client.get_imported_model = MagicMock(
            side_effect=[
                ClientError(error_response, 'GetImportedModel'),
                {
                    'modelArn': f'arn:aws:bedrock:us-west-2:123456789012:custom-model/{matched_model_name}',
                    'modelName': matched_model_name,
                },
            ]
        )

        # Execute
        response = client.get_imported_model(model_name)

        # Verify
        client.bedrock_client.list_imported_models.assert_called_with(nameContains=model_name)
        client.bedrock_client.get_imported_model.assert_has_calls(
            [call(modelIdentifier=model_name), call(modelIdentifier=matched_model_name)]
        )
        assert response['modelName'] == matched_model_name

    async def test_list_imported_models(self, client: BedrockModelImportClient):
        """Test listing imported models."""
        # Setup
        expected_response = {
            'modelSummaries': [
                {'modelName': 'model1'},
                {'modelName': 'model2'},
            ],
            'nextToken': 'token123',
        }
        client.bedrock_client.list_imported_models = MagicMock(return_value=expected_response)

        # Execute
        response = client.list_imported_models(nameContains='model')

        # Verify
        client.bedrock_client.list_imported_models.assert_called_once_with(nameContains='model')
        assert response == expected_response

    async def test_delete_imported_model(self, client: BedrockModelImportClient):
        """Test deleting an imported model."""
        # Setup
        model_identifier = 'test-model'
        client.bedrock_client.delete_imported_model = MagicMock()

        # Execute
        client.delete_imported_model(model_identifier)

        # Verify
        client.bedrock_client.delete_imported_model.assert_called_once_with(
            modelIdentifier=model_identifier
        )

    async def test_delete_imported_model_failure(self, client: BedrockModelImportClient):
        """Test failure when deleting an imported model."""
        # Setup
        model_identifier = 'test-model'
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Model not found'}}
        client.bedrock_client.delete_imported_model = MagicMock(
            side_effect=ClientError(error_response, 'DeleteImportedModel')
        )

        # Execute and verify
        with pytest.raises(ClientError) as excinfo:
            client.delete_imported_model(model_identifier)

        # Verify the error details
        assert excinfo.value.response['Error']['Code'] == 'ValidationException'
        client.bedrock_client.delete_imported_model.assert_called_once_with(
            modelIdentifier=model_identifier
        )

    async def test_find_model_in_s3(self, client: BedrockModelImportClient):
        """Test the find_model_in_s3 method."""
        # Setup
        bucket_name = 'test-bucket'

        # Mock S3 paginator and response
        mock_paginator = MagicMock()
        client.s3_client.get_paginator.return_value = mock_paginator

        # Test exact match
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    # Valid model folder with .safetensors file
                    {'Key': 'models/test-model/model.safetensors'},
                    {'Key': 'models/test-model/config.json'},
                    # Another valid model folder
                    {'Key': 'models/test-model-v2/pytorch_model.safetensors'},
                    {'Key': 'models/test-model-v2/config.json'},
                    # Invalid folder - no .safetensors file
                    {'Key': 'models/other-model/v1/model.bin'},
                    {'Key': 'models/other-model/v1/config.json'},
                    # Valid model folder with multiple .safetensors files
                    {'Key': 'models/test_model_variant/model-00001-of-00002.safetensors'},
                    {'Key': 'models/test_model_variant/model-00002-of-00002.safetensors'},
                    # Valid model folder in different location
                    {'Key': 'archive/old-test-model/model.safetensors'},
                ]
            }
        ]

        # Test exact match
        result = client._find_model_in_s3(bucket_name, 'test-model')
        assert result == 's3://test-bucket/models/test-model'

        # Test approximate match with version
        result = client._find_model_in_s3(bucket_name, 'test model v2')
        assert result == 's3://test-bucket/models/test-model-v2'

        # Test approximate match with underscores
        result = client._find_model_in_s3(bucket_name, 'test model variant')
        assert result == 's3://test-bucket/models/test_model_variant'

        # Test approximate match with prefix
        result = client._find_model_in_s3(bucket_name, 'old test model')
        assert result == 's3://test-bucket/archive/old-test-model'

        # Test model not found
        result = client._find_model_in_s3(bucket_name, 'non-existent')
        assert result is None

        # Test empty bucket
        mock_paginator.paginate.return_value = [{'Contents': []}]
        result = client._find_model_in_s3(bucket_name, 'test-model')
        assert result is None

        # Test folder without .safetensors file
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'models/test-model/data.json'},
                    {'Key': 'models/test-model/model.bin'},
                ]
            }
        ]
        result = client._find_model_in_s3(bucket_name, 'test-model')
        assert result is None

        # Test folder with only .bin files
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {'Key': 'models/test-model/pytorch_model.bin'},
                    {'Key': 'models/test-model/config.json'},
                ]
            }
        ]
        result = client._find_model_in_s3(bucket_name, 'test-model')
        assert result is None

        # Test error handling
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
        client.s3_client.get_paginator.side_effect = ClientError(error_response, 'ListObjects')
        result = client._find_model_in_s3(bucket_name, 'test-model')
        assert result is None

        client.s3_client.get_paginator.side_effect = Exception('Test error')
        with pytest.raises(Exception, match='Test error'):
            client._find_model_in_s3(bucket_name, 'test-model')

    async def test_find_job_by_approximate_match(self, client: BedrockModelImportClient):
        """Test the _find_job_by_approximate_match method."""
        # Setup
        job_name = 'test-job'

        # Test successful nameContains match
        client.bedrock_client.list_model_import_jobs.return_value = {
            'modelImportJobSummaries': [
                {'jobName': 'test-job', 'status': 'InProgress'},
            ]
        }
        result = client._find_job_by_approximate_match(job_name)
        assert result == 'test-job'
        client.bedrock_client.list_model_import_jobs.assert_called_with(nameContains=job_name)

        # Test multiple nameContains matches with preference for active jobs
        client.bedrock_client.list_model_import_jobs.return_value = {
            'modelImportJobSummaries': [
                {'jobName': 'test-job-v2', 'status': 'Completed'},
                {'jobName': 'test-job', 'status': 'InProgress'},
            ]
        }
        result = client._find_job_by_approximate_match(job_name)
        assert result == 'test-job'  # Should prefer the InProgress job

        # Test nameContains returns no results, falls back to approximate matching
        # First call with nameContains returns empty list
        client.bedrock_client.list_model_import_jobs.side_effect = [
            {'modelImportJobSummaries': []},  # nameContains returns empty
        ]
        # Then paginator for approximate matching returns results
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {
                'modelImportJobSummaries': [
                    {'jobName': 'test-job', 'status': 'InProgress'},
                    {'jobName': 'test-job-v2', 'status': 'Completed'},
                ]
            }
        ]
        client.bedrock_client.get_paginator.return_value = paginator_mock

        result = client._find_job_by_approximate_match(job_name)
        assert result == 'test-job'  # Should find via approximate matching

        # Test nameContains throws exception, falls back to approximate matching
        client.bedrock_client.list_model_import_jobs.side_effect = Exception('API Error')
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {
                'modelImportJobSummaries': [
                    {'jobName': 'test-job', 'status': 'InProgress'},
                ]
            }
        ]
        client.bedrock_client.get_paginator.return_value = paginator_mock

        result = client._find_job_by_approximate_match(job_name)
        assert result == 'test-job'  # Should find via approximate matching

        # Test both nameContains and approximate matching find nothing
        client.bedrock_client.list_model_import_jobs.side_effect = [
            {'modelImportJobSummaries': []},  # nameContains returns empty
        ]
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {'modelImportJobSummaries': []}  # approximate matching also returns empty
        ]
        client.bedrock_client.get_paginator.return_value = paginator_mock

        result = client._find_job_by_approximate_match(job_name)
        assert result is None

        # Test error handling in approximate matching
        client.bedrock_client.list_model_import_jobs.side_effect = [
            {'modelImportJobSummaries': []},  # nameContains returns empty
        ]
        client.bedrock_client.get_paginator.side_effect = Exception('Test error')
        with pytest.raises(Exception, match='Test error'):
            client._find_job_by_approximate_match(job_name)

    async def test_find_model_by_approximate_match(self, client: BedrockModelImportClient):
        """Test the _find_model_by_approximate_match method."""
        # Setup
        model_name = 'test-model'

        # Test successful nameContains match
        client.bedrock_client.list_imported_models.return_value = {
            'modelSummaries': [
                {'modelName': 'test-model', 'status': 'InProgress'},
            ]
        }
        result = client._find_model_by_approximate_match(model_name)
        assert result == 'test-model'
        client.bedrock_client.list_imported_models.assert_called_with(nameContains=model_name)

        # Test multiple nameContains matches with preference for first model
        client.bedrock_client.list_imported_models.return_value = {
            'modelSummaries': [
                {'modelName': 'test-model-v2'},
                {'modelName': 'test-model'},
            ]
        }
        result = client._find_model_by_approximate_match(model_name)
        assert result == 'test-model-v2'

        # Test nameContains returns no results, falls back to approximate matching
        # First call with nameContains returns empty list
        client.bedrock_client.list_imported_models.side_effect = [
            {'modelSummaries': []},  # nameContains returns empty
        ]
        # Then paginator for approximate matching returns results
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {
                'modelSummaries': [
                    {'modelName': 'test-model', 'status': 'InProgress'},
                    {'modelName': 'test-model-v2', 'status': 'Ready'},
                ]
            }
        ]
        client.bedrock_client.get_paginator.return_value = paginator_mock

        result = client._find_model_by_approximate_match(model_name)
        assert result == 'test-model'  # Should find via approximate matching

        # Test nameContains throws exception, falls back to approximate matching
        client.bedrock_client.list_imported_models.side_effect = Exception('API Error')
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {
                'modelSummaries': [
                    {'modelName': 'test-model', 'status': 'InProgress'},
                ]
            }
        ]
        client.bedrock_client.get_paginator.return_value = paginator_mock

        result = client._find_model_by_approximate_match(model_name)
        assert result == 'test-model'  # Should find via approximate matching

        # Test both nameContains and approximate matching find nothing
        client.bedrock_client.list_imported_models.side_effect = [
            {'modelSummaries': []},  # nameContains returns empty
        ]
        paginator_mock = MagicMock()
        paginator_mock.paginate.return_value = [
            {'modelSummaries': []}  # approximate matching also returns empty
        ]
        client.bedrock_client.get_paginator.return_value = paginator_mock

        result = client._find_model_by_approximate_match(model_name)
        assert result is None

        # Test error handling in approximate matching
        client.bedrock_client.list_imported_models.side_effect = [
            {'modelSummaries': []},  # nameContains returns empty
        ]
        client.bedrock_client.get_paginator.side_effect = Exception('Test error')
        with pytest.raises(Exception, match='Test error'):
            client._find_model_by_approximate_match(model_name)

    async def test_paginate_results(self, client: BedrockModelImportClient):
        """Test the _paginate_results method with various scenarios including throttling."""
        # Setup
        paginator_mock = MagicMock()

        # Test 1: Normal pagination with multiple pages
        paginator_mock.paginate.return_value = [
            {'Contents': [{'Key': 'file1'}, {'Key': 'file2'}]},
            {'Contents': [{'Key': 'file3'}]},
        ]

        results = client._paginate_results(paginator_mock, Bucket='test-bucket')
        assert len(results) == 3
        assert results[0]['Key'] == 'file1'
        assert results[2]['Key'] == 'file3'
        paginator_mock.paginate.assert_called_once_with(Bucket='test-bucket')

        # Test 2: Empty results
        paginator_mock.reset_mock()
        paginator_mock.paginate.return_value = [{}]

        results = client._paginate_results(paginator_mock)
        assert len(results) == 0

        # Test 3: Different key in response
        paginator_mock.reset_mock()
        paginator_mock.paginate.return_value = [
            {'Items': [{'id': 'item1'}, {'id': 'item2'}]},
        ]

        results = client._paginate_results(paginator_mock)
        assert len(results) == 2
        assert results[0]['id'] == 'item1'

        # Test 4: Throttling exception
        paginator_mock.reset_mock()

        # First page succeeds, second page throws throttling exception
        def paginate_side_effect(**kwargs):
            yield {'Contents': [{'Key': 'file1'}, {'Key': 'file2'}]}
            error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
            raise ClientError(error_response, 'ListObjects')

        paginator_mock.paginate.side_effect = paginate_side_effect

        # Should return partial results and not re-raise the throttling exception
        with patch(
            'awslabs.aws_bedrock_custom_model_import_mcp_server.client.logger'
        ) as mock_logger:
            results = client._paginate_results(paginator_mock)
            assert len(results) == 2
            assert results[0]['Key'] == 'file1'
            mock_logger.warning.assert_called_once()
            assert 'Throttling occurred' in mock_logger.warning.call_args[0][0]

        # Test 5: Other ClientError exception
        paginator_mock.reset_mock()

        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
        paginator_mock.paginate.side_effect = ClientError(error_response, 'ListObjects')

        # Should re-raise non-throttling exceptions
        with pytest.raises(ClientError) as excinfo:
            client._paginate_results(paginator_mock)
        assert excinfo.value.response['Error']['Code'] == 'AccessDenied'

        # Test 6: Test all throttling error codes
        throttling_codes = [
            'ThrottlingException',
            'Throttling',
            'TooManyRequestsException',
            'RequestLimitExceeded',
        ]

        for code in throttling_codes:
            paginator_mock.reset_mock()
            error_response = {'Error': {'Code': code, 'Message': f'{code} occurred'}}
            paginator_mock.paginate.side_effect = ClientError(error_response, 'ListObjects')

            # Should handle all throttling codes and return empty results
            with patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.client.logger'
            ) as mock_logger:
                results = client._paginate_results(paginator_mock)
                assert len(results) == 0
                mock_logger.warning.assert_called_once()
                assert 'Throttling occurred' in mock_logger.warning.call_args[0][0]
