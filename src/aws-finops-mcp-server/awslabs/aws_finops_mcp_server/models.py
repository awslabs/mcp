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

"""Models for the AWS FinOps MCP Server.

This module contains Pydantic models for data validation and serialization.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional


class SchemaFormat(str, Enum):
    """Format of the Storage Lens data schema.

    Attributes:
        CSV: Comma-separated values format.
        PARQUET: Apache Parquet columnar storage format.
    """

    CSV = 'CSV'
    PARQUET = 'PARQUET'


class ColumnDefinition(BaseModel):
    """Definition of a column in the Storage Lens data schema.

    Attributes:
        name: Name of the column.
        type: Data type of the column (e.g., STRING, BIGINT, DOUBLE).
    """

    name: str = Field(..., description='Name of the column')
    type: str = Field(..., description='Data type of the column')


class SchemaInfo(BaseModel):
    """Schema information for Storage Lens data.

    Attributes:
        format: Format of the data (CSV or PARQUET).
        columns: List of column definitions.
        skip_header: Whether to skip the header row (typically true for CSV).
    """

    format: SchemaFormat = Field(..., description='Format of the data (CSV or PARQUET)')
    columns: List[ColumnDefinition] = Field(..., description='List of column definitions')
    skip_header: bool = Field(default=False, description='Whether to skip the header row')


class QueryStatistics(BaseModel):
    """Statistics about an Athena query execution.

    Attributes:
        engine_execution_time_ms: Engine execution time in milliseconds.
        data_scanned_bytes: Amount of data scanned in bytes.
        total_execution_time_ms: Total execution time in milliseconds.
    """

    engine_execution_time_ms: int = Field(
        default=0, description='Engine execution time in milliseconds'
    )
    data_scanned_bytes: int = Field(default=0, description='Amount of data scanned in bytes')
    total_execution_time_ms: int = Field(
        default=0, description='Total execution time in milliseconds'
    )


class QueryResult(BaseModel):
    """Result of a Storage Lens query.

    Attributes:
        columns: Column names in the result set.
        rows: Rows of data in the result set.
        statistics: Query execution statistics.
        query: SQL query that was executed.
        manifest_location: Location of the manifest file.
        data_location: Location of the data files.
    """

    columns: List[str] = Field(..., description='Column names in the result set')
    rows: List[Dict[str, str]] = Field(..., description='Rows of data in the result set')
    statistics: QueryStatistics = Field(..., description='Query execution statistics')
    query: str = Field(..., description='SQL query that was executed')
    manifest_location: str = Field(..., description='Location of the manifest file')
    data_location: str = Field(..., description='Location of the data files')


class StorageLensQueryRequest(BaseModel):
    """Request parameters for a Storage Lens query.

    Attributes:
        manifest_location: S3 URI to manifest file or folder.
        query: SQL query to execute against the data.
        output_location: S3 location for Athena query results.
        database_name: Athena database name to use.
        table_name: Table name to create/use for the data.
    """

    manifest_location: str = Field(..., description='S3 URI to manifest file or folder')
    query: str = Field(..., description='SQL query to execute against the data')
    output_location: Optional[str] = Field(
        None, description='S3 location for Athena query results'
    )
    database_name: str = Field(
        default='storage_lens_db', description='Athena database name to use'
    )
    table_name: str = Field(
        default='storage_lens_metrics', description='Table name to create/use for the data'
    )

    @field_validator('manifest_location')
    @classmethod
    def validate_manifest_location(cls, v):
        """Validate that the manifest location is a valid S3 URI."""
        if not v.startswith('s3://'):
            raise ValueError("manifest_location must be a valid S3 URI starting with 's3://'")
        return v

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        """Validate that the query is not empty."""
        if not v.strip():
            raise ValueError('query cannot be empty')
        return v


class ManifestFile(BaseModel):
    """S3 Storage Lens manifest file information.

    Attributes:
        key: S3 object key of the manifest file.
        last_modified: Last modified timestamp of the manifest file.
    """

    key: str = Field(..., description='S3 object key of the manifest file')
    last_modified: datetime = Field(
        ..., description='Last modified timestamp of the manifest file'
    )


class AWSService(str, Enum):
    """AWS services supported by the FinOps MCP Server.

    Attributes:
        COST_OPTIMIZATION_HUB: AWS Cost Optimization Hub service.
        COMPUTE_OPTIMIZER: AWS Compute Optimizer service.
        COST_EXPLORER: AWS Cost Explorer service.
    """

    COST_OPTIMIZATION_HUB = 'cost_optimization_hub'
    COMPUTE_OPTIMIZER = 'compute_optimizer'
    COST_EXPLORER = 'cost_explorer'


class AWSServiceMapping(BaseModel):
    """Mapping between internal service names and AWS service names.

    Attributes:
        internal_name: Internal name used in the MCP server.
        aws_name: Actual service name used by boto3.
    """

    internal_name: AWSService
    aws_name: str


class AWSServiceNameMap(BaseModel):
    """Map of internal service names to AWS service names.

    Attributes:
        mappings: List of service name mappings.
    """

    mappings: Dict[AWSService, str] = Field(
        default={
            AWSService.COST_OPTIMIZATION_HUB: 'cost-optimization-hub',
            AWSService.COMPUTE_OPTIMIZER: 'compute-optimizer',
            AWSService.COST_EXPLORER: 'ce',
        },
        description='Mapping of internal service names to AWS service names',
    )


class ServerConfig(BaseModel):
    """Configuration for the AWS FinOps MCP Server.

    Attributes:
        server_name: Name of the MCP server.
        server_instructions: Instructions for using the MCP server.
        dependencies: List of dependencies required by the server.
        default_aws_region: Default AWS region to use if not specified.
        storage_lens_default_database: Default database name for Storage Lens data.
        storage_lens_default_table: Default table name for Storage Lens data.
        athena_max_retries: Maximum number of retries for Athena query completion.
        athena_retry_delay_seconds: Delay between retries in seconds.
    """

    server_name: str = Field(..., description='Name of the MCP server')
    server_instructions: str = Field(..., description='Instructions for using the MCP server')
    dependencies: List[str] = Field(..., description='List of dependencies required by the server')
    default_aws_region: str = Field(
        default='us-east-1', description='Default AWS region to use if not specified'
    )
    storage_lens_default_database: str = Field(
        default='storage_lens_db', description='Default database name for Storage Lens data'
    )
    storage_lens_default_table: str = Field(
        default='storage_lens_metrics', description='Default table name for Storage Lens data'
    )
    athena_max_retries: int = Field(
        default=100, description='Maximum number of retries for Athena query completion'
    )
    athena_retry_delay_seconds: int = Field(
        default=1, description='Delay between retries in seconds'
    )


class Boto3ToolInfo(BaseModel):
    """Information about a boto3 tool registered with the MCP server.

    Attributes:
        service: AWS service name.
        method: Method name in the service.
        docstring: Documentation string for the method.
    """

    service: str = Field(..., description='AWS service name')
    method: str = Field(..., description='Method name in the service')
    docstring: str = Field(..., description='Documentation string for the method')


class AthenaQueryExecution(BaseModel):
    """Information about an Athena query execution.

    Attributes:
        query_execution_id: ID of the query execution.
        status: Status of the query execution.
    """

    query_execution_id: str = Field(..., description='ID of the query execution')
    status: str = Field(..., description='Status of the query execution')
