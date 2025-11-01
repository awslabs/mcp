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

"""Response and common data models for AWS DMS operations.

Pydantic models for validating and serializing AWS DMS API responses.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ReplicationInstanceResponse(BaseModel):
    """Response model for replication instance."""

    replication_instance_arn: str
    replication_instance_identifier: str
    replication_instance_class: str
    replication_instance_status: str
    allocated_storage: int
    engine_version: str
    multi_az: bool
    publicly_accessible: bool
    instance_create_time: Optional[datetime] = None
    vpc_security_groups: Optional[List[Dict[str, Any]]] = None
    availability_zone: Optional[str] = None


class EndpointResponse(BaseModel):
    """Response model for endpoint."""

    endpoint_arn: str
    endpoint_identifier: str
    endpoint_type: str
    engine_name: str
    server_name: str
    port: int
    database_name: str
    username: str
    status: str
    ssl_mode: str
    certificate_arn: Optional[str] = None


class TaskResponse(BaseModel):
    """Response model for replication task."""

    replication_task_arn: str
    replication_task_identifier: str
    status: str
    migration_type: str
    source_endpoint_arn: str
    target_endpoint_arn: str
    replication_instance_arn: str
    table_mappings: str
    replication_task_stats: Optional[Dict[str, Any]] = None
    task_create_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None


class TableStatistics(BaseModel):
    """Model for table replication statistics."""

    schema_name: str
    table_name: str
    inserts: int
    deletes: int
    updates: int
    ddls: int
    full_load_rows: int
    full_load_condtnl_chk_failed_rows: int = 0
    full_load_error_rows: int = 0
    full_load_start_time: Optional[datetime] = None
    full_load_end_time: Optional[datetime] = None
    full_load_reloaded: bool = False
    last_update_time: Optional[datetime] = None
    table_state: str
    validation_pending_records: Optional[int] = None
    validation_failed_records: Optional[int] = None
    validation_suspended_records: Optional[int] = None
    validation_state: Optional[str] = None


class PaginationConfig(BaseModel):
    """Pagination configuration for API calls."""

    max_results: int = Field(default=100, ge=1, le=100)
    marker: Optional[str] = None


class FilterConfig(BaseModel):
    """Generic filter configuration for API calls."""

    name: str = Field(..., description="Filter name (e.g., 'replication-instance-id')")
    values: List[str] = Field(..., description='Filter values')


class OperationResponse(BaseModel):
    """Standard operation response wrapper."""

    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat() + 'Z'}


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""

    error: bool = True
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat() + 'Z'}


# TODO: Add validation for AWS ARN formats
# TODO: Add custom serializers for datetime fields
# TODO: Add model for connection test results
