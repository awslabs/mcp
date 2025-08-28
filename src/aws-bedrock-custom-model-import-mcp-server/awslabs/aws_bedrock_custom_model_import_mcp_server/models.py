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

"""Models for the Bedrock Custom Model Import MCP Server."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional


class S3DataSource(BaseModel):
    """S3 data source configuration."""

    s3_uri: str = Field(..., alias='s3Uri', description='S3 URI for the model data')


class ModelDataSource(BaseModel):
    """Model data source configuration."""

    s3_data_source: S3DataSource = Field(..., alias='s3DataSource')


class VpcConfig(BaseModel):
    """VPC configuration for the model import job."""

    subnet_ids: List[str] = Field(..., alias='subnetIds', description='List of subnet IDs')
    security_group_ids: List[str] = Field(
        ..., alias='securityGroupIds', description='List of security group IDs'
    )


class Tag(BaseModel):
    """Tag model for resources."""

    key: str = Field(..., description='Tag key')
    value: str = Field(..., description='Tag value')


class CreateModelImportJobRequest(BaseModel):
    """Request model for creating a model import job."""

    job_name: str = Field(
        ..., alias='jobName', description='Name of the model import job', max_length=50
    )
    imported_model_name: str = Field(
        ..., alias='importedModelName', description='Name of the model to import', max_length=50
    )
    role_arn: Optional[str] = Field(
        None, alias='roleArn', description='ARN of the IAM role for the import job'
    )
    model_data_source: Optional[ModelDataSource] = Field(
        None,
        alias='modelDataSource',
        description='Model data source configuration. This is optional, will be inferred from imported_model_name if not given',
    )
    job_tags: Optional[List[Tag]] = Field(
        default_factory=lambda: [
            Tag(key='CreatedBy', value='agent'),
        ],
        alias='jobTags',
        description='Tags for the import job',
    )
    imported_model_tags: Optional[List[Tag]] = Field(
        default_factory=lambda: [
            Tag(key='CreatedBy', value='agent'),
        ],
        alias='importedModelTags',
        description='Tags for the imported model',
    )
    client_request_token: Optional[str] = Field(
        None, alias='clientRequestToken', description='Idempotency token'
    )
    vpc_config: Optional[VpcConfig] = Field(
        None, alias='vpcConfig', description='VPC configuration'
    )
    imported_model_kms_key_id: Optional[str] = Field(
        None, alias='importedModelKmsKeyId', description='KMS key ID for the imported model'
    )


class JobStatus(str, Enum):
    """Enum for job status."""

    IN_PROGRESS = 'InProgress'
    COMPLETED = 'Completed'
    FAILED = 'Failed'


class ModelImportJobSummary(BaseModel):
    """Summary model for a model import job."""

    job_arn: str = Field(..., alias='jobArn')
    job_name: str = Field(..., alias='jobName')
    status: JobStatus = Field(...)
    last_modified_time: datetime = Field(..., alias='lastModifiedTime')
    creation_time: datetime = Field(..., alias='creationTime')
    end_time: Optional[datetime] = Field(None, alias='endTime')
    imported_model_arn: Optional[str] = Field(None, alias='importedModelArn')
    imported_model_name: Optional[str] = Field(None, alias='importedModelName')


class ModelImportJob(BaseModel):
    """Model representing a model import job."""

    job_arn: str = Field(..., alias='jobArn')
    job_name: str = Field(..., alias='jobName')
    imported_model_name: Optional[str] = Field(..., alias='importedModelName')
    imported_model_arn: Optional[str] = Field(..., alias='importedModelArn')
    role_arn: str = Field(..., alias='roleArn')
    model_data_source: ModelDataSource = Field(..., alias='modelDataSource')
    status: JobStatus = Field(...)
    failure_message: Optional[str] = Field(None, alias='failureMessage')
    creation_time: datetime = Field(..., alias='creationTime')
    last_modified_time: Optional[datetime] = Field(..., alias='lastModifiedTime')
    end_time: Optional[datetime] = Field(None, alias='endTime')
    vpc_config: Optional[VpcConfig] = Field(None, alias='vpcConfig')
    imported_model_kms_key_arn: Optional[str] = Field(None, alias='importedModelKmsKeyArn')


class CustomModelUnits(BaseModel):
    """Model representing custom model units."""

    custom_model_units_per_model_copy: int = Field(..., alias='customModelUnitsPerModelCopy')
    custom_model_units_version: str = Field(..., alias='customModelUnitsVersion')


class ImportedModel(BaseModel):
    """Model representing an imported model."""

    model_arn: str = Field(..., alias='modelArn')
    model_name: str = Field(..., alias='modelName')
    job_name: str = Field(..., alias='jobName')
    job_arn: str = Field(..., alias='jobArn')
    model_data_source: ModelDataSource = Field(..., alias='modelDataSource')
    creation_time: datetime = Field(..., alias='creationTime')
    model_architecture: str = Field(..., alias='modelArchitecture')
    model_kms_key_arn: Optional[str] = Field(None, alias='modelKmsKeyArn')
    instruct_supported: bool = Field(..., alias='instructSupported')
    custom_model_units: Optional[CustomModelUnits] = Field(..., alias='customModelUnits')


class ListModelImportJobsRequest(BaseModel):
    """Request model for listing model import jobs."""

    creation_time_after: Optional[datetime] = Field(
        None, alias='creationTimeAfter', description='Filter jobs created after this time'
    )
    creation_time_before: Optional[datetime] = Field(
        None, alias='creationTimeBefore', description='Filter jobs created before this time'
    )
    status_equals: Optional[JobStatus] = Field(
        None,
        alias='statusEquals',
        description='Filter jobs by status (InProgress, Completed, Failed)',
    )
    name_contains: Optional[str] = Field(
        None, alias='nameContains', description='Filter jobs by name substring'
    )
    sort_by: Optional[str] = Field(
        None, alias='sortBy', description='Sort results by field (CreationTime)'
    )
    sort_order: Optional[str] = Field(
        None, alias='sortOrder', description='Sort order (Ascending, Descending)'
    )


class ListModelImportJobsResponse(BaseModel):
    """Response model for listing model import jobs."""

    model_import_job_summaries: List[ModelImportJobSummary] = Field(
        ..., alias='modelImportJobSummaries', description='List of model import job summaries'
    )
    next_token: Optional[str] = Field(None, alias='nextToken', description='Token for pagination')


class ModelSummary(BaseModel):
    """Summary model for an imported model."""

    model_arn: str = Field(..., alias='modelArn')
    model_name: str = Field(..., alias='modelName')
    creation_time: datetime = Field(..., alias='creationTime')
    instruct_supported: bool = Field(..., alias='instructSupported')
    model_architecture: str = Field(..., alias='modelArchitecture')


class ListImportedModelsRequest(BaseModel):
    """Request model for listing imported models."""

    creation_time_before: Optional[datetime] = Field(
        None, alias='creationTimeBefore', description='Filter models created before this time'
    )
    creation_time_after: Optional[datetime] = Field(
        None, alias='creationTimeAfter', description='Filter models created after this time'
    )
    name_contains: Optional[str] = Field(
        None, alias='nameContains', description='Filter models by name substring'
    )
    sort_by: Optional[str] = Field(
        None, alias='sortBy', description='Sort results by field (CreationTime)'
    )
    sort_order: Optional[str] = Field(
        None, alias='sortOrder', description='Sort order (Ascending, Descending)'
    )


class ListImportedModelsResponse(BaseModel):
    """Response model for listing imported models."""

    model_summaries: List[ModelSummary] = Field(
        ..., alias='modelSummaries', description='List of model summaries'
    )
    next_token: Optional[str] = Field(None, alias='nextToken', description='Token for pagination')
