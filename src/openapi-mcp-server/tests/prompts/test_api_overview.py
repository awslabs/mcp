"""Tests for the api_overview module."""

from awslabs.openapi_mcp_server.prompts.api_overview import (
    create_api_overview_prompt,
    generate_api_overview,
)
from unittest.mock import MagicMock, patch


def test_generate_api_overview_basic():
    """Test generating a basic API overview."""
    # Setup test data
    api_name = 'test_api'
    api_title = 'Test API'
    api_description = 'This is a test API'
    api_version = '1.0.0'
    paths = {}
    components = {}

    # Call the function
    result = generate_api_overview(
        api_name=api_name,
        api_title=api_title,
        api_description=api_description,
        api_version=api_version,
        paths=paths,
        components=components,
    )

    # Verify the result
    assert '# Test API' in result
    assert 'This is a test API' in result
    assert 'Version: 1.0.0' in result
    assert '## Available Endpoints' in result


def test_generate_api_overview_with_servers():
    """Test generating an API overview with servers."""
    # Setup test data
    api_name = 'test_api'
    api_title = 'Test API'
    api_description = 'This is a test API'
    api_version = '1.0.0'
    paths = {}
    components = {}
    servers = [
        {'url': 'https://api.example.com/v1', 'description': 'Production server'},
        {'url': 'https://staging-api.example.com/v1', 'description': 'Staging server'},
    ]

    # Call the function
    result = generate_api_overview(
        api_name=api_name,
        api_title=api_title,
        api_description=api_description,
        api_version=api_version,
        paths=paths,
        components=components,
        servers=servers,
    )

    # Verify the result
    assert '## API Servers' in result
    assert '**https://api.example.com/v1**' in result
    assert 'Production server' in result
    assert '**https://staging-api.example.com/v1**' in result
    assert 'Staging server' in result


def test_generate_api_overview_with_security_schemes():
    """Test generating an API overview with security schemes."""
    # Setup test data
    api_name = 'test_api'
    api_title = 'Test API'
    api_description = 'This is a test API'
    api_version = '1.0.0'
    paths = {}
    components = {}
    security_schemes = {
        'api_key': {
            'type': 'apiKey',
            'name': 'X-API-Key',
            'in': 'header',
            'description': 'API key authentication',
        },
        'oauth2': {
            'type': 'oauth2',
            'flows': {
                'implicit': {
                    'authorizationUrl': 'https://example.com/oauth/authorize',
                    'scopes': {'read': 'Read access', 'write': 'Write access'},
                }
            },
            'description': 'OAuth2 authentication',
        },
        'basic_auth': {'type': 'http', 'scheme': 'basic', 'description': 'Basic authentication'},
    }

    # Call the function
    result = generate_api_overview(
        api_name=api_name,
        api_title=api_title,
        api_description=api_description,
        api_version=api_version,
        paths=paths,
        components=components,
        security_schemes=security_schemes,
    )

    # Verify the result
    assert '## Authentication' in result

    # API Key
    assert '**api_key** (apiKey)' in result
    assert '**Name**: X-API-Key' in result
    assert '**In**: header' in result

    # OAuth2
    assert '**oauth2** (oauth2)' in result
    assert '**Flows**: implicit' in result

    # Basic Auth
    assert '**basic_auth** (http)' in result
    assert '**Scheme**: basic' in result


def test_generate_api_overview_with_paths():
    """Test generating an API overview with paths."""
    # Setup test data
    api_name = 'test_api'
    api_title = 'Test API'
    api_description = 'This is a test API'
    api_version = '1.0.0'
    paths = {
        '/items': {
            'get': {'operationId': 'listItems', 'summary': 'List all items', 'tags': ['items']},
            'post': {
                'operationId': 'createItem',
                'summary': 'Create a new item',
                'tags': ['items'],
            },
        },
        '/items/{itemId}': {
            'get': {'operationId': 'getItem', 'summary': 'Get an item by ID', 'tags': ['items']},
            'put': {'operationId': 'updateItem', 'summary': 'Update an item', 'tags': ['items']},
            'delete': {
                'operationId': 'deleteItem',
                'summary': 'Delete an item',
                'tags': ['items'],
            },
        },
    }
    components = {}

    # Call the function
    result = generate_api_overview(
        api_name=api_name,
        api_title=api_title,
        api_description=api_description,
        api_version=api_version,
        paths=paths,
        components=components,
    )

    # Verify the result
    assert '## Available Endpoints' in result
    assert '### items' in result

    # Check that the table contains the expected operations
    assert 'GET' in result
    assert 'POST' in result
    assert 'PUT' in result
    assert 'DELETE' in result
    assert '`/items`' in result
    assert '`/items/{itemId}`' in result
    assert 'listItems' in result
    assert 'createItem' in result
    assert 'getItem' in result
    assert 'updateItem' in result
    assert 'deleteItem' in result
    assert 'List all items' in result
    assert 'Create a new item' in result
    assert 'Get an item by ID' in result
    assert 'Update an item' in result
    assert 'Delete an item' in result


def test_generate_api_overview_with_schemas():
    """Test generating an API overview with schemas."""
    # Setup test data
    api_name = 'test_api'
    api_title = 'Test API'
    api_description = 'This is a test API'
    api_version = '1.0.0'
    paths = {}
    components = {
        'schemas': {
            'Item': {
                'type': 'object',
                'description': 'An item in the system',
                'properties': {
                    'id': {'type': 'string', 'description': 'The item ID'},
                    'name': {'type': 'string', 'description': 'The item name'},
                    'price': {'type': 'number', 'description': 'The item price'},
                },
                'required': ['id', 'name'],
            },
            'Error': {
                'type': 'object',
                'description': 'Error response',
                'properties': {
                    'code': {'type': 'integer', 'description': 'Error code'},
                    'message': {'type': 'string', 'description': 'Error message'},
                },
            },
        }
    }

    # Call the function
    result = generate_api_overview(
        api_name=api_name,
        api_title=api_title,
        api_description=api_description,
        api_version=api_version,
        paths=paths,
        components=components,
    )

    # Verify the result
    assert '## Available Schemas' in result

    # Check Item schema
    assert '### Item' in result
    assert 'An item in the system' in result
    assert '**Type**: object' in result
    assert '**Properties**:' in result

    # Check that the table contains the expected properties
    assert 'id' in result
    assert 'string' in result
    assert 'Yes' in result  # Required
    assert 'The item ID' in result

    assert 'name' in result
    assert 'The item name' in result

    assert 'price' in result
    assert 'number' in result
    assert 'No' in result  # Not required
    assert 'The item price' in result

    # Check Error schema
    assert '### Error' in result
    assert 'Error response' in result
    assert 'code' in result
    assert 'integer' in result
    assert 'message' in result


def test_generate_api_overview_with_workflow_section():
    """Test generating an API overview with a workflow section."""
    # Setup test data
    api_name = 'test_api'
    api_title = 'Test API'
    api_description = 'This is a test API'
    api_version = '1.0.0'
    paths = {}
    components = {}
    workflow_section = """## Common Workflows

### List, Get, and Update Items

This workflow demonstrates how to list items, get details for a specific item, and update it.

```python
# Step 1: List all items
item_list = await listItems()
print(f"Found {len(item_list)} items")

# Step 2: Get details for a specific item
if item_list:
    item_id = item_list[0]['id']
    item_details = await getItem(item_id)
    print(f"Details for item {item_id}:")
    print(item_details)

    # Step 3: Update the item
    updated_item = await updateItem(item_id, {"name": "Updated Name"})
    print("Updated item:")
    print(updated_item)
```
"""

    # Call the function
    result = generate_api_overview(
        api_name=api_name,
        api_title=api_title,
        api_description=api_description,
        api_version=api_version,
        paths=paths,
        components=components,
        workflow_section=workflow_section,
    )

    # Verify the result
    assert '## Common Workflows' in result
    assert '### List, Get, and Update Items' in result
    assert 'This workflow demonstrates how to list items' in result
    assert '```python' in result
    assert '# Step 1: List all items' in result
    assert 'item_list = await listItems()' in result
    assert '# Step 2: Get details for a specific item' in result
    assert '# Step 3: Update the item' in result
    assert '```' in result


def test_create_api_overview_prompt():
    """Test creating an API overview prompt."""
    # Setup test data
    server = MagicMock()
    server._prompt_manager = MagicMock()

    api_name = 'test_api'
    api_title = 'Test API'
    api_description = 'This is a test API'
    api_version = '1.0.0'
    paths = {}
    components = {}

    # Mock the generate_api_overview function
    with patch(
        'awslabs.openapi_mcp_server.prompts.api_overview.generate_api_overview',
        return_value='mocked_api_overview',
    ):
        with patch('fastmcp.prompts.prompt.Prompt') as mock_prompt:
            mock_prompt.from_function = MagicMock()

            # Call the function
            create_api_overview_prompt(
                server=server,
                api_name=api_name,
                api_title=api_title,
                api_description=api_description,
                api_version=api_version,
                paths=paths,
                components=components,
            )

            # Verify the result
            mock_prompt.from_function.assert_called_once()
            server._prompt_manager.add_prompt.assert_called_once()
