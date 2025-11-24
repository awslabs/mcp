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

"""Tests for cfn_tools module."""

import json
from unittest.mock import patch, MagicMock
from awslabs.aws_iac_mcp_server.tools.cfn_tools import (
    cloudformation_pre_deploy_validation,
    validate_cloudformation_template_tool,
    check_cloudformation_template_compliance_tool,
    troubleshoot_cloudformation_deployment_tool,
)


def test_cloudformation_pre_deploy_validation_returns_valid_json():
    """Test that cloudformation_pre_deploy_validation returns valid JSON."""
    result = cloudformation_pre_deploy_validation()
    parsed = json.loads(result)
    
    assert 'overview' in parsed
    assert 'validation_types' in parsed
    assert 'workflow' in parsed


def test_cloudformation_pre_deploy_validation_includes_required_fields():
    """Test that result includes all required instruction fields."""
    result = cloudformation_pre_deploy_validation()
    parsed = json.loads(result)
    
    assert 'validation_types' in parsed
    assert 'property_syntax' in parsed['validation_types']
    assert 'resource_name_conflict' in parsed['validation_types']
    assert 's3_bucket_emptiness' in parsed['validation_types']
    assert 'workflow' in parsed
    assert 'key_considerations' in parsed


@patch('awslabs.aws_iac_mcp_server.tools.cfn_tools.validate_template')
def test_validate_cloudformation_template_tool(mock_validate):
    """Test validate_cloudformation_template_tool calls validate_template."""
    mock_validate.return_value = {'valid': True}
    result = validate_cloudformation_template_tool('template', ['us-east-1'], ['W2001'])
    
    mock_validate.assert_called_once_with(
        template_content='template', regions=['us-east-1'], ignore_checks=['W2001']
    )
    assert result == {'valid': True}


@patch('awslabs.aws_iac_mcp_server.tools.cfn_tools.check_compliance')
def test_check_cloudformation_template_compliance_tool(mock_check):
    """Test check_cloudformation_template_compliance_tool calls check_compliance."""
    mock_check.return_value = {'compliant': True}
    result = check_cloudformation_template_compliance_tool('template', 'rules.guard')
    
    mock_check.assert_called_once_with(template_content='template', rules_file_path='rules.guard')
    assert result == {'compliant': True}


@patch('awslabs.aws_iac_mcp_server.tools.cfn_tools.DeploymentTroubleshooter')
def test_troubleshoot_cloudformation_deployment_tool(mock_troubleshooter_class):
    """Test troubleshoot_cloudformation_deployment_tool adds deeplink."""
    mock_instance = MagicMock()
    mock_instance.troubleshoot_stack_deployment.return_value = {'status': 'failed'}
    mock_troubleshooter_class.return_value = mock_instance
    
    result = troubleshoot_cloudformation_deployment_tool('my-stack', 'us-west-2', True)
    
    mock_troubleshooter_class.assert_called_once_with(region='us-west-2')
    mock_instance.troubleshoot_stack_deployment.assert_called_once_with(
        stack_name='my-stack', include_cloudtrail=True
    )
    assert '_instruction' in result
    assert 'us-west-2' in result['_instruction']
    assert 'my-stack' in result['_instruction']

