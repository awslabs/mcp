#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Standardized error handling framework for AWS Network MCP Server."""

from typing import Any, Callable, Dict, Optional, Type, Union
from functools import wraps
from dataclasses import dataclass
import logging
import traceback
from enum import Enum
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better handling."""
    VALIDATION = "validation"
    RESOURCE_NOT_FOUND = "resource_not_found"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors."""
    tool_name: str
    service: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    region: Optional[str] = None
    account_id: Optional[str] = None
    parameters: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class StandardizedError(Exception):
    """Base class for all standardized errors."""
    
    def __init__(self,
                 message: str,
                 category: ErrorCategory,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 context: Optional[ErrorContext] = None,
                 original_error: Optional[Exception] = None,
                 remediation: Optional[str] = None):
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.original_error = original_error
        self.remediation = remediation
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format error message consistently."""
        parts = [self.message]
        
        if self.context:
            if self.context.resource_type and self.context.resource_id:
                parts.append(f"Resource: {self.context.resource_type}/{self.context.resource_id}")
            if self.context.region:
                parts.append(f"Region: {self.context.region}")
        
        if self.remediation:
            parts.append(f"Suggested action: {self.remediation}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'error': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'context': self.context.to_dict() if self.context else None,
            'remediation': self.remediation
        }


class ValidationError(StandardizedError):
    """Error for invalid input parameters."""
    
    def __init__(self, parameter: str, value: Any, constraint: str, **kwargs):
        message = f"Invalid parameter '{parameter}': {constraint}"
        remediation = f"Ensure '{parameter}' meets the constraint: {constraint}"
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            remediation=remediation,
            **kwargs
        )


class ResourceNotFoundError(StandardizedError):
    """Error when AWS resource cannot be found."""
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        message = f"{resource_type} '{resource_id}' not found"
        remediation = f"Verify the {resource_type} ID exists and you have access"
        super().__init__(
            message=message,
            category=ErrorCategory.RESOURCE_NOT_FOUND,
            severity=ErrorSeverity.WARNING,
            remediation=remediation,
            **kwargs
        )


class PermissionError(StandardizedError):
    """Error for AWS permission issues."""
    
    def __init__(self, action: str, resource: str, **kwargs):
        message = f"Permission denied for action '{action}' on resource '{resource}'"
        remediation = "Check IAM policies and ensure proper permissions are granted"
        super().__init__(
            message=message,
            category=ErrorCategory.PERMISSION_DENIED,
            severity=ErrorSeverity.ERROR,
            remediation=remediation,
            **kwargs
        )


class ErrorHandler:
    """Centralized error handler with retry and fallback logic."""
    
    def __init__(self):
        self.error_stats = {}
        self.handlers = {}
    
    def register_handler(self, error_type: Type[Exception], handler: Callable):
        """Register custom error handler for specific exception types."""
        self.handlers[error_type] = handler
    
    def handle_aws_error(self, error: Exception, context: ErrorContext) -> StandardizedError:
        """Convert AWS SDK errors to standardized errors."""
        error_code = getattr(error, 'response', {}).get('Error', {}).get('Code', '')
        error_message = str(error)
        
        # Map AWS error codes to categories
        error_mapping = {
            'ResourceNotFoundException': ErrorCategory.RESOURCE_NOT_FOUND,
            'AccessDeniedException': ErrorCategory.PERMISSION_DENIED,
            'UnauthorizedException': ErrorCategory.PERMISSION_DENIED,
            'ThrottlingException': ErrorCategory.RATE_LIMIT,
            'RequestLimitExceeded': ErrorCategory.RATE_LIMIT,
            'NetworkingError': ErrorCategory.NETWORK,
            'Timeout': ErrorCategory.TIMEOUT,
            'InvalidParameterException': ErrorCategory.VALIDATION,
            'ValidationException': ErrorCategory.VALIDATION,
        }
        
        category = error_mapping.get(error_code, ErrorCategory.UNKNOWN)
        
        # Create standardized error based on category
        if category == ErrorCategory.RESOURCE_NOT_FOUND:
            return ResourceNotFoundError(
                resource_type=context.resource_type or "Resource",
                resource_id=context.resource_id or "unknown",
                context=context,
                original_error=error
            )
        elif category == ErrorCategory.PERMISSION_DENIED:
            return PermissionError(
                action=context.tool_name,
                resource=f"{context.resource_type}/{context.resource_id}" if context.resource_type else "resource",
                context=context,
                original_error=error
            )
        elif category == ErrorCategory.VALIDATION:
            return ValidationError(
                parameter="input",
                value=context.parameters,
                constraint=error_message,
                context=context,
                original_error=error
            )
        else:
            return StandardizedError(
                message=f"AWS API error: {error_message}",
                category=category,
                context=context,
                original_error=error,
                remediation="Check AWS service status and retry if transient"
            )
    
    def wrap_tool(self, tool_name: str, service: str):
        """Decorator to wrap tools with error handling."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                context = ErrorContext(
                    tool_name=tool_name,
                    service=service,
                    parameters=kwargs
                )
                
                try:
                    # Extract common parameters if present
                    context.region = kwargs.get('region')
                    context.resource_id = kwargs.get('vpc_id') or kwargs.get('tgw_id') or kwargs.get('core_network_id')
                    
                    # Execute the tool
                    return func(*args, **kwargs)
                    
                except StandardizedError:
                    # Already standardized, just re-raise
                    raise
                    
                except Exception as e:
                    # Convert to standardized error
                    standardized = self.handle_aws_error(e, context)
                    
                    # Log the error
                    logger.error(f"Error in {tool_name}: {standardized}", exc_info=True)
                    
                    # Update statistics
                    self.error_stats[tool_name] = self.error_stats.get(tool_name, 0) + 1
                    
                    raise standardized
            
            return wrapper
        return decorator


# Global error handler instance
error_handler = ErrorHandler()


@contextmanager
def error_context(tool_name: str, service: str, **kwargs):
    """Context manager for error handling."""
    context = ErrorContext(tool_name=tool_name, service=service, **kwargs)
    try:
        yield context
    except Exception as e:
        if isinstance(e, StandardizedError):
            raise
        raise error_handler.handle_aws_error(e, context)