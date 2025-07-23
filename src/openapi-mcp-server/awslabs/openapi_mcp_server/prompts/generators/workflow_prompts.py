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
"""Workflow prompt generation for OpenAPI specifications."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.prompts.models import PromptArgument
from fastmcp.prompts.prompt import Prompt
from typing import Any, Dict, List


def identify_workflows(paths: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify common workflows from API paths."""
    workflows = []

    # Group operations by resource type
    resource_operations = {}

    for path, path_item in paths.items():
        # Extract resource type from path
        path_parts = path.strip('/').split('/')
        resource_type = None

        # Look for resource identifier in path
        for part in path_parts:
            if part and not part.startswith('{'):
                resource_type = part
                break

        if not resource_type:
            continue

        # Initialize resource operations
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
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue

            op_id = operation.get('operationId', '')
            op_id_lower = op_id.lower()

            # Categorize based on method and operation ID
            if method == 'get':
                if 'list' in op_id_lower or 'getall' in op_id_lower:
                    resource_operations[resource_type]['list'] = operation
                elif 'search' in op_id_lower or 'find' in op_id_lower:
                    resource_operations[resource_type]['search'] = operation
                else:
                    resource_operations[resource_type]['get'] = operation
            elif method == 'post':
                if 'create' in op_id_lower or 'add' in op_id_lower:
                    resource_operations[resource_type]['create'] = operation
            elif method in ['put', 'patch']:
                resource_operations[resource_type]['update'] = operation
            elif method == 'delete':
                resource_operations[resource_type]['delete'] = operation

    # Identify List-Get-Update workflow
    for resource_type, operations in resource_operations.items():
        if operations['list'] and operations['get'] and operations['update']:
            workflows.append(
                {
                    'name': f'{resource_type}_list_get_update',
                    'type': 'list_get_update',
                    'resource_type': resource_type,
                    'operations': {
                        'list': operations['list'],
                        'get': operations['get'],
                        'update': operations['update'],
                    },
                }
            )

        # Identify Search-Create workflow
        if operations['search'] and operations['create']:
            workflows.append(
                {
                    'name': f'{resource_type}_search_create',
                    'type': 'search_create',
                    'resource_type': resource_type,
                    'operations': {'search': operations['search'], 'create': operations['create']},
                }
            )

    return workflows


def generate_workflow_documentation(workflow: Dict[str, Any]) -> str:
    """Generate documentation for a workflow."""
    workflow_type = workflow['type']
    resource_type = workflow['resource_type']
    operations = workflow['operations']

    doc_lines = []

    # Add title (concise)
    doc_lines.append(
        f'# {resource_type.capitalize()} {workflow_type.replace("_", " ").title()} Workflow'
    )

    # Add workflow steps
    doc_lines.append('\n## Steps')

    if workflow_type == 'list_get_update':
        list_op_id = operations['list'].get('operationId', 'list')
        get_op_id = operations['get'].get('operationId', 'get')
        update_op_id = operations['update'].get('operationId', 'update')

        doc_lines.append(f'\n1. List {resource_type}s using `{list_op_id}`')
        doc_lines.append(f'2. Get a specific {resource_type} using `{get_op_id}`')
        doc_lines.append(f'3. Update the {resource_type} using `{update_op_id}`')

        # Add code example
        doc_lines.append('\n## Example Code')
        doc_lines.append('```python')
        doc_lines.append(f'# List all {resource_type}s')
        doc_lines.append(f'{resource_type}_list = await {list_op_id}()')
        doc_lines.append(f'\n# Get a specific {resource_type}')
        doc_lines.append(
            f"{resource_type}_id = {resource_type}_list[0]['id']  # Example: use first item"
        )
        doc_lines.append(f'{resource_type}_details = await {get_op_id}({resource_type}_id)')
        doc_lines.append(f'\n# Update the {resource_type}')
        doc_lines.append('update_data = {')
        doc_lines.append('    # Include required fields here')
        doc_lines.append('}')
        doc_lines.append(f'updated = await {update_op_id}({resource_type}_id, update_data)')
        doc_lines.append('```')

    elif workflow_type == 'search_create':
        search_op_id = operations['search'].get('operationId', 'search')
        create_op_id = operations['create'].get('operationId', 'create')

        doc_lines.append(f'\n1. Search for {resource_type}s using `{search_op_id}`')
        doc_lines.append(f'2. If not found, create a new {resource_type} using `{create_op_id}`')

        # Add code example
        doc_lines.append('\n## Example Code')
        doc_lines.append('```python')
        doc_lines.append(f'# Search for {resource_type}s')
        doc_lines.append('search_criteria = {')
        doc_lines.append('    # Include search parameters here')
        doc_lines.append('}')
        doc_lines.append(f'search_results = await {search_op_id}(**search_criteria)')
        doc_lines.append('\n# Create if not found')
        doc_lines.append('if not search_results:')
        doc_lines.append('    create_data = {')
        doc_lines.append('        # Include required fields here')
        doc_lines.append('    }')
        doc_lines.append(f'    new_{resource_type} = await {create_op_id}(create_data)')
        doc_lines.append('```')

    return '\n'.join(doc_lines)


def create_workflow_prompt(server: Any, workflow: Dict[str, Any]) -> bool:
    """Create and register a workflow prompt with the server.

    Args:
        server: MCP server instance
        workflow: Workflow definition

    Returns:
        bool: True if prompt was registered successfully, False otherwise

    """
    try:
        workflow_type = workflow['type']
        resource_type = workflow['resource_type']

        # Generate documentation
        documentation = generate_workflow_documentation(workflow)

        # Get operations from workflow
        operations = workflow['operations']

        # Extract arguments from workflow operations
        workflow_args = []

        # Add resource type as an argument
        workflow_args.append(
            PromptArgument(
                name='resource_type',
                description=f'The type of resource ({resource_type})',
                required=False,
            )
        )

        # Add operation-specific arguments
        for op_type, operation in operations.items():
            if operation and 'parameters' in operation:
                for param in operation.get('parameters', []):
                    if param.get('required', False):
                        param_name = param.get('name', '')
                        param_desc = param.get('description', f'Parameter for {op_type} operation')

                        # Check if this parameter is already added
                        if not any(arg.name == param_name for arg in workflow_args):
                            workflow_args.append(
                                PromptArgument(
                                    name=param_name,
                                    description=param_desc,
                                    required=False,  # Optional in workflow context
                                )
                            )

        # Create a function that returns messages for this workflow
        def workflow_fn() -> List[Dict[str, Any]]:
            # Create messages
            messages = [{'role': 'user', 'content': {'type': 'text', 'text': documentation}}]

            return messages

        # Register the function as a prompt
        if hasattr(server, '_prompt_manager'):
            # Create tags based on workflow metadata
            tags = {resource_type, workflow_type}

            # Create a prompt from the function
            prompt = Prompt.from_function(
                fn=workflow_fn,
                name=workflow['name'],
                description=f'Execute a {workflow_type} workflow for {resource_type}',
                tags=tags,
            )

            # Add the prompt to the server
            server._prompt_manager.add_prompt(prompt)
            logger.debug(f'Added workflow prompt: {workflow["name"]}')
            return True
        else:
            logger.warning('Server does not have _prompt_manager')
            return False

    except Exception as e:
        logger.warning(f'Failed to create workflow prompt: {e}')
        return False
