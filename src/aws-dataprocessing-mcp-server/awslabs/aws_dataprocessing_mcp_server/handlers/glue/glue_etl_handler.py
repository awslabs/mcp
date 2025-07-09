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

"""GlueEtlJobsHandler for Data Processing MCP Server."""

import json
from awslabs.aws_dataprocessing_mcp_server.models.glue_models import (
    BatchStopJobRunResponse,
    CreateJobResponse,
    DeleteJobResponse,
    GetJobBookmarkResponse,
    GetJobResponse,
    GetJobRunResponse,
    GetJobRunsResponse,
    GetJobsResponse,
    ResetJobBookmarkResponse,
    StartJobRunResponse,
    StopJobRunResponse,
    UpdateJobResponse,
)
from awslabs.aws_dataprocessing_mcp_server.utils.aws_helper import AwsHelper
from awslabs.aws_dataprocessing_mcp_server.utils.logging_helper import (
    LogLevel,
    log_with_request_id,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from typing import Any, Dict, List, Optional, Union


class GlueEtlJobsHandler:
    """Handler for Amazon Glue ETL Jobs operations."""

    def __init__(self, mcp, allow_write: bool = False, allow_sensitive_data_access: bool = False):
        """Initialize the Glue ETL Jobs handler.

        Args:
            mcp: The MCP server instance
            allow_write: Whether to enable write access (default: False)
            allow_sensitive_data_access: Whether to allow access to sensitive data (default: False)
        """
        self.mcp = mcp
        self.allow_write = allow_write
        self.allow_sensitive_data_access = allow_sensitive_data_access
        self.glue_client = AwsHelper.create_boto3_client('glue')

        # Register tools
        self.mcp.tool(name='manage_aws_glue_jobs')(self.manage_aws_glue_jobs)

    async def manage_aws_glue_jobs(
        self,
        ctx: Context,
        operation: str = Field(
            ...,
            description='Operation to perform: create-job, delete-job, get-job, get-jobs, update-job, start-job-run, stop-job-run, get-job-run, get-job-runs, batch-stop-job-run, get-job-bookmark, reset-job-bookmark. Choose "get-job", "get-jobs", "get-job-run", "get-job-runs", or "get-job-bookmark" for read-only operations when write access is disabled.',
        ),
        job_name: Optional[str] = Field(
            None,
            description='Name of the job (required for all operations except get-jobs).',
        ),
        job_definition: Optional[Dict[str, Any]] = Field(
            None,
            description='Job definition for create-job and update-job operations. For create-job, must include Role and Command parameters.',
        ),
        job_run_id: Optional[str] = Field(
            None,
            description='Job run ID for get-job-run, stop-job-run operations, or to retry for start-job-run operation.',
        ),
        job_run_ids: Optional[List[str]] = Field(
            None,
            description='List of job run IDs for batch-stop-job-run operation.',
        ),
        job_arguments: Optional[Dict[str, str]] = Field(
            None,
            description='Job arguments for start-job-run operation. These replace the default arguments set in the job definition.',
        ),
        max_results: Optional[int] = Field(
            None,
            description='Maximum number of results to return for get-jobs or get-job-runs operations.',
        ),
        next_token: Optional[str] = Field(
            None,
            description='Pagination token for get-jobs or get-job-runs operations.',
        ),
        worker_type: Optional[str] = Field(
            None,
            description='Worker type for start-job-run operation (G.1X, G.2X, G.4X, G.8X, G.025X for Spark jobs, Z.2X for Ray jobs).',
        ),
        number_of_workers: Optional[int] = Field(
            None,
            description='Number of workers for start-job-run operation.',
        ),
        max_capacity: Optional[float] = Field(
            None,
            description='Maximum capacity in DPUs for start-job-run operation (not compatible with worker_type and number_of_workers).',
        ),
        timeout: Optional[int] = Field(
            None,
            description='Timeout in minutes for start-job-run operation.',
        ),
        security_configuration: Optional[str] = Field(
            None,
            description='Security configuration name for start-job-run operation.',
        ),
        execution_class: Optional[str] = Field(
            None,
            description='Execution class for start-job-run operation (STANDARD or FLEX).',
        ),
        job_run_queuing_enabled: Optional[bool] = Field(
            None,
            description='Whether job run queuing is enabled for start-job-run operation.',
        ),
        predecessors_included: Optional[bool] = Field(
            None,
            description='Whether to include predecessor runs in get-job-run operation.',
        ),
    ) -> Union[
        CreateJobResponse,
        DeleteJobResponse,
        GetJobResponse,
        GetJobsResponse,
        StartJobRunResponse,
        StopJobRunResponse,
        UpdateJobResponse,
        GetJobRunResponse,
        GetJobRunsResponse,
        BatchStopJobRunResponse,
        GetJobBookmarkResponse,
        ResetJobBookmarkResponse,
    ]:
        """Manage AWS Glue ETL jobs and job runs with both read and write operations.

        This tool provides comprehensive operations for managing AWS Glue ETL jobs and job runs,
        including creating, updating, retrieving, listing, starting, stopping, and monitoring jobs.

        ## Requirements
        - The server must be run with the `--allow-write` flag for create-job, delete-job, update-job, start-job-run, stop-job-run, and batch-stop-job-run operations
        - Appropriate AWS permissions for Glue ETL job operations

        ## Job Operations
        - **create-job**: Create a new ETL job in AWS Glue
        - **delete-job**: Delete an existing ETL job from AWS Glue
        - **get-job**: Retrieve detailed information about a specific job
        - **get-jobs**: List all jobs in your AWS Glue account
        - **update-job**: Update an existing job's properties
        - **start-job-run**: Start a job run using a job name

        ## Job Run Operations
        - **stop-job-run**: Stop a job run using a job name and run ID
        - **get-job-run**: Retrieve detailed information about a specific job run
        - **get-job-runs**: List all job runs for a specific job
        - **batch-stop-job-run**: Stop one or more running jobs

        ## Usage Tips
        - Job names must be unique within your AWS account and region
        - Create a script required by the customer and push the script to a customer S3 Location. Ask for S3 Location if not provided.
        - Verify if the IAM role used has glue trusted entities in the role if not update the role or create a new one
        - Job definitions should include command, role, and other required parameters
        - As rule of thumb use Glue Version 5.0 or latest to create jobs

        ## Examples
        ```
        # Create a new Spark ETL job
        {
            'operation': 'create-job',
            'job_name': 'my-etl-job',
            'job_definition': {
                'Role': 'arn:aws:iam::123456789012:role/GlueETLRole',
                'Command': {
                    'Name': 'glueetl',
                    'ScriptLocation': 's3://my-bucket/scripts/etl-script.py',
                },
                'GlueVersion': '5.0',
                'MaxRetries': 2,
                'Timeout': 120,
                'WorkerType': 'G.1X',
                'NumberOfWorkers': 5,
            },
        }

        # Start a job run
        {
            'operation': 'start-job-run',
            'job_name': 'my-etl-job',
            'worker_type': 'G.1X',
            'number_of_workers': 5,
        }

        # Get details of a specific job run
        {
            'operation': 'get-job-run',
            'job_name': 'my-etl-job',
            'job_run_id': 'jr_1234567890abcdef0',
        }
        ```

        Args:
            ctx: MCP context
            operation: Operation to perform
            job_name: Name of the job
            job_definition: Job definition for create-job and update-job operations
            job_run_id: Job run ID for get-job-run, stop-job-run operations, or to retry for start-job-run operation
            job_run_ids: List of job run IDs for batch-stop-job-run operation
            job_arguments: Job arguments for start-job-run operation
            max_results: Maximum number of results to return for get-jobs or get-job-runs operations
            next_token: Pagination token for get-jobs or get-job-runs operations
            worker_type: Worker type for start-job-run operation
            number_of_workers: Number of workers for start-job-run operation
            max_capacity: Maximum capacity in DPUs for start-job-run operation
            timeout: Timeout in minutes for start-job-run operation
            security_configuration: Security configuration name for start-job-run operation
            execution_class: Execution class for start-job-run operation
            job_run_queuing_enabled: Whether job run queuing is enabled for start-job-run operation
            predecessors_included: Whether to include predecessor runs in get-job-run operation

        Returns:
            Union of response types specific to the operation performed
        """
        try:
            log_with_request_id(
                ctx,
                LogLevel.INFO,
                f'Glue ETL Handler - Tool: manage_aws_glue_jobs_and_runs - Operation: {operation}',
            )

            # Check write access for operations that require it
            read_only_operations = [
                'get-job',
                'get-jobs',
                'get-job-run',
                'get-job-runs',
                'get-job-bookmark',
            ]
            if not self.allow_write and operation not in read_only_operations:
                error_message = f'Operation {operation} is not allowed without write access'
                log_with_request_id(ctx, LogLevel.ERROR, error_message)

                # Return appropriate error response based on operation
                if operation == 'create-job':
                    return CreateJobResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        job_name='',
                        job_id='',
                        operation='create-job',
                    )
                elif operation == 'delete-job':
                    return DeleteJobResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        job_name='',
                    )
                elif operation == 'start-job-run':
                    return StartJobRunResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        job_name='',
                        job_run_id='',
                    )
                elif operation == 'stop-job-run':
                    return StopJobRunResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        job_name='',
                        job_run_id='',
                    )
                elif operation == 'update-job':
                    return UpdateJobResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        job_name='',
                    )
                elif operation == 'batch-stop-job-run':
                    return BatchStopJobRunResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        job_name='',
                        successful_submissions=[],
                        failed_submissions=[],
                    )

            # Job operations
            if operation == 'create-job':
                if job_name is None or job_definition is None:
                    raise ValueError(
                        'job_name and job_definition are required for create-job operation'
                    )

                # Add MCP management tags to job definition
                resource_tags = AwsHelper.prepare_resource_tags('GlueJob')
                if 'Tags' in job_definition:
                    job_definition['Tags'].update(resource_tags)
                else:
                    job_definition['Tags'] = resource_tags

                # Create the job
                response = self.glue_client.create_job(Name=job_name, **job_definition)

                return CreateJobResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully created Glue job {job_name} with MCP management tags',
                        )
                    ],
                    job_name=job_name,
                    job_id=response.get('Name'),
                )

            elif operation == 'delete-job':
                if job_name is None:
                    raise ValueError('job_name is required for delete-job operation')

                # Verify that the job is managed by MCP before deleting
                # Construct the ARN for the job
                region = AwsHelper.get_aws_region() or 'us-east-1'
                account_id = AwsHelper.get_aws_account_id()
                job_arn = f'arn:aws:glue:{region}:{account_id}:job/{job_name}'

                # Get job parameters
                try:
                    response = self.glue_client.get_job(JobName=job_name)
                    job = response.get('Job', {})
                    parameters = job.get('Parameters', {})
                except ClientError:
                    parameters = {}

                # Check if the job is managed by MCP
                if not AwsHelper.is_resource_mcp_managed(self.glue_client, job_arn, parameters):
                    error_message = f'Cannot delete job {job_name} - it is not managed by the MCP server (missing required tags)'
                    log_with_request_id(ctx, LogLevel.ERROR, error_message)
                    return DeleteJobResponse(
                        isError=True,
                        content=[TextContent(type='text', text=error_message)],
                        job_name=job_name,
                    )

                # Delete the job
                self.glue_client.delete_job(JobName=job_name)

                return DeleteJobResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully deleted MCP-managed Glue job {job_name}',
                        )
                    ],
                    job_name=job_name,
                )

            elif operation == 'get-job':
                if job_name is None:
                    raise ValueError('job_name is required for get-job operation')

                # Get the job
                response = self.glue_client.get_job(JobName=job_name)

                return GetJobResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved job {job_name}',
                        )
                    ],
                    job_name=job_name,
                    job_details=response.get('Job', {}),
                )

            elif operation == 'get-jobs':
                # Prepare parameters
                params: Dict[str, Any] = {}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token

                # Get jobs
                response = self.glue_client.get_jobs(**params)

                jobs = response.get('Jobs', [])
                return GetJobsResponse(
                    isError=False,
                    content=[TextContent(type='text', text='Successfully retrieved jobs')],
                    jobs=jobs,
                    count=len(jobs),
                    next_token=response.get('NextToken'),
                    operation='list',
                )

            elif operation == 'update-job':
                if job_name is None or job_definition is None:
                    raise ValueError(
                        'job_name and job_definition are required for update-job operation'
                    )

                # Verify that the job is managed by MCP before updating
                try:
                    # Get the job to check if it's managed by MCP
                    response = self.glue_client.get_job(JobName=job_name)
                    job = response.get('Job', {})
                    parameters = job.get('Parameters', {})

                    # Construct the ARN for the job
                    region = AwsHelper.get_aws_region() or 'us-east-1'
                    account_id = AwsHelper.get_aws_account_id()
                    job_arn = f'arn:aws:glue:{region}:{account_id}:job/{job_name}'

                    # Check if the job is managed by MCP
                    if not AwsHelper.is_resource_mcp_managed(
                        self.glue_client, job_arn, parameters
                    ):
                        error_message = f'Cannot update job {job_name} - it is not managed by the MCP server (missing required tags)'
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return UpdateJobResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            job_name=job_name,
                        )

                    # Update Job does not support updating jobs
                    job_definition.pop('Tags', None)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'EntityNotFoundException':
                        error_message = f'Job {job_name} not found'
                        log_with_request_id(ctx, LogLevel.ERROR, error_message)
                        return UpdateJobResponse(
                            isError=True,
                            content=[TextContent(type='text', text=error_message)],
                            job_name=job_name,
                        )
                    else:
                        raise e

                # Update the job
                self.glue_client.update_job(JobName=job_name, JobUpdate=job_definition)

                return UpdateJobResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully updated MCP-managed job {job_name}',
                        )
                    ],
                    job_name=job_name,
                )

            elif operation == 'start-job-run':
                if job_name is None:
                    raise ValueError('job_name is required for start-job-run operation')

                # Prepare parameters
                params = {'JobName': job_name}
                if job_arguments is not None:
                    params['Arguments'] = json.dumps(job_arguments)
                if job_run_id is not None:
                    params['JobRunId'] = job_run_id
                if timeout is not None:
                    params['Timeout'] = timeout
                if security_configuration is not None:
                    params['SecurityConfiguration'] = security_configuration
                if job_run_queuing_enabled is not None:
                    params['JobRunQueuingEnabled'] = str(job_run_queuing_enabled)
                if execution_class is not None:
                    params['ExecutionClass'] = execution_class

                # Worker configuration
                if worker_type is not None and number_of_workers is not None:
                    params['WorkerType'] = worker_type
                    params['NumberOfWorkers'] = str(number_of_workers)
                elif max_capacity is not None:
                    params['MaxCapacity'] = str(max_capacity)

                # Start job run
                response = self.glue_client.start_job_run(**params)

                return StartJobRunResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully started job run for {job_name}',
                        )
                    ],
                    job_name=job_name,
                    job_run_id=response.get('JobRunId', ''),
                )

            # Job run operations
            elif operation == 'stop-job-run':
                if job_name is None or job_run_id is None:
                    raise ValueError(
                        'job_name and job_run_id are required for stop-job-run operation'
                    )

                # Stop job run
                self.glue_client.batch_stop_job_run(JobName=job_name, JobRunIds=[job_run_id])

                return StopJobRunResponse(
                    job_name=job_name,
                    job_run_id=job_run_id,
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully stopped job run {job_run_id} for job {job_name}',
                        )
                    ],
                )

            elif operation == 'get-job-run':
                if job_name is None or job_run_id is None:
                    raise ValueError(
                        'job_name and job_run_id are required for get-job-run operation'
                    )

                # Prepare parameters
                params = {'JobName': job_name, 'RunId': job_run_id}
                if predecessors_included is not None:
                    params['PredecessorsIncluded'] = str(predecessors_included)

                # Get the job run
                response = self.glue_client.get_job_run(**params)

                return GetJobRunResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved job run {job_run_id} for job {job_name}',
                        )
                    ],
                    job_name=job_name,
                    job_run_id=job_run_id,
                    job_run_details=response.get('JobRun', {}),
                )

            elif operation == 'get-job-runs':
                if job_name is None:
                    raise ValueError('job_name is required for get-job-runs operation')

                # Prepare parameters
                params: Dict[str, Any] = {'JobName': job_name}
                if max_results is not None:
                    params['MaxResults'] = max_results
                if next_token is not None:
                    params['NextToken'] = next_token

                # Get job runs
                response = self.glue_client.get_job_runs(**params)

                job_runs = response.get('JobRuns', [])
                return GetJobRunsResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved job runs for job {job_name}',
                        )
                    ],
                    job_name=job_name,
                    job_runs=job_runs,
                    count=len(job_runs),
                    next_token=response.get('NextToken'),
                    operation='list',
                )

            elif operation == 'batch-stop-job-run':
                if job_name is None:
                    raise ValueError('job_name is required for batch-stop-job-run operation')
                if job_run_id is None and job_run_ids is None:
                    raise ValueError(
                        'Either job_run_id or job_run_ids is required for batch-stop-job-run operation'
                    )

                # Prepare job run IDs
                run_ids = []
                if job_run_id is not None:
                    run_ids.append(job_run_id)
                if job_run_ids is not None:
                    run_ids.extend(job_run_ids)

                # Stop job runs
                response = self.glue_client.batch_stop_job_run(JobName=job_name, JobRunIds=run_ids)

                return BatchStopJobRunResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully processed batch stop job run request for job {job_name}',
                        )
                    ],
                    job_name=job_name,
                    successful_submissions=response.get('SuccessfulSubmissions', []),
                    failed_submissions=response.get('Errors', []),
                )

            # Job bookmark operations
            elif operation == 'get-job-bookmark':
                if job_name is None:
                    raise ValueError('job_name is required for get-job-bookmark operation')

                # Get the job bookmark
                response = self.glue_client.get_job_bookmark(JobName=job_name)

                return GetJobBookmarkResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully retrieved job bookmark for job {job_name}',
                        )
                    ],
                    job_name=job_name,
                    bookmark_details=response.get('JobBookmarkEntry', {}),
                )

            elif operation == 'reset-job-bookmark':
                if job_name is None:
                    raise ValueError('job_name is required for reset-job-bookmark operation')

                # Prepare parameters
                params = {'JobName': job_name}
                if job_run_id is not None:
                    params['RunId'] = job_run_id

                # Reset job bookmark
                self.glue_client.reset_job_bookmark(**params)

                return ResetJobBookmarkResponse(
                    isError=False,
                    content=[
                        TextContent(
                            type='text',
                            text=f'Successfully reset job bookmark for job {job_name}',
                        )
                    ],
                    job_name=job_name,
                    run_id=job_run_id,
                )

            else:
                error_message = (
                    f'Invalid operation: {operation}. Must be one of: '
                    'create-job, delete-job, get-job, get-jobs, update-job, start-job-run, '
                    'stop-job-run, get-job-run, get-job-runs, batch-stop-job-run'
                )
                log_with_request_id(ctx, LogLevel.ERROR, error_message)
                return GetJobResponse(
                    isError=True,
                    content=[TextContent(type='text', text=error_message)],
                    job_name=job_name or '',
                    job_details={},
                )

        except ValueError as e:
            log_with_request_id(ctx, LogLevel.ERROR, f'Parameter validation error: {str(e)}')
            raise
        except Exception as e:
            error_message = f'Error in manage_aws_glue_jobs_and_runs: {str(e)}'
            log_with_request_id(ctx, LogLevel.ERROR, error_message)
            return GetJobResponse(
                isError=True,
                content=[TextContent(type='text', text=error_message)],
                job_name=job_name or '',
                job_details={},
            )
