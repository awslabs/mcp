"""
Base classes and utilities for MCP tools.

This module provides common base classes, decorators, and utilities used
across all CloudWAN MCP tools for consistent behavior and error handling.
"""

import logging
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from mcp.types import TextContent, Tool, CallToolResult, ErrorData
from mcp import McpError
from pydantic import BaseModel

from ..aws.client_manager import AWSClientManager
from ..config import CloudWANConfig
from ..models.base import BaseResponse

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ToolError(Exception):
    """Base exception for MCP tool errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ValidationError(ToolError):
    """Exception for tool input validation errors."""

    pass


class AWSOperationError(ToolError):
    """Exception for AWS operation errors."""

    pass


def handle_errors(func: Callable) -> Callable:
    """Decorator to handle sync/async errors and return MCP-compliant responses."""
    import asyncio
    import json

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> CallToolResult:
        try:
            result = await func(*args, **kwargs)
            return _format_result(result)
        except ValidationError as e:
            error_data = ErrorData(
                code=-32602,  # Invalid params
                message=f"Validation error: {e.message}",
                data={"field": e.error_code} if e.error_code else None
            )
            raise McpError(error_data)
        except AWSOperationError as e:
            error_data = ErrorData(
                code=-32603,  # Internal Error
                message=f"AWS operation failed: {e.message}",
                data={"aws_error_code": e.error_code} if e.error_code else None
            )
            raise McpError(error_data)
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            # Check if we have access to config for production flag
            try:
                show_details = True
                if hasattr(args[0], 'config'):
                    show_details = not getattr(args[0].config, 'production', False)
            except:
                show_details = True
                
            error_data = ErrorData(
                code=-32603,  # Internal Error
                message="Internal server error",
                data={"details": str(e)} if show_details else None
            )
            raise McpError(error_data)

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> CallToolResult:
        try:
            result = func(*args, **kwargs)
            return _format_result(result)
        except ValidationError as e:
            error_data = ErrorData(
                code=-32602,  # Invalid params
                message=f"Validation error: {e.message}",
                data={"field": e.error_code} if e.error_code else None
            )
            raise McpError(error_data)
        except AWSOperationError as e:
            error_data = ErrorData(
                code=-32603,  # Internal Error
                message=f"AWS operation failed: {e.message}",
                data={"aws_error_code": e.error_code} if e.error_code else None
            )
            raise McpError(error_data)
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            # Check if we have access to config for production flag
            try:
                show_details = True
                if hasattr(args[0], 'config'):
                    show_details = not getattr(args[0].config, 'production', False)
            except:
                show_details = True
                
            error_data = ErrorData(
                code=-32603,  # Internal Error
                message="Internal server error",
                data={"details": str(e)} if show_details else None
            )
            raise McpError(error_data)

    def _format_result(result):
        if isinstance(result, CallToolResult):
            return result
        
        content = []
        if isinstance(result, BaseModel):
            content.append(TextContent(type="text", text=result.model_dump_json(indent=2)))
        elif isinstance(result, (dict, list)):
            content.append(TextContent(type="text", text=json.dumps(result, indent=2)))
        else:
            content.append(TextContent(type="text", text=str(result)))
        
        return CallToolResult(content=content)

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def validate_regions(regions: Optional[List[str]], config: CloudWANConfig) -> List[str]:
    """
    Validate and normalize region list.

    Args:
        regions: Input regions list
        config: CloudWAN configuration

    Returns:
        Validated regions list

    Raises:
        ValidationError: If regions are invalid
    """
    if not regions:
        return config.aws.regions

    # Validate region format
    for region in regions:
        if not region or len(region.split("-")) < 3:
            raise ValidationError(f"Invalid region format: {region}")

    return list(set(regions))  # Remove duplicates


def validate_ip_address(ip_address: str) -> str:
    """
    Validate IP address format.

    Args:
        ip_address: IP address to validate

    Returns:
        Validated IP address

    Raises:
        ValidationError: If IP address is invalid
    """
    import ipaddress

    try:
        # This will raise ValueError for invalid IPs
        ipaddress.ip_address(ip_address)
        return ip_address
    except ValueError as e:
        raise ValidationError(f"Invalid IP address: {ip_address} - {e}")


def validate_cidr_block(cidr: str) -> str:
    """
    Validate CIDR block format.

    Args:
        cidr: CIDR block to validate

    Returns:
        Validated CIDR block

    Raises:
        ValidationError: If CIDR block is invalid
    """
    import ipaddress

    try:
        ipaddress.ip_network(cidr)
        return cidr
    except ValueError as e:
        raise ValidationError(f"Invalid CIDR block: {cidr} - {e}")


ARN_REGEX = r'^arn:aws:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:[a-zA-Z0-9-_/]+$'

def validate_arn(arn: str) -> str:
    """Security-focused ARN validation"""
    import re
    if not re.match(ARN_REGEX, arn):
        raise ValidationError("Invalid ARN format - potential injection attempt")
    return arn

class BaseMCPTool(ABC):
    """
    Abstract base class for all CloudWAN MCP tools.

    Provides common functionality and ensures consistent tool implementation
    across all tool categories.
    """

    def __init__(self, aws_manager: AWSClientManager, config: CloudWANConfig):
        """
        Initialize base tool.

        Args:
            aws_manager: AWS client manager instance
            config: CloudWAN configuration
        """
        self.aws_manager = aws_manager
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Get the tool name for MCP registration."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tool description for MCP registration."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Get the tool input schema for MCP registration."""
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> CallToolResult:
        """
        Execute the tool with given parameters.

        Args:
            arguments: Dictionary containing tool parameters

        Returns:
            CallToolResult with tool response content
        """
        pass

    def get_tool_settings(self) -> Dict[str, Any]:
        """Get tool-specific settings from configuration."""
        return self.config.get_tool_settings(self.tool_name)

    async def execute_multi_region_operation(
        self,
        service: str,
        operation: str,
        regions: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute operation across multiple regions.

        Args:
            service: AWS service name
            operation: Operation to execute
            regions: Target regions
            **kwargs: Operation parameters

        Returns:
            Results by region
        """
        target_regions = regions or self.config.aws.regions
        return await self.aws_manager.execute_multi_region(
            service, operation, target_regions, **kwargs
        )

    def create_mcp_tool(self) -> Tool:
        """
        Create MCP Tool instance for registration.

        Returns:
            MCP Tool instance
        """
        return Tool(
            name=self.tool_name,
            description=self.description,
            inputSchema=self.input_schema,
        )


def create_simple_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    handler: Callable,
    aws_manager: AWSClientManager,
    config: CloudWANConfig,
) -> Tool:
    """
    Create a simple MCP tool without class-based implementation.

    Args:
        name: Tool name
        description: Tool description
        input_schema: Input schema
        handler: Tool handler function
        aws_manager: AWS client manager
        config: Configuration

    Returns:
        MCP Tool instance
    """
    # Wrap handler with error handling
    wrapped_handler = handle_errors(handler)

    return Tool(name=name, description=description, inputSchema=input_schema)


async def paginate_aws_operation(
    client: Any,
    operation: str,
    paginator_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """
    Paginate AWS operation results.

    Args:
        client: AWS client
        operation: Operation name
        paginator_config: Paginator configuration
        **kwargs: Operation parameters

    Returns:
        All paginated results
    """
    try:
        paginator = client.get_paginator(operation)
        page_iterator = paginator.paginate(PaginationConfig=paginator_config or {}, **kwargs)

        results = []
        async for page in page_iterator:
            results.append(page)

        return results
    except Exception as e:
        logger.error(f"Pagination failed for {operation}: {e}")
        # Fallback to single operation
        method = getattr(client, operation)
        result = await method(**kwargs)
        return [result]


def format_response(data: Any, title: Optional[str] = None) -> str:
    """
    Format response data for display.

    Args:
        data: Response data
        title: Optional title

    Returns:
        Formatted response string
    """
    import json

    response_parts = []

    if title:
        response_parts.append(f"# {title}\n")

    if isinstance(data, BaseModel):
        response_parts.append(data.model_dump_json(indent=2))
    elif isinstance(data, (dict, list)):
        response_parts.append(json.dumps(data, indent=2, default=str))
    else:
        response_parts.append(str(data))

    return "\n".join(response_parts)
