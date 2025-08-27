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

"""Data models for AWS Billing and Cost Management MCP Server."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional


# Common Enums
class APIStatus(str, Enum):
    """API response status."""

    SUCCESS = 'success'
    ERROR = 'error'


class CostMetric(str, Enum):
    """AWS Cost Explorer cost metrics."""

    UNBLENDED_COST = 'UnblendedCost'
    BLENDED_COST = 'BlendedCost'
    AMORTIZED_COST = 'AmortizedCost'
    NET_UNBLENDED_COST = 'NetUnblendedCost'
    NET_AMORTIZED_COST = 'NetAmortizedCost'
    USAGE_QUANTITY = 'UsageQuantity'
    NORMALIZED_USAGE_AMOUNT = 'NormalizedUsageAmount'


class DateGranularity(str, Enum):
    """AWS Cost Explorer time granularity."""

    DAILY = 'DAILY'
    MONTHLY = 'MONTHLY'
    HOURLY = 'HOURLY'


class SchemaFormat(str, Enum):
    """Storage Lens schema formats."""

    CSV = 'CSV'
    PARQUET = 'PARQUET'
    JSON = 'JSON'


# Base Models
class BaseResponse(BaseModel):
    """Base model for API responses."""

    status: APIStatus
    message: Optional[str] = None


class ErrorResponse(BaseResponse):
    """Error response model."""

    status: APIStatus = APIStatus.ERROR
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseResponse):
    """Success response model."""

    status: APIStatus = APIStatus.SUCCESS
    data: Optional[Dict[str, Any]] = None


class DateRange(BaseModel):
    """Date range for cost queries."""

    start_date: str = Field(description='The start date in YYYY-MM-DD format')
    end_date: str = Field(description='The end date in YYYY-MM-DD format')

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f'Invalid date format: {v}. Expected format: YYYY-MM-DD')
        return v


# Storage Lens Models
class ColumnDefinition(BaseModel):
    """Column definition for Storage Lens data schema."""

    name: str
    type: str
    nullable: Optional[bool] = True


class SchemaInfo(BaseModel):
    """Schema information for Storage Lens data."""

    format: SchemaFormat
    columns: List[ColumnDefinition]
    skip_header: Optional[bool] = False


class StorageLensQueryRequest(BaseModel):
    """Storage Lens query request."""

    manifest_location: str = Field(description='S3 URI to the manifest file or folder')
    query: str = Field(description='SQL query to execute against the data')
    database_name: Optional[str] = 'storage_lens_db'
    table_name: Optional[str] = 'storage_lens_metrics'
    output_location: Optional[str] = None


class AthenaQueryExecution(BaseModel):
    """Athena query execution status."""

    query_execution_id: str
    status: str
    submission_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    state_change_reason: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None


# Cost Explorer Models
class GroupBy(BaseModel):
    """Group by dimension for cost queries."""

    type: str = 'DIMENSION'
    key: str


class CostFilter(BaseModel):
    """Cost filter for AWS Cost Explorer queries."""

    dimensions: Optional[Dict[str, List[str]]] = None
    tags: Optional[Dict[str, List[str]]] = None


class CostExplorerRequest(BaseModel):
    """Cost Explorer request model."""

    time_period: DateRange
    granularity: Optional[DateGranularity] = DateGranularity.MONTHLY
    metrics: List[CostMetric] = [CostMetric.UNBLENDED_COST]
    group_by: Optional[List[GroupBy]] = None
    filter: Optional[CostFilter] = None


# Compute Optimizer Models
class RecommendationType(str, Enum):
    """AWS Compute Optimizer recommendation types."""

    EC2_INSTANCE = 'Ec2Instance'
    AUTO_SCALING_GROUP = 'AutoScalingGroup'
    EBS_VOLUME = 'EbsVolume'
    LAMBDA_FUNCTION = 'LambdaFunction'
    ECS_SERVICE = 'EcsService'
    FARGATE = 'Fargate'
    RDS = 'Rds'


class ComputeOptimizerRequest(BaseModel):
    """Compute Optimizer recommendation request."""

    resource_type: RecommendationType
    account_ids: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    filter_by_finding_types: Optional[List[str]] = None


# Budget Models
class BudgetPeriod(str, Enum):
    """AWS Budget time periods."""

    DAILY = 'DAILY'
    MONTHLY = 'MONTHLY'
    QUARTERLY = 'QUARTERLY'
    ANNUALLY = 'ANNUALLY'


class BudgetType(str, Enum):
    """AWS Budget types."""

    COST = 'COST'
    USAGE = 'USAGE'
    RI_UTILIZATION = 'RI_UTILIZATION'
    RI_COVERAGE = 'RI_COVERAGE'
    SAVINGS_PLANS_UTILIZATION = 'SAVINGS_PLANS_UTILIZATION'
    SAVINGS_PLANS_COVERAGE = 'SAVINGS_PLANS_COVERAGE'


# SQL Models
class SQLExecutionResult(BaseModel):
    """SQL execution result."""

    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int


# Export/Import models for interoperability between tools
__all__ = [
    # Enums
    'APIStatus',
    'CostMetric',
    'DateGranularity',
    'SchemaFormat',
    'RecommendationType',
    'BudgetPeriod',
    'BudgetType',
    # Base models
    'BaseResponse',
    'ErrorResponse',
    'SuccessResponse',
    'DateRange',
    'GroupBy',
    'CostFilter',
    # Storage Lens models
    'ColumnDefinition',
    'SchemaInfo',
    'StorageLensQueryRequest',
    'AthenaQueryExecution',
    # Cost Explorer models
    'CostExplorerRequest',
    # Compute Optimizer models
    'ComputeOptimizerRequest',
    # SQL models
    'SQLExecutionResult',
]
