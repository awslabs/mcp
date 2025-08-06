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

import os
import boto3
from botocore.config import Config
from typing import Any, Optional, Type
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# Pydantic model for AWS credentials + region
# ------------------------------------------------------------------------------
class AWSConfig(BaseModel):
    """AWS credentials and region for creating clients."""
    aws_access_key_id: str = Field(..., description="AWS access key ID")
    aws_secret_access_key: str = Field(..., description="AWS secret access key")
    region_name: str = Field(..., description="AWS region, e.g. 'us-east-1'")

# ------------------------------------------------------------------------------
# Base connection manager using AWSConfig
# ------------------------------------------------------------------------------
class BaseConnectionManager:
    """
    Base class for AWS service connection managers.

    Use get_connection(cls, aws_config) to obtain a client built from explicit
    credentials. Retry settings are still read from env using the subclass's _env_prefix.
    """
    _client: Optional[Any] = None
    _service_name: str = ""    # override in subclass
    _env_prefix: str = ""      # override in subclass

    @classmethod
    def get_connection(cls, aws_config: AWSConfig) -> Any:
        """
        Get or create an AWS service client with retry capabilities, using explicit AWSConfig.

        Args:
            aws_config: validated AWSConfig instance
        Returns:
            boto3.client for cls._service_name
        """
        if cls._client is None:
            # read retry settings from environment
            max_retries = int(os.environ.get(f"{cls._env_prefix}_MAX_RETRIES", "3"))
            retry_mode = os.environ.get(f"{cls._env_prefix}_RETRY_MODE", "standard")
            connect_timeout = int(os.environ.get(f"{cls._env_prefix}_CONNECT_TIMEOUT", "5"))
            read_timeout = int(os.environ.get(f"{cls._env_prefix}_READ_TIMEOUT", "10"))

            config = Config(
                retries={"max_attempts": max_retries, "mode": retry_mode},
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                user_agent_extra="MCP/ConnectionManager",
            )

            # instantiate client with explicit credentials
            cls._client = boto3.client(
                cls._service_name,
                aws_access_key_id=aws_config.aws_access_key_id,
                aws_secret_access_key=aws_config.aws_secret_access_key,
                region_name=aws_config.region_name,
                config=config,
            )

        return cls._client

    @classmethod
    def close_connection(cls) -> None:
        """Close the AWS service client and reset it."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None

# ------------------------------------------------------------------------------
# Concrete connection managers
# ------------------------------------------------------------------------------
class ElastiCacheConnectionManager(BaseConnectionManager):
    """Manages connection to ElastiCache using boto3."""
    _service_name = "elasticache"
    _env_prefix = "ELASTICACHE"


class EC2ConnectionManager(BaseConnectionManager):
    """Manages connection to EC2 using boto3."""
    _service_name = "ec2"
    _env_prefix = "EC2"


class CloudWatchLogsConnectionManager(BaseConnectionManager):
    """Manages connection to CloudWatch Logs using boto3."""
    _service_name = "logs"
    _env_prefix = "CLOUDWATCH_LOGS"


class FirehoseConnectionManager(BaseConnectionManager):
    """Manages connection to Kinesis Firehose using boto3."""
    _service_name = "firehose"
    _env_prefix = "FIREHOSE"


class CostExplorerConnectionManager(BaseConnectionManager):
    """Manages connection to AWS Cost Explorer using boto3."""
    _service_name = "ce"
    _env_prefix = "COST_EXPLORER"


class CloudWatchConnectionManager(BaseConnectionManager):
    """Manages connection to CloudWatch using boto3."""
    _service_name = "cloudwatch"
    _env_prefix = "CLOUDWATCH"
