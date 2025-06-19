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
"""Bearer token authentication provider."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_cache import cached_auth_data
from awslabs.openapi_mcp_server.auth.auth_errors import MissingCredentialsError
from awslabs.openapi_mcp_server.auth.base_auth import BaseAuthProvider
from typing import Dict


class BearerAuthProvider(BaseAuthProvider):
    """Bearer token authentication provider.

    This provider adds an Authorization header with a Bearer token
    to all HTTP requests.
    """

    def __init__(self, config: Config):
        """Initialize with configuration.

        Args:
            config: Application configuration

        """
        # Store token before calling super().__init__
        self._token = config.auth_token
        self._token_ttl = getattr(config, 'auth_token_ttl', 3600)  # Default 1 hour

        # Call parent initializer which will validate and initialize auth
        super().__init__(config)

    def _validate_config(self) -> bool:
        """Validate the configuration.

        Returns:
            bool: True if token is provided, False otherwise

        Raises:
            MissingCredentialsError: If token is missing

        """
        if not self._token:
            raise MissingCredentialsError(
                'Bearer authentication requires a valid token',
                {
                    'help': 'Provide a token using --auth-token command line argument or AUTH_TOKEN environment variable'
                },
            )
        return True

    def _log_validation_error(self) -> None:
        """Log validation error messages."""
        logger.error(
            'Bearer authentication requires a valid token. When using bearer authentication, a token must be provided.'
        )
        logger.error(
            'Please provide a token using --auth-token command line argument or AUTH_TOKEN environment variable.'
        )

    def _initialize_auth(self) -> None:
        """Initialize authentication data after validation."""
        # We'll use the cached method to generate headers
        self._auth_headers = self._generate_auth_headers(self._token)

    @cached_auth_data(ttl=3600)  # Cache for 1 hour by default
    def _generate_auth_headers(self, token: str) -> Dict[str, str]:
        """Generate authentication headers.

        This method is cached to avoid regenerating headers for the same token.

        Args:
            token: Bearer token

        Returns:
            Dict[str, str]: Authentication headers

        """
        # Log without including the token
        logger.debug('Generating new bearer token headers')

        # Calculate token length for debugging purposes
        token_length = len(token) if token else 0
        logger.debug(f'Token length: {token_length} characters')

        return {'Authorization': f'Bearer {token}'}

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider.

        Returns:
            str: Name of the authentication provider

        """
        return 'bearer'
