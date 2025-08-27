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

"""Tool for retrieving model import job details from Amazon Bedrock."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.llm_context import (
    build_model_import_job_details_context,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import JobStatus, ModelImportJob
from awslabs.aws_bedrock_custom_model_import_mcp_server.services.model_import_service import (
    ModelImportService,
)
from fastmcp import Context, FastMCP
from loguru import logger
from pydantic import Field
from typing import Annotated, Optional


class GetModelImportJob:
    """Tool for retrieving model import job details from Amazon Bedrock.

    This class implements the get_model_import_job tool which allows users to
    retrieve detailed information about model import jobs in Amazon Bedrock.
    It supports looking up jobs by their name and includes fuzzy matching for
    approximate name matches.

    The tool provides comprehensive job details including the job's ARN, status,
    creation time, and associated model information. It's particularly useful for
    monitoring the progress of model imports and diagnosing any issues that may
    arise during the import process.

    Attributes:
        model_import_service: The service for managing model import operations
    """

    def __init__(self, mcp: FastMCP, model_import_service: ModelImportService) -> None:
        """Initialize the get model import job tool.

        Args:
            mcp: The FastMCP instance to register the tool with
            model_import_service: The service for managing model import operations
        """
        self.model_import_service = model_import_service
        mcp.tool(self.get_model_import_job)

    async def get_model_import_job(
        self,
        ctx: Optional[Context],
        job_identifier: Annotated[str, Field(description='Name or ARN of the job')],
    ) -> str:
        """Get model import job details from Amazon Bedrock.

        This tool retrieves detailed information about a model import job in Amazon Bedrock.
        If the exact job name is not found, it will attempt to find a close match.

        ## Usage Instructions
        1. Provide the job name or ARN as the job_identifier parameter
        2. The tool will attempt to find close matches if the exact name isn't found

        ## Information Returned
        - Job status (In Progress, Completed, or Failed)
        - Creation, modification, and completion timestamps
        - Job ARN and failure message (if applicable)
        - Model details including name and ARN
        - Configuration details including role ARN, data source, VPC config, and KMS key

        ## When to Use
        - To check the status of an ongoing model import
        - To troubleshoot failed imports by examining error messages
        - To verify the configuration of a completed import
        - To get the ARN of an imported model after job completion

        ## Status Indicators
        - 🔄 In Progress: The import job is currently running
        - ✅ Completed: The import job has successfully completed
        - ❌ Failed: The import job encountered an error

        Args:
            ctx: The MCP context
            job_identifier: The name or ARN of the model import job to retrieve

        Returns:
            str: Formatted markdown text containing the job details

        Raises:
            ValueError: If job cannot be found even with approximate matching
            ClientError: If there is an error from the AWS service
        """
        try:
            job = await self.model_import_service.get_model_import_job(job_identifier)

            # Format the response
            formatted_text = self._format_response(job)

            # Add contextual information
            if ctx:
                await ctx.info('Adding contextual information about model import job details')
                formatted_text += build_model_import_job_details_context(job)

            return formatted_text
        except ValueError as e:
            if ctx:
                await ctx.error(
                    'Import job cannot be found. '
                    'Suggest user to specify the exact jobName or ARN to rety.'
                )
            raise ValueError(f'Error getting model import job: {str(e)}')
        except Exception as e:
            logger.error(f'Error getting model import job: {str(e)}')
            if ctx:
                await ctx.error(f'Error getting model import job: {str(e)}')
            raise Exception(f'Error getting model import job: {str(e)}')

    def _format_response(self, job: ModelImportJob) -> str:
        """Format the job details into a markdown string.

        Args:
            job: The job details

        Returns:
            str: The formatted job details
        """
        status_emoji = (
            '🔄'
            if job.status == JobStatus.IN_PROGRESS
            else '✅'
            if job.status == JobStatus.COMPLETED
            else '❌'
        )
        formatted_text = f'## Model Import Job: `{job.job_name}`\n\n'

        formatted_text += '### Job Details\n\n'
        formatted_text += f'- **Status**: {status_emoji} `{job.status.value}`\n'

        if job.creation_time:
            formatted_text += (
                f'- **Created**: `{job.creation_time.strftime("%Y-%m-%d %H:%M:%S")}`\n'
            )

        if job.last_modified_time:
            formatted_text += (
                f'- **Last Modified**: `{job.last_modified_time.strftime("%Y-%m-%d %H:%M:%S")}`\n'
            )

        if job.end_time:
            formatted_text += f'- **Completed**: `{job.end_time.strftime("%Y-%m-%d %H:%M:%S")}`\n'

        if job.job_arn:
            formatted_text += f'- **Job ARN**: `{job.job_arn}`\n'

        if job.failure_message:
            formatted_text += f'- **Failure Reason**: `{job.failure_message}`\n'

        formatted_text += '\n### Model Details\n\n'
        formatted_text += f'- **Model Name**: `{job.imported_model_name}`\n'
        if job.imported_model_arn:
            formatted_text += f'- **Model ARN**: `{job.imported_model_arn}`\n'

        formatted_text += '\n### Configuration\n\n'
        if job.role_arn:
            formatted_text += f'- **Role ARN**: `{job.role_arn}`\n'
        if job.model_data_source and job.model_data_source.s3_data_source:
            formatted_text += (
                f'- **Data Source**: `{job.model_data_source.s3_data_source.s3_uri}`\n'
            )

        if job.vpc_config:
            vpc_config = job.vpc_config
            subnet_ids = ', '.join(vpc_config.subnet_ids) if vpc_config.subnet_ids else 'None'
            security_groups = (
                ', '.join(vpc_config.security_group_ids)
                if vpc_config.security_group_ids
                else 'None'
            )
            formatted_text += '- **VPC Config**:\n'
            formatted_text += f'  - Subnet IDs: `{subnet_ids}`\n'
            formatted_text += f'  - Security Groups: `{security_groups}`\n'

        if job.imported_model_kms_key_arn:
            formatted_text += f'- **KMS Key ARN**: `{job.imported_model_kms_key_arn}`\n'

        return formatted_text
