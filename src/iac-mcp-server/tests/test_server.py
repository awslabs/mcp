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
from awslabs.iac_mcp_server.server import (
    check_template_compliance,
    troubleshoot_deployment,
    validate_cloudformation_template,
)
from unittest.mock import Mock, patch


class TestValidateCloudFormationTemplate:
    """Test validate_cloudformation_template tool."""

    @patch('awslabs.iac_mcp_server.server.validate_template')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_success(self, mock_sanitize, mock_validate):
        """Test successful template validation."""
        mock_validate.return_value = {'validation_results': {'is_valid': True}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        result = validate_cloudformation_template(template)

        assert result == 'sanitized response'
        mock_validate.assert_called_once()
        mock_sanitize.assert_called_once()

    @patch('awslabs.iac_mcp_server.server.validate_template')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
    def test_validate_template_with_regions(self, mock_sanitize, mock_validate):
        """Test validation with specific regions."""
        mock_validate.return_value = {'validation_results': {'is_valid': True}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        validate_cloudformation_template(template, regions=['us-west-2', 'us-east-1'])

        mock_validate.assert_called_once_with(
            template_content=template, regions=['us-west-2', 'us-east-1'], ignore_checks=None
        )

    @patch('awslabs.iac_mcp_server.server.validate_template')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
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
    """Test check_template_compliance tool."""

    @patch('awslabs.iac_mcp_server.server.check_compliance')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
    def test_check_compliance_success(self, mock_sanitize, mock_check):
        """Test successful compliance check."""
        mock_check.return_value = {'compliance_results': {'overall_status': 'PASS'}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        result = check_template_compliance(template)

        assert result == 'sanitized response'
        mock_check.assert_called_once()

    @patch('awslabs.iac_mcp_server.server.check_compliance')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
    def test_check_compliance_with_custom_rules(self, mock_sanitize, mock_check):
        """Test compliance check with custom rules."""
        mock_check.return_value = {'compliance_results': {'overall_status': 'PASS'}}
        mock_sanitize.return_value = 'sanitized response'

        template = json.dumps({'Resources': {}})
        check_template_compliance(template, rules_file_path='/custom/rules.guard')

        mock_check.assert_called_once_with(
            template_content=template, rules_file_path='/custom/rules.guard'
        )


class TestTroubleshootDeployment:
    """Test troubleshoot_deployment tool."""

    @patch('awslabs.iac_mcp_server.server.DeploymentTroubleshooter')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_deployment_success(self, mock_sanitize, mock_troubleshooter_class):
        """Test successful deployment troubleshooting."""
        mock_troubleshooter = Mock()
        mock_troubleshooter_class.return_value = mock_troubleshooter
        mock_troubleshooter.troubleshoot_stack_deployment.return_value = {
            'status': 'success',
            'raw_data': {'cloudformation_events': []},
        }
        mock_sanitize.return_value = 'sanitized response'

        result = troubleshoot_deployment('test-stack', 'us-west-2')

        assert result == 'sanitized response'
        mock_troubleshooter_class.assert_called_once_with(region='us-west-2')
        mock_troubleshooter.troubleshoot_stack_deployment.assert_called_once()

    @patch('awslabs.iac_mcp_server.server.DeploymentTroubleshooter')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_deployment_without_cloudtrail(
        self, mock_sanitize, mock_troubleshooter_class
    ):
        """Test troubleshooting without CloudTrail."""
        mock_troubleshooter = Mock()
        mock_troubleshooter_class.return_value = mock_troubleshooter
        mock_troubleshooter.troubleshoot_stack_deployment.return_value = {
            'status': 'success',
            'raw_data': {'cloudformation_events': []},
        }
        mock_sanitize.return_value = 'sanitized response'

        troubleshoot_deployment('test-stack', 'us-west-2', include_cloudtrail=False)

        mock_troubleshooter.troubleshoot_stack_deployment.assert_called_once_with(
            stack_name='test-stack', include_cloudtrail=False
        )

    @patch('awslabs.iac_mcp_server.server.DeploymentTroubleshooter')
    @patch('awslabs.iac_mcp_server.server.sanitize_tool_response')
    def test_troubleshoot_deployment_adds_deeplink(self, mock_sanitize, mock_troubleshooter_class):
        """Test that deployment troubleshooting adds console deeplink."""
        mock_troubleshooter = Mock()
        mock_troubleshooter_class.return_value = mock_troubleshooter
        mock_troubleshooter.troubleshoot_stack_deployment.return_value = {
            'status': 'success',
            'stack_name': 'test-stack',
            'raw_data': {'cloudformation_events': []},
        }
        mock_sanitize.return_value = 'sanitized response'

        troubleshoot_deployment('test-stack', 'us-west-2')

        # Verify the result was modified to include deeplink
        call_args = mock_sanitize.call_args[0][0]
        assert 'console.aws.amazon.com/cloudformation' in call_args
        assert 'test-stack' in call_args
        assert 'us-west-2' in call_args


class TestGetTemplateExamples:
    """Test get_template_examples resource."""

    def test_get_template_examples_returns_json(self):
        """Test that get_template_examples returns valid JSON."""
        from awslabs.iac_mcp_server.server import get_template_examples

        result = get_template_examples()

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert 'template_examples_repository' in parsed
        assert 'architectural_best_practices' in parsed
        assert 'resource_documentation' in parsed

    def test_get_template_examples_contains_urls(self):
        """Test that template examples contain expected URLs."""
        from awslabs.iac_mcp_server.server import get_template_examples

        result = get_template_examples()
        parsed = json.loads(result)

        # Check for expected content
        assert 'github.com' in parsed['template_examples_repository']['url']
        assert (
            'docs.aws.amazon.com'
            in parsed['architectural_best_practices']['general_best_practices']
        )


class TestMain:
    """Test main function."""

    @patch('awslabs.iac_mcp_server.server.mcp')
    def test_main_calls_mcp_run(self, mock_mcp):
        """Test that main() calls mcp.run()."""
        from awslabs.iac_mcp_server.server import main

        main()

        mock_mcp.run.assert_called_once()
