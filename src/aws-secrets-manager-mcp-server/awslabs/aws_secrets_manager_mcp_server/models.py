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

"""Pydantic models for AWS Secrets Manager MCP server."""

import json
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from .consts import (
    MAX_DESCRIPTION_LENGTH,
    MAX_SECRET_NAME_LENGTH,
    MAX_SECRET_SIZE,
    SECRET_NAME_PATTERN,
)


class SecretType(str, Enum):
    """Enumeration of common secret types for validation and suggestions."""
    
    DATABASE = 'database'
    API_KEY = 'api_key'
    OAUTH = 'oauth'
    CERTIFICATE = 'certificate'
    GENERIC = 'generic'


class RotationStatus(str, Enum):
    """Enumeration of secret rotation statuses."""
    
    ENABLED = 'enabled'
    DISABLED = 'disabled'
    IN_PROGRESS = 'in_progress'
    FAILED = 'failed'


class SecretVersionStage(str, Enum):
    """Enumeration of secret version stages."""
    
    AWSCURRENT = 'AWSCURRENT'
    AWSPENDING = 'AWSPENDING'
    AWSPREVIOUS = 'AWSPREVIOUS'


class Tag(BaseModel):
    """Represents a tag key-value pair for AWS resources."""
    
    key: str = Field(..., min_length=1, max_length=128, description='Tag key')
    value: str = Field(..., max_length=256, description='Tag value')
    
    @field_validator('key')
    @classmethod
    def validate_tag_key(cls, v: str) -> str:
        """Validate tag key format."""
        if not re.match(r'^[a-zA-Z0-9\s_.:/=+\-@]+$', v):
            raise ValueError('Tag key contains invalid characters')
        return v


class SecretValue(BaseModel):
    """Represents a secret value with metadata."""
    
    secret_string: Optional[str] = Field(None, description='Secret value as string')
    secret_binary: Optional[bytes] = Field(None, description='Secret value as binary data')
    version_id: Optional[str] = Field(None, description='Version ID of the secret')
    version_stages: List[str] = Field(default_factory=list, description='Version stages')
    created_date: Optional[datetime] = Field(None, description='Creation timestamp')
    
    @model_validator(mode='after')
    def validate_secret_value(self):
        """Validate that either secret_string or secret_binary is provided."""
        if not self.secret_string and not self.secret_binary:
            raise ValueError('Either secret_string or secret_binary must be provided')
        if self.secret_string and self.secret_binary:
            raise ValueError('Only one of secret_string or secret_binary can be provided')
        return self
    
    @field_validator('secret_string')
    @classmethod
    def validate_secret_string_size(cls, v: Optional[str]) -> Optional[str]:
        """Validate secret string size."""
        if v and len(v.encode('utf-8')) > MAX_SECRET_SIZE:
            raise ValueError(f'Secret string exceeds maximum size of {MAX_SECRET_SIZE} bytes')
        return v


class RotationConfiguration(BaseModel):
    """Configuration for automatic secret rotation."""
    
    lambda_function_arn: str = Field(..., description='ARN of the Lambda function for rotation')
    rotation_interval_days: int = Field(
        30, 
        ge=1, 
        le=365, 
        description='Number of days between automatic rotations'
    )
    rotation_immediately: bool = Field(
        False, 
        description='Whether to rotate the secret immediately after enabling'
    )


class SecretMetadata(BaseModel):
    """Metadata for a secret without the actual secret value."""
    
    name: str = Field(..., description='Name of the secret')
    arn: str = Field(..., description='ARN of the secret')
    description: Optional[str] = Field(None, description='Description of the secret')
    kms_key_id: Optional[str] = Field(None, description='KMS key ID used for encryption')
    rotation_enabled: bool = Field(False, description='Whether automatic rotation is enabled')
    rotation_lambda_arn: Optional[str] = Field(None, description='Lambda function ARN for rotation')
    rotation_interval_days: Optional[int] = Field(None, description='Rotation interval in days')
    last_rotated_date: Optional[datetime] = Field(None, description='Last rotation timestamp')
    last_changed_date: Optional[datetime] = Field(None, description='Last change timestamp')
    last_accessed_date: Optional[datetime] = Field(None, description='Last access timestamp')
    deleted_date: Optional[datetime] = Field(None, description='Deletion timestamp if scheduled')
    tags: List[Tag] = Field(default_factory=list, description='Tags associated with the secret')
    version_ids_to_stages: Dict[str, List[str]] = Field(
        default_factory=dict, 
        description='Mapping of version IDs to their stages'
    )
    created_date: Optional[datetime] = Field(None, description='Creation timestamp')
    primary_region: Optional[str] = Field(None, description='Primary region for the secret')
    replication_status: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description='Replication status across regions'
    )


class CreateSecretRequest(BaseModel):
    """Request model for creating a new secret."""
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=MAX_SECRET_NAME_LENGTH,
        description='Name of the secret to create'
    )
    secret_value: Union[str, Dict[str, Any]] = Field(
        ..., 
        description='Secret value as string or structured data'
    )
    description: Optional[str] = Field(
        None, 
        max_length=MAX_DESCRIPTION_LENGTH,
        description='Description of the secret'
    )
    kms_key_id: Optional[str] = Field(
        None, 
        description='KMS key ID for encryption (uses default if not specified)'
    )
    tags: List[Tag] = Field(
        default_factory=list, 
        description='Tags to associate with the secret'
    )
    force_overwrite_replica_secret: bool = Field(
        False, 
        description='Whether to overwrite replica secrets'
    )
    replica_regions: List[str] = Field(
        default_factory=list, 
        description='Regions to replicate the secret to'
    )
    
    @field_validator('name')
    @classmethod
    def validate_secret_name(cls, v: str) -> str:
        """Validate secret name format."""
        if not re.match(SECRET_NAME_PATTERN, v):
            raise ValueError(f'Secret name must match pattern: {SECRET_NAME_PATTERN}')
        return v
    
    @field_validator('secret_value')
    @classmethod
    def validate_secret_value_size(cls, v: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Validate secret value size."""
        if isinstance(v, dict):
            v_str = json.dumps(v)
        else:
            v_str = str(v)
        
        if len(v_str.encode('utf-8')) > MAX_SECRET_SIZE:
            raise ValueError(f'Secret value exceeds maximum size of {MAX_SECRET_SIZE} bytes')
        return v


class UpdateSecretRequest(BaseModel):
    """Request model for updating an existing secret."""
    
    secret_id: str = Field(..., description='Name or ARN of the secret to update')
    secret_value: Optional[Union[str, Dict[str, Any]]] = Field(
        None, 
        description='New secret value'
    )
    description: Optional[str] = Field(
        None, 
        max_length=MAX_DESCRIPTION_LENGTH,
        description='New description for the secret'
    )
    kms_key_id: Optional[str] = Field(
        None, 
        description='New KMS key ID for encryption'
    )
    
    @field_validator('secret_value')
    @classmethod
    def validate_secret_value_size(cls, v: Optional[Union[str, Dict[str, Any]]]) -> Optional[Union[str, Dict[str, Any]]]:
        """Validate secret value size."""
        if v is None:
            return v
        
        if isinstance(v, dict):
            v_str = json.dumps(v)
        else:
            v_str = str(v)
        
        if len(v_str.encode('utf-8')) > MAX_SECRET_SIZE:
            raise ValueError(f'Secret value exceeds maximum size of {MAX_SECRET_SIZE} bytes')
        return v


class RandomPasswordConfig(BaseModel):
    """Configuration for generating random passwords."""
    
    password_length: int = Field(32, ge=4, le=4096, description='Length of the password')
    exclude_characters: Optional[str] = Field(
        None, 
        description='Characters to exclude from the password'
    )
    exclude_numbers: bool = Field(False, description='Whether to exclude numbers')
    exclude_punctuation: bool = Field(False, description='Whether to exclude punctuation')
    exclude_uppercase: bool = Field(False, description='Whether to exclude uppercase letters')
    exclude_lowercase: bool = Field(False, description='Whether to exclude lowercase letters')
    include_space: bool = Field(False, description='Whether to include space character')
    require_each_included_type: bool = Field(
        True, 
        description='Whether to require at least one character from each included type'
    )


class SecretsManagerResponse(BaseModel):
    """Base response model for Secrets Manager operations."""
    
    success: bool = Field(..., description='Whether the operation was successful')
    message: str = Field(..., description='Human-readable message about the operation')
    data: Optional[Dict[str, Any]] = Field(None, description='Additional response data')


class SecretListItem(BaseModel):
    """Simplified secret information for list operations."""
    
    name: str = Field(..., description='Name of the secret')
    arn: str = Field(..., description='ARN of the secret')
    description: Optional[str] = Field(None, description='Description of the secret')
    created_date: Optional[datetime] = Field(None, description='Creation timestamp')
    last_changed_date: Optional[datetime] = Field(None, description='Last change timestamp')
    last_accessed_date: Optional[datetime] = Field(None, description='Last access timestamp')
    rotation_enabled: bool = Field(False, description='Whether rotation is enabled')
    tags: List[Tag] = Field(default_factory=list, description='Tags associated with the secret')


class ListSecretsResponse(BaseModel):
    """Response model for listing secrets."""
    
    secrets: List[SecretListItem] = Field(..., description='List of secrets')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    total_count: int = Field(..., description='Total number of secrets found')


class ResourcePolicy(BaseModel):
    """Resource-based policy for a secret."""
    
    policy: str = Field(..., description='JSON policy document')
    policy_id: Optional[str] = Field(None, description='Policy ID')
    policy_checksum: Optional[str] = Field(None, description='Policy checksum')
