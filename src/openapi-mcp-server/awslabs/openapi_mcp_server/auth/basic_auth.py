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
from awslabs.openapi_mcp_server.auth.auth_cache import cached_auth_data
from awslabs.openapi_mcp_server.auth.auth_errors import MissingCredentialsError
from awslabs.openapi_mcp_server.auth.base_auth import BaseAuthProvider
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
        self._credentials_hash = None

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

        # Create a hash of the credentials for caching
        self._credentials_hash = self._hash_credentials(self._username, self._password)
        return True

    def _log_validation_error(self) -> None:
        """Log validation error messages."""
        logger.error(
            'Basic authentication requires both username and password. Please provide them using --auth-username and --auth-password command line arguments or AUTH_USERNAME and AUTH_PASSWORD environment variables.'
        )

    def _initialize_auth(self) -> None:
        """Initialize authentication data after validation."""
        # Use cached methods to generate auth data
        self._auth_headers = self._generate_auth_headers(self._credentials_hash)
        self._httpx_auth = self._generate_httpx_auth(self._username, self._password)

    @staticmethod
    def _hash_credentials(username: str, password: str) -> str:
        """Create a hash of the credentials for caching.

        Args:
            username: Username
            password: Password

        Returns:
            str: Hash of the credentials

        """
        # Create a hash of the credentials to use as a cache key
        # This avoids storing the actual credentials in the cache key
        # Using bcrypt for stronger security
        import bcrypt

        credentials = f'{username}:{password}'
        # Generate a salt and hash the credentials
        # We only need a string representation for caching, so we'll use the hexdigest of the hash
        hashed = bcrypt.hashpw(credentials.encode('utf-8'), bcrypt.gensalt(rounds=10))
        # Convert to hex string for consistent cache key format
        return hashed.hex()

    @cached_auth_data(ttl=3600)  # Cache for 1 hour by default
    def _generate_auth_headers(self, credentials_hash: str) -> Dict[str, str]:
        """Generate authentication headers.

        This method is cached to avoid regenerating headers for the same credentials.

        Args:
            credentials_hash: Hash of the credentials

        Returns:
            Dict[str, str]: Authentication headers

        """
        logger.debug(f'Generating new basic auth headers for user: {self._username}')

        # Create the basic auth header
        auth_string = f'{self._username}:{self._password}'
        auth_bytes = auth_string.encode('utf-8')
        encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')

        return {'Authorization': f'Basic {encoded_auth}'}

    @cached_auth_data(ttl=3600)  # Cache for 1 hour by default
    def _generate_httpx_auth(self, username: str, password: str) -> httpx.BasicAuth:
        """Generate HTTPX auth object.

        This method is cached to avoid regenerating auth objects for the same credentials.

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
