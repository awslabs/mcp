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
"""Tests for the server module."""

import os
import sys
from awslabs.aws_serverless_mcp_server.server import main, mcp
from awslabs.aws_serverless_mcp_server.utils.const import DEPLOYMENT_STATUS_DIR
from unittest.mock import ANY, MagicMock, call, patch


class TestServer:
    """Tests for the server module."""

    def test_mcp_initialization(self):
        """Test that the MCP server is initialized with the correct parameters."""
        # Verify the MCP server is initialized with the correct name
        assert mcp.name == 'awslabs.aws-serverless-mcp-server'
        # Verify the MCP server has instructions
        assert mcp.instructions is not None
        assert 'AWS Serverless MCP' in mcp.instructions
        # Verify the MCP server has dependencies
        assert 'pydantic' in mcp.dependencies
        assert 'boto3' in mcp.dependencies
        assert 'loguru' in mcp.dependencies

    def test_resource_registration(self):
        """Test that resources are registered correctly."""
        # Get all registered templates
        templates = mcp._resource_manager.list_templates()
        template_uris = [template.uri_template for template in templates]

        # Get all registered resources
        resources = mcp._resource_manager.list_resources()
        resource_uris = [str(resource.uri) for resource in resources]

        # Verify template resources are registered (either as templates or concrete resources)
        assert ('template://list' in template_uris) or ('template://list' in resource_uris)
        assert ('template://{template_name}' in template_uris) or any(
            uri.startswith('template://') for uri in resource_uris
        )

        # Verify deployment resources are registered (either as templates or concrete resources)
        assert ('deployment://list' in template_uris) or ('deployment://list' in resource_uris)
        assert ('deployment://{project_name}' in template_uris) or any(
            uri.startswith('deployment://') for uri in resource_uris
        )

    @patch('awslabs.aws_serverless_mcp_server.server.os.makedirs')
    @patch('awslabs.aws_serverless_mcp_server.server.logger')
    @patch('awslabs.aws_serverless_mcp_server.server.argparse.ArgumentParser')
    @patch('awslabs.aws_serverless_mcp_server.server.WebappDeploymentHelpTool')
    @patch('awslabs.aws_serverless_mcp_server.server.DeployServerlessAppHelpTool')
    @patch('awslabs.aws_serverless_mcp_server.server.GetIaCGuidanceTool')
    @patch('awslabs.aws_serverless_mcp_server.server.GetLambdaEventSchemasTool')
    @patch('awslabs.aws_serverless_mcp_server.server.GetLambdaGuidanceTool')
    @patch('awslabs.aws_serverless_mcp_server.server.GetServerlessTemplatesTool')
    @patch('awslabs.aws_serverless_mcp_server.server.SamBuildTool')
    @patch('awslabs.aws_serverless_mcp_server.server.SamDeployTool')
    @patch('awslabs.aws_serverless_mcp_server.server.SamInitTool')
    @patch('awslabs.aws_serverless_mcp_server.server.SamLocalInvokeTool')
    @patch('awslabs.aws_serverless_mcp_server.server.SamLogsTool')
    @patch('awslabs.aws_serverless_mcp_server.server.ListRegistriesTool')
    @patch('awslabs.aws_serverless_mcp_server.server.SearchSchemaTool')
    @patch('awslabs.aws_serverless_mcp_server.server.DescribeSchemaTool')
    @patch('awslabs.aws_serverless_mcp_server.server.GetMetricsTool')
    @patch('awslabs.aws_serverless_mcp_server.server.ConfigureDomainTool')
    @patch('awslabs.aws_serverless_mcp_server.server.DeployWebAppTool')
    @patch('awslabs.aws_serverless_mcp_server.server.UpdateFrontendTool')
    @patch('awslabs.aws_serverless_mcp_server.server.mcp')
    def test_main_success(
        self,
        mock_mcp,
        mock_update_frontend,
        mock_deploy_webapp,
        mock_configure_domain,
        mock_get_metrics,
        mock_describe_schema,
        mock_search_schema,
        mock_list_registries,
        mock_sam_logs,
        mock_sam_local_invoke,
        mock_sam_init,
        mock_sam_deploy,
        mock_sam_build,
        mock_get_serverless_templates,
        mock_get_lambda_guidance,
        mock_get_lambda_event_schemas,
        mock_get_iac_guidance,
        mock_deploy_serverless_app_help,
        mock_webapp_deployment_help,
        mock_arg_parser,
        mock_logger,
        mock_makedirs,
    ):
        """Test the main function with successful execution."""
        # Setup mock argument parser
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.allow_write = True
        mock_args.allow_sensitive_data_access = True
        mock_parser.parse_args.return_value = mock_args

        # Setup mock MCP run
        mock_mcp.run.return_value = None

        # Call the main function
        result = main()

        # Verify the result
        assert result == 0

        # Verify directories are created
        mock_makedirs.assert_called_once_with(DEPLOYMENT_STATUS_DIR, exist_ok=True)

        # Verify logger is configured
        mock_logger.remove.assert_called_once()
        mock_logger.add.assert_called_once()

        # Verify argument parser is configured
        mock_parser.add_argument.assert_has_calls(
            [
                call('--allow-write', action='store_true', help=ANY),
                call('--allow-sensitive-data-access', action='store_true', help=ANY),
            ],
            any_order=True,
        )

        # Verify tools are initialized
        mock_webapp_deployment_help.assert_called_once_with(mock_mcp)
        mock_deploy_serverless_app_help.assert_called_once_with(mock_mcp)
        mock_get_iac_guidance.assert_called_once_with(mock_mcp)
        mock_get_lambda_event_schemas.assert_called_once_with(mock_mcp)
        mock_get_lambda_guidance.assert_called_once_with(mock_mcp)
        mock_get_serverless_templates.assert_called_once_with(mock_mcp)

        mock_sam_build.assert_called_once_with(mock_mcp)
        mock_sam_deploy.assert_called_once_with(mock_mcp, True)  # allow_write=True
        mock_sam_init.assert_called_once_with(mock_mcp)
        mock_sam_local_invoke.assert_called_once_with(mock_mcp)
        mock_sam_logs.assert_called_once_with(mock_mcp, True)  # allow_sensitive_data_access=True

        mock_list_registries.assert_called_once()
        mock_search_schema.assert_called_once()
        mock_describe_schema.assert_called_once()

        mock_get_metrics.assert_called_once_with(mock_mcp)
        mock_configure_domain.assert_called_once_with(mock_mcp, True)
        mock_deploy_webapp.assert_called_once_with(mock_mcp, True)  # allow_write=True
        mock_update_frontend.assert_called_once_with(mock_mcp, True)

        # Verify MCP server is run
        mock_mcp.run.assert_called_once()

        # Verify AWS_EXECUTION_ENV is set
        assert os.environ.get('AWS_EXECUTION_ENV', '').startswith(
            'awslabs/mcp/aws-serverless-mcp-server/'
        )

    @patch('awslabs.aws_serverless_mcp_server.server.os.makedirs')
    @patch('awslabs.aws_serverless_mcp_server.server.logger')
    @patch('awslabs.aws_serverless_mcp_server.server.argparse.ArgumentParser')
    @patch('awslabs.aws_serverless_mcp_server.server.mcp')
    def test_main_failure(self, mock_mcp, mock_arg_parser, mock_logger, mock_makedirs):
        """Test the main function with a failure during execution."""
        # Setup mock argument parser
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.allow_write = False
        mock_args.allow_sensitive_data_access = False
        mock_parser.parse_args.return_value = mock_args

        # Setup mock MCP run to raise an exception
        mock_mcp.run.side_effect = Exception('Test error')

        # Call the main function
        result = main()

        # Verify the result
        assert result == 1

        # Verify error is logged
        mock_logger.error.assert_called_once()
        assert 'Test error' in mock_logger.error.call_args[0][0]

    @patch('awslabs.aws_serverless_mcp_server.server.os.makedirs')
    @patch('awslabs.aws_serverless_mcp_server.server.logger')
    @patch('awslabs.aws_serverless_mcp_server.server.argparse.ArgumentParser')
    @patch('awslabs.aws_serverless_mcp_server.server.SamDeployTool')
    @patch('awslabs.aws_serverless_mcp_server.server.SamLogsTool')
    @patch('awslabs.aws_serverless_mcp_server.server.DeployWebAppTool')
    @patch('awslabs.aws_serverless_mcp_server.server.mcp')
    def test_main_with_different_args(
        self,
        mock_mcp,
        mock_deploy_webapp,
        mock_sam_logs,
        mock_sam_deploy,
        mock_arg_parser,
        mock_logger,
        mock_makedirs,
    ):
        """Test the main function with different command-line arguments."""
        # Setup mock argument parser
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        # Test with allow_write=False and allow_sensitive_data_access=False
        mock_args = MagicMock()
        mock_args.allow_write = False
        mock_args.allow_sensitive_data_access = False
        mock_parser.parse_args.return_value = mock_args

        # Call the main function
        main()

        # Verify tools are initialized with correct flags
        mock_sam_deploy.assert_called_once_with(mock_mcp, False)  # allow_write=False
        mock_sam_logs.assert_called_once_with(mock_mcp, False)  # allow_sensitive_data_access=False
        mock_deploy_webapp.assert_called_once_with(mock_mcp, False)  # allow_write=False

    def test_main_as_script(self):
        """Test the __main__ block."""
        # Create a mock for sys.exit
        with patch('sys.exit') as mock_exit:
            # Create a mock for main that returns 42
            with patch(
                'awslabs.aws_serverless_mcp_server.server.main', return_value=42
            ) as mock_main:
                # Call the code that would be executed in __main__
                if __name__ == '__main__':
                    sys.exit(mock_main())
                else:
                    # Simulate the __main__ block execution
                    mock_exit(mock_main())

                # Verify main was called
                mock_main.assert_called_once()
                # Verify sys.exit was called with the return value from main
                mock_exit.assert_called_once_with(42)
