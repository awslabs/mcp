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

"""Configuration models for AWS DMS resources.

Pydantic models for validating input parameters when creating DMS resources.
"""

import json
from pydantic import BaseModel, Field, SecretStr, field_validator
from typing import List, Literal, Optional


# Database engine types supported by DMS
DatabaseEngine = Literal['mysql', 'postgres', 'oracle', 'mariadb', 'aurora', 'aurora-postgresql']


class ReplicationInstanceConfig(BaseModel):
    """Configuration for creating a replication instance."""

    replication_instance_identifier: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description='Unique identifier for the replication instance',
    )
    replication_instance_class: str = Field(
        ..., description='Instance class (e.g., dms.t3.medium)'
    )
    allocated_storage: int = Field(default=50, ge=5, le=6144, description='Storage in GB')
    multi_az: bool = Field(default=False, description='Enable Multi-AZ deployment')
    engine_version: Optional[str] = Field(default=None, description='DMS engine version')
    vpc_security_group_ids: Optional[List[str]] = Field(
        default=None, description='VPC security group IDs'
    )
    replication_subnet_group_identifier: Optional[str] = Field(
        default=None, description='Replication subnet group'
    )
    publicly_accessible: bool = Field(
        default=False, description='Make instance publicly accessible'
    )

    @field_validator('replication_instance_class')
    @classmethod
    def validate_instance_class(cls, v: str) -> str:
        """Validate instance class format."""
        valid_classes = [
            'dms.t2.micro',
            'dms.t2.small',
            'dms.t2.medium',
            'dms.t3.micro',
            'dms.t3.small',
            'dms.t3.medium',
            'dms.t3.large',
            'dms.c5.large',
            'dms.c5.xlarge',
            'dms.c5.2xlarge',
            'dms.r5.large',
            'dms.r5.xlarge',
            'dms.r5.2xlarge',
        ]
        if v not in valid_classes:
            raise ValueError(f'Invalid instance class: {v}. Must be one of {valid_classes}')
        return v


class EndpointConfig(BaseModel):
    """Configuration for creating a database endpoint."""

    endpoint_identifier: str = Field(
        ..., min_length=1, max_length=255, description='Unique identifier for the endpoint'
    )
    endpoint_type: Literal['source', 'target'] = Field(..., description='Endpoint type')
    engine_name: DatabaseEngine = Field(..., description='Database engine')
    server_name: str = Field(..., description='Database server hostname or IP')
    port: int = Field(..., ge=1, le=65535, description='Database port')
    database_name: str = Field(..., description='Database name')
    username: str = Field(..., description='Database username')
    password: SecretStr = Field(..., description='Database password (will be masked in logs)')
    ssl_mode: Literal['none', 'require', 'verify-ca', 'verify-full'] = Field(
        default='none', description='SSL connection mode'
    )
    extra_connection_attributes: Optional[str] = Field(
        default=None, description='Additional connection attributes'
    )
    certificate_arn: Optional[str] = Field(default=None, description='SSL certificate ARN')


class TaskConfig(BaseModel):
    """Configuration for creating a replication task."""

    replication_task_identifier: str = Field(
        ..., min_length=1, max_length=255, description='Unique identifier for the task'
    )
    source_endpoint_arn: str = Field(..., description='Source endpoint ARN')
    target_endpoint_arn: str = Field(..., description='Target endpoint ARN')
    replication_instance_arn: str = Field(..., description='Replication instance ARN')
    migration_type: Literal['full-load', 'cdc', 'full-load-and-cdc'] = Field(
        ..., description='Migration type'
    )
    table_mappings: str = Field(..., description='Table mappings JSON')
    replication_task_settings: Optional[str] = Field(
        default=None, description='Task settings JSON'
    )
    cdc_start_position: Optional[str] = Field(default=None, description='CDC start position')

    @field_validator('table_mappings')
    @classmethod
    def validate_table_mappings(cls, v: str) -> str:
        """Validate table mappings JSON."""
        try:
            mappings = json.loads(v)
            if 'rules' not in mappings:
                raise ValueError("Table mappings must contain 'rules' key")
            return v
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON in table_mappings: {e}')

    @field_validator('replication_task_settings')
    @classmethod
    def validate_task_settings(cls, v: Optional[str]) -> Optional[str]:
        """Validate task settings JSON if provided."""
        if v is None:
            return v
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON in replication_task_settings: {e}')


# TODO: Add validation for ARN formats
# TODO: Add cross-field validation (e.g., CDC settings only valid for CDC migration types)
# TODO: Add support for Secrets Manager integration in EndpointConfig
