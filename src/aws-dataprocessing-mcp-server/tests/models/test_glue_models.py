from awslabs.aws_dataprocessing_mcp_server.models.glue_models import (
    CreateClassifierResponse,
    CreateCrawlerResponse,
    CreateJobResponse,
    CreateSecurityConfigurationResponse,
    CreateSessionResponse,
    CreateTriggerResponse,
    CreateWorkflowResponse,
    DeleteJobResponse,
    GetClassifiersResponse,
    GetCrawlerMetricsResponse,
    GetJobResponse,
    GetSessionResponse,
    GetTriggersResponse,
    GetWorkflowResponse,
    ListSessionsResponse,
    ListWorkflowsResponse,
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


class TestTriggerResponses:
    """Test class for Glue trigger response models."""

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


class TestSessionResponses:
    """Test class for Glue session response models."""

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
    list_response = ListWorkflowsResponse(
        isError=False, content=sample_text_content, workflows=sample_list, next_token=None
    )
    assert list_response.next_token is None

    # Test response with optional session
    session_response = GetSessionResponse(
        isError=False, content=sample_text_content, session_id='session-123', session=None
    )
    assert session_response.session is None
