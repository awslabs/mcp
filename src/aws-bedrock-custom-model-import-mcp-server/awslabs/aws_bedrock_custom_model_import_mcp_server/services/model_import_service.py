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

"""Model import service class for Bedrock Custom Model Import MCP Server."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.client import (
    BedrockModelImportClient,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    CreateModelImportJobRequest,
    ListModelImportJobsRequest,
    ListModelImportJobsResponse,
    ModelDataSource,
    ModelImportJob,
    ModelImportJobSummary,
    S3DataSource,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.aws import (
    get_iam_role_arn_from_sts,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.utils.config import AppConfig
from datetime import datetime
from fastmcp.exceptions import ToolError
from loguru import logger
from typing import Any, Dict, Optional
from uuid import uuid4


class ModelImportService:
    """Service for model import operations."""

    def __init__(self, client: BedrockModelImportClient, config: AppConfig):
        """Initialize the service with the given client.

        Args:
            client: The Bedrock Custom Model client
            config: Configuration of the MCP server
        """
        self.client = client
        self.config = config
        logger.info('ModelImportService initialized')

    async def create_model_import_job(
        self, request: CreateModelImportJobRequest
    ) -> ModelImportJob:
        """Create a new model import job.

        Args:
            request: The request parameters

        Returns:
            ModelImportJob: The created model import job

        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If there is an error creating the model import job
        """
        # Check if write access is disabled
        if not self.config.allow_write:
            error_message = (
                'Creating model import job requires --allow-write flag in MCP server configuration'
            )
            logger.error(error_message)
            raise ToolError(error_message)

        try:
            # Get S3 bucket from environment or use model data source
            s3_bucket = self.config.aws_config.s3_bucket

            if not s3_bucket:
                raise ValueError('Please configure S3 bucket for MCP server')

            if not request.model_data_source:
                # Search for model in configured S3 bucket
                s3_uri = self.client._find_model_in_s3(s3_bucket, request.imported_model_name)
                if s3_uri:
                    request.model_data_source = ModelDataSource(
                        s3DataSource=S3DataSource(s3Uri=s3_uri)
                    )
                else:
                    error_msg = (
                        f'Model {request.imported_model_name} not found in bucket {s3_bucket}. '
                        'Please ensure model exist and weights are in .safetensors format. '
                        'Try a more specific model name or specify the model source in the request.'
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

            # Get role ARN from environment or assumed credentials if not provided
            if not request.role_arn:
                role_arn = self.config.aws_config.role_arn
                if role_arn:
                    request.role_arn = role_arn
                else:
                    request.role_arn = get_iam_role_arn_from_sts()

            # Append datetime suffix to job name and model name to prevent conflicts
            request.job_name = self._append_datetime_suffix(request.job_name)
            request.imported_model_name = self._append_datetime_suffix(request.imported_model_name)

            # Log request specifications
            logger.info(f"""Creating model import job with specifications:
                        Job Name: {request.job_name}
                        Model Name: {request.imported_model_name}
                        Model Data Source: {request.model_data_source}
                        Role ARN: {request.role_arn}
                        Job Tags: {request.job_tags if request.job_tags else 'Not specified'}
                        Model Tags: {request.imported_model_tags if request.imported_model_tags else 'Not specified'}
                        VPC Config: {request.vpc_config if request.vpc_config else 'Not specified'}
                        KMS Key ID: {request.imported_model_kms_key_id if request.imported_model_kms_key_id else 'Not specified'}""")

            # Create import job
            create_args = self._prepare_create_job_args(request)

            _ = self.client.create_model_import_job(create_args)

            job_info = self.client.get_model_import_job(request.job_name)
            return self._create_model_import_job_from_response(job_info)
        except Exception as e:
            error_msg = f'Error creating model import job: {str(e)}'
            logger.error(error_msg)
            raise

    def _prepare_create_job_args(self, request: CreateModelImportJobRequest) -> Dict[str, Any]:
        """Prepare arguments for creating a model import job.

        Args:
            request: The request parameters

        Returns:
            Dict[str, Any]: Arguments for creating the model import job
        """
        assert request.model_data_source is not None, 'Model data source is required'

        create_args = {
            'jobName': request.job_name,
            'importedModelName': request.imported_model_name,
            'modelDataSource': request.model_data_source.model_dump(by_alias=True),
            'roleArn': request.role_arn,
        }

        # Add optional parameters if provided
        if request.job_tags:
            create_args['jobTags'] = [tag.model_dump() for tag in request.job_tags]
        if request.imported_model_tags:
            create_args['importedModelTags'] = [
                tag.model_dump() for tag in request.imported_model_tags
            ]
        if request.vpc_config:
            create_args['vpcConfig'] = request.vpc_config.model_dump()
        if request.imported_model_kms_key_id:
            create_args['importedModelKmsKeyId'] = request.imported_model_kms_key_id
        if request.client_request_token:
            create_args['clientRequestToken'] = request.client_request_token
        else:
            create_args['clientRequestToken'] = str(uuid4())

        return create_args

    async def list_model_import_jobs(
        self, request: Optional[ListModelImportJobsRequest] = None
    ) -> ListModelImportJobsResponse:
        """List model import jobs.

        Args:
            request: Optional request parameters including filters and pagination

        Returns:
            ListModelImportJobsResponse: List of model import job summaries
        """
        try:
            logger.info('Listing model import jobs')
            kwargs = self._prepare_list_jobs_kwargs(request)

            response = self.client.list_model_import_jobs(**kwargs)
            summaries = [
                self._create_job_summary(job) for job in response['modelImportJobSummaries']
            ]

            logger.info(f'Found {len(summaries)} model import jobs')
            return ListModelImportJobsResponse(
                modelImportJobSummaries=summaries,
                nextToken=response.get('nextToken'),
            )
        except Exception as e:
            error_msg = f'Error listing model import jobs: {str(e)}'
            logger.error(error_msg)
            raise

    def _prepare_list_jobs_kwargs(
        self, request: Optional[ListModelImportJobsRequest]
    ) -> Dict[str, Any]:
        """Prepare kwargs for listing model import jobs.

        Args:
            request: Optional request parameters

        Returns:
            Dict[str, Any]: Kwargs for listing model import jobs
        """
        kwargs: Dict[str, Any] = {}
        if request:
            if request.status_equals:
                kwargs['statusEquals'] = request.status_equals
                logger.info(f'Filtering by status: {request.status_equals}')
            if request.creation_time_after:
                kwargs['creationTimeAfter'] = request.creation_time_after
                logger.info(f'Filtering by creation time after: {request.creation_time_after}')
            if request.creation_time_before:
                kwargs['creationTimeBefore'] = request.creation_time_before
                logger.info(f'Filtering by creation time before: {request.creation_time_before}')
            if request.name_contains:
                kwargs['nameContains'] = request.name_contains
                logger.info(f'Filtering by name contains: {request.name_contains}')
            if request.sort_by:
                kwargs['sortBy'] = request.sort_by
                logger.info(f'Sorting by: {request.sort_by}')
            if request.sort_order:
                kwargs['sortOrder'] = request.sort_order
                logger.info(f'Sort order: {request.sort_order}')
        return kwargs

    async def get_model_import_job(self, job_identifier: str) -> ModelImportJob:
        """Get model import job details.

        Args:
            job_identifier: Name or ARN of the job

        Returns:
            ModelImportJob: The model import job details

        Raises:
            ValueError: If job cannot be found
            ClientError: If there is an error from the AWS service
        """
        try:
            logger.info(f'Getting model import job details for: {job_identifier}')
            response = self.client.get_model_import_job(job_identifier)
            return self._create_model_import_job_from_response(response)
        except Exception as e:
            error_msg = f'Error getting model import job: {str(e)}'
            logger.error(error_msg)
            raise e

    def _create_model_import_job_from_response(self, job_info: Dict[str, Any]) -> ModelImportJob:
        """Create a ModelImportJob from the API response.

        Args:
            job_info: The job data from the API

        Returns:
            ModelImportJob: The model import job
        """
        return ModelImportJob(
            jobArn=job_info['jobArn'],
            jobName=job_info['jobName'],
            importedModelName=job_info.get('importedModelName'),
            importedModelArn=job_info.get('importedModelArn'),
            roleArn=job_info['roleArn'],
            modelDataSource=job_info['modelDataSource'],
            status=job_info['status'],
            failureMessage=job_info.get('failureMessage'),
            creationTime=job_info['creationTime'],
            lastModifiedTime=job_info.get('lastModifiedTime'),
            endTime=job_info.get('endTime'),
            vpcConfig=job_info.get('vpcConfig'),
            importedModelKmsKeyArn=job_info.get('importedModelKmsKeyArn'),
        )

    def _create_job_summary(self, job: Dict[str, Any]) -> ModelImportJobSummary:
        """Create a job summary from the API response.

        Args:
            job: The job data from the API

        Returns:
            ModelImportJobSummary: The job summary
        """
        return ModelImportJobSummary(
            jobArn=job['jobArn'],
            jobName=job['jobName'],
            status=job['status'],
            lastModifiedTime=job['lastModifiedTime'],
            creationTime=job['creationTime'],
            endTime=job.get('endTime'),
            importedModelArn=job.get('importedModelArn'),
            importedModelName=job.get('importedModelName'),
        )

    def _append_datetime_suffix(self, name: str) -> str:
        """Append a datetime suffix to a name to prevent conflicts.

        Args:
            name: The original name

        Returns:
            str: The name with an appended datetime suffix that complies with Bedrock naming constraints
        """
        now = datetime.now()
        datetime_suffix = now.strftime('%Y%m%d-%H%M%S')
        return f'{name}-{datetime_suffix}'
