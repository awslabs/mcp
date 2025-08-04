"""
Shared exceptions for CloudWAN MCP Server.

This module consolidates all shared exception classes used across the MCP server
to provide consistent error handling and reporting. All exceptions include
comprehensive context information for debugging and operational monitoring.

Key Features:
- Hierarchical exception structure with base CloudWANMCPError
- Multi-region error context support
- Structured error details for programmatic handling
- Integration with MCP protocol error mapping
- Comprehensive logging and monitoring support
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import traceback
import json


class CloudWANMCPError(Exception):
    """
    Base exception class for all CloudWAN MCP Server errors.
    
    Provides comprehensive error context including operation details,
    multi-region information, and structured error data for both
    human-readable messages and programmatic handling.
    
    Attributes:
        message: Human-readable error message
        error_code: Structured error code for programmatic handling
        operation_id: Unique operation identifier for tracing
        component: Component that generated the error
        regions: AWS regions involved in the operation
        details: Additional error context and debugging information
        cause: Optional underlying exception that caused this error
        timestamp: When the error occurred
        severity: Error severity level
        recoverable: Whether the error condition might be temporary
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        operation_id: Optional[str] = None,
        component: Optional[str] = None,
        regions: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        severity: str = "error",
        recoverable: bool = False,
        **kwargs
    ):
        super().__init__(message)
        
        self.message = message
        self.error_code = error_code or "CLOUDWAN_MCP_ERROR"
        self.operation_id = operation_id
        self.component = component
        self.regions = regions or []
        self.details = details or {}
        self.cause = cause
        self.severity = severity  # error, warning, critical
        self.recoverable = recoverable
        self.timestamp = datetime.now()
        
        # Add any additional context from kwargs
        self.details.update(kwargs)
        
        # Capture stack trace if cause is provided
        if cause:
            self.details["cause_trace"] = traceback.format_exception(
                type(cause), cause, cause.__traceback__
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "operation_id": self.operation_id,
            "component": self.component,
            "regions": self.regions,
            "severity": self.severity,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }

    def to_json(self) -> str:
        """Convert exception to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def get_error_summary(self) -> str:
        """Get a concise error summary for logging."""
        return f"{self.error_code}: {self.message}"

    def add_context(self, key: str, value: Any) -> None:
        """Add additional context to error details."""
        self.details[key] = value

    def add_region(self, region: str) -> None:
        """Add a region to the error context."""
        if region not in self.regions:
            self.regions.append(region)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"error_code='{self.error_code}', "
            f"component='{self.component}', "
            f"regions={self.regions})"
        )


class ValidationError(CloudWANMCPError):
    """
    Exception for data validation and input validation errors.
    
    Raised when input data fails validation checks, schema validation,
    or business rule validation. Includes detailed validation failure
    information for client feedback.
    
    Attributes:
        field_errors: Dictionary of field-specific validation errors
        validation_type: Type of validation that failed (schema, business, etc.)
        invalid_value: The value that failed validation
        expected_format: Expected format or constraints
    """

    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, List[str]]] = None,
        validation_type: str = "general",
        invalid_value: Any = None,
        expected_format: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity="error",
            **kwargs
        )
        
        self.field_errors = field_errors or {}
        self.validation_type = validation_type
        self.invalid_value = invalid_value
        self.expected_format = expected_format
        
        # Add validation-specific details
        self.add_context("field_errors", self.field_errors)
        self.add_context("validation_type", self.validation_type)
        self.add_context("invalid_value", str(invalid_value) if invalid_value is not None else None)
        self.add_context("expected_format", self.expected_format)

    def add_field_error(self, field: str, error: str) -> None:
        """Add a field-specific validation error."""
        if field not in self.field_errors:
            self.field_errors[field] = []
        self.field_errors[field].append(error)
        self.add_context("field_errors", self.field_errors)

    def has_field_errors(self) -> bool:
        """Check if there are field-specific validation errors."""
        return bool(self.field_errors)

    def get_field_error_summary(self) -> str:
        """Get summary of all field errors."""
        if not self.field_errors:
            return "No field-specific errors"
        
        errors = []
        for field, field_errs in self.field_errors.items():
            errors.append(f"{field}: {', '.join(field_errs)}")
        return "; ".join(errors)


class AWSOperationError(CloudWANMCPError):
    """
    Exception for AWS API operation failures.
    
    Raised when AWS API calls fail, including network issues, authentication
    problems, authorization failures, and service errors. Includes AWS-specific
    error context for debugging and retry logic.
    
    Attributes:
        aws_error_code: AWS error code from the API response
        status_code: HTTP status code from AWS API
        service: AWS service that generated the error
        operation: AWS API operation that failed
        request_id: AWS request ID for tracking
        retry_after: Suggested retry delay in seconds
    """

    def __init__(
        self,
        message: str,
        aws_error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        # Determine if error is recoverable based on AWS error patterns
        recoverable = AWSOperationError._is_recoverable_aws_error(aws_error_code, status_code)
        
        super().__init__(
            message=message,
            error_code=f"AWS_{aws_error_code}" if aws_error_code else "AWS_OPERATION_ERROR",
            recoverable=recoverable,
            severity="critical" if not recoverable else "error",
            **kwargs
        )
        
        self.aws_error_code = aws_error_code
        self.status_code = status_code
        self.service = service
        self.operation = operation
        self.request_id = request_id
        self.retry_after = retry_after
        
        # Add AWS-specific context
        self.add_context("aws_error_code", aws_error_code)
        self.add_context("status_code", status_code)
        self.add_context("service", service)
        self.add_context("operation", operation)
        self.add_context("request_id", request_id)
        self.add_context("retry_after", retry_after)

    @classmethod
    def _is_recoverable_aws_error(cls, error_code: Optional[str], status_code: Optional[int]) -> bool:
        """Determine if AWS error is potentially recoverable."""
        if not error_code and not status_code:
            return False
            
        # Recoverable error patterns
        recoverable_codes = {
            "Throttling", "ThrottlingException", "ProvisionedThroughputExceededException",
            "ServiceUnavailable", "InternalError", "InternalServerError", 
            "RequestTimeout", "TimeoutException", "NetworkConnectionError",
            "ConnectionError", "EndpointConnectionError", "ReadTimeoutError"
        }
        
        recoverable_status_codes = {429, 500, 502, 503, 504}
        
        return (
            error_code in recoverable_codes or
            status_code in recoverable_status_codes
        )

    def should_retry(self) -> bool:
        """Determine if operation should be retried."""
        return self.recoverable and (
            self.aws_error_code in {
                "Throttling", "ServiceUnavailable", "InternalError", "RequestTimeout"
            } or self.status_code in {429, 500, 502, 503, 504}
        )

    def get_retry_delay(self) -> int:
        """Get suggested retry delay in seconds."""
        if self.retry_after:
            return self.retry_after
        
        # Default retry delays based on error type
        if self.aws_error_code == "Throttling":
            return 5  # Exponential backoff recommended
        elif self.status_code == 429:
            return 10
        elif self.status_code in {500, 502, 503, 504}:
            return 2
        else:
            return 1


class BGPAnalysisError(CloudWANMCPError):
    """
    Exception for BGP protocol analysis failures.
    
    Raised when BGP analysis operations fail, including peer discovery,
    route analysis, protocol compliance checking, and security analysis.
    
    Attributes:
        analysis_type: Type of BGP analysis that failed
        peer_info: Information about BGP peers involved
        route_info: Information about routes being analyzed
        protocol_error: Specific BGP protocol error
    """

    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        peer_info: Optional[Dict[str, Any]] = None,
        route_info: Optional[Dict[str, Any]] = None,
        protocol_error: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="BGP_ANALYSIS_ERROR",
            component="bgp_analyzer",
            **kwargs
        )
        
        self.analysis_type = analysis_type
        self.peer_info = peer_info or {}
        self.route_info = route_info or {}
        self.protocol_error = protocol_error
        
        # Add BGP-specific context
        self.add_context("analysis_type", analysis_type)
        self.add_context("peer_info", peer_info)
        self.add_context("route_info", route_info)
        self.add_context("protocol_error", protocol_error)


class SecurityThreatError(CloudWANMCPError):
    """
    Exception for security threat detection and analysis failures.
    
    Raised when security analysis fails or when security threats are
    detected that require immediate attention.
    
    Attributes:
        threat_type: Type of security threat detected
        threat_level: Severity level of the threat
        affected_resources: Resources affected by the threat
        mitigation_steps: Suggested mitigation steps
        indicators: Security indicators that triggered the alert
    """

    def __init__(
        self,
        message: str,
        threat_type: Optional[str] = None,
        threat_level: str = "unknown",
        affected_resources: Optional[List[str]] = None,
        mitigation_steps: Optional[List[str]] = None,
        indicators: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        # Security threats are critical by default
        severity = "critical" if threat_level in {"critical", "high"} else "error"
        
        super().__init__(
            message=message,
            error_code="SECURITY_THREAT_ERROR",
            component="security_analyzer",
            severity=severity,
            **kwargs
        )
        
        self.threat_type = threat_type
        self.threat_level = threat_level
        self.affected_resources = affected_resources or []
        self.mitigation_steps = mitigation_steps or []
        self.indicators = indicators or {}
        
        # Add security-specific context
        self.add_context("threat_type", threat_type)
        self.add_context("threat_level", threat_level)
        self.add_context("affected_resources", affected_resources)
        self.add_context("mitigation_steps", mitigation_steps)
        self.add_context("security_indicators", indicators)


class NetworkElementError(CloudWANMCPError):
    """
    Exception for network element analysis and discovery failures.
    
    Raised when network topology discovery fails or when network
    element analysis encounters errors.
    
    Attributes:
        element_type: Type of network element involved
        element_id: Identifier of the network element
        discovery_stage: Stage of discovery where error occurred
        topology_context: Topology context information
    """

    def __init__(
        self,
        message: str,
        element_type: Optional[str] = None,
        element_id: Optional[str] = None,
        discovery_stage: Optional[str] = None,
        topology_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="NETWORK_ELEMENT_ERROR",
            component="network_analyzer",
            **kwargs
        )
        
        self.element_type = element_type
        self.element_id = element_id
        self.discovery_stage = discovery_stage
        self.topology_context = topology_context or {}
        
        # Add network element context
        self.add_context("element_type", element_type)
        self.add_context("element_id", element_id)
        self.add_context("discovery_stage", discovery_stage)
        self.add_context("topology_context", topology_context)


class ConfigurationError(CloudWANMCPError):
    """
    Exception for configuration-related errors.
    
    Raised when system configuration is invalid, missing, or incompatible.
    
    Attributes:
        config_section: Configuration section with the error
        config_key: Specific configuration key
        expected_value: Expected configuration value or format
        actual_value: Actual configuration value found
    """

    def __init__(
        self,
        message: str,
        config_section: Optional[str] = None,
        config_key: Optional[str] = None,
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            component="configuration",
            severity="critical",  # Config errors are usually critical
            **kwargs
        )
        
        self.config_section = config_section
        self.config_key = config_key
        self.expected_value = expected_value
        self.actual_value = actual_value
        
        # Add configuration context
        self.add_context("config_section", config_section)
        self.add_context("config_key", config_key)
        self.add_context("expected_value", expected_value)
        self.add_context("actual_value", actual_value)


class MultiRegionOperationError(CloudWANMCPError):
    """
    Exception for multi-region operation failures.
    
    Raised when operations spanning multiple AWS regions fail or
    when region-specific issues affect multi-region operations.
    
    Attributes:
        failed_regions: List of regions where operations failed
        successful_regions: List of regions where operations succeeded
        region_errors: Dictionary mapping regions to their specific errors
        partial_success: Whether some regions succeeded
    """

    def __init__(
        self,
        message: str,
        failed_regions: Optional[List[str]] = None,
        successful_regions: Optional[List[str]] = None,
        region_errors: Optional[Dict[str, str]] = None,
        partial_success: bool = False,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="MULTI_REGION_OPERATION_ERROR",
            regions=(failed_regions or []) + (successful_regions or []),
            severity="error" if partial_success else "critical",
            recoverable=partial_success,  # Might be recoverable if some regions worked
            **kwargs
        )
        
        self.failed_regions = failed_regions or []
        self.successful_regions = successful_regions or []
        self.region_errors = region_errors or {}
        self.partial_success = partial_success
        
        # Add multi-region context
        self.add_context("failed_regions", failed_regions)
        self.add_context("successful_regions", successful_regions)
        self.add_context("region_errors", region_errors)
        self.add_context("partial_success", partial_success)

    def get_failure_rate(self) -> float:
        """Calculate failure rate across regions."""
        total_regions = len(self.failed_regions) + len(self.successful_regions)
        if total_regions == 0:
            return 0.0
        return len(self.failed_regions) / total_regions

    def has_complete_failure(self) -> bool:
        """Check if all regions failed."""
        return len(self.successful_regions) == 0 and len(self.failed_regions) > 0


class TopologyError(CloudWANMCPError):
    """
    Exception for topology-related errors.
    
    Raised when network topology operations fail, including topology construction,
    analysis, validation, and relationship mapping errors.
    
    Attributes:
        topology_id: ID of the topology with the error
        topology_operation: Operation that failed (discovery, analysis, validation)
        element_count: Number of elements in the topology
        connection_count: Number of connections in the topology
        failed_elements: List of element IDs that failed processing
    """

    def __init__(
        self,
        message: str,
        topology_id: Optional[str] = None,
        topology_operation: Optional[str] = None,
        element_count: Optional[int] = None,
        connection_count: Optional[int] = None,
        failed_elements: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="TOPOLOGY_ERROR",
            component="topology_analyzer",
            **kwargs
        )
        
        self.topology_id = topology_id
        self.topology_operation = topology_operation
        self.element_count = element_count
        self.connection_count = connection_count
        self.failed_elements = failed_elements or []
        
        # Add topology context
        self.add_context("topology_id", topology_id)
        self.add_context("topology_operation", topology_operation)
        self.add_context("element_count", element_count)
        self.add_context("connection_count", connection_count)
        self.add_context("failed_elements", failed_elements)

    def add_failed_element(self, element_id: str) -> None:
        """Add an element ID to the failed elements list."""
        if element_id not in self.failed_elements:
            self.failed_elements.append(element_id)
            self.add_context("failed_elements", self.failed_elements)

    def get_failure_summary(self) -> str:
        """Get summary of topology processing failures."""
        if not self.failed_elements:
            return "No specific element failures"
        
        summary = f"{len(self.failed_elements)} element(s) failed: "
        summary += ", ".join(self.failed_elements[:5])
        if len(self.failed_elements) > 5:
            summary += f" (and {len(self.failed_elements) - 5} more)"
        
        return summary


# =============================================================================
# Utility Functions for Exception Handling
# =============================================================================

def create_error_response(
    error: Exception,
    operation_id: Optional[str] = None,
    include_traceback: bool = False
) -> Dict[str, Any]:
    """
    Create standardized error response from exception.
    
    Args:
        error: Exception to convert
        operation_id: Operation ID for tracking
        include_traceback: Whether to include full traceback
        
    Returns:
        Standardized error response dictionary
    """
    if isinstance(error, CloudWANMCPError):
        response = error.to_dict()
        if operation_id:
            response["operation_id"] = operation_id
    else:
        # Handle non-CloudWAN exceptions
        response = {
            "error_type": type(error).__name__,
            "message": str(error),
            "error_code": "UNEXPECTED_ERROR",
            "operation_id": operation_id,
            "component": "unknown",
            "regions": [],
            "severity": "error",
            "recoverable": False,
            "timestamp": datetime.now().isoformat(),
            "details": {},
            "cause": None,
        }
    
    if include_traceback:
        response["traceback"] = traceback.format_exception(
            type(error), error, error.__traceback__
        )
    
    return response


def is_recoverable_error(error: Exception) -> bool:
    """
    Determine if an error is potentially recoverable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error might be recoverable with retry
    """
    if isinstance(error, CloudWANMCPError):
        return error.recoverable
    
    # Check for common recoverable error patterns
    error_str = str(error).lower()
    recoverable_patterns = [
        "timeout", "connection", "network", "throttl", "rate limit",
        "service unavailable", "internal server error", "temporary"
    ]
    
    return any(pattern in error_str for pattern in recoverable_patterns)


def get_error_severity(error: Exception) -> str:
    """
    Determine error severity level.
    
    Args:
        error: Exception to analyze
        
    Returns:
        Severity level (critical, error, warning)
    """
    if isinstance(error, CloudWANMCPError):
        return error.severity
    
    # Default severity based on exception type
    if isinstance(error, (KeyboardInterrupt, SystemExit)):
        return "critical"
    elif isinstance(error, (ValueError, TypeError, AttributeError)):
        return "error"
    else:
        return "error"


# Export commonly used exception groups
VALIDATION_EXCEPTIONS = [ValidationError, ConfigurationError]
AWS_EXCEPTIONS = [AWSOperationError, MultiRegionOperationError]
ANALYSIS_EXCEPTIONS = [BGPAnalysisError, NetworkElementError, SecurityThreatError, TopologyError]
CORE_EXCEPTIONS = [CloudWANMCPError] + VALIDATION_EXCEPTIONS + AWS_EXCEPTIONS + ANALYSIS_EXCEPTIONS

ALL_SHARED_EXCEPTIONS = CORE_EXCEPTIONS