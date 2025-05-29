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
"""Tests for the deployment_details resource."""

import pytest
from awslabs.aws_serverless_mcp_server.resources.deployment_details import (
    handle_deployment_details,
)
from awslabs.aws_serverless_mcp_server.utils.deployment_manager import DeploymentStatus
from unittest.mock import AsyncMock, patch


class TestDeploymentDetails:
    """Tests for the deployment_details resource."""

    @pytest.mark.asyncio
    async def test_handle_deployment_details_found(self):
        """Test the handle_deployment_details function with a found deployment."""
        # Mock data for deployment details
        mock_deployment = {
            'status': DeploymentStatus.DEPLOYED,
            'deploymentType': 'backend',
            'framework': 'express',
            'timestamp': '2025-05-28T12:00:00Z',
            'lastUpdated': '2025-05-28T12:30:00Z',
            'outputs': {'ApiUrl': 'https://api.example.com', 'FunctionName': 'test-function'},
            'stackStatus': 'CREATE_COMPLETE',
            'stackStatusReason': 'Stack creation completed successfully',
        }

        # Mock the get_deployment_status function
        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_details.get_deployment_status',
            new_callable=AsyncMock,
        ) as mock_get_status:
            mock_get_status.return_value = mock_deployment

            # Call the function
            project_name = 'test-project'
            result = await handle_deployment_details(project_name)

            # Verify the result structure
            assert result['success'] is True
            assert f"Deployment status retrieved for project '{project_name}'" in result['message']
            assert result['status'] == DeploymentStatus.DEPLOYED
            assert result['deploymentType'] == 'backend'
            assert result['framework'] == 'express'
            assert result['startedAt'] == '2025-05-28T12:00:00Z'
            assert result['updatedAt'] == '2025-05-28T12:30:00Z'
            assert result['outputs'] == {
                'ApiUrl': 'https://api.example.com',
                'FunctionName': 'test-function',
            }
            assert result['stackStatus'] == 'CREATE_COMPLETE'
            assert result['stackStatusReason'] == 'Stack creation completed successfully'

    @pytest.mark.asyncio
    async def test_handle_deployment_details_not_found(self):
        """Test the handle_deployment_details function with a not found deployment."""
        # Mock the get_deployment_status function to return a not found status
        mock_deployment = {'status': DeploymentStatus.NOT_FOUND}

        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_details.get_deployment_status',
            new_callable=AsyncMock,
        ) as mock_get_status:
            mock_get_status.return_value = mock_deployment

            # Call the function
            project_name = 'nonexistent-project'
            result = await handle_deployment_details(project_name)

            # Verify the result structure
            assert result['success'] is False
            assert f"No deployment found for project '{project_name}'" in result['message']
            assert result['status'] == 'NOT_FOUND'

    @pytest.mark.asyncio
    async def test_handle_deployment_details_exception(self):
        """Test the handle_deployment_details function when an exception occurs."""
        # Mock the get_deployment_status function to raise an exception
        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_details.get_deployment_status',
            new_callable=AsyncMock,
        ) as mock_get_status:
            mock_get_status.side_effect = Exception('Test exception')

            # Call the function
            project_name = 'test-project'
            result = await handle_deployment_details(project_name)

            # Verify the result structure
            assert result['success'] is False
            assert (
                f"Failed to get deployment status for project '{project_name}'"
                in result['message']
            )
            assert 'Test exception' in result['error']

    @pytest.mark.asyncio
    async def test_handle_deployment_details_in_progress(self):
        """Test the handle_deployment_details function with an in-progress deployment."""
        # Mock data for an in-progress deployment
        mock_deployment = {
            'status': DeploymentStatus.IN_PROGRESS,
            'deploymentType': 'fullstack',
            'framework': 'express+react',
            'timestamp': '2025-05-28T14:00:00Z',
            'lastUpdated': '2025-05-28T14:10:00Z',
            'stackStatus': 'CREATE_IN_PROGRESS',
            'stackStatusReason': 'Resource creation in progress',
        }

        # Mock the get_deployment_status function
        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_details.get_deployment_status',
            new_callable=AsyncMock,
        ) as mock_get_status:
            mock_get_status.return_value = mock_deployment

            # Call the function
            project_name = 'in-progress-project'
            result = await handle_deployment_details(project_name)

            # Verify the result structure
            assert result['success'] is True
            assert f"Deployment status retrieved for project '{project_name}'" in result['message']
            assert result['status'] == DeploymentStatus.IN_PROGRESS
            assert result['deploymentType'] == 'fullstack'
            assert result['framework'] == 'express+react'
            assert result['startedAt'] == '2025-05-28T14:00:00Z'
            assert result['updatedAt'] == '2025-05-28T14:10:00Z'
            assert result['stackStatus'] == 'CREATE_IN_PROGRESS'
            assert result['stackStatusReason'] == 'Resource creation in progress'

    @pytest.mark.asyncio
    async def test_handle_deployment_details_failed(self):
        """Test the handle_deployment_details function with a failed deployment."""
        # Mock data for a failed deployment
        mock_deployment = {
            'status': DeploymentStatus.FAILED,
            'deploymentType': 'frontend',
            'framework': 'react',
            'timestamp': '2025-05-28T15:00:00Z',
            'lastUpdated': '2025-05-28T15:05:00Z',
            'error': 'Resource creation failed',
            'stackStatus': 'CREATE_FAILED',
            'stackStatusReason': 'Resource creation failed: S3 bucket already exists',
        }

        # Mock the get_deployment_status function
        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_details.get_deployment_status',
            new_callable=AsyncMock,
        ) as mock_get_status:
            mock_get_status.return_value = mock_deployment

            # Call the function
            project_name = 'failed-project'
            result = await handle_deployment_details(project_name)

            # Verify the result structure
            assert result['success'] is True
            assert f"Deployment status retrieved for project '{project_name}'" in result['message']
            assert result['status'] == DeploymentStatus.FAILED
            assert result['deploymentType'] == 'frontend'
            assert result['framework'] == 'react'
            assert result['startedAt'] == '2025-05-28T15:00:00Z'
            assert result['updatedAt'] == '2025-05-28T15:05:00Z'
            assert result['error'] == 'Resource creation failed'
            assert result['stackStatus'] == 'CREATE_FAILED'
            assert (
                result['stackStatusReason'] == 'Resource creation failed: S3 bucket already exists'
            )
