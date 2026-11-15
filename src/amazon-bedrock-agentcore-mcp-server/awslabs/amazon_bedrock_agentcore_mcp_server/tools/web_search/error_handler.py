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

"""Error handling utilities for AgentCore Web Search tools."""

from .models import ErrorResponse
from botocore.exceptions import ClientError
from loguru import logger


ACCESS_DENIED_HINT = (
    ' The caller needs the bedrock-agentcore:InvokeWebSearch permission on '
    'arn:aws:bedrock-agentcore:<region>:aws:tool/web-search.v1.'
)


def handle_web_search_error(operation: str, error: Exception) -> ErrorResponse:
    """Convert an exception into a structured ErrorResponse.

    Extracts error code, message, and HTTP status from botocore ClientError.
    For ValidationException it adds the reason and the invalid fields; for
    AccessDeniedException it names the required IAM permission.

    Args:
        operation: Name of the operation that failed (e.g. 'InvokeWebSearch').
        error: The exception that was raised.

    Returns:
        ErrorResponse with structured error details.
    """
    if isinstance(error, ClientError):
        error_info = error.response.get('Error', {})
        code = error_info.get('Code', 'Unknown')
        msg = error_info.get('Message', str(error))
        http_status = str(error.response.get('ResponseMetadata', {}).get('HTTPStatusCode', ''))

        if code == 'ValidationException':
            reason = error.response.get('reason')
            fields = [f['name'] for f in error.response.get('fieldList', []) if f.get('name')]
            if reason:
                msg = f'{msg} (reason: {reason})'
            if fields:
                msg = f'{msg} (fields: {", ".join(fields)})'
        elif code == 'AccessDeniedException':
            msg = f'{msg}.{ACCESS_DENIED_HINT}'

        logger.error(f'{operation} failed: {code} - {msg}')
        return ErrorResponse(
            message=f'{operation} failed: {msg}',
            error_type=code,
            error_code=http_status,
        )

    logger.error(f'{operation} failed: {type(error).__name__}: {error}')
    return ErrorResponse(
        message=f'{operation} failed: {error}',
        error_type=type(error).__name__,
    )
