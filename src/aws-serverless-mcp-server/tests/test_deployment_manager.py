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

"""Tests for deployment manager utilities."""

import json
import os
import pytest
import tempfile
from awslabs.aws_serverless_mcp_server.utils.deployment_manager import (
    DeploymentStatus,
    get_deployment_status,
    initialize_deployment_status,
    list_deployments,
    store_deployment_error,
    store_deployment_metadata,
)
from unittest.mock import patch


class TestDeploymentManagerComprehensive:
    """Comprehensive test cases for deployment manager."""

    @pytest.fixture
    def temp_deployment_dir(self):
        """Create a temporary directory for deployment metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                'awslabs.aws_serverless_mcp_server.utils.deployment_manager.DEPLOYMENT_STATUS_DIR',
                temp_dir,
            ):
                yield temp_dir

    @pytest.mark.asyncio
    async def test_initialize_deployment_status_with_region(self, temp_deployment_dir):
        """Test initializing deployment status with region."""
        await initialize_deployment_status('test-project', 'backend', 'express', 'us-east-1')

        metadata_file = os.path.join(temp_deployment_dir, 'test-project.json')
        assert os.path.exists(metadata_file)

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert metadata['projectName'] == 'test-project'
        assert metadata['deploymentType'] == 'backend'
        assert metadata['framework'] == 'express'
        assert metadata['region'] == 'us-east-1'
        assert metadata['status'] == DeploymentStatus.IN_PROGRESS
        assert 'timestamp' in metadata

    @pytest.mark.asyncio
    async def test_initialize_deployment_status_without_region(self, temp_deployment_dir):
        """Test initializing deployment status without region."""
        await initialize_deployment_status('test-project', 'frontend', 'react', None)

        metadata_file = os.path.join(temp_deployment_dir, 'test-project.json')
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert 'region' not in metadata
        assert metadata['status'] == DeploymentStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_initialize_deployment_status_file_creation_error(self, temp_deployment_dir):
        """Test handling file creation errors during initialization."""
        # Make directory read-only to cause write error
        os.chmod(temp_deployment_dir, 0o444)

        try:
            # Should not raise exception, just log error
            await initialize_deployment_status('test-project', 'backend', 'express', 'us-east-1')

            metadata_file = os.path.join(temp_deployment_dir, 'test-project.json')
            assert not os.path.exists(metadata_file)
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_deployment_dir, 0o755)

    @pytest.mark.asyncio
    async def test_store_deployment_metadata_new_file(self, temp_deployment_dir):
        """Test storing metadata when file doesn't exist."""
        metadata = {
            'stackName': 'test-stack',
            'status': DeploymentStatus.DEPLOYED,
            'outputs': {'ApiUrl': 'https://api.example.com'},
        }

        await store_deployment_metadata('new-project', metadata)

        metadata_file = os.path.join(temp_deployment_dir, 'new-project.json')
        assert os.path.exists(metadata_file)

        with open(metadata_file, 'r') as f:
            stored_metadata = json.load(f)

        assert stored_metadata['stackName'] == 'test-stack'
        assert stored_metadata['status'] == DeploymentStatus.DEPLOYED
        assert 'lastUpdated' in stored_metadata

    @pytest.mark.asyncio
    async def test_store_deployment_metadata_existing_file(self, temp_deployment_dir):
        """Test storing metadata when file already exists."""
        # Create initial file
        await initialize_deployment_status('existing-project', 'backend', 'express', 'us-east-1')

        # Update with new metadata
        new_metadata = {'stackName': 'updated-stack', 'status': DeploymentStatus.DEPLOYED}

        await store_deployment_metadata('existing-project', new_metadata)

        metadata_file = os.path.join(temp_deployment_dir, 'existing-project.json')
        with open(metadata_file, 'r') as f:
            stored_metadata = json.load(f)

        # Should merge with existing data
        assert stored_metadata['projectName'] == 'existing-project'  # From initial
        assert stored_metadata['stackName'] == 'updated-stack'  # From update
        assert stored_metadata['status'] == DeploymentStatus.DEPLOYED  # From update
        assert 'lastUpdated' in stored_metadata

    @pytest.mark.asyncio
    async def test_store_deployment_metadata_write_error(self, temp_deployment_dir):
        """Test handling write errors when storing metadata."""
        # Create initial file
        metadata_file = os.path.join(temp_deployment_dir, 'error-project.json')
        with open(metadata_file, 'w') as f:
            json.dump({'initial': 'data'}, f)

        # Make file read-only to cause write error
        os.chmod(metadata_file, 0o444)

        try:
            # Should not raise exception, just log error
            await store_deployment_metadata('error-project', {'new': 'data'})

            # File should remain unchanged
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            assert metadata == {'initial': 'data'}
        finally:
            # Restore permissions for cleanup
            os.chmod(metadata_file, 0o644)

    @pytest.mark.asyncio
    async def test_store_deployment_error_basic(self, temp_deployment_dir):
        """Test storing deployment error information."""
        error_message = 'Deployment failed'

        await store_deployment_error('failed-project', error_message)

        metadata_file = os.path.join(temp_deployment_dir, 'failed-project.json')
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert metadata['status'] == DeploymentStatus.FAILED
        assert metadata['error'] == 'Deployment failed'
        assert 'errorTimestamp' in metadata
        assert 'lastUpdated' in metadata

    @pytest.mark.asyncio
    async def test_store_deployment_error_with_exception(self, temp_deployment_dir):
        """Test storing deployment error with exception object."""
        try:
            raise ValueError('Test exception')
        except Exception as e:
            await store_deployment_error('exception-project', e)

        metadata_file = os.path.join(temp_deployment_dir, 'exception-project.json')
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert metadata['status'] == DeploymentStatus.FAILED
        assert 'Test exception' in metadata['error']

    @pytest.mark.asyncio
    async def test_get_deployment_status_existing_file(self, temp_deployment_dir):
        """Test getting deployment status for existing project."""
        # Create test metadata
        metadata = {
            'projectName': 'test-project',
            'status': DeploymentStatus.DEPLOYED,
            'deploymentType': 'backend',
            'framework': 'express',
            'timestamp': '2024-01-01T00:00:00',
        }
        metadata_file = os.path.join(temp_deployment_dir, 'test-project.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info'
        ) as mock_get_stack:
            mock_get_stack.return_value = {
                'status': 'CREATE_COMPLETE',
                'statusReason': 'Stack created successfully',
                'outputs': {'ApiUrl': 'https://api.example.com'},
                'lastUpdatedTime': '2024-01-01T01:00:00',
            }

            result = await get_deployment_status('test-project')

            assert result['projectName'] == 'test-project'
            assert result['status'] == 'DEPLOYED'
            assert result['stackStatus'] == 'CREATE_COMPLETE'
            assert result['outputs']['ApiUrl'] == 'https://api.example.com'
            assert 'formattedOutputs' in result

    @pytest.mark.asyncio
    async def test_get_deployment_status_file_not_found(self, temp_deployment_dir):
        """Test getting deployment status when file doesn't exist."""
        result = await get_deployment_status('nonexistent-project')

        assert result['projectName'] == 'nonexistent-project'
        assert result['status'] == DeploymentStatus.NOT_FOUND
        assert result['message'] == 'No deployment found for project: nonexistent-project'

    @pytest.mark.asyncio
    async def test_get_deployment_status_invalid_json(self, temp_deployment_dir):
        """Test getting deployment status with invalid JSON file."""
        metadata_file = os.path.join(temp_deployment_dir, 'invalid-project.json')
        with open(metadata_file, 'w') as f:
            f.write('invalid json content')

        # The function raises an exception for invalid JSON
        with pytest.raises(Exception) as exc_info:
            await get_deployment_status('invalid-project')

        assert 'Failed to get deployment status' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_deployment_status_cloudformation_error(self, temp_deployment_dir):
        """Test getting deployment status when CloudFormation call fails."""
        metadata = {
            'projectName': 'cf-error-project',
            'status': DeploymentStatus.DEPLOYED,
            'deploymentType': 'backend',
            'framework': 'express',
            'timestamp': '2024-01-01T00:00:00',
        }
        metadata_file = os.path.join(temp_deployment_dir, 'cf-error-project.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info'
        ) as mock_get_stack:
            mock_get_stack.side_effect = Exception('CloudFormation error')

            result = await get_deployment_status('cf-error-project')

            assert result['projectName'] == 'cf-error-project'
            assert result['status'] == 'unknown'
            assert 'CloudFormation error' in result['message']

    @pytest.mark.asyncio
    async def test_list_deployments_with_files(self, temp_deployment_dir):
        """Test listing deployments when files exist."""
        # Create multiple deployment files
        deployments = [
            {
                'projectName': 'project1',
                'status': DeploymentStatus.DEPLOYED,
                'timestamp': '2024-01-01T00:00:00',
            },
            {
                'projectName': 'project2',
                'status': DeploymentStatus.IN_PROGRESS,
                'timestamp': '2024-01-02T00:00:00',
            },
            {
                'projectName': 'project3',
                'status': DeploymentStatus.FAILED,
                'timestamp': '2024-01-03T00:00:00',
            },
        ]

        for deployment in deployments:
            filename = f'{deployment["projectName"]}.json'
            filepath = os.path.join(temp_deployment_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(deployment, f)

        # Create a non-JSON file that should be ignored
        with open(os.path.join(temp_deployment_dir, 'not-json.txt'), 'w') as f:
            f.write('not json')

        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info'
        ) as mock_get_stack:
            mock_get_stack.return_value = {'status': 'NOT_FOUND'}

            result = await list_deployments()

            assert len(result) == 3
            project_names = [d['projectName'] for d in result]
            assert 'project1' in project_names
            assert 'project2' in project_names
            assert 'project3' in project_names

    @pytest.mark.asyncio
    async def test_list_deployments_empty_directory(self, temp_deployment_dir):
        """Test listing deployments when directory is empty."""
        result = await list_deployments()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_deployments_directory_not_exists(self):
        """Test listing deployments when directory doesn't exist."""
        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.DEPLOYMENT_STATUS_DIR',
            '/nonexistent/path',
        ):
            result = await list_deployments()
            assert result == []

    @pytest.mark.asyncio
    async def test_list_deployments_with_filters(self, temp_deployment_dir):
        """Test listing deployments with filters and sorting."""
        # Create test files
        deployments = [
            {
                'projectName': 'deployed1',
                'status': DeploymentStatus.DEPLOYED,
                'timestamp': '2024-01-01T00:00:00',
            },
            {
                'projectName': 'deployed2',
                'status': DeploymentStatus.DEPLOYED,
                'timestamp': '2024-01-03T00:00:00',
            },
            {
                'projectName': 'failed1',
                'status': DeploymentStatus.FAILED,
                'timestamp': '2024-01-02T00:00:00',
            },
        ]

        for deployment in deployments:
            filename = f'{deployment["projectName"]}.json'
            filepath = os.path.join(temp_deployment_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(deployment, f)

        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info'
        ) as mock_get_stack:
            mock_get_stack.return_value = {'status': 'NOT_FOUND'}

            # Test filtering by status
            result = await list_deployments(filter_status=DeploymentStatus.DEPLOYED)
            assert len(result) == 2

            # Test limit
            result = await list_deployments(limit=1)
            assert len(result) == 1

            # Test sorting
            result = await list_deployments(sort_by='timestamp', sort_order='asc')
            assert len(result) == 3
            assert result[0]['timestamp'] == '2024-01-01T00:00:00'

    @pytest.mark.asyncio
    async def test_list_deployments_processing_error(self, temp_deployment_dir):
        """Test listing deployments with file processing errors."""
        # Create valid file
        with open(os.path.join(temp_deployment_dir, 'valid.json'), 'w') as f:
            json.dump({'projectName': 'valid', 'status': 'DEPLOYED'}, f)

        # Create invalid JSON file
        with open(os.path.join(temp_deployment_dir, 'invalid.json'), 'w') as f:
            f.write('invalid json')

        with patch(
            'awslabs.aws_serverless_mcp_server.utils.deployment_manager.get_stack_info'
        ) as mock_get_stack:
            mock_get_stack.return_value = {'status': 'NOT_FOUND'}

            result = await list_deployments()

            # Should only return valid deployments
            assert len(result) == 1
            assert result[0]['projectName'] == 'valid'

    def test_deployment_status_constants(self):
        """Test that deployment status constants are properly defined."""
        assert DeploymentStatus.IN_PROGRESS == 'IN_PROGRESS'
        assert DeploymentStatus.DEPLOYED == 'DEPLOYED'
        assert DeploymentStatus.FAILED == 'FAILED'
        assert DeploymentStatus.NOT_FOUND == 'NOT_FOUND'
