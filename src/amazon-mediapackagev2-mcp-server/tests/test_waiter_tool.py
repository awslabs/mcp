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

"""Unit tests for waiter tool handler."""

import pytest
from awslabs.amazon_mediapackagev2_mcp_server.errors import (
    handle_client_error,
    handle_general_error,
)
from awslabs.amazon_mediapackagev2_mcp_server.server import (
    WaiterConfig,
    WaitForResourceInput,
    _register_waiter_tool,
)
from botocore.exceptions import ClientError, WaiterError
from pydantic import ValidationError
from typing import Optional
from unittest.mock import MagicMock, patch


TEST_REGISTRY = {
    'harvest_job_finished': {
        'boto3_waiter_name': 'harvest_job_finished',
        'description': 'Wait until harvest job finishes',
        'delay': 2,
        'max_attempts': 60,
    },
}


def _build_handler(registry):
    """Build a standalone async handler replicating _register_waiter_tool() logic."""
    mock_waiter = MagicMock()
    mock_waiter.wait = MagicMock()
    mock_client = MagicMock()
    mock_client.get_waiter = MagicMock(return_value=mock_waiter)

    async def wait_for_resource(config: WaitForResourceInput) -> dict:
        if config.waiter_name not in registry:
            return {
                'error': 'InvalidWaiterName',
                'message': f"Unknown waiter '{config.waiter_name}'. "
                f'Valid waiters: {sorted(registry.keys())}',
            }
        entry = registry[config.waiter_name]
        waiter_kwargs = {'Delay': entry['delay'], 'MaxAttempts': entry['max_attempts']}
        if config.waiter_config is not None:
            waiter_kwargs.update(config.waiter_config.model_dump(exclude_none=True))
        try:
            waiter = mock_client.get_waiter(entry['boto3_waiter_name'])
            waiter.wait(WaiterConfig=waiter_kwargs, **config.params)
            return {
                'status': 'success',
                'waiter_name': config.waiter_name,
                'message': f'Resource reached desired state (waiter: {config.waiter_name})',
            }
        except WaiterError as e:
            return {'error': 'WaiterError', 'waiter_name': config.waiter_name, 'message': str(e)}
        except ClientError as e:
            return handle_client_error(e)
        except Exception as e:
            return handle_general_error(e)

    return wait_for_resource, mock_client


@pytest.mark.asyncio
async def test_successful_waiter_completion():
    """Verify successful waiter returns success dict."""
    handler, mock_client = _build_handler(TEST_REGISTRY)
    config = WaitForResourceInput(
        waiter_name='harvest_job_finished',
        params={'ChannelGroupName': 'grp', 'ChannelName': 'ch', 'OriginEndpointName': 'ep'},
    )
    result = await handler(config)
    assert result['status'] == 'success'
    assert result['waiter_name'] == 'harvest_job_finished'
    mock_client.get_waiter.assert_called_once_with('harvest_job_finished')


@pytest.mark.asyncio
async def test_invalid_waiter_name():
    """Verify unknown waiter name returns error."""
    handler, _ = _build_handler(TEST_REGISTRY)
    config = WaitForResourceInput(waiter_name='nonexistent', params={})
    result = await handler(config)
    assert result['error'] == 'InvalidWaiterName'


@pytest.mark.asyncio
async def test_client_error_during_polling():
    """Verify ClientError during polling is handled."""
    handler, mock_client = _build_handler(TEST_REGISTRY)
    mock_client.get_waiter.return_value.wait.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'No access'}, 'ResponseMetadata': {}},
        'GetHarvestJob',
    )
    config = WaitForResourceInput(waiter_name='harvest_job_finished', params={})
    result = await handler(config)
    assert result['error'] == 'ClientError'
    assert result['code'] == 'AccessDenied'


@pytest.mark.asyncio
async def test_unexpected_exception():
    """Verify unexpected exception is handled."""
    handler, mock_client = _build_handler(TEST_REGISTRY)
    mock_client.get_waiter.return_value.wait.side_effect = RuntimeError('boom')
    config = WaitForResourceInput(waiter_name='harvest_job_finished', params={})
    result = await handler(config)
    assert result['error'] == 'RuntimeError'


@pytest.mark.asyncio
async def test_waiter_config_override():
    """Verify waiter config overrides are applied."""
    handler, mock_client = _build_handler(TEST_REGISTRY)
    config = WaitForResourceInput(
        waiter_name='harvest_job_finished',
        params={},
        waiter_config=WaiterConfig(Delay=10, MaxAttempts=5),
    )
    await handler(config)
    call_kwargs = mock_client.get_waiter.return_value.wait.call_args.kwargs
    assert call_kwargs['WaiterConfig']['Delay'] == 10
    assert call_kwargs['WaiterConfig']['MaxAttempts'] == 5


def test_empty_registry_skips_registration():
    """Verify empty registry skips waiter tool registration."""
    with (
        patch('awslabs.amazon_mediapackagev2_mcp_server.server.WAITER_REGISTRY', {}),
        patch('awslabs.amazon_mediapackagev2_mcp_server.server.mcp') as mock_mcp,
    ):
        _register_waiter_tool()
        mock_mcp.tool.assert_not_called()


class TestWaitForResourceInputModel:
    """Tests for WaitForResourceInput model validation."""

    def test_waiter_name_is_required(self):
        """Validate waiter_name is required."""
        with pytest.raises(ValidationError):
            WaitForResourceInput(params={})

    def test_params_is_required(self):
        """Validate params is required."""
        with pytest.raises(ValidationError):
            WaitForResourceInput(waiter_name='test')

    def test_waiter_config_is_optional(self):
        """Validate waiter_config defaults to None."""
        model = WaitForResourceInput(waiter_name='test', params={})
        assert model.waiter_config is None

    def test_waiter_config_partial_override(self):
        """Validate partial WaiterConfig override."""
        wc = WaiterConfig(Delay=3)
        assert wc.Delay == 3
        assert wc.MaxAttempts is None

    def test_field_types(self):
        """Validate field type annotations."""
        fields = WaitForResourceInput.model_fields
        assert fields['waiter_name'].annotation is str
        assert fields['params'].annotation is dict
        assert fields['waiter_config'].annotation == Optional[WaiterConfig]
