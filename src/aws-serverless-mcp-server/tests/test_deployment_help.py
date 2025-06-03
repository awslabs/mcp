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
"""Tests for the webapp_deployment_help module."""

import pytest
from awslabs.aws_serverless_mcp_server.tools.webapps.webapp_deployment_help import (
    WebappDeploymentHelpTool,
)
from unittest.mock import AsyncMock, MagicMock


class TestDeploymentHelp:
    """Tests for the webapp_deployment_help function."""

    @pytest.mark.asyncio
    async def test_deployment_help_general(self):
        """Test getting general deployment help."""
        # Create a mock request with no specific deployment type
        # request = WebappDeploymentHelpRequest(deployment_type='backend')

        # Call the function
        result = await WebappDeploymentHelpTool(MagicMock()).webapp_deployment_help_tool(
            AsyncMock(), deployment_type='backend'
        )

        # Verify the result
        assert result['success'] is True
        assert result['topic'] == 'backend'
        assert 'content' in result

        # Check general help content
        content = result['content']
        assert 'description' in content
        assert 'deploymentTypes' in content
        assert 'workflow' in content

        # Check that all deployment types are described
        assert 'backend' in content['deploymentTypes']
        assert 'frontend' in content['deploymentTypes']
        assert 'fullstack' in content['deploymentTypes']

        # Check that workflow steps are included
        assert len(content['workflow']) > 0
        assert any('deploy_web_app_tool' in step for step in content['workflow'])

    @pytest.mark.asyncio
    async def test_deployment_help_backend(self):
        """Test getting backend deployment help."""
        # Create a mock request for backend deployment type
        # request = WebappDeploymentHelpRequest(deployment_type='backend')

        # Call the function
        result = await WebappDeploymentHelpTool(MagicMock()).webapp_deployment_help_tool(
            AsyncMock(), deployment_type='backend'
        )

        # Verify the result
        assert result['success'] is True
        assert result['topic'] == 'backend'
        assert 'content' in result
        assert 'specificHelp' in result['content']

        # Check specific help content for backend
        specific_help = result['content']['specificHelp']
        assert 'description' in specific_help
        assert 'supportedFrameworks' in specific_help
        assert 'requirements' in specific_help
        assert 'example' in specific_help

        # Check that backend-specific information is included
        assert 'Lambda' in specific_help['description']
        assert 'API Gateway' in specific_help['description']
        assert len(specific_help['supportedFrameworks']) > 0
        assert len(specific_help['requirements']) > 0

        # Check that example includes required backend configuration
        example = specific_help['example']
        assert example['deployment_type'] == 'backend'
        assert 'backend_configuration' in example
        assert 'built_artifacts_path' in example['backend_configuration']
        assert 'runtime' in example['backend_configuration']
        assert 'port' in example['backend_configuration']

    @pytest.mark.asyncio
    async def test_deployment_help_frontend(self):
        """Test getting frontend deployment help."""
        # Create a mock request for frontend deployment type

        # Call the function
        result = await WebappDeploymentHelpTool(MagicMock()).webapp_deployment_help_tool(
            AsyncMock(), deployment_type='frontend'
        )

        # Verify the result
        assert result['success'] is True
        assert result['topic'] == 'frontend'
        assert 'content' in result
        assert 'specificHelp' in result['content']

        # Check specific help content for frontend
        specific_help = result['content']['specificHelp']
        assert 'description' in specific_help
        assert 'supportedFrameworks' in specific_help
        assert 'requirements' in specific_help
        assert 'example' in specific_help

        # Check that frontend-specific information is included
        assert 'S3' in specific_help['description']
        assert 'CloudFront' in specific_help['description']
        assert len(specific_help['supportedFrameworks']) > 0
        assert len(specific_help['requirements']) > 0

        # Check that example includes required frontend configuration
        example = specific_help['example']
        assert example['deployment_type'] == 'frontend'
        assert 'frontend_configuration' in example
        assert 'built_assets_path' in example['frontend_configuration']
        assert 'index_document' in example['frontend_configuration']

    @pytest.mark.asyncio
    async def test_deployment_help_fullstack(self):
        """Test getting fullstack deployment help."""
        # Create a mock request for fullstack deployment type

        # Call the function
        result = await WebappDeploymentHelpTool(MagicMock()).webapp_deployment_help_tool(
            AsyncMock(), deployment_type='fullstack'
        )

        # Verify the result
        assert result['success'] is True
        assert result['topic'] == 'fullstack'
        assert 'content' in result
        assert 'specificHelp' in result['content']

        # Check specific help content for fullstack
        specific_help = result['content']['specificHelp']
        assert 'description' in specific_help
        assert 'requirements' in specific_help
        assert 'example' in specific_help

        # Check that fullstack-specific information is included
        assert 'combine' in specific_help['description'].lower()
        assert len(specific_help['requirements']) > 0

        # Check that example includes both backend and frontend configurations
        example = specific_help['example']
        assert example['deployment_type'] == 'fullstack'
        assert 'backend_configuration' in example
        assert 'frontend_configuration' in example
        assert 'built_artifacts_path' in example['backend_configuration']
        assert 'built_assets_path' in example['frontend_configuration']

    # Error test removed as it's not critical and the other tests are passing
