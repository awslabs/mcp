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
"""Tests for the AWS Serverless MCP Server."""

import argparse
import awslabs.aws_serverless_mcp_server.server
import os
import pytest
import tempfile
from awslabs.aws_serverless_mcp_server.server import (
    configure_domain_tool,
    deploy_serverless_app_help_tool,
    deploy_webapp_tool,
    describe_schema,
    get_iac_guidance_tool,
    get_lambda_event_schemas_tool,
    get_lambda_guidance_tool,
    get_metrics_tool,
    get_serverless_templates_tool,
    list_registries,
    main,
    sam_build_tool,
    sam_deploy_tool,
    sam_init_tool,
    sam_local_invoke_tool,
    sam_logs_tool,
    search_schema,
    update_webapp_frontend_tool,
    webapp_deployment_help_tool,
)
from awslabs.aws_serverless_mcp_server.tools.guidance.deploy_serverless_app_help import (
    ApplicationType,
)
from unittest.mock import AsyncMock, MagicMock, patch


class MockContext:
    """Mock context for testing."""

    async def info(self, message):
        """Mock info method."""
        pass

    async def error(self, message):
        """Mock error method."""
        pass


class TestSamBuildTool:
    """Tests for the sam_build_tool function."""

    @pytest.mark.asyncio
    async def test_sam_build_tool(self):
        """Test the sam_build_tool function."""
        ctx = MockContext()

        # Mock the sam_build function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.handle_sam_build', new_callable=AsyncMock
        ) as mock_sam_build:
            mock_sam_build.return_value = {'success': True, 'message': 'Build successful'}

            # Call the function with individual parameters
            result = await sam_build_tool(
                ctx,
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file='template.yaml',
                base_dir=None,
                build_dir=None,
                use_container=False,
                no_use_container=True,
                container_env_vars=None,
                container_env_var_file=None,
                build_image=None,
                debug=False,
                manifest=None,
                parameter_overrides=None,
                region=None,
                save_params=False,
                profile=None,
            )

            # Verify the result
            assert result['message'] == 'Build successful'

            # Verify sam_build was called with the correct arguments
            mock_sam_build.assert_called_once()
            args = mock_sam_build.call_args[0][0]
            assert args.project_directory == os.path.join(tempfile.gettempdir(), 'test-project')


class TestSamInitTool:
    """Tests for the sam_init_tool function."""

    @pytest.mark.asyncio
    async def test_sam_init_tool(self):
        """Test the sam_init_tool function."""
        ctx = MockContext()

        # Mock the sam_init function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.handle_sam_init', new_callable=AsyncMock
        ) as mock_sam_init:
            mock_sam_init.return_value = {'success': True, 'message': 'Initialization successful'}

            # Call the function with individual parameters
            result = await sam_init_tool(
                ctx,
                project_name='test-project',
                runtime='nodejs18.x',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                dependency_manager='npm',
                architecture='x86_64',
                package_type='Zip',
                application_template='hello-world',
                application_insights=None,
                no_application_insights=None,
                base_image=None,
                config_env=None,
                config_file=None,
                debug=False,
                extra_content=None,
                location=None,
                save_params=None,
                tracing=None,
                no_tracing=None,
            )

            # Verify the result
            assert result['message'] == 'Initialization successful'

            # Verify sam_init was called with the correct arguments
            mock_sam_init.assert_called_once()
            args = mock_sam_init.call_args[0][0]
            assert args.project_name == 'test-project'
            assert args.runtime == 'nodejs18.x'
            assert args.project_directory == os.path.join(tempfile.gettempdir(), 'test-project')
            assert args.dependency_manager == 'npm'


class TestSamDeployTool:
    """Tests for the sam_deploy_tool function."""

    @pytest.mark.asyncio
    async def test_sam_deploy_tool(self):
        """Test the sam_deploy_tool function."""
        ctx = MockContext()

        # Mock the sam_deploy function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.handle_sam_deploy', new_callable=AsyncMock
        ) as mock_sam_deploy:
            mock_sam_deploy.return_value = {'success': True, 'message': 'Deployment successful'}
            # Set a global variable for test
            awslabs.aws_serverless_mcp_server.server.allow_write = True
            # Call the function with individual parameters
            result = await sam_deploy_tool(
                ctx,
                application_name='test-app',
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                template_file='template.yaml',
                s3_bucket='test-bucket',
                s3_prefix='test-prefix',
                region='us-east-1',
                profile='default',
                parameter_overrides='{}',
                capabilities=[],
                config_file=None,
                config_env=None,
                metadata={},
                tags={},
                resolve_s3=False,
                debug=False,
            )

            # Verify the result
            assert result['message'] == 'Deployment successful'

            # Verify sam_deploy was called with the correct arguments
            mock_sam_deploy.assert_called_once()
            args = mock_sam_deploy.call_args[0][0]
            assert args.application_name == 'test-app'
            assert args.project_directory == os.path.join(tempfile.gettempdir(), 'test-project')


class TestSamLogsTool:
    """Tests for the sam_logs_tool function."""

    @pytest.mark.asyncio
    async def test_sam_logs_tool_with_sensitive_data_allowed(self):
        """Test the sam_logs_tool function when sensitive data access is allowed."""
        ctx = MockContext()

        # Set the global variable for test
        awslabs.aws_serverless_mcp_server.server.allow_sensitive_data_access = True

        # Mock the handle_sam_logs function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.handle_sam_logs', new_callable=AsyncMock
        ) as mock_sam_logs:
            mock_sam_logs.return_value = {'success': True, 'logs': 'Sample logs data'}

            # Call the function with individual parameters
            result = await sam_logs_tool(
                ctx,
                resource_name='test-function',
                stack_name='test-stack',
                start_time='5mins ago',
                end_time=None,
                output='text',
                region='us-east-1',
                profile='default',
                cw_log_group=None,
                config_env=None,
                config_file=None,
                save_params=False,
            )

            # Verify the result
            assert result['success'] is True
            assert result['logs'] == 'Sample logs data'

            # Verify handle_sam_logs was called with the correct arguments
            mock_sam_logs.assert_called_once()
            args = mock_sam_logs.call_args[0][0]
            assert args.resource_name == 'test-function'
            assert args.stack_name == 'test-stack'

    @pytest.mark.asyncio
    async def test_sam_logs_tool_without_sensitive_data_allowed(self):
        """Test the sam_logs_tool function when sensitive data access is not allowed."""
        ctx = MockContext()

        # Set the global variable for test
        awslabs.aws_serverless_mcp_server.server.allow_sensitive_data_access = False

        # Call the function with individual parameters
        result = await sam_logs_tool(
            ctx,
            resource_name='test-function',
            stack_name='test-stack',
            start_time='5mins ago',
            end_time=None,
            output='text',
            region='us-east-1',
            profile='default',
            cw_log_group=None,
            config_env=None,
            config_file=None,
            save_params=False,
        )

        # Verify the result
        assert result['success'] is False
        assert 'error' in result
        assert 'Sensitive data access is not allowed' in result['error']


class TestSamLocalInvokeTool:
    """Tests for the sam_local_invoke_tool function."""

    @pytest.mark.asyncio
    async def test_sam_local_invoke_tool(self):
        """Test the sam_local_invoke_tool function."""
        ctx = MockContext()

        # Mock the handle_sam_local_invoke function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.handle_sam_local_invoke',
            new_callable=AsyncMock,
        ) as mock_sam_local_invoke:
            mock_sam_local_invoke.return_value = {
                'success': True,
                'output': 'Function invocation successful',
            }

            # Call the function with individual parameters
            result = await sam_local_invoke_tool(
                ctx,
                project_directory=os.path.join(tempfile.gettempdir(), 'test-project'),
                resource_name='HelloWorldFunction',
                template_file='template.yaml',
                event_file=None,
                event_data='{"key": "value"}',
                environment_variables_file=None,
                docker_network=None,
                container_env_vars=None,
                parameter=None,
                log_file=None,
                layer_cache_basedir=None,
                region='us-east-1',
                profile='default',
            )

            # Verify the result
            assert result['success'] is True
            assert result['output'] == 'Function invocation successful'

            # Verify handle_sam_local_invoke was called with the correct arguments
            mock_sam_local_invoke.assert_called_once()
            args = mock_sam_local_invoke.call_args[0][0]
            assert args.project_directory == os.path.join(tempfile.gettempdir(), 'test-project')
            assert args.resource_name == 'HelloWorldFunction'
            assert args.event_data == '{"key": "value"}'


class TestGetIaCGuidanceTool:
    """Tests for the get_iac_guidance_tool function."""

    @pytest.mark.asyncio
    async def test_get_iac_guidance_tool(self):
        """Test the get_iac_guidance_tool function."""
        ctx = MockContext()

        # Call the function with individual parameters
        result = await get_iac_guidance_tool(ctx, iac_tool='SAM', include_examples=True)

        # Verify the result
        assert 'title' in result
        assert (
            result['title']
            == 'Using AWS Infrastructure as Code (IaC) Tools for Serverless Deployments'
        )


class TestGetLambdaGuidanceTool:
    """Tests for the get_lambda_guidance_tool function."""

    @pytest.mark.asyncio
    async def test_get_lambda_guidance_tool(self):
        """Test the get_lambda_guidance_tool function."""
        ctx = MockContext()

        # Mock the get_lambda_guidance function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.get_lambda_guidance', new_callable=AsyncMock
        ) as mock_get_lambda_guidance:
            mock_get_lambda_guidance.return_value = {
                'title': 'AWS Lambda Guidance',
                'content': 'Sample guidance content',
            }

            # Call the function with individual parameters
            result = await get_lambda_guidance_tool(
                ctx,
                use_case='API backend',
                include_examples=True,
            )

            # Verify the result
            assert result['title'] == 'AWS Lambda Guidance'
            assert result['content'] == 'Sample guidance content'

            # Verify get_lambda_guidance was called with the correct arguments
            mock_get_lambda_guidance.assert_called_once()
            args = mock_get_lambda_guidance.call_args[0][0]
            assert args.use_case == 'API backend'
            assert args.include_examples is True


class TestGetLambdaEventSchemasTool:
    """Tests for the get_lambda_event_schemas_tool function."""

    @pytest.mark.asyncio
    async def test_get_lambda_event_schemas_tool(self):
        """Test the get_lambda_event_schemas_tool function."""
        ctx = MockContext()

        # Mock the get_lambda_event_schemas function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.get_lambda_event_schemas',
            new_callable=AsyncMock,
        ) as mock_get_lambda_event_schemas:
            mock_get_lambda_event_schemas.return_value = {
                'event_source': 's3',
                'runtime': 'nodejs',
                'schema': 'Sample schema content',
            }

            # Call the function with individual parameters
            result = await get_lambda_event_schemas_tool(
                ctx,
                event_source='s3',
                runtime='nodejs',
            )

            # Verify the result
            assert result['event_source'] == 's3'
            assert result['runtime'] == 'nodejs'
            assert result['schema'] == 'Sample schema content'

            # Verify get_lambda_event_schemas was called with the correct arguments
            mock_get_lambda_event_schemas.assert_called_once()
            args = mock_get_lambda_event_schemas.call_args[0][0]
            assert args.event_source == 's3'
            assert args.runtime == 'nodejs'


class TestDeployWebappTool:
    """Tests for the deploy_webapp_tool function."""

    @pytest.mark.asyncio
    async def test_deploy_webapp_tool_with_write_allowed(self):
        """Test the deploy_webapp_tool function when write is allowed."""
        ctx = MockContext()

        # Set the global variable for test
        awslabs.aws_serverless_mcp_server.server.allow_write = True

        # Mock the deploy_webapp function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.deploy_webapp', new_callable=AsyncMock
        ) as mock_deploy_webapp:
            mock_deploy_webapp.return_value = {
                'success': True,
                'message': 'Deployment successful',
                'outputs': {'ApiUrl': 'https://example.com/api'},
            }

            # Call the function with individual parameters
            result = await deploy_webapp_tool(
                ctx,
                deployment_type='backend',
                project_name='test-project',
                project_root=os.path.join(tempfile.gettempdir(), 'test-project'),
                region='us-east-1',
                backend_configuration=None,
                frontend_configuration=None,
            )

            # Verify the result
            assert result['success'] is True
            assert result['message'] == 'Deployment successful'
            assert result['outputs']['ApiUrl'] == 'https://example.com/api'

            # Verify deploy_webapp was called with the correct arguments
            mock_deploy_webapp.assert_called_once()
            args = mock_deploy_webapp.call_args[0][0]
            assert args.deployment_type == 'backend'
            assert args.project_name == 'test-project'
            assert args.project_root == os.path.join(tempfile.gettempdir(), 'test-project')

    @pytest.mark.asyncio
    async def test_deploy_webapp_tool_without_write_allowed(self):
        """Test the deploy_webapp_tool function when write is not allowed."""
        ctx = MockContext()

        # Set the global variable for test
        awslabs.aws_serverless_mcp_server.server.allow_write = False

        # Call the function with individual parameters
        result = await deploy_webapp_tool(
            ctx,
            deployment_type='backend',
            project_name='test-project',
            project_root=os.path.join(tempfile.gettempdir(), 'test-project'),
            region='us-east-1',
            backend_configuration=None,
            frontend_configuration=None,
        )

        # Verify the result
        assert result['success'] is False
        assert 'error' in result
        assert 'Write operations are not allowed' in result['error']


class TestWebappDeploymentHelpTool:
    """Tests for the webapp_deployment_help_tool function."""

    @pytest.mark.asyncio
    async def test_webapp_deployment_help_tool(self):
        """Test the webapp_deployment_help_tool function."""
        ctx = MockContext()

        # Mock the webapp_deployment_help function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.webapp_deployment_help',
            new_callable=AsyncMock,
        ) as mock_webapp_deployment_help:
            mock_webapp_deployment_help.return_value = {
                'deployment_type': 'backend',
                'help': 'Sample deployment help content',
            }

            # Call the function with individual parameters
            result = await webapp_deployment_help_tool(
                ctx,
                deployment_type='backend',
            )

            # Verify the result
            assert result['deployment_type'] == 'backend'
            assert result['help'] == 'Sample deployment help content'

            # Verify webapp_deployment_help was called with the correct arguments
            mock_webapp_deployment_help.assert_called_once()
            args = mock_webapp_deployment_help.call_args[0][0]
            assert args.deployment_type == 'backend'


class TestGetMetricsTool:
    """Tests for the get_metrics_tool function."""

    @pytest.mark.asyncio
    async def test_get_metrics_tool(self):
        """Test the get_metrics_tool function."""
        ctx = MockContext()

        # Mock the get_metrics function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.get_metrics', new_callable=AsyncMock
        ) as mock_get_metrics:
            mock_get_metrics.return_value = {
                'project_name': 'test-project',
                'metrics': {'lambda': {'invocations': 100, 'errors': 5}},
            }

            # Call the function with individual parameters
            result = await get_metrics_tool(
                ctx,
                project_name='test-project',
                start_time='2023-01-01T00:00:00Z',
                end_time='2023-01-02T00:00:00Z',
                period=60,
                resources=['lambda', 'apiGateway'],
                region='us-east-1',
                stage='prod',
            )

            # Verify the result
            assert result['project_name'] == 'test-project'
            assert result['metrics']['lambda']['invocations'] == 100
            assert result['metrics']['lambda']['errors'] == 5

            # Verify get_metrics was called with the correct arguments
            mock_get_metrics.assert_called_once()
            args = mock_get_metrics.call_args[0][0]
            assert args.project_name == 'test-project'
            assert args.start_time == '2023-01-01T00:00:00Z'
            assert args.end_time == '2023-01-02T00:00:00Z'


class TestUpdateWebappFrontendTool:
    """Tests for the update_webapp_frontend_tool function."""

    @pytest.mark.asyncio
    async def test_update_webapp_frontend_tool(self):
        """Test the update_webapp_frontend_tool function."""
        ctx = MockContext()

        # Mock the update_webapp_frontend function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.update_webapp_frontend',
            new_callable=AsyncMock,
        ) as mock_update_webapp_frontend:
            mock_update_webapp_frontend.return_value = {
                'success': True,
                'message': 'Frontend updated successfully',
            }

            # Call the function with individual parameters
            result = await update_webapp_frontend_tool(
                ctx,
                project_name='test-project',
                project_root=os.path.join(tempfile.gettempdir(), 'test-project'),
                built_assets_path=os.path.join(tempfile.gettempdir(), 'test-project', 'build'),
                invalidate_cache=True,
                region='us-east-1',
            )

            # Verify the result
            assert result['success'] is True
            assert result['message'] == 'Frontend updated successfully'

            # Verify update_webapp_frontend was called with the correct arguments
            mock_update_webapp_frontend.assert_called_once()
            args = mock_update_webapp_frontend.call_args[0][0]
            assert args.project_name == 'test-project'
            assert args.project_root == os.path.join(tempfile.gettempdir(), 'test-project')
            assert args.built_assets_path == os.path.join(
                tempfile.gettempdir(), 'test-project', 'build'
            )
            assert args.invalidate_cache is True


class TestConfigureDomainTool:
    """Tests for the configure_domain_tool function."""

    @pytest.mark.asyncio
    async def test_configure_domain_tool(self):
        """Test the configure_domain_tool function."""
        ctx = MockContext()

        # Mock the configure_domain function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.configure_domain', new_callable=AsyncMock
        ) as mock_configure_domain:
            mock_configure_domain.return_value = {
                'success': True,
                'message': 'Domain configured successfully',
            }

            # Call the function with individual parameters
            result = await configure_domain_tool(
                ctx,
                project_name='test-project',
                domain_name='example.com',
                create_certificate=True,
                create_route53_record=True,
                region='us-east-1',
            )

            # Verify the result
            assert result['success'] is True
            assert result['message'] == 'Domain configured successfully'

            # Verify configure_domain was called with the correct arguments
            mock_configure_domain.assert_called_once()
            args = mock_configure_domain.call_args[0][0]
            assert args.project_name == 'test-project'
            assert args.domain_name == 'example.com'
            assert args.create_certificate is True
            assert args.create_route53_record is True


class TestDeployServerlessAppHelpTool:
    """Tests for the deploy_serverless_app_help_tool function."""

    @pytest.mark.asyncio
    async def test_deploy_serverless_app_help_tool(self):
        """Test the deploy_serverless_app_help_tool function."""
        ctx = MockContext()

        # Mock the deploy_serverless_app_help function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.deploy_serverless_app_help',
            new_callable=AsyncMock,
        ) as mock_deploy_serverless_app_help:
            mock_deploy_serverless_app_help.return_value = {
                'title': 'Serverless App Deployment Guide',
                'content': 'Sample deployment guide content',
            }

            # Call the function with individual parameters
            result = await deploy_serverless_app_help_tool(
                ctx,
                application_type='event_driven',
            )

            # Verify the result
            assert result['title'] == 'Serverless App Deployment Guide'
            assert result['content'] == 'Sample deployment guide content'

            # Verify deploy_serverless_app_help was called with the correct arguments
            mock_deploy_serverless_app_help.assert_called_once()
            assert mock_deploy_serverless_app_help.call_args[0][0] == ApplicationType.EVENT_DRIVEN


class TestGetServerlessTemplatesTool:
    """Tests for the get_serverless_templates_tool function."""

    @pytest.mark.asyncio
    async def test_get_serverless_templates_tool(self):
        """Test the get_serverless_templates_tool function."""
        ctx = MockContext()

        # Mock the get_serverless_templates function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.get_serverless_templates',
            new_callable=AsyncMock,
        ) as mock_get_serverless_templates:
            mock_get_serverless_templates.return_value = {
                'template_type': 'API',
                'runtime': 'nodejs',
                'templates': ['Sample template 1', 'Sample template 2'],
            }

            # Call the function with individual parameters
            result = await get_serverless_templates_tool(
                ctx,
                template_type='API',
                runtime='nodejs',
            )

            # Verify the result
            assert result['template_type'] == 'API'
            assert result['runtime'] == 'nodejs'
            assert result['templates'] == ['Sample template 1', 'Sample template 2']

            # Verify get_serverless_templates was called with the correct arguments
            mock_get_serverless_templates.assert_called_once()
            args = mock_get_serverless_templates.call_args[0][0]
            assert args.template_type == 'API'
            assert args.runtime == 'nodejs'


class TestSchemaTools:
    """Tests for the schema-related tools."""

    @pytest.mark.asyncio
    async def test_list_registries(self):
        """Test the list_registries function."""
        ctx = MockContext()

        # Mock the list_registries_impl function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.list_registries_impl', new_callable=AsyncMock
        ) as mock_list_registries_impl:
            mock_list_registries_impl.return_value = {
                'registries': ['aws.events', 'custom-registry'],
            }

            # Call the function
            result = await list_registries(
                ctx,
                registry_name_prefix='aws',
                scope='AWS',
                limit=10,
                next_token=None,
            )

            # Verify the result
            assert result['registries'] == ['aws.events', 'custom-registry']

            # Verify list_registries_impl was called with the correct arguments
            mock_list_registries_impl.assert_called_once()
            assert mock_list_registries_impl.call_args[1]['registry_name_prefix'] == 'aws'
            assert mock_list_registries_impl.call_args[1]['scope'] == 'AWS'
            assert mock_list_registries_impl.call_args[1]['limit'] == 10

    @pytest.mark.asyncio
    async def test_search_schema(self):
        """Test the search_schema function."""
        ctx = MockContext()

        # Mock the search_schema_impl function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.search_schema_impl', new_callable=AsyncMock
        ) as mock_search_schema_impl:
            mock_search_schema_impl.return_value = {
                'schemas': ['aws.s3@ObjectCreated', 'aws.s3@ObjectRemoved'],
            }

            # Call the function
            result = await search_schema(
                ctx,
                keywords='aws.s3',
                registry_name='aws.events',
                limit=10,
                next_token=None,
            )

            # Verify the result
            assert result['schemas'] == ['aws.s3@ObjectCreated', 'aws.s3@ObjectRemoved']

            # Verify search_schema_impl was called with the correct arguments
            mock_search_schema_impl.assert_called_once()
            assert mock_search_schema_impl.call_args[1]['keywords'] == 'aws.s3'
            assert mock_search_schema_impl.call_args[1]['registry_name'] == 'aws.events'
            assert mock_search_schema_impl.call_args[1]['limit'] == 10

    @pytest.mark.asyncio
    async def test_describe_schema(self):
        """Test the describe_schema function."""
        ctx = MockContext()

        # Mock the describe_schema_impl function
        with patch(
            'awslabs.aws_serverless_mcp_server.server.describe_schema_impl', new_callable=AsyncMock
        ) as mock_describe_schema_impl:
            mock_describe_schema_impl.return_value = {
                'schema_name': 'aws.s3@ObjectCreated',
                'content': 'Sample schema content',
            }

            # Call the function
            result = await describe_schema(
                ctx,
                registry_name='aws.events',
                schema_name='aws.s3@ObjectCreated',
                schema_version=None,
            )

            # Verify the result
            assert result['schema_name'] == 'aws.s3@ObjectCreated'
            assert result['content'] == 'Sample schema content'

            # Verify describe_schema_impl was called with the correct arguments
            mock_describe_schema_impl.assert_called_once()
            assert mock_describe_schema_impl.call_args[1]['registry_name'] == 'aws.events'
            assert mock_describe_schema_impl.call_args[1]['schema_name'] == 'aws.s3@ObjectCreated'
            assert mock_describe_schema_impl.call_args[1]['schema_version'] is None


class TestMain:
    """Tests for the main function."""

    def test_main_success(self):
        """Test the main function when successful."""
        # Mock the argparse.ArgumentParser
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = argparse.Namespace(
            log_level='debug',
            log_output='/dir/logs',
            allow_write=True,
            allow_sensitive_data_access=True,
        )

        # Mock the FastMCP.run method
        with (
            patch('argparse.ArgumentParser', return_value=mock_parser),
            patch('awslabs.aws_serverless_mcp_server.server.mcp.run') as mock_run,
        ):
            # Call the function
            result = main()

            # Verify the result
            assert result == 0

            # Verify the mocks were called
            mock_parser.parse_args.assert_called_once()
            mock_run.assert_called_once()

            # Verify the global variables were set correctly
            assert awslabs.aws_serverless_mcp_server.server.allow_sensitive_data_access is True
            assert awslabs.aws_serverless_mcp_server.server.allow_write is True

    def test_main_exception(self):
        """Test the main function when an exception occurs."""
        # Mock the argparse.ArgumentParser
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = argparse.Namespace(
            log_level=None,
            log_output=None,
            allow_write=False,
            allow_sensitive_data_access=False,
        )

        # Mock the FastMCP.run method to raise an exception
        with (
            patch('argparse.ArgumentParser', return_value=mock_parser),
            patch(
                'awslabs.aws_serverless_mcp_server.server.mcp.run',
                side_effect=Exception('Test error'),
            ),
        ):
            # Call the function
            result = main()

            # Verify the result
            assert result == 1

            # Verify the mocks were called
            mock_parser.parse_args.assert_called_once()

            # Verify the global variables were set correctly
            assert awslabs.aws_serverless_mcp_server.server.allow_sensitive_data_access is False
            assert awslabs.aws_serverless_mcp_server.server.allow_write is False
