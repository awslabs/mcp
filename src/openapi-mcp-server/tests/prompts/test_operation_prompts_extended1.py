"""Extended tests for the operation_prompts module - Part 1."""

from awslabs.openapi_mcp_server.prompts.operation_prompts import (
    _format_schema,
)


def test_format_schema_object():
    """Test formatting an object schema."""
    # Setup test data
    schema = {
        'type': 'object',
        'properties': {
            'id': {'type': 'string', 'description': 'The ID of the item'},
            'name': {'type': 'string', 'description': 'The name of the item'},
            'active': {'type': 'boolean', 'description': 'Whether the item is active'},
        },
        'required': ['id', 'name'],
    }

    # Call the function
    result = _format_schema(schema)

    # Verify the result
    assert '**Type**: Object' in result
    assert '**Properties**:' in result
    assert '**id** (required): string' in result
    assert 'The ID of the item' in result
    assert '**name** (required): string' in result
    assert 'The name of the item' in result
    assert '**active**: boolean' in result
    assert 'Whether the item is active' in result
