#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Common utilities and helpers for S3 Tables MCP Server."""

import os
from functools import wraps
from typing import Optional

import boto3
from botocore.config import Config
from loguru import logger
from pydantic import Field

from .models import (
    TABLE_ARN_PATTERN,
    TABLE_BUCKET_ARN_PATTERN,
    TABLE_NAME_PATTERN,
)


def handle_exceptions(func):
    """Decorator to handle exceptions consistently across tools."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {str(e)}')
            return {'error': str(e), 'tool': func.__name__}
    return wrapper


def handle_field_param(param_value):
    """Handle Pydantic Field parameter conversion to actual values."""
    if param_value is None:
        return None
    
    param_str = str(param_value)
    # Check if the string representation suggests it's a FieldInfo object
    if 'annotation=' in param_str and 'description=' in param_str:
        return None  # Treat FieldInfo representation of None as actual None
    
    return param_str


def get_s3tables_client(region_name: Optional[str] = None):
    """Create a boto3 S3 Tables client."""
    # Handle FieldInfo objects for region_name
    region_str = handle_field_param(region_name)
    region = region_str or os.getenv('AWS_REGION') or 'us-east-1'
    config = Config(user_agent_extra='MCP/S3TablesServer')
    session = boto3.Session()
    return session.client('s3tables', region_name=region, config=config)


# Common field patterns for reuse in annotations
TABLE_BUCKET_ARN_FIELD = Field(..., description='Table bucket ARN', pattern=TABLE_BUCKET_ARN_PATTERN)
TABLE_ARN_FIELD = Field(..., description='Table ARN', pattern=TABLE_ARN_PATTERN)
NAMESPACE_NAME_FIELD = Field(..., description='Namespace name', pattern=r'^[0-9a-z_]+$', max_length=255)
TABLE_NAME_FIELD = Field(..., description='Table name', pattern=TABLE_NAME_PATTERN, max_length=255)
REGION_NAME_FIELD = Field(default=None, description='AWS region name')
