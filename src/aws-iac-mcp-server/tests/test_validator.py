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

"""Edge case tests for validator module."""

import json
import pytest
from awslabs.aws_iac_mcp_server.compliance_checker import check_compliance
from awslabs.aws_iac_mcp_server.validator import _format_results, _map_level, validate_template
from cfnlint.match import Match
from cfnlint.rules import CloudFormationLintRule
from unittest.mock import Mock


class TestMapLevel:
    """Test severity determination from rule IDs."""

    def test_error_severity(self):
        """Test error severity for E-prefixed rules."""
        assert _map_level('E1234') == 'error'
        assert _map_level('E9999') == 'error'

    def test_warning_severity(self):
        """Test warning severity for W-prefixed rules."""
        assert _map_level('W1234') == 'warning'
        assert _map_level('W9999') == 'warning'

    def test_info_severity(self):
        """Test info severity for I-prefixed rules."""
        assert _map_level('I1234') == 'info'
        assert _map_level('I9999') == 'info'

    def test_unknown_severity_defaults_to_error(self):
        """Test unknown rule IDs default to error."""
        assert _map_level('X1234') == 'error'
        assert _map_level('1234') == 'error'
        assert _map_level('') == 'error'


class TestFormatResults:
    """Test match formatting with different severity levels."""

    def test_format_results_with_info_level(self):
        """Test formatting matches with info level."""
        mock_rule = Mock(spec=CloudFormationLintRule)
        mock_rule.id = 'I1234'
        mock_rule.shortdesc = 'Info message'
        mock_rule.description = 'Info description'

        match = Match(
            linenumber=10,
            columnnumber=5,
            linenumberend=10,
            columnnumberend=20,
            filename='template.yaml',
            rule=mock_rule,
            message='This is an info message',
        )

        result = _format_results([match])

        assert result['validation_results']['info_count'] == 1
        assert result['validation_results']['warning_count'] == 0
        assert result['validation_results']['error_count'] == 0
        assert len(result['issues']) == 1
        assert result['issues'][0]['level'] == 'info'

    def test_format_results_with_warning_level(self):
        """Test formatting matches with warning level."""
        mock_rule = Mock(spec=CloudFormationLintRule)
        mock_rule.id = 'W1234'
        mock_rule.shortdesc = 'Warning message'
        mock_rule.description = 'Warning description'

        match = Match(
            linenumber=5,
            columnnumber=10,
            linenumberend=5,
            columnnumberend=25,
            filename='template.yaml',
            rule=mock_rule,
            message='This is a warning',
        )

        result = _format_results([match])

        assert result['validation_results']['warning_count'] == 1
        assert result['validation_results']['error_count'] == 0
        assert result['validation_results']['info_count'] == 0
        assert result['message'] == 'Template has 1 warnings. Review and address as needed.'

    def test_format_results_no_issues(self):
        """Test formatting with no matches returns valid template message."""
        result = _format_results([])

        assert result['validation_results']['error_count'] == 0
        assert result['validation_results']['warning_count'] == 0
        assert result['validation_results']['info_count'] == 0
        assert result['message'] == 'Template is valid.'
        assert result['validation_results']['is_valid'] is True


class TestOversizedTemplates:
    """Test handling of oversized templates (>500KB)."""

    def test_oversized_template_validation(self):
        """Test that oversized templates are handled gracefully."""
        # Create a template larger than 500KB
        large_template = {'AWSTemplateFormatVersion': '2010-09-09', 'Resources': {}}
        # Add many resources to exceed 500KB
        for i in range(10000):
            large_template['Resources'][f'Bucket{i}'] = {
                'Type': 'AWS::S3::Bucket',
                'Properties': {'BucketName': f'test-bucket-{i}' + 'x' * 100},
            }

        template_str = json.dumps(large_template)
        assert len(template_str) > 500_000, 'Template should exceed 500KB'

        # Should handle without crashing
        result = validate_template(template_str)
        assert isinstance(result, dict)
        assert 'valid' in result or 'error' in result


class TestMalformedTemplates:
    """Test handling of malformed JSON/YAML."""

    def test_invalid_json(self):
        """Test invalid JSON syntax."""
        invalid_json = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {'
        result = validate_template(invalid_json)
        assert isinstance(result, dict)
        assert result['validation_results']['is_valid'] is False

    def test_invalid_yaml(self):
        """Test invalid YAML syntax."""
        invalid_yaml = """
AWSTemplateFormatVersion: 2010-09-09
Resources:
  Bucket:
    Type: AWS::S3::Bucket
      Properties:  # Invalid indentation
    BucketName: test
"""
        result = validate_template(invalid_yaml)
        assert isinstance(result, dict)
        assert result['validation_results']['is_valid'] is False

    def test_empty_template(self):
        """Test empty template string."""
        result = validate_template('')
        assert isinstance(result, dict)
        assert result.get('valid') is False or 'error' in result

    def test_non_string_template(self):
        """Test non-string template input."""
        # Validator handles None gracefully with error response
        result = validate_template(None)  # type: ignore[arg-type]
        assert isinstance(result, dict)
        assert (
            result.get('valid') is False
            or result.get('validation_results', {}).get('is_valid') is False
        )

        # Validator raises AttributeError for integers (no .strip() method)
        with pytest.raises(AttributeError):
            validate_template(123)  # type: ignore[arg-type]

    def test_binary_data(self):
        """Test binary data as template."""
        binary_data = b'\x00\x01\x02\x03'
        # Validator handles binary data gracefully
        result = validate_template(binary_data)  # type: ignore[arg-type]
        assert isinstance(result, dict)
        assert result['validation_results']['is_valid'] is False


class TestInvalidParameters:
    """Test handling of invalid parameters."""

    def test_invalid_region_format(self):
        """Test invalid AWS region format."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        result = validate_template(template, regions=['invalid-region-123'])
        assert isinstance(result, dict)

    def test_invalid_ignore_checks_type(self):
        """Test invalid ignore_checks parameter type."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        # Validator handles invalid types gracefully
        result = validate_template(template, ignore_checks='not-a-list')
        assert isinstance(result, dict)

    def test_invalid_rules_file_path(self):
        """Test non-existent rules file path."""
        # Reset the global cache to force re-initialization
        import awslabs.aws_iac_mcp_server.compliance_checker as cc

        cc._RULES_CONTENT_CACHE = None

        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        result = check_compliance(template, rules_file_path='/nonexistent/path/rules.guard')
        assert isinstance(result, dict)
        assert (
            'error' in result
            or result.get('compliance_results', {}).get('overall_status') == 'ERROR'
        )

    def test_special_characters_in_parameters(self):
        """Test special characters in parameters."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        # Should handle special characters gracefully
        result = validate_template(template, regions=['us-east-1', '../../etc/passwd'])
        assert isinstance(result, dict)

    def test_sql_injection_in_parameters(self):
        """Test SQL injection patterns in parameters."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        result = validate_template(template, regions=["us-east-1'; DROP TABLE stacks;--"])
        assert isinstance(result, dict)

    def test_command_injection_in_parameters(self):
        """Test command injection patterns in parameters."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        result = validate_template(template, regions=['us-east-1; rm -rf /'])
        assert isinstance(result, dict)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_unicode_in_template(self):
        """Test Unicode characters in template."""
        template = """
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Template with Unicode: 你好世界 🌍",
    "Resources": {}
}
"""
        result = validate_template(template)
        assert isinstance(result, dict)

    def test_deeply_nested_template(self):
        """Test deeply nested template structure."""
        nested = {'AWSTemplateFormatVersion': '2010-09-09', 'Resources': {}}
        current = nested
        for i in range(100):
            current[f'Level{i}'] = {}
            current = current[f'Level{i}']

        result = validate_template(json.dumps(nested))
        assert isinstance(result, dict)

    def test_template_with_null_values(self):
        """Test template with null values."""
        template = """
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Bucket": {
            "Type": "AWS::S3::Bucket",
            "Properties": null
        }
    }
}
"""
        result = validate_template(template)
        assert isinstance(result, dict)

    def test_duplicate_resource_names(self):
        """Test template with duplicate resource names."""
        template = """
{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "Bucket": {"Type": "AWS::S3::Bucket"},
        "Bucket": {"Type": "AWS::S3::Bucket"}
    }
}
"""
        result = validate_template(template)
        assert isinstance(result, dict)

    def test_extremely_long_resource_name(self):
        """Test resource with extremely long name."""
        long_name = 'A' * 10000
        template = f"""
{{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {{
        "{long_name}": {{"Type": "AWS::S3::Bucket"}}
    }}
}}
"""
        result = validate_template(template)
        assert isinstance(result, dict)


class TestParameterValidation:
    """Test MCP inputSchema validation."""

    def test_missing_required_template_content(self):
        """Test that missing required parameter raises error."""
        with pytest.raises(TypeError):
            validate_template()  # type: ignore[call-arg]

    def test_valid_minimal_parameters(self):
        """Test valid minimal parameters."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        result = validate_template(template)
        assert isinstance(result, dict)
        assert 'validation_results' in result
        assert result['validation_results']['is_valid'] is True

    def test_valid_all_parameters(self):
        """Test valid parameters with all optional fields."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        result = validate_template(
            template, regions=['us-east-1', 'us-west-2'], ignore_checks=['W2001', 'E3012']
        )
        assert isinstance(result, dict)

    def test_empty_optional_arrays(self):
        """Test empty arrays for optional parameters."""
        template = '{"AWSTemplateFormatVersion": "2010-09-09", "Resources": {}}'
        result = validate_template(template, regions=[], ignore_checks=[])
        assert isinstance(result, dict)
