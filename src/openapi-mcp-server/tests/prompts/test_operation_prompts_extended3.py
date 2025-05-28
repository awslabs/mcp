"""Extended tests for the operation_prompts module - Part 3."""

from awslabs.openapi_mcp_server.prompts.operation_prompts import (
    _is_complex_schema,
)


def test_is_complex_schema_simple_object():
    """Test identifying a simple object schema."""
    # Setup test data
    schema = {
        'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'name': {'type': 'string'},
            'active': {'type': 'boolean'},
        },
    }

    # Call the function
    result = _is_complex_schema(schema)

    # Verify the result
    assert result is False


def test_is_complex_schema_complex_object():
    """Test identifying a complex object schema."""
    # Setup test data
    schema = {
        'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'name': {'type': 'string'},
            'description': {'type': 'string'},
            'created_at': {'type': 'string'},
            'updated_at': {'type': 'string'},
        },
    }

    # Call the function
    result = _is_complex_schema(schema)

    # Verify the result
    assert result is True
