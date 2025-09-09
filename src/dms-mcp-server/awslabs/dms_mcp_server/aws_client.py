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

"""AWS client utilities for Database Migration Service MCP Server."""

import boto3
import os
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from loguru import logger
from typing import Optional


def get_aws_region() -> str:
    """Get AWS region from environment or default to us-east-1."""
    from awslabs.dms_mcp_server.consts import DEFAULT_AWS_REGION, ENV_VARS

    return os.getenv(ENV_VARS['AWS_REGION'], os.getenv('AWS_DEFAULT_REGION', DEFAULT_AWS_REGION))


def get_dms_client(region: Optional[str] = None):
    """Create and return a DMS boto3 client.

    Args:
        region: AWS region to use. If None, uses environment or defaults to us-east-1

    Returns:
        boto3 DMS client

    Raises:
        NoCredentialsError: If AWS credentials are not available
        PartialCredentialsError: If AWS credentials are incomplete
    """
    try:
        if region is None:
            region = get_aws_region()

        # Create config with retry settings optimized for DMS operations
        config = Config(
            region_name=region,
            retries={'max_attempts': 10, 'mode': 'adaptive'},
            max_pool_connections=50,
        )

        client = boto3.client('dms', config=config)

        # Test the client by making a simple call
        client.describe_account_attributes()

        logger.debug(f'Successfully created DMS client for region: {region}')
        return client

    except NoCredentialsError:
        logger.error('AWS credentials not found. Please configure your AWS credentials.')
        raise
    except PartialCredentialsError:
        logger.error(
            'Partial AWS credentials found. Please ensure all required credentials are provided.'
        )
        raise
    except ClientError as e:
        logger.error(f'Failed to create DMS client: {e}')
        raise
    except Exception as e:
        logger.error(f'Unexpected error creating DMS client: {e}')
        raise


def get_ec2_client(region: Optional[str] = None):
    """Create and return an EC2 boto3 client (used for VPC/subnet operations).

    Args:
        region: AWS region to use. If None, uses environment or defaults to us-east-1

    Returns:
        boto3 EC2 client
    """
    try:
        if region is None:
            region = get_aws_region()

        config = Config(region_name=region, retries={'max_attempts': 10, 'mode': 'adaptive'})

        client = boto3.client('ec2', config=config)
        logger.debug(f'Successfully created EC2 client for region: {region}')
        return client

    except Exception as e:
        logger.error(f'Failed to create EC2 client: {e}')
        raise


def get_sns_client(region: Optional[str] = None):
    """Create and return an SNS boto3 client (used for event notifications).

    Args:
        region: AWS region to use. If None, uses environment or defaults to us-east-1

    Returns:
        boto3 SNS client
    """
    try:
        if region is None:
            region = get_aws_region()

        config = Config(region_name=region, retries={'max_attempts': 10, 'mode': 'adaptive'})

        client = boto3.client('sns', config=config)
        logger.debug(f'Successfully created SNS client for region: {region}')
        return client

    except Exception as e:
        logger.error(f'Failed to create SNS client: {e}')
        raise


def handle_aws_error(e: Exception) -> str:
    """Handle AWS errors and return a user-friendly error message.

    Args:
        e: The exception that was raised

    Returns:
        str: User-friendly error message
    """
    if isinstance(e, ClientError):
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        # Map common DMS error codes to user-friendly messages
        error_mappings = {
            'InvalidResourceStateFault': 'Resource is in an invalid state for this operation',
            'ResourceNotFoundFault': 'The requested resource was not found',
            'ResourceQuotaExceededFault': 'Resource quota has been exceeded',
            'ResourceAlreadyExistsFault': 'Resource already exists',
            'InsufficientResourceCapacityFault': 'Insufficient resource capacity',
            'AccessDeniedFault': 'Access denied - check your permissions',
            'KMSKeyNotAccessibleFault': 'KMS key is not accessible',
            'InvalidParameterValueException': 'Invalid parameter value provided',
            'InvalidParameterCombinationException': 'Invalid combination of parameters',
            'UnauthorizedOperation': 'Unauthorized operation - check your permissions',
            'InvalidSubnet': 'Invalid subnet specified',
            'InvalidVpcID': 'Invalid VPC ID specified',
        }

        friendly_message = error_mappings.get(error_code, f'AWS Error ({error_code})')
        return f'{friendly_message}: {error_message}'

    elif isinstance(e, NoCredentialsError):
        return 'AWS credentials not found. Please configure your AWS credentials.'

    elif isinstance(e, PartialCredentialsError):
        return 'Incomplete AWS credentials. Please ensure all required credentials are provided.'

    else:
        return f'Unexpected error: {str(e)}'


def validate_aws_credentials() -> bool:
    """Validate that AWS credentials are properly configured.

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    try:
        # Try to get the caller identity to validate credentials
        sts_client = boto3.client('sts')
        sts_client.get_caller_identity()
        logger.debug('AWS credentials validation successful')
        return True
    except Exception as e:
        logger.error(f'AWS credentials validation failed: {e}')
        return False
