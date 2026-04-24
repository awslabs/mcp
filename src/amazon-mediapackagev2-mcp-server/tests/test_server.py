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

"""Tests for server.py functions."""

import pytest
from awslabs.amazon_mediapackagev2_mcp_server.server import (
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


PKG = 'awslabs.amazon_mediapackagev2_mcp_server.server'


# --- _check_botocore_version ---


@patch(f'{PKG}.BOTOCORE_SOURCE_VERSION', None)
def test_check_botocore_version_none():
    """Verify version check is skipped when BOTOCORE_SOURCE_VERSION is None."""
    _check_botocore_version()


@patch(f'{PKG}.BOTOCORE_SOURCE_VERSION', '1.0.0')
@patch(f'{PKG}.botocore')
def test_check_botocore_version_older(mock_botocore):
    """Verify warning when installed botocore is older than generated version."""
    mock_botocore.__version__ = '0.9.0'
    _check_botocore_version()


@patch(f'{PKG}.BOTOCORE_SOURCE_VERSION', '1.0.0')
@patch(f'{PKG}.botocore')
def test_check_botocore_version_newer(mock_botocore):
    """Verify no warning when installed botocore is newer."""
    mock_botocore.__version__ = '2.0.0'
    _check_botocore_version()


# --- _make_tool_handler ---


class SimpleInput(BaseModel):
    """Simple test input model."""

    model_config = {'populate_by_name': True}

    channel_group_name: str = Field(..., alias='ChannelGroupName')


@pytest.mark.asyncio
async def test_make_tool_handler_success():
    """Verify handler calls client method and returns response."""
    mock_client = MagicMock()
    mock_client.get_channel_group.return_value = {'ChannelGroupName': 'test', 'Arn': 'arn:123'}

    op_meta = {'input_model': SimpleInput, 'tool_name': 'get_channel_group'}
    handler = _make_tool_handler('GetChannelGroup', op_meta, mock_client)
    result = await handler(SimpleInput(channel_group_name='test'))

    mock_client.get_channel_group.assert_called_once_with(ChannelGroupName='test')
    assert result['Arn'] == 'arn:123'


@pytest.mark.asyncio
async def test_make_tool_handler_client_error():
    """Verify handler returns structured error on ClientError."""
    mock_client = MagicMock()
    mock_client.get_channel_group.side_effect = ClientError(
        {'Error': {'Code': 'NotFoundException', 'Message': 'Not found'}, 'ResponseMetadata': {}},
        'GetChannelGroup',
    )

    op_meta = {'input_model': SimpleInput, 'tool_name': 'get_channel_group'}
    handler = _make_tool_handler('GetChannelGroup', op_meta, mock_client)
    result = await handler(SimpleInput(channel_group_name='test'))

    assert result['error'] == 'ClientError'
    assert result['code'] == 'NotFoundException'


@pytest.mark.asyncio
async def test_make_tool_handler_general_error():
    """Verify handler returns generic error on unexpected exception."""
    mock_client = MagicMock()
    mock_client.get_channel_group.side_effect = RuntimeError('boom')

    op_meta = {'input_model': SimpleInput, 'tool_name': 'get_channel_group'}
    handler = _make_tool_handler('GetChannelGroup', op_meta, mock_client)
    result = await handler(SimpleInput(channel_group_name='test'))

    assert result['error'] == 'RuntimeError'


@pytest.mark.asyncio
async def test_make_tool_handler_with_pagination_default():
    """Verify handler injects default page size for paginated operations."""
    mock_client = MagicMock()
    mock_client.list_channel_groups.return_value = {'Items': []}

    class ListInput(BaseModel):
        """List input model."""

        model_config = {'populate_by_name': True}
        max_results: int = Field(None, alias='MaxResults')

    op_meta = {
        'input_model': ListInput,
        'tool_name': 'list_channel_groups',
        'pagination': {'limit_key': 'MaxResults', 'output_tokens': ['NextToken']},
    }

    with patch(f'{PKG}.PAGINATION_DEFAULTS', {'ListChannelGroups': 10}):
        handler = _make_tool_handler('ListChannelGroups', op_meta, mock_client)
        await handler(ListInput())

    mock_client.list_channel_groups.assert_called_once_with(MaxResults=10)


@pytest.mark.asyncio
async def test_make_tool_handler_with_validation_error():
    """Verify handler returns validation errors when Tier 2 check fails."""
    mock_client = MagicMock()

    op_meta = {'input_model': SimpleInput, 'tool_name': 'get_channel_group'}

    with patch(f'{PKG}.VALIDATORS', {'GetChannelGroup': lambda params: ['bad reference']}):
        handler = _make_tool_handler('GetChannelGroup', op_meta, mock_client)
        result = await handler(SimpleInput(channel_group_name='test'))

    assert result['error'] == 'ValidationError'
    assert 'bad reference' in result['messages']
    mock_client.get_channel_group.assert_not_called()


@pytest.mark.asyncio
async def test_make_tool_handler_no_pagination():
    """Verify handler works without pagination metadata."""
    mock_client = MagicMock()
    mock_client.get_channel_group.return_value = {'ok': True}

    op_meta = {'input_model': SimpleInput, 'tool_name': 'get_channel_group'}
    handler = _make_tool_handler('GetChannelGroup', op_meta, mock_client)
    result = await handler(SimpleInput(channel_group_name='test'))
    assert result == {'ok': True}


@pytest.mark.asyncio
async def test_make_tool_handler_pagination_no_default():
    """Verify handler skips default injection when no PAGINATION_DEFAULTS entry."""
    mock_client = MagicMock()
    mock_client.list_channel_groups.return_value = {'Items': []}

    class ListInput(BaseModel):
        """List input."""

        model_config = {'populate_by_name': True}
        max_results: int = Field(None, alias='MaxResults')

    op_meta = {
        'input_model': ListInput,
        'tool_name': 'list_channel_groups',
        'pagination': {'limit_key': 'MaxResults'},
    }

    with patch(f'{PKG}.PAGINATION_DEFAULTS', {}):
        handler = _make_tool_handler('ListChannelGroups', op_meta, mock_client)
        await handler(ListInput())

    call_kwargs = mock_client.list_channel_groups.call_args[1]
    assert 'MaxResults' not in call_kwargs


@pytest.mark.asyncio
async def test_make_tool_handler_pagination_no_limit_key():
    """Verify handler skips default injection when pagination has no limit_key."""
    mock_client = MagicMock()
    mock_client.get_channel_group.return_value = {'ok': True}

    op_meta = {
        'input_model': SimpleInput,
        'tool_name': 'get_channel_group',
        'pagination': {'limit_key': None},
    }

    handler = _make_tool_handler('GetChannelGroup', op_meta, mock_client)
    await handler(SimpleInput(channel_group_name='test'))
    mock_client.get_channel_group.assert_called_once()


# --- _apply_field_description_overrides ---


def test_apply_field_description_overrides_to_model():
    """Verify field description overrides are applied to a model."""

    class TestModel(BaseModel):
        """Test model."""

        some_field: str = Field('', description='original')

    with patch(f'{PKG}.FIELD_DESCRIPTION_OVERRIDES', {'TestModel.some_field': 'overridden'}):
        result = _apply_field_description_overrides_to_model(TestModel)

    assert result is True
    assert TestModel.model_fields['some_field'].description == 'overridden'


def test_apply_field_description_overrides_no_match():
    """Verify no changes when no overrides match."""

    class TestModel2(BaseModel):
        """Test model 2."""

        other_field: str = Field('', description='original')

    with patch(f'{PKG}.FIELD_DESCRIPTION_OVERRIDES', {}):
        result = _apply_field_description_overrides_to_model(TestModel2)

    assert result is False


@patch(f'{PKG}.models', None)
def test_apply_all_overrides_with_no_models():
    """Verify _apply_all_field_description_overrides handles None models."""
    _apply_all_field_description_overrides()


@patch(f'{PKG}.models')
def test_apply_all_overrides_iterates_models(mock_models):
    """Verify _apply_all_field_description_overrides processes BaseModel subclasses."""

    class FakeModel(BaseModel):
        """Fake model."""

        x: str = Field('', description='orig')

    type(mock_models).__dir__ = lambda self: ['FakeModel']
    type(mock_models).FakeModel = FakeModel

    with patch(f'{PKG}.FIELD_DESCRIPTION_OVERRIDES', {}):
        _apply_all_field_description_overrides()


# --- _register_tools ---


@patch(f'{PKG}.OPERATIONS', {})
def test_register_tools_no_operations():
    """Verify _register_tools handles empty OPERATIONS gracefully."""
    _register_tools()


@patch(f'{PKG}.boto3')
@patch(f'{PKG}.OPERATIONS')
@patch(f'{PKG}.INCLUDED_OPERATIONS', {'TestOp'})
@patch(f'{PKG}.mcp')
def test_register_tools_registers_included_ops(mock_mcp, mock_ops, mock_boto3):
    """Verify _register_tools registers included operations."""
    mock_ops.__bool__ = lambda self: True
    mock_ops.items.return_value = [
        (
            'TestOp',
            {'tool_name': 'test_op', 'input_model': SimpleInput, 'auto_description': 'Test.'},
        ),
        (
            'ExcludedOp',
            {'tool_name': 'excluded', 'input_model': SimpleInput, 'auto_description': 'No.'},
        ),
    ]
    mock_mcp.tool.return_value = lambda f: f

    _register_tools()

    mock_mcp.tool.assert_called_once()
    assert mock_mcp.tool.call_args[1]['name'] == 'test_op'


@patch(f'{PKG}.boto3')
@patch(f'{PKG}.OPERATIONS')
@patch(f'{PKG}.INCLUDED_OPERATIONS', {'PagOp'})
@patch(f'{PKG}.mcp')
def test_register_tools_pagination_hints_all_fields(mock_mcp, mock_ops, mock_boto3):
    """Verify pagination hints include output_tokens, input_tokens, and limit_key."""
    mock_ops.__bool__ = lambda self: True
    mock_ops.items.return_value = [
        (
            'PagOp',
            {
                'tool_name': 'pag_op',
                'input_model': SimpleInput,
                'auto_description': 'Pag.',
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
    desc = mock_mcp.tool.call_args[1]['description']
    assert 'NextToken' in desc
    assert 'MaxResults' in desc


@patch(f'{PKG}.boto3')
@patch(f'{PKG}.OPERATIONS')
@patch(f'{PKG}.INCLUDED_OPERATIONS', {'EmptyPag'})
@patch(f'{PKG}.mcp')
def test_register_tools_pagination_hints_empty(mock_mcp, mock_ops, mock_boto3):
    """Verify pagination hints handle empty fields."""
    mock_ops.__bool__ = lambda self: True
    mock_ops.items.return_value = [
        (
            'EmptyPag',
            {
                'tool_name': 'empty_pag',
                'input_model': SimpleInput,
                'auto_description': 'Empty.',
                'pagination': {'output_tokens': [], 'input_tokens': [], 'limit_key': None},
            },
        ),
    ]
    mock_mcp.tool.return_value = lambda f: f
    _register_tools()
    assert 'pagination' in mock_mcp.tool.call_args[1]['description'].lower()


# --- _register_waiter_tool ---


@patch(f'{PKG}.WAITER_REGISTRY', {})
def test_register_waiter_tool_empty_registry():
    """Verify _register_waiter_tool skips when no waiters available."""
    _register_waiter_tool()


@patch(f'{PKG}.boto3')
@patch(f'{PKG}.mcp')
@patch(
    f'{PKG}.WAITER_REGISTRY',
    {
        'harvest_job_finished': {
            'description': 'Wait for harvest job to finish.',
            'boto3_waiter_name': 'harvest_job_finished',
            'delay': 2,
            'max_attempts': 60,
        }
    },
)
def test_register_waiter_tool_with_registry(mock_mcp, mock_boto3):
    """Verify _register_waiter_tool registers when waiters exist."""
    mock_mcp.tool.return_value = lambda f: f
    _register_waiter_tool()
    mock_mcp.tool.assert_called_once()
    assert mock_mcp.tool.call_args[1]['name'] == 'wait_for_resource'
    assert 'harvest_job_finished' in mock_mcp.tool.call_args[1]['description']


# --- _register_workflow_context_tool ---


@patch(f'{PKG}.mcp')
def test_register_workflow_context_tool(mock_mcp):
    """Verify workflow context tool is registered."""
    mock_mcp.tool.return_value = lambda f: f
    _register_workflow_context_tool()
    mock_mcp.tool.assert_called_once()
    assert mock_mcp.tool.call_args[1]['name'] == 'get_media_workflow_context'


# --- main ---


@patch(f'{PKG}.mcp')
def test_main_calls_mcp_run(mock_mcp):
    """Verify main() calls mcp.run with stdio transport."""
    main()
    mock_mcp.run.assert_called_once_with(transport='stdio')
