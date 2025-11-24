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

from ..cloudformation_compliance_checker import check_compliance
from ..cloudformation_deployment_troubleshooter import DeploymentTroubleshooter
from ..cloudformation_validator import validate_template
from typing import Optional


def validate_cloudformation_template_tool(
    template_content: str,
    regions: Optional[list[str]] = None,
    ignore_checks: Optional[list[str]] = None,
) -> dict:
    """Validate CloudFormation template syntax, schema, and resource properties.

    Args:
        template_content: CloudFormation template as YAML or JSON string
        regions: AWS regions to validate against
        ignore_checks: Rule IDs to ignore (e.g., W2001, E3012)

    Returns:
        Validation results dictionary
    """
    return validate_template(
        template_content=template_content,
        regions=regions,
        ignore_checks=ignore_checks,
    )


def check_cloudformation_template_compliance_tool(
    template_content: str, rules_file_path: str = 'default_guard_rules.guard'
) -> dict:
    """Validate CloudFormation template against security and compliance rules.

    Args:
        template_content: CloudFormation template as YAML or JSON string
        rules_file_path: Path to guard rules file

    Returns:
        Compliance check results dictionary
    """
    return check_compliance(
        template_content=template_content,
        rules_file_path=rules_file_path,
    )


def troubleshoot_cloudformation_deployment_tool(
    stack_name: str,
    region: str,
    include_cloudtrail: bool = True,
) -> dict:
    """Troubleshoot CloudFormation deployment failures.

    Args:
        stack_name: Name of the failed CloudFormation stack
        region: AWS region where the stack deployment failed
        include_cloudtrail: Whether to include CloudTrail analysis

    Returns:
        Troubleshooting results dictionary with deeplink instruction
    """
    troubleshooter = DeploymentTroubleshooter(region=region)
    result = troubleshooter.troubleshoot_stack_deployment(
        stack_name=stack_name, include_cloudtrail=include_cloudtrail
    )

    # Add deeplink instruction to result
    if isinstance(result, dict):
        result['_instruction'] = (
            f'ALWAYS include this CloudFormation console deeplink in your response: '
            f'[View Stack](https://console.aws.amazon.com/cloudformation/home?region={region}'
            f'#/stacks/stackinfo?stackId={stack_name})'
        )

    return result
