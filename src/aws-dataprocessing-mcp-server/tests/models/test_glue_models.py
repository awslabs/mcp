from awslabs.aws_dataprocessing_mcp_server.models.glue_models import (
    BatchStopJobRunResponse,
    CancelStatementResponse,
    CreateClassifierResponse,
    CreateCrawlerResponse,
    CreateJobResponse,
    CreateSecurityConfigurationResponse,
    CreateSessionResponse,
    CreateTriggerResponse,
    CreateUsageProfileResponse,
    CreateWorkflowResponse,
    DeleteJobResponse,
    DeleteSessionResponse,
    DeleteTriggerResponse,
    DeleteWorkflowResponse,
    GetClassifiersResponse,
    GetCrawlerMetricsResponse,
    GetJobBookmarkResponse,
    GetJobResponse,
    GetJobRunResponse,
    GetJobRunsResponse,
    GetJobsResponse,
    GetSessionResponse,
    GetStatementResponse,
    GetTriggersResponse,
    GetWorkflowResponse,
    ListSessionsResponse,
    ListStatementsResponse,
    ListWorkflowsResponse,
    ResetJobBookmarkResponse,
    RunStatementResponse,
    StartJobRunResponse,
    StartTriggerResponse,
    StartWorkflowRunResponse,
    StopJobRunResponse,
    StopSessionResponse,
    StopTriggerResponse,
    UpdateJobResponse,
)
from mcp.types import TextContent


# Test data
sample_text_content = [TextContent(type='text', text='Test message')]
sample_dict = {'key': 'value'}
sample_list = [{'id': 1}, {'id': 2}]


class TestJobResponses:
    """Test class for Glue job response models."""

    def test_create_job_response(self):
        """Test the CreateJobResponse model."""
        response = CreateJobResponse(
            isError=False, content=sample_text_content, job_name='test-job', job_id='job-123'
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.job_id == 'job-123'
        assert response.operation == 'create'

    def test_delete_job_response(self):
        """Test the DeleteJobResponse model."""
        response = DeleteJobResponse(
            isError=False, content=sample_text_content, job_name='test-job'
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.operation == 'delete'

    def test_get_job_response(self):
        """Test the GetJobResponse model."""
        response = GetJobResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            job_details=sample_dict,
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.job_details == sample_dict
        assert response.operation == 'get'

    def test_get_jobs_response(self):
        """Test the GetJobsResponse model."""
        response = GetJobsResponse(
            isError=False,
            content=sample_text_content,
            jobs=sample_list,
            count=2,
            next_token='next-page',
        )
        assert response.isError is False
        assert response.jobs == sample_list
        assert response.count == 2
        assert response.next_token == 'next-page'
        assert response.operation == 'list'

    def test_start_job_run_response(self):
        """Test the StartJobRunResponse model."""
        response = StartJobRunResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            job_run_id='run-123',
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.job_run_id == 'run-123'
        assert response.operation == 'start_run'

    def test_stop_job_run_response(self):
        """Test the StopJobRunResponse model."""
        response = StopJobRunResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            job_run_id='run-123',
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.job_run_id == 'run-123'
        assert response.operation == 'stop_run'

    def test_update_job_response(self):
        """Test the UpdateJobResponse model."""
        response = UpdateJobResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.operation == 'update'

    def test_get_job_run_response(self):
        """Test the GetJobRunResponse model."""
        response = GetJobRunResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            job_run_id='run-123',
            job_run_details=sample_dict,
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.job_run_id == 'run-123'
        assert response.job_run_details == sample_dict
        assert response.operation == 'get'

    def test_get_job_runs_response(self):
        """Test the GetJobRunsResponse model."""
        response = GetJobRunsResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            job_runs=sample_list,
            count=2,
            next_token='next-page',
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.job_runs == sample_list
        assert response.count == 2
        assert response.next_token == 'next-page'
        assert response.operation == 'list'

    def test_batch_stop_job_run_response(self):
        """Test the BatchStopJobRunResponse model."""
        response = BatchStopJobRunResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            successful_submissions=[{'JobRunId': 'run-1'}],
            failed_submissions=[{'JobRunId': 'run-2', 'ErrorDetail': 'Error'}],
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.successful_submissions == [{'JobRunId': 'run-1'}]
        assert response.failed_submissions == [{'JobRunId': 'run-2', 'ErrorDetail': 'Error'}]
        assert response.operation == 'batch_stop'

    def test_get_job_bookmark_response(self):
        """Test the GetJobBookmarkResponse model."""
        response = GetJobBookmarkResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            bookmark_details=sample_dict,
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.bookmark_details == sample_dict
        assert response.operation == 'get'

    def test_reset_job_bookmark_response(self):
        """Test the ResetJobBookmarkResponse model."""
        response = ResetJobBookmarkResponse(
            isError=False,
            content=sample_text_content,
            job_name='test-job',
            run_id='run-123',
        )
        assert response.isError is False
        assert response.job_name == 'test-job'
        assert response.run_id == 'run-123'
        assert response.operation == 'reset'


class TestWorkflowResponses:
    """Test class for Glue workflow response models."""

    def test_create_workflow_response(self):
        """Test the CreateWorkflowResponse model."""
        response = CreateWorkflowResponse(
            isError=False, content=sample_text_content, workflow_name='test-workflow'
        )
        assert response.isError is False
        assert response.workflow_name == 'test-workflow'
        assert response.operation == 'create-workflow'

    def test_get_workflow_response(self):
        """Test the GetWorkflowResponse model."""
        response = GetWorkflowResponse(
            isError=False,
            content=sample_text_content,
            workflow_name='test-workflow',
            workflow_details=sample_dict,
        )
        assert response.isError is False
        assert response.workflow_name == 'test-workflow'
        assert response.workflow_details == sample_dict
        assert response.operation == 'get-workflow'

    def test_delete_workflow_response(self):
        """Test the DeleteWorkflowResponse model."""
        response = DeleteWorkflowResponse(
            isError=False,
            content=sample_text_content,
            workflow_name='test-workflow',
        )
        assert response.isError is False
        assert response.workflow_name == 'test-workflow'
        assert response.operation == 'delete-workflow'

    def test_start_workflow_run_response(self):
        """Test the StartWorkflowRunResponse model."""
        response = StartWorkflowRunResponse(
            isError=False,
            content=sample_text_content,
            workflow_name='test-workflow',
            run_id='run-123',
        )
        assert response.isError is False
        assert response.workflow_name == 'test-workflow'
        assert response.run_id == 'run-123'
        assert response.operation == 'start-workflow-run'


class TestTriggerResponses:
    """Test trigger response models."""

    def test_create_trigger_response(self):
        """Test the CreateTriggerResponse model."""
        response = CreateTriggerResponse(
            isError=False, content=sample_text_content, trigger_name='test-trigger'
        )
        assert response.isError is False
        assert response.trigger_name == 'test-trigger'
        assert response.operation == 'create-trigger'

    def test_get_triggers_response(self):
        """Test the GetTriggersResponse model."""
        response = GetTriggersResponse(
            isError=False,
            content=sample_text_content,
            triggers=sample_list,
            next_token='next-page',
        )
        assert response.isError is False
        assert response.triggers == sample_list
        assert response.next_token == 'next-page'
        assert response.operation == 'get-triggers'

    def test_delete_trigger_response(self):
        """Test the DeleteTriggerResponse model."""
        response = DeleteTriggerResponse(
            isError=False,
            content=sample_text_content,
            trigger_name='test-trigger',
        )
        assert response.isError is False
        assert response.trigger_name == 'test-trigger'
        assert response.operation == 'delete-trigger'

    def test_start_trigger_response(self):
        """Test the StartTriggerResponse model."""
        response = StartTriggerResponse(
            isError=False,
            content=sample_text_content,
            trigger_name='test-trigger',
        )
        assert response.isError is False
        assert response.trigger_name == 'test-trigger'
        assert response.operation == 'start-trigger'

    def test_stop_trigger_response(self):
        """Test the StopTriggerResponse model."""
        response = StopTriggerResponse(
            isError=False,
            content=sample_text_content,
            trigger_name='test-trigger',
        )
        assert response.isError is False
        assert response.trigger_name == 'test-trigger'
        assert response.operation == 'stop-trigger'


class TestSessionResponses:
    """Test session response models."""

    def test_create_session_response(self):
        """Test the CreateSessionResponse model."""
        response = CreateSessionResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
            session=sample_dict,
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.session == sample_dict
        assert response.operation == 'create-session'

    def test_list_sessions_response(self):
        """Test the ListSessionsResponse model."""
        response = ListSessionsResponse(
            isError=False,
            content=sample_text_content,
            sessions=sample_list,
            ids=['session-1', 'session-2'],
            count=2,
            next_token='next-page',
        )
        assert response.isError is False
        assert response.sessions == sample_list
        assert response.count == 2
        assert response.ids == ['session-1', 'session-2']
        assert response.next_token == 'next-page'
        assert response.operation == 'list-sessions'

    def test_get_session_response(self):
        """Test the GetSessionResponse model."""
        response = GetSessionResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
            session=sample_dict,
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.session == sample_dict
        assert response.operation == 'get-session'

    def test_delete_session_response(self):
        """Test the DeleteSessionResponse model."""
        response = DeleteSessionResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.operation == 'delete-session'

    def test_stop_session_response(self):
        """Test the StopSessionResponse model."""
        response = StopSessionResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.operation == 'stop-session'


class TestSecurityResponses:
    """Test class for Glue security configuration response models."""

    def test_create_security_configuration_response(self):
        """Test the CreateSecurityConfigurationResponse model."""
        response = CreateSecurityConfigurationResponse(
            isError=False,
            content=sample_text_content,
            config_name='test-config',
            creation_time='2023-01-01T00:00:00',
            encryption_configuration=sample_dict,
        )
        assert response.isError is False
        assert response.config_name == 'test-config'
        assert response.creation_time == '2023-01-01T00:00:00'
        assert response.encryption_configuration == sample_dict
        assert response.operation == 'create'


class TestCrawlerResponses:
    """Test class for Glue crawler response models."""

    def test_create_crawler_response(self):
        """Test the CreateCrawlerResponse model."""
        response = CreateCrawlerResponse(
            isError=False, content=sample_text_content, crawler_name='test-crawler'
        )
        assert response.isError is False
        assert response.crawler_name == 'test-crawler'
        assert response.operation == 'create'

    def test_get_crawler_metrics_response(self):
        """Test the GetCrawlerMetricsResponse model."""
        response = GetCrawlerMetricsResponse(
            isError=False,
            content=sample_text_content,
            crawler_metrics=sample_list,
            count=2,
            next_token='next-page',
        )
        assert response.isError is False
        assert response.crawler_metrics == sample_list
        assert response.count == 2
        assert response.next_token == 'next-page'
        assert response.operation == 'get_metrics'


class TestClassifierResponses:
    """Test class for Glue classifier response models."""

    def test_create_classifier_response(self):
        """Test the CreateClassifierResponse model."""
        response = CreateClassifierResponse(
            isError=False, content=sample_text_content, classifier_name='test-classifier'
        )
        assert response.isError is False
        assert response.classifier_name == 'test-classifier'
        assert response.operation == 'create'

    def test_get_classifiers_response(self):
        """Test the GetClassifiersResponse model."""
        response = GetClassifiersResponse(
            isError=False,
            content=sample_text_content,
            classifiers=sample_list,
            count=2,
            next_token='next-page',
        )
        assert response.isError is False
        assert response.classifiers == sample_list
        assert response.count == 2
        assert response.next_token == 'next-page'
        assert response.operation == 'list'


class TestStatementResponses:
    """Test class for Glue statement response models."""

    def test_run_statement_response(self):
        """Test the RunStatementResponse model."""
        response = RunStatementResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
            statement_id=1,
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.statement_id == 1
        assert response.operation == 'run-statement'

    def test_cancel_statement_response(self):
        """Test the CancelStatementResponse model."""
        response = CancelStatementResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
            statement_id=1,
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.statement_id == 1
        assert response.operation == 'cancel-statement'

    def test_get_statement_response(self):
        """Test the GetStatementResponse model."""
        response = GetStatementResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
            statement_id=1,
            statement=sample_dict,
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.statement_id == 1
        assert response.statement == sample_dict
        assert response.operation == 'get-statement'

    def test_list_statements_response(self):
        """Test the ListStatementsResponse model."""
        response = ListStatementsResponse(
            isError=False,
            content=sample_text_content,
            session_id='session-123',
            statements=sample_list,
            count=2,
            next_token='next-page',
        )
        assert response.isError is False
        assert response.session_id == 'session-123'
        assert response.statements == sample_list
        assert response.count == 2
        assert response.next_token == 'next-page'
        assert response.operation == 'list-statements'


class TestUsageProfileResponses:
    """Test class for Glue usage profile response models."""

    def test_create_usage_profile_response(self):
        """Test the CreateUsageProfileResponse model."""
        response = CreateUsageProfileResponse(
            isError=False,
            content=sample_text_content,
            profile_name='test-profile',
        )
        assert response.isError is False
        assert response.profile_name == 'test-profile'
        assert response.operation == 'create'


def test_error_responses():
    """Test error cases for various response types."""
    error_content = [TextContent(type='text', text='Error occurred')]

    # Test job error response
    job_error = CreateJobResponse(
        isError=True, content=error_content, job_name='test-job', job_id=None
    )
    assert job_error.isError is True
    assert job_error.content == error_content

    # Test workflow error response
    workflow_error = CreateWorkflowResponse(
        isError=True, content=error_content, workflow_name='test-workflow'
    )
    assert workflow_error.isError is True
    assert workflow_error.content == error_content


def test_optional_fields():
    """Test responses with optional fields."""
    # Test response with optional next_token
    list_response = ListWorkflowsResponse(
        isError=False, content=sample_text_content, workflows=sample_list, next_token=None
    )
    assert list_response.next_token is None

    # Test response with optional session
    session_response = GetSessionResponse(
        isError=False, content=sample_text_content, session_id='session-123', session=None
    )
    assert session_response.session is None
