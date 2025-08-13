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

"""Configuration for Bedrock Custom Model Import MCP Server."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.consts import (
    AWS_PROFILE,
    AWS_REGION,
    LOG_FORMAT,
    LOG_LEVEL,
    ROLE_ARN,
    S3_BUCKET_NAME,
)
from dataclasses import dataclass


@dataclass
class AWSConfig:
    """AWS configuration for Bedrock and S3 access."""

    region: str
    s3_bucket: str | None
    role_arn: str | None
    profile: str | None

    @classmethod
    def from_env(cls):
        """Create an AWSConfig instance from environment variables."""
        return cls(
            region=AWS_REGION,
            s3_bucket=S3_BUCKET_NAME,
            role_arn=ROLE_ARN,
            profile=AWS_PROFILE,
        )


@dataclass
class LoggingConfig:
    """Logging configuration for the MCP server."""

    level: str
    format: str

    @classmethod
    def from_env(cls):
        """Create a LoggingConfig instance from environment variables."""
        return cls(
            level=LOG_LEVEL,
            format=LOG_FORMAT,
        )


@dataclass
class AppConfig:
    """Application configuration for Bedrock Custom Model Import MCP Server."""

    aws_config: AWSConfig
    logging_config: LoggingConfig
    allow_write: bool

    @classmethod
    def from_env(cls, allow_write: bool = False):
        """Create an AppConfig instance from environment variables.

        Args:
            allow_write: Whether to allow write operations (create/delete)

        Returns:
            AppConfig: The application configuration
        """
        return cls(
            aws_config=AWSConfig.from_env(),
            logging_config=LoggingConfig.from_env(),
            allow_write=allow_write,
        )
