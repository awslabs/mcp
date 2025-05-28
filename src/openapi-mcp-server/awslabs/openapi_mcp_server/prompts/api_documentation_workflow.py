"""Workflow prompt generation for OpenAPI specifications."""

from awslabs.openapi_mcp_server import logger


def _generate_list_get_update_workflow(resource_type, list_op, get_op, update_op):
    """Generate a workflow for list → get → update pattern.

    Args:
        resource_type: The resource type
        list_op: The list operation
        get_op: The get operation
        update_op: The update operation

    Returns:
        str: The generated workflow

    """
    list_op_id = list_op.get('operationId', 'list')
    get_op_id = get_op.get('operationId', 'get')
    update_op_id = update_op.get('operationId', 'update')

    return f"""### List, Get, Update {resource_type}s

```python
# List all {resource_type}s
{resource_type.lower()}_list = await {list_op_id}()

# Get details for a specific {resource_type}
{resource_type.lower()}_id = {resource_type.lower()}_list[0]['id']
{resource_type.lower()}_details = await {get_op_id}({resource_type.lower()}_id)

# Update the {resource_type}
update_data = {{"name": "Updated Name", "description": "Updated via API"}}
updated = await {update_op_id}({resource_type.lower()}_id, update_data)
```

**Pattern**: List → Select → Get details → Update"""


def _generate_search_create_workflow(search_op, create_op):
    """Generate a workflow for search → create pattern.

    Args:
        search_op: The search operation
        create_op: The create operation

    Returns:
        str: The generated workflow

    """
    search_op_id = search_op.get('operationId', 'search')
    create_op_id = create_op.get('operationId', 'create')

    # Extract resource type from create operation ID
    resource_type = 'Resource'
    if create_op_id and create_op_id.startswith('create'):
        resource_type = create_op_id[6:]  # Remove "create" prefix

    return f"""### Search and Create {resource_type}

```python
# Search for {resource_type}s with specific criteria
search_results = await {search_op_id}(name="Example", status="active")

# Create if not found
if not search_results:
    new_data = {{
        "name": "New {resource_type}",
        "description": "Created via API",
        "status": "active"
    }}
    new_item = await {create_op_id}(new_data)
```

**Pattern**: Search → Create if not found"""


async def generate_generic_workflow_prompts(server, api_name, api_structure, components):
    """Generate generic workflow prompts based on API structure analysis.

    Args:
        server: The MCP server
        api_name: The name of the API
        api_structure: The API structure
        components: The API components

    Returns:
        str: The generated workflow section for the API overview

    """
    try:
        from fastmcp.prompts.prompt import Prompt
    except ImportError:
        logger.warning('Failed to import Prompt from fastmcp')
        return '\n## Common Workflows\n\nNo workflows available (fastmcp not found).'

    # Validate that inputs are dictionaries
    if not isinstance(api_structure, dict):
        logger.warning(
            f"API structure is not a dictionary, it's a {type(api_structure).__name__}. Cannot generate workflows."
        )
        return '\n## Common Workflows\n\nNo common workflows could be generated due to unexpected API structure format.'

    workflow_section = '\n## Common Workflows\n\n'
    workflows = []
    resource_operations = {}

    # Group operations by resource type
    try:
        for path, path_info in api_structure.items():
            # Skip if path_info is not a dictionary
            if not isinstance(path_info, dict):
                continue

            # Try to extract resource type from path
            path_parts = path.strip('/').split('/')
            resource_type = None

            # Look for resource identifier in path
            for part in path_parts:
                if part and not part.startswith('{'):
                    # Convert to singular form if plural
                    if part.endswith('s'):
                        resource_type = part[:-1].capitalize()
                    else:
                        resource_type = part.capitalize()
                    break

            # Skip if we couldn't determine a resource type
            if not resource_type:
                continue

            # Initialize resource operations if not exists
            if resource_type not in resource_operations:
                resource_operations[resource_type] = {
                    'list': None,
                    'get': None,
                    'create': None,
                    'update': None,
                    'delete': None,
                    'search': None,
                }

            # Categorize operations
            for method, operation in path_info.items():
                # Skip if operation is not a dictionary
                if not isinstance(operation, dict):
                    continue

                op_id = operation.get('operationId', f'{method}{path}')
                op_id_lower = op_id.lower()

                # Categorize based on method and operation ID
                if method == 'get':
                    if 'list' in op_id_lower or 'getall' in op_id_lower:
                        resource_operations[resource_type]['list'] = operation
                    elif 'search' in op_id_lower or 'find' in op_id_lower or 'query' in op_id_lower:
                        resource_operations[resource_type]['search'] = operation
                    else:
                        resource_operations[resource_type]['get'] = operation
                elif method == 'post':
                    if 'create' in op_id_lower or 'add' in op_id_lower:
                        resource_operations[resource_type]['create'] = operation
                    elif 'search' in op_id_lower or 'find' in op_id_lower or 'query' in op_id_lower:
                        resource_operations[resource_type]['search'] = operation
                elif method == 'put' or method == 'patch':
                    if 'update' in op_id_lower or 'modify' in op_id_lower:
                        resource_operations[resource_type]['update'] = operation
                elif method == 'delete':
                    resource_operations[resource_type]['delete'] = operation

        # Generate workflows for the overview section
        for resource_type, operations in resource_operations.items():
            try:
                # List -> Get -> Update workflow
                list_op = operations['list']
                get_op = operations['get']
                update_op = operations['update']

                if list_op and get_op and update_op:
                    workflows.append(
                        _generate_list_get_update_workflow(
                            resource_type, list_op, get_op, update_op
                        )
                    )

                # Search -> Create workflow
                search_op = operations['search']
                create_op = operations['create']

                if search_op and create_op:
                    workflows.append(_generate_search_create_workflow(search_op, create_op))

                # Create MCP-compliant workflow prompt
                if list_op and get_op and update_op:
                    # Create workflow prompt name
                    prompt_name = f'{resource_type.lower()}_workflow'

                    # Create concise description
                    prompt_description = f'Perform operations on {resource_type} resources'

                    # Define workflow arguments
                    prompt_arguments = [
                        {
                            'name': 'workflow_type',
                            'description': 'Workflow: list_get_update or search_create',
                            'required': True,
                        },
                        {
                            'name': f'{resource_type.lower()}_id',
                            'description': f'{resource_type} ID for get/update operations',
                            'required': False,
                        },
                        {
                            'name': 'filter',
                            'description': 'Filter criteria for list/search operations',
                            'required': False,
                        },
                        {
                            'name': 'data',
                            'description': f'Data for create/update {resource_type}',
                            'required': False,
                        },
                    ]

                    # Generate workflow documentation
                    workflow_doc = _generate_list_get_update_workflow(
                        resource_type, list_op, get_op, update_op
                    )

                    # Create the workflow prompt
                    # pyright: ignore[reportCallIssue]
                    workflow_prompt = Prompt(
                        name=prompt_name,
                        description=prompt_description,
                        arguments=prompt_arguments,
                        fn=lambda **kwargs: workflow_doc,
                    )

                    # Add the prompt to the server
                    server._prompt_manager.add_prompt(workflow_prompt)
                    logger.debug(f'Added workflow prompt: {prompt_name}')

            except Exception as e:
                logger.warning(f'Error generating workflows for resource type {resource_type}: {e}')
                continue

    except Exception as e:
        logger.warning(f'Error processing API structure: {e}')

    # Add workflows to the section for the overview documentation
    if workflows:
        workflow_section += '\n\n'.join(workflows)
    else:
        workflow_section += 'No common workflows identified for this API.'

    return workflow_section
