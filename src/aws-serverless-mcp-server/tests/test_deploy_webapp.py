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
"""Tests for the deploy_webapp module."""

import json
import os
import pytest
import tempfile
from awslabs.aws_serverless_mcp_server.models import (
    BackendConfiguration,
    DeployWebAppRequest,
    FrontendConfiguration,
)
from awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp import (
    check_dependencies_installed,
    check_destructive_deployment_change,
    deploy_webapp,
)
from unittest.mock import mock_open, patch


class TestDeployWebapp:
    """Tests for the deploy_webapp module."""

    def test_check_dependencies_installed_nodejs(self):
        """Test checking for Node.js dependencies."""
        with patch('os.path.exists', return_value=True):
            # Test with Node.js runtime
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'nodejs18.x'
            )
            assert result is True

        with patch('os.path.exists', return_value=False):
            # Test with Node.js runtime but no node_modules
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'nodejs18.x'
            )
            assert result is False

    def test_check_dependencies_installed_python(self):
        """Test checking for Python dependencies."""
        # Test with site-packages directory
        with patch('os.path.exists', side_effect=lambda path: 'site-packages' in path):
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'python3.9'
            )
            assert result is True

        # Test with .dist-info files
        with (
            patch('os.path.exists', return_value=False),
            patch('os.listdir', return_value=['requests-2.28.1.dist-info', 'boto3']),
        ):
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'python3.9'
            )
            assert result is True

        # Test with no dependencies
        with (
            patch('os.path.exists', return_value=False),
            patch('os.listdir', return_value=['app.py', 'utils']),
        ):
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'python3.9'
            )
            assert result is False

    def test_check_dependencies_installed_ruby(self):
        """Test checking for Ruby dependencies."""
        with patch('os.path.exists', side_effect=lambda path: 'vendor/bundle' in path):
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'ruby3.2'
            )
            assert result is True

        with patch('os.path.exists', return_value=False):
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'ruby3.2'
            )
            assert result is False

    def test_check_dependencies_installed_other_runtime(self):
        """Test checking for dependencies with other runtimes."""
        # For other runtimes, we assume dependencies are installed
        result = check_dependencies_installed(
            os.path.join(tempfile.gettempdir(), 'artifacts'), 'java11'
        )
        assert result is True

    def test_check_dependencies_installed_exception(self):
        """Test checking for dependencies with an exception."""
        with patch('os.path.exists', side_effect=Exception('Test error')):
            result = check_dependencies_installed(
                os.path.join(tempfile.gettempdir(), 'artifacts'), 'nodejs18.x'
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_check_destructive_deployment_change_no_existing_deployment(self):
        """Test checking for destructive deployment change with no existing deployment."""
        with patch('os.path.exists', return_value=False):
            result = await check_destructive_deployment_change('test-project', 'backend')
            assert result['isDestructive'] is False

    @pytest.mark.asyncio
    async def test_check_destructive_deployment_change_same_type(self):
        """Test checking for destructive deployment change with same type."""
        status_data = {'deploymentType': 'backend', 'status': 'COMPLETED'}

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=json.dumps(status_data))),
        ):
            result = await check_destructive_deployment_change('test-project', 'backend')
            assert result['isDestructive'] is False

    @pytest.mark.asyncio
    async def test_check_destructive_deployment_change_destructive(self):
        """Test checking for destructive deployment change with destructive change."""
        status_data = {'deploymentType': 'backend', 'status': 'COMPLETED'}

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=json.dumps(status_data))),
        ):
            result = await check_destructive_deployment_change('test-project', 'frontend')
            assert result['isDestructive'] is True
            assert 'WARNING' in result['warning']
            assert 'destructive' in result['warning']

    @pytest.mark.asyncio
    async def test_check_destructive_deployment_change_non_destructive(self):
        """Test checking for destructive deployment change with non-destructive change."""
        status_data = {'deploymentType': 'backend', 'status': 'COMPLETED'}

        with (
            patch('os.path.exists', return_value=True),
            patch('builtins.open', mock_open(read_data=json.dumps(status_data))),
        ):
            result = await check_destructive_deployment_change('test-project', 'fullstack')
            assert result['isDestructive'] is False

    @pytest.mark.asyncio
    async def test_check_destructive_deployment_change_exception(self):
        """Test checking for destructive deployment change with an exception."""
        with patch('os.path.exists', side_effect=Exception('Test error')):
            result = await check_destructive_deployment_change('test-project', 'backend')
            assert result['isDestructive'] is False

    @pytest.mark.asyncio
    async def test_deploy_webapp_destructive_change(self):
        """Test deploying a webapp with a destructive change."""
        # Create a mock request
        request = DeployWebAppRequest(
            deployment_type='frontend',
            project_name='test-project',
            project_root=os.path.join(tempfile.gettempdir(), 'test-project'),
            region=None,
            frontend_configuration=FrontendConfiguration(
                built_assets_path=os.path.join(tempfile.gettempdir(), 'test-project/build'),
                framework=None,
                index_document=None,
                error_document=None,
                custom_domain=None,
                certificate_arn=None,
            ),
            backend_configuration=None,
        )

        # Mock check_destructive_deployment_change to return a destructive change
        mock_destructive_check = {
            'isDestructive': True,
            'warning': 'WARNING: Destructive change detected',
        }

        with patch(
            'awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp.check_destructive_deployment_change',
            return_value=mock_destructive_check,
        ):
            # Call the function
            result = await deploy_webapp(request)

            # Verify the result
            assert 'content' in result
            assert len(result['content']) > 0
            assert 'text' in result['content'][0]

            # Parse the JSON response
            response_json = json.loads(result['content'][0]['text'])
            assert response_json['success'] is False
            assert 'Destructive deployment type change detected' in response_json['message']
            assert 'warning' in response_json
            assert 'WARNING: Destructive change detected' in response_json['warning']

    @pytest.mark.asyncio
    async def test_deploy_webapp_missing_dependencies(self):
        """Test deploying a webapp with missing dependencies."""
        # Create a mock request
        request = DeployWebAppRequest(
            deployment_type='backend',
            project_name='test-project',
            project_root=os.path.join(tempfile.gettempdir(), 'test-project'),
            region=None,
            backend_configuration=BackendConfiguration(
                built_artifacts_path=os.path.join(tempfile.gettempdir(), 'test-project/dist'),
                runtime='nodejs18.x',
                port=3000,
                framework=None,
                startup_script=None,
                entry_point=None,
                generate_startup_script=None,
                architecture=None,
                memory_size=None,
                timeout=None,
                stage=None,
                cors=None,
                environment=None,
                database_configuration=None,
            ),
            frontend_configuration=None,
        )

        # Mock check_destructive_deployment_change to return non-destructive
        mock_destructive_check = {'isDestructive': False}

        with (
            patch(
                'awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp.check_destructive_deployment_change',
                return_value=mock_destructive_check,
            ),
            patch(
                'awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp.check_dependencies_installed',
                return_value=False,
            ),
        ):
            # Call the function
            result = await deploy_webapp(request)

            # Verify the result
            assert 'content' in result
            assert len(result['content']) > 0
            assert 'text' in result['content'][0]

            # Parse the JSON response
            response_json = json.loads(result['content'][0]['text'])
            assert response_json['success'] is False
            assert 'Dependencies not found' in response_json['message']
            assert 'instructions' in response_json
            assert 'npm install' in response_json['instructions']

    @pytest.mark.asyncio
    async def test_deploy_webapp_success(self):
        """Test deploying a webapp successfully."""
        # Create a mock request
        request = DeployWebAppRequest(
            deployment_type='backend',
            project_name='test-project',
            project_root=os.path.join(tempfile.gettempdir(), 'test-project'),
            region=None,
            backend_configuration=BackendConfiguration(
                built_artifacts_path=os.path.join(tempfile.gettempdir(), 'test-project/dist'),
                runtime='nodejs18.x',
                port=3000,
                framework=None,
                startup_script=None,
                entry_point=None,
                generate_startup_script=None,
                architecture=None,
                memory_size=None,
                timeout=None,
                stage=None,
                cors=None,
                environment=None,
                database_configuration=None,
            ),
            frontend_configuration=None,
        )

        # Mock check_destructive_deployment_change to return non-destructive
        mock_destructive_check = {'isDestructive': False}

        with (
            patch(
                'awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp.check_destructive_deployment_change',
                return_value=mock_destructive_check,
            ),
            patch(
                'awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp.check_dependencies_installed',
                return_value=True,
            ),
            patch('threading.Thread') as mock_thread,
        ):
            # Call the function
            result = await deploy_webapp(request)

            # Verify the result
            assert 'content' in result
            assert len(result['content']) > 0
            assert 'text' in result['content'][0]

            # Parse the JSON response
            response_json = json.loads(result['content'][0]['text'])
            assert response_json['success'] is True
            assert 'Deployment of test-project initiated successfully' in response_json['message']
            assert response_json['status'] == 'IN_PROGRESS'

            # Verify that a background thread was started
            mock_thread.assert_called_once()
            mock_thread.return_value.daemon = True
            mock_thread.return_value.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_webapp_exception(self):
        """Test deploying a webapp with an exception."""
        # Create a mock request
        request = DeployWebAppRequest(
            deployment_type='backend',
            project_name='test-project',
            project_root=os.path.join(tempfile.gettempdir(), 'test-project'),
            region=None,
            backend_configuration=BackendConfiguration(
                built_artifacts_path=os.path.join(tempfile.gettempdir(), 'test-project/dist'),
                runtime='nodejs18.x',
                port=3000,
                framework=None,
                startup_script=None,
                entry_point=None,
                generate_startup_script=None,
                architecture=None,
                memory_size=None,
                timeout=None,
                stage=None,
                cors=None,
                environment=None,
                database_configuration=None,
            ),
            frontend_configuration=None,
        )

        # Mock check_destructive_deployment_change to raise an exception
        with patch(
            'awslabs.aws_serverless_mcp_server.tools.webapps.deploy_webapp.check_destructive_deployment_change',
            side_effect=Exception('Test error'),
        ):
            # Call the function
            result = await deploy_webapp(request)

            # Verify the result
            assert 'content' in result
            assert len(result['content']) > 0
            assert 'text' in result['content'][0]

            # Parse the JSON response
            response_json = json.loads(result['content'][0]['text'])
            assert response_json['success'] is False
            assert 'Deployment failed' in response_json['message']
            assert 'Test error' in response_json['error']
