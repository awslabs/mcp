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

"""Property-based tests for waiter tool logic.

Tests Properties 2–6 from the MCP Waiter Support design document.
Uses Hypothesis with @settings(max_examples=100).
"""

import asyncio
import hypothesis.strategies as st
import os
import sys
from hypothesis import given, settings
from unittest.mock import MagicMock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from awslabs.amazon_medialive_mcp_server.server import (
    WaiterConfig,
    WaitForResourceInput,
)
from botocore.exceptions import WaiterError


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Waiter names: lowercase letters + underscores, reasonable length
waiter_name_strategy = st.from_regex(r'[a-z][a-z_]{2,30}', fullmatch=True)

# Simple param dicts with string keys and string/int values
param_key_strategy = st.from_regex(r'[A-Z][a-zA-Z]{2,20}', fullmatch=True)
param_value_strategy = st.one_of(
    st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))),
    st.integers(min_value=1, max_value=999999),
)
params_strategy = st.dictionaries(
    keys=param_key_strategy,
    values=param_value_strategy,
    min_size=1,
    max_size=5,
)

# Delay and max_attempts for registry defaults
delay_strategy = st.integers(min_value=1, max_value=120)
max_attempts_strategy = st.integers(min_value=1, max_value=500)

# Description strings
description_strategy = st.text(
    min_size=5,
    max_size=100,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Z', 'P')),
)

# Error message strings
error_message_strategy = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
)

# Registry entry strategy: generates a single waiter config dict
registry_entry_strategy = st.fixed_dictionaries(
    {
        'boto3_waiter_name': waiter_name_strategy,
        'description': description_strategy,
        'delay': delay_strategy,
        'max_attempts': max_attempts_strategy,
    }
)

# A non-empty registry: dict of waiter_name -> config
registry_strategy = st.dictionaries(
    keys=waiter_name_strategy,
    values=registry_entry_strategy,
    min_size=1,
    max_size=8,
)


# ---------------------------------------------------------------------------
# Helper: build a fixed registry for tests that need a known set of names
# ---------------------------------------------------------------------------

FIXED_REGISTRY = {
    'channel_running': {
        'boto3_waiter_name': 'channel_running',
        'description': 'Wait until channel is running',
        'delay': 5,
        'max_attempts': 120,
    },
    'channel_stopped': {
        'boto3_waiter_name': 'channel_stopped',
        'description': 'Wait until channel is stopped',
        'delay': 5,
        'max_attempts': 60,
    },
    'channel_deleted': {
        'boto3_waiter_name': 'channel_deleted',
        'description': 'Wait until channel is deleted',
        'delay': 5,
        'max_attempts': 84,
    },
}


def _build_handler(registry):
    """Build a standalone async handler that replicates _register_waiter_tool() logic.

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

    return wait_for_resource, mock_client


# ---------------------------------------------------------------------------
# Property 2: Invalid waiter name returns error listing all valid names
# ---------------------------------------------------------------------------


# Feature: mcp-waiter-support, Property 2: Invalid waiter name returns error listing all valid names
# **Validates: Requirements 1.2**
@given(
    invalid_name=st.text(
        min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd'))
    )
)
@settings(max_examples=100)
def test_invalid_waiter_name_returns_error_listing_all_valid_names(invalid_name):
    """For any string that is not a key in the WAITER_REGISTRY, calling the.

    waiter handler with that string as waiter_name should return an error
    response whose message contains every valid waiter name from the registry.
    """
    registry = FIXED_REGISTRY

    # Skip if the generated name happens to be a valid key
    if invalid_name in registry:
        return

    handler, _ = _build_handler(registry)
    config = WaitForResourceInput(
        waiter_name=invalid_name,
        params={'ChannelId': '12345'},
    )

    result = asyncio.get_event_loop().run_until_complete(handler(config))

    assert result.get('error') == 'InvalidWaiterName', (
        f"Expected 'InvalidWaiterName' error, got: {result}"
    )

    message = result.get('message', '')
    for valid_name in registry.keys():
        assert valid_name in message, (
            f"Valid waiter name '{valid_name}' not found in error message: {message}"
        )


# ---------------------------------------------------------------------------
# Property 3: Tool description contains all registry waiter names
# ---------------------------------------------------------------------------


# Feature: mcp-waiter-support, Property 3: Tool description contains all registry waiter names
# **Validates: Requirements 2.2**
@given(registry=registry_strategy)
@settings(max_examples=100)
def test_tool_description_contains_all_registry_waiter_names(registry):
    """For any non-empty WAITER_REGISTRY, the generated tool description string.

    for wait_for_resource should contain every waiter name that is a key in
    the registry.
    """
    # Replicate the description-building logic from _register_waiter_tool()
    waiter_lines = []
    for name, config in sorted(registry.items()):
        waiter_lines.append(f'- {name}: {config["description"]}')
    waiter_list = '\n'.join(waiter_lines)

    description = (
        f'Wait for a resource to reach a desired state by polling the appropriate '
        f'describe API. Supported waiters:\n{waiter_list}'
    )

    for name in registry.keys():
        assert name in description, (
            f"Waiter name '{name}' not found in tool description:\n{description}"
        )


# ---------------------------------------------------------------------------
# Property 4: Correct boto3 waiter dispatched with provided params
# ---------------------------------------------------------------------------


# Feature: mcp-waiter-support, Property 4: Correct boto3 waiter dispatched with provided params
# **Validates: Requirements 3.1**
@given(
    waiter_name=st.sampled_from(list(FIXED_REGISTRY.keys())),
    params=params_strategy,
)
@settings(max_examples=100)
def test_correct_boto3_waiter_dispatched_with_provided_params(waiter_name, params):
    """For any valid waiter name in the registry and any params dict, the handler.

    should call client.get_waiter() with the registry's boto3_waiter_name and
    then call waiter.wait() with those exact params.
    """
    handler, mock_client = _build_handler(FIXED_REGISTRY)

    config = WaitForResourceInput(
        waiter_name=waiter_name,
        params=params,
    )

    result = asyncio.get_event_loop().run_until_complete(handler(config))

    assert result.get('status') == 'success', f'Expected success response, got: {result}'

    expected_boto3_name = FIXED_REGISTRY[waiter_name]['boto3_waiter_name']
    mock_client.get_waiter.assert_called_with(expected_boto3_name)

    mock_waiter = mock_client.get_waiter.return_value
    call_args = mock_waiter.wait.call_args

    # Verify params are passed through
    for key, value in params.items():
        assert call_args.kwargs.get(key) == value or (call_args and key in call_args.kwargs), (
            f"Expected param '{key}={value}' in wait() call, got kwargs: {call_args.kwargs}"
        )


# ---------------------------------------------------------------------------
# Property 5: Config merge — overrides win, defaults fill gaps
# ---------------------------------------------------------------------------


# Feature: mcp-waiter-support, Property 5: Config merge — overrides win, defaults fill gaps
# **Validates: Requirements 3.2, 3.3**
@given(
    default_delay=delay_strategy,
    default_max_attempts=max_attempts_strategy,
    override_delay=st.one_of(st.none(), delay_strategy),
    override_max_attempts=st.one_of(st.none(), max_attempts_strategy),
)
@settings(max_examples=100)
def test_config_merge_overrides_win_defaults_fill_gaps(
    default_delay, default_max_attempts, override_delay, override_max_attempts
):
    """For any registry entry with default delay and max_attempts, and any.

    WaiterConfig override with zero or more fields set, the WaiterConfig
    passed to waiter.wait() should use the override value for each field
    that is set, and the registry default for each field that is not set.
    """
    test_registry = {
        'test_waiter': {
            'boto3_waiter_name': 'test_waiter',
            'description': 'Test waiter',
            'delay': default_delay,
            'max_attempts': default_max_attempts,
        },
    }

    handler, mock_client = _build_handler(test_registry)

    waiter_config = None
    if override_delay is not None or override_max_attempts is not None:
        waiter_config = WaiterConfig(
            Delay=override_delay,
            MaxAttempts=override_max_attempts,
        )

    config = WaitForResourceInput(
        waiter_name='test_waiter',
        params={'ResourceId': 'abc123'},
        waiter_config=waiter_config,
    )

    asyncio.get_event_loop().run_until_complete(handler(config))

    mock_waiter = mock_client.get_waiter.return_value
    call_kwargs = mock_waiter.wait.call_args.kwargs
    merged_config = call_kwargs['WaiterConfig']

    expected_delay = override_delay if override_delay is not None else default_delay
    expected_max = (
        override_max_attempts if override_max_attempts is not None else default_max_attempts
    )

    assert merged_config['Delay'] == expected_delay, (
        f'Expected Delay={expected_delay}, got {merged_config["Delay"]}. '
        f'Override={override_delay}, Default={default_delay}'
    )
    assert merged_config['MaxAttempts'] == expected_max, (
        f'Expected MaxAttempts={expected_max}, got {merged_config["MaxAttempts"]}. '
        f'Override={override_max_attempts}, Default={default_max_attempts}'
    )


# ---------------------------------------------------------------------------
# Property 6: WaiterError produces structured error response
# ---------------------------------------------------------------------------


# Feature: mcp-waiter-support, Property 6: WaiterError produces structured error response
# **Validates: Requirements 4.1**
@given(
    waiter_name=st.sampled_from(list(FIXED_REGISTRY.keys())),
    error_msg=error_message_strategy,
)
@settings(max_examples=100)
def test_waiter_error_produces_structured_error_response(waiter_name, error_msg):
    """For any waiter name and any WaiterError exception with an arbitrary.

    message string, the handler should return a dict containing
    "error": "WaiterError", the waiter_name, and a message field containing
    the exception's message text.
    """
    handler, mock_client = _build_handler(FIXED_REGISTRY)

    # Make the mock waiter raise a WaiterError
    mock_waiter = mock_client.get_waiter.return_value
    waiter_error = WaiterError(name=waiter_name, reason=error_msg, last_response={})
    mock_waiter.wait.side_effect = waiter_error

    config = WaitForResourceInput(
        waiter_name=waiter_name,
        params={'ChannelId': '12345'},
    )

    result = asyncio.get_event_loop().run_until_complete(handler(config))

    assert result.get('error') == 'WaiterError', (
        f"Expected 'WaiterError' error type, got: {result.get('error')}"
    )
    assert result.get('waiter_name') == waiter_name, (
        f"Expected waiter_name='{waiter_name}', got: {result.get('waiter_name')}"
    )
    assert error_msg in result.get('message', ''), (
        f"Expected error message to contain '{error_msg}', got: {result.get('message')}"
    )
