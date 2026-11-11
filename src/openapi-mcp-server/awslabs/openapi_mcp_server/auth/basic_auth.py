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
"""Basic authentication provider."""

import base64
import httpx
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import MissingCredentialsError
from awslabs.openapi_mcp_server.auth.auth_provider import BaseAuthProvider
from typing import Dict, Optional


class BasicAuthProvider(BaseAuthProvider):
    """Basic authentication provider.

    This provider adds an Authorization header with Basic authentication
    to all HTTP requests.
    """

    def __init__(self, config: Config):
        """Initialize with configuration.

        Args:
            config: Application configuration

        """
        # Store credentials before calling super().__init__
        self._username = config.auth_username
        self._password = config.auth_password
        self._httpx_auth: Optional[httpx.Auth] = None

        # Call parent initializer which will validate and initialize auth
        super().__init__(config)

    def _validate_config(self) -> bool:
        """Validate the configuration.

        Returns:
            bool: True if username and password are provided, False otherwise

        Raises:
            MissingCredentialsError: If username or password is missing

        """
        if not self._username:
            raise MissingCredentialsError(
                'Basic authentication requires a username',
                {
                    'help': 'Provide a username using --auth-username command line argument or AUTH_USERNAME environment variable'
                },
            )

        if not self._password:
            raise MissingCredentialsError(
                'Basic authentication requires a password',
                {
                    'help': 'Provide a password using --auth-password command line argument or AUTH_PASSWORD environment variable'
                },
            )

        return True

    def _log_validation_error(self) -> None:
        """Log validation error messages."""
        logger.error(
            'Basic authentication requires both username and password. Please provide them using --auth-username and --auth-password command line arguments or AUTH_USERNAME and AUTH_PASSWORD environment variables.'
        )

    def _initialize_auth(self) -> None:
        """Initialize authentication data after validation."""
        self._auth_headers = self._generate_auth_headers(None)
        self._httpx_auth = self._generate_httpx_auth(self._username, self._password)

    def _generate_auth_headers(self, credentials_hash: str = None) -> Dict[str, str]:
        """Generate the Basic authentication header.

        Args:
            credentials_hash: Unused; retained for call-site compatibility.

        Returns:
            Dict[str, str]: Authentication headers

        """
        logger.debug(f'Generating basic auth headers for user: {self._username}')

        # Create the basic auth header
        auth_string = f'{self._username}:{self._password}'
        auth_bytes = auth_string.encode('utf-8')
        encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')

        return {'Authorization': f'Basic {encoded_auth}'}

    def _generate_httpx_auth(self, username: str, password: str) -> httpx.BasicAuth:
        """Generate HTTPX auth object.

        Args:
            username: Username
            password: Password

        Returns:
            httpx.BasicAuth: HTTPX auth object

        """
        logger.debug(f'Generating new HTTPX basic auth object for user: {username}')
        return httpx.BasicAuth(username=username, password=password)

    def get_httpx_auth(self) -> Optional[httpx.Auth]:
        """Get authentication object for HTTPX.

        Returns:
            Optional[httpx.Auth]: Basic auth object for HTTPX client

        """
        return self._httpx_auth

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider.

        Returns:
            str: Name of the authentication provider

        """
        return 'basic'
