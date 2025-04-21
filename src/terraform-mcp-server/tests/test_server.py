# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the server module of the terraform-mcp-server."""

import pytest
from awslabs.terraform_mcp_server.server import (
    main,
    mcp,
    terraform_aws_provider_resources_listing,
    terraform_awscc_provider_resources_listing,
)
from unittest.mock import MagicMock, patch


class TestMCPServer:
    """Tests for the MCP server."""

    def test_mcp_initialization(self):
        """Test that the MCP server is initialized correctly."""
        assert mcp.name == 'terraform_mcp_server'
        assert mcp.instructions is not None and 'AWS-IA modules' in mcp.instructions
        assert 'pydantic' in mcp.dependencies
        assert 'loguru' in mcp.dependencies
        assert 'requests' in mcp.dependencies
        assert 'beautifulsoup4' in mcp.dependencies
        assert 'PyPDF2' in mcp.dependencies

    def test_mcp_dependencies(self):
        """Test that the MCP server has the required dependencies."""
        assert 'pydantic' in mcp.dependencies
        assert 'loguru' in mcp.dependencies
        assert 'requests' in mcp.dependencies
        assert 'beautifulsoup4' in mcp.dependencies
        assert 'PyPDF2' in mcp.dependencies


class TestTools:
    """Tests for the MCP tools."""

    def test_execute_terraform_command_registration(self):
        """Test that the execute_terraform_command tool is registered correctly."""
        tool = mcp._tool_manager.get_tool('ExecuteTerraformCommand')
        assert tool is not None
        assert tool.name == 'ExecuteTerraformCommand'
        assert 'Execute Terraform workflow commands' in tool.description

        # Verify the tool exists
        assert tool is not None
        assert tool.name == 'ExecuteTerraformCommand'
        assert 'Execute Terraform workflow commands' in tool.description

    def test_search_aws_provider_docs_registration(self):
        """Test that the search_aws_provider_docs tool is registered correctly."""
        tool = mcp._tool_manager.get_tool('SearchAwsProviderDocs')
        assert tool is not None
        assert tool.name == 'SearchAwsProviderDocs'
        assert 'Search AWS provider documentation' in tool.description

        # Verify the tool exists
        assert tool is not None
        assert tool.name == 'SearchAwsProviderDocs'
        assert 'Search AWS provider documentation' in tool.description

    def test_search_awscc_provider_docs_registration(self):
        """Test that the search_awscc_provider_docs tool is registered correctly."""
        tool = mcp._tool_manager.get_tool('SearchAwsccProviderDocs')
        assert tool is not None
        assert tool.name == 'SearchAwsccProviderDocs'
        assert 'Search AWSCC provider documentation' in tool.description

        # Verify the tool exists
        assert tool is not None
        assert tool.name == 'SearchAwsccProviderDocs'
        assert 'Search AWSCC provider documentation' in tool.description

    def test_search_specific_aws_ia_modules_registration(self):
        """Test that the search_specific_aws_ia_modules tool is registered correctly."""
        tool = mcp._tool_manager.get_tool('SearchSpecificAwsIaModules')
        assert tool is not None
        assert tool.name == 'SearchSpecificAwsIaModules'
        assert 'Search for specific AWS-IA Terraform modules' in tool.description

        # Verify the tool exists
        assert tool is not None
        assert tool.name == 'SearchSpecificAwsIaModules'
        assert 'Search for specific AWS-IA Terraform modules' in tool.description

    def test_run_checkov_scan_registration(self):
        """Test that the run_checkov_scan tool is registered correctly."""
        tool = mcp._tool_manager.get_tool('RunCheckovScan')
        assert tool is not None
        assert tool.name == 'RunCheckovScan'
        assert 'Run Checkov security scan' in tool.description

        # Verify the tool exists
        assert tool is not None
        assert tool.name == 'RunCheckovScan'
        assert 'Run Checkov security scan' in tool.description


class TestResources:
    """Tests for the MCP resources."""

    def test_resource_registrations(self):
        """Test that all resources are registered correctly."""
        # Test terraform_development_workflow resource
        resource_info = mcp._resource_manager._resources.get('terraform://development_workflow')
        assert resource_info is not None
        assert resource_info.name == 'terraform_development_workflow'
        assert str(resource_info.uri) == 'terraform://development_workflow'
        assert (
            resource_info.description is not None
            and 'Terraform Development Workflow Guide' in resource_info.description
        )
        assert resource_info.mime_type == 'text/markdown'

        # Test terraform_aws_provider_resources_listing resource
        resource_info = mcp._resource_manager._resources.get(
            'terraform://aws_provider_resources_listing'
        )
        assert resource_info is not None
        assert resource_info.name == 'terraform_aws_provider_resources_listing'
        assert str(resource_info.uri) == 'terraform://aws_provider_resources_listing'
        assert (
            resource_info.description is not None
            and 'Comprehensive listing of AWS provider resources' in resource_info.description
        )
        assert resource_info.mime_type == 'text/markdown'

        # Test terraform_awscc_provider_resources_listing resource
        resource_info = mcp._resource_manager._resources.get(
            'terraform://awscc_provider_resources_listing'
        )
        assert resource_info is not None
        assert resource_info.name == 'terraform_awscc_provider_resources_listing'
        assert str(resource_info.uri) == 'terraform://awscc_provider_resources_listing'
        assert (
            resource_info.description is not None
            and 'Comprehensive listing of AWSCC provider resources' in resource_info.description
        )
        assert resource_info.mime_type == 'text/markdown'

        # Test terraform_aws_best_practices resource
        resource_info = mcp._resource_manager._resources.get('terraform://aws_best_practices')
        assert resource_info is not None
        assert resource_info.name == 'terraform_aws_best_practices'
        assert str(resource_info.uri) == 'terraform://aws_best_practices'
        assert (
            resource_info.description is not None
            and 'AWS Terraform Provider Best Practices' in resource_info.description
        )
        assert resource_info.mime_type == 'text/markdown'

    def test_terraform_development_workflow_resource(self):
        """Test the terraform_development_workflow resource."""
        # Test terraform_development_workflow resource
        resource_info = mcp._resource_manager._resources.get('terraform://development_workflow')
        assert resource_info is not None
        assert resource_info.name == 'terraform_development_workflow'
        assert str(resource_info.uri) == 'terraform://development_workflow'
        assert (
            resource_info.description is not None
            and 'Terraform Development Workflow Guide' in resource_info.description
        )
        assert resource_info.mime_type == 'text/markdown'

    @pytest.mark.asyncio
    async def test_terraform_aws_provider_resources_listing_resource(self):
        """Test the terraform_aws_provider_resources_listing resource."""
        # Call the function
        result = await terraform_aws_provider_resources_listing()

        # Check that the result is a string and contains expected content
        assert isinstance(result, str)
        assert 'AWS Provider Resources' in result

    @pytest.mark.asyncio
    async def test_terraform_awscc_provider_resources_listing_resource(self):
        """Test the terraform_awscc_provider_resources_listing resource."""
        # Call the function
        result = await terraform_awscc_provider_resources_listing()

        # Check that the result is a string and contains expected content
        assert isinstance(result, str)
        assert 'AWSCC Provider Resources' in result

    def test_terraform_aws_best_practices_resource(self):
        """Test the terraform_aws_best_practices resource."""
        # Test terraform_aws_best_practices resource
        resource_info = mcp._resource_manager._resources.get('terraform://aws_best_practices')
        assert resource_info is not None
        assert resource_info.name == 'terraform_aws_best_practices'
        assert str(resource_info.uri) == 'terraform://aws_best_practices'
        assert (
            resource_info.description is not None
            and 'AWS Terraform Provider Best Practices' in resource_info.description
        )
        assert resource_info.mime_type == 'text/markdown'


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.terraform_mcp_server.server.argparse.ArgumentParser')
    @patch('awslabs.terraform_mcp_server.server.mcp')
    def test_main_default(self, mock_mcp, mock_argument_parser):
        """Test the main function with default arguments."""
        # Set up the mock
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.sse = False
        mock_parser.parse_args.return_value = mock_args
        mock_argument_parser.return_value = mock_parser

        # Call the function
        main()

        # Check that the parser was set up correctly
        mock_argument_parser.assert_called_once_with(
            description='A Model Context Protocol (MCP) server'
        )
        mock_parser.add_argument.assert_any_call(
            '--sse', action='store_true', help='Use SSE transport'
        )
        mock_parser.add_argument.assert_any_call(
            '--port', type=int, default=8888, help='Port to run the server on'
        )

        # Check that mcp.run was called with the correct arguments
        mock_mcp.run.assert_called_once_with()

    @patch('awslabs.terraform_mcp_server.server.argparse.ArgumentParser')
    @patch('awslabs.terraform_mcp_server.server.mcp')
    def test_main_with_sse(self, mock_mcp, mock_argument_parser):
        """Test the main function with SSE transport."""
        # Set up the mock
        mock_parser = MagicMock()
        mock_args = MagicMock()
        mock_args.sse = True
        mock_args.port = 9999
        mock_parser.parse_args.return_value = mock_args
        mock_argument_parser.return_value = mock_parser

        # Call the function
        main()

        # Check that the parser was set up correctly
        mock_argument_parser.assert_called_once_with(
            description='A Model Context Protocol (MCP) server'
        )
        mock_parser.add_argument.assert_any_call(
            '--sse', action='store_true', help='Use SSE transport'
        )
        mock_parser.add_argument.assert_any_call(
            '--port', type=int, default=8888, help='Port to run the server on'
        )

        # Check that mcp.settings.port was set correctly
        assert mock_mcp.settings.port == 9999

        # Check that mcp.run was called with the correct arguments
        mock_mcp.run.assert_called_once_with(transport='sse')
