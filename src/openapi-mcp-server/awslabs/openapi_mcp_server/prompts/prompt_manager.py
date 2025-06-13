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
"""MCP prompt manager for OpenAPI specifications."""

from awslabs.openapi_mcp_server import logger
from awslabs.openapi_mcp_server.prompts.generators.operation_prompts import create_operation_prompt
from awslabs.openapi_mcp_server.prompts.generators.workflow_prompts import (
    create_workflow_prompt,
    identify_workflows,
)
from typing import Any, Dict


class MCPPromptManager:
    """Manager for MCP-compliant prompts."""

    def __init__(self):
        """Initialize the prompt manager."""
        self.prompts = []
        self.resource_handlers = {}

    async def generate_prompts(
        self, server: Any, api_name: str, openapi_spec: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Generate MCP-compliant prompts from an OpenAPI specification.

        Args:
            server: MCP server instance
            api_name: Name of the API
            openapi_spec: OpenAPI specification

        Returns:
            Status of prompt generation

        """
        logger.info(f'Generating MCP prompts for {api_name}')

        # Extract API information
        paths = openapi_spec.get('paths', {})

        # Track generation status
        status = {'operation_prompts_generated': False, 'workflow_prompts_generated': False}

        # Generate operation prompts
        operation_count = 0

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in ['get', 'post', 'put', 'patch', 'delete']:
                    continue

                operation_id = operation.get('operationId')
                if not operation_id:
                    continue

                # Create and register operation prompt
                success = create_operation_prompt(
                    server=server,
                    api_name=api_name,
                    operation_id=operation_id,
                    method=method,
                    path=path,
                    summary=operation.get('summary', ''),
                    description=operation.get('description', ''),
                    parameters=operation.get('parameters', []),
                    request_body=operation.get('requestBody'),
                    responses=operation.get('responses', {}),
                    security=operation.get('security', []),
                    paths=paths,
                )

                if success:
                    operation_count += 1

        status['operation_prompts_generated'] = operation_count > 0
        logger.info(f'Generated {operation_count} operation prompts')

        # Generate workflow prompts
        workflows = identify_workflows(paths)
        workflow_count = 0

        for workflow in workflows:
            # Create and register workflow prompt
            success = create_workflow_prompt(server, workflow)
            if success:
                workflow_count += 1

        status['workflow_prompts_generated'] = workflow_count > 0
        logger.info(f'Generated {workflow_count} workflow prompts')

        return status

    def register_api_resource_handler(self, server: Any, api_name: str, client: Any) -> None:
        """Register a handler for API resources.

        Args:
            server: MCP server instance
            api_name: Name of the API
            client: HTTP client for making API requests

        """

        async def api_resource_handler(uri: str, params: Dict[str, Any]) -> Dict[str, Any]:
            """Handle API resource requests."""
            # Extract path from URI
            # Format: api://api_name/path/to/resource
            path = uri.split(f'api://{api_name}')[1]

            # Substitute path parameters
            for param_name, param_value in params.items():
                path = path.replace(f'{{{param_name}}}', str(param_value))

            try:
                # Make the API request using the authenticated client
                response = await client.get(path)
                response.raise_for_status()

                # Return the response
                return {
                    'text': response.text,
                    'mimeType': response.headers.get('Content-Type', 'application/json'),
                }
            except Exception as e:
                logger.error(f'Error accessing API resource {uri}: {e}')
                return {'text': f'Error: {str(e)}', 'mimeType': 'text/plain'}

        # Store the resource handler for later use
        resource_uri = f'api://{api_name}/'
        self.resource_handlers[resource_uri] = api_resource_handler

        # Try to register the resource handler if the server supports it
        try:
            if hasattr(server, 'register_resource_handler'):
                server.register_resource_handler(resource_uri, api_resource_handler)
                logger.debug(f'Registered resource handler for {resource_uri}')
            else:
                logger.debug(f'Stored resource handler locally for {resource_uri}')
        except Exception as e:
            logger.warning(f'Failed to register resource handler: {e}')
