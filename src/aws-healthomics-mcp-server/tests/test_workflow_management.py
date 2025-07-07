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

"""Unit tests for workflow management tools."""

import base64
import botocore.exceptions
import pytest
from awslabs.aws_healthomics_mcp_server.tools.workflow_management import (
    create_workflow,
    create_workflow_version,
    get_workflow,
    list_workflow_versions,
    list_workflows,
)
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_list_workflows_success():
    """Test successful listing of workflows."""
    # Mock response data
    creation_time = datetime.now(timezone.utc)
    mock_response = {
        'items': [
            {
                'id': 'wfl-12345',
                'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
                'name': 'test-workflow-1',
                'description': 'Test workflow 1',
                'status': 'ACTIVE',
                'parameters': {'param1': 'value1'},
                'storageType': 'DYNAMIC',
                'type': 'WDL',
                'creationTime': creation_time,
            },
            {
                'id': 'wfl-67890',
                'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-67890',
                'name': 'test-workflow-2',
                'status': 'ACTIVE',
                'storageType': 'STATIC',
                'storageCapacity': 100,
                'type': 'CWL',
                'creationTime': creation_time,
            },
        ],
        'nextToken': 'next-page-token',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_workflows.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_workflows(ctx=mock_ctx, max_results=10, next_token=None)

    # Verify client was called correctly
    mock_client.list_workflows.assert_called_once_with(maxResults=10)

    # Verify result structure
    assert 'workflows' in result
    assert 'nextToken' in result
    assert result['nextToken'] == 'next-page-token'
    assert len(result['workflows']) == 2

    # Verify first workflow
    wf1 = result['workflows'][0]
    assert wf1['id'] == 'wfl-12345'
    assert wf1['name'] == 'test-workflow-1'
    assert wf1['description'] == 'Test workflow 1'
    assert wf1['status'] == 'ACTIVE'
    assert wf1['parameters'] == {'param1': 'value1'}
    assert wf1['storageType'] == 'DYNAMIC'
    assert wf1['type'] == 'WDL'
    assert wf1['creationTime'] == creation_time.isoformat()

    # Verify second workflow
    wf2 = result['workflows'][1]
    assert wf2['id'] == 'wfl-67890'
    assert wf2['status'] == 'ACTIVE'
    assert wf2['storageType'] == 'STATIC'
    assert wf2['storageCapacity'] == 100


@pytest.mark.asyncio
async def test_list_workflows_empty_response():
    """Test listing workflows with empty response."""
    mock_response = {'items': []}

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_workflows.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_workflows(ctx=mock_ctx, max_results=10, next_token=None)

    # Verify empty result
    assert result['workflows'] == []
    assert 'nextToken' not in result


@pytest.mark.asyncio
async def test_list_workflows_with_pagination():
    """Test listing workflows with pagination."""
    mock_response = {
        'items': [{'id': 'wfl-12345', 'name': 'test-workflow'}],
        'nextToken': 'next-page-token',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_workflows.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await list_workflows(ctx=mock_ctx, max_results=10, next_token='current-token')

    # Verify pagination parameters
    mock_client.list_workflows.assert_called_once_with(
        maxResults=10, startingToken='current-token'
    )
    assert result['nextToken'] == 'next-page-token'


@pytest.mark.asyncio
async def test_list_workflows_boto_error():
    """Test handling of BotoCoreError in list_workflows."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_workflows.side_effect = botocore.exceptions.BotoCoreError()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await list_workflows(ctx=mock_ctx, max_results=10, next_token=None)

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error listing workflows' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_workflows_unexpected_error():
    """Test handling of unexpected errors in list_workflows."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.list_workflows.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(Exception, match='Unexpected error'):
            await list_workflows(ctx=mock_ctx, max_results=10, next_token=None)

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error listing workflows' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_workflow_success():
    """Test successful retrieval of workflow details."""
    # Mock response data
    creation_time = datetime.now(timezone.utc)
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'name': 'test-workflow',
        'status': 'ACTIVE',
        'statusMessage': 'Workflow is ready for execution',
        'type': 'WDL',
        'description': 'Test workflow description',
        'parameterTemplate': {'param1': {'type': 'string'}},
        'creationTime': creation_time,
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=False)

    # Verify client was called correctly
    mock_client.get_workflow.assert_called_once_with(id='wfl-12345')

    # Verify result contains all expected fields
    assert result['id'] == 'wfl-12345'
    assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345'
    assert result['name'] == 'test-workflow'
    assert result['status'] == 'ACTIVE'
    assert result['statusMessage'] == 'Workflow is ready for execution'
    assert result['type'] == 'WDL'
    assert result['description'] == 'Test workflow description'
    assert result['parameterTemplate'] == {'param1': {'type': 'string'}}
    assert result['creationTime'] == creation_time.isoformat()


@pytest.mark.asyncio
async def test_get_workflow_with_export():
    """Test workflow retrieval with export definition."""
    # Mock response data with presigned URL (as returned by AWS API)
    mock_response = {
        'id': 'wfl-12345',
        'name': 'test-workflow',
        'definition': 'https://s3.amazonaws.com/bucket/workflow-definition.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=True)

    # Verify export parameter was passed
    mock_client.get_workflow.assert_called_once_with(id='wfl-12345', export=['DEFINITION'])

    # Verify presigned URL was included in result
    assert result['definition'].startswith('https://s3.amazonaws.com/')
    assert 'X-Amz-Algorithm' in result['definition']


@pytest.mark.asyncio
async def test_get_workflow_without_export():
    """Test workflow retrieval without export definition."""
    # Mock response data without definition field (normal response)
    creation_time = datetime.now(timezone.utc)
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'name': 'test-workflow',
        'status': 'ACTIVE',
        'type': 'WDL',
        'description': 'Test workflow description',
        'parameterTemplate': {'param1': {'type': 'string'}},
        'creationTime': creation_time,
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=False)

    # Verify export parameter was NOT passed
    mock_client.get_workflow.assert_called_once_with(id='wfl-12345')

    # Verify no definition field in result
    assert 'definition' not in result

    # Verify other fields are present
    assert result['parameterTemplate'] == {'param1': {'type': 'string'}}


@pytest.mark.asyncio
async def test_get_workflow_minimal_response():
    """Test workflow retrieval with minimal response fields."""
    # Mock response with minimal fields
    creation_time = datetime.now(timezone.utc)
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'name': 'test-workflow',
        'status': 'ACTIVE',
        'type': 'WDL',
        'creationTime': creation_time,
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=False)

    # Verify required fields
    assert result['id'] == 'wfl-12345'
    assert result['status'] == 'ACTIVE'
    assert result['creationTime'] == creation_time.isoformat()

    # Verify optional fields are not present
    assert 'description' not in result
    assert 'parameterTemplate' not in result
    assert 'definition' not in result


@pytest.mark.asyncio
async def test_get_workflow_boto_error():
    """Test handling of BotoCoreError in get_workflow."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.side_effect = botocore.exceptions.BotoCoreError()

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(botocore.exceptions.BotoCoreError):
            await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=False)

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error getting workflow' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_workflow_unexpected_error():
    """Test handling of unexpected errors in get_workflow."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        with pytest.raises(Exception, match='Unexpected error'):
            await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=False)

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error getting workflow' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_workflow_none_timestamp():
    """Test handling of None timestamp in get_workflow."""
    # Mock response with None timestamp
    mock_response = {
        'id': 'wfl-12345',
        'name': 'test-workflow',
        'status': 'ACTIVE',
        'type': 'WDL',
        'creationTime': None,
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=False)

    # Verify timestamp handling
    assert result['creationTime'] is None


@pytest.mark.asyncio
async def test_get_workflow_with_status_message():
    """Test workflow retrieval with status message."""
    # Mock response with status message
    creation_time = datetime.now(timezone.utc)
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'name': 'test-workflow',
        'status': 'FAILED',
        'statusMessage': 'Workflow validation failed: Invalid WDL syntax',
        'type': 'WDL',
        'creationTime': creation_time,
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.get_workflow.return_value = mock_response

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await get_workflow(ctx=mock_ctx, workflow_id='wfl-12345', export_definition=False)

    # Verify status message is included
    assert result['status'] == 'FAILED'
    assert result['statusMessage'] == 'Workflow validation failed: Invalid WDL syntax'


@pytest.mark.asyncio
async def test_list_workflow_versions_success(mock_omics_client, mock_context):
    """Test successful listing of workflow versions."""
    # Mock response from AWS
    mock_omics_client.list_workflow_versions.return_value = {
        'items': [
            {
                'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/abc123/1.0',
                'id': 'abc123',
                'status': 'ACTIVE',
                'type': 'WDL',
                'name': 'Test Workflow',
                'versionName': '1.0',
                'creationTime': '2023-01-01T00:00:00Z',
            },
            {
                'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/abc123/2.0',
                'id': 'abc123',
                'status': 'ACTIVE',
                'type': 'WDL',
                'name': 'Test Workflow',
                'versionName': '2.0',
                'creationTime': '2023-02-01T00:00:00Z',
            },
        ],
        'nextToken': None,
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_omics_client,
    ):
        # Call the function
        result = await list_workflow_versions(mock_context, workflow_id='abc123', max_results=10)

    # Assertions
    assert 'versions' in result
    assert len(result['versions']) == 2
    assert result['versions'][0]['versionName'] == '1.0'
    assert result['versions'][1]['versionName'] == '2.0'
    assert result['nextToken'] is None


@pytest.mark.asyncio
async def test_list_workflow_versions_with_pagination(mock_omics_client, mock_context):
    """Test listing workflow versions with pagination."""
    # First call response with nextToken
    mock_omics_client.list_workflow_versions.side_effect = [
        {
            'items': [
                {
                    'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/abc123/1.0',
                    'id': 'abc123',
                    'status': 'ACTIVE',
                    'type': 'WDL',
                    'name': 'Test Workflow',
                    'versionName': '1.0',
                    'creationTime': '2023-01-01T00:00:00Z',
                }
            ],
            'nextToken': 'next-page-token',
        },
        {
            'items': [
                {
                    'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/abc123/2.0',
                    'id': 'abc123',
                    'status': 'ACTIVE',
                    'type': 'WDL',
                    'name': 'Test Workflow',
                    'versionName': '2.0',
                    'creationTime': '2023-02-01T00:00:00Z',
                }
            ],
            'nextToken': None,
        },
    ]

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_omics_client,
    ):
        # First call
        result1 = await list_workflow_versions(mock_context, workflow_id='abc123', max_results=1)

        # Second call with next token
        result2 = await list_workflow_versions(
            mock_context, workflow_id='abc123', max_results=1, next_token=result1['nextToken']
        )

    # Assertions for first call
    assert 'versions' in result1
    assert len(result1['versions']) == 1
    assert result1['versions'][0]['versionName'] == '1.0'
    assert result1['nextToken'] == 'next-page-token'

    # Assertions for second call
    assert 'versions' in result2
    assert len(result2['versions']) == 1
    assert result2['versions'][0]['versionName'] == '2.0'
    assert result2['nextToken'] is None


@pytest.mark.asyncio
async def test_list_workflow_versions_empty_result(mock_omics_client, mock_context):
    """Test listing workflow versions with empty result."""
    # Mock empty response
    mock_omics_client.list_workflow_versions.return_value = {
        'items': [],
        'nextToken': None,
    }

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_omics_client,
    ):
        # Call the function
        result = await list_workflow_versions(mock_context, workflow_id='abc123', max_results=10)

    # Assertions
    assert 'versions' in result
    assert len(result['versions']) == 0
    if 'nextToken' in result:
        assert result['nextToken'] is None


@pytest.mark.asyncio
async def test_list_workflow_versions_client_error(mock_omics_client, mock_context):
    """Test handling of client error when listing workflow versions."""
    from botocore.exceptions import ClientError

    # Mock client error
    error_response = {
        'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Workflow not found'}
    }
    mock_omics_client.list_workflow_versions.side_effect = ClientError(
        error_response,  # type: ignore
        'ListWorkflowVersions',
    )

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_omics_client,
    ):
        # Call the function and expect it to raise an exception
        with pytest.raises(ClientError):
            await list_workflow_versions(mock_context, workflow_id='nonexistent-id')

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        assert 'Workflow not found' in mock_context.error.call_args[0][0]


@pytest.mark.asyncio
async def test_list_workflow_versions_general_exception(mock_omics_client, mock_context):
    """Test handling of general exception when listing workflow versions."""
    # Mock general exception
    mock_omics_client.list_workflow_versions.side_effect = Exception('Unexpected error')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_omics_client,
    ):
        # Call the function and expect it to raise an exception
        with pytest.raises(Exception):
            await list_workflow_versions(mock_context, workflow_id='abc123')

        # Verify error was reported to context
        mock_context.error.assert_called_once()
        assert 'Unexpected error listing workflow versions' in mock_context.error.call_args[0][0]


@pytest.mark.asyncio
async def test_create_workflow_success():
    """Test successful workflow creation."""
    # Mock response data
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'status': 'ACTIVE',
        'name': 'test-workflow',
        'description': 'Test workflow description',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_workflow.return_value = mock_response

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content').decode('utf-8')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await create_workflow(
            mock_ctx,
            name='test-workflow',
            definition_zip_base64=definition_zip_base64,
            description='Test workflow description',
            parameter_template={'param1': {'type': 'string'}},
        )

    # Verify client was called correctly
    mock_client.create_workflow.assert_called_once_with(
        name='test-workflow',
        definitionZip=b'test workflow content',
        description='Test workflow description',
        parameterTemplate={'param1': {'type': 'string'}},
    )

    # Verify result contains expected fields
    assert result['id'] == 'wfl-12345'
    assert result['arn'] == 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345'
    assert result['status'] == 'ACTIVE'
    assert result['name'] == 'test-workflow'
    assert result['description'] == 'Test workflow description'


@pytest.mark.asyncio
async def test_create_workflow_minimal():
    """Test workflow creation with minimal required parameters."""
    # Mock response data
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'status': 'ACTIVE',
        'name': 'test-workflow',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_workflow.return_value = mock_response

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content').decode('utf-8')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await create_workflow(
            mock_ctx,
            name='test-workflow',
            definition_zip_base64=definition_zip_base64,
            description=None,
            parameter_template=None,
        )

    # Verify client was called with only required parameters
    mock_client.create_workflow.assert_called_once_with(
        name='test-workflow',
        definitionZip=b'test workflow content',
    )

    # Verify result contains expected fields
    assert result['id'] == 'wfl-12345'
    assert result['name'] == 'test-workflow'
    # description should not be in result when it's None in response
    assert result.get('description') is None


@pytest.mark.asyncio
async def test_create_workflow_invalid_base64():
    """Test workflow creation with invalid base64 content."""
    # Mock context
    mock_ctx = AsyncMock()

    with pytest.raises(Exception, match='Invalid base64-encoded string'):
        await create_workflow(
            mock_ctx,
            name='test-workflow',
            definition_zip_base64='invalid base64!',
            description=None,
            parameter_template=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Failed to decode base64' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_create_workflow_boto_error():
    """Test handling of BotoCoreError in create_workflow."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_workflow.side_effect = botocore.exceptions.BotoCoreError()

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content').decode('utf-8')

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ),
        pytest.raises(botocore.exceptions.BotoCoreError),
    ):
        await create_workflow(
            mock_ctx,
            name='test-workflow',
            definition_zip_base64=definition_zip_base64,
            description=None,
            parameter_template=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error creating workflow' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_create_workflow_unexpected_error():
    """Test handling of unexpected errors in create_workflow."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_workflow.side_effect = Exception('Unexpected error')

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content').decode('utf-8')

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ),
        pytest.raises(Exception, match='Unexpected error'),
    ):
        await create_workflow(
            mock_ctx,
            name='test-workflow',
            definition_zip_base64=definition_zip_base64,
            description=None,
            parameter_template=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Unexpected error creating workflow' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_create_workflow_version_success():
    """Test successful workflow version creation."""
    # Mock response data
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'status': 'ACTIVE',
        'name': 'test-workflow',
        'versionName': 'v2.0',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_workflow_version.return_value = mock_response

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content v2').decode('utf-8')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        result = await create_workflow_version(
            mock_ctx,
            workflow_id='wfl-12345',
            version_name='v2.0',
            definition_zip_base64=definition_zip_base64,
            description='Version 2.0 of test workflow',
            parameter_template={'param1': {'type': 'string'}},
            storage_type='DYNAMIC',
            storage_capacity=None,
        )

    # Verify client was called correctly
    mock_client.create_workflow_version.assert_called_once_with(
        workflowId='wfl-12345',
        versionName='v2.0',
        definitionZip=b'test workflow content v2',
        description='Version 2.0 of test workflow',
        parameterTemplate={'param1': {'type': 'string'}},
        storageType='DYNAMIC',
    )

    # Verify result contains expected fields
    assert result['id'] == 'wfl-12345'
    assert result['versionName'] == 'v2.0'
    assert result['status'] == 'ACTIVE'


@pytest.mark.asyncio
async def test_create_workflow_version_with_static_storage():
    """Test workflow version creation with static storage."""
    # Mock response data
    mock_response = {
        'id': 'wfl-12345',
        'arn': 'arn:aws:omics:us-east-1:123456789012:workflow/wfl-12345',
        'status': 'ACTIVE',
        'name': 'test-workflow',
        'versionName': 'v2.0',
    }

    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_workflow_version.return_value = mock_response

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content v2').decode('utf-8')

    with patch(
        'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
        return_value=mock_client,
    ):
        await create_workflow_version(
            mock_ctx,
            workflow_id='wfl-12345',
            version_name='v2.0',
            definition_zip_base64=definition_zip_base64,
            description=None,
            parameter_template=None,
            storage_type='STATIC',
            storage_capacity=1000,
        )

    # Verify client was called with static storage parameters
    mock_client.create_workflow_version.assert_called_once_with(
        workflowId='wfl-12345',
        versionName='v2.0',
        definitionZip=b'test workflow content v2',
        storageType='STATIC',
        storageCapacity=1000,
    )


@pytest.mark.asyncio
async def test_create_workflow_version_static_without_capacity():
    """Test workflow version creation with static storage but no capacity."""
    # Mock context
    mock_ctx = AsyncMock()

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content v2').decode('utf-8')

    with pytest.raises(ValueError, match='Storage capacity is required'):
        await create_workflow_version(
            mock_ctx,
            workflow_id='wfl-12345',
            version_name='v2.0',
            definition_zip_base64=definition_zip_base64,
            description=None,
            parameter_template=None,
            storage_type='STATIC',
            storage_capacity=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()


@pytest.mark.asyncio
async def test_create_workflow_version_invalid_base64():
    """Test workflow version creation with invalid base64 content."""
    # Mock context
    mock_ctx = AsyncMock()

    with pytest.raises(Exception, match='Invalid base64-encoded string'):
        await create_workflow_version(
            mock_ctx,
            workflow_id='wfl-12345',
            version_name='v2.0',
            definition_zip_base64='invalid base64!',
            description=None,
            parameter_template=None,
            storage_type='DYNAMIC',
            storage_capacity=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'Failed to decode base64' in mock_ctx.error.call_args[0][0]


@pytest.mark.asyncio
async def test_create_workflow_version_boto_error():
    """Test handling of BotoCoreError in create_workflow_version."""
    # Mock context and client
    mock_ctx = AsyncMock()
    mock_client = MagicMock()
    mock_client.create_workflow_version.side_effect = botocore.exceptions.BotoCoreError()

    # Create base64 encoded workflow definition
    definition_zip_base64 = base64.b64encode(b'test workflow content v2').decode('utf-8')

    with (
        patch(
            'awslabs.aws_healthomics_mcp_server.tools.workflow_management.get_omics_client',
            return_value=mock_client,
        ),
        pytest.raises(botocore.exceptions.BotoCoreError),
    ):
        await create_workflow_version(
            mock_ctx,
            workflow_id='wfl-12345',
            version_name='v2.0',
            definition_zip_base64=definition_zip_base64,
            description=None,
            parameter_template=None,
            storage_type='DYNAMIC',
            storage_capacity=None,
        )

    # Verify error was reported to context
    mock_ctx.error.assert_called_once()
    assert 'AWS error creating workflow version' in mock_ctx.error.call_args[0][0]
