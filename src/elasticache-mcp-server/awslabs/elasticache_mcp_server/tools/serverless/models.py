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

"""Models for serverless cache operations."""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Dict, List, Optional, Union


class DataStorageLimits(BaseModel):
    """Limits for data storage capacity in serverless configuration."""

    Maximum: int = Field(..., description='Maximum storage in GB', gt=0)
    Minimum: int = Field(..., description='Minimum storage in GB', gt=0)
    Unit: str = Field(..., description='Storage unit (currently only GB is supported)')

    @field_validator('Unit')
    def validate_unit(cls, v):
        """Validate that Unit is 'GB'."""
        if v != 'GB':
            raise ValueError("Unit must be 'GB'")
        return v

    @field_validator('Minimum')
    def minimum_less_than_maximum(cls, v, values):
        """Validate that Minimum is less than or equal to Maximum."""
        if hasattr(values, 'data') and 'Maximum' in values.data and v > values.data['Maximum']:
            raise ValueError('Minimum must be less than or equal to Maximum')
        return v


class ECPULimits(BaseModel):
    """Limits for ECPU (ElastiCache Processing Units) in serverless configuration."""

    Maximum: int = Field(..., description='Maximum ECPU per second', gt=0)
    Minimum: int = Field(..., description='Minimum ECPU per second', gt=0)

    @field_validator('Minimum')
    def minimum_less_than_maximum(cls, v, values):
        """Validate that Minimum is less than or equal to Maximum."""
        if hasattr(values, 'data') and 'Maximum' in values.data and v > values.data['Maximum']:
            raise ValueError('Minimum must be less than or equal to Maximum')
        return v


class CacheUsageLimits(BaseModel):
    """Combined limits for data storage and ECPU in serverless configuration."""

    DataStorage: DataStorageLimits = Field(..., description='Data storage limits configuration')
    ECPUPerSecond: ECPULimits = Field(..., description='ECPU limits configuration')


class Tag(BaseModel):
    """Tag model for ElastiCache resources."""

    Key: str = Field(..., description='The key for the tag')
    Value: Optional[str] = Field(None, description="The tag's value")


class CreateServerlessCacheRequest(BaseModel):
    """Request model for creating an ElastiCache serverless cache."""

    serverless_cache_name: str = Field(..., description='The identifier of the serverless cache')
    engine: str = Field(..., description='The name of the cache engine')
    description: Optional[str] = Field(None, description='Description for the cache')
    kms_key_id: Optional[str] = Field(None, description='KMS key ID for encryption')
    major_engine_version: Optional[str] = Field(None, description='Major engine version')
    snapshot_arns_to_restore: Optional[List[str]] = Field(
        None, description='List of snapshot ARNs to restore from'
    )
    subnet_ids: Optional[List[str]] = Field(
        None, description='List of subnet IDs for VPC configuration'
    )
    tags: Optional[Union[str, List[Tag], Dict[str, Optional[str]]]] = Field(
        None,
        description=(
            'Tags to apply. Can be a string in Key=value format, '
            'a list of Tag objects, or a dict of key-value pairs'
        ),
    )
    vpc_security_group_ids: Optional[List[str]] = Field(
        None, description='List of VPC security group IDs'
    )
    cache_usage_limits: Optional[CacheUsageLimits] = Field(
        None, description='Usage limits for the cache'
    )
    user_group_id: Optional[str] = Field(
        None, description='ID of the user group to associate with the cache'
    )
    snapshot_retention_limit: Optional[int] = Field(
        None, description='Number of days to retain automatic snapshots', ge=0
    )
    daily_snapshot_time: Optional[str] = Field(
        None,
        description="Time range (in UTC) when daily snapshots are taken (e.g., '04:00-05:00')",
    )

    @field_validator('daily_snapshot_time')
    def validate_snapshot_time(cls, v):
        """Validate snapshot time format."""
        if v is not None:
            import re

            if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]-([0-1][0-9]|2[0-3]):[0-5][0-9]$', v):
                raise ValueError('Invalid time range format. Must be in format HH:MM-HH:MM')
        return v

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)


class ModifyServerlessCacheRequest(BaseModel):
    """Request model for modifying an ElastiCache serverless cache."""

    serverless_cache_name: str = Field(
        ..., description='The name of the serverless cache to modify'
    )
    description: Optional[str] = Field(None, description='New description for the cache')
    major_engine_version: Optional[str] = Field(None, description='New major engine version')
    snapshot_retention_limit: Optional[int] = Field(
        None, description='Number of days to retain automatic snapshots', ge=0
    )
    daily_snapshot_time: Optional[str] = Field(
        None,
        description="Time range (in UTC) when daily snapshots are taken (e.g., '04:00-05:00')",
    )
    cache_usage_limits: Optional[CacheUsageLimits] = Field(
        None, description='New usage limits for the cache'
    )
    remove_user_group: Optional[bool] = Field(
        None, description='Whether to remove the user group association'
    )
    user_group_id: Optional[str] = Field(
        None, description='ID of the user group to associate with the cache'
    )
    vpc_security_group_ids: Optional[List[str]] = Field(
        None, description='List of VPC security group IDs'
    )

    @field_validator('daily_snapshot_time')
    def validate_snapshot_time(cls, v):
        """Validate snapshot time format."""
        if v is not None:
            import re

            if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]-([0-1][0-9]|2[0-3]):[0-5][0-9]$', v):
                raise ValueError('Invalid time range format. Must be in format HH:MM-HH:MM')
        return v

    model_config = ConfigDict(validate_by_name=True, arbitrary_types_allowed=True)
