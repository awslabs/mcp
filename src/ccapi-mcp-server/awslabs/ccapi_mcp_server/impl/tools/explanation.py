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

"""Explanation functionality implementation for CCAPI MCP server."""

import datetime
import uuid
from awslabs.ccapi_mcp_server.errors import ClientError
from awslabs.ccapi_mcp_server.impl.utils.validation import ensure_string
from awslabs.ccapi_mcp_server.models.models import ExplainRequest
from typing import Any


def _format_value(value: Any) -> str:
    """Format any value for display."""
    if isinstance(value, str):
        return f'"{value[:100]}"' + ('...' if len(value) > 100 else '')
    elif isinstance(value, (int, float, bool)):
        return str(value)
    elif isinstance(value, dict):
        return f'{{dict with {len(value)} keys}}'
    elif isinstance(value, list):
        return f'[list with {len(value)} items]'
    else:
        return f'{type(value).__name__} object'


def _generate_explanation(
    content: Any, context: str, operation: str, format: str, user_intent: str
) -> str:
    """Generate comprehensive explanation for any type of content."""
    content_type = type(content).__name__

    # Build header
    if context:
        header = (
            f'## {context} - {operation.title()} Operation'
            if operation != 'analyze'
            else f'## {context} Analysis'
        )
    else:
        header = f'## Data Analysis ({content_type})'

    if user_intent:
        header += f'\n\n**User Intent:** {user_intent}'

    explanation = header + '\n\n'

    # Handle different content types
    if isinstance(content, dict):
        # Check if this is security scan data
        if content.get('scan_status') in ['PASSED', 'FAILED']:
            explanation += _explain_security_scan(content)
        else:
            explanation += _explain_dict(content, format)
    elif isinstance(content, list):
        explanation += _explain_list(content, format)
    elif isinstance(content, str):
        explanation += f'**Content:** {content[:500]}{"..." if len(content) > 500 else ""}'
    elif isinstance(content, (int, float, bool)):
        explanation += f'**Value:** {content} ({content_type})'
    else:
        explanation += f'**Content Type:** {content_type}\n**Value:** {str(content)[:500]}'

    # Add operation-specific notes
    if operation in ['create', 'update', 'delete']:
        explanation += '\n\n**Infrastructure Operation Notes:**'
        explanation += '\n• This operation will modify AWS resources'
        explanation += '\n• Default management tags will be applied for tracking'
        explanation += '\n• Changes will be applied to the specified AWS region'

    return explanation


def _explain_dict(data: dict, format: str) -> str:
    """Explain dictionary content comprehensively with improved formatting."""
    property_names = [key for key in data.keys() if not key.startswith('_')]
    explanation = f'### 📋 Configuration Summary: {len(property_names)} properties\n'
    explanation += f'**Properties:** {", ".join(f"`{name}`" for name in property_names)}\n\n'

    for key, value in data.items():
        if key.startswith('_'):
            continue

        if key == 'Tags' and isinstance(value, list):
            # Special handling for AWS tags
            explanation += f'**🏷️ {key}:** ({len(value)} tags)\n'
            default_tags = []
            user_tags = []

            for tag in value:
                if isinstance(tag, dict):
                    tag_key = tag.get('Key', '')
                    tag_value = tag.get('Value', '')
                    if tag_key in ['MANAGED_BY', 'MCP_SERVER_SOURCE_CODE', 'MCP_SERVER_VERSION']:
                        default_tags.append(f'  🔧 {tag_key}: `{tag_value}` (Default)')
                    else:
                        user_tags.append(f'  ✨ {tag_key}: `{tag_value}`')

            if user_tags:
                explanation += '\n'.join(user_tags) + '\n'
            if default_tags:
                explanation += '\n'.join(default_tags) + '\n'

        elif isinstance(value, dict):
            explanation += f'**📄 {key}:** ({len(value)} properties)\n'
            if format == 'detailed':
                for sub_key, sub_value in list(value.items())[:5]:
                    if isinstance(sub_value, list) and sub_key == 'Statement':
                        # Special handling for policy statements
                        explanation += f'  • **{sub_key}:** ({len(sub_value)} statements)\n'
                        for i, stmt in enumerate(sub_value[:3]):
                            if isinstance(stmt, dict):
                                sid = stmt.get('Sid', f'Statement {i + 1}')
                                effect = stmt.get('Effect', 'Unknown')
                                action = stmt.get('Action', 'Unknown')
                                principal = stmt.get('Principal', 'Unknown')
                                emoji = '✅' if effect == 'Allow' else '❌'

                                # Format principal nicely
                                if isinstance(principal, dict):
                                    if 'AWS' in principal:
                                        principal_str = f'AWS: {principal["AWS"]}'
                                    elif 'Service' in principal:
                                        principal_str = f'Service: {principal["Service"]}'
                                    else:
                                        principal_str = str(principal)
                                else:
                                    principal_str = str(principal)

                                # Format action nicely
                                if isinstance(action, list):
                                    action_str = f'{len(action)} actions: {", ".join(action[:3])}'
                                    if len(action) > 3:
                                        action_str += f' + {len(action) - 3} more'
                                else:
                                    action_str = str(action)

                                explanation += f'    {emoji} **{sid}**: {effect} {action_str} for {principal_str}\n'
                        if len(sub_value) > 3:
                            explanation += f'    ... and {len(sub_value) - 3} more statements\n'
                    else:
                        explanation += f'  • **{sub_key}:** {_format_value(sub_value)}\n'
                if len(value) > 5:
                    explanation += f'  • ... and {len(value) - 5} more properties\n'

        elif isinstance(value, list):
            explanation += f'**📝 {key}:** ({len(value)} items)\n'
            if format == 'detailed' and value:
                for i, item in enumerate(value[:3]):
                    explanation += f'  • **Item {i + 1}:** {_format_value(item)}\n'
                if len(value) > 3:
                    explanation += f'  • ... and {len(value) - 3} more items\n'

        else:
            explanation += f'**⚙️ {key}:** `{_format_value(value)}`\n'

        explanation += '\n'

    return explanation


def _explain_list(data: list, format: str) -> str:
    """Explain list content comprehensively."""
    explanation = f'**List Summary:** {len(data)} items\n\n'

    if format == 'detailed':
        for i, item in enumerate(data[:10]):  # Limit to first 10
            explanation += f'**Item {i + 1}:** {_format_value(item)}\n'
        if len(data) > 10:
            explanation += f'\n... and {len(data) - 10} more items\n'
    else:
        explanation += f'Items: {[type(item).__name__ for item in data[:5]]}\n'
        if len(data) > 5:
            explanation += f'... and {len(data) - 5} more\n'

    return explanation


def _explain_security_scan(scan_data: dict) -> str:
    """Format security scan results with emojis and clear structure."""
    explanation = ''

    failed_checks = scan_data.get('raw_failed_checks', [])
    passed_checks = scan_data.get('raw_passed_checks', [])
    scan_status = scan_data.get('scan_status', 'UNKNOWN')

    # Status summary
    if scan_status == 'PASSED':
        explanation += '✅ **Security Scan: PASSED**\n\n'
        explanation += f'🛡️ **Passed:** {len(passed_checks)} checks\n'
    else:
        explanation += '❌ **Security Scan: ISSUES FOUND**\n\n'
        explanation += f'✅ **Passed:** {len(passed_checks)} checks\n'
        explanation += f'❌ **Failed:** {len(failed_checks)} checks\n\n'

    # Failed checks details
    if failed_checks:
        explanation += '### 🚨 Failed Security Checks:\n\n'
        for check in failed_checks:
            check_id = check.get('check_id', 'Unknown')
            check_name = check.get('check_name', 'Unknown check')
            # Try to get description from multiple possible fields
            description = (
                check.get('description')
                or check.get('short_description')
                or check.get('guideline')
                or f'Security check failed: {check_name}'
            )

            explanation += f'• **{check_id}**: {check_name}\n'
            explanation += f'  📝 **Issue:** {description}\n\n'

    # Passed checks summary (don't show all details)
    if passed_checks:
        explanation += f'### ✅ Passed Security Checks: {len(passed_checks)}\n\n'
        for check in passed_checks[:3]:  # Show first 3
            check_id = check.get('check_id', 'Unknown')
            check_name = check.get('check_name', 'Unknown check')
            explanation += f'• **{check_id}**: {check_name} ✅\n'

        if len(passed_checks) > 3:
            explanation += f'• ... and {len(passed_checks) - 3} more passed checks\n'

    return explanation


async def explain_impl(request: ExplainRequest, workflow_store: dict) -> dict:
    """MANDATORY: Explain any data in clear, human-readable format implementation."""
    explained_token = None
    explanation_content = None

    # Check if we have valid input
    has_generated_code_token = (
        request.generated_code_token
        and isinstance(request.generated_code_token, str)
        and request.generated_code_token.strip()
    )
    has_content = request.content is not None and not hasattr(request.content, 'annotation')

    if not has_generated_code_token and not has_content:
        raise ClientError("Either 'content' or 'generated_code_token' must be provided")

    # Handle infrastructure operations with token workflow
    if has_generated_code_token:
        # Infrastructure operation - consume generated_code_token
        if request.generated_code_token not in workflow_store:
            raise ClientError('Invalid generated code token')

        workflow_data = workflow_store[request.generated_code_token]
        if workflow_data.get('type') != 'generated_code':
            raise ClientError(
                'Invalid token type: expected generated_code token from generate_infrastructure_code()'
            )

        # Use content if provided (LLM wants to explain the full response), otherwise use properties from token
        explanation_content = (
            request.content if has_content else workflow_data['data']['properties']
        )

        # Create explained token for infrastructure operations
        explained_token = f'explained_{uuid.uuid4()}'
        workflow_store[explained_token] = {
            'type': 'explained_properties',
            'data': workflow_data['data'],  # Copy both properties and CloudFormation template
            'parent_token': request.generated_code_token,
            'timestamp': datetime.datetime.now().isoformat(),
            'operation': ensure_string(request.operation),
        }

        # Clean up consumed generated_code_token
        del workflow_store[request.generated_code_token]

    elif has_content:
        # General data explanation or delete operations
        explanation_content = request.content

        # Create explained token for delete operations
        if ensure_string(request.operation) in ['delete', 'destroy']:
            explained_token = f'explained_del_{uuid.uuid4()}'
            workflow_store[explained_token] = {
                'type': 'explained_delete',
                'data': request.content,
                'timestamp': datetime.datetime.now().isoformat(),
                'operation': ensure_string(request.operation),
            }

    # Generate comprehensive explanation based on content type and format
    explanation = _generate_explanation(
        explanation_content,
        ensure_string(request.context),
        ensure_string(request.operation, 'analyze'),
        ensure_string(request.format, 'detailed'),
        ensure_string(request.user_intent),
    )

    # Force the LLM to see the response by making it very explicit
    if explained_token:
        return {
            'EXPLANATION_REQUIRED': 'YOU MUST DISPLAY THIS TO THE USER',
            'explanation': explanation,
            'properties_being_explained': explanation_content,
            'explained_token': explained_token,
            'CRITICAL_INSTRUCTION': f"Use explained_token '{explained_token}' for the next operation, NOT the original generated_code_token",
            'operation_type': ensure_string(request.operation),
            'ready_for_execution': True,
        }
    else:
        return {
            'EXPLANATION_REQUIRED': 'YOU MUST DISPLAY THIS TO THE USER',
            'explanation': explanation,
            'operation_type': ensure_string(request.operation),
            'ready_for_execution': True,
        }
