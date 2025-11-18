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

"""Tests for compliance_checker module."""

import json
from awslabs.iac_mcp_server.compliance_checker import (
    _extract_remediation_from_rules,
    _parse_template_resources,
    check_compliance,
    initialize_guard_rules,
)
from unittest.mock import mock_open, patch


class TestInitializeGuardRules:
    """Test guard rules initialization."""

    def test_initialize_default_rules_file(self):
        """Test that default rules file can be loaded without mocking."""
        result = initialize_guard_rules()

        assert result is True, 'Default rules file should load successfully'

    @patch('builtins.open', new_callable=mock_open, read_data='rule test_rule { }')
    def test_initialize_with_custom_rules(self, mock_file):
        """Test initialization with custom rules file."""
        result = initialize_guard_rules('/custom/path/rules.guard')

        assert result is True
        mock_file.assert_called_once_with('/custom/path/rules.guard', 'r')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_initialize_file_not_found(self, mock_file):
        """Test initialization with non-existent file."""
        result = initialize_guard_rules('/nonexistent/rules.guard')

        assert result is False


class TestExtractRemediationFromRules:
    """Test remediation extraction from guard rules."""

    def test_extract_remediation_simple(self):
        """Test extracting remediation from simple rule."""
        rules_content = """
rule s3_bucket_encryption {
    # Fix: Enable default encryption on S3 bucket
    Properties.BucketEncryption exists
}
"""
        result = _extract_remediation_from_rules(rules_content)

        assert 's3_bucket_encryption' in result
        assert 'Enable default encryption' in result['s3_bucket_encryption']

    def test_extract_remediation_no_remediation(self):
        """Test rule without remediation comment."""
        rules_content = """
rule simple_rule {
    Properties.Something exists
}
"""
        result = _extract_remediation_from_rules(rules_content)

        # Rule exists but has no Fix comment
        assert 'simple_rule' not in result

    def test_extract_remediation_empty_rules(self):
        """Test with empty rules content."""
        result = _extract_remediation_from_rules('')

        assert isinstance(result, dict)


class TestParseTemplateResources:
    """Test template resource parsing."""

    def test_parse_yaml_template(self):
        """Test parsing YAML CloudFormation template."""
        template = """
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
  MyTable:
    Type: AWS::DynamoDB::Table
"""
        result = _parse_template_resources(template)

        assert 'MyBucket' in result
        assert result['MyBucket'] == 'AWS::S3::Bucket'
        assert 'MyTable' in result
        assert result['MyTable'] == 'AWS::DynamoDB::Table'

    def test_parse_json_template(self):
        """Test parsing JSON CloudFormation template."""
        template = json.dumps(
            {
                'AWSTemplateFormatVersion': '2010-09-09',
                'Resources': {
                    'MyBucket': {'Type': 'AWS::S3::Bucket'},
                },
            }
        )

        result = _parse_template_resources(template)

        assert 'MyBucket' in result
        assert result['MyBucket'] == 'AWS::S3::Bucket'

    def test_parse_invalid_template(self):
        """Test parsing invalid template."""
        result = _parse_template_resources('invalid yaml {]')

        assert result == {}

    def test_parse_template_no_resources(self):
        """Test template without Resources section."""
        template = json.dumps({'AWSTemplateFormatVersion': '2010-09-09'})

        result = _parse_template_resources(template)

        assert result == {}


class TestCheckCompliance:
    """Test compliance checking."""

    def test_check_compliance_empty_template(self):
        """Test compliance check with empty template."""
        result = check_compliance('')

        assert 'compliance_results' in result
        assert result['compliance_results']['overall_status'] == 'ERROR'

    def test_check_compliance_invalid_json(self):
        """Test compliance check with invalid JSON."""
        result = check_compliance('{invalid json')

        assert 'compliance_results' in result
        assert result['compliance_results']['overall_status'] == 'ERROR'

    @patch('awslabs.iac_mcp_server.compliance_checker._RULES_CONTENT_CACHE', None)
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_check_compliance_rules_not_found(self, mock_file):
        """Test compliance check when rules file not found."""
        template = json.dumps({'AWSTemplateFormatVersion': '2010-09-09', 'Resources': {}})

        result = check_compliance(template, rules_file_path='/nonexistent/rules.guard')

        assert 'compliance_results' in result
        assert result['compliance_results']['overall_status'] == 'ERROR'
