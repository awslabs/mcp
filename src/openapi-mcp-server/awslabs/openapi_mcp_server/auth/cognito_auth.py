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
"""Cognito User Pool authentication provider."""

import boto3
import threading
import time
from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.api.config import Config
from awslabs.openapi_mcp_server.auth.auth_errors import (
    ConfigurationError,
    ExpiredTokenError,
    InvalidCredentialsError,
    MissingCredentialsError,
    NetworkError,
)
from awslabs.openapi_mcp_server.auth.bearer_auth import BearerAuthProvider
from typing import Dict, Optional


class CognitoAuthProvider(BearerAuthProvider):
    """Cognito User Pool authentication provider.

    This provider obtains ID tokens from AWS Cognito User Pools
    and delegates to BearerAuthProvider for adding Authorization headers
    to all HTTP requests.
    """

    def __init__(self, config: Config):
        """Initialize with configuration.

        Args:
            config: Application configuration

        """
        # Store Cognito-specific configuration
        self._client_id = config.auth_cognito_client_id
        self._username = config.auth_cognito_username
        self._password = config.auth_cognito_password
        self._user_pool_id = config.auth_cognito_user_pool_id
        self._region = config.auth_cognito_region

        # Add debug log early in initialization
        logger.debug(
            f'Cognito auth configuration: Username={self._username}, ClientID={self._client_id}, '
            f'Password={"SET" if self._password else "NOT SET"}, UserPoolID={self._user_pool_id or "NOT SET"}'
        )

        # Token management
        self._token_expires_at = 0
        self._refresh_token_value = None
        self._token_lock = threading.RLock()  # For thread safety

        # Get initial token before parent initialization
        try:
            # Only try to get token if we have the minimum required credentials
            if self._client_id and self._username and self._password:
                token = self._get_cognito_token()
                if token:
                    # Set token in config for parent class to use
                    config.auth_token = token
            else:
                logger.warning(
                    'Missing required Cognito credentials, skipping initial token acquisition'
                )
        except Exception as e:
            logger.warning(f'Failed to get initial Cognito token: {e}')
            # We'll let the parent validation handle this error

        # Call parent initializer which will validate and initialize auth
        # This will set self._token from config.auth_token
        super().__init__(config)

    def _validate_config(self) -> bool:
        """Validate the configuration.

        Returns:
            bool: True if all required parameters are provided, False otherwise

        Raises:
            MissingCredentialsError: If required parameters are missing
            ConfigurationError: If configuration is invalid

        """
        # Validate required parameters
        if not self._client_id:
            raise MissingCredentialsError(
                'Cognito authentication requires a client ID',
                {
                    'help': 'Provide client ID using --auth-cognito-client-id command line argument or AUTH_COGNITO_CLIENT_ID environment variable'
                },
            )

        if not self._username:
            raise MissingCredentialsError(
                'Cognito authentication requires a username',
                {
                    'help': 'Provide username using --auth-cognito-username command line argument or AUTH_COGNITO_USERNAME environment variable'
                },
            )

        if not self._password:
            raise MissingCredentialsError(
                'Cognito authentication requires a password',
                {
                    'help': 'Provide password using --auth-cognito-password command line argument or AUTH_COGNITO_PASSWORD environment variable'
                },
            )

        # Let parent class validate the token
        return super()._validate_config()

    def _log_validation_error(self) -> None:
        """Log validation error messages."""
        logger.error('Cognito authentication requires client ID, username, and password.')
        logger.error(
            'Please provide client ID using --auth-cognito-client-id, username using --auth-cognito-username, '
            'and password using --auth-cognito-password command line arguments or corresponding environment variables.'
        )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with auto-refresh.

        Returns:
            Dict[str, str]: Authentication headers

        """
        # Check if token needs refreshing and refresh if necessary
        self._check_and_refresh_token_if_needed()

        # Delegate to parent class for header generation
        return super().get_auth_headers()

    def _check_and_refresh_token_if_needed(self) -> None:
        """Check if token needs refreshing and refresh if necessary."""
        with self._token_lock:
            if self._is_token_expired_or_expiring_soon():
                self._refresh_token()

    def _is_token_expired_or_expiring_soon(self) -> bool:
        """Check if token is expired or will expire soon.

        Returns:
            bool: True if token is expired or will expire soon, False otherwise

        """
        # Add buffer time (5 minutes) to refresh before actual expiration
        buffer_seconds = 300
        return time.time() + buffer_seconds >= self._token_expires_at

    def _refresh_token(self) -> None:
        """Refresh the token if possible, or re-authenticate.

        Logs at INFO level when token is refreshed.
        """
        try:
            old_token = self._token
            new_token = None

            # Try using refresh token if available
            if self._refresh_token_value:
                logger.debug(f'Attempting to refresh Cognito token for user: {self._username}')
                new_token = self._refresh_cognito_token()

            # If refresh failed or no refresh token available, re-authenticate
            if not new_token:
                logger.debug(f'Re-authenticating Cognito user: {self._username}')
                new_token = self._get_cognito_token()

            # Update token if we got a new one
            if new_token and new_token != old_token:
                self._token = new_token
                logger.info(f'Cognito token refreshed for user: {self._username}')

                # Force parent class to regenerate auth headers with new token
                self._initialize_auth()
            else:
                logger.debug('Token refresh did not result in a new token')

        except Exception as e:
            logger.error(f'Failed to refresh token: {e}')
            raise ExpiredTokenError('Token refresh failed', {'error': str(e)})

    def _get_cognito_token(self) -> Optional[str]:
        """Get a new token from Cognito using username/password.

        Returns:
            str: Cognito ID token or None if authentication fails

        Raises:
            AuthenticationError: If authentication fails

        """
        client = boto3.client('cognito-idp', region_name=self._region)

        try:
            logger.debug(f'Authenticating with Cognito for user: {self._username}')

            # Log parameters for debugging (without sensitive info)
            logger.debug(f'Initiating auth with ClientId: {self._client_id}')
            logger.debug('AuthFlow: USER_PASSWORD_AUTH')
            logger.debug(f'USERNAME parameter provided: {self._username}')
            logger.debug(
                f'PASSWORD parameter provided: {"*" * (len(self._password) if self._password else 0)}'
            )

            # Add clear confirmation of required variables
            logger.debug(
                f'Cognito auth configuration: Username={self._username}, ClientID={self._client_id}, Password={"SET" if self._password else "NOT SET"}'
            )

            # Try with different parameter formats
            # Format 1: Standard format
            auth_params = {'USERNAME': self._username, 'PASSWORD': self._password}

            # Add user pool ID if provided (some configurations might require this)
            if self._user_pool_id:
                logger.debug(f'User pool ID provided: {self._user_pool_id}')
                # Some Cognito configurations might use this format
                auth_params['UserPoolId'] = self._user_pool_id

            # Try with USER_PASSWORD_AUTH flow first
            try:
                logger.debug('Trying USER_PASSWORD_AUTH flow')
                response = client.initiate_auth(
                    ClientId=self._client_id,
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters=auth_params,
                )
            except client.exceptions.InvalidParameterException:
                # If USER_PASSWORD_AUTH fails, try ADMIN_USER_PASSWORD_AUTH flow
                # This requires user pool ID
                if self._user_pool_id:
                    logger.debug('USER_PASSWORD_AUTH failed, trying ADMIN_USER_PASSWORD_AUTH flow')
                    logger.debug(f'Using user pool ID: {self._user_pool_id}')

                    # ADMIN_USER_PASSWORD_AUTH requires admin credentials
                    # This will use the AWS credentials from the environment
                    response = client.admin_initiate_auth(
                        UserPoolId=self._user_pool_id,
                        ClientId=self._client_id,
                        AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                        AuthParameters={'USERNAME': self._username, 'PASSWORD': self._password},
                    )
                else:
                    # Re-raise the original exception if we can't try ADMIN_USER_PASSWORD_AUTH
                    logger.error(
                        'USER_PASSWORD_AUTH failed and no user pool ID provided for ADMIN_USER_PASSWORD_AUTH'
                    )
                    raise

            auth_result = response.get('AuthenticationResult', {})

            # Store the refresh token
            self._refresh_token_value = auth_result.get('RefreshToken')

            # Extract token expiry from ID token
            id_token = auth_result.get('IdToken')
            if id_token:
                self._token_expires_at = self._extract_token_expiry(id_token)

            # Get the ID token
            id_token = auth_result.get('IdToken')
            if id_token:
                # Extract token expiry
                self._token_expires_at = self._extract_token_expiry(id_token)

                # Log token acquisition at INFO level
                logger.info(f'Obtained new Cognito ID token for user: {self._username}')

                # Log token length for debugging
                token_length = len(id_token) if id_token else 0
                logger.debug(f'Token length: {token_length} characters')

                return id_token
            else:
                logger.error('No ID token found in authentication result')
                return None

        except client.exceptions.NotAuthorizedException as e:
            logger.error(f'Authentication failed: {e}')
            logger.error('Please check your Cognito credentials (client ID, username, password)')
            logger.error(
                'Make sure the user exists in the Cognito User Pool and the password is correct'
            )
            raise InvalidCredentialsError(
                'Invalid Cognito credentials',
                {
                    'error': str(e),
                    'help': 'Check your Cognito credentials and ensure the user exists in the User Pool',
                },
            )
        except client.exceptions.UserNotConfirmedException as e:
            logger.error(f'User not confirmed: {e}')
            logger.error('The user exists but has not been confirmed in the Cognito User Pool')
            logger.error(
                'Please confirm the user in the AWS Console or use the AWS CLI to confirm the user'
            )
            raise ConfigurationError(
                'User not confirmed',
                {
                    'error': str(e),
                    'help': 'Confirm the user in the AWS Console or use the AWS CLI',
                },
            )
        except client.exceptions.InvalidParameterException as e:
            logger.error(f'Invalid parameter: {e}')
            # Check if the error message contains information about which parameter is missing
            error_msg = str(e)
            if 'Missing required parameter' in error_msg:
                logger.error('Missing required parameter for Cognito authentication')
                logger.error(f'Client ID: {self._client_id}')
                logger.error(f'Username provided: {bool(self._username)}')
                logger.error(f'Password provided: {bool(self._password)}')
                logger.error(f'User Pool ID provided: {bool(self._user_pool_id)}')

                # Check specific parameters
                if not self._client_id:
                    raise MissingCredentialsError(
                        'Missing Cognito client ID',
                        {
                            'error': error_msg,
                            'help': 'Provide client ID using --auth-cognito-client-id or AUTH_COGNITO_CLIENT_ID',
                        },
                    )
                elif not self._username:
                    raise MissingCredentialsError(
                        'Missing Cognito username',
                        {
                            'error': error_msg,
                            'help': 'Provide username using --auth-cognito-username or AUTH_COGNITO_USERNAME',
                        },
                    )
                elif not self._password:
                    raise MissingCredentialsError(
                        'Missing Cognito password',
                        {
                            'error': error_msg,
                            'help': 'Provide password using --auth-cognito-password or AUTH_COGNITO_PASSWORD',
                        },
                    )
                elif not self._user_pool_id:
                    logger.error('User Pool ID might be required for this Cognito configuration')
                    raise ConfigurationError(
                        'Missing User Pool ID for Cognito authentication',
                        {
                            'error': error_msg,
                            'help': 'Provide User Pool ID using --auth-cognito-user-pool-id or AUTH_COGNITO_USER_POOL_ID',
                        },
                    )
                else:
                    raise ConfigurationError(
                        'Missing required parameter for Cognito authentication',
                        {
                            'error': error_msg,
                            'help': 'Check the error message for details on which parameter is missing',
                        },
                    )
            else:
                raise ConfigurationError(
                    f'Invalid parameter for Cognito authentication: {error_msg}',
                    {
                        'error': error_msg,
                        'help': 'Check the error message for details on which parameter is invalid',
                    },
                )
        except client.exceptions.ResourceNotFoundException as e:
            logger.error(f'Resource not found: {e}')
            logger.error('The specified Cognito User Pool or Client ID does not exist')
            raise ConfigurationError(
                'Cognito resource not found',
                {'error': str(e), 'help': 'Check your User Pool ID and Client ID'},
            )
        except Exception as e:
            logger.error(f'Cognito authentication error: {e}')
            logger.error(
                'This could be due to network issues, AWS credentials, or Cognito configuration'
            )
            raise NetworkError(
                'Cognito authentication failed',
                {'error': str(e), 'help': 'Check your network connection and AWS credentials'},
            )

    def _refresh_cognito_token(self) -> Optional[str]:
        """Refresh the Cognito token using the refresh token.

        Returns:
            str: New Cognito ID token or None if refresh fails

        Raises:
            AuthenticationError: If token refresh fails

        """
        client = boto3.client('cognito-idp', region_name=self._region)

        try:
            logger.debug(f'Refreshing token for user: {self._username}')

            # Try with standard REFRESH_TOKEN_AUTH flow first
            try:
                logger.debug('Trying REFRESH_TOKEN_AUTH flow')
                response = client.initiate_auth(
                    ClientId=self._client_id,
                    AuthFlow='REFRESH_TOKEN_AUTH',
                    AuthParameters={'REFRESH_TOKEN': self._refresh_token_value},
                )
            except client.exceptions.InvalidParameterException:
                # If REFRESH_TOKEN_AUTH fails, try ADMIN_REFRESH_TOKEN_AUTH flow
                # This requires user pool ID
                if self._user_pool_id:
                    logger.debug('REFRESH_TOKEN_AUTH failed, trying ADMIN_REFRESH_TOKEN_AUTH flow')
                    logger.debug(f'Using user pool ID: {self._user_pool_id}')

                    # ADMIN_REFRESH_TOKEN_AUTH requires admin credentials
                    # This will use the AWS credentials from the environment
                    response = client.admin_initiate_auth(
                        UserPoolId=self._user_pool_id,
                        ClientId=self._client_id,
                        AuthFlow='REFRESH_TOKEN',
                        AuthParameters={'REFRESH_TOKEN': self._refresh_token_value},
                    )
                else:
                    # Re-raise the original exception if we can't try ADMIN_REFRESH_TOKEN_AUTH
                    logger.error(
                        'REFRESH_TOKEN_AUTH failed and no user pool ID provided for ADMIN_REFRESH_TOKEN_AUTH'
                    )
                    raise

            auth_result = response.get('AuthenticationResult', {})

            # Extract token expiry from ID token
            id_token = auth_result.get('IdToken')
            if id_token:
                self._token_expires_at = self._extract_token_expiry(id_token)

            # Get the ID token
            id_token = auth_result.get('IdToken')
            if id_token:
                # Extract token expiry
                self._token_expires_at = self._extract_token_expiry(id_token)

                # Log token refresh at INFO level
                logger.info(f'Successfully refreshed Cognito ID token for user: {self._username}')

                # Log token length for debugging
                token_length = len(id_token) if id_token else 0
                logger.debug(f'Token length: {token_length} characters')

                return id_token
            else:
                logger.error('No ID token found in refresh result')
                return None

        except client.exceptions.NotAuthorizedException:
            logger.warning('Refresh token expired, falling back to re-authentication')
            return None  # Will trigger a full re-authentication
        except Exception as e:
            logger.error(f'Token refresh error: {e}')
            return None  # Will trigger a full re-authentication

    def _extract_token_expiry(self, token: str) -> int:
        """Extract expiry timestamp from token.

        Args:
            token: JWT token

        Returns:
            int: Expiry timestamp

        """
        try:
            # Parse the JWT token without using the decode function
            # JWT tokens are in the format: header.payload.signature
            # We only need the payload part to extract the expiry
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError('Invalid JWT token format')

            # The payload is base64url encoded
            # Add padding if needed
            payload = parts[1]
            padding = '=' * ((4 - len(payload) % 4) % 4)  # Fix padding calculation

            # Replace URL-safe characters and decode
            payload = payload.replace('-', '+').replace('_', '/') + padding

            try:
                import base64

                decoded_payload = base64.b64decode(payload).decode('utf-8')
                import json

                payload_data = json.loads(decoded_payload)
                exp_time = payload_data.get('exp', 0)

                # Log the expiry duration at INFO level
                if exp_time > 0:
                    current_time = int(time.time())
                    duration_seconds = exp_time - current_time
                    duration_minutes = duration_seconds / 60
                    duration_hours = duration_minutes / 60

                    if duration_seconds > 0:
                        logger.info(
                            f'Token expires in {duration_hours:.2f} hours ({duration_minutes:.0f} minutes)'
                        )
                    else:
                        logger.info(f'Token is already expired by {-duration_seconds} seconds')

                return exp_time
            except Exception as e:
                logger.warning(f'Failed to decode payload: {e}')
                raise
        except Exception as e:
            logger.warning(f'Failed to extract token expiry: {e}')
            # Default to 1 hour from now if extraction fails
            return int(time.time()) + 3600

    @property
    def provider_name(self) -> str:
        """Get the name of the authentication provider.

        Returns:
            str: Name of the authentication provider

        """
        return 'cognito'
