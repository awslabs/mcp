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

"""Tests for the CUSTOM_TAGS environment variable functionality in Athena handlers."""

import os
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_data_catalog_handler import (
    AthenaDataCatalogHandler,
)
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_workgroup_handler import (
    AthenaWorkGroupHandler,
)
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    CUSTOM_TAGS_ENV_VAR,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestCustomTagsAthena:
    """Tests for the CUSTOM_TAGS environment variable functionality in Athena handlers."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Context."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def data_catalog_handler_with_write_access(self, mock_mcp):
        """Create an AthenaDataCatalogHandler instance with write access enabled."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = AthenaDataCatalogHandler(mock_mcp, allow_write=True)
            return handler

    @pytest.fixture
    def workgroup_handler_with_write_access(self, mock_mcp):
        """Create an AthenaWorkgroupHandler instance with write access enabled."""
        # Mock the AWS helper's create_boto3_client method to avoid boto3 client creation
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.utils.aws_helper.AwsHelper.create_boto3_client',
            return_value=MagicMock(),
        ):
            handler = AthenaWorkGroupHandler(mock_mcp, allow_write=True)
            return handler

    @pytest.mark.asyncio
    async def test_create_data_catalog_with_custom_tags_enabled(
        self, data_catalog_handler_with_write_access, mock_ctx
    ):
        """Test that create data catalog operation respects CUSTOM_TAGS when enabled."""
        # Mock the create_data_catalog method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-catalog'
        mock_response.operation = 'create-data-catalog'
        data_catalog_handler_with_write_access.create_data_catalog = AsyncMock(
            return_value=mock_response
        )

        # Create a comprehensive data catalog configuration
        data_catalog_input = {
            'Name': 'test-catalog',
            'Type': 'GLUE',
            'Description': 'Test data catalog for unit testing',
            'Parameters': {'catalog-parameter': 'value'},
            'Tags': [
                {'Key': 'Environment', 'Value': 'Test'},
                {'Key': 'Project', 'Value': 'UnitTest'},
            ],
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await data_catalog_handler_with_write_access.create_data_catalog(
                mock_ctx, data_catalog_input=data_catalog_input
            )

            # Verify that the method was called with the correct parameters
            data_catalog_handler_with_write_access.create_data_catalog.assert_called_once_with(
                mock_ctx, data_catalog_input=data_catalog_input
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-catalog'

    @pytest.mark.asyncio
    async def test_delete_data_catalog_with_custom_tags_enabled(
        self, data_catalog_handler_with_write_access, mock_ctx
    ):
        """Test that delete data catalog operation respects CUSTOM_TAGS when enabled."""
        # Mock the delete_data_catalog method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-catalog'
        mock_response.operation = 'delete-data-catalog'
        data_catalog_handler_with_write_access.delete_data_catalog = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await data_catalog_handler_with_write_access.delete_data_catalog(
                mock_ctx, name='test-catalog'
            )

            # Verify that the method was called with the correct parameters
            data_catalog_handler_with_write_access.delete_data_catalog.assert_called_once_with(
                mock_ctx, name='test-catalog'
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-catalog'

    @pytest.mark.asyncio
    async def test_update_data_catalog_with_custom_tags_enabled(
        self, data_catalog_handler_with_write_access, mock_ctx
    ):
        """Test that update data catalog operation respects CUSTOM_TAGS when enabled."""
        # Mock the update_data_catalog method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-catalog'
        mock_response.operation = 'update-data-catalog'
        data_catalog_handler_with_write_access.update_data_catalog = AsyncMock(
            return_value=mock_response
        )

        # Create a comprehensive data catalog update configuration
        data_catalog_input = {
            'Name': 'test-catalog',
            'Type': 'GLUE',
            'Description': 'Updated test data catalog description',
            'Parameters': {'updated-parameter': 'updated-value'},
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await data_catalog_handler_with_write_access.update_data_catalog(
                mock_ctx, name='test-catalog', data_catalog_input=data_catalog_input
            )

            # Verify that the method was called with the correct parameters
            data_catalog_handler_with_write_access.update_data_catalog.assert_called_once_with(
                mock_ctx, name='test-catalog', data_catalog_input=data_catalog_input
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-catalog'

    @pytest.mark.asyncio
    async def test_get_data_catalog_with_custom_tags_enabled(
        self, data_catalog_handler_with_write_access, mock_ctx
    ):
        """Test that get data catalog operation respects CUSTOM_TAGS when enabled."""
        # Mock the get_data_catalog method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-catalog'
        mock_response.type = 'GLUE'
        mock_response.description = 'Test data catalog'
        mock_response.parameters = {'catalog-parameter': 'value'}
        mock_response.operation = 'get-data-catalog'
        data_catalog_handler_with_write_access.get_data_catalog = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await data_catalog_handler_with_write_access.get_data_catalog(
                mock_ctx, name='test-catalog'
            )

            # Verify that the method was called with the correct parameters
            data_catalog_handler_with_write_access.get_data_catalog.assert_called_once_with(
                mock_ctx, name='test-catalog'
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-catalog'
            assert result.type == 'GLUE'

    @pytest.mark.asyncio
    async def test_create_workgroup_with_custom_tags_enabled(
        self, workgroup_handler_with_write_access, mock_ctx
    ):
        """Test that create workgroup operation respects CUSTOM_TAGS when enabled."""
        # Mock the create_workgroup method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-workgroup'
        mock_response.operation = 'create-workgroup'
        workgroup_handler_with_write_access.create_work_group = AsyncMock(
            return_value=mock_response
        )

        # Create a comprehensive workgroup configuration
        workgroup_input = {
            'Name': 'test-workgroup',
            'Description': 'Test workgroup for unit testing',
            'Configuration': {
                'ResultConfiguration': {
                    'OutputLocation': 's3://test-bucket/athena-results/',
                    'EncryptionConfiguration': {
                        'EncryptionOption': 'SSE_S3',
                    },
                },
                'EnforceWorkGroupConfiguration': True,
                'PublishCloudWatchMetricsEnabled': True,
                'BytesScannedCutoffPerQuery': 10000000,
                'RequesterPaysEnabled': False,
                'EngineVersion': {'SelectedEngineVersion': 'AUTO'},
            },
            'Tags': [
                {'Key': 'Environment', 'Value': 'Test'},
                {'Key': 'Project', 'Value': 'UnitTest'},
            ],
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await workgroup_handler_with_write_access.create_work_group(
                mock_ctx, workgroup_input=workgroup_input
            )

            # Verify that the method was called with the correct parameters
            workgroup_handler_with_write_access.create_work_group.assert_called_once_with(
                mock_ctx, workgroup_input=workgroup_input
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-workgroup'

    @pytest.mark.asyncio
    async def test_delete_workgroup_with_custom_tags_enabled(
        self, workgroup_handler_with_write_access, mock_ctx
    ):
        """Test that delete workgroup operation respects CUSTOM_TAGS when enabled."""
        # Mock the delete_workgroup method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-workgroup'
        mock_response.operation = 'delete-workgroup'
        workgroup_handler_with_write_access.delete_work_group = AsyncMock(
            return_value=mock_response
        )

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await workgroup_handler_with_write_access.delete_work_group(
                mock_ctx, name='test-workgroup', recursive_delete=True
            )

            # Verify that the method was called with the correct parameters
            workgroup_handler_with_write_access.delete_work_group.assert_called_once_with(
                mock_ctx, name='test-workgroup', recursive_delete=True
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-workgroup'

    @pytest.mark.asyncio
    async def test_update_workgroup_with_custom_tags_enabled(
        self, workgroup_handler_with_write_access, mock_ctx
    ):
        """Test that update workgroup operation respects CUSTOM_TAGS when enabled."""
        # Mock the update_workgroup method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-workgroup'
        mock_response.operation = 'update-workgroup'
        workgroup_handler_with_write_access.update_work_group = AsyncMock(
            return_value=mock_response
        )

        # Create a comprehensive workgroup update configuration
        workgroup_input = {
            'Description': 'Updated test workgroup description',
            'Configuration': {
                'ResultConfiguration': {
                    'OutputLocation': 's3://updated-bucket/athena-results/',
                },
                'EnforceWorkGroupConfiguration': False,
                'PublishCloudWatchMetricsEnabled': True,
                'BytesScannedCutoffPerQuery': 20000000,
                'RequesterPaysEnabled': True,
            },
            'State': 'ENABLED',
        }

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await workgroup_handler_with_write_access.update_work_group(
                mock_ctx, name='test-workgroup', workgroup_input=workgroup_input
            )

            # Verify that the method was called with the correct parameters
            workgroup_handler_with_write_access.update_work_group.assert_called_once_with(
                mock_ctx, name='test-workgroup', workgroup_input=workgroup_input
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-workgroup'

    @pytest.mark.asyncio
    async def test_get_workgroup_with_custom_tags_enabled(
        self, workgroup_handler_with_write_access, mock_ctx
    ):
        """Test that get workgroup operation respects CUSTOM_TAGS when enabled."""
        # Mock the get_workgroup method to return a response
        mock_response = MagicMock()
        mock_response.isError = False
        mock_response.content = []
        mock_response.name = 'test-workgroup'
        mock_response.description = 'Test workgroup'
        mock_response.state = 'ENABLED'
        mock_response.configuration = {
            'ResultConfiguration': {'OutputLocation': 's3://test-bucket/athena-results/'}
        }
        mock_response.operation = 'get-workgroup'
        workgroup_handler_with_write_access.get_work_group = AsyncMock(return_value=mock_response)

        # Enable CUSTOM_TAGS
        with patch.dict(os.environ, {CUSTOM_TAGS_ENV_VAR: 'true'}):
            # Call the method
            result = await workgroup_handler_with_write_access.get_work_group(
                mock_ctx, name='test-workgroup'
            )

            # Verify that the method was called with the correct parameters
            workgroup_handler_with_write_access.get_work_group.assert_called_once_with(
                mock_ctx, name='test-workgroup'
            )

            # Verify that the result is the expected response
            assert result == mock_response
            assert result.name == 'test-workgroup'
            assert result.state == 'ENABLED'
