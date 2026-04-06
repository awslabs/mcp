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

"""Data models for SSM for SAP health summary and report tools."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class ComponentEntry(BaseModel):
    """Health status for a single SAP component."""

    component_id: str = Field(..., description='Component ID')
    component_type: str = Field(default='UNKNOWN', description='Component type')
    status: str = Field(default='UNKNOWN', description='Component status')
    sid: str = Field(default='-', description='SAP SID')
    ec2_instance_ids: List[str] = Field(default_factory=list, description='Associated EC2 instance IDs')
    hana_version: Optional[str] = Field(default=None, description='HANA version if available')
    replication_mode: Optional[str] = Field(default=None, description='HANA system replication mode')
    operation_mode: Optional[str] = Field(default=None, description='HANA system replication operation mode')
    databases: Optional[List[str]] = Field(default=None, description='List of database names')
    cluster_status: Optional[str] = Field(default=None, description='Cluster status for HA setups')


class RuleResultEntry(BaseModel):
    """Individual rule evaluation result within a sub-check."""

    rule_id: str = Field(..., description='Rule identifier')
    description: Optional[str] = Field(default=None, description='Rule description')
    status: str = Field(default='UNKNOWN', description='Rule status (PASSED, FAILED, WARNING, INFO)')
    message: Optional[str] = Field(default=None, description='Actionable detail message')
    metadata: Optional[Dict[str, str]] = Field(default=None, description='Context metadata (component, instance, etc.)')


class SubCheckEntry(BaseModel):
    """Sub-check result within a configuration check."""

    id: Optional[str] = Field(default=None, description='Sub-check result ID')
    name: str = Field(default='UNKNOWN', description='Sub-check name')
    result: str = Field(default='UNKNOWN', description='Sub-check result (Passed, Failed, Warning, Info)')
    description: Optional[str] = Field(default=None, description='Sub-check description')
    rule_results: List[RuleResultEntry] = Field(default_factory=list, description='Rule-level results')


class ConfigCheckEntry(BaseModel):
    """Summary of a configuration check result."""

    check_id: str = Field(..., description='Configuration check ID')
    status: str = Field(default='UNKNOWN', description='Check operation status')
    result: str = Field(default='-', description='Check result (PASS, WARN, FAIL, etc.)')
    last_updated: Optional[str] = Field(default=None, description='Last updated timestamp')
    triggered_by_summary: bool = Field(default=False, description='Whether this check was auto-triggered by the summary tool')
    subchecks: List[SubCheckEntry] = Field(default_factory=list, description='Sub-check details grouped by severity')





class CloudWatchMetricsEntry(BaseModel):
    """CloudWatch metrics for an EC2 instance."""

    instance_id: str = Field(..., description='EC2 instance ID')
    cpu_avg: Optional[float] = Field(default=None, description='Average CPU utilization (%)')
    cpu_max: Optional[float] = Field(default=None, description='Maximum CPU utilization (%)')
    status_check: str = Field(default='N/A', description='Status check result')
    memory_used_pct: Optional[float] = Field(default=None, description='Memory used percentage from CWAgent')
    disk_used_pct: Optional[float] = Field(default=None, description='Disk used percentage from CWAgent')
    network_in: Optional[float] = Field(default=None, description='Network bytes in from CWAgent')
    network_out: Optional[float] = Field(default=None, description='Network bytes out from CWAgent')


class FilesystemUsageEntry(BaseModel):
    """Filesystem usage for an EC2 instance via SSM RunCommand."""

    instance_id: str = Field(..., description='EC2 instance ID')
    filesystem_info: Optional[str] = Field(default=None, description='df -h output for SAP filesystems')
    status: str = Field(default='N/A', description='Check status (Success, Failed, etc.)')


class BackupStatusEntry(BaseModel):
    """AWS Backup status for an EC2 instance."""

    instance_id: str = Field(..., description='EC2 instance ID')
    last_backup: Optional[str] = Field(default=None, description='Last backup completion time')
    backup_status: str = Field(default='N/A', description='Backup job status')
    failure_reason: Optional[str] = Field(default=None, description='Failure reason from AWS Backup API (StatusMessage)')


class LogBackupStatusEntry(BaseModel):
    """SSM agent / log backup status for an EC2 instance."""

    instance_id: str = Field(..., description='EC2 instance ID')
    ssm_agent_status: str = Field(default='UNKNOWN', description='SSM agent ping status')
    agent_version: Optional[str] = Field(default=None, description='SSM agent version')
    log_backup_status: Optional[str] = Field(default=None, description='HANA log backup check result')
    log_backup_details: Optional[str] = Field(default=None, description='HANA log backup check output details')


class ApplicationHealthEntry(BaseModel):
    """Health status for a single SAP application."""

    application_id: str = Field(..., description='SAP application ID')
    app_type: str = Field(default='UNKNOWN', description='Application type (HANA, SAP_ABAP, etc.)')
    status: str = Field(default='UNKNOWN', description='Application status')
    discovery_status: str = Field(default='UNKNOWN', description='Discovery status')
    component_count: int = Field(default=0, description='Number of components')
    status_message: Optional[str] = Field(default=None, description='Optional status message')
    components: List[ComponentEntry] = Field(default_factory=list, description='Component details')
    config_checks: List[ConfigCheckEntry] = Field(default_factory=list, description='Configuration check results')
    cloudwatch_metrics: List[CloudWatchMetricsEntry] = Field(default_factory=list, description='CloudWatch metrics')
    backup_status: List[BackupStatusEntry] = Field(default_factory=list, description='AWS Backup status')
    log_backup_status: List[LogBackupStatusEntry] = Field(default_factory=list, description='HANA log backup status')
    filesystem_usage: List[FilesystemUsageEntry] = Field(default_factory=list, description='Filesystem usage from SSM')


class HealthSummaryResponse(BaseModel):
    """Response from the SAP health summary tool — comprehensive status overview."""

    status: str = Field(..., description='Operation status (success or error)')
    message: str = Field(..., description='Status message or error description')
    application_count: int = Field(default=0, description='Number of applications checked')
    healthy_count: int = Field(default=0, description='Number of healthy applications')
    unhealthy_count: int = Field(default=0, description='Number of unhealthy applications')
    applications: List[ApplicationHealthEntry] = Field(default_factory=list, description='Per-application health entries')
    summary: Optional[str] = Field(default=None, description='Markdown summary')


class HealthReportResponse(BaseModel):
    """Response from the SAP health report tool — detailed downloadable report."""

    status: str = Field(..., description='Operation status (success or error)')
    message: str = Field(..., description='Status message or error description')
    report: Optional[str] = Field(default=None, description='Markdown-formatted detailed health report')
    application_count: int = Field(default=0, description='Number of applications checked')
