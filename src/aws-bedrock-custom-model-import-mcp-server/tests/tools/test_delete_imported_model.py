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

"""Tests for the delete_imported_model tool."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.tools.delete_imported_model import (
    DeleteImportedModel,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import AppConfig
from botocore.exceptions import ClientError
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from unittest.mock import AsyncMock, MagicMock


class TestDeleteImportedModel:
    """Tests for the DeleteImportedModel tool."""

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
        mock.delete_imported_model = AsyncMock()
        return mock

    @pytest.fixture
    def tool(self, mock_mcp, mock_service):
        """Fixture for creating a DeleteImportedModel instance."""
        return DeleteImportedModel(mock_mcp, mock_service)

    @pytest.fixture
    def mock_context(self):
        """Fixture for mocking MCP Context."""
        mock = MagicMock()
        mock.info = AsyncMock()
        mock.error = AsyncMock()
        return mock

    def test_initialization(self, mock_mcp, mock_service):
        """Test tool initialization."""
        tool = DeleteImportedModel(mock_mcp, mock_service)
        assert tool.imported_model_service == mock_service
        assert mock_mcp.tool.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_imported_model_with_context(self, tool, mock_context):
        """Test deleting an imported model with context."""
        # Setup
        model_identifier = 'test-model'

        # Execute
        result = await tool.delete_imported_model(mock_context, model_identifier)

        # Verify
        tool.imported_model_service.delete_imported_model.assert_called_once_with(model_identifier)
        mock_context.info.assert_called_once()
        assert 'Model Deletion' in result
        assert f'✅ **Successfully deleted model**: `{model_identifier}`' in result

    @pytest.mark.asyncio
    async def test_delete_imported_model_without_context(self, tool):
        """Test deleting an imported model without context."""
        # Setup
        model_identifier = 'test-model'

        # Execute
        result = await tool.delete_imported_model(None, model_identifier)

        # Verify
        tool.imported_model_service.delete_imported_model.assert_called_once_with(model_identifier)
        assert 'Model Deletion' in result
        assert f'✅ **Successfully deleted model**: `{model_identifier}`' in result

    @pytest.mark.asyncio
    async def test_delete_imported_model_not_found(self, tool, mock_context):
        """Test error handling when model is not found."""
        # Setup
        model_identifier = 'test-model'
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Model not found'}}
        tool.imported_model_service.delete_imported_model.side_effect = ClientError(
            error_response, 'DeleteImportedModel'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.delete_imported_model(mock_context, model_identifier)

        # Verify the error details
        assert 'Error deleting imported model' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_imported_model_access_denied(self, tool, mock_context):
        """Test error handling when access is denied."""
        # Setup
        model_identifier = 'test-model'
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        tool.imported_model_service.delete_imported_model.side_effect = ClientError(
            error_response, 'DeleteImportedModel'
        )

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.delete_imported_model(mock_context, model_identifier)

        # Verify the error details
        assert 'Error deleting imported model' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_imported_model_other_error(self, tool, mock_context):
        """Test error handling for other errors."""
        # Setup
        model_identifier = 'test-model'
        error_msg = 'Some other error'
        tool.imported_model_service.delete_imported_model.side_effect = Exception(error_msg)

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.delete_imported_model(mock_context, model_identifier)

        # Verify the error details
        assert f'Error deleting imported model: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_imported_model_allow_write_enabled(
        self, mock_mcp, mock_service, mock_context
    ):
        """Test deleting an imported model with allow_write enabled."""
        # Setup - allow_write is True
        mock_service.config = MagicMock(spec=AppConfig)
        mock_service.config.allow_write = True

        model_identifier = 'test-model'

        tool = DeleteImportedModel(mock_mcp, mock_service)

        # Execute
        result = await tool.delete_imported_model(mock_context, model_identifier)

        # Verify
        mock_service.delete_imported_model.assert_called_once_with(model_identifier)
        mock_context.info.assert_called_once()
        assert 'Model Deletion' in result
        assert f'✅ **Successfully deleted model**: `{model_identifier}`' in result

    @pytest.mark.asyncio
    async def test_delete_imported_model_allow_write_disabled(
        self, mock_mcp, mock_service, mock_context
    ):
        """Test deleting an imported model with allow_write disabled."""
        # Setup - allow_write is False
        mock_service.config = MagicMock(spec=AppConfig)
        mock_service.config.allow_write = False

        # We need to patch the service's delete_imported_model method to raise ToolError
        # but we don't want the tool's delete_imported_model method to catch and re-raise it
        error_msg = 'Deleting imported models requires --allow-write flag'
        mock_service.delete_imported_model.side_effect = ToolError(error_msg)

        tool = DeleteImportedModel(mock_mcp, mock_service)
        model_identifier = 'test-model'

        # Execute and verify
        with pytest.raises(Exception) as excinfo:
            await tool.delete_imported_model(mock_context, model_identifier)

        # Verify the error details
        assert f'Error deleting imported model: {error_msg}' in str(excinfo.value)
        mock_context.error.assert_called_once()
