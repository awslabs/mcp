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


"""Data models for EMR operations."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# Data models for EMR Instance Operations


class AddInstanceFleetData(BaseModel):
    """Data model for add instance fleet operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    instance_fleet_id: str = Field(..., description='ID of the added instance fleet')
    cluster_arn: Optional[str] = Field(None, description='ARN of the cluster')
    operation: str = Field(default='add_fleet', description='Operation performed')


class AddInstanceGroupsData(BaseModel):
    """Data model for add instance groups operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    job_flow_id: Optional[str] = Field(None, description='Job flow ID (same as cluster ID)')
    instance_group_ids: List[str] = Field(..., description='IDs of the added instance groups')
    cluster_arn: Optional[str] = Field(None, description='ARN of the cluster')
    operation: str = Field(default='add_groups', description='Operation performed')


class ModifyInstanceFleetData(BaseModel):
    """Data model for modify instance fleet operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    instance_fleet_id: str = Field(..., description='ID of the modified instance fleet')
    operation: str = Field(default='modify_fleet', description='Operation performed')


class ModifyInstanceGroupsData(BaseModel):
    """Data model for modify instance groups operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    instance_group_ids: List[str] = Field(..., description='IDs of the modified instance groups')
    operation: str = Field(default='modify_groups', description='Operation performed')


class ListInstanceFleetsData(BaseModel):
    """Data model for list instance fleets operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    instance_fleets: List[Dict[str, Any]] = Field(..., description='List of instance fleets')
    count: int = Field(..., description='Number of instance fleets found')
    marker: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class ListInstancesData(BaseModel):
    """Data model for list instances operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    instances: List[Dict[str, Any]] = Field(..., description='List of instances')
    count: int = Field(..., description='Number of instances found')
    marker: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class ListSupportedInstanceTypesData(BaseModel):
    """Data model for list supported instance types operation."""

    instance_types: List[Dict[str, Any]] = Field(
        ..., description='List of supported instance types'
    )
    count: int = Field(..., description='Number of instance types found')
    marker: Optional[str] = Field(None, description='Token for pagination')
    release_label: str = Field(..., description='EMR release label')
    operation: str = Field(default='list', description='Operation performed')


# Data models for EMR Steps Operations


class AddStepsData(BaseModel):
    """Data model for add steps operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    step_ids: List[str] = Field(..., description='IDs of the added steps')
    count: int = Field(..., description='Number of steps added')
    operation: str = Field(default='add', description='Operation performed')


class CancelStepsData(BaseModel):
    """Data model for cancel steps operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    step_cancellation_info: List[Dict[str, Any]] = Field(
        ...,
        description='Information about cancelled steps with status (SUBMITTED/FAILED) and reason',
    )
    count: int = Field(..., description='Number of steps for which cancellation was attempted')
    operation: str = Field(default='cancel', description='Operation performed')


class DescribeStepData(BaseModel):
    """Data model for describe step operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    step: Dict[str, Any] = Field(
        ...,
        description='Step details including ID, name, config, status, and execution role',
    )
    operation: str = Field(default='describe', description='Operation performed')


class ListStepsData(BaseModel):
    """Data model for list steps operation."""

    cluster_id: str = Field(..., description='ID of the EMR cluster')
    steps: List[Dict[str, Any]] = Field(
        ..., description='List of steps in reverse order (most recent first)'
    )
    count: int = Field(..., description='Number of steps found')
    marker: Optional[str] = Field(
        None, description='Pagination token for retrieving next set of results'
    )
    operation: str = Field(default='list', description='Operation performed')


# Data models for EMR Cluster Operations


class CreateClusterData(BaseModel):
    """Data model for create cluster operation."""

    cluster_id: Optional[str] = Field(default='', description='ID of the created cluster')
    cluster_arn: Optional[str] = Field(default='', description='ARN of the created cluster')
    operation: str = Field(default='create', description='Operation performed')


class DescribeClusterData(BaseModel):
    """Data model for describe cluster operation."""

    cluster: Dict[str, Any] = Field(..., description='Cluster details')
    operation: str = Field(default='describe', description='Operation performed')


class ModifyClusterData(BaseModel):
    """Data model for modify cluster operation."""

    cluster_id: str = Field(..., description='ID of the modified cluster')
    step_concurrency_level: Optional[int] = Field(None, description='Step concurrency level')
    operation: str = Field(default='modify', description='Operation performed')


class ModifyClusterAttributesData(BaseModel):
    """Data model for modify cluster attributes operation."""

    cluster_id: str = Field(..., description='ID of the cluster with modified attributes')
    operation: str = Field(default='modify_attributes', description='Operation performed')


class TerminateClustersData(BaseModel):
    """Data model for terminate clusters operation."""

    cluster_ids: List[str] = Field(..., description='IDs of the terminated clusters')
    operation: str = Field(default='terminate', description='Operation performed')


class ListClustersData(BaseModel):
    """Data model for list clusters operation."""

    clusters: List[Dict[str, Any]] = Field(..., description='List of clusters')
    count: int = Field(..., description='Number of clusters found')
    marker: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class WaitClusterData(BaseModel):
    """Data model for wait operation."""

    cluster_id: str = Field(..., description='ID of the cluster')
    state: str = Field(..., description='Current state of the cluster')
    operation: str = Field(default='wait', description='Operation performed')


# Data models for EMR Serverless Operations


class CreateApplicationData(BaseModel):
    """Data model for create EMR Serverless application operation."""

    application_id: str = Field(..., description='ID of the created application')
    name: str = Field(..., description='Name of the created application')
    arn: str = Field(..., description='ARN of the created application')
    operation: str = Field(default='create-application', description='Operation performed')


class GetApplicationData(BaseModel):
    """Data model for get EMR Serverless application operation."""

    application: Dict[str, Any] = Field(..., description='Application details')
    operation: str = Field(default='get-application', description='Operation performed')


class UpdateApplicationData(BaseModel):
    """Data model for update EMR Serverless application operation."""

    application: Dict[str, Any] = Field(..., description='Updated application details')
    operation: str = Field(default='update-application', description='Operation performed')


class DeleteApplicationData(BaseModel):
    """Data model for delete EMR Serverless application operation."""

    application_id: str = Field(..., description='ID of the deleted application')
    operation: str = Field(default='delete-application', description='Operation performed')


class ListApplicationsData(BaseModel):
    """Data model for list EMR Serverless applications operation."""

    applications: List[Dict[str, Any]] = Field(..., description='List of applications')
    count: int = Field(..., description='Number of applications found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list-applications', description='Operation performed')


class StartApplicationData(BaseModel):
    """Data model for start EMR Serverless application operation."""

    application_id: str = Field(..., description='ID of the started application')
    operation: str = Field(default='start-application', description='Operation performed')


class StopApplicationData(BaseModel):
    """Data model for stop EMR Serverless application operation."""

    application_id: str = Field(..., description='ID of the stopped application')
    operation: str = Field(default='stop-application', description='Operation performed')


class StartJobRunData(BaseModel):
    """Data model for start EMR Serverless job run operation."""

    application_id: str = Field(..., description='ID of the application')
    job_run_id: str = Field(..., description='ID of the started job run')
    arn: str = Field(..., description='ARN of the job run')
    operation: str = Field(default='start-job-run', description='Operation performed')


class GetJobRunData(BaseModel):
    """Data model for get EMR Serverless job run operation."""

    job_run: Dict[str, Any] = Field(..., description='Job run details')
    operation: str = Field(default='get-job-run', description='Operation performed')


class CancelJobRunData(BaseModel):
    """Data model for cancel EMR Serverless job run operation."""

    application_id: str = Field(..., description='ID of the application')
    job_run_id: str = Field(..., description='ID of the cancelled job run')
    operation: str = Field(default='cancel-job-run', description='Operation performed')


class ListJobRunsData(BaseModel):
    """Data model for list EMR Serverless job runs operation."""

    job_runs: List[Dict[str, Any]] = Field(..., description='List of job runs')
    count: int = Field(..., description='Number of job runs found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list-job-runs', description='Operation performed')


class GetDashboardForJobRunData(BaseModel):
    """Data model for get dashboard for EMR Serverless job run operation."""

    url: str = Field(..., description='Dashboard URL for the job run')
    operation: str = Field(default='get-dashboard-for-job-run', description='Operation performed')


class CreateSecurityConfigurationData(BaseModel):
    """Data model for create security configuration operation."""

    name: str = Field(..., description='Name of the created security configuration')
    creation_date_time: str = Field(..., description='Creation timestamp in ISO format')
    operation: str = Field(default='create', description='Operation performed')


class DeleteSecurityConfigurationData(BaseModel):
    """Data model for delete security configuration operation."""

    name: str = Field(..., description='Name of the deleted security configuration')
    operation: str = Field(default='delete', description='Operation performed')


class DescribeSecurityConfigurationData(BaseModel):
    """Data model for describe security configuration operation."""

    name: str = Field(..., description='Name of the security configuration')
    security_configuration: str = Field(..., description='Security configuration content')
    creation_date_time: str = Field(..., description='Creation timestamp in ISO format')
    operation: str = Field(default='describe', description='Operation performed')


class ListSecurityConfigurationsData(BaseModel):
    """Data model for list security configurations operation."""

    security_configurations: List[Dict[str, Any]] = Field(
        ..., description='List of security configurations'
    )
    count: int = Field(..., description='Number of security configurations found')
    marker: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')
