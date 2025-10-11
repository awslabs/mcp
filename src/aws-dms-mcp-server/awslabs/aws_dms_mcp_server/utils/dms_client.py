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

"""DMS Client wrapper for boto3.

Provides centralized AWS DMS client management with retry logic,
error handling, and read-only mode enforcement.
"""

import boto3
from ..config import DMSServerConfig
from ..exceptions import AWS_ERROR_MAP, DMSMCPException, DMSReadOnlyModeException
from botocore.exceptions import ClientError
from loguru import logger
from typing import Any, Dict


class DMSClient:
    """Wrapper for boto3 DMS client with enhanced error handling."""

    # Read-only operations that are always allowed
    READ_ONLY_OPERATIONS = {
        'describe_replication_instances',
        'describe_endpoints',
        'describe_replication_tasks',
        'describe_table_statistics',
        'describe_connections',
        'test_connection',  # Test connection is considered read-only
    }

    def __init__(self, config: DMSServerConfig):
        """Initialize DMS client.

        Args:
            config: Server configuration
        """
        self.config = config
        self._client = None

        logger.info(
            'Initializing DMS client', region=config.aws_region, read_only=config.read_only_mode
        )

    def get_client(self) -> Any:
        """Get or create boto3 DMS client.

        Returns:
            Configured boto3 DMS client
        """
        if self._client is None:
            from botocore.config import Config

            # Configure retry logic with exponential backoff
            retry_config = Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                connect_timeout=self.config.default_timeout,
                read_timeout=self.config.default_timeout,
            )

            # Create session with optional profile
            if self.config.aws_profile:
                session = boto3.Session(profile_name=self.config.aws_profile)
                self._client = session.client(
                    'dms', region_name=self.config.aws_region, config=retry_config
                )
            else:
                self._client = boto3.client(
                    'dms', region_name=self.config.aws_region, config=retry_config
                )

            logger.debug(
                'Created boto3 DMS client',
                region=self.config.aws_region,
                timeout=self.config.default_timeout,
            )

        return self._client

    def call_api(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Call DMS API operation with error handling and logging.

        Args:
            operation: DMS API operation name
            **kwargs: Operation parameters

        Returns:
            API response dictionary

        Raises:
            DMSReadOnlyModeException: Operation not allowed in read-only mode
            DMSMCPException: API call failed
        """
        # Check read-only mode
        if self.config.read_only_mode and not self.is_read_only_operation(operation):
            raise DMSReadOnlyModeException(operation)

        logger.info('Calling DMS API', operation=operation, params=kwargs)

        try:
            client = self.get_client()

            # Get the operation method from the client
            operation_method = getattr(client, operation)

            # Call the API with provided parameters
            response = operation_method(**kwargs)

            # Log successful response
            logger.debug(
                'DMS API call successful',
                operation=operation,
                response_metadata=response.get('ResponseMetadata', {}),
            )

            return response

        except ClientError as e:
            # Translate AWS error to custom exception
            exception = self.translate_error(e)
            logger.error('DMS API call failed', operation=operation, error=str(exception))
            raise exception

    def is_read_only_operation(self, operation: str) -> bool:
        """Check if operation is read-only.

        Args:
            operation: Operation name

        Returns:
            True if operation is read-only
        """
        return operation in self.READ_ONLY_OPERATIONS

    def translate_error(self, error: ClientError) -> DMSMCPException:
        """Translate AWS SDK error to custom exception.

        Args:
            error: boto3 ClientError

        Returns:
            Custom DMSMCPException
        """
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', 'Unknown error')
        request_id = error.response.get('ResponseMetadata', {}).get('RequestId')

        exception_class = AWS_ERROR_MAP.get(error_code, DMSMCPException)

        return exception_class(
            message=f'DMS API Error: {error_message}',
            details={
                'error_code': error_code,
                'aws_request_id': request_id,
            },
        )


# TODO: Implement exponential backoff retry logic
# TODO: Add connection pooling for performance
# TODO: Add metrics collection for API calls
