"""Extended tests for the operation_prompts module."""

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


def test_format_schema_array():
    """Test formatting an array schema."""
    # Setup test data
    schema = {'type': 'array', 'items': {'type': 'string', 'enum': ['red', 'green', 'blue']}}

    # Call the function
    result = _format_schema(schema)

    # Verify the result
    assert '**Type**: Array' in result
    assert '**Items Type**: string' in result
    assert '**Allowed Values**:' in result
    assert '`red`' in result
    assert '`green`' in result
    assert '`blue`' in result


def test_format_schema_array_of_objects():
    """Test formatting an array of objects schema."""
    # Setup test data
    schema = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}},
        },
    }

    # Call the function
    result = _format_schema(schema)

    # Verify the result
    assert '**Type**: Array' in result
    assert '**Items Type**: object' in result
    assert '**Properties**:' in result
    assert '**id**' in result
    assert '**name**' in result


def test_format_schema_nested_objects():
    """Test formatting a schema with nested objects."""
    # Setup test data
    schema = {
        'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'address': {
                'type': 'object',
                'properties': {'street': {'type': 'string'}, 'city': {'type': 'string'}},
            },
        },
    }

    # Call the function
    result = _format_schema(schema)

    # Verify the result
    assert '**Type**: Object' in result
    assert '**Properties**:' in result
    assert '**id**' in result
    assert '**address**' in result
    assert '**street**' in result
    assert '**city**' in result
