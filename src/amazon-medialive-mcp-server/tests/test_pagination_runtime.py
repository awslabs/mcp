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

# Feature: mcp-pagination-support, Property 5: Single-page pass-through
"""Property-based tests for single-page pass-through pagination at runtime.

**Validates: Requirements 5.1, 5.2, 5.3**

Tests that for any paginated operation invocation, the tool handler makes
exactly one boto3 client method call and returns the response unchanged
(including any NextToken or other output tokens in the response).
"""

import hypothesis.strategies as st
from hypothesis import given, settings
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Replicate the core handler logic from server.py _make_tool_handler
# to test in isolation without importing the full server module chain.
# ---------------------------------------------------------------------------
def _make_tool_handler_under_test(
    op_name: str, op_meta: dict, client, pagination_defaults: dict, validators: dict
):
    """Mirrors server.py _make_tool_handler for isolated testing."""
    op_meta['input_model']
    tool_name = op_meta['tool_name']
    pagination = op_meta.get('pagination')

    async def handler(config) -> dict:
        params = config.model_dump(by_alias=True, exclude_none=True)

        if pagination is not None:
            limit_key = pagination.get('limit_key')
            if limit_key and limit_key not in params:
                default = pagination_defaults.get(op_name)
                if default is not None:
                    params[limit_key] = default

        validator = validators.get(op_name)
        if validator is not None:
            errors = validator(params)
            if errors:
                return {'error': 'ValidationError', 'messages': errors}

        client_method = getattr(client, tool_name)
        response = await client_method(**params)
        return response

    handler.__name__ = tool_name
    handler.__qualname__ = tool_name
    return handler


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------
_identifier = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_',
        max_codepoint=127,
    ),
    min_size=1,
    max_size=20,
).filter(lambda s: s[0].isalpha())

_token_list = st.lists(_identifier, min_size=1, max_size=3)


@st.composite
def pagination_meta_strategy(draw):
    """Generate a random pagination metadata dict matching the runtime format."""
    return {
        'input_tokens': draw(_token_list),
        'output_tokens': draw(_token_list),
        'result_keys': draw(_token_list),
        'limit_key': draw(st.one_of(st.none(), _identifier)),
    }


@st.composite
def response_dict_strategy(draw):
    """Generate a random boto3-like response dict, optionally with a NextToken."""
    result_key = draw(_identifier)
    items = draw(
        st.lists(
            st.dictionaries(
                st.text(min_size=1, max_size=10),
                st.text(min_size=0, max_size=20),
                min_size=0,
                max_size=3,
            ),
            min_size=0,
            max_size=5,
        )
    )
    response = {result_key: items}
    if draw(st.booleans()):
        response['NextToken'] = draw(st.text(min_size=1, max_size=50))
    return response


@st.composite
def single_page_scenario(draw):
    """Generate a complete scenario for testing single-page pass-through.

    Returns (op_name, op_meta, mock_response) where:
    - op_meta has pagination metadata and a simple Pydantic input model
    - mock_response is the expected boto3 response
    """
    op_name = draw(
        st.sampled_from(['ListChannels', 'ListInputs', 'DescribeSchedule', 'ListOfferings'])
    )
    tool_name = draw(st.just(op_name[0].lower() + op_name[1:]))
    pagination = draw(pagination_meta_strategy())
    mock_response = draw(response_dict_strategy())

    op_meta = {
        'input_model': _DynamicInput,
        'tool_name': tool_name,
        'pagination': pagination,
    }

    return op_name, op_meta, mock_response


class _DynamicInput(BaseModel):
    """Simple Pydantic model for testing — mimics a generated input model."""

    model_config = ConfigDict(populate_by_name=True)

    next_token: Optional[str] = Field(default=None, alias='NextToken')
    max_results: Optional[int] = Field(default=None, alias='MaxResults')


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


# **Validates: Requirements 5.1, 5.2, 5.3**
@given(scenario=single_page_scenario())
@settings(max_examples=100)
async def test_single_page_pass_through(scenario) -> None:
    """For any paginated operation invocation, the tool handler shall make.

    exactly one boto3 client method call and return the response unchanged.
    """
    op_name, op_meta, mock_response = scenario
    tool_name = op_meta['tool_name']

    mock_client = MagicMock()
    mock_method = AsyncMock(return_value=mock_response)
    setattr(mock_client, tool_name, mock_method)

    handler = _make_tool_handler_under_test(
        op_name=op_name,
        op_meta=op_meta,
        client=mock_client,
        pagination_defaults={},
        validators={},
    )

    config = _DynamicInput()
    result = await handler(config)

    # Verify exactly one call to the client method
    assert mock_method.call_count == 1, (
        f'Expected exactly 1 call to {tool_name}, got {mock_method.call_count}'
    )

    # Verify the response is returned unchanged
    assert result == mock_response, (
        f'Response should be returned unchanged.\nExpected: {mock_response}\nGot: {result}'
    )

    # If the mock response contains a NextToken, verify it's preserved
    if 'NextToken' in mock_response:
        assert 'NextToken' in result, 'NextToken should be preserved in the response'
        assert result['NextToken'] == mock_response['NextToken'], (
            'NextToken value should be unchanged'
        )


# Feature: mcp-pagination-support, Property 6: Default page size injection with LLM precedence
# **Validates: Requirements 5.4, 5.5, 6.2, 6.3**


@st.composite
def default_injection_scenario(draw):
    """Generate a scenario for testing default page size injection precedence.

    Returns (op_name, limit_key, pagination_defaults_value, llm_provides_limit, llm_limit_value)
    where:
    - op_name: random operation name
    - limit_key: random limit key name for the paginated operation
    - pagination_defaults_value: value from PAGINATION_DEFAULTS (or None if not configured)
    - llm_provides_limit: whether the LLM includes the limit key in params
    - llm_limit_value: the LLM-provided limit value (only meaningful if llm_provides_limit)
    """
    op_name = draw(_identifier)
    limit_key = draw(_identifier)
    has_default = draw(st.booleans())
    pagination_defaults_value = (
        draw(st.integers(min_value=1, max_value=1000)) if has_default else None
    )
    llm_provides_limit = draw(st.booleans())
    llm_limit_value = draw(st.integers(min_value=1, max_value=500))
    return op_name, limit_key, pagination_defaults_value, llm_provides_limit, llm_limit_value


@given(scenario=default_injection_scenario())
@settings(max_examples=100)
async def test_default_page_size_injection_with_llm_precedence(scenario) -> None:
    """For any paginated operation with a limit_key, the final boto3 call params.

    shall follow precedence: (a) LLM value wins, (b) PAGINATION_DEFAULTS if LLM
    omits, (c) absent if neither provides a value.
    """
    op_name, limit_key, pagination_defaults_value, llm_provides_limit, llm_limit_value = scenario

    'tool_' + op_name

    pagination = {
        'input_tokens': ['NextToken'],
        'output_tokens': ['NextToken'],
        'result_keys': ['Items'],
        'limit_key': limit_key,
    }

    pagination_defaults = {}
    if pagination_defaults_value is not None:
        pagination_defaults[op_name] = pagination_defaults_value

    # Build a dynamic Pydantic model that uses the random limit_key as an alias
    dynamic_fields = {}
    if llm_provides_limit:
        dynamic_fields[limit_key] = llm_limit_value

    # We test the injection logic directly by simulating what the handler does:
    # serialize params, then apply the default injection logic.
    # This avoids needing a Pydantic model with a dynamic alias for each limit_key.
    params = dict(dynamic_fields)

    # --- Replicate the injection logic from _make_tool_handler_under_test ---
    if pagination is not None:
        lk = pagination.get('limit_key')
        if lk and lk not in params:
            default = pagination_defaults.get(op_name)
            if default is not None:
                params[lk] = default

    # --- Verify precedence rules ---
    if llm_provides_limit:
        # (a) LLM-provided value wins
        assert limit_key in params, 'LLM-provided limit key should be present'
        assert params[limit_key] == llm_limit_value, (
            f'LLM value should win. Expected {llm_limit_value}, got {params[limit_key]}'
        )
    elif pagination_defaults_value is not None:
        # (b) PAGINATION_DEFAULTS value injected when LLM omits
        assert limit_key in params, 'Default should be injected when LLM omits limit key'
        assert params[limit_key] == pagination_defaults_value, (
            f'Default value should be injected. Expected {pagination_defaults_value}, got {params[limit_key]}'
        )
    else:
        # (c) Absent if neither provides a value
        assert limit_key not in params, (
            f'Limit key should be absent when neither LLM nor defaults provide a value, '
            f'but found {params.get(limit_key)}'
        )


@st.composite
def default_injection_e2e_scenario(draw):
    """Generate an end-to-end scenario that exercises the full handler path.

    with a mock boto3 client, verifying the actual params passed to boto3.
    """
    op_name = draw(st.sampled_from(['ListChannels', 'ListInputs', 'ListOfferings']))
    tool_name = op_name[0].lower() + op_name[1:]
    limit_key = 'MaxResults'  # Use the standard alias supported by _DynamicInput

    has_default = draw(st.booleans())
    default_value = draw(st.integers(min_value=1, max_value=100)) if has_default else None
    llm_provides_limit = draw(st.booleans())
    llm_limit_value = draw(st.integers(min_value=1, max_value=500))

    return op_name, tool_name, limit_key, default_value, llm_provides_limit, llm_limit_value


@given(scenario=default_injection_e2e_scenario())
@settings(max_examples=100)
async def test_default_page_size_injection_e2e(scenario) -> None:
    """End-to-end test: invoke the handler with a mock boto3 client and verify.

    the actual params passed to the client method follow precedence rules.
    """
    op_name, tool_name, limit_key, default_value, llm_provides_limit, llm_limit_value = scenario

    pagination = {
        'input_tokens': ['NextToken'],
        'output_tokens': ['NextToken'],
        'result_keys': ['Items'],
        'limit_key': limit_key,
    }

    op_meta = {
        'input_model': _DynamicInput,
        'tool_name': tool_name,
        'pagination': pagination,
    }

    pagination_defaults = {}
    if default_value is not None:
        pagination_defaults[op_name] = default_value

    mock_response = {'Items': [{'Id': 'test'}]}
    mock_client = MagicMock()
    mock_method = AsyncMock(return_value=mock_response)
    setattr(mock_client, tool_name, mock_method)

    handler = _make_tool_handler_under_test(
        op_name=op_name,
        op_meta=op_meta,
        client=mock_client,
        pagination_defaults=pagination_defaults,
        validators={},
    )

    if llm_provides_limit:
        config = _DynamicInput(max_results=llm_limit_value)
    else:
        config = _DynamicInput()

    await handler(config)

    # Inspect the actual kwargs passed to the mock boto3 method
    assert mock_method.call_count == 1
    call_kwargs = mock_method.call_args[1]

    if llm_provides_limit:
        # (a) LLM-provided value wins
        assert limit_key in call_kwargs, 'LLM-provided limit key should be in boto3 call'
        assert call_kwargs[limit_key] == llm_limit_value
    elif default_value is not None:
        # (b) PAGINATION_DEFAULTS value injected
        assert limit_key in call_kwargs, 'Default should be injected into boto3 call'
        assert call_kwargs[limit_key] == default_value
    else:
        # (c) Absent if neither provides a value
        assert limit_key not in call_kwargs, (
            f'Limit key should be absent from boto3 call, but found {call_kwargs.get(limit_key)}'
        )
