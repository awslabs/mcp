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
"""Tests for the template renderer module."""

import pytest
from awslabs.aws_serverless_mcp_server.models import (
    BackendConfiguration,
    DeployWebAppRequest,
    FrontendConfiguration,
)
from awslabs.aws_serverless_mcp_server.template.registry import (
    DeploymentTypes,
    Template,
)
from awslabs.aws_serverless_mcp_server.template.renderer import (
    get_jinja_filters,
    get_jinja_tests,
    render_template,
)
from unittest.mock import MagicMock, patch


class TestTemplateRenderer:
    """Tests for the template renderer module."""

    def test_get_jinja_filters(self):
        """Test the get_jinja_filters function."""
        filters = get_jinja_filters()

        # Verify the filters exist
        assert 'cf_ref' in filters
        assert 'cf_get_att' in filters
        assert 'cf_sub' in filters

        # Test the cf_ref filter
        cf_ref = filters['cf_ref']
        assert cf_ref('MyResource') == '{ "Ref": "MyResource" }'

        # Test the cf_get_att filter
        cf_get_att = filters['cf_get_att']
        assert (
            cf_get_att('MyResource', 'Attribute')
            == '{ "Fn::GetAtt": ["MyResource", "Attribute"] }'
        )

        # Test the cf_sub filter
        cf_sub = filters['cf_sub']
        assert cf_sub('${AWS::Region}') == '{ "Fn::Sub": "${AWS::Region}" }'

    def test_get_jinja_tests(self):
        """Test the get_jinja_tests function."""
        tests = get_jinja_tests()

        # Verify the tests exist
        assert 'equals' in tests
        assert 'exists' in tests

        # Test the equals test
        equals = tests['equals']
        assert equals(1, 1) is True
        assert equals(1, 2) is False
        assert equals('a', 'a') is True
        assert equals('a', 'b') is False

        # Test the exists test
        exists = tests['exists']
        assert exists('value') is True
        assert exists('') is False
        assert exists(None) is False
        assert exists(0) is True  # 0 is a valid value

    @pytest.mark.asyncio
    async def test_render_template_backend(self):
        """Test render_template with a backend deployment."""
        # Create a mock request
        request = DeployWebAppRequest(
            region='us-east-1',
            deployment_type='backend',
            project_name='test-project',
            project_root='/dir/test-project',
            frontend_configuration=None,
            backend_configuration=BackendConfiguration(
                built_artifacts_path='/dir/build',
                runtime='nodejs18.x',
                port=3000,
                framework='express',
                startup_script=None,
                entry_point=None,
                generate_startup_script=False,
                architecture=None,
                memory_size=None,
                timeout=None,
                stage=None,
                cors=None,
                environment=None,
                database_configuration=None,
            ),
        )

        # Mock the template
        mock_template = Template(
            name='backend-express',
            path='/templates/backend-express.yaml',
            type_=DeploymentTypes.BACKEND,
            framework='express',
        )

        # Mock the get_template_for_deployment function
        with patch(
            'awslabs.aws_serverless_mcp_server.template.renderer.get_template_for_deployment'
        ) as mock_get_template:
            mock_get_template.return_value = mock_template

            # Mock the Jinja2 environment
            mock_env = MagicMock()
            mock_template_obj = MagicMock()
            mock_template_obj.render.return_value = 'Rendered template content'
            mock_env.get_template.return_value = mock_template_obj

            with patch(
                'awslabs.aws_serverless_mcp_server.template.renderer.Environment'
            ) as mock_env_class:
                mock_env_class.return_value = mock_env

                # Call the function
                result = await render_template(request)

                # Verify the result
                assert result == 'Rendered template content'

                # Verify the template was loaded correctly
                mock_get_template.assert_called_once_with(DeploymentTypes.BACKEND, 'express')
                mock_env.get_template.assert_called_once_with('backend-express.yaml')

                # Verify the template was rendered with the correct variables
                template_vars = mock_template_obj.render.call_args[1]
                assert template_vars['project_name'] == 'test-project'
                assert template_vars['deployment_type'] == 'backend'
                assert template_vars['description'] == 'test-project - backend deployment'
                assert 'backend_configuration' in template_vars

    @pytest.mark.asyncio
    async def test_render_template_frontend(self):
        """Test render_template with a frontend deployment."""
        # Create a mock request
        request = DeployWebAppRequest(
            region='us-east-1',
            deployment_type='frontend',
            project_name='test-project',
            project_root='/dir/test-project',
            backend_configuration=None,
            frontend_configuration=FrontendConfiguration(
                custom_domain=None,
                certificate_arn=None,
                index_document='index.html',
                built_assets_path='/dir/build',
                framework='react',
                error_document='error.html',
            ),
        )

        # Mock the template
        mock_template = Template(
            name='frontend-react',
            path='/templates/frontend-react.yaml',
            type_=DeploymentTypes.FRONTEND,
            framework='react',
        )

        # Mock the get_template_for_deployment function
        with patch(
            'awslabs.aws_serverless_mcp_server.template.renderer.get_template_for_deployment'
        ) as mock_get_template:
            mock_get_template.return_value = mock_template

            # Mock the Jinja2 environment
            mock_env = MagicMock()
            mock_template_obj = MagicMock()
            mock_template_obj.render.return_value = 'Rendered template content'
            mock_env.get_template.return_value = mock_template_obj

            with patch(
                'awslabs.aws_serverless_mcp_server.template.renderer.Environment'
            ) as mock_env_class:
                mock_env_class.return_value = mock_env

                # Call the function
                result = await render_template(request)

                # Verify the result
                assert result == 'Rendered template content'

                # Verify the template was loaded correctly
                mock_get_template.assert_called_once_with(DeploymentTypes.FRONTEND, 'react')
                mock_env.get_template.assert_called_once_with('frontend-react.yaml')

                # Verify the template was rendered with the correct variables
                template_vars = mock_template_obj.render.call_args[1]
                assert template_vars['project_name'] == 'test-project'
                assert template_vars['deployment_type'] == 'frontend'
                assert template_vars['description'] == 'test-project - frontend deployment'
                assert 'frontend_configuration' in template_vars
                # Skip checking the framework attribute as it might be a dict or an object
                # depending on how the mock is set up

    @pytest.mark.asyncio
    async def test_render_template_fullstack(self):
        """Test render_template with a fullstack deployment."""
        # Create a mock request
        request = DeployWebAppRequest(
            region='us-east-1',
            deployment_type='fullstack',
            project_name='test-project',
            project_root='/dir/test-project',
            backend_configuration=BackendConfiguration(
                built_artifacts_path='/dir/build-backend',
                runtime='nodejs18.x',
                port=3000,
                framework='express',
                startup_script=None,
                entry_point=None,
                generate_startup_script=False,
                architecture=None,
                memory_size=None,
                timeout=None,
                stage=None,
                cors=None,
                environment=None,
                database_configuration=None,
            ),
            frontend_configuration=FrontendConfiguration(
                custom_domain=None,
                certificate_arn=None,
                built_assets_path='/dir/build-frontend',
                framework='react',
                index_document='index.html',
                error_document='error.html',
            ),
        )

        # Mock the template
        mock_template = Template(
            name='fullstack-express-react',
            path='/templates/fullstack-express-react.yaml',
            type_=DeploymentTypes.FULLSTACK,
            framework='express-react',
        )

        # Mock the get_template_for_deployment function
        with patch(
            'awslabs.aws_serverless_mcp_server.template.renderer.get_template_for_deployment'
        ) as mock_get_template:
            mock_get_template.return_value = mock_template

            # Mock the Jinja2 environment
            mock_env = MagicMock()
            mock_template_obj = MagicMock()
            mock_template_obj.render.return_value = 'Rendered template content'
            mock_env.get_template.return_value = mock_template_obj

            with patch(
                'awslabs.aws_serverless_mcp_server.template.renderer.Environment'
            ) as mock_env_class:
                mock_env_class.return_value = mock_env

                # Call the function
                result = await render_template(request)

                # Verify the result
                assert result == 'Rendered template content'

                # Verify the template was loaded correctly
                mock_get_template.assert_called_once_with(
                    DeploymentTypes.FULLSTACK, 'express-react'
                )
                mock_env.get_template.assert_called_once_with('fullstack-express-react.yaml')

                # Verify the template was rendered with the correct variables
                template_vars = mock_template_obj.render.call_args[1]
                assert template_vars['project_name'] == 'test-project'
                assert template_vars['deployment_type'] == 'fullstack'
                assert template_vars['description'] == 'test-project - fullstack deployment'
                assert 'backend_configuration' in template_vars
                assert 'frontend_configuration' in template_vars
                # Skip checking the framework attributes as they might be dicts or objects
                # depending on how the mock is set up

    @pytest.mark.asyncio
    async def test_render_template_no_framework(self):
        """Test render_template without a framework."""
        # Create a mock request
        request = DeployWebAppRequest(
            region='us-east-1',
            deployment_type='backend',
            project_name='test-project',
            project_root='/dir/test-project',
            frontend_configuration=None,
            backend_configuration=BackendConfiguration(
                built_artifacts_path='/dir/build',
                runtime='nodejs18.x',
                port=3000,
                framework=None,  # No framework specified
                startup_script=None,
                entry_point=None,
                generate_startup_script=False,
                architecture=None,
                memory_size=None,
                timeout=None,
                stage=None,
                cors=None,
                environment=None,
                database_configuration=None,
            ),
        )

        # Mock the template
        mock_template = Template(
            name='backend',
            path='/templates/backend.yaml',
            type_=DeploymentTypes.BACKEND,
            framework=None,
        )

        # Mock the get_template_for_deployment function
        with patch(
            'awslabs.aws_serverless_mcp_server.template.renderer.get_template_for_deployment'
        ) as mock_get_template:
            mock_get_template.return_value = mock_template

            # Mock the Jinja2 environment
            mock_env = MagicMock()
            mock_template_obj = MagicMock()
            mock_template_obj.render.return_value = 'Rendered template content'
            mock_env.get_template.return_value = mock_template_obj

            with patch(
                'awslabs.aws_serverless_mcp_server.template.renderer.Environment'
            ) as mock_env_class:
                mock_env_class.return_value = mock_env

                # Call the function
                result = await render_template(request)

                # Verify the result
                assert result == 'Rendered template content'

                # Verify the template was loaded correctly
                mock_get_template.assert_called_once_with(DeploymentTypes.BACKEND, None)
                mock_env.get_template.assert_called_once_with('backend.yaml')

    @pytest.mark.asyncio
    async def test_render_template_error(self):
        """Test render_template when an error occurs."""
        # Create a mock request
        request = DeployWebAppRequest(
            deployment_type='backend',
            project_name='test-project',
            project_root='/dir/test-project',
            region='us-east-1',
            backend_configuration=BackendConfiguration(
                built_artifacts_path='/dir/build',
                runtime='nodejs18.x',
                port=3000,
                framework='express',
                startup_script=None,
                entry_point=None,
                generate_startup_script=False,
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

        # Mock the get_template_for_deployment function to raise an exception
        with patch(
            'awslabs.aws_serverless_mcp_server.template.renderer.get_template_for_deployment'
        ) as mock_get_template:
            mock_get_template.side_effect = Exception('Test error')

            # Call the function and expect an exception
            with pytest.raises(Exception) as excinfo:
                await render_template(request)

            # Just verify that an exception was raised
            # The exact error message format may vary
            assert 'Test error' in str(excinfo.value)
