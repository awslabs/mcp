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

"""Tests for server.py MCP tool definitions."""

import json
import pytest
from awslabs.aws_iac_mcp_server.knowledge_models import CDKToolResponse
from awslabs.aws_iac_mcp_server.server import (
    cdk_best_practices,
    check_cloudformation_template_compliance,
    get_cloudformation_pre_deploy_validation_instructions,
    read_iac_documentation_page,
    search_cdk_documentation,
    search_cdk_samples_and_constructs,
    search_cloudformation_documentation,
    troubleshoot_cloudformation_deployment,
    validate_cloudformation_template,
)
from unittest.mock import patch


class TestValidateCloudFormationTemplate:
    """Test validate_cloudformation_template tool."""

    @patch('awslabs.aws_iac_mcp_server.server.validate_template')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_success(self, mock_sanitize, mock_validate):
        """Test successful template validation."""
        mock_validate.return_value = {'validation_results': {'is_valid': True}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        result = validate_cloudformation_template(template)

        assert result == 'sanitized response'
        mock_validate.assert_called_once()
        mock_sanitize.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.validate_template')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_with_regions(self, mock_sanitize, mock_validate):
        """Test validation with specific regions."""
        mock_validate.return_value = {'validation_results': {'is_valid': True}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        validate_cloudformation_template(template, regions=['us-west-2', 'us-east-1'])

        mock_validate.assert_called_once_with(
            template_content=template, regions=['us-west-2', 'us-east-1'], ignore_checks=None
        )

    @patch('awslabs.aws_iac_mcp_server.server.validate_template')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_with_ignore_checks(self, mock_sanitize, mock_validate):
        """Test validation with ignored checks."""
        mock_validate.return_value = {'validation_results': {'is_valid': True}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        validate_cloudformation_template(template, ignore_checks=['W1234'])

        mock_validate.assert_called_once_with(
            template_content=template, regions=None, ignore_checks=['W1234']
        )


class TestCheckTemplateCompliance:
    """Test check_cloudformation_template_compliance tool."""

    @patch('awslabs.aws_iac_mcp_server.server.check_compliance')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_check_compliance_success(self, mock_sanitize, mock_check):
        """Test successful compliance check."""
        mock_check.return_value = {'compliance_results': {'overall_status': 'PASS'}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        result = check_cloudformation_template_compliance(template)

        assert result == 'sanitized response'
        mock_check.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.check_compliance')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_check_compliance_with_custom_rules(self, mock_sanitize, mock_check):
        """Test compliance check with custom rules."""
        mock_check.return_value = {'compliance_results': {'overall_status': 'PASS'}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        check_cloudformation_template_compliance(template, rules_file_path='/custom/rules.guard')

        mock_check.assert_called_once_with(
            template_content=template, rules_file_path='/custom/rules.guard'
        )


class TestTroubleshootDeployment:
    """Test troubleshoot_cloudformation_deployment tool."""

    @patch('awslabs.aws_iac_mcp_server.server.DeploymentTroubleshooter')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_cloudformation_deployment_success(
        self, mock_sanitize, mock_troubleshooter_class
    ):
        """Test successful deployment troubleshooting."""
        mock_instance = mock_troubleshooter_class.return_value
        mock_instance.troubleshoot_stack_deployment.return_value = {
            'status': 'success',
            'raw_data': {'cloudformation_events': []},
        }
        mock_sanitize.return_value = 'sanitized response'

        result = troubleshoot_cloudformation_deployment('test-stack', 'us-west-2')

        assert result == 'sanitized response'
        mock_troubleshooter_class.assert_called_once_with(region='us-west-2')
        mock_instance.troubleshoot_stack_deployment.assert_called_once_with(
            stack_name='test-stack', include_cloudtrail=True
        )

    @patch('awslabs.aws_iac_mcp_server.server.DeploymentTroubleshooter')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_cloudformation_deployment_without_cloudtrail(
        self, mock_sanitize, mock_troubleshooter_class
    ):
        """Test troubleshooting without CloudTrail."""
        mock_instance = mock_troubleshooter_class.return_value
        mock_instance.troubleshoot_stack_deployment.return_value = {
            'status': 'success',
            'raw_data': {'cloudformation_events': []},
        }
        mock_sanitize.return_value = 'sanitized response'

        troubleshoot_cloudformation_deployment('test-stack', 'us-west-2', include_cloudtrail=False)

        mock_troubleshooter_class.assert_called_once_with(region='us-west-2')
        mock_instance.troubleshoot_stack_deployment.assert_called_once_with(
            stack_name='test-stack', include_cloudtrail=False
        )

    @patch('awslabs.aws_iac_mcp_server.server.DeploymentTroubleshooter')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_cloudformation_deployment_adds_deeplink(
        self, mock_sanitize, mock_troubleshooter_class
    ):
        """Test that deployment troubleshooting adds console deeplink."""
        mock_instance = mock_troubleshooter_class.return_value
        mock_instance.troubleshoot_stack_deployment.return_value = {
            'status': 'success',
            'stack_name': 'test-stack',
            'raw_data': {'cloudformation_events': []},
        }
        mock_sanitize.return_value = 'sanitized response'

        troubleshoot_cloudformation_deployment('test-stack', 'us-west-2')

        # Verify the result was modified to include deeplink
        call_args = mock_sanitize.call_args[0][0]
        assert 'console.aws.amazon.com/cloudformation' in call_args
        assert 'test-stack' in call_args
        assert 'us-west-2' in call_args
        assert '_instruction' in call_args

    @patch('awslabs.aws_iac_mcp_server.server.DeploymentTroubleshooter')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_cloudformation_deployment_non_dict_result(
        self, mock_sanitize, mock_troubleshooter_class
    ):
        """Test troubleshooting when result is not a dict."""
        mock_instance = mock_troubleshooter_class.return_value
        mock_instance.troubleshoot_stack_deployment.return_value = 'error string'
        mock_sanitize.return_value = 'sanitized response'

        result = troubleshoot_cloudformation_deployment('test-stack', 'us-west-2')

        assert result == 'sanitized response'
        # Verify no deeplink was added (result wasn't a dict)
        call_args = mock_sanitize.call_args[0][0]
        assert '_instruction' not in call_args

    """Test search_cdk_documentation tool."""

    @patch('awslabs.aws_iac_mcp_server.server.search_cdk_documentation_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_search_cdk_documentation_success(self, mock_sanitize, mock_search):
        """Test successful CDK documentation search."""
        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='To read the full documentation pages for these search results, use the `read_iac_documentation_page` tool. If you need to find real code examples for constructs referenced in the search results, use the `search_cdk_samples_and_constructs` tool.',
        )
        mock_search.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = await search_cdk_documentation('lambda function')

        assert result == 'sanitized response'
        mock_search.assert_called_once_with('lambda function')
        mock_sanitize.assert_called_once()


class TestReadIaCDocumentationPage:
    """Test read_iac_documentation_page tool."""

    @patch('awslabs.aws_iac_mcp_server.server.read_iac_documentation_page_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_read_iac_documentation_page_success(self, mock_sanitize, mock_read):
        """Test successful CDK documentation page read."""
        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='If you need code examples, use `search_cdk_samples_and_constructs` tool.',
        )
        mock_read.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = await read_iac_documentation_page('https://example.com/doc')

        assert result == 'sanitized response'
        mock_read.assert_called_once_with('https://example.com/doc', 0)
        mock_sanitize.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.read_iac_documentation_page_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_read_iac_documentation_page_with_starting_index(self, mock_sanitize, mock_read):
        """Test CDK documentation page read with starting index."""
        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='If you need code examples, use `search_cdk_samples_and_constructs` tool.',
        )
        mock_read.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        await read_iac_documentation_page('https://example.com/doc', starting_index=100)

        mock_read.assert_called_once_with('https://example.com/doc', 100)


class TestSearchCloudFormationDocumentation:
    """Test search_cloudformation_documentation tool."""

    @patch('awslabs.aws_iac_mcp_server.server.search_cloudformation_documentation_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_search_cloudformation_documentation_success(self, mock_sanitize, mock_search):
        """Test successful CloudFormation documentation search."""
        mock_response = CDKToolResponse(knowledge_response=[], next_step_guidance=None)
        mock_search.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = await search_cloudformation_documentation('AWS::S3::Bucket')

        assert result == 'sanitized response'
        mock_search.assert_called_once_with('AWS::S3::Bucket')
        mock_sanitize.assert_called_once()


class TestSearchCdkSamplesAndConstructs:
    """Test search_cdk_samples_and_constructs tool."""

    @patch('awslabs.aws_iac_mcp_server.server.search_cdk_samples_and_constructs_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_search_cdk_samples_and_constructs_success(self, mock_sanitize, mock_search):
        """Test successful CDK samples and constructs search."""
        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='To read the full documentation pages for these search results, use the `read_iac_documentation_page` tool.',
        )
        mock_search.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = await search_cdk_samples_and_constructs('serverless api')

        assert result == 'sanitized response'
        mock_search.assert_called_once_with('serverless api', 'typescript')
        mock_sanitize.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.search_cdk_samples_and_constructs_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_search_cdk_samples_and_constructs_with_language(
        self, mock_sanitize, mock_search
    ):
        """Test CDK samples search with specific language."""
        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='To read the full documentation pages for these search results, use the `read_iac_documentation_page` tool.',
        )
        mock_search.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        await search_cdk_samples_and_constructs('lambda function', language='python')

        mock_search.assert_called_once_with('lambda function', 'python')


class TestPreDeployValidation:
    """Test get_cloudformation_pre_deploy_validation_instructions tool."""

    @patch('awslabs.aws_iac_mcp_server.server.cloudformation_pre_deploy_validation')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_get_pre_deploy_validation_instructions(self, mock_sanitize, mock_validation):
        """Test pre-deploy validation instructions."""
        mock_validation.return_value = '{"instructions": "test"}'
        mock_sanitize.return_value = 'sanitized response'

        result = get_cloudformation_pre_deploy_validation_instructions()

        assert result == 'sanitized response'
        mock_validation.assert_called_once()
        mock_sanitize.assert_called_once_with('{"instructions": "test"}')


class TestCdkBestPractices:
    """Test cdk_best_practices tool."""

    @patch('awslabs.aws_iac_mcp_server.server.cdk_best_practices_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_cdk_best_practices_success(self, mock_sanitize, mock_best_practices):
        """Test successful CDK best practices retrieval."""
        from awslabs.aws_iac_mcp_server.knowledge_models import CDKToolResponse

        mock_response = CDKToolResponse(knowledge_response=[], next_step_guidance=None)
        mock_best_practices.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = await cdk_best_practices()

        assert result == 'sanitized response'
        mock_best_practices.assert_called_once_with()
        mock_sanitize.assert_called_once()


class TestMain:
    """Test main function."""

    @patch('awslabs.aws_iac_mcp_server.server.mcp')
    def test_main_calls_mcp_run(self, mock_mcp):
        """Test that main() calls mcp.run()."""
        from awslabs.aws_iac_mcp_server.server import main

        main()

        mock_mcp.run.assert_called_once()
