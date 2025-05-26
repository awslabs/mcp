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

import os
import pytest
import tempfile
from awslabs.terraform_mcp_server.models import (
    CheckovScanResult,
    CheckovVulnerability,
    ModuleSearchResult,
    SearchUserProvidedModuleResult,
    TerraformAWSCCProviderDocsResult,
    TerraformAWSProviderDocsResult,
    TerraformExecutionResult,
    TerraformOutput,
    TerraformVariable,
    TerragruntExecutionResult,
)
from awslabs.terraform_mcp_server.server import (
    main,
    mcp,
    terraform_aws_provider_resources_listing,
    terraform_awscc_provider_resources_listing,
)
from unittest.mock import patch


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

    @pytest.mark.asyncio
    @patch('awslabs.terraform_mcp_server.server.execute_terraform_command_impl')
    async def test_execute_terraform_command(self, mock_execute_terraform_command_impl):
        """Test the execute_terraform_command function."""
        from awslabs.terraform_mcp_server.server import execute_terraform_command

        # Use a secure temporary directory path instead of hardcoded /tmp
        temp_dir = os.path.join(tempfile.gettempdir(), 'terraform_test_dir')

        # Setup mock
        mock_result = TerraformExecutionResult(
            command='init',
            status='success',
            return_code=0,
            stdout='Terraform initialized',
            stderr='',
            working_directory=temp_dir,
            error_message=None,
            outputs=None,
        )
        mock_execute_terraform_command_impl.return_value = mock_result

        # Call the function
        result = await execute_terraform_command(
            command='init',
            working_directory=temp_dir,
            variables={'foo': 'bar'},
            aws_region='us-west-2',
            strip_ansi=True,
        )

        # Verify the result
        assert result == mock_result

        # Verify the mock was called with the correct arguments
        mock_execute_terraform_command_impl.assert_called_once()
        args, _ = mock_execute_terraform_command_impl.call_args
        request = args[0]
        assert request.command == 'init'
        assert request.working_directory == temp_dir
        assert request.variables == {'foo': 'bar'}
        assert request.aws_region == 'us-west-2'
        assert request.strip_ansi is True

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

    @pytest.mark.asyncio
    @patch('awslabs.terraform_mcp_server.server.search_aws_provider_docs_impl')
    async def test_search_aws_provider_docs(self, mock_search_aws_provider_docs_impl):
        """Test the search_aws_provider_docs function."""
        from awslabs.terraform_mcp_server.server import search_aws_provider_docs

        # Setup mock
        mock_result = [
            TerraformAWSProviderDocsResult(
                asset_name='aws_s3_bucket',
                asset_type='resource',
                description='Provides an S3 bucket resource',
                url='https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket',
                example_usage=[],
                arguments=[],
                attributes=[],
            )
        ]
        mock_search_aws_provider_docs_impl.return_value = mock_result

        # Call the function
        result = await search_aws_provider_docs(
            asset_name='aws_s3_bucket',
            asset_type='resource',
        )

        # Verify the result
        assert result == mock_result

        # Verify the mock was called with the correct arguments
        mock_search_aws_provider_docs_impl.assert_called_once_with('aws_s3_bucket', 'resource')

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

    @pytest.mark.asyncio
    @patch('awslabs.terraform_mcp_server.server.search_awscc_provider_docs_impl')
    async def test_search_awscc_provider_docs(self, mock_search_awscc_provider_docs_impl):
        """Test the search_awscc_provider_docs function."""
        from awslabs.terraform_mcp_server.server import search_awscc_provider_docs

        # Setup mock
        mock_result = [
            TerraformAWSCCProviderDocsResult(
                asset_name='awscc_s3_bucket',
                asset_type='resource',
                description='Provides an S3 bucket resource using Cloud Control API',
                url='https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/s3_bucket',
                example_usage=[],
                schema_arguments=[],
            )
        ]
        mock_search_awscc_provider_docs_impl.return_value = mock_result

        # Call the function
        result = await search_awscc_provider_docs(
            asset_name='awscc_s3_bucket',
            asset_type='resource',
        )

        # Verify the result
        assert result == mock_result

        # Verify the mock was called with the correct arguments
        mock_search_awscc_provider_docs_impl.assert_called_once_with('awscc_s3_bucket', 'resource')

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

    @pytest.mark.asyncio
    @patch('awslabs.terraform_mcp_server.server.search_specific_aws_ia_modules_impl')
    async def test_search_specific_aws_ia_modules(self, mock_search_specific_aws_ia_modules_impl):
        """Test the search_specific_aws_ia_modules function."""
        from awslabs.terraform_mcp_server.server import search_specific_aws_ia_modules

        # Setup mock
        mock_result = [
            ModuleSearchResult(
                name='bedrock',
                namespace='aws-ia',
                provider='aws',
                version='1.0.0',
                url='https://registry.terraform.io/modules/aws-ia/bedrock/aws',
                description='Amazon Bedrock module for generative AI applications',
            )
        ]
        mock_search_specific_aws_ia_modules_impl.return_value = mock_result

        # Call the function
        result = await search_specific_aws_ia_modules(query='bedrock')

        # Verify the result
        assert result == mock_result

        # Verify the mock was called with the correct arguments
        mock_search_specific_aws_ia_modules_impl.assert_called_once_with('bedrock')

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

    @pytest.mark.asyncio
    @patch('awslabs.terraform_mcp_server.server.run_checkov_scan_impl')
    async def test_run_checkov_scan(self, mock_run_checkov_scan_impl):
        """Test the run_checkov_scan function."""
        from awslabs.terraform_mcp_server.server import run_checkov_scan

        # Use a secure temporary directory path instead of hardcoded /tmp
        temp_dir = os.path.join(tempfile.gettempdir(), 'terraform_test_dir')
        test_file = os.path.join(temp_dir, 'main.tf')

        # Setup mock
        mock_result = CheckovScanResult(
            status='success',
            return_code=0,
            working_directory=temp_dir,
            vulnerabilities=[
                CheckovVulnerability(
                    id='CKV_AWS_1',
                    type='terraform_aws',
                    resource='aws_s3_bucket.example',
                    file_path=test_file,
                    line=10,
                    description='Ensure S3 bucket has encryption enabled',
                    severity='HIGH',
                    guideline='Enable encryption for S3 buckets',
                    fixed=False,
                    fix_details=None,
                )
            ],
            summary={'passed': 5, 'failed': 1, 'skipped': 0},
            raw_output='',
        )
        mock_run_checkov_scan_impl.return_value = mock_result

        # Call the function
        result = await run_checkov_scan(
            working_directory=temp_dir,
            framework='terraform',
            check_ids=['CKV_AWS_1'],
            skip_check_ids=['CKV_AWS_2'],
            output_format='json',
        )

        # Verify the result
        assert result == mock_result

        # Verify the mock was called with the correct arguments
        mock_run_checkov_scan_impl.assert_called_once()
        args, _ = mock_run_checkov_scan_impl.call_args
        request = args[0]
        assert request.working_directory == temp_dir
        assert request.framework == 'terraform'
        assert request.check_ids == ['CKV_AWS_1']
        assert request.skip_check_ids == ['CKV_AWS_2']
        assert request.output_format == 'json'

    def test_search_user_provided_module_registration(self):
        """Test that the search_user_provided_module tool is registered correctly."""
        tool = mcp._tool_manager.get_tool('SearchUserProvidedModule')
        assert tool is not None
        assert tool.name == 'SearchUserProvidedModule'
        assert 'Search for a user-provided Terraform registry module' in tool.description

        # Verify the tool exists
        assert tool is not None
        assert tool.name == 'SearchUserProvidedModule'
        assert 'Search for a user-provided Terraform registry module' in tool.description

    @pytest.mark.asyncio
    @patch('awslabs.terraform_mcp_server.server.search_user_provided_module_impl')
    async def test_search_user_provided_module(self, mock_search_user_provided_module_impl):
        """Test the search_user_provided_module function."""
        from awslabs.terraform_mcp_server.server import search_user_provided_module

        # Setup mock
        mock_result = SearchUserProvidedModuleResult(
            status='success',
            module_name='vpc',
            module_url='terraform-aws-modules/vpc/aws',
            module_version='3.14.0',
            module_description='Terraform module which creates VPC resources on AWS',
            variables=[
                TerraformVariable(
                    name='name',
                    type='string',
                    description='Name to be used on all the resources as identifier',
                    required=True,
                )
            ],
            outputs=[
                TerraformOutput(
                    name='vpc_id',
                    description='The ID of the VPC',
                )
            ],
            readme_content='# VPC Module\n\nA Terraform module to create an AWS VPC.',
            error_message=None,
        )
        mock_search_user_provided_module_impl.return_value = mock_result

        # Call the function
        result = await search_user_provided_module(
            module_url='terraform-aws-modules/vpc/aws',
            version='3.14.0',
            variables={'name': 'my-vpc'},
        )

        # Verify the result
        assert result == mock_result

        # Verify the mock was called with the correct arguments
        mock_search_user_provided_module_impl.assert_called_once()
        args, _ = mock_search_user_provided_module_impl.call_args
        request = args[0]
        assert request.module_url == 'terraform-aws-modules/vpc/aws'
        assert request.version == '3.14.0'
        assert request.variables == {'name': 'my-vpc'}

    def test_execute_terragrunt_command_registration(self):
        """Test that the execute_terragrunt_command tool is registered correctly."""
        tool = mcp._tool_manager.get_tool('ExecuteTerragruntCommand')
        assert tool is not None
        assert tool.name == 'ExecuteTerragruntCommand'
        assert 'Execute Terragrunt workflow commands' in tool.description

        # Verify the tool exists
        assert tool is not None
        assert tool.name == 'ExecuteTerragruntCommand'
        assert 'Execute Terragrunt workflow commands' in tool.description

    @pytest.mark.asyncio
    @patch('awslabs.terraform_mcp_server.server.execute_terragrunt_command_impl')
    async def test_execute_terragrunt_command(self, mock_execute_terragrunt_command_impl):
        """Test the execute_terragrunt_command function."""
        from awslabs.terraform_mcp_server.server import execute_terragrunt_command

        # Use a secure temporary directory path instead of hardcoded /tmp
        temp_dir = os.path.join(tempfile.gettempdir(), 'terragrunt_test_dir')

        # Setup mock
        mock_result = TerragruntExecutionResult(
            command='init',
            status='success',
            return_code=0,
            stdout='Terragrunt initialized',
            stderr='',
            working_directory=temp_dir,
            error_message=None,
            outputs=None,
            affected_dirs=None,
        )
        mock_execute_terragrunt_command_impl.return_value = mock_result

        # Call the function
        result = await execute_terragrunt_command(
            command='init',
            working_directory=temp_dir,
            variables={'foo': 'bar'},
            aws_region='us-west-2',
            strip_ansi=True,
            include_dirs=['/path/to/module1'],
            exclude_dirs=['/path/to/excluded'],
            run_all=False,
            terragrunt_config='custom-terragrunt.hcl',
        )

        # Verify the result
        assert result == mock_result

        # Verify the mock was called with the correct arguments
        mock_execute_terragrunt_command_impl.assert_called_once()
        args, _ = mock_execute_terragrunt_command_impl.call_args
        request = args[0]
        assert request.command == 'init'
        assert request.working_directory == temp_dir
        assert request.variables == {'foo': 'bar'}
        assert request.aws_region == 'us-west-2'
        assert request.strip_ansi is True
        assert request.include_dirs == ['/path/to/module1']
        assert request.exclude_dirs == ['/path/to/excluded']
        assert request.run_all is False
        assert request.terragrunt_config == 'custom-terragrunt.hcl'


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
    @patch('awslabs.terraform_mcp_server.server.TERRAFORM_WORKFLOW_GUIDE', 'Test workflow guide')
    async def test_terraform_development_workflow_content(self):
        """Test the terraform_development_workflow resource content."""
        from awslabs.terraform_mcp_server.server import terraform_development_workflow

        # Call the function
        result = await terraform_development_workflow()

        # Verify the result
        assert result == 'Test workflow guide'

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

    @pytest.mark.asyncio
    @patch(
        'awslabs.terraform_mcp_server.server.AWS_TERRAFORM_BEST_PRACTICES', 'Test best practices'
    )
    async def test_terraform_aws_best_practices_content(self):
        """Test the terraform_aws_best_practices resource content."""
        from awslabs.terraform_mcp_server.server import terraform_aws_best_practices

        # Call the function
        result = await terraform_aws_best_practices()

        # Verify the result
        assert result == 'Test best practices'


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.terraform_mcp_server.server.mcp')
    def test_main_default(self, mock_mcp):
        """Test the main function with default arguments."""
        # Set up the mock

        # Call the function
        main()

        # Check that mcp.run was called with the correct arguments
        mock_mcp.run.assert_called_once_with()
