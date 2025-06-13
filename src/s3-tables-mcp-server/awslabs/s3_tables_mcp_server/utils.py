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

from awslabs.s3_tables_mcp_server.constants import MCP_SERVER_VERSION


def handle_exceptions(func):
    """Decorator to handle exceptions consistently across tools."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
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
    """Create a boto3 S3 Tables client.
    
    Args:
        region_name: Optional AWS region name. If not provided, uses AWS_REGION environment variable
                    or defaults to 'us-east-1'.
    
    Returns:
        boto3.client: Configured S3 Tables client
    """
    # Handle FieldInfo objects for region_name
    region_str = handle_field_param(region_name)
    region = region_str or os.getenv('AWS_REGION') or 'us-east-1'
    config = Config(user_agent_extra=f'awslabs/mcp/s3tables/{MCP_SERVER_VERSION}')
    session = boto3.Session()
    return session.client('s3tables', region_name=region, config=config)
