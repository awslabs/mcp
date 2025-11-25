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
from awslabs.aws_iac_mcp_server.compliance_checker import (
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

    @patch('awslabs.aws_iac_mcp_server.compliance_checker._RULES_CONTENT_CACHE', None)
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_check_compliance_rules_not_found(self, mock_file):
        """Test compliance check when rules file not found."""
        template = json.dumps({'AWSTemplateFormatVersion': '2010-09-09', 'Resources': {}})

        result = check_compliance(template, rules_file_path='/nonexistent/rules.guard')

        assert 'compliance_results' in result
        assert result['compliance_results']['overall_status'] == 'ERROR'


class TestInitializeGuardRulesDetailed:
    """Test guard rules initialization."""

    @patch('builtins.open', new_callable=mock_open, read_data='rule test_rule { true }')
    @patch('os.path.join')
    @patch('os.path.dirname')
    def test_initialize_with_default_rules(self, mock_dirname, mock_join, mock_file):
        """Test initialization with default rules."""
        mock_dirname.return_value = '/fake/path'
        mock_join.return_value = '/fake/path/default_guard_rules.guard'

        result = initialize_guard_rules()

        assert result is True

    @patch('builtins.open', new_callable=mock_open, read_data='rule test_rule { true }')
    def test_initialize_with_custom_rules(self, mock_file):
        """Test initialization with custom rules file."""
        result = initialize_guard_rules('/custom/rules.guard')

        assert result is True

    @patch('builtins.open', side_effect=FileNotFoundError())
    def test_initialize_file_not_found(self, mock_file):
        """Test initialization when file not found."""
        result = initialize_guard_rules('/nonexistent/rules.guard')

        assert result is False

    @patch('builtins.open', side_effect=Exception('Read error'))
    def test_initialize_general_exception(self, mock_file):
        """Test initialization with general exception."""
        result = initialize_guard_rules('/bad/rules.guard')

        assert result is False


class TestExtractRemediationFromRulesDetailed:
    """Test remediation extraction from guard rules."""

    def test_extract_remediation_simple(self):
        """Test extracting simple remediation."""
        rules_content = """
rule S3_BUCKET_ENCRYPTION {
    # Fix: Enable default encryption
    Resources.*.Properties.BucketEncryption exists
}
"""
        result = _extract_remediation_from_rules(rules_content)

        assert 'S3_BUCKET_ENCRYPTION' in result
        assert 'Enable default encryption' in result['S3_BUCKET_ENCRYPTION']

    def test_extract_multiple_remediations(self):
        """Test extracting multiple remediations."""
        rules_content = """
rule RULE_ONE {
    # Fix: Fix one
    true
}

rule RULE_TWO {
    # Fix: Fix two
    true
}
"""
        result = _extract_remediation_from_rules(rules_content)

        assert len(result) == 2
        assert 'RULE_ONE' in result
        assert 'RULE_TWO' in result

    def test_extract_no_remediation(self):
        """Test when no remediation comments exist."""
        rules_content = """
rule NO_REMEDIATION {
    true
}
"""
        result = _extract_remediation_from_rules(rules_content)

        assert result == {}


class TestParseTemplateResourcesDetailed:
    """Test template resource parsing."""

    def test_parse_json_template(self):
        """Test parsing JSON CloudFormation template."""
        template = json.dumps(
            {
                'Resources': {
                    'MyBucket': {
                        'Type': 'AWS::S3::Bucket',
                        'Properties': {'BucketName': 'test-bucket'},
                    }
                }
            }
        )

        result = _parse_template_resources(template)

        # Function returns {name: type} not {name: {Type: type}}
        assert 'MyBucket' in result
        assert result['MyBucket'] == 'AWS::S3::Bucket'

    def test_parse_yaml_template(self):
        """Test parsing YAML CloudFormation template."""
        template = """
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: test-bucket
"""
        result = _parse_template_resources(template)

        # Function returns {name: type} not {name: {Type: type}}
        assert 'MyBucket' in result
        assert result['MyBucket'] == 'AWS::S3::Bucket'

    def test_parse_invalid_template(self):
        """Test parsing invalid template."""
        template = 'not valid json or yaml'

        result = _parse_template_resources(template)

        assert result == {}

    def test_parse_template_without_resources(self):
        """Test parsing template without Resources section."""
        template = json.dumps({'AWSTemplateFormatVersion': '2010-09-09'})

        result = _parse_template_resources(template)

        assert result == {}


class TestCheckComplianceDetailed:
    """Test main compliance checking function."""

    def test_check_compliance_empty_template(self):
        """Test compliance check with empty template."""
        result = check_compliance('')

        assert 'message' in result
        assert 'empty' in result['message'].lower()

    def test_check_compliance_whitespace_template(self):
        """Test compliance check with whitespace-only template."""
        result = check_compliance('   \n  \t  ')

        assert 'message' in result
        assert 'empty' in result['message'].lower()

    @patch('awslabs.aws_iac_mcp_server.compliance_checker._RULES_CONTENT_CACHE', None)
    @patch('awslabs.aws_iac_mcp_server.compliance_checker.initialize_guard_rules')
    def test_check_compliance_rules_init_failure(self, mock_init):
        """Test compliance check when rules initialization fails."""
        mock_init.return_value = False

        template = json.dumps({'Resources': {}})
        result = check_compliance(template)

        assert 'message' in result
        assert 'failed' in result['message'].lower()

    @patch('awslabs.aws_iac_mcp_server.compliance_checker.guardpycfn.validate_with_guard')
    @patch('awslabs.aws_iac_mcp_server.compliance_checker._RULES_CONTENT_CACHE', 'cached rules')
    @patch('awslabs.aws_iac_mcp_server.compliance_checker._REMEDIATION_CACHE', {})
    def test_check_compliance_guard_validation_failure(self, mock_validate):
        """Test compliance check when guard validation fails."""
        mock_validate.return_value = {'success': False}

        template = json.dumps({'Resources': {}})
        result = check_compliance(template)

        assert 'message' in result
        assert 'failed' in result['message'].lower()

    @patch('awslabs.aws_iac_mcp_server.compliance_checker.guardpycfn.validate_with_guard')
    @patch('awslabs.aws_iac_mcp_server.compliance_checker._RULES_CONTENT_CACHE', 'cached rules')
    def test_check_compliance_exception_handling(self, mock_validate):
        """Test compliance check exception handling."""
        mock_validate.side_effect = Exception('Validation error')

        template = json.dumps({'Resources': {}})
        result = check_compliance(template)

        assert 'message' in result
        assert 'Validation error' in result['message']

    @patch('awslabs.aws_iac_mcp_server.compliance_checker.guardpycfn.validate_with_guard')
    @patch('awslabs.aws_iac_mcp_server.compliance_checker._RULES_CONTENT_CACHE', 'cached rules')
    @patch(
        'awslabs.aws_iac_mcp_server.compliance_checker._REMEDIATION_CACHE', {'TEST_RULE': 'Fix it'}
    )
    def test_check_compliance_with_violations_full_path(self, mock_validate):
        """Test full compliance check path with violations."""
        # Simulate a guard result with violations
        mock_validate.return_value = {
            'success': True,
            'container': {'RuleCheck': {'name': 'TEST_RULE', 'status': 'FAIL'}},
            'children': [
                {
                    'container': {
                        'ClauseValueCheck': {'status': 'FAIL', 'message': 'Test violation'}
                    },
                    'path': '/Resources/MyBucket/Type',
                    'value': 'AWS::S3::Bucket',
                }
            ],
        }

        template = json.dumps({'Resources': {'MyBucket': {'Type': 'AWS::S3::Bucket'}}})
        result = check_compliance(template)

        assert 'compliance_results' in result
        assert 'violations' in result


class TestComplianceCheckerWithRealTemplate:
    """Test compliance checker with real CloudFormation templates."""

    def test_check_compliance_with_real_failing_template(self):
        """Test compliance check with a real template that has violations."""
        failing_template = """{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "S3Bucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": {
        "BucketName": "test-bucket-no-encryption"
      }
    },
    "S3BucketPolicy": {
      "Type": "AWS::S3::BucketPolicy",
      "Properties": {
        "Bucket": "test-bucket-no-encryption",
        "PolicyDocument": {
          "Version": "2012-10-17",
          "Statement": [
            {
              "Sid": "AllowPublicReadAccess",
              "Effect": "Allow",
              "Principal": "*",
              "Action": "s3:GetObject",
              "Resource": "arn:aws:s3:::test-bucket-no-encryption/*"
            }
          ]
        }
      }
    }
  }
}"""

        # Initialize rules first
        initialize_guard_rules()
        result = check_compliance(failing_template)

        # Should have compliance results
        assert 'compliance_results' in result
        assert 'violations' in result
        assert isinstance(result['violations'], list)

    def test_check_compliance_with_valid_template(self):
        """Test compliance check with a valid template."""
        valid_template = """{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "S3Bucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": {
        "BucketName": "test-bucket-encrypted",
        "BucketEncryption": {
          "ServerSideEncryptionConfiguration": [
            {
              "ServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
              }
            }
          ]
        },
        "PublicAccessBlockConfiguration": {
          "BlockPublicAcls": true,
          "BlockPublicPolicy": true,
          "IgnorePublicAcls": true,
          "RestrictPublicBuckets": true
        },
        "VersioningConfiguration": {
          "Status": "Enabled"
        },
        "LoggingConfiguration": {
          "DestinationBucketName": "logging-bucket",
          "LogFilePrefix": "logs/"
        }
      }
    }
  }
}"""

        initialize_guard_rules()
        result = check_compliance(valid_template)

        assert 'compliance_results' in result
        assert isinstance(result, dict)

    def test_check_compliance_processes_nested_violations(self):
        """Test that nested violations are properly processed."""
        template_with_issues = """{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "MyBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": {
        "BucketName": "my-test-bucket"
      }
    },
    "MySecurityGroup": {
      "Type": "AWS::EC2::SecurityGroup",
      "Properties": {
        "GroupDescription": "Test security group",
        "SecurityGroupIngress": [
          {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 22,
            "CidrIp": "0.0.0.0/0"
          }
        ]
      }
    }
  }
}"""

        initialize_guard_rules()
        result = check_compliance(template_with_issues)

        # Should process the template
        assert 'compliance_results' in result
        assert 'message' in result

    def test_extract_resource_info_with_paths(self):
        """Test _extract_resource_info with resource paths."""
        from awslabs.aws_iac_mcp_server.compliance_checker import _extract_resource_info

        node = {'path': '/Resources/MyBucket/Type', 'value': 'AWS::S3::Bucket'}
        template_resources = {'MyBucket': 'AWS::S3::Bucket'}

        resource_name, resource_type = _extract_resource_info(node, template_resources)

        assert resource_name == 'MyBucket'
        assert resource_type == 'AWS::S3::Bucket'

    def test_extract_resource_info_with_s3_fallback(self):
        """Test _extract_resource_info S3 fallback logic."""
        from awslabs.aws_iac_mcp_server.compliance_checker import _extract_resource_info

        node = {}
        template_resources = {'MyBucket': 'AWS::S3::Bucket', 'MyInstance': 'AWS::EC2::Instance'}

        resource_name, resource_type = _extract_resource_info(node, template_resources)

        # Should return S3 resource as fallback
        assert 'S3' in resource_type or resource_name == 'MyBucket'

    def test_extract_resource_info_no_dict(self):
        """Test _extract_resource_info with non-dict input."""
        from awslabs.aws_iac_mcp_server.compliance_checker import _extract_resource_info

        resource_name, resource_type = _extract_resource_info('not a dict', {})  # type: ignore[arg-type]

        assert resource_name == 'Unknown'
        assert resource_type == 'Unknown'

    def test_extract_resource_info_no_resources(self):
        """Test _extract_resource_info with no template resources."""
        from awslabs.aws_iac_mcp_server.compliance_checker import _extract_resource_info

        node = {'path': '/some/path'}

        resource_name, resource_type = _extract_resource_info(node, {})

        assert resource_name == 'Unknown'
        assert resource_type == 'Unknown'

    def test_check_compliance_with_custom_rules_file(self):
        """Test compliance check with custom rules file path."""
        template = '{"Resources": {}}'

        with patch('builtins.open', mock_open(read_data='rule custom { true }')):
            result = check_compliance(template, rules_file_path='/custom/rules.guard')

            assert 'compliance_results' in result

    def test_parse_template_resources_with_multiple_types(self):
        """Test parsing template with multiple resource types."""
        template = """{
  "Resources": {
    "Bucket1": {"Type": "AWS::S3::Bucket"},
    "Bucket2": {"Type": "AWS::S3::Bucket"},
    "Instance1": {"Type": "AWS::EC2::Instance"},
    "SecurityGroup1": {"Type": "AWS::EC2::SecurityGroup"}
  }
}"""

        result = _parse_template_resources(template)

        assert len(result) == 4
        assert result['Bucket1'] == 'AWS::S3::Bucket'
        assert result['Instance1'] == 'AWS::EC2::Instance'

    def test_initialize_guard_rules_exception_handling(self):
        """Test initialize_guard_rules handles import exceptions."""
        with patch(
            'awslabs.aws_iac_mcp_server.compliance_checker.os.path.dirname',
            side_effect=Exception('Import error'),
        ):
            result = initialize_guard_rules()

            assert result is False
