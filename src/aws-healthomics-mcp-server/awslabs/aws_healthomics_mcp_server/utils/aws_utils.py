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

"""AWS utility functions for the HealthOmics MCP server."""

import base64
import boto3
import botocore.session
import io
import os
import zipfile
from awslabs.aws_healthomics_mcp_server import __version__
from awslabs.aws_healthomics_mcp_server.consts import (
    AGENT_ENV,
    DEFAULT_OMICS_SERVICE_NAME,
    DEFAULT_REGION,
)
from functools import lru_cache
from loguru import logger
from typing import Any, Dict


def get_region() -> str:
    """Get the AWS region from environment variable or default.

    Returns:
        str: AWS region name
    """
    return os.environ.get('AWS_REGION', DEFAULT_REGION)


def get_omics_service_name() -> str:
    """Get the HealthOmics service name from environment variable or default.

    Returns:
        str: HealthOmics service name
    """
    service_name = os.environ.get('HEALTHOMICS_SERVICE_NAME', DEFAULT_OMICS_SERVICE_NAME)

    # Check if service name is empty or only whitespace
    if not service_name or not service_name.strip():
        logger.warning(
            'HEALTHOMICS_SERVICE_NAME environment variable is empty or contains only whitespace. '
            f'Using default service name: {DEFAULT_OMICS_SERVICE_NAME}'
        )
        return DEFAULT_OMICS_SERVICE_NAME

    return service_name.strip()


def get_omics_endpoint_url() -> str | None:
    """Get the HealthOmics service endpoint URL from environment variable.

    Returns:
        str | None: HealthOmics endpoint URL if valid, None otherwise
    """
    endpoint_url = os.environ.get('HEALTHOMICS_ENDPOINT_URL')

    # If environment variable is not set, return None (no warning needed)
    if endpoint_url is None:
        return None

    endpoint_url = endpoint_url.strip()

    # Check if endpoint URL is empty or only whitespace
    if not endpoint_url:
        logger.warning(
            'HEALTHOMICS_ENDPOINT_URL environment variable is empty or contains only whitespace. '
            'Using default endpoint.'
        )
        return None

    # Validate that endpoint URL starts with http:// or https://
    if not (endpoint_url.startswith('http://') or endpoint_url.startswith('https://')):
        logger.warning(
            f'HEALTHOMICS_ENDPOINT_URL environment variable "{endpoint_url}" must begin with '
            'http:// or https://. Using default endpoint.'
        )
        return None

    return endpoint_url


def get_agent_value() -> str | None:
    """Get the agent identifier from the AGENT environment variable.

    Reads the value, strips whitespace, sanitizes by removing characters
    not permitted in HTTP header values (outside visible ASCII 0x20-0x7E),
    and returns None if the result is empty.

    Returns:
        str | None: The sanitized agent value if valid, None otherwise.
    """
    raw = os.environ.get(AGENT_ENV)
    if raw is None:
        return None

    stripped = raw.strip()
    if not stripped:
        return None

    sanitized = ''.join(c for c in stripped if 0x20 <= ord(c) <= 0x7E)

    if not sanitized:
        logger.warning(
            f'{AGENT_ENV} environment variable value became empty after sanitization. '
            'Treating as unset.'
        )
        return None

    return sanitized


def get_aws_session(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> boto3.Session:
    """Get an AWS session with the centralized region configuration.

    Args:
        region_name: Optional region override. If not specified, falls back to
            AWS_REGION environment variable or default region.
        profile_name: Optional AWS profile override. If not specified, falls back to
            the default credential chain.

    Returns:
        boto3.Session: Configured AWS session

    Raises:
        ImportError: If boto3 is not available
    """
    # Handle FieldInfo objects from Pydantic (FastMCP compatibility)
    if not isinstance(region_name, (str, type(None))):
        region_name = None
    if not isinstance(profile_name, (str, type(None))):
        profile_name = None

    botocore_session = botocore.session.Session()
    user_agent_extra = f'md/awslabs#mcp#aws-healthomics-mcp-server#{__version__}'

    agent_value = get_agent_value()
    if agent_value:
        user_agent_extra += f' agent/{agent_value.lower()}'

    botocore_session.user_agent_extra = user_agent_extra

    kwargs: dict[str, Any] = {
        'region_name': region_name or get_region(),
        'botocore_session': botocore_session,
    }
    if profile_name:
        kwargs['profile_name'] = profile_name

    return boto3.Session(**kwargs)


def create_zip_file(files: Dict[str, str]) -> bytes:
    """Create a ZIP file in memory from a dictionary of files.

    Args:
        files: Dictionary mapping filenames to file contents

    Returns:
        bytes: ZIP file content as bytes
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files.items():
            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.read()


def encode_to_base64(data: bytes) -> str:
    """Encode bytes to base64 string.

    Args:
        data: Bytes to encode

    Returns:
        str: Base64-encoded string
    """
    return base64.b64encode(data).decode('utf-8')


def decode_from_base64(data: str) -> bytes:
    """Decode base64 string to bytes.

    Args:
        data: Base64-encoded string

    Returns:
        bytes: Decoded bytes
    """
    return base64.b64decode(data)


def create_aws_client(
    service_name: str,
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Generic AWS client factory for any service.

    Args:
        service_name: Name of the AWS service (e.g., 'omics', 'logs', 's3')
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured AWS service client

    Raises:
        Exception: If client creation fails
    """
    session = get_aws_session(region_name=region_name, profile_name=profile_name)
    try:
        return session.client(service_name)
    except Exception as e:
        logger.error(
            f'Failed to create {service_name} client in region {region_name or get_region()}: {str(e)}'
        )
        raise


def get_omics_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS HealthOmics client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured HealthOmics client

    Raises:
        Exception: If client creation fails
    """
    session = get_aws_session(region_name=region_name, profile_name=profile_name)
    service_name = get_omics_service_name()
    endpoint_url = get_omics_endpoint_url()

    try:
        if endpoint_url:
            return session.client(service_name, endpoint_url=endpoint_url)
        else:
            return session.client(service_name)
    except Exception as e:
        logger.error(
            f'Failed to create {service_name} client in region {region_name or get_region()}: {str(e)}'
        )
        raise


def get_logs_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS CloudWatch Logs client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured CloudWatch Logs client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('logs', region_name=region_name, profile_name=profile_name)


def get_codeconnections_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS CodeConnections client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured CodeConnections client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('codeconnections', region_name=region_name, profile_name=profile_name)


def get_ecr_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS ECR client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured ECR client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('ecr', region_name=region_name, profile_name=profile_name)


def get_codebuild_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS CodeBuild client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured CodeBuild client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('codebuild', region_name=region_name, profile_name=profile_name)


def get_iam_client(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> Any:
    """Get an AWS IAM client.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        boto3.client: Configured IAM client

    Raises:
        Exception: If client creation fails
    """
    return create_aws_client('iam', region_name=region_name, profile_name=profile_name)


def get_account_id(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> str:
    """Get the current AWS account ID.

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        str: AWS account ID

    Raises:
        Exception: If unable to retrieve account ID
    """
    try:
        session = get_aws_session(region_name=region_name, profile_name=profile_name)
        sts_client = session.client('sts')
        response = sts_client.get_caller_identity()
        return response['Account']
    except Exception as e:
        logger.error(f'Failed to get AWS account ID: {str(e)}')
        raise


@lru_cache
def get_partition(
    region_name: str | None = None,
    profile_name: str | None = None,
) -> str:
    """Get the current AWS partition (cached by region/profile).

    Args:
        region_name: Optional region override
        profile_name: Optional AWS profile override

    Returns:
        str: AWS partition (e.g., 'aws', 'aws-cn', 'aws-us-gov')

    Raises:
        Exception: If unable to retrieve partition
    """
    try:
        session = get_aws_session(region_name=region_name, profile_name=profile_name)
        sts_client = session.client('sts')
        response = sts_client.get_caller_identity()
        # Extract partition from the ARN: arn:partition:sts::account-id:assumed-role/...
        arn = response['Arn']
        partition = arn.split(':')[1]
        logger.debug(f'Detected AWS partition: {partition}')
        return partition
    except Exception as e:
        logger.error(f'Failed to get AWS partition: {str(e)}')
        raise
