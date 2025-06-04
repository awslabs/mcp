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
"""Tests for the deployment_list resource."""

import json
import pytest
from awslabs.aws_serverless_mcp_server.resources.deployment_list import handle_deployments_list
from unittest.mock import AsyncMock, patch


class TestDeploymentList:
    """Tests for the deployment_list resource."""

    @pytest.mark.asyncio
    async def test_handle_deployments_list_with_deployments(self):
        """Test the handle_deployments_list function with deployments."""
        # Mock data for deployments
        mock_deployments = [
            {
                'projectName': 'test-project-1',
                'deploymentType': 'backend',
                'status': 'COMPLETE',
                'timestamp': '2025-05-28T12:00:00Z',
                'lastUpdated': '2025-05-28T12:30:00Z',
            },
            {
                'projectName': 'test-project-2',
                'deploymentType': 'frontend',
                'status': 'IN_PROGRESS',
                'timestamp': '2025-05-28T13:00:00Z',
                'lastUpdated': '2025-05-28T13:15:00Z',
            },
        ]

        # Mock the list_deployments function
        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_list.list_deployments',
            new_callable=AsyncMock,
        ) as mock_list_deployments:
            mock_list_deployments.return_value = mock_deployments

            # Call the function
            result = await handle_deployments_list()

            # Verify the result structure
            assert 'contents' in result
            assert 'metadata' in result
            assert 'count' in result['metadata']
            assert result['metadata']['count'] == len(mock_deployments)

            # Verify the contents
            assert len(result['contents']) == len(mock_deployments)

            # Verify each deployment
            for i, deployment in enumerate(result['contents']):
                assert deployment['uri'] == f'deployment://{mock_deployments[i]["projectName"]}'

                # Parse the deployment details
                deployment_details = json.loads(deployment['text'])
                assert deployment_details['projectName'] == mock_deployments[i]['projectName']
                assert deployment_details['type'] == mock_deployments[i]['deploymentType']
                assert deployment_details['status'] == mock_deployments[i]['status']
                assert deployment_details['timestamp'] == mock_deployments[i]['timestamp']
                assert deployment_details['lastUpdated'] == mock_deployments[i]['lastUpdated']

    @pytest.mark.asyncio
    async def test_handle_deployments_list_no_deployments(self):
        """Test the handle_deployments_list function with no deployments."""
        # Mock the list_deployments function to return an empty list
        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_list.list_deployments',
            new_callable=AsyncMock,
        ) as mock_list_deployments:
            mock_list_deployments.return_value = []

            # Call the function
            result = await handle_deployments_list()

            # Verify the result structure
            assert 'contents' in result
            assert 'metadata' in result
            assert 'count' in result['metadata']
            assert result['metadata']['count'] == 0
            assert 'message' in result['metadata']
            assert result['metadata']['message'] == 'No deployments found'

            # Verify the contents
            assert len(result['contents']) == 0

    @pytest.mark.asyncio
    async def test_handle_deployments_list_exception(self):
        """Test the handle_deployments_list function when an exception occurs."""
        # Mock the list_deployments function to raise an exception
        with patch(
            'awslabs.aws_serverless_mcp_server.resources.deployment_list.list_deployments',
            new_callable=AsyncMock,
        ) as mock_list_deployments:
            mock_list_deployments.side_effect = Exception('Test exception')

            # Call the function
            result = await handle_deployments_list()

            # Verify the result structure
            assert 'contents' in result
            assert 'metadata' in result
            assert 'count' in result['metadata']
            assert result['metadata']['count'] == 0
            assert 'error' in result['metadata']
            assert 'Failed to list deployments' in result['metadata']['error']

            # Verify the contents
            assert len(result['contents']) == 0
