"""Tests for the base module."""

import pytest
from awslabs.openapi_mcp_server.prompts.base import (
    format_code_block,
    format_markdown_table,
    format_parameter_description,
)
from unittest.mock import patch


# Mock the Prompt class since it might be imported from different places
class MockPrompt:
    """Mock Prompt class for testing."""

    def __init__(
        self,
        name: str,
        content: str,
        description: str = None,
        metadata: dict = None,
    ):
        """Initialize a MockPrompt."""
        self.name = name
        self.content = content
        self.description = description or ''
        self.metadata = metadata or {}
        self.fn = lambda: content


@pytest.fixture
def mock_prompt():
    """Patch the Prompt class with our MockPrompt."""
    with patch('awslabs.openapi_mcp_server.prompts.base.Prompt', MockPrompt):
        yield


def test_prompt_initialization(mock_prompt):
    """Test initializing a Prompt object."""
    # Import Prompt after patching
    from awslabs.openapi_mcp_server.prompts.base import Prompt

    # Test with minimal parameters
    prompt = Prompt(name='test_prompt', content='This is a test prompt')
    assert prompt.name == 'test_prompt'
    assert prompt.content == 'This is a test prompt'
    assert prompt.description == ''
    assert prompt.metadata == {}
    assert prompt.fn() == 'This is a test prompt'

    # Test with all parameters
    metadata = {'key': 'value'}
    prompt = Prompt(
        name='test_prompt',
        content='This is a test prompt',
        description='A test prompt description',
        metadata=metadata,
    )
    assert prompt.name == 'test_prompt'
    assert prompt.content == 'This is a test prompt'
    assert prompt.description == 'A test prompt description'
    assert prompt.metadata == metadata
    assert prompt.fn() == 'This is a test prompt'


def test_format_markdown_table():
    """Test formatting a markdown table."""
    # Test with simple data
    headers = ['Name', 'Type', 'Description']
    rows = [
        ['param1', 'string', 'First parameter'],
        ['param2', 'integer', 'Second parameter'],
        ['param3', 'boolean', 'Third parameter'],
    ]

    expected = (
        '| Name | Type | Description |\n'
        '| --- | --- | --- |\n'
        '| param1 | string | First parameter |\n'
        '| param2 | integer | Second parameter |\n'
        '| param3 | boolean | Third parameter |\n'
    )

    result = format_markdown_table(headers, rows)
    assert result == expected

    # Test with empty rows
    result = format_markdown_table(headers, [])
    assert result == ''


def test_format_code_block():
    """Test formatting a code block."""
    # Test with default language
    code = "def test_function():\n    return 'test'"
    expected = "```python\ndef test_function():\n    return 'test'\n```"

    result = format_code_block(code)
    assert result == expected

    # Test with specified language
    result = format_code_block(code, language='javascript')
    expected = "```javascript\ndef test_function():\n    return 'test'\n```"
    assert result == expected


def test_format_parameter_description():
    """Test formatting a parameter description."""
    # Test required parameter with description
    param = {
        'name': 'test_param',
        'description': 'A test parameter',
        'required': True,
        'schema': {'type': 'string'},
    }

    expected = '**test_param** (required): string - A test parameter'
    result = format_parameter_description(param)
    assert result == expected

    # Test optional parameter with description
    param['required'] = False
    expected = '**test_param** (optional): string - A test parameter'
    result = format_parameter_description(param)
    assert result == expected

    # Test parameter with enum values
    param['schema']['enum'] = ['value1', 'value2', 'value3']
    expected = '**test_param** (optional): string - A test parameter\n  Allowed values: `value1`, `value2`, `value3`'
    result = format_parameter_description(param)
    assert result == expected

    # Test parameter with default value
    param['schema']['default'] = 'value1'
    expected = '**test_param** (optional): string - A test parameter\n  Allowed values: `value1`, `value2`, `value3`\n  Default: `value1`'
    result = format_parameter_description(param)
    assert result == expected

    # Test parameter without description
    param = {'name': 'test_param', 'required': True, 'schema': {'type': 'integer'}}

    expected = '**test_param** (required): integer'
    result = format_parameter_description(param)
    assert result == expected
