import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_etl_handler import GlueEtlJobsHandler
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from unittest.mock import Mock, patch


@pytest.fixture
def mock_glue_client():
    """Create a mock glue client instance for testing."""
    return Mock()


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.glue_etl_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = Mock()
        mock.get_aws_region.return_value = 'us-east-1'
        mock.get_aws_account_id.return_value = '123456789012'
        mock.prepare_resource_tags.return_value = {'mcp-managed': 'true'}
        mock.is_resource_mcp_managed.return_value = True
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock GlueEtlJobsHandler instance for testing."""
    mcp = Mock()
    return GlueEtlJobsHandler(mcp, allow_write=True)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return Mock(spec=Context)


@pytest.fixture
def basic_job_definition():
    """Create a sample job definition for testing."""
    return {
        'Role': 'arn:aws:iam::123456789012:role/GlueETLRole',
        'Command': {'Name': 'glueetl', 'ScriptLocation': 's3://bucket/script.py'},
        'GlueVersion': '5.0',
    }


@pytest.mark.asyncio
async def test_create_job_success(handler, mock_glue_client):
    """Test successful creation of a Glue job."""
    handler.glue_client = mock_glue_client
    mock_glue_client.create_job.return_value = {'Name': 'test-job'}

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx,
        operation='create-job',
        job_name='test-job',
        job_definition={
            'Role': 'test-role',
            'Command': {'Name': 'glueetl', 'ScriptLocation': 's3://bucket/script.py'},
        },
    )

    assert not response.isError
    assert response.job_name == 'test-job'
    mock_glue_client.create_job.assert_called_once()


@pytest.mark.asyncio
async def test_create_job_missing_parameters(handler):
    """Test that creating a job fails when the job_name and job_definition args are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(
            ctx, operation='create-job', job_name=None, job_definition=None
        )


@pytest.mark.asyncio
async def test_delete_job_success(handler, mock_glue_client):
    """Test successful deletion of a Glue job."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job.return_value = {'Job': {'Parameters': {}}}

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(ctx, operation='delete-job', job_name='test-job')

    assert not response.isError
    mock_glue_client.delete_job.assert_called_once_with(JobName='test-job')


@pytest.mark.asyncio
async def test_get_job_success(handler, mock_glue_client):
    """Test successful retrieval of a Glue job."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job.return_value = {'Job': {'Name': 'test-job'}}

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(ctx, operation='get-job', job_name='test-job')

    assert not response.isError
    assert response.job_details == {'Name': 'test-job'}


@pytest.mark.asyncio
async def test_get_jobs_success(handler, mock_glue_client):
    """Test successful retrieval of multiple Glue jobs."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_jobs.return_value = {
        'Jobs': [{'Name': 'job1'}, {'Name': 'job2'}],
        'NextToken': 'token123',
    }

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx, operation='get-jobs', max_results=10, next_token='token'
    )

    assert not response.isError
    assert len(response.jobs) == 2
    assert response.next_token == 'token123'


@pytest.mark.asyncio
async def test_start_job_run_success(handler, mock_glue_client):
    """Test successful start of a Glue job run."""
    handler.glue_client = mock_glue_client
    mock_glue_client.start_job_run.return_value = {'JobRunId': 'run123'}

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx,
        operation='start-job-run',
        job_name='test-job',
        job_arguments=None,
        worker_type='G.1X',
        number_of_workers=2,
    )

    assert not response.isError
    assert response.job_run_id == 'run123'


@pytest.mark.asyncio
async def test_stop_job_run_success(handler, mock_glue_client):
    """Test successful termination of a Glue job run."""
    handler.glue_client = mock_glue_client

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx, operation='stop-job-run', job_name='test-job', job_run_id='run123'
    )

    assert not response.isError
    mock_glue_client.batch_stop_job_run.assert_called_once()


@pytest.mark.asyncio
async def test_create_job_operation_without_write_permission(handler):
    """Test that creating a job fails when write access is disabled."""
    handler.allow_write = False

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx,
        operation='create-job',
        job_name='test-job',
    )

    assert response.isError


@pytest.mark.asyncio
async def test_delete_job_operation_without_write_permission(handler):
    """Test that deleting a job fails when write access is disabled."""
    handler.allow_write = False

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx,
        operation='delete-job',
        job_name='test-job',
    )

    assert response.isError


@pytest.mark.asyncio
async def test_create_job_operation_invalid_arguments(handler):
    """Test that creating a job fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='create-job', job_name=None)


@pytest.mark.asyncio
async def test_delete_job_operation_invalid_arguments(handler):
    """Test that deleting a job fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='delete-job', job_name=None)


@pytest.mark.asyncio
async def test_get_job_operation_invalid_arguments(handler):
    """Test that retrieving a job fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='get-job', job_name=None)


@pytest.mark.asyncio
async def test_update_job_operation_invalid_arguments(handler):
    """Test that updating a job fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='update-job', job_name=None)


@pytest.mark.asyncio
async def test_start_job_run_operation_invalid_arguments(handler):
    """Test that starting a job run fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='start-job-run', job_name=None)


@pytest.mark.asyncio
async def test_stop_job_run_operation_invalid_arguments(handler):
    """Test that stopping a job run fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='stop-job-run', job_name=None)


@pytest.mark.asyncio
async def test_get_job_run_operation_invalid_arguments(handler):
    """Test that retrieving a job run fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='get-job-run', job_name=None)


@pytest.mark.asyncio
async def test_get_job_runs_operation_invalid_arguments(handler):
    """Test that retrieving multiple job runs fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='get-job-runs', job_name=None)


@pytest.mark.asyncio
async def test_batch_stop_job_run_operation_invalid_arguments(handler):
    """Test that stopping multiple job runs fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='batch-stop-job-run', job_name=None)


@pytest.mark.asyncio
async def test_get_job_bookmark_operation_invalid_arguments(handler):
    """Test that retrieving job bookmark details fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='get-job-bookmark', job_name=None)


@pytest.mark.asyncio
async def test_reset_job_bookmark_operation_invalid_arguments(handler):
    """Test that resetting a job bookmark fails when required arguments are missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_glue_jobs(ctx, operation='reset-job-bookmark', job_name=None)


@pytest.mark.asyncio
async def test_start_job_run_operation_without_write_permission(handler):
    """Test that starting a job run fails when write access is disabled."""
    handler.allow_write = False

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx,
        operation='start-job-run',
        job_name='test-job',
    )

    assert response.isError


@pytest.mark.asyncio
async def test_stop_job_run_operation_without_write_permission(handler):
    """Test that stopping a job run fails when write access is disabled."""
    handler.allow_write = False

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx,
        operation='stop-job-run',
        job_name='test-job',
    )

    assert response.isError


@pytest.mark.asyncio
async def test_batch_stop_job_run_operation_without_write_permission(handler):
    """Test that stopping multiple job runs fails when write access is disabled."""
    handler.allow_write = False

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx,
        operation='batch-stop-job-run',
        job_name='test-job',
    )

    assert response.isError


@pytest.mark.asyncio
async def test_update_job_operation_without_write_permission(handler):
    """Test that updating a job fails when write access is disabled."""
    handler.allow_write = False

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx, operation='update-job', job_name='test-job', job_definition={}
    )

    assert response.isError


@pytest.mark.asyncio
async def test_invalid_operation(handler):
    """Test that running manage_aws_glue_jobs with an invalid operation results in an error."""
    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(
        ctx, operation='invalid-operation', job_name='test-job'
    )

    assert response.isError


@pytest.mark.asyncio
async def test_client_error_handling(handler, mock_glue_client):
    """Test that calling get-job on a non-existent job results in an error."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job.side_effect = ClientError(
        {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}, 'GetJob'
    )

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(ctx, operation='get-job', job_name='test-job')

    assert response.isError


@pytest.mark.asyncio
async def test_update_job_does_not_exist(handler, mock_glue_client):
    """Test that calling update-job on a non-existent job results in an error."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job.side_effect = ClientError(
        {'Error': {'Code': 'EntityNotFoundException', 'Message': 'Not found'}}, 'GetJob'
    )

    ctx = Mock()
    response = await handler.manage_aws_glue_jobs(ctx, operation='update-job', job_name='test-job')

    assert response.isError


@pytest.mark.asyncio
async def test_create_job_with_tags(handler, mock_glue_client, basic_job_definition):
    """Test the creation of a job with tags."""
    handler.glue_client = mock_glue_client
    job_definition = basic_job_definition.copy()
    job_definition['Tags'] = {'custom-tag': 'value'}
    mock_glue_client.create_job.return_value = {'Name': 'test-job'}

    await handler.manage_aws_glue_jobs(
        Mock(), operation='create-job', job_name='test-job', job_definition=job_definition
    )

    # Verify tags were merged correctly
    called_args = mock_glue_client.create_job.call_args[1]
    assert 'mcp-managed' in called_args['Tags']
    assert called_args['Tags']['custom-tag'] == 'value'


@pytest.mark.asyncio
async def test_update_job_non_mcp_managed(handler, mock_glue_client, mock_aws_helper):
    """Test that attempting to update a job without the correct MCP tag results in an error."""
    handler.glue_client = mock_glue_client
    mock_aws_helper.is_resource_mcp_managed.return_value = False

    response = await handler.manage_aws_glue_jobs(
        Mock(), operation='update-job', job_name='test-job', job_definition={'Role': 'new-role'}
    )

    assert response.isError
    assert 'not managed by the MCP server' in response.content[0].text


# Job run operation tests
@pytest.mark.asyncio
async def test_start_job_run_with_all_parameters(handler, mock_glue_client):
    """Test starting a job run."""
    handler.glue_client = mock_glue_client
    mock_glue_client.start_job_run.return_value = {'JobRunId': 'run123'}

    await handler.manage_aws_glue_jobs(
        Mock(),
        operation='start-job-run',
        job_name='test-job',
        job_arguments={'--conf': 'value'},
        worker_type='G.1X',
        number_of_workers=2,
        timeout=60,
        security_configuration='sec-config',
        execution_class='STANDARD',
        job_run_queuing_enabled=True,
    )

    call_kwargs = mock_glue_client.start_job_run.call_args[1]
    assert call_kwargs['JobName'] == 'test-job'
    assert call_kwargs['WorkerType'] == 'G.1X'
    assert call_kwargs['NumberOfWorkers'] == '2'
    assert call_kwargs['Timeout'] == 60
    assert call_kwargs['SecurityConfiguration'] == 'sec-config'
    assert call_kwargs['ExecutionClass'] == 'STANDARD'
    assert call_kwargs['JobRunQueuingEnabled'] == 'True'


@pytest.mark.asyncio
async def test_start_job_run_with_max_capacity(handler, mock_glue_client):
    """Test starting a job run with an adjusted max capacity."""
    mock_glue_client.start_job_run.return_value = {
        'JobRunId': 'runid',
    }
    handler.glue_client = mock_glue_client

    await handler.manage_aws_glue_jobs(
        Mock(),
        operation='start-job-run',
        job_arguments=None,
        job_name='test-job',
        worker_type=None,
        max_capacity=10.0,
    )

    called_args = mock_glue_client.start_job_run.call_args[1]
    assert called_args['MaxCapacity'] == '10.0'


# Bookmark operation tests
@pytest.mark.asyncio
async def test_get_job_bookmark_success(handler, mock_glue_client):
    """Test retrieving details about a job bookmark."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job_bookmark.return_value = {
        'JobBookmarkEntry': {'JobName': 'test-job', 'Version': 1, 'Run': 0}
    }

    response = await handler.manage_aws_glue_jobs(
        Mock(), operation='get-job-bookmark', job_name='test-job'
    )

    assert not response.isError
    assert response.bookmark_details['JobName'] == 'test-job'


@pytest.mark.asyncio
async def test_reset_job_bookmark_with_run_id(handler, mock_glue_client):
    """Test resetting a job bookmark."""
    handler.glue_client = mock_glue_client

    response = await handler.manage_aws_glue_jobs(
        Mock(), operation='reset-job-bookmark', job_name='test-job', job_run_id='run123'
    )

    assert not response.isError
    mock_glue_client.reset_job_bookmark.assert_called_with(JobName='test-job', RunId='run123')


# Batch operations tests
@pytest.mark.asyncio
async def test_batch_stop_job_run_multiple_ids(handler, mock_glue_client):
    """Test stopping multiple job runs."""
    handler.glue_client = mock_glue_client
    mock_glue_client.batch_stop_job_run.return_value = {
        'SuccessfulSubmissions': [{'JobRunId': 'run1'}, {'JobRunId': 'run2'}],
        'Errors': [],
    }

    response = await handler.manage_aws_glue_jobs(
        Mock(), operation='batch-stop-job-run', job_name='test-job', job_run_ids=['run1', 'run2']
    )

    assert not response.isError
    assert len(response.successful_submissions) == 2
    assert len(response.failed_submissions) == 0


@pytest.mark.asyncio
async def test_batch_stop_job_run_with_failures(handler, mock_glue_client):
    """Test stopping multiple job runs with a mix of successful and failed submissions."""
    handler.glue_client = mock_glue_client
    mock_glue_client.batch_stop_job_run.return_value = {
        'SuccessfulSubmissions': [{'JobRunId': 'run1'}],
        'Errors': [{'JobRunId': 'run2', 'ErrorDetail': {'ErrorCode': 'NotFound'}}],
    }

    response = await handler.manage_aws_glue_jobs(
        Mock(), operation='batch-stop-job-run', job_name='test-job', job_run_ids=['run1', 'run2']
    )

    assert not response.isError
    assert len(response.successful_submissions) == 1
    assert len(response.failed_submissions) == 1


# Error handling tests
@pytest.mark.asyncio
async def test_get_job_runs_with_client_error(handler, mock_glue_client):
    """Test handling of internal service exception for retrieving multiple job runs."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job_runs.side_effect = ClientError(
        {'Error': {'Code': 'InternalServiceException', 'Message': 'Internal error'}}, 'GetJobRuns'
    )

    response = await handler.manage_aws_glue_jobs(
        Mock(), operation='get-job-runs', job_name='test-job'
    )

    assert response.isError
    assert 'Error in manage_aws_glue_jobs_and_runs' in response.content[0].text


@pytest.mark.asyncio
async def test_pagination_parameters(handler, mock_glue_client):
    """Test handling of pagination parameters for retrieving multiple job runs."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job_runs.return_value = {'JobRuns': [], 'NextToken': 'next-token'}

    await handler.manage_aws_glue_jobs(
        Mock(),
        operation='get-job-runs',
        job_name='test-job',
        max_results=50,
        next_token='current-token',
    )

    mock_glue_client.get_job_runs.assert_called_with(
        JobName='test-job', MaxResults=50, NextToken='current-token'
    )


# Security and validation tests
@pytest.mark.asyncio
async def test_get_job_run_with_predecessors(handler, mock_glue_client):
    """Test handling of predecessors for retrieving multiple job runs."""
    handler.glue_client = mock_glue_client
    mock_glue_client.get_job_run.return_value = {'Name': 'test-job', 'JobRun': {}}

    await handler.manage_aws_glue_jobs(
        Mock(),
        operation='get-job-run',
        job_name='test-job',
        job_run_id='run123',
        predecessors_included=True,
    )

    mock_glue_client.get_job_run.assert_called_with(
        JobName='test-job', RunId='run123', PredecessorsIncluded='True'
    )


@pytest.mark.asyncio
async def test_initialization_parameters(mock_aws_helper):
    """Test initialization of parameters for GlueEtlJobsHandler object."""
    mcp = Mock()
    handler = GlueEtlJobsHandler(mcp, allow_write=True, allow_sensitive_data_access=True)

    assert handler.allow_write
    assert handler.allow_sensitive_data_access
    assert handler.mcp == mcp


@pytest.mark.asyncio
async def test_invalid_execution_class(handler, mock_glue_client):
    """Test that passing an invalid execution class results in an error."""
    handler.glue_client = mock_glue_client
    mock_glue_client.start_job_run.side_effect = ClientError(
        {'Error': {'Code': 'ValidationException', 'Message': 'Invalid execution class'}},
        'StartJobRun',
    )

    response = await handler.manage_aws_glue_jobs(
        Mock(), operation='start-job-run', job_name='test-job', execution_class='INVALID'
    )

    assert response.isError
