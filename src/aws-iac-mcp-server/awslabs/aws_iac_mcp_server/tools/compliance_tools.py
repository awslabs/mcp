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

"""Tool adapter for CloudFormation template compliance checking."""

import json
from ..services.compliance_checker import check_compliance as check_service
from ..utils.sanitizer import sanitize_tool_response


def check_template_compliance(
    template_content: str,
    rules_file_path: str = 'default_guard_rules.guard'
) -> str:
    """Check template compliance.

    Adapter function that bridges MCP tool to service layer.

    Args:
        template_content: CloudFormation template content (YAML or JSON)
        rules_file_path: Path to guard rules file

    Returns:
        JSON string with compliance check results
    """
    try:
        # Call service layer directly with parameters
        response = check_service(
            template_content=template_content,
            rules_file_path=rules_file_path
        )

        # Serialize and sanitize response
        json_response = response.model_dump_json(indent=2)
        return sanitize_tool_response(json_response)

    except Exception as e:
        # Format general error response
        error_response = {
            'compliance_results': {
                'overall_status': 'ERROR',
                'total_violations': 0,
                'error_count': 0,
                'warning_count': 0,
                'rule_sets_applied': []
            },
            'violations': [],
            'message': f'Compliance check error: {str(e)}'
        }
        return sanitize_tool_response(json.dumps(error_response, indent=2))
