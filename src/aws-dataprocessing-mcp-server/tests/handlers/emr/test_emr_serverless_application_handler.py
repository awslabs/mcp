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


"""Tests for EMRServerlessApplicationHandler."""

import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_application_handler import (
    EMRServerlessApplicationHandler,
)
from awslabs.aws_dataprocessing_mcp_server.models.emr_models import (
    CreateApplicationResponse,
    DeleteApplicationResponse,
    GetApplicationResponse,
    ListApplicationsResponse,
    StartApplicationResponse,
    StopApplicationResponse,
    UpdateApplicationResponse,
)
from mcp.server.fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.emr.emr_serverless_application_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = MagicMock()
        mock.prepare_resource_tags.return_value = {
            'MCP:Managed': 'true',
            'MCP:ResourceType': 'EMRServerlessApplication',
        }
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock EMRServerlessApplicationHandler instance for testing."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    return EMRServerlessApplicationHandler(mcp, allow_write=True, allow_sensitive_data_access=True)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return MagicMock(spec=Context)


@pytest.mark.asyncio
async def test_create_application_success(handler, mock_context):
    """Test successful creation of an EMR Serverless application."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.create_application.return_value = {
        'applicationId': 'app-1234567890abcdef0',
        'name': 'TestApplication',
        'arn': 'arn:aws:emr-serverless:us-west-2:123456789012:application/app-1234567890abcdef0',
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label='emr-7.9.0',
        type='Spark',
    )

    assert isinstance(response, CreateApplicationResponse)
    assert not response.isError
    assert response.application_id == 'app-1234567890abcdef0'
    assert response.name == 'TestApplication'
    handler.emr_serverless_client.create_application.assert_called_once()


@pytest.mark.asyncio
async def test_create_application_missing_name(handler, mock_context):
    """Test that creating an application fails when name is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name=None,
        release_label='emr-7.9.0',
        type='Spark',
    )

    assert response.isError
    assert (
        'name, release_label, and type are required for create-application operation'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_create_application_missing_release_label(handler, mock_context):
    """Test that creating an application fails when release_label is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label=None,
        type='Spark',
    )

    assert response.isError
    assert (
        'name, release_label, and type are required for create-application operation'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_create_application_missing_type(handler, mock_context):
    """Test that creating an application fails when type is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label='emr-7.9.0',
        type=None,
    )

    assert response.isError
    assert (
        'name, release_label, and type are required for create-application operation'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_create_application_error(handler, mock_context):
    """Test error handling during application creation."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.create_application.side_effect = Exception('Test exception')

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label='emr-7.9.0',
        type='Spark',
    )

    assert response.isError
    assert (
        'Error in manage_aws_emr_serverless_applications: Test exception'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_get_application_success(handler, mock_context):
    """Test successful retrieval of an EMR Serverless application."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_application.return_value = {
        'application': {
            'applicationId': 'app-1234567890abcdef0',
            'name': 'TestApplication',
            'state': 'CREATED',
            'type': 'Spark',
        }
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='get-application', application_id='app-1234567890abcdef0'
    )

    assert isinstance(response, GetApplicationResponse)
    assert not response.isError
    assert response.application['applicationId'] == 'app-1234567890abcdef0'
    assert response.application['name'] == 'TestApplication'
    handler.emr_serverless_client.get_application.assert_called_once_with(
        applicationId='app-1234567890abcdef0'
    )


@pytest.mark.asyncio
async def test_get_application_missing_id(handler, mock_context):
    """Test that getting an application fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='get-application', application_id=None
    )

    assert response.isError
    assert 'application_id is required for get-application operation' in response.content[0].text


@pytest.mark.asyncio
async def test_update_application_success(handler, mock_context):
    """Test successful update of an EMR Serverless application."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.update_application.return_value = {
        'application': {
            'applicationId': 'app-1234567890abcdef0',
            'name': 'UpdatedApplication',
        }
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='update-application',
        application_id='app-1234567890abcdef0',
        name='UpdatedApplication',
    )

    assert isinstance(response, UpdateApplicationResponse)
    assert not response.isError
    assert response.application['applicationId'] == 'app-1234567890abcdef0'
    assert response.application['name'] == 'UpdatedApplication'


@pytest.mark.asyncio
async def test_update_application_unmanaged(handler, mock_aws_helper, mock_context):
    """Test that updating unmanaged application fails."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.return_value = {
        'is_valid': False,
        'error_message': 'is not managed by MCP (missing required tags)',
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='update-application',
        application_id='app-1234567890abcdef0',
        name='UpdatedApplication',
    )

    assert response.isError
    assert 'Cannot update application' in response.content[0].text
    assert 'not managed by MCP' in response.content[0].text


@pytest.mark.asyncio
async def test_update_application_missing_id(handler, mock_context):
    """Test that updating an application fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='update-application', application_id=None
    )

    assert response.isError
    assert (
        'application_id is required for update-application operation' in response.content[0].text
    )


@pytest.mark.asyncio
async def test_delete_application_success(handler, mock_context):
    """Test successful deletion of an EMR Serverless application."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.delete_application.return_value = {}

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='delete-application',
        application_id='app-1234567890abcdef0',
    )

    assert isinstance(response, DeleteApplicationResponse)
    assert not response.isError
    assert response.application_id == 'app-1234567890abcdef0'


@pytest.mark.asyncio
async def test_delete_application_unmanaged(handler, mock_aws_helper, mock_context):
    """Test that deleting unmanaged application fails."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.return_value = {
        'is_valid': False,
        'error_message': 'is not managed by MCP (missing required tags)',
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='delete-application',
        application_id='app-1234567890abcdef0',
    )

    assert response.isError
    assert 'Cannot delete application' in response.content[0].text
    assert 'not managed by MCP' in response.content[0].text


@pytest.mark.asyncio
async def test_delete_application_missing_id(handler, mock_context):
    """Test that deleting an application fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='delete-application', application_id=None
    )

    assert response.isError
    assert (
        'application_id is required for delete-application operation' in response.content[0].text
    )


@pytest.mark.asyncio
async def test_list_applications_success(handler, mock_context):
    """Test successful listing of EMR Serverless applications."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.list_applications.return_value = {
        'applications': [
            {'applicationId': 'app-1234567890abcdef0', 'name': 'App1', 'state': 'CREATED'},
            {'applicationId': 'app-0987654321fedcba0', 'name': 'App2', 'state': 'STARTED'},
        ],
        'nextToken': 'next-page-token',
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='list-applications', states=['CREATED', 'STARTED']
    )

    assert isinstance(response, ListApplicationsResponse)
    assert not response.isError
    assert response.count == 2
    assert response.next_token == 'next-page-token'
    handler.emr_serverless_client.list_applications.assert_called_once()


@pytest.mark.asyncio
async def test_start_application_success(handler, mock_context):
    """Test successful start of an EMR Serverless application."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.start_application.return_value = {}

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='start-application',
        application_id='app-1234567890abcdef0',
    )

    assert isinstance(response, StartApplicationResponse)
    assert not response.isError
    assert response.application_id == 'app-1234567890abcdef0'


@pytest.mark.asyncio
async def test_start_application_unmanaged(handler, mock_aws_helper, mock_context):
    """Test that starting unmanaged application fails."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.return_value = {
        'is_valid': False,
        'error_message': 'is not managed by MCP (missing required tags)',
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='start-application',
        application_id='app-1234567890abcdef0',
    )

    assert response.isError
    assert 'Cannot start application' in response.content[0].text
    assert 'not managed by MCP' in response.content[0].text


@pytest.mark.asyncio
async def test_start_application_missing_id(handler, mock_context):
    """Test that starting an application fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='start-application', application_id=None
    )

    assert response.isError
    assert 'application_id is required for start-application operation' in response.content[0].text


@pytest.mark.asyncio
async def test_stop_application_success(handler, mock_context):
    """Test successful stop of an EMR Serverless application."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.stop_application.return_value = {}

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='stop-application',
        application_id='app-1234567890abcdef0',
    )

    assert isinstance(response, StopApplicationResponse)
    assert not response.isError
    assert response.application_id == 'app-1234567890abcdef0'


@pytest.mark.asyncio
async def test_stop_application_unmanaged(handler, mock_aws_helper, mock_context):
    """Test that stopping unmanaged application fails."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.return_value = {
        'is_valid': False,
        'error_message': 'is not managed by MCP (missing required tags)',
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='stop-application',
        application_id='app-1234567890abcdef0',
    )

    assert response.isError
    assert 'Cannot stop application' in response.content[0].text
    assert 'not managed by MCP' in response.content[0].text


@pytest.mark.asyncio
async def test_stop_application_missing_id(handler, mock_context):
    """Test that stopping an application fails when application_id is missing."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='stop-application', application_id=None
    )

    assert response.isError
    assert 'application_id is required for stop-application operation' in response.content[0].text


# Write access restriction tests
@pytest.mark.asyncio
async def test_create_application_no_write_access(mock_aws_helper, mock_context):
    """Test that creating an application fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessApplicationHandler(mcp, allow_write=False)

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label='emr-7.9.0',
        type='Spark',
    )

    assert response.isError
    assert (
        'Operation create-application is not allowed without write access'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_update_application_no_write_access(mock_aws_helper, mock_context):
    """Test that updating an application fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessApplicationHandler(mcp, allow_write=False)

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='update-application',
        application_id='app-1234567890abcdef0',
        name='UpdatedApplication',
    )

    assert response.isError
    assert (
        'Operation update-application is not allowed without write access'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_delete_application_no_write_access(mock_aws_helper, mock_context):
    """Test that deleting an application fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessApplicationHandler(mcp, allow_write=False)

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='delete-application',
        application_id='app-1234567890abcdef0',
    )

    assert response.isError
    assert (
        'Operation delete-application is not allowed without write access'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_start_application_no_write_access(mock_aws_helper, mock_context):
    """Test that starting an application fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessApplicationHandler(mcp, allow_write=False)

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='start-application',
        application_id='app-1234567890abcdef0',
    )

    assert response.isError
    assert (
        'Operation start-application is not allowed without write access'
        in response.content[0].text
    )


@pytest.mark.asyncio
async def test_stop_application_no_write_access(mock_aws_helper, mock_context):
    """Test that stopping an application fails without write access."""
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessApplicationHandler(mcp, allow_write=False)

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='stop-application',
        application_id='app-1234567890abcdef0',
    )

    assert response.isError
    assert (
        'Operation stop-application is not allowed without write access'
        in response.content[0].text
    )


# AWS permission and client error tests
@pytest.mark.asyncio
async def test_get_application_aws_error(handler, mock_context):
    """Test AWS client error handling for get application."""
    from botocore.exceptions import ClientError

    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.get_application.side_effect = ClientError(
        {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Application not found'}},
        'GetApplication',
    )

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='get-application', application_id='app-nonexistent'
    )

    assert response.isError
    assert 'Error in manage_aws_emr_serverless_applications:' in response.content[0].text


@pytest.mark.asyncio
async def test_create_application_access_denied(handler, mock_context):
    """Test AWS access denied error during application creation."""
    from botocore.exceptions import ClientError

    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.create_application.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}, 'CreateApplication'
    )

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label='emr-7.9.0',
        type='Spark',
    )

    assert response.isError
    assert 'Error in manage_aws_emr_serverless_applications:' in response.content[0].text


# Invalid operation test
@pytest.mark.asyncio
async def test_invalid_operation(handler, mock_context):
    """Test handling of invalid operation."""
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='invalid-operation'
    )

    assert response.isError
    assert 'Invalid operation: invalid-operation' in response.content[0].text


# Test with optional parameters
@pytest.mark.asyncio
async def test_create_application_with_optional_params(handler, mock_context):
    """Test creating application with optional parameters."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.create_application.return_value = {
        'applicationId': 'app-1234567890abcdef0'
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label='emr-7.9.0',
        type='Spark',
        initial_capacity={'DRIVER': {'workerCount': 1}, 'EXECUTOR': {'workerCount': 2}},
        maximum_capacity={'DRIVER': {'cpu': '2 vCPU', 'memory': '4 GB'}},
        auto_start_configuration={'enabled': True},
        auto_stop_configuration={'enabled': True, 'idleTimeoutMinutes': 15},
        network_configuration={'subnetIds': ['subnet-12345']},
        architecture='X86_64',
        image_configuration={'imageUri': 'public.ecr.aws/emr-serverless/spark/emr-7.9.0:latest'},
        worker_type_specifications={
            'DRIVER': {'imageConfiguration': {'imageUri': 'custom-image:latest'}}
        },
        runtime_configuration=[
            {'classification': 'spark-defaults', 'properties': {'key': 'value'}}
        ],
        monitoring_configuration={'s3MonitoringConfiguration': {'logUri': 's3://bucket/logs/'}},
        interactive_configuration={'studioEnabled': True, 'livyEndpointEnabled': True},
    )

    assert not response.isError
    # Verify that optional parameters were passed to the AWS call
    call_args = handler.emr_serverless_client.create_application.call_args[1]
    assert call_args['initialCapacity'] == {
        'DRIVER': {'workerCount': 1},
        'EXECUTOR': {'workerCount': 2},
    }
    assert call_args['maximumCapacity'] == {'DRIVER': {'cpu': '2 vCPU', 'memory': '4 GB'}}
    assert call_args['autoStartConfiguration'] == {'enabled': True}
    assert call_args['autoStopConfiguration'] == {'enabled': True, 'idleTimeoutMinutes': 15}
    assert call_args['networkConfiguration'] == {'subnetIds': ['subnet-12345']}
    assert call_args['architecture'] == 'X86_64'


# Test list applications with optional parameters
@pytest.mark.asyncio
async def test_list_applications_with_all_params(handler, mock_context):
    """Test list applications with all optional parameters."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.list_applications.return_value = {
        'applications': [],
        'nextToken': None,
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='list-applications',
        states=['CREATED', 'STARTED'],
        max_results=50,
        next_token='test-token',
    )

    assert not response.isError
    call_args = handler.emr_serverless_client.list_applications.call_args[1]
    assert call_args['states'] == ['CREATED', 'STARTED']
    assert call_args['maxResults'] == 50
    assert call_args['nextToken'] == 'test-token'


# Test update application with all optional parameters
@pytest.mark.asyncio
async def test_update_application_with_all_params(handler, mock_context):
    """Test updating application with all optional parameters."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.update_application.return_value = {
        'application': {'applicationId': 'app-1234567890abcdef0'}
    }

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='update-application',
        application_id='app-1234567890abcdef0',
        name='UpdatedApplication',
        initial_capacity={'DRIVER': {'workerCount': 2}},
        maximum_capacity={'DRIVER': {'cpu': '4 vCPU', 'memory': '8 GB'}},
        auto_start_configuration={'enabled': False},
        auto_stop_configuration={'enabled': False},
        network_configuration={'subnetIds': ['subnet-67890']},
        architecture='ARM64',
        image_configuration={'imageUri': 'updated-image:latest'},
        worker_type_specifications={
            'EXECUTOR': {'imageConfiguration': {'imageUri': 'executor-image:latest'}}
        },
        release_label='emr-7.10.0',
        runtime_configuration=[{'classification': 'spark-env', 'properties': {'key2': 'value2'}}],
        monitoring_configuration={'cloudWatchLoggingConfiguration': {'enabled': True}},
        interactive_configuration={'studioEnabled': False},
    )

    assert not response.isError
    call_args = handler.emr_serverless_client.update_application.call_args[1]
    assert call_args['name'] == 'UpdatedApplication'
    assert call_args['initialCapacity'] == {'DRIVER': {'workerCount': 2}}
    assert call_args['maximumCapacity'] == {'DRIVER': {'cpu': '4 vCPU', 'memory': '8 GB'}}
    assert call_args['autoStartConfiguration'] == {'enabled': False}
    assert call_args['autoStopConfiguration'] == {'enabled': False}
    assert call_args['networkConfiguration'] == {'subnetIds': ['subnet-67890']}
    assert call_args['architecture'] == 'ARM64'
    assert call_args['releaseLabel'] == 'emr-7.10.0'


# Test verification exception handling
@pytest.mark.asyncio
async def test_update_application_verification_exception(handler, mock_aws_helper, mock_context):
    """Test update application when verification raises exception."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.side_effect = Exception(
        'Cannot update application'
    )

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='update-application',
        application_id='app-nonexistent',
        name='UpdatedApplication',
    )

    assert response.isError
    assert 'Cannot update application' in response.content[0].text


@pytest.mark.asyncio
async def test_delete_application_verification_exception(handler, mock_aws_helper, mock_context):
    """Test delete application when verification raises exception."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.side_effect = Exception(
        'Cannot delete application'
    )

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='delete-application',
        application_id='app-nonexistent',
    )

    assert response.isError
    assert 'Cannot delete application' in response.content[0].text


@pytest.mark.asyncio
async def test_start_application_verification_exception(handler, mock_aws_helper, mock_context):
    """Test start application when verification raises exception."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.side_effect = Exception(
        'Cannot start application'
    )

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='start-application',
        application_id='app-nonexistent',
    )

    assert response.isError
    assert 'Cannot start application' in response.content[0].text


@pytest.mark.asyncio
async def test_stop_application_verification_exception(handler, mock_aws_helper, mock_context):
    """Test stop application when verification raises exception."""
    handler.emr_serverless_client = MagicMock()
    mock_aws_helper.verify_emr_serverless_application_managed_by_mcp.side_effect = Exception(
        'Cannot stop application'
    )

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='stop-application',
        application_id='app-nonexistent',
    )

    assert response.isError
    assert 'Cannot stop application' in response.content[0].text


# Test ValueError exception handling
@pytest.mark.asyncio
async def test_create_application_value_error(handler, mock_context):
    """Test ValueError handling during application creation."""
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.create_application.side_effect = ValueError(
        'Invalid parameter value'
    )

    response = await handler.manage_aws_emr_serverless_applications(
        mock_context,
        operation='create-application',
        name='TestApplication',
        release_label='emr-7.9.0',
        type='Spark',
    )

    assert response.isError
    assert 'Invalid parameter value' in response.content[0].text


# Test error response creation for different operation types
@pytest.mark.asyncio
async def test_create_error_response_coverage(mock_aws_helper, mock_context):
    """Test _create_error_response for different operation types."""
    # Create a fresh handler instance for this test to avoid state interference
    mcp = MagicMock()
    mcp.tool = MagicMock(return_value=lambda f: f)
    handler = EMRServerlessApplicationHandler(
        mcp, allow_write=True, allow_sensitive_data_access=True
    )

    # Test update-application error response
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='update-application', application_id=None
    )
    assert response.isError
    assert isinstance(response, UpdateApplicationResponse)

    # Test delete-application error response
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='delete-application', application_id=None
    )
    assert response.isError
    assert isinstance(response, DeleteApplicationResponse)

    # Test list-applications success (properly mock the response)
    handler.emr_serverless_client = MagicMock()
    handler.emr_serverless_client.list_applications.return_value = {
        'applications': [],
        'nextToken': None,  # Explicitly set to None instead of letting it be a MagicMock
    }
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='list-applications'
    )
    assert not response.isError
    assert isinstance(response, ListApplicationsResponse)

    # Test start-application error response
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='start-application', application_id=None
    )
    assert response.isError
    assert isinstance(response, StartApplicationResponse)

    # Test stop-application error response
    response = await handler.manage_aws_emr_serverless_applications(
        mock_context, operation='stop-application', application_id=None
    )
    assert response.isError
    assert isinstance(response, StopApplicationResponse)
