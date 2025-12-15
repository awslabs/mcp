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

"""EMRServerlessJobRunHandler for Data Processing MCP Server."""

from awslabs.aws_dataprocessing_mcp_server.models.emr_models import (
    CancelJobRunResponse,
    GetDashboardForJobRunResponse,
    GetJobRunResponse,
    ListJobRunsResponse,
    StartJobRunResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.consts import (
    EMR_SERVERLESS_JOB_RUN_RESOURCE_TYPE,
)
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from mcp.server.fastmcp import Context
from mcp.types import Content, TextContent
from pydantic import Field
from typing import Annotated, Any, Dict, List, Optional, Union


class EMRServerlessJobRunHandler:
    """Handler for Amazon EMR Serverless Job Run operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the EMR Serverless Job Run handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.emr_serverless_client = AwsHelper.create_boto3_client('emr-serverless')

        # Register tools
        self.mcp.tool(name='manage_aws_emr_serverless_job_runs')(
            self.manage_aws_emr_serverless_job_runs
        )

    def _create_error_response(self, operation: str, error_message: str):
        """Create appropriate error response based on operation type."""
        content: List[Content] = [TextContent(type='text', text=error_message)]

        if operation == 'start-job-run':
            return StartJobRunResponse(
                isError=True, content=content, application_id='', job_run_id='', arn=''
            )
        elif operation == 'get-job-run':
            return GetJobRunResponse(isError=True, content=content, job_run={})
        elif operation == 'cancel-job-run':
            return CancelJobRunResponse(
                isError=True, content=content, application_id='', job_run_id=''
            )
        elif operation == 'list-job-runs':
            return ListJobRunsResponse(
                isError=True, content=content, job_runs=[], count=0, next_token=None
            )
        elif operation == 'get-dashboard-for-job-run':
            return GetDashboardForJobRunResponse(isError=True, content=content, url='')
        else:
            return GetJobRunResponse(isError=True, content=content, job_run={})

    async def manage_aws_emr_serverless_job_runs(
        self,
        ctx: Context,
        operation: Annotated[
            str,
            Field(
                description='Operation to perform: start-job-run, get-job-run, cancel-job-run, list-job-runs, get-dashboard-for-job-run. Choose read-only operations when write access is disabled.',
            ),
        ],
        application_id: Annotated[
            Optional[str],
            Field(
                description='ID of the EMR Serverless application (required for all operations).',
            ),
        ] = None,
        job_run_id: Annotated[
            Optional[str],
            Field(
                description='ID of the job run (required for get-job-run, cancel-job-run, get-dashboard-for-job-run).',
            ),
        ] = None,
        execution_role_arn: Annotated[
            Optional[str],
            Field(
                description='The execution role ARN for the job run (required for start-job-run).',
            ),
        ] = None,
        job_driver: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='The job driver configuration (required for start-job-run). Example: {"sparkSubmit": {"entryPoint": "s3://bucket/script.py"}}',
            ),
        ] = None,
        configuration_overrides: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Configuration overrides for the job run (optional for start-job-run).',
            ),
        ] = None,
        tags: Annotated[
            Optional[Dict[str, str]],
            Field(
                description='Tags to apply to the job run (optional for start-job-run).',
            ),
        ] = None,
        execution_timeout_minutes: Annotated[
            Optional[int],
            Field(
                description='Maximum execution time in minutes (optional for start-job-run).',
            ),
        ] = None,
        name: Annotated[
            Optional[str],
            Field(
                description='Name for the job run (optional for start-job-run).',
            ),
        ] = None,
        client_token: Annotated[
            Optional[str],
            Field(
                description='Client token for idempotency (optional for start-job-run).',
            ),
        ] = None,
        max_results: Annotated[
            Optional[int],
            Field(
                description='Maximum number of results to return (optional for list-job-runs).',
            ),
        ] = None,
        next_token: Annotated[
            Optional[str],
            Field(
                description='Token for pagination (optional for list-job-runs).',
            ),
        ] = None,
        created_at_after: Annotated[
            Optional[str],
            Field(
                description='Filter job runs created after this timestamp (optional for list-job-runs). Format: ISO 8601',
            ),
        ] = None,
        created_at_before: Annotated[
            Optional[str],
            Field(
                description='Filter job runs created before this timestamp (optional for list-job-runs). Format: ISO 8601',
            ),
        ] = None,
        states: Annotated[
            Optional[List[str]],
            Field(
                description='Filter job runs by states (optional for list-job-runs). Valid states: SUBMITTED, PENDING, SCHEDULED, RUNNING, SUCCESS, FAILED, CANCELLING, CANCELLED',
            ),
        ] = None,
        mode: Annotated[
            Optional[str],
            Field(
                description='Mode for the dashboard (optional for get-dashboard-for-job-run).',
            ),
        ] = None,
        job_timeout_minutes: Annotated[
            Optional[int],
            Field(
                description='Job timeout in minutes (optional for start-job-run).',
            ),
        ] = None,
        retry_policy: Annotated[
            Optional[Dict[str, Any]],
            Field(
                description='Retry policy configuration (optional for start-job-run).',
            ),
        ] = None,
        attempt: Annotated[
            Optional[int],
            Field(
                description='Attempt number for dashboard (optional for get-dashboard-for-job-run).',
            ),
        ] = None,
    ) -> Union[
        StartJobRunResponse,
        GetJobRunResponse,
        CancelJobRunResponse,
        ListJobRunsResponse,
        GetDashboardForJobRunResponse,
    ]:
        """Manage AWS EMR Serverless job runs for executing data processing workloads.

        This tool provides operations for managing Amazon EMR Serverless job runs,
        including starting new jobs, monitoring execution, cancelling jobs, and accessing dashboards.

        ## Requirements
        - The server must be run with the `--allow-write` flag for start-job-run and cancel-job-run operations
        - Application must exist and be in appropriate state for job execution
        - Appropriate AWS permissions for EMR Serverless job run operations

        ## Operations
        - **start-job-run**: Start a new job run on an EMR Serverless application
        - **get-job-run**: Get detailed information about a specific job run
        - **cancel-job-run**: Cancel a running job run
        - **list-job-runs**: List job runs for an application with optional filtering
        - **get-dashboard-for-job-run**: Get the dashboard URL for monitoring a job run

        ## Example
        ```
        # Start a Spark job run
        {
            'operation': 'start-job-run',
            'application_id': '00f4ac4c0b27001f',
            'execution_role_arn': 'arn:aws:iam::123456789012:role/EMRServerlessExecutionRole',
            'job_driver': {
                'sparkSubmit': {
                    'entryPoint': 's3://my-bucket/my-spark-job.py',
                    'entryPointArguments': [
                        '--input',
                        's3://my-bucket/input/',
                        '--output',
                        's3://my-bucket/output/',
                    ],
                    'sparkSubmitParameters': '--conf spark.executor.cores=2 --conf spark.executor.memory=4g',
                }
            },
            'name': 'MySparkJob',
            'tags': {'Environment': 'Production', 'Team': 'DataEngineering'},
        }
        ```

        ## Usage Tips
        - Use list-job-runs to find job run IDs before performing operations on specific job runs
        - Check job run state before performing operations that require specific states
        - For large result sets, use pagination with next_token parameter
        - Use get-dashboard-for-job-run to get monitoring URLs for active job runs

        Args:
            ctx: MCP context for request tracking and logging
            operation: Operation to perform (start-job-run, get-job-run, cancel-job-run, list-job-runs, get-dashboard-for-job-run)
            application_id: ID of the EMR Serverless application (required for all operations)
            job_run_id: ID of the job run (required for get-job-run, cancel-job-run, get-dashboard-for-job-run)
            execution_role_arn: The execution role ARN for the job run (required for start-job-run)
            job_driver: The job driver configuration (required for start-job-run). Example: {"sparkSubmit": {"entryPoint": "s3://bucket/script.py"}}
            configuration_overrides: Configuration overrides for the job run (optional for start-job-run)
            tags: Tags to apply to the job run (optional for start-job-run)
            execution_timeout_minutes: Maximum execution time in minutes (optional for start-job-run)
            name: Name for the job run (optional for start-job-run)
            client_token: Client token for idempotency (optional for start-job-run)
            max_results: Maximum number of results to return (optional for list-job-runs)
            next_token: Token for pagination (optional for list-job-runs)
            created_at_after: Filter job runs created after this timestamp (optional for list-job-runs). Format: ISO 8601
            created_at_before: Filter job runs created before this timestamp (optional for list-job-runs). Format: ISO 8601
            states: Filter job runs by states (optional for list-job-runs). Valid states: SUBMITTED, PENDING, SCHEDULED, RUNNING, SUCCESS, FAILED, CANCELLING, CANCELLED
            mode: Mode for the dashboard (optional for get-dashboard-for-job-run)
            job_timeout_minutes: Job timeout in minutes (optional for start-job-run)
            retry_policy: Retry policy configuration (optional for start-job-run)
            attempt: Attempt number for dashboard (optional for get-dashboard-for-job-run)

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'EMR Serverless Job Run Handler - Tool: manage_aws_emr_serverless_job_runs - Operation: {operation}',
            )

            if not self.allow_write and operation in [
                'start-job-run',
                'cancel-job-run',
            ]:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return self._create_error_response(operation, error_message)

            if operation == 'start-job-run':
                # Check required parameters
                missing_params = []
                if application_id is None:
                    missing_params.append('application_id')
                if execution_role_arn is None:
                    missing_params.append('execution_role_arn')
                if job_driver is None:
                    missing_params.append('job_driver')

                if missing_params:
                    error_message = 'application_id, execution_role_arn, and job_driver are required for start-job-run operation'
                    return self._create_error_response(operation, error_message)

                # Prepare tags with MCP management tags
                resource_tags = AwsHelper.prepare_resource_tags(
                    EMR_SERVERLESS_JOB_RUN_RESOURCE_TYPE
                )
                if tags:
                    resource_tags.update(tags)

                # Prepare parameters
                params: Dict[str, Any] = {
                    'applicationId': application_id,
                    'executionRoleArn': execution_role_arn,
                    'jobDriver': job_driver,
                }

                if configuration_overrides is not None:
                    params['configurationOverrides'] = configuration_overrides
                if resource_tags:
                    params['tags'] = resource_tags
                if execution_timeout_minutes is not None:
                    params['executionTimeoutMinutes'] = execution_timeout_minutes
                if name is not None:
                    params['name'] = name
                if client_token is not None:
                    params['clientToken'] = client_token
                if job_timeout_minutes is not None:
                    params['jobTimeoutMinutes'] = job_timeout_minutes
                if retry_policy is not None:
                    params['retryPolicy'] = retry_policy
                if mode is not None:
                    params['mode'] = mode

                # Start job run
                response = self.emr_serverless_client.start_job_run(**params)

                content: List[Content] = [
                    TextContent(
                        type='text',
                        text=f'Successfully started job run {response.get("jobRunId", "")} on application {application_id} with MCP management tags',
                    )
                ]
                return StartJobRunResponse(
                    isError=False,
                    content=content,
                    application_id=application_id or '',
                    job_run_id=response.get('jobRunId', ''),
                    arn=response.get('arn', ''),
                )

            elif operation == 'get-job-run':
                if application_id is None or job_run_id is None:
                    error_message = (
                        'application_id and job_run_id are required for get-job-run operation'
                    )
                    return self._create_error_response(operation, error_message)

                # Get job run
                response = self.emr_serverless_client.get_job_run(
                    applicationId=application_id,
                    jobRunId=job_run_id,
                )

                content: List[Content] = [
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved job run {job_run_id} details',
                    )
                ]
                return GetJobRunResponse(
                    isError=False,
                    content=content,
                    job_run=response.get('jobRun', {}),
                )

            elif operation == 'cancel-job-run':
                if application_id is None or job_run_id is None:
                    error_message = (
                        'application_id and job_run_id are required for cancel-job-run operation'
                    )
                    return self._create_error_response(operation, error_message)

                # Cancel job run
                self.emr_serverless_client.cancel_job_run(
                    applicationId=application_id,
                    jobRunId=job_run_id,
                )

                content: List[Content] = [
                    TextContent(
                        type='text',
                        text=f'Successfully cancelled job run {job_run_id} on application {application_id}',
                    )
                ]
                return CancelJobRunResponse(
                    isError=False,
                    content=content,
                    application_id=application_id,
                    job_run_id=job_run_id,
                )

            elif operation == 'list-job-runs':
                if application_id is None:
                    error_message = 'application_id is required for list-job-runs operation'
                    return self._create_error_response(operation, error_message)

                # Prepare parameters
                params: Dict[str, Any] = {'applicationId': application_id}
                if max_results is not None:
                    params['maxResults'] = max_results
                if next_token is not None:
                    params['nextToken'] = next_token
                if created_at_after is not None:
                    params['createdAtAfter'] = created_at_after
                if created_at_before is not None:
                    params['createdAtBefore'] = created_at_before
                if states is not None:
                    params['states'] = states
                if mode is not None:
                    params['mode'] = mode

                # List job runs
                response = self.emr_serverless_client.list_job_runs(**params)

                job_runs = response.get('jobRuns', [])
                content: List[Content] = [
                    TextContent(type='text', text='Successfully listed EMR Serverless job runs')
                ]
                return ListJobRunsResponse(
                    isError=False,
                    content=content,
                    job_runs=job_runs,
                    count=len(job_runs),
                    next_token=response.get('nextToken'),
                )

            elif operation == 'get-dashboard-for-job-run':
                if application_id is None or job_run_id is None:
                    error_message = 'application_id and job_run_id are required for get-dashboard-for-job-run operation'
                    return self._create_error_response(operation, error_message)

                # Prepare parameters
                params = {
                    'applicationId': application_id,
                    'jobRunId': job_run_id,
                }
                if mode is not None:
                    params['mode'] = mode
                if attempt is not None:
                    params['attempt'] = attempt

                # Get dashboard URL
                response = self.emr_serverless_client.get_dashboard_for_job_run(**params)

                content: List[Content] = [
                    TextContent(
                        type='text',
                        text=f'Successfully retrieved dashboard URL for job run {job_run_id}',
                    )
                ]
                return GetDashboardForJobRunResponse(
                    isError=False,
                    content=content,
                    url=response.get('url', ''),
                )

            else:
                error_message = f'Invalid operation: {operation}. Must be one of: start-job-run, get-job-run, cancel-job-run, list-job-runs, get-dashboard-for-job-run'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return self._create_error_response('get-job-run', error_message)

        except ValueError as e:
            error_message = str(e)
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return self._create_error_response(operation, error_message)
        except Exception as e:
            error_message = f'Error in manage_aws_emr_serverless_job_runs: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return self._create_error_response(operation, error_message)
