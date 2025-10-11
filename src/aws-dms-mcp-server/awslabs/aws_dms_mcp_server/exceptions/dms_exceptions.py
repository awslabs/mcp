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

"""Exception hierarchy for AWS DMS MCP Server.

Provides custom exceptions that map to AWS DMS API errors with
structured error information for proper error handling.
"""

from datetime import datetime
from typing import Any, Dict, Optional


class DMSMCPException(Exception):
    """Base exception for DMS MCP server."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggested_action: Optional[str] = None,
    ):
        """Initialize base exception.

        Args:
            message: Error message
            details: Additional error details
            suggested_action: Suggested action to resolve the error
        """
        self.message = message
        self.details = details or {}
        self.suggested_action = suggested_action
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to structured dictionary.

        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            'error': True,
            'error_type': self.__class__.__name__,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() + 'Z',
        }

        if self.details:
            error_dict['details'] = self.details

        if self.suggested_action:
            error_dict['details'] = error_dict.get('details', {})
            error_dict['details']['suggested_action'] = self.suggested_action

        return error_dict


class DMSResourceNotFoundException(DMSMCPException):
    """Resource not found (404-equivalent)."""

    pass


class DMSInvalidParameterException(DMSMCPException):
    """Invalid parameter provided."""

    pass


class DMSAccessDeniedException(DMSMCPException):
    """Access denied (403-equivalent)."""

    pass


class DMSResourceInUseException(DMSMCPException):
    """Resource is currently in use."""

    pass


class DMSConnectionTestException(DMSMCPException):
    """Connection test failed."""

    pass


class DMSReadOnlyModeException(DMSMCPException):
    """Operation not allowed in read-only mode."""

    def __init__(self, operation: str):
        """Initialize read-only mode exception.

        Args:
            operation: The operation that was attempted
        """
        message = f"Operation '{operation}' not allowed in read-only mode"
        suggested_action = 'Disable read-only mode by setting DMS_READ_ONLY_MODE=false'
        super().__init__(message, suggested_action=suggested_action)


class DMSValidationException(DMSMCPException):
    """Data validation failed."""

    pass


# AWS Error Code Mapping
# Used by DMSClient to translate AWS SDK errors to custom exceptions
AWS_ERROR_MAP = {
    'ResourceNotFoundFault': DMSResourceNotFoundException,
    'InvalidParameterValueException': DMSInvalidParameterException,
    'InvalidParameterCombinationException': DMSInvalidParameterException,
    'AccessDeniedFault': DMSAccessDeniedException,
    'AccessDeniedException': DMSAccessDeniedException,
    'ResourceAlreadyExistsFault': DMSResourceInUseException,
    'InvalidResourceStateFault': DMSResourceInUseException,
    'TestConnectionFault': DMSConnectionTestException,
}


# TODO: Add retry logic for transient errors
# TODO: Add error code to exception class mapping
# TODO: Add structured logging integration
