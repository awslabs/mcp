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

import boto3
import logging
import os
from .boto3_docstrings import boto3_docstrings
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Map our service names to boto3 service names
SERVICE_NAME_MAP = {
    'cost_optimization_hub': 'cost-optimization-hub',
    'compute_optimizer': 'compute-optimizer',
    'cost_explorer': 'ce',  # Cost Explorer's actual service name in boto3 is "ce"
}

# Default region to use if no region is found
DEFAULT_REGION = 'us-east-1'


class Boto3ToolRegistry:
    """Registry for boto3 tools that can be exposed through the MCP server."""

    def __init__(self):
        """Initialize the registry with an empty tools dictionary."""
        self.tools = {}

    def register_all_tools(self):
        """Register all tools from boto3_docstrings."""
        for service_name, methods in boto3_docstrings.items():
            for method_name, docstring in methods.items():
                # Clean up the docstring by removing extra whitespace
                clean_docstring = '\n'.join(line.strip() for line in docstring.strip().split('\n'))
                self.register_tool(service_name, method_name, clean_docstring)

    def register_tool(self, service_name: str, method_name: str, docstring: str):
        """Register a new tool in the registry."""
        tool_name = f'{service_name}_{method_name}'
        self.tools[tool_name] = {
            'service': service_name,
            'method': method_name,
            'docstring': docstring,
        }

    async def generic_handler(self, tool_name: str, **kwargs):
        """Generic handler for all boto3 tools."""
        if tool_name not in self.tools:
            logger.error(f'Tool {tool_name} not found in registry')
            return {'error': f'Tool {tool_name} not found in registry'}

        tool_info = self.tools[tool_name]
        service_name = tool_info['service']
        method_name = tool_info['method']

        # Map our service name to boto3 service name
        boto3_service_name = SERVICE_NAME_MAP.get(service_name, service_name)

        # Get region from environment variables or use default
        region = (
            os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION') or DEFAULT_REGION
        )
        logger.info(f'Using region: {region}')

        logger.info(f'Creating boto3 client for service: {boto3_service_name}')
        # Create boto3 client with region
        client = boto3.client(boto3_service_name, region_name=region)

        # Transform parameters if needed (camelCase to PascalCase for some services)
        boto3_params = {}
        for param_name, param_value in kwargs.items():
            # For cost_explorer (ce), convert to PascalCase
            if service_name == 'cost_explorer':
                boto3_param_name = param_name[0].upper() + param_name[1:]
            else:
                boto3_param_name = param_name
            boto3_params[boto3_param_name] = param_value

        logger.info(f'Calling boto3 method: {method_name} with params: {boto3_params}')
        # Call the boto3 method
        method = getattr(client, method_name)
        try:
            response = method(**boto3_params)
            return response
        except Exception as e:
            # Handle and log the error
            logger.error(f'Error calling boto3 method: {e}')
            return {'error': str(e)}
