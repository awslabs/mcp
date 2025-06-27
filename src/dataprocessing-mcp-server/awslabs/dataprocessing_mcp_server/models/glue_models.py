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


from mcp.types import CallToolResult, TextContent
from pydantic import Field
from typing import Any, Dict, List, Optional


# Response models for Jobs
class CreateJobResponse(CallToolResult):
    """Response model for create job operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the created job')
    job_id: Optional[str] = Field(None, description='ID of the created job')
    operation: str = Field(default='create', description='Operation performed')


class DeleteJobResponse(CallToolResult):
    """Response model for delete job operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the deleted job')
    operation: str = Field(default='delete', description='Operation performed')


class GetJobResponse(CallToolResult):
    """Response model for get job operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    job_details: Dict[str, Any] = Field(..., description='Complete job definition')
    operation: str = Field(default='get', description='Operation performed')


class GetJobsResponse(CallToolResult):
    """Response model for get jobs operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    jobs: List[Dict[str, Any]] = Field(..., description='List of jobs')
    count: int = Field(..., description='Number of jobs found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class StartJobRunResponse(CallToolResult):
    """Response model for start job run operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    job_run_id: str = Field(..., description='ID of the job run')
    operation: str = Field(default='start_run', description='Operation performed')


class StopJobRunResponse(CallToolResult):
    """Response model for stop job run operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    job_run_id: str = Field(..., description='ID of the job run')
    operation: str = Field(default='stop_run', description='Operation performed')


class UpdateJobResponse(CallToolResult):
    """Response model for update job operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the updated job')
    operation: str = Field(default='update', description='Operation performed')


# Response models for Workflows
class CreateWorkflowResponse(CallToolResult):
    """Response model for create workflow operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    workflow_name: str = Field(..., description='Name of the created workflow')
    operation: str = Field(default='create-workflow', description='Creates a new workflow.')


class DeleteWorkflowResponse(CallToolResult):
    """Response model for delete workflow operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    workflow_name: str = Field(..., description='Name of the deleted workflow')
    operation: str = Field(default='delete-workflow', description='Deletes a workflow.')


class GetWorkflowResponse(CallToolResult):
    """Response model for get workflow operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    workflow_name: str = Field(..., description='Name of the workflow')
    workflow_details: Dict[str, Any] = Field(..., description='Complete workflow definition')
    operation: str = Field(
        default='get-workflow', description='Retrieves resource metadata for a workflow.'
    )


class ListWorkflowsResponse(CallToolResult):
    """Response model for get workflows operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    workflows: List[Dict[str, Any]] = Field(..., description='List of workflows')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(
        default='list-workflows', description='Lists names of workflows created in the account.'
    )


class StartWorkflowRunResponse(CallToolResult):
    """Response model for start workflow run operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    workflow_name: str = Field(..., description='Name of the workflow')
    run_id: str = Field(..., description='ID of the workflow run')
    operation: str = Field(
        default='start-workflow-run', description='Starts a new run of the specified workflow.'
    )


# Response models for Triggers
class CreateTriggerResponse(CallToolResult):
    """Response model for create trigger operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    trigger_name: str = Field(..., description='Name of the created trigger')
    operation: str = Field(default='create-trigger', description='Creates a new trigger.')


class DeleteTriggerResponse(CallToolResult):
    """Response model for delete trigger operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    trigger_name: str = Field(..., description='Name of the deleted trigger')
    operation: str = Field(
        default='delete-trigger',
        description='Deletes a specified trigger. If the trigger is not found, no exception is thrown.',
    )


class GetTriggerResponse(CallToolResult):
    """Response model for get trigger operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    trigger_name: str = Field(..., description='Name of the trigger')
    trigger_details: Dict[str, Any] = Field(..., description='Complete trigger definition')
    operation: str = Field(
        default='get-trigger', description='Retrieves the definition of a trigger.'
    )


class GetTriggersResponse(CallToolResult):
    """Response model for get triggers operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    triggers: List[Dict[str, Any]] = Field(..., description='List of triggers')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(
        default='get-triggers', description='Gets all the triggers associated with a job.'
    )


class StartTriggerResponse(CallToolResult):
    """Response model for start trigger operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    trigger_name: str = Field(..., description='Name of the trigger')
    operation: str = Field(default='start-trigger', description='Starts an existing trigger.')


class StopTriggerResponse(CallToolResult):
    """Response model for stop trigger operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    trigger_name: str = Field(..., description='Name of the trigger')
    operation: str = Field(default='stop-trigger', description='Stops a specified trigger.')


# Response models for Job Runs
class GetJobRunResponse(CallToolResult):
    """Response model for get job run operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    job_run_id: str = Field(..., description='ID of the job run')
    job_run_details: Dict[str, Any] = Field(..., description='Complete job run definition')
    operation: str = Field(default='get', description='Operation performed')


class GetJobRunsResponse(CallToolResult):
    """Response model for get job runs operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    job_runs: List[Dict[str, Any]] = Field(..., description='List of job runs')
    count: int = Field(..., description='Number of job runs found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class BatchStopJobRunResponse(CallToolResult):
    """Response model for batch stop job run operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    successful_submissions: List[str] = Field(
        ..., description='List of successfully stopped job run IDs'
    )
    failed_submissions: List[Dict[str, Any]] = Field(
        ..., description='List of failed stop attempts'
    )
    operation: str = Field(default='batch_stop', description='Operation performed')


# Response models for Bookmarks
class GetJobBookmarkResponse(CallToolResult):
    """Response model for get job bookmark operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    bookmark_details: Dict[str, Any] = Field(..., description='Complete bookmark definition')
    operation: str = Field(default='get', description='Operation performed')


class ResetJobBookmarkResponse(CallToolResult):
    """Response model for reset job bookmark operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    job_name: str = Field(..., description='Name of the job')
    run_id: Optional[str] = Field(None, description='ID of the job run')
    operation: str = Field(default='reset', description='Operation performed')


# Response models for Sessions
class CreateSessionResponse(CallToolResult):
    """Response model for create session operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the created session')
    session: Optional[Dict[str, Any]] = Field(None, description='Complete session object')
    operation: str = Field(default='create-session', description='Created a new session.')


class DeleteSessionResponse(CallToolResult):
    """Response model for delete session operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the deleted session')
    operation: str = Field(default='delete-session', description='Deleted the session.')


class GetSessionResponse(CallToolResult):
    """Response model for get session operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the session')
    session: Optional[Dict[str, Any]] = Field(None, description='Complete session object')
    operation: str = Field(default='get-session', description='Retrieves the session.')


class ListSessionsResponse(CallToolResult):
    """Response model for list sessions operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    sessions: List[Dict[str, Any]] = Field(..., description='List of sessions')
    ids: Optional[List[str]] = Field(None, description='List of session IDs')
    count: int = Field(..., description='Number of sessions found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list-sessions', description='Retrieve a list of sessions.')


class StopSessionResponse(CallToolResult):
    """Response model for stop session operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the stopped session')
    operation: str = Field(default='stop-session', description='Stops the session.')


# Response models for Statements
class RunStatementResponse(CallToolResult):
    """Response model for run statement operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the session')
    statement_id: int = Field(..., description='ID of the statement')
    operation: str = Field(default='run-statement', description='Executes the statement.')


class CancelStatementResponse(CallToolResult):
    """Response model for cancel statement operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the session')
    statement_id: int = Field(..., description='ID of the canceled statement')
    operation: str = Field(default='cancel-statement', description='Cancels the statement.')


class GetStatementResponse(CallToolResult):
    """Response model for get statement operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the session')
    statement_id: int = Field(..., description='ID of the statement')
    statement: Optional[Dict[str, Any]] = Field(None, description='Complete statement definition')
    operation: str = Field(default='get-statement', description='Retrieves the statement.')


class ListStatementsResponse(CallToolResult):
    """Response model for list statements operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    session_id: str = Field(..., description='ID of the session')
    statements: List[Dict[str, Any]] = Field(..., description='List of statements')
    count: int = Field(..., description='Number of statements found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(
        default='list-statements', description='Lists statements for the session.'
    )


# Response models for Usage Profiles
class CreateUsageProfileResponse(CallToolResult):
    """Response model for create usage profile operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    profile_name: str = Field(..., description='Name of the created usage profile')
    operation: str = Field(default='create', description='Operation performed')


class DeleteUsageProfileResponse(CallToolResult):
    """Response model for delete usage profile operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    profile_name: str = Field(..., description='Name of the deleted usage profile')
    operation: str = Field(default='delete', description='Operation performed')


class GetUsageProfileResponse(CallToolResult):
    """Response model for get usage profile operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    profile_name: str = Field(..., description='Name of the usage profile')
    profile_details: Dict[str, Any] = Field(..., description='Complete usage profile definition')
    operation: str = Field(default='get', description='Operation performed')


class UpdateUsageProfileResponse(CallToolResult):
    """Response model for update usage profile operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    profile_name: str = Field(..., description='Name of the updated usage profile')
    operation: str = Field(default='update', description='Operation performed')


# Response models for Security
class CreateSecurityConfigurationResponse(CallToolResult):
    """Response model for create security configuration operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    config_name: str = Field(..., description='Name of the created security configuration')
    creation_time: str = Field(..., description='Creation timestamp in ISO format')
    encryption_configuration: Dict[str, Any] = Field(
        {}, description='Encryption configuration settings'
    )
    operation: str = Field(default='create', description='Operation performed')


class DeleteSecurityConfigurationResponse(CallToolResult):
    """Response model for delete security configuration operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    config_name: str = Field(..., description='Name of the deleted security configuration')
    operation: str = Field(default='delete', description='Operation performed')


class GetSecurityConfigurationResponse(CallToolResult):
    """Response model for get security configuration operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    config_name: str = Field(..., description='Name of the security configuration')
    config_details: Dict[str, Any] = Field(
        ..., description='Complete security configuration definition'
    )
    encryption_configuration: Dict[str, Any] = Field(
        {}, description='Encryption configuration settings'
    )
    creation_time: str = Field(..., description='Creation timestamp in ISO format')
    operation: str = Field(default='get', description='Operation performed')


# Response models for Encryption
class GetDataCatalogEncryptionSettingsResponse(CallToolResult):
    """Response model for get data catalog encryption settings operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    encryption_settings: Dict[str, Any] = Field(
        ..., description='Data catalog encryption settings'
    )
    operation: str = Field(default='get', description='Operation performed')


class PutDataCatalogEncryptionSettingsResponse(CallToolResult):
    """Response model for put data catalog encryption settings operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    operation: str = Field(default='put', description='Operation performed')


# Response models for Resource Policies
class GetResourcePolicyResponse(CallToolResult):
    """Response model for get resource policy operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    policy_hash: Optional[str] = Field(None, description='Hash of the resource policy')
    policy_in_json: Optional[str] = Field(None, description='Resource policy in JSON format')
    create_time: Optional[str] = Field(None, description='Creation timestamp in ISO format')
    update_time: Optional[str] = Field(None, description='Last update timestamp in ISO format')
    operation: str = Field(default='get', description='Operation performed')


class PutResourcePolicyResponse(CallToolResult):
    """Response model for put resource policy operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    policy_hash: Optional[str] = Field(None, description='Hash of the resource policy')
    operation: str = Field(default='put', description='Operation performed')


class DeleteResourcePolicyResponse(CallToolResult):
    """Response model for delete resource policy operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    operation: str = Field(default='delete', description='Operation performed')


# Response models for Crawlers
class CreateCrawlerResponse(CallToolResult):
    """Response model for create crawler operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the created crawler')
    operation: str = Field(default='create', description='Operation performed')


class DeleteCrawlerResponse(CallToolResult):
    """Response model for delete crawler operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the deleted crawler')
    operation: str = Field(default='delete', description='Operation performed')


class GetCrawlerResponse(CallToolResult):
    """Response model for get crawler operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the crawler')
    crawler_details: Dict[str, Any] = Field(..., description='Complete crawler definition')
    operation: str = Field(default='get', description='Operation performed')


class GetCrawlersResponse(CallToolResult):
    """Response model for get crawlers operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawlers: List[Dict[str, Any]] = Field(..., description='List of crawlers')
    count: int = Field(..., description='Number of crawlers found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class StartCrawlerResponse(CallToolResult):
    """Response model for start crawler operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='start', description='Operation performed')


class StopCrawlerResponse(CallToolResult):
    """Response model for stop crawler operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='stop', description='Operation performed')


class GetCrawlerMetricsResponse(CallToolResult):
    """Response model for get crawler metrics operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_metrics: List[Dict[str, Any]] = Field(..., description='List of crawler metrics')
    count: int = Field(..., description='Number of crawler metrics found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='get_metrics', description='Operation performed')


class StartCrawlerScheduleResponse(CallToolResult):
    """Response model for start crawler schedule operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='start_schedule', description='Operation performed')


class StopCrawlerScheduleResponse(CallToolResult):
    """Response model for stop crawler schedule operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='stop_schedule', description='Operation performed')


class BatchGetCrawlersResponse(CallToolResult):
    """Response model for batch get crawlers operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawlers: List[Any] = Field(..., description='List of crawlers')
    crawlers_not_found: List[str] = Field(..., description='List of crawler names not found')
    operation: str = Field(default='batch_get', description='Operation performed')


class ListCrawlersResponse(CallToolResult):
    """Response model for list crawlers operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawlers: List[Any] = Field(..., description='List of crawlers')
    count: int = Field(..., description='Number of crawlers found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdateCrawlerResponse(CallToolResult):
    """Response model for update crawler operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the updated crawler')
    operation: str = Field(default='update', description='Operation performed')


class UpdateCrawlerScheduleResponse(CallToolResult):
    """Response model for update crawler schedule operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='update_schedule', description='Operation performed')


# Response models for Classifiers
class CreateClassifierResponse(CallToolResult):
    """Response model for create classifier operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    classifier_name: str = Field(..., description='Name of the created classifier')
    operation: str = Field(default='create', description='Operation performed')


class DeleteClassifierResponse(CallToolResult):
    """Response model for delete classifier operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    classifier_name: str = Field(..., description='Name of the deleted classifier')
    operation: str = Field(default='delete', description='Operation performed')


class GetClassifierResponse(CallToolResult):
    """Response model for get classifier operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    classifier_name: str = Field(..., description='Name of the classifier')
    classifier_details: Dict[str, Any] = Field(..., description='Complete classifier definition')
    operation: str = Field(default='get', description='Operation performed')


class GetClassifiersResponse(CallToolResult):
    """Response model for get classifiers operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    classifiers: List[Dict[str, Any]] = Field(..., description='List of classifiers')
    count: int = Field(..., description='Number of classifiers found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdateClassifierResponse(CallToolResult):
    """Response model for update classifier operation."""

    isError: bool = Field(..., description='Whether the operation resulted in an error')
    content: List[TextContent] = Field(..., description='Content of the response')
    classifier_name: str = Field(..., description='Name of the updated classifier')
    operation: str = Field(default='update', description='Operation performed')
