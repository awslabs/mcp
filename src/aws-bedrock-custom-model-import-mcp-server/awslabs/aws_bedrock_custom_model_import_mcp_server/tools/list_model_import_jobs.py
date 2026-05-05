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

"""Tool for listing model import jobs in Amazon Bedrock."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.llm_context import (
    build_list_model_import_jobs_context,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    JobStatus,
    ListModelImportJobsRequest,
    ListModelImportJobsResponse,
)
from awslabs.aws_bedrock_custom_model_import_mcp_server.services.model_import_service import (
    ModelImportService,
)
from fastmcp import Context, FastMCP
from loguru import logger
from typing import Optional


class ListModelImportJobs:
    """Tool for listing model import jobs in Amazon Bedrock.

    This class implements the list_model_import_jobs tool which allows users to
    retrieve a list of all model import jobs in Amazon Bedrock. It supports
    filtering and sorting options to help users track and monitor their import
    operations effectively.

    The tool provides a paginated list of import jobs with their status and details.
    Users can filter jobs by creation time, status, name patterns, and other criteria.
    Results can be sorted to help track recent imports or find specific jobs. This is
    particularly useful for monitoring ongoing imports and auditing past operations.

    Attributes:
        model_import_service: The service for managing model import operations
    """

    def __init__(self, mcp: FastMCP, model_import_service: ModelImportService) -> None:
        """Initialize the list model import jobs tool.

        Args:
            mcp: The FastMCP instance to register the tool with
            model_import_service: The service for managing model import operations
        """
        self.model_import_service = model_import_service
        mcp.tool(self.list_model_import_jobs)

    async def list_model_import_jobs(
        self, ctx: Optional[Context], request: Optional[ListModelImportJobsRequest] = None
    ) -> str:
        """List model import jobs in Amazon Bedrock.

        This tool retrieves a list of model import jobs in Amazon Bedrock.
        The results can be filtered and sorted using the optional request parameters.

        ## Usage Instructions
        1. Call this tool without parameters to list all model import jobs
        2. Optionally provide filtering parameters in the request:
           - creationTimeAfter: Filter jobs created after this time
           - creationTimeBefore: Filter jobs created before this time
           - statusEquals: Filter jobs by status (InProgress, Completed, Failed)
           - nameContains: Filter jobs by name substring
           - sortBy: Sort results by field (e.g., CreationTime)
           - sortOrder: Sort order (Ascending, Descending)

        ## Information Returned
        - Job name and ARN
        - Status with visual indicator (🔄 In Progress, ✅ Completed, ❌ Failed)
        - Creation and last modified times
        - Associated model name and ARN

        ## How to Use This Information
        - Monitor ongoing imports with status indicators
        - Find recently created or modified jobs
        - Identify completed jobs to access their imported models
        - Troubleshoot failed imports

        ## When to Use
        - To check the status of recent model imports
        - Before using get_model_import_job to find the exact job name
        - To monitor multiple ongoing imports
        - To verify if a specific import job exists
        - To find the job associated with a specific model

        Args:
            ctx: The MCP context
            request: Optional request parameters for filtering and sorting the results

        Returns:
            str: Formatted markdown text containing the list of jobs

        Raises:
            Exception: If there is an error listing the jobs
        """
        try:
            response = await self.model_import_service.list_model_import_jobs(request)

            # Format the response
            formatted_text = self._format_response(response)

            # Add contextual information
            if ctx:
                await ctx.info('Adding contextual information about model import jobs')
                formatted_text += build_list_model_import_jobs_context(response)

            return formatted_text
        except Exception as e:
            logger.error(f'Error listing model import jobs: {str(e)}')
            if ctx:
                await ctx.error(f'Error listing model import jobs: {str(e)}')
            raise Exception(f'Error listing model import jobs: {str(e)}')

    def _format_response(self, response: ListModelImportJobsResponse) -> str:
        """Format the list of model import jobs as markdown.

        Args:
            response: The response containing the list of jobs

        Returns:
            str: Formatted markdown text containing the list of jobs
        """
        formatted_text = '## Model Import Jobs\n\n'

        if response.model_import_job_summaries:
            formatted_text += (
                '| Job Name | Status | Created | Last Modified | Model Name | ARN |\n'
            )
            formatted_text += (
                '|----------|--------|---------|---------------|------------|-----|\n'
            )

            for job in response.model_import_job_summaries:
                model_name = job.imported_model_name if job.imported_model_name else 'N/A'
                model_arn = job.imported_model_arn if job.imported_model_arn else 'N/A'
                status_emoji = (
                    '🔄'
                    if job.status == JobStatus.IN_PROGRESS
                    else '✅'
                    if job.status == JobStatus.COMPLETED
                    else '❌'
                )
                created_time = (
                    job.creation_time.strftime('%Y-%m-%d %H:%M') if job.creation_time else 'N/A'
                )
                modified_time = (
                    job.last_modified_time.strftime('%Y-%m-%d %H:%M')
                    if job.last_modified_time
                    else 'N/A'
                )

                formatted_text += (
                    f'| `{job.job_name}` | {status_emoji} `{job.status.value}` | '
                    f'`{created_time}` | '
                    f'`{modified_time}` | '
                    f'`{model_name}` | `{model_arn}` |\n'
                )
        else:
            formatted_text += 'No model import jobs found.\n'

        return formatted_text
