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

"""Tests for the list_imported_models tool."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    ListImportedModelsRequest,
    ListImportedModelsResponse,
    ModelSummary,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.list_imported_models import (
    ListImportedModels,
)
from botocore.exceptions import ClientError
from datetime import datetime
from fastmcp import FastMCP
from unittest.mock import AsyncMock, MagicMock


class TestListImportedModels:
    """Tests for the ListImportedModels tool."""

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
        mock.list_imported_models = AsyncMock()
        return mock

    @pytest.fixture
    def tool(self, mock_mcp, mock_service):
        """Fixture for creating a ListImportedModels instance."""
        return ListImportedModels(mock_mcp, mock_service)

    @pytest.fixture
    def mock_context(self):
        """Fixture for mocking MCP Context."""
        mock = MagicMock()
        mock.info = AsyncMock()
        mock.error = AsyncMock()
        return mock

    @pytest.fixture
    def sample_response(self):
        """Fixture for creating a sample ListImportedModelsResponse."""
        return ListImportedModelsResponse(
            modelSummaries=[
                ModelSummary(
                    modelArn='arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model-1',
                    modelName='test-model-1',
                    creationTime=datetime(2025, 1, 1, 12, 0, 0),
                    instructSupported=True,
                    modelArchitecture='llama2',
                ),
                ModelSummary(
                    modelArn='arn:aws:bedrock:us-west-2:123456789012:custom-model/test-model-2',
                    modelName='test-model-2',
                    creationTime=datetime(2025, 1, 2, 12, 0, 0),
                    instructSupported=False,
                    modelArchitecture='mistral',
                ),
            ],
            nextToken='next-token',
        )

    def test_initialization(self, mock_mcp, mock_service):
        """Test tool initialization."""
        tool = ListImportedModels(mock_mcp, mock_service)
        assert tool.imported_model_service == mock_service
        assert mock_mcp.tool.call_count == 1

    @pytest.mark.asyncio
    async def test_list_imported_models_with_context(self, tool, mock_context, sample_response):
        """Test listing imported models with context."""
        # Setup
        tool.imported_model_service.list_imported_models.return_value = sample_response

        # Execute
        result = await tool.list_imported_models(mock_context)

        # Verify
        tool.imported_model_service.list_imported_models.assert_called_once_with(None)
        mock_context.info.assert_called_once()
        assert 'Imported Models' in result
        assert '| Model Name | Created | Architecture | Instruct Support | ARN |' in result
        assert '| `test-model-1` |' in result
        assert '| `test-model-2` |' in result
        assert '✅' in result  # For test-model-1
        assert '❌' in result  # For test-model-2
        assert '`llama2`' in result
        assert '`mistral`' in result

    @pytest.mark.asyncio
    async def test_list_imported_models_without_context(self, tool, sample_response):
        """Test listing imported models without context."""
        # Setup
        tool.imported_model_service.list_imported_models.return_value = sample_response

        # Execute
        result = await tool.list_imported_models(None)

        # Verify
        tool.imported_model_service.list_imported_models.assert_called_once_with(None)
        assert 'Imported Models' in result
        assert '| Model Name | Created | Architecture | Instruct Support | ARN |' in result
        assert '| `test-model-1` |' in result
        assert '| `test-model-2` |' in result

    @pytest.mark.asyncio
    async def test_list_imported_models_with_filters(self, tool, mock_context, sample_response):
        """Test listing imported models with filters."""
        # Setup
        request = ListImportedModelsRequest(
            nameContains='test',
            creationTimeAfter=datetime(2025, 1, 1),
            creationTimeBefore=datetime(2025, 12, 31),
            sortBy='CreationTime',
            sortOrder='Descending',
        )
        tool.imported_model_service.list_imported_models.return_value = sample_response

        # Execute
        result = await tool.list_imported_models(mock_context, request)

        # Verify
        tool.imported_model_service.list_imported_models.assert_called_once_with(request)
        assert 'Imported Models' in result
        assert '| Model Name | Created | Architecture | Instruct Support | ARN |' in result
        assert '| `test-model-1` |' in result
        assert '| `test-model-2` |' in result

    @pytest.mark.asyncio
    async def test_list_imported_models_no_results(self, tool, mock_context):
        """Test listing imported models with no results."""
        # Setup
        response = ListImportedModelsResponse(modelSummaries=[], nextToken=None)
        tool.imported_model_service.list_imported_models.return_value = response

        # Execute
        result = await tool.list_imported_models(mock_context)

        # Verify
        tool.imported_model_service.list_imported_models.assert_called_once_with(None)
        assert 'Imported Models' in result
        assert 'No imported models found.' in result

    @pytest.mark.asyncio
    async def test_list_imported_models_access_denied(self, tool, mock_context):
        """Test error handling when access is denied."""
        # Setup
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        tool.imported_model_service.list_imported_models.side_effect = ClientError(
            error_response, 'ListImportedModels'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.list_imported_models(mock_context)

        # Verify the error details
        assert 'Error listing imported models' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_imported_models_other_error(self, tool, mock_context):
        """Test error handling for other errors."""
        # Setup
        error_msg = 'Some other error'
        tool.imported_model_service.list_imported_models.side_effect = Exception(error_msg)

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.list_imported_models(mock_context)

        # Verify the error details
        assert f'Error listing imported models: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()
