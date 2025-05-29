# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Simplified tests for the deployment_manager utility module."""

import json
import pytest
from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
    DeploymentStatus,
    initialize_deployment_status,
    store_deployment_error,
    store_deployment_metadata,
)
from unittest.mock import AsyncMock, MagicMock, mock_open, patch


class TestDeploymentManagerSimple:
    """Simplified tests for the deployment_manager utility module."""

    @pytest.mark.asyncio
    async def test_initialize_deployment_status_basic(self):
        """Test initialize_deployment_status function with basic functionality."""
        # Mock the open function
        mock_file = mock_open()

        with patch('builtins.open', mock_file), patch('json.dump') as mock_json_dump:
            # Call the function
            project_name = 'test-project'
            deployment_type = 'backend'
            framework = 'express'
            region = 'us-west-2'

            await initialize_deployment_status(project_name, deployment_type, framework, region)

            # Verify the file was opened
            mock_file.assert_called_once()

            # Verify json.dump was called
            mock_json_dump.assert_called_once()

            # Get the metadata that was written
            args, kwargs = mock_json_dump.call_args
            metadata = args[0]

            # Verify the metadata structure
            assert metadata['projectName'] == project_name
            assert metadata['deploymentType'] == deployment_type
            assert metadata['framework'] == framework
            assert metadata['status'] == DeploymentStatus.IN_PROGRESS
            assert metadata['region'] == region
            assert 'timestamp' in metadata

    @pytest.mark.asyncio
    async def test_store_deployment_metadata_basic(self):
        """Test store_deployment_metadata function with basic functionality."""
        # Mock the open function for reading (file doesn't exist)
        mock_read = MagicMock(side_effect=FileNotFoundError())
        mock_write = mock_open()

        def open_side_effect(file, mode, **kwargs):
            if mode == 'r':
                return mock_read()
            return mock_write()

        with (
            patch('builtins.open', side_effect=open_side_effect),
            patch('json.dump') as mock_json_dump,
        ):
            # Call the function
            project_name = 'test-project'
            metadata = {'key': 'value', 'status': DeploymentStatus.DEPLOYED}

            await store_deployment_metadata(project_name, metadata)

            # Verify json.dump was called
            mock_json_dump.assert_called_once()

            # Get the metadata that was written
            args, kwargs = mock_json_dump.call_args
            stored_metadata = args[0]

            # Verify the metadata was merged correctly
            assert stored_metadata['key'] == 'value'
            assert stored_metadata['status'] == DeploymentStatus.DEPLOYED
            assert 'lastUpdated' in stored_metadata

    @pytest.mark.asyncio
    async def test_store_deployment_error_basic(self):
        """Test store_deployment_error function with basic functionality."""
        # Mock the store_deployment_metadata function
        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.store_deployment_metadata',
            new_callable=AsyncMock,
        ) as mock_store:
            # Call the function
            project_name = 'test-project'
            error = 'Test error message'

            await store_deployment_error(project_name, error)

            # Verify store_deployment_metadata was called
            mock_store.assert_called_once()

            # Get the arguments passed to store_deployment_metadata
            args, kwargs = mock_store.call_args
            assert args[0] == project_name

            error_metadata = args[1]
            assert error_metadata['status'] == DeploymentStatus.FAILED
            assert error_metadata['error'] == error
            assert 'errorTimestamp' in error_metadata

    def test_deployment_status_constants(self):
        """Test that DeploymentStatus constants are defined correctly."""
        assert DeploymentStatus.IN_PROGRESS == 'IN_PROGRESS'
        assert DeploymentStatus.DEPLOYED == 'DEPLOYED'
        assert DeploymentStatus.FAILED == 'FAILED'
        assert DeploymentStatus.NOT_FOUND == 'NOT_FOUND'

    @pytest.mark.asyncio
    async def test_initialize_deployment_status_without_region(self):
        """Test initialize_deployment_status function without region."""
        # Mock the open function
        mock_file = mock_open()

        with patch('builtins.open', mock_file), patch('json.dump') as mock_json_dump:
            # Call the function without region
            project_name = 'test-project'
            deployment_type = 'frontend'
            framework = 'react'

            await initialize_deployment_status(project_name, deployment_type, framework, None)

            # Verify json.dump was called
            mock_json_dump.assert_called_once()

            # Get the metadata that was written
            args, kwargs = mock_json_dump.call_args
            metadata = args[0]

            # Verify the metadata structure (no region)
            assert metadata['projectName'] == project_name
            assert metadata['deploymentType'] == deployment_type
            assert metadata['framework'] == framework
            assert metadata['status'] == DeploymentStatus.IN_PROGRESS
            assert 'region' not in metadata
            assert 'timestamp' in metadata

    @pytest.mark.asyncio
    async def test_store_deployment_metadata_with_existing_file(self):
        """Test store_deployment_metadata function with existing file."""
        # Mock existing metadata
        existing_metadata = {'existing': 'data', 'timestamp': '2025-05-28T10:00:00Z'}

        with (
            patch('builtins.open', mock_open(read_data=json.dumps(existing_metadata))),
            patch('json.load', return_value=existing_metadata),
            patch('json.dump') as mock_json_dump,
        ):
            # Call the function
            project_name = 'test-project'
            new_metadata = {'new': 'value', 'status': DeploymentStatus.DEPLOYED}

            await store_deployment_metadata(project_name, new_metadata)

            # Verify json.dump was called
            mock_json_dump.assert_called_once()

            # Get the metadata that was written
            args, kwargs = mock_json_dump.call_args
            stored_metadata = args[0]

            # Verify the metadata was merged correctly
            assert stored_metadata['existing'] == 'data'
            assert stored_metadata['new'] == 'value'
            assert stored_metadata['status'] == DeploymentStatus.DEPLOYED
            assert 'lastUpdated' in stored_metadata
            # Original timestamp should be preserved
            assert stored_metadata['timestamp'] == '2025-05-28T10:00:00Z'

    @pytest.mark.asyncio
    async def test_store_deployment_error_with_exception_object(self):
        """Test store_deployment_error function with an exception object."""
        # Mock the store_deployment_metadata function
        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.store_deployment_metadata',
            new_callable=AsyncMock,
        ) as mock_store:
            # Call the function with an exception object
            project_name = 'test-project'
            error = Exception('Test exception')

            await store_deployment_error(project_name, error)

            # Verify store_deployment_metadata was called
            mock_store.assert_called_once()

            # Get the arguments passed to store_deployment_metadata
            args, kwargs = mock_store.call_args
            assert args[0] == project_name

            error_metadata = args[1]
            assert error_metadata['status'] == DeploymentStatus.FAILED
            assert error_metadata['error'] == 'Test exception'
            assert 'errorTimestamp' in error_metadata
