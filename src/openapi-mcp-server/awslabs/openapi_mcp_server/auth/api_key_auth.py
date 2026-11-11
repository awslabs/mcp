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

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ConfigurationError,
    MissingCredentialsError,
)
from awslabs.openapi_mcp_server.auth.auth_provider import BaseAuthProvider
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
        """Initialize authentication data based on the API key location."""
        if self._api_key_in == 'header':
            self._auth_headers = self._generate_auth_data(self._api_key_name)
        elif self._api_key_in == 'query':
            self._auth_params = self._generate_auth_data(self._api_key_name)
        elif self._api_key_in == 'cookie':
            self._auth_cookies = self._generate_auth_data(self._api_key_name)

    def _generate_auth_data(self, api_key_name: str) -> Dict[str, str]:
        """Build the ``{name: key}`` mapping used for header, query, or cookie auth.

        Args:
            api_key_name: Name of the API key field

        Returns:
            Dict[str, str]: The API key mapping

        """
        logger.debug(f'Generating API key auth data with name: {api_key_name}')
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
