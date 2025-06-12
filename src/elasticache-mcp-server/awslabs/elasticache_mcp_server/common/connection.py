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

"""Connection management for AWS services used by MCP Server."""

import boto3
import os
from botocore.config import Config
from typing import Any, Optional


class BaseConnectionManager:
    """Base class for AWS service connection managers."""

    _client: Optional[Any] = None
    _service_name: str = ''  # Must be overridden by subclasses
    _env_prefix: str = ''  # Must be overridden by subclasses

    @classmethod
    def get_connection(cls) -> Any:
        """Get or create an AWS service client connection with retry capabilities.

        Returns:
            boto3.client: An AWS service client configured with retries
        """
        if cls._client is None:
            # Get AWS configuration from environment
            aws_profile = os.environ.get('AWS_PROFILE', 'default')
            aws_region = os.environ.get('AWS_REGION', 'us-east-1')

            # Configure retry settings
            max_retries = int(os.environ.get(f'{cls._env_prefix}_MAX_RETRIES', '3'))
            retry_mode = os.environ.get(f'{cls._env_prefix}_RETRY_MODE', 'standard')
            connect_timeout = int(os.environ.get(f'{cls._env_prefix}_CONNECT_TIMEOUT', '5'))
            read_timeout = int(os.environ.get(f'{cls._env_prefix}_READ_TIMEOUT', '10'))

            # Create boto3 config with retry settings
            config = Config(
                retries={'max_attempts': max_retries, 'mode': retry_mode},
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                # Configure custom user agent to identify requests from LLM/MCP
                user_agent_extra='MCP/ElastiCacheServer',
            )

            # Initialize AWS client with session and config
            # so that if user changes credential, it will be reflected immediately in the next call
            session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
            cls._client = session.client(service_name=cls._service_name, config=config)

        return cls._client

    @classmethod
    def close_connection(cls) -> None:
        """Close the AWS service client connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None


class ElastiCacheConnectionManager(BaseConnectionManager):
    """Manages connection to ElastiCache using boto3."""

    _client: Optional[Any] = None
    _service_name = 'elasticache'
    _env_prefix = 'ELASTICACHE'


class EC2ConnectionManager(BaseConnectionManager):
    """Manages connection to EC2 using boto3."""

    _client: Optional[Any] = None
    _service_name = 'ec2'
    _env_prefix = 'EC2'


class CloudWatchLogsConnectionManager(BaseConnectionManager):
    """Manages connection to CloudWatch Logs using boto3."""

    _client: Optional[Any] = None
    _service_name = 'logs'
    _env_prefix = 'CLOUDWATCH_LOGS'


class FirehoseConnectionManager(BaseConnectionManager):
    """Manages connection to Kinesis Firehose using boto3."""

    _client: Optional[Any] = None
    _service_name = 'firehose'
    _env_prefix = 'FIREHOSE'


class CostExplorerConnectionManager(BaseConnectionManager):
    """Manages connection to AWS Cost Explorer using boto3."""

    _client: Optional[Any] = None
    _service_name = 'ce'
    _env_prefix = 'COST_EXPLORER'


class CloudWatchConnectionManager(BaseConnectionManager):
    """Manages connection to CloudWatch using boto3."""

    _client: Optional[Any] = None
    _service_name = 'cloudwatch'
    _env_prefix = 'CLOUDWATCH'
