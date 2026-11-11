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
"""Authentication provider interface and base implementations."""

import httpx
from abc import ABC, abstractmethod
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import AuthError, ConfigurationError
from typing import Any, Dict, Optional


class AuthProvider(ABC):
    """Abstract base class for authentication providers.

    Authentication providers handle different authentication methods for APIs.
    Implementing classes must provide methods for setting up authentication
    for HTTP requests.
    """

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for HTTP requests."""
        ...

    @abstractmethod
    def get_auth_params(self) -> Dict[str, str]:
        """Get authentication query parameters for HTTP requests."""
        ...

    @abstractmethod
    def get_auth_cookies(self) -> Dict[str, str]:
        """Get authentication cookies for HTTP requests."""
        ...

    @abstractmethod
    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Get authentication object for HTTPX."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the authentication provider is properly configured."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of the authentication provider."""
        ...


class NullAuthProvider(AuthProvider):
    """No-op authentication provider.

    This provider is used when authentication is disabled or not configured.
    """

    def __init__(self, config: Any = None):
        """Initialize with optional configuration (ignored)."""
        pass

    def get_auth_headers(self) -> Dict[str, str]:
        """Return an empty set of headers."""
        return {}

    def get_auth_params(self) -> Dict[str, str]:
        """Return an empty set of query parameters."""
        return {}

    def get_auth_cookies(self) -> Dict[str, str]:
        """Return an empty set of cookies."""
        return {}

    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Return no HTTPX auth."""
        return None

    def is_configured(self) -> bool:
        """Null provider requires no configuration, so it is always ready."""
        return True

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider."""
        return 'none'


class BaseAuthProvider(AuthProvider):
    """Base class for configured authentication providers.

    Implements a small template method: on construction the configuration is
    validated and, if valid, authentication data is initialized. Invalid
    configuration raises an ``AuthError`` so callers can surface the problem.
    """

    def __init__(self, config: Config):
        """Validate configuration and initialize authentication data.

        Args:
            config: Application configuration

        Raises:
            AuthError: If the configuration is invalid

        """
        self._config = config
        self._is_valid = False
        self._auth_headers: Dict[str, str] = {}
        self._auth_params: Dict[str, str] = {}
        self._auth_cookies: Dict[str, str] = {}
        self._validation_error: Optional[AuthError] = None

        try:
            self._is_valid = self._validate_config()
            if self._is_valid:
                self._initialize_auth()
            else:
                self._handle_validation_error()
        except AuthError as e:
            self._validation_error = e
            self._is_valid = False
            self._log_auth_error(e)
            raise
        except Exception as e:
            self._validation_error = ConfigurationError(
                f'Unexpected error during authentication provider initialization: {str(e)}'
            )
            self._is_valid = False
            self._log_auth_error(self._validation_error)
            raise self._validation_error

    def _initialize_auth(self) -> None:
        """Initialize authentication data after successful validation.

        Override in subclasses to populate headers, params, or cookies.
        """
        pass

    @abstractmethod
    def _validate_config(self) -> bool:
        """Validate the configuration.

        Returns:
            bool: True if configuration is valid, False otherwise

        Raises:
            AuthError: If validation fails with a specific error

        """
        ...

    def _handle_validation_error(self) -> None:
        """Record and log a generic validation error.

        Called when validation returns False without raising. Subclasses may
        override to provide a more specific error.
        """
        self._validation_error = ConfigurationError(
            f'Invalid configuration for {self.provider_name} authentication provider'
        )
        self._log_auth_error(self._validation_error)

    def _log_validation_error(self) -> None:
        """Log validation error messages (overridden by subclasses)."""
        self._handle_validation_error()

    def _log_auth_error(self, error: AuthError) -> None:
        """Log an authentication error."""
        logger.error(f'[{self.provider_name.upper()}] {error.message}')
        if error.details:
            logger.debug(f'Error details: {error.details}')

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers, or an empty dict if misconfigured."""
        return self._auth_headers if self._is_valid else {}

    def get_auth_params(self) -> Dict[str, str]:
        """Get authentication query parameters, or an empty dict if misconfigured."""
        return self._auth_params if self._is_valid else {}

    def get_auth_cookies(self) -> Dict[str, str]:
        """Get authentication cookies, or an empty dict if misconfigured."""
        return self._auth_cookies if self._is_valid else {}

    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Get an HTTPX auth object (none by default)."""
        return None

    def is_configured(self) -> bool:
        """Check if the authentication provider is properly configured."""
        return self._is_valid

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of the authentication provider."""
        ...
