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

from .config import DEFAULT_REGION, MAX_TEMPLATE_SIZE_BYTES
from cfnlint.api import lint as cfn_lint
from cfnlint.match import Match
from typing import Any, Sequence


def validate_template(
    template_content: str,
    regions: Sequence[str] | None = None,
    ignore_checks: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate a CloudFormation template using cfn-lint.

    Args:
        template_content: CloudFormation template as YAML or JSON string
        regions: AWS regions to validate against
        ignore_checks: Rule IDs to ignore

    Returns:
        Validation results dictionary with matches and metadata
    """
    if not template_content or not template_content.strip():
        return {
            'valid': False,
            'error': 'template_required',
            'message': 'Template content cannot be empty',
        }

    if len(template_content) > MAX_TEMPLATE_SIZE_BYTES:
        return {
            'valid': False,
            'error': 'template_too_large',
            'message': f'Template exceeds maximum size of {MAX_TEMPLATE_SIZE_BYTES} bytes',
        }

    manual_args: dict[str, Any] = {
        'regions': list(regions) if regions else list(DEFAULT_REGION),
    }
    if ignore_checks:
        manual_args['ignore_checks'] = list(ignore_checks)

    try:
        matches = cfn_lint(
            s=template_content,
            regions=None,
            config=manual_args,  # type: ignore[arg-type]
        )
        return _format_results(matches)

    except Exception as e:
        return {
            'valid': False,
            'error': 'validation_failed',
            'message': str(e),
        }


def _format_results(matches: Sequence[Match]) -> dict[str, Any]:
    """Format cfn-lint Match objects into output schema."""
    formatted_matches: list[dict[str, Any]] = []
    error_count = 0
    warning_count = 0
    info_count = 0

    for match in matches:
        level = _map_level(match.rule.id)

        if level == 'error':
            error_count += 1
        elif level == 'warning':
            warning_count += 1
        else:
            info_count += 1

        formatted_match = {
            'rule': match.rule.id,
            'level': level,
            'message': match.message,
            'filename': getattr(match, 'filename', None) or 'template.yaml',
            'line_number': match.linenumber,
            'column_number': match.columnnumber,
            'fix_suggestion': match.rule.description,
        }
        formatted_matches.append(formatted_match)

    # Generate appropriate message
    if error_count > 0:
        message = 'Template has validation errors. Fix the errors above, then use `cloudformation_template_compliance_validation` to check security and compliance rules.'
    elif warning_count > 0:
        message = f'Template has {warning_count} warnings. Review and address as needed.'
    else:
        message = 'Template is valid.'

    return {
        'validation_results': {
            'is_valid': error_count == 0,
            'error_count': error_count,
            'warning_count': warning_count,
            'info_count': info_count,
        },
        'issues': formatted_matches,
        'message': message,
    }


def _map_level(rule_id: str) -> str:
    """Map rule ID prefix to severity level.

    Args:
        rule_id: Rule identifier (e.g., E3012, W2001)

    Returns:
        Severity level string
    """
    if rule_id.startswith('E'):
        return 'error'
    if rule_id.startswith('W'):
        return 'warning'
    if rule_id.startswith('I'):
        return 'info'
    return 'error'
