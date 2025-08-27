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

"""Tests for the ImportedModelService class."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    ListImportedModelsRequest,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.services import (
    ImportedModelService,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import AppConfig
from botocore.exceptions import ClientError
from datetime import datetime
from unittest.mock import MagicMock


class TestImportedModelService:
    """Tests for the ImportedModelService class."""

    @pytest.fixture
    def mock_client(self):
        """Fixture for mocking BedrockModelImportClient."""
        mock = MagicMock()
        mock.list_imported_models = MagicMock()
        mock.get_imported_model = MagicMock()
        mock.delete_imported_model = MagicMock()
        mock._find_model_by_approximate_match = MagicMock()
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
        """Fixture for creating an ImportedModelService instance with a mocked client."""
        return ImportedModelService(mock_client, mock_config)

    def test_initialization(self, mock_client, mock_config):
        """Test service initialization."""
        service = ImportedModelService(mock_client, mock_config)
        assert service.client == mock_client

    @pytest.mark.asyncio
    async def test_list_imported_models_with_filters(self, service):
        """Test listing imported models with filters."""
        # Setup
        request = ListImportedModelsRequest(
            creationTimeAfter=datetime(2025, 1, 1),
            creationTimeBefore=datetime(2025, 12, 31),
            nameContains='test',
            sortBy='CreationTime',
            sortOrder='Descending',
        )

        # Mock client response
        service.client.list_imported_models.return_value = {
            'modelSummaries': [
                {
                    'modelArn': 'model-arn-1',
                    'modelName': 'test-model-1',
                    'creationTime': datetime(2025, 6, 1),
                    'instructSupported': True,
                    'modelArchitecture': 'llama2',
                },
                {
                    'modelArn': 'model-arn-2',
                    'modelName': 'test-model-2',
                    'creationTime': datetime(2025, 5, 1),
                    'instructSupported': False,
                    'modelArchitecture': 'mistral',
                },
            ],
            'nextToken': 'next-token',
        }

        # Execute
        result = await service.list_imported_models(request)

        # Verify
        service.client.list_imported_models.assert_called_once_with(
            creationTimeAfter=datetime(2025, 1, 1),
            creationTimeBefore=datetime(2025, 12, 31),
            nameContains='test',
            sortBy='CreationTime',
            sortOrder='Descending',
        )

        # Verify result
        assert len(result.model_summaries) == 2
        assert result.model_summaries[0].model_name == 'test-model-1'
        assert result.model_summaries[1].model_name == 'test-model-2'
        assert result.next_token == 'next-token'

    @pytest.mark.asyncio
    async def test_list_imported_models_without_filters(self, service):
        """Test listing imported models without filters."""
        # Setup
        # Mock client response
        service.client.list_imported_models.return_value = {
            'modelSummaries': [
                {
                    'modelArn': 'model-arn-1',
                    'modelName': 'test-model-1',
                    'creationTime': datetime(2025, 6, 1),
                    'instructSupported': True,
                    'modelArchitecture': 'llama2',
                }
            ]
        }

        # Execute
        result = await service.list_imported_models()

        # Verify
        service.client.list_imported_models.assert_called_once_with()

        # Verify result
        assert len(result.model_summaries) == 1
        assert result.model_summaries[0].model_name == 'test-model-1'
        assert result.model_summaries[0].instruct_supported is True
        assert result.model_summaries[0].model_architecture == 'llama2'
        assert result.next_token is None

    @pytest.mark.asyncio
    async def test_get_imported_model_success(self, service):
        """Test getting an imported model successfully."""
        # Setup
        model_name = 'test-model'

        # Mock client response
        service.client.get_imported_model.return_value = {
            'modelArn': 'model-arn',
            'modelName': model_name,
            'jobName': 'job-name',
            'jobArn': 'job-arn',
            'modelDataSource': {'s3DataSource': {'s3Uri': 's3://bucket/model'}},
            'creationTime': datetime(2025, 6, 1),
            'modelArchitecture': 'llama2',
            'instructSupported': True,
            'customModelUnits': {
                'customModelUnitsPerModelCopy': 1,
                'customModelUnitsVersion': '1.0',
            },
        }

        # Execute
        result = await service.get_imported_model(model_name)

        # Verify
        service.client.get_imported_model.assert_called_once_with(model_name)

        # Verify result
        assert result.model_arn == 'model-arn'
        assert result.model_name == model_name
        assert result.job_name == 'job-name'
        assert result.model_architecture == 'llama2'
        assert result.instruct_supported is True
        assert result.custom_model_units.custom_model_units_per_model_copy == 1
        assert result.custom_model_units.custom_model_units_version == '1.0'

    @pytest.mark.asyncio
    async def test_get_imported_model_other_client_error(self, service):
        """Test getting an imported model with a non-ValidationException ClientError."""
        # Setup
        model_name = 'test-model'

        # Mock client methods
        # Call fails with AccessDeniedException
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        service.client.get_imported_model.side_effect = ClientError(
            error_response, 'GetImportedModel'
        )

        # Execute and verify
        with pytest.raises(ClientError) as excinfo:
            await service.get_imported_model(model_name)

        # Verify the error details
        assert excinfo.value.response['Error']['Code'] == 'AccessDeniedException'
        service.client._find_model_by_approximate_match.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_imported_model(self, service):
        """Test deleting an imported model."""
        # Setup
        model_identifier = 'test-model'

        # Execute
        await service.delete_imported_model(model_identifier)

        # Verify
        service.client.delete_imported_model.assert_called_once_with(model_identifier)

    @pytest.mark.asyncio
    async def test_delete_imported_model_failure(self, service):
        """Test failure when deleting an imported model."""
        # Setup
        model_identifier = 'test-model'

        # Mock client to raise an exception
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Model not found'}}
        service.client.delete_imported_model.side_effect = ClientError(
            error_response, 'DeleteImportedModel'
        )

        # Execute and verify
        with pytest.raises(ClientError) as excinfo:
            await service.delete_imported_model(model_identifier)

        # Verify the error details
        assert excinfo.value.response['Error']['Code'] == 'ValidationException'
        service.client.delete_imported_model.assert_called_once_with(model_identifier)
