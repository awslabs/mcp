"""Cognito User Pool authentication provider."""

import boto3
import jwt
import os
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
from typing import Dict


class CognitoAuthProvider(BearerAuthProvider):
    """Cognito User Pool authentication provider.

    This provider obtains tokens from AWS Cognito User Pools
    and adds an Authorization header with a Bearer token
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

        # Try to get password from env var if not in config
        self._password = config.auth_cognito_password or os.environ.get('AUTH_COGNITO_PASSWORD')

        self._user_pool_id = config.auth_cognito_user_pool_id
        self._region = config.auth_cognito_region or 'us-east-1'

        # Add debug log early in initialization
        logger.debug(
            f'Cognito auth configuration: Username={self._username}, ClientID={self._client_id}, Password={"SET" if self._password else "NOT SET"}, UserPoolID={self._user_pool_id or "NOT SET"}'
        )

        # Token management
        self._token = None
        self._token_expires_at = 0
        self._refresh_token_value = None
        self._token_lock = threading.RLock()  # For thread safety

        # Call parent initializer which will validate and initialize auth
        super().__init__(config)

        # If validation passed, get the token
        if self.is_configured():
            config.auth_token = self._get_cognito_token()

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

        # Validate token
        if not self._token:
            raise InvalidCredentialsError(
                'Failed to obtain Cognito token',
                {'help': 'Check your Cognito credentials and try again'},
            )

        return True

    def _log_validation_error(self) -> None:
        """Log validation error messages."""
        logger.error('Cognito authentication requires client ID, username, and password.')
        logger.error(
            'Please provide client ID using --auth-cognito-client-id, username using --auth-cognito-username, and password using --auth-cognito-password command line arguments or corresponding environment variables.'
        )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with auto-refresh.

        Returns:
            Dict[str, str]: Authentication headers

        """
        with self._token_lock:
            if self._is_token_expired_or_expiring_soon():
                self._refresh_token()

        return super().get_auth_headers()

    def _is_token_expired_or_expiring_soon(self) -> bool:
        """Check if token is expired or will expire soon.

        Returns:
            bool: True if token is expired or will expire soon, False otherwise

        """
        # Add buffer time (5 minutes) to refresh before actual expiration
        buffer_seconds = 300
        return time.time() + buffer_seconds >= self._token_expires_at

    def _refresh_token(self) -> None:
        """Refresh the token if possible, or re-authenticate."""
        try:
            # Try using refresh token if available
            if self._refresh_token_value:
                logger.debug(f'Refreshing Cognito token for user: {self._username}')
                self._token = self._refresh_cognito_token()
            else:
                # Otherwise re-authenticate with username/password
                logger.debug(f'Re-authenticating Cognito user: {self._username}')
                self._token = self._get_cognito_token()

            # Update auth headers with new token
            self._auth_headers = self._generate_auth_headers(self._token)

        except Exception as e:
            logger.error(f'Failed to refresh token: {e}')
            raise ExpiredTokenError('Token refresh failed', {'error': str(e)})

    def _get_cognito_token(self) -> str:
        """Get a new token from Cognito using username/password.

        Returns:
            str: Cognito access token

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

            # Log token length for debugging
            access_token = auth_result.get('AccessToken')
            token_length = len(access_token) if access_token else 0
            logger.debug(f'Obtained Cognito token, length: {token_length} characters')

            # Return the access token
            return access_token

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

    def _refresh_cognito_token(self) -> str:
        """Refresh the Cognito token using the refresh token.

        Returns:
            str: New Cognito access token

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

            # Log token length for debugging
            access_token = auth_result.get('AccessToken')
            token_length = len(access_token) if access_token else 0
            logger.debug(f'Refreshed Cognito token, length: {token_length} characters')

            # Return the new access token
            return access_token

        except client.exceptions.NotAuthorizedException:
            logger.warning('Refresh token expired, re-authenticating...')
            return self._get_cognito_token()  # Fall back to full auth
        except Exception as e:
            logger.error(f'Token refresh error: {e}')
            raise ExpiredTokenError('Token refresh failed', {'error': str(e)})

    def _extract_token_expiry(self, token: str) -> int:
        """Extract expiry timestamp from token.

        Args:
            token: JWT token

        Returns:
            int: Expiry timestamp

        """
        try:
            # Decode the token without verification to extract the expiry
            # This is safe because we're not using the token for authentication here
            # Use an empty key since we're not verifying the signature
            # Disable all verification options since we just want to extract the expiry
            decoded = jwt.decode(
                token,
                key='',
                options={
                    'verify_signature': False,
                    'verify_aud': False,
                    'verify_iat': False,
                    'verify_exp': False,
                    'verify_nbf': False,
                    'verify_iss': False,
                    'verify_sub': False,
                    'verify_jti': False,
                    'verify_at_hash': False,
                },
            )
            return decoded.get('exp', 0)
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
