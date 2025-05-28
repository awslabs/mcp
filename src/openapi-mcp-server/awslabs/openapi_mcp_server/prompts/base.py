"""Base classes and common utilities for prompt generation."""

import os
from typing import Any, Dict, List, Optional


# Configuration options
GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY = (
    os.environ.get('GENERATE_PROMPTS_FOR_COMPLEX_OPERATIONS_ONLY', 'false').lower() == 'true'
)

# Try to import Prompt from different locations
try:
    from mcp.prompts import Prompt  # type: ignore
except ImportError:
    try:
        from fastmcp.prompts.prompt import Prompt  # type: ignore
    except ImportError:
        # Define a simple Prompt class if neither is available
        class Prompt:
            """Simple Prompt class for when MCP is not available."""

            def __init__(
                self,
                name: str,
                content: str,
                description: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None,
            ):
                """Initialize a Prompt.

                Args:
                    name: The name of the prompt
                    content: The content of the prompt
                    description: Optional description of the prompt
                    metadata: Optional metadata for the prompt

                """
                self.name = name
                self.content = content
                self.description = description or ''
                self.metadata = metadata or {}
                # Add the fn field required by FastMCP
                self.fn = lambda: content


def format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format a markdown table.

    Args:
        headers: The table headers
        rows: The table rows

    Returns:
        str: The formatted markdown table

    """
    if not rows:
        return ''

    # Create header row
    table = '| ' + ' | '.join(headers) + ' |\n'
    # Create separator row
    table += '| ' + ' | '.join(['---' for _ in headers]) + ' |\n'
    # Create data rows
    for row in rows:
        table += '| ' + ' | '.join(row) + ' |\n'

    return table


def format_code_block(code: str, language: str = 'python') -> str:
    """Format a code block.

    Args:
        code: The code to format
        language: The language of the code

    Returns:
        str: The formatted code block

    """
    return f'```{language}\n{code}\n```'


def format_display_name(name: str) -> str:
    """Format a technical name into a more readable display name.

    - Converts camelCase to Title Case with spaces
    - Replaces underscores with spaces
    - Ensures proper capitalization

    Args:
        name: The technical name to format

    Returns:
        str: The formatted display name

    """
    # Step 1: Insert spaces before capital letters in camelCase
    # Using regex to find capital letters not at the beginning and insert space
    import re

    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)

    # Step 2: Replace underscores with spaces
    name = name.replace('_', ' ')

    # Step 3: Title case the result (capitalize first letter of each word)
    name = ' '.join(word.capitalize() for word in name.split())

    return name


def format_parameter_description(param: Dict[str, Any]) -> str:
    """Format a parameter description.

    Args:
        param: The parameter to format

    Returns:
        str: The formatted parameter description

    """
    name = param.get('name', '')
    description = param.get('description', '')
    required = ' (required)' if param.get('required', False) else ' (optional)'
    schema = param.get('schema', {})
    param_type = schema.get('type', 'any')

    result = f'**{name}**{required}: {param_type}'
    if description:
        result += f' - {description}'

    # Add enum values if available
    if 'enum' in schema:
        enum_values = ', '.join([f'`{v}`' for v in schema['enum']])
        result += f'\n  Allowed values: {enum_values}'

    # Add default value if available
    if 'default' in schema:
        result += f'\n  Default: `{schema["default"]}`'

    return result
