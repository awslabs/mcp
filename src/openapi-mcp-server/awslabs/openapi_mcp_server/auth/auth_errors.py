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
"""Authentication errors for the OpenAPI MCP Server."""

from typing import Dict, Optional


class AuthError(Exception):
    """Base class for authentication errors."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """Initialize the error.

        Args:
            message: Error message
            details: Additional error details

        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class MissingCredentialsError(AuthError):
    """Error raised when required credentials are missing."""


class InvalidCredentialsError(AuthError):
    """Error raised when credentials are invalid."""


class ExpiredTokenError(AuthError):
    """Error raised when a token has expired."""


class ConfigurationError(AuthError):
    """Error raised when there is a configuration issue."""


class NetworkError(AuthError):
    """Error raised when there is a network issue."""
