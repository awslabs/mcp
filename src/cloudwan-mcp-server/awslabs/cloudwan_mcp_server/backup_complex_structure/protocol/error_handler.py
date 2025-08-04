"""
MCP Protocol Error Handling and Mapping System.

This module provides comprehensive error mapping from AWS ClientError exceptions
to proper MCP protocol error types, ensuring full MCP specification compliance.
"""

import logging
import os
import re
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError
from mcp import McpError
from mcp.types import ErrorData

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


class AWSErrorMapping:
    """Maps AWS error codes to MCP error codes with context."""

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
        "InvalidTransitGatewayID.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidNetworkInterfaceID.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidLoadBalancerName.NotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        # Parameter and Validation Errors
        "InvalidParameterException": MCPErrorCode.INVALID_PARAMS,
        "InvalidParameter": MCPErrorCode.INVALID_PARAMS,
        "InvalidParameterValue": MCPErrorCode.INVALID_PARAMS,
        "InvalidParameterCombination": MCPErrorCode.INVALID_PARAMS,
        "MissingParameter": MCPErrorCode.INVALID_PARAMS,
        "ValidationException": MCPErrorCode.VALIDATION_ERROR,
        "InvalidInput": MCPErrorCode.VALIDATION_ERROR,
        "MalformedPolicyDocument": MCPErrorCode.SCHEMA_ERROR,
        "InvalidPolicyDocument": MCPErrorCode.SCHEMA_ERROR,
        # Rate Limiting and Throttling
        "Throttling": MCPErrorCode.RATE_LIMITED,
        "ThrottlingException": MCPErrorCode.RATE_LIMITED,
        "RequestLimitExceeded": MCPErrorCode.RATE_LIMITED,
        "TooManyRequestsException": MCPErrorCode.RATE_LIMITED,
        "LimitExceeded": MCPErrorCode.QUOTA_EXCEEDED,
        "ServiceLimitExceeded": MCPErrorCode.QUOTA_EXCEEDED,
        "QuotaExceeded": MCPErrorCode.QUOTA_EXCEEDED,
        # Service and Network Errors
        "ServiceUnavailable": MCPErrorCode.SERVICE_UNAVAILABLE,
        "InternalError": MCPErrorCode.INTERNAL_ERROR,
        "InternalServerError": MCPErrorCode.INTERNAL_ERROR,
        "InternalFailure": MCPErrorCode.INTERNAL_ERROR,
        "RequestTimeout": MCPErrorCode.TIMEOUT,
        "NetworkTimeout": MCPErrorCode.TIMEOUT,
        "EndpointConnectionError": MCPErrorCode.NETWORK_ERROR,
        "ConnectionError": MCPErrorCode.NETWORK_ERROR,
        "DNSError": MCPErrorCode.NETWORK_ERROR,
        # CloudWAN Specific Errors
        "CoreNetworkNotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "GlobalNetworkNotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "AttachmentNotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "PolicyVersionNotFound": MCPErrorCode.RESOURCE_NOT_FOUND,
        "InvalidCoreNetworkState": MCPErrorCode.RESOURCE_UNAVAILABLE,
        "InvalidAttachmentState": MCPErrorCode.RESOURCE_UNAVAILABLE,
        # NetworkManager Specific Errors
        "ResourceInUse": MCPErrorCode.RESOURCE_UNAVAILABLE,
        "ConflictException": MCPErrorCode.RESOURCE_UNAVAILABLE,
        "DependencyViolation": MCPErrorCode.RESOURCE_UNAVAILABLE,
        "InvalidState": MCPErrorCode.RESOURCE_UNAVAILABLE,
    }

    @classmethod
    def get_mcp_error_code(cls, aws_error_code: str) -> MCPErrorCode:
        """Get MCP error code for AWS error code."""
        return cls.AWS_TO_MCP_MAPPING.get(aws_error_code, MCPErrorCode.INTERNAL_ERROR)

    @classmethod
    def get_troubleshooting_tips(cls, aws_error_code: str, service: str = None) -> List[str]:
        """Get troubleshooting tips for specific AWS error codes."""
        tips = []

        # Access-related troubleshooting
        if aws_error_code in ["AccessDenied", "UnauthorizedOperation"]:
            tips.extend(
                [
                    "Check IAM policies for required permissions",
                    "Verify the role has permissions for the specific AWS service",
                    (
                        f"Ensure permissions for {service} service are granted"
                        if service
                        else "Check service-specific permissions"
                    ),
                    "Review resource-based policies if applicable",
                    "Check if MFA is required for this operation",
                ]
            )

        # Resource not found troubleshooting
        elif aws_error_code.endswith(".NotFound") or aws_error_code in [
            "ResourceNotFound",
            "NoSuchEntity",
        ]:
            tips.extend(
                [
                    "Verify the resource ID/ARN is correct",
                    "Check if the resource exists in the specified region",
                    "Ensure the resource hasn't been deleted recently",
                    "Check if you have list/describe permissions to see the resource",
                ]
            )

        # Rate limiting troubleshooting
        elif aws_error_code in [
            "Throttling",
            "ThrottlingException",
            "RequestLimitExceeded",
        ]:
            tips.extend(
                [
                    "Implement exponential backoff retry logic",
                    "Reduce request frequency",
                    "Consider using AWS SDK built-in retry mechanisms",
                    "Check if you're hitting API rate limits",
                    "Consider requesting service limit increases if needed",
                ]
            )

        # CloudWAN specific troubleshooting
        elif service == "networkmanager":
            if aws_error_code == "CoreNetworkNotFound":
                tips.extend(
                    [
                        "Verify the Core Network ID is correct",
                        "Check if the Core Network exists in the Global Network",
                        "Ensure you have NetworkManager permissions",
                    ]
                )
            elif aws_error_code == "InvalidCoreNetworkState":
                tips.extend(
                    [
                        "Check the Core Network state - it may be updating",
                        "Wait for the Core Network to reach AVAILABLE state",
                        "Review recent policy changes that might affect state",
                    ]
                )

        # Service-specific troubleshooting
        elif service == "ec2":
            tips.extend(
                [
                    "Verify the region is correct for the resource",
                    "Check VPC and subnet configurations",
                    "Ensure security groups allow required access",
                ]
            )

        # Default troubleshooting
        if not tips:
            tips.extend(
                [
                    "Check AWS service status page for known issues",
                    "Verify your AWS credentials are valid",
                    "Ensure the AWS region is accessible",
                    "Review CloudTrail logs for detailed error information",
                ]
            )

        return tips


class ProductionErrorSanitizer:
    """
    OWASP ASVS 5.4.3 compliant error sanitization for production environments.

    Removes sensitive information from stack traces and error messages
    to prevent information disclosure vulnerabilities.
    """

    # Patterns that indicate sensitive information
    SENSITIVE_PATTERNS = [
        # AWS credentials and secrets
        r"AKIA[0-9A-Z]{16}",  # AWS Access Key ID
        r"[A-Za-z0-9/+=]{40}",  # AWS Secret Access Key pattern
        r"aws[_-]?secret[_-]?access[_-]?key",
        r"aws[_-]?access[_-]?key[_-]?id",
        r"aws[_-]?session[_-]?token",
        # Database connections and passwords
        r'password\s*=\s*["\'][^"\']*["\']',
        r'passwd\s*=\s*["\'][^"\']*["\']',
        r'pwd\s*=\s*["\'][^"\']*["\']',
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[^@]+@",  # DB connection strings
        # File paths that may contain sensitive info
        r"/home/[^/\s]+/\.aws/",
        r"/Users/[^/\s]+/\.aws/",
        r"C:\\Users\\[^\\]+\\\.aws\\",
        # Network information
        r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",  # IP addresses (internal networks)
        r"\b[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}:[0-9a-fA-F:]*\b",  # IPv6
        # API keys and tokens
        r'["\']?[a-zA-Z0-9_-]*(?:key|token|secret|password)["\']?\s*[:=]\s*["\'][^"\']*["\']',
        # Internal server paths
        r"/opt/[^/\s]*",
        r"/var/[^/\s]*",
        r"/etc/[^/\s]*",
        # Session IDs and tokens
        r'session[_-]?id\s*[:=]\s*["\'][^"\']*["\']',
        r'csrf[_-]?token\s*[:=]\s*["\'][^"\']*["\']',
        # CloudWAN specific sensitive data
        r"global-network-[a-f0-9-]+",
        r"core-network-[a-f0-9-]+",
        r"tgw-[a-f0-9-]+",
        r"vpc-[a-f0-9-]+",
    ]

    # File paths to sanitize from stack traces
    SENSITIVE_PATHS = [
        "/home/",
        "/Users/",
        "C:\\Users\\",
        "/opt/",
        "/var/",
        "/etc/",
        "/.aws/",
        "\\.aws\\",
    ]

    def __init__(self, is_production: bool = None):
        """
        Initialize error sanitizer.

        Args:
            is_production: Whether to enable production-grade sanitization.
                          If None, determined from environment variables.
        """
        if is_production is None:
            # Auto-detect production environment
            self.is_production = (
                os.getenv("ENV", "").lower() in ["production", "prod"]
                or os.getenv("ENVIRONMENT", "").lower() in ["production", "prod"]
                or os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
                or os.getenv("ECS_CONTAINER_METADATA_URI") is not None
            )
        else:
            self.is_production = is_production

        # Compile regex patterns for performance
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SENSITIVE_PATTERNS
        ]

        logger.info(
            f"Production error sanitization: {'ENABLED' if self.is_production else 'DISABLED'}"
        )

    def sanitize_error_message(self, message: str) -> str:
        """
        Sanitize error message by removing sensitive information.

        Args:
            message: Original error message

        Returns:
            Sanitized error message
        """
        if not self.is_production:
            return message

        sanitized = message

        # Apply all sensitive patterns
        for pattern in self._compiled_patterns:
            sanitized = pattern.sub("[REDACTED]", sanitized)

        # Sanitize file paths
        for path in self.SENSITIVE_PATHS:
            if path in sanitized:
                # Replace everything after the sensitive path until next space or quote
                pattern = re.escape(path) + r'[^\s"\']+'
                sanitized = re.sub(pattern, f"{path}[REDACTED]", sanitized, flags=re.IGNORECASE)

        return sanitized

    def sanitize_stack_trace(self, stack_trace: str) -> str:
        """
        Sanitize stack trace by removing sensitive file paths and data.

        Args:
            stack_trace: Original stack trace

        Returns:
            Sanitized stack trace or generic message in production
        """
        if not self.is_production:
            return stack_trace

        # In production, provide only essential debugging info
        lines = stack_trace.split("\n")
        sanitized_lines = []

        for line in lines:
            # Keep function names and error types, but sanitize paths
            if 'File "' in line:
                # Extract just the filename, not the full path
                match = re.search(r'File "([^"]*[/\\])([^/\\]+)", line (\d+)', line)
                if match:
                    filename = match.group(2)
                    line_num = match.group(3)
                    sanitized_line = f'File "[REDACTED]/{filename}", line {line_num}'
                    sanitized_lines.append(sanitized_line)
                else:
                    sanitized_lines.append('File "[REDACTED]"')
            elif line.strip().startswith("in "):
                # Keep function names
                sanitized_lines.append(line)
            elif any(keyword in line for keyword in ["Error:", "Exception:", "Traceback"]):
                # Keep error types and messages (they'll be sanitized separately)
                sanitized_lines.append(self.sanitize_error_message(line))
            elif line.strip() and not any(path in line for path in self.SENSITIVE_PATHS):
                # Keep other non-sensitive lines
                sanitized_lines.append(self.sanitize_error_message(line))

        # If stack trace is too revealing, provide generic message
        if len(sanitized_lines) > 10:
            return (
                "Internal server error occurred. "
                "Contact support with request ID for detailed assistance. "
                "[OWASP ASVS 5.4.3 - Error details hidden in production]"
            )

        return "\n".join(sanitized_lines)

    def sanitize_debug_data(self, debug_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize debug data dictionary.

        Args:
            debug_data: Original debug data

        Returns:
            Sanitized debug data or empty dict in production
        """
        if not self.is_production:
            return debug_data

        # In production, remove all debug data except essential error info
        return {
            "environment": "production",
            "debug_mode": False,
            "message": "Debug information hidden in production environment",
            "compliance": "OWASP ASVS 5.4.3",
        }

    def create_production_safe_error(
        self,
        error_code: str,
        user_message: str,
        internal_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create production-safe error response.

        Args:
            error_code: Error code for categorization
            user_message: Safe message for user display
            internal_message: Internal message (will be sanitized)
            context: Additional context (will be sanitized)

        Returns:
            Production-safe error data
        """
        if self.is_production:
            # Generic user-facing message
            safe_message = self._get_generic_error_message(error_code)

            return {
                "error_code": error_code,
                "message": safe_message,
                "user_message": user_message,
                "timestamp": f"{os.urandom(8).hex()}",  # Random request ID
                "support_info": {
                    "contact": "support@example.com",
                    "documentation": "https://docs.example.com/troubleshooting",
                    "compliance": "OWASP ASVS 5.4.3",
                },
            }
        else:
            # Development mode - include more details
            return {
                "error_code": error_code,
                "message": user_message,
                "internal_message": internal_message,
                "context": context or {},
                "environment": "development",
            }

    def _get_generic_error_message(self, error_code: str) -> str:
        """Get generic error message for production."""
        generic_messages = {
            "ACCESS_DENIED": "Access denied. Please verify your permissions.",
            "RESOURCE_NOT_FOUND": "The requested resource was not found.",
            "INVALID_PARAMS": "Invalid parameters provided.",
            "RATE_LIMITED": "Request rate limit exceeded. Please try again later.",
            "SERVICE_UNAVAILABLE": "Service temporarily unavailable. Please try again later.",
            "INTERNAL_ERROR": "Internal server error. Please contact support.",
            "TIMEOUT": "Request timeout. Please try again.",
            "VALIDATION_ERROR": "Request validation failed.",
        }

        return generic_messages.get(
            error_code,
            "An error occurred while processing your request. Please contact support.",
        )


class MCPErrorHandler:
    """Handles conversion of exceptions to MCP-compliant error responses."""

    def __init__(self, enable_debug: bool = False, is_production: bool = None):
        self.enable_debug = enable_debug
        self.error_mapping = AWSErrorMapping()

        # Initialize production error sanitizer
        self.sanitizer = ProductionErrorSanitizer(is_production=is_production)

    def handle_aws_error(
        self, error: ClientError, context: Optional[ErrorContext] = None
    ) -> McpError:
        """
        Convert AWS ClientError to MCP-compliant error.

        Args:
            error: AWS ClientError exception
            context: Additional error context

        Returns:
            MCP-compliant error response
        """
        # Extract AWS error details
        error_response = error.response.get("Error", {})
        aws_error_code = error_response.get("Code", "UnknownError")
        aws_message = error_response.get("Message", str(error))
        request_id = error.response.get("ResponseMetadata", {}).get("RequestId")

        # Sanitize AWS error message
        sanitized_aws_message = self.sanitizer.sanitize_error_message(aws_message)

        # Map to MCP error code
        mcp_error_code = self.error_mapping.get_mcp_error_code(aws_error_code)

        # Build context
        if context is None:
            context = ErrorContext()

        # Add request ID if available
        if request_id:
            context.request_id = request_id

        # Get troubleshooting tips
        context.troubleshooting_tips = self.error_mapping.get_troubleshooting_tips(
            aws_error_code, context.service
        )

        # Build error message (sanitized)
        error_message = self._build_error_message(
            aws_error_code, sanitized_aws_message, mcp_error_code, context
        )

        # Create error data (sanitized)
        error_data = self._build_error_data(aws_error_code, sanitized_aws_message, context, error)

        logger.warning(
            f"AWS Error mapped to MCP: {aws_error_code} -> {mcp_error_code.value} "
            f"(Service: {context.service}, Region: {context.region})"
        )

        # Convert string error code to integer code for MCP compliance
        mcp_code = self._get_numeric_error_code(mcp_error_code)
        
        # Create ErrorData object
        error_data_obj = ErrorData(
            code=mcp_code,
            message=error_message,
            data=error_data
        )
        
        return McpError(error_data_obj)

    def handle_general_error(
        self, error: Exception, context: Optional[ErrorContext] = None
    ) -> McpError:
        """
        Handle general Python exceptions with MCP compliance.

        Args:
            error: Python exception
            context: Additional error context

        Returns:
            MCP-compliant error response
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Determine MCP error code based on exception type
        if isinstance(error, (ValueError, TypeError)):
            mcp_error_code = MCPErrorCode.INVALID_PARAMS
        elif isinstance(error, PermissionError):
            mcp_error_code = MCPErrorCode.ACCESS_DENIED
        elif isinstance(error, FileNotFoundError):
            mcp_error_code = MCPErrorCode.RESOURCE_NOT_FOUND
        elif isinstance(error, TimeoutError):
            mcp_error_code = MCPErrorCode.TIMEOUT
        elif isinstance(error, ConnectionError):
            mcp_error_code = MCPErrorCode.NETWORK_ERROR
        else:
            mcp_error_code = MCPErrorCode.INTERNAL_ERROR

        # Build context
        if context is None:
            context = ErrorContext()

        context.troubleshooting_tips = [
            "Check input parameters for validity",
            "Verify system state and dependencies",
            "Review error logs for additional context",
            "Contact support if issue persists",
        ]

        # Build error message
        full_message = f"{error_type}: {error_message}"
        if context.operation:
            full_message = f"Operation '{context.operation}' failed: {full_message}"

        # Create error data
        error_data = {
            "error_type": error_type,
            "original_message": error_message,
            "mcp_error_code": mcp_error_code.value,
            "context": {
                "operation": context.operation,
                "service": context.service,
                "region": context.region,
            },
            "troubleshooting": {
                "tips": context.troubleshooting_tips,
                "documentation": "https://github.com/iag/cloudwan-mcp/docs/",
            },
        }

        # Add debug information if enabled (sanitized in production)
        if self.enable_debug:
            raw_traceback = traceback.format_exc()
            sanitized_traceback = self.sanitizer.sanitize_stack_trace(raw_traceback)

            debug_data = {
                "traceback": sanitized_traceback,
                "error_args": getattr(error, "args", []),
            }

            error_data["debug"] = self.sanitizer.sanitize_debug_data(debug_data)

        logger.error(
            f"General error mapped to MCP: {error_type} -> {mcp_error_code.value} "
            f"(Operation: {context.operation})"
        )

        # Convert string error code to integer code for MCP compliance
        mcp_code = self._get_numeric_error_code(mcp_error_code)
        
        # Create ErrorData object
        error_data_obj = ErrorData(
            code=mcp_code,
            message=full_message,
            data=error_data
        )
        
        return McpError(error_data_obj)

    def _get_numeric_error_code(self, mcp_error_code: MCPErrorCode) -> int:
        """
        Convert MCPErrorCode enum to numeric code for MCP protocol.
        
        Args:
            mcp_error_code: The enum error code
            
        Returns:
            Integer error code as defined in MCP protocol
        """
        # Import MCP constants
        from mcp.types import PARSE_ERROR, INVALID_REQUEST, INVALID_PARAMS, INTERNAL_ERROR
        
        # Map our error codes to MCP numeric codes
        code_mapping = {
            MCPErrorCode.PARSE_ERROR: PARSE_ERROR,
            MCPErrorCode.INVALID_REQUEST: INVALID_REQUEST,
            MCPErrorCode.INVALID_PARAMS: INVALID_PARAMS,
            MCPErrorCode.INTERNAL_ERROR: INTERNAL_ERROR,
            # For other codes not defined in MCP, use appropriate mappings
            MCPErrorCode.RESOURCE_NOT_FOUND: INVALID_PARAMS,  # -32602
            MCPErrorCode.RESOURCE_UNAVAILABLE: INTERNAL_ERROR,  # -32603
            MCPErrorCode.ACCESS_DENIED: INVALID_PARAMS,  # -32602
            MCPErrorCode.UNAUTHORIZED: INVALID_PARAMS,  # -32602
            MCPErrorCode.FORBIDDEN: INVALID_PARAMS,  # -32602
            MCPErrorCode.RATE_LIMITED: INTERNAL_ERROR,  # -32603
            MCPErrorCode.QUOTA_EXCEEDED: INTERNAL_ERROR,  # -32603
            MCPErrorCode.SERVICE_UNAVAILABLE: INTERNAL_ERROR,  # -32603
            MCPErrorCode.TIMEOUT: INTERNAL_ERROR,  # -32603
            MCPErrorCode.NETWORK_ERROR: INTERNAL_ERROR,  # -32603
            MCPErrorCode.VALIDATION_ERROR: INVALID_PARAMS,  # -32602
            MCPErrorCode.SCHEMA_ERROR: INVALID_PARAMS,  # -32602
        }
        
        return code_mapping.get(mcp_error_code, INTERNAL_ERROR)

    def _build_error_message(
        self,
        aws_error_code: str,
        aws_message: str,
        mcp_error_code: MCPErrorCode,
        context: ErrorContext,
    ) -> str:
        """Build comprehensive error message."""
        parts = []

        # Service and operation context
        if context.service:
            if context.operation:
                parts.append(
                    f"AWS {context.service.upper()} operation '{context.operation}' failed"
                )
            else:
                parts.append(f"AWS {context.service.upper()} operation failed")

        # Region context
        if context.region:
            parts.append(f"in region {context.region}")

        # Error details
        if parts:
            message = f"{' '.join(parts)}: {aws_error_code} - {aws_message}"
        else:
            message = f"{aws_error_code}: {aws_message}"

        # Resource context
        if context.resource_id:
            message += f" (Resource: {context.resource_id})"

        return message

    def _build_error_data(
        self,
        aws_error_code: str,
        aws_message: str,
        context: ErrorContext,
        original_error: Exception,
    ) -> Dict[str, Any]:
        """Build comprehensive error data."""
        error_data = {
            "aws_error": {
                "code": aws_error_code,
                "message": aws_message,
                "request_id": context.request_id,
            },
            "context": {
                "service": context.service,
                "region": context.region,
                "operation": context.operation,
                "resource_arn": context.resource_arn,
                "resource_id": context.resource_id,
            },
            "troubleshooting": {
                "tips": context.troubleshooting_tips,
                "related_errors": context.related_errors,
                "documentation": (
                    f"https://docs.aws.amazon.com/{context.service}/" if context.service else None
                ),
            },
            "mcp_protocol": {
                "version": "1.0",
                "error_mapping": "AWS-to-MCP",
                "spec_compliance": "MCP-SPEC-101",
            },
        }

        # Add debug information if enabled (sanitized in production)
        if self.enable_debug:
            raw_traceback = traceback.format_exc()
            sanitized_traceback = self.sanitizer.sanitize_stack_trace(raw_traceback)

            debug_data = {
                "traceback": sanitized_traceback,
                "exception_type": type(original_error).__name__,
                "exception_args": getattr(original_error, "args", []),
            }

            error_data["debug"] = self.sanitizer.sanitize_debug_data(debug_data)

        # Remove None values for cleaner output
        error_data = self._clean_dict(error_data)

        return error_data

    def _clean_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove None values from nested dictionary."""
        if not isinstance(data, dict):
            return data

        cleaned = {}
        for key, value in data.items():
            if value is None:
                continue
            elif isinstance(value, dict):
                cleaned_value = self._clean_dict(value)
                if cleaned_value:  # Only add if not empty
                    cleaned[key] = cleaned_value
            elif isinstance(value, list):
                cleaned_value = [
                    self._clean_dict(item) if isinstance(item, dict) else item
                    for item in value
                    if item is not None
                ]
                if cleaned_value:  # Only add if not empty
                    cleaned[key] = cleaned_value
            else:
                cleaned[key] = value

        return cleaned


# Global error handler instance (auto-detects production environment)
error_handler = MCPErrorHandler(enable_debug=False, is_production=None)


def handle_mcp_error(
    error: Exception,
    service: str = None,
    region: str = None,
    operation: str = None,
    resource_id: str = None,
    resource_arn: str = None,
) -> McpError:
    """
    Convenience function to handle any error with MCP compliance.

    Args:
        error: Exception to handle
        service: AWS service name
        region: AWS region
        operation: Operation being performed
        resource_id: Resource identifier
        resource_arn: Resource ARN

    Returns:
        MCP-compliant error response
    """
    context = ErrorContext(
        service=service,
        region=region,
        operation=operation,
        resource_id=resource_id,
        resource_arn=resource_arn,
    )

    if isinstance(error, ClientError):
        return error_handler.handle_aws_error(error, context)
    else:
        return error_handler.handle_general_error(error, context)


def configure_error_handler(enable_debug: bool = False, is_production: bool = None) -> None:
    """Configure global error handler settings."""
    global error_handler
    error_handler = MCPErrorHandler(enable_debug=enable_debug, is_production=is_production)
