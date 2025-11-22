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

"""Pydantic models for AWS Carbon Footprint MCP Server."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = 'CSV'
    PARQUET = 'PARQUET'


class CompressionType(str, Enum):
    """Supported compression types."""

    GZIP = 'GZIP'
    NONE = 'NONE'


class ExportStatus(str, Enum):
    """Export status values."""

    CREATING = 'CREATING'
    ACTIVE = 'ACTIVE'
    UPDATING = 'UPDATING'
    DELETING = 'DELETING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class GroupByOption(str, Enum):
    """Grouping options for carbon data queries."""

    SERVICE = 'service'
    REGION = 'region'
    ACCOUNT = 'account'
    DATE = 'date'


class CarbonExportConfig(BaseModel):
    """Configuration for creating a carbon data export."""

    export_name: str = Field(
        ..., description='Unique name for the carbon export', min_length=1, max_length=128
    )

    s3_bucket: str = Field(
        ..., description='S3 bucket name for storing export files', min_length=3, max_length=63
    )

    s3_prefix: str = Field(
        default='carbon-exports/', description='S3 prefix path for organizing export files'
    )

    start_date: str = Field(..., description='Export start date in YYYY-MM-DD format')

    end_date: str = Field(..., description='Export end date in YYYY-MM-DD format')

    format: ExportFormat = Field(default=ExportFormat.CSV, description='Export file format')

    compression: CompressionType = Field(
        default=CompressionType.GZIP, description='Compression type for export files'
    )

    description: Optional[str] = Field(
        None, description='Optional description for the export', max_length=512
    )

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format is YYYY-MM-DD."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @field_validator('s3_bucket')
    @classmethod
    def validate_s3_bucket_name(cls, v: str) -> str:
        """Validate S3 bucket name format."""
        import re

        if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', v):
            raise ValueError('Invalid S3 bucket name format')
        return v


class CarbonQueryFilter(BaseModel):
    """Filters for querying carbon emissions data."""

    start_date: str = Field(..., description='Query start date in YYYY-MM-DD format')

    end_date: str = Field(..., description='Query end date in YYYY-MM-DD format')

    service: Optional[str] = Field(
        None, description="Filter by AWS service code (e.g., 'EC2-Instance', 'S3')"
    )

    region: Optional[str] = Field(
        None, description="Filter by AWS region code (e.g., 'us-east-1', 'eu-west-1')"
    )

    account_id: Optional[str] = Field(
        None, description='Filter by AWS account ID (12-digit number)'
    )

    group_by: GroupByOption = Field(
        default=GroupByOption.SERVICE, description='Group query results by specified dimension'
    )

    limit: int = Field(
        default=100, ge=1, le=10000, description='Maximum number of results to return'
    )

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format is YYYY-MM-DD."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @field_validator('account_id')
    @classmethod
    def validate_account_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate AWS account ID format."""
        if v is not None and not v.isdigit() or len(v) != 12:
            raise ValueError('Account ID must be a 12-digit number')
        return v


class ExportInfo(BaseModel):
    """Information about a carbon data export."""

    export_name: str = Field(..., description='Name of the export')
    export_arn: str = Field(..., description='ARN of the export')
    status: ExportStatus = Field(..., description='Current export status')
    created_at: Optional[str] = Field(None, description='Export creation timestamp')
    completed_at: Optional[str] = Field(None, description='Export completion timestamp')
    description: Optional[str] = Field(None, description='Export description')
    s3_location: Optional[str] = Field(None, description='S3 location of export files')
    error_message: Optional[str] = Field(None, description='Error message if failed')


class CarbonEmissionRecord(BaseModel):
    """Individual carbon emission record."""

    billing_period_start_date: str = Field(..., description='Billing period start date')
    billing_period_end_date: str = Field(..., description='Billing period end date')
    account_id: str = Field(..., description='AWS account ID')
    region_code: str = Field(..., description='AWS region code')
    product_code: str = Field(..., description='AWS service code')
    total_mbm_emissions_value: float = Field(
        ..., description='Emissions value in metric tons CO2e'
    )
    total_mbm_emissions_unit: str = Field(default='MTCO2e', description='Emissions unit')


class CarbonQueryResult(BaseModel):
    """Result of a carbon emissions query."""

    group_key: str = Field(..., description='Grouping dimension value')
    total_emissions_mtco2e: float = Field(..., description='Total emissions in metric tons CO2e')
    record_count: int = Field(..., description='Number of records aggregated')
    earliest_date: str = Field(..., description='Earliest date in the group')
    latest_date: str = Field(..., description='Latest date in the group')


class ExportFileInfo(BaseModel):
    """Information about an export file."""

    file_key: str = Field(..., description='S3 object key')
    size_bytes: int = Field(..., description='File size in bytes')
    last_modified: str = Field(..., description='Last modification timestamp')
    s3_uri: str = Field(..., description='Complete S3 URI')


class CarbonExportResponse(BaseModel):
    """Response from carbon export operations."""

    status: str = Field(..., description='Operation status (success/error)')
    message: str = Field(..., description='Human-readable message')
    export_arn: Optional[str] = Field(None, description='ARN of created/referenced export')
    export_name: Optional[str] = Field(None, description='Name of the export')
    s3_location: Optional[str] = Field(None, description='S3 location for export files')
    date_range: Optional[str] = Field(None, description='Date range for the export')
    format: Optional[str] = Field(None, description='Export file format')
    next_steps: Optional[List[str]] = Field(None, description='Suggested next actions')
    error_details: Optional[Dict] = Field(None, description='Detailed error information')


class CarbonDataResponse(BaseModel):
    """Response from carbon data retrieval operations."""

    status: str = Field(..., description='Operation status (success/error)')
    message: str = Field(..., description='Human-readable message')
    export_arn: Optional[str] = Field(None, description='Source export ARN')
    s3_location: Optional[str] = Field(None, description='S3 location of data files')
    files: Optional[List[ExportFileInfo]] = Field(None, description='List of export files')
    total_files: Optional[int] = Field(None, description='Total number of files')
    data_records: Optional[List[CarbonEmissionRecord]] = Field(
        None, description='Sample data records'
    )
    query_results: Optional[List[CarbonQueryResult]] = Field(
        None, description='Aggregated query results'
    )
    note: Optional[str] = Field(None, description='Additional information or instructions')


class CarbonExportListResponse(BaseModel):
    """Response from listing carbon exports."""

    status: str = Field(..., description='Operation status (success/error)')
    message: str = Field(..., description='Human-readable message')
    exports: List[ExportInfo] = Field(default_factory=list, description='List of carbon exports')
    total_count: Optional[int] = Field(None, description='Total number of exports')
