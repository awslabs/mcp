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

"""CloudFormation template validation tools."""

from __future__ import annotations

from ..config import DEFAULT_REGION
from ..models.validation_models import (
    ValidationIssue,
    ValidationResponse,
    ValidationResults,
)
from cfnlint.api import lint as cfn_lint
from cfnlint.match import Match
from typing import List, Optional, Sequence


def validate_cloudformation_template(
    template_content: str,
    regions: Optional[List[str]] = None,
    ignore_checks: Optional[List[str]] = None,
) -> ValidationResponse:
    """Validate CloudFormation template using cfn-lint.

    Logic is directly in this function - no service layer.
    Returns ValidationResponse dataclass.

    Args:
        template_content: CloudFormation template content (YAML or JSON)
        regions: Optional list of AWS regions to validate against
        ignore_checks: Optional list of rule IDs to ignore

    Returns:
        ValidationResponse with validation results
    """
    manual_args = {
        'regions': list(regions) if regions else list(DEFAULT_REGION),
    }
    if ignore_checks:
        manual_args['ignore_checks'] = list(ignore_checks)

    try:
        # Run cfn-lint validation
        matches = cfn_lint(
            s=template_content,
            regions=None,
            config=manual_args,  # type: ignore[arg-type]
        )
        return _format_results(matches)

    except Exception as e:
        # Return error as ValidationResponse
        return ValidationResponse(
            validation_results=ValidationResults(
                is_valid=False,
                error_count=0,
                warning_count=0,
                info_count=0,
            ),
            issues=[],
            message=f'Validation failed: {str(e)}',
        )


def _format_results(matches: Sequence[Match]) -> ValidationResponse:
    """Format cfn-lint Match objects into ValidationResponse model.

    Args:
        matches: Sequence of cfn-lint Match objects

    Returns:
        ValidationResponse with formatted results
    """
    issues: list[ValidationIssue] = []
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

        issues.append(
            ValidationIssue(
                rule=match.rule.id,
                level=level,
                message=match.message,
                filename=getattr(match, 'filename', None) or 'template.yaml',
                line_number=match.linenumber,
                column_number=match.columnnumber,
                fix_suggestion=match.rule.description,
            )
        )

    # Generate appropriate message
    if error_count > 0:
        message = 'Template has validation errors. Fix the errors above, then use `cloudformation_template_compliance_validation` to check security and compliance rules.'
    elif warning_count > 0:
        message = f'Template has {warning_count} warnings. Review and address as needed.'
    else:
        message = 'Template is valid.'

    return ValidationResponse(
        validation_results=ValidationResults(
            is_valid=error_count == 0,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
        ),
        issues=issues,
        message=message,
    )


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
