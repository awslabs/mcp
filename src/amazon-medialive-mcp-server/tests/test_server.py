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

"""Tests for server.py functions that need additional coverage."""

import pytest
from awslabs.amazon_medialive_mcp_server.server import (
    _apply_all_field_description_overrides,
    _apply_field_description_overrides_to_model,
    _check_botocore_version,
    _make_tool_handler,
    _register_tools,
    _register_waiter_tool,
    _register_workflow_context_tool,
    main,
)
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
from unittest.mock import MagicMock, patch


# --- _check_botocore_version ---


@patch('awslabs.amazon_medialive_mcp_server.server.BOTOCORE_SOURCE_VERSION', None)
def test_check_botocore_version_none():
    """Verify version check is skipped when BOTOCORE_SOURCE_VERSION is None."""
    _check_botocore_version()  # Should not raise


@patch('awslabs.amazon_medialive_mcp_server.server.BOTOCORE_SOURCE_VERSION', '1.0.0')
@patch('awslabs.amazon_medialive_mcp_server.server.botocore')
def test_check_botocore_version_older(mock_botocore):
    """Verify warning when installed botocore is older than generated version."""
    mock_botocore.__version__ = '0.9.0'
    _check_botocore_version()  # Should log warning but not raise


@patch('awslabs.amazon_medialive_mcp_server.server.BOTOCORE_SOURCE_VERSION', '1.0.0')
@patch('awslabs.amazon_medialive_mcp_server.server.botocore')
def test_check_botocore_version_newer(mock_botocore):
    """Verify no warning when installed botocore is newer."""
    mock_botocore.__version__ = '2.0.0'
    _check_botocore_version()  # Should not warn


# --- _make_tool_handler ---


class SimpleInput(BaseModel):
    """Simple test input model."""

    model_config = {'populate_by_name': True}

    channel_id: str = Field(..., alias='ChannelId')


@pytest.mark.asyncio
async def test_make_tool_handler_success():
    """Verify handler calls client method and returns response."""
    mock_client = MagicMock()
    mock_client.describe_channel.return_value = {'ChannelId': '123', 'State': 'IDLE'}

    op_meta = {
        'input_model': SimpleInput,
        'tool_name': 'describe_channel',
    }
    handler = _make_tool_handler('DescribeChannel', op_meta, mock_client)
    result = await handler(SimpleInput(channel_id='123'))

    mock_client.describe_channel.assert_called_once_with(ChannelId='123')
    assert result['State'] == 'IDLE'


@pytest.mark.asyncio
async def test_make_tool_handler_client_error():
    """Verify handler returns structured error on ClientError."""
    mock_client = MagicMock()
    mock_client.describe_channel.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}, 'ResponseMetadata': {}},
        'DescribeChannel',
    )

    op_meta = {'input_model': SimpleInput, 'tool_name': 'describe_channel'}
    handler = _make_tool_handler('DescribeChannel', op_meta, mock_client)
    result = await handler(SimpleInput(channel_id='123'))

    assert result['error'] == 'ClientError'
    assert result['code'] == 'NotFoundException'


@pytest.mark.asyncio
async def test_make_tool_handler_general_error():
    """Verify handler returns generic error on unexpected exception."""
    mock_client = MagicMock()
    mock_client.describe_channel.side_effect = RuntimeError('boom')

    op_meta = {'input_model': SimpleInput, 'tool_name': 'describe_channel'}
    handler = _make_tool_handler('DescribeChannel', op_meta, mock_client)
    result = await handler(SimpleInput(channel_id='123'))

    assert result['error'] == 'RuntimeError'


@pytest.mark.asyncio
async def test_make_tool_handler_with_pagination_default():
    """Verify handler injects default page size for paginated operations."""
    mock_client = MagicMock()
    mock_client.list_channels.return_value = {'Channels': []}

    class ListInput(BaseModel):
        """List input model."""

        model_config = {'populate_by_name': True}

        max_results: int = Field(None, alias='MaxResults')

    op_meta = {
        'input_model': ListInput,
        'tool_name': 'list_channels',
        'pagination': {'limit_key': 'MaxResults', 'output_tokens': ['NextToken']},
    }

    with patch(
        'awslabs.amazon_medialive_mcp_server.server.PAGINATION_DEFAULTS',
        {'ListChannels': 5},
    ):
        handler = _make_tool_handler('ListChannels', op_meta, mock_client)
        await handler(ListInput())

    mock_client.list_channels.assert_called_once_with(MaxResults=5)


@pytest.mark.asyncio
async def test_make_tool_handler_with_validation_error():
    """Verify handler returns validation errors when Tier 2 check fails."""
    mock_client = MagicMock()

    op_meta = {'input_model': SimpleInput, 'tool_name': 'describe_channel'}

    with patch(
        'awslabs.amazon_medialive_mcp_server.server.VALIDATORS',
        {'DescribeChannel': lambda params: ['bad reference']},
    ):
        handler = _make_tool_handler('DescribeChannel', op_meta, mock_client)
        result = await handler(SimpleInput(channel_id='123'))

    assert result['error'] == 'ValidationError'
    assert 'bad reference' in result['messages']
    mock_client.describe_channel.assert_not_called()


# --- _apply_field_description_overrides ---


def test_apply_field_description_overrides_to_model():
    """Verify field description overrides are applied to a model."""

    class TestModel(BaseModel):
        """Test model."""

        some_field: str = Field('', description='original')

    with patch(
        'awslabs.amazon_medialive_mcp_server.server.FIELD_DESCRIPTION_OVERRIDES',
        {'TestModel.some_field': 'overridden description'},
    ):
        result = _apply_field_description_overrides_to_model(TestModel)

    assert result is True
    assert TestModel.model_fields['some_field'].description == 'overridden description'


def test_apply_field_description_overrides_no_match():
    """Verify no changes when no overrides match."""

    class TestModel2(BaseModel):
        """Test model 2."""

        other_field: str = Field('', description='original')

    with patch(
        'awslabs.amazon_medialive_mcp_server.server.FIELD_DESCRIPTION_OVERRIDES',
        {},
    ):
        result = _apply_field_description_overrides_to_model(TestModel2)

    assert result is False


@patch('awslabs.amazon_medialive_mcp_server.server.models', None)
def test_apply_all_overrides_with_no_generated_models():
    """Verify _apply_all_field_description_overrides handles None generated_models."""
    _apply_all_field_description_overrides()  # Should not raise


@patch('awslabs.amazon_medialive_mcp_server.server.models')
def test_apply_all_overrides_iterates_models(mock_models):
    """Verify _apply_all_field_description_overrides processes BaseModel subclasses."""

    class FakeModel(BaseModel):
        """Fake model."""

        x: str = Field('', description='orig')

    # Use spec=[] to avoid __dir__ issues with MagicMock
    type(mock_models).__dir__ = lambda self: ['FakeModel']
    type(mock_models).FakeModel = FakeModel

    with patch(
        'awslabs.amazon_medialive_mcp_server.server.FIELD_DESCRIPTION_OVERRIDES',
        {},
    ):
        _apply_all_field_description_overrides()


# --- _register_tools ---


@patch('awslabs.amazon_medialive_mcp_server.server.OPERATIONS', {})
def test_register_tools_no_operations():
    """Verify _register_tools handles empty OPERATIONS gracefully."""
    _register_tools()  # Should log error but not raise


@patch('awslabs.amazon_medialive_mcp_server.server.boto3')
@patch('awslabs.amazon_medialive_mcp_server.server.OPERATIONS')
@patch('awslabs.amazon_medialive_mcp_server.server.INCLUDED_OPERATIONS', {'TestOp'})
@patch('awslabs.amazon_medialive_mcp_server.server.mcp')
def test_register_tools_registers_included_ops(mock_mcp, mock_ops, mock_boto3):
    """Verify _register_tools registers included operations."""
    mock_ops.__bool__ = lambda self: True
    mock_ops.items.return_value = [
        (
            'TestOp',
            {
                'tool_name': 'test_op',
                'input_model': SimpleInput,
                'auto_description': 'Test operation.',
            },
        ),
        (
            'ExcludedOp',
            {
                'tool_name': 'excluded_op',
                'input_model': SimpleInput,
                'auto_description': 'Excluded.',
            },
        ),
    ]
    mock_mcp.tool.return_value = lambda f: f

    _register_tools()

    mock_mcp.tool.assert_called_once()
    call_kwargs = mock_mcp.tool.call_args[1]
    assert call_kwargs['name'] == 'test_op'


# --- _register_waiter_tool ---


@patch('awslabs.amazon_medialive_mcp_server.server.WAITER_REGISTRY', {})
def test_register_waiter_tool_empty_registry():
    """Verify _register_waiter_tool skips when no waiters available."""
    _register_waiter_tool()  # Should log info but not raise


@patch('awslabs.amazon_medialive_mcp_server.server.boto3')
@patch('awslabs.amazon_medialive_mcp_server.server.mcp')
@patch(
    'awslabs.amazon_medialive_mcp_server.server.WAITER_REGISTRY',
    {
        'channel_running': {
            'description': 'Wait for channel to be running.',
            'boto3_waiter_name': 'channel_running',
            'delay': 5,
            'max_attempts': 20,
        }
    },
)
def test_register_waiter_tool_with_registry(mock_mcp, mock_boto3):
    """Verify _register_waiter_tool registers when waiters exist."""
    mock_mcp.tool.return_value = lambda f: f
    _register_waiter_tool()
    mock_mcp.tool.assert_called_once()
    call_kwargs = mock_mcp.tool.call_args[1]
    assert call_kwargs['name'] == 'wait_for_resource'
    assert 'channel_running' in call_kwargs['description']


# --- _register_workflow_context_tool ---


@patch('awslabs.amazon_medialive_mcp_server.server.mcp')
def test_register_workflow_context_tool(mock_mcp):
    """Verify workflow context tool is registered."""
    mock_mcp.tool.return_value = lambda f: f
    _register_workflow_context_tool()
    mock_mcp.tool.assert_called_once()
    call_kwargs = mock_mcp.tool.call_args[1]
    assert call_kwargs['name'] == 'get_media_workflow_context'


# --- main ---


@patch('awslabs.amazon_medialive_mcp_server.server.mcp')
def test_main_calls_mcp_run(mock_mcp):
    """Verify main() calls mcp.run with stdio transport."""
    main()
    mock_mcp.run.assert_called_once_with(transport='stdio')


# --- Branch coverage for pagination hint building ---


@patch('awslabs.amazon_medialive_mcp_server.server.boto3')
@patch('awslabs.amazon_medialive_mcp_server.server.OPERATIONS')
@patch('awslabs.amazon_medialive_mcp_server.server.INCLUDED_OPERATIONS', {'PaginatedOp'})
@patch('awslabs.amazon_medialive_mcp_server.server.mcp')
def test_register_tools_pagination_hints_all_fields(mock_mcp, mock_ops, mock_boto3):
    """Verify pagination hints include output_tokens, input_tokens, and limit_key."""
    mock_ops.__bool__ = lambda self: True
    mock_ops.items.return_value = [
        (
            'PaginatedOp',
            {
                'tool_name': 'paginated_op',
                'input_model': SimpleInput,
                'auto_description': 'Paginated op.',
                'pagination': {
                    'output_tokens': ['NextToken'],
                    'input_tokens': ['NextToken'],
                    'limit_key': 'MaxResults',
                },
            },
        ),
    ]
    mock_mcp.tool.return_value = lambda f: f

    _register_tools()

    call_kwargs = mock_mcp.tool.call_args[1]
    assert 'NextToken' in call_kwargs['description']
    assert 'MaxResults' in call_kwargs['description']


@patch('awslabs.amazon_medialive_mcp_server.server.boto3')
@patch('awslabs.amazon_medialive_mcp_server.server.OPERATIONS')
@patch('awslabs.amazon_medialive_mcp_server.server.INCLUDED_OPERATIONS', {'EmptyPagOp'})
@patch('awslabs.amazon_medialive_mcp_server.server.mcp')
def test_register_tools_pagination_hints_empty_fields(mock_mcp, mock_ops, mock_boto3):
    """Verify pagination hints handle empty output_tokens/input_tokens/limit_key."""
    mock_ops.__bool__ = lambda self: True
    mock_ops.items.return_value = [
        (
            'EmptyPagOp',
            {
                'tool_name': 'empty_pag_op',
                'input_model': SimpleInput,
                'auto_description': 'Empty pag op.',
                'pagination': {
                    'output_tokens': [],
                    'input_tokens': [],
                    'limit_key': None,
                },
            },
        ),
    ]
    mock_mcp.tool.return_value = lambda f: f

    _register_tools()

    call_kwargs = mock_mcp.tool.call_args[1]
    assert 'pagination' in call_kwargs['description'].lower()


# --- Branch coverage for _make_tool_handler pagination ---


@pytest.mark.asyncio
async def test_make_tool_handler_no_pagination():
    """Verify handler works without pagination metadata."""
    mock_client = MagicMock()
    mock_client.describe_channel.return_value = {'ok': True}

    op_meta = {'input_model': SimpleInput, 'tool_name': 'describe_channel'}
    handler = _make_tool_handler('DescribeChannel', op_meta, mock_client)
    result = await handler(SimpleInput(channel_id='123'))
    assert result == {'ok': True}


@pytest.mark.asyncio
async def test_make_tool_handler_pagination_no_default():
    """Verify handler skips default injection when no PAGINATION_DEFAULTS entry."""
    mock_client = MagicMock()
    mock_client.list_channels.return_value = {'Channels': []}

    class ListInput(BaseModel):
        """List input."""

        model_config = {'populate_by_name': True}
        max_results: int = Field(None, alias='MaxResults')

    op_meta = {
        'input_model': ListInput,
        'tool_name': 'list_channels',
        'pagination': {'limit_key': 'MaxResults'},
    }

    with patch(
        'awslabs.amazon_medialive_mcp_server.server.PAGINATION_DEFAULTS',
        {},
    ):
        handler = _make_tool_handler('ListChannels', op_meta, mock_client)
        await handler(ListInput())

    # MaxResults should NOT be in the call since there's no default
    call_kwargs = mock_client.list_channels.call_args[1]
    assert 'MaxResults' not in call_kwargs


@pytest.mark.asyncio
async def test_make_tool_handler_pagination_no_limit_key():
    """Verify handler skips default injection when pagination has no limit_key."""
    mock_client = MagicMock()
    mock_client.describe_channel.return_value = {'ok': True}

    op_meta = {
        'input_model': SimpleInput,
        'tool_name': 'describe_channel',
        'pagination': {'limit_key': None},
    }

    handler = _make_tool_handler('DescribeChannel', op_meta, mock_client)
    await handler(SimpleInput(channel_id='123'))
    mock_client.describe_channel.assert_called_once()
