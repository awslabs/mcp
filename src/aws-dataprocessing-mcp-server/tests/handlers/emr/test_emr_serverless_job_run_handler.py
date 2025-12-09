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


"""Tests for EMRServerlessJobRunHandler."""

import datetime
import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_job_run_handler import (
    EMRServerlessJobRunHandler,
)
from awslabs.aws_dataprocessing_mcp_server.models.emr_models import (
    CancelJobRunResponse,
    GetDashboardForJobRunResponse,
    GetJobRunResponse,
    ListJobRunsResponse,
    StartJobRunResponse,
)
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_job_run_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = MagicMock()
        mock.prepare_resource_tags.return_value = {
            'MCP:Managed': 'true',
            'MCP:ResourceType': 'EMRServerlessJobRun',
        }
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock EMRServerlessJobRunHandler instance for testing."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    return EMRServerlessJobRunHandler(mcp, allow_write=True, allow_sensitive_data_access=True)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return MagicMock(spec=Context)


@pytest.mark.asyncio
async def test_start_job_run_success(handler, mock_context):
    """Test successful start of an EMR Serverless job run."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_job_run.return_value = {
        'jobRunId': 'job-1234567890abcdef0',
        'arn': 'arn:aws:emr-serverless:us-west-2:123456789012:application/app-1234567890abcdef0/jobrun/job-1234567890abcdef0',
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
    )

    assert isinstance(response, StartJobRunResponse)
    assert not response.isError
    assert response.job_run_id == 'job-1234567890abcdef0'
    handler.emr_serverless_client.start_job_run.assert_called_once()


@pytest.mark.asyncio
async def test_start_job_run_missing_application_id(handler, mock_context):
    """Test that starting a job run fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id=None,
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
    )

    assert response.isError
    assert (
        'application_id, execution_role_arn, and job_driver are required for start-job-run operation'
        in str(response.content[0])
    )


@pytest.mark.asyncio
async def test_start_job_run_missing_execution_role_arn(handler, mock_context):
    """Test that starting a job run fails when execution_role_arn is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn=None,
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
    )

    assert response.isError
    assert (
        'application_id, execution_role_arn, and job_driver are required for start-job-run operation'
        in str(response.content[0])
    )


@pytest.mark.asyncio
async def test_start_job_run_missing_job_driver(handler, mock_context):
    """Test that starting a job run fails when job_driver is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver=None,
    )

    assert response.isError
    assert (
        'application_id, execution_role_arn, and job_driver are required for start-job-run operation'
        in str(response.content[0])
    )


@pytest.mark.asyncio
async def test_start_job_run_error(handler, mock_context):
    """Test error handling during job run start."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_job_run.side_effect = Exception('Test exception')

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
    )

    assert response.isError
    assert 'Error in manage_aws_emr_serverless_job_runs: Test exception' in str(
        response.content[0]
    )


@pytest.mark.asyncio
async def test_get_job_run_success(handler, mock_context):
    """Test successful retrieval of an EMR Serverless job run."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_job_run.return_value = {
        'jobRun': {
            'jobRunId': 'job-1234567890abcdef0',
            'applicationId': 'app-1234567890abcdef0',
            'state': 'RUNNING',
        }
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-1234567890abcdef0',
    )

    assert isinstance(response, GetJobRunResponse)
    assert not response.isError
    assert response.job_run['jobRunId'] == 'job-1234567890abcdef0'
    assert response.job_run['applicationId'] == 'app-1234567890abcdef0'
    handler.emr_serverless_client.get_job_run.assert_called_once_with(
        applicationId='app-1234567890abcdef0', jobRunId='job-1234567890abcdef0'
    )


@pytest.mark.asyncio
async def test_get_job_run_missing_application_id(handler, mock_context):
    """Test that getting a job run fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-job-run',
        application_id=None,
        job_run_id='job-1234567890abcdef0',
    )

    assert response.isError
    assert 'application_id and job_run_id are required for get-job-run operation' in str(
        response.content[0]
    )


@pytest.mark.asyncio
async def test_get_job_run_missing_job_run_id(handler, mock_context):
    """Test that getting a job run fails when job_run_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id=None,
    )

    assert response.isError
    assert 'application_id and job_run_id are required for get-job-run operation' in str(
        response.content[0]
    )


@pytest.mark.asyncio
async def test_cancel_job_run_success(handler, mock_context):
    """Test successful cancellation of an EMR Serverless job run."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.cancel_job_run.return_value = {
        'jobRunId': 'job-1234567890abcdef0',
        'applicationId': 'app-1234567890abcdef0',
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='cancel-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-1234567890abcdef0',
    )

    assert isinstance(response, CancelJobRunResponse)
    assert not response.isError
    assert response.job_run_id == 'job-1234567890abcdef0'
    assert response.application_id == 'app-1234567890abcdef0'


@pytest.mark.asyncio
async def test_cancel_job_run_missing_application_id(handler, mock_context):
    """Test that cancelling a job run fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='cancel-job-run',
        application_id=None,
        job_run_id='job-1234567890abcdef0',
    )

    assert response.isError
    assert 'application_id and job_run_id are required for cancel-job-run operation' in str(
        response.content[0]
    )


@pytest.mark.asyncio
async def test_cancel_job_run_missing_job_run_id(handler, mock_context):
    """Test that cancelling a job run fails when job_run_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='cancel-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id=None,
    )

    assert response.isError
    assert 'application_id and job_run_id are required for cancel-job-run operation' in str(
        response.content[0]
    )


@pytest.mark.asyncio
async def test_list_job_runs_success(handler, mock_context):
    """Test successful listing of EMR Serverless job runs."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.list_job_runs.return_value = {
        'jobRuns': [
            {'jobRunId': 'job-1234567890abcdef0', 'state': 'RUNNING'},
            {'jobRunId': 'job-0987654321fedcba0', 'state': 'SUCCESS'},
        ],
        'nextToken': 'next-page-token',
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='list-job-runs',
        application_id='app-1234567890abcdef0',
        states=['RUNNING', 'SUCCESS'],
    )

    assert isinstance(response, ListJobRunsResponse)
    assert not response.isError
    assert response.count == 2
    assert response.next_token == 'next-page-token'
    handler.emr_serverless_client.list_job_runs.assert_called_once()


@pytest.mark.asyncio
async def test_list_job_runs_missing_application_id(handler, mock_context):
    """Test that listing job runs fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context, operation='list-job-runs', application_id=None
    )

    assert response.isError
    assert 'application_id is required for list-job-runs operation' in str(response.content[0])


@pytest.mark.asyncio
async def test_get_dashboard_for_job_run_success(handler, mock_context):
    """Test successful retrieval of dashboard for EMR Serverless job run."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_dashboard_for_job_run.return_value = {
        'url': 'https://console.aws.amazon.com/emr/serverless/dashboard/job-1234567890abcdef0'
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-dashboard-for-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-1234567890abcdef0',
    )

    assert isinstance(response, GetDashboardForJobRunResponse)
    assert not response.isError
    assert (
        response.url
        == 'https://console.aws.amazon.com/emr/serverless/dashboard/job-1234567890abcdef0'
    )


@pytest.mark.asyncio
async def test_get_dashboard_for_job_run_missing_application_id(handler, mock_context):
    """Test that getting dashboard fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-dashboard-for-job-run',
        application_id=None,
        job_run_id='job-1234567890abcdef0',
    )

    assert response.isError
    assert (
        'application_id and job_run_id are required for get-dashboard-for-job-run operation'
        in str(response.content[0])
    )


@pytest.mark.asyncio
async def test_get_dashboard_for_job_run_missing_job_run_id(handler, mock_context):
    """Test that getting dashboard fails when job_run_id is missing."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-dashboard-for-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id=None,
    )

    assert response.isError
    assert (
        'application_id and job_run_id are required for get-dashboard-for-job-run operation'
        in str(response.content[0])
    )


# Write access restriction tests
@pytest.mark.asyncio
async def test_start_job_run_no_write_access(mock_aws_helper, mock_context):
    """Test that starting a job run fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessJobRunHandler(mcp, allow_write=False)

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
    )

    assert response.isError
    assert 'Operation start-job-run is not allowed without write access' in str(
        response.content[0]
    )


@pytest.mark.asyncio
async def test_cancel_job_run_no_write_access(mock_aws_helper, mock_context):
    """Test that cancelling a job run fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessJobRunHandler(mcp, allow_write=False)

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='cancel-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-1234567890abcdef0',
    )

    assert response.isError
    assert 'Operation cancel-job-run is not allowed without write access' in str(
        response.content[0]
    )


# AWS permission and client error tests
@pytest.mark.asyncio
async def test_get_job_run_aws_error(handler, mock_context):
    """Test AWS client error handling for get job run."""
    from botocore.exceptions import ClientError

    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_job_run.side_effect = ClientError(
        {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Job run not found'}},
        'GetJobRun',
    )

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-nonexistent',
    )

    assert response.isError
    assert 'Error in manage_aws_emr_serverless_job_runs:' in str(response.content[0])


@pytest.mark.asyncio
async def test_start_job_run_access_denied(handler, mock_context):
    """Test AWS access denied error during job run start."""
    from botocore.exceptions import ClientError

    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_job_run.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'StartJobRun'
    )

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
    )

    assert response.isError
    assert 'Error in manage_aws_emr_serverless_job_runs:' in str(response.content[0])


# Invalid operation test
@pytest.mark.asyncio
async def test_invalid_operation(handler, mock_context):
    """Test handling of invalid operation."""
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context, operation='invalid-operation'
    )

    assert response.isError
    assert 'Invalid operation: invalid-operation' in str(response.content[0])


# Test with optional parameters
@pytest.mark.asyncio
async def test_start_job_run_with_optional_params(handler, mock_context):
    """Test starting job run with optional parameters."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_job_run.return_value = {
        'jobRunId': 'job-1234567890abcdef0'
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
        name='TestJobRun',
        configuration_overrides={
            'applicationConfiguration': [
                {'classification': 'spark-defaults', 'properties': {'key': 'value'}}
            ],
            'monitoringConfiguration': {
                's3MonitoringConfiguration': {'logUri': 's3://bucket/logs/'}
            },
        },
        execution_timeout_minutes=60,
        job_timeout_minutes=120,
        retry_policy={'maxAttempts': 3},
        mode='BATCH',
    )

    assert not response.isError
    # Verify that optional parameters were passed to the AWS call
    call_args = handler.emr_serverless_client.start_job_run.call_args[1]
    assert call_args['name'] == 'TestJobRun'
    assert call_args['configurationOverrides']['applicationConfiguration'] == [
        {'classification': 'spark-defaults', 'properties': {'key': 'value'}}
    ]
    assert call_args['executionTimeoutMinutes'] == 60
    assert call_args['jobTimeoutMinutes'] == 120
    assert call_args['retryPolicy'] == {'maxAttempts': 3}
    assert call_args['mode'] == 'BATCH'


# Test list job runs with optional parameters
@pytest.mark.asyncio
async def test_list_job_runs_with_all_params(handler, mock_context):
    """Test list job runs with all optional parameters."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.list_job_runs.return_value = {
        'jobRuns': [],
        'nextToken': None,
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='list-job-runs',
        application_id='app-1234567890abcdef0',
        next_token='test-token',
        max_results=50,
        created_at_after='2023-01-01T00:00:00Z',
        created_at_before='2023-12-31T23:59:59Z',
        states=['RUNNING', 'SUCCESS'],
        mode='BATCH',
    )

    assert not response.isError
    call_args = handler.emr_serverless_client.list_job_runs.call_args[1]
    assert call_args['nextToken'] == 'test-token'
    assert call_args['maxResults'] == 50
    assert call_args['createdAtAfter'] == '2023-01-01T00:00:00Z'
    assert call_args['createdAtBefore'] == '2023-12-31T23:59:59Z'
    assert call_args['states'] == ['RUNNING', 'SUCCESS']
    assert call_args['mode'] == 'BATCH'


# Test get dashboard with attempt parameter
@pytest.mark.asyncio
async def test_get_dashboard_for_job_run_with_attempt(handler, mock_context):
    """Test getting dashboard with attempt parameter."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_dashboard_for_job_run.return_value = {
        'url': 'https://console.aws.amazon.com/emr/serverless/dashboard/job-1234567890abcdef0'
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-dashboard-for-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-1234567890abcdef0',
        attempt=2,
    )

    assert not response.isError
    call_args = handler.emr_serverless_client.get_dashboard_for_job_run.call_args[1]
    assert call_args['attempt'] == 2


# Test start job run with all job driver types
@pytest.mark.asyncio
async def test_start_job_run_with_hive_driver(handler, mock_context):
    """Test starting job run with Hive job driver."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_job_run.return_value = {
        'jobRunId': 'job-1234567890abcdef0'
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={
            'hive': {'query': 'SELECT * FROM table', 'initQueryFile': 's3://bucket/init.sql'}
        },
    )

    assert not response.isError
    call_args = handler.emr_serverless_client.start_job_run.call_args[1]
    assert call_args['jobDriver']['hive']['query'] == 'SELECT * FROM table'
    assert call_args['jobDriver']['hive']['initQueryFile'] == 's3://bucket/init.sql'


# Test error response creation for different operations
@pytest.mark.asyncio
async def test_create_error_response_coverage(handler, mock_context):
    """Test _create_error_response for different operation types."""
    # Test get-job-run error response
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context, operation='get-job-run', application_id=None, job_run_id=None
    )
    assert response.isError
    assert 'application_id and job_run_id are required' in str(response.content[0])

    # Test cancel-job-run error response
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context, operation='cancel-job-run', application_id=None, job_run_id=None
    )
    assert response.isError
    assert 'application_id and job_run_id are required' in str(response.content[0])

    # Test list-job-runs error response
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context, operation='list-job-runs', application_id=None
    )
    assert response.isError
    assert 'application_id is required' in str(response.content[0])

    # Test get-dashboard-for-job-run error response
    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context, operation='get-dashboard-for-job-run', application_id=None, job_run_id=None
    )
    assert response.isError
    assert 'application_id and job_run_id are required' in str(response.content[0])


# Test start job run with complex configuration overrides
@pytest.mark.asyncio
async def test_start_job_run_complex_configuration(handler, mock_context):
    """Test starting job run with complex configuration overrides."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_job_run.return_value = {
        'jobRunId': 'job-1234567890abcdef0'
    }

    complex_config = {
        'applicationConfiguration': [
            {
                'classification': 'spark-defaults',
                'properties': {'spark.sql.adaptive.enabled': 'true'},
            },
            {
                'classification': 'spark-hive-site',
                'properties': {
                    'javax.jdo.option.ConnectionURL': 'jdbc:mysql://localhost/metastore'
                },
            },
        ],
        'monitoringConfiguration': {
            's3MonitoringConfiguration': {
                'logUri': 's3://my-bucket/logs/',
                'encryptionKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
            },
            'managedPersistenceMonitoringConfiguration': {
                'enabled': True,
                'encryptionKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
            },
            'cloudWatchLoggingConfiguration': {
                'enabled': True,
                'logGroupName': '/aws/emr-serverless/applications',
                'logStreamNamePrefix': 'my-job',
                'encryptionKeyArn': 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012',
                'logTypes': {'SPARK_DRIVER': ['stdout', 'stderr'], 'SPARK_EXECUTOR': ['stdout']},
            },
            'prometheusMonitoringConfiguration': {
                'remoteWriteUrl': 'https://prometheus.example.com/api/v1/remote_write'
            },
        },
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
        configuration_overrides=complex_config,
    )

    assert not response.isError
    call_args = handler.emr_serverless_client.start_job_run.call_args[1]
    assert call_args['configurationOverrides'] == complex_config


# Test list job runs with date filtering
@pytest.mark.asyncio
async def test_list_job_runs_date_filtering(handler, mock_context):
    """Test list job runs with date filtering."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.list_job_runs.return_value = {
        'jobRuns': [
            {
                'jobRunId': 'job-1234567890abcdef0',
                'state': 'SUCCESS',
                'createdAt': datetime.datetime(2023, 6, 1),
            }
        ],
        'nextToken': None,
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='list-job-runs',
        application_id='app-1234567890abcdef0',
        created_at_after='2023-05-01T00:00:00Z',
        created_at_before='2023-07-01T00:00:00Z',
    )

    assert not response.isError
    assert response.count == 1
    call_args = handler.emr_serverless_client.list_job_runs.call_args[1]
    assert call_args['createdAtAfter'] == '2023-05-01T00:00:00Z'
    assert call_args['createdAtBefore'] == '2023-07-01T00:00:00Z'


# Test ValueError exception handling
@pytest.mark.asyncio
async def test_start_job_run_value_error(handler, mock_context):
    """Test ValueError handling during job run start."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_job_run.side_effect = ValueError('Invalid parameter value')

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='start-job-run',
        application_id='app-1234567890abcdef0',
        execution_role_arn='arn:aws:iam::123456789012:role/EMRServerlessRole',
        job_driver={'sparkSubmit': {'entryPoint': 's3://bucket/script.py'}},
    )

    assert response.isError
    assert 'Invalid parameter value' in str(response.content[0])


# Test get dashboard with mode parameter
@pytest.mark.asyncio
async def test_get_dashboard_for_job_run_with_mode(handler, mock_context):
    """Test getting dashboard with mode parameter."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_dashboard_for_job_run.return_value = {
        'url': 'https://console.aws.amazon.com/emr/serverless/dashboard/job-1234567890abcdef0'
    }

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-dashboard-for-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-1234567890abcdef0',
        mode='STREAMING',
    )

    assert not response.isError
    call_args = handler.emr_serverless_client.get_dashboard_for_job_run.call_args[1]
    assert call_args['mode'] == 'STREAMING'


# Test get dashboard error handling
@pytest.mark.asyncio
async def test_get_dashboard_for_job_run_error(handler, mock_context):
    """Test error handling during get dashboard operation."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_dashboard_for_job_run.side_effect = Exception(
        'Dashboard error'
    )

    response = await handler.manage_aws_emr_serverless_job_runs(
        mock_context,
        operation='get-dashboard-for-job-run',
        application_id='app-1234567890abcdef0',
        job_run_id='job-1234567890abcdef0',
    )

    assert response.isError
    assert 'Error in manage_aws_emr_serverless_job_runs: Dashboard error' in str(
        response.content[0]
    )


# Test additional error response creation coverage
@pytest.mark.asyncio
async def test_create_error_response_additional_coverage(handler, mock_context):
    """Test _create_error_response for additional operation types."""
    # Test with an unknown operation to trigger the else clause
    response = handler._create_error_response('unknown-operation', 'Test error')
    assert response.isError
    assert isinstance(response, GetJobRunResponse)
    assert 'Test error' in str(response.content[0])
