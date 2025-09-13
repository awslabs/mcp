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

"""Pydantic models for AWS Database Migration Service MCP Server."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ReplicationInstanceResponse(BaseModel):
    """Response model for replication instance operations."""

    replication_instance_identifier: str = Field(description='The replication instance identifier')
    replication_instance_arn: str = Field(description='The ARN of the replication instance')
    replication_instance_class: str = Field(
        description='The compute and memory capacity of the replication instance'
    )
    engine_version: str = Field(
        description='The engine version number of the replication instance'
    )
    replication_instance_status: str = Field(description='The status of the replication instance')
    allocated_storage: int = Field(
        description='The amount of storage (in GB) allocated for the replication instance'
    )
    replication_instance_public_ip_address: Optional[str] = Field(
        default=None, description='The public IP address of the replication instance'
    )
    replication_instance_private_ip_address: Optional[str] = Field(
        default=None, description='The private IP address of the replication instance'
    )
    availability_zone: Optional[str] = Field(
        default=None, description='The Availability Zone for the instance'
    )
    vpc_security_groups: Optional[List[Dict[str, Any]]] = Field(
        default=None, description='The VPC security group for the instance'
    )
    preferred_maintenance_window: Optional[str] = Field(
        default=None, description='The maintenance window times for the replication instance'
    )
    multi_az: bool = Field(
        description='Specifies whether the replication instance is a Multi-AZ deployment'
    )
    auto_minor_version_upgrade: bool = Field(
        description='Boolean value indicating whether minor engine upgrades are applied automatically'
    )
    instance_create_time: Optional[datetime] = Field(
        default=None, description='The time the replication instance was created'
    )


class EndpointResponse(BaseModel):
    """Response model for endpoint operations."""

    endpoint_identifier: str = Field(description='The database endpoint identifier')
    endpoint_arn: str = Field(description='The ARN of the endpoint')
    endpoint_type: str = Field(description='The type of endpoint, either source or target')
    engine_name: str = Field(description='The type of engine for the endpoint')
    username: Optional[str] = Field(
        default=None, description='The user name to be used to login to the endpoint database'
    )
    server_name: Optional[str] = Field(
        default=None, description='The name of the server where the endpoint database resides'
    )
    port: Optional[int] = Field(
        default=None, description='The port value used to access the endpoint'
    )
    database_name: Optional[str] = Field(
        default=None, description='The name of the endpoint database'
    )
    status: str = Field(description='The status of the endpoint')
    ssl_mode: Optional[str] = Field(
        default=None, description='The SSL mode used to connect to the endpoint'
    )


class ReplicationTaskResponse(BaseModel):
    """Response model for replication task operations."""

    replication_task_identifier: str = Field(
        description='The user-assigned replication task identifier'
    )
    replication_task_arn: str = Field(description='The ARN of the replication task')
    source_endpoint_arn: str = Field(
        description='The Amazon Resource Name (ARN) string that uniquely identifies the source endpoint'
    )
    target_endpoint_arn: str = Field(
        description='The Amazon Resource Name (ARN) string that uniquely identifies the target endpoint'
    )
    replication_instance_arn: str = Field(
        description='The Amazon Resource Name (ARN) of the replication instance'
    )
    migration_type: str = Field(
        description='The type of migration (full-load, cdc, or full-load-and-cdc)'
    )
    table_mappings: Optional[str] = Field(
        default=None, description='The table mappings specified in JSON format'
    )
    replication_task_settings: Optional[str] = Field(
        default=None, description='The settings for the replication task'
    )
    status: str = Field(description='The status of the replication task')
    replication_task_creation_date: Optional[datetime] = Field(
        default=None, description='The date the replication task was created'
    )
    replication_task_start_date: Optional[datetime] = Field(
        default=None, description='The date the replication task is scheduled to start'
    )
    cdc_start_position: Optional[str] = Field(
        default=None,
        description='Indicates when you want a change data capture (CDC) operation to start',
    )
    recovery_checkpoint: Optional[str] = Field(
        default=None,
        description='Indicates the last checkpoint that occurred during a change data capture (CDC) operation',
    )


class DatabaseMigrationServiceListResponse(BaseModel):
    """Base response model for list operations."""

    marker: Optional[str] = Field(
        default=None, description='An optional pagination token provided by a previous request'
    )


class CreateReplicationInstanceResponse(BaseModel):
    """Response model for create replication instance operations."""

    replication_instance: ReplicationInstanceResponse = Field(
        description='The created replication instance details'
    )


class ReplicationInstanceListResponse(DatabaseMigrationServiceListResponse):
    """Response model for list replication instances."""

    replication_instances: List[ReplicationInstanceResponse] = Field(
        description='The list of replication instances'
    )


class EndpointListResponse(DatabaseMigrationServiceListResponse):
    """Response model for list endpoints."""

    endpoints: List[EndpointResponse] = Field(description='The list of endpoints')


class ReplicationTaskListResponse(DatabaseMigrationServiceListResponse):
    """Response model for list replication tasks."""

    replication_tasks: List[ReplicationTaskResponse] = Field(
        description='The list of replication tasks'
    )


class CreateEndpointResponse(BaseModel):
    """Response model for create endpoint operations."""

    endpoint: EndpointResponse = Field(description='The created endpoint details')


class ConnectionTestResponse(BaseModel):
    """Response model for test connection operations."""

    replication_instance_arn: str = Field(description='The ARN of the replication instance')
    endpoint_arn: str = Field(description='The ARN of the endpoint being tested')
    status: str = Field(description='The status of the connection')
    last_failure_message: Optional[str] = Field(
        default=None, description='The error message when the connection last failed'
    )


class ConnectionResponse(BaseModel):
    """Response model for connection information."""

    replication_instance_arn: str = Field(description='The ARN of the replication instance')
    endpoint_arn: str = Field(description='The ARN of the endpoint')
    status: str = Field(description='The status of the connection')
    last_failure_message: Optional[str] = Field(
        default=None, description='The error message when the connection last failed'
    )
    endpoint_identifier: str = Field(description='The identifier of the endpoint')
    replication_instance_identifier: str = Field(
        description='The identifier of the replication instance'
    )


class ConnectionListResponse(DatabaseMigrationServiceListResponse):
    """Response model for list connections."""

    connections: List[ConnectionResponse] = Field(description='The list of connections')
