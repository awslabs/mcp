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

"""Unit tests for prompts module.

These tests verify the functionality of the prompt system, including:
- Decorator functionality and metadata handling
- Prompt registration and discovery
- Content generation with parameters
- Message format and structure
"""

from awslabs.billing_cost_management_mcp_server.prompts.decorator import finops_prompt
from awslabs.billing_cost_management_mcp_server.prompts.types import as_prompt_function
from unittest.mock import MagicMock


def test_decorator_basic():
    """Test that the decorator correctly sets metadata."""

    @finops_prompt(name='test_prompt', description='Test description', tags={'test'})
    def test_function():
        """This is a test docstring."""
        return 'Test'

    # Cast to PromptFunction for type checking
    prompt_func = as_prompt_function(test_function)

    # Check that metadata is correctly set
    assert hasattr(prompt_func, '_finops_prompt')
    assert prompt_func._finops_prompt is True
    assert prompt_func._prompt_name == 'test_prompt'
    assert prompt_func._prompt_description == 'Test description'
    assert prompt_func._prompt_tags == {'test'}


def test_decorator_defaults():
    """Test that the decorator uses defaults correctly."""

    @finops_prompt()
    def test_function():
        """This is a test docstring."""
        return 'Test'

    # Cast to PromptFunction for type checking
    prompt_func = as_prompt_function(test_function)

    # Check that defaults are correctly used
    assert prompt_func._prompt_name == 'test_function'
    assert prompt_func._prompt_description == 'This is a test docstring.'
    assert prompt_func._prompt_tags == {'finops'}


def test_decorator_function_execution():
    """Test that the decorated function still executes correctly."""

    @finops_prompt()
    def test_function(a, b):
        """This is a test docstring."""
        return a + b

    # Check that the function still works
    assert test_function(1, 2) == 3


def test_register_all_prompts():
    """Test that register_all_prompts correctly registers prompts."""
    # Create a mock MCP server
    mock_mcp = MagicMock()
    mock_prompt = MagicMock()
    mock_mcp.prompt.return_value = mock_prompt

    # Import the register_all_prompts function
    from awslabs.billing_cost_management_mcp_server.prompts import register_all_prompts

    # Call the function with the mock MCP server
    register_all_prompts(mock_mcp)

    # Check that mcp.prompt was called at least once
    # (we have at least two prompts: graviton_migration and savings_plans)
    assert mock_mcp.prompt.call_count >= 2

    # Check that the prompt decorator was called with the correct arguments
    for call in mock_mcp.prompt.call_args_list:
        args, kwargs = call
        assert 'name' in kwargs
        assert 'description' in kwargs


def test_graviton_migration_prompt():
    """Test that the graviton migration prompt generates correct content."""
    # Import the prompt function
    from awslabs.billing_cost_management_mcp_server.prompts.graviton_migration import (
        graviton_migration_analysis,
    )

    # Call the function with test parameters
    account_ids = '123456789012'
    lookback_days = 7
    region = 'us-west-2'
    messages = graviton_migration_analysis(account_ids, lookback_days, region)

    # Check that the result is a list of messages
    assert isinstance(messages, list)
    assert len(messages) == 2

    # Get the content of the first message (user message)
    user_message = messages[0]
    content_text = ''

    # Extract the text content regardless of the message format
    if hasattr(user_message, 'content'):
        if hasattr(user_message.content, 'text'):
            # If content is a TextContent object with text attribute
            content_text = user_message.content.text  # type: ignore
        else:
            # If content is a string
            content_text = str(user_message.content)
    else:
        content_text = str(user_message)

    # Check that the content contains the expected information
    assert '123456789012' in content_text
    assert '7 days' in content_text
    assert 'us-west-2' in content_text
    assert 'compute_optimizer_get_ec2_instance_recommendations' in content_text

    # Check the assistant message
    assistant_message = messages[1]
    role = ''

    # Extract the role regardless of the message format
    if hasattr(assistant_message, 'role'):
        role = assistant_message.role
    elif isinstance(assistant_message, dict) and 'role' in assistant_message:
        role = assistant_message['role']
    else:
        # Try to find role in string representation
        message_str = str(assistant_message)
        if "role='assistant'" in message_str or 'role="assistant"' in message_str:
            role = 'assistant'

    assert 'assistant' in role.lower()


def test_savings_plans_prompt():
    """Test that the savings plans prompt generates correct content."""
    # Import the prompt function
    from awslabs.billing_cost_management_mcp_server.prompts.savings_plans import (
        savings_plans_analysis,
    )

    # Call the function with test parameters
    account_ids = '123456789012'
    lookback_days = 60
    term_in_years = 3
    messages = savings_plans_analysis(account_ids, lookback_days, term_in_years)

    # Check that the result is a list of messages
    assert isinstance(messages, list)
    assert len(messages) == 2

    # Get the content of the first message (user message)
    user_message = messages[0]
    content_text = ''

    # Extract the text content regardless of the message format
    if hasattr(user_message, 'content'):
        if hasattr(user_message.content, 'text'):
            # If content is a TextContent object with text attribute
            content_text = user_message.content.text  # type: ignore
        else:
            # If content is a string
            content_text = str(user_message.content)
    else:
        content_text = str(user_message)

    # Check that the content contains the expected information
    assert '123456789012' in content_text
    assert '60 days' in content_text
    assert '3 years' in content_text
    assert 'cost_explorer_get_savings_plans_purchase_recommendation' in content_text

    # Check the assistant message
    assistant_message = messages[1]
    role = ''

    # Extract the role regardless of the message format
    if hasattr(assistant_message, 'role'):
        role = assistant_message.role
    elif isinstance(assistant_message, dict) and 'role' in assistant_message:
        role = assistant_message['role']
    else:
        # Try to find role in string representation
        message_str = str(assistant_message)
        if "role='assistant'" in message_str or 'role="assistant"' in message_str:
            role = 'assistant'

    assert 'assistant' in role.lower()
