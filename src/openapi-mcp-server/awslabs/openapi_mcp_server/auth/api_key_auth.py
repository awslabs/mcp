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
"""API Key authentication provider."""

import bcrypt
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_cache import cached_auth_data
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ConfigurationError,
    MissingCredentialsError,
)
from awslabs.openapi_mcp_server.auth.base_auth import BaseAuthProvider
from typing import Dict


class ApiKeyAuthProvider(BaseAuthProvider):
    """API Key authentication provider.

    This provider adds an API key to requests, either in a header,
    query parameter, or cookie.
    """

    def __init__(self, config: Config):
        """Initialize with configuration.

        Args:
            config: Application configuration

        """
        # Store configuration values before calling super().__init__
        # so they're available during validation
        self._api_key = config.auth_api_key
        self._api_key_name = config.auth_api_key_name or 'api_key'
        self._api_key_in = config.auth_api_key_in or 'header'
        self._api_key_hash = None

        # Call parent initializer which will validate and initialize auth
        super().__init__(config)

    def _validate_config(self) -> bool:
        """Validate the configuration.

        Returns:
            bool: True if API key is provided, False otherwise

        Raises:
            MissingCredentialsError: If API key is missing
            ConfigurationError: If API key location is invalid

        """
        if not self._api_key:
            raise MissingCredentialsError(
                'API Key authentication requires a valid API key',
                {
                    'help': 'Provide it using --auth-api-key command line argument or AUTH_API_KEY environment variable'
                },
            )

        if self._api_key_in not in ('header', 'query', 'cookie'):
            raise ConfigurationError(
                f'Invalid API key location: {self._api_key_in}',
                {
                    'valid_locations': ['header', 'query', 'cookie'],
                    'help': 'Provide a valid location using --auth-api-key-in command line argument or AUTH_API_KEY_IN environment variable',
                },
            )

        # Create a hash of the API key for caching
        self._api_key_hash = self._hash_api_key(self._api_key)
        return True

    def _handle_validation_error(self) -> None:
        """Handle validation error."""
        # This should not be called since we raise exceptions in _validate_config
        # But we implement it for completeness
        self._validation_error = MissingCredentialsError(
            'API Key authentication requires a valid API key',
            {
                'help': 'Provide it using --auth-api-key command line argument or AUTH_API_KEY environment variable'
            },
        )
        self._log_auth_error(self._validation_error)

    def _initialize_auth(self) -> None:
        """Initialize authentication data after validation."""
        # Use cached methods to generate auth data based on location
        if self._api_key_in == 'header':
            self._auth_headers = self._generate_auth_headers(self._api_key_hash, self._api_key_name)
        elif self._api_key_in == 'query':
            self._auth_params = self._generate_auth_params(self._api_key_hash, self._api_key_name)
        elif self._api_key_in == 'cookie':
            self._auth_cookies = self._generate_auth_cookies(self._api_key_hash, self._api_key_name)

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """Create a hash of the API key for caching.

        Args:
            api_key: API key

        Returns:
            str: Hash of the API key

        """
        # Create a hash of the API key to use as a cache key
        return bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt(rounds=10)).hex()

    @cached_auth_data(ttl=3600)  # Cache for 1 hour by default
    def _generate_auth_headers(self, api_key_hash: str, api_key_name: str) -> Dict[str, str]:
        """Generate authentication headers.

        This method is cached to avoid regenerating headers for the same API key.

        Args:
            api_key_hash: Hash of the API key
            api_key_name: Name of the API key header

        Returns:
            Dict[str, str]: Authentication headers

        """
        logger.debug(f'Generating new API key headers with name: {api_key_name}')
        # Log key length for debugging without exposing the key
        logger.debug(f'API key length: {len(self._api_key) if self._api_key else 0} characters')
        return {api_key_name: self._api_key}

    @cached_auth_data(ttl=3600)  # Cache for 1 hour by default
    def _generate_auth_params(self, api_key_hash: str, api_key_name: str) -> Dict[str, str]:
        """Generate authentication query parameters.

        This method is cached to avoid regenerating parameters for the same API key.

        Args:
            api_key_hash: Hash of the API key
            api_key_name: Name of the API key parameter

        Returns:
            Dict[str, str]: Authentication query parameters

        """
        logger.debug(f'Generating new API key query parameters with name: {api_key_name}')
        # Log key length for debugging without exposing the key
        logger.debug(f'API key length: {len(self._api_key) if self._api_key else 0} characters')
        return {api_key_name: self._api_key}

    @cached_auth_data(ttl=3600)  # Cache for 1 hour by default
    def _generate_auth_cookies(self, api_key_hash: str, api_key_name: str) -> Dict[str, str]:
        """Generate authentication cookies.

        This method is cached to avoid regenerating cookies for the same API key.

        Args:
            api_key_hash: Hash of the API key
            api_key_name: Name of the API key cookie

        Returns:
            Dict[str, str]: Authentication cookies

        """
        logger.debug(f'Generating new API key cookies with name: {api_key_name}')
        # Log key length for debugging without exposing the key
        logger.debug(f'API key length: {len(self._api_key) if self._api_key else 0} characters')
        return {api_key_name: self._api_key}

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider.

        Returns:
            str: Name of the authentication provider

        """
        return 'api_key'
