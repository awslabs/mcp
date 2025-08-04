"""
MCP Protocol Error Mapping System.

This module provides comprehensive error mapping from AWS exceptions to proper MCP protocol
error types, ensuring full MCP specification compliance. Provides a fallback implementation
that doesn't require external dependencies.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class MCPErrorCode(Enum):
    """MCP Protocol Error Codes as defined in MCP-SPEC-101."""

    # Core MCP Error Types
    PARSE_ERROR = "PARSE_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"
    INVALID_PARAMS = "INVALID_PARAMS"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Resource-related Errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"

    # Permission-related Errors
    ACCESS_DENIED = "ACCESS_DENIED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # Rate Limiting and Throttling
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # Network and Service Errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"

    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SCHEMA_ERROR = "SCHEMA_ERROR"


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Additional context for error responses."""

    service: Optional[str] = None
    region: Optional[str] = None
    operation: Optional[str] = None
    resource_arn: Optional[str] = None
    resource_id: Optional[str] = None
    request_id: Optional[str] = None
    troubleshooting_tips: List[str] = None
    related_errors: List[str] = None

    def __post_init__(self):
        if self.troubleshooting_tips is None:
            self.troubleshooting_tips = []
        if self.related_errors is None:
            self.related_errors = []


class MCPError(Exception):
    """Base exception class for MCP protocol errors."""

    def __init__(
        self,
        message: str,
        code: MCPErrorCode = MCPErrorCode.INTERNAL_ERROR,
        data: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}
        self.severity = severity


class ToolError(MCPError):
    """Exception for tool-related errors."""

    def __init__(
        self,
        message: str,
        code: MCPErrorCode = MCPErrorCode.INTERNAL_ERROR,
        data: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ):
        super().__init__(message, code, data, severity)


class AWSToMCPErrorMapper:
    """Maps AWS service errors to MCP error codes."""

    # AWS Error Code to MCP Error Code mapping
    AWS_TO_MCP_MAPPING = {
        # Access and Permission Errors
        "AccessDenied": MCPErrorCode.ACCESS_DENIED,
        "UnauthorizedOperation": MCPErrorCode.ACCESS_DENIED,
        "Forbidden": MCPErrorCode.FORBIDDEN,
        "InvalidUserID.NotFound": MCPErrorCode.UNAUTHORIZED,
        "AuthFailure": MCPErrorCode.UNAUTHORIZED,
        "SignatureDoesNotMatch": MCPErrorCode.UNAUTHORIZED,
        "TokenRefreshRequired": MCPErrorCode.UNAUTHORIZED,
        "ExpiredToken": MCPErrorCode.UNAUTHORIZED,
        "InvalidAccessKeyId": MCPErrorCode.UNAUTHORIZED,
        "InvalidSecretAccessKey": MCPErrorCode.UNAUTHORIZED,
        # Resource Not Found Errors
        "ResourceNotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "NoSuchEntity": MCPErrorCode.RESOURCE_NOT_FOUND,
        "NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidVpcID.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidSubnetID.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidInstanceID.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidSecurityGroupID.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidRouteTableID.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        # Rate Limiting and Throttling
        "Throttling": MCPErrorCode.RATE_LIMITED,
        "RequestLimitExceeded": MCPErrorCode.RATE_LIMITED,
        "TooManyRequestsException": MCPErrorCode.RATE_LIMITED,
        "QuotaExceededException": MCPErrorCode.QUOTA_EXCEEDED,
        "LimitExceededException": MCPErrorCode.QUOTA_EXCEEDED,
        # Validation Errors
        "InvalidParameterValue": MCPErrorCode.VALIDATION_ERROR,
        "InvalidParameter": MCPErrorCode.VALIDATION_ERROR,
        "MalformedPolicyDocument": MCPErrorCode.VALIDATION_ERROR,
        "ValidationException": MCPErrorCode.VALIDATION_ERROR,
        # Service and Network Errors
        "ServiceUnavailable": MCPErrorCode.SERVICE_UNAVAILABLE,
        "InternalServerError": MCPErrorCode.INTERNAL_ERROR,
        "InternalError": MCPErrorCode.INTERNAL_ERROR,
        "RequestTimeout": MCPErrorCode.TIMEOUT,
        "NetworkingError": MCPErrorCode.NETWORK_ERROR,
        "ConnectionError": MCPErrorCode.NETWORK_ERROR,
    }

    def __init__(self):
        """Initialize AWS to MCP error mapper."""
        pass

    def map_aws_error_to_mcp(self, aws_error_code: str, aws_error_message: str = "") -> MCPError:
        """
        Map AWS error code to MCP error.

        Args:
            aws_error_code: AWS error code
            aws_error_message: AWS error message

        Returns:
            MCPError instance
        """
        # Get MCP error code mapping
        mcp_error_code = self.AWS_TO_MCP_MAPPING.get(aws_error_code, MCPErrorCode.INTERNAL_ERROR)

        # Determine severity based on error type
        severity = self._determine_severity(mcp_error_code)

        # Create error context
        error_data = {
            "aws_error_code": aws_error_code,
            "aws_error_message": aws_error_message,
            "mcp_error_code": mcp_error_code.value,
            "timestamp": self._get_timestamp(),
        }

        # Create message
        if aws_error_message:
            message = f"{aws_error_message} (AWS Error: {aws_error_code})"
        else:
            message = f"AWS Error: {aws_error_code}"

        return MCPError(message=message, code=mcp_error_code, data=error_data, severity=severity)

    def map_exception_to_mcp(self, exception: Exception) -> MCPError:
        """
        Map Python exception to MCP error.

        Args:
            exception: Python exception

        Returns:
            MCPError instance
        """
        exception_type = type(exception).__name__

        # Try to extract AWS error code if it's a boto3 ClientError
        aws_error_code = None
        aws_error_message = str(exception)

        # Check if this looks like a boto3 ClientError
        if hasattr(exception, "response") and isinstance(exception.response, dict):
            error_info = exception.response.get("Error", {})
            aws_error_code = error_info.get("Code")
            aws_error_message = error_info.get("Message", str(exception))

        # If we have an AWS error code, use that mapping
        if aws_error_code:
            return self.map_aws_error_to_mcp(aws_error_code, aws_error_message)

        # Otherwise, map based on exception type
        exception_mappings = {
            "ValueError": MCPErrorCode.VALIDATION_ERROR,
            "KeyError": MCPErrorCode.INVALID_PARAMS,
            "TypeError": MCPErrorCode.INVALID_PARAMS,
            "AttributeError": MCPErrorCode.INVALID_PARAMS,
            "FileNotFoundError": MCPErrorCode.RESOURCE_NOT_FOUND,
            "PermissionError": MCPErrorCode.ACCESS_DENIED,
            "TimeoutError": MCPErrorCode.TIMEOUT,
            "ConnectionError": MCPErrorCode.NETWORK_ERROR,
            "OSError": MCPErrorCode.NETWORK_ERROR,
        }

        mcp_error_code = exception_mappings.get(exception_type, MCPErrorCode.INTERNAL_ERROR)

        return MCPError(
            message=f"{exception_type}: {str(exception)}",
            code=mcp_error_code,
            data={
                "exception_type": exception_type,
                "exception_message": str(exception),
                "timestamp": self._get_timestamp(),
            },
            severity=self._determine_severity(mcp_error_code),
        )

    def _determine_severity(self, error_code: MCPErrorCode) -> ErrorSeverity:
        """Determine error severity based on error code."""
        high_severity_codes = {
            MCPErrorCode.INTERNAL_ERROR,
            MCPErrorCode.SERVICE_UNAVAILABLE,
            MCPErrorCode.NETWORK_ERROR,
        }

        medium_severity_codes = {
            MCPErrorCode.ACCESS_DENIED,
            MCPErrorCode.UNAUTHORIZED,
            MCPErrorCode.FORBIDDEN,
            MCPErrorCode.TIMEOUT,
        }

        if error_code in high_severity_codes:
            return ErrorSeverity.HIGH
        elif error_code in medium_severity_codes:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW

    def _get_timestamp(self) -> str:
        """Get current timestamp for error context."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


# Global mapper instance
_error_mapper = AWSToMCPErrorMapper()


def map_aws_error_to_mcp(exception_or_code: Union[Exception, str], message: str = "") -> MCPError:
    """
    Utility function to map AWS errors to MCP format.

    Args:
        exception_or_code: Exception instance or AWS error code string
        message: Error message (used when first arg is error code)

    Returns:
        MCPError instance
    """
    if isinstance(exception_or_code, str):
        return _error_mapper.map_aws_error_to_mcp(exception_or_code, message)
    else:
        return _error_mapper.map_exception_to_mcp(exception_or_code)
