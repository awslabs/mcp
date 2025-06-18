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

"""Tests for prompt models dict method."""

from awslabs.openapi_mcp_server.prompts.models import PromptArgument


def test_prompt_argument_dict_with_description():
    """Test PromptArgument.dict() method with description."""
    arg = PromptArgument(name='test_arg', description='Test description', required=True)

    result = arg.dict()

    expected = {'name': 'test_arg', 'description': 'Test description', 'required': True}

    assert result == expected


def test_prompt_argument_dict_without_description():
    """Test PromptArgument.dict() method without description."""
    arg = PromptArgument(name='test_arg', required=False)

    result = arg.dict()

    expected = {'name': 'test_arg', 'required': False}

    assert result == expected
    # Verify description is not included when None/empty
    assert 'description' not in result


def test_prompt_argument_dict_with_empty_description():
    """Test PromptArgument.dict() method with empty description."""
    arg = PromptArgument(name='test_arg', description='', required=True)

    result = arg.dict()

    expected = {'name': 'test_arg', 'required': True}

    assert result == expected
    # Verify empty description is not included
    assert 'description' not in result


def test_prompt_argument_dict_defaults():
    """Test PromptArgument.dict() method with default values."""
    arg = PromptArgument(name='test_arg')

    result = arg.dict()

    expected = {
        'name': 'test_arg',
        'required': False,  # Default value
    }

    assert result == expected
