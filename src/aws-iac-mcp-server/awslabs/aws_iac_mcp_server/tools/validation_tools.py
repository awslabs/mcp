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

"""Tool adapter for CloudFormation template validation."""

import json
from ..services.validator import validate_template as validate_service
from ..utils.sanitizer import sanitize_tool_response
from typing import List, Optional


def validate_cloudformation_template(
    template_content: str,
    regions: Optional[List[str]] = None,
    ignore_checks: Optional[List[str]] = None,
) -> str:
    """Validate CloudFormation template.

    Adapter function that bridges MCP tool to service layer.

    Args:
        template_content: CloudFormation template content (YAML or JSON)
        regions: Optional list of AWS regions to validate against
        ignore_checks: Optional list of rule IDs to ignore

    Returns:
        JSON string with validation results
    """
    try:
        # Call service layer directly with parameters
        response = validate_service(
            template_content=template_content,
            regions=regions,
            ignore_checks=ignore_checks
        )

        # Serialize and sanitize response
        json_response = response.model_dump_json(indent=2)
        return sanitize_tool_response(json_response)

    except Exception as e:
        # Format general error response
        error_response = {
            'validation_results': {
                'is_valid': False,
                'error_count': 0,
                'warning_count': 0,
                'info_count': 0
            },
            'issues': [],
            'message': f'Validation error: {str(e)}'
        }
        return sanitize_tool_response(json.dumps(error_response, indent=2))
