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
from botocore.exceptions import ClientError
from loguru import logger


def get_appsync_client():
    """Get AWS AppSync client with proper configuration."""
    try:
        session = boto3.Session(
            profile_name=os.getenv('AWS_PROFILE'), region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        return session.client('appsync')
    except Exception as e:
        logger.error(f'Failed to create AppSync client: {e}')
        raise


def handle_exceptions(func):
    """Decorator to handle AWS exceptions consistently."""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f'AWS AppSync error [{error_code}]: {error_message}')
            raise Exception(f'AppSync API error: {error_message}')
        except Exception as e:
            logger.error(f'Unexpected error in {func.__name__}: {e}')
            raise

    return wrapper
