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

"""AWS client utilities for Bedrock AgentCore Browser MCP Server."""

from __future__ import annotations

from awslabs.amazon_bedrock_agentcore_browser_mcp_server import __version__
from boto3 import Session
from botocore.config import Config
from botocore.exceptions import ClientError
from functools import wraps
from loguru import logger
from os import getenv
from typing import Any


_clients: dict[str, Any] = {}


def _get_client(service_name: str, region_name: str | None = None):
    """Get or create a cached boto3 client for the given service."""
    profile_name = getenv('AWS_PROFILE', None)
    config = Config(user_agent_extra=f'md/awslabs#mcp#agentcore-browser#{__version__}')
    session = Session(profile_name=profile_name) if profile_name else Session()
    region = region_name or getenv('AWS_REGION') or session.region_name or 'us-east-1'

    cache_key = f'{service_name}:{region}'
    if cache_key not in _clients:
        _clients[cache_key] = session.client(service_name, region_name=region, config=config)
    return _clients[cache_key]


def get_data_plane_client(region_name: str | None = None):
    """Get cached boto3 client for Bedrock AgentCore data plane API."""
    return _get_client('bedrock-agentcore', region_name)


def get_control_plane_client(region_name: str | None = None):
    """Get cached boto3 client for Bedrock AgentCore control plane API."""
    return _get_client('bedrock-agentcore-control', region_name)


def handle_aws_errors(operation: str):
    """Decorator that catches ClientError and Exception, returning standardized error dicts."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                logger.error(f'Failed to {operation}: {error_code} - {error_message}')
                return {'error': error_code, 'message': error_message}
            except Exception as e:
                logger.error(f'Unexpected error in {operation}: {str(e)}')
                return {'error': 'UnexpectedError', 'message': str(e)}

        return wrapper

    return decorator
