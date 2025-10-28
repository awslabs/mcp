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

"""Tests for the get_imported_model tool."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    CustomModelUnits,
    ImportedModel,
    ModelDataSource,
    S3DataSource,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.get_imported_model import (
    GetImportedModel,
)
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import FastMCP
from unittest.mock import AsyncMock, MagicMock


class TestGetImportedModel:
    """Tests for the GetImportedModel tool."""

    @pytest.fixture
    def mock_mcp(self):
        """Fixture for mocking FastMCP."""
        mock = MagicMock(spec=FastMCP)
        mock.tool = MagicMock(return_value=MagicMock())
        return mock

    @pytest.fixture
    def mock_service(self):
        """Fixture for mocking ImportedModelService."""
        mock = MagicMock()
        mock.get_imported_model = AsyncMock()
        return mock

    @pytest.fixture
    def tool(self, mock_mcp, mock_service):
        """Fixture for creating a GetImportedModel instance."""
        return GetImportedModel(mock_mcp, mock_service)

    @pytest.fixture
    def mock_context(self):
        """Fixture for mocking MCP Context."""
        mock = MagicMock()
        mock.info = AsyncMock()
        mock.error = AsyncMock()
        return mock

    @pytest.fixture
    def sample_model(self):
        """Fixture for creating a sample ImportedModel."""
        return ImportedModel(
            modelArn='arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model',
            modelName='test-model',
            jobName='test-job',
            jobArn='arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            modelArchitecture='llama2',
            instructSupported=True,
            customModelUnits=None,
            modelKmsKeyArn=None,
        )

    def test_initialization(self, mock_mcp, mock_service):
        """Test tool initialization."""
        tool = GetImportedModel(mock_mcp, mock_service)
        assert tool.imported_model_service == mock_service
        assert mock_mcp.tool.call_count == 1

    @pytest.mark.asyncio
    async def test_get_imported_model_with_context(self, tool, mock_context, sample_model):
        """Test getting an imported model with context."""
        # Setup
        model_identifier = 'test-model'
        tool.imported_model_service.get_imported_model.return_value = sample_model

        # Execute
        result = await tool.get_imported_model(mock_context, model_identifier)

        # Verify
        tool.imported_model_service.get_imported_model.assert_called_once_with(model_identifier)
        mock_context.info.assert_called_once()
        assert 'Imported Model: `test-model`' in result
        assert (
            '**Model ARN**: `arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model`'
            in result
        )
        assert '**Architecture**: `llama2`' in result
        assert '**Instruct Support**: ✅' in result

    @pytest.mark.asyncio
    async def test_get_imported_model_without_context(self, tool, sample_model):
        """Test getting an imported model without context."""
        # Setup
        model_identifier = 'test-model'
        tool.imported_model_service.get_imported_model.return_value = sample_model

        # Execute
        result = await tool.get_imported_model(None, model_identifier)

        # Verify
        tool.imported_model_service.get_imported_model.assert_called_once_with(model_identifier)
        assert 'Imported Model: `test-model`' in result
        assert (
            '**Model ARN**: `arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model`'
            in result
        )
        assert '**Architecture**: `llama2`' in result
        assert '**Instruct Support**: ✅' in result

    @pytest.mark.asyncio
    async def test_get_imported_model_with_kms_and_units(self, tool, mock_context):
        """Test getting an imported model with KMS and custom model units."""
        # Setup
        model_identifier = 'test-model'
        model = ImportedModel(
            modelArn='arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model',
            modelName='test-model',
            jobName='test-job',
            jobArn='arn:aws:bedrock:us-west-2:123456789012:model-import-job/test-job',
            modelDataSource=ModelDataSource(
                s3DataSource=S3DataSource(s3Uri='s3://test-bucket/models/test-model')
            ),
            creationTime=datetime(2025, 1, 1, 12, 0, 0),
            modelArchitecture='llama2',
            instructSupported=True,
            customModelUnits=CustomModelUnits(
                customModelUnitsPerModelCopy=10,
                customModelUnitsVersion='1.0',
            ),
            modelKmsKeyArn='test-kms-key-arn',
        )
        tool.imported_model_service.get_imported_model.return_value = model

        # Execute
        result = await tool.get_imported_model(mock_context, model_identifier)

        # Verify
        tool.imported_model_service.get_imported_model.assert_called_once_with(model_identifier)
        assert '**KMS Key ARN**: `test-kms-key-arn`' in result
        assert '**Custom Model Units**: `Units per copy = 10`' in result
        assert '`Version = 1.0`' in result

    @pytest.mark.asyncio
    async def test_get_imported_model_not_found(self, tool, mock_context):
        """Test error handling when model is not found."""
        # Setup
        model_identifier = 'test-model'
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Model not found'}}
        tool.imported_model_service.get_imported_model.side_effect = ClientError(
            error_response, 'GetImportedModel'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.get_imported_model(mock_context, model_identifier)

        # Verify the error details
        assert 'Error getting imported model' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_imported_model_access_denied(self, tool, mock_context):
        """Test error handling when access is denied."""
        # Setup
        model_identifier = 'test-model'
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        tool.imported_model_service.get_imported_model.side_effect = ClientError(
            error_response, 'GetImportedModel'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.get_imported_model(mock_context, model_identifier)

        # Verify the error details
        assert 'Error getting imported model' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_imported_model_other_error(self, tool, mock_context):
        """Test error handling for other errors."""
        # Setup
        model_identifier = 'test-model'
        error_msg = 'Some other error'
        tool.imported_model_service.get_imported_model.side_effect = Exception(error_msg)

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.get_imported_model(mock_context, model_identifier)

        # Verify the error details
        assert f'Error getting imported model: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()
