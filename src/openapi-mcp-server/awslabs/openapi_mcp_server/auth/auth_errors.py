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
"""Authentication error handling.

This module provides centralized error handling for authentication providers.
"""

from enum import Enum
from typing import Dict, Optional, Type


class AuthErrorType(Enum):
    """Authentication error types."""

    MISSING_CREDENTIALS = 'missing_credentials'
    INVALID_CREDENTIALS = 'invalid_credentials'
    EXPIRED_TOKEN = 'expired_token'  # nosec B105
    INSUFFICIENT_PERMISSIONS = 'insufficient_permissions'
    CONFIGURATION_ERROR = 'configuration_error'
    NETWORK_ERROR = 'network_error'
    UNKNOWN_ERROR = 'unknown_error'


class AuthError(Exception):
    """Base class for authentication errors."""

    def __init__(
        self,
        message: str,
        error_type: AuthErrorType = AuthErrorType.UNKNOWN_ERROR,
        details: Optional[Dict] = None,
    ):
        """Initialize the error.

        Args:
            message: Error message
            error_type: Type of authentication error
            details: Additional error details

        """
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Get string representation of the error.

        Returns:
            str: Error message with type

        """
        return f'{self.error_type.value}: {self.message}'


class MissingCredentialsError(AuthError):
    """Error raised when required credentials are missing."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details

        """
        super().__init__(
            message=message, error_type=AuthErrorType.MISSING_CREDENTIALS, details=details
        )


class InvalidCredentialsError(AuthError):
    """Error raised when credentials are invalid."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details

        """
        super().__init__(
            message=message, error_type=AuthErrorType.INVALID_CREDENTIALS, details=details
        )


class ExpiredTokenError(AuthError):
    """Error raised when a token has expired."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details

        """
        super().__init__(message=message, error_type=AuthErrorType.EXPIRED_TOKEN, details=details)


class InsufficientPermissionsError(AuthError):
    """Error raised when permissions are insufficient."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details

        """
        super().__init__(
            message=message, error_type=AuthErrorType.INSUFFICIENT_PERMISSIONS, details=details
        )


class ConfigurationError(AuthError):
    """Error raised when there is a configuration issue."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details

        """
        super().__init__(
            message=message, error_type=AuthErrorType.CONFIGURATION_ERROR, details=details
        )


class NetworkError(AuthError):
    """Error raised when there is a network issue."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details

        """
        super().__init__(message=message, error_type=AuthErrorType.NETWORK_ERROR, details=details)


# Map of error types to error classes
ERROR_CLASSES: Dict[AuthErrorType, Type[AuthError]] = {
    AuthErrorType.MISSING_CREDENTIALS: MissingCredentialsError,
    AuthErrorType.INVALID_CREDENTIALS: InvalidCredentialsError,
    AuthErrorType.EXPIRED_TOKEN: ExpiredTokenError,
    AuthErrorType.INSUFFICIENT_PERMISSIONS: InsufficientPermissionsError,
    AuthErrorType.CONFIGURATION_ERROR: ConfigurationError,
    AuthErrorType.NETWORK_ERROR: NetworkError,
    AuthErrorType.UNKNOWN_ERROR: AuthError,
}


def create_auth_error(
    error_type: AuthErrorType, message: str, details: Optional[Dict] = None
) -> AuthError:
    """Create an authentication error of the specified type.

    Args:
        error_type: Type of authentication error
        message: Error message
        details: Additional error details

    Returns:
        AuthError: An instance of the appropriate error class

    """
    error_class = ERROR_CLASSES.get(error_type, AuthError)
    if error_class == AuthError:
        # For the base class, we need to pass the error_type explicitly
        return AuthError(message=message, error_type=error_type, details=details)
    else:
        # For subclasses, the error_type is already set in the constructor
        return error_class(message=message, details=details)


def format_error_message(provider_name: str, error_type: AuthErrorType, message: str) -> str:
    """Format an error message for consistent output.

    Args:
        provider_name: Name of the authentication provider
        error_type: Type of authentication error
        message: Error message

    Returns:
        str: Formatted error message

    """
    return f'[{provider_name.upper()}] {error_type.value}: {message}'
