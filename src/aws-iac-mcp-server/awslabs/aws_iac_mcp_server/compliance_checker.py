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

from __future__ import annotations

import guardpycfn
import json
import os
import re
import yaml
from typing import Any, Optional


# Global cache for remediation mappings
_REMEDIATION_CACHE = {}
_RULES_CONTENT_CACHE = None
_TEMPLATE_RESOURCES = {}


def initialize_guard_rules(rules_file_path: Optional[str] = None) -> bool:
    """Initialize guard rules and cache remediation mappings on server startup.

    Args:
        rules_file_path: Path to guard rules file

    Returns:
        True if initialization successful, False otherwise
    """
    global _REMEDIATION_CACHE, _RULES_CONTENT_CACHE

    # Use absolute path to default guard rules if none provided
    if rules_file_path is None or rules_file_path == 'default_guard_rules.guard':
        try:
            import awslabs.aws_iac_mcp_server

            package_dir = os.path.dirname(awslabs.aws_iac_mcp_server.__file__)
            rules_file_path = os.path.join(package_dir, 'default_guard_rules.guard')
        except Exception:
            return False

    try:
        with open(rules_file_path, 'r') as f:
            rules_content = f.read()

        # Cache the rules content
        _RULES_CONTENT_CACHE = rules_content

        # Extract and cache remediation mappings
        _REMEDIATION_CACHE = _extract_remediation_from_rules(rules_content)

        return True

    except FileNotFoundError:
        return False
    except Exception:
        return False


def _extract_remediation_from_rules(rules_content: str) -> dict[str, str]:
    """Extract remediation advice from guard rules file."""
    remediation_map = {}

    # Split rules into sections by rule names
    rule_sections = re.split(r'rule\s+(\w+)', rules_content)

    for i in range(1, len(rule_sections), 2):
        if i + 1 < len(rule_sections):
            rule_name = rule_sections[i]
            rule_content = rule_sections[i + 1]

            # Look for Fix: comments in the rule content
            fix_match = re.search(r'Fix:\s*(.+?)(?:\n|$)', rule_content, re.IGNORECASE)
            if fix_match:
                remediation_map[rule_name] = fix_match.group(1).strip()

    return remediation_map


def _parse_template_resources(template_content: str) -> dict:
    """Parse template to extract resource names and types."""
    try:
        # Try YAML first, then JSON
        try:
            template = yaml.safe_load(template_content)
        except Exception:
            template = json.loads(template_content)

        resources = template.get('Resources', {})
        return {name: res.get('Type', 'Unknown') for name, res in resources.items()}
    except Exception:
        return {}


def _extract_resource_info(node: dict, template_resources: dict) -> tuple[str, str]:
    """Extract resource name and type, using template as fallback."""
    if not isinstance(node, dict):
        return 'Unknown', 'Unknown'

    # Try to find resource info in guard result paths
    def find_paths(obj, paths=None):
        if paths is None:
            paths = []
        if isinstance(obj, dict):
            if 'path' in obj:
                paths.append((obj['path'], obj.get('value', '')))
            for value in obj.values():
                find_paths(value, paths)
        elif isinstance(obj, list):
            for item in obj:
                find_paths(item, paths)
        return paths

    all_paths = find_paths(node)

    # Look for resource paths
    for path, value in all_paths:
        if '/Resources/' in path:
            resource_name = path.split('/Resources/')[1].split('/')[0]
            resource_type = (
                value
                if path.endswith('/Type')
                else template_resources.get(resource_name, 'Unknown')
            )
            return resource_name, resource_type

    # Fallback: if we have S3 rules and S3 resources, match them
    if template_resources:
        s3_resources = {name: rtype for name, rtype in template_resources.items() if 'S3' in rtype}
        if s3_resources:
            # Return first S3 resource for S3-related rules
            resource_name, resource_type = next(iter(s3_resources.items()))
            return resource_name, resource_type

    return 'Unknown', 'Unknown'


def check_compliance(
    template_content: str,
    rules_file_path: Optional[str] = None,
) -> dict[str, Any]:
    """Validate CloudFormation template against cfn-guard rules using guardpycfn."""
    global _REMEDIATION_CACHE, _RULES_CONTENT_CACHE

    def error_result(message: str) -> dict[str, Any]:
        return {
            'compliance_results': {
                'overall_status': 'ERROR',
                'total_violations': 0,
                'error_count': 0,
                'warning_count': 0,
                'rule_sets_applied': [],
            },
            'violations': [],
            'message': message,
        }

    if not template_content or not template_content.strip():
        return error_result('Template content cannot be empty')

    if _RULES_CONTENT_CACHE is None and not initialize_guard_rules(rules_file_path):
        return error_result('Failed to initialize guard rules')

    # Parse template resources for fallback resource identification
    template_resources = _parse_template_resources(template_content)

    try:
        guard_result = guardpycfn.validate_with_guard(  # type: ignore[attr-defined]
            template_content, _RULES_CONTENT_CACHE, verbose=True
        )

        if not guard_result.get('success', False):
            return error_result('Guard validation failed to execute properly')

        violations = []

        def process_node(node, rule_name='Unknown'):
            if not isinstance(node, dict):
                return

            container = node.get('container', {})

            if 'RuleCheck' in container:
                rule_check = container['RuleCheck']
                rule_name = rule_check.get('name', 'Unknown')
                if rule_check.get('status') == 'FAIL':
                    found_specific = False
                    for child in node.get('children', []):
                        if add_violations_from_child(child, rule_name):
                            found_specific = True

                    if not found_specific:
                        resource_name, resource_type = get_resource_for_rule(
                            rule_name, template_resources
                        )
                        violations.append(
                            create_violation(
                                rule_name,
                                resource_name,
                                resource_type,
                                f'Rule {rule_name} failed validation',
                            )
                        )

            for child in node.get('children', []):
                process_node(child, rule_name)

        def add_violations_from_child(node, rule_name):
            clause_check = node.get('container', {}).get('ClauseValueCheck', {})
            if not isinstance(clause_check, dict):
                return False

            resource_name, resource_type = _extract_resource_info(node, template_resources)
            if resource_name == 'Unknown':
                resource_name, resource_type = get_resource_for_rule(rule_name, template_resources)

            for check_type in ['Unary', 'Comparison']:
                check_data = clause_check.get(check_type, {})
                if check_data.get('status') == 'FAIL':
                    message = check_data.get(
                        'message',
                        'Rule violation detected'
                        if check_type == 'Unary'
                        else 'Rule comparison failed',
                    )
                    violations.append(
                        create_violation(rule_name, resource_name, resource_type, message)
                    )
                    return True
            return False

        def get_resource_for_rule(rule_name, template_resources):
            """Get appropriate resource for a rule based on rule name patterns."""
            return 'Unknown', 'Unknown'

        def create_violation(rule_id, resource, resource_type, message):
            return {
                'rule_id': rule_id,
                'severity': 'ERROR',
                'resource': resource,
                'resource_type': resource_type,
                'message': message,
                'remediation': _REMEDIATION_CACHE.get(
                    rule_id,
                    'Review the resource configuration and ensure it meets the policy requirements',
                ),
            }

        process_node(guard_result.get('result', {}))

        error_count = len(
            violations
        )  # All violations are ERROR severity in current implementation
        overall_status = 'COMPLIANT' if error_count == 0 else 'VIOLATIONS_FOUND'

        message = (
            'Template is compliant with all rules.'
            if overall_status == 'COMPLIANT'
            else 'Template has compliance violations. Address the ERROR-level issues before deployment. Use `cloudformation_pre_deploy_validation` for final deployment readiness check.'
        )

        return {
            'compliance_results': {
                'overall_status': overall_status,
                'total_violations': error_count,
                'error_count': error_count,
                'warning_count': 0,
                'rule_sets_applied': ['aws-security'],
            },
            'violations': violations,
            'message': message,
        }

    except Exception as e:
        return error_result(f'Validation failed: {str(e)}')
