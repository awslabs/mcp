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

"""Configuration management for AWS DMS MCP Server.

Uses Pydantic for type-safe configuration with environment variable support.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal, Optional


class DMSServerConfig(BaseSettings):
    """Configuration for AWS DMS MCP Server."""

    model_config = SettingsConfigDict(
        env_prefix='DMS_', case_sensitive=False, validate_assignment=True, extra='ignore'
    )

    # AWS Configuration
    aws_region: str = Field(default='us-east-1', description='AWS region for DMS operations')
    aws_profile: Optional[str] = Field(default=None, description='AWS credentials profile name')

    # Server Configuration
    read_only_mode: bool = Field(
        default=False, description='Enable read-only mode (prevents mutations)'
    )
    default_timeout: int = Field(
        default=300, ge=30, le=3600, description='Default timeout for DMS operations (seconds)'
    )
    max_results: int = Field(default=100, ge=1, le=100, description='Maximum results per API call')

    # Logging Configuration
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field(
        default='INFO', description='Logging level'
    )
    enable_structured_logging: bool = Field(
        default=True, description='Enable structured JSON logging'
    )

    # Feature Flags
    enable_connection_caching: bool = Field(
        default=True, description='Cache connection test results'
    )
    validate_table_mappings: bool = Field(
        default=True, description='Validate table mapping JSON before submission'
    )

    @field_validator('aws_region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """Validate AWS region format."""
        valid_regions = [
            'us-east-1',
            'us-east-2',
            'us-west-1',
            'us-west-2',
            'eu-west-1',
            'eu-west-2',
            'eu-central-1',
            'ap-southeast-1',
            'ap-southeast-2',
            'ap-northeast-1',
            'sa-east-1',
            'ca-central-1',
        ]
        if v not in valid_regions:
            raise ValueError(f'Invalid AWS region: {v}. Must be one of {valid_regions}')
        return v


# TODO: Add configuration loading from file support
# TODO: Add configuration validation on server startup
# TODO: Add configuration hot-reload support
