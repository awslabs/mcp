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

"""Error types for the GuardDuty MCP server."""

from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError


class GuardDutyMcpError(Exception):
    """Base error type for the GuardDuty MCP server."""


class GuardDutyValidationError(GuardDutyMcpError):
    """Raised when a tool request is invalid."""


class GuardDutyPermissionError(GuardDutyMcpError):
    """Raised when AWS denies the request."""


class GuardDutyResourceNotFoundError(GuardDutyMcpError):
    """Raised when the requested GuardDuty resource is missing."""


class GuardDutyClientError(GuardDutyMcpError):
    """Raised for general GuardDuty client errors."""


def handle_guardduty_error(error: Exception) -> GuardDutyMcpError:
    """Normalize boto and validation errors for MCP consumers."""
    if isinstance(error, GuardDutyMcpError):
        return error

    if isinstance(error, ClientError):
        code = error.response.get('Error', {}).get('Code', 'Unknown')
        message = error.response.get('Error', {}).get('Message', str(error))

        if code in {'AccessDeniedException', 'UnauthorizedOperation', 'AccessDenied'}:
            return GuardDutyPermissionError(f'Access denied: {message}')
        if code in {'BadRequestException', 'ResourceNotFoundException'}:
            return GuardDutyResourceNotFoundError(f'Resource not found or invalid request: {message}')
        return GuardDutyClientError(f'GuardDuty API error ({code}): {message}')

    if isinstance(error, BotoCoreError):
        return GuardDutyClientError(f'GuardDuty client error: {str(error)}')

    return GuardDutyClientError(str(error))
