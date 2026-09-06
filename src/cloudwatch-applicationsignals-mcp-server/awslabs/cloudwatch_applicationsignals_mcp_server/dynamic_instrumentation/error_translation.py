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
"""Translate botocore exceptions into the human-readable failure text used by MCP tools.

Replaces the ad-hoc ``Failed to ...`` blocks that the AWS-CLI-based code
emitted from ``subprocess`` failure ladders. Keeps the section headers
(``Error:``, ``ATTEMPTED PARAMETERS:``, ``POSSIBLE CAUSES:``,
``TROUBLESHOOTING:``) so MCP clients see no contract change.
"""

from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)
from typing import Mapping, Optional, Sequence


def _format_block(label: str, context: Optional[Mapping[str, object]]) -> str:
    if not context:
        return ''
    lines = []
    for key, value in context.items():
        if value is None or value == '':
            continue
        lines.append(f'- {key}: {value}')
    if not lines:
        return ''
    return f'\n{label}\n' + '\n'.join(lines) + '\n'


def _format_attempted_block(context: Optional[Mapping[str, object]]) -> str:
    return _format_block('ATTEMPTED PARAMETERS:', context)


def _format_numbered_section(label: str, items: Optional[Sequence[str]]) -> str:
    if not items:
        return ''
    body = '\n'.join(f'{idx}. {item}' for idx, item in enumerate(items, 1))
    return f'\n{label}\n{body}\n'


def _client_error_body(exc: ClientError) -> tuple[str, str]:
    error = exc.response.get('Error', {}) if isinstance(exc.response, dict) else {}
    code = error.get('Code') or 'ClientError'
    message = error.get('Message') or str(exc)
    return code, message


def render_client_error(
    exc: ClientError,
    *,
    action: str,
    attempted_label: str = 'ATTEMPTED PARAMETERS:',
    attempted: Optional[Mapping[str, object]] = None,
    possible_causes: Optional[Sequence[str]] = None,
    troubleshooting: Optional[Sequence[str]] = None,
    trailer: Optional[str] = None,
) -> str:
    """Render a tool-tailored failure block for a botocore ``ClientError``.

    Tools share the same skeleton — ``Failed to {action}``, an ``Error:`` line,
    an attempted-values block, and ``POSSIBLE CAUSES`` / ``TROUBLESHOOTING``
    numbered sections — but each tool tunes the labels and bullet content.
    This helper takes those bullets as parameters so each call site can keep
    its CLI-era wording without re-implementing the skeleton.

    Use ``trailer`` for any tool-specific footer (e.g. the location
    troubleshooting block emitted after a failed create).
    """
    code, message = _client_error_body(exc)
    sections = [
        f'Failed to {action}\n',
        f'\nError: {code} - {message}\n',
        _format_block(attempted_label, attempted),
        _format_numbered_section('POSSIBLE CAUSES:', possible_causes),
        _format_numbered_section('TROUBLESHOOTING:', troubleshooting),
    ]
    body = ''.join(sections).rstrip()
    if trailer:
        return f'{body}\n\n{trailer}'
    return body


def translate_aws_error(
    exc: BaseException,
    *,
    action: str,
    context: Optional[Mapping[str, object]] = None,
) -> str:
    """Render a human-readable failure block for an AWS API exception.

    Args:
        exc: The exception raised by a boto3/botocore call.
        action: A short verb phrase such as ``"create BREAKPOINT instrumentation"``.
        context: Optional ordered mapping of attempted parameters.

    Returns:
        A multi-line string starting with ``Failed to {action}`` and including
        an ``Error:`` line, an ``ATTEMPTED PARAMETERS:`` block when context
        is provided, and standard ``POSSIBLE CAUSES``/``TROUBLESHOOTING``
        sections tuned to the exception type.
    """
    attempted = _format_attempted_block(context)

    if isinstance(exc, ClientError):
        code, message = _client_error_body(exc)
        return (
            f'Failed to {action}\n\n'
            f'Error: {code} - {message}\n'
            f'{attempted}'
            '\nPOSSIBLE CAUSES:\n'
            '1. Invalid input parameters (validation error)\n'
            '2. Resource not found, already exists, or scoped to a different account\n'
            '3. Insufficient IAM permissions\n'
            '4. Service-side throttling or transient error\n'
            '\nTROUBLESHOOTING:\n'
            '1. Re-read the error message above for the specific failure cause\n'
            '2. Verify service, environment, and instrumentation_type identifiers\n'
            '3. Verify credentials map to an account/region with access\n'
        )

    if isinstance(exc, EndpointConnectionError):
        return (
            f'Failed to {action}\n\n'
            f'Error: EndpointConnectionError - {exc}\n'
            f'{attempted}'
            '\nTROUBLESHOOTING:\n'
            '1. Check network connectivity to the AWS endpoint\n'
            '2. Verify AWS region resolution (AWS_REGION env var or profile)\n'
        )

    if isinstance(exc, (ReadTimeoutError, ConnectTimeoutError)):
        return (
            f'Failed to {action}\n\n'
            f'Error: TimeoutError - {exc}\n'
            f'{attempted}'
            '\nTROUBLESHOOTING:\n'
            '1. Retry the request — the AWS endpoint did not respond within the socket timeout\n'
            '2. Check network connectivity\n'
        )

    if isinstance(exc, (NoCredentialsError, PartialCredentialsError)):
        return (
            f'Failed to {action}\n\n'
            f'Error: {type(exc).__name__} - {exc}\n'
            f'{attempted}'
            '\nTROUBLESHOOTING:\n'
            '1. Verify AWS credentials: aws configure list\n'
            '2. Set AWS_PROFILE or supply credentials via env vars\n'
        )

    return f'Failed to {action}\n\nUnexpected error: {exc}\n{attempted}'
