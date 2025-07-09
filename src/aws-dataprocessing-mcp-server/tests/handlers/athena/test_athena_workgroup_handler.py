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


import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_workgroup_handler import (
    AthenaWorkGroupHandler,
)
from botocore.exceptions import ClientError
from mcp.server.fastmcp import Context
from unittest.mock import Mock, patch


@pytest.fixture
def mock_athena_client():
    """Create a mock Athena client instance for testing."""
    return Mock()


@pytest.fixture
def mock_aws_helper():
    """Create a mock AwsHelper instance for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.athena.athena_workgroup_handler.AwsHelper'
    ) as mock:
        mock.create_boto3_client.return_value = Mock()
        mock.prepare_resource_tags.return_value = {
            'ManagedBy': 'MCP',
            'ResourceType': 'AthenaWorkgroup',
        }
        mock.convert_tags_to_aws_format.return_value = [{'Key': 'ManagedBy', 'Value': 'MCP'}]
        mock.get_resource_tags_athena_workgroup.return_value = [
            {'Key': 'ManagedBy', 'Value': 'MCP'}
        ]
        mock.verify_resource_managed_by_mcp.return_value = True
        yield mock


@pytest.fixture
def handler(mock_aws_helper):
    """Create a mock AthenaWorkGroupHandler instance for testing."""
    mcp = Mock()
    return AthenaWorkGroupHandler(mcp, allow_write=True)


@pytest.fixture
def read_only_handler(mock_aws_helper):
    """Create a mock AthenaWorkGroupHandler instance with read-only access for testing."""
    mcp = Mock()
    return AthenaWorkGroupHandler(mcp, allow_write=False)


@pytest.fixture
def mock_context():
    """Create a mock context instance for testing."""
    return Mock(spec=Context)


# WorkGroup Tests


@pytest.mark.asyncio
async def test_create_work_group_success(handler, mock_athena_client):
    """Test successful creation of a workgroup."""
    handler.athena_client = mock_athena_client

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx,
        operation='create-work-group',
        name='test-workgroup',
        description='Test workgroup',
        configuration={'ResultConfiguration': {'OutputLocation': 's3://bucket/path'}},
        state='ENABLED',
        tags={'Owner': 'TestTeam'},
    )

    assert not response.isError
    assert response.work_group_name == 'test-workgroup'
    assert response.operation == 'create-work-group'
    mock_athena_client.create_work_group.assert_called_once()


@pytest.mark.asyncio
async def test_create_work_group_missing_parameters(handler):
    """Test that create workgroup fails when name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_workgroups(ctx, operation='create-work-group', name=None)


@pytest.mark.asyncio
async def test_create_work_group_without_write_permission(read_only_handler):
    """Test that creating a workgroup fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_workgroups(
        ctx, operation='create-work-group', name='test-workgroup', description='Test workgroup'
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text
    assert response.work_group_name == ''


@pytest.mark.asyncio
async def test_delete_work_group_success(handler, mock_athena_client, mock_aws_helper):
    """Test successful deletion of a workgroup."""
    handler.athena_client = mock_athena_client
    mock_aws_helper.verify_resource_managed_by_mcp.return_value = True

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx, operation='delete-work-group', name='test-workgroup', recursive_delete_option=True
    )

    assert not response.isError
    assert response.work_group_name == 'test-workgroup'
    assert response.operation == 'delete-work-group'
    mock_athena_client.delete_work_group.assert_called_once_with(
        WorkGroup='test-workgroup', RecursiveDeleteOption=True
    )


@pytest.mark.asyncio
async def test_delete_work_group_missing_parameters(handler):
    """Test that delete workgroup fails when name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_workgroups(ctx, operation='delete-work-group', name=None)


@pytest.mark.asyncio
async def test_delete_work_group_without_write_permission(read_only_handler):
    """Test that deleting a workgroup fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_workgroups(
        ctx, operation='delete-work-group', name='test-workgroup'
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text
    assert response.work_group_name == ''


@pytest.mark.asyncio
async def test_delete_work_group_not_mcp_managed(handler, mock_aws_helper):
    """Test that deleting a non-MCP managed workgroup fails."""
    # Simulate a workgroup without MCP managed tags
    mock_aws_helper.get_resource_tags_athena_workgroup.return_value = [
        {'Key': 'OtherTag', 'Value': 'OtherValue'}
    ]
    mock_aws_helper.verify_resource_managed_by_mcp.return_value = False

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx, operation='delete-work-group', name='test-workgroup'
    )

    assert response.isError
    assert 'not managed by the MCP server' in response.content[0].text
    assert response.work_group_name == 'test-workgroup'


@pytest.mark.asyncio
async def test_get_work_group_success(handler, mock_athena_client):
    """Test successful retrieval of a workgroup."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_work_group.return_value = {
        'WorkGroup': {
            'Name': 'test-workgroup',
            'State': 'ENABLED',
            'Configuration': {'ResultConfiguration': {'OutputLocation': 's3://bucket/path'}},
        }
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx, operation='get-work-group', name='test-workgroup'
    )

    assert not response.isError
    assert response.work_group['Name'] == 'test-workgroup'
    assert response.operation == 'get-work-group'
    mock_athena_client.get_work_group.assert_called_once_with(WorkGroup='test-workgroup')


@pytest.mark.asyncio
async def test_get_work_group_missing_parameters(handler):
    """Test that get workgroup fails when name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_workgroups(ctx, operation='get-work-group', name=None)


@pytest.mark.asyncio
async def test_list_work_groups_success(handler, mock_athena_client):
    """Test successful listing of workgroups."""
    handler.athena_client = mock_athena_client
    mock_athena_client.list_work_groups.return_value = {
        'WorkGroups': [
            {'Name': 'workgroup1', 'State': 'ENABLED'},
            {'Name': 'workgroup2', 'State': 'DISABLED'},
        ],
        'NextToken': 'next-token',
    }

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx, operation='list-work-groups', max_results=10, next_token='token'
    )

    assert not response.isError
    assert len(response.work_groups) == 2
    assert response.count == 2
    assert response.next_token == 'next-token'
    assert response.operation == 'list-work-groups'
    mock_athena_client.list_work_groups.assert_called_once_with(MaxResults=10, NextToken='token')


@pytest.mark.asyncio
async def test_update_work_group_success(handler, mock_athena_client, mock_aws_helper):
    """Test successful update of a workgroup."""
    handler.athena_client = mock_athena_client
    mock_aws_helper.verify_resource_managed_by_mcp.return_value = True

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx,
        operation='update-work-group',
        name='test-workgroup',
        description='Updated description',
        configuration={'ResultConfiguration': {'OutputLocation': 's3://new-bucket/path'}},
        state='DISABLED',
    )

    assert not response.isError
    assert response.work_group_name == 'test-workgroup'
    assert response.operation == 'update-work-group'
    mock_athena_client.update_work_group.assert_called_once_with(
        WorkGroup='test-workgroup',
        Description='Updated description',
        ConfigurationUpdates={'ResultConfiguration': {'OutputLocation': 's3://new-bucket/path'}},
        State='DISABLED',
    )


@pytest.mark.asyncio
async def test_update_work_group_missing_parameters(handler):
    """Test that update workgroup fails when name is missing."""
    ctx = Mock()
    with pytest.raises(ValueError):
        await handler.manage_aws_athena_workgroups(ctx, operation='update-work-group', name=None)


@pytest.mark.asyncio
async def test_update_work_group_without_write_permission(read_only_handler):
    """Test that updating a workgroup fails when write access is disabled."""
    ctx = Mock()
    response = await read_only_handler.manage_aws_athena_workgroups(
        ctx,
        operation='update-work-group',
        name='test-workgroup',
        description='Updated description',
    )

    assert response.isError
    assert 'not allowed without write access' in response.content[0].text
    assert response.work_group_name == ''


@pytest.mark.asyncio
async def test_update_work_group_not_mcp_managed(handler, mock_aws_helper):
    """Test that updating a non-MCP managed workgroup fails."""
    # Simulate a workgroup without MCP managed tags
    mock_aws_helper.get_resource_tags_athena_workgroup.return_value = [
        {'Key': 'OtherTag', 'Value': 'OtherValue'}
    ]
    mock_aws_helper.verify_resource_managed_by_mcp.return_value = False

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx,
        operation='update-work-group',
        name='test-workgroup',
        description='Updated description',
    )

    assert response.isError
    assert 'not managed by the MCP server' in response.content[0].text
    assert response.work_group_name == 'test-workgroup'


@pytest.mark.asyncio
async def test_invalid_work_group_operation(handler):
    """Test that running manage_aws_athena_workgroups with an invalid operation results in an error."""
    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(ctx, operation='invalid-operation')

    assert response.isError
    assert 'Invalid operation' in response.content[0].text


@pytest.mark.asyncio
async def test_work_group_client_error_handling(handler, mock_athena_client):
    """Test error handling when Athena client raises an exception."""
    handler.athena_client = mock_athena_client
    mock_athena_client.get_work_group.side_effect = ClientError(
        {'Error': {'Code': 'InvalidRequestException', 'Message': 'Invalid request'}},
        'GetWorkGroup',
    )

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx, operation='get-work-group', name='test-workgroup'
    )

    assert response.isError
    assert 'Error in manage_aws_athena_workgroups' in response.content[0].text


@pytest.mark.asyncio
async def test_delete_work_group_empty_tags(handler, mock_aws_helper):
    """Test that deleting a workgroup with empty tags fails."""
    # Simulate a workgroup with empty tags
    mock_aws_helper.get_resource_tags_athena_workgroup.return_value = []
    mock_aws_helper.verify_resource_managed_by_mcp.return_value = False

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx, operation='delete-work-group', name='test-workgroup'
    )

    assert response.isError
    assert 'not managed by the MCP server' in response.content[0].text
    assert response.work_group_name == 'test-workgroup'


@pytest.mark.asyncio
async def test_update_work_group_empty_tags(handler, mock_aws_helper):
    """Test that updating a workgroup with empty tags fails."""
    # Simulate a workgroup with empty tags
    mock_aws_helper.get_resource_tags_athena_workgroup.return_value = []
    mock_aws_helper.verify_resource_managed_by_mcp.return_value = False

    ctx = Mock()
    response = await handler.manage_aws_athena_workgroups(
        ctx,
        operation='update-work-group',
        name='test-workgroup',
        description='Updated description',
    )

    assert response.isError
    assert 'not managed by the MCP server' in response.content[0].text
    assert response.work_group_name == 'test-workgroup'


# Initialization Tests


@pytest.mark.asyncio
async def test_initialization_parameters(mock_aws_helper):
    """Test initialization of parameters for AthenaWorkGroupHandler object."""
    mcp = Mock()
    handler = AthenaWorkGroupHandler(mcp, allow_write=True, allow_sensitive_data_access=True)

    assert handler.allow_write
    assert handler.allow_sensitive_data_access
    assert handler.mcp == mcp


@pytest.mark.asyncio
async def test_initialization_registers_tools(mock_aws_helper):
    """Test that initialization registers the tools with the MCP server."""
    mcp = Mock()
    AthenaWorkGroupHandler(mcp)

    mcp.tool.assert_called_once_with(name='manage_aws_athena_workgroups')
