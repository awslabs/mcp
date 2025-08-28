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

"""Tool for creating model import jobs in Amazon Bedrock."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.llm_context import (
    build_model_import_job_details_context,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    CreateModelImportJobRequest,
    ModelImportJob,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.services.model_import_service import (
    ModelImportService,
)
from fastmcp import Context, FastMCP
from loguru import logger
from typing import Optional


class CreateModelImportJob:
    """Tool for creating model import jobs in Amazon Bedrock.

    This class implements the create_model_import_job tool which allows users to
    initiate the import of custom models into Amazon Bedrock. It handles the creation
    of model import jobs with configurable parameters such as job name, model name,
    and optional settings like VPC configuration and tags.

    The tool validates input parameters and creates a model import job through the
    Bedrock service. It supports both basic imports with minimal configuration and
    advanced scenarios with full customization of the import process.

    Attributes:
        model_import_service: The service for managing model import operations
    """

    def __init__(self, mcp: FastMCP, model_import_service: ModelImportService) -> None:
        """Initialize the create model import job tool.

        Args:
            mcp: The FastMCP instance to register the tool with
            model_import_service: The service for managing model import operations
        """
        self.model_import_service = model_import_service
        mcp.tool(self.create_model_import_job)

    async def create_model_import_job(
        self, ctx: Optional[Context], request: CreateModelImportJobRequest
    ) -> str:
        """Create a model import job to import a model into Amazon Bedrock.

        This tool creates a model import job in Amazon Bedrock to import a custom model.
        The job name and model name are mandatory parameters. The S3 URI for the model data source
        is optional and will be automatically inferred from the model name if not provided.

        ## Usage Instructions
        1. Create descriptive job and model names based on the model you want to import
           - The tool itself will automatically add a timestamp suffix to distinguish names from multiple imports
           - Example: For a LLAMA-2 model, use "llama-2-import-job" and "llama-2" for job name and model name respectively
        2. The S3 URI is NOT required - it will be automatically inferred from the model name
        3. For advanced configurations, you can optionally specify:
           - Role ARN for permissions
           - VPC configuration for secure imports
           - KMS key for encryption
           - Tags for resource organization

        ## Best Practices
        - Use clear, descriptive names for both jobName and importedModelName
        - Name the model based on its architecture and purpose (e.g., "llama-2-7b-chat")
        - When importing multiple versions of the same model, use consistent naming with version indicators

        Args:
            ctx: The MCP context
            request: The model import job request containing job name, model name, and optional parameters

        Returns:
            str: Formatted markdown text containing the model import job details

        Raises:
            Exception: If there is an error creating the model import job
        """
        try:
            job = await self.model_import_service.create_model_import_job(request)

            # Format the response
            formatted_text = self._format_response(job)

            # Add contextual information
            if ctx:
                await ctx.info('Adding contextual information about model import jobs')
                formatted_text += build_model_import_job_details_context(job)

            return formatted_text
        except ValueError as e:
            if ctx:
                await ctx.error(
                    f'Model cannot be found in the bucket {self.model_import_service.config.aws_config.s3_bucket}. '
                    'Suggest the user to specify s3Uri to retry create_model_import_job tool.'
                )
            raise ValueError(f'Error creating model import job: {str(e)}')
        except Exception as e:
            logger.error(f'Error creating model import job: {str(e)}')
            if ctx:
                await ctx.error(f'Error creating model import job: {str(e)}')
            raise Exception(f'Error creating model import job: {str(e)}')

    def _format_response(self, job: ModelImportJob) -> str:
        """Format the response for the created model import job.

        Args:
            job: The created model import job

        Returns:
            str: Formatted markdown text containing the model import job details
        """
        formatted_text = f'## Model Import Job: `{job.job_name}`\n\n'
        formatted_text += '### Job Details\n\n'
        formatted_text += f'- **Status**: `{job.status.value}`\n'
        formatted_text += f'- **Created**: `{job.creation_time}`\n'
        formatted_text += f'- **Last Modified**: `{job.last_modified_time}`\n'

        if job.end_time:
            formatted_text += f'- **Completed**: `{job.end_time}`\n'

        if job.job_arn:
            formatted_text += f'- **Job ARN**: `{job.job_arn}`\n'

        formatted_text += '\n### Model Details\n\n'
        formatted_text += f'- **Model Name**: `{job.imported_model_name}`\n'
        formatted_text += f'- **Model ARN**: `{job.imported_model_arn}`\n'

        formatted_text += '\n### Configuration\n\n'
        formatted_text += f'- **Role ARN**: `{job.role_arn}`\n'
        formatted_text += f'- **Data Source**: `{job.model_data_source.s3_data_source.s3_uri}`\n'

        if job.vpc_config:
            formatted_text += '- **VPC Config**: Enabled\n'

        if job.imported_model_kms_key_arn:
            formatted_text += f'- **KMS Key ARN**: `{job.imported_model_kms_key_arn}`\n'
        return formatted_text
