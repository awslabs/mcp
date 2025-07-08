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
from awslabs.aws_finops_mcp_server.consts import (
    AWS_SERVICE_NAME_MAP,
    DEFAULT_AWS_REGION,
    ENV_AWS_DEFAULT_REGION,
    ENV_AWS_REGION,
)
from awslabs.aws_finops_mcp_server.models import (
    AWSServiceNameMap,
    Boto3ToolInfo,
)
from dotenv import load_dotenv
from typing import Any, Dict


# Load environment variables from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class Boto3ToolRegistry:
    """Registry for boto3 tools that can be exposed through the MCP server."""

    def __init__(self):
        """Initialize the registry with an empty tools dictionary."""
        self.tools: Dict[str, Boto3ToolInfo] = {}
        self.service_map = AWSServiceNameMap()

    def register_all_tools(self) -> None:
        """Register all tools from boto3_docstrings."""
        for service_name, methods in boto3_docstrings.items():
            for method_name, docstring in methods.items():
                # Clean up the docstring by removing extra whitespace
                clean_docstring = '\n'.join(line.strip() for line in docstring.strip().split('\n'))

                # Create a Boto3ToolInfo object
                tool_info = Boto3ToolInfo(
                    service=service_name,
                    method=method_name,
                    docstring=clean_docstring,
                )

                # Register the tool with the object
                self.register_tool(tool_info)

    def register_tool(self, tool_info: Boto3ToolInfo) -> None:
        """Register a new tool in the registry.

        Args:
            tool_info: Boto3ToolInfo object containing service, method, and docstring
        """
        tool_name = f'{tool_info.service}_{tool_info.method}'
        self.tools[tool_name] = tool_info

    async def generic_handler(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Generic handler for all boto3 tools.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Parameters to pass to the boto3 method

        Returns:
            Dict[str, Any]: Response from the boto3 method or error information
        """
        if tool_name not in self.tools:
            logger.error(f'Tool {tool_name} not found in registry')
            return {'error': f'Tool {tool_name} not found in registry'}

        tool_info = self.tools[tool_name]
        service_name = tool_info.service
        method_name = tool_info.method

        # Map our service name to boto3 service name
        boto3_service_name = AWS_SERVICE_NAME_MAP.get(service_name, service_name)

        # Get region from environment variables or use default
        region = (
            os.environ.get(ENV_AWS_DEFAULT_REGION)
            or os.environ.get(ENV_AWS_REGION)
            or DEFAULT_AWS_REGION
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
