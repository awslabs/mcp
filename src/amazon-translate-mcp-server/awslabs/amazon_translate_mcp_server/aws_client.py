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

"""AWS Client Manager for Amazon Translate MCP Server.

This module provides centralized AWS client management with credential chain support,
session management, and connection pooling for Amazon Translate, S3, and CloudWatch services.
"""

import boto3
import logging
import os
import threading
from .consts import MCP_SERVER_VERSION
from .exceptions import (
    AuthenticationError,
    TranslateException,
    map_aws_error,
)
from .logging_config import LoggerMixin, get_correlation_id
from .retry_handler import TRANSLATION_RETRY_CONFIG, with_retry
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
    ProfileNotFound,
)
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class AWSClientManager(LoggerMixin):
    """Manages AWS service clients with credential chain support and connection pooling.

    This class provides centralized management of AWS clients for Amazon Translate,
    S3, and CloudWatch services. It handles credential validation, region configuration,
    session management, and implements connection pooling for optimal performance.
    """

    def __init__(
        self,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        max_pool_connections: int = 50,
        retries: int = 3,
        timeout: int = 60,
    ):
        """Initialize the AWS Client Manager.

        Args:
            region_name: AWS region name. If None, uses AWS_REGION env var or default region
            profile_name: AWS profile name. If None, uses AWS_PROFILE env var
            aws_access_key_id: AWS access key ID. If None, uses credential chain
            aws_secret_access_key: AWS secret access key. If None, uses credential chain
            aws_session_token: AWS session token for temporary credentials
            max_pool_connections: Maximum number of connections in the connection pool
            retries: Number of retry attempts for failed requests
            timeout: Request timeout in seconds

        """
        self._region_name = (
            region_name or os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION')
        )
        self._profile_name = profile_name or os.getenv('AWS_PROFILE')
        self._aws_access_key_id = aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self._aws_secret_access_key = aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self._aws_session_token = aws_session_token or os.getenv('AWS_SESSION_TOKEN')

        # Connection pool configuration
        self._config = Config(
            region_name=self._region_name,
            retries={'max_attempts': retries, 'mode': 'adaptive'},
            max_pool_connections=max_pool_connections,
            connect_timeout=timeout,
            read_timeout=timeout,
            user_agent_extra=f'awslabs/mcp/amazon-translate-mcp-server/{MCP_SERVER_VERSION}',
        )

        # Thread-safe client cache
        self._clients: Dict[str, Any] = {}
        self._session: Optional[boto3.Session] = None
        self._lock = threading.RLock()

        # Initialize session
        self._initialize_session()

    def _initialize_session(self) -> None:
        """Initialize the boto3 session with credential chain support."""
        try:
            session_kwargs = {}

            # Add profile if specified
            if self._profile_name:
                session_kwargs['profile_name'] = self._profile_name

            # Add explicit credentials if provided
            if self._aws_access_key_id and self._aws_secret_access_key:
                session_kwargs.update(
                    {
                        'aws_access_key_id': self._aws_access_key_id,
                        'aws_secret_access_key': self._aws_secret_access_key,
                    }
                )
                if self._aws_session_token:
                    session_kwargs['aws_session_token'] = self._aws_session_token

            # Add region if specified
            if self._region_name:
                session_kwargs['region_name'] = self._region_name

            self._session = boto3.Session(**session_kwargs)

            # Validate credentials by attempting to get caller identity
            self._validate_credentials()

            self.info(
                f'AWS session initialized successfully. Region: {self._session.region_name if self._session else "default"}, '
                f'Profile: {self._profile_name or "default"}'
            )

        except (NoCredentialsError, PartialCredentialsError) as e:
            correlation_id = get_correlation_id()
            self.error(
                f'AWS credentials not found or incomplete: {str(e)}', correlation_id=correlation_id
            )
            raise AuthenticationError(
                f'AWS credentials not found or incomplete: {str(e)}',
                details={'credential_source': 'credential_chain'},
                correlation_id=correlation_id,
            )
        except ProfileNotFound as e:
            correlation_id = get_correlation_id()
            self.error(
                f"AWS profile '{self._profile_name}' not found: {str(e)}",
                correlation_id=correlation_id,
            )
            raise AuthenticationError(
                f"AWS profile '{self._profile_name}' not found: {str(e)}",
                details={'profile_name': self._profile_name},
                correlation_id=correlation_id,
            )
        except AuthenticationError:
            # Re-raise AuthenticationError from _validate_credentials without modification
            raise
        except Exception as e:
            correlation_id = get_correlation_id()
            self.error(
                f'Failed to initialize AWS session: {str(e)}', correlation_id=correlation_id
            )
            raise map_aws_error(e, correlation_id)

    @with_retry(TRANSLATION_RETRY_CONFIG)
    def _validate_credentials(self, correlation_id: Optional[str] = None) -> None:
        """Validate AWS credentials by calling STS GetCallerIdentity."""
        correlation_id = correlation_id or get_correlation_id()

        if not self._session:
            raise AuthenticationError('AWS session not initialized', correlation_id=correlation_id)

        try:
            sts_client = self._session.client('sts', config=self._config)
            response = sts_client.get_caller_identity()

            self.debug(
                f'Credentials validated. Account: {response.get("Account", "unknown")}, '
                f'User: {response.get("Arn", "unknown")}',
                correlation_id=correlation_id,
            )

        except ClientError as e:
            self.error(f'Credential validation failed: {str(e)}', correlation_id=correlation_id)
            raise map_aws_error(e, correlation_id)
        except Exception as e:
            self.error(
                f'Unexpected error during credential validation: {str(e)}',
                correlation_id=correlation_id,
            )
            raise map_aws_error(e, correlation_id)

    def _get_client(self, service_name: str) -> Any:
        """Get or create a cached AWS service client.

        Args:
            service_name: Name of the AWS service (e.g., 'translate', 's3', 'cloudwatch')

        Returns:
            AWS service client instance

        Raises:
            AuthenticationError: If credentials are invalid
            ServiceUnavailableError: If service is unavailable

        """
        with self._lock:
            # Return cached client if available
            if service_name in self._clients:
                return self._clients[service_name]

            if not self._session:
                raise AuthenticationError('AWS session not initialized')

            try:
                # Create new client
                client = self._session.client(service_name, config=self._config)

                # Test client connectivity with a simple operation
                self._test_client_connectivity(service_name, client)

                # Cache the client
                self._clients[service_name] = client

                self.debug(f'Created and cached {service_name} client')
                return client

            except TranslateException:
                # Re-raise our custom exceptions without modification
                raise
            except Exception as e:
                correlation_id = get_correlation_id()
                self.error(
                    f'Failed to create {service_name} client: {str(e)}',
                    correlation_id=correlation_id,
                )
                # Create exception with service context
                exception = map_aws_error(e, correlation_id)
                # Add service context to details
                if hasattr(exception, 'details'):
                    exception.details['service'] = service_name
                raise exception

    def _test_client_connectivity(self, service_name: str, client: Any) -> None:
        """Test client connectivity with a simple operation.

        Args:
            service_name: Name of the AWS service
            client: AWS service client to test

        Raises:
            ServiceUnavailableError: If connectivity test fails

        """
        try:
            if service_name == 'translate':
                # Test with list_languages operation
                client.list_languages(DisplayLanguageCode='en', MaxResults=1)
            elif service_name == 's3':
                # Test with list_buckets operation
                client.list_buckets()
            elif service_name == 'cloudwatch':
                # Test with list_metrics operation (no parameters needed)
                client.list_metrics()
            elif service_name == 'comprehend':
                # Test with describe_dominant_language_detection_job operation (lightweight)
                # Actually, let's skip connectivity test for comprehend to avoid permission issues
                self.debug(f'Skipping connectivity test for {service_name} service')
            else:
                # For other services, skip connectivity test
                self.debug(f'Skipping connectivity test for {service_name} service')

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            if error_code in ['AccessDenied', 'UnauthorizedOperation']:
                # Permission issues will be handled when actual operations are called
                self.debug(
                    f'Skipping connectivity test for {service_name} due to permission issue: {error_message}'
                )
            else:
                # Only raise for actual connectivity/service issues
                correlation_id = get_correlation_id()
                self.error(
                    f'Connectivity test failed for {service_name}: {error_message}',
                    correlation_id=correlation_id,
                )
                # Create exception with service context
                exception = map_aws_error(e, correlation_id)
                # Add service context to details
                if hasattr(exception, 'details'):
                    exception.details['service'] = service_name
                raise exception

    def get_translate_client(self) -> Any:
        """Get Amazon Translate client.

        Returns:
            boto3 Translate client instance

        Raises:
            AuthenticationError: If credentials are invalid
            ServiceUnavailableError: If Translate service is unavailable

        """
        return self._get_client('translate')

    def get_comprehend_client(self) -> Any:
        """Get Amazon Comprehend client.

        Returns:
            boto3 Comprehend client instance

        Raises:
            AuthenticationError: If credentials are invalid
            ServiceUnavailableError: If Comprehend service is unavailable

        """
        return self._get_client('comprehend')

    def get_s3_client(self) -> Any:
        """Get Amazon S3 client.

        Returns:
            boto3 S3 client instance

        Raises:
            AuthenticationError: If credentials are invalid
            ServiceUnavailableError: If S3 service is unavailable

        """
        return self._get_client('s3')

    def get_cloudwatch_client(self) -> Any:
        """Get Amazon CloudWatch client.

        Returns:
            boto3 CloudWatch client instance

        Raises:
            AuthenticationError: If credentials are invalid
            ServiceUnavailableError: If CloudWatch service is unavailable

        """
        return self._get_client('cloudwatch')

    def validate_credentials(self) -> bool:
        """Validate current AWS credentials.

        Returns:
            True if credentials are valid, False otherwise

        """
        try:
            self._validate_credentials()
            return True
        except AuthenticationError:
            return False

    def refresh_credentials(self) -> None:
        """Refresh AWS credentials and clear client cache.

        This method reinitializes the session and clears all cached clients,
        forcing them to be recreated with fresh credentials.

        Raises:
            AuthenticationError: If credential refresh fails

        """
        with self._lock:
            # Clear cached clients
            self._clients.clear()

            # Reinitialize session
            self._initialize_session()

            self.info('AWS credentials refreshed successfully')

    def get_region(self) -> Optional[str]:
        """Get the current AWS region.

        Returns:
            Current AWS region name or None if not set

        """
        return self._session.region_name if self._session else None

    def get_account_id(self) -> Optional[str]:
        """Get the current AWS account ID.

        Returns:
            Current AWS account ID or None if unable to retrieve

        """
        if not self._session:
            return None

        try:
            sts_client = self._session.client('sts', config=self._config)
            response = sts_client.get_caller_identity()
            return response.get('Account')
        except Exception as e:
            self.warning(f'Failed to get account ID: {str(e)}')
            return None

    def get_user_arn(self) -> Optional[str]:
        """Get the current user/role ARN.

        Returns:
            Current user/role ARN or None if unable to retrieve

        """
        if not self._session:
            return None

        try:
            sts_client = self._session.client('sts', config=self._config)
            response = sts_client.get_caller_identity()
            return response.get('Arn')
        except Exception as e:
            self.warning(f'Failed to get user ARN: {str(e)}')
            return None

    def close(self) -> None:
        """Close all cached clients and clean up resources.

        This method should be called when the client manager is no longer needed
        to ensure proper cleanup of resources.
        """
        with self._lock:
            # Clear all cached clients
            self._clients.clear()
            self._session = None

            self.debug('AWS client manager closed and resources cleaned up')

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
