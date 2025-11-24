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
from awslabs.aws_iac_mcp_server.server import (
    check_template_compliance,
    troubleshoot_deployment,
    validate_cloudformation_template,
)
from unittest.mock import patch
from urllib.parse import urlparse


class TestValidateCloudFormationTemplate:
    """Test validate_cloudformation_template tool."""

    @patch('awslabs.aws_iac_mcp_server.server.validate_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_success(self, mock_sanitize, mock_validate_tool):
        """Test successful template validation."""
        from awslabs.aws_iac_mcp_server.models.validation_models import (
            ValidationResponse,
            ValidationResults,
        )

        mock_response = ValidationResponse(
            validation_results=ValidationResults(
                is_valid=True, error_count=0, warning_count=0, info_count=0
            ),
            issues=[],
            message='Template is valid.',
        )
        mock_validate_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        result = validate_cloudformation_template(template)

        assert result == 'sanitized response'
        mock_validate_tool.assert_called_once()
        mock_sanitize.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.validate_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_with_regions(self, mock_sanitize, mock_validate_tool):
        """Test validation with specific regions."""
        from awslabs.aws_iac_mcp_server.models.validation_models import (
            ValidationResponse,
            ValidationResults,
        )

        mock_response = ValidationResponse(
            validation_results=ValidationResults(
                is_valid=True, error_count=0, warning_count=0, info_count=0
            ),
            issues=[],
            message='Template is valid.',
        )
        mock_validate_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        validate_cloudformation_template(template, regions=['us-west-2', 'us-east-1'])

        mock_validate_tool.assert_called_once_with(
            template_content=template, regions=['us-west-2', 'us-east-1'], ignore_checks=None
        )

    @patch('awslabs.aws_iac_mcp_server.server.validate_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_with_ignore_checks(self, mock_sanitize, mock_validate_tool):
        """Test validation with ignored checks."""
        from awslabs.aws_iac_mcp_server.models.validation_models import (
            ValidationResponse,
            ValidationResults,
        )

        mock_response = ValidationResponse(
            validation_results=ValidationResults(
                is_valid=True, error_count=0, warning_count=0, info_count=0
            ),
            issues=[],
            message='Template is valid.',
        )
        mock_validate_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        validate_cloudformation_template(template, ignore_checks=['W1234'])

        mock_validate_tool.assert_called_once_with(
            template_content=template, regions=None, ignore_checks=['W1234']
        )


class TestCheckTemplateCompliance:
    """Test check_template_compliance tool."""

    @patch('awslabs.aws_iac_mcp_server.server.compliance_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_check_compliance_success(self, mock_sanitize, mock_compliance_tool):
        """Test successful compliance check."""
        from awslabs.aws_iac_mcp_server.models.compliance_models import (
            ComplianceResponse,
            ComplianceResults,
        )

        mock_response = ComplianceResponse(
            compliance_results=ComplianceResults(
                overall_status='COMPLIANT',
                total_violations=0,
                error_count=0,
                warning_count=0,
                rule_sets_applied=['aws-security'],
            ),
            violations=[],
            message='Template is compliant with all rules.',
        )
        mock_compliance_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        result = check_template_compliance(template)

        assert result == 'sanitized response'
        mock_compliance_tool.assert_called_once()
        mock_sanitize.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.compliance_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_check_compliance_with_custom_rules(self, mock_sanitize, mock_compliance_tool):
        """Test compliance check with custom rules."""
        from awslabs.aws_iac_mcp_server.models.compliance_models import (
            ComplianceResponse,
            ComplianceResults,
        )

        mock_response = ComplianceResponse(
            compliance_results=ComplianceResults(
                overall_status='COMPLIANT',
                total_violations=0,
                error_count=0,
                warning_count=0,
                rule_sets_applied=['aws-security'],
            ),
            violations=[],
            message='Template is compliant with all rules.',
        )
        mock_compliance_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        check_template_compliance(template, rules_file_path='/custom/rules.guard')

        mock_compliance_tool.assert_called_once_with(
            template_content=template, rules_file_path='/custom/rules.guard'
        )


class TestTroubleshootDeployment:
    """Test troubleshoot_deployment tool."""

    @patch('awslabs.aws_iac_mcp_server.server.deployment_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_deployment_success(self, mock_sanitize, mock_deployment_tool):
        """Test successful deployment troubleshooting."""
        from awslabs.aws_iac_mcp_server.models.deployment_models import DeploymentResponse

        mock_response = DeploymentResponse(
            stack_name='test-stack',
            stack_status='CREATE_COMPLETE',
            failed_resources=[],
            events=[],
            root_cause_analysis='No failed resources found in stack events.',
            remediation_steps=['Review stack events for details'],
            console_deeplink='https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/stackinfo?stackId=test-stack',
        )
        mock_deployment_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = troubleshoot_deployment('test-stack', 'us-west-2')

        assert result == 'sanitized response'
        mock_deployment_tool.assert_called_once()
        mock_sanitize.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.deployment_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_deployment_without_cloudtrail(self, mock_sanitize, mock_deployment_tool):
        """Test troubleshooting without CloudTrail."""
        from awslabs.aws_iac_mcp_server.models.deployment_models import DeploymentResponse

        mock_response = DeploymentResponse(
            stack_name='test-stack',
            stack_status='CREATE_COMPLETE',
            failed_resources=[],
            events=[],
            root_cause_analysis='No failed resources found in stack events.',
            remediation_steps=['Review stack events for details'],
            console_deeplink='https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/stackinfo?stackId=test-stack',
        )
        mock_deployment_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        troubleshoot_deployment('test-stack', 'us-west-2', include_cloudtrail=False)

        mock_deployment_tool.assert_called_once_with(
            stack_name='test-stack', region='us-west-2', include_cloudtrail=False
        )

    @patch('awslabs.aws_iac_mcp_server.server.deployment_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_deployment_adds_deeplink(self, mock_sanitize, mock_deployment_tool):
        """Test that deployment troubleshooting adds console deeplink."""
        from awslabs.aws_iac_mcp_server.models.deployment_models import DeploymentResponse

        mock_response = DeploymentResponse(
            stack_name='test-stack',
            stack_status='CREATE_COMPLETE',
            failed_resources=[],
            events=[],
            root_cause_analysis='No failed resources found in stack events.',
            remediation_steps=['Review stack events for details'],
            console_deeplink='https://console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/stackinfo?stackId=test-stack',
        )
        mock_deployment_tool.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response with deeplink'

        result = troubleshoot_deployment('test-stack', 'us-west-2')

        assert result == 'sanitized response with deeplink'
        mock_deployment_tool.assert_called_once()
        # Verify that the _instruction field is added in server.py
        assert mock_sanitize.called


class TestGetTemplateExamples:
    """Test get_template_examples resource."""

    def test_get_template_examples_returns_json(self):
        """Test that get_template_examples returns valid JSON."""
        from awslabs.aws_iac_mcp_server.server import get_template_examples

        result = get_template_examples()

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert 'template_examples_repository' in parsed
        assert 'architectural_best_practices' in parsed
        assert 'resource_documentation' in parsed

    def test_get_template_examples_contains_urls(self):
        """Test that template examples contain expected URLs."""
        from awslabs.aws_iac_mcp_server.server import get_template_examples

        result = get_template_examples()
        parsed = json.loads(result)

        # Check for expected content - validate URLs by parsing them
        repo_url = parsed['template_examples_repository']['url']
        parsed_repo = urlparse(repo_url)
        assert parsed_repo.scheme == 'https'
        assert parsed_repo.netloc == 'github.com'

        best_practices_url = parsed['architectural_best_practices']['general_best_practices']
        parsed_bp = urlparse(best_practices_url)
        assert parsed_bp.scheme == 'https'
        assert parsed_bp.netloc == 'docs.aws.amazon.com'


class TestSearchCdkDocumentation:
    """Test search_cdk_documentation tool."""

    @patch('awslabs.aws_iac_mcp_server.server.search_cdk_documentation_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_search_cdk_documentation_success(self, mock_sanitize, mock_search):
        """Test successful CDK documentation search."""
        from awslabs.aws_iac_mcp_server.models.cdk_tool_models import CDKToolResponse
        from awslabs.aws_iac_mcp_server.server import search_cdk_documentation

        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='To read the full documentation pages for these search results, use the `read_cdk_documentation_page` tool. If you need to find real code examples for constructs referenced in the search results, use the `search_cdk_samples_and_constructs` tool.',
        )
        mock_search.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = await search_cdk_documentation('lambda function')

        assert result == 'sanitized response'
        mock_search.assert_called_once_with('lambda function')
        mock_sanitize.assert_called_once()


class TestReadCdkDocumentationPage:
    """Test read_cdk_documentation_page tool."""

    @patch('awslabs.aws_iac_mcp_server.server.read_cdk_documentation_page_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_read_cdk_documentation_page_success(self, mock_sanitize, mock_read):
        """Test successful CDK documentation page read."""
        from awslabs.aws_iac_mcp_server.models.cdk_tool_models import CDKToolResponse
        from awslabs.aws_iac_mcp_server.server import read_cdk_documentation_page

        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='If you need code examples, use `search_cdk_samples_and_constructs` tool.',
        )
        mock_read.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        result = await read_cdk_documentation_page('https://example.com/doc')

        assert result == 'sanitized response'
        mock_read.assert_called_once_with('https://example.com/doc', 0)
        mock_sanitize.assert_called_once()

    @patch('awslabs.aws_iac_mcp_server.server.read_cdk_documentation_page_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_read_cdk_documentation_page_with_starting_index(self, mock_sanitize, mock_read):
        """Test CDK documentation page read with starting index."""
        from awslabs.aws_iac_mcp_server.models.cdk_tool_models import CDKToolResponse
        from awslabs.aws_iac_mcp_server.server import read_cdk_documentation_page

        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='If you need code examples, use `search_cdk_samples_and_constructs` tool.',
        )
        mock_read.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        await read_cdk_documentation_page('https://example.com/doc', starting_index=100)

        mock_read.assert_called_once_with('https://example.com/doc', 100)


class TestSearchCloudFormationDocumentation:
    """Test search_cloudformation_documentation tool."""

    @patch('awslabs.aws_iac_mcp_server.server.search_cloudformation_documentation_tool')
    @patch('awslabs.aws_iac_mcp_server.server.sanitize_tool_response')
    @pytest.mark.asyncio
    async def test_search_cloudformation_documentation_success(self, mock_sanitize, mock_search):
        """Test successful CloudFormation documentation search."""
        from awslabs.aws_iac_mcp_server.models.cdk_tool_models import CDKToolResponse
        from awslabs.aws_iac_mcp_server.server import search_cloudformation_documentation

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
        from awslabs.aws_iac_mcp_server.models.cdk_tool_models import CDKToolResponse
        from awslabs.aws_iac_mcp_server.server import search_cdk_samples_and_constructs

        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='To read the full documentation pages for these search results, use the `read_cdk_documentation_page` tool.',
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
        from awslabs.aws_iac_mcp_server.models.cdk_tool_models import CDKToolResponse
        from awslabs.aws_iac_mcp_server.server import search_cdk_samples_and_constructs

        mock_response = CDKToolResponse(
            knowledge_response=[],
            next_step_guidance='To read the full documentation pages for these search results, use the `read_cdk_documentation_page` tool.',
        )
        mock_search.return_value = mock_response
        mock_sanitize.return_value = 'sanitized response'

        await search_cdk_samples_and_constructs('lambda function', language='python')

        mock_search.assert_called_once_with('lambda function', 'python')


class TestMain:
    """Test main function."""

    @patch('awslabs.aws_iac_mcp_server.server.mcp')
    def test_main_calls_mcp_run(self, mock_mcp):
        """Test that main() calls mcp.run()."""
        from awslabs.aws_iac_mcp_server.server import main

        main()

        mock_mcp.run.assert_called_once()
