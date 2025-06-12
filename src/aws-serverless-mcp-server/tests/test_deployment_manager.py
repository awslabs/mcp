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

    @pytest.mark.asyncio
    async def test_get_deployment_status_file_not_found(self):
        """Test get_deployment_status when metadata file doesn't exist."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
            get_deployment_status,
        )

        with patch('os.path.exists', return_value=False):
            result = await get_deployment_status('nonexistent-project')

            assert result['status'] == DeploymentStatus.NOT_FOUND
            assert result['projectName'] == 'nonexistent-project'
            assert 'No deployment found' in result['message']

    @pytest.mark.asyncio
    async def test_get_deployment_status_with_cloudformation_success(self):
        """Test get_deployment_status with successful CloudFormation query."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
            get_deployment_status,
        )

        # Mock metadata
        metadata = {
            'projectName': 'test-project',
            'timestamp': '2025-06-06T10:00:00Z',
            'deploymentType': 'backend',
            'framework': 'express',
            'region': 'us-west-2',
        }

        # Mock CloudFormation response
        stack_info = {
            'status': 'CREATE_COMPLETE',
            'statusReason': 'Stack created successfully',
            'lastUpdatedTime': '2025-06-06T10:30:00Z',
            'outputs': {'ApiEndpoint': 'https://api.example.com', 'BucketName': 'my-bucket'},
        }

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=json.dumps(metadata))),
            patch('json.load', return_value=metadata),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info',
                return_value=stack_info,
            ) as mock_get_stack,
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.map_cloudformation_status',
                return_value='COMPLETE',
            ) as mock_map_status,
        ):
            result = await get_deployment_status('test-project')

            # Verify CloudFormation was queried
            mock_get_stack.assert_called_once_with('test-project', 'us-west-2')
            mock_map_status.assert_called_once_with('CREATE_COMPLETE')

            # Verify result structure
            assert result['status'] == 'COMPLETE'
            assert result['stackStatus'] == 'CREATE_COMPLETE'
            assert result['stackStatusReason'] == 'Stack created successfully'
            assert result['projectName'] == 'test-project'
            assert result['deploymentType'] == 'backend'
            assert result['framework'] == 'express'
            assert result['region'] == 'us-west-2'
            assert result['outputs'] == stack_info['outputs']
            assert 'formattedOutputs' in result
            assert result['formattedOutputs']['ApiEndpoint']['value'] == 'https://api.example.com'

    @pytest.mark.asyncio
    async def test_get_deployment_status_cloudformation_not_found(self):
        """Test get_deployment_status when CloudFormation stack is not found."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
            get_deployment_status,
        )

        # Mock metadata
        metadata = {
            'projectName': 'test-project',
            'timestamp': '2025-06-06T10:00:00Z',
            'deploymentType': 'backend',
            'framework': 'express',
            'status': 'FAILED',
        }

        # Mock CloudFormation response - stack not found
        stack_info = {'status': 'NOT_FOUND'}

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=json.dumps(metadata))),
            patch('json.load', return_value=metadata),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info',
                return_value=stack_info,
            ),
        ):
            result = await get_deployment_status('test-project')

            # Should return original metadata when stack not found
            assert result == metadata

    @pytest.mark.asyncio
    async def test_get_deployment_status_cloudformation_error(self):
        """Test get_deployment_status when CloudFormation query fails."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
            get_deployment_status,
        )

        # Mock metadata
        metadata = {
            'projectName': 'test-project',
            'timestamp': '2025-06-06T10:00:00Z',
            'deploymentType': 'backend',
            'framework': 'express',
        }

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=json.dumps(metadata))),
            patch('json.load', return_value=metadata),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info',
                side_effect=Exception('CloudFormation error'),
            ),
        ):
            result = await get_deployment_status('test-project')

            # Should return metadata with error information
            assert result['status'] == 'unknown'
            assert result['projectName'] == 'test-project'
            assert 'Error querying CloudFormation' in result['message']

    @pytest.mark.asyncio
    async def test_get_deployment_status_file_read_error(self):
        """Test get_deployment_status when file reading fails."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
            get_deployment_status,
        )

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', side_effect=Exception('File read error')),
        ):
            with pytest.raises(Exception, match='Failed to get deployment status'):
                await get_deployment_status('test-project')

    @pytest.mark.asyncio
    async def test_list_deployments_no_files(self):
        """Test list_deployments when no deployment files exist."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments

        with patch('os.listdir', return_value=[]):
            result = await list_deployments()
            assert result == []

    @pytest.mark.asyncio
    async def test_list_deployments_directory_error(self):
        """Test list_deployments when directory reading fails."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments

        with patch('os.listdir', side_effect=Exception('Directory error')):
            result = await list_deployments()
            assert result == []

    @pytest.mark.asyncio
    async def test_list_deployments_with_files(self):
        """Test list_deployments with multiple deployment files."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments

        # Mock deployment statuses
        deployment1 = {
            'projectName': 'project1',
            'status': 'DEPLOYED',
            'timestamp': '2025-06-06T10:00:00Z',
        }
        deployment2 = {
            'projectName': 'project2',
            'status': 'FAILED',
            'timestamp': '2025-06-06T11:00:00Z',
        }

        with (
            patch('os.listdir', return_value=['project1.json', 'project2.json', 'other.txt']),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_deployment_status'
            ) as mock_get_status,
        ):
            # Mock different returns for each project
            mock_get_status.side_effect = [deployment1, deployment2]

            result = await list_deployments()

            # Should return both deployments, sorted by timestamp desc
            assert len(result) == 2
            assert result[0] == deployment2  # Later timestamp first
            assert result[1] == deployment1

            # Verify get_deployment_status was called for each project
            assert mock_get_status.call_count == 2
            mock_get_status.assert_any_call('project1')
            mock_get_status.assert_any_call('project2')

    @pytest.mark.asyncio
    async def test_list_deployments_with_limit(self):
        """Test list_deployments with limit parameter."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments

        deployments = [
            {'projectName': 'project1', 'timestamp': '2025-06-06T10:00:00Z'},
            {'projectName': 'project2', 'timestamp': '2025-06-06T11:00:00Z'},
            {'projectName': 'project3', 'timestamp': '2025-06-06T12:00:00Z'},
        ]

        with (
            patch('os.listdir', return_value=['project1.json', 'project2.json', 'project3.json']),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_deployment_status',
                side_effect=deployments,
            ),
        ):
            result = await list_deployments(limit=2)

            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_deployments_with_status_filter(self):
        """Test list_deployments with status filter."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments

        deployments = [
            {'projectName': 'project1', 'status': 'DEPLOYED'},
            {'projectName': 'project2', 'status': 'FAILED'},
            {'projectName': 'project3', 'status': 'DEPLOYED'},
        ]

        with (
            patch('os.listdir', return_value=['project1.json', 'project2.json', 'project3.json']),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_deployment_status',
                side_effect=deployments,
            ),
        ):
            result = await list_deployments(filter_status='DEPLOYED')

            assert len(result) == 2
            assert all(d['status'] == 'DEPLOYED' for d in result)

    @pytest.mark.asyncio
    async def test_list_deployments_with_sorting(self):
        """Test list_deployments with different sorting options."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments

        deployments = [
            {'projectName': 'project-c', 'timestamp': '2025-06-06T10:00:00Z'},
            {'projectName': 'project-a', 'timestamp': '2025-06-06T11:00:00Z'},
            {'projectName': 'project-b', 'timestamp': '2025-06-06T12:00:00Z'},
        ]

        with (
            patch('os.listdir', return_value=['project1.json', 'project2.json', 'project3.json']),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_deployment_status',
                side_effect=deployments,
            ),
        ):
            # Test ascending sort by project name
            result = await list_deployments(sort_by='projectName', sort_order='asc')

            assert len(result) == 3
            assert result[0]['projectName'] == 'project-a'
            assert result[1]['projectName'] == 'project-b'
            assert result[2]['projectName'] == 'project-c'

    @pytest.mark.asyncio
    async def test_list_deployments_with_processing_error(self):
        """Test list_deployments when processing individual files fails."""
        from awslabs.aws_serverless_mcp_server.utils.deployment_manager import list_deployments

        with (
            patch('os.listdir', return_value=['project1.json', 'project2.json']),
            patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_deployment_status'
            ) as mock_get_status,
        ):
            # First call succeeds, second fails
            mock_get_status.side_effect = [
                {'projectName': 'project1', 'status': 'DEPLOYED'},
                Exception('Processing error'),
            ]

            result = await list_deployments()

            # Should return only the successful one
            assert len(result) == 1
            assert result[0]['projectName'] == 'project1'
