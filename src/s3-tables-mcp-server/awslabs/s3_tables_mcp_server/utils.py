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

"""Common utilities and helpers for S3 Tables MCP Server."""

import boto3
import os
from . import __version__
from botocore.client import BaseClient
from botocore.config import Config
from functools import wraps
from typing import Optional


_user_agent_mode = 'ro'  # Default to read-only


def set_user_agent_mode(allow_write: bool):
    """Set the user agent mode to 'rw' (read-write) or 'ro' (read-only)."""
    global _user_agent_mode
    _user_agent_mode = 'rw' if allow_write else 'ro'


def _user_agent_extra():
    return f'awslabs/mcp/s3-tables-mcp-server/{__version__}/{_user_agent_mode}'


def handle_exceptions(func):
    """Decorator to handle exceptions consistently across tools."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {'error': str(e), 'tool': func.__name__}

    return wrapper


def get_s3tables_client(region_name: Optional[str] = None) -> BaseClient:
    """Create a boto3 S3 Tables client.

    Args:
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable
                    or defaults to 'us-east-1'.

    Returns:
        boto3.client: Configured S3 Tables client
    """
    region = region_name or os.getenv('AWS_REGION') or 'us-east-1'
    config = Config(user_agent_extra=_user_agent_extra())
    session = boto3.Session()
    return session.client('s3tables', region_name=region, config=config)


def get_s3_client(region_name: Optional[str] = None) -> BaseClient:
    """Create a boto3 S3 client.

    Args:
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable
                    or defaults to 'us-east-1'.

    Returns:
        boto3.client: Configured S3 client
    """
    region = region_name or os.getenv('AWS_REGION') or 'us-east-1'
    config = Config(user_agent_extra=_user_agent_extra())
    session = boto3.Session()
    return session.client('s3', region_name=region, config=config)


def get_sts_client(region_name: Optional[str] = None) -> BaseClient:
    """Create a boto3 STS client.

    Args:
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable
                    or defaults to 'us-east-1'.

    Returns:
        boto3.client: Configured STS client
    """
    region = region_name or os.getenv('AWS_REGION') or 'us-east-1'
    config = Config(user_agent_extra=_user_agent_extra())
    session = boto3.Session()
    return session.client('sts', region_name=region, config=config)


def get_athena_client(region_name: Optional[str] = None) -> BaseClient:
    """Create a boto3 Athena client.

    Args:
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable
                    or defaults to 'us-east-1'.

    Returns:
        boto3.client: Configured Athena client
    """
    region = region_name or os.getenv('AWS_REGION') or 'us-east-1'
    config = Config(user_agent_extra=_user_agent_extra())
    session = boto3.Session()
    return session.client('athena', region_name=region, config=config)


def pyiceberg_load_catalog(
    catalog_name: str,
    warehouse: str,
    uri: str,
    region: str,
    rest_signing_name: str = 's3tables',
    rest_sigv4_enabled: str = 'true',
):
    """Load a PyIceberg catalog with the given parameters."""
    from pyiceberg.catalog import load_catalog

    catalog = load_catalog(
        catalog_name,
        **{
            'type': 'rest',
            'warehouse': warehouse,
            'uri': uri,
            'rest.sigv4-enabled': rest_sigv4_enabled,
            'rest.signing-name': rest_signing_name,
            'rest.signing-region': region,
        },
    )
    catalog._session.headers['User-Agent'] = _user_agent_extra()  # type: ignore[attr-defined]
    return catalog
