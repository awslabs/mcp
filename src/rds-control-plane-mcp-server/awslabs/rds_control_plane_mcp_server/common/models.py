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

"""Model definitions for RDS Control Plane MCP Server."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional


class VpcSecurityGroup(BaseModel):
    """VPC security group model."""

    id: str = Field(description='The VPC security group ID')
    status: str = Field(description='The status of the VPC security group')


class ClusterMember(BaseModel):
    """DB cluster member model."""

    instance_id: str = Field(description='The instance identifier of the DB cluster member')
    is_writer: bool = Field(description='Whether the cluster member is a writer instance')
    status: Optional[str] = Field(
        None, description='The status of the DB cluster parameter group for this member'
    )


class ClusterModel(BaseModel):
    """DB cluster model."""

    cluster_id: str = Field(description='The DB cluster identifier')
    status: str = Field(description='The current status of the DB cluster')
    engine: str = Field(description='The database engine')
    engine_version: Optional[str] = Field(None, description='The version of the database engine')
    endpoint: Optional[str] = Field(
        None, description='The connection endpoint for the primary instance'
    )
    reader_endpoint: Optional[str] = Field(
        None, description='The reader endpoint for the DB cluster'
    )
    multi_az: bool = Field(
        description='Whether the DB cluster has instances in multiple Availability Zones'
    )
    backup_retention: int = Field(description='The retention period for automated backups')
    preferred_backup_window: Optional[str] = Field(
        None, description='The daily time range during which automated backups are created'
    )
    preferred_maintenance_window: Optional[str] = Field(
        None, description='The weekly time range during which system maintenance can occur'
    )
    created_time: Optional[str] = Field(
        None, description='The time when the DB cluster was created'
    )
    members: List[ClusterMember] = Field(
        default_factory=list, description='A list of DB cluster members'
    )
    vpc_security_groups: List[VpcSecurityGroup] = Field(
        default_factory=list, description='A list of VPC security groups the DB cluster belongs to'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    resource_uri: Optional[str] = Field(None, description='The resource URI for this cluster')


class ClusterListModel(BaseModel):
    """DB cluster list model."""

    clusters: List[ClusterModel] = Field(default_factory=list, description='List of DB clusters')
    count: int = Field(description='Total number of DB clusters')
    resource_uri: str = Field(description='The resource URI for the DB clusters')


class InstanceEndpoint(BaseModel):
    """DB instance endpoint model."""

    address: Optional[str] = Field(None, description='The DNS address of the instance')
    port: Optional[int] = Field(
        None, description='The port that the database engine is listening on'
    )
    hosted_zone_id: Optional[str] = Field(
        None, description='The ID of the Amazon Route 53 hosted zone'
    )


class InstanceStorage(BaseModel):
    """DB instance storage model."""

    type: Optional[str] = Field(None, description='The storage type')
    allocated: Optional[int] = Field(None, description='The allocated storage size in gibibytes')
    encrypted: Optional[bool] = Field(None, description='Whether the storage is encrypted')


class InstanceModel(BaseModel):
    """DB instance model."""

    instance_id: str = Field(description='The DB instance identifier')
    status: str = Field(description='The current status of the DB instance')
    engine: str = Field(description='The database engine')
    engine_version: Optional[str] = Field(None, description='The version of the database engine')
    instance_class: str = Field(
        description='The compute and memory capacity class of the DB instance'
    )
    endpoint: InstanceEndpoint = Field(
        default_factory=InstanceEndpoint, description='The connection endpoint'
    )
    availability_zone: Optional[str] = Field(
        None, description='The Availability Zone of the DB instance'
    )
    multi_az: bool = Field(description='Whether the DB instance is a Multi-AZ deployment')
    storage: InstanceStorage = Field(
        default_factory=InstanceStorage, description='The storage configuration'
    )
    preferred_backup_window: Optional[str] = Field(
        None, description='The daily time range during which automated backups are created'
    )
    preferred_maintenance_window: Optional[str] = Field(
        None, description='The weekly time range during which system maintenance can occur'
    )
    publicly_accessible: bool = Field(description='Whether the DB instance is publicly accessible')
    vpc_security_groups: List[VpcSecurityGroup] = Field(
        default_factory=list,
        description='A list of VPC security groups the DB instance belongs to',
    )
    db_cluster: Optional[str] = Field(
        None, description='The DB cluster identifier, if this is a member of a DB cluster'
    )
    tags: Dict[str, str] = Field(default_factory=dict, description='A list of tags')
    dbi_resource_id: Optional[str] = Field(
        None, description='The AWS Region-unique, immutable identifier for the DB instance'
    )
    resource_uri: Optional[str] = Field(None, description='The resource URI for this instance')


class InstanceListModel(BaseModel):
    """DB instance list model."""

    instances: List[InstanceModel] = Field(
        default_factory=list, description='List of DB instances'
    )
    count: int = Field(description='Total number of DB instances')
    resource_uri: str = Field(description='The resource URI for the DB instances')


class DBLogFileSummary(BaseModel):
    """Database log file information.

    This model represents an Amazon RDS database log file with its metadata,
    including name, last modification time, and size.

    Attributes:
        log_file_name: The name of the log file in the database instance.
        last_written: A POSIX timestamp when the last log entry was written.
        size: Size of the log file in bytes.
    """

    log_file_name: str = Field(
        description='Name of the log file',
    )
    last_written: datetime = Field(
        description='A POSIX timestamp when the last log entry was written.'
    )
    size: int = Field(description='Size of the log file in bytes', ge=0)


class DBLogFileListModel(BaseModel):
    """DB cluster list model."""

    log_files: List[DBLogFileSummary] = Field(
        default_factory=list, description='List of DB log files'
    )
    count: int = Field(
        description='Total number of non-empty log files for the DB instance in Amazon RDS'
    )
    resource_uri: str = Field(description='The resource URI for the DB log files')


class PerformanceReportSummary(BaseModel):
    """Performance analysis report information.

    This model represents an Amazon RDS performance analysis report with its metadata,
    including report ID, creation time, time range of the analysis, and status.

    Attributes:
        analysis_report_id: Unique identifier for the performance report.
        create_time: Timestamp when the report was created.
        start_time: Start time of the performance analysis period.
        end_time: End time of the performance analysis period.
        status: Current status of the report (RUNNING, SUCCEEDED, or FAILED).
    """

    # Models the AnalysisReportSummaryTypeDef class which has no required fields
    analysis_report_id: str | None = Field(
        None, description='Unique identifier for the performance report'
    )
    create_time: str | None = Field(None, description='Time when the report was created')
    start_time: str | None = Field(None, description='Start time of the analysis period')
    end_time: str | None = Field(None, description='End time of the analysis period')
    status: Literal['RUNNING', 'SUCCEEDED', 'FAILED'] | None = None


class PerformanceReportListModel(BaseModel):
    """DB cluster list model."""

    reports: List[PerformanceReportSummary] = Field(
        default_factory=list, description='List of performance reports for a RDS instance'
    )
    count: int = Field(description='Total number of performance reports')
    resource_uri: str = Field(description='The resource URI for the performance reports')
