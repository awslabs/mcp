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

"""Pydantic models for CloudTrail MCP Server."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from typing import Any, Dict, List, Optional


class EventDataStore(BaseModel):
    """Model for CloudTrail Lake Event Data Store."""

    event_data_store_arn: Optional[str] = Field(None, alias='EventDataStoreArn')
    name: Optional[str] = Field(None, alias='Name')
    status: Optional[str] = Field(None, alias='Status')
    advanced_event_selectors: Optional[List[Dict[str, Any]]] = Field(
        None, alias='AdvancedEventSelectors'
    )
    multi_region_enabled: Optional[bool] = Field(None, alias='MultiRegionEnabled')
    organization_enabled: Optional[bool] = Field(None, alias='OrganizationEnabled')
    retention_period: Optional[int] = Field(None, alias='RetentionPeriod')
    termination_protection_enabled: Optional[bool] = Field(
        None, alias='TerminationProtectionEnabled'
    )
    created_timestamp: Optional[datetime] = Field(None, alias='CreatedTimestamp')
    updated_timestamp: Optional[datetime] = Field(None, alias='UpdatedTimestamp')
    kms_key_id: Optional[str] = Field(None, alias='KmsKeyId')
    billing_mode: Optional[str] = Field(None, alias='BillingMode')

    model_config = ConfigDict(populate_by_name=True)

    @field_serializer('created_timestamp', 'updated_timestamp')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class QueryResult(BaseModel):
    """Model for CloudTrail Lake query result."""

    query_id: str
    query_status: str
    query_statistics: Optional[Dict[str, Any]] = None
    query_result_rows: Optional[List[List[Dict[str, str]]]] = None
    next_token: Optional[str] = None
    error_message: Optional[str] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)


class QueryStatus(BaseModel):
    """Model for CloudTrail Lake query status."""

    query_id: str
    query_status: str
    query_statistics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    delivery_s3_uri: Optional[str] = None
    delivery_status: Optional[str] = None

    def model_dump(self, **kwargs):
        """Override model_dump to exclude None values."""
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)
