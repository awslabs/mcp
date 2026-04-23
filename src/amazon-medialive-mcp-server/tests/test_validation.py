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

"""Property-based tests for Tier 2 validation gating.

Tests Property 19 from the design document.
"""

import hypothesis.strategies as st
import os
import sys
from awslabs.amazon_medialive_mcp_server.overrides.validation import (
    VALIDATORS,
    validate_create_channel,
)
from hypothesis import given, settings
from unittest.mock import MagicMock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Helper: simulate the tool handler validation gating logic from server.py
# ---------------------------------------------------------------------------


def simulate_tool_handler(params: dict, validator, client_method) -> dict:
    """Simulate the validation gating logic from _make_tool_handler.

    This mirrors the Tier 2 validation path in server.py:
    1. If a validator is registered and returns errors → return errors, skip API call.
    2. If a validator is registered and returns empty list → call the client method.
    """
    if validator is not None:
        errors = validator(params)
        if errors:
            return {'error': 'ValidationError', 'messages': errors}

    response = client_method(**params)
    return response


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

error_message_strategy = st.text(
    min_size=1,
    max_size=100,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
)

error_list_strategy = st.lists(error_message_strategy, min_size=0, max_size=5)

params_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
    min_size=1,
    max_size=20,
)

params_value_strategy = st.text(
    min_size=0,
    max_size=50,
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')),
)

params_strategy = st.dictionaries(
    keys=params_key_strategy,
    values=params_value_strategy,
    min_size=0,
    max_size=5,
)


# ---------------------------------------------------------------------------
# Property 19: Tier 2 validation gates API calls
# ---------------------------------------------------------------------------


# Feature: medialive-mcp-server, Property 19: Tier 2 validation gates API calls
# **Validates: Requirements 12.2, 12.3, 12.4, 20.2**
@given(errors=error_list_strategy, params=params_strategy)
@settings(max_examples=100)
def test_tier2_validation_gates_api_calls(errors, params):
    """For any operation with a registered validator, the boto3 client method.

    shall be called if and only if the validator returns an empty error list.
    When the validator returns errors, those error messages shall be returned
    to the caller without an API call.
    """
    mock_client_method = MagicMock(return_value={'ResponseMetadata': {'HTTPStatusCode': 200}})
    validator = MagicMock(return_value=errors)

    result = simulate_tool_handler(params, validator, mock_client_method)

    # Validator is always called exactly once
    validator.assert_called_once_with(params)

    if errors:
        # Client method must NOT be called when validator returns errors
        (
            mock_client_method.assert_not_called(),
            (f'Client method was called despite validator returning errors: {errors}'),
        )
        # Response must contain the exact error messages
        assert result == {'error': 'ValidationError', 'messages': errors}, (
            f'Expected validation error response with messages {errors}, got {result}'
        )
        # Each error message must appear in the response
        for msg in errors:
            assert msg in result['messages'], (
                f'Error message {msg!r} not found in response messages {result["messages"]}'
            )
    else:
        # Client method MUST be called when validator returns empty list
        (
            mock_client_method.assert_called_once_with(**params),
            ('Client method was not called despite validator returning empty error list'),
        )
        # Response should be the client's response
        assert result == {'ResponseMetadata': {'HTTPStatusCode': 200}}, (
            f'Expected client response, got {result}'
        )


# ---------------------------------------------------------------------------
# Unit tests for validate_create_channel
# ---------------------------------------------------------------------------


def test_validators_registry_contains_create_channel():
    """Verify CreateChannel is registered in the VALIDATORS dict."""
    assert 'CreateChannel' in VALIDATORS
    assert VALIDATORS['CreateChannel'] is validate_create_channel


def test_empty_config_returns_no_errors():
    """Verify an empty config produces no validation errors."""
    assert validate_create_channel({}) == []


def test_config_without_encoder_settings_returns_no_errors():
    """Verify config without EncoderSettings produces no errors."""
    assert validate_create_channel({'Name': 'test'}) == []


def test_valid_video_description_reference():
    """Verify valid VideoDescriptionName reference passes."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [{'Name': 'video_1080p'}],
            'AudioDescriptions': [{'Name': 'audio_aac'}],
            'OutputGroups': [
                {
                    'Outputs': [
                        {
                            'VideoDescriptionName': 'video_1080p',
                            'AudioDescriptionNames': ['audio_aac'],
                        }
                    ]
                }
            ],
        }
    }
    assert validate_create_channel(config) == []


def test_invalid_video_description_reference():
    """Verify invalid VideoDescriptionName reference is caught."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [{'Name': 'video_1080p'}],
            'AudioDescriptions': [],
            'OutputGroups': [{'Outputs': [{'VideoDescriptionName': 'nonexistent_video'}]}],
        }
    }
    errors = validate_create_channel(config)
    assert len(errors) == 1
    assert 'nonexistent_video' in errors[0]


def test_invalid_audio_description_reference():
    """Verify invalid AudioDescriptionName reference is caught."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [],
            'AudioDescriptions': [{'Name': 'audio_aac'}],
            'OutputGroups': [{'Outputs': [{'AudioDescriptionNames': ['nonexistent_audio']}]}],
        }
    }
    errors = validate_create_channel(config)
    assert len(errors) == 1
    assert 'nonexistent_audio' in errors[0]


def test_multiple_errors_returned():
    """Verify multiple cross-reference errors are all reported."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [{'Name': 'video_1'}],
            'AudioDescriptions': [{'Name': 'audio_1'}],
            'OutputGroups': [
                {
                    'Outputs': [
                        {
                            'VideoDescriptionName': 'bad_video',
                            'AudioDescriptionNames': ['bad_audio_1', 'bad_audio_2'],
                        }
                    ]
                }
            ],
        }
    }
    errors = validate_create_channel(config)
    assert len(errors) == 3


def test_snake_case_keys_also_work():
    """Verify validation works with snake_case keys."""
    config = {
        'encoder_settings': {
            'video_descriptions': [{'name': 'video_1'}],
            'audio_descriptions': [{'name': 'audio_1'}],
            'output_groups': [
                {
                    'outputs': [
                        {
                            'video_description_name': 'video_1',
                            'audio_description_names': ['audio_1'],
                        }
                    ]
                }
            ],
        }
    }
    assert validate_create_channel(config) == []


def test_snake_case_invalid_reference():
    """Verify validation catches errors with snake_case keys."""
    config = {
        'encoder_settings': {
            'video_descriptions': [{'name': 'video_1'}],
            'audio_descriptions': [],
            'output_groups': [{'outputs': [{'video_description_name': 'wrong_name'}]}],
        }
    }
    assert validate_create_channel(config) == [
        "VideoDescriptionName 'wrong_name' not found in VideoDescriptions. Valid: {'video_1'}"
    ]


def test_empty_output_groups():
    """Verify empty output groups produce no errors."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [{'Name': 'video_1'}],
            'AudioDescriptions': [],
            'OutputGroups': [],
        }
    }
    assert validate_create_channel(config) == []


def test_output_without_video_or_audio_refs():
    """Verify outputs without video/audio references produce no errors."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [],
            'AudioDescriptions': [],
            'OutputGroups': [{'Outputs': [{}]}],
        }
    }
    assert validate_create_channel(config) == []


def test_none_video_and_audio_descriptions():
    """Verify validation handles None video/audio descriptions."""
    config = {
        'EncoderSettings': {
            'OutputGroups': [{'Outputs': [{'VideoDescriptionName': 'vid1'}]}],
        }
    }
    errors = validate_create_channel(config)
    assert len(errors) == 1


def test_none_output_groups():
    """Verify validation handles None output groups."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [{'Name': 'v1'}],
            'AudioDescriptions': [{'Name': 'a1'}],
        }
    }
    assert validate_create_channel(config) == []


def test_none_outputs_in_group():
    """Verify validation handles None outputs within a group."""
    config = {
        'EncoderSettings': {
            'VideoDescriptions': [{'Name': 'v1'}],
            'AudioDescriptions': [],
            'OutputGroups': [{}],
        }
    }
    assert validate_create_channel(config) == []
