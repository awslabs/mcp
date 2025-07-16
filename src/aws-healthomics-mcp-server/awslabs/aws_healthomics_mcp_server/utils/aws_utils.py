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
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_REGION
from loguru import logger
from typing import Any, Dict, Optional


def get_aws_session(region: Optional[str] = None) -> boto3.Session:
    """Get an AWS session with the specified or default region.

    Args:
        region: AWS region name (optional)

    Returns:
        boto3.Session: Configured AWS session
    """
    botocore_session = botocore.session.Session()
    user_agent_extra = f'awslabs/mcp/aws-healthomics-mcp-server/{__version__}'
    botocore_session.user_agent_extra = user_agent_extra
    region = region or os.environ.get('AWS_REGION', DEFAULT_REGION)
    return boto3.Session(region_name=region, botocore_session=botocore_session)


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


def create_aws_client(service_name: str, region: Optional[str] = None) -> Any:
    """Generic AWS client factory for any service.

    Args:
        service_name: Name of the AWS service (e.g., 'omics', 'logs', 'ssm')
        region: AWS region name (optional, defaults to environment/DEFAULT_REGION)

    Returns:
        boto3.client: Configured AWS service client

    Raises:
        Exception: If client creation fails
    """
    resolved_region = region or os.environ.get('AWS_REGION', DEFAULT_REGION)
    session = get_aws_session(resolved_region)
    try:
        return session.client(service_name)
    except Exception as e:
        logger.error(
            f'Failed to create {service_name} client in region {resolved_region}: {str(e)}'
        )
        raise


def get_omics_client(region: Optional[str] = None) -> Any:
    """Get an AWS HealthOmics client.

    Args:
        region: AWS region name (optional, defaults to environment/DEFAULT_REGION)

    Returns:
        boto3.client: Configured HealthOmics client

    Raises:
        Exception: If client creation fails
    """
    resolved_region = region or os.environ.get('AWS_REGION', DEFAULT_REGION)
    session = get_aws_session(resolved_region)
    try:
        return session.client('omics')
    except Exception as e:
        logger.error(f'Failed to create HealthOmics client in region {resolved_region}: {str(e)}')
        raise


def get_logs_client(region: Optional[str] = None) -> Any:
    """Get an AWS CloudWatch Logs client.

    Args:
        region: AWS region name (optional, defaults to environment/DEFAULT_REGION)

    Returns:
        boto3.client: Configured CloudWatch Logs client

    Raises:
        Exception: If client creation fails
    """
    resolved_region = region or os.environ.get('AWS_REGION', DEFAULT_REGION)
    session = get_aws_session(resolved_region)
    try:
        return session.client('logs')
    except Exception as e:
        logger.error(
            f'Failed to create CloudWatch Logs client in region {resolved_region}: {str(e)}'
        )
        raise


def get_ssm_client(region: Optional[str] = None) -> Any:
    """Get an AWS SSM client.

    Args:
        region: AWS region name (optional, defaults to environment/DEFAULT_REGION)

    Returns:
        boto3.client: Configured SSM client

    Raises:
        Exception: If client creation fails
    """
    resolved_region = region or os.environ.get('AWS_REGION', DEFAULT_REGION)
    session = get_aws_session(resolved_region)
    try:
        return session.client('ssm')
    except Exception as e:
        logger.error(f'Failed to create SSM client in region {resolved_region}: {str(e)}')
        raise
