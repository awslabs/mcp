# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Pydantic models for AWS S3 Tables MCP Server."""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# Constants and patterns
TABLE_BUCKET_ARN_PATTERN = r'^arn:aws[-a-z0-9]*:[a-z0-9]+:[-a-z0-9]*:[0-9]{12}:bucket/[a-z0-9_-]{3,63}$'
TABLE_ARN_PATTERN = r'^arn:aws[-a-z0-9]*:[a-z0-9]+:[-a-z0-9]*:[0-9]{12}:bucket/[a-z0-9_-]{3,63}/table/[a-zA-Z0-9-_]{1,255}$'
NAMESPACE_NAME_PATTERN = r'^[0-9a-z_]*$'
TABLE_NAME_PATTERN = r'^[0-9a-z_]*$'
TABLE_BUCKET_NAME_PATTERN = r'^[0-9a-z-]*$'


class SSEAlgorithm(str, Enum):
    """Server-side encryption algorithm."""
    AES256 = 'AES256'
    AWS_KMS = 'aws:kms'


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


class QueryEngine(str, Enum):
    """Supported query engines."""
    AUTO = 'auto'
    DUCKDB = 'duckdb'
    ATHENA = 'athena'
    SPARK = 'spark'
    GLUE = 'glue'


class DataFormat(str, Enum):
    """Supported data formats."""
    JSON = 'json'
    CSV = 'csv'
    PARQUET = 'parquet'
    AVRO = 'avro'


class WriteMode(str, Enum):
    """Data write modes."""
    APPEND = 'append'
    OVERWRITE = 'overwrite'
    MERGE = 'merge'


# Core S3 Tables models
class EncryptionConfiguration(BaseModel):
    """Configuration specifying how data should be encrypted.
    
    This structure defines the encryption algorithm and optional KMS key to be used for server-side encryption.
    """
    sse_algorithm: SSEAlgorithm = Field(
        ...,
        alias='sseAlgorithm',
        description='The server-side encryption algorithm to use. Valid values are AES256 for S3-managed encryption keys, or aws:kms for AWS KMS-managed encryption keys.'
    )
    kms_key_arn: Optional[str] = Field(
        None,
        alias='kmsKeyArn',
        description='The Amazon Resource Name (ARN) of the KMS key to use for encryption. This field is required only when sseAlgorithm is set to aws:kms.',
        min_length=1,
        max_length=2048,
        pattern=r'arn:aws[-a-z0-9]*:kms:[-a-z0-9]*:[0-9]{12}:key/.+'
    )

    @model_validator(mode='after')
    def validate_kms_key_required_for_kms(self) -> 'EncryptionConfiguration':
        """Validate that kmsKeyArn is provided when using aws:kms encryption."""
        if self.sse_algorithm == SSEAlgorithm.AWS_KMS and not self.kms_key_arn:
            raise ValueError('kmsKeyArn is required when sseAlgorithm is aws:kms')
        return self


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


class IcebergUnreferencedFileRemovalSettings(BaseModel):
    """Settings for unreferenced file removal."""
    unreferenced_days: Optional[int] = Field(None, ge=1, le=2147483647)
    non_current_days: Optional[int] = Field(None, ge=1, le=2147483647)


class TableBucketMaintenanceSettings(BaseModel):
    """Contains details about the maintenance settings for the table bucket.
    
    This data type is a UNION, so only one of the following members can be specified when used or returned.
    """
    iceberg_unreferenced_file_removal: Optional[IcebergUnreferencedFileRemovalSettings] = Field(
        None,
        alias='icebergUnreferencedFileRemoval',
        description='The unreferenced file removal settings for the table bucket.'
    )

    @model_validator(mode='after')
    def validate_only_one_setting(self) -> 'TableBucketMaintenanceSettings':
        """Validate that only one setting is specified."""
        settings = [
            self.iceberg_unreferenced_file_removal,
        ]
        if sum(1 for s in settings if s is not None) > 1:
            raise ValueError('Only one maintenance setting can be specified')
        return self


class TableBucketMaintenanceConfigurationValue(BaseModel):
    """Details about the values that define the maintenance configuration for a table bucket."""
    settings: Optional[TableBucketMaintenanceSettings] = Field(
        None,
        description='Contains details about the settings of the maintenance configuration.'
    )
    status: Optional[MaintenanceStatus] = Field(
        None,
        description='The status of the maintenance configuration.'
    )


class IcebergCompactionSettings(BaseModel):
    """Settings for Iceberg compaction."""
    target_file_size_mb: Optional[int] = Field(None, ge=1, le=2147483647)


class IcebergSnapshotManagementSettings(BaseModel):
    """Settings for Iceberg snapshot management."""
    min_snapshots_to_keep: Optional[int] = Field(None, ge=1, le=2147483647)
    max_snapshot_age_hours: Optional[int] = Field(None, ge=1, le=2147483647)


# Table bucket models
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


# Namespace models
class NamespaceSummary(BaseModel):
    """Namespace summary."""
    namespace: List[str]
    created_at: datetime
    created_by: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    owner_account_id: str = Field(min_length=12, max_length=12, pattern=r'[0-9].*')
    namespace_id: Optional[str] = None
    table_bucket_id: Optional[str] = None


# Table models
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


# Maintenance models
class TableMaintenanceJobStatusValue(BaseModel):
    """Table maintenance job status value."""
    status: JobStatus
    last_run_timestamp: Optional[datetime] = None
    failure_message: Optional[str] = None


class TableMaintenanceConfigurationValue(BaseModel):
    """Table maintenance configuration value."""
    status: Optional[MaintenanceStatus] = None
    settings: Optional[Union[IcebergCompactionSettings, IcebergSnapshotManagementSettings]] = None


# Query execution models
class QueryResult(BaseModel):
    """Query execution result."""
    status: Literal['success', 'error']
    message: Optional[str] = None
    rows_returned: Optional[int] = None
    execution_time_ms: Optional[float] = None
    engine_used: Optional[QueryEngine] = None
    data: Optional[List[Dict[str, Any]]] = None
    result_schema: Optional[Dict[str, Any]] = Field(None, alias='schema')
    next_token: Optional[str] = None


class QueryRequest(BaseModel):
    """Query request parameters."""
    table_arn: str = Field(pattern=TABLE_ARN_PATTERN)
    sql_query: str = Field(min_length=1, max_length=10000)
    engine: QueryEngine = QueryEngine.AUTO
    limit: Optional[int] = Field(None, ge=1, le=10000)
    output_format: DataFormat = DataFormat.JSON
    
    @field_validator('sql_query')
    @classmethod
    def validate_sql_query(cls, v: str) -> str:
        """Validate SQL query for security."""
        import sqlparse
        
        # Basic security checks - allow INSERT and UPDATE for data manipulation
        dangerous_keywords = ['DROP', 'DELETE', 'CREATE', 'ALTER', 'TRUNCATE']
        upper_query = v.upper()
        
        for keyword in dangerous_keywords:
            if keyword in upper_query:
                raise ValueError(f'SQL keyword "{keyword}" is not allowed. Only SELECT, INSERT, and UPDATE queries are permitted.')
        
        # Parse SQL to ensure it's a valid statement
        try:
            parsed = sqlparse.parse(v)
            if not parsed:
                raise ValueError('Invalid SQL syntax')
            
            # Allow SELECT, INSERT, UPDATE statements
            statement_type = parsed[0].get_type()
            allowed_types = ['SELECT', 'INSERT', 'UPDATE']
            if statement_type not in allowed_types:
                raise ValueError(f'Only {", ".join(allowed_types)} statements are allowed')
        except Exception as e:
            # Don't fail on parsing issues, let the engine handle SQL validation
            pass
        
        return v


class DataInsertRequest(BaseModel):
    """Data insertion request."""
    table_arn: str = Field(pattern=TABLE_ARN_PATTERN)
    data_source: str = Field(min_length=1)  # S3 path, local file, or inline data
    source_format: DataFormat
    engine: Literal['spark', 'glue'] = 'spark'
    write_mode: WriteMode = WriteMode.APPEND


class TableOptimizationRequest(BaseModel):
    """Table optimization request."""
    table_arn: str = Field(pattern=TABLE_ARN_PATTERN)
    operation: Literal['compact', 'vacuum', 'rewrite_manifests'] = 'compact'
    engine: Literal['spark', 'glue'] = 'spark'


# Resource discovery models
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


# Error handling
class S3TablesError(BaseModel):
    """S3 Tables error response."""
    error_code: str
    error_message: str
    request_id: Optional[str] = None
    resource_name: Optional[str] = None


# Engine configuration
class EngineConfig(BaseModel):
    """Base engine configuration."""
    engine_type: QueryEngine
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    auto_retry: bool = True
    max_retries: int = Field(default=3, ge=0, le=10)


class DuckDBConfig(EngineConfig):
    """DuckDB engine configuration."""
    engine_type: QueryEngine = QueryEngine.DUCKDB
    memory_limit: str = '2GB'
    threads: int = Field(default=4, ge=1, le=32)


class AthenaConfig(EngineConfig):
    """Athena engine configuration."""
    engine_type: QueryEngine = QueryEngine.ATHENA
    workgroup: str = 'primary'
    result_location: Optional[str] = None


class SparkConfig(EngineConfig):
    """Spark engine configuration."""
    engine_type: QueryEngine = QueryEngine.SPARK
    application_id: Optional[str] = None
    executor_memory: str = '4g'
    executor_cores: int = Field(default=2, ge=1, le=8)
    driver_memory: str = '2g'


class GlueConfig(EngineConfig):
    """Glue engine configuration."""
    engine_type: QueryEngine = QueryEngine.GLUE
    job_name: Optional[str] = None
    role: Optional[str] = None
    max_capacity: Optional[int] = Field(None, ge=1, le=100)
