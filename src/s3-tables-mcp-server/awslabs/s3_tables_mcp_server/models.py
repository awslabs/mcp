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

"""AWS S3 Tables MCP Server models."""

from awslabs.s3_tables_mcp_server.constants import (
    TABLE_ARN_PATTERN,
    TABLE_BUCKET_ARN_PATTERN,
    TABLE_BUCKET_NAME_PATTERN,
    TABLE_NAME_PATTERN,
)
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Union


# Enums
class OpenTableFormat(str, Enum):
    """Supported open table formats."""

    ICEBERG = 'ICEBERG'


class TableBucketType(str, Enum):
    """Table bucket type."""

    CUSTOMER = 'customer'
    AWS = 'aws'


class TableType(str, Enum):
    """Table type."""

    CUSTOMER = 'customer'
    AWS = 'aws'


class MaintenanceStatus(str, Enum):
    """Maintenance status."""

    ENABLED = 'enabled'
    DISABLED = 'disabled'


class JobStatus(str, Enum):
    """Job status."""

    NOT_YET_RUN = 'Not_Yet_Run'
    SUCCESSFUL = 'Successful'
    FAILED = 'Failed'
    DISABLED = 'Disabled'


class TableBucketMaintenanceType(str, Enum):
    """Table bucket maintenance type."""

    ICEBERG_UNREFERENCED_FILE_REMOVAL = 'icebergUnreferencedFileRemoval'


class TableMaintenanceType(str, Enum):
    """Table maintenance type."""

    ICEBERG_COMPACTION = 'icebergCompaction'
    ICEBERG_SNAPSHOT_MANAGEMENT = 'icebergSnapshotManagement'


class TableMaintenanceJobType(str, Enum):
    """Table maintenance job type."""

    ICEBERG_COMPACTION = 'icebergCompaction'
    ICEBERG_SNAPSHOT_MANAGEMENT = 'icebergSnapshotManagement'
    ICEBERG_UNREFERENCED_FILE_REMOVAL = 'icebergUnreferencedFileRemoval'


# Core Models
class TableBucketSummary(BaseModel):
    """Table bucket summary."""

    arn: str = Field(pattern=TABLE_BUCKET_ARN_PATTERN)
    name: str = Field(min_length=3, max_length=63, pattern=TABLE_BUCKET_NAME_PATTERN)
    owner_account_id: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    created_at: datetime
    table_bucket_id: Optional[str] = None
    type: Optional[TableBucketType] = None


class TableBucket(BaseModel):
    """Complete table bucket information."""

    arn: str = Field(pattern=TABLE_BUCKET_ARN_PATTERN)
    name: str = Field(min_length=3, max_length=63, pattern=TABLE_BUCKET_NAME_PATTERN)
    owner_account_id: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    created_at: datetime
    table_bucket_id: Optional[str] = None
    type: Optional[TableBucketType] = None


class NamespaceSummary(BaseModel):
    """Namespace summary."""

    namespace: List[str]
    created_at: datetime
    created_by: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    owner_account_id: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    namespace_id: Optional[str] = None
    table_bucket_id: Optional[str] = None


class TableSummary(BaseModel):
    """Table summary."""

    namespace: List[str]
    name: str = Field(min_length=1, max_length=255, pattern=TABLE_NAME_PATTERN)
    type: TableType
    table_arn: str = Field(pattern=TABLE_ARN_PATTERN)
    created_at: datetime
    modified_at: datetime
    namespace_id: Optional[str] = None
    table_bucket_id: Optional[str] = None


class Table(BaseModel):
    """Complete table information."""

    name: str = Field(min_length=1, max_length=255, pattern=TABLE_NAME_PATTERN)
    type: TableType
    table_arn: str = Field(pattern=TABLE_ARN_PATTERN, alias='tableARN')
    namespace: List[str]
    namespace_id: Optional[str] = None
    version_token: str = Field(min_length=1, max_length=2048)
    metadata_location: Optional[str] = Field(None, min_length=1, max_length=2048)
    warehouse_location: str = Field(min_length=1, max_length=2048)
    created_at: datetime
    created_by: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    managed_by_service: Optional[str] = None
    modified_at: datetime
    modified_by: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    owner_account_id: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    format: OpenTableFormat
    table_bucket_id: Optional[str] = None


# Maintenance Models
class IcebergCompactionSettings(BaseModel):
    """Settings for Iceberg compaction."""

    target_file_size_mb: Optional[int] = Field(None, ge=1, le=2147483647)


class IcebergSnapshotManagementSettings(BaseModel):
    """Settings for Iceberg snapshot management."""

    min_snapshots_to_keep: Optional[int] = Field(None, ge=1, le=2147483647)
    max_snapshot_age_hours: Optional[int] = Field(None, ge=1, le=2147483647)


class TableMaintenanceJobStatusValue(BaseModel):
    """Table maintenance job status value."""

    status: JobStatus
    last_run_timestamp: Optional[datetime] = None
    failure_message: Optional[str] = None


class TableMaintenanceConfigurationValue(BaseModel):
    """Table maintenance configuration value."""

    status: Optional[MaintenanceStatus] = None
    settings: Optional[Union[IcebergCompactionSettings, IcebergSnapshotManagementSettings]] = None


class IcebergUnreferencedFileRemovalSettings(BaseModel):
    """Settings for unreferenced file removal."""

    unreferenced_days: Optional[int] = Field(None, ge=1, le=2147483647)
    non_current_days: Optional[int] = Field(None, ge=1, le=2147483647)


class TableBucketMaintenanceSettings(BaseModel):
    """Contains details about the maintenance settings for the table bucket."""

    iceberg_unreferenced_file_removal: Optional[IcebergUnreferencedFileRemovalSettings] = Field(
        None, description='Settings for unreferenced file removal.'
    )

    @model_validator(mode='after')
    def validate_only_one_setting(self) -> 'TableBucketMaintenanceSettings':
        """Validate that only one setting is specified."""
        settings = [self.iceberg_unreferenced_file_removal]
        if sum(1 for s in settings if s is not None) > 1:
            raise ValueError('Only one maintenance setting can be specified')
        return self


class TableBucketMaintenanceConfigurationValue(BaseModel):
    """Details about the values that define the maintenance configuration for a table bucket."""

    settings: Optional[TableBucketMaintenanceSettings] = Field(
        None, description='Contains details about the settings of the maintenance configuration.'
    )
    status: Optional[MaintenanceStatus] = Field(
        None, description='The status of the maintenance configuration.'
    )


# Resource Models
class TableBucketsResource(BaseModel):
    """Resource containing all table buckets."""

    table_buckets: List[TableBucketSummary]
    total_count: int


class NamespacesResource(BaseModel):
    """Resource containing all namespaces."""

    namespaces: List[NamespaceSummary]
    total_count: int


class TablesResource(BaseModel):
    """Resource containing all tables."""

    tables: List[TableSummary]
    total_count: int


# Error Models
class S3TablesError(BaseModel):
    """S3 Tables error response."""

    error_code: str
    error_message: str
    request_id: Optional[str] = None
    resource_name: Optional[str] = None


# Schema Models
class SchemaField(BaseModel):
    """Iceberg schema field."""

    name: str
    type: str
    required: Optional[bool] = None


class IcebergSchema(BaseModel):
    """Iceberg table schema."""

    fields: List[SchemaField]


class IcebergMetadata(BaseModel):
    """Iceberg table metadata."""

    table_schema: IcebergSchema = Field(alias='schema')


class TableMetadata(BaseModel):
    """Table metadata union."""

    iceberg: Optional[IcebergMetadata] = None
