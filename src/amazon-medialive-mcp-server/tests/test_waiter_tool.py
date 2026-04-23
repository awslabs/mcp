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

"""Unit tests for waiter tool handler.

Example-based tests covering specific scenarios for the wait_for_resource tool:
- Successful waiter completion
- ClientError during polling
- Unexpected exception during polling
- Empty WAITER_REGISTRY skips registration
- WaitForResourceInput model field types and required/optional status

Validates: Requirements 3.4, 3.5, 4.1, 4.2, 4.3
"""

import os
import pytest
import sys
from typing import Optional
from unittest.mock import MagicMock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.amazon_medialive_mcp_server.errors import (
    handle_client_error,
    handle_general_error,
)
from awslabs.amazon_medialive_mcp_server.server import (
    WaiterConfig,
    WaitForResourceInput,
    _register_waiter_tool,
)
from botocore.exceptions import ClientError, WaiterError
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Shared test registry and handler builder
# ---------------------------------------------------------------------------

TEST_REGISTRY = {
    'channel_running': {
        'boto3_waiter_name': 'channel_running',
        'description': 'Wait until channel is running',
        'delay': 5,
        'max_attempts': 120,
    },
}


def _build_handler(registry):
    """Build a standalone async handler replicating _register_waiter_tool() logic.

    Returns (handler, mock_client) so tests can inspect boto3 calls.
    """
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

        registry_entry = registry[config.waiter_name]
        boto3_name = registry_entry['boto3_waiter_name']

        waiter_kwargs = {
            'Delay': registry_entry['delay'],
            'MaxAttempts': registry_entry['max_attempts'],
        }
        if config.waiter_config is not None:
            overrides = config.waiter_config.model_dump(exclude_none=True)
            waiter_kwargs.update(overrides)

        try:
            waiter = mock_client.get_waiter(boto3_name)
            waiter.wait(WaiterConfig=waiter_kwargs, **config.params)
            return {
                'status': 'success',
                'waiter_name': config.waiter_name,
                'message': f'Resource reached desired state (waiter: {config.waiter_name})',
            }
        except WaiterError as e:
            return {
                'error': 'WaiterError',
                'waiter_name': config.waiter_name,
                'message': str(e),
            }
        except ClientError as e:
            return handle_client_error(e)
        except Exception as e:
            return handle_general_error(e)

    return wait_for_resource, mock_client


# ---------------------------------------------------------------------------
# Test: Successful waiter completion returns success dict with waiter_name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_waiter_completion():
    """Validates: Requirements 3.4, 3.5."""
    handler, mock_client = _build_handler(TEST_REGISTRY)

    config = WaitForResourceInput(
        waiter_name='channel_running',
        params={'ChannelId': '12345'},
    )

    result = await handler(config)

    assert result['status'] == 'success'
    assert result['waiter_name'] == 'channel_running'
    assert 'channel_running' in result['message']

    mock_client.get_waiter.assert_called_once_with('channel_running')
    mock_waiter = mock_client.get_waiter.return_value
    mock_waiter.wait.assert_called_once()
    call_kwargs = mock_waiter.wait.call_args.kwargs
    assert call_kwargs['ChannelId'] == '12345'
    assert call_kwargs['WaiterConfig']['Delay'] == 5
    assert call_kwargs['WaiterConfig']['MaxAttempts'] == 120


# ---------------------------------------------------------------------------
# Test: ClientError during polling delegates to handle_client_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_error_during_polling():
    """Validates: Requirements 4.2."""
    handler, mock_client = _build_handler(TEST_REGISTRY)

    client_error = ClientError(
        {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'},
            'ResponseMetadata': {},
        },
        'DescribeChannel',
    )
    mock_waiter = mock_client.get_waiter.return_value
    mock_waiter.wait.side_effect = client_error

    config = WaitForResourceInput(
        waiter_name='channel_running',
        params={'ChannelId': '12345'},
    )

    result = await handler(config)

    assert result['error'] == 'ClientError'
    assert result['code'] == 'AccessDeniedException'
    assert result['message'] == 'Not authorized'


# ---------------------------------------------------------------------------
# Test: Unexpected exception delegates to handle_general_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unexpected_exception_delegates_to_handle_general_error():
    """Validates: Requirements 4.3."""
    handler, mock_client = _build_handler(TEST_REGISTRY)

    mock_waiter = mock_client.get_waiter.return_value
    mock_waiter.wait.side_effect = RuntimeError('Something broke internally')

    config = WaitForResourceInput(
        waiter_name='channel_running',
        params={'ChannelId': '12345'},
    )

    result = await handler(config)

    assert result['error'] == 'RuntimeError'
    assert 'unexpected error' in result['message'].lower()
    # Internal details should NOT be exposed
    assert 'Something broke internally' not in result['message']


# ---------------------------------------------------------------------------
# Test: Empty WAITER_REGISTRY causes _register_waiter_tool() to skip
# ---------------------------------------------------------------------------


def test_empty_registry_skips_registration():
    """Validates: Requirements 7.2."""
    with (
        patch('awslabs.amazon_medialive_mcp_server.server.WAITER_REGISTRY', {}),
        patch('awslabs.amazon_medialive_mcp_server.server.mcp') as mock_mcp,
        patch('awslabs.amazon_medialive_mcp_server.server.logger') as mock_logger,
    ):
        _register_waiter_tool()

        # mcp.tool() should NOT have been called
        mock_mcp.tool.assert_not_called()

        # Logger should have logged an info message about skipping
        mock_logger.info.assert_any_call(
            'No waiters available for this service — skipping waiter tool registration.'
        )


# ---------------------------------------------------------------------------
# Test: WaitForResourceInput model field types and required/optional status
# ---------------------------------------------------------------------------


class TestWaitForResourceInputModel:
    """Validates: Requirements 2.3."""

    def test_waiter_name_is_required_string(self):
        """Validate waiter_name is a required field."""
        with pytest.raises(ValidationError):
            WaitForResourceInput(params={'ChannelId': '123'})

    def test_params_is_required_dict(self):
        """Validate params is a required field."""
        with pytest.raises(ValidationError):
            WaitForResourceInput(waiter_name='channel_running')

    def test_waiter_config_is_optional(self):
        """Validate waiter_config defaults to None."""
        model = WaitForResourceInput(
            waiter_name='channel_running',
            params={'ChannelId': '123'},
        )
        assert model.waiter_config is None

    def test_waiter_config_accepts_waiter_config_object(self):
        """Validate waiter_config accepts WaiterConfig."""
        model = WaitForResourceInput(
            waiter_name='channel_running',
            params={'ChannelId': '123'},
            waiter_config=WaiterConfig(Delay=10, MaxAttempts=5),
        )
        assert model.waiter_config is not None
        assert model.waiter_config.Delay == 10
        assert model.waiter_config.MaxAttempts == 5

    def test_field_types(self):
        """Validate field type annotations."""
        fields = WaitForResourceInput.model_fields
        assert fields['waiter_name'].annotation is str
        assert fields['params'].annotation is dict
        assert fields['waiter_config'].annotation == Optional[WaiterConfig]

    def test_waiter_config_delay_and_max_attempts_are_optional(self):
        """Validate WaiterConfig fields are optional."""
        wc = WaiterConfig()
        assert wc.Delay is None
        assert wc.MaxAttempts is None

    def test_waiter_config_partial_override(self):
        """Validate partial WaiterConfig override."""
        wc = WaiterConfig(Delay=3)
        assert wc.Delay == 3
        assert wc.MaxAttempts is None
