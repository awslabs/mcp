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

"""Helper functions for AWS AppSync MCP Server."""

import boto3
import os
import re
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger


def get_appsync_client():
    """Get AWS AppSync client with proper configuration."""
    from awslabs.aws_appsync_mcp_server import __version__

    # Create config with user agent
    config = Config(user_agent_extra=f'awslabs/mcp/aws-appsync-mcp-server/{__version__}')
    try:
        session = boto3.Session(
            profile_name=os.getenv('AWS_PROFILE'), region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        return session.client('appsync', config=config)
    except Exception:
        logger.error('Failed to create AppSync client')
        raise


def _sanitize_error_message(message: str) -> str:
    """Remove sensitive information from error messages."""
    # Remove account IDs, ARNs, and other sensitive patterns
    patterns = [
        (r'\b\d{12}\b', '[ACCOUNT-ID]'),  # AWS account IDs
        (r'arn:aws:[^\s]+', '[ARN]'),  # ARNs
        (r'\b[A-Z0-9]{20}\b', '[ACCESS-KEY]'),  # Access keys
    ]
    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


def handle_exceptions(func):
    """Decorator to handle AWS exceptions consistently."""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ClientError as e:
            error_code = str(e.response['Error']['Code'])
            error_message = str(e.response['Error']['Message'])
            sanitized_message = _sanitize_error_message(error_message)
            logger.error(f'AWS AppSync error [{error_code}]: {sanitized_message}')
            raise Exception(f'AppSync API error [{error_code}]: {sanitized_message}')
        except Exception:
            raise

    return wrapper
