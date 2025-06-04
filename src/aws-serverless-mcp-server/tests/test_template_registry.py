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
"""Tests for the template registry module."""

import os
import pytest
from awslabs.aws_serverless_mcp_server.template.registry import (
    DeploymentTypes,
    Template,
    discover_templates,
    get_template_for_deployment,
    get_templates_path,
)
from pathlib import Path
from unittest.mock import patch


class TestTemplateRegistry:
    """Tests for the template registry module."""

    def test_template_class_initialization(self):
        """Test the Template class initialization."""
        template = Template(
            name='test-template',
            path='/path/to/template.yaml',
            type_=DeploymentTypes.BACKEND,
            framework='express',
        )

        assert template.name == 'test-template'
        assert template.path == '/path/to/template.yaml'
        assert template.type == DeploymentTypes.BACKEND
        assert template.framework == 'express'

    def test_template_class_initialization_no_framework(self):
        """Test the Template class initialization without a framework."""
        template = Template(
            name='test-template', path='/path/to/template.yaml', type_=DeploymentTypes.BACKEND
        )

        assert template.name == 'test-template'
        assert template.path == '/path/to/template.yaml'
        assert template.type == DeploymentTypes.BACKEND
        assert template.framework is None

    @patch.dict(os.environ, {'TEMPLATES_PATH': '/custom/templates/path'})
    def test_get_templates_path_from_env(self):
        """Test get_templates_path when TEMPLATES_PATH environment variable is set."""
        path = get_templates_path()
        assert path == '/custom/templates/path'

    @patch.dict(os.environ, {}, clear=True)
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.glob')
    def test_get_templates_path_default_locations(self, mock_glob, mock_is_dir, mock_exists):
        """Test get_templates_path when checking default locations."""
        # Setup mocks to make the first path valid
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        mock_glob.return_value = [Path('/path/to/template.yaml')]

        path = get_templates_path()

        # Verify the first path was checked
        assert mock_exists.called
        assert mock_is_dir.called

        # The path should be the first valid path found
        assert path.endswith('template/templates')

    @patch.dict(os.environ, {}, clear=True)
    @patch('os.path.exists')
    @patch('os.path.isdir')
    @patch('pathlib.Path.glob')
    def test_get_templates_path_no_valid_paths(self, mock_glob, mock_isdir, mock_exists):
        """Test get_templates_path when no valid paths are found."""
        # Setup mocks to make all paths invalid
        mock_exists.return_value = False
        mock_isdir.return_value = False
        mock_glob.return_value = []

        path = get_templates_path()

        # The path should default to the current directory
        assert path.endswith('templates')

    @pytest.mark.asyncio
    async def test_get_template_for_deployment_with_framework(self):
        """Test get_template_for_deployment with a framework specified."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('os.path.exists') as mock_exists:
                # Make the framework-specific template exist
                mock_exists.side_effect = lambda path: path == '/templates/backend-express.yaml'

                template = await get_template_for_deployment(DeploymentTypes.BACKEND, 'express')

                assert template.name == 'backend-express'
                assert template.path == '/templates/backend-express.yaml'
                assert template.type == DeploymentTypes.BACKEND
                assert template.framework == 'express'

    @pytest.mark.asyncio
    async def test_get_template_for_deployment_default_template(self):
        """Test get_template_for_deployment falling back to the default template."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('os.path.exists') as mock_exists:
                # Make only the default template exist
                mock_exists.side_effect = lambda path: path == '/templates/backend-default.yaml'

                template = await get_template_for_deployment(DeploymentTypes.BACKEND, 'express')

                assert template.name == 'backend-default'
                assert template.path == '/templates/backend-default.yaml'
                assert template.type == DeploymentTypes.BACKEND
                assert template.framework == 'express'  # Framework is still preserved

    @pytest.mark.asyncio
    async def test_get_template_for_deployment_generic_template(self):
        """Test get_template_for_deployment falling back to the generic template."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('os.path.exists') as mock_exists:
                # Make only the generic template exist
                mock_exists.side_effect = lambda path: path == '/templates/backend.yaml'

                template = await get_template_for_deployment(DeploymentTypes.BACKEND, 'express')

                assert template.name == 'backend'
                assert template.path == '/templates/backend.yaml'
                assert template.type == DeploymentTypes.BACKEND
                assert template.framework == 'express'  # Framework is still preserved

    @pytest.mark.asyncio
    async def test_get_template_for_deployment_no_template(self):
        """Test get_template_for_deployment when no template is found."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('os.path.exists') as mock_exists:
                # Make no templates exist
                mock_exists.return_value = False

                with pytest.raises(FileNotFoundError):
                    await get_template_for_deployment(DeploymentTypes.BACKEND, 'express')

    @pytest.mark.asyncio
    async def test_discover_templates(self):
        """Test discover_templates."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True

                with patch('pathlib.Path.glob') as mock_glob:
                    # Mock finding template files
                    mock_glob.side_effect = (
                        lambda pattern: [
                            Path('/templates/backend-express.yaml'),
                            Path('/templates/frontend-react.yaml'),
                            Path('/templates/fullstack.yaml'),
                            Path('/templates/invalid-name.yaml'),  # Should be skipped
                        ]
                        if pattern.endswith('*.yaml')
                        else []
                    )

                    templates = await discover_templates()

                    # Should find 3 valid templates
                    assert len(templates) == 3

                    # Verify the templates
                    template_names = [t.name for t in templates]
                    assert 'backend-express' in template_names
                    assert 'frontend-react' in template_names
                    assert 'fullstack' in template_names

                    # Verify the frameworks
                    backend_template = next(t for t in templates if t.name == 'backend-express')
                    assert backend_template.framework == 'express'

                    frontend_template = next(t for t in templates if t.name == 'frontend-react')
                    assert frontend_template.framework == 'react'

                    fullstack_template = next(t for t in templates if t.name == 'fullstack')
                    assert fullstack_template.framework is None

    @pytest.mark.asyncio
    async def test_discover_templates_empty_directory(self):
        """Test discover_templates with an empty directory."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True

                with patch('pathlib.Path.glob') as mock_glob:
                    # Mock finding no template files
                    mock_glob.return_value = []

                    templates = await discover_templates()

                    # Should find no templates
                    assert len(templates) == 0

    @pytest.mark.asyncio
    async def test_discover_templates_directory_not_exists(self):
        """Test discover_templates when the directory doesn't exist."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = False

                templates = await discover_templates()

                # Should find no templates
                assert len(templates) == 0

    @pytest.mark.asyncio
    async def test_discover_templates_error(self):
        """Test discover_templates when an error occurs."""
        with patch(
            'awslabs.aws_serverless_mcp_server.template.registry.get_templates_path'
        ) as mock_get_path:
            mock_get_path.return_value = '/templates'

            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.side_effect = Exception('Test error')

                with pytest.raises(Exception, match='Test error'):
                    await discover_templates()
