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

"""Base classes for MCP tools following AWS Labs patterns."""

from ..utils.logger import get_logger
from ..utils.response_formatter import format_error_response, format_success_response
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import boto3


class BaseMCPTool(ABC):
    """Base class for all MCP tools following AWS Labs patterns."""

    def __init__(self, name: str, description: str):
        """Initialize base MCP tool.
        
        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
        self.logger = get_logger(f"{__name__}.{name}")

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool operation.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Tool execution result
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input parameters.
        
        Args:
            input_data: Input parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic validation - subclasses can override
            return isinstance(input_data, dict)
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False

    def format_response(self, data: Any = None, error: Optional[str] = None,
                       error_code: Optional[str] = None) -> Dict[str, Any]:
        """Format tool response following AWS Labs standards.
        
        Args:
            data: Response data for success case
            error: Error message for failure case
            error_code: Error code for failure case
            
        Returns:
            Formatted response dictionary
        """
        if error:
            return format_error_response(error, error_code or "ToolError")
        else:
            return format_success_response(data)

    async def safe_execute(self, **kwargs) -> Dict[str, Any]:
        """Safely execute tool with error handling.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result with proper error handling
        """
        try:
            # Validate input
            if not self.validate_input(kwargs):
                return self.format_response(
                    error=f"Invalid input parameters for {self.name}",
                    error_code="ValidationError"
                )

            # Execute tool
            result = await self.execute(**kwargs)
            return result

        except Exception as e:
            self.logger.error(f"Tool {self.name} execution failed: {e}")
            return self.format_response(
                error=f"{self.name} execution failed: {str(e)}",
                error_code="ExecutionError"
            )


class AWSBaseTool(BaseMCPTool):
    """Base class for AWS-specific MCP tools."""

    def __init__(self, name: str, description: str, service_name: str = ""):
        """Initialize AWS-specific tool.
        
        Args:
            name: Tool name
            description: Tool description
            service_name: AWS service name (e.g., 'networkmanager')
        """
        super().__init__(name, description)
        self.service_name = service_name

    def validate_aws_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate AWS-specific input parameters.
        
        Args:
            input_data: Input parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        # AWS region validation
        region = input_data.get('region')
        if region and not isinstance(region, str):
            return False

        return super().validate_input(input_data)


class BaseTool:
    def __init__(self, client):
        # Validate client type
        if not hasattr(client, 'meta'):
            raise ValueError("Invalid AWS client instance")
        self.client = client

class NetworkConnectivityTool(BaseTool):
    def __init__(self, client):
        super().__init__(client)
        self.service_name = 'cloudwan'
        self.max_retries = getattr(client.meta.config, 'retries', {}).get('max_attempts', 3)
