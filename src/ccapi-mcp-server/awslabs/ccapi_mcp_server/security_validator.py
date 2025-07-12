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

"""Security validation utilities for the CFN MCP Server."""

import datetime
from awslabs.ccapi_mcp_server.errors import ClientError


def validate_security_check_result(
    security_check_result, resource_type, skip_security_check=False
):
    """Validate that a security check result is valid and appropriate for the resource.

    Args:
        security_check_result: The result from run_checkov()
        resource_type: The AWS resource type being created or updated
        skip_security_check: Whether security checks should be skipped

    Returns:
        None if validation passes

    Raises:
        ClientError: If validation fails
    """
    if skip_security_check:
        return

    # Verify that security_check_result is valid and came from run_checkov()
    if not security_check_result or not isinstance(security_check_result, dict):
        raise ClientError('You must call run_checkov() first and pass its result to this function')

    # Check if the security check is recent (within the last hour)
    if 'timestamp' in security_check_result:
        try:
            check_time = datetime.datetime.fromisoformat(
                security_check_result['timestamp'].replace('Z', '+00:00')
            )
            now = datetime.datetime.now()
            time_diff = now - check_time
            if time_diff.total_seconds() > 3600:  # 1 hour
                raise ClientError(
                    f'Security check is too old (performed {time_diff.total_seconds() / 60:.1f} minutes ago). '
                    'Please run a new security check with run_checkov().'
                )
        except (ValueError, TypeError):
            # If we can't parse the timestamp, continue with other validations
            pass

    # Verify that the security check was performed on the correct resource type
    if (
        security_check_result.get('resource_type')
        and security_check_result.get('resource_type') != resource_type
    ):
        raise ClientError(
            f'Security check was performed for {security_check_result.get("resource_type")} but you are trying to '
            f'create/update {resource_type}. Please run security checks for the correct resource type.'
        )

    # Process security check failures
    if not security_check_result.get('passed', False):
        failed_checks = security_check_result.get('failed_checks', [])
        if failed_checks:
            # Check for high severity issues
            high_severity_issues = [
                check
                for check in failed_checks
                if check.get('severity')
                and check.get('severity', '').upper() in ['HIGH', 'CRITICAL']
            ]

            if high_severity_issues:
                # Format the security findings for the user
                security_findings = 'Security scan found the following issues:\n\n'
                for issue in high_severity_issues:
                    security_findings += f'- {issue.get("check_name", "Unknown check")}: {issue.get("check_id", "No ID")}\n'
                    security_findings += f'  Severity: {issue.get("severity", "Unknown")}\n'
                    security_findings += (
                        f'  Description: {issue.get("description", "No description")}\n'
                    )
                    security_findings += f'  File: {issue.get("file_path", "Unknown")}\n'
                    security_findings += f'  Resource: {issue.get("resource", "Unknown")}\n\n'

                # Raise an error with the security findings
                raise ClientError(
                    f'Security checks failed with high severity issues:\n\n{security_findings}\n\n'
                    'Please fix these issues before creating/updating the resource or use skip_security_check=True '
                    'to bypass (not recommended).'
                )
